"""Where a project's derivatives are written: its draft root.

Answers, addenda and review records are the answer loop's files, and the
answer loop is docstrap's. Where they go is not: a plugin may provide the
place, and otherwise a project may declare one.

:func:`draft_root` asks the plugins enabled for the project first, and
the first answer wins. If none answers, it is the project's declared
``draft`` source when that folder exists — nothing creates a declared
folder — and failing that there is none. A project with no draft
root has nowhere for a derivative to go, so a writer raises
:class:`NoDraftRoot` rather than invent a directory.
"""
from __future__ import annotations

from pathlib import Path

from docstrap import plugins


class NoDraftRoot(LookupError):
    """The project has no draft root: no plugin provides one and it declares none."""


def draft_root(project_slug: str) -> Path | None:
    """The project's draft root, or None. A plugin's answer is created by it.

    The project is looked up by its slug among the registered stores, so
    its own settings decide which plugins are asked. A slug no registered
    store declares has no project-level settings; the installation level
    alone decides for it, and it has no declared source to fall back to.
    """
    project = _project(project_slug)
    if project is None:
        enabled = plugins.enabled_for_installation()
    else:
        enabled = plugins.enabled_for(project)
    answered = plugins.draft_root(project_slug, enabled)
    if answered is not None:
        return answered
    if project is not None:
        for source in project.sources:
            if source.is_draft and source.path.is_dir():
                return source.path
    return None


def require(project_slug: str) -> Path:
    """The project's draft root, or :class:`NoDraftRoot`."""
    root = draft_root(project_slug)
    if root is None:
        raise NoDraftRoot(
            f"project {project_slug!r} has no draft root: no enabled plugin provides "
            f"one and it declares no source with role `draft`."
        )
    return root


def _project(project_slug: str):
    from docstrap import projectscope

    try:
        return projectscope.resolve_slug(project_slug).project
    except projectscope.UnknownProjectSlug:
        return None
