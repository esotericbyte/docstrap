"""Declaration: the inline question tool."""
from __future__ import annotations

from docstrap.tools.declaration import Kind, Target, ToolDeclaration

DECLARATION = ToolDeclaration(
    id="qa",
    title="Questions",
    kind=Kind.TOOL,
    target=Target.DOCUMENT,
    entry="docstrap.tools.qa",
    # Owns the answers collection; the route prefix follows from this
    # plus the document target — see ToolDeclaration.route_prefix.
    api_collection="answers",
    # The form renders with the page today, and keeps doing so.
    default_visible=True,
    summary="Answer the questions the author placed in this document.",
)
