"""The three-panel Q&A instrument — Sphinx entry point.

Everything belonging to this instrument is in this directory: the declaration, the question and
answer endpoints in ``routes.py``, the Svelte source under ``ui/`` and
the built bundle under ``static/``. It contributes no directive — the
questions it lists are the author's own ``Q<n>`` items, read from the
source documents, so there is nothing for an author to place on a page.
"""
from __future__ import annotations

from typing import Any

from docstrap.sphinx.tool_support import inject_page_metatags, register_tool_assets
from docstrap.tools.qapanels.declaration import DECLARATION


def _on_html_page_context(
    app,
    pagename: str,
    templatename: str,
    context: dict[str, Any],
    doctree,
) -> None:
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
