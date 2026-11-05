"""The inline question tool — Sphinx entry point.

Everything belonging to this tool is in this directory: the
declaration, the ``docstrap-questions`` directive in ``views.py``, the
answers endpoint in ``routes.py``, and the client source under
``static/``.
"""
from __future__ import annotations

from typing import Any

from docstrap.sphinx.tool_support import inject_page_metatags, register_tool_assets
from docstrap.tools.qa.declaration import DECLARATION
from docstrap.tools.qa.views import DocstrapQuestionsDirective


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
    app.add_directive("docstrap-questions", DocstrapQuestionsDirective)
    app.connect("html-page-context", _on_html_page_context)
    return {
        "version": "0.1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
