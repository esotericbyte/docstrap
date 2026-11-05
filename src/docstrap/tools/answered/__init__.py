"""The answered/open marker — Sphinx entry point.

A reader of a question document
could not tell an answered question from an open one, could not see the
answer, and had no link to the store. This is
where that is corrected, and it is corrected **without writing into the
document**: nothing is altered in place, and that stays true here.

**Anchored at build, resolved at serve.** Two halves, and the split is
the whole design.

The build half is this module. It marks each `Q<n>` block in the
**rendered doctree** with a class naming its label, so the derivative
HTML says where its questions are. Nothing is added to the page and
nothing is written to the source; a class on a paragraph of the output
is a rendering fact about the derivative, exactly as a heading anchor
is.

The serve half is the client bundle. It reads
``/api/answers/{project}/{doc_slug}`` — the server's answers API,
live — and hangs each question's current answer off the block the
build marked. Baking answers into the HTML instead was rejected:
answers change constantly and the document does not rebuild when they
do, and a *stale* decision shown as current is worse in a decision
system than no decision shown at all.

**Which blocks get marked is not decided here.** :mod:`docstrap.questions`
owns the three rules, and this asks it: :func:`questions.find` for the
document's authoritative set — the last ascending run, so a superseded
earlier run is left alone exactly as ``docstrap questions`` leaves it —
and :func:`questions.label_of` to recognise the same label in rendered
text, where the author's ``**`` are gone. A second labelling rule here
is precisely what the one-owner rules exist to prevent.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from docutils import nodes

from docstrap import questions
from docstrap.sphinx.tool_support import inject_page_metatags, register_tool_assets
from docstrap.tools.answered.declaration import DECLARATION

#: On every marked block, so a stylesheet and a client can find them all.
BLOCK_CLASS = "docstrap-question"


def label_class(label: str) -> str:
    """The per-label class. ``Q1`` → ``docstrap-question-q1``.

    docutils lowercases and normalises class names, so the client reads
    the label back in lower case and the two agree by construction.
    """
    return f"{BLOCK_CLASS}-{label.lower()}"


def _mark(doctree: nodes.document, wanted: frozenset[str]) -> int:
    """Class each block that opens one of ``wanted``. Returns how many.

    The block is whatever docutils made of the item — a paragraph for a
    plain ``**Q1.** …``, a list item for a bulleted or task-list one. The
    outermost of those is marked, so the client has one element per
    question to hang an answer after.
    """
    marked = 0
    seen: set[str] = set()
    for node in doctree.findall(nodes.Element):
        if not isinstance(node, (nodes.paragraph, nodes.list_item)):
            continue
        text = node.astext().strip()
        if not text:
            continue
        label = questions.label_of(text.splitlines()[0])
        if label is None or label not in wanted or label in seen:
            continue
        # A paragraph inside an already-marked list item is the same
        # question seen twice; `seen` keeps the outer one, which is the
        # one findall reaches first.
        seen.add(label)
        classes = node.setdefault("classes", [])
        for name in (BLOCK_CLASS, label_class(label)):
            if name not in classes:
                classes.append(name)
        marked += 1
    return marked


def _on_doctree_read(app, doctree: nodes.document) -> None:
    """Mark this document's questions, if it has any."""
    source = doctree.get("source")
    if not source:
        return
    path = Path(source)
    if not path.is_file():
        return
    try:
        found = questions.find(path)
    except (OSError, UnicodeDecodeError):
        # A source docstrap cannot read is a source with no questions as
        # far as this tool is concerned. The page still builds.
        return
    if not found.questions:
        return
    _mark(doctree, frozenset(q.label for q in found.questions))


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
    app.connect("doctree-read", _on_doctree_read)
    app.connect("html-page-context", _on_html_page_context)
    return {
        "version": "0.1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
