"""The plugin seam: what a plugin may contribute, and when it runs.

Docstrap defines six hooks and a plugin implements any of them. The
mechanism is pluggy.

**A plugin is found by being installed.** :func:`manager` loads every
module a package declares under the ``docstrap.plugins`` entry-point
group, registered under its entry-point name. That name is the one the
``plugins`` block of the settings surface keys on. Nothing here names a
plugin: a plugin docstrap ships with declares itself under the same group
in docstrap's own package metadata, exactly as an outside package would.

**Being installed does not turn a plugin on.** A plugin runs for a project
only when the settings enable it there
(:func:`docstrap.settings.plugin_setting`). A per-project hook is called
through pluggy's ``subset_hook_caller``, which leaves out every plugin not
enabled for that project; docstrap writes no filtering of its own. The
three hooks that belong to no project — ``.gitignore`` lines, ``docstrap
init`` and ``docstrap doctor`` — run the plugins the installation level
enables.

Each enabled plugin receives ``settings``, a mapping from plugin name to
that plugin's own keys as the levels merged them, and reads its own entry.
Docstrap reads none of those keys.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

import pluggy

from docstrap import settings as settings_mod
from docstrap.config import DocstrapConfigError, Source
from docstrap.settings import Installation, ResolvedSource

if TYPE_CHECKING:
    from docstrap.scan import ScannedProject

PROJECT_NAME = "docstrap"
#: The entry-point group a package declares a docstrap plugin under.
ENTRY_POINT_GROUP = "docstrap.plugins"

hookspec = pluggy.HookspecMarker(PROJECT_NAME)
#: What a plugin marks each of its hook implementations with.
hookimpl = pluggy.HookimplMarker(PROJECT_NAME)


@dataclass(frozen=True)
class Finding:
    """One line a plugin adds to ``docstrap doctor``: a check and its verdict."""

    ok: bool
    message: str


class Specs:
    """The six hooks. Each docstring names what calls it."""

    @hookspec
    def docstrap_prepare_project(
        self, project: ScannedProject, settings: Mapping[str, dict]
    ) -> None:
        """Run before a project's build mirrors anything.

        The place to wire what the project's sources will read, such as a
        store entry and the link to it.
        """

    @hookspec
    def docstrap_project_sources(
        self, project: ScannedProject, settings: Mapping[str, dict]
    ) -> list[Source]:
        """Source folders this plugin adds to ``project``, after its declared ones.

        A source's ``path`` may be absolute. It should state a ``mount``;
        one a declared source already holds is not added.
        Must not create anything: :mod:`docstrap.projectscope` asks too.
        """

    @hookspec(firstresult=True)
    def docstrap_draft_root(self, project_slug: str) -> Path | None:
        """Where the project's derivatives are written, creating it.

        The first answer wins. :func:`docstrap.drafts.draft_root` falls
        back to the project's declared ``draft`` source when none answers.
        """

    @hookspec
    def docstrap_gitignore_patterns(self) -> list[str]:
        """Lines a project's ``.gitignore`` should carry for this plugin."""

    @hookspec
    def docstrap_init(self) -> list[tuple[str, Path]]:
        """Create this plugin's directories; return them as labelled paths."""

    @hookspec
    def docstrap_doctor_report(self, root: Path) -> list[Finding]:
        """Findings for ``docstrap doctor``, which was pointed at ``root``."""


@lru_cache(maxsize=1)
def manager() -> pluggy.PluginManager:
    """The one plugin manager, with every installed plugin registered."""
    pm = pluggy.PluginManager(PROJECT_NAME)
    pm.add_hookspecs(Specs)
    pm.load_setuptools_entrypoints(ENTRY_POINT_GROUP)
    return pm


def installed() -> tuple[str, ...]:
    """The names of the registered plugins, in registration order."""
    return tuple(
        name for name, plugin in manager().list_name_plugin() if plugin is not None
    )


# --- which plugins run ----------------------------------------------------------


def enabled_for(
    project: ScannedProject, installation: Installation | None = None
) -> dict[str, dict]:
    """The plugins enabled for ``project``, each with its merged settings."""
    installation = installation or settings_mod.installation()
    return _enabled(project.project_plugins, project.repository_plugins, installation)


def enabled_for_installation(installation: Installation | None = None) -> dict[str, dict]:
    """The plugins the installation level enables, each with its settings."""
    return _enabled(None, None, installation or settings_mod.installation())


def _enabled(
    project: dict[str, dict] | None,
    repository: dict[str, dict] | None,
    installation: Installation,
) -> dict[str, dict]:
    found: dict[str, dict] = {}
    for name in installed():
        setting = settings_mod.plugin_setting(name, project, repository, installation)
        if setting.enabled:
            found[name] = setting.settings
    return found


def hook(name: str, enabled: Mapping[str, dict]) -> pluggy.HookCaller:
    """The hook ``name``, calling only the plugins in ``enabled``."""
    pm = manager()
    left_out = [
        plugin
        for plugin_name, plugin in pm.list_name_plugin()
        if plugin is not None and plugin_name not in enabled
    ]
    return pm.subset_hook_caller(name, left_out)


# --- the calls docstrap makes -----------------------------------------------------


def prepare_project(project: ScannedProject) -> None:
    """Hook 1, for every plugin enabled for ``project``."""
    enabled = enabled_for(project)
    hook("docstrap_prepare_project", enabled)(project=project, settings=enabled)


def project_sources(project: ScannedProject) -> tuple[ResolvedSource, ...]:
    """Hook 2: the sources plugins add to ``project``, resolved and mounted.

    A source whose mount a declared source, or an earlier plugin source,
    already holds is not added — the declared statement is the more
    deliberate one.
    """
    enabled = enabled_for(project)
    taken = {s.mount for s in project.sources}
    added: list[ResolvedSource] = []
    for contributed in hook("docstrap_project_sources", enabled)(
        project=project, settings=enabled
    ):
        for source in contributed or ():
            mount = source.mount if source.mount is not None else source.path
            try:
                (resolved,) = settings_mod.mounted(
                    project.root_dir,
                    (Source(path=source.path, role=source.role, mount=mount),),
                    where=f"a plugin source of `{project.slug}`",
                )
            except DocstrapConfigError:
                continue
            if resolved.mount in taken:
                continue
            taken.add(resolved.mount)
            added.append(resolved)
    return tuple(added)


def draft_root(project_slug: str, enabled: Mapping[str, dict]) -> Path | None:
    """Hook 3, first answer wins. See :func:`docstrap.drafts.draft_root`."""
    answer = hook("docstrap_draft_root", enabled)(project_slug=project_slug)
    return Path(answer) if answer is not None else None


def gitignore_patterns() -> tuple[str, ...]:
    """Hook 4: the ``.gitignore`` lines the installation's plugins want."""
    patterns: list[str] = []
    for contributed in hook("docstrap_gitignore_patterns", enabled_for_installation())():
        for pattern in contributed or ():
            if pattern not in patterns:
                patterns.append(pattern)
    return tuple(patterns)


def init() -> list[tuple[str, Path]]:
    """Hook 5: create each plugin's directories, and say which they are."""
    created: list[tuple[str, Path]] = []
    for contributed in hook("docstrap_init", enabled_for_installation())():
        created.extend(contributed or ())
    return created


def doctor_report(root: Path) -> list[Finding]:
    """Hook 6: every plugin's findings for ``docstrap doctor``."""
    findings: list[Finding] = []
    for contributed in hook("docstrap_doctor_report", enabled_for_installation())(
        root=root
    ):
        findings.extend(contributed or ())
    return findings
