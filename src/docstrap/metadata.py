"""Metadata SQLite store — docstrap's system-of-record for documents.

Owned by docstrap; nothing else writes to this database. WAL mode so
the daemon (future) and the CLI can operate concurrently without
contention.

Design notes:
- No frontmatter or sidecar files touched — content files stay pure content.
- No `in_git` column; docstrap queries git at operation time when needed.
- Document IDs are ULIDs (26-char Crockford base32, timestamp-prefixed,
  sortable). Self-contained generator here — no external dependency.

**There is no migration machinery**, and `SCHEMA` below is replayed with
`CREATE TABLE IF NOT EXISTS` on every open. The distinction that follows
from that is load-bearing and is the reason `file_index` could be added
at all: a *table* missing from an existing database is created by the
replay, so adding one reaches every database that already exists. A
*column* added to a table that already exists is not, and never will be
until an upgrade path exists — a user's data
silently stays on the old shape and nothing says so. Add a table if you
must; do not add a column.
"""
from __future__ import annotations

import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

from docstrap import paths

# --- ULID ------------------------------------------------------------------

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"  # 32-char, no I/L/O/U


def _encode_crockford(value: int, length: int) -> str:
    """Encode an integer as a fixed-length Crockford base32 string."""
    chars = []
    for _ in range(length):
        chars.append(_CROCKFORD[value & 0x1F])
        value >>= 5
    return "".join(reversed(chars))


def new_ulid() -> str:
    """Generate a new ULID: 26-char Crockford base32 (10 time + 16 random)."""
    ts_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    rand = int.from_bytes(secrets.token_bytes(10), "big")
    return _encode_crockford(ts_ms, 10) + _encode_crockford(rand, 16)


# --- schema ----------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
  id             TEXT PRIMARY KEY,
  project        TEXT NOT NULL,
  current_path   TEXT NOT NULL,
  current_status TEXT NOT NULL,
  title          TEXT,
  tags           TEXT,
  created_at     TEXT NOT NULL,
  updated_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS documents_current_path ON documents(current_path);
CREATE INDEX IF NOT EXISTS documents_project      ON documents(project);

CREATE TABLE IF NOT EXISTS path_history (
  seq          INTEGER PRIMARY KEY AUTOINCREMENT,
  document_id  TEXT NOT NULL REFERENCES documents(id),
  path         TEXT NOT NULL,
  moved_at     TEXT NOT NULL,
  source       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS status_history (
  seq          INTEGER PRIMARY KEY AUTOINCREMENT,
  document_id  TEXT NOT NULL REFERENCES documents(id),
  status       TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  changed_at   TEXT NOT NULL,
  source       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS content_observations (
  seq              INTEGER PRIMARY KEY AUTOINCREMENT,
  document_id      TEXT NOT NULL REFERENCES documents(id),
  content_hash     TEXT NOT NULL,
  observed_at      TEXT NOT NULL,
  observed_at_path TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS content_observations_by_hash ON content_observations(content_hash);

-- The file index. What a published directory contains, answerable
-- without touching the filesystem. Written by `docstrap.fileindex`,
-- which is the only module that reads or writes it; see its docstring
-- for why it is a table of its own and not more `content_observations`.
--
-- Derived and disposable: drop it and the next build fills it in.
-- Nothing else in this schema is, which is why it is the one table a
-- reader may treat as a cache.
--
-- `document_id` deliberately declares no REFERENCES. A derived
-- projection must never be able to block a write to the system of
-- record, and `PRAGMA foreign_keys = ON` would let a stale index row
-- refuse a `documents` delete.
CREATE TABLE IF NOT EXISTS file_index (
  project        TEXT NOT NULL,
  docname        TEXT NOT NULL,
  path           TEXT NOT NULL,
  parent_docname TEXT NOT NULL,
  kind           TEXT NOT NULL,
  grouping       TEXT NOT NULL,
  title          TEXT NOT NULL,
  sort_key       TEXT NOT NULL,
  content_hash   TEXT NOT NULL,
  document_id    TEXT,
  observed_at    TEXT NOT NULL,
  PRIMARY KEY (project, docname)
);
CREATE INDEX IF NOT EXISTS file_index_parent ON file_index(project, parent_docname);
CREATE INDEX IF NOT EXISTS file_index_hash   ON file_index(content_hash);
CREATE INDEX IF NOT EXISTS file_index_path   ON file_index(path);
"""

VALID_STATUSES: frozenset[str] = frozenset(
    {"draft", "proposal", "spec", "plan", "active", "archived"}
)


class MetadataError(Exception):
    """Raised for schema / data errors from the metadata store."""


# --- connection management -------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@contextmanager
def connect(db_path: Optional[Path] = None) -> Iterator[sqlite3.Connection]:
    """Yield a WAL-mode SQLite connection to the metadata DB.

    Ensures the parent directory exists, creates the schema on first
    open, sets WAL journal mode, uses foreign-key enforcement.
    """
    path = db_path or paths.metadata_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(SCHEMA)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def initialize(db_path: Optional[Path] = None) -> Path:
    """Create the metadata database if it doesn't exist. Return its path."""
    path = db_path or paths.metadata_db_path()
    with connect(path):
        pass
    return path


# --- dataclass wrappers ----------------------------------------------------


@dataclass
class Document:
    id: str
    project: str
    current_path: str
    current_status: str
    title: Optional[str]
    tags: list[str]
    created_at: str
    updated_at: str


def _row_to_document(row: sqlite3.Row) -> Document:
    return Document(
        id=row["id"],
        project=row["project"],
        current_path=row["current_path"],
        current_status=row["current_status"],
        title=row["title"],
        tags=json.loads(row["tags"]) if row["tags"] else [],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


# --- lookups ---------------------------------------------------------------


def get_document_by_id(doc_id: str, db_path: Optional[Path] = None) -> Optional[Document]:
    with connect(db_path) as conn:
        row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
        return _row_to_document(row) if row else None


def get_document_by_path(path: str, db_path: Optional[Path] = None) -> Optional[Document]:
    """Look up a document by its current_path. Path must be exactly what's stored."""
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM documents WHERE current_path = ?", (path,)
        ).fetchone()
        return _row_to_document(row) if row else None


def ids_by_path(db_path: Optional[Path] = None) -> dict[str, str]:
    """Every document's current path mapped to its id, in one query.

    For a caller holding many paths at once — the file index, which links
    each entry to a document row when there is one. Asking per path costs
    a connection each, and a connection replays the whole schema: 222 µs
    a file, against 1.6 µs to hash it.
    """
    with connect(db_path) as conn:
        return {
            row["current_path"]: row["id"]
            for row in conn.execute("SELECT id, current_path FROM documents")
        }


def list_documents(
    project: Optional[str] = None, db_path: Optional[Path] = None
) -> list[Document]:
    with connect(db_path) as conn:
        if project is None:
            rows = conn.execute("SELECT * FROM documents ORDER BY project, current_path").fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM documents WHERE project = ? ORDER BY current_path",
                (project,),
            ).fetchall()
        return [_row_to_document(r) for r in rows]


# --- mutations -------------------------------------------------------------


def _normalise_path(p: str) -> str:
    """Canonicalise a path string for storage (absolute, resolved)."""
    return str(Path(p).expanduser().resolve())


def _validate_status(status: str) -> None:
    if status not in VALID_STATUSES:
        raise MetadataError(
            f"invalid status {status!r}; must be one of {sorted(VALID_STATUSES)}"
        )


def git_blob_hash(data: bytes) -> str:
    """Git's blob hash for these bytes. docstrap's one content hash.

    Public because the file index hashes bytes it has already read and
    must not arrive at a different answer from ``status_history`` and
    ``content_observations`` for the same file — the hash is how a
    renamed file is recognised across both.
    """
    import hashlib

    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def _git_hash_object(path: str) -> str:
    """Compute git's blob hash for a file's current content."""
    p = Path(path)
    if not p.exists():
        return ""
    return git_blob_hash(p.read_bytes())


def create_document(
    project: str,
    path: str,
    status: str,
    title: Optional[str] = None,
    tags: Optional[list[str]] = None,
    source: str = "user",
    db_path: Optional[Path] = None,
) -> Document:
    """Insert a new document row + first path_history and status_history entries."""
    _validate_status(status)
    doc_id = new_ulid()
    now = _now_iso()
    abs_path = _normalise_path(path)
    tags_json = json.dumps(tags or [])
    with connect(db_path) as conn:
        conn.execute(
            "INSERT INTO documents (id, project, current_path, current_status, title, tags, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (doc_id, project, abs_path, status, title, tags_json, now, now),
        )
        conn.execute(
            "INSERT INTO path_history (document_id, path, moved_at, source) VALUES (?, ?, ?, ?)",
            (doc_id, abs_path, now, "create"),
        )
        content_hash = _git_hash_object(abs_path)
        conn.execute(
            "INSERT INTO status_history (document_id, status, content_hash, changed_at, source) "
            "VALUES (?, ?, ?, ?, ?)",
            (doc_id, status, content_hash, now, source),
        )
        if content_hash:
            conn.execute(
                "INSERT INTO content_observations (document_id, content_hash, observed_at, observed_at_path) "
                "VALUES (?, ?, ?, ?)",
                (doc_id, content_hash, now, abs_path),
            )
    return Document(
        id=doc_id,
        project=project,
        current_path=abs_path,
        current_status=status,
        title=title,
        tags=tags or [],
        created_at=now,
        updated_at=now,
    )


def set_status(
    doc_id: str, status: str, source: str = "user", db_path: Optional[Path] = None
) -> Document:
    """Change a document's current status; append to status_history."""
    _validate_status(status)
    now = _now_iso()
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT current_path FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
        if not row:
            raise MetadataError(f"no such document id: {doc_id}")
        content_hash = _git_hash_object(row["current_path"])
        conn.execute(
            "UPDATE documents SET current_status = ?, updated_at = ? WHERE id = ?",
            (status, now, doc_id),
        )
        conn.execute(
            "INSERT INTO status_history (document_id, status, content_hash, changed_at, source) "
            "VALUES (?, ?, ?, ?, ?)",
            (doc_id, status, content_hash, now, source),
        )
    updated = get_document_by_id(doc_id, db_path)
    assert updated is not None
    return updated


def set_tags(doc_id: str, tags: list[str], db_path: Optional[Path] = None) -> Document:
    """Replace a document's tags with the given list (deduplicated, sorted)."""
    now = _now_iso()
    normalised = sorted(set(t.strip() for t in tags if t.strip()))
    with connect(db_path) as conn:
        cur = conn.execute(
            "UPDATE documents SET tags = ?, updated_at = ? WHERE id = ?",
            (json.dumps(normalised), now, doc_id),
        )
        if cur.rowcount == 0:
            raise MetadataError(f"no such document id: {doc_id}")
    updated = get_document_by_id(doc_id, db_path)
    assert updated is not None
    return updated


def record_move(
    doc_id: str, new_path: str, source: str = "rename", db_path: Optional[Path] = None
) -> Document:
    """Update current_path and append to path_history."""
    now = _now_iso()
    abs_path = _normalise_path(new_path)
    with connect(db_path) as conn:
        cur = conn.execute(
            "UPDATE documents SET current_path = ?, updated_at = ? WHERE id = ?",
            (abs_path, now, doc_id),
        )
        if cur.rowcount == 0:
            raise MetadataError(f"no such document id: {doc_id}")
        conn.execute(
            "INSERT INTO path_history (document_id, path, moved_at, source) VALUES (?, ?, ?, ?)",
            (doc_id, abs_path, now, source),
        )
    updated = get_document_by_id(doc_id, db_path)
    assert updated is not None
    return updated


def record_observation(
    doc_id: str, path: str, db_path: Optional[Path] = None
) -> str:
    """Compute git-hash of the file at path; record it. Returns the hash."""
    now = _now_iso()
    abs_path = _normalise_path(path)
    content_hash = _git_hash_object(abs_path)
    if not content_hash:
        return ""
    with connect(db_path) as conn:
        conn.execute(
            "INSERT INTO content_observations (document_id, content_hash, observed_at, observed_at_path) "
            "VALUES (?, ?, ?, ?)",
            (doc_id, content_hash, now, abs_path),
        )
    return content_hash


def get_or_create_document(
    project: str, path: str, default_status: str = "draft", db_path: Optional[Path] = None
) -> Document:
    """Convenience: fetch existing document by path or create a new one at draft."""
    abs_path = _normalise_path(path)
    existing = get_document_by_path(abs_path, db_path)
    if existing is not None:
        return existing
    return create_document(
        project=project,
        path=abs_path,
        status=default_status,
        db_path=db_path,
    )
