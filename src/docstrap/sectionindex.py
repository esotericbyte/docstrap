"""Section pages: which directories get one, and what one contains.

A docs tree is directories, and a directory with no landing page is a
hole in the sidebar. docstrap composes a section page for every one of
them — a heading and a listing of that directory's children — with no
exception for a directory that holds an `index.md`, because a docs tree
is not allowed to hold one. See :data:`REFUSED_INDEX_FILES`.

**A section page is never markdown.** An index is HTML only, and since
the output is HTML no intermediate markdown step is kept in the build
either. So this module composes a *model* — :class:`SectionPage` — and
:mod:`docstrap.sphinx.composed` turns it into a document node tree that
Sphinx renders straight to HTML. No markdown is produced at any stage,
by anything, anywhere.

This module is the one owner of two facts, because several callers need
the same answer and a second implementation is how a generated file
stopped being recognisable as generated:

1. **The content.** :func:`compose` returns the model a section page
   holds, read from the file index and never from a directory walk. The
   parser renders it during a build; a watcher will call it for the one
   directory that changed.
2. **The sites.** :func:`sites` yields the directories that get a page,
   and :func:`is_section_dir` is the predicate underneath it. The build
   applies the predicate as it mirrors; the ``generated-indexes`` report
   walks the project with it, because that is where the old writes
   landed.

Nothing here writes, and nothing here reads a directory except
:func:`sites`, which exists for the report.
"""
from __future__ import annotations

import os
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from docstrap import fileindex

#: An index file in a documentation tree, which docstrap neither
#: publishes nor lets stand in for the page it composes. docstrap creates
#: section pages ephemerally, as part of its build, in its own
#: directories; a documentation tree holds no index.md at all. `index.rst`
#: is the same file under another suffix and is refused beside it.
#:
#: This replaced a "the user wrote their own index" check reading the
#: same two names. That check is what made the first build's output
#: permanent and let it go stale in place — a directory that already had
#: an `index.md` was skipped, so the file docstrap wrote was never the
#: file docstrap wrote again. Now nothing is written into a tree and
#: nothing in a tree is read as a landing page, so the exception has
#: nothing left to protect.
REFUSED_INDEX_FILES = frozenset({"index.md", "index.rst"})

#: The name a section page takes as a docname. It has no file extension
#: because it has no file: the page exists as a document inside the build
#: and is written out as `index.html`.
GENERATED_INDEX_NAME = "index"

#: Directory names that are never a documentation section, whatever a
#: project declares and whether or not they are hidden. A docs tree does
#: not publish its own tooling, and walking one of these costs a great
#: deal to learn nothing.
NEVER_A_SECTION = frozenset({
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
})


def humanize(name: str) -> str:
    """dashes/underscores → spaces, title-case for display."""
    return name.replace("-", " ").replace("_", " ").strip().title() or name


def _is_hidden(name: str) -> bool:
    """Names a docs tree carries but a docs *site* does not.

    A leading dot or underscore marks a directory as infrastructure —
    ``.git``, ``_build``, ``_static``. Sphinx does not publish them and no
    listing names them, so no section page is composed for them either.
    """
    return name.startswith((".", "_"))


def is_section_dir(
    name: str,
    exclude_dirs: set[str],
    *,
    include_hidden: bool = False,
) -> bool:
    """Whether a directory of this name is a section of the site.

    One predicate, because the build decides from it which directories it
    indexes and gives a page to, and :func:`sites` decides from it which
    directories the report looks in. Two predicates that disagreed would
    put a listing entry in front of a page nothing ever composed.
    """
    if name in exclude_dirs or name in NEVER_A_SECTION:
        return False
    return include_hidden or not _is_hidden(name)


def is_document_file(
    name: str,
    exclude_suffixes: set[str],
    *,
    document_suffixes: tuple[str, ...] = (".md", ".rst"),
) -> bool:
    """Whether a file of this name is published as a page of its own.

    The companion to :func:`is_section_dir`, and the second half of what
    the build indexes. An `index.md` is excluded because it is not
    allowed to be in a docs tree at all — see
    :data:`REFUSED_INDEX_FILES`. It once was excluded for the opposite
    reason, that it *became* the section's landing.
    """
    if _is_hidden(name):
        return False
    if name in REFUSED_INDEX_FILES:
        return False
    if not name.endswith(document_suffixes):
        return False
    return not any(name.endswith(s) for s in exclude_suffixes)


# --- what a section page contains ------------------------------------------


@dataclass(frozen=True)
class Listing:
    """One entry on a section page: a docname and a caption for it.

    ``title`` is what the index knows the entry is called. It is not
    necessarily what the rendered link says — Sphinx substitutes the
    target document's own title when it resolves a listing — so it is
    here for a caller that wants an answer without a Sphinx run.
    """

    docname: str
    title: str
    is_section: bool


@dataclass(frozen=True)
class SectionPage:
    """A section page, decided and not yet rendered.

    ``groups`` is a list of (caption, entries). A section has exactly one
    group; a project's root page has one per role among its sources —
    always one for its documentation, and one for drafts or any other
    role only when that role has something to list. Empty groups are dropped
    before the page is built, so an empty list here means a section with
    nothing in it — which is a page that says so rather than no page.
    """

    docname: str
    title: str
    groups: list[tuple[str, list[Listing]]]

    @property
    def is_empty(self) -> bool:
        return not any(entries for _caption, entries in self.groups)


#: The captions a project root's listings carry, one per source role. A
#: role docstrap does not name is captioned with the role itself. A
#: section's own listing is captioned with the section's title.
DOCS_CAPTION = "Docs"
DRAFTS_CAPTION = "Drafts"


def _caption(role: str) -> str:
    """What a root listing of ``role`` is captioned: the role, in words.

    A caption is the source's role and nothing else. It
    does not say which source or which plugin a listing came from.
    """
    if role == fileindex.DOCS:
        return DOCS_CAPTION
    if role == fileindex.DRAFTS:
        return DRAFTS_CAPTION
    return humanize(role)


def _listings(entries: list[fileindex.Entry]) -> list[Listing]:
    return [
        Listing(docname=e.docname, title=e.title, is_section=e.is_section)
        for e in entries
    ]


def compose(
    project: str,
    docname: str,
    db_path: Optional[Path] = None,
) -> SectionPage:
    """The page ``docname`` gets, composed from what the index holds.

    One indexed lookup per group and no filesystem access at all, which
    is what makes this callable from inside a Sphinx parser, from a
    watcher handling a single creation event, and from a test, without
    any of them needing the tree in front of them.

    The project's root page is the docname :data:`GENERATED_INDEX_NAME`
    and is the one that can carry several groups, one per source role, in
    the order documentation, every other role by name, drafts; every
    other section carries one.
    """
    entry = fileindex.get(project, docname, db_path)
    title = entry.title if entry is not None else humanize(
        docname.rsplit("/", 2)[-2] if "/" in docname else docname
    )

    if docname == GENERATED_INDEX_NAME:
        by_role: dict[str, list[fileindex.Entry]] = {fileindex.DOCS: []}
        for child in fileindex.children(project, docname, None, db_path):
            by_role.setdefault(child.grouping, []).append(child)
        roles = sorted(
            by_role,
            key=lambda r: (r == fileindex.DRAFTS, r != fileindex.DOCS, r),
        )
        groups = [
            (_caption(role), _listings(by_role[role]))
            for role in roles
            if role == fileindex.DOCS or by_role[role]
        ]
        return SectionPage(docname=docname, title=title, groups=groups)

    entries = _listings(fileindex.children(project, docname, None, db_path))
    return SectionPage(docname=docname, title=title, groups=[(title, entries)])


# --- which directories get one ---------------------------------------------


def sites(
    root: Path,
    exclude_dirs: set[str],
    *,
    follow_symlinks: bool,
    include_hidden: bool = False,
) -> Iterator[Path]:
    """Every directory below ``root`` that is a section of the site.

    ``root`` itself is never yielded: a tree's landing page is the
    project root's page, not a section's.

    This is the report's walk. A build no longer performs it — it decides
    the same question with :func:`is_section_dir` as it mirrors the tree
    it was going to walk anyway — but the report has to find files that
    earlier builds left, and for that it has to reach where those builds
    reached.

    ``follow_symlinks`` is the whole difference between the two reaches.
    A build that walked its scratch tree with symlinks followed was
    walking through a hole into somebody's repository, and that is how
    the writes landed there. The report passes ``True`` deliberately,
    because that is the reach the writes had.

    ``include_hidden`` is the report's honesty rather than the build's
    behaviour. No section page is composed for a dotted or underscored
    directory, but an earlier generator descended into them, so a file
    may be sitting in one — and a report that pruned them would tell the
    cleanup a file it cannot see is not there. Vendored and build trees
    stay pruned either way.

    A directory already visited by realpath is not visited twice, so a
    symlink cycle terminates instead of recurring.
    """
    root_real = os.path.realpath(root)
    seen: set[str] = {root_real}

    for current, dirs, _files in os.walk(str(root), followlinks=follow_symlinks):
        dirs[:] = sorted(
            d for d in dirs
            if is_section_dir(d, exclude_dirs, include_hidden=include_hidden)
        )
        real = os.path.realpath(current)
        if real in seen and current != str(root):
            dirs.clear()
            continue
        seen.add(real)
        if real == root_real:
            continue
        yield Path(current)
