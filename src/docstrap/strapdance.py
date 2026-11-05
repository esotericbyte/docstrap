"""The strapdance front-matter reader — one implementation, two runtimes.

Implements the strapdance front-matter standard: markdown documents stay
files, YAML front-matter carries context, and every field that is absent
resolves through a fallback chain instead of being a hole.

Three properties this module exists to guarantee:

1. **It reads only its own namespace.** Every top-level key other than
   ``strapdance`` is preserved byte-for-byte and ignored. An
   unrecognised namespace is never an error.
2. **It never writes.** Absence of front-matter is a valid state the chain
   handles; a malformed block is reported, not repaired.
3. **Every resolved value carries its provenance** — which step of the
   chain produced it. The classifier needs that to show a person what was
   inferred versus declared, and a suggestion must never become
   storage without confirmation.

The ``docstrap`` console script and its plugins use this module.
A second implementation of this standard would
reproduce the split-slug defect that silently orphaned submitted answers.

Public entry point::

    from docstrap.strapdance import read_context
    ctx = read_context(Path("docs/proposals/thing.md"))
    ctx.kind.value       # 'proposal'
    ctx.kind.step        # ChainStep.POSITION
    ctx.kind.detail      # "parent directory `proposals`"
"""
from __future__ import annotations

import re
import subprocess
import tomllib
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from docstrap import config as docstrap_config
from docstrap.frontmatter import FrontMatterBlock, read_front_matter, split_front_matter
from docstrap.sectionindex import humanize
from docstrap.scan import ScannedProject, scan
from docstrap.slugs import slugify

#: The one top-level key this standard owns.
NAMESPACE = "strapdance"

#: The standard's fields that may also appear as bare, un-namespaced keys.
#: Read-only compatibility — the reader never writes a bare key,
#: so it can never squat a name another tool may want. ``declined`` is
#: deliberately absent: it is state this tool records rather than a field
#: inherited from documents that already exist, and a bare ``declined``
#: almost certainly belongs to somebody else.
BARE_COMPAT_FIELDS: frozenset[str] = frozenset({
    "id", "title", "kind", "status", "project",
    "relates_to", "answers", "created", "updated",
})

#: Parent-directory name → ``kind``. Both the plural directory names
#: real repositories use and their singular forms are accepted.
KIND_BY_DIRECTORY: dict[str, str] = {
    "drafts": "draft", "draft": "draft",
    "proposals": "proposal", "proposal": "proposal",
    "plans": "plan", "plan": "plan",
    "notes": "note", "note": "note",
    "adr": "adr", "adrs": "adr",
    "research": "research",
    "spec": "spec", "specs": "spec",
    "templates": "template", "template": "template",
    "memories": "memory", "memory": "memory",
}

#: Parent-or-grandparent directory name → the ``status`` it already
#: implies.
#: ``hold`` is absent on purpose — see ``HOLD_DIRECTORY``.
STATUS_BY_DIRECTORY: dict[str, str] = {
    "done": "done",
    "templates": "reusable",
    "memories": "reference",
    "notes": "reference",
}

#: ``hold/`` implies active-with-work-paused rather than a distinct
#: value, so it resolves to ``active`` and says so in the provenance.
HOLD_DIRECTORY = "hold"

#: The step-4 value for ``status``. The standard's default is ``active``,
#: so status is the one field whose step 4 still yields a usable value. The
#: step is reported as UNKNOWN anyway, because a default is not a finding.
DEFAULT_STATUS = "active"

#: How far into the body a bare ``Status:`` line still counts as the
#: document declaring its own status. Deep in a body it is prose.
_STATUS_LINE_LOOKAHEAD = 10


class ChainStep(str, Enum):
    """Which step of the fallback chain produced a value.

    The four canonical steps are EXPLICIT, POSITION, CONTENT and UNKNOWN.
    HISTORY is the dates-only step (git history of the file; filesystem
    mtime only when the file is untracked), which is neither position nor content.
    """

    EXPLICIT = "explicit"
    POSITION = "position"
    CONTENT = "content"
    HISTORY = "history"
    UNKNOWN = "unknown"


class ExaminationState(str, Enum):
    """The three-way distinction between unexamined, declined and classified.

    Two of these look identical on disk and must not be treated alike:

    * ``NOT_EXAMINED`` — no ``strapdance`` namespace; nobody has looked.
      A document carrying only foreign namespaces or bare keys is still
      not-examined, because nobody has looked *with this tool*.
    * ``DECLINED`` — someone looked and recorded that this document has
      no meaningful context, or should not carry front-matter. A positive
      fact, not an absence. Without it a continual classifier re-offers
      the same document forever.
    * ``CLASSIFIED`` — the namespace is present and carries at least one
      field. An empty ``strapdance: {}``, or one holding nothing but
      ``declined: false``, stays NOT_EXAMINED: it records no decision.
    """

    NOT_EXAMINED = "not_examined"
    DECLINED = "declined"
    CLASSIFIED = "classified"


class ProjectSource(str, Enum):
    """Which of the ``project`` chain's four answers actually replied.

    ``project`` is the one field whose chain has three distinct
    position-step sources, and a caller cannot tell them apart from
    ``ChainStep.POSITION`` alone. The distinction is the whole point:
    a member directory naming its own project is a real answer, while the
    workspace root answering is the honest admission that position could
    not say. ``docstrap doctor`` reports on exactly that difference, and a
    classifier showing a person what was inferred needs the same split.
    """

    EXPLICIT = "explicit"
    DOCSTRAP_PROJECT = "docstrap_project"
    WORKSPACE_MEMBER = "workspace_member"
    WORKSPACE_ROOT = "workspace_root"
    NONE = "none"


@dataclass(frozen=True)
class ResolvedField:
    """One field's value together with the chain step that produced it."""

    value: Any
    step: ChainStep
    detail: str

    @property
    def is_explicit(self) -> bool:
        """True when a person wrote this value into the document."""
        return self.step is ChainStep.EXPLICIT

    @property
    def is_known(self) -> bool:
        """False when the chain ran out and reached step 4.

        ``status`` is the one field that still carries a value at step 4
        (the standard's ``active`` default), so read this as "somebody or
        something actually said so", not as "value is None".
        """
        return self.step is not ChainStep.UNKNOWN


@dataclass(frozen=True)
class DocumentContext:
    """A document's resolved strapdance context, field by field.

    Every field is a :class:`ResolvedField`, so a caller can always ask
    both "what is the value" and "where did it come from".
    """

    path: Path
    collection_root: Path
    state: ExaminationState

    id: ResolvedField
    title: ResolvedField
    kind: ResolvedField
    status: ResolvedField
    project: ResolvedField
    relates_to: ResolvedField
    answers: ResolvedField
    created: ResolvedField
    updated: ResolvedField

    front_matter: FrontMatterBlock
    #: Top-level keys, in document order, that this reader does not own.
    #: Preserved byte-for-byte in ``front_matter``; never interpreted.
    foreign_keys: tuple[str, ...] = ()
    #: Malformed-block reports. Non-empty does not stop resolution.
    errors: tuple[str, ...] = ()
    #: Which answer of the project chain replied. ``project.step``
    #: says how far the chain went; this says who was standing there.
    project_source: ProjectSource = ProjectSource.NONE

    @property
    def declined(self) -> bool:
        return self.state is ExaminationState.DECLINED

    @property
    def fields(self) -> dict[str, ResolvedField]:
        """The standard's fields by name, for callers that iterate."""
        return {
            "id": self.id, "title": self.title, "kind": self.kind,
            "status": self.status, "project": self.project,
            "relates_to": self.relates_to, "answers": self.answers,
            "created": self.created, "updated": self.updated,
        }


# --- the public entry points -----------------------------------------------


def read_title(path: Path, *, text: Optional[str] = None) -> str:
    """One document's title, and nothing else resolved.

    :func:`read_context` answers every field, and two of them —
    ``project`` and ``id`` — reload the enclosing ``.docstrap`` and glob
    the uv workspace to do it. That is right for a reader that wants the
    whole context and wrong for a caller that wants a caption: measured
    at 1.7 ms a document, against 1.6 µs to hash the same bytes, it made
    indexing a fifty-project workspace cost seconds of work to answer a
    question the title chain answers from the document alone.

    So this runs the title chain and stops. It is here, beside the chain,
    rather than in the caller, because the title chain has one owner and
    an inlined copy of "front-matter, else first heading, else the
    filename" is exactly the second implementation that must not exist.
    """
    block = split_front_matter(text) if text is not None else read_front_matter(path)
    namespace = block.data.get(NAMESPACE)
    if not isinstance(namespace, dict):
        namespace = {}
    return _resolve_title(Path(path), block, namespace).value


def read_context(
    path: Path,
    *,
    collection_root: Optional[Path] = None,
    text: Optional[str] = None,
) -> DocumentContext:
    """Resolve one document's strapdance context. Never writes anything.

    ``path`` is the document. ``collection_root`` overrides the directory
    ``id`` is made relative to; when omitted it is derived from the
    enclosing ``.docstrap`` project, then the uv workspace, then the
    document's own directory. ``text`` lets a caller supply already-read
    document text (the file is still used for its path and dates).

    A missing, malformed or foreign-namespaced front-matter block is
    never an error: the chain simply carries on from the next step, and
    anything that could not be parsed is reported in ``errors``.
    """
    path = Path(path)
    block = split_front_matter(text) if text is not None else read_front_matter(path)

    errors: list[str] = []
    if block.error:
        errors.append(f"{path}: {block.error}")

    ns = block.data.get(NAMESPACE)
    if ns is not None and not isinstance(ns, dict):
        errors.append(
            f"{path}: `{NAMESPACE}` must be a mapping, got {type(ns).__name__}; "
            "treating it as absent"
        )
        ns = None
    namespace: dict[str, Any] = ns or {}

    project_hint = _resolve_docstrap_project(path)
    workspace = _resolve_uv_workspace(path)
    root = collection_root or _collection_root(path, project_hint, workspace)
    project, project_source = _resolve_project(block, namespace, project_hint, workspace)

    return DocumentContext(
        path=path,
        collection_root=root,
        state=_examination_state(block, namespace),
        id=_resolve_id(path, root, block, namespace),
        title=_resolve_title(path, block, namespace),
        kind=_resolve_kind(path, block, namespace),
        status=_resolve_status(path, block, namespace),
        project=project,
        relates_to=_resolve_list(block, namespace, "relates_to"),
        answers=_resolve_list(block, namespace, "answers"),
        created=_resolve_date(path, block, namespace, "created"),
        updated=_resolve_date(path, block, namespace, "updated"),
        front_matter=block,
        foreign_keys=block.keys_other_than(NAMESPACE),
        errors=tuple(errors),
        project_source=project_source,
    )


# --- step 1: explicit ------------------------------------------------------


def _explicit(
    block: FrontMatterBlock, namespace: dict[str, Any], name: str
) -> Optional[ResolvedField]:
    """Step 1. Namespaced value first, then the bare compatibility key.

    A namespaced value always wins over a bare one, and a bare key
    is read only for the fields this standard already names.
    """
    if name in namespace and namespace[name] is not None:
        return ResolvedField(namespace[name], ChainStep.EXPLICIT, f"`{NAMESPACE}.{name}`")
    if name in BARE_COMPAT_FIELDS:
        bare = block.data.get(name)
        if bare is not None:
            return ResolvedField(
                bare, ChainStep.EXPLICIT, f"bare key `{name}` (compatibility)"
            )
    return None


# --- per-field resolution --------------------------------------------------


def _resolve_id(
    path: Path, root: Path, block: FrontMatterBlock, namespace: dict[str, Any]
) -> ResolvedField:
    explicit = _explicit(block, namespace, "id")
    if explicit is not None:
        return ResolvedField(str(explicit.value), explicit.step, explicit.detail)

    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError:
        relative = Path(path.name)
    stem = relative.with_suffix("")
    return ResolvedField(
        slugify(stem.as_posix()),
        ChainStep.POSITION,
        f"path `{stem.as_posix()}` relative to collection root `{root}`",
    )


def _resolve_title(
    path: Path, block: FrontMatterBlock, namespace: dict[str, Any]
) -> ResolvedField:
    """First level-1 heading, else the filename de-slugged.

    This is the one field that puts content ahead of position, for a
    reason — an authored heading beats a filename. Every other field keeps
    the chain's usual order.
    """
    explicit = _explicit(block, namespace, "title")
    if explicit is not None:
        return ResolvedField(str(explicit.value), explicit.step, explicit.detail)

    heading = _first_h1(block.body)
    if heading:
        return ResolvedField(heading, ChainStep.CONTENT, "first level-1 heading")

    return ResolvedField(
        humanize(path.stem), ChainStep.POSITION, f"filename `{path.name}` de-slugged"
    )


def _resolve_kind(
    path: Path, block: FrontMatterBlock, namespace: dict[str, Any]
) -> ResolvedField:
    explicit = _explicit(block, namespace, "kind")
    if explicit is not None:
        return ResolvedField(str(explicit.value), explicit.step, explicit.detail)

    parent = path.resolve().parent.name
    mapped = KIND_BY_DIRECTORY.get(parent.lower())
    if mapped:
        return ResolvedField(mapped, ChainStep.POSITION, f"parent directory `{parent}`")

    # Step 4. The parent directory is not one this standard maps and the
    # document body cannot say what sort of document it is without
    # guessing, so unknown is stated rather than invented.
    return ResolvedField(
        None,
        ChainStep.UNKNOWN,
        f"parent directory `{parent}` maps to no known kind; not guessed",
    )


def _resolve_status(
    path: Path, block: FrontMatterBlock, namespace: dict[str, Any]
) -> ResolvedField:
    """An OPEN vocabulary, never coerced.

    Whatever survives the chain is returned verbatim. No mapping, no
    normalisation, no enum, and an unrecognised value is not an error.
    """
    explicit = _explicit(block, namespace, "status")
    if explicit is not None:
        return ResolvedField(str(explicit.value), explicit.step, explicit.detail)

    resolved = path.resolve()
    for label, directory in (("parent", resolved.parent), ("grandparent", resolved.parent.parent)):
        name = directory.name.lower()
        if name in STATUS_BY_DIRECTORY:
            return ResolvedField(
                STATUS_BY_DIRECTORY[name],
                ChainStep.POSITION,
                f"{label} directory `{directory.name}`",
            )
        if name == HOLD_DIRECTORY:
            return ResolvedField(
                DEFAULT_STATUS,
                ChainStep.POSITION,
                f"{label} directory `{directory.name}` — work paused, "
                "hold is not a distinct status value",
            )

    declared = _status_line(block.body)
    if declared:
        return ResolvedField(declared, ChainStep.CONTENT, "`Status:` line in the document")

    # Step 4. The standard defaults to `active`, so status is the one
    # field that always has a value — but the step still says UNKNOWN,
    # because nothing declared or implied it and a classifier must be
    # able to tell a default from a finding.
    return ResolvedField(
        DEFAULT_STATUS,
        ChainStep.UNKNOWN,
        "nothing declares or implies a status; the standard's default is `active`",
    )


def _resolve_project(
    block: FrontMatterBlock,
    namespace: dict[str, Any],
    project_hint: Optional[ScannedProject],
    workspace: Optional[_Workspace],
) -> tuple[ResolvedField, ProjectSource]:
    """The one case where the directory genuinely cannot answer.

    A prompt or spec at the ROOT of a repo often belongs to one workspace
    member, and position cannot express that because the position IS the
    root. Explicit first; then nearest ``.docstrap`` entry, then the uv
    workspace member containing the document, then the workspace root —
    which for a root-level document is honest rather than wrong.

    Returns the field together with which of those four replied, because
    ``ChainStep.POSITION`` covers three of them and they do not mean the
    same thing to a caller (see :class:`ProjectSource`).
    """
    explicit = _explicit(block, namespace, "project")
    if explicit is not None:
        return (
            ResolvedField(str(explicit.value), explicit.step, explicit.detail),
            ProjectSource.EXPLICIT,
        )

    if project_hint is not None:
        return (
            ResolvedField(
                project_hint.slug,
                ChainStep.POSITION,
                f"nearest `.docstrap` project entry `{project_hint.slug}`",
            ),
            ProjectSource.DOCSTRAP_PROJECT,
        )

    if workspace is not None:
        if workspace.member_name:
            return (
                ResolvedField(
                    workspace.member_name,
                    ChainStep.POSITION,
                    f"uv workspace member `{workspace.member_path}`",
                ),
                ProjectSource.WORKSPACE_MEMBER,
            )
        return (
            ResolvedField(
                workspace.root_name,
                ChainStep.POSITION,
                f"uv workspace root `{workspace.root}` (document is not inside a member)",
            ),
            ProjectSource.WORKSPACE_ROOT,
        )

    return (
        ResolvedField(
            None,
            ChainStep.UNKNOWN,
            "no `.docstrap` entry and no uv workspace above this document",
        ),
        ProjectSource.NONE,
    )


def _resolve_list(
    block: FrontMatterBlock, namespace: dict[str, Any], name: str
) -> ResolvedField:
    """``relates_to`` and ``answers`` have no honest fallback.

    They are exactly the two things a directory could never express, which
    is why the standard earns its keep — and why inferring them would be a
    guess. Absent means empty, and the step says so.
    """
    explicit = _explicit(block, namespace, name)
    if explicit is not None:
        value = explicit.value
        items = tuple(value) if isinstance(value, (list, tuple)) else (value,)
        return ResolvedField(items, explicit.step, explicit.detail)
    return ResolvedField((), ChainStep.UNKNOWN, "no honest fallback; stays empty")


def _resolve_date(
    path: Path, block: FrontMatterBlock, namespace: dict[str, Any], name: str
) -> ResolvedField:
    explicit = _explicit(block, namespace, name)
    if explicit is not None:
        return explicit

    dates = _git_dates(path)
    if dates is not None:
        created, updated = dates
        return ResolvedField(
            created if name == "created" else updated,
            ChainStep.HISTORY,
            "git history of the file",
        )

    try:
        mtime = path.stat().st_mtime
    except OSError:
        return ResolvedField(None, ChainStep.UNKNOWN, "file has no history and no mtime")
    stamp = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
    return ResolvedField(stamp, ChainStep.HISTORY, "filesystem mtime (file is untracked)")


# --- the three-way state ---------------------------------------------------


def _examination_state(
    block: FrontMatterBlock, namespace: dict[str, Any]
) -> ExaminationState:
    if namespace.get("declined"):
        return ExaminationState.DECLINED
    meaningful = [k for k in namespace if k != "declined"]
    if meaningful:
        return ExaminationState.CLASSIFIED
    return ExaminationState.NOT_EXAMINED


# --- step 3: the document's own content ------------------------------------

_H1_RE = re.compile(r"^#[ \t]+(.+?)[ \t]*#*[ \t]*$")
_STATUS_RE = re.compile(r"^[ \t]*status[ \t]*:[ \t]*(\S+)", re.IGNORECASE)
_FENCE_RE = re.compile(r"^[ \t]*(?:```|~~~)")


def _uncoded_lines(body: str):
    """Yield the body's lines with fenced code blocks skipped."""
    in_fence = False
    for line in body.splitlines():
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            yield line


def _first_h1(body: str) -> Optional[str]:
    """The first ATX level-1 heading, or None."""
    for line in _uncoded_lines(body):
        match = _H1_RE.match(line)
        if match:
            return match.group(1).strip()
    return None


def _status_line(body: str) -> Optional[str]:
    """A ``Status:`` line the author wrote near the top of the document.

    Deliberately narrow. It fires only in the document's opening lines and
    takes a single token, because documents open with lines like
    ``Status: DRAFT for review, 2026-08-25.`` — the declaration
    is the first word and the rest is prose. The token is returned
    verbatim: status is an open vocabulary and nothing is normalised.
    Provenance marks it CONTENT so a classifier can show it was inferred.
    """
    seen = 0
    for line in _uncoded_lines(body):
        if not line.strip():
            continue
        seen += 1
        if seen > _STATUS_LINE_LOOKAHEAD:
            return None
        match = _STATUS_RE.match(line)
        if match:
            token = match.group(1).strip(".,;:")
            return token or None
    return None


# --- position: .docstrap, uv workspace, collection root --------------------


@dataclass(frozen=True)
class _Workspace:
    """The uv workspace above a document, and the member containing it."""

    root: Path
    root_name: str
    member_path: Optional[str] = None
    member_dir: Optional[Path] = None
    member_name: Optional[str] = None


def _resolve_docstrap_project(path: Path) -> Optional[ScannedProject]:
    """The deepest ``.docstrap`` project entry whose root contains ``path``.

    Reuses ``config`` and ``scan`` rather than walking the tree again —
    docstrap already owns project discovery and there must not be a second
    scanner.
    """
    config_path = docstrap_config.find_config(path.parent)
    if config_path is None:
        return None
    try:
        cfg = docstrap_config.load(config_path)
        projects = list(scan(cfg))
    except docstrap_config.DocstrapConfigError:
        return None

    resolved = path.resolve()
    best: Optional[ScannedProject] = None
    for project in projects:
        if _contains(project.root_dir, resolved):
            if best is None or len(project.root_dir.parts) > len(best.root_dir.parts):
                best = project
    return best


def workspace_root(path: Path) -> Optional[Path]:
    """The uv workspace root at or above ``path``, or None.

    The reader already walks up for this to answer ``project``; exposing
    it keeps a second caller — ``docstrap doctor``, which has to know
    where "the workspace root" is before it can walk its ``docs/`` — from
    growing a second upward walk that could disagree with this one.
    """
    found = _find_workspace_root(path)
    return found[0] if found is not None else None


def _resolve_uv_workspace(path: Path) -> Optional[_Workspace]:
    found = _find_workspace_root(path)
    if found is None:
        return None
    root, data = found
    root_name = _project_name(data) or root.name

    resolved = path.resolve()
    best_dir: Optional[Path] = None
    best_pattern: Optional[str] = None
    members = data.get("tool", {}).get("uv", {}).get("workspace", {}).get("members", [])
    excludes = data.get("tool", {}).get("uv", {}).get("workspace", {}).get("exclude", [])
    excluded = {p.resolve() for pattern in excludes for p in root.glob(str(pattern))}

    for pattern in members:
        for candidate in root.glob(str(pattern)):
            if not candidate.is_dir() or candidate.resolve() in excluded:
                continue
            if not (candidate / "pyproject.toml").is_file():
                continue
            if not _contains(candidate, resolved):
                continue
            if best_dir is None or len(candidate.resolve().parts) > len(best_dir.parts):
                best_dir, best_pattern = candidate.resolve(), str(pattern)

    if best_dir is None:
        return _Workspace(root=root, root_name=root_name)

    member_data = _read_toml(best_dir / "pyproject.toml") or {}
    return _Workspace(
        root=root,
        root_name=root_name,
        member_path=(
            best_dir.relative_to(root.resolve()).as_posix()
            if _contains(root, best_dir) else best_pattern
        ),
        member_dir=best_dir,
        member_name=_project_name(member_data) or best_dir.name,
    )


def _find_workspace_root(path: Path) -> Optional[tuple[Path, dict]]:
    """Walk up for the nearest pyproject.toml declaring a uv workspace."""
    current = path.resolve()
    if current.is_file():
        current = current.parent
    while True:
        candidate = current / "pyproject.toml"
        if candidate.is_file():
            data = _read_toml(candidate)
            if data and "workspace" in data.get("tool", {}).get("uv", {}):
                return current, data
        if current.parent == current:
            return None
        current = current.parent


def _read_toml(path: Path) -> Optional[dict]:
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return None


def _project_name(data: dict) -> Optional[str]:
    name = data.get("project", {}).get("name")
    return str(name) if name else None


def _collection_root(
    path: Path, project: Optional[ScannedProject], workspace: Optional[_Workspace]
) -> Path:
    """The directory ``id`` is made relative to.

    The innermost source folder of the enclosing ``.docstrap`` project
    when the document is inside one, then that project's root, then the uv workspace
    member or root, and finally the document's own directory.
    """
    resolved = path.resolve()
    if project is not None:
        holding = [s.path for s in project.sources if _contains(s.path, resolved)]
        if holding:
            return max(holding, key=lambda d: len(d.parts))
        return project.root_dir
    if workspace is not None:
        if workspace.member_dir is not None:
            return workspace.member_dir
        return workspace.root
    return resolved.parent


def _contains(directory: Path, target: Path) -> bool:
    """True when ``target`` is at or below ``directory``."""
    try:
        target.resolve().relative_to(directory.resolve())
    except (ValueError, OSError):
        return False
    return True


# --- the history step ------------------------------------------------------


def _git_dates(path: Path) -> Optional[tuple[str, str]]:
    """(created, updated) from git, or None when the file is not tracked.

    Git history of the file; filesystem mtime only when the file is
    untracked.
    """
    directory = path.resolve().parent
    if not directory.is_dir():
        return None
    if _git(directory, "rev-parse", "--show-toplevel") is None:
        return None
    target = str(path.resolve())
    if _git(directory, "ls-files", "--error-unmatch", "--", target) is None:
        return None

    updated = _git(directory, "log", "-1", "--format=%aI", "--", target)
    if not updated:
        return None
    history = _git(directory, "log", "--follow", "--diff-filter=A", "--format=%aI", "--", target)
    created = history.splitlines()[-1] if history else updated
    return created, updated


def _git(directory: Path, *args: str) -> Optional[str]:
    """Run git in ``directory``; None on any failure. Read-only commands."""
    try:
        result = subprocess.run(
            ["git", "-C", str(directory), *args],
            capture_output=True, text=True, timeout=15, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()
