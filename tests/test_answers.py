"""The keyed answer store, proved through the endpoints that write it.

These are end-to-end on purpose, in the
way promdance's `tests/test_storage_owner.py` is: the defect this store replaces
lived in the gap between a question and the file an answer landed in, and
a unit test of either half would have missed it. A real project on disk,
registered the way a store a build reads is registered, scanned through
the same enumeration the build uses, answered through the mounted route,
and then read back off the file.

What each test holds up:

1. The listing is the project's own `Q<n>` questions, found by scanning.
2. An answer goes in under `<doc-id>:<label>`, and answering again
   supersedes rather than stacking a second section.
3. The key is the document's identity, so a renamed document keeps its
   answers — the failure the per-document, slug-named answer file had.
4. Two documents' `Q1`s are two different questions.
5. An answer counts when a person presses Finish and not before, and a
   row written before that distinction existed still counts.
6. A submitted answer may be revised, and the answer a revision replaces
   is kept rather than lost.
7. The listing is readable at two scopes — one document, or the whole
   project — and they are two different lists.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from starlette.routing import Match

from docstrap import answers, metadata, user_config
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

Some prose about the thing.

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
    """A registered project with two documents that pose questions."""
    store = tmp_path / "store"
    docs = store / PROJECT_PATH / "docs"
    docs.mkdir(parents=True)
    (docs / "spec.md").write_text(SPEC, encoding="utf-8")
    (docs / "note.md").write_text(NOTE, encoding="utf-8")
    (store / PROJECT_PATH / "drafts").mkdir()
    (store / ".docstrap").write_text(DOCSTRAP_YAML, encoding="utf-8")
    user_config.add_store(store / ".docstrap")

    scanned = [p for p in scan(load(store / ".docstrap")) if p.kind == "project"]
    assert [p.slug for p in scanned] == [PROJECT_SLUG]
    return scanned[0]


def _dispatch(method: str, url: str):
    """Resolve a URL the way the running server resolves it.

    Starlette's own matcher, against the routes ``mount_all`` mounted, so
    a handler reached here is the handler the server would reach. Nothing
    in this file writes a URL down for its own sake: the one below is
    built from the declaration's own prefix.
    """
    app = FastAPI()
    mounting.mount_all(app)
    scope = {
        "type": "http",
        "method": method,
        "path": url,
        "headers": [],
        "path_params": {},
        "root_path": "",
    }
    for route in app.router.routes:
        match, child = route.matches(scope)
        if match is Match.FULL:
            return route.endpoint, child["path_params"]
    raise AssertionError(f"no mounted route matched {method} {url}")


def _url() -> str:
    prefix = registry.get("qapanels").route_prefix
    assert prefix is not None
    return prefix.format(project=PROJECT_SLUG)


def _document_url(doc_slug: str) -> str:
    prefix = registry.get("qapanels").route_prefixes[1]
    return prefix.format(project=PROJECT_SLUG, doc_slug=doc_slug)


def _endpoints() -> dict[str, object]:
    """The instrument's handlers: two GETs read at two scopes, POST writes."""
    url = _url()
    return {
        "questions": _dispatch("GET", url)[0],
        "answers": _dispatch("POST", url)[0],
        "documentQuestions": _dispatch("GET", _document_url("spec"))[0],
    }


def test_the_instruments_url_is_not_shadowed_by_a_document_targeted_tool():
    """The collision a sub-path under a project prefix would create.

    `/api/tools/{project}/qa/answers` is indistinguishable from the
    qa tool's `/api/tools/{project}/{doc_slug}/answers` with a
    doc_slug of `qa`, and the qa tool mounts first. Keeping the
    instrument's read and write on the prefix itself is what makes the
    two shapes different lengths, so neither can capture the other.
    """
    url = _url()
    get_handler, get_params = _dispatch("GET", url)
    post_handler, post_params = _dispatch("POST", url)
    assert get_params == post_params == {"project": PROJECT_SLUG}
    assert get_handler.__module__ == post_handler.__module__
    assert get_handler.__module__.endswith("qapanels.routes")


# --- 1: the listing is a scan of the project's own documents ----------------


def test_the_listing_is_the_projects_own_numbered_questions(project: ScannedProject):
    listing = _endpoints()["questions"](project=PROJECT_SLUG)

    assert listing["project"] == PROJECT_SLUG
    assert listing["count"] == 3
    by_slug = {d["docSlug"]: d for d in listing["documents"]}
    assert set(by_slug) == {"spec", "note"}
    assert [q["label"] for q in by_slug["spec"]["questions"]] == ["Q1", "Q2"]
    assert by_slug["spec"]["questions"][0]["text"] == "Which storage layout?"
    # Nothing is answered yet, and listing must not have registered the
    # documents in the metadata store: reading is not answering.
    assert by_slug["spec"]["docId"] is None
    assert all(q["answer"] == "" for q in by_slug["spec"]["questions"])


# --- 2: an answer lands under a key, and answering again supersedes ---------


def test_answering_twice_supersedes_rather_than_stacking(project: ScannedProject):
    submit = _endpoints()["answers"]

    first = submit(
        project=PROJECT_SLUG,
        payload=AnswerSubmission(
            doc_slug="spec", label="Q1", answer="Flat files.", submitted=True
        ),
    )
    second = submit(
        project=PROJECT_SLUG,
        payload=AnswerSubmission(
            doc_slug="spec",
            label="Q1",
            answer="Flat files, keyed by document id.",
            submitted=True,
        ),
    )

    assert first["key"] == second["key"]
    assert first["key"].endswith(":Q1")
    assert first["key"].split(":")[0] == first["docId"]

    held = answers.read(PROJECT_SLUG)
    assert [a.key for a in held] == [first["key"]], "one row, not two"
    assert held[0].text == "Flat files, keyed by document id."

    text = Path(second["writtenTo"]).read_text(encoding="utf-8")
    assert text.count(f"## {first['key']}") == 1, "one section, not two"
    assert "Flat files." not in text.replace("Flat files, keyed by document id.", "")


def test_the_answer_prose_is_never_embedded_in_the_yaml(project: ScannedProject):
    """The property that ruled out markdown inside YAML."""
    submit = _endpoints()["answers"]
    submit(
        project=PROJECT_SLUG,
        payload=AnswerSubmission(
            doc_slug="spec", label="Q2", answer="Line one.\n\nLine two."
        ),
    )
    text = answers.store_path(PROJECT_SLUG).read_text(encoding="utf-8")
    front, _, body = text.partition("\n---\n")
    assert "Line one." not in front and "Line one." in body
    # One flow-style row per answer, so a re-answer is one changed line.
    rows = [line for line in front.splitlines() if line.strip().startswith("- {")]
    assert len(rows) == 1 and rows[0].rstrip().endswith("}")


# --- 3: the key is identity, so a rename does not orphan the answer ---------


def test_an_answer_survives_the_document_being_renamed(project: ScannedProject):
    endpoints = _endpoints()
    stored = endpoints["answers"](
        project=PROJECT_SLUG,
        payload=AnswerSubmission(
            doc_slug="spec", label="Q1", answer="Flat files.", submitted=True
        ),
    )

    # Move it, the way promoting a document out of proposals/ into plans/
    # moves one, and tell the metadata store where it went.
    source = project.docs_dir / "spec.md"
    moved = project.docs_dir / "specification.md"
    source.rename(moved)
    metadata.record_move(stored["docId"], str(moved))

    listing = endpoints["questions"](project=PROJECT_SLUG)
    by_slug = {d["docSlug"]: d for d in listing["documents"]}
    assert "spec" not in by_slug and "specification" in by_slug

    renamed = by_slug["specification"]
    assert renamed["docId"] == stored["docId"]
    q1 = next(q for q in renamed["questions"] if q["label"] == "Q1")
    assert q1["key"] == stored["key"], "the key did not move with the file"
    assert q1["answer"] == "Flat files."


# --- 4: two documents' Q1s are two questions --------------------------------


def test_the_same_label_in_two_documents_is_two_answers(project: ScannedProject):
    submit = _endpoints()["answers"]
    spec = submit(
        project=PROJECT_SLUG,
        payload=AnswerSubmission(
            doc_slug="spec", label="Q1", answer="The spec's.", submitted=True
        ),
    )
    note = submit(
        project=PROJECT_SLUG,
        payload=AnswerSubmission(
            doc_slug="note", label="Q1", answer="The note's.", submitted=True
        ),
    )

    assert spec["key"] != note["key"]
    assert spec["label"] == note["label"] == "Q1"
    held = {a.key: a.text for a in answers.read(PROJECT_SLUG)}
    assert held[spec["key"]] == "The spec's."
    assert held[note["key"]] == "The note's."


# --- the store's own invariants ---------------------------------------------


def test_a_missing_file_is_an_empty_store_and_not_an_error(project: ScannedProject):
    assert answers.read(PROJECT_SLUG) == []
    assert answers.get(PROJECT_SLUG, "01ABC:Q1") is None


def test_an_unreadable_answer_file_raises_rather_than_reading_as_empty(
    project: ScannedProject,
):
    """Returning nothing would look identical to the empty case, and the
    next write would then overwrite whatever was really in there."""
    answers.store_path(PROJECT_SLUG).write_text("---\n: :\n---\n", encoding="utf-8")
    with pytest.raises(answers.AnswerStoreError):
        answers.read(PROJECT_SLUG)


def test_a_label_may_not_carry_the_key_separator():
    with pytest.raises(answers.AnswerStoreError):
        answers.key_for("01ABC", "Q1:extra")


def test_a_heading_inside_an_answer_stays_part_of_that_answer(
    project: ScannedProject,
):
    """The body is markdown someone wrote, so it may hold headings."""
    submit = _endpoints()["answers"]
    stored = submit(
        project=PROJECT_SLUG,
        payload=AnswerSubmission(
            doc_slug="spec",
            label="Q1",
            answer="Because:\n\n## Reasons\n\nThose ones.",
            submitted=True,
        ),
    )
    held = answers.get(PROJECT_SLUG, stored["key"])
    assert held is not None
    assert held.text == "Because:\n\n## Reasons\n\nThose ones."


# --- 5: an answer counts when a person says it does -------------------------
#
# The first real run counted a reply at three characters — "NO!" —
# because an autosave and a finished answer were the same event.


def test_typing_in_pieces_is_invisible_until_finish(project: ScannedProject):
    """The step's proof, both halves of it.

    An answer typed in pieces produces no consumer-visible event until
    submit, and the same answer submitted produces exactly one.
    """
    endpoints = _endpoints()
    submit = endpoints["answers"]

    # The run that hurt: the editor autosaves a burst at a time.
    for piece in ["NO!", "NO! It should", "NO! It should not be a slug."]:
        submit(
            project=PROJECT_SLUG,
            payload=AnswerSubmission(doc_slug="spec", label="Q1", answer=piece),
        )
        assert answers.submitted(PROJECT_SLUG) == [], (
            f"a consumer saw {piece!r} before anyone said they were finished"
        )

    # Stored the whole time, though — losing the draft would throw away
    # the point of autosaving it.
    drafts = answers.read(PROJECT_SLUG)
    assert [a.draft for a in drafts] == ["NO! It should not be a slug."]
    assert drafts[0].text == "", "a draft is not the submitted answer"
    assert drafts[0].editable_text == "NO! It should not be a slug."
    assert drafts[0].submitted is False and drafts[0].is_submitted is False
    assert drafts[0].submitted_at is None

    # And a draft leaves the question open, which is what the panel's
    # header and the list's mark both read.
    listing = endpoints["questions"](project=PROJECT_SLUG)
    assert listing["count"] == 3 and listing["open"] == 3
    spec = next(d for d in listing["documents"] if d["docSlug"] == "spec")
    q1 = next(q for q in spec["questions"] if q["label"] == "Q1")
    assert q1["answer"] == "NO! It should not be a slug.", "the writer gets it back"
    assert q1["submittedAnswer"] == "", "nothing is answered yet"
    assert q1["submitted"] is False and q1["submittedAt"] is None
    assert q1["hasDraft"] is True

    # Finish. Exactly one event, carrying the whole answer.
    result = submit(
        project=PROJECT_SLUG,
        payload=AnswerSubmission(
            doc_slug="spec",
            label="Q1",
            answer="NO! It should not be a slug.",
            submitted=True,
        ),
    )
    assert result["submitted"] is True and result["submittedAt"]

    seen = answers.submitted(PROJECT_SLUG)
    assert len(seen) == 1, "one submission, not one per keystroke burst"
    assert seen[0].key == result["key"]
    assert seen[0].text == "NO! It should not be a slug."

    listing = endpoints["questions"](project=PROJECT_SLUG)
    assert listing["open"] == 2, "the finished one is no longer open"


def test_put_makes_every_caller_say_whether_it_is_submitted():
    """No default, because a default here is the guess that caused this."""
    with pytest.raises(TypeError):
        answers.put(
            PROJECT_SLUG,
            doc_id="01ABC",
            label="Q1",
            document="docs/spec.md",
            text="Yes.",
        )


# --- the ten real answers that predate the distinction ----------------------
#
# A real answer store holds ten answers written before any of
# this existed. They are platform decisions that travelled and closed
# work, and two of them have still never been acted on. Their rows carry
# no `submitted` field, and both properties below are about them.

LEGACY_ROW = (
    "  - {key: '01M2EQ4WT39AFVNKR1WB15KVHZ:Q2', "
    "document: docs/questions/2026-09-12-platform-decisions.md, "
    "label: Q2, answered_at: '2026-09-14T01:21:52+00:00'}"
)

LEGACY_STORE = f"""\
---
answers:
{LEGACY_ROW}
---

# Answers — {PROJECT_SLUG}

## 01M2EQ4WT39AFVNKR1WB15KVHZ:Q2 — docs/questions/2026-09-12-platform-decisions.md

No. It should not.
"""


def test_a_row_written_before_the_distinction_counts_as_submitted(
    project: ScannedProject,
):
    """Storing an answer *was* finishing it under the older rule.

    Reading these as drafts would retroactively un-answer ten real
    decisions — the opposite of what this step is for.
    """
    answers.store_path(PROJECT_SLUG).write_text(LEGACY_STORE, encoding="utf-8")

    held = answers.read(PROJECT_SLUG)
    assert len(held) == 1
    assert held[0].submitted is None, "absent is a third state, not False"
    assert held[0].is_submitted is True
    assert [a.key for a in answers.submitted(PROJECT_SLUG)] == [held[0].key]


def test_a_row_written_before_the_distinction_keeps_its_bytes(
    project: ScannedProject,
):
    """Writing a new answer must not rewrite the old ones.

    `put` rewrites the whole file, so every untouched row passes through
    the renderer. A row that arrived without a `submitted` field leaves
    without one.
    """
    path = answers.store_path(PROJECT_SLUG)
    path.write_text(LEGACY_STORE, encoding="utf-8")

    _endpoints()["answers"](
        project=PROJECT_SLUG,
        payload=AnswerSubmission(
            doc_slug="spec", label="Q1", answer="Something new.", submitted=True
        ),
    )

    rewritten = path.read_text(encoding="utf-8")
    assert LEGACY_ROW in rewritten, "the legacy row was reformatted"
    assert "No. It should not." in rewritten, "the legacy prose was lost"
    assert rewritten.count("submitted: true") == 1, "only the new row carries it"


# --- 6: a submitted answer may be revised ------------------------------------
#
# A person rewriting their own reply is ordinary; it used to need a hand
# repair of the record.


def _submit(answer: str, label: str = "Q1", doc_slug: str = "spec") -> dict:
    return _endpoints()["answers"](
        project=PROJECT_SLUG,
        payload=AnswerSubmission(
            doc_slug=doc_slug, label=label, answer=answer, submitted=True
        ),
    )


def _draft(answer: str, label: str = "Q1", doc_slug: str = "spec") -> dict:
    return _endpoints()["answers"](
        project=PROJECT_SLUG,
        payload=AnswerSubmission(doc_slug=doc_slug, label=label, answer=answer),
    )


def test_a_revision_supersedes_and_the_earlier_answer_survives(
    project: ScannedProject,
):
    """The step's proof: answer, submit, answer differently, submit.

    The second is what everything downstream reads, and the first is
    recoverable rather than lost.
    """
    first = _submit("Flat files.")
    second = _submit("Flat files, keyed by document id.")
    assert first["key"] == second["key"], "a revision is the same question"
    assert second["supersededCount"] == 1

    # What everything downstream reads is the second.
    seen = answers.submitted(PROJECT_SLUG)
    assert len(seen) == 1
    assert seen[0].text == "Flat files, keyed by document id."

    # And the first is still there, whole, with both timestamps.
    past = answers.history(PROJECT_SLUG, first["key"])
    assert [entry.text for entry in past] == ["Flat files."]
    assert past[0].revision == 1
    assert past[0].submitted_at == first["submittedAt"]
    assert past[0].superseded_at == second["submittedAt"]

    # A third revision stacks rather than replacing the second.
    third = _submit("Flat files, keyed by document id and label.")
    assert third["supersededCount"] == 2
    assert [entry.text for entry in answers.history(PROJECT_SLUG, first["key"])] == [
        "Flat files.",
        "Flat files, keyed by document id.",
    ]
    assert [e.revision for e in answers.history(PROJECT_SLUG, first["key"])] == [1, 2]


def test_the_superseded_answers_are_beside_the_current_ones_not_among_them(
    project: ScannedProject,
):
    """Two files. Everything reading `answers.md` reads current answers.

    History rows among them would change what that file means to every
    consumer of it, which is why they are not there.
    """
    _submit("Flat files.")
    _submit("Flat files, keyed by document id.")

    current = answers.store_path(PROJECT_SLUG).read_text(encoding="utf-8")
    assert current.count("- {key:") == 1, "one current answer, not two"
    assert "Flat files." not in current.replace(
        "Flat files, keyed by document id.", ""
    ), "the superseded prose is not in the current file"

    past = answers.history_path(PROJECT_SLUG)
    assert past.exists() and past.parent == answers.store_path(PROJECT_SLUG).parent
    text = past.read_text(encoding="utf-8")
    assert text.startswith("---\nanswers:\n") and "# Superseded answers — " in text
    assert "revision: 1" in text and "Flat files." in text


def test_resubmitting_the_same_answer_supersedes_nothing(project: ScannedProject):
    """Pressing Finish twice is not a revision, so nothing is kept."""
    first = _submit("Flat files.")
    again = _submit("Flat files.")
    assert again["supersededCount"] == 0
    assert answers.history(PROJECT_SLUG, first["key"]) == []


def test_a_draft_revision_does_not_unanswer_the_submitted_one(
    project: ScannedProject,
):
    """The damage an explicit submit would otherwise have introduced.

    Retyping a reply must not make the recorded decision vanish from
    every consumer for as long as the retyping takes.
    """
    endpoints = _endpoints()
    submitted = _submit("Flat files.")

    # The person starts rewriting. The editor autosaves as they type.
    _draft("Flat fi")
    _draft("Flat files, keyed by document id.")

    # The decision is still the decision.
    seen = answers.submitted(PROJECT_SLUG)
    assert [a.text for a in seen] == ["Flat files."]
    assert seen[0].has_draft and seen[0].draft == "Flat files, keyed by document id."
    assert seen[0].submitted_at == submitted["submittedAt"]

    # The question is not open — it has an answer — but the panel can see
    # that a revision is in flight, and the editor resumes the revision.
    listing = endpoints["questions"](project=PROJECT_SLUG)
    q1 = next(
        q
        for d in listing["documents"]
        if d["docSlug"] == "spec"
        for q in d["questions"]
        if q["label"] == "Q1"
    )
    assert listing["open"] == 2, "an answered question with a draft is not open again"
    assert q1["submitted"] is True and q1["hasDraft"] is True
    assert q1["submittedAnswer"] == "Flat files."
    assert q1["answer"] == "Flat files, keyed by document id.", "resume where they were"

    # Finishing spends the draft and supersedes.
    _submit("Flat files, keyed by document id.")
    after = answers.get(PROJECT_SLUG, submitted["key"])
    assert after is not None
    assert after.text == "Flat files, keyed by document id."
    assert after.draft is None and after.has_draft is False
    assert [e.text for e in answers.history(PROJECT_SLUG, submitted["key"])] == [
        "Flat files."
    ]


def test_a_draft_matching_the_submitted_answer_is_not_a_revision(
    project: ScannedProject,
):
    """Clicking into a question and out again leaves no revision mark."""
    _submit("Flat files.")
    _draft("Flat files.")
    held = answers.get(PROJECT_SLUG, _submit("Flat files.")["key"])
    assert held is not None and held.has_draft is False


def _drafts_on_the_page(listing: dict) -> list[dict]:
    """What the panels' one Finish submits: every question with a draft,
    carrying the draft as its answer (`ui/finish.ts` ``pendingDrafts``)."""
    return [
        {"doc_slug": d["docSlug"], "label": q["label"], "answer": q["answer"]}
        for d in listing["documents"]
        for q in d["questions"]
        if q["hasDraft"]
    ]


def test_the_one_finish_submits_every_draft_on_the_page(project: ScannedProject):
    """Three drafts, one press, three submissions, through the existing route.

    The panels' Finish sits below the question list and submits every
    draft in scope, because one button per answer left thirteen
    answers as drafts on 2026-11-04. It reads the drafts off the
    listing and posts each through the same write a per-answer Finish
    made; this is that sequence against the mounted route.
    """
    endpoints = _endpoints()
    _draft("Flat files.", label="Q1")
    _draft("The slug owner.", label="Q2")
    _draft("No, a different one.", label="Q1", doc_slug="note")

    listing = endpoints["questions"](project=PROJECT_SLUG)
    drafts = _drafts_on_the_page(listing)
    assert len(drafts) == 3
    assert answers.submitted(PROJECT_SLUG) == [], "a draft is nobody's decision yet"

    for draft in drafts:
        _submit(draft["answer"], label=draft["label"], doc_slug=draft["doc_slug"])

    after = endpoints["questions"](project=PROJECT_SLUG)
    assert _drafts_on_the_page(after) == [], "each draft was spent by its submission"
    assert after["open"] == 0
    assert sorted(a.text for a in answers.submitted(PROJECT_SLUG)) == [
        "Flat files.",
        "No, a different one.",
        "The slug owner.",
    ]


def test_a_page_with_no_drafts_offers_finish_nothing_to_submit(
    project: ScannedProject,
):
    """Nothing typed, or everything already submitted: no drafts, so the
    panels' Finish is disabled (`ui/finish.ts` ``finishState``)."""
    endpoints = _endpoints()
    assert _drafts_on_the_page(endpoints["questions"](project=PROJECT_SLUG)) == []
    _submit("Flat files.")
    _draft("Flat files.")  # clicking in and out again is not a revision
    assert _drafts_on_the_page(endpoints["questions"](project=PROJECT_SLUG)) == []


def test_an_answer_written_before_any_of_this_may_still_be_revised(
    project: ScannedProject,
):
    """The ten real ones are revisable, and revising one keeps it."""
    answers.store_path(PROJECT_SLUG).write_text(LEGACY_STORE, encoding="utf-8")
    key = "01M2EQ4WT39AFVNKR1WB15KVHZ:Q2"

    answers.put(
        PROJECT_SLUG,
        doc_id="01M2EQ4WT39AFVNKR1WB15KVHZ",
        label="Q2",
        document="docs/questions/2026-09-12-platform-decisions.md",
        text="No. It should not, and here is the reason.",
        submitted=True,
    )

    held = answers.get(PROJECT_SLUG, key)
    assert held is not None
    assert held.text == "No. It should not, and here is the reason."
    kept = answers.history(PROJECT_SLUG, key)
    assert [entry.text for entry in kept] == ["No. It should not."]
    assert kept[0].revision == 1


# --- 7: the panel is scoped deliberately -------------------------------------
#
# The instrument registered only `list_questions(project)`, which takes no
# document argument, so opening it while reading one document listed
# every question in the project.


def test_the_document_scope_is_reachable_and_is_not_the_project_scope(
    project: ScannedProject,
):
    """The step's proof: two documents in one project, two lists."""
    read_project = _endpoints()["questions"]
    spec_url = _document_url("spec")
    note_url = _document_url("note")
    read_spec, spec_params = _dispatch("GET", spec_url)
    read_note, note_params = _dispatch("GET", note_url)

    # The two GETs are the same handler, told which document. (`_dispatch`
    # mounts a fresh app each call, so compare the handler and not the
    # closure object.)
    assert read_spec.__qualname__ == read_note.__qualname__
    assert read_spec.__qualname__.endswith("list_document_questions")
    assert spec_params == {"project": PROJECT_SLUG, "doc_slug": "spec"}
    assert note_params == {"project": PROJECT_SLUG, "doc_slug": "note"}

    whole = read_project(project=PROJECT_SLUG)
    spec = read_spec(**spec_params)
    note = read_note(**note_params)

    assert [d["docSlug"] for d in whole["documents"]] == ["note", "spec"] or [
        d["docSlug"] for d in whole["documents"]
    ] == ["spec", "note"]
    assert [d["docSlug"] for d in spec["documents"]] == ["spec"]
    assert [d["docSlug"] for d in note["documents"]] == ["note"]

    # Two different lists, and neither is the project's.
    assert [q["label"] for q in spec["documents"][0]["questions"]] == ["Q1", "Q2"]
    assert [q["label"] for q in note["documents"][0]["questions"]] == ["Q1"]
    assert spec["count"] == 2 and note["count"] == 1 and whole["count"] == 3

    # Same shape either way, so nothing reading a listing has to know
    # which scope produced it.
    assert set(spec) == set(whole)


def test_a_document_scope_carries_that_documents_answers(project: ScannedProject):
    """Narrowing the scan does not narrow what an answer knows."""
    stored = _submit("Flat files.", label="Q1", doc_slug="spec")
    _submit("The note's.", label="Q1", doc_slug="note")

    handler, params = _dispatch("GET", _document_url("spec"))
    spec = handler(**params)
    q1 = spec["documents"][0]["questions"][0]
    assert q1["key"] == stored["key"]
    assert q1["submittedAnswer"] == "Flat files."
    assert spec["open"] == 1, "Q2 is still open; the note's Q1 is not counted here"


def test_a_document_scope_on_a_slug_the_project_does_not_declare_is_404(
    project: ScannedProject,
):
    """Quietly returning nothing would read as "no questions here"."""
    handler, params = _dispatch("GET", _document_url("nope"))
    with pytest.raises(HTTPException) as raised:
        handler(**params)
    assert raised.value.status_code == 404


def test_the_document_scope_is_not_shadowed_by_the_qa_tools_answers_route(
    project: ScannedProject,
):
    """Both are document-targeted; only the collection leaf differs.

    The qa tool mounts first, so if a leaf could be confused for a slug
    this is where it would show.
    """
    panels, _ = _dispatch("GET", _document_url("spec"))
    qa_prefix = registry.get("qa").route_prefix
    assert qa_prefix is not None
    qa, _ = _dispatch(
        "POST", qa_prefix.format(project=PROJECT_SLUG, doc_slug="spec")
    )
    assert panels.__module__.endswith("qapanels.routes")
    assert qa.__module__.endswith("qa.routes")
