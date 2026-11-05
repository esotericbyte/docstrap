"""A project's README reaches the site, and nothing else comes with it.

Every entry in a `.docstrap` sets `docs_root: docs`, so a build only ever
saw `<project>/docs`. The README one level above it was absent from the
site docstrap generated — docstrap's own included. The one way to reach
it was to drop `docs_root` and take the entire project root along, which
is why the capability looked missing rather than merely expensive.

The README joins the project's documents; it does not become or replace
the landing page. These tests run real sphinx-builds and read the HTML
that comes out, because the question is not whether a path was computed
but whether the README is on the page — and whether the rest of the
project root stayed off it.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from docstrap.config import load
from docstrap.layouts import markdown
from docstrap.scan import ScannedProject, find_readme, scan

PROJECT_PATH = "packages/widget"
PROJECT_SLUG = "packages__widget"

DOCSTRAP_YAML = f"""\
version: 1
title: Sample Store
projects:
  - path: {PROJECT_PATH}
    title: Widget
    layout: markdown
    docs_root: docs
"""

README_MD = """\
# Widget

Install it, then run it. This sentence is only in the README.
"""

DOCS_OVERVIEW = """\
# Widget documentation

A document in docs_root, which the README does not replace.
"""


def _store(tmp_path: Path, files: dict[str, str], config: str = DOCSTRAP_YAML) -> Path:
    """A real store on disk: the named files, plus a `.docstrap`."""
    store = tmp_path / "store"
    store.mkdir(parents=True, exist_ok=True)
    for relative, content in files.items():
        path = store / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    (store / ".docstrap").write_text(config, encoding="utf-8")
    return store


def _projects(store: Path) -> list[ScannedProject]:
    return [p for p in scan(load(store / ".docstrap")) if p.kind == "project"]


def _one(store: Path) -> ScannedProject:
    projects = _projects(store)
    assert [p.slug for p in projects] == [PROJECT_SLUG]
    return projects[0]


def _build(tmp_path: Path, files: dict[str, str], config: str = DOCSTRAP_YAML):
    """Scan and build one project; return (built HTML root, scratch dir)."""
    project = _one(_store(tmp_path, files, config))
    out = tmp_path / "out"
    result = markdown.build(project, out)
    return result.html_root, out / "_scratch" / project.slug


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# --- the four shapes the site has to get right -------------------------------


def test_a_project_with_a_readme_and_a_docs_dir_publishes_both(
    tmp_path: Path, user_dirs: Path
):
    """Both appear. The README is another document, not a replacement."""
    html_root, _ = _build(
        tmp_path,
        {
            f"{PROJECT_PATH}/README.md": README_MD,
            f"{PROJECT_PATH}/docs/overview.md": DOCS_OVERVIEW,
            f"{PROJECT_PATH}/docs/guide.md": "# Guide\n\nA second document.\n",
        },
    )

    assert "This sentence is only in the README." in _text(html_root / "readme.html")

    assert "A document in docs_root, which the README does not replace." in _text(
        html_root / "overview.html"
    )

    landing = _text(html_root / "index.html")
    assert 'href="readme.html"' in landing, "the README is missing from the toctree"
    assert 'href="overview.html"' in landing, "the docs_root document is missing"
    assert (html_root / "guide.html").is_file(), "the docs_root documents still build"


def test_a_project_with_a_readme_and_no_docs_dir_still_publishes_the_readme(
    tmp_path: Path, user_dirs: Path
):
    """Nothing under docs_root is not a reason to drop the README."""
    html_root, _ = _build(tmp_path, {f"{PROJECT_PATH}/README.md": README_MD})

    assert "This sentence is only in the README." in _text(html_root / "readme.html")
    assert 'href="readme.html"' in _text(html_root / "index.html")


def test_a_readme_txt_is_published_as_the_literal_text_it_is(
    tmp_path: Path, user_dirs: Path
):
    """`.txt` is not markdown, so it is wrapped rather than parsed.

    The generated conf.py maps only `.md`/`.rst` to a parser. Registering
    `.txt` would reinterpret every plain-text file in a docs tree as
    markup; wrapping this one file publishes it as written.
    """
    html_root, _ = _build(
        tmp_path,
        {
            f"{PROJECT_PATH}/README.txt": (
                "Widget\n"
                "======\n"
                "\n"
                "Run *widget* --help. Nothing here is markdown.\n"
                "\n"
                "```\n"
                "Not a fence either -- the wrapper's own fence outruns it.\n"
                "```\n"
            ),
        },
    )

    page = _text(html_root / "readme.html")
    assert "Run *widget* --help. Nothing here is markdown." in page
    assert "<em>widget</em>" not in page, "the text was parsed as markup"
    assert "Not a fence either" in page, "backticks in the text closed the wrapper"
    assert "Widget README" in page, "the wrapper gives the page a title"


def test_a_project_with_neither_gets_no_readme_page(tmp_path: Path, user_dirs: Path):
    """No README, no invented one."""
    html_root, scratch = _build(
        tmp_path, {f"{PROJECT_PATH}/docs/overview.md": DOCS_OVERVIEW}
    )

    assert not (html_root / "readme.html").exists()
    assert not (scratch / "readme.md").exists()
    assert 'href="overview.html"' in _text(html_root / "index.html")


# --- and nothing else crosses over -------------------------------------------


def test_only_the_readme_crosses_from_the_project_root(
    tmp_path: Path, user_dirs: Path
):
    """The mechanism brings in one file, not the directory holding it."""
    html_root, scratch = _build(
        tmp_path,
        {
            f"{PROJECT_PATH}/README.md": README_MD,
            f"{PROJECT_PATH}/NOTES.md": "# Notes\n\nNot documentation.\n",
            f"{PROJECT_PATH}/CHANGELOG.md": "# Changelog\n\nNot documentation.\n",
            f"{PROJECT_PATH}/docs/overview.md": DOCS_OVERVIEW,
        },
    )

    assert (html_root / "readme.html").is_file()
    names = {entry.name for entry in scratch.iterdir()}
    assert "NOTES.md" not in names and "CHANGELOG.md" not in names
    assert not (html_root / "NOTES.html").exists()
    assert not (html_root / "CHANGELOG.html").exists()


def test_the_readme_does_not_take_a_docname_a_document_already_claimed(
    tmp_path: Path, user_dirs: Path
):
    """A `docs/readme.md` keeps its name; the project README gets another."""
    html_root, _ = _build(
        tmp_path,
        {
            f"{PROJECT_PATH}/README.md": README_MD,
            f"{PROJECT_PATH}/docs/overview.md": DOCS_OVERVIEW,
            f"{PROJECT_PATH}/docs/readme.md": (
                "# Reading the docs\n\nA document that happens to be named readme.\n"
            ),
        },
    )

    assert "A document that happens to be named readme." in _text(
        html_root / "readme.html"
    )
    assert "This sentence is only in the README." in _text(
        html_root / "project-readme.html"
    )


# --- what counts as a README -------------------------------------------------


@pytest.mark.parametrize("name", ["README.md", "readme.md", "Readme.MD"])
def test_a_readme_is_matched_whatever_its_case(tmp_path: Path, name: str):
    store = _store(tmp_path, {f"{PROJECT_PATH}/{name}": README_MD})
    assert _one(store).readme_path == store / PROJECT_PATH / name


def test_a_markdown_readme_is_preferred_over_a_text_one(tmp_path: Path):
    """Both on disk is not ambiguous: markdown is the richer document."""
    store = _store(
        tmp_path,
        {
            f"{PROJECT_PATH}/README.md": README_MD,
            f"{PROJECT_PATH}/README.txt": "Plain text.\n",
        },
    )
    assert _one(store).readme_path == store / PROJECT_PATH / "README.md"


def test_a_readme_already_inside_docs_dir_is_not_added_a_second_time(tmp_path: Path):
    """A related directory with no docs_root already publishes its README."""
    config = """\
version: 1
title: Sample Store
layout: markdown
docs_root: .

related_directories:
  - path: notes
    title: Notes
"""
    store = _store(
        tmp_path,
        {"README.md": README_MD, "notes/README.md": README_MD},
        config=config,
    )
    for project in scan(load(store / ".docstrap")):
        assert project.readme_path is None, project.slug


def test_a_readme_whose_suffix_the_config_excludes_is_not_published(tmp_path: Path):
    """`exclude_file_suffixes` is not overridden by being called README."""
    config = DOCSTRAP_YAML + 'exclude_file_suffixes: [".txt"]\n'
    store = _store(tmp_path, {f"{PROJECT_PATH}/README.txt": "Plain text.\n"}, config)
    assert _one(store).readme_path is None


def test_a_project_that_declares_itself_ignored_stays_ignored(tmp_path: Path):
    """An ignored subtree contributes no documents, README included."""
    store = _store(
        tmp_path,
        {
            f"{PROJECT_PATH}/README.md": README_MD,
            f"{PROJECT_PATH}/.docstrap": "version: 1\ntitle: Widget\nignore: true\n",
        },
    )
    assert _projects(store) == []


def test_find_readme_looks_no_deeper_than_the_project_root(tmp_path: Path):
    """A README nested somewhere in the tree is not the project's README."""
    root = tmp_path / "project"
    (root / "src" / "vendor").mkdir(parents=True)
    (root / "src" / "vendor" / "README.md").write_text(README_MD, encoding="utf-8")
    assert find_readme(root, root / "docs") is None
