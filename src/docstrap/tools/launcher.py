"""The single visibility launcher — which tools are offered, and where.

Without it, each widget would inject its own floating button into the same
corner with no arbitration. One control
owns what is showing; tools declare themselves to it rather than each
bolting on its own affordance.

The *decision* of what to offer lives here, in Python, not in the
client. The build computes the offer list for a page from the
declarations and the page's context, and serialises it into the page;
``docstrap-launcher.js`` renders what it is given. That keeps the rule
that the launcher only offers what is valid where the person is
standing in one testable place rather than in a browser.

A consequence to keep: with every tool hidden the
page reads as a plain document, which matters if one is ever shared.
The launcher itself can be dismissed for that reason.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterable, Sequence
from urllib.parse import quote

from docstrap.tools import registry
from docstrap.tools.declaration import Kind, Target, ToolDeclaration


@dataclass(frozen=True, slots=True)
class PageContext:
    """What the reader is standing on when the launcher renders.

    ``project`` and ``doc_slug`` come from the ``docstrap-*`` meta tags
    the build injects. Either may be absent: a page built outside a
    recognised project has no project, and a synthetic page (a generated
    index) may have no document identity.

    ``doc_slug`` is a path below the project's `docs_root` with the
    suffix dropped, not a single segment — most documents in most
    projects are nested, and the identity is the path. See
    :meth:`docstrap.projectscope.ProjectScope.document_slug`.

    **Absent means absent.** A page that belongs to no project carries
    ``project=None``, and the launcher then offers nothing that needs
    one. Inventing an identity to fill the hole — slugifying a page
    title, say — produces a name that addresses nothing, which is how a
    store's own front page came to advertise a project that did not
    exist. An explicit context bound to a real project is another matter
    entirely: a temporary or on-the-fly document with a project and a
    slug bound to it is a context like any other, and the launcher offers
    for it accordingly.
    """

    project: str | None = None
    doc_slug: str | None = None

    @property
    def has_document(self) -> bool:
        """A document is identified by its project and its slug together."""
        return bool(self.project) and bool(self.doc_slug)

    @property
    def has_project(self) -> bool:
        return bool(self.project)


def is_valid_here(declaration: ToolDeclaration, context: PageContext) -> bool:
    """Whether a declaration is offerable in this page context.

    The rule reads both halves of the declaration:

    * **target** decides whether there is a workpiece to act on. A
      document-targeted tool needs a document; a project-targeted one
      needs a project, so a project-targeted classifier never appears on
      a lone page with no project to act on.
    * **kind** decides whether this launcher is the right launcher. The
      document view's launcher offers tools, which work in place, and
      instruments, which it hands off to by navigating away. An
      instrument still needs its target satisfied to be worth offering.
    """
    if declaration.target is Target.DOCUMENT and not context.has_document:
        return False
    if declaration.target is Target.PROJECT and not context.has_project:
        return False
    if declaration.kind not in (Kind.TOOL, Kind.INSTRUMENT):  # pragma: no cover
        return False
    return True


def offers_for(
    context: PageContext,
    declarations: Iterable[ToolDeclaration] | None = None,
) -> tuple[ToolDeclaration, ...]:
    """The declarations this page's launcher should offer, in order.

    Tools first, then instruments — a tool acts on the page you are
    reading and an instrument takes you off it, so the in-place actions
    come first. Within each kind, discovery order.
    """
    source: Sequence[ToolDeclaration] = (
        tuple(declarations) if declarations is not None else registry.declarations()
    )
    valid = [d for d in source if is_valid_here(d, context)]
    tools = [d for d in valid if d.kind is Kind.TOOL]
    instruments = [d for d in valid if d.kind is Kind.INSTRUMENT]
    return tuple(tools + instruments)


def resolve_route(
    declaration: ToolDeclaration, context: PageContext
) -> str | None:
    """The concrete URL this tool's API has on this page, or None.

    ``route_prefix`` is a template — ``/api/tools/{project}/{doc_slug}
    /answers``. Filling it in here means the client never assembles a
    path, so the declaration stays the only place a tool's URL is
    written down, on the server side and the browser side both.
    """
    return _fill(declaration.route_prefix, context)


def resolve_alt_route(
    declaration: ToolDeclaration, context: PageContext
) -> str | None:
    """The URL of this tool's second declared scope, or None.

    Only a tool that declared ``also_scoped_to`` has one. It is filled in
    here for the same reason the first is: the client assembles no path,
    so choosing a scope in the browser is choosing between two URLs the
    declaration resolved rather than editing one.

    ``None`` on a page with nothing to fill the template — the document
    scope needs a doc slug, and an aggregate index has none, which is
    why the panel falls back to the project scope there.
    """
    if declaration.also_scoped_to is None:
        return None
    return _fill(declaration.route_prefix_for(declaration.also_scoped_to), context)


def _fill(prefix: str | None, context: PageContext) -> str | None:
    """A route template with this page's identities substituted in.

    The two identities are encoded differently, and the difference is the
    whole of the defect this repairs.

    A **project** slug is one segment — :mod:`docstrap.slugs` guarantees
    it — so its separators, if it somehow had any, would not be its own.
    It is encoded with nothing safe.

    A **document** slug is a PATH below the project's `docs_root` with
    the suffix dropped, ``proposals/0002-the-upgrade-path``, and its
    separators ARE the identity. Encoding them as ``%2F`` spelled a
    one-segment name that no route matched and no project declared, so
    every document-targeted tool 404ed on every document below the root
    while the panel reported the server as absent. ``/`` is therefore
    safe here; every other reserved character is still escaped, so a
    document whose name contains a space or a ``#`` still travels
    correctly.
    """
    if prefix is None:
        return None
    if "{project}" in prefix and not context.project:
        return None
    if "{doc_slug}" in prefix and not context.doc_slug:
        return None
    return prefix.format(
        project=quote(context.project or "", safe=""),
        doc_slug=quote(context.doc_slug or "", safe="/"),
    )


def offer_payload(
    declaration: ToolDeclaration, context: PageContext
) -> dict[str, object]:
    """One offer as the client receives it: the projection plus its URLs."""
    payload = declaration.to_offer()
    payload["route"] = resolve_route(declaration, context)
    payload["altRoute"] = resolve_alt_route(declaration, context)
    return payload


def offers_json(
    context: PageContext,
    declarations: Iterable[ToolDeclaration] | None = None,
) -> str:
    """The offer list as the JSON the client reads. Sorted keys, compact."""
    return json.dumps(
        [offer_payload(d, context) for d in offers_for(context, declarations)],
        sort_keys=True,
        separators=(",", ":"),
    )
