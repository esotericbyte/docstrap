"""What the loop delivers.

Ten real decisions were stored and nothing was produced — no addendum, no version,
no artifact anyone would cite.

The step's proof is two clauses, and they are the two tests under "the
proof" below: **answering a question produces something a person can
cite, and the document's version reflects that it was answered.**

Everything here goes through the mounted write route rather than calling
`addendum.deliver` directly, because the thing being tested is that
*answering* delivers. A delivery that only happens when a test asks for
it is the defect, not the repair.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from starlette.routing import Match

from docstrap import addendum, answers, pairing, user_config
from docstrap.config import load
from docstrap.scan import ScannedProject, scan
from docstrap.tools import mounting, registry
from docstrap.tools.qapanels.routes import AnswerSubmission

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
    return [p for p in scan(load(store / ".docstrap")) if p.kind == "project"][0]


def _post(label: str, answer: str, *, submitted: bool, doc_slug: str = "spec") -> dict:
    """Answer through the instrument's own mounted write route."""
    app = FastAPI()
    mounting.mount_all(app)
    prefix = registry.get("qapanels").route_prefix
    assert prefix is not None
    scope = {
        "type": "http",
        "method": "POST",
        "path": prefix.format(project=PROJECT_SLUG),
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
    raise AssertionError("the write endpoint is not mounted")


# --- the proof ---------------------------------------------------------------


def test_answering_a_question_produces_something_a_person_can_cite(
    project: ScannedProject,
):
    """The first clause. A file, at a path, with the decision in it."""
    result = _post("Q1", "Flat files, keyed by document id.", submitted=True)

    delivered = result["addendum"]
    assert delivered is not None, "a submission that delivered nothing"

    path = Path(delivered["path"])
    assert path.is_file(), "the citation points at something"
    text = path.read_text(encoding="utf-8")

    # What a person citing it gets: the question, the answer, the key it
    # hangs on, and when it was decided.
    assert "Which storage layout?" in text
    assert "Flat files, keyed by document id." in text
    assert delivered["docId"] and f"{delivered['docId']}:Q1" in text
    assert delivered["generatedAt"] in text

    # And the open one, because half of what a reader needs is what is
    # still undecided.
    assert "Who owns the name?" in text
    assert "**Open.** No answer has been submitted." in text
    assert delivered["answered"] == 1 and delivered["open"] == 1


def test_the_documents_version_reflects_that_it_was_answered(
    project: ScannedProject,
):
    """The second clause, and the property alpha's contract stamp needs.

    The version moves when an answer moves and at no other time.
    """
    first = _post("Q1", "Flat files.", submitted=True)["addendum"]
    assert first["version"]

    # Regenerating with nothing changed does not move it. A version that
    # churned on every write would tell a consumer a decision changed
    # when it had not.
    again = addendum.deliver(PROJECT_SLUG, "spec")
    assert again.version == first["version"]

    # A draft against the same question does not move it either: nothing
    # has been decided, and a draft delivers nothing at all.
    drafted = _post("Q1", "Actually, maybe not flat", submitted=False)
    assert drafted["addendum"] is None
    assert addendum.deliver(PROJECT_SLUG, "spec").version == first["version"]

    # Answering the OTHER question moves it.
    second = _post("Q2", "docstrap.slugs, and nothing else.", submitted=True)["addendum"]
    assert second["version"] != first["version"]
    assert second["answered"] == 2 and second["open"] == 0

    # And revising an existing answer moves it again.
    third = _post("Q1", "Flat files, keyed by document id.", submitted=True)["addendum"]
    assert third["version"] != second["version"]


def test_pressing_finish_again_on_unedited_text_does_not_move_the_version(
    project: ScannedProject,
):
    """Re-affirming a decision is not making a new one.

    Found by a real run against `docstrap serve`, not by a test: the
    version had the submission time in it, so clicking Finish twice moved
    it and a consumer would have re-stamped a contract for nothing. The
    store already treats this as a non-event — it supersedes nothing —
    and now the version agrees with the store.
    """
    first = _post("Q1", "Flat files.", submitted=True)["addendum"]
    again = _post("Q1", "Flat files.", submitted=True)["addendum"]

    assert again["version"] == first["version"]
    assert answers.history(PROJECT_SLUG) == [], "nothing was superseded either"


# --- what it is, and what it is not ------------------------------------------


def test_the_source_document_is_not_written_to(project: ScannedProject):
    """Nothing is altered in place, which is why this is a file of its own.

    The reason the loop delivers an addendum rather than an appended
    section: nothing is altered in place, ever.
    """
    source = project.docs_dir / "spec.md"
    _post("Q1", "Flat files.", submitted=True)
    assert source.read_text(encoding="utf-8") == SPEC


def test_it_lands_beside_the_original_in_the_draft_root(project: ScannedProject):
    delivered = _post("Q1", "Flat files.", submitted=True)["addendum"]
    path = Path(delivered["path"])
    assert path.parent == answers.store_path(PROJECT_SLUG).parent
    assert path.name == "spec__answers.md"


def test_the_path_is_stable_so_a_citation_keeps_working(project: ScannedProject):
    """Not timestamped. A citation made today resolves tomorrow."""
    first = _post("Q1", "Flat files.", submitted=True)["addendum"]
    second = _post("Q2", "docstrap.slugs.", submitted=True)["addendum"]
    assert first["path"] == second["path"]
    assert first["version"] != second["version"], "the file moved on; the path did not"

    # Rewritten whole, so it never stacks.
    text = Path(second["path"]).read_text(encoding="utf-8")
    assert text.count("## Q1 —") == 1
    assert text.count("## Q2 —") == 1


def test_each_document_gets_its_own(project: ScannedProject):
    """Two documents' Q1s are two questions, and two artifacts."""
    spec = _post("Q1", "The spec's.", submitted=True)["addendum"]
    note = _post("Q1", "The note's.", submitted=True, doc_slug="note")

    assert spec["path"] != note["addendum"]["path"]
    assert "The note's." not in Path(spec["path"]).read_text(encoding="utf-8")
    assert "The spec's." not in Path(note["addendum"]["path"]).read_text(
        encoding="utf-8"
    )


def test_a_draft_delivers_nothing(project: ScannedProject):
    """A draft decides nothing, so there is nothing to deliver."""
    result = _post("Q1", "NO! It should not be", submitted=False)
    assert result["addendum"] is None
    assert not addendum.path_for(PROJECT_SLUG, "spec").is_file()


def test_a_draft_over_a_submitted_answer_does_not_change_the_artifact(
    project: ScannedProject,
):
    """The published decision stands while its author retypes it."""
    _post("Q1", "Flat files.", submitted=True)
    before = addendum.path_for(PROJECT_SLUG, "spec").read_text(encoding="utf-8")

    _post("Q1", "Actually the document id, beca", submitted=False)
    after = addendum.path_for(PROJECT_SLUG, "spec").read_text(encoding="utf-8")

    assert after == before
    assert "Actually the document id" not in after, "a draft was published"


def test_a_superseded_answer_is_named_but_not_reproduced(project: ScannedProject):
    """The artifact says what was decided, and that it changed."""
    _post("Q1", "The slug is the address.", submitted=True)
    delivered = _post("Q1", "The document id is the address.", submitted=True)

    text = Path(delivered["addendum"]["path"]).read_text(encoding="utf-8")
    assert "The document id is the address." in text
    assert "The slug is the address." not in text
    assert "Supersedes 1 earlier answer" in text
    assert "answers-history.md" in text, "and where to find it"


def test_the_answer_is_reproduced_as_written(project: ScannedProject):
    """Including its line breaks. A record is not a rewrite."""
    delivered = _post(
        "Q1", "First line.\n\nSecond line.\n- and a bullet", submitted=True
    )["addendum"]
    text = Path(delivered["path"]).read_text(encoding="utf-8")
    assert "> First line." in text
    assert "> Second line." in text
    assert "> - and a bullet" in text


def test_the_front_matter_is_readable_without_reading_the_prose(
    project: ScannedProject,
):
    """A consumer checks the version; it should not have to parse markdown."""
    import yaml

    from docstrap.frontmatter import split_front_matter

    delivered = _post("Q1", "Flat files.", submitted=True)["addendum"]
    block = split_front_matter(
        Path(delivered["path"]).read_text(encoding="utf-8")
    )
    assert not block.malformed
    data = block.data
    assert data["strapdance"]["kind"] == "answer-addendum"
    assert data["strapdance"]["project"] == PROJECT_SLUG
    assert data["answered_version"] == delivered["version"]
    assert data["document_id"] == delivered["docId"]
    assert data["answered"] == 1 and data["open"] == 1
    assert data["generated_at"] == delivered["generatedAt"]
    # Round-trips through a plain YAML load too, which is what a
    # consumer that is not docstrap will use.
    assert yaml.safe_load(block.raw)["answered_version"] == delivered["version"]


def test_the_version_is_over_the_answers_and_not_the_questions(
    project: ScannedProject,
):
    """Rewording a question does not claim its answer changed."""
    _post("Q1", "Flat files.", submitted=True)
    before = addendum.version_of(pairing.pair(PROJECT_SLUG, "spec"))

    source = project.docs_dir / "spec.md"
    source.write_text(
        SPEC.replace("Which storage layout?", "Which storage layout, exactly?"),
        encoding="utf-8",
    )
    after = addendum.version_of(pairing.pair(PROJECT_SLUG, "spec"))
    assert after == before


def test_a_failed_delivery_does_not_fail_the_answer(
    project: ScannedProject, monkeypatch
):
    """The answer is already stored by the time delivery runs.

    Reporting the write as failed would invite a caller to retry a write
    that succeeded, which for a superseding store means a second history
    entry for one decision.
    """

    def boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(addendum, "deliver", boom)
    result = _post("Q1", "Flat files.", submitted=True)

    assert result["addendum"] is None, "the surface is told nothing was delivered"
    assert result["submitted"] is True
    held = answers.submitted(PROJECT_SLUG)
    assert [a.text for a in held] == ["Flat files."], "the answer is stored"


def test_the_qa_form_tool_delivers_the_same_artifact(project: ScannedProject):
    """One delivery function, so the surface used does not change the record."""
    app = FastAPI()
    mounting.mount_all(app)
    prefix = registry.get("qa").route_prefix
    assert prefix is not None
    url = prefix.format(project=PROJECT_SLUG, doc_slug="spec")
    scope = {
        "type": "http",
        "method": "POST",
        "path": url,
        "headers": [],
        "path_params": {},
        "root_path": "",
    }
    from docstrap.tools.qa.routes import AnswerSubmission as FormSubmission

    handler = params = None
    for route in app.router.routes:
        match, child = route.matches(scope)
        if match is Match.FULL:
            handler, params = route.endpoint, child["path_params"]
            break
    assert handler is not None

    result = handler(
        **params,
        payload=FormSubmission(question_id="Q1", answer="Through the form."),
    )
    delivered = result["addendum"]
    assert delivered is not None
    assert Path(delivered["path"]) == addendum.path_for(PROJECT_SLUG, "spec")
    assert "Through the form." in Path(delivered["path"]).read_text(encoding="utf-8")
