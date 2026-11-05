"""The answers API: what is answered, without parsing markdown.

`/api/promdance/answers` once returned 404, and a consumer of a decision
had no way to reach one.

Routes are reached through Starlette's own matcher against the real
`make_app`, the way `test_answers.py` reaches the tool routes: a handler
reached here is the handler the server would reach, and no URL in this
file is written for its own sake. The over-the-wire half — a caller that
is not the browser, speaking HTTP, parsing no markdown — is demonstrated
against a real running `docstrap serve`, which is what `curl` in the
step's commit message records.

Two properties beyond the endpoint existing, and both matter more than
it does:

1. It shows **no draft, ever**. The Finish button decides what an
   audience sees, and a consumer reading this is that audience.
2. It is the **same pairing** the instrument's panel serialises — one
   scan-and-match in `docstrap.pairing`, two projections — so the browser and
   a consumer cannot come to disagree about what a project has decided.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import HTTPException
from starlette.routing import Match

from docstrap import pairing, user_config
from docstrap.config import load
from docstrap.scan import ScannedProject, scan
from docstrap.server import make_app
from docstrap.tools import mounting, registry
from docstrap.tools.qapanels.routes import AnswerSubmission
from docstrap.tools.qapanels.routes import _listing as panel_listing

PROJECT_PATH = "packages/thing"
PROJECT_SLUG = "packages__thing"

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

**Q2.** Who owns the name?
"""

NOTE = """\
# A note

## Open questions

**Q1.** Is this the same Q1 as the spec's?
"""


@pytest.fixture
def project(tmp_path: Path, user_dirs: Path) -> ScannedProject:
    store = tmp_path / "store"
    docs = store / PROJECT_PATH / "docs"
    docs.mkdir(parents=True)
    (docs / "spec.md").write_text(SPEC, encoding="utf-8")
    (docs / "note.md").write_text(NOTE, encoding="utf-8")
    (store / PROJECT_PATH / "drafts").mkdir()
    (store / ".docstrap").write_text(DOCSTRAP_YAML, encoding="utf-8")
    user_config.add_store(store / ".docstrap")
    scanned = [p for p in scan(load(store / ".docstrap")) if p.kind == "project"]
    return scanned[0]


def _resolve(path: str, method: str = "GET"):
    """The handler `make_app` would reach for this path, and its params."""
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
        match, child = route.matches(scope)
        if match is Match.FULL:
            return route.endpoint, child["path_params"]
    raise AssertionError(f"no route matched {method} {path}")


def _get(path: str, **query):
    """Call the answers API as a consumer would, through the real app."""
    handler, params = _resolve(path)
    return handler(**params, **query)


def _json(path: str, **query) -> str:
    """The response body as a consumer would receive it — JSON text.

    Asserting against this is how "no draft reached the API" is checked:
    a field-by-field check can only rule out the fields it thought of.
    """
    return json.dumps(_get(path, **query))


def _spec_q1(body: dict) -> dict:
    """The spec's Q1. Both documents pose one, which is the point of keying
    on the document id and is exactly the mistake a label-only lookup makes."""
    return next(
        q
        for q in body["questions"]
        if q["label"] == "Q1" and q["docSlug"] == "spec"
    )


def _write(label: str, answer: str, *, submitted: bool, doc_slug: str = "spec"):
    """Answer through the panel's own endpoint, as a person would."""
    from fastapi import FastAPI

    app = FastAPI()
    mounting.mount_all(app)
    prefix = registry.get("qapanels").route_prefix
    assert prefix is not None
    url = prefix.format(project=PROJECT_SLUG)
    scope = {
        "type": "http",
        "method": "POST",
        "path": url,
        "headers": [],
        "path_params": {},
        "root_path": "",
    }
    for route in app.router.routes:
        match, child = route.matches(scope)
        if match is Match.FULL:
            return route.endpoint(
                **child["path_params"],
                payload=AnswerSubmission(
                    doc_slug=doc_slug,
                    label=label,
                    answer=answer,
                    submitted=submitted,
                ),
            )
    raise AssertionError("the panel's write endpoint is not mounted")


# --- the endpoint exists and answers the question it was asked --------------


def test_a_caller_can_ask_what_is_answered_without_parsing_markdown(
    project: ScannedProject,
):
    """The step's proof. Nothing in here opens the store file."""
    _write("Q1", "Flat files, keyed by document id.", submitted=True)

    body = _get(f"/api/answers/{PROJECT_SLUG}")

    assert body["project"] == PROJECT_SLUG
    assert body["count"] == 3 and body["answered"] == 1 and body["open"] == 2

    answered = [q for q in body["questions"] if q["answered"]]
    assert len(answered) == 1
    q1 = answered[0]
    # The pair: the question as its author wrote it, and the answer.
    assert q1["label"] == "Q1"
    assert q1["question"] == "Which storage layout?"
    assert q1["document"] == "docs/spec.md"
    assert q1["answer"] == "Flat files, keyed by document id."
    assert q1["key"] == f"{q1['docId']}:Q1"
    assert q1["submittedAt"] and q1["answeredAt"]


def test_the_answers_api_is_the_servers_and_not_a_tools(project: ScannedProject):
    """It is reachable without knowing which tool happens to exist.

    `/api/answers/...` is not under `/api/tools/{project}/...`, which
    is where a tool's collection lives. A consumer of decisions should no
    more need to know about the qapanels instrument than a consumer of
    metadata needs to know about the status badge.
    """
    handler, params = _resolve(f"/api/answers/{PROJECT_SLUG}")
    assert handler.__module__.endswith("docstrap.server")
    assert params == {"project": PROJECT_SLUG}

    declared = {
        prefix
        for prefixes in mounting.declared_route_prefixes().values()
        for prefix in prefixes
    }
    assert not any(p.startswith("/api/answers") for p in declared)


def test_an_unknown_project_is_404_rather_than_an_empty_answer(
    project: ScannedProject,
):
    handler, params = _resolve("/api/answers/no-such-project")
    with pytest.raises(HTTPException) as raised:
        handler(**params)
    assert raised.value.status_code == 404


def test_a_document_slug_the_project_does_not_declare_is_404(
    project: ScannedProject,
):
    handler, params = _resolve(f"/api/answers/{PROJECT_SLUG}/nope")
    with pytest.raises(HTTPException) as raised:
        handler(**params)
    assert raised.value.status_code == 404


def test_the_document_scope_narrows_to_that_document(project: ScannedProject):
    _write("Q1", "The spec's.", submitted=True)
    _write("Q1", "The note's.", submitted=True, doc_slug="note")

    spec = _get(f"/api/answers/{PROJECT_SLUG}/spec")
    note = _get(f"/api/answers/{PROJECT_SLUG}/note")

    assert spec["docSlug"] == "spec" and note["docSlug"] == "note"
    assert {q["document"] for q in spec["questions"]} == {"docs/spec.md"}
    assert {q["document"] for q in note["questions"]} == {"docs/note.md"}
    assert spec["count"] == 2 and note["count"] == 1
    # Two documents' Q1s are two questions, and the API keeps them apart.
    spec_q1 = next(q for q in spec["questions"] if q["label"] == "Q1")
    note_q1 = next(q for q in note["questions"] if q["label"] == "Q1")
    assert spec_q1["answer"] == "The spec's."
    assert note_q1["answer"] == "The note's."
    assert spec_q1["key"] != note_q1["key"]


@pytest.mark.parametrize(
    "include,expected", [("all", 3), ("answered", 1), ("open", 2)]
)
def test_include_selects_which_questions_come_back(
    project: ScannedProject, include: str, expected: int
):
    _write("Q1", "Flat files.", submitted=True)
    body = _get(f"/api/answers/{PROJECT_SLUG}", include=include)
    assert body["include"] == include
    assert len(body["questions"]) == expected
    # The counts describe the project either way, not the filtered slice.
    assert body["count"] == 3 and body["answered"] == 1 and body["open"] == 2


def test_an_unknown_include_is_rejected_rather_than_ignored(
    project: ScannedProject,
):
    handler, params = _resolve(f"/api/answers/{PROJECT_SLUG}")
    with pytest.raises(HTTPException) as raised:
        handler(**params, include="maybe")
    assert raised.value.status_code == 400
    assert "include must be one of" in raised.value.detail


# --- no draft, ever ---------------------------------------------------------


def test_a_draft_is_invisible_to_this_endpoint(project: ScannedProject):
    """The Finish button decides what an audience sees, and this is one.

    Not the text, and not the fact that one exists: an answer nobody has
    finished is not a decision, and showing unfinished writing to an
    audience its author has not shown it to is the reverse of what the
    submit distinction is for.
    """
    _write("Q1", "NO! It should not be a", submitted=False)

    body = _get(f"/api/answers/{PROJECT_SLUG}")
    q1 = _spec_q1(body)
    assert q1["answered"] is False
    assert q1["answer"] == ""
    assert q1["answeredAt"] is None and q1["submittedAt"] is None
    assert body["answered"] == 0 and body["open"] == 3
    assert "NO!" not in _json(f"/api/answers/{PROJECT_SLUG}")

    # Restricting to what is answered returns nothing, not the draft.
    answered = _get(f"/api/answers/{PROJECT_SLUG}", include="answered")
    assert answered["questions"] == []


def test_a_revision_in_flight_does_not_disturb_the_published_answer(
    project: ScannedProject,
):
    """A submitted answer stays visible while its author retypes it."""
    _write("Q1", "Yes.", submitted=True)
    _write("Q1", "No, and here is w", submitted=False)

    body = _get(f"/api/answers/{PROJECT_SLUG}")
    q1 = _spec_q1(body)
    assert q1["answered"] is True
    assert q1["answer"] == "Yes."
    assert "here is w" not in _json(f"/api/answers/{PROJECT_SLUG}")


def test_a_superseded_answer_is_counted_but_not_republished(
    project: ScannedProject,
):
    _write("Q1", "The slug is the address.", submitted=True)
    _write("Q1", "The document id is the address.", submitted=True)

    body = _get(f"/api/answers/{PROJECT_SLUG}")
    q1 = _spec_q1(body)
    assert q1["answer"] == "The document id is the address."
    assert q1["superseded"] == 1, "the earlier one is kept; the API says so"
    assert "The slug is the address." not in _json(f"/api/answers/{PROJECT_SLUG}")


# --- one pairing, two projections -------------------------------------------


def test_the_api_and_the_panel_read_one_pairing(project: ScannedProject):
    """A second scan-and-match is what the single-owner rules prevent.

    They project it differently — that is deliberate and is the two tests
    above — but the questions they see, in the order they see them, and
    the answers they attach, all come from `docstrap.pairing.pair`.
    """
    _write("Q1", "Flat files.", submitted=True)
    _write("Q2", "A draft of who owns it", submitted=False)

    api = _get(f"/api/answers/{PROJECT_SLUG}")
    panel = panel_listing(PROJECT_SLUG)

    api_labels = [(q["docSlug"], q["label"]) for q in api["questions"]]
    panel_labels = [
        (doc["docSlug"], q["label"])
        for doc in panel["documents"]
        for q in doc["questions"]
    ]
    assert api_labels == panel_labels
    assert api["count"] == panel["count"]
    assert api["open"] == panel["open"]

    # And where they differ, they differ in exactly one way: the panel
    # hands a writer their draft back and the API does not.
    panel_q2 = next(
        q
        for doc in panel["documents"]
        for q in doc["questions"]
        if q["label"] == "Q2"
    )
    api_q2 = next(q for q in api["questions"] if q["label"] == "Q2")
    assert panel_q2["answer"] == "A draft of who owns it"
    assert api_q2["answer"] == ""


def test_the_pairing_introduces_no_index(project: ScannedProject):
    """It is a scan, per call, derived and disposable.

    Adding a
    question to a document changes the next pairing with nothing told.
    """
    assert pairing.pair(PROJECT_SLUG).count == 3

    note = project.docs_dir / "note.md"
    note.write_text(NOTE + "\n**Q2.** And a second one?\n", encoding="utf-8")

    after = pairing.pair(PROJECT_SLUG)
    assert after.count == 4
    assert [p.question.label for p in after.pairs if p.doc_slug == "note"] == [
        "Q1",
        "Q2",
    ]


def test_pairing_does_not_register_a_document_in_the_metadata_store(
    project: ScannedProject,
):
    """Reading is not answering."""
    paired = pairing.pair(PROJECT_SLUG)
    assert all(p.doc_id is None for p in paired.pairs)
    assert all(p.key is None for p in paired.pairs)
    assert all(p.is_open for p in paired.pairs)
