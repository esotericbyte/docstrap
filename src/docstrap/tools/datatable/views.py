"""The datatable tool's view: the ``docstrap-datatable`` directive.

The directive names a JSON file beside the page — the format is in
``spec.py`` — and renders it where the author put the directive::

    ```{docstrap-datatable} census.json
    ```

What comes out is two things in one wrapper. A plain HTML table, which is
the document: it reads on a page opened on its own, in print, and with no
script at all. And the same table as data, in a
``<script type="application/json">``, which the client reads to draw the
sortable, filterable version inside the viewer. Nothing is fetched.

A link cell's target is resolved here, at build time. A target naming a
document — ``tasks/fm-12``, relative to this page, with or without its
suffix — becomes that document's built URL, so the file never has to know
how the site spells a page; a document the build does not have is warned
about and shown unlinked. A target with a scheme, or starting with ``/``
or ``#``, is used as written.
"""
from __future__ import annotations

import html
import json
import posixpath
import re
from pathlib import Path
from typing import Any

from docutils import nodes
from sphinx.util import logging
from sphinx.util.docutils import SphinxDirective

from docstrap.tools.datatable import spec

logger = logging.getLogger(__name__)

#: A target the build leaves alone: one with a scheme, or a site path, or
#: an anchor on this page.
_AS_WRITTEN = re.compile(r"^(?:[a-zA-Z][a-zA-Z0-9+.-]*:|/|#)")

WRAPPER_CLASS = "docstrap-datatable"
DATA_CLASS = "docstrap-datatable-data"
STATIC_CLASS = "docstrap-datatable-static"


def display(value: Any, symbols: dict[str, str] | None = None) -> str:
    """A cell as text, through a symbol column's map when given one.

    ``ui/table.ts`` ``cellText`` is the same rule; a test holds the two
    to the same outputs.
    """
    if value is None:
        return ""
    if isinstance(value, list):
        separator = " " if symbols is not None else ", "
        return separator.join(display(v, symbols) for v in value)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float) and value.is_integer():
        # JSON has one number type; `2.0` reads back as `2` in the client.
        value = int(value)
    text = str(value)
    if symbols is not None:
        return symbols.get(text, text)
    return text


def script_json(payload: Any) -> str:
    """JSON that cannot end the ``<script>`` element it is written into."""
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def render(table: spec.Table, links: list[dict[str, str]]) -> str:
    """The wrapper, the data, and the plain table, as HTML.

    ``links`` is one mapping per row from a link column's key to the URL
    its cell goes to; a cell missing from it is shown unlinked.
    """
    payload = {
        "columns": [column.to_payload() for column in table.columns],
        "rows": [
            {
                "cells": {c.key: row.get(c.key) for c in table.columns},
                "links": row_links,
            }
            for row, row_links in zip(table.rows, links)
        ],
    }

    head = "".join(
        f'<th class="head" data-type="{c.type}">{html.escape(c.label)}</th>'
        for c in table.columns
    )
    body = []
    for row, row_links in zip(table.rows, links):
        cells = []
        for column in table.columns:
            value = row.get(column.key)
            text = html.escape(display(value, column.symbols))
            if column.type == "link" and column.key in row_links:
                href = html.escape(row_links[column.key], quote=True)
                text = f'<a class="reference" href="{href}">{text}</a>'
            elif column.type == "symbol" and value is not None:
                title = html.escape(display(value), quote=True)
                text = f'<span title="{title}">{text}</span>'
            cells.append(f"<td>{text}</td>")
        body.append(f"<tr>{''.join(cells)}</tr>")

    return (
        f'<div class="{WRAPPER_CLASS}">'
        f'<script type="application/json" class="{DATA_CLASS}">'
        f"{script_json(payload)}</script>"
        f'<div class="{STATIC_CLASS} table-wrapper">'
        f'<table class="docutils align-default">'
        f"<thead><tr>{head}</tr></thead>"
        f"<tbody>{''.join(body)}</tbody>"
        f"</table></div></div>"
    )


def resolve_target(directive: SphinxDirective, target: str, name: str) -> str | None:
    """The URL a link target goes to from the directive's page, or None.

    ``name`` is the directive's own, for the warning a target naming no
    document gets. The task tool resolves its task pages through this
    too, so the two say the same thing about the same target.
    """
    if _AS_WRITTEN.match(target):
        return target
    path, _, anchor = target.partition("#")
    for suffix in directive.config.source_suffix:
        if path.endswith(suffix):
            path = path[: -len(suffix)]
            break
    here = directive.env.docname
    docname = posixpath.normpath(posixpath.join(posixpath.dirname(here), path))
    if docname not in directive.env.found_docs:
        logger.warning(
            "%s: link target %r names no document in this build",
            name,
            target,
            location=(here, directive.lineno),
        )
        return None
    uri = directive.env.app.builder.get_relative_uri(here, docname)
    return f"{uri}#{anchor}" if anchor else uri


class DocstrapDatatableDirective(SphinxDirective):
    """Render a JSON table file as a table the datatable tool enhances."""

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec: dict[str, Any] = {}

    def run(self) -> list[nodes.Node]:
        argument = self.arguments[0]
        relative, absolute = self.env.relfn2path(argument)
        # A change to the table file rebuilds the page that shows it.
        self.env.note_dependency(relative)
        try:
            table = spec.load(Path(absolute))
        except spec.TableError as exc:
            raise self.error(f"docstrap-datatable {argument}: {exc}") from exc

        links = [self._links(row, table) for row in table.rows]
        return [nodes.raw("", render(table, links), format="html")]

    def _links(self, row: dict[str, Any], table: spec.Table) -> dict[str, str]:
        resolved: dict[str, str] = {}
        for column in table.columns:
            if column.type != "link":
                continue
            target = row.get(column.href or column.key)
            if not isinstance(target, str) or not target:
                continue
            url = resolve_target(self, target, "docstrap-datatable")
            if url is not None:
                resolved[column.key] = url
        return resolved
