"""Layout dispatch: given a scanned project, invoke the right builder.

Each layout handles building one project's docs. The dispatcher
(`build_project`) picks the right layout based on the project's
declared `layout:` field and returns the path to the built HTML root
for that project.
"""
from __future__ import annotations

from pathlib import Path

from docstrap.layouts.base import BuildResult, LayoutError
from docstrap.scan import ScannedProject


def build_project(
    project: ScannedProject, out_dir: Path, site_root: Path | None = None
) -> BuildResult:
    """Dispatch to the right layout builder for a project.

    ``site_root`` is where the viewer shell is published, or None. Only a
    layout docstrap configures can give its pages a way into it; the
    others accept it and leave the project's own pages as they are.
    """
    from docstrap.layouts import markdown, mkdocs, quarto, sphinx

    layout_map = {
        "sphinx": sphinx.build,
        "markdown": markdown.build,
        "mkdocs": mkdocs.build,
        "quarto": quarto.build,
    }
    builder = layout_map.get(project.layout)
    if builder is None:
        raise LayoutError(f"Unknown layout `{project.layout}` for project `{project.slug}`")
    return builder(project, out_dir, site_root)


__all__ = ["build_project", "BuildResult", "LayoutError"]
