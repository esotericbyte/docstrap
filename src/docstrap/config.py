"""Parser for .docstrap YAML config files.

Two modes: workspace-mode (top-level `projects:` array, for uv workspaces
and multi-project repos) and standalone-mode (fields at top level, for
single-project repos).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from docstrap import legacy_settings

DOCSTRAP_FILENAME = ".docstrap"
IGNORE_FIELD = "ignore"
# The old shape of one plugin's switch, before it moved into the
# `plugins` block, spelled by docstrap.legacy_settings.
# Still parsed, tri-state as it always was, so an installation that has
# not run `docstrap config migrate` keeps reading it;
# :mod:`docstrap.settings` decides whether it may be read at all.
LEGACY_ENABLED_FIELD = legacy_settings.ENABLED_FIELD
# The one settings surface: source folders with roles,
# and a block of settings per plugin. Parsed here; resolved across the
# three levels, and written, only by :mod:`docstrap.settings`.
SOURCES_FIELD = "sources"
PLUGINS_FIELD = "plugins"
DOCS_ROOT_FIELD = "docs_root"
#: The role `docs_root: X` is shorthand for.
DOCUMENTATION_ROLE = "documentation"
#: The one role docstrap gives special behaviour: published under its own
#: group, never walked as a document, and the fallback draft root.
DRAFT_ROLE = "draft"

VALID_LAYOUTS = frozenset({"sphinx", "mkdocs", "markdown", "quarto"})

# Directory names skipped everywhere in a project's docs tree unless
# the .docstrap file overrides. Applied recursively at any depth.
DEFAULT_EXCLUDE_DIRS: tuple[str, ...] = ("archive", "deprecated")


class DocstrapConfigError(Exception):
    """Raised when a .docstrap file is invalid or missing required fields."""


@dataclass(frozen=True)
class Source:
    """One folder a project publishes, as a level states it.

    ``path`` is relative to the project root. ``role`` is a word from an
    open vocabulary — docstrap is told a folder's role, never guesses it
    from the name. ``mount`` is where the folder appears in the site and
    in document identity; None means the default, which only the whole
    effective list can decide.
    """

    path: str
    role: str
    mount: str | None = None


@dataclass
class ProjectEntry:
    """One project inside a workspace-mode .docstrap file."""

    path: str
    title: str
    layout: str
    # As written, or None when the entry does not say. Shorthand for a
    # one-entry `sources` list; `sources` below already carries it.
    docs_root: str | None = None
    short: str | None = None
    icon: str | None = None
    priority: int | None = None
    # The project-level switch in its old shape (LEGACY_ENABLED_FIELD).
    # None means the entry says nothing.
    legacy_enabled: bool | None = None
    # What this entry states for the one settings surface. None means it
    # states nothing and a wider level decides.
    sources: tuple[Source, ...] | None = None
    plugins: dict[str, dict] | None = None


@dataclass
class RelatedDirectory:
    """A non-code directory to include in the aggregate."""

    path: str
    title: str
    layout: str = "markdown"
    docs_root: str | None = None
    sources: tuple[Source, ...] | None = None
    plugins: dict[str, dict] | None = None


@dataclass
class DocstrapConfig:
    """A parsed .docstrap file."""

    version: int
    title: str
    # If true, this .docstrap declares that its directory and subtree
    # should be skipped by docstrap discovery-style scans.
    ignore: bool = False
    # The repository-level switch in its old shape (LEGACY_ENABLED_FIELD).
    # None means this file says nothing.
    legacy_enabled: bool | None = None
    # Repository-level `sources` and `plugins`; None means unstated.
    sources: tuple[Source, ...] | None = None
    plugins: dict[str, dict] | None = None
    short: str | None = None
    icon: str | None = None
    priority: int | None = None
    # Standalone-mode fields:
    layout: str | None = None
    docs_root: str | None = None
    # Workspace-mode field:
    projects: list[ProjectEntry] = field(default_factory=list)
    # Optional, both modes:
    related_directories: list[RelatedDirectory] = field(default_factory=list)
    # Directory names skipped anywhere in the docs tree. Defaults to
    # DEFAULT_EXCLUDE_DIRS when the YAML omits the field.
    exclude_dirs: tuple[str, ...] = DEFAULT_EXCLUDE_DIRS
    # File extensions skipped everywhere (code files never indexed or
    # displayed). Empty means "publish everything Sphinx recognises."
    exclude_file_suffixes: tuple[str, ...] = (
        ".py", ".pyc", ".pyi", ".js", ".ts", ".tsx", ".jsx", ".mjs", ".cjs",
        ".sh", ".bash", ".zsh", ".fish", ".ps1", ".bat",
        ".go", ".rs", ".rb", ".php", ".java", ".kt", ".swift", ".c", ".cpp",
        ".h", ".hpp", ".cs", ".m", ".mm", ".sql", ".lua", ".pl", ".r",
    )
    # Where the file was loaded from (for path resolution).
    source_path: Path | None = None

    @property
    def is_workspace_mode(self) -> bool:
        """True if this config lists projects (workspace-mode)."""
        return bool(self.projects)

    @property
    def root_dir(self) -> Path:
        """Directory containing the .docstrap file. Base for relative paths."""
        if self.source_path is None:
            raise DocstrapConfigError("Config has no source_path; cannot resolve paths.")
        return self.source_path.parent


def load(path: Path) -> DocstrapConfig:
    """Load and parse a .docstrap file from a given path."""
    if not path.exists():
        raise DocstrapConfigError(f"No .docstrap file at {path}")
    with path.open("r", encoding="utf-8") as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise DocstrapConfigError(f"Invalid YAML in {path}: {e}") from e
    if not isinstance(data, dict):
        raise DocstrapConfigError(f"{path} must contain a YAML mapping at top level.")
    return _from_dict(data, source_path=path)


def ignores_tree(path: Path) -> bool:
    """True when a .docstrap file declares its directory should be skipped."""
    config_path = path if path.name == DOCSTRAP_FILENAME else path / DOCSTRAP_FILENAME
    if not config_path.exists():
        return False
    with config_path.open("r", encoding="utf-8") as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError:
            return False
    return isinstance(data, dict) and data.get(IGNORE_FIELD) is True


def in_ignored_tree(path: Path, root: Path) -> bool:
    """True if path is root or below a directory with `ignore: true`."""
    root = root.resolve()
    path = path.resolve()
    try:
        relative = path.relative_to(root)
    except ValueError:
        return False

    current = root
    if ignores_tree(current):
        return True
    for part in relative.parts:
        current = current / part
        if ignores_tree(current):
            return True
    return False


def find_config(start: Path) -> Path | None:
    """Walk up from start looking for a .docstrap file. Return path or None."""
    current = start.resolve()
    while True:
        candidate = current / DOCSTRAP_FILENAME
        if candidate.exists():
            return candidate
        if current.parent == current:
            return None
        current = current.parent


def _from_dict(data: dict, source_path: Path | None = None) -> DocstrapConfig:
    """Build a DocstrapConfig from a parsed dict. Applies defaults freely."""
    if "version" not in data:
        raise DocstrapConfigError("Missing required field: version")

    version = data["version"]
    if not isinstance(version, int):
        raise DocstrapConfigError(f"version must be an integer, got {type(version).__name__}")
    if version != 1:
        raise DocstrapConfigError(f"Unsupported .docstrap schema version: {version} (this docstrap supports version 1)")

    ignore = data.get(IGNORE_FIELD, False)
    if not isinstance(ignore, bool):
        raise DocstrapConfigError(f"`{IGNORE_FIELD}` must be a boolean when provided")

    where = str(source_path or "<config>")
    legacy_enabled = _parse_legacy_enabled(data, where=where)
    plugins = parse_plugins(data, where=where)
    _refuse_both_shapes(legacy_enabled, plugins, where=where)

    projects_raw = data.get("projects", [])
    if not isinstance(projects_raw, list):
        raise DocstrapConfigError("`projects` must be a list")
    projects = [_parse_project(p, where) for p in projects_raw]

    related_raw = data.get("related_directories", [])
    if not isinstance(related_raw, list):
        raise DocstrapConfigError("`related_directories` must be a list")
    related = [_parse_related(r, where) for r in related_raw]

    # Standalone-mode fields — defaults apply when omitted so a minimal
    # `.docstrap` is: `version: 1`. Title defaults to the parent dir name.
    # There is no default folder: where the documents are comes from
    # `sources` or `docs_root` at whichever level states one, resolved by
    # docstrap.settings. Docstrap has no built-in folder name.
    is_standalone = not projects
    layout = data.get("layout")
    docs_root = data.get(DOCS_ROOT_FIELD)
    sources = parse_sources(data, where=where)

    if is_standalone:
        if layout is None:
            layout = "markdown"
        if layout not in VALID_LAYOUTS:
            raise DocstrapConfigError(
                f"Invalid layout `{layout}`; must be one of {sorted(VALID_LAYOUTS)}"
            )

    title = data.get("title")
    if title is None:
        if source_path is not None:
            title = source_path.parent.name
        else:
            raise DocstrapConfigError("Missing required field: title (and no source_path to derive from)")

    # Optional overrides — YAML lists become tuples; empty list means
    # "no exclusions". Absence means "use defaults."
    excl_raw = data.get("exclude_dirs")
    exclude_dirs: tuple[str, ...] = (
        DEFAULT_EXCLUDE_DIRS if excl_raw is None else tuple(str(x) for x in excl_raw)
    )
    file_excl_raw = data.get("exclude_file_suffixes")
    # Preserve the dataclass default (long list of code suffixes) when
    # the YAML omits the field. If provided, must be a list of strings
    # (each dot-prefixed).
    default_exclude_suffixes = DocstrapConfig.__dataclass_fields__[
        "exclude_file_suffixes"
    ].default
    exclude_file_suffixes: tuple[str, ...] = (
        default_exclude_suffixes if file_excl_raw is None
        else tuple(
            s if s.startswith(".") else "." + s
            for s in (str(x) for x in file_excl_raw)
        )
    )

    return DocstrapConfig(
        version=version,
        title=title,
        ignore=ignore,
        legacy_enabled=legacy_enabled,
        sources=sources,
        plugins=plugins,
        short=data.get("short"),
        icon=data.get("icon"),
        priority=data.get("priority"),
        layout=layout,
        docs_root=docs_root,
        projects=projects,
        related_directories=related,
        exclude_dirs=exclude_dirs,
        exclude_file_suffixes=exclude_file_suffixes,
        source_path=source_path,
    )


def _parse_legacy_enabled(raw: dict, where: str) -> bool | None:
    """Read the tri-state old-shape switch. Absent stays absent.

    The distinction matters: the old switch was opt-out, so `False` from
    one level has to be distinguishable from that level saying nothing at
    all. Collapsing absence to a default here is what would let an
    installation-level `false` be silently out-voted by every repository
    that never mentions it.
    """
    if LEGACY_ENABLED_FIELD not in raw:
        return None
    value = raw[LEGACY_ENABLED_FIELD]
    if value is None:
        return None
    if not isinstance(value, bool):
        raise DocstrapConfigError(
            f"`{LEGACY_ENABLED_FIELD}` must be true or false when provided (in {where})"
        )
    return value


def parse_sources(raw: dict, where: str) -> tuple[Source, ...] | None:
    """The `sources` one level states, with `docs_root` read as its shorthand.

    None means the level states neither, which is not the same as an
    empty list: an empty list says "no sources" and wins over a wider
    level, while None lets the wider level decide. A level that states
    both is refused rather than merged — two spellings of one fact at one
    level have no order between them.
    """
    stated = raw.get(SOURCES_FIELD)
    docs_root = raw.get(DOCS_ROOT_FIELD)
    if SOURCES_FIELD in raw and docs_root is not None:
        raise DocstrapConfigError(
            f"`{DOCS_ROOT_FIELD}` is shorthand for `{SOURCES_FIELD}`; state one of "
            f"them, not both (in {where})"
        )
    if docs_root is not None:
        if not isinstance(docs_root, str) or not docs_root:
            raise DocstrapConfigError(
                f"`{DOCS_ROOT_FIELD}` must be a non-empty path (in {where})"
            )
        return (Source(path=docs_root, role=DOCUMENTATION_ROLE),)
    if SOURCES_FIELD not in raw:
        return None
    if stated is None:
        stated = []
    if not isinstance(stated, list):
        raise DocstrapConfigError(f"`{SOURCES_FIELD}` must be a list (in {where})")
    parsed: list[Source] = []
    for item in stated:
        if not isinstance(item, dict):
            raise DocstrapConfigError(
                f"each `{SOURCES_FIELD}` entry must be a mapping with `path` and "
                f"`role` (in {where})"
            )
        for required in ("path", "role"):
            value = item.get(required)
            if not isinstance(value, str) or not value.strip():
                raise DocstrapConfigError(
                    f"`{SOURCES_FIELD}` entry {item!r} needs `{required}` "
                    f"(in {where}). Docstrap is told a folder's role; it does not "
                    f"guess one from the name."
                )
        mount = item.get("mount")
        if mount is not None and not isinstance(mount, str):
            raise DocstrapConfigError(
                f"`mount` must be a path when given (in {where})"
            )
        unknown = set(item) - {"path", "role", "mount"}
        if unknown:
            raise DocstrapConfigError(
                f"`{SOURCES_FIELD}` entry has unknown field(s) "
                f"{sorted(unknown)} (in {where})"
            )
        parsed.append(
            Source(path=item["path"].strip(), role=item["role"].strip(), mount=mount)
        )
    return tuple(parsed)


def parse_plugins(raw: dict, where: str) -> dict[str, dict] | None:
    """The `plugins` block one level states: plugin name to settings block.

    Only `enabled` is docstrap's to read, and it must be a boolean when
    given. Every other key belongs to the plugin and is passed on unread.
    """
    if PLUGINS_FIELD not in raw or raw[PLUGINS_FIELD] is None:
        return None
    block = raw[PLUGINS_FIELD]
    if not isinstance(block, dict):
        raise DocstrapConfigError(
            f"`{PLUGINS_FIELD}` must map a plugin's name to its settings (in {where})"
        )
    parsed: dict[str, dict] = {}
    for name, settings in block.items():
        if settings is None:
            settings = {}
        if not isinstance(settings, dict):
            raise DocstrapConfigError(
                f"`{PLUGINS_FIELD}.{name}` must be a mapping (in {where})"
            )
        enabled = settings.get("enabled")
        if enabled is not None and not isinstance(enabled, bool):
            raise DocstrapConfigError(
                f"`{PLUGINS_FIELD}.{name}.enabled` must be true or false when "
                f"provided (in {where})"
            )
        parsed[str(name)] = dict(settings)
    return parsed


def _refuse_both_shapes(
    legacy_enabled: bool | None, plugins: dict[str, dict] | None, where: str
) -> None:
    """One level may not state the old switch in both its old and new shape."""
    plugin = legacy_settings.PLUGIN
    if legacy_enabled is not None and plugins is not None and plugin in plugins:
        raise DocstrapConfigError(
            f"`{LEGACY_ENABLED_FIELD}:` and `{PLUGINS_FIELD}.{plugin}` both set (in "
            f"{where}). `{LEGACY_ENABLED_FIELD}:` is the old shape; run "
            f"`docstrap config migrate`."
        )


def _parse_project(raw: dict, where: str = "<config>") -> ProjectEntry:
    """Parse one project entry from the projects: list.

    Only `path` is required; layout and title get sensible defaults so a
    minimal entry is just `- path: packages/foo`. Where its documents are
    is not defaulted here: an entry that states no `sources` or
    `docs_root` takes the wider level's.
    """
    if "path" not in raw:
        raise DocstrapConfigError(f"Project entry missing required field: path (in {raw!r})")
    layout = raw.get("layout", "markdown")
    if layout not in VALID_LAYOUTS:
        raise DocstrapConfigError(f"Project at path `{raw['path']}` has invalid layout `{layout}`")
    # Title defaults to the last path segment.
    from pathlib import PurePosixPath
    title = raw.get("title") or PurePosixPath(raw["path"]).name
    here = f"project `{raw['path']}` in {where}"
    legacy_enabled = _parse_legacy_enabled(raw, where=here)
    plugins = parse_plugins(raw, where=here)
    _refuse_both_shapes(legacy_enabled, plugins, where=here)
    return ProjectEntry(
        path=raw["path"],
        title=title,
        layout=layout,
        docs_root=raw.get(DOCS_ROOT_FIELD),
        short=raw.get("short"),
        icon=raw.get("icon"),
        priority=raw.get("priority"),
        legacy_enabled=legacy_enabled,
        sources=parse_sources(raw, where=here),
        plugins=plugins,
    )


def _parse_related(raw: dict, where: str = "<config>") -> RelatedDirectory:
    """Parse one related_directories entry."""
    for req in ("path", "title"):
        if req not in raw:
            raise DocstrapConfigError(f"related_directories entry missing required field: {req}")
    layout = raw.get("layout", "markdown")
    if layout not in VALID_LAYOUTS:
        raise DocstrapConfigError(f"related_directories entry has invalid layout `{layout}`")
    here = f"related directory `{raw['path']}` in {where}"
    return RelatedDirectory(
        path=raw["path"],
        title=raw["title"],
        layout=layout,
        docs_root=raw.get(DOCS_ROOT_FIELD),
        sources=parse_sources(raw, where=here),
        plugins=parse_plugins(raw, where=here),
    )
