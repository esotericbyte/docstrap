"""An index is recomputed, never stored, and never markdown.

The section pages a build composes are transient and transparent. An
index is HTML only, never an `index.md`; any such file is a transient
part of the system, not a stored one, and files are indexed in a
database table with paths and hashes. Sphinx's toctree being a markdown
construct is no reason to keep a markdown step: the output is HTML, so
no markdown is kept for an index.

Four properties follow and each has a test here.

1. **No markdown, at any stage.** Not in a project, not in the build, not
   as a temporary file. `test_a_build_produces_no_markdown_anywhere` is
   the one that would have caught the whole defect, and it looks at every
   file a build touches rather than at the places the bug was known to
   reach.
2. **Navigation survives.** The rendered site keeps its sections, its
   section pages and its sidebar — the thing a literal reading of "HTML
   only" could have cost, and did not.
3. **The index is a table.** A directory's contents are answerable from
   `file_index` with the tree unavailable, which is what makes the pages
   recomputable and a watcher possible.
4. **Nothing is cached.** A document that appears is on the next build's
   page with no invalidation step, because there is nothing to
   invalidate.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from docstrap import fileindex, metadata, paths, sectionindex
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


def _markdown_written_by(root: Path) -> list[str]:
    """Every markdown file under ``root`` that is not a link to a document.

    A symlink is the project's own file, seen through the build. A real
    file with a markdown suffix is something the build made, which is the
    thing that must not exist.
    """
    return sorted(
        str(Path(current, name).relative_to(root))
        for current, _dirs, files in os.walk(root, followlinks=False)
        for name in files
        if name.endswith((".md", ".markdown", ".rst"))
        and not Path(current, name).is_symlink()
    )


# --- 1. no markdown, at any stage --------------------------------------------


def test_a_build_produces_no_markdown_anywhere(tmp_path: Path, user_dirs: Path):
    """The rule, checked over everything a build touches.

    Not "no index.md in the project" and not "no index.md in the scratch
    tree" — no generated markdown at all, in either place or in the HTML
    output. A composed page that reappeared as a file of any markdown
    suffix, under any name, fails here.
    """
    store = _store(tmp_path)
    project = _one(store)
    out = tmp_path / "out"
    result = markdown.build(project, out)

    assert _markdown_written_by(out) == [], "the build wrote markdown"
    assert _markdown_written_by(store / PROJECT_PATH / "docs") == [
        "guide.md",
        "plans/rollout/phase.md",
        "specs/census.md",
        "specs/ledger.md",
    ], "the project holds its own documents and nothing else"
    assert result.html_root.joinpath("specs", "index.html").is_file()


def test_the_only_thing_a_section_gets_in_the_build_is_an_empty_marker(
    tmp_path: Path, user_dirs: Path
):
    """What replaced the markdown carries nothing that can go stale."""
    store = _store(tmp_path)
    project = _one(store)
    out = tmp_path / "out"
    markdown.build(project, out)

    scratch = out / "_scratch" / project.slug
    markers = sorted(
        str(p.relative_to(scratch)) for p in scratch.rglob(f"*{composed.MARKER_SUFFIX}")
    )
    assert markers == [
        f"index{composed.MARKER_SUFFIX}",
        f"plans/index{composed.MARKER_SUFFIX}",
        f"plans/rollout/index{composed.MARKER_SUFFIX}",
        f"specs/index{composed.MARKER_SUFFIX}",
    ]
    for relative in markers:
        assert (scratch / relative).read_bytes() == b""


def test_an_aggregate_page_is_composed_without_markdown_too(
    tmp_path: Path, user_dirs: Path
):
    """A store's landing page lists projects, so it is an index as well.

    It was the second markdown file a build wrote and it went the same
    way; its model travels in the generated conf.py instead.
    """
    from docstrap.build import build_all

    store = _store(tmp_path)
    out = tmp_path / "out"
    report = build_all(load(store / ".docstrap"), out)

    assert _markdown_written_by(out) == []
    landing = (out / "index.html").read_text(encoding="utf-8")
    assert "Sample Store" in landing
    assert f'href="{PROJECT_SLUG}/index.html"' in landing
    assert [r.project_slug for r in report.successes] == [PROJECT_SLUG]


# --- 2. navigation survives ---------------------------------------------------


def test_the_site_still_has_its_sections_and_its_sidebar(
    tmp_path: Path, user_dirs: Path
):
    """The cost a literal reading could have had, and did not."""
    store = _store(tmp_path)
    result = markdown.build(_one(store), tmp_path / "out")

    section = (result.html_root / "specs" / "index.html").read_text(encoding="utf-8")
    assert "Specs" in section
    assert 'href="census.html"' in section
    assert 'href="ledger.html"' in section

    # The sidebar of an ordinary document carries the whole tree, so a
    # reader is never on a page with no way out of it.
    page = (result.html_root / "specs" / "census.html").read_text(encoding="utf-8")
    sidebar = page.split('class="sidebar-tree"', 1)[-1]
    for expected in ("Specs", "Ledger", "Plans", "Rollout", "Guide"):
        assert expected in sidebar, f"{expected} missing from the sidebar"


def test_an_index_left_in_a_tree_is_neither_published_nor_touched(
    tmp_path: Path, user_dirs: Path
):
    """A documentation tree holds no index.md at all.

    A tree that still holds one is the case this covers, because the
    files exist in repositories today. The landing page is composed like
    any other, the file is not brought into the build, and it is left on
    disk byte for byte — a build reads a project and writes nothing into
    one, and that includes not deleting.
    """
    narrative = "# Widget\n\nThe hand-written landing, with its own grid cards.\n"
    store = _store(
        tmp_path, TREE | {f"{PROJECT_PATH}/docs/index.md": narrative}
    )
    project = _one(store)
    out = tmp_path / "out"
    result = markdown.build(project, out)

    landing = (result.html_root / "index.html").read_text(encoding="utf-8")
    assert "The hand-written landing, with its own grid cards." not in landing
    assert 'href="specs/index.html"' in landing

    # Their file, byte for byte, and a marker where their file is not.
    assert (store / PROJECT_PATH / "docs" / "index.md").read_text(
        encoding="utf-8"
    ) == narrative
    scratch = out / "_scratch" / project.slug
    assert not (scratch / "index.md").exists()
    assert (scratch / composed.MARKER_NAME).is_file()


def test_a_section_with_nothing_in_it_says_so(tmp_path: Path, user_dirs: Path):
    """An empty section is a page that says it is empty, not a gap."""
    store = _store(tmp_path)
    (store / PROJECT_PATH / "docs" / "empty").mkdir()
    result = markdown.build(_one(store), tmp_path / "out")

    page = (result.html_root / "empty" / "index.html").read_text(encoding="utf-8")
    assert "(no documents in this section)" in page


# --- 3. the index is a table --------------------------------------------------


def test_a_directorys_contents_come_from_the_table_not_the_tree(
    tmp_path: Path, user_dirs: Path
):
    """The requirement in its strongest form: delete the tree, ask again.

    Everything a section page needs is a row. Nothing composes a page by
    looking at a directory, which is what lets the same composer serve a
    build, a report and a watcher that has only seen one event.
    """
    store = _store(tmp_path)
    project = _one(store)
    markdown.build(project, tmp_path / "out")

    shutil.rmtree(store)
    assert not store.exists()

    page = sectionindex.compose(project.slug, "specs/index")
    assert page.title == "Specs"
    assert [entry.docname for _caption, entries in page.groups for entry in entries] == [
        "specs/census",
        "specs/ledger",
    ]

    root = sectionindex.compose(project.slug, "index")
    assert root.title == "Widget"
    assert [caption for caption, _entries in root.groups] == [
        sectionindex.DOCS_CAPTION
    ]


def test_the_table_carries_a_path_and_a_hash_for_every_document(
    tmp_path: Path, user_dirs: Path
):
    """*"files can be indexed in a database table with paths and hashes."*"""
    store = _store(tmp_path)
    project = _one(store)
    markdown.build(project, tmp_path / "out")

    census = fileindex.get(project.slug, "specs/census")
    assert census is not None
    assert census.kind == fileindex.DOCUMENT
    assert Path(census.path) == (
        store / PROJECT_PATH / "docs" / "specs" / "census.md"
    ).resolve()
    assert census.content_hash == metadata.git_blob_hash(
        Path(census.path).read_bytes()
    )
    assert census.title == "Census"

    section = fileindex.get(project.slug, "specs/index")
    assert section is not None and section.kind == fileindex.SECTION
    assert Path(section.path) == (store / PROJECT_PATH / "docs" / "specs").resolve()


def test_an_indexed_path_is_always_in_the_project_never_in_the_build(
    tmp_path: Path, user_dirs: Path
):
    """Every row points at bytes that outlive the build that indexed them.

    Three things in the mirrored tree resolve somewhere other than the
    project if you take them at face value: a mirrored directory (the
    build made it), and a `.txt` README, whose generated wrapper is a
    build file standing in for a project one. Both are corrected from
    the map the mirror fills.
    """
    store = _store(
        tmp_path, {k: v for k, v in TREE.items()} | {
            f"{PROJECT_PATH}/README.txt": "Plain text, not markdown.\n",
        }
    )
    project = _one(store)
    out = tmp_path / "out"
    markdown.build(project, out)

    build_root = (out / "_scratch").resolve()
    for entry in fileindex.list_project(project.slug):
        assert not Path(entry.path).resolve().is_relative_to(build_root), (
            f"{entry.docname} is indexed at a path inside the build: {entry.path}"
        )

    readme = fileindex.get(project.slug, "readme")
    assert readme is not None
    assert Path(readme.path) == (store / PROJECT_PATH / "README.txt").resolve()


def test_one_path_can_be_indexed_and_forgotten_on_its_own(
    tmp_path: Path, user_dirs: Path
):
    """Written incrementally, because a watcher only ever knows one path.

    A planned filesystem watcher is the caller; this is the seam it needs.
    No whole-project pass, no invalidation, no cache to sweep.
    """
    store = _store(tmp_path)
    project = _one(store)
    markdown.build(project, tmp_path / "out")

    arrival = store / PROJECT_PATH / "docs" / "specs" / "tariff.md"
    arrival.write_text("# Tariff\n\nA third spec.\n", encoding="utf-8")
    fileindex.record(
        fileindex.Entry(
            project=project.slug,
            docname="specs/tariff",
            path=str(arrival.resolve()),
            parent_docname="specs/index",
            kind=fileindex.DOCUMENT,
            title="Tariff",
            sort_key="tariff.md",
            content_hash=metadata.git_blob_hash(arrival.read_bytes()),
        )
    )
    page = sectionindex.compose(project.slug, "specs/index")
    listed = [e.docname for _c, entries in page.groups for e in entries]
    assert listed == ["specs/census", "specs/ledger", "specs/tariff"]

    assert fileindex.forget_path(arrival) == 1
    page = sectionindex.compose(project.slug, "specs/index")
    listed = [e.docname for _c, entries in page.groups for e in entries]
    assert listed == ["specs/census", "specs/ledger"]


def test_a_rename_is_recognisable_by_the_documents_own_id(
    tmp_path: Path, user_dirs: Path
):
    """A file the metadata store knows keeps its identity across a move.

    The index does not keep a history of its own: it carries the id, and
    `documents` / `path_history` carry the history. That is why the
    column is there.
    """
    store = _store(tmp_path)
    project = _one(store)
    census = store / PROJECT_PATH / "docs" / "specs" / "census.md"
    document = metadata.create_document(
        project=project.slug, path=str(census), status="spec"
    )

    markdown.build(project, tmp_path / "out")
    indexed = fileindex.get(project.slug, "specs/census")
    assert indexed is not None and indexed.document_id == document.id

    renamed = census.with_name("census-2027.md")
    census.rename(renamed)
    metadata.record_move(document.id, str(renamed))
    markdown.build(project, tmp_path / "out")

    assert fileindex.get(project.slug, "specs/census") is None, (
        "the reconcile left a row for a document that moved"
    )
    moved = fileindex.get(project.slug, "specs/census-2027")
    assert moved is not None and moved.document_id == document.id


def test_a_rename_is_recognisable_by_content_for_a_file_with_no_document_row(
    tmp_path: Path, user_dirs: Path
):
    """The ordinary case: nobody tagged the file, so the hash is identity."""
    store = _store(tmp_path)
    project = _one(store)
    markdown.build(project, tmp_path / "out")

    before = fileindex.get(project.slug, "specs/census")
    assert before is not None and before.document_id is None

    census = store / PROJECT_PATH / "docs" / "specs" / "census.md"
    census.rename(census.with_name("headcount.md"))
    markdown.build(project, tmp_path / "out")

    same_bytes = fileindex.by_content_hash(before.content_hash)
    assert [e.docname for e in same_bytes] == ["specs/headcount"]


def test_the_index_is_a_table_of_its_own_and_not_content_observations():
    """Stated as a test because the alternative was a real proposal.

    `content_observations` is an append-only log hanging off a
    `documents` row. Indexing every file in a docs tree through it would
    mint a ULID per markdown file, in a store whose document rows are
    already mostly test residue. The shapes are checked here so that a
    later merge of the two has to argue with something.
    """
    assert "CREATE TABLE IF NOT EXISTS file_index" in metadata.SCHEMA
    assert "PRIMARY KEY (project, docname)" in metadata.SCHEMA
    # No foreign key: a derived projection must never be able to refuse a
    # write to the system of record.
    file_index_sql = metadata.SCHEMA.split("CREATE TABLE IF NOT EXISTS file_index", 1)[1]
    assert "REFERENCES" not in file_index_sql.split(";", 1)[0]


def test_dropping_the_index_costs_nothing_but_a_build(
    tmp_path: Path, user_dirs: Path
):
    """Derived and disposable, which is what makes it safe to keep here."""
    store = _store(tmp_path)
    project = _one(store)
    markdown.build(project, tmp_path / "out")

    assert fileindex.drop_project(project.slug) > 0
    assert fileindex.list_project(project.slug) == []

    result = markdown.build(project, tmp_path / "out")
    assert fileindex.get(project.slug, "specs/census") is not None
    assert 'href="census.html"' in (
        result.html_root / "specs" / "index.html"
    ).read_text(encoding="utf-8")


# --- 4. nothing is cached -----------------------------------------------------


def test_a_new_document_appears_with_no_invalidation_step(
    tmp_path: Path, user_dirs: Path
):
    """*"100 documents ... over several directories ... with even 50
    projects is not that much processing."* So it is recomputed, and
    there is no staleness to detect, no cache key and nothing to sweep.
    """
    store = _store(tmp_path)
    project = _one(store)
    out = tmp_path / "out"
    markdown.build(project, out)

    (store / PROJECT_PATH / "docs" / "specs" / "tariff.md").write_text(
        "# Tariff\n\nArrived after the first build.\n", encoding="utf-8"
    )
    result = markdown.build(project, out)

    page = (result.html_root / "specs" / "index.html").read_text(encoding="utf-8")
    assert 'href="tariff.html"' in page


def test_a_deleted_document_leaves_the_page_it_was_listed_on(
    tmp_path: Path, user_dirs: Path
):
    """The failure mode of the pages this replaced: they never refreshed.

    `beta/docs/specs/index.md` still says *(no documents in this section)*
    and then lists one, because the first build's output became permanent
    and the "user wrote their own index" check skipped it forever after.
    """
    store = _store(tmp_path)
    project = _one(store)
    out = tmp_path / "out"
    markdown.build(project, out)

    (store / PROJECT_PATH / "docs" / "specs" / "ledger.md").unlink()
    result = markdown.build(project, out)

    page = (result.html_root / "specs" / "index.html").read_text(encoding="utf-8")
    assert 'href="census.html"' in page
    assert 'href="ledger.html"' not in page
    assert fileindex.get(project.slug, "specs/ledger") is None


# --- the guard ----------------------------------------------------------------


PACKAGE = Path(paths.__file__).parent


def _sources() -> list[Path]:
    return sorted(PACKAGE.rglob("*.py"))


@pytest.mark.parametrize(
    "fingerprint",
    [
        "```{toctree}",          # the composed markdown a build used to write
        ":caption: Docs",        # the landing page's markdown toctree
        ":maxdepth: 2",          # both of them
    ],
)
def test_no_module_composes_a_markdown_index(fingerprint: str):
    """No markdown index survives anywhere in the package.

    `generated_indexes.py` is the one exception and it is deliberate: it
    reproduces the bytes builds up to 0.0.3 wrote so that a committed
    file can still be recognised as docstrap's and deleted. It composes
    nothing and nothing calls it to write.
    """
    offenders = [
        path.name
        for path in _sources()
        if path.name != "generated_indexes.py"
        and fingerprint in path.read_text(encoding="utf-8")
    ]
    assert offenders == [], fingerprint


def test_the_frozen_recogniser_is_never_written_by_anything():
    """It reads. A caller that wrote its bytes would be writing markdown."""
    from docstrap import generated_indexes

    source = Path(generated_indexes.__file__).read_text(encoding="utf-8")
    assert "write_text" not in source
    assert "write_bytes" not in source

    callers = [
        path.name
        for path in _sources()
        if path.name not in ("generated_indexes.py", "cli.py")
        and "legacy_markdown" in path.read_text(encoding="utf-8")
    ]
    assert callers == []
