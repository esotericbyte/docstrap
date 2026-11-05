"""Declaration: the three-panel Q&A instrument."""
from __future__ import annotations

from docstrap.tools.declaration import Kind, Target, ToolDeclaration

DECLARATION = ToolDeclaration(
    id="qapanels",
    title="Q&A panels",
    # An instrument, not a tool: it takes the view rather than working
    # inside it, so the launcher gives it a launch action rather than a
    # toggle. That is the seam — a second control
    # driving `docstrap.tools` visibility without owning it.
    kind=Kind.INSTRUMENT,
    # The project, not the page. A project's open questions are answered
    # in one sitting; the qa tool answers the question in front of you.
    target=Target.PROJECT,
    entry="docstrap.tools.qapanels",
    # Owns the `qa` collection under the project route base, which gives
    # `/api/tools/{project}/qa` — see ToolDeclaration.route_prefix.
    # The answer FILE it writes through is owned by `docstrap.answers`,
    # which the qa tool writes through too; a route and a store are
    # different things to own.
    api_collection="qa",
    # And readable under the document base too, which gives
    # `/api/tools/{project}/{doc_slug}/qa`. The requirement is that the
    # choice of scope be explicit rather than project-wide by omission,
    # so both are reachable
    # and the panel says which one it is showing. Declared rather than
    # mounted on the side: the server's route table is compared against
    # what the declarations derive, and an undeclared second path is the
    # thing that comparison exists to catch.
    also_scoped_to=Target.DOCUMENT,
    # Never on before someone asks for it: it replaces the view.
    default_visible=False,
    summary="Answer this project's open questions in three panels.",
)
