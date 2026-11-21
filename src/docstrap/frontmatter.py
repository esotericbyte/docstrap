"""Lossless YAML front-matter split for markdown documents.

It splits a
document into (opening delimiter, raw YAML text, closing delimiter, body)
and keeps every piece verbatim, so ``to_text()`` reproduces the original
document exactly — including line endings, indentation, comments, key
order and any leading byte-order mark.

That exactness is a correctness property, not a nicety. Every top-level
key has to survive untouched, and the cheapest way to
guarantee that is to never rebuild the YAML from parsed data at all.

Nothing here writes to disk. A malformed block is reported through
``error`` and left exactly as it was found.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# A front-matter block opens with `---` alone on the document's first line.
_OPEN_RE = re.compile(r"\A---[ \t]*(?:\r\n|\n|\r)")

# ...and closes with `---` or `...` alone on a line of its own. YAML allows
# both as document-end markers and hand-written front-matter uses both.
_CLOSE_RE = re.compile(r"^(?:---|\.\.\.)[ \t]*(?:\r\n|\n|\r|\Z)", re.MULTILINE)

_BOM = "﻿"


@dataclass(frozen=True)
class FrontMatterBlock:
    """A document split into its front-matter parts, all kept verbatim.

    ``prefix + open_delim + raw + close_delim + body`` is the original
    document, always. When there is no front-matter, everything but
    ``body`` (and a possible BOM ``prefix``) is empty.
    """

    present: bool
    prefix: str            # byte-order mark, if the file carried one
    open_delim: str        # `---` line that opened the block, with its newline
    raw: str               # exact YAML text between the delimiters
    close_delim: str       # `---` / `...` line that closed it, with its newline
    body: str              # everything after the closing delimiter
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_text(self) -> str:
        """Reassemble the original document, byte for byte."""
        return self.prefix + self.open_delim + self.raw + self.close_delim + self.body

    @property
    def malformed(self) -> bool:
        """True when the block could not be parsed as a YAML mapping."""
        return self.error is not None


def split_front_matter(text: str) -> FrontMatterBlock:
    """Split document text into front-matter and body without altering either.

    Never raises for malformed input: an unterminated block, invalid YAML,
    or a block that is not a mapping all come back as a block with ``error``
    set, empty ``data``, and the original text still recoverable through
    ``to_text()``.
    """
    prefix = ""
    rest = text
    if rest.startswith(_BOM):
        prefix, rest = _BOM, rest[1:]

    opening = _OPEN_RE.match(rest)
    if opening is None:
        return FrontMatterBlock(
            present=False, prefix=prefix, open_delim="", raw="",
            close_delim="", body=rest,
        )

    open_delim = opening.group(0)
    closing = _CLOSE_RE.search(rest, opening.end())
    if closing is None:
        # Unterminated. Report it; repair nothing. The whole
        # remainder stays in `raw` so to_text() is still exact.
        return FrontMatterBlock(
            present=True, prefix=prefix, open_delim=open_delim,
            raw=rest[opening.end():], close_delim="", body="",
            error="front-matter block opened with `---` but was never closed",
        )

    raw = rest[opening.end():closing.start()]
    parts = dict(
        present=True, prefix=prefix, open_delim=open_delim, raw=raw,
        close_delim=closing.group(0), body=rest[closing.end():],
    )

    try:
        parsed = yaml.safe_load(raw) if raw.strip() else None
    except yaml.YAMLError as exc:
        summary = " ".join(str(exc).split())
        return FrontMatterBlock(**parts, error=f"front-matter is not valid YAML: {summary}")

    if parsed is None:
        return FrontMatterBlock(**parts, data={})
    if not isinstance(parsed, dict):
        return FrontMatterBlock(
            **parts,
            error=(
                "front-matter must be a YAML mapping at top level, got "
                f"{type(parsed).__name__}"
            ),
        )
    return FrontMatterBlock(**parts, data=parsed)


def read_front_matter(path: Path) -> FrontMatterBlock:
    """Read a document from disk and split it. Read-only.

    Opened with ``newline=""`` so Python's universal-newline translation
    does not silently rewrite a CRLF document into LF on the way in. The
    byte-for-byte promise has to start at the read.
    """
    with path.open("r", encoding="utf-8", newline="") as handle:
        return split_front_matter(handle.read())
