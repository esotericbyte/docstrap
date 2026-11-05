"""Declaration: the section-marking reviewer."""
from __future__ import annotations

from docstrap.tools.declaration import Kind, Target, ToolDeclaration

DECLARATION = ToolDeclaration(
    id="review",
    title="Review",
    kind=Kind.TOOL,
    target=Target.DOCUMENT,
    entry="docstrap.tools.review",
    # Owns the reviews collection; the route prefix follows from this
    # plus the document target — see ToolDeclaration.route_prefix.
    api_collection="reviews",
    # Off until asked for, as it was behind its own floating button.
    default_visible=False,
    summary="Mark sentences and sections, then submit a review record.",
)
