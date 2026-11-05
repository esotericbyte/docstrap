"""Helpers for launching Sphinx from docstrap's own environment."""
from __future__ import annotations

import sys


def sphinx_build_command(*args: str) -> list[str]:
    """Return argv for a Sphinx build in the active docstrap environment."""
    # uv tool installs expose only docstrap on PATH. Running Sphinx through
    # this interpreter keeps isolated tool installs and `uv run docstrap`
    # on the same dependency resolution path.
    return [sys.executable, "-m", "sphinx", *args]
