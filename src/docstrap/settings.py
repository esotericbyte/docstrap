"""The one settings surface: source folders and plugin settings, at three levels.

Where a project's documents are, what role each folder plays, and which
plugins run for it are read from the two files that already exist — the
user config (``~/.config/docstrap/config.yaml``, the **installation**
level) and a ``.docstrap`` file (the **repository** level at its top, the
**project** level on one ``projects:`` or ``related_directories`` entry).
There is no second mechanism.

**Sources.** The most specific level that states a ``sources`` list wins
whole; lists are never merged. ``docs_root: X`` is shorthand for
``sources: [{path: X, role: documentation}]`` at the level that writes
it. Docstrap has no built-in folder name: if nothing states a list, the
project has no sources. A related directory that states neither field
keeps its old rule, which is that the directory itself is the source.

**Plugins.** ``plugins`` maps a plugin's name to its settings block.
Docstrap reads one key from a block, ``enabled``, tri-state as it
has always been: the most specific level that states it decides, and
nothing stated means off. Every other key is the plugin's, merged key by
key with the more specific level winning, and passed on unread.

**Compatibility.** An installation whose user config states neither
``sources`` nor ``plugins`` has not run ``docstrap config migrate``, and
is read exactly as before: its installation level contributes the
``docs`` default that migrate would write, and the old switch keys
:mod:`docstrap.legacy_settings` spells are read where they stand, with
that plugin on when nothing says otherwise. Once the user config carries
the new shape, an old switch key anywhere is a load error naming the
command — being out of date is loud, not silently read.

**Writes.** This module is the only code that writes either file, and it
writes through ruamel.yaml's round-trip mode, so a person's comments,
key order and indentation survive an edit.
"""
from __future__ import annotations

import difflib
import io
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Sequence

import yaml
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.util import load_yaml_guess_indent

from docstrap import legacy_settings as legacy
from docstrap import paths
from docstrap.config import (
    DOCSTRAP_FILENAME,
    DOCUMENTATION_ROLE,
    DRAFT_ROLE,
    LEGACY_ENABLED_FIELD,
    PLUGINS_FIELD,
    SOURCES_FIELD,
    DocstrapConfig,
    DocstrapConfigError,
    ProjectEntry,
    RelatedDirectory,
    Source,
    find_config,
    parse_plugins,
    parse_sources,
)

#: The three levels, and the answer when none of them states anything.
INSTALLATION = "installation"
REPOSITORY = "repository"
PROJECT = "project"
DEFAULT = "default"

#: The key docstrap reads from a plugin's block. Every other key is the
#: plugin's own.
ENABLED_KEY = "enabled"

MIGRATE_COMMAND = "docstrap config migrate"


#: What an unmigrated installation reads as its installation-level
#: sources, and what ``migrate`` writes so that it keeps reading them.
LEGACY_SOURCES: tuple[Source, ...] = (Source(path="docs", role=DOCUMENTATION_ROLE),)



# --- the installation level ---------------------------------------------------


@dataclass(frozen=True)
class Installation:
    """What the user config states for the one settings surface.

    ``migrated`` is whether the file carries the new shape; an unmigrated
    one is read under the compatibility rule in the module docstring.
    """

    path: Path
    migrated: bool
    sources: tuple[Source, ...] | None = None
    plugins: dict[str, dict] = field(default_factory=dict, hash=False, compare=False)

    def plugin_block(self, name: str) -> dict | None:
        return self.plugins.get(name)

    def default_enabled(self, name: str) -> bool:
        """Whether ``name`` is on when no level states ``enabled``.

        Off, except for the plugin the old switch belonged to, on an
        installation that has not migrated: it was opt-out there, and that
        installation is read as it always was.
        """
        return name == legacy.PLUGIN and not self.migrated


def installation(path: Path | None = None) -> Installation:
    """Read the installation level from the user config."""
    path = path or paths.user_config_file()
    raw = _read_mapping(path)
    where = str(path)
    migrated = SOURCES_FIELD in raw or PLUGINS_FIELD in raw
    if not migrated:
        return Installation(
            path=path,
            migrated=False,
            sources=LEGACY_SOURCES,
            plugins=_legacy_user_plugins(raw, where),
        )
    stale = [key for key in legacy.USER_FIELDS if key in raw]
    if stale:
        raise DocstrapConfigError(
            f"{where} states {', '.join(f'`{k}:`' for k in stale)} alongside the "
            f"`{PLUGINS_FIELD}`/`{SOURCES_FIELD}` shape. That is the old shape of "
            f"the `{legacy.PLUGIN}` setting; run `{MIGRATE_COMMAND}`."
        )
    return Installation(
        path=path,
        migrated=True,
        sources=parse_sources(raw, where=where),
        plugins=parse_plugins(raw, where=where) or {},
    )


def _legacy_user_plugins(raw: dict, where: str) -> dict[str, dict]:
    """The plugin block an unmigrated user config's old keys amount to."""
    block: dict[str, Any] = {}
    value = raw.get(legacy.ENABLED_FIELD)
    if isinstance(value, bool):
        block[ENABLED_KEY] = value
    root = raw.get(legacy.PROJECTS_ROOT_FIELD)
    if isinstance(root, str) and root:
        block[legacy.PROJECTS_ROOT_KEY] = root
    return {legacy.PLUGIN: block} if block else {}


def _read_mapping(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise DocstrapConfigError(f"Invalid YAML in {path}: {e}") from e
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise DocstrapConfigError(f"{path} must contain a YAML mapping at top level.")
    return data


# --- the .docstrap levels -----------------------------------------------------


def level_plugins(
    stated: dict[str, dict] | None,
    legacy_enabled: bool | None,
    where: str,
    installation: Installation,
) -> dict[str, dict] | None:
    """One `.docstrap` level's plugin blocks, its old switch key folded in.

    The old key is read only on an installation that has not migrated;
    after migration it is a load error.
    """
    if legacy_enabled is None:
        return stated
    if installation.migrated:
        raise DocstrapConfigError(
            f"`{LEGACY_ENABLED_FIELD}:` in {where} is the old shape of the "
            f"`{legacy.PLUGIN}` setting, and this installation has moved to "
            f"`{PLUGINS_FIELD}`. Run `{MIGRATE_COMMAND}`."
        )
    merged = dict(stated or {})
    merged[legacy.PLUGIN] = {
        **merged.get(legacy.PLUGIN, {}), ENABLED_KEY: legacy_enabled
    }
    return merged


@dataclass(frozen=True)
class ProjectLevels:
    """One project's effective source list, and each `.docstrap` level's plugins.

    The plugin levels are kept apart rather than folded together, so a
    report can name the level that decided.
    """

    sources: tuple[Source, ...] | None
    project_plugins: dict[str, dict] | None = field(default=None, hash=False, compare=False)
    repository_plugins: dict[str, dict] | None = field(
        default=None, hash=False, compare=False
    )


def project_levels(
    config: DocstrapConfig,
    entry: ProjectEntry | RelatedDirectory | None,
    installation: Installation,
) -> ProjectLevels:
    """The effective source list and the plugin blocks for one project.

    ``entry`` is the project's own entry, or None for a standalone
    project, whose only `.docstrap` level is the top of the file.
    """
    where = str(config.source_path or "<config>")
    repository_plugins = level_plugins(
        config.plugins, config.legacy_enabled, where, installation
    )
    project_plugins = None
    if isinstance(entry, ProjectEntry):
        project_plugins = level_plugins(
            entry.plugins, entry.legacy_enabled, f"project `{entry.path}` in {where}",
            installation,
        )
    elif isinstance(entry, RelatedDirectory):
        project_plugins = entry.plugins

    if isinstance(entry, RelatedDirectory):
        # A related directory stating neither field keeps its old rule:
        # the directory itself is the source.
        sources = entry.sources
        if sources is None:
            sources = (Source(path=".", role=DOCUMENTATION_ROLE),)
    else:
        sources = _most_specific(
            entry.sources if entry is not None else None,
            config.sources,
            installation.sources,
        )
    return ProjectLevels(
        sources=sources,
        project_plugins=project_plugins,
        repository_plugins=repository_plugins,
    )


def _most_specific(
    *levels: tuple[Source, ...] | None,
) -> tuple[Source, ...] | None:
    """The first level, most specific first, that states a list. Never a merge."""
    return next((sources for sources in levels if sources is not None), None)


# --- sources, mounted ---------------------------------------------------------


@dataclass(frozen=True)
class ResolvedSource:
    """A source folder resolved against its project root.

    ``mount`` is a posix path below the built project, ``''`` for the
    project root. A document in this source is identified by its mount
    plus its path below ``path``.
    """

    path: Path
    role: str
    mount: str
    stated: str

    @property
    def is_draft(self) -> bool:
        return self.role == DRAFT_ROLE

    def identity(self, document: Path) -> str | None:
        """``document``'s identity with its suffix dropped, or None if outside."""
        try:
            relative = document.resolve().relative_to(self.path.resolve())
        except ValueError:
            return None
        name = relative.with_suffix("").as_posix()
        if not self.mount:
            return name
        return self.mount if name == "." else f"{self.mount}/{name}"


def mounted(
    root: Path, sources: Sequence[Source] | None, where: str = ""
) -> tuple[ResolvedSource, ...]:
    """Each source with its effective mount, resolved against ``root``.

    The first source mounts at the project root and every other at its
    own path, unless it states a mount. That default is what keeps every
    existing document identity the same. Two sources on one
    mount, or one mount inside another, would put two folders' documents
    under one name, so both are refused.
    """
    resolved: list[ResolvedSource] = []
    for index, source in enumerate(sources or ()):
        if source.mount is not None:
            mount = _normal_mount(source.mount, where)
        elif index == 0:
            mount = ""
        else:
            mount = _normal_mount(source.path, where)
        resolved.append(
            ResolvedSource(
                path=(root / source.path).resolve(),
                role=source.role,
                mount=mount,
                stated=source.path,
            )
        )
    mounts = [s.mount for s in resolved]
    for i, a in enumerate(mounts):
        for b in mounts[i + 1:]:
            if a == b:
                raise DocstrapConfigError(
                    f"two sources mount at `{a or '.'}`{_in(where)}; give one of "
                    f"them its own `mount`."
                )
            if a and b and (b.startswith(a + "/") or a.startswith(b + "/")):
                raise DocstrapConfigError(
                    f"source mounts `{a}` and `{b}` nest{_in(where)}; a mount may "
                    f"not lie inside another."
                )
    return tuple(resolved)


def _normal_mount(raw: str, where: str) -> str:
    text = raw.replace("\\", "/").strip().strip("/")
    parts = [p for p in PurePosixPath(text).parts if p not in ("", ".")]
    if any(p == ".." for p in parts):
        raise DocstrapConfigError(f"mount `{raw}` leaves the project{_in(where)}")
    return "/".join(parts)


def _in(where: str) -> str:
    return f" (in {where})" if where else ""


# --- plugins ------------------------------------------------------------------


@dataclass(frozen=True)
class PluginSetting:
    """Whether a plugin runs for a project, which level decided, and its keys."""

    name: str
    enabled: bool
    level: str
    settings: dict = field(default_factory=dict, hash=False, compare=False)

    @property
    def stated(self) -> bool:
        return self.level != DEFAULT


def plugin_setting(
    name: str,
    project: dict[str, dict] | None,
    repository: dict[str, dict] | None,
    installation: Installation,
) -> PluginSetting:
    """Resolve one plugin across the three levels.

    ``enabled``: the most specific level that states it wins; nothing
    stated means :meth:`Installation.default_enabled`. Every other key is
    merged key by key, the more specific level winning.
    """
    blocks = (
        (PROJECT, (project or {}).get(name)),
        (REPOSITORY, (repository or {}).get(name)),
        (INSTALLATION, installation.plugin_block(name)),
    )
    enabled, level = installation.default_enabled(name), DEFAULT
    for where, block in blocks:
        if block is not None and block.get(ENABLED_KEY) is not None:
            enabled, level = bool(block[ENABLED_KEY]), where
            break
    merged: dict[str, Any] = {}
    for _where, block in reversed(blocks):
        for key, value in (block or {}).items():
            if key != ENABLED_KEY:
                merged[key] = value
    return PluginSetting(name=name, enabled=enabled, level=level, settings=merged)


def stated_enabled(blocks: dict[str, dict] | None, name: str) -> bool | None:
    """What one level's blocks say about ``name``'s ``enabled``, or None."""
    block = (blocks or {}).get(name)
    if block is None:
        return None
    value = block.get(ENABLED_KEY)
    return value if isinstance(value, bool) else None


# --- round-trip writes ----------------------------------------------------------


def _yaml_for(text: str) -> YAML:
    """A round-trip YAML that writes ``text``'s indentation back as it found it."""
    rt = YAML()
    rt.preserve_quotes = True
    rt.width = 4096
    mapping, sequence, offset = 2, 2, 0
    if text.strip():
        try:
            _data, guessed, block_seq_indent = load_yaml_guess_indent(text)
        except Exception:  # noqa: BLE001 — a guess is only a guess
            guessed, block_seq_indent = None, None
        if guessed is not None and block_seq_indent is not None:
            sequence, offset = guessed, block_seq_indent
        mapping = _mapping_indent(text) or mapping
    rt.indent(mapping=mapping, sequence=max(sequence, offset + 2), offset=offset)
    return rt


def _mapping_indent(text: str) -> int | None:
    """The indent of the first nested mapping key in ``text``, if any."""
    lines = [line for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    for above, below in zip(lines, lines[1:]):
        if not above.rstrip().endswith(":") or above.lstrip().startswith("- "):
            continue
        outer = len(above) - len(above.lstrip())
        inner = len(below) - len(below.lstrip())
        if inner > outer and not below.lstrip().startswith("- "):
            return inner - outer
    return None


@dataclass(frozen=True)
class FileChange:
    """One file a write changed, or would change; ``before`` is '' for a new file."""

    path: Path
    before: str
    after: str
    changes: tuple[str, ...] = ()

    @property
    def changed(self) -> bool:
        return self.before != self.after

    def diff(self) -> str:
        return "".join(
            difflib.unified_diff(
                self.before.splitlines(keepends=True),
                self.after.splitlines(keepends=True),
                fromfile=str(self.path),
                tofile=str(self.path),
            )
        )


class _Edit:
    """A loaded document being edited, and the notes on what changed."""

    def __init__(self, path: Path):
        self.path = path
        self.before = path.read_text(encoding="utf-8") if path.exists() else ""
        self.yaml = _yaml_for(self.before)
        data = self.yaml.load(self.before) if self.before.strip() else None
        if data is None:
            data = CommentedMap()
        if not isinstance(data, CommentedMap):
            raise DocstrapConfigError(f"{path} must contain a YAML mapping at top level.")
        self.data: CommentedMap = data
        self.changes: list[str] = []

    def result(self) -> FileChange:
        if not self.changes:
            return FileChange(self.path, self.before, self.before)
        out = io.StringIO()
        self.yaml.dump(self.data, out)
        return FileChange(self.path, self.before, out.getvalue(), tuple(self.changes))


def _apply(path: Path, edit: Callable[[_Edit], None], write: bool = True) -> FileChange:
    """Load ``path`` for a round-trip edit, apply ``edit``, write if it changed."""
    loaded = _Edit(path)
    edit(loaded)
    change = loaded.result()
    if write and change.changed:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(change.after, encoding="utf-8")
    return change


def _set_key(m: CommentedMap, key: str, value: Any, after: str | None = None) -> bool:
    """Set ``key`` to ``value``; a new key goes after ``after`` when given."""
    if key in m and _plain(m[key]) == _plain(value):
        return False
    if key in m or after is None or after not in m:
        m[key] = value
    else:
        m.insert(list(m.keys()).index(after) + 1, key, value)
    return True


def _plain(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_plain(v) for v in value]
    return value


def _replace_key(m: CommentedMap, old: str, new: str, value: Any) -> None:
    """Put ``new: value`` where ``old`` stood, keeping the comment on its line."""
    position = list(m.keys()).index(old)
    comment = m.ca.items.pop(old, None)
    del m[old]
    m.insert(position, new, value)
    if comment is not None and comment[2] is not None:
        _carry_comment(value, comment[2])


def _carry_comment(value: Any, token: Any) -> None:
    """Hang a moved line's trailing comment on the innermost last key of ``value``."""
    target = value
    while isinstance(target, CommentedMap) and target:
        last = list(target.keys())[-1]
        if isinstance(target[last], CommentedMap) and target[last]:
            target = target[last]
            continue
        target.ca.items[last] = [None, None, token, None]
        return


def _plugin_block(m: CommentedMap, plugin: str) -> CommentedMap:
    plugins = m.get(PLUGINS_FIELD)
    if not isinstance(plugins, CommentedMap):
        plugins = CommentedMap()
        m[PLUGINS_FIELD] = plugins
    block = plugins.get(plugin)
    if not isinstance(block, CommentedMap):
        block = CommentedMap()
        plugins[plugin] = block
    return block


def write_user_fields(updates: dict[str, Any]) -> FileChange:
    """Set (or, for None, remove) top-level keys of the user config.

    Everything else in the file — keys this caller does not own, comments,
    order — is left as it was. ``docstrap.user_config`` saves the stores
    list through this.
    """
    def edit(loaded: _Edit) -> None:
        for key, value in updates.items():
            if value is None:
                if key in loaded.data:
                    del loaded.data[key]
                    loaded.changes.append(f"removed `{key}`")
            elif _set_key(loaded.data, key, _rt(value)):
                loaded.changes.append(f"set `{key}`")

    return _apply(paths.user_config_file(), edit)


def _rt(value: Any) -> Any:
    """``value`` as round-trip nodes, so new structure dumps in block style."""
    if isinstance(value, dict):
        m = CommentedMap()
        for k, v in value.items():
            m[k] = _rt(v)
        return m
    if isinstance(value, (list, tuple)):
        s = CommentedSeq()
        s.extend(_rt(v) for v in value)
        return s
    return value


def create_docstrap(path: Path, fields: dict[str, Any]) -> FileChange:
    """Write a new `.docstrap` holding ``fields``, replacing any file there."""
    if path.exists():
        path.unlink()

    def edit(loaded: _Edit) -> None:
        for key, value in fields.items():
            loaded.data[key] = _rt(value)
            loaded.changes.append(f"set `{key}`")

    return _apply(path, edit)


def write_plugin_setting(
    level: str,
    target: Path | None,
    plugin: str,
    key: str,
    value: Any,
) -> FileChange:
    """Set ``plugins.<plugin>.<key>`` at one level. Idempotent.

    ``level`` is :data:`INSTALLATION` (``target`` ignored; the user
    config), :data:`REPOSITORY` (``target`` a `.docstrap` file or the
    directory holding one) or :data:`PROJECT` (``target`` the project's
    directory; its `.docstrap` entry is found, and a standalone project's
    entry is the top of its file).
    """
    if level == INSTALLATION:
        path, locate = paths.user_config_file(), None
    elif level == REPOSITORY:
        if target is None:
            raise ValueError("a repository-level write needs the `.docstrap` it goes in")
        path = target if target.name == DOCSTRAP_FILENAME else target / DOCSTRAP_FILENAME
        locate = None
    elif level == PROJECT:
        if target is None:
            raise ValueError("a project-level write needs the project's directory")
        path, locate = _project_file(target)
    else:
        raise ValueError(f"unknown level {level!r}")
    if level != INSTALLATION and not path.is_file():
        raise DocstrapConfigError(f"No {DOCSTRAP_FILENAME} file at {path}")

    def edit(loaded: _Edit) -> None:
        mapping = loaded.data if locate is None else _entry(loaded.data, path, locate)
        block = _plugin_block(mapping, plugin)
        if _set_key(block, key, _rt(value)):
            loaded.changes.append(f"{PLUGINS_FIELD}.{plugin}.{key}: {_show(value)}")

    return _apply(path, edit)


def _show(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _project_file(project_dir: Path) -> tuple[Path, str | None]:
    """The `.docstrap` a project is declared in, and its entry's path (None: standalone)."""
    project_dir = project_dir.expanduser().resolve()
    config_path = find_config(project_dir)
    if config_path is None:
        raise DocstrapConfigError(f"No {DOCSTRAP_FILENAME} above {project_dir}")
    base = config_path.parent.resolve()
    raw = _read_mapping(config_path)
    for group in ("projects", "related_directories"):
        for item in raw.get(group) or []:
            if isinstance(item, dict) and "path" in item:
                if (base / str(item["path"])).resolve() == project_dir:
                    return config_path, str(item["path"])
    if raw.get("projects"):
        raise DocstrapConfigError(
            f"{config_path} declares no project at {project_dir}"
        )
    if base != project_dir:
        raise DocstrapConfigError(
            f"{project_dir} is not the standalone project {config_path} declares"
        )
    return config_path, None


def _entry(data: CommentedMap, path: Path, entry_path: str) -> CommentedMap:
    for group in ("projects", "related_directories"):
        for item in data.get(group) or []:
            if isinstance(item, CommentedMap) and str(item.get("path")) == entry_path:
                return item
    raise DocstrapConfigError(f"{path} has no entry for `{entry_path}`")


# --- docstrap config migrate ----------------------------------------------------


def migrate(*, write: bool = False) -> list[FileChange]:
    """Rewrite the user config and every registered store into the new shape.

    In the user config, the old switch key (spelled in
    :mod:`docstrap.legacy_settings`) becomes ``plugins.<plugin>.enabled``
    — absent becomes ``true``, so this machine keeps its opt-out
    behaviour — and the old projects-root key becomes
    ``plugins.<plugin>.projects_root``; ``members`` is added with the
    member rule that was built in, and ``sources`` with the ``docs``
    default every `.docstrap` relying on it needs. In each registered
    store, every old switch key, at the top and on each entry, becomes
    ``plugins.<plugin>.enabled``.

    Returns every file that changes (or, without ``write``, would). It
    moves no file and touches no database. The stores are written before
    the user config, so an interrupted run leaves an installation that is
    still read under the compatibility rule rather than one that refuses
    its own stores. Running it twice changes nothing the second time.
    """
    user_path = paths.user_config_file()
    results = [
        _apply(store, _migrate_docstrap, write=write)
        for store in _stores(_read_mapping(user_path))
    ]
    results.append(_apply(user_path, _migrate_user, write=write))
    return [change for change in results if change.changed]


def _stores(raw_user: dict) -> list[Path]:
    found: list[Path] = []
    for item in raw_user.get("stores") or []:
        path = Path(str(item)).expanduser()
        if path.is_file() and path not in found:
            found.append(path)
    return found


def _migrate_user(edit: _Edit) -> None:
    m = edit.data
    stale = [key for key in legacy.USER_FIELDS if key in m]
    already = SOURCES_FIELD in m or PLUGINS_FIELD in m
    if already and not stale:
        return

    if "version" not in m:
        m.insert(0, "version", 1)
        edit.changes.append("added `version: 1`")

    wanted: dict[str, Any] = {}
    if not already:
        sources = _rt([{"path": s.path, "role": s.role} for s in LEGACY_SOURCES])
        for item in sources:
            item.fa.set_flow_style()
        _set_key(m, SOURCES_FIELD, sources, after="stores")
        edit.changes.append(
            f"added `{SOURCES_FIELD}` with the `docs` default the stores rely on"
        )
        old = m.get(legacy.ENABLED_FIELD)
        wanted[ENABLED_KEY] = old if isinstance(old, bool) else True
        members = _rt(list(legacy.MEMBERS))
        members.fa.set_flow_style()
        wanted[legacy.MEMBERS_KEY] = members
    elif isinstance(m.get(legacy.ENABLED_FIELD), bool):
        wanted[ENABLED_KEY] = m[legacy.ENABLED_FIELD]
    if legacy.PROJECTS_ROOT_FIELD in m:
        wanted[legacy.PROJECTS_ROOT_KEY] = m[legacy.PROJECTS_ROOT_FIELD]

    if PLUGINS_FIELD not in m:
        if stale:
            m.insert(list(m.keys()).index(stale[0]), PLUGINS_FIELD, CommentedMap())
        else:
            _set_key(m, PLUGINS_FIELD, CommentedMap(), after=SOURCES_FIELD)
    comments = []
    for key in stale:
        comment = m.ca.items.pop(key, None)
        if comment is not None and comment[2] is not None:
            comments.append(comment[2])
        del m[key]
        edit.changes.append(f"moved `{key}` into `{PLUGINS_FIELD}.{legacy.PLUGIN}`")

    block = _plugin_block(m, legacy.PLUGIN)
    for key, value in wanted.items():
        if key not in block and _set_key(block, key, value):
            edit.changes.append(f"set `{PLUGINS_FIELD}.{legacy.PLUGIN}.{key}`")
    if comments:
        _carry_comment(block, comments[0])


def _migrate_docstrap(edit: _Edit) -> None:
    _migrate_level(edit, edit.data, "top level")
    for group in ("projects", "related_directories"):
        for item in edit.data.get(group) or []:
            if isinstance(item, CommentedMap):
                _migrate_level(edit, item, f"`{item.get('path')}`")


def _migrate_level(edit: _Edit, m: CommentedMap, label: str) -> None:
    if LEGACY_ENABLED_FIELD not in m:
        return
    value = m[LEGACY_ENABLED_FIELD]
    if PLUGINS_FIELD in m:
        comment = m.ca.items.pop(LEGACY_ENABLED_FIELD, None)
        del m[LEGACY_ENABLED_FIELD]
        if value is not None:
            block = _plugin_block(m, legacy.PLUGIN)
            _set_key(block, ENABLED_KEY, value)
            if comment is not None and comment[2] is not None:
                _carry_comment(block, comment[2])
    elif value is None:
        del m[LEGACY_ENABLED_FIELD]
    else:
        inner = CommentedMap()
        inner[ENABLED_KEY] = value
        new = CommentedMap()
        new[legacy.PLUGIN] = inner
        _replace_key(m, LEGACY_ENABLED_FIELD, PLUGINS_FIELD, new)
    edit.changes.append(
        f"{label}: `{LEGACY_ENABLED_FIELD}:` → "
        f"`{PLUGINS_FIELD}.{legacy.PLUGIN}.{ENABLED_KEY}`"
    )
