"""The launcher offers only what is valid where the person is standing.

Synthetic declarations rather than the real three, because the rule
under test is about kind and target in general and should not be
provable only for the tools that happen to exist today.
"""
from __future__ import annotations

import json

import pytest

from docstrap.sphinx.launcher import OFFERS_ELEMENT_ID, offers_script_tag
from docstrap.tools.declaration import Kind, Target, ToolDeclaration
from docstrap.tools.launcher import (
    PageContext,
    is_valid_here,
    offer_payload,
    offers_for,
    offers_json,
    resolve_route,
)

DOC_TOOL = ToolDeclaration(
    id="doctool",
    title="Doc tool",
    kind=Kind.TOOL,
    target=Target.DOCUMENT,
    entry="fake.doctool",
    api_collection="notes",
)
PROJECT_TOOL = ToolDeclaration(
    id="projtool",
    title="Project tool",
    kind=Kind.TOOL,
    target=Target.PROJECT,
    entry="fake.projtool",
    api_collection="rollup",
)
DOC_INSTRUMENT = ToolDeclaration(
    id="docinst",
    title="Doc instrument",
    kind=Kind.INSTRUMENT,
    target=Target.DOCUMENT,
    entry="fake.docinst",
)
PROJECT_INSTRUMENT = ToolDeclaration(
    id="classifier",
    title="Classifier",
    kind=Kind.INSTRUMENT,
    target=Target.PROJECT,
    entry="fake.classifier",
)
ALL = (DOC_TOOL, PROJECT_TOOL, DOC_INSTRUMENT, PROJECT_INSTRUMENT)

ON_A_DOCUMENT = PageContext(project="Docs", doc_slug="notes/a")
LONE_PAGE = PageContext(project=None, doc_slug="notes/a")
PROJECT_ONLY = PageContext(project="Docs", doc_slug=None)
NOWHERE = PageContext()


def ids(declarations) -> list[str]:
    return [d.id for d in declarations]


def test_a_document_page_offers_everything_targeted_at_a_document():
    offered = ids(offers_for(ON_A_DOCUMENT, ALL))
    assert "doctool" in offered
    assert "docinst" in offered


def test_a_project_targeted_instrument_never_appears_on_a_lone_page():
    """No project to act on, so the classifier is not offered."""
    offered = ids(offers_for(LONE_PAGE, ALL))
    assert "classifier" not in offered
    assert "projtool" not in offered


def test_a_project_page_offers_project_targets_but_not_document_ones():
    offered = ids(offers_for(PROJECT_ONLY, ALL))
    assert offered == ["projtool", "classifier"]


def test_a_page_with_no_workpiece_offers_nothing():
    assert offers_for(NOWHERE, ALL) == ()


def test_a_document_inside_a_project_offers_project_targets_too():
    """There is a project to act on here, so a project target is valid."""
    assert "classifier" in ids(offers_for(ON_A_DOCUMENT, ALL))


def test_tools_are_offered_before_instruments():
    """A tool acts on the page you are reading; an instrument takes you off it."""
    offered = ids(offers_for(ON_A_DOCUMENT, ALL))
    assert offered == ["doctool", "projtool", "docinst", "classifier"]


@pytest.mark.parametrize(
    "declaration,context,expected",
    [
        (DOC_TOOL, ON_A_DOCUMENT, True),
        (DOC_TOOL, PROJECT_ONLY, False),
        (PROJECT_TOOL, PROJECT_ONLY, True),
        (PROJECT_TOOL, NOWHERE, False),
        (PROJECT_INSTRUMENT, ON_A_DOCUMENT, True),
        (PROJECT_INSTRUMENT, LONE_PAGE, False),
    ],
)
def test_validity_rule(declaration, context, expected):
    assert is_valid_here(declaration, context) is expected


# --- what the client is handed ---------------------------------------------


def test_the_client_is_handed_a_resolved_url_not_a_template():
    """A tool never assembles a path; the declaration's is filled in here."""
    assert resolve_route(DOC_TOOL, ON_A_DOCUMENT) == "/api/tools/Docs/notes/a/notes"
    assert resolve_route(PROJECT_TOOL, PROJECT_ONLY) == "/api/tools/Docs/rollup"


def test_a_nested_document_keeps_its_separators_in_the_url():
    """The document identity is a PATH, and the URL spells it as one.

    This is the defect the whole path-aware change exists to fix. The
    slug was percent-encoded whole, so `proposals/0002-the-upgrade-path`
    went out as `proposals%2F0002-the-upgrade-path`, matched no route,
    and every document-targeted tool 404ed on every document below a
    project's `docs_root` — which is 666 of 686 pages in a real
    multi-project site. The panel then blamed the server, which was running.
    """
    deep = PageContext(project="packages__docstrap", doc_slug="proposals/0002-the-upgrade-path")
    assert resolve_route(DOC_TOOL, deep) == (
        "/api/tools/packages__docstrap/proposals/0002-the-upgrade-path/notes"
    )
    assert "%2F" not in (resolve_route(DOC_TOOL, deep) or "")


def test_everything_but_the_separator_is_still_escaped():
    """`/` is safe because it is the identity; nothing else is.

    A slug is not trusted to be URL-clean just because it may contain a
    separator — a directory with a space or a `#` in its name still has
    to survive the trip.
    """
    odd = PageContext(project="Docs", doc_slug="design notes/a#b")
    assert resolve_route(DOC_TOOL, odd) == "/api/tools/Docs/design%20notes/a%23b/notes"


def test_the_project_slug_is_still_one_segment():
    """A project slug is one segment, so its separators are not its own."""
    weird = PageContext(project="a/b", doc_slug="x")
    assert resolve_route(DOC_TOOL, weird) == "/api/tools/a%2Fb/x/notes"


def test_a_tool_with_no_collection_resolves_to_no_url():
    assert resolve_route(DOC_INSTRUMENT, ON_A_DOCUMENT) is None
    assert offer_payload(DOC_INSTRUMENT, ON_A_DOCUMENT)["route"] is None


def test_the_offer_carries_kind_target_and_visibility_class():
    payload = offer_payload(DOC_TOOL, ON_A_DOCUMENT)
    assert payload["kind"] == "tool"
    assert payload["target"] == "document"
    assert payload["visibilityClass"] == "docstrap-show-doctool"


def test_offers_json_is_parseable_and_ordered():
    parsed = json.loads(offers_json(ON_A_DOCUMENT, ALL))
    assert [entry["id"] for entry in parsed] == [
        "doctool",
        "projtool",
        "docinst",
        "classifier",
    ]


# --- the script tag the page carries ---------------------------------------


def test_the_script_tag_is_json_the_client_can_read():
    tag = offers_script_tag(PageContext(project="Docs", doc_slug="index"))
    assert OFFERS_ELEMENT_ID in tag
    body = tag.split(">", 1)[1].rsplit("<", 1)[0]
    parsed = json.loads(body.replace("<\\/", "</"))
    assert {entry["id"] for entry in parsed} >= {"status", "review", "qa"}


def test_a_page_with_no_workpiece_carries_no_payload_at_all():
    assert offers_script_tag(PageContext()) == ""
