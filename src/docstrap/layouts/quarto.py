"""Quarto layout — stub. Not yet implemented in Alpha 1."""
from __future__ import annotations

from pathlib import Path

from docstrap.layouts.base import BuildResult, LayoutError
from docstrap.scan import ScannedProject


def build(
    project: ScannedProject, out_dir: Path, site_root: Path | None = None
) -> BuildResult:
    raise LayoutError(
        f"Layout `quarto` is not yet implemented (project `{project.slug}`). "
        f"Change layout to `markdown` or `sphinx` for now."
    )
