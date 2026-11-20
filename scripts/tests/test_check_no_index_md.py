"""Nobody commits an `index.md` into a docs tree.

The rule has two ends. A build writes none, and docstrap's own suite
holds that end. This file holds the other: `scripts/check-no-index-md.py`
run over this repository, as a commit hook would, plus the evidence that
it explains an exemption and fails on a committed file.

The script is self-contained so the repositories that still carry the
pollution — `rlp` has seven committed, `formizer` has them too — can run
it as it stands when each is cleaned under its own task.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

#: The repository this file lives in. `scripts/` is at its root.
REPO_ROOT = Path(__file__).resolve().parents[2]
CHECK_SCRIPT = REPO_ROOT / "scripts" / "check-no-index-md.py"


def _run_check(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CHECK_SCRIPT), *args],
        capture_output=True,
        text=True,
    )


def _git_add_all(repo: Path) -> None:
    """Make ``repo`` a git repository tracking everything in it."""
    for command in (
        ["git", "init", "-q"],
        ["git", "add", "-A"],
    ):
        subprocess.run(command, cwd=repo, check=True, capture_output=True)


def test_no_index_file_is_committed_into_a_docs_tree():
    """The check, run over this repository, as a commit hook would."""
    if not (REPO_ROOT / ".git").exists():
        pytest.skip(f"{REPO_ROOT} is not a git checkout")

    result = _run_check(str(REPO_ROOT))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "no index file in any documentation tree" in result.stdout


def test_the_check_says_why_a_file_is_exempt_and_not_merely_that_it_is(
    tmp_path: Path,
):
    """A bare count invites deletion on a literal reading of the rule.

    The exemption is the one place the captain's *"At all. period."* can
    be read two ways, so the output carries the distinction it turns on
    — a master document against a generated index — and a reader does
    not have to find the spec to know which they are looking at. This
    repository carries no exempt file, so a Sphinx source root's master
    document is made here for the check to explain.
    """
    repo = tmp_path / "repo"
    (repo / "site").mkdir(parents=True)
    (repo / "site" / "index.md").write_text("# The site\n", encoding="utf-8")
    _git_add_all(repo)

    stdout = _run_check(str(repo)).stdout
    reason = next(
        line for line in stdout.splitlines() if "not enforced" in line
    )
    assert "master document" in reason
    assert "never regenerated" in reason
    assert "document directory" in reason


def test_the_check_fails_on_a_committed_index_file(tmp_path: Path):
    """And it is a check rather than a description: it fails.

    Two trees in one repository — a directory named `docs`, and a
    `docs_root` a `.docstrap` declares under another name — because the
    second is the one a convention-based check would miss.
    """
    repo = tmp_path / "repo"
    (repo / "docs" / "specs").mkdir(parents=True)
    (repo / "manual").mkdir()
    (repo / "docs" / "specs" / "index.md").write_text("# Stale\n", encoding="utf-8")
    (repo / "manual" / "index.md").write_text("# Also stale\n", encoding="utf-8")
    (repo / ".docstrap").write_text(
        "version: 1\ntitle: T\nprojects:\n  - path: .\n    docs_root: manual\n",
        encoding="utf-8",
    )
    # A Sphinx source root's own master document, which is not pollution
    # in a document directory and must not fail the check.
    (repo / "site").mkdir()
    (repo / "site" / "index.md").write_text("# The site\n", encoding="utf-8")

    _git_add_all(repo)

    result = _run_check(str(repo))
    assert result.returncode == 1, result.stdout + result.stderr
    assert "docs/specs/index.md" in result.stdout
    assert "manual/index.md" in result.stdout
    assert "outside a documentation tree, not enforced" in result.stdout
    assert "site/index.md" in result.stdout
