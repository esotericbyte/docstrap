"""No `index.md` in a docs tree: a build composes section pages ephemerally.

A build composes its section pages in its own directories, never as files
in a project's documentation tree.
`test_a_build_writes_no_index_file_into_a_tree` is the whole of it: hash
nothing, walk everything, and require that no file of that name exists
anywhere the build could have reached. `test_build_writes_no_project_files.py`
proves the larger invariant the same way; this one is named for the
file, so a regression is obvious from the failure line alone.

The middle case is the one that made the defect survive: a build that
met a file already in the tree *skipped composing* for that directory, so
the first build's output became permanent and went stale in place. There
is no skip now, and `test_the_composed_page_wins_over_a_file_left_in_the_tree`
is that.
"""
from __future__ import annotations

import os
from pathlib import Path

from docstrap import errorlog
from docstrap.config import load
from docstrap.layouts import markdown
from docstrap.scan import ScannedProject, scan
from docstrap.sphinx import composed

PROJECT_PATH = "packages/widget"

DOCSTRAP_YAML = f"""\
version: 1
title: Sample Store
projects:
  - path: {PROJECT_PATH}
    title: Widget
    layout: markdown
    docs_root: docs
"""

TREE = {
    f"{PROJECT_PATH}/docs/guide.md": "# Guide\n\nTop level.\n",
    f"{PROJECT_PATH}/docs/specs/census.md": "# Census\n\nA spec.\n",
    f"{PROJECT_PATH}/docs/specs/ledger.md": "# Ledger\n\nAnother spec.\n",
    f"{PROJECT_PATH}/docs/plans/rollout/phase.md": "# Phase\n\nNested deeper.\n",
}

def _store(tmp_path: Path, files: dict[str, str] | None = None) -> Path:
    store = tmp_path / "store"
    for relative, content in (files or TREE).items():
        path = store / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    (store / ".docstrap").write_text(DOCSTRAP_YAML, encoding="utf-8")
    return store


def _one(store: Path) -> ScannedProject:
    return [p for p in scan(load(store / ".docstrap")) if p.kind == "project"][0]


def _index_files_under(root: Path) -> list[str]:
    """Every `index.md`/`index.rst` below ``root``, links included.

    A symlink counts here where it would not in
    `test_indexes_are_transient.py`: that file asks what the build
    *wrote*, and this one asks whether such a file exists at all, on
    either side of a link.
    """
    return sorted(
        str(Path(current, name).relative_to(root))
        for current, _dirs, files in os.walk(root, followlinks=False)
        for name in files
        if name in ("index.md", "index.rst")
    )


# --- end one: a build writes none ---------------------------------------------


def test_a_build_writes_no_index_file_into_a_tree(tmp_path: Path, user_dirs: Path):
    """The rule, over the project and over everything the build made.

    The docs tree has the shape that did the damage — nested
    subdirectories, none carrying an index — and the site that comes out
    has a page for every one of them.
    """
    store = _store(tmp_path)
    project = _one(store)
    out = tmp_path / "out"
    result = markdown.build(project, out)

    assert _index_files_under(store) == [], "a build wrote into the project"
    assert _index_files_under(out) == [], "a build wrote an index file of its own"

    # And the pages exist, as HTML, which is the half that is easy to
    # lose while satisfying the half above.
    for relative in ("index.html", "specs/index.html", "plans/rollout/index.html"):
        assert result.html_root.joinpath(relative).is_file(), relative


def test_the_composed_page_wins_over_a_file_left_in_the_tree(
    tmp_path: Path, user_dirs: Path
):
    """No "the user wrote their own index" skip, at any level.

    That skip is what let the first build's output stand forever. Each
    of these three directories holds a file of that name, and each gets
    the page docstrap composes: the root, a section, and a section
    nested below one.
    """
    store = _store(
        tmp_path,
        TREE | {
            f"{PROJECT_PATH}/docs/index.md": "# Stale root\n\nNOT-ON-THE-SITE\n",
            f"{PROJECT_PATH}/docs/specs/index.md": "# Stale specs\n\nNOT-ON-THE-SITE\n",
            f"{PROJECT_PATH}/docs/plans/rollout/index.md": (
                "# Stale rollout\n\nNOT-ON-THE-SITE\n"
            ),
        },
    )
    project = _one(store)
    out = tmp_path / "out"
    result = markdown.build(project, out)

    scratch = out / "_scratch" / project.slug
    for relative in ("", "specs", "plans/rollout"):
        marker = scratch / relative / composed.MARKER_NAME
        assert marker.is_file(), f"no composed page for {relative or 'the root'!r}"
        page = (result.html_root / relative / "index.html").read_text(encoding="utf-8")
        assert "NOT-ON-THE-SITE" not in page, relative

    # Not brought into the build, and not removed from the project: a
    # build reads a project, which includes not deleting from one.
    assert _index_files_under(scratch) == []
    assert _index_files_under(store) == [
        f"{PROJECT_PATH}/docs/index.md",
        f"{PROJECT_PATH}/docs/plans/rollout/index.md",
        f"{PROJECT_PATH}/docs/specs/index.md",
    ]


def test_an_ignored_index_file_is_a_warning_in_the_error_log_and_nothing_else(
    tmp_path: Path, user_dirs: Path
):
    """Ignored: not on the site, not in the result, one line in the error log.

    These files used to be reported on the project's landing page, above
    its listing, and in the build result the store's landing page and the
    CLI print beside every project. In a real tree with two dozen of them
    that notice was most of the page — an error where the documentation
    should have been. An ignored file is not an error, so the build says
    nothing about it in its output; the error log keeps the names for
    whoever wants to clear them out.
    """
    store = _store(
        tmp_path,
        TREE | {
            f"{PROJECT_PATH}/docs/index.md": "# Stale\n",
            f"{PROJECT_PATH}/docs/specs/index.rst": "Stale\n=====\n",
        },
    )
    project = _one(store)
    result = markdown.build(project, tmp_path / "out")

    assert "index" not in result.notes, result.notes
    landing = (result.html_root / "index.html").read_text(encoding="utf-8")
    assert "Not published" not in landing
    assert "specs/index.rst" not in landing
    # The real output is all still there.
    for expected in ("guide.html", "specs/index.html", "plans/index.html"):
        assert f'href="{expected}"' in landing, expected

    log = errorlog.path().read_text(encoding="utf-8")
    assert "WARNING" in log
    assert project.slug in log
    assert "index.md" in log and "specs/index.rst" in log


def test_a_document_is_not_dropped_from_the_site_by_any_of_this(
    tmp_path: Path, user_dirs: Path
):
    """The harm the committed files did, checked directly.

    A committed `index.md` in a real docs tree listed two of the three
    documents beside it, so the third was in no toctree and off the
    site. A composed page is read from the file index, so every document
    in a directory is on that directory's page — there is no hand-kept
    list to fall behind.
    """
    store = _store(
        tmp_path,
        TREE | {
            f"{PROJECT_PATH}/docs/specs/index.md": (
                "# Specs\n\n"
                "```{toctree}\n"
                "census\n"
                "```\n"
            ),
            f"{PROJECT_PATH}/docs/specs/omitted.md": "# Omitted\n\nThe third one.\n",
        },
    )
    result = markdown.build(_one(store), tmp_path / "out")

    page = (result.html_root / "specs" / "index.html").read_text(encoding="utf-8")
    for expected in ("census.html", "ledger.html", "omitted.html"):
        assert f'href="{expected}"' in page, f"{expected} is off the site"
        assert (result.html_root / "specs" / expected).is_file()
