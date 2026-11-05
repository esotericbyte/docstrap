"""Project enumeration from a loaded .docstrap config.

For workspace-mode: yields each ProjectEntry directly.
For standalone-mode: yields a synthetic single-project entry derived
from the config's top-level fields.
Related directories are yielded after projects.
"""
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from docstrap import settings
from docstrap.config import (
    DocstrapConfig,
    ProjectEntry,
    RelatedDirectory,
    in_ignored_tree,
)
from docstrap.settings import Installation, ResolvedSource
from docstrap.slugs import slugify


@dataclass(frozen=True)
class ScannedProject:
    """A project resolved to absolute filesystem paths, ready to build."""

    slug: str
    title: str
    layout: str
    root_dir: Path        # absolute; where the project lives on disk
    # absolute; the source mounted at the project root, or None when no
    # source is — a project whose settings state no sources has none.
    docs_dir: Path | None
    short: str | None = None
    icon: str | None = None
    priority: int | None = None
    kind: str = "project"  # 'project' | 'related'
    # Inherited from the parent .docstrap config; layouts apply as
    # both a top-level-directory skip and a Sphinx exclude_patterns entry.
    exclude_dirs: tuple[str, ...] = ()
    exclude_file_suffixes: tuple[str, ...] = ()
    # The project's own README, when it has one and it sits outside
    # docs_dir. Layouts include it as one extra document; see
    # find_readme for what counts.
    readme_path: Path | None = None
    # The project's source folders, each with its role and mount, as the
    # one settings surface resolves them. `docs_dir` is the
    # one among them mounted at the project root.
    sources: tuple[ResolvedSource, ...] = ()
    # The two `.docstrap` levels of the `plugins` block, kept apart rather
    # than folded together, so a report can name which level decided.
    # Resolution lives in docstrap.settings.plugin_setting.
    project_plugins: dict[str, dict] | None = field(
        default=None, hash=False, compare=False
    )
    repository_plugins: dict[str, dict] | None = field(
        default=None, hash=False, compare=False
    )

    @property
    def published_sources(self) -> tuple[ResolvedSource, ...]:
        """The sources walked as documents: every one but a draft."""
        return tuple(s for s in self.sources if not s.is_draft)


def scan(
    config: DocstrapConfig, installation: Installation | None = None
) -> Iterator[ScannedProject]:
    """Enumerate all projects and related directories in a .docstrap config.

    ``installation`` is the user config's level of the settings surface;
    read when not given, since a project's sources can come from there.
    """
    if config.ignore:
        return
    if installation is None:
        installation = settings.installation()

    if config.is_workspace_mode:
        for p in config.projects:
            if _has_hidden_path_part(p.path):
                continue
            project = _from_entry(p, config, installation, kind="project")
            if not in_ignored_tree(project.root_dir, config.root_dir):
                yield project
    else:
        yield _from_standalone(config, installation)

    for r in config.related_directories:
        if _has_hidden_path_part(r.path):
            continue
        related = _from_entry(r, config, installation, kind="related")
        if not in_ignored_tree(related.root_dir, config.root_dir):
            yield related


# The two README filenames docstrap recognises, in preference order.
# Matched case-insensitively, so README.md, readme.md and Readme.MD all
# count; nothing beyond these two stems is a README here.
_README_SUFFIXES: tuple[str, ...] = (".md", ".txt")
_README_STEM = "readme"


def find_readme(
    root_dir: Path,
    sources: tuple[ResolvedSource, ...] | Path | None,
    exclude_file_suffixes: tuple[str, ...] = (),
) -> Path | None:
    """The project's README file, or None when it has none worth adding.

    Only root_dir's immediate children are considered — a README is a
    top-level file by definition, and widening the search is exactly the
    docs_root-less sweep that made this capability unusable before.

    Returns None when the README already lies inside a published source:
    that source's walk publishes it there, and yielding it here as well
    would put the same file on the site twice. A suffix the config
    excludes is likewise not a README docstrap will publish.
    ``sources`` may be one directory, for a caller that has only that.
    """
    if not root_dir.is_dir():
        return None
    if isinstance(sources, Path):
        directories = [sources]
    else:
        directories = [s.path for s in sources or () if not s.is_draft]
    if any(_is_within(root_dir, directory) for directory in directories):
        return None

    excluded = {s.lower() for s in exclude_file_suffixes}
    try:
        children = sorted(root_dir.iterdir())
    except OSError:
        return None

    by_suffix: dict[str, Path] = {}
    for child in children:
        suffix = child.suffix.lower()
        if child.stem.lower() != _README_STEM:
            continue
        if suffix not in _README_SUFFIXES or suffix in excluded:
            continue
        if not child.is_file():
            continue
        # `children` is sorted, so among case variants of one name the
        # first seen is the one every run picks.
        by_suffix.setdefault(suffix, child)

    for suffix in _README_SUFFIXES:
        if suffix in by_suffix:
            return by_suffix[suffix]
    return None


def _is_within(path: Path, ancestor: Path) -> bool:
    """True when path is ancestor or lies beneath it."""
    try:
        path.resolve().relative_to(ancestor.resolve())
    except ValueError:
        return False
    return True


def _from_entry(
    entry: ProjectEntry | RelatedDirectory,
    cfg: DocstrapConfig,
    installation: Installation,
    kind: str,
) -> ScannedProject:
    root = (cfg.root_dir / entry.path).resolve()
    return _scanned(
        cfg,
        installation,
        entry,
        root=root,
        slug=slugify(entry.path),
        title=entry.title,
        layout=entry.layout,
        kind=kind,
        short=getattr(entry, "short", None),
        icon=getattr(entry, "icon", None),
        priority=getattr(entry, "priority", None),
    )


def _from_standalone(config: DocstrapConfig, installation: Installation) -> ScannedProject:
    assert config.layout is not None  # validated at load
    return _scanned(
        config,
        installation,
        None,
        root=config.root_dir,
        slug=slugify(config.title),
        title=config.title,
        layout=config.layout,
        kind="project",
        short=config.short,
        icon=config.icon,
        priority=config.priority,
    )


def _scanned(
    cfg: DocstrapConfig,
    installation: Installation,
    entry: ProjectEntry | RelatedDirectory | None,
    *,
    root: Path,
    slug: str,
    title: str,
    layout: str,
    kind: str,
    short: str | None,
    icon: str | None,
    priority: int | None,
) -> ScannedProject:
    levels = settings.project_levels(cfg, entry, installation)
    where = f"`{entry.path}` in {cfg.source_path}" if entry is not None else str(cfg.source_path)
    sources = settings.mounted(root, levels.sources, where=where)
    docs_dir = next((s.path for s in sources if s.mount == ""), None)
    return ScannedProject(
        slug=slug,
        title=title,
        layout=layout,
        root_dir=root,
        docs_dir=docs_dir,
        readme_path=find_readme(root, sources, cfg.exclude_file_suffixes),
        short=short,
        icon=icon,
        priority=priority,
        kind=kind,
        sources=sources,
        project_plugins=levels.project_plugins,
        repository_plugins=levels.repository_plugins,
        exclude_dirs=cfg.exclude_dirs,
        exclude_file_suffixes=cfg.exclude_file_suffixes,
    )


def _has_hidden_path_part(path: str) -> bool:
    """True when a config-relative path enters a dotted directory."""
    return any(
        part.startswith(".")
        for part in PurePosixPath(path.replace("\\", "/")).parts
        if part not in ("", ".")
    )
