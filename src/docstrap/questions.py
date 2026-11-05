"""Find the questions a document poses, by reading the author's own numbering.

A document in this corpus ends with its open questions, and they are
numbered `Q1`, `Q2`, `Q3` — an enumeration deliberately kept separate from
section numbering so a question is never confused with a section. That
convention is the whole detector. There is no classifier here, nothing
weighs evidence, and nothing guesses: a question is an item the author
labelled as one, and everything else in the document is left alone.

What that buys is a finder with no false positives to argue about. A
question mark is not a question — a heading phrased as one, a rhetorical
transition, an example inside a quotation, an FAQ entry with its answer
below it all carry one — and none of them carry a `Q<n>` label.

Three rules, and they are the entire specification.

1. **A question is a block whose first line opens with a `Q<n>` label.**
   The label may be emphasised (`**Q1.**`), carried on a bullet
   (`- **Q1.**`), or carried on a task item (`- [ ] **Q1.**`). The
   separator after the number is `.`, `:`, or `)`. The item runs to the
   next blank line, so a question wrapped over four lines is one question.
2. **Labels inside fenced code, blockquotes, front-matter, and headings do
   not count.** A `Q3` mentioned mid-sentence does not count either: the
   label has to open the block.
3. **The questions are the ones at the end.** Items whose numbers ascend by
   one form a run; the last run in the document is what the finder returns.
   A document that carries an earlier, superseded set keeps it out of the
   result — see :attr:`DocumentQuestions.all_labelled` to inspect it.

Deciding whether an unlabelled question in the prose is genuinely posed to
a reader is a larger and much less certain problem. It is not attempted
here.

*Which* documents are read is not decided here either. This module reads
the documents it is handed; the set comes from
:mod:`docstrap.projectscope`, which resolves a path to the one project that
owns it and enumerates that project's own documents. Nothing is stored:
questions live in the documents and are read when somebody asks.
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from docstrap.frontmatter import split_front_matter

#: The label, and everything the corpus wraps it in. Anchored at the start
#: of a line, because a `Q3` inside a sentence is a cross-reference.
_LABEL_RE = re.compile(
    r"^[ \t]{0,3}"
    r"(?:(?P<marker>[-*+]|\d+[.)])[ \t]+)?"          # bullet or number
    r"(?:\[(?P<checkbox>[ xX])\][ \t]+)?"            # task-list checkbox
    r"(?:\*\*|__)?"                                  # opening emphasis
    r"Q(?P<number>\d+)"
    r"[*_]*[.:)][*_]*"                               # separator, emphasis either side
    r"[ \t]+(?P<rest>\S.*)$"
)

_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,}|:{3,})")
_HEADING_RE = re.compile(r"^ {0,3}#{1,6}\s")
_QUOTE_RE = re.compile(r"^ {0,3}>")


@dataclass(frozen=True)
class Question:
    """One `Q<n>` item, as the author wrote it."""

    number: int
    #: 1-based line of the item's first line, in the whole file.
    line: int
    #: The item's text with the label removed and its lines joined.
    text: str
    #: Nearest heading above the item, for saying where it was found.
    section: str
    #: `' '` or `'x'` when the item is a task-list item, else `''`.
    checkbox: str = ""

    @property
    def label(self) -> str:
        return f"Q{self.number}"


@dataclass(frozen=True)
class DocumentQuestions:
    """What one document asks."""

    path: Path
    #: The last ascending run of labelled items — the questions at the end.
    questions: tuple[Question, ...] = ()
    #: Every labelled item in the document, including earlier runs.
    all_labelled: tuple[Question, ...] = ()

    def __bool__(self) -> bool:
        return bool(self.questions)


def find_in_text(text: str, *, path: Path | None = None) -> DocumentQuestions:
    """Find the `Q<n>` questions in one markdown document's text."""
    block = split_front_matter(text)
    offset = 0
    if block.present:
        offset = (
            block.prefix + block.open_delim + block.raw + block.close_delim
        ).count("\n")

    found = _labelled_items(block.body, line_offset=offset)
    return DocumentQuestions(
        path=path if path is not None else Path("<text>"),
        questions=_last_run(found),
        all_labelled=found,
    )


def find(path: Path) -> DocumentQuestions:
    """Find the `Q<n>` questions in one markdown file."""
    return find_in_text(path.read_text(encoding="utf-8"), path=path)


def label_of(line: str) -> str | None:
    """The `Q<n>` label a line opens with, or None.

    Rule 1 alone, exposed so that something looking at *rendered* text —
    a docutils paragraph, say, where the author's `**` are gone — can ask
    the same question this module asks of source, and get the same
    answer. Rules 2 and 3 are about a document's structure and are not
    decidable from one line; a caller that needs them asks :func:`find`
    for the document and intersects.
    """
    match = _LABEL_RE.match(line)
    return f"Q{int(match.group('number'))}" if match else None


def _labelled_items(body: str, *, line_offset: int) -> tuple[Question, ...]:
    """Every block whose first line opens with a `Q<n>` label."""
    found: list[Question] = []
    section = ""
    fence = ""
    number = 0
    started = 0
    checkbox = ""
    lines: list[str] = []

    def close() -> None:
        nonlocal lines
        if lines:
            found.append(
                Question(
                    number=number,
                    line=started,
                    text=re.sub(r"\s+", " ", " ".join(lines)).strip(),
                    section=section,
                    checkbox=checkbox,
                )
            )
            lines = []

    for index, line in enumerate(body.splitlines()):
        fence_match = _FENCE_RE.match(line)
        if fence:
            if fence_match and fence_match.group(1)[0] == fence[0]:
                fence = ""
            continue
        if fence_match:
            close()
            fence = fence_match.group(1)
            continue

        if not line.strip():
            close()
            continue
        if _HEADING_RE.match(line):
            close()
            section = line.lstrip("# ").rstrip(" #").strip()
            continue
        if _QUOTE_RE.match(line):
            close()
            continue

        match = _LABEL_RE.match(line)
        if match:
            close()
            number = int(match.group("number"))
            started = index + 1 + line_offset
            checkbox = (match.group("checkbox") or "").lower()
            lines = [match.group("rest")]
        elif lines:
            lines.append(line.strip())

    close()
    return tuple(found)


def _last_run(items: tuple[Question, ...]) -> tuple[Question, ...]:
    """The final run of items whose numbers ascend by one.

    A number that does not follow its predecessor starts a new run, so a
    document carrying an older `Q1…Q3` above a current `Q1…Q5` reports only
    the current set.
    """
    run: list[Question] = []
    for item in items:
        if run and item.number == run[-1].number + 1:
            run.append(item)
        else:
            run = [item]
    return tuple(run)


def scan(documents: Iterable[Path]) -> list[DocumentQuestions]:
    """Find questions in each of ``documents``, in the order given.

    This does not walk anything. The document set is decided by whoever
    calls it, and for a run over more than one document that is
    :meth:`docstrap.projectscope.ProjectScope.documents` — a project's own
    declared documents, never a raw directory listing, so a sibling
    project's questions cannot arrive here.

    Documents that ask nothing are omitted; a file that cannot be read as
    text is skipped rather than raised on, so one bad file does not end a
    run over a whole project.
    """
    results: list[DocumentQuestions] = []
    for document in documents:
        try:
            result = find(document)
        except (OSError, UnicodeDecodeError):
            continue
        if result:
            results.append(result)
    return results
