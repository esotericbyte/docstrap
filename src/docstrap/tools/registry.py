"""Discovery of tool declarations.

Tools are found on the filesystem, not in a list. Every direct
subpackage of :mod:`docstrap.tools` that exposes a ``declaration``
module with a module-level ``DECLARATION`` is a tool. Subpackages whose
name starts with an underscore are shared infrastructure and are
skipped.

That is what makes "adding a tool is adding a directory" true rather
than aspirational: there is no registration list to append to, so
forgetting to append to one cannot happen.
"""
from __future__ import annotations

import importlib
import pkgutil
from functools import lru_cache
from pathlib import Path
from typing import Iterator

from docstrap.tools.declaration import DeclarationError, ToolDeclaration

_TOOLS_PACKAGE = "docstrap.tools"


def _tools_package_path() -> Path:
    return Path(__file__).parent


def discover_in(package: str, path: Path) -> tuple[ToolDeclaration, ...]:
    """Declarations found in the subpackages of ``package`` at ``path``.

    EXTENSION POINT. Discovery is not hardwired to
    :mod:`docstrap.tools`: any importable package laid out the same way
    is a tool source. That is what lets a third party ship tools, and
    what lets a test stand a whole new tool up through the same seams
    the real ones use rather than by patching around them.
    """
    found: list[ToolDeclaration] = []
    seen_ids: dict[str, str] = {}
    names = sorted(
        info.name
        for info in pkgutil.iter_modules([str(path)])
        if info.ispkg and not info.name.startswith("_")
    )
    for name in names:
        module_name = f"{package}.{name}.declaration"
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError:
            # A subpackage with no declaration is not a tool. Silent by
            # design — the directory is the registration, and a
            # directory that does not declare itself has not registered.
            continue
        declaration = getattr(module, "DECLARATION", None)
        if declaration is None:
            continue
        if not isinstance(declaration, ToolDeclaration):
            raise DeclarationError(
                f"{module_name}.DECLARATION is not a ToolDeclaration"
            )
        if declaration.id in seen_ids:
            raise DeclarationError(
                f"duplicate tool id {declaration.id!r} in {module_name} "
                f"and {seen_ids[declaration.id]}"
            )
        if declaration.entry != f"{package}.{name}":
            raise DeclarationError(
                f"{module_name} declares entry {declaration.entry!r} but "
                f"lives in {package}.{name}"
            )
        seen_ids[declaration.id] = module_name
        found.append(declaration)
    return tuple(found)


@lru_cache(maxsize=1)
def _discover() -> tuple[ToolDeclaration, ...]:
    return discover_in(_TOOLS_PACKAGE, _tools_package_path())


def iter_declarations() -> Iterator[ToolDeclaration]:
    """Every declared tool, in stable (directory-name) order."""
    return iter(_discover())


def declarations() -> tuple[ToolDeclaration, ...]:
    """Every declared tool as a tuple."""
    return _discover()


def get(tool_id: str) -> ToolDeclaration:
    """One declaration by id. Raises :class:`KeyError` if unknown."""
    for declaration in _discover():
        if declaration.id == tool_id:
            return declaration
    raise KeyError(tool_id)


def tool_directory(declaration: ToolDeclaration) -> Path:
    """The on-disk directory that holds everything belonging to a tool.

    Resolved through the declared entry point rather than assumed to sit
    under this package, so a tool shipped from elsewhere finds its own
    assets.
    """
    module = importlib.import_module(declaration.entry)
    return Path(module.__file__).parent  # type: ignore[arg-type]


def static_directory(declaration: ToolDeclaration) -> Path:
    """The tool's own ``static/`` dir — its client source and styles."""
    return tool_directory(declaration) / "static"


def sphinx_extensions() -> tuple[str, ...]:
    """Entry points for a generated ``conf.py`` ``extensions`` list.

    The build reads this instead of naming modules, so a new tool
    directory appears in the built site without the layout template
    being touched. The launcher goes after the tools: it needs the tools
    it offers to have registered their assets first. The viewer button
    goes last, because it is what runs every script registered before it
    once the page is inside the viewer.
    """
    return tuple(declaration.entry for declaration in _discover()) + (
        "docstrap.sphinx.launcher",
        "docstrap.sphinx.viewer_button",
    )


def reset_cache() -> None:
    """Forget discovered declarations. For tests that add a tool dir."""
    _discover.cache_clear()
