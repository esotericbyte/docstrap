"""Declaration: the sortable, filterable data table."""
from __future__ import annotations

from docstrap.tools.declaration import Kind, Target, ToolDeclaration

DECLARATION = ToolDeclaration(
    id="datatable",
    title="Data tables",
    # A tool: the table is drawn where the author put it, and the page
    # being read is still the page being looked at.
    kind=Kind.TOOL,
    target=Target.DOCUMENT,
    entry="docstrap.tools.datatable",
    # Owns no collection. The rows are in the page, put there by the
    # build from the JSON file the directive names; nothing is fetched.
    api_collection=None,
    # On by default: the author placed a table to be read, and sorting
    # and filtering it is how it is read.
    default_visible=True,
    summary="Sort and filter the data tables on this page.",
)
