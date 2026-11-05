"""Sphinx extension: a published page's way into the viewer.

Not a tool — the tools are what it holds back. A page opened on its own
is the document and one small button; every tool script on it is
registered inert (:data:`~docstrap.sphinx.tool_support.DEFERRED_SCRIPT_TYPE`),
so no Svelte runtime is fetched until a reader asks for the viewer.
Pressing the button replaces the page with the viewer shell showing this
same page, and inside the shell's frame the same script runs the tools
and draws no button.

Two halves, and the decision is split between them deliberately:

* **Here, at build time**, the address. A page knows where it sits below
  its own build, and :func:`docstrap.build` tells the build where that
  sits below the site the shell is published at
  (:data:`VIEWER_BASE_CONFIG`). The address is composed in Python from
  the same :func:`~docstrap.viewer.manifest.page_url` the manifest lists
  the page by, so the shell is handed a page it knows. A page with no
  shell above it carries no address and gets no button.
* **In the browser**, the state. ``docstrap-viewer-button.js`` decides
  whether the page is inside a frame, marks the root element with that,
  and either draws the button or turns the deferred tools on. The
  stylesheet shows the button only under the top-level mark, so it
  cannot appear in a frame even before the script has run.
"""
from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from docstrap.sphinx.tool_support import add_common_asset, register_static_dir
from docstrap.viewer import manifest as viewer

#: The conf.py value: this build's output directory below the site root
#: the viewer shell is published at, as ``store/project/`` (or ``''``),
#: or None when no shell is published above it. Written by
#: :func:`docstrap.layouts.markdown.write_conf_py`.
VIEWER_BASE_CONFIG = "docstrap_viewer_base"

_STATIC_DIR = Path(__file__).parent / "static"


def meta_tag(base: str, pagename: str) -> str:
    """The head tag carrying this page's address in the viewer."""
    href = html.escape(viewer.open_in_viewer_href(base, pagename), quote=True)
    return f'<meta name="{viewer.OPEN_IN_VIEWER_META}" content="{href}">'


def _on_html_page_context(
    app,
    pagename: str,
    templatename: str,
    context: dict[str, Any],
    doctree,
) -> None:
    base = getattr(app.config, VIEWER_BASE_CONFIG, None)
    if base is None:
        return
    existing = context.get("metatags") or ""
    # The whole attribute, not the bare name: another tag's content — a
    # source path, say — may contain the name and is not this tag.
    if f'name="{viewer.OPEN_IN_VIEWER_META}"' in existing:
        return
    context["metatags"] = existing + "\n" + meta_tag(base, pagename) + "\n"


def setup(app):
    """Sphinx entry point."""
    add_common_asset(app)
    register_static_dir(app, _STATIC_DIR)
    app.add_config_value(VIEWER_BASE_CONFIG, None, "html")
    app.add_js_file("docstrap-viewer-button.js")
    app.add_css_file("docstrap-viewer-button.css")
    app.connect("html-page-context", _on_html_page_context)
    return {
        "version": "0.1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
