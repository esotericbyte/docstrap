"""A question run belongs to one project, and is bounded by what it declares.

The fixture workspace holds two sibling projects and a related directory.
Alpha is the one under test, and it is deliberately awkward: a directory the
config excludes, a subtree with its own `ignore: true`, a draft, a document
outside `docs_root`, and a README beside it. Everything below is either
"Alpha's, therefore collected" or "not Alpha's, therefore never seen" — the
second list being the point of the change.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from docstrap import projectscope, questions
from docstrap.cli import app

runner = CliRunner()


def _texts(root: Path) -> list[str]:
    """Every question text a scoped run over ``root`` returns."""
    scope = projectscope.resolve(root)
    return [
        q.text
        for document in questions.scan(scope.documents(under=root))
        for q in document.questions
    ]


def _names(root: Path) -> list[str]:
    scope = projectscope.resolve(root)
    return sorted(
        d.path.name for d in questions.scan(scope.documents(under=root))
    )


# --- one project's result is only that project's ---------------------------


def test_a_projects_result_excludes_a_sibling_projects_questions(
    question_workspace: Path,
):
    """The whole point: Beta asks three things, and Alpha's run has none."""
    alpha = _texts(question_workspace / "alpha")

    assert not any("Beta" in text for text in alpha)
    assert "beta-plan.md" not in _names(question_workspace / "alpha")


def test_the_sibling_reports_its_own_and_only_its_own(question_workspace: Path):
    assert len(_texts(question_workspace / "beta")) == 3
    assert _names(question_workspace / "beta") == ["beta-plan.md"]


def test_a_related_directory_is_its_own_context(question_workspace: Path):
    """`notes/` declares no docs_root, so the directory itself is its docs."""
    scope = projectscope.resolve(question_workspace / "notes")

    assert scope.slug == "notes"
    assert scope.kind == "related"
    assert _names(question_workspace / "notes") == ["workspace-note.md"]


# --- what the project declares away ----------------------------------------


def test_an_excluded_directory_is_not_walked(question_workspace: Path):
    """`held/` is named in the config's exclude_dirs, not in the defaults."""
    assert "superseded.md" not in _names(question_workspace / "alpha")


def test_an_ignore_declaration_prunes_the_subtree(question_workspace: Path):
    """`docs/vendored/.docstrap` says `ignore: true`, and that is honoured."""
    assert "borrowed.md" not in _names(question_workspace / "alpha")


def test_drafts_are_never_walked(question_workspace: Path):
    """`docs/drafts/` is a source with the role `draft`: off limits by role.

    It used to be off limits by name, as `promdance`. A folder's role is
    not derivable from its name, so the fixture says what this one is.
    """
    assert "draft.md" not in _names(question_workspace / "alpha")


def test_a_document_outside_docs_root_is_not_the_projects(
    question_workspace: Path,
):
    """A raw walk from the project root would take `src/design-note.md`."""
    assert "design-note.md" not in _names(question_workspace / "alpha")


# --- what the project does declare -----------------------------------------


def test_the_projects_own_documents_are_collected(question_workspace: Path):
    assert _names(question_workspace / "alpha") == [
        "README.md",
        "nested.md",
        "open-questions.md",
    ]


def test_the_readme_is_one_of_the_projects_documents(question_workspace: Path):
    """A project's README reaches the site, so its questions are its own."""
    texts = _texts(question_workspace / "alpha")

    assert "Does the README's own question belong to Alpha?" in texts


def test_a_subdirectory_narrows_without_leaving_the_project(
    question_workspace: Path,
):
    inside = question_workspace / "alpha" / "docs" / "decisions"

    assert _names(inside) == ["nested.md"]
    assert projectscope.resolve(inside).slug == "alpha"


# --- resolution ------------------------------------------------------------


def test_the_workspace_root_spans_projects_and_is_refused(
    question_workspace: Path,
):
    """Answering here at all is the library-wide behaviour being removed."""
    with pytest.raises(projectscope.SpansProjects) as raised:
        projectscope.resolve(question_workspace)

    message = str(raised.value)
    assert "alpha" in message and "beta" in message and "notes" in message


def test_a_directory_holding_exactly_one_project_resolves_to_it(tmp_path: Path):
    """A parent directory holding one project is still one context."""
    (tmp_path / ".docstrap").write_text(
        "version: 1\ntitle: one\nprojects:\n  - path: apps/only\n    title: Only\n",
        encoding="utf-8",
    )
    docs = tmp_path / "apps" / "only" / "docs"
    docs.mkdir(parents=True)
    (docs / "plan.md").write_text("Q1. Is one project unambiguous?\n")

    scope = projectscope.resolve(tmp_path / "apps")

    assert scope.slug == "apps__only"
    assert [d.name for d in scope.documents()] == ["plan.md"]


def test_a_directory_with_no_docstrap_above_it_has_no_project_context(
    tmp_path: Path,
):
    loose = tmp_path / "loose"
    loose.mkdir()
    (loose / "note.md").write_text("Q1. Is this anybody's question?\n")

    with pytest.raises(projectscope.ScopeError):
        projectscope.resolve(loose)


def test_a_standalone_project_is_its_own_context(collection: Path):
    """A single-project `.docstrap` resolves to the one project it declares."""
    scope = projectscope.resolve(collection)

    assert scope.docs_dir == (collection / "docs").resolve()
    assert all(
        d.is_relative_to(collection / "docs") for d in scope.documents()
    )


# --- the command -----------------------------------------------------------


def test_the_command_names_the_project_and_reports_only_its_questions(
    question_workspace: Path,
):
    result = runner.invoke(app, ["questions", str(question_workspace / "alpha")])

    assert result.exit_code == 0, result.output
    assert "project: alpha  (Alpha)" in result.output
    assert "Beta" not in result.output
    assert "in project alpha" in result.output


def test_the_command_refuses_a_path_that_spans_projects(
    question_workspace: Path,
):
    result = runner.invoke(app, ["questions", str(question_workspace)])

    assert result.exit_code == 2, result.output
    assert "Traceback" not in result.output
    assert "spans 3 projects" in result.output


def test_the_command_refuses_a_directory_no_project_declares(
    question_workspace: Path,
):
    loose = question_workspace / "sketches"
    loose.mkdir()
    (loose / "idea.md").write_text("Q1. Is a sketch anybody's document?\n")

    result = runner.invoke(app, ["questions", str(loose)])

    assert result.exit_code == 2, result.output
    assert "Traceback" not in result.output
    assert "belongs to no project" in result.output


def test_a_path_inside_a_project_but_outside_its_docs_says_so(
    question_workspace: Path,
):
    """`alpha/src` is Alpha's, but Alpha declares no documents there."""
    result = runner.invoke(
        app, ["questions", str(question_workspace / "alpha" / "src")]
    )

    assert result.exit_code == 0, result.output
    assert "no documents here" in result.output
    assert "0 question(s)" in result.output


def test_the_command_still_reads_a_single_document(question_workspace: Path):
    document = question_workspace / "beta" / "docs" / "beta-plan.md"

    result = runner.invoke(app, ["questions", str(document)])

    assert result.exit_code == 0, result.output
    assert "Which of Beta's stores is authoritative?" in result.output
    assert "3 question(s) in 1 document(s)" in result.output


def test_a_single_document_needs_no_project_around_it(tmp_path: Path):
    """Pointing at a document is answering about that document, and works."""
    document = tmp_path / "loose.md"
    document.write_text("# Loose\n\nQ1. Does a document alone still work?\n")

    result = runner.invoke(app, ["questions", str(document)])

    assert result.exit_code == 0, result.output
    assert "Does a document alone still work?" in result.output


def test_the_json_payload_keeps_its_shape(question_workspace: Path):
    import json

    result = runner.invoke(
        app, ["questions", str(question_workspace / "beta"), "--json"]
    )

    payload = json.loads(result.output)
    assert [Path(entry["path"]).name for entry in payload] == ["beta-plan.md"]
    assert [q["label"] for q in payload[0]["questions"]] == ["Q1", "Q2", "Q3"]


def test_all_still_widens_to_the_earlier_runs(question_workspace: Path):
    """`--all` is unchanged: it reports every labelled item, scope aside."""
    document = question_workspace / "alpha" / "docs" / "two-runs.md"
    document.write_text(
        "# Two runs\n\nQ1. Superseded?\n\nQ2. Also superseded?\n\n"
        "## 2 Open questions\n\nQ1. Current?\n",
        encoding="utf-8",
    )

    scoped = runner.invoke(app, ["questions", str(question_workspace / "alpha")])
    every = runner.invoke(
        app, ["questions", str(question_workspace / "alpha"), "--all"]
    )

    assert "Superseded?" not in scoped.output
    assert "Superseded?" in every.output
