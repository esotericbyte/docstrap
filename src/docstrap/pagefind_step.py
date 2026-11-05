"""Post-build step: run pagefind over the aggregate site to produce a search index.

The binary is found by the upstream ``pagefind`` Python package, which
docstrap depends on with its ``bin`` extra: ``PAGEFIND_BINARY_PATH`` if set,
then the binary that extra installs, then ``pagefind`` on PATH.

If no binary is found, the step is skipped with a note naming the package
to install (the build still succeeds without a search index).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from pagefind.service import get_executable

#: What to install when no binary is found.
MISSING_BINARY = (
    "pagefind binary not found: install the Python package `pagefind[bin]` "
    "or put `pagefind` on PATH; search index skipped"
)


def find_pagefind_binary() -> Path | None:
    """Return a usable pagefind binary path, or None if none is found."""
    try:
        return get_executable()
    except FileNotFoundError:
        # `pagefind_bin` is importable but its binary is missing.
        return None


def run_pagefind(site_root: Path) -> tuple[bool, str]:
    """Run pagefind --site <site_root>. Returns (success, notes)."""
    binary = find_pagefind_binary()
    if binary is None:
        return False, MISSING_BINARY
    result = subprocess.run(
        [str(binary), "--site", str(site_root)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False, f"pagefind exited {result.returncode}: {result.stderr.strip()[:200]}"
    # Pagefind writes /pagefind/ subdirectory under site_root.
    return True, f"pagefind index written to {site_root}/pagefind/"
