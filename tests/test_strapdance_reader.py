"""The fallback chain, end to end against real documents.

Every test here reads a file that exists in ``tests/fixtures``. The chain
is the whole point of the standard, so each step and
each boundary between steps gets its own case.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from docstrap.strapdance import (
    NAMESPACE,
    ChainStep,
    ExaminationState,
    ProjectSource,
    read_context,
)


# --- step 1 beats step 2 ---------------------------------------------------


def test_explicit_front_matter_wins_over_position(collection: Path):
    document = collection / "docs" / "proposals" / "explicit-wins.md"

    ctx = read_context(document)

    assert ctx.kind.value == "note"
    assert ctx.kind.step is ChainStep.EXPLICIT
    assert ctx.kind.detail == f"`{NAMESPACE}.kind`"
    # The directory would have said `proposal`, and did not get the chance.
    assert ctx.status.value == "done"
    assert ctx.status.step is ChainStep.EXPLICIT


def test_namespaced_value_wins_over_a_bare_key(collection: Path):
    """Bare keys are a compatibility fallback ranked below the namespace."""
    document = collection / "docs" / "proposals" / "namespace-beats-bare.md"

    ctx = read_context(document)

    assert ctx.kind.value == "proposal"
    assert ctx.kind.detail == f"`{NAMESPACE}.kind`"
    # The namespace carries no title, so the bare one is read — and named
    # as a compatibility read, so nothing mistakes it for a strapdance key.
    assert ctx.title.value == "the bare title"
    assert ctx.title.step is ChainStep.EXPLICIT
    assert "bare key `title`" in ctx.title.detail


# --- step 2 beats step 3 ---------------------------------------------------


def test_position_wins_over_content(collection: Path):
    """The document body declares a status; the directory implies one too."""
    document = collection / "docs" / "done" / "position-beats-content.md"
    assert "Status: DRAFT" in document.read_text(encoding="utf-8")

    ctx = read_context(document)

    assert ctx.status.value == "done"
    assert ctx.status.step is ChainStep.POSITION
    assert ctx.status.detail == "parent directory `done`"


def test_content_answers_when_position_has_nothing_to_say(collection: Path):
    """Step 3 runs only once step 2 has come up empty."""
    document = collection / "docs" / "research" / "content-declares-status.md"

    ctx = read_context(document)

    assert ctx.status.value == "superseded"
    assert ctx.status.step is ChainStep.CONTENT
    assert ctx.status.detail == "`Status:` line in the document"


def test_a_status_line_deep_in_the_body_is_prose_not_a_declaration(collection: Path):
    document = collection / "docs" / "research" / "status-deep-in-the-body.md"

    ctx = read_context(document)

    assert ctx.status.value == "active"
    assert ctx.status.step is ChainStep.UNKNOWN


# --- step 4: unknown is stated, never guessed ------------------------------


def test_unknown_kind_is_explicit(collection: Path):
    """An explicit unknown that is never guessed silently."""
    document = collection / "scratch" / "loose-note.md"

    ctx = read_context(document)

    assert ctx.kind.value is None
    assert ctx.kind.step is ChainStep.UNKNOWN
    assert ctx.kind.is_known is False
    assert "not guessed" in ctx.kind.detail


def test_relates_to_and_answers_have_no_fallback(collection: Path):
    """The two fields a directory could never express stay empty."""
    document = collection / "docs" / "adr" / "0009-hosted-app-routes.md"

    ctx = read_context(document)

    for resolved in (ctx.relates_to, ctx.answers):
        assert resolved.value == ()
        assert resolved.step is ChainStep.UNKNOWN
        assert resolved.detail == "no honest fallback; stays empty"


def test_explicit_relates_to_and_answers_are_read(collection: Path):
    document = collection / "docs" / "proposals" / "coexisting-namespaces.md"

    ctx = read_context(document)

    assert ctx.relates_to.value == ("docs/adr/0009-hosted-app-routes.md",)
    assert ctx.relates_to.step is ChainStep.EXPLICIT
    # A scalar is accepted where a list is expected, and normalised in
    # shape only — the value itself is untouched.
    assert ctx.answers.value == ("type2-url-grammar",)


# --- status is an open vocabulary ------------------------------------------


def test_unrecognised_status_is_preserved_verbatim(collection: Path):
    """Never coerced, mapped or normalised — not even in case."""
    document = collection / "docs" / "proposals" / "unrecognised-status.md"

    ctx = read_context(document)

    assert ctx.status.value == "PercolatinG"
    assert ctx.status.step is ChainStep.EXPLICIT


def test_directory_implied_statuses(collection: Path):
    notes = read_context(collection / "docs" / "notes" / "reference-by-directory.md")
    assert notes.status.value == "reference"
    assert notes.status.step is ChainStep.POSITION
    assert notes.kind.value == "note"

    hold = read_context(collection / "docs" / "hold" / "paused.md")
    assert hold.status.value == "active", "hold is not a distinct status value"
    assert hold.status.step is ChainStep.POSITION
    assert "work paused" in hold.status.detail


# --- the three-way state ---------------------------------------------------


def test_not_examined_declined_and_classified_are_distinguishable(collection: Path):
    """Two of these look identical on disk; they must not read alike."""
    proposals = collection / "docs" / "proposals"

    not_examined = read_context(proposals.parent / "adr" / "0009-hosted-app-routes.md")
    declined = read_context(proposals / "declined.md")
    classified = read_context(proposals / "classified.md")

    assert not_examined.state is ExaminationState.NOT_EXAMINED
    assert declined.state is ExaminationState.DECLINED
    assert classified.state is ExaminationState.CLASSIFIED

    states = {not_examined.state, declined.state, classified.state}
    assert len(states) == 3

    assert declined.declined is True
    assert classified.declined is False
    assert not_examined.declined is False


def test_a_declined_document_still_resolves_normally(collection: Path):
    """Declined documents remain normal documents in every other respect."""
    ctx = read_context(collection / "docs" / "proposals" / "declined.md")

    assert ctx.state is ExaminationState.DECLINED
    assert ctx.kind.value == "proposal"
    assert ctx.title.value == "Examined and declined"


def test_foreign_front_matter_alone_leaves_a_document_not_examined(collection: Path):
    """Nobody has looked *with this tool*, whatever else the block carries."""
    ctx = read_context(collection / "docs" / "proposals" / "namespace-beats-bare.md")
    assert ctx.state is ExaminationState.CLASSIFIED

    ctx = read_context(collection / "docs" / "proposals" / "empty-namespace.md")
    assert ctx.state is ExaminationState.NOT_EXAMINED, "an empty namespace records no decision"


# --- malformed blocks ------------------------------------------------------


def test_malformed_block_is_reported_and_the_chain_still_runs(collection: Path):
    """Reported, not repaired, and the document still resolves."""
    document = collection / "docs" / "proposals" / "malformed.md"
    original = document.read_bytes()

    ctx = read_context(document)

    assert ctx.errors, "the malformed block must be reported"
    assert "not valid YAML" in ctx.errors[0]
    assert str(document) in ctx.errors[0]

    assert ctx.kind.value == "proposal"
    assert ctx.kind.step is ChainStep.POSITION
    assert ctx.title.value == "A malformed block"
    assert ctx.title.step is ChainStep.CONTENT

    assert document.read_bytes() == original, "the reader never repairs anything"


def test_a_namespace_that_is_not_a_mapping_is_reported_not_fatal(tmp_path: Path):
    document = tmp_path / "wrong-shape.md"
    document.write_text(
        f"---\n{NAMESPACE}: just a string\n---\n\n# Wrong shape\n", encoding="utf-8"
    )

    ctx = read_context(document)

    assert any("must be a mapping" in e for e in ctx.errors)
    assert ctx.state is ExaminationState.NOT_EXAMINED
    assert ctx.title.value == "Wrong shape"


def test_an_unrecognised_namespace_is_never_an_error(collection: Path):
    """Stated as a test so it cannot quietly stop being true."""
    ctx = read_context(collection / "docs" / "proposals" / "coexisting-namespaces.md")

    assert ctx.errors == ()
    assert "some_other_tool" in ctx.foreign_keys
    assert NAMESPACE not in ctx.foreign_keys
    assert ctx.front_matter.data["some_other_tool"] == {
        "whatever": "it wants",
        "nested": ["one", "two"],
    }


# --- title and id ----------------------------------------------------------


def test_title_falls_back_to_the_first_heading_then_the_filename(collection: Path, tmp_path: Path):
    with_heading = read_context(collection / "docs" / "adr" / "0009-hosted-app-routes.md")
    assert with_heading.title.value == "Hosted app routes"
    assert with_heading.title.step is ChainStep.CONTENT

    headless = tmp_path / "no-heading-at-all.md"
    headless.write_text("Just a paragraph, no heading.\n", encoding="utf-8")
    assert read_context(headless).title.value == "No Heading At All"
    assert read_context(headless).title.step is ChainStep.POSITION


def test_id_is_the_path_slug_relative_to_the_collection_root(collection: Path):
    ctx = read_context(collection / "docs" / "adr" / "0009-hosted-app-routes.md")

    assert ctx.collection_root == (collection / "docs").resolve()
    assert ctx.id.value == "adr__0009-hosted-app-routes"
    assert ctx.id.step is ChainStep.POSITION

    outside_docs = read_context(collection / "scratch" / "loose-note.md")
    assert outside_docs.collection_root == collection.resolve()
    assert outside_docs.id.value == "scratch__loose-note"


def test_collection_root_can_be_overridden(collection: Path):
    document = collection / "docs" / "adr" / "0009-hosted-app-routes.md"

    ctx = read_context(document, collection_root=collection)

    assert ctx.id.value == "docs__adr__0009-hosted-app-routes"


# --- project, including the repo-root case ---------------------------------


def test_project_comes_from_the_nearest_docstrap_entry(collection: Path):
    ctx = read_context(collection / "docs" / "proposals" / "classified.md")

    assert ctx.project.value == "strapdance-fixture"
    assert ctx.project.step is ChainStep.POSITION
    assert "`.docstrap`" in ctx.project.detail


def test_repo_root_document_is_sub_scoped_by_an_explicit_project(workspace: Path):
    """The case where position genuinely cannot answer."""
    ctx = read_context(workspace / "root-prompt-scoped-to-alpha.md")

    assert ctx.project.value == "alpha"
    assert ctx.project.step is ChainStep.EXPLICIT


def test_repo_root_document_without_a_project_resolves_to_the_workspace_root(workspace: Path):
    """Honest rather than wrong."""
    ctx = read_context(workspace / "root-prompt-unscoped.md")

    assert ctx.project.value == "fixture-workspace"
    assert ctx.project.step is ChainStep.POSITION
    assert "workspace root" in ctx.project.detail


def test_a_document_inside_a_member_resolves_to_that_member(workspace: Path):
    ctx = read_context(workspace / "packages" / "alpha" / "docs" / "notes" / "inside-a-member.md")

    assert ctx.project.value == "alpha"
    assert ctx.project.step is ChainStep.POSITION
    assert "packages/alpha" in ctx.project.detail


def test_the_project_answer_says_which_of_the_four_replied(
    collection: Path, workspace: Path
):
    """Three of the four answers are all `POSITION`, and differ."""
    sources = {
        (collection / "docs" / "proposals" / "classified.md"): ProjectSource.DOCSTRAP_PROJECT,
        (workspace / "root-prompt-scoped-to-alpha.md"): ProjectSource.EXPLICIT,
        (workspace / "root-prompt-unscoped.md"): ProjectSource.WORKSPACE_ROOT,
        (workspace / "packages" / "alpha" / "docs" / "notes" / "inside-a-member.md"):
            ProjectSource.WORKSPACE_MEMBER,
    }

    for document, expected in sources.items():
        assert read_context(document).project_source is expected


def test_project_is_unknown_with_no_docstrap_and_no_workspace(tmp_path: Path):
    document = tmp_path / "orphan.md"
    document.write_text("# Orphan\n", encoding="utf-8")

    ctx = read_context(document)

    assert ctx.project.value is None
    assert ctx.project.step is ChainStep.UNKNOWN


# --- dates -----------------------------------------------------------------


def test_untracked_file_dates_come_from_the_filesystem(collection: Path):
    ctx = read_context(collection / "docs" / "adr" / "0009-hosted-app-routes.md")

    assert ctx.created.step is ChainStep.HISTORY
    assert ctx.created.detail == "filesystem mtime (file is untracked)"
    assert ctx.updated.value == ctx.created.value


def test_tracked_file_dates_come_from_git_history(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    document = repo / "tracked.md"
    document.write_text("# Tracked\n", encoding="utf-8")
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "fixture@example.invalid")
    _git(repo, "config", "user.name", "Fixture")
    _git(repo, "add", "tracked.md")
    _git(repo, "commit", "-q", "-m", "add tracked.md", "--date", "2020-01-02T03:04:05+00:00")

    ctx = read_context(document)

    assert ctx.created.step is ChainStep.HISTORY
    assert ctx.created.detail == "git history of the file"
    assert ctx.created.value.startswith("2020-01-02")


def test_explicit_dates_win_over_history(tmp_path: Path):
    document = tmp_path / "dated.md"
    document.write_text(
        f"---\n{NAMESPACE}:\n  created: 2019-05-06\n---\n\n# Dated\n", encoding="utf-8"
    )

    ctx = read_context(document)

    assert ctx.created.step is ChainStep.EXPLICIT
    assert str(ctx.created.value) == "2019-05-06"
    assert ctx.updated.step is ChainStep.HISTORY


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        env={
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_SYSTEM": "/dev/null",
            "GIT_AUTHOR_DATE": "2020-01-02T03:04:05+00:00",
            "GIT_COMMITTER_DATE": "2020-01-02T03:04:05+00:00",
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "HOME": str(repo),
        },
    )


# --- the promises that hold the whole thing up -----------------------------


def test_the_reader_never_writes(collection: Path, workspace: Path):
    """Checked over every fixture at once rather than case by case."""
    documents = sorted(collection.rglob("*.md")) + sorted(workspace.rglob("*.md"))
    before = {d: d.read_bytes() for d in documents}

    for document in documents:
        read_context(document)

    assert {d: d.read_bytes() for d in documents} == before


def test_every_field_reports_its_provenance(collection: Path):
    """Provenance is not decoration, so no field may omit it."""
    for document in sorted(collection.rglob("*.md")):
        ctx = read_context(document)
        assert set(ctx.fields) == {
            "id", "title", "kind", "status", "project",
            "relates_to", "answers", "created", "updated",
        }
        for name, resolved in ctx.fields.items():
            assert isinstance(resolved.step, ChainStep), (document, name)
            assert resolved.detail, (document, name)


def test_text_may_be_supplied_without_re_reading_the_file(collection: Path):
    document = collection / "docs" / "proposals" / "classified.md"

    from_disk = read_context(document)
    from_text = read_context(document, text=document.read_text(encoding="utf-8"))

    assert from_text.kind == from_disk.kind
    assert from_text.state is from_disk.state


@pytest.mark.parametrize(
    "name",
    ["docs/proposals/malformed.md", "docs/proposals/unterminated.md", "scratch/loose-note.md"],
)
def test_reading_any_fixture_returns_a_context_rather_than_raising(collection: Path, name: str):
    ctx = read_context(collection / name)
    assert ctx.path == collection / name
    assert ctx.status.value
