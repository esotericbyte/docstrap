"""Mounting declared tool routes on the app server.

The server does not know any tool's URL. It walks the declarations,
asks each one for its route prefix, and hands the tool's ``routes``
module the declaration to hang its handlers off. A tool that declares
no ``api_collection`` has no prefix and mounts nothing.
"""
from __future__ import annotations

import importlib
from typing import Iterable

from docstrap.tools import registry
from docstrap.tools.declaration import (
    ToolDeclaration,
    as_server_path,
    check_route_separation,
)


def _routes_module(declaration: ToolDeclaration):
    """The tool's ``routes`` module, or None when it has no routes."""
    try:
        return importlib.import_module(f"{declaration.entry}.routes")
    except ModuleNotFoundError:
        return None


def mount_all(app, declarations: Iterable[ToolDeclaration] | None = None) -> tuple[str, ...]:
    """Mount every declared tool's routes. Returns the paths mounted.

    EXTENSION POINT — a tool serves an API by putting a ``routes``
    module in its own directory with a ``register(app, declaration)``
    function. It reads the path off the declaration it is handed, so
    neither the tool nor the server writes a URL down.

    Ordering follows discovery order so the mounted path list is stable
    and can be asserted against the declarations in a test.

    Every path a tool returns is checked by
    :func:`~docstrap.tools.declaration.check_route_separation` before the
    call returns. The document parameter spans separators, so a project
    URL and a document URL are told apart by segment count alone — and
    that holds only while no route reaches deeper than a base plus its
    collection. The check makes a tool that broke it fail at startup
    rather than quietly answer for another tool's endpoint.
    """
    source = (
        tuple(declarations) if declarations is not None else registry.declarations()
    )
    mounted: list[str] = []
    for declaration in source:
        module = _routes_module(declaration)
        if module is None:
            continue
        register = getattr(module, "register", None)
        if register is None:
            continue
        paths = register(app, declaration) or ()
        mounted.extend(paths)
    check_route_separation(mounted)
    return tuple(mounted)


def declared_route_prefixes() -> dict[str, tuple[str, ...]]:
    """Every tool id that owns an API, mapped to its derived prefixes.

    The expected shape of the server's tool route table, computed from
    declarations alone. Tests compare the real table to this.

    A tuple rather than one string, because a tool may declare a second
    scope (``also_scoped_to``) and be readable under both bases — the
    qapanels instrument is, project-wide and narrowed to one document.
    Everything in here is still derived; nothing is a path written down.
    """
    return {
        declaration.id: declaration.route_prefixes
        for declaration in registry.iter_declarations()
        if declaration.route_prefixes
    }


def declared_server_route_prefixes() -> dict[str, tuple[str, ...]]:
    """The same table in the spelling the ASGI router uses.

    :func:`declared_route_prefixes` is the declaration's own spelling,
    which is what the launcher fills in for the browser. This is that
    table with the document parameter marked as spanning separators,
    which is what a mounted route's path actually reads. Comparing the
    server's real table against this is comparing like with like; the
    translation between them lives in one function
    (:func:`~docstrap.tools.declaration.as_server_path`).
    """
    return {
        tool_id: tuple(as_server_path(prefix) for prefix in prefixes)
        for tool_id, prefixes in declared_route_prefixes().items()
    }
