"""Docstrap tools and instruments — one directory per tool.

Each tool owns a directory here holding everything that belongs to it:
its declaration, its server routes, its views, and its client source
under ``static/``. The filesystem answers "what belongs to the
reviewer" in one place, and adding a tool is adding a directory.

The pieces shared across tools:

* :mod:`docstrap.tools.declaration` — the declaration object itself.
* :mod:`docstrap.tools.registry` — filesystem discovery of declarations.
* :mod:`docstrap.tools.launcher` — which tools a page's launcher offers.
* :mod:`docstrap.tools.mounting` — mounting declared routes on the app.
"""
from __future__ import annotations

from docstrap.tools.declaration import (
    DeclarationError,
    Kind,
    Target,
    ToolDeclaration,
)

__all__ = [
    "DeclarationError",
    "Kind",
    "Target",
    "ToolDeclaration",
]
