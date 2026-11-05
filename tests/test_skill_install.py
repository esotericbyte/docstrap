"""The packaged Claude skills, and the one path that installs them.

`docstrap init` is the installer. A second skill must arrive
through it rather than beside it, so these tests run `init` against a
redirected HOME and look at what landed.
"""
from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from docstrap.cli import app

runner = CliRunner()

PACKAGED_SKILLS = Path(__file__).parent.parent / "src" / "docstrap" / "skills"


def test_both_skills_ship_inside_the_package():
    names = sorted(p.name for p in PACKAGED_SKILLS.glob("*.md"))

    assert names == ["docstrap-authoring.md", "docstrap-lifecycle.md"]


def test_init_installs_every_packaged_skill(tmp_path: Path, monkeypatch):
    home = _redirect_home(tmp_path, monkeypatch)

    result = runner.invoke(app, ["init", "--install-skills"])

    assert result.exit_code == 0, result.output
    installed = home / ".claude" / "skills"
    for skill in sorted(PACKAGED_SKILLS.glob("*.md")):
        assert (installed / skill.name).read_bytes() == skill.read_bytes()
    assert "installed: docstrap-lifecycle.md" in result.output


def test_init_installs_no_skills_when_declined(tmp_path: Path, monkeypatch):
    home = _redirect_home(tmp_path, monkeypatch)

    result = runner.invoke(app, ["init", "--no-install-skills"])

    assert result.exit_code == 0, result.output
    assert not (home / ".claude" / "skills").exists()


def test_the_lifecycle_skill_states_its_two_gates_and_its_command():
    text = (PACKAGED_SKILLS / "docstrap-lifecycle.md").read_text(encoding="utf-8")

    assert text.startswith("---\nname: docstrap-lifecycle\n")
    assert "Explicitly prompted" in text
    assert "Explicitly approved" in text
    assert "docstrap status <path> <new-status>" in text
    # It routes through the CLI, and says the databases are off limits.
    assert "Never write to the databases" in text
    assert "sqlite3" in text


def _redirect_home(tmp_path: Path, monkeypatch) -> Path:
    """Point HOME and the XDG dirs at a throwaway tree."""
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(home))
    for var, name in (
        ("XDG_CONFIG_HOME", ".config"),
        ("XDG_DATA_HOME", ".local/share"),
        ("XDG_CACHE_HOME", ".cache"),
        ("XDG_STATE_HOME", ".local/state"),
    ):
        monkeypatch.setenv(var, str(home / name))
    return home
