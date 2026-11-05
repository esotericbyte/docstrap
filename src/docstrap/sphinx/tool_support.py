"""Shared Sphinx plumbing for docstrap tools.

This module is the renderer adapter, not a tool: it handles what every
tool needs from Sphinx regardless of what the tool does. Registering a
``static/`` directory so client source gets copied into the built site,
computing the per-page metadata (project slug, doc slug, document ID)
that tools inject into rendered HTML, and turning a page into the
:class:`~docstrap.tools.launcher.PageContext` the launcher decides with.

Anything specific to one tool belongs in that tool's own directory
under :mod:`docstrap.tools`, not here.
"""
from __future__ import annotations

import html
import os
from pathlib import Path
from typing import Any, Optional

from docstrap.slugs import slugify
from docstrap.tools import registry
from docstrap.tools.declaration import ToolDeclaration
from docstrap.tools.launcher import PageContext

# Directory holding the assets shared by every tool: the common bundle,
# the base stylesheet, and the launcher itself.
_STATIC_DIR = Path(__file__).parent / "static"

#: The conf.py value carrying the scanned project's slug. Written by
#: :func:`docstrap.layouts.markdown.write_conf_py`, read back here. It
#: exists because Sphinx's own ``project`` is a human-readable title,
#: and a tool addressing the project by its title wrote its derivatives
#: into a directory the project never links to.
PROJECT_SLUG_CONFIG = "docstrap_project_slug"


#: The ``type`` every tool's script is registered under, and the shared
#: scripts the tools run on. A browser neither fetches nor runs a
#: ``<script>`` of a type it does not know, so a published page carries
#: its tools inert: what reaches a reader who opened the page on its own
#: is the document and the button that opens it in the viewer. Inside
#: the viewer, ``docstrap-viewer-button.js`` turns each of these into a
#: real script, in page order. Sphinx still writes the tags, so they keep
#: the URL and the cache-busting checksum it gives every other asset.
#: The client spells this once too; ``test_viewer.py`` holds the two to
#: one name.
DEFERRED_SCRIPT_TYPE = "text/x-docstrap-deferred"


def add_deferred_js_file(app, filename: str) -> None:
    """Register a script that runs only inside the viewer.

    The Svelte runtime is in every tool bundle, so this is what keeps it
    off a page opened directly (:data:`DEFERRED_SCRIPT_TYPE`). Styles are
    not deferred: the qa form's gate is a stylesheet rule on the
    directive's own markup and has to hold with no script at all.
    """
    app.add_js_file(filename, type=DEFERRED_SCRIPT_TYPE)


def register_static_dir(app, directory: Optional[Path] = None) -> None:
    """Add a static directory to html_static_path.

    Idempotent — safe to call from every tool's setup(). Sphinx flattens
    every entry of ``html_static_path`` into a single ``_static/``, so
    ``add_js_file()`` can reference files by bare filename no matter
    which tool directory they came from. Declaration-derived bundle
    names (``docstrap-<id>.js``) keep that flattening collision-free
    because tool ids are unique.

    Defaults to the shared directory when no directory is given.
    """
    resolved = str((directory or _STATIC_DIR).resolve())
    if resolved not in app.config.html_static_path:
        app.config.html_static_path.append(resolved)


def register_project_slug_config(app) -> None:
    """Declare :data:`PROJECT_SLUG_CONFIG`, once, whoever asks first.

    Two extensions need the value and either may load first — the tools,
    which address a project's storage by it, and
    :mod:`docstrap.sphinx.composed`, which composes that project's pages.
    Sphinx raises on a second registration of the same name, so the
    declaration lives here and both call this.

    The guard is a flag on the application rather than a look into its
    config, because the config object differs between a Sphinx run and
    the fake app the extension-point tests drive, and a registration
    guard that only works in one of them is not a guard.
    """
    if getattr(app, "_docstrap_project_slug_registered", False):
        return
    app.add_config_value(PROJECT_SLUG_CONFIG, "", "html")
    app._docstrap_project_slug_registered = True  # type: ignore[attr-defined]


def add_common_asset(app) -> None:
    """Register the shared docstrap-common.js and docstrap.css.

    Called by every tool's setup; guarded so it only registers once.
    """
    if getattr(app, "_docstrap_common_registered", False):
        return
    register_static_dir(app)
    add_deferred_js_file(app, "docstrap-common.js")
    app.add_css_file("docstrap.css")
    register_project_slug_config(app)
    app._docstrap_common_registered = True  # type: ignore[attr-defined]


def register_tool_assets(app, declaration: ToolDeclaration) -> None:
    """Register one tool's client source, named from its declaration.

    The build never spells a bundle filename: it asks the declaration
    for :attr:`~docstrap.tools.declaration.ToolDeclaration.js_bundle`
    and :attr:`~docstrap.tools.declaration.ToolDeclaration.css_bundle`
    and registers whichever of them the tool directory actually ships.
    A tool with no styles of its own simply has no CSS file. The script
    is deferred to the viewer (:func:`add_deferred_js_file`).
    """
    add_common_asset(app)
    static_dir = registry.static_directory(declaration)
    register_static_dir(app, static_dir)
    if (static_dir / declaration.js_bundle).is_file():
        add_deferred_js_file(app, declaration.js_bundle)
    if (static_dir / declaration.css_bundle).is_file():
        app.add_css_file(declaration.css_bundle)


# --- per-page metadata ------------------------------------------------------


def is_aggregate_build(app) -> bool:
    """Whether this Sphinx run composes an aggregate rather than a project.

    A store's landing page and the super-aggregate above it list the
    projects a build produced. **They are not projects**, which is why
    :func:`docstrap.layouts.markdown.write_conf_py` gives them no
    ``project_slug``, and the one thing that distinguishes them from a
    project build in the generated conf.py is that they carry an
    aggregate model.

    That distinction is needed because "no declared slug" has two quite
    different causes — an aggregate, which has no project, and a site
    built from someone's own conf.py, which has one that docstrap never
    scanned — and only the second is a case for guessing.
    """
    from docstrap.sphinx.composed import CONF_AGGREGATE

    return bool(getattr(app.config, CONF_AGGREGATE, None))


def _load_config_for_pagename(app, pagename: str) -> Optional[dict[str, Any]]:
    """Best-effort per-page context: project slug + source path.

    Returns a dict with at least ``project`` and ``source_path`` keys,
    or None if the pagename can't be resolved to a real source file.

    ``project`` is the project's SLUG, never its title. A docstrap-built
    site carries the scanned slug in :data:`PROJECT_SLUG_CONFIG` and it
    is used verbatim.

    **An aggregate page gets no project at all.** It belongs to none —
    it lists them — so there is nothing to address and nothing to offer
    a project-targeted tool. Falling back to the title there invented
    ``fleet-queue`` out of the heading "Fleet queue", which named no
    store, no directory and no draft root; launching the Q&A panels
    from a store's own front page asked the server for that project's
    questions and got a 404 dressed as "is `docstrap serve` running?".
    A slug that addresses nothing is worse than no slug, because no slug
    is a thing the launcher already knows how to handle: it offers
    nothing that needs one (:class:`docstrap.tools.launcher.PageContext`).

    A site built from someone's own conf.py is the remaining case with no
    declared slug, and it *does* have a project — docstrap simply never
    scanned it. There the title (or the srcdir name) is slugified through
    :func:`docstrap.slugs.slugify`: best effort, but at least it is the
    same normalisation everything else uses.
    """
    try:
        doc_source = app.env.doc2path(pagename)
    except Exception:  # noqa: BLE001 — env may not have this pagename
        return None
    if not doc_source:
        return None
    source_path = str(Path(doc_source).resolve())
    declared = getattr(app.config, PROJECT_SLUG_CONFIG, "") or ""
    if declared:
        project = declared
    elif is_aggregate_build(app):
        project = ""
    else:
        title = getattr(app.config, "project", "") or os.path.basename(app.srcdir)
        project = slugify(title) if title else ""
    return {
        "project": project,
        "source_path": source_path,
        "doc_slug": pagename,
    }


def _lookup_doc_id(source_path: str) -> Optional[str]:
    """Look up the docstrap metadata document ID for a source file path.

    Returns None if metadata DB isn't reachable or the file isn't
    registered. Tools degrade gracefully when no ID is available.
    """
    try:
        from docstrap import metadata

        doc = metadata.get_document_by_path(source_path)
        return doc.id if doc else None
    except Exception:  # noqa: BLE001 — DB missing or unopenable
        return None


def page_context(app, pagename: str) -> PageContext:
    """The launcher's view of a page: what workpieces are available here.

    A page whose source can't be resolved has neither, so the launcher
    offers nothing on it.
    """
    ctx = _load_config_for_pagename(app, pagename)
    if ctx is None:
        return PageContext()
    return PageContext(project=ctx["project"] or None, doc_slug=ctx["doc_slug"] or None)


def inject_page_metatags(app, pagename: str, context: dict[str, Any]) -> None:
    """Inject docstrap-* meta tags into the page's <head>.

    Called from html-page-context in each tool's setup, but the
    metatags are cumulative — if two tools both call this, the tags
    appear only once because each check is guarded on presence.
    """
    ctx = _load_config_for_pagename(app, pagename)
    if ctx is None:
        return

    existing = context.get("metatags") or ""
    additions: list[str] = []

    project = html.escape(ctx["project"], quote=True)
    doc_slug = html.escape(ctx["doc_slug"], quote=True)
    source_path = html.escape(ctx["source_path"], quote=True)

    if 'name="docstrap-project"' not in existing:
        additions.append(f'<meta name="docstrap-project" content="{project}">')
    if 'name="docstrap-doc-slug"' not in existing:
        additions.append(f'<meta name="docstrap-doc-slug" content="{doc_slug}">')
    if 'name="docstrap-source-path"' not in existing:
        additions.append(f'<meta name="docstrap-source-path" content="{source_path}">')

    doc_id = _lookup_doc_id(ctx["source_path"])
    if doc_id and 'name="docstrap-doc-id"' not in existing:
        did = html.escape(doc_id, quote=True)
        additions.append(f'<meta name="docstrap-doc-id" content="{did}">')

    if additions:
        context["metatags"] = existing + "\n" + "\n".join(additions) + "\n"
