"""Sphinx layout — invokes the project's own conf.py via sphinx-build.

Used when a project ships its own Sphinx configuration (conf.py inside
the docs_root). Docstrap does not modify the project's config; it just
invokes sphinx-build and captures the output.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from docstrap.layouts.base import BuildResult, LayoutError
from docstrap.scan import ScannedProject
from docstrap.sphinx_build import sphinx_build_command


def build(
    project: ScannedProject, out_dir: Path, site_root: Path | None = None
) -> BuildResult:
    """Run sphinx-build against project.docs_dir; write HTML to out_dir/<slug>/."""
    if project.docs_dir is None:
        raise LayoutError(
            f"Project `{project.slug}` declares layout: sphinx but no source is mounted "
            f"at its root, so there is no directory to look for a conf.py in."
        )
    conf_py = project.docs_dir / "conf.py"
    if not conf_py.exists():
        raise LayoutError(
            f"Project `{project.slug}` declares layout: sphinx but has no conf.py at {conf_py}. "
            f"Either add a conf.py, or change the layout to `markdown` (which supplies docstrap's bundled config)."
        )
    html_root = out_dir / project.slug
    html_root.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        sphinx_build_command("-b", "html", "-q", str(project.docs_dir), str(html_root)),
        capture_output=True,
        text=True,
    )
    warnings = result.stderr.count("WARNING")
    if result.returncode != 0:
        raise LayoutError(
            f"sphinx-build failed for `{project.slug}` (exit {result.returncode}).\n"
            f"stderr:\n{result.stderr}"
        )
    return BuildResult(
        project_slug=project.slug,
        html_root=html_root,
        warnings=warnings,
        notes=f"sphinx-build ok ({warnings} warnings)",
    )
