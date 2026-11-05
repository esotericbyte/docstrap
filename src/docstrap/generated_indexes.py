"""Which `index.md` files in a project a build put there.

Builds up to 0.0.3 composed their section pages by walking a scratch tree
of symlinks with ``followlinks=True``, so the writes went through the
links and landed in the project. Fifty-five such files are tracked across
five repositories. No build writes one any more — since 0.0.4 no build
produces markdown for a section page at all, anywhere, see
:mod:`docstrap.sphinx.composed` — which stops the bleeding but does not
identify what is already committed. The cleanup has to know which files
are docstrap's before it deletes anything.

**The discrimination comes from what docstrap knows, never from reading
the prose.** Two facts are known and both are exact:

1. **Where those builds wrote.** :func:`docstrap.sectionindex.sites`
   yields the directories, and this module runs it over the project with
   the reach the old walk had. A path this walk does not reach is not
   docstrap's, whatever is in it.
2. **What those builds wrote.** :func:`legacy_markdown` reproduces the
   exact bytes. A file equal to them is docstrap's output; a file that
   differs is not claimed.

**The bytes are frozen here on purpose**, and that is new. They used to
come from the live composer, which meant the report's answer moved
whenever the composer did — and the composer has now moved so far that
it produces no bytes at all. A recogniser of files written in the past
has to keep describing the past. :func:`legacy_markdown` and
:func:`legacy_children` are therefore copies, deliberately not shared
with anything, and they are finished: they describe what builds up to
0.0.3 emitted and they are correct forever because that will never
change again. When the last of the fifty-five is gone, this module and
its command go with them.

The second rule is strict, and it is strict in the safe direction. Two
files in one real repository are the reason to say so plainly. ``docs/specs/index.md``
is stale output of an older build — it says *(no documents in this
section)* and then lists a document — so it is **not** byte-equal to
what those builds composed and comes back ``divergent``. ``docs/adr/
index.md`` was written by a different tool altogether, and it is
``divergent`` for exactly the same reason, from exactly the same rule.
Both are reported and left alone. Deciding from a file's shape or its
wording which of those two it is, is the prose route that got this wrong
once already; the report hands over the evidence with ``--diff`` and a
person decides.

Nothing here writes, moves or repairs anything. It reports, and the
cleanup — which is somebody else's commit, in somebody else's
repository — is driven from what it reports.
"""
from __future__ import annotations

import difflib
from dataclasses import dataclass
from pathlib import Path

from docstrap import sectionindex
from docstrap.projectscope import ProjectScope

#: The filename those builds wrote. A section page has no file of its own
#: any more, so this name lives here rather than in
#: :mod:`docstrap.sectionindex`, where it would read as something the
#: tool still produces.
LEGACY_INDEX_FILENAME = "index.md"

#: An earlier build wrote a page at this path and the file on disk is
#: byte-identical to it. docstrap wrote it; deleting it loses nothing,
#: because the page it stood for is composed inside the build now.
GENERATED = "generated"

#: An earlier build wrote a page at this path, and the file there is not
#: it. docstrap does not claim the file. Stale output of an older build,
#: another tool's page, and a page somebody hand-wrote are all here,
#: because from what docstrap knows they are the same case.
DIVERGENT = "divergent"

#: An earlier build wrote a page at this path and there is no file there.
#: The ordinary state once the writes stopped; reported only on request.
ABSENT = "absent"

#: The project's docs_root landing page, and not the placeholder an older
#: build left when it created that directory. The user's own file.
AUTHORED = "authored"


@dataclass(frozen=True)
class Finding:
    """One path a build writes to, and what is there now."""

    path: Path
    state: str
    display: str
    detail: str

    @property
    def is_docstrap(self) -> bool:
        """Whether docstrap claims authorship of the file on disk."""
        return self.state == GENERATED


# --- the frozen recogniser --------------------------------------------------
#
# What builds up to 0.0.3 put in a section's `index.md`, reproduced
# exactly. Do not refactor these two functions to share anything with the
# live composer, and do not "improve" what they emit: every change makes
# a committed file stop being recognisable as docstrap's, which turns a
# safe deletion into a file somebody has to read and judge.

#: The names those builds skipped when listing a directory, held here
#: rather than imported. `sectionindex` carries the same two names for
#: the live rule, and that rule has already changed meaning once — the
#: recogniser must not follow it.
_LEGACY_USER_INDEX_FILES = frozenset({"index.md", "index.rst"})


def legacy_children(
    dir_path: Path,
    exclude_dirs: set[str],
    exclude_suffixes: set[str],
) -> list[str]:
    """The toctree entries those builds listed for ``dir_path``.

    Subdirectories contributed ``<name>/index``; files contributed their
    stem; a user's own `index.md` was skipped because it *became* the
    section landing. Sorted by filename, so a directory and a document
    interleave.
    """
    entries: list[str] = []
    try:
        children = sorted(dir_path.iterdir())
    except OSError:
        return entries
    for child in children:
        if child.is_dir():
            if not sectionindex.is_section_dir(child.name, exclude_dirs):
                continue
            entries.append(f"{child.name}/index")
        elif child.is_file():
            if child.name.startswith((".", "_")):
                continue
            if child.name in _LEGACY_USER_INDEX_FILES:
                continue
            if child.suffix not in (".md", ".rst"):
                continue
            if any(child.name.endswith(s) for s in exclude_suffixes):
                continue
            entries.append(child.stem)
    return entries


def legacy_markdown(
    dir_path: Path,
    exclude_dirs: set[str],
    exclude_suffixes: set[str],
) -> str:
    """The bytes those builds wrote into ``dir_path/index.md``."""
    title = sectionindex.humanize(dir_path.name)
    entries = legacy_children(dir_path, exclude_dirs, exclude_suffixes)
    body = [f"# {title}", ""]
    if entries:
        body.append("```{toctree}")
        body.append(f":caption: {title}")
        body.append(":maxdepth: 2")
        body.append("")
        body.extend(entries)
        body.append("```")
        body.append("")
    else:
        body.append("*(no documents in this section)*")
        body.append("")
    return "\n".join(body)


def docs_dir_stub(title: str) -> str:
    """The placeholder an older build left when it created a docs_root.

    Gone from the layout in the same change that stopped the section
    writes, and kept here because copies of it are sitting in projects
    and the report has to recognise one exactly.
    """
    return (
        f"# {title}\n\n"
        "*Docs directory auto-created by docstrap. Add markdown files "
        "here and rebuild to publish.*\n"
    )


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def _classify(path: Path, composed: str, scope: ProjectScope) -> Finding:
    """One site's state, decided by bytes and by nothing else."""
    display = scope.display_path(path)
    if not path.is_file():
        return Finding(path, ABSENT, display, "a build wrote this page here")
    if _read(path) == composed:
        return Finding(
            path, GENERATED, display, "byte-identical to what a build wrote here"
        )
    return Finding(
        path,
        DIVERGENT,
        display,
        "a build wrote a different page here; docstrap does not claim this file",
    )


def scan(scope: ProjectScope) -> list[Finding]:
    """Every `index.md` an earlier build wrote into this project, and its state.

    The docs_root landing page comes first, because it is the one site
    with its own composed content — the placeholder stub, not a section
    page. The rest follow in path order.
    """
    docs_dir = scope.docs_dir
    if docs_dir is None or not docs_dir.is_dir():
        return []

    exclude_dirs = set(scope.project.exclude_dirs)
    exclude_suffixes = set(scope.project.exclude_file_suffixes)

    findings: list[Finding] = []

    landing = docs_dir / LEGACY_INDEX_FILENAME
    if landing.is_file():
        if _read(landing) == docs_dir_stub(scope.title):
            findings.append(
                Finding(
                    landing,
                    GENERATED,
                    scope.display_path(landing),
                    "byte-identical to the placeholder an older build left here",
                )
            )
        else:
            findings.append(
                Finding(
                    landing,
                    AUTHORED,
                    scope.display_path(landing),
                    "not the placeholder an older build left, so docstrap "
                    "does not claim it — and not published either: a docs "
                    "tree is not allowed an index file",
                )
            )

    for directory in sorted(
        sectionindex.sites(
            docs_dir, exclude_dirs, follow_symlinks=True, include_hidden=True
        )
    ):
        path = directory / LEGACY_INDEX_FILENAME
        composed = legacy_markdown(directory, exclude_dirs, exclude_suffixes)
        findings.append(_classify(path, composed, scope))

    return findings


def diff(finding: Finding, scope: ProjectScope) -> str:
    """A unified diff between the file and what an earlier build wrote there.

    Offered for a file docstrap does not claim, so a person can see at a
    glance whether they are looking at a stale page of docstrap's or at a
    document somebody wrote. The report will not draw that conclusion
    itself; this is how it hands the evidence over instead.
    """
    if finding.state not in (DIVERGENT, AUTHORED):
        return ""
    if finding.state == AUTHORED:
        composed = docs_dir_stub(scope.title)
    else:
        composed = legacy_markdown(
            finding.path.parent,
            set(scope.project.exclude_dirs),
            set(scope.project.exclude_file_suffixes),
        )
    actual = _read(finding.path) or ""
    return "".join(
        difflib.unified_diff(
            actual.splitlines(keepends=True),
            composed.splitlines(keepends=True),
            fromfile=f"{finding.display} (on disk)",
            tofile="what a build wrote there",
        )
    )
