"""Declaration: the status badge."""
from __future__ import annotations

from docstrap.tools.declaration import Kind, Target, ToolDeclaration

DECLARATION = ToolDeclaration(
    id="status",
    title="Status badge",
    kind=Kind.TOOL,
    target=Target.DOCUMENT,
    entry="docstrap.tools.status",
    # No collection of its own: the badge reads the shared
    # /api/documents metadata API rather than owning a namespace.
    api_collection=None,
    # Renders on load today, and keeps doing so.
    default_visible=True,
    summary="Show this document's docstrap status beside its title.",
)
