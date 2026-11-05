"""Discover candidate git repositories in a directory tree.

Reports directories that look like git repos and don't already have a
.docstrap file. Read-only; a helper for finding projects to register.

It also answers the adjacent question of *identity*: two paths can be
the same project seen twice, because a linked git worktree is a second
checkout of one repository. :func:`canonical_dir` maps such a path to
its position in the main working tree, which is how `promdance backup`
stopped reading a worktree and its main checkout as two sources
colliding on one slug.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from docstrap.config import DOCSTRAP_FILENAME, ignores_tree

# Directory names to skip when walking. Standard build / vendored patterns.
SKIP_DIRS = frozenset({
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "target",
    "dist",
    "build",
    "_build",
    ".svelte-kit",
    ".next",
    "site",         # mkdocs default output
    "docs-site-build",
    ".doctrees",
})


@dataclass(frozen=True)
class Candidate:
    """A discovered directory that looks like a git repo boundary."""

    path: Path
    has_docstrap: bool


def find(root: Path) -> list[Candidate]:
    """Walk below root, return sorted list of candidate git-repo dirs.

    A candidate is any directory containing a `.git` entry (directory OR
    file — a file indicates a submodule or worktree). The walker does not
    descend into a discovered repo, so submodules of a submodule are
    reported at their outer boundary only.
    """
    root = root.resolve()
    candidates: list[Candidate] = []
    if ignores_tree(root):
        return candidates
    if _is_git_repo(root):
        candidates.append(_make_candidate(root))
    _walk(root, candidates)
    return sorted(candidates, key=lambda c: c.path)


def _walk(current: Path, out: list[Candidate]) -> None:
    try:
        entries = sorted(current.iterdir())
    except (PermissionError, FileNotFoundError, OSError):
        return
    for entry in entries:
        if not entry.is_dir() or entry.is_symlink():
            continue
        if entry.name in SKIP_DIRS or entry.name.startswith("."):
            continue
        if ignores_tree(entry):
            continue
        if _is_git_repo(entry):
            out.append(_make_candidate(entry))
            # Do not descend into found repos.
        else:
            _walk(entry, out)


def canonical_dir(path: Path) -> Path:
    """Where `path` sits in the main working tree of its repository.

    A linked git worktree is a second checkout of one repository, so
    ``~/wt/myrepo/a-branch/apps/web`` and
    ``~/myrepo/apps/web`` are one project at two paths. Asked
    for either, this returns the second — the main working tree's — so a
    caller comparing directories sees one source rather than a
    collision.

    ``git rev-parse --git-common-dir`` is the authority: in a linked
    worktree it names the *main* repository's git directory, whereas
    ``--git-dir`` names the worktree's own. The main working tree is
    that directory's parent when it is a conventional ``<root>/.git``;
    a bare repository or a separated git dir has no working tree to map
    onto and the path is returned unchanged.

    Never raises. A path outside git, a git that is not installed, and a
    repository shape this does not recognise all resolve to the path
    itself, because identity falling back to "itself" is correct and a
    backup that refused to run without git would not be a safety net.
    """
    resolved = path.expanduser().resolve()
    if not resolved.is_dir():
        return resolved

    common = _git_common_dir(resolved)
    if common is None or common.name != ".git":
        return resolved
    main_root = common.parent
    if main_root == resolved or not main_root.is_dir():
        return resolved

    worktree_root = _git_toplevel(resolved)
    if worktree_root is None:
        return resolved
    if worktree_root == main_root:
        return resolved
    try:
        relative = resolved.relative_to(worktree_root)
    except ValueError:
        return resolved
    candidate = (main_root / relative).resolve()
    return candidate if candidate.is_dir() else resolved


def is_linked_worktree(path: Path) -> bool:
    """True when ``path`` sits in a linked git worktree, not a main checkout.

    A linked worktree's own git directory is not the repository's common
    one, which is the whole test: ``--absolute-git-dir`` names
    ``<main>/.git/worktrees/<name>`` there and ``<main>/.git`` everywhere
    else, including a submodule, whose two answers are one directory.

    Never raises. Outside git, or with no git installed, it is False:
    nothing can be a second checkout of a repository that is not there.
    """
    resolved = path.expanduser().resolve()
    if not resolved.is_dir():
        return False
    own = _git(resolved, "rev-parse", "--absolute-git-dir")
    common = _git_common_dir(resolved)
    if own is None or common is None:
        return False
    return Path(own).resolve() != common


def _git_common_dir(directory: Path) -> Path | None:
    out = _git(directory, "rev-parse", "--git-common-dir")
    if out is None:
        return None
    return (directory / out).resolve() if not Path(out).is_absolute() else Path(out).resolve()


def _git_toplevel(directory: Path) -> Path | None:
    out = _git(directory, "rev-parse", "--show-toplevel")
    return Path(out).resolve() if out else None


def _git(directory: Path, *args: str) -> str | None:
    try:
        proc = subprocess.run(
            ("git", "-C", str(directory), *args),
            check=False,
            text=True,
            capture_output=True,
        )
    except (OSError, ValueError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def _is_git_repo(path: Path) -> bool:
    """True if path contains a `.git` entry (directory OR file)."""
    git_marker = path / ".git"
    return git_marker.is_dir() or git_marker.is_file()


def _make_candidate(path: Path) -> Candidate:
    return Candidate(
        path=path,
        has_docstrap=(path / DOCSTRAP_FILENAME).exists(),
    )
