"""A document below `docs_root` is reachable, and its identity is its path.

The defect this closes was silent, wrong about its own cause, and applied
to almost every page anybody actually reads. A document's identity is its
path below the project's `docs_root` with the suffix dropped —
`proposals/0002-the-upgrade-path` — which is what
:meth:`docstrap.projectscope.ProjectScope.document_slug` returns and what
the rendered page carries in its `docstrap-doc-slug` meta tag. Every
document-targeted route spelled that identity as a single segment, the
launcher percent-encoded the separator into `%2F`, nothing matched, and
the panel said `is docstrap serve running?` while the server was running
and answering. Across six built projects in a real multi-project site,
666 of 686 pages are nested; 20 are not.

**Why the tests that existed could not see it.**
`test_tool_declarations.py` compares the server's route table against the
templates the declarations derive — template against template, never
filled in. So this file fills them in, with a real nested document, and
drives the real `make_app` router. Nothing here asserts about a template.

Two things are held, and the second is as important as the first:

1. A nested document reaches the handler meant for it, through every
   document-targeted route there is — the qapanels document read, the
   server's `/api/answers` read, the qa tool's write and the review
   tool's write. The report's table had those at 404, 404, 405 and 405.
2. The project-level endpoints are NOT captured by the now-greedy
   document parameter. That separation used to hold by accident of
   segment counts; making the parameter carry a path is precisely what
   `tools/qapanels/routes.py` warned would reopen the ambiguity, so it
   is asserted here against the real matcher rather than argued for.

The loop is closed end to end: the URL the LAUNCHER resolves from the
declaration for a nested page is the URL fed to the router. A fix that
repaired only one end would pass half of this file.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from starlette.routing import Match

from docstrap import projectscope, user_config
from docstrap.config import load
from docstrap.scan import ScannedProject, scan
from docstrap.server import make_app
from docstrap.tools import registry
from docstrap.tools.launcher import PageContext, resolve_alt_route, resolve_route

PROJECT_PATH = "packages/thing"
PROJECT_SLUG = "packages__thing"

#: The nested document. Two levels below `docs_root`, so a fix that only
#: handled one extra segment is not enough either.
NESTED_SLUG = "proposals/drafts/0002-the-upgrade-path"
ROOT_SLUG = "spec"

DOCSTRAP_YAML = f"""\
version: 1
title: A Store
projects:
  - path: {PROJECT_PATH}
    title: The Thing
    layout: markdown
    sources:
      - path: docs
        role: documentation
      - path: drafts
        role: draft
"""

SPEC = """\
# The thing

## Open questions

**Q1.** Which storage layout?
"""

NESTED = """\
# The upgrade path

## Open questions

**Q1.** Does an existing database ever gain a column?

**Q2.** Who stamps the promdance store?
"""


@pytest.fixture
def project(tmp_path: Path, user_dirs: Path) -> ScannedProject:
    """A project with one document at its root and one two levels down."""
    store = tmp_path / "store"
    docs = store / PROJECT_PATH / "docs"
    (docs / "proposals" / "drafts").mkdir(parents=True)
    (docs / "spec.md").write_text(SPEC, encoding="utf-8")
    (docs / "proposals" / "drafts" / "0002-the-upgrade-path.md").write_text(
        NESTED, encoding="utf-8"
    )
    (store / PROJECT_PATH / "drafts").mkdir()
    (store / ".docstrap").write_text(DOCSTRAP_YAML, encoding="utf-8")
    user_config.add_store(store / ".docstrap")
    scanned = [p for p in scan(load(store / ".docstrap")) if p.kind == "project"]
    return scanned[0]


def _match(path: str, method: str = "GET"):
    """The handler `make_app` reaches for this path, and its path params.

    The real router, the real app. `AssertionError` when nothing matches,
    which is what a 404 from a running server looked like from the
    browser.
    """
    app = make_app(Path("/nonexistent-site-root"))
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": [],
        "path_params": {},
        "root_path": "",
    }
    for route in app.router.routes:
        matched, child = route.matches(scope)
        if matched is Match.FULL:
            return route.endpoint, child["path_params"]
    raise AssertionError(f"no route matched {method} {path}")


def _matches(path: str, method: str = "GET") -> bool:
    try:
        _match(path, method)
    except AssertionError:
        return False
    return True


# --- the identity itself ----------------------------------------------------


def test_a_nested_document_is_named_by_its_path(project: ScannedProject):
    """`document_slug` returns the path, and `document_for_slug` takes it.

    Recorded here because everything below rests on it: the identity was
    never the thing that was wrong, and it is not being changed.
    """
    scope = projectscope.resolve_slug(PROJECT_SLUG)
    source = scope.docs_dir / "proposals" / "drafts" / "0002-the-upgrade-path.md"
    assert scope.document_slug(source) == NESTED_SLUG
    assert scope.document_for_slug(NESTED_SLUG) == source


@pytest.mark.parametrize(
    "malformed",
    ["", "/leading", "trailing/", "a//b", "a/../b", ".", "a\\b", " a/b "],
)
def test_a_shape_no_document_has_resolves_to_nothing(
    project: ScannedProject, malformed: str
):
    """A greedy path parameter catches shapes a slug never has.

    `projectscope` owns what a document identity is, so it owns which
    shapes are not one. Not a security boundary — resolution compares
    against the project's own documents and composes no path — but a
    malformed identity gets a clean no rather than an accidental one.
    """
    assert not projectscope.is_document_slug(malformed)
    scope = projectscope.resolve_slug(PROJECT_SLUG)
    assert scope.document_for_slug(malformed) is None


def test_the_nested_slug_is_a_document_slug():
    assert projectscope.is_document_slug(NESTED_SLUG)
    assert projectscope.is_document_slug(ROOT_SLUG)


# --- the launcher resolves a path, not a flattened segment ------------------


def test_the_launcher_hands_the_browser_a_path(project: ScannedProject):
    """Where the `%2F` came from. It must not come back.

    The declaration is filled in for a real nested page here, which is
    the step `test_tool_declarations.py` never takes.
    """
    context = PageContext(project=PROJECT_SLUG, doc_slug=NESTED_SLUG)
    qa_url = resolve_route(registry.get("qa"), context)
    panel_url = resolve_alt_route(registry.get("qapanels"), context)

    assert qa_url == f"/api/tools/{PROJECT_SLUG}/{NESTED_SLUG}/answers"
    assert panel_url == f"/api/tools/{PROJECT_SLUG}/{NESTED_SLUG}/qa"
    for url in (qa_url, panel_url):
        assert "%2F" not in url


# --- every document-targeted route, filled in with a real nested document ---


def test_the_panels_read_a_nested_document(project: ScannedProject):
    """`GET …/{project}/{doc_slug}/qa` — 404 before, and an empty panel."""
    context = PageContext(project=PROJECT_SLUG, doc_slug=NESTED_SLUG)
    url = resolve_alt_route(registry.get("qapanels"), context)
    assert url is not None

    handler, params = _match(url)
    assert params["doc_slug"] == NESTED_SLUG

    body = handler(**params)
    assert [d["docSlug"] for d in body["documents"]] == [NESTED_SLUG]
    assert [q["label"] for q in body["documents"][0]["questions"]] == ["Q1", "Q2"]
    assert body["count"] == 2


def test_the_answers_api_reads_a_nested_document(project: ScannedProject):
    """`GET /api/answers/{project}/{doc_slug}` — the `answered` tool's read.

    This one fires on every page load with nothing launched, so a nested
    document simply showed no answers under any question, silently.
    """
    handler, params = _match(f"/api/answers/{PROJECT_SLUG}/{NESTED_SLUG}")
    assert params["doc_slug"] == NESTED_SLUG

    body = handler(**params)
    assert body["docSlug"] == NESTED_SLUG
    assert {q["label"] for q in body["questions"]} == {"Q1", "Q2"}


def test_the_qa_tool_can_submit_against_a_nested_document(project: ScannedProject):
    """`POST …/{project}/{doc_slug}/answers` — 405 before.

    Answering a question in a nested document through the on-page form
    was not possible at all.
    """
    from docstrap.tools.qa.routes import AnswerSubmission

    context = PageContext(project=PROJECT_SLUG, doc_slug=NESTED_SLUG)
    url = resolve_route(registry.get("qa"), context)
    assert url is not None

    handler, params = _match(url, method="POST")
    assert params["doc_slug"] == NESTED_SLUG

    result = handler(
        **params,
        payload=AnswerSubmission(
            question_id="Q1",
            question="Does an existing database ever gain a column?",
            answer="No. A table is safe; a column is not.",
        ),
    )
    assert result["question_id"] == "Q1"
    assert result["submitted"] is True
    # It delivered too: the addendum beside a nested document is named
    # from the flattened slug, because a filename is one segment — the
    # identity itself is untouched.
    assert result["addendum"] is not None
    assert Path(result["addendum"]["path"]).name == (
        "proposals__drafts__0002-the-upgrade-path__answers.md"
    )

    # And it is readable back through the document-scoped read, which is
    # the half of the loop a route fix could otherwise leave broken.
    read, read_params = _match(f"/api/answers/{PROJECT_SLUG}/{NESTED_SLUG}")
    answered = read(**read_params)
    q1 = next(q for q in answered["questions"] if q["label"] == "Q1")
    assert q1["answer"] == "No. A table is safe; a column is not."


def test_the_review_tool_can_submit_against_a_nested_document(
    project: ScannedProject,
):
    """`POST …/{project}/{doc_slug}/reviews` — 405 before.

    The identity is recorded as the path it is; only the FILENAME the
    review lands under is flattened, because a filename is one segment.
    """
    from docstrap.tools.review.routes import ReviewSubmission

    context = PageContext(project=PROJECT_SLUG, doc_slug=NESTED_SLUG)
    url = resolve_route(registry.get("review"), context)
    assert url is not None

    handler, params = _match(url, method="POST")
    assert params["doc_slug"] == NESTED_SLUG

    result = handler(
        **params,
        payload=ReviewSubmission(sentence_marks=[], section_marks=[]),
    )
    written = Path(result["written_to"])
    assert written.is_file()
    # The filename is flattened through the one slugifier, because a
    # filename is one segment. What it RECORDS is the identity itself.
    assert written.name.startswith("proposals__drafts__0002-the-upgrade-path_review-")
    assert f"reviewed_doc: {NESTED_SLUG}" in written.read_text(encoding="utf-8")


# --- the separation the greedy parameter had to earn back -------------------


def test_the_project_scope_is_not_captured_by_the_document_scope(
    project: ScannedProject,
):
    """`…/{project}/qa` reaches the project read, not the document one.

    The collision `tools/qapanels/routes.py` describes. A greedy
    `{doc_slug}` makes the two mutually capturable in principle; they
    stay apart because a project URL has exactly one segment after the
    project and a document URL has two or more, and because no route
    reaches deeper than a base plus its collection
    (`declaration.check_route_separation`).
    """
    from docstrap.tools.qapanels import routes as panel_routes

    project_handler, project_params = _match(f"/api/tools/{PROJECT_SLUG}/qa")
    document_handler, document_params = _match(
        f"/api/tools/{PROJECT_SLUG}/{NESTED_SLUG}/qa"
    )

    assert project_params == {"project": PROJECT_SLUG}
    assert "doc_slug" not in project_params
    assert document_params["doc_slug"] == NESTED_SLUG
    assert project_handler is not document_handler
    assert project_handler.__name__ == "list_questions"
    assert document_handler.__name__ == "list_document_questions"
    assert panel_routes.register is not None  # the module under test, named

    # And they answer differently: the project read spans both documents.
    both = project_handler(**project_params)
    assert {d["docSlug"] for d in both["documents"]} == {ROOT_SLUG, NESTED_SLUG}
    one = document_handler(**document_params)
    assert {d["docSlug"] for d in one["documents"]} == {NESTED_SLUG}


def test_the_project_write_is_not_captured_either(project: ScannedProject):
    """`POST …/{project}/qa` is the panel's one writer and stays so."""
    handler, params = _match(f"/api/tools/{PROJECT_SLUG}/qa", method="POST")
    assert params == {"project": PROJECT_SLUG}
    assert handler.__name__ == "submit_answer"


def test_the_project_answers_read_is_not_captured_either(project: ScannedProject):
    """`/api/answers/{project}` keeps reaching the project-wide read.

    `{project}` is one segment, so a two-segment URL cannot reach it and
    a one-segment URL cannot reach the document read below it.
    """
    handler, params = _match(f"/api/answers/{PROJECT_SLUG}")
    assert params == {"project": PROJECT_SLUG}
    assert handler.__name__ == "list_answers"


def test_a_document_named_like_a_collection_still_reaches_its_own_route(
    project: ScannedProject,
):
    """The worst case the ambiguity produces, pinned.

    A document whose slug is literally `qa` gives `…/{project}/qa/answers`
    — which is exactly the sub-path under the project base that
    `check_route_separation` forbids any tool from mounting. Because none
    does, the URL is unambiguously the qa tool's document write, and the
    project's own `…/{project}/qa` is untouched.
    """
    handler, params = _match(
        f"/api/tools/{PROJECT_SLUG}/qa/answers", method="POST"
    )
    assert params == {"project": PROJECT_SLUG, "doc_slug": "qa"}
    assert handler.__name__ == "submit_answer"

    panel_handler, panel_params = _match(f"/api/tools/{PROJECT_SLUG}/qa")
    assert panel_params == {"project": PROJECT_SLUG}
    assert panel_handler.__name__ == "list_questions"


def test_nothing_reaches_deeper_than_a_base_plus_its_collection():
    """No tool route has a sub-path, so the two scopes cannot overlap."""
    from docstrap.tools import mounting
    from docstrap.tools.declaration import check_route_separation

    check_route_separation(
        prefix
        for prefixes in mounting.declared_server_route_prefixes().values()
        for prefix in prefixes
    )


def test_an_unknown_nested_slug_is_a_404_and_not_a_match_failure(
    project: ScannedProject,
):
    """A route that matches and a document that exists are two questions.

    The route now matches any path shape, so "this project declares no
    such document" has to be answered by the handler. It is, and as a
    404 rather than an empty listing that would read as "this document
    poses no questions".
    """
    from fastapi import HTTPException

    handler, params = _match(f"/api/tools/{PROJECT_SLUG}/proposals/nope/qa")
    assert params["doc_slug"] == "proposals/nope"
    with pytest.raises(HTTPException) as raised:
        handler(**params)
    assert raised.value.status_code == 404


def test_the_root_level_document_did_not_regress(project: ScannedProject):
    """The 3 % that always worked still does."""
    assert _matches(f"/api/tools/{PROJECT_SLUG}/{ROOT_SLUG}/qa")
    assert _matches(f"/api/answers/{PROJECT_SLUG}/{ROOT_SLUG}")
    assert _matches(f"/api/tools/{PROJECT_SLUG}/{ROOT_SLUG}/answers", "POST")
    assert _matches(f"/api/tools/{PROJECT_SLUG}/{ROOT_SLUG}/reviews", "POST")
