"""The file index: what a published directory contains, from a table.

Files are indexed in a database table with paths and hashes. This is
that table's one owner. Nothing else reads or
writes `file_index`; the schema itself lives in :mod:`docstrap.metadata`,
which owns the shape of the store.

**Why a table of its own rather than more `content_observations`.** That
table is an append-only *log* — one row per time a document's bytes were
seen — hanging off a `documents` row by foreign key. Three things follow
and each one rules it out for this job. Answering "what is in this
directory now" from a log means finding the latest observation per
document and then establishing that the document still exists, which is a
query over history pretending to be a query over state. Every indexed
file would need a `documents` row first, so indexing a docs tree would
mint a ULID for every markdown file in it, filling the system of record
with rows nobody asked for. And an index is
*derived*: it may be dropped and recomputed at will, which is true of
nothing else in that database. A disposable projection does not belong in
the system of record's own tables.

It does belong in the same *database*, and that is deliberate too. The
rename requirement is answered by joining `documents` and `path_history`,
which live here; a second file would push that join into Python for no
gain, and would need a second connection owner, a second schema and a
second set of paths.

**How a rename survives.** Two ways, and which one applies depends on
whether the metadata store knows the file at all.

1. It has a `documents` row. Then `document_id` carries the identity and
   the rename is already handled where renames are handled — `documents.
   current_path` moves and `path_history` gains a row. The index row is
   re-keyed on the new docname and points at the same document.
2. It has no `documents` row, which is the ordinary case for a file
   nobody has tagged. Then `content_hash` is the identity: the same bytes
   under a new path are recognisable as a move rather than as a deletion
   and an unrelated arrival. :func:`by_content_hash` is that lookup, and
   `file_index_hash` is the index that makes it cheap.

**Written incrementally, not only rebuilt.** :func:`record` puts one
entry in place and :func:`forget` takes one out; :func:`reconcile` is
built from them and adds only "and delete what I did not mention". The
planned filesystem watcher is the intended writer and
it will only ever know about one path at a time, so the one-path calls
are the primitives and the whole-project call is the convenience.

Nothing here reads a document's bytes or walks a directory. The caller
brings the entries; this module stores them and answers questions about
them.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from docstrap.config import DOCUMENTATION_ROLE, DRAFT_ROLE
from docstrap.metadata import connect

#: A file that is published as a page of its own.
DOCUMENT = "document"

#: A directory that is published as a section, with a page listing what
#: it holds. The project's own root is one of these.
SECTION = "section"

#: An entry's `grouping` is the role of the source it came from — an open
#: vocabulary, so these two are the roles docstrap names rather than the
#: only values the column holds. Content a project
#: publishes as documentation:
DOCS = DOCUMENTATION_ROLE

#: Draft content, which the site shows in a listing of its own and never
#: walks as a document.
DRAFTS = DRAFT_ROLE

#: The docname a section's own page takes, and therefore the suffix of
#: every section docname below the root. A parent lists a child section
#: as `<name>/index`, which is the name Sphinx resolves.
SECTION_DOCNAME = "index"


@dataclass(frozen=True)
class Entry:
    """One indexed path.

    ``docname`` is the name the built site gives it — relative to the
    site root for this project, without a suffix — and it is the key,
    together with the project. ``path`` is where the bytes actually are,
    which for a draft is outside the project entirely.

    ``parent_docname`` is the section page that lists this entry, so a
    directory's contents are one indexed lookup and never a walk. The
    project root's own entry has ``''`` — it is listed by nothing.
    """

    project: str
    docname: str
    path: str
    parent_docname: str
    kind: str
    grouping: str = DOCS
    title: str = ""
    sort_key: str = ""
    content_hash: str = ""
    document_id: Optional[str] = None
    observed_at: str = ""

    @property
    def is_section(self) -> bool:
        return self.kind == SECTION


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _row_to_entry(row: sqlite3.Row) -> Entry:
    return Entry(
        project=row["project"],
        docname=row["docname"],
        path=row["path"],
        parent_docname=row["parent_docname"],
        kind=row["kind"],
        grouping=row["grouping"],
        title=row["title"],
        sort_key=row["sort_key"],
        content_hash=row["content_hash"],
        document_id=row["document_id"],
        observed_at=row["observed_at"],
    )


_UPSERT = """
INSERT INTO file_index
  (project, docname, path, parent_docname, kind, grouping, title,
   sort_key, content_hash, document_id, observed_at)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(project, docname) DO UPDATE SET
  path           = excluded.path,
  parent_docname = excluded.parent_docname,
  kind           = excluded.kind,
  grouping       = excluded.grouping,
  title          = excluded.title,
  sort_key       = excluded.sort_key,
  content_hash   = excluded.content_hash,
  document_id    = excluded.document_id,
  observed_at    = excluded.observed_at
"""


def _params(entry: Entry, now: str) -> tuple:
    return (
        entry.project,
        entry.docname,
        entry.path,
        entry.parent_docname,
        entry.kind,
        entry.grouping,
        entry.title or entry.docname.rsplit("/", 1)[-1],
        entry.sort_key or entry.docname.rsplit("/", 1)[-1],
        entry.content_hash,
        entry.document_id,
        entry.observed_at or now,
    )


# --- writing ---------------------------------------------------------------


def record(entry: Entry, db_path: Optional[Path] = None) -> Entry:
    """Put one entry in the index, replacing whatever was at its docname.

    The primitive. A watcher that has seen one file appear calls this and
    nothing else — there is no whole-project pass it has to trigger and
    no invalidation to perform, because nothing downstream is cached.
    """
    now = _now_iso()
    with connect(db_path) as conn:
        conn.execute(_UPSERT, _params(entry, now))
    return replace(entry, observed_at=entry.observed_at or now)


def record_many(entries: list[Entry], db_path: Optional[Path] = None) -> int:
    """:func:`record` for a batch, in one transaction. Returns the count."""
    if not entries:
        return 0
    now = _now_iso()
    with connect(db_path) as conn:
        conn.executemany(_UPSERT, [_params(e, now) for e in entries])
    return len(entries)


def forget(project: str, docname: str, db_path: Optional[Path] = None) -> bool:
    """Drop one entry. True when there was one to drop."""
    with connect(db_path) as conn:
        cur = conn.execute(
            "DELETE FROM file_index WHERE project = ? AND docname = ?",
            (project, docname),
        )
        return cur.rowcount > 0


def forget_path(path: str | Path, db_path: Optional[Path] = None) -> int:
    """Drop every entry pointing at ``path``. Returns how many.

    The deletion a watcher performs: it sees a path go, not a docname.
    """
    resolved = str(Path(path).expanduser().resolve())
    with connect(db_path) as conn:
        cur = conn.execute("DELETE FROM file_index WHERE path = ?", (resolved,))
        return cur.rowcount


def reconcile(
    project: str, entries: list[Entry], db_path: Optional[Path] = None
) -> int:
    """Make the index for ``project`` be exactly ``entries``.

    Upserts every entry and deletes the project's rows that are not among
    them, in one transaction. A build calls this because a build has just
    looked at the whole tree anyway; nothing else needs to, and nothing
    downstream notices the difference between this and a sequence of
    :func:`record` calls.

    Returns the number of rows removed.
    """
    now = _now_iso()
    keep = {e.docname for e in entries}
    with connect(db_path) as conn:
        if entries:
            conn.executemany(_UPSERT, [_params(e, now) for e in entries])
        existing = {
            row["docname"]
            for row in conn.execute(
                "SELECT docname FROM file_index WHERE project = ?", (project,)
            )
        }
        gone = sorted(existing - keep)
        if gone:
            conn.executemany(
                "DELETE FROM file_index WHERE project = ? AND docname = ?",
                [(project, docname) for docname in gone],
            )
    return len(gone)


def drop_project(project: str, db_path: Optional[Path] = None) -> int:
    """Forget a whole project. Returns how many entries went."""
    with connect(db_path) as conn:
        cur = conn.execute("DELETE FROM file_index WHERE project = ?", (project,))
        return cur.rowcount


# --- reading ---------------------------------------------------------------


def children(
    project: str,
    parent_docname: str,
    grouping: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> list[Entry]:
    """What a section contains, in the order its page lists it.

    The query the whole table exists for, and it touches no filesystem.
    Ordering is by ``sort_key`` — the entry's own filename, so a
    directory and a document interleave alphabetically exactly as they
    did when a walk decided this.
    """
    sql = (
        "SELECT * FROM file_index WHERE project = ? AND parent_docname = ?"
    )
    params: list[object] = [project, parent_docname]
    if grouping is not None:
        sql += " AND grouping = ?"
        params.append(grouping)
    sql += " ORDER BY sort_key, docname"
    with connect(db_path) as conn:
        return [_row_to_entry(r) for r in conn.execute(sql, params)]


def get(
    project: str, docname: str, db_path: Optional[Path] = None
) -> Optional[Entry]:
    """One entry by its docname, or None."""
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM file_index WHERE project = ? AND docname = ?",
            (project, docname),
        ).fetchone()
        return _row_to_entry(row) if row else None


def list_project(project: str, db_path: Optional[Path] = None) -> list[Entry]:
    """Every entry a project has, in docname order."""
    with connect(db_path) as conn:
        return [
            _row_to_entry(r)
            for r in conn.execute(
                "SELECT * FROM file_index WHERE project = ? ORDER BY docname",
                (project,),
            )
        ]


def by_content_hash(
    content_hash: str, db_path: Optional[Path] = None
) -> list[Entry]:
    """Every entry holding these exact bytes, anywhere, in any project.

    How a move is recognised for a file the metadata store has never been
    told about: the same hash under a different path is one document that
    moved, not one that vanished and one that arrived. A caller that
    wants document *identity* rather than a guess should look at
    ``document_id`` first and only fall back to this.
    """
    if not content_hash:
        return []
    with connect(db_path) as conn:
        return [
            _row_to_entry(r)
            for r in conn.execute(
                "SELECT * FROM file_index WHERE content_hash = ? "
                "ORDER BY project, docname",
                (content_hash,),
            )
        ]


def by_path(path: str | Path, db_path: Optional[Path] = None) -> list[Entry]:
    """Every entry pointing at ``path``."""
    resolved = str(Path(path).expanduser().resolve())
    with connect(db_path) as conn:
        return [
            _row_to_entry(r)
            for r in conn.execute(
                "SELECT * FROM file_index WHERE path = ? ORDER BY project, docname",
                (resolved,),
            )
        ]
