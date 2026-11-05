"""Declaration: the answered/open marker beside each question."""
from __future__ import annotations

from docstrap.tools.declaration import Kind, Target, ToolDeclaration

DECLARATION = ToolDeclaration(
    id="answered",
    title="Answers",
    # A tool, not an instrument: it works in place and the page you were
    # reading is still the page you are looking at.
    kind=Kind.TOOL,
    target=Target.DOCUMENT,
    entry="docstrap.tools.answered",
    # No collection of its own. It reads `/api/answers/{project}/{doc}`,
    # which is the server's rather than any tool's
    # — the same arrangement the status badge has with `/api/documents`.
    # A tool owning a second route onto one store would be a second way
    # to read it.
    api_collection=None,
    # On by default, because the finding this repairs is that a reader
    # could not tell an answered question from an open one at all.
    # Off by default would leave that
    # true for anyone who never opens the launcher.
    default_visible=True,
    summary="Show each question's answer, and mark the ones still open.",
)
