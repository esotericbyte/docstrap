"""Which page has a project, and which page only looks like it has one.

A store's landing page lists the projects a build produced. It is not one
of them. The build knows that and says so — `write_conf_py` gives an
aggregate no `project_slug` — but `tool_support` then filled the hole by
slugifying Sphinx's `project`, which is a human-readable TITLE. A real
site's front page carried
`<meta name="docstrap-project" content="fleet-queue">`, derived from the
heading "Fleet queue". There is no `fleet-queue` store, no `fleet-queue`
directory and no `fleet-queue` promdance entry; launching the Q&A panels
there asked the server for that project's questions, got a 404, and
reported it as `is docstrap serve running?`.

A slug that addresses nothing is worse than no slug, because no slug is a
case the launcher already handles correctly: it offers nothing that needs
a project (`docstrap.tools.launcher.is_valid_here`). This is the same
class of defect `slugs.py`'s docstring describes as having once orphaned
submitted answers — surviving in the one place a slug was invented from a
title rather than read.

What is NOT removed is the fallback itself. A site built from somebody's
own `conf.py` has a real project that docstrap simply never scanned, and
guessing a name for it is the best that can be done there. The two cases
are told apart by the aggregate model the generated `conf.py` carries,
which is the one thing an aggregate build has and a project build does
not.

Nor is an explicit context removed. A page that binds a real project and
a real document — temporary, on the fly, or built from a repository — is
a context like any other and is offered for accordingly; that is the case
at the bottom of this file, and it is the Q&A browsing and answering use
case working.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from docstrap.sphinx import tool_support
from docstrap.sphinx.composed import CONF_AGGREGATE
from docstrap.sphinx.tool_support import PROJECT_SLUG_CONFIG
from docstrap.tools.launcher import offers_for


class FakeEnv:
    def __init__(self, source: Path) -> None:
        self._source = source

    def doc2path(self, pagename: str) -> str:
        return str(self._source)


class FakeApp:
    """Just enough Sphinx for the per-page context to be computed.

    The real `page_context` reads three things off the application: the
    environment's source path for the page, the declared project slug,
    and the aggregate model. Standing those up directly keeps the test
    about the decision rather than about Sphinx.
    """

    def __init__(self, tmp_path: Path, *, slug: str = "", aggregate=None, title: str):
        source = tmp_path / "index.md"
        source.write_text("# A page\n", encoding="utf-8")
        self.env = FakeEnv(source)
        self.srcdir = str(tmp_path)
        self.config = type(
            "Config",
            (),
            {
                PROJECT_SLUG_CONFIG: slug,
                CONF_AGGREGATE: aggregate,
                "project": title,
            },
        )()


# --- the aggregate has no project, and is given none ------------------------


def test_an_aggregate_page_invents_no_project(tmp_path: Path):
    """`fleet-queue`, and why it must not come back."""
    app = FakeApp(tmp_path, slug="", aggregate={"stores": []}, title="Fleet queue")
    context = tool_support.page_context(app, "index")
    assert context.project is None
    assert not context.has_project
    assert not context.has_document


def test_an_aggregate_page_offers_nothing(tmp_path: Path):
    """With no project there is no workpiece, and the rule already knows it.

    Project-targeted apparatus and document-targeted apparatus alike are
    withheld — which is the honest answer on a page that lists projects
    rather than being one.
    """
    app = FakeApp(tmp_path, slug="", aggregate={"stores": []}, title="Fleet queue")
    assert offers_for(tool_support.page_context(app, "index")) == ()


def test_the_aggregate_meta_tag_names_no_project(tmp_path: Path):
    """What the browser reads. The tools read this, not the config."""
    app = FakeApp(tmp_path, slug="", aggregate={"stores": []}, title="Fleet queue")
    context: dict = {}
    tool_support.inject_page_metatags(app, "index", context)
    assert '<meta name="docstrap-project" content="">' in context["metatags"]
    assert "fleet-queue" not in context["metatags"]


def test_an_aggregate_is_recognised_by_its_model_not_its_missing_slug(
    tmp_path: Path,
):
    """The distinction the repair turns on.

    "No declared slug" has two causes and only one of them is a case for
    guessing. The aggregate model is what a store's landing page has and
    a project build does not.
    """
    aggregate = FakeApp(tmp_path, aggregate={"stores": []}, title="Fleet queue")
    foreign = FakeApp(tmp_path, aggregate=None, title="Fleet queue")
    assert tool_support.is_aggregate_build(aggregate)
    assert not tool_support.is_aggregate_build(foreign)


# --- what is deliberately NOT changed ---------------------------------------


def test_a_foreign_sphinx_site_still_gets_a_best_effort_slug(tmp_path: Path):
    """Someone's own conf.py has a project; docstrap just never scanned it.

    Removing this would take the tools off every non-docstrap Sphinx site
    that loads them, which is a different change and not this one.
    """
    app = FakeApp(tmp_path, slug="", aggregate=None, title="Some Project")
    assert tool_support.page_context(app, "index").project == "some-project"


def test_a_scanned_project_slug_is_used_verbatim(tmp_path: Path):
    """A declared slug wins over everything, aggregate model or not."""
    app = FakeApp(
        tmp_path, slug="packages__docstrap", aggregate=None, title="Docstrap"
    )
    assert tool_support.page_context(app, "index").project == "packages__docstrap"


# --- an explicitly bound context is a context ------------------------------


def test_a_bound_project_and_document_is_offered_for(tmp_path: Path):
    """The Q&A use case, on a page whose context was handed to it.

    A document need not be a permanent fixture of a repository to be
    answerable — what makes it a workpiece is that a real project and a
    real document identity are bound to the page. A nested identity is
    the ordinary case, so that is the one asserted.
    """
    app = FakeApp(
        tmp_path, slug="packages__docstrap", aggregate=None, title="Docstrap"
    )
    context = tool_support.page_context(app, "proposals/0002-the-upgrade-path")
    assert context.project == "packages__docstrap"
    assert context.doc_slug == "proposals/0002-the-upgrade-path"
    assert context.has_document

    offered = {d.id for d in offers_for(context)}
    assert {"qa", "answered", "qapanels"} <= offered


@pytest.mark.parametrize("pagename", ["spec", "proposals/0002-the-upgrade-path"])
def test_the_doc_slug_is_the_pagename_whatever_its_depth(
    tmp_path: Path, pagename: str
):
    """Sphinx's docname IS the identity, at any depth. Nothing flattens it."""
    app = FakeApp(tmp_path, slug="proj", aggregate=None, title="Proj")
    assert tool_support.page_context(app, pagename).doc_slug == pagename
