"""`docstrap help` is the subcommand spelling of `docstrap --help`.

Both spellings are exercised through the real CLI and compared to each
other, so the test states the promise (they agree) rather than pinning the
help text, which changes every time a command is added.
"""
from __future__ import annotations

from typer.testing import CliRunner

from docstrap.cli import app

runner = CliRunner()


def test_help_subcommand_prints_the_same_text_as_the_help_flag() -> None:
    flag = runner.invoke(app, ["--help"])
    word = runner.invoke(app, ["help"])
    assert flag.exit_code == 0
    assert word.exit_code == 0
    assert word.output.strip() == flag.output.strip()


def test_help_subcommand_shows_the_command_table() -> None:
    result = runner.invoke(app, ["help"])
    assert "build" in result.output
    assert "scan" in result.output


def test_help_is_itself_listed_as_a_command() -> None:
    result = runner.invoke(app, ["--help"])
    assert "help" in result.output
