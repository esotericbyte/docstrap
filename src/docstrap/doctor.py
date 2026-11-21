"""`docstrap doctor` — find ambiguously-scoped documents, and say so.

The job: walk the workspace looking for
top-level documents that do not clearly belong to any project — docs
under a workspace-root ``docs/`` that no project's ``.docstrap`` claims.

Two properties this module exists to guarantee.

1. **It reports and proposes. It never acts.** Nothing is altered in
   place. Doctor moves no file, edits no document, and writes
   no ``.docstrap``. ``--fix-plan`` writes ONE new file — a shell script
   nobody has run — and refuses to overwrite anything. Every other output
   goes to the terminal. That is what makes doctor safe to point at a
   clone, a read-only checkout, or somebody else's repo.
2. **The verdict comes from the document's position, and shows its work.**
   Which project owns a document is read off where it sits — the nearest
   ``.docstrap`` project entry, then the uv workspace member containing
   it, then the workspace root — and every finding carries the step and
   the provenance detail that produced it.

The detection rule is one line: a document is ambiguously scoped when the
answer to "which project owns this?" came from the workspace ROOT — or
from nothing at all. A member directory or a ``.docstrap`` project entry
are both real answers. The workspace root is position being honest that
it could not say, and that is exactly the case doctor looks for.
"""
from __future__ import annotations

import shlex
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

from docstrap import config as docstrap_config
from docstrap import plugins
from docstrap.firstmate import FirstmateHome, detect_firstmate_homes
from docstrap.scan import ScannedProject, scan

#: Document extensions doctor examines: the set the docs tree is actually
#: authored in.
DOCUMENT_SUFFIXES: tuple[str, ...] = (".md", ".markdown")


class ProjectSource(str, Enum):
    """Which of the position answers to "which project owns this?" replied.

    A member directory naming its own project is a real answer, while the
    workspace root answering is the honest admission that position could
    not say. Doctor reports on exactly that difference.
    """

    DOCSTRAP_PROJECT = "docstrap_project"
    WORKSPACE_MEMBER = "workspace_member"
    WORKSPACE_ROOT = "workspace_root"
    NONE = "none"


#: The two project answers that mean "no project owns this document".
AMBIGUOUS_SOURCES: frozenset[ProjectSource] = frozenset(
    {ProjectSource.WORKSPACE_ROOT, ProjectSource.NONE}
)

#: Why each ambiguous source is a finding, in words for the report.
_REASONS: dict[ProjectSource, str] = {
    ProjectSource.WORKSPACE_ROOT: (
        "the workspace root answered because no project could; nothing here "
        "declares which project this document belongs to"
    ),
    ProjectSource.NONE: (
        "nothing answered at all: no `.docstrap` project entry and no uv "
        "workspace above this document"
    ),
}


@dataclass(frozen=True)
class Ambiguity:
    """One document whose owning project nothing actually declares."""

    path: Path
    relative_path: str
    project: Optional[str]
    detail: str
    source: ProjectSource

    @property
    def reason(self) -> str:
        return _REASONS[self.source]

    @property
    def chain(self) -> str:
        """The step that answered and its provenance, as one reportable line."""
        step = "unknown" if self.source is ProjectSource.NONE else "position"
        return f"{step} — {self.detail}"


@dataclass(frozen=True)
class FirstmateFinding:
    """A firstmate operational home found below the examined root.

    Folded in rather than reimplemented: the detection is
    :func:`docstrap.firstmate.detect_firstmate_homes`, the same one
    ``docstrap firstmate-ignore-check`` uses. Doctor only reports it —
    the ignore declaration is written by that command, never by this one.
    """

    home: FirstmateHome
    already_ignored: bool

    @property
    def path(self) -> Path:
        return self.home.path


@dataclass(frozen=True)
class DoctorReport:
    """Everything doctor found, and where it looked."""

    root: Path
    workspace_root: Path
    workspace_detail: str
    docs_dir: Optional[Path]
    examined: tuple[Path, ...]
    ambiguities: tuple[Ambiguity, ...]
    firstmate: tuple[FirstmateFinding, ...]
    #: What the enabled plugins found, each a check
    #: and its verdict.
    plugin_findings: tuple[plugins.Finding, ...] = ()

    @property
    def docs_dir_exists(self) -> bool:
        return self.docs_dir is not None and self.docs_dir.is_dir()

    @property
    def unignored_firstmate(self) -> tuple[FirstmateFinding, ...]:
        return tuple(f for f in self.firstmate if not f.already_ignored)

    @property
    def ok(self) -> bool:
        """True when doctor found nothing to report."""
        return (
            not self.ambiguities
            and not self.unignored_firstmate
            and all(finding.ok for finding in self.plugin_findings)
        )


# --- examination -----------------------------------------------------------


def examine(
    root: Path,
    *,
    docs_directory: Optional[str] = None,
    firstmate_root: Optional[Path] = None,
) -> DoctorReport:
    """Walk the workspace and report. Reads only; writes nothing.

    ``root`` is where to start. The workspace root is resolved from it
    (see :func:`locate_workspace`), and the documents examined are those
    under that root's docs directory — the first source the workspace's
    ``.docstrap`` states, else the first the user config states, unless
    ``docs_directory`` overrides both.

    Each enabled plugin adds its own findings, given ``root``; what a
    plugin examines is its own to decide.
    """
    root = Path(root).expanduser().resolve()
    workspace, workspace_detail = locate_workspace(root)
    cfg = _load_config(workspace)

    docs_name = docs_directory or _docs_name(cfg)
    docs_dir = (workspace / docs_name).resolve() if docs_name else None

    exclude_dirs = (
        cfg.exclude_dirs if cfg is not None else docstrap_config.DEFAULT_EXCLUDE_DIRS
    )
    documents = tuple(_documents(docs_dir, exclude_dirs))

    ambiguities = []
    for document in documents:
        project, detail, source = _owning_project(document)
        if source not in AMBIGUOUS_SOURCES:
            continue
        ambiguities.append(
            Ambiguity(
                path=document,
                relative_path=_relative(document, workspace),
                project=project,
                detail=detail,
                source=source,
            )
        )

    firstmate = tuple(
        FirstmateFinding(home=home, already_ignored=docstrap_config.ignores_tree(home.path))
        for home in detect_firstmate_homes(firstmate_root or root)
    )

    return DoctorReport(
        root=root,
        workspace_root=workspace,
        workspace_detail=workspace_detail,
        docs_dir=docs_dir,
        examined=documents,
        ambiguities=tuple(ambiguities),
        firstmate=firstmate,
        plugin_findings=tuple(plugins.doctor_report(root)),
    )


def locate_workspace(root: Path) -> tuple[Path, str]:
    """The workspace root above ``root``, and how it was decided.

    A ``.docstrap`` wins, because a person put it there deliberately;
    then the uv workspace root; then
    ``root`` itself, which is stated rather than implied.
    """
    root = Path(root).expanduser().resolve()

    config_path = docstrap_config.find_config(root)
    if config_path is not None:
        return config_path.parent, f"`{docstrap_config.DOCSTRAP_FILENAME}` at {config_path.parent}"

    found = _find_workspace_root(root)
    if found is not None:
        return found[0], f"uv workspace root {found[0]}"

    return root, "no `.docstrap` and no uv workspace above it; using --root itself"


def _docs_name(cfg: Optional[docstrap_config.DocstrapConfig]) -> Optional[str]:
    """The workspace's documentation folder, as the settings surface says.

    The first source the `.docstrap` states at its top level, else the
    first the user config states. Docstrap has no built-in folder name,
    so where neither states one there is nothing to examine.
    """
    from docstrap import settings

    stated = cfg.sources if cfg is not None else None
    if stated is None:
        stated = settings.installation().sources
    return stated[0].path if stated else None


def _load_config(workspace: Path) -> Optional[docstrap_config.DocstrapConfig]:
    config_path = workspace / docstrap_config.DOCSTRAP_FILENAME
    if not config_path.exists():
        return None
    try:
        return docstrap_config.load(config_path)
    except docstrap_config.DocstrapConfigError:
        return None


def _documents(docs_dir: Path, exclude_dirs: Sequence[str]):
    """Every document under ``docs_dir``, minus the excluded directories."""
    if docs_dir is None or not docs_dir.is_dir():
        return
    excluded = {name.lower() for name in exclude_dirs}
    for path in sorted(docs_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in DOCUMENT_SUFFIXES:
            continue
        parts = path.relative_to(docs_dir).parts[:-1]
        if any(part.startswith(".") or part.lower() in excluded for part in parts):
            continue
        yield path


def _relative(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return str(path)


# --- which project owns a document -----------------------------------------


def _owning_project(path: Path) -> tuple[Optional[str], str, ProjectSource]:
    """The project a document's position puts it in, how, and who said so.

    Nearest ``.docstrap`` project entry, then the uv workspace member
    containing the document, then the workspace root — which for a
    root-level document is honest rather than wrong.
    """
    project = _docstrap_project(path)
    if project is not None:
        return (
            project.slug,
            f"nearest `.docstrap` project entry `{project.slug}`",
            ProjectSource.DOCSTRAP_PROJECT,
        )

    found = _find_workspace_root(path)
    if found is None:
        return (
            None,
            "no `.docstrap` entry and no uv workspace above this document",
            ProjectSource.NONE,
        )

    root, data = found
    member = _workspace_member(root, data, path)
    if member is not None:
        member_data = _read_toml(member / "pyproject.toml") or {}
        return (
            _project_name(member_data) or member.name,
            f"uv workspace member `{_relative(member, root)}`",
            ProjectSource.WORKSPACE_MEMBER,
        )
    return (
        _project_name(data) or root.name,
        f"uv workspace root `{root}` (document is not inside a member)",
        ProjectSource.WORKSPACE_ROOT,
    )


def _docstrap_project(path: Path) -> Optional[ScannedProject]:
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

    best: Optional[ScannedProject] = None
    for project in projects:
        if _contains(project.root_dir, path):
            if best is None or len(project.root_dir.parts) > len(best.root_dir.parts):
                best = project
    return best


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


def _workspace_member(root: Path, data: dict, path: Path) -> Optional[Path]:
    """The deepest uv workspace member directory containing ``path``."""
    settings = data.get("tool", {}).get("uv", {}).get("workspace", {})
    excluded = {
        p.resolve() for pattern in settings.get("exclude", []) for p in root.glob(str(pattern))
    }
    best: Optional[Path] = None
    for pattern in settings.get("members", []):
        for candidate in root.glob(str(pattern)):
            if not candidate.is_dir() or candidate.resolve() in excluded:
                continue
            if not (candidate / "pyproject.toml").is_file():
                continue
            if not _contains(candidate, path):
                continue
            if best is None or len(candidate.resolve().parts) > len(best.parts):
                best = candidate.resolve()
    return best


def _read_toml(path: Path) -> Optional[dict]:
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return None


def _project_name(data: dict) -> Optional[str]:
    name = data.get("project", {}).get("name")
    return str(name) if name else None


def _contains(directory: Path, target: Path) -> bool:
    """True when ``target`` is at or below ``directory``."""
    try:
        target.resolve().relative_to(directory.resolve())
    except (ValueError, OSError):
        return False
    return True


# --- the proposal ----------------------------------------------------------


class FixPlanExists(Exception):
    """Raised rather than overwrite a file that is already there."""


def write_fix_plan(
    report: DoctorReport,
    path: Path,
    destinations: Optional[Mapping[str, str]] = None,
) -> Path:
    """Write the proposal script to ``path``. Refuses to overwrite.

    This is the one file doctor creates, and it creates nothing else. The
    script it writes has not been run — that is a separate, deliberate act
    by a person.
    """
    path = Path(path).expanduser()
    if path.exists():
        raise FixPlanExists(f"{path} already exists; doctor will not overwrite it")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(fix_plan(report, destinations), encoding="utf-8")
    path.chmod(0o755)
    return path


def fix_plan(
    report: DoctorReport, destinations: Optional[Mapping[str, str]] = None
) -> str:
    """Render the proposal script for ``report`` as text.

    Every move whose destination nobody chose stays commented out, so a
    plan run without further thought does nothing at all. A destination
    supplied by ``--interactive`` — keyed by the finding's workspace-
    relative path — becomes a live ``git mv``, because a person named it.
    """
    chosen = dict(destinations or {})
    lines = [
        "#!/usr/bin/env bash",
        "#",
        "# docstrap doctor — proposed fixes for ambiguously-scoped documents.",
        "#",
        "# docstrap WROTE this file and RAN NONE OF IT. Nothing has been moved,",
        "# edited, or deleted. Read it, decide, then run it deliberately.",
        "#",
        f"# workspace root: {report.workspace_root}",
        f"# docs directory: {report.docs_dir}",
        f"# examined:       {len(report.examined)} document(s)",
        f"# proposed:       {len(report.ambiguities)} document(s)",
        "",
        "set -euo pipefail",
        "",
        f"cd {shlex.quote(str(report.workspace_root))}",
        "",
    ]

    if not report.ambiguities:
        lines += ["# Nothing ambiguous was found. There is nothing to propose.", ""]
        return "\n".join(lines)

    for finding in report.ambiguities:
        lines += _plan_entry(finding, chosen.get(finding.relative_path))

    lines += _plan_footer(report)
    return "\n".join(lines)


def _plan_entry(finding: Ambiguity, destination: Optional[str]) -> list[str]:
    source = shlex.quote(finding.relative_path)
    lines = [
        f"# --- {finding.relative_path}",
        f"#     project: {finding.project or '(none)'}",
        f"#     chain:   {finding.chain}",
        f"#     reason:  {finding.reason}",
        "#",
        "#     Move it into the docs tree of the project that owns it.",
    ]

    if destination:
        target = f"{destination.rstrip('/')}/{Path(finding.relative_path).name}"
        lines += [
            f"mkdir -p {shlex.quote(str(Path(target).parent))}",
            f"git mv {source} {shlex.quote(target)}",
        ]
    else:
        placeholder = f"<project>/docs/{Path(finding.relative_path).name}"
        lines += [
            "#     No destination was chosen, so this stays commented out.",
            f"# git mv {source} {shlex.quote(placeholder)}",
        ]

    lines.append("")
    return lines


def _plan_footer(report: DoctorReport) -> list[str]:
    lines = [
        "# --- environment",
        "#",
    ]
    unignored = report.unignored_firstmate
    if unignored:
        lines.append(
            "#     firstmate operational home(s) below the examined root are not"
        )
        lines.append("#     declared `ignore: true`. `docstrap firstmate-ignore-check`")
        lines.append("#     writes that declaration; doctor does not:")
        for finding in unignored:
            lines.append(f"# docstrap firstmate-ignore-check --root {shlex.quote(str(finding.path.parent))}")
    else:
        lines.append("#     No firstmate operational homes need an ignore declaration.")
    lines.append("")
    return lines
