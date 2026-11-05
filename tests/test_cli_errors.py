from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from docstrap.cli import app

runner = CliRunner()


def test_scan_reports_non_mapping_docstrap_without_traceback(tmp_path: Path) -> None:
    config = tmp_path / ".docstrap"
    config.write_text(
        "DIRECTIVE-STOP!\n#Do not operate on this folder or any subtree\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["scan", "--config", str(config)])

    assert result.exit_code == 2, result.output
    assert "Traceback" not in result.output
    assert f"Invalid .docstrap config: {config}" in result.output
    assert "key/value pairs at the top level" in result.output
    assert "ignore: true" in result.output


def test_scan_reports_invalid_yaml_docstrap_without_traceback(tmp_path: Path) -> None:
    config = tmp_path / ".docstrap"
    config.write_text("version: [\n", encoding="utf-8")

    result = runner.invoke(app, ["scan", "--config", str(config)])

    assert result.exit_code == 2, result.output
    assert "Traceback" not in result.output
    assert f"Invalid .docstrap config: {config}" in result.output
    assert "could not be parsed as YAML" in result.output
    assert "ignore: true" in result.output


def test_build_config_load_error_uses_same_clean_cli_message(tmp_path: Path) -> None:
    config = tmp_path / ".docstrap"
    config.write_text("DIRECTIVE-STOP!\n", encoding="utf-8")

    result = runner.invoke(app, ["build", "--config", str(config), "--out", str(tmp_path / "out")])

    assert result.exit_code == 2, result.output
    assert "Traceback" not in result.output
    assert f"Invalid .docstrap config: {config}" in result.output
    assert "ignore: true" in result.output


def test_tag_reports_metadata_error_without_traceback(
    tmp_path: Path, monkeypatch, user_dirs: Path
) -> None:
    # `tag` registers the document before it sets tags, so without a
    # throwaway home every run left a row in the real metadata store.
    from docstrap import metadata as meta

    document = tmp_path / "note.md"
    document.write_text("# Note\n", encoding="utf-8")

    def fail_set_tags(*args, **kwargs):
        raise meta.MetadataError("metadata store rejected tags")

    monkeypatch.setattr(meta, "set_tags", fail_set_tags)

    result = runner.invoke(app, ["tag", str(document), "review"])

    assert result.exit_code == 2, result.output
    assert "Traceback" not in result.output
    assert "metadata store rejected tags" in result.output
