"""The task tool — Sphinx entry point.

Everything belonging to this tool is in this directory: the declaration,
the task file's reader in ``spec.py``, the ``docstrap-tasks`` directive in
``views.py``, how a decision is keyed in the answer store in
``decisions.py``, the decisions route in ``routes.py``, and the client
source under ``ui/``.

The directive renders the tasks as a plain table grouped by project at
build time, so a page opened on its own — which runs no tool — still reads. Inside the viewer
the client takes it over: grouping by project or status, drilling into a
group with the drill kept in the address, sorting, filtering, and one
decision per task.
"""
from __future__ import annotations

from typing import Any

from docstrap.sphinx.tool_support import inject_page_metatags, register_tool_assets
from docstrap.tools.tasks.declaration import DECLARATION
from docstrap.tools.tasks.views import DocstrapTasksDirective


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
    app.add_directive("docstrap-tasks", DocstrapTasksDirective)
    app.connect("html-page-context", _on_html_page_context)
    return {
        "version": "0.1.0",
        # The directive's HTML is pickled into each page's doctree, and a
        # build re-reads only a page whose source or task file changed. So
        # a change to what `views.render` writes bumps this: Sphinx then
        # discards an existing build's environment and every page showing
        # tasks is rendered again. 2: column keys and wrappers for the
        # shared column layout.
        "env_version": 3,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
