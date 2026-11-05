"""What the cleanup is driven from: which `index.md` files are docstrap's.

Fifty-five of them are tracked across five repositories, written there by
builds that walked a symlinked scratch tree. Deleting them is separate
work, per repository, and it needs a list it can trust. This report is
that list, and the property it has to hold is narrow: **it claims a file
only when docstrap composes exactly those bytes.**

The trap these tests are built around is the one that has already been
sprung. An earlier attempt told generated files from authored ones with a
five-line grep over their prose and got it wrong. So the interesting
cases here are not the clean ones — they are the stale page that *is*
docstrap's but no longer matches, and the foreign page that is not
docstrap's at all. The report must decline to claim both, from one rule,
without looking at a word either of them says.

Since 0.0.4 no build composes markdown for a section page, so the bytes
the report recognises are **frozen** in `generated_indexes.legacy_
markdown` rather than taken from a live composer that has nothing left
to say. These tests write files with that function for the same reason
the report reads with it: it is the description of what those builds
emitted, and it has to keep describing the past.
"""
from __future__ import annotations

from pathlib import Path

from docstrap import generated_indexes, projectscope
from docstrap.config import load
from docstrap.layouts import markdown
from docstrap.scan import scan
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
    f"{PROJECT_PATH}/docs/adr/0001-a-decision.md": "# A decision\n\nAccepted.\n",
}


def _store(tmp_path: Path, files: dict[str, str]) -> Path:
    store = tmp_path / "store"
    store.mkdir(parents=True, exist_ok=True)
    for relative, content in files.items():
        path = store / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    (store / ".docstrap").write_text(DOCSTRAP_YAML, encoding="utf-8")
    return store


def _scope(store: Path) -> projectscope.ProjectScope:
    return projectscope.resolve(store / PROJECT_PATH)


def _states(findings) -> dict[str, str]:
    return {f.display: f.state for f in findings}


def _project(store: Path):
    return [p for p in scan(load(store / ".docstrap")) if p.kind == "project"][0]


# --- the deterministic rule ---------------------------------------------------


def test_a_file_matching_what_a_build_composes_is_claimed(tmp_path: Path):
    """The known-good case: docstrap's own output, unchanged since."""
    store = _store(tmp_path, TREE)
    scope = _scope(store)
    specs = store / PROJECT_PATH / "docs" / "specs"
    (specs / "index.md").write_text(
        generated_indexes.legacy_markdown(specs, set(), set()), encoding="utf-8"
    )

    states = _states(generated_indexes.scan(scope))
    assert states["docs/specs/index.md"] == generated_indexes.GENERATED


def test_stale_output_of_an_older_build_is_reported_and_not_claimed(tmp_path: Path):
    """`beta/docs/specs/index.md` is this: written when the directory was
    empty, never regenerated, and now describing a section that has a
    document in it. It is docstrap's, and the report still declines to
    say so, because the only evidence it would have is the prose."""
    store = _store(tmp_path, TREE)
    scope = _scope(store)
    specs = store / PROJECT_PATH / "docs" / "specs"
    (specs / "index.md").write_text(
        "# Specs\n\n*(no documents in this section)*\n", encoding="utf-8"
    )

    findings = {f.display: f for f in generated_indexes.scan(scope)}
    finding = findings["docs/specs/index.md"]
    assert finding.state == generated_indexes.DIVERGENT
    assert not finding.is_docstrap
    assert "census" in generated_indexes.diff(finding, scope), (
        "the diff is what a person decides from"
    )


def test_another_tools_page_is_reported_and_not_claimed(tmp_path: Path):
    """`beta/docs/adr/index.md` was written by a different tool entirely.

    It needs no special case: it is at a path a build writes to, it is
    not the bytes a build writes, so it is not claimed. The same rule
    that spares the stale page spares this one.
    """
    store = _store(tmp_path, TREE)
    scope = _scope(store)
    adr = store / PROJECT_PATH / "docs" / "adr"
    (adr / "index.md").write_text(
        "<!-- This file is the homepage of your knowledge base -->\n\n"
        "# Architecture knowledge base\n\nWelcome.\n",
        encoding="utf-8",
    )

    findings = {f.display: f for f in generated_indexes.scan(scope)}
    finding = findings["docs/adr/index.md"]
    assert finding.state == generated_indexes.DIVERGENT
    assert not finding.is_docstrap


def test_a_path_with_no_file_is_absent_rather_than_missing(tmp_path: Path):
    """After the fix this is every site, which is the point of the fix."""
    store = _store(tmp_path, TREE)
    scope = _scope(store)

    states = _states(generated_indexes.scan(scope))
    assert states["docs/specs/index.md"] == generated_indexes.ABSENT
    assert states["docs/adr/index.md"] == generated_indexes.ABSENT


def test_the_report_finds_the_same_directories_a_build_gives_pages_to(
    tmp_path: Path, user_dirs: Path
):
    """One predicate, two callers. A site the report misses is a file the
    cleanup never hears about; a site it invents is a file it might try
    to delete.

    The build no longer walks to answer this — it marks the sections as
    it mirrors — so what is compared is the set of markers it left
    against the set of paths the report names.
    """
    store = _store(tmp_path, TREE | {
        f"{PROJECT_PATH}/docs/plans/rollout/phase.md": "# Phase\n\nDeeper.\n",
    })
    project = _project(store)
    out = tmp_path / "out"
    markdown.build(project, out)
    scratch = out / "_scratch" / project.slug

    given_a_page_in_the_build = {
        str(p.parent.relative_to(scratch))
        for p in scratch.rglob(composed.MARKER_NAME)
        if p.parent != scratch and "promdance" not in p.parts
    }
    reported = {
        str(Path(f.display).parent.relative_to("docs"))
        for f in generated_indexes.scan(_scope(store))
        if Path(f.display) != Path("docs/index.md")
    }
    assert reported == given_a_page_in_the_build


# --- the landing page ---------------------------------------------------------


def test_the_placeholder_an_older_build_left_is_claimed(tmp_path: Path):
    """`_ensure_docs_dir_exists` wrote this one; it is docstrap's."""
    store = _store(tmp_path, TREE)
    scope = _scope(store)
    (store / PROJECT_PATH / "docs" / "index.md").write_text(
        generated_indexes.docs_dir_stub("Widget"), encoding="utf-8"
    )

    findings = {f.display: f for f in generated_indexes.scan(scope)}
    assert findings["docs/index.md"].state == generated_indexes.GENERATED


def test_a_hand_written_landing_page_is_not_claimed(tmp_path: Path):
    """A hand-written site landing page, with grid cards in it."""
    store = _store(tmp_path, TREE)
    scope = _scope(store)
    (store / PROJECT_PATH / "docs" / "index.md").write_text(
        "# Sample Platform\n\n::::{grid} 2\n:::{grid-item-card} Servers\n:::\n::::\n",
        encoding="utf-8",
    )

    findings = {f.display: f for f in generated_indexes.scan(scope)}
    finding = findings["docs/index.md"]
    assert finding.state == generated_indexes.AUTHORED
    assert not finding.is_docstrap


# --- the command ---------------------------------------------------------------


def test_the_command_reports_and_changes_nothing(tmp_path: Path):
    from typer.testing import CliRunner

    from docstrap.cli import app

    store = _store(tmp_path, TREE)
    specs = store / PROJECT_PATH / "docs" / "specs"
    (specs / "index.md").write_text(
        generated_indexes.legacy_markdown(specs, set(), set()), encoding="utf-8"
    )
    before = (specs / "index.md").read_bytes()

    result = CliRunner().invoke(
        app, ["generated-indexes", str(store / PROJECT_PATH), "--json"]
    )
    assert result.exit_code == 0, result.output

    import json

    payload = json.loads(result.output)
    claimed = [f for f in payload["findings"] if f["docstrap_wrote_it"]]
    assert [f["display"] for f in claimed] == ["docs/specs/index.md"]
    assert (specs / "index.md").read_bytes() == before
