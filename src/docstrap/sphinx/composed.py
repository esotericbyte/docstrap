"""Pages docstrap composes, built as document nodes and never as markdown.

A section page, a project's landing page and a store's aggregate page are
all pages docstrap decides rather than pages somebody wrote. Until 0.0.3
each of them was emitted as markdown that Sphinx then parsed back. That
step is gone: the output is HTML, so no markdown is kept for an index. An
intermediate that exists only to be converted is not earning its place, and the one docstrap had
is the same artefact that leaked into five repositories.

So there is no markdown here, and no markdown anywhere in a build. A
composed page is assembled directly as a docutils document — a section, a
title, a :class:`sphinx.addnodes.toctree` — and Sphinx renders it to HTML
with the rest of the site, in the site's theme, in the site's sidebar,
with the site's previous/next links.

## How a page with no source becomes a Sphinx document

Sphinx reads its documents from files: ``Builder.read_doc`` is ``@final``
and its first act is ``env.doc2path(docname).read_text()``. There is no
supported way to hand it a document that is not on disk, and the
unsupported ways all reach into private state — ``env._pickled_doctree_
cache``, a ``Project`` subclass rewriting the docname-to-path bijection,
a ``Path`` subclass whose ``read_text`` lies. Each was considered and
each buys a zero-file build at the price of a tool that breaks on a
Sphinx point release.

What is supported is choosing the *parser*. So a composed page is a
**zero-byte marker** — `index.docstrap-section` — in the build's scratch
tree, mapped by ``source_suffix`` to a parser that ignores the (empty)
content entirely and composes the document from
:func:`docstrap.sectionindex.compose`, which reads the file index. The
marker carries no index, cannot go stale, cannot be mistaken for a
document, and exists only inside a build. Nothing is converted from one
format to another and nothing markdown-shaped is written at any stage.

The one cost: a build's scratch tree holds one empty marker per section.

## The project's own landing page

One case. The scratch root gets the same zero-byte marker as any section
and the page is composed whole.

There used to be a second — a project that had written its own
`index.md`, whose file Sphinx read and whose doctree the navigation was
appended to on ``doctree-read``. The case was removed rather than the
code path: a documentation tree holds no index.md at all, so a build
never meets one, and :mod:`docstrap.layouts.markdown` does not mirror one
into the build if a tree still has it.
"""
from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from docutils import nodes
from docutils.parsers import Parser

from sphinx import addnodes

from docstrap import sectionindex

if TYPE_CHECKING:
    from pathlib import Path

    from sphinx.application import Sphinx

#: The suffix a composed page's marker takes, and the filetype that
#: suffix maps to. Deliberately not `.docstrap` — a store's config file
#: is named that, and a docs tree is allowed to contain one.
MARKER_SUFFIX = ".docstrap-section"
SECTION_FILETYPE = "docstrap-section"

#: The aggregate pages of `docstrap.build` — a store's landing page and
#: the super-aggregate above it — are composed the same way but from a
#: different model, so they get a filetype of their own.
AGGREGATE_MARKER_SUFFIX = ".docstrap-aggregate"
AGGREGATE_FILETYPE = "docstrap-aggregate"

#: The marker's filename. The docname it produces is `<dir>/index`, which
#: is the name a parent's listing points at.
MARKER_NAME = f"index{MARKER_SUFFIX}"
AGGREGATE_MARKER_NAME = f"index{AGGREGATE_MARKER_SUFFIX}"

#: conf.py values a composed build carries. The project slug is already
#: written for the tools and is reused here.
CONF_INDEX_DB = "docstrap_index_db"
CONF_PROJECT_SLUG = "docstrap_project_slug"
CONF_ROOT_NOTE = "docstrap_root_note"
CONF_AGGREGATE = "docstrap_aggregate"


# Markers are created by :func:`docstrap.layouts.markdown.write_marker`,
# which routes the write through the guard that refuses any destination
# outside the build. This module only names them.


# --- the node level ---------------------------------------------------------


def toctree_node(
    docname: str,
    caption: str,
    entries: list[str],
    *,
    maxdepth: int = 2,
) -> addnodes.toctree:
    """A toctree, built rather than parsed.

    Every key the directive would have set is set here explicitly.
    Sphinx's toctree resolution reads them by name and a missing one is
    a ``KeyError`` deep inside the writer, so none is left to a default.
    """
    node = addnodes.toctree()
    node["parent"] = docname
    node["entries"] = [(None, entry) for entry in entries]
    node["includefiles"] = list(entries)
    node["maxdepth"] = maxdepth
    node["caption"] = caption
    node["rawcaption"] = caption
    node["glob"] = False
    node["hidden"] = False
    node["includehidden"] = False
    node["numbered"] = 0
    node["titlesonly"] = False
    return node


def _emphasis_paragraph(text: str) -> nodes.paragraph:
    paragraph = nodes.paragraph()
    paragraph += nodes.emphasis(text=text)
    return paragraph


def section_page_nodes(page: sectionindex.SectionPage) -> list[nodes.Node]:
    """The body of a composed page: its listings, or a note that it has none.

    Returned as a list so the caller decides whether it hangs off a
    section of its own (a page composed whole) or is appended to a
    document somebody wrote (the landing-page case).
    """
    body: list[nodes.Node] = []
    for caption, entries in page.groups:
        if not entries:
            continue
        body.append(
            toctree_node(page.docname, caption, [e.docname for e in entries])
        )
    if not body:
        body.append(_emphasis_paragraph("(no documents in this section)"))
    return body


def _titled_section(docname: str, title: str, body: list[nodes.Node]) -> nodes.section:
    section = nodes.section(ids=[nodes.make_id(docname or title)])
    section["names"] = [nodes.fully_normalize_name(title)]
    section += nodes.title(text=title)
    section.extend(body)
    return section


# --- the parsers ------------------------------------------------------------


class _ComposedParser(Parser):
    """Shared plumbing: find the docname, ignore the (empty) input."""

    def _docname(self, document: nodes.document) -> str:
        return document.settings.env.current_document.docname

    def _config(self, document: nodes.document):
        return document.settings.env.config


class SectionPageParser(_ComposedParser):
    """A section page, or a project's landing page when it wrote none."""

    supported = (SECTION_FILETYPE,)

    def parse(self, inputstring: str, document: nodes.document) -> None:
        config = self._config(document)
        docname = self._docname(document)
        project = getattr(config, CONF_PROJECT_SLUG, "") or ""
        db_path = _db_path(config)

        page = sectionindex.compose(project, docname, db_path)
        body: list[nodes.Node] = []
        note = getattr(config, CONF_ROOT_NOTE, "") or ""
        if note and docname == sectionindex.GENERATED_INDEX_NAME:
            body.append(_emphasis_paragraph(note))
        body.extend(section_page_nodes(page))
        document += _titled_section(docname, page.title, body)


class AggregatePageParser(_ComposedParser):
    """A store's landing page, or the super-aggregate above every store.

    Its model is not the file index — an aggregate lists *builds*, which
    only the run that just performed them knows about — so it arrives
    through :data:`CONF_AGGREGATE` in the generated conf.py, which is
    already generated Python and already carries the project slug. That
    keeps the "no file for a composed page" rule whole: the aggregate
    needs no source of its own either.
    """

    supported = (AGGREGATE_FILETYPE,)

    def parse(self, inputstring: str, document: nodes.document) -> None:
        model = getattr(self._config(document), CONF_AGGREGATE, None) or {}
        if isinstance(model, str):
            model = json.loads(model)
        document += _aggregate_section(model)


def _aggregate_section(model: dict[str, Any]) -> nodes.section:
    """Compose an aggregate page from the model the build handed over.

    ``model`` is ``{title, short, blocks}``; a block is ``{heading,
    short, lead, links, notes}`` and every piece is optional. Links are
    raw HTML anchors rather than references, for the same reason the
    markdown version used raw anchors: a docstrap site's cross-project
    links point at built `index.html` files that are not documents of
    this Sphinx run, and a resolved reference to one is not a link.
    """
    body: list[nodes.Node] = []
    if model.get("short"):
        body.append(_emphasis_paragraph(model["short"]))
    if model.get("raw_html"):
        body.append(nodes.raw("", model["raw_html"], format="html"))

    for block in model.get("blocks", ()):
        inner: list[nodes.Node] = []
        if block.get("short"):
            inner.append(_emphasis_paragraph(block["short"]))
        if block.get("lead"):
            inner.append(nodes.raw("", block["lead"], format="html"))
        if block.get("links"):
            items = nodes.bullet_list()
            for link in block["links"]:
                item = nodes.list_item()
                item += nodes.raw("", link, format="html")
                items += item
            inner.append(items)
        for note in block.get("notes", ()):
            inner.append(_emphasis_paragraph(note))
        body.append(
            _titled_section(
                nodes.make_id(block.get("heading", "")), block.get("heading", ""), inner
            )
        )

    return _titled_section("index", model.get("title", "Docstrap"), body)


def _db_path(config) -> Path | None:
    from pathlib import Path as _Path

    raw = getattr(config, CONF_INDEX_DB, "") or ""
    return _Path(raw) if raw else None


def setup(app: Sphinx) -> dict[str, Any]:
    from docstrap.sphinx.tool_support import register_project_slug_config

    register_project_slug_config(app)
    app.add_config_value(CONF_INDEX_DB, "", "env", types=(str,))
    app.add_config_value(CONF_ROOT_NOTE, "", "env", types=(str,))
    app.add_config_value(CONF_AGGREGATE, None, "env")
    app.add_source_parser(SectionPageParser)
    app.add_source_parser(AggregatePageParser)
    return {
        "version": "0.0.4",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
