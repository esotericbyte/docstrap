#!/usr/bin/env python3
"""Fail if an index file is committed into a documentation tree.

    scripts/check-no-index-md.py                  # this repository
    scripts/check-no-index-md.py /path/to/repo …

The captain, 2026-09-30: *"do strap must create them ephmerally. as part
of it's build in it's own directories. you can clean those all up. no
index.md in docs/ trees. At all. period."*

docstrap composes every section page during its build, inside the build's
own scratch tree, and renders it straight to HTML. A committed `index.md`
in a docs tree is therefore never needed and never honoured: the build
does not publish one. This is the other half of that rule — the build
cannot write one, and this stops one arriving by hand.
`packages/docstrap/docs/spec.md` §7.8.3 is the rule; §7.8.1 is how
fifty-five of them reached five repositories.

Self-contained on purpose — git and the standard library, with PyYAML
used only if it is importable — because the repositories that still carry
the pollution are cleaned under their own tasks and can run this as it
stands.

**What counts as a documentation tree**, and the check fails on these:

1. Any tracked path with a directory component named `docs`. That is the
   convention every `docs_root` in these repositories uses.
2. Any `docs_root` a tracked `.docstrap` declares. Read through PyYAML;
   without it the declarations are skipped and the report says so rather
   than claiming a pass it did not establish.

Every other tracked index file is **listed and does not fail**. A Sphinx
source root's own `index.md` is that site's master document rather than
pollution in a document directory, and the distinction is the reason this
check reports what it did not enforce instead of staying quiet about it.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

#: Both suffixes, because the build refuses both: an `index.rst` is the
#: same file under another name and shadows the same composed page.
INDEX_NAMES = frozenset({"index.md", "index.rst"})

USAGE = "usage: check-no-index-md.py [REPO ...]"


def tracked_files(repo: Path) -> list[str]:
    """Every path git tracks in ``repo``, repository-relative."""
    out = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "-z"],
        capture_output=True,
        check=True,
    ).stdout.decode("utf-8", errors="replace")
    return [path for path in out.split("\0") if path]


def declared_docs_roots(repo: Path, tracked: list[str]) -> tuple[set[str], str]:
    """Every ``docs_root`` the repository's `.docstrap` files declare.

    Returns the roots and a note about what could not be read, so a run
    with no YAML available reports a narrower check rather than a clean
    one.
    """
    try:
        import yaml
    except ImportError:
        return set(), (
            "PyYAML is not importable, so declared docs_root entries were not "
            "read; only directories named `docs` were enforced"
        )

    roots: set[str] = set()
    for config in (p for p in tracked if Path(p).name == ".docstrap"):
        try:
            data = yaml.safe_load((repo / config).read_text(encoding="utf-8")) or {}
        except Exception:  # noqa: BLE001 — an unreadable declaration is not this check's business
            continue
        base = Path(config).parent
        for key in ("projects", "related_directories"):
            for entry in data.get(key) or ():
                if not isinstance(entry, dict) or not entry.get("path"):
                    continue
                root = base / entry["path"] / (entry.get("docs_root") or "")
                roots.add(os.path.normpath(str(root)))
    return roots, ""


def in_docs_tree(path: str, declared: set[str]) -> bool:
    """Whether ``path`` sits inside a documentation tree."""
    if "docs" in Path(path).parts[:-1]:
        return True
    parent = os.path.normpath(str(Path(path).parent))
    return any(
        parent == root or parent.startswith(root + os.sep) for root in declared
    )


def check(repo: Path) -> bool:
    """Report on one repository. True when it passes."""
    print(f"repository: {repo}")
    tracked = tracked_files(repo)
    declared, note = declared_docs_roots(repo, tracked)
    if note:
        print(f"  note: {note}")

    indexes = [p for p in tracked if Path(p).name in INDEX_NAMES]
    offending = sorted(p for p in indexes if in_docs_tree(p, declared))
    elsewhere = sorted(p for p in indexes if not in_docs_tree(p, declared))

    if elsewhere:
        print(
            f"  outside a documentation tree, not enforced: {len(elsewhere)} — "
            f"a Sphinx source root's own index.md is that site's master "
            f"document, hand-written and never regenerated, rather than a "
            f"generated index sitting in a document directory"
        )
        for path in elsewhere:
            print(f"    {path}")

    if offending:
        print(
            f"  FAIL: index file(s) committed into a documentation tree: "
            f"{len(offending)}"
        )
        for path in offending:
            print(f"    {path}")
        print(
            "  An index is composed by the build and rendered as HTML; none "
            "belongs in a document directory. Delete these."
        )
        return False

    print("  ok: no index file in any documentation tree")
    return True


def main(argv: list[str]) -> int:
    if argv and argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    if any(arg.startswith("-") for arg in argv):
        print(USAGE, file=sys.stderr)
        return 2

    passed = True
    for candidate in argv or ["."]:
        try:
            top = subprocess.run(
                ["git", "-C", candidate, "rev-parse", "--show-toplevel"],
                capture_output=True,
                check=True,
            ).stdout.decode().strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"check-no-index-md: not a git repository: {candidate}", file=sys.stderr)
            return 2
        passed = check(Path(top)) and passed
        print()
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
