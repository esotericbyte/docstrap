from __future__ import annotations

from pathlib import Path

from docstrap.build import build_stores


SPHINX_CONF = """\
project = "Sphinx Store"
extensions = ["myst_parser"]
master_doc = "index"
source_suffix = {".md": "markdown"}
html_theme = "alabaster"
"""


def _write_docstrap(root: Path, *, title: str, layout: str) -> Path:
    docs = root / "docs"
    docs.mkdir(parents=True)
    # The sphinx layout runs the project's own conf.py, whose master_doc
    # is `index`. The markdown layout composes its landing page, and a
    # docs tree is not allowed to hold an `index.md` at all.
    name = "index.md" if layout == "sphinx" else "overview.md"
    (docs / name).write_text(f"# {title}\n\nBuilt from {layout}.\n", encoding="utf-8")
    (root / ".docstrap").write_text(
        f"version: 1\ntitle: {title}\nlayout: {layout}\ndocs_root: docs\n",
        encoding="utf-8",
    )
    return root / ".docstrap"


def test_sphinx_builds_use_docstrap_environment_not_path(tmp_path: Path, monkeypatch):
    """A uv tool install puts Sphinx beside docstrap, not necessarily on PATH."""
    path_without_sphinx = tmp_path / "bin"
    path_without_sphinx.mkdir()
    monkeypatch.setenv("PATH", str(path_without_sphinx))

    markdown_config = _write_docstrap(
        tmp_path / "markdown-store",
        title="Markdown Store",
        layout="markdown",
    )
    sphinx_config = _write_docstrap(
        tmp_path / "sphinx-store",
        title="Sphinx Store",
        layout="sphinx",
    )
    (sphinx_config.parent / "docs" / "conf.py").write_text(SPHINX_CONF, encoding="utf-8")

    out = tmp_path / "site"
    report = build_stores([markdown_config, sphinx_config], out)

    assert report.load_errors == []
    assert [store_report.failures for _, _, store_report in report.per_store] == [[], []]
    assert (out / "index.html").is_file()
    assert (out / "markdown-store" / "markdown-store" / "index.html").is_file()
    assert (out / "sphinx-store" / "sphinx-store" / "index.html").is_file()
