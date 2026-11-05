"""The `Q<n>` finder, against documents shaped like the real corpus.

The fixtures are excerpted from documents that exist in this workspace, so
every "must not be collected" case below is a question mark somebody
actually wrote — a rhetorical heading, a question answered in its next
sentence, a quoted prompt, an FAQ entry, an example list, a fenced code
block, and a `Q3` mentioned mid-sentence.

The point of the numbering convention is that none of them need judging.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from docstrap import questions


@pytest.fixture
def question_docs(fixture_tree) -> Path:
    return fixture_tree("questions")


# --- the question marks that must not be collected -------------------------


def test_a_document_full_of_question_marks_yields_nothing(question_docs: Path):
    """Seven kinds of non-question question mark, and not one label."""
    document = question_docs / "prose-full-of-question-marks.md"

    found = questions.find(document)

    assert found.questions == ()
    assert found.all_labelled == ()
    assert not found


def test_a_q_label_inside_a_fenced_block_is_not_a_question(question_docs: Path):
    """The fixture's fenced example contains `Q1.` and `Q2.` verbatim."""
    document = question_docs / "prose-full-of-question-marks.md"

    body = document.read_text(encoding="utf-8")

    assert "Q1. Should this fixture's fenced example be collected?" in body
    assert questions.find(document).all_labelled == ()


def test_a_q_reference_mid_sentence_is_not_a_question():
    """`I heard Q3=X, Q5=Y — confirm?` is a cross-reference, not a label."""
    text = 'A turn that carries answers confirms them: "I heard Q3=X, Q5=Y — confirm?"'

    assert questions.find_in_text(text).questions == ()


def test_a_q_label_inside_a_blockquote_is_not_a_question():
    text = "> Q1. Is a quoted question the document's own question?\n"

    assert questions.find_in_text(text).questions == ()


def test_a_heading_that_looks_like_a_label_is_not_a_question():
    text = "## Q1. Where does the legacy bucket live?\n"

    assert questions.find_in_text(text).questions == ()


# --- the questions that must be collected ----------------------------------


def test_the_numbered_questions_at_the_end_are_found(question_docs: Path):
    document = question_docs / "spec-with-open-questions.md"

    found = questions.find(document)

    assert [q.label for q in found.questions] == ["Q1", "Q2", "Q3"]
    assert [q.section for q in found.questions] == ["8 Open questions"] * 3


def test_a_question_wrapped_over_several_lines_is_one_question(question_docs: Path):
    document = question_docs / "spec-with-open-questions.md"

    first = questions.find(document).questions[0]

    assert first.text.startswith("Should `issue` be allowed to run")
    assert first.text.endswith("cite a state that never became a commit.")
    assert first.line == 13


def test_a_section_after_the_questions_does_not_hide_them(question_docs: Path):
    """`## 9 Risks` follows the run; the run is still the end of the asking."""
    document = question_docs / "spec-with-open-questions.md"

    assert len(questions.find(document).questions) == 3


def test_task_list_questions_are_found_with_their_checkbox(question_docs: Path):
    document = question_docs / "pitch-with-task-questions.md"

    found = questions.find(document)

    assert [q.label for q in found.questions] == ["Q1", "Q2", "Q3", "Q4"]
    assert [q.checkbox for q in found.questions] == [" ", " ", "x", " "]
    assert found.questions[0].text.startswith('Name: "Pitchhouse"?')


def test_a_multi_question_item_stays_one_question(question_docs: Path):
    """Q1 holds four question marks. It is one thing a reader answers."""
    document = question_docs / "pitch-with-task-questions.md"

    first = questions.find(document).questions[0]

    assert first.text.count("?") == 4
    assert first.number == 1


# --- which run is "the end" ------------------------------------------------


def test_only_the_last_run_is_reported(question_docs: Path):
    document = question_docs / "two-runs.md"

    found = questions.find(document)

    assert [q.label for q in found.questions] == ["Q1", "Q2", "Q3"]
    assert found.questions[0].section == "7 Open questions (round 8 — current)"
    # The superseded round-3 pair is still inspectable.
    assert len(found.all_labelled) == 5


def test_a_run_breaks_where_the_numbering_does_not_ascend():
    text = "Q1. First.\n\nQ2. Second.\n\nQ1. A fresh set.\n\nQ2. Its second.\n"

    found = questions.find_in_text(text)

    assert len(found.all_labelled) == 4
    assert [q.line for q in found.questions] == [5, 7]


# --- label shapes ----------------------------------------------------------


@pytest.mark.parametrize(
    "line",
    [
        "Q1. plain",
        "Q1: colon",
        "Q1) paren",
        "**Q1.** emphasised",
        "- **Q1.** bulleted",
        "- [ ] **Q1.** a task",
        "1. **Q1.** inside a numbered list",
        "* Q1. a star bullet",
    ],
)
def test_label_shapes_the_corpus_uses(line: str):
    found = questions.find_in_text(line + "\n")

    assert len(found.questions) == 1
    assert found.questions[0].number == 1


@pytest.mark.parametrize(
    "line",
    [
        "Q1 no separator at all",
        "Quantity. a word beginning with Q",
        "Q. no number",
        "Q1.no space after the separator",
        "The answer to Q1. is elsewhere",
    ],
)
def test_shapes_that_are_not_labels(line: str):
    assert questions.find_in_text(line + "\n").all_labelled == ()


# --- front matter and line numbers -----------------------------------------


def test_line_numbers_count_from_the_top_of_the_file():
    text = "---\ntitle: x\n---\n\n## Open questions\n\nQ1. Where?\n"

    found = questions.find_in_text(text)

    assert found.questions[0].line == 7
    assert found.questions[0].section == "Open questions"


def test_a_document_with_no_questions_is_falsey():
    assert not questions.find_in_text("# Just a title\n\nNo questions here.\n")


# --- reading a set of documents --------------------------------------------
#
# `scan` walks nothing: it reads the documents it is handed, and which
# documents those are is a project's business — see
# `test_questions_project_scope.py`.


def test_scan_reports_only_documents_that_ask_something(question_docs: Path):
    results = questions.scan(sorted(question_docs.glob("*.md")))

    names = sorted(d.path.name for d in results)
    assert names == [
        "pitch-with-task-questions.md",
        "spec-with-open-questions.md",
        "two-runs.md",
    ]
    assert sum(len(d.questions) for d in results) == 10


def test_scan_keeps_the_order_it_was_given(question_docs: Path):
    given = sorted(question_docs.glob("*.md"), reverse=True)

    results = questions.scan(given)

    assert [d.path.name for d in results] == [
        "two-runs.md",
        "spec-with-open-questions.md",
        "pitch-with-task-questions.md",
    ]


def test_a_document_that_cannot_be_read_does_not_end_the_run(tmp_path: Path):
    unreadable = tmp_path / "gone.md"
    readable = tmp_path / "here.md"
    readable.write_text("Q1. Seen?\n", encoding="utf-8")

    results = questions.scan([unreadable, readable])

    assert [d.path.name for d in results] == ["here.md"]
