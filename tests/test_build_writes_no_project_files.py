"""A build reads a project. It never writes into one.

The defect these tests exist for: the markdown layout populated its
scratch directory with symlinks into the project and then walked that
directory with ``followlinks=True``, composing an `index.md` into every
subdirectory that lacked one. The walk followed the symlinks out of the
build area, so the writes landed in the repositories. Fifty-five such
files ended up tracked across five of them, one batch committed with the
message "index.md in docs for docstrap maybe are being added to the
repo? this does not look right but moving forwared".

The first test is the one that matters: hash the project tree, build it,
hash it again, and require the two to be identical. It is written
against a fixture whose docs tree has the shape that did the damage —
subdirectories with no index of their own — so a regression that
reintroduces the symlinked scratch tree fails here rather than in
somebody's git status.

The rest hold the things that must survive the fix: the sidebar keeps
its section pages, an index file already sitting in a tree is left on
disk and kept out of the site, and a declared docs_root that does not
exist is reported rather than created.

Since 0.0.4 a section page is not a file at all. What the build puts in
its scratch tree is a zero-byte marker whose parser composes the page
during the Sphinx run, so the assertions below are about markers and
about the HTML that came out — never about markdown, because a build
produces none. `test_no_markdown_is_produced_anywhere` holds that.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

from docstrap.config import load
from docstrap.layouts import markdown
from docstrap.scan import ScannedProject, scan
from docstrap.sphinx import composed

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

#: A docs tree of the shape that was being written into: nested
#: directories, none of which carries an index of its own.
TREE = {
    f"{PROJECT_PATH}/docs/guide.md": "# Guide\n\nTop level.\n",
    f"{PROJECT_PATH}/docs/specs/census.md": "# Census\n\nA spec.\n",
    f"{PROJECT_PATH}/docs/specs/ledger.md": "# Ledger\n\nAnother spec.\n",
    f"{PROJECT_PATH}/docs/plans/rollout/phase.md": "# Phase\n\nNested deeper.\n",
}


def _store(tmp_path: Path, files: dict[str, str], config: str = DOCSTRAP_YAML) -> Path:
    store = tmp_path / "store"
    store.mkdir(parents=True, exist_ok=True)
    for relative, content in files.items():
        path = store / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    (store / ".docstrap").write_text(config, encoding="utf-8")
    return store


def _one(store: Path) -> ScannedProject:
    projects = [p for p in scan(load(store / ".docstrap")) if p.kind == "project"]
    assert [p.slug for p in projects] == [PROJECT_SLUG]
    return projects[0]


def _fingerprint(root: Path) -> dict[str, str]:
    """Every path under ``root``, with a digest of each file's bytes.

    Directories and symlinks are recorded too — a build that created a
    directory or replaced a link would change this map without changing
    any file's content. The walk does not follow links, so docstrap's
    linked storage is not mistaken for project content.
    """
    seen: dict[str, str] = {}
    for current, dirs, files in os.walk(root, followlinks=False):
        here = Path(current)
        for name in sorted(dirs):
            path = here / name
            key = str(path.relative_to(root))
            seen[key] = f"link:{os.readlink(path)}" if path.is_symlink() else "dir"
        for name in sorted(files):
            path = here / name
            key = str(path.relative_to(root))
            if path.is_symlink():
                seen[key] = f"link:{os.readlink(path)}"
            else:
                seen[key] = hashlib.sha256(path.read_bytes()).hexdigest()
    return seen


# --- the invariant -----------------------------------------------------------


def test_a_build_leaves_the_project_tree_byte_identical(
    tmp_path: Path, user_dirs: Path
):
    """The whole point. Build it; the repository must not have moved."""
    store = _store(tmp_path, TREE)
    project = _one(store)
    project_root = store / PROJECT_PATH

    before = _fingerprint(project_root)
    markdown.build(project, tmp_path / "out")
    after = _fingerprint(project_root)

    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    changed = sorted(k for k in before if k in after and before[k] != after[k])
    assert added == [], f"the build created these in the project: {added}"
    assert removed == [], f"the build removed these from the project: {removed}"
    assert changed == [], f"the build modified these in the project: {changed}"


def test_the_build_writes_no_index_into_the_projects_subdirectories(
    tmp_path: Path, user_dirs: Path
):
    """Named for the file that was appearing: `<docs>/<section>/index.md`."""
    store = _store(tmp_path, TREE)
    markdown.build(_one(store), tmp_path / "out")

    docs = store / PROJECT_PATH / "docs"
    assert not (docs / "specs" / "index.md").exists()
    assert not (docs / "plans" / "index.md").exists()
    assert not (docs / "plans" / "rollout" / "index.md").exists()
    assert not (docs / "index.md").exists()


def test_no_directory_in_the_build_is_a_symlink(tmp_path: Path, user_dirs: Path):
    """The structural half of the fix, asserted structurally.

    A symlinked directory in the scratch tree is the hole the writes went
    through. There is not supposed to be one, so there is nothing to
    write through even if some later walk follows links again.
    """
    store = _store(tmp_path, TREE)
    project = _one(store)
    out = tmp_path / "out"
    markdown.build(project, out)

    scratch = out / "_scratch" / project.slug
    linked = [
        str(Path(current, name).relative_to(scratch))
        for current, dirs, _files in os.walk(scratch, followlinks=False)
        for name in dirs
        if Path(current, name).is_symlink()
    ]
    assert linked == [], f"symlinked directories in the build: {linked}"


def test_a_generated_write_aimed_outside_the_build_is_refused(
    tmp_path: Path, user_dirs: Path
):
    """The executable half of the invariant, exercised directly.

    Nothing in the layout can reach this today. It is the backstop for
    the change that reintroduces a symlinked directory without noticing.
    """
    import pytest

    from docstrap.layouts.base import LayoutError

    project_dir = tmp_path / "somebodys-repo"
    project_dir.mkdir()
    build_root = tmp_path / "build"
    build_root.mkdir()
    (build_root / "section").symlink_to(project_dir)

    with pytest.raises(LayoutError, match="never writes into one"):
        markdown._write_generated(
            build_root / "section" / "index.md", "# Nope\n", build_root
        )
    assert not (project_dir / "index.md").exists()


def test_a_symlinked_directory_inside_the_docs_tree_is_not_written_through(
    tmp_path: Path, user_dirs: Path
):
    """The defect's own shape, one level in.

    A docs tree that itself symlinks a directory from elsewhere is the
    case the old walk handled by writing into wherever it pointed. The
    mirror gives that directory a real home in the build and the target
    is untouched.
    """
    store = _store(tmp_path, TREE)
    outside = tmp_path / "shared-notes"
    outside.mkdir()
    (outside / "shared.md").write_text("# Shared\n\nFrom outside.\n", encoding="utf-8")
    (store / PROJECT_PATH / "docs" / "notes").symlink_to(outside)

    before = _fingerprint(outside)
    project = _one(store)
    out = tmp_path / "out"
    result = markdown.build(project, out)

    assert _fingerprint(outside) == before, "written through the symlink"
    assert not (outside / "index.md").exists()
    assert (
        out / "_scratch" / project.slug / "notes" / composed.MARKER_NAME
    ).is_file()
    assert (result.html_root / "notes" / "index.html").is_file()
    assert (result.html_root / "notes" / "shared.html").is_file()


def test_a_symlink_cycle_terminates(tmp_path: Path, user_dirs: Path):
    """A docs tree pointing back at itself is a build, not a hang."""
    store = _store(tmp_path, TREE)
    docs = store / PROJECT_PATH / "docs"
    (docs / "specs" / "loop").symlink_to(docs)

    project = _one(store)
    result = markdown.build(project, tmp_path / "out")
    assert (result.html_root / "index.html").is_file()


def test_two_directories_pointing_at_one_target_both_get_a_section_page(
    tmp_path: Path, user_dirs: Path
):
    """Two siblings resolving to the same place are not a cycle.

    The parent's toctree lists both, so composing a page for only the
    first would leave the second's entry pointing at nothing.
    """
    store = _store(tmp_path, TREE)
    shared = tmp_path / "shared"
    shared.mkdir()
    (shared / "doc.md").write_text("# Shared doc\n", encoding="utf-8")
    docs = store / PROJECT_PATH / "docs"
    (docs / "first").symlink_to(shared)
    (docs / "second").symlink_to(shared)

    project = _one(store)
    out = tmp_path / "out"
    result = markdown.build(project, out)

    scratch = out / "_scratch" / project.slug
    assert (scratch / "first" / composed.MARKER_NAME).is_file()
    assert (scratch / "second" / composed.MARKER_NAME).is_file()
    assert not (shared / "index.md").exists()
    assert (result.html_root / "first" / "index.html").is_file()
    assert (result.html_root / "second" / "index.html").is_file()


# --- and the site is the same ------------------------------------------------


def test_the_section_pages_are_still_in_the_build_and_on_the_page(
    tmp_path: Path, user_dirs: Path
):
    """Where the page lives changed; the navigation did not.

    It is now HTML and only ever HTML, composed during the Sphinx run
    from the file index. What the build puts in the scratch tree for it
    is an empty marker carrying no content at all.
    """
    store = _store(tmp_path, TREE)
    project = _one(store)
    out = tmp_path / "out"
    result = markdown.build(project, out)

    scratch = out / "_scratch" / project.slug
    for relative in ("specs", "plans", "plans/rollout"):
        marker = scratch / relative / composed.MARKER_NAME
        assert marker.is_file(), f"no section marker at {relative}"
        assert not marker.is_symlink()
        assert marker.read_bytes() == b"", "a marker carries no content"

    section = (result.html_root / "specs" / "index.html").read_text(encoding="utf-8")
    assert 'href="census.html"' in section
    assert 'href="ledger.html"' in section

    landing = (result.html_root / "index.html").read_text(encoding="utf-8")
    assert 'href="specs/index.html"' in landing
    assert 'href="plans/index.html"' in landing
    assert (result.html_root / "plans" / "rollout" / "index.html").is_file()


def test_a_section_index_in_the_tree_does_not_become_the_section_page(
    tmp_path: Path, user_dirs: Path
):
    """The exception that used to live here, removed.

    A directory holding an `index.md` was skipped, so the page docstrap
    had written into it the first time was never rewritten and went
    stale in place. Now every section gets a composed page and the file
    in the tree is not published at all — it is not allowed to be there.
    """
    store = _store(
        tmp_path,
        TREE | {
            f"{PROJECT_PATH}/docs/specs/index.md": (
                "# The specs, introduced by hand\n\n"
                "This sentence was written by the author; no build composed it.\n"
            ),
        },
    )
    project = _one(store)
    out = tmp_path / "out"
    result = markdown.build(project, out)

    page = (result.html_root / "specs" / "index.html").read_text(encoding="utf-8")
    assert "This sentence was written by the author; no build composed it." not in page
    assert 'href="census.html"' in page and 'href="ledger.html"' in page

    # Not published, and not touched either: the file is still on disk.
    assert (store / PROJECT_PATH / "docs" / "specs" / "index.md").is_file()
    scratch = out / "_scratch" / project.slug
    assert not (scratch / "specs" / "index.md").exists()
    assert (scratch / "specs" / composed.MARKER_NAME).is_file()


def test_an_index_in_the_tree_does_not_become_the_landing_page(
    tmp_path: Path, user_dirs: Path
):
    """The same rule at the root, where it supersedes an older exception.

    A project's own `index.md` used to open its site. A documentation
    tree holds no index.md at all.
    """
    store = _store(
        tmp_path,
        TREE | {
            f"{PROJECT_PATH}/docs/index.md": (
                "# Widget\n\nThe hand-written landing, with its own narrative.\n"
            ),
        },
    )
    result = markdown.build(_one(store), tmp_path / "out")

    landing = (result.html_root / "index.html").read_text(encoding="utf-8")
    assert "The hand-written landing, with its own narrative." not in landing
    assert 'href="specs/index.html"' in landing
    assert (store / PROJECT_PATH / "docs" / "index.md").is_file()


# --- a missing docs directory ------------------------------------------------


def test_a_missing_docs_root_is_reported_and_not_created(
    tmp_path: Path, user_dirs: Path
):
    """The placeholder stub was the same defect in a smaller form."""
    store = _store(tmp_path, {f"{PROJECT_PATH}/README.md": "# Widget\n\nRead me.\n"})
    project = _one(store)
    result = markdown.build(project, tmp_path / "out")

    assert not (store / PROJECT_PATH / "docs").exists(), (
        "the build created a directory in the project"
    )
    assert "does not exist" in result.notes
    landing = (result.html_root / "index.html").read_text(encoding="utf-8")
    assert "No documentation directory yet" in landing
    assert (result.html_root / "readme.html").is_file(), (
        "a project with no docs_root still publishes its README"
    )
