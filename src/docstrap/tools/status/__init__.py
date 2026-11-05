"""The status badge tool — Sphinx entry point.

Injects the ``docstrap-*`` meta tags and this tool's client source. The
client fetches ``GET /api/documents/<id>/state`` on page load and
inserts a small badge near the page title when the tool is showing.
Degrades silently if the docstrap app server isn't running or the
document isn't registered.

Everything belonging to this tool is in this directory: the declaration
next door, the client source under ``static/``. It owns no server
routes — see ``declaration.py`` for why.
"""
from __future__ import annotations

from typing import Any

from docstrap.sphinx.tool_support import inject_page_metatags, register_tool_assets
from docstrap.tools.status.declaration import DECLARATION


def _on_html_page_context(
    app,
    pagename: str,
    templatename: str,
    context: dict[str, Any],
    doctree,
) -> None:
    """Inject docstrap-* meta tags into every rendered page's <head>."""
    inject_page_metatags(app, pagename, context)


def setup(app):
    """Sphinx entry point."""
    register_tool_assets(app, DECLARATION)
    app.connect("html-page-context", _on_html_page_context)
    return {
        "version": "0.1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
