"""Declaration: the task list, grouped and drilled into, one decision per task."""
from __future__ import annotations

from docstrap.tools.declaration import Kind, Target, ToolDeclaration

DECLARATION = ToolDeclaration(
    id="tasks",
    title="Tasks",
    # A tool: the list is drawn where the author put the directive, and
    # the page being read is still the page being looked at.
    kind=Kind.TOOL,
    target=Target.DOCUMENT,
    entry="docstrap.tools.tasks",
    # Owns the `decisions` collection under the document base, which
    # gives `/api/tools/{project}/{doc_slug}/decisions`: GET reads the
    # decisions recorded on this page, POST records one. The answer FILE
    # they land in is owned by `docstrap.answers`; `decisions.py` here is
    # only how a task decision is spelled inside it.
    api_collection="decisions",
    # On by default: the author placed the list to be read and acted on.
    default_visible=True,
    summary="Group, drill into and decide on the tasks on this page.",
)
