"""Shared types for layout builders."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class LayoutError(Exception):
    """Raised when a layout build fails or is misconfigured."""


@dataclass(frozen=True)
class BuildResult:
    """Result of building one project."""

    project_slug: str
    html_root: Path        # absolute; where the project's built HTML landed
    warnings: int = 0
    notes: str = ""
