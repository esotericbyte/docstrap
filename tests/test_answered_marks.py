"""The pair on the reading surface, through a real Sphinx build.

A reader of a question document could not tell an answered question from an
open one, could not see the answer, and had no indication that anything
had been answered at all.

The repair is anchored at build and resolved at serve, and this file is
about the build half — the only half that can be asserted without a
browser. A real `sphinx-build` over a real source tree, then assertions
on the HTML that comes out, the same way `test_rendered_page.py` does it.

The property that matters most is that nothing is altered in place, and
it is the first test below: **the source document is not written to.**
Not by the build, not by anything. What the build adds is a class on a
paragraph of the *derivative*, which is a rendering fact about the output
in the same way a heading anchor is.

The serve half — the note appearing under each question, live from the
answers API — needs a browser and is recorded in the step's commit
message against a real running `docstrap serve`.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

from docstrap import questions
from docstrap.tools import registry
from docstrap.tools.answered import BLOCK_CLASS, label_class

PAGE = """\
# A document that asks things

Some prose. A sentence mentioning Q1 in passing, which is a
cross-reference and not a question.

## An earlier, superseded set

**Q1.** An old question nobody kept.

**Q2.** Another old one.

## Some other section

> **Q7.** Quoted, so not a question.

```
**Q8.** Fenced, so not a question.
```

## Open questions

**Q1.** Which storage layout?

**Q2.** Who owns the name, and what happens when
two things want it?

- **Q3.** Carried on a bullet.
"""

CONF = """\
project = "Sample Project"
extensions = {extensions!r}
master_doc = "index"
html_theme = "alabaster"
"""


@pytest.fixture(scope="module")
def source(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("answered")
    src = root / "src"
    src.mkdir()
    (src / "index.md").write_text(PAGE, encoding="utf-8")
    extensions = ["myst_parser", *registry.sphinx_extensions()]
    (src / "conf.py").write_text(CONF.format(extensions=extensions), encoding="utf-8")
    return src


@pytest.fixture(scope="module")
def built(source: Path) -> Path:
    out = source.parent / "out"
    result = subprocess.run(
        [sys.executable, "-m", "sphinx", "-q", "-b", "html", str(source), str(out)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    return out


@pytest.fixture(scope="module")
def html(built: Path) -> str:
    return (built / "index.html").read_text(encoding="utf-8")


# --- nothing is altered in place, first ------------------------------------


def test_the_build_does_not_write_to_the_source_document(source: Path, built: Path):
    """Nothing is altered in place.

    The whole reason this repair is a rendering step and not an appended
    section. Checked byte for byte, after a build that marked three
    questions in the output.
    """
    assert (source / "index.md").read_text(encoding="utf-8") == PAGE
    assert built.is_dir(), "the build ran"


# --- the mark, and which blocks get one --------------------------------------


def _marked(html: str) -> list[str]:
    """Every label the built page carries a mark for, in document order."""
    return [
        m.group(1).upper()
        for m in re.finditer(rf'class="[^"]*\b{BLOCK_CLASS}-(q\d+)\b', html)
    ]


def test_the_questions_at_the_end_are_marked(html: str):
    assert _marked(html) == ["Q1", "Q2", "Q3"]
    assert html.count(f'{BLOCK_CLASS}"') + html.count(f'{BLOCK_CLASS} ') >= 3


def test_the_superseded_earlier_run_is_not_marked(source: Path, html: str):
    """Rule 3 is `docstrap.questions`', and this tool does not re-decide it.

    The document carries an earlier `Q1`/`Q2` pair above its real ones.
    `docstrap questions` returns only the last run, and so must the page,
    or a reader would be shown two things both called Q1.
    """
    found = questions.find(source / "index.md")
    assert [q.label for q in found.questions] == ["Q1", "Q2", "Q3"]
    assert len(found.all_labelled) > len(found.questions), "the fixture has an old run"
    # One mark per label, not one per labelled item anywhere in the file.
    assert _marked(html) == [q.label for q in found.questions]
    assert "An old question nobody kept" in html, "the old run still renders"


def test_a_quoted_or_fenced_label_is_not_marked(html: str):
    """Rule 2, inherited rather than reimplemented."""
    assert "Q7" not in _marked(html)
    assert "Q8" not in _marked(html)
    assert "Quoted, so not a question" in html


def test_a_cross_reference_in_prose_is_not_marked(html: str):
    """A `Q1` mid-sentence is a reference; the label has to open the block."""
    assert "mentioning Q1 in passing" in html
    # Three marks, not four — the prose mention did not become one.
    assert len(_marked(html)) == 3


def test_a_bulleted_question_is_marked_once(html: str):
    """The outer list item is marked, not it and its inner paragraph."""
    assert _marked(html).count("Q3") == 1


def test_the_label_class_is_what_the_client_reads_back():
    """Both halves agree by construction, not by two spellings of a rule."""
    assert label_class("Q1") == f"{BLOCK_CLASS}-q1"
    assert label_class("Q12") == f"{BLOCK_CLASS}-q12"


# --- the tool is a tool like the others --------------------------------------


def test_the_tool_reads_the_servers_answers_api_and_owns_no_route():
    """It shows what the store knows; it is not a second way to read it."""
    declaration = registry.get("answered")
    assert declaration.api_collection is None
    assert declaration.route_prefix is None
    assert declaration.default_visible is True, (
        "off by default would leave the finding true for anyone who never "
        "opens the launcher"
    )


def test_its_bundles_reach_the_built_site(built: Path):
    declaration = registry.get("answered")
    static = built / "_static"
    assert (static / declaration.js_bundle).is_file()
    assert (static / declaration.css_bundle).is_file()


def test_a_page_that_asks_nothing_is_not_marked(tmp_path: Path):
    """No question, no mark, and the client then asks the server nothing."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "index.md").write_text("# Plain\n\nNo questions here.\n", encoding="utf-8")
    extensions = ["myst_parser", *registry.sphinx_extensions()]
    (src / "conf.py").write_text(CONF.format(extensions=extensions), encoding="utf-8")
    out = tmp_path / "out"
    result = subprocess.run(
        [sys.executable, "-m", "sphinx", "-q", "-b", "html", str(src), str(out)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    page = (out / "index.html").read_text(encoding="utf-8")
    assert BLOCK_CLASS not in page


def test_the_built_page_carries_no_answer_text(html: str):
    """The mark is an anchor, not a bake.

    Answers are resolved at serve time from the live store. Baking one
    into the HTML would show a decision as current long after it was
    revised, which in a decision system is worse than showing none.
    """
    assert "Answered" not in _body(html)
    assert "Open — not yet answered" not in _body(html)


def _body(html: str) -> str:
    match = re.search(r"<body[^>]*>(.*)</body>", html, re.S)
    assert match, "no body in built page"
    return match.group(1)
