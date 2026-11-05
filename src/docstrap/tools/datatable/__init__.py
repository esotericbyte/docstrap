"""The data table tool — Sphinx entry point.

Everything belonging to this tool is in this directory: the declaration,
the table file's reader in ``spec.py``, the ``docstrap-datatable``
directive in ``views.py``, and the client source under ``ui/``.

The directive renders the table as plain HTML at build time, so a page
opened on its own — which runs no tool — still reads as the document its author wrote. Inside the viewer
the client takes that table over and adds sorting and filtering.
"""
from __future__ import annotations

from typing import Any

from docstrap.sphinx.tool_support import inject_page_metatags, register_tool_assets
from docstrap.tools.datatable.declaration import DECLARATION
from docstrap.tools.datatable.views import DocstrapDatatableDirective


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
    app.add_directive("docstrap-datatable", DocstrapDatatableDirective)
    app.connect("html-page-context", _on_html_page_context)
    return {
        "version": "0.1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
