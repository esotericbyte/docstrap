from __future__ import annotations

from pathlib import Path

from docstrap.cli import app
from docstrap.firstmate import detect_firstmate_homes
from typer.testing import CliRunner

runner = CliRunner()


def test_detects_firstmate_operational_home_by_shape(tmp_path: Path) -> None:
    scan_root = tmp_path / "scan"
    firstmate_home = _make_firstmate_home(scan_root / "ops")
    nonmatching = scan_root / "not-firstmate"
    (nonmatching / "bin").mkdir(parents=True)
    (nonmatching / "projects").mkdir()
    (nonmatching / "AGENTS.md").write_text("agent notes\n", encoding="utf-8")

    homes = detect_firstmate_homes(scan_root)

    assert [home.path for home in homes] == [firstmate_home]
    assert homes[0].agents_file == firstmate_home / "AGENTS.md"
    assert homes[0].projects_dir == firstmate_home / "projects"
    assert [script.name for script in homes[0].bin_scripts] == ["fm-status.sh"]


def test_firstmate_ignore_check_decline_writes_nothing(tmp_path: Path) -> None:
    scan_root = tmp_path / "scan"
    firstmate_home = _make_firstmate_home(scan_root / "ops")

    result = runner.invoke(
        app,
        ["firstmate-ignore-check", "--root", str(scan_root)],
        input="n\n",
    )

    assert result.exit_code == 0, result.output
    assert "firstmate operational home(s) found" in result.output
    assert "matched shape: AGENTS.md plus bin/fm-*.sh plus projects/" in result.output
    assert "double-count projects" in result.output
    assert "declined:" in result.output
    assert not (firstmate_home / ".docstrap").exists()


def _make_firstmate_home(path: Path) -> Path:
    (path / "bin").mkdir(parents=True)
    (path / "projects").mkdir()
    (path / "AGENTS.md").write_text("agent notes\n", encoding="utf-8")
    (path / "bin" / "fm-status.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    return path
