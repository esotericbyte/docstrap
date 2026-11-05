"""The tool declaration object.

One small declaration per tool, and it is the single source of truth.
Three consumers read it and none of them keeps its own copy of what it
says:

* the **server** derives the route prefix a tool's API mounts under
  (:mod:`docstrap.tools.registry` walks declarations; ``server.py`` has
  no path strings of its own);
* the **launcher** reads :attr:`ToolDeclaration.kind` and
  :attr:`ToolDeclaration.target` to decide whether to offer the tool
  where the reader is standing (:mod:`docstrap.tools.launcher`);
* the **build** names the client bundles from the declaration
  (:attr:`js_bundle` / :attr:`css_bundle`) and lists the Sphinx
  extension from :attr:`entry`.

Adding a tool is adding a directory with one of these in it. Nothing
outside that directory needs editing.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class Kind(str, Enum):
    """Tool or instrument — the boundary test.

    A **tool** is usable from the standard document view: it works in
    place, and the page you were reading is still the page you are
    looking at. An overlay or a popover drawn on the page is still a
    tool.

    An **instrument** brings up a separate component or navigates away
    from the standard main view — the view is replaced or left.

    The distinction is not cosmetic. A tool ships with every rendered
    page, so what it weighs is paid on every page view and it must not
    fight the host theme for styling; an instrument loads on demand and
    owns its own view. Both are built — a tool's UI is Svelte with scoped
    component styles — but only an instrument may reach for a styling
    toolkit of its own.
    """

    TOOL = "tool"
    INSTRUMENT = "instrument"


class Target(str, Enum):
    """What the tool is applied to — the workpiece.

    ``DOCUMENT`` — the page in front of you. Nearly every tool.
    ``PROJECT`` — a whole project, ranging across many documents. The
    launcher must not offer one of these on a lone page with no project
    to act on.
    """

    DOCUMENT = "document"
    PROJECT = "project"


# The API base each target hangs its tool-owned collections under. This
# mapping is the ONLY place the shape of a tool route is written down;
# the server asks a declaration for its prefix rather than repeating a
# path. The base names what owns the routes — the tools — and not where a
# tool happens to write: a derivative goes to the project's draft root,
# whichever plugin or source provides it (docstrap.drafts).
_TARGET_ROUTE_BASE: dict[Target, str] = {
    Target.DOCUMENT: "/api/tools/{project}/{doc_slug}",
    Target.PROJECT: "/api/tools/{project}",
}

#: The one route parameter that carries a PATH and not a single segment.
#:
#: A document's identity is its path below ``docs_root`` with the suffix
#: dropped — ``proposals/0002-the-upgrade-path`` — which is what
#: :meth:`docstrap.projectscope.ProjectScope.document_slug` returns and
#: what the rendered page carries in its ``docstrap-doc-slug`` meta tag.
#: A route that treated it as one segment made that identity unreachable:
#: the slash was percent-encoded, nothing matched, and every
#: document-targeted tool 404ed on every document below the root while
#: reporting the server as absent. The identity is not flattened to suit
#: the route; the route carries the path.
DOCUMENT_PARAMETER = "doc_slug"

#: How the ASGI router is told a parameter spans separators. Kept next to
#: the bases because it is part of the same one written-down shape.
_PATH_CONVERTOR = "path"

_DOCUMENT_PLACEHOLDER = "{" + DOCUMENT_PARAMETER + "}"
_DOCUMENT_PATH_PLACEHOLDER = (
    "{" + DOCUMENT_PARAMETER + ":" + _PATH_CONVERTOR + "}"
)


class DeclarationError(ValueError):
    """A declaration is malformed. Raised at discovery, not at request time."""


class RouteCollisionError(RuntimeError):
    """Two declared routes could capture one another.

    Raised at mount time, not at request time: a route table that cannot
    be told apart is a fault in the declarations, and the server refusing
    to start is a better failure than one endpoint silently answering for
    another.
    """


def as_server_path(template: str) -> str:
    """A route template in the form the ASGI router needs.

    The declaration's own spelling — ``{doc_slug}`` — is the one the
    launcher fills in for the browser, so a client URL and a server route
    are still the same written-down shape. This is the single place that
    shape is translated for the router, by marking the one parameter that
    spans separators (:data:`DOCUMENT_PARAMETER`).
    """
    return template.replace(_DOCUMENT_PLACEHOLDER, _DOCUMENT_PATH_PLACEHOLDER)


def as_declared_path(template: str) -> str:
    """A route template back in the declaration's own spelling.

    The inverse of :func:`as_server_path`, so a path read off a mounted
    route can be compared with what the declarations derive without
    either side keeping a second copy of the shape.
    """
    return template.replace(_DOCUMENT_PATH_PLACEHOLDER, _DOCUMENT_PLACEHOLDER)


def target_of_route(template: str) -> Target | None:
    """Which base ``template`` hangs off, or None when it hangs off neither.

    Accepts either spelling — the declaration's or the router's. The
    document base is tested first because the project base is a prefix of
    it; asking in the other order would call every document route a
    project one.
    """
    declared = as_declared_path(template)
    for target in (Target.DOCUMENT, Target.PROJECT):
        if declared.startswith(_TARGET_ROUTE_BASE[target] + "/"):
            return target
    return None


def check_route_separation(templates: Iterable[str]) -> None:
    """Refuse a route table whose two scopes could capture each other.

    With the document parameter carrying a path, the two bases are told
    apart by segment count alone: a project URL has exactly one segment
    after the project, a document URL has two or more, and neither
    pattern can produce the other's shape. **That separation holds only
    while every declared route is a base plus one static leaf.** A tool
    that hung a sub-path off the project base would break it in exactly
    the way ``tools/qapanels/routes.py`` describes at length:
    ``…/{project}/qa/answers`` is indistinguishable from the qa tool's
    ``…/{project}/{doc_slug}/answers`` with ``doc_slug`` equal to ``qa``.

    Before the document parameter carried a path that was an argument;
    now it is the load-bearing guarantee, so it is checked rather than
    trusted. A tool needing two operations on one collection
    distinguishes them by method, which is what the collection routes
    already do.
    """
    for template in templates:
        declared = as_declared_path(template)
        target = target_of_route(declared)
        if target is None:
            raise RouteCollisionError(
                f"{template!r} hangs off neither declared route base; a tool "
                f"route is a base from _TARGET_ROUTE_BASE plus its collection"
            )
        leaf = declared[len(_TARGET_ROUTE_BASE[target]) + 1 :]
        if not leaf or "/" in leaf or "{" in leaf:
            raise RouteCollisionError(
                f"{template!r} is not a route base plus one static "
                f"collection; a deeper path under the project base has the "
                f"shape of a document route and would capture it"
            )


@dataclass(frozen=True, slots=True)
class ToolDeclaration:
    """One tool's declaration. Frozen: nothing mutates a declaration.

    :param id: Short stable identifier, lowercase and filename-safe.
        Names the directory, the bundles, and the visibility key.
    :param title: Human label. What the launcher shows.
    :param kind: :class:`Kind` — tool or instrument.
    :param target: :class:`Target` — document or project.
    :param entry: Dotted module path exposing ``setup(app)``, the
        Sphinx entry point. The build lists this in ``extensions``.
    :param api_collection: Leaf name of the collection this tool owns
        on the server, or ``None`` when the tool mounts no routes of
        its own. ``"answers"`` gives the qa tool
        ``/api/tools/{project}/{doc_slug}/answers``.
    :param default_visible: Whether the launcher shows the tool before
        anyone has said otherwise. False means the reader opts in.
    :param summary: One line describing what the tool does, shown as
        the launcher entry's title text.
    :param also_scoped_to: A second :class:`Target` this tool serves its
        collection under, or ``None``. Declared, so that the derived
        route table is still exactly what the declarations say — a tool
        that mounted an undeclared second path would be the thing
        ``test_server_route_table_equals_what_the_declarations_derive``
        exists to catch. The qapanels instrument is the one that uses
        it: project-targeted, and also readable narrowed to one
        document, a deliberate choice of scope.
    """

    id: str
    title: str
    kind: Kind
    target: Target
    entry: str
    api_collection: str | None = None
    default_visible: bool = True
    summary: str = ""
    also_scoped_to: Target | None = None

    def __post_init__(self) -> None:
        # The id becomes a filename and a CSS class, so keep it to
        # characters that are safe in both and identical across
        # case-insensitive filesystems.
        allowed = "abcdefghijklmnopqrstuvwxyz0123456789-"
        if not self.id or not all(c in allowed for c in self.id):
            raise DeclarationError(
                f"tool id must be non-empty and [a-z0-9-]: {self.id!r}"
            )
        if not self.title:
            raise DeclarationError(f"tool {self.id!r} has no title")
        if not self.entry:
            raise DeclarationError(f"tool {self.id!r} has no entry point")
        if self.api_collection is not None and not self.api_collection:
            raise DeclarationError(
                f"tool {self.id!r} declares an empty api_collection; use None"
            )
        if self.also_scoped_to is not None:
            if self.api_collection is None:
                raise DeclarationError(
                    f"tool {self.id!r} declares a second scope but owns no "
                    f"api_collection to serve there"
                )
            if self.also_scoped_to is self.target:
                raise DeclarationError(
                    f"tool {self.id!r} declares its own target as a second "
                    f"scope; that is one route, not two"
                )

    # --- the server's view -------------------------------------------------

    @property
    def route_prefix(self) -> str | None:
        """The route prefix this tool's API mounts under, or None.

        Derived: the target picks the base, the tool names its
        collection. A tool that owns no collection mounts nothing — the
        status badge is one, because it reads the shared
        ``/api/documents`` metadata API rather than a namespace of its
        own.
        """
        return self.route_prefix_for(self.target)

    def route_prefix_for(self, target: Target) -> str | None:
        """This tool's collection under some target's base, or None.

        A tool's own target is the answer almost always, and
        :attr:`route_prefix` is that call. The other target is reachable
        only for a tool that declared ``also_scoped_to``. Both come from
        ``_TARGET_ROUTE_BASE``, so the shape of a tool route is still
        written down in exactly one place, and the two shapes differ in
        length and cannot capture each other.
        """
        if self.api_collection is None:
            return None
        return f"{_TARGET_ROUTE_BASE[target]}/{self.api_collection}"

    @property
    def route_prefixes(self) -> tuple[str, ...]:
        """Every prefix this tool's API is reachable at, in mount order.

        One for nearly every tool. Two for one that declared a second
        scope, its own target first. This is what the server's route
        table is compared against, so a path mounted that is not in here
        is a tool writing a URL down.
        """
        if self.api_collection is None:
            return ()
        targets = [self.target]
        if self.also_scoped_to is not None:
            targets.append(self.also_scoped_to)
        return tuple(
            prefix
            for prefix in (self.route_prefix_for(target) for target in targets)
            if prefix is not None
        )

    @property
    def server_route_prefix(self) -> str | None:
        """:attr:`route_prefix` in the form the ASGI router needs, or None."""
        prefix = self.route_prefix
        return None if prefix is None else as_server_path(prefix)

    @property
    def server_route_prefixes(self) -> tuple[str, ...]:
        """Every prefix this tool mounts at, in the router's own spelling.

        The same tuple as :attr:`route_prefixes`, in the same order, with
        the document parameter marked as spanning separators. A routes
        module mounts these; the launcher fills the other ones in. Both
        come from the one base map, so the shape is still written down
        exactly once.
        """
        return tuple(as_server_path(prefix) for prefix in self.route_prefixes)

    # --- the build's view --------------------------------------------------

    @property
    def js_bundle(self) -> str:
        """Client bundle filename. Unique because tool ids are unique."""
        return f"docstrap-{self.id}.js"

    @property
    def css_bundle(self) -> str:
        """Stylesheet filename for this tool's own chrome."""
        return f"docstrap-{self.id}.css"

    # --- the launcher's view -----------------------------------------------

    @property
    def visibility_class(self) -> str:
        """Body class the launcher sets when this tool is showing.

        CSS-driven visibility for chrome that is in the HTML already
        (the qa form) rather than injected on demand.
        """
        return f"docstrap-show-{self.id}"

    def to_offer(self) -> dict[str, object]:
        """The JSON the launcher's client code receives for this tool.

        Deliberately a projection, not the whole declaration: the client
        gets what it renders and decides with, and nothing else.
        """
        return {
            "id": self.id,
            "title": self.title,
            "kind": self.kind.value,
            "target": self.target.value,
            "summary": self.summary,
            "defaultVisible": self.default_visible,
            "visibilityClass": self.visibility_class,
        }
