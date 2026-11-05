"""Sphinx extension: the single visibility launcher.

Not a tool — it is the control tools declare themselves to, so it has
no declaration and discovery skips it. It does two things: registers
its own client source, and serialises this page's offer list into the
page so the client renders what the declarations decided.

The offer list is computed in :mod:`docstrap.tools.launcher` from each
tool's kind and target against the page's context. Doing it here rather
than in the browser keeps the rule that the launcher offers only what
is valid where the person is in one testable place, and
means a page that offers nothing carries no offer list at all.

Registered last in the generated ``extensions`` list so every tool has
registered its assets before this one adds its own.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from docstrap.sphinx import tool_support
from docstrap.sphinx.tool_support import (
    add_common_asset,
    add_deferred_js_file,
    register_static_dir,
)
from docstrap.tools.launcher import PageContext, offers_for, offers_json

# The id the client looks the offer list up by. One name, shared with
# docstrap-common.js.
OFFERS_ELEMENT_ID = "docstrap-tool-offers"

_STATIC_DIR = Path(__file__).parent / "static"


def offers_script_tag(context_: PageContext) -> str:
    """The ``<script type="application/json">`` carrying this page's offers.

    Empty string when nothing is offerable here, so a page with no
    workpiece carries no launcher payload at all.
    """
    declarations = offers_for(context_)
    if not declarations:
        return ""
    payload = offers_json(context_)
    # A JSON payload in a script element only needs the closing-tag
    # sequence neutralised; JSON has no other way out of the element.
    safe = payload.replace("</", "<\\/")
    return (
        f'<script type="application/json" id="{OFFERS_ELEMENT_ID}">'
        f"{safe}</script>"
    )


def _on_html_page_context(
    app,
    pagename: str,
    templatename: str,
    context: dict[str, Any],
    doctree,
) -> None:
    """Serialise the offer list for this page into its <head>."""
    page = tool_support.page_context(app, pagename)
    tag = offers_script_tag(page)
    if not tag:
        return
    existing = context.get("metatags") or ""
    if OFFERS_ELEMENT_ID in existing:
        return
    context["metatags"] = existing + "\n" + tag + "\n"


def setup(app):
    """Sphinx entry point."""
    add_common_asset(app)
    register_static_dir(app, _STATIC_DIR)
    add_deferred_js_file(app, "docstrap-launcher.js")
    app.add_css_file("docstrap-launcher.css")
    app.connect("html-page-context", _on_html_page_context)
    return {
        "version": "0.1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }


__all__ = ["OFFERS_ELEMENT_ID", "offers_script_tag", "setup", "PageContext"]
