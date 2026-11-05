"""What the frontend build needs to know, read off the declarations.

The build compiles one Svelte bundle per tool, and it must not invent
the names or the locations of what it writes. So it asks here, and this
asks the declarations: a tool's client source is ``ui/`` in its own
directory, its output is ``static/`` in that same directory, and the
two filenames are :attr:`ToolDeclaration.js_bundle` and
:attr:`ToolDeclaration.css_bundle`. Nothing in ``build-tools.mjs``
spells a tool id or a bundle filename.

EXTENSION POINT — a tool gets a Svelte build by putting ``ui/index.ts``
in its own directory. No entry is added anywhere; the same "the
directory is the registration" rule that :mod:`docstrap.tools.registry`
applies to declarations applies here to client source. A tool whose UI
is genuinely tiny may keep hand-written client source in ``static/``
and have no ``ui/`` at all; it simply does not appear in the manifest.

The viewer shell (``docstrap.viewer``) is built here too, and it is the
one target that is not a tool: an application page rather than a bundle
Sphinx adds to every page, so it is described by :func:`shell_target`
rather than by a declaration.

Run as a module to print the manifest the Node build reads::

    uv run python -m docstrap.tools.frontend
"""
from __future__ import annotations

import json
from typing import Any

from docstrap.tools import registry

# The client-source directory inside a tool's own directory. One name,
# written once, because both sides of the build have to agree on it.
UI_DIRNAME = "ui"

# The module the bundler starts from. A directory without this is not a
# built tool, whatever else it holds.
UI_ENTRY = "index.ts"


def build_targets() -> list[dict[str, Any]]:
    """Every tool that ships Svelte client source, and where it goes.

    Each entry carries the absolute entry module, the absolute output
    directory, and the two bundle filenames the declaration derives.
    Ordered by discovery order so a build log reads the same twice.
    """
    targets: list[dict[str, Any]] = []
    for declaration in registry.iter_declarations():
        directory = registry.tool_directory(declaration)
        entry = directory / UI_DIRNAME / UI_ENTRY
        if not entry.is_file():
            continue
        targets.append(
            {
                "id": declaration.id,
                "entry": str(entry),
                "outDir": str(directory / "static"),
                "jsBundle": declaration.js_bundle,
                "cssBundle": declaration.css_bundle,
            }
        )
    return targets


def shell_target() -> dict[str, Any]:
    """Where the viewer shell's source is and where its build goes.

    Every name in it comes from :mod:`docstrap.viewer.manifest`, which is
    also what copies the output into a site, so the two sides cannot
    disagree about what the page or its asset directory is called.
    """
    from docstrap.viewer import manifest

    return {
        "id": "viewer",
        "root": str(manifest.UI_DIR),
        "page": manifest.SHELL_PAGE,
        "assetsDir": manifest.ASSET_DIR,
        "outDir": str(manifest.STATIC_DIR),
    }


def main() -> None:
    """Print the manifest as JSON on stdout. The Node build reads this."""
    print(json.dumps({"tools": build_targets(), "shell": shell_target()}, indent=2))


if __name__ == "__main__":  # pragma: no cover — invoked by the build
    main()
