from __future__ import annotations

import os
import shlex
import subprocess
import sys
import textwrap
from pathlib import Path

from docstrap import generated_indexes


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "scrub-docstrap-generated-indexes.sh"


def _run(command: list[str], cwd: Path, **kwargs) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=True,
        **kwargs,
    )


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return _run(["git", "-C", str(repo), *args], cwd=repo)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _fixture_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "rlp"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")
    _write(repo / ".docstrap", "version: 1\ntitle: Fixture\n")
    _write(repo / "docs/generated/topic.md", "# Topic\n")
    _write(
        repo / "docs/generated/index.md",
        generated_indexes.legacy_markdown(
            repo / "docs/generated", {"archive", "deprecated"}, set()
        ),
    )
    _write(repo / "docs/authored/topic.md", "# Authored topic\n")
    _write(repo / "docs/authored/index.md", "# Authored\n")
    _write(repo / "docs/adr/0001-decision.md", "# Decision\n")
    _write(repo / "docs/adr/index.md", "# Log4brains\n")
    _write(repo / "notes/index.md", "# Outside docstrap report\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "fixture")
    return repo


def _docstrap_wrapper(tmp_path: Path) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    wrapper = bin_dir / "docstrap"
    wrapper.write_text(
        textwrap.dedent(
            f"""\
            #!/usr/bin/env bash
            exec {shlex.quote(sys.executable)} -m docstrap.cli "$@"
            """
        ),
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    return bin_dir


def _env(bin_dir: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    return env


def test_scrubber_removes_only_docstrap_claimed_index_files(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    bin_dir = _docstrap_wrapper(tmp_path)

    dry = _run(["bash", str(SCRIPT), str(repo)], cwd=REPO_ROOT, env=_env(bin_dir))
    assert "would remove: docs/generated/index.md" in dry.stdout
    assert "docs/authored/index.md - divergent; docstrap does not claim this file" in dry.stdout
    assert "notes/index.md - not reported by docstrap generated-indexes" in dry.stdout
    assert "docs/adr/index.md - Log4brains residue from a retired tool; not touched" in dry.stdout
    assert (repo / "docs/generated/index.md").exists()

    applied = _run(
        ["bash", str(SCRIPT), "--apply", str(repo)], cwd=REPO_ROOT, env=_env(bin_dir)
    )
    assert "removed and staged: 1 file(s)" in applied.stdout

    assert not (repo / "docs/generated/index.md").exists()
    assert (repo / "docs/authored/index.md").exists()
    assert (repo / "docs/adr/index.md").exists()
    assert (repo / "notes/index.md").exists()
    assert _git(repo, "status", "--short").stdout.splitlines() == [
        "D  docs/generated/index.md"
    ]


def test_scrubber_skips_dirty_tracked_repositories(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    bin_dir = _docstrap_wrapper(tmp_path)
    (repo / "docs/authored/index.md").write_text("# Dirty\n", encoding="utf-8")

    result = subprocess.run(
        ["bash", str(SCRIPT), "--apply", str(repo)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        env=_env(bin_dir),
        check=False,
    )

    assert result.returncode == 1
    assert "SKIPPED: dirty tracked tree" in result.stdout
    assert (repo / "docs/generated/index.md").exists()
    assert _git(repo, "status", "--short").stdout.splitlines() == [
        " M docs/authored/index.md"
    ]
