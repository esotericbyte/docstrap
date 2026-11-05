"""Setup helpers for firstmate operational-home exclusions.

Docstrap runtime scans only honor declarations in `.docstrap`; they do
not carry built-in path prohibitions. This module supports a setup-style
check that detects firstmate operational homes by shape and offers to
write the normal `ignore: true` declaration there.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from docstrap.config import DOCSTRAP_FILENAME, ignores_tree
from docstrap.projectfinder import SKIP_DIRS


@dataclass(frozen=True)
class FirstmateHome:
    """A directory that looks like a firstmate operational home."""

    path: Path
    agents_file: Path
    bin_scripts: tuple[Path, ...]
    projects_dir: Path


def detect_firstmate_homes(root: Path) -> list[FirstmateHome]:
    """Find firstmate-shaped directories below root without following symlinks."""
    root = root.expanduser().resolve()
    if not root.exists() or not root.is_dir():
        return []

    homes: list[FirstmateHome] = []

    def walk(current: Path) -> None:
        home = _firstmate_home_at(current)
        if home is not None:
            homes.append(home)
            return

        try:
            entries = sorted(current.iterdir())
        except (OSError, PermissionError, FileNotFoundError):
            return
        for entry in entries:
            if entry.is_symlink() or not entry.is_dir():
                continue
            if entry.name in SKIP_DIRS or entry.name.startswith("."):
                continue
            walk(entry)

    walk(root)
    return sorted(homes, key=lambda home: home.path)


def ensure_ignore_declaration(directory: Path) -> bool:
    """Ensure directory's `.docstrap` declares `ignore: true`.

    Returns True if the file changed.
    """
    config_path = directory / DOCSTRAP_FILENAME
    if ignores_tree(directory):
        return False

    if not config_path.exists():
        config_path.write_text(
            f"version: 1\ntitle: {directory.name}\nignore: true\n",
            encoding="utf-8",
        )
        return True

    content = config_path.read_text(encoding="utf-8")
    replaced = re.subn(
        r"(?m)^(\s*)ignore\s*:.*$",
        "ignore: true",
        content,
        count=1,
    )
    if replaced[1]:
        new_content = replaced[0]
    else:
        separator = "" if not content or content.endswith("\n") else "\n"
        new_content = f"{content}{separator}ignore: true\n"
    if new_content == content:
        return False
    config_path.write_text(new_content, encoding="utf-8")
    return True


def _firstmate_home_at(path: Path) -> FirstmateHome | None:
    agents_file = path / "AGENTS.md"
    bin_dir = path / "bin"
    projects_dir = path / "projects"
    if not agents_file.is_file() or not bin_dir.is_dir() or not projects_dir.is_dir():
        return None

    bin_scripts = tuple(sorted(p for p in bin_dir.glob("fm-*.sh") if p.is_file()))
    if not bin_scripts:
        return None

    return FirstmateHome(
        path=path,
        agents_file=agents_file,
        bin_scripts=bin_scripts,
        projects_dir=projects_dir,
    )
