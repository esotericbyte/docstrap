"""`docstrap doctor` over real trees on disk, including what it must not do.

Every test here runs doctor against an actual directory — the fixture
workspace copied into ``tmp_path``, or a tree the test builds — and reads
the result. Nothing is mocked, because the thing under test is a walk of a
filesystem and a promise about not touching it.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from docstrap import doctor
from docstrap.cli import app
from docstrap.doctor import ProjectSource

runner = CliRunner()


@pytest.fixture(autouse=True)
def _throwaway_home(user_dirs: Path) -> Path:
    """Doctor reads user-level state under the home directory, so every run
    here gets a throwaway one."""
    return user_dirs


# --- detection -------------------------------------------------------------


def test_reports_the_root_documents_that_only_the_workspace_root_scopes(
    doctor_workspace: Path,
):
    report = doctor.examine(doctor_workspace)

    assert [f.relative_path for f in report.ambiguities] == [
        "docs/notes/also-unscoped.md",
        "docs/proposals/unscoped-at-the-root.md",
    ]
    for finding in report.ambiguities:
        assert finding.source is ProjectSource.WORKSPACE_ROOT
        assert finding.chain.startswith("position — ")
        assert finding.project == "doctor-fixture-workspace"
        assert "workspace root" in finding.detail


def test_excluded_and_out_of_tree_documents_are_never_examined(doctor_workspace: Path):
    report = doctor.examine(doctor_workspace)

    examined = {f.name for f in report.examined}
    # `archive/` is excluded everywhere docstrap looks.
    assert "superseded.md" not in examined
    # The README is not under docs/, and the member's doc is the member's.
    assert "README.md" not in examined
    assert "owned-by-alpha.md" not in examined
    assert len(report.examined) == 2


def test_a_document_with_nothing_above_it_reports_that_nothing_answered(tmp_path: Path):
    docs = tmp_path / "loose" / "docs"
    docs.mkdir(parents=True)
    (docs / "orphan.md").write_text("# Orphan\n", encoding="utf-8")

    report = doctor.examine(tmp_path / "loose")

    assert len(report.ambiguities) == 1
    finding = report.ambiguities[0]
    assert finding.source is ProjectSource.NONE
    assert finding.chain.startswith("unknown — ")
    assert finding.project is None
    assert "no `.docstrap` entry" in finding.detail


def test_a_missing_docs_directory_is_reported_rather_than_raised(tmp_path: Path):
    report = doctor.examine(tmp_path)

    assert report.docs_dir_exists is False
    assert report.examined == ()
    assert report.ok is True


def test_the_firstmate_home_check_is_folded_in_not_reimplemented(tmp_path: Path):
    home = _make_firstmate_home(tmp_path / "ops")

    report = doctor.examine(tmp_path)

    assert [f.path for f in report.firstmate] == [home]
    assert report.unignored_firstmate == report.firstmate
    assert report.ok is False
    # Doctor reports it; `docstrap firstmate-ignore-check` is what writes.
    assert not (home / ".docstrap").exists()


# --- the promise: doctor does not act --------------------------------------


def test_doctor_modifies_nothing(doctor_workspace: Path, tmp_path: Path):
    """The whole point of the command. Nothing under the root may change."""
    before = _snapshot(doctor_workspace)
    plan = tmp_path / "outside-the-tree" / "fix-plan.sh"

    result = runner.invoke(
        app,
        [
            "doctor",
            "--root", str(doctor_workspace),
            "--interactive",
            "--fix-plan", str(plan),
        ],
        # A destination for the first finding, silence for the second.
        input="packages/alpha/docs\n\n",
    )

    assert result.exit_code == 0, result.output
    assert _snapshot(doctor_workspace) == before
    assert plan.exists()  # the one file it creates, and it is outside the tree


def test_the_fix_plan_leaves_every_undecided_move_commented_out(
    doctor_workspace: Path, tmp_path: Path
):
    report = doctor.examine(doctor_workspace)

    plan = doctor.write_fix_plan(report, tmp_path / "plan.sh")
    script = plan.read_text(encoding="utf-8")

    assert "RAN NONE OF IT" in script
    assert "docs/proposals/unscoped-at-the-root.md" in script
    # Every git mv in an undecided plan is commented; running it does nothing.
    moves = [line for line in script.splitlines() if "git mv" in line]
    assert moves and all(line.lstrip().startswith("#") for line in moves)


def test_a_chosen_destination_becomes_a_live_move_in_the_plan(
    doctor_workspace: Path, tmp_path: Path
):
    report = doctor.examine(doctor_workspace)

    plan = doctor.write_fix_plan(
        report,
        tmp_path / "plan.sh",
        destinations={"docs/proposals/unscoped-at-the-root.md": "packages/alpha/docs"},
    )
    script = plan.read_text(encoding="utf-8")

    assert (
        "git mv docs/proposals/unscoped-at-the-root.md "
        "packages/alpha/docs/unscoped-at-the-root.md" in script
    )
    assert "mkdir -p packages/alpha/docs" in script
    # The finding nobody decided on is still inert.
    assert "# git mv docs/notes/also-unscoped.md" in script
    # And writing the plan still moved nothing.
    assert (doctor_workspace / "docs" / "proposals" / "unscoped-at-the-root.md").exists()
    assert not (doctor_workspace / "packages" / "alpha" / "docs" / "unscoped-at-the-root.md").exists()


def test_the_fix_plan_refuses_to_overwrite_an_existing_file(
    doctor_workspace: Path, tmp_path: Path
):
    existing = tmp_path / "plan.sh"
    existing.write_text("# somebody else's script\n", encoding="utf-8")
    report = doctor.examine(doctor_workspace)

    with pytest.raises(doctor.FixPlanExists):
        doctor.write_fix_plan(report, existing)

    assert existing.read_text(encoding="utf-8") == "# somebody else's script\n"


def test_the_cli_refuses_to_overwrite_and_says_so(doctor_workspace: Path, tmp_path: Path):
    existing = tmp_path / "plan.sh"
    existing.write_text("# somebody else's script\n", encoding="utf-8")

    result = runner.invoke(
        app, ["doctor", "--root", str(doctor_workspace), "--fix-plan", str(existing)]
    )

    assert result.exit_code == 1
    assert "will not overwrite" in result.output
    assert existing.read_text(encoding="utf-8") == "# somebody else's script\n"


# --- the report ------------------------------------------------------------


def test_the_cli_reports_each_finding_with_the_chain_step_that_produced_it(
    doctor_workspace: Path,
):
    result = runner.invoke(app, ["doctor", "--root", str(doctor_workspace)])

    assert result.exit_code == 0, result.output
    assert "ambiguously-scoped documents (2)" in result.output
    assert "docs/proposals/unscoped-at-the-root.md" in result.output
    assert "chain:    position — uv workspace root" in result.output
    assert "doctor reports and proposes only. Nothing was modified." in result.output


def test_the_cli_reports_a_clean_workspace_as_clean(tmp_path: Path):
    result = runner.invoke(app, ["doctor", "--root", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert "every examined document is scoped to a project" in result.output
    assert "no firstmate operational homes" in result.output


# --- helpers ---------------------------------------------------------------


def _snapshot(root: Path) -> dict[str, bytes]:
    """Every file below root, by relative path, with its bytes."""
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _make_firstmate_home(path: Path) -> Path:
    (path / "bin").mkdir(parents=True)
    (path / "projects").mkdir()
    (path / "AGENTS.md").write_text("agent notes\n", encoding="utf-8")
    (path / "bin" / "fm-status.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    return path
