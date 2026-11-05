"""Check and update .gitignore for docstrap-relevant entries.

Docstrap generates a build-output directory inside each project's
tree, and a plugin may generate entries of its own there — a link to a
draft area, say. All of them should be gitignored so they don't end up
committed accidentally. A plugin's lines come from the plugin;
docstrap's own are :data:`DOCSTRAP_PATTERNS`.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

# Patterns docstrap itself wants in .gitignore for any registered project.
DOCSTRAP_PATTERNS = ("docstrap-build/",)


def required_patterns() -> tuple[str, ...]:
    """Every pattern a registered project needs: the plugins', then docstrap's."""
    from docstrap import plugins

    contributed = plugins.gitignore_patterns()
    return contributed + tuple(p for p in DOCSTRAP_PATTERNS if p not in contributed)


@dataclass
class CheckResult:
    """Outcome of a .gitignore check for one project."""

    gitignore_path: Path
    exists: bool
    missing: list[str]
    present: list[str]

    @property
    def ok(self) -> bool:
        return self.exists and not self.missing


def check(project_root: Path, patterns: Sequence[str] | None = None) -> CheckResult:
    """Report which required patterns are missing from `.gitignore`.

    ``patterns`` defaults to :func:`required_patterns`.
    """
    if patterns is None:
        patterns = required_patterns()
    gi = project_root / ".gitignore"
    if not gi.exists():
        return CheckResult(
            gitignore_path=gi,
            exists=False,
            missing=list(patterns),
            present=[],
        )
    lines = _read_effective_lines(gi)
    equivalent = {_equivalent(line) for line in lines}
    missing: list[str] = []
    present: list[str] = []
    for pat in patterns:
        if _equivalent(pat) in equivalent:
            present.append(pat)
        else:
            missing.append(pat)
    return CheckResult(gitignore_path=gi, exists=True, missing=missing, present=present)


def fix(project_root: Path, patterns: Sequence[str] | None = None) -> CheckResult:
    """Add missing required patterns to `.gitignore`. Idempotent."""
    result = check(project_root, patterns=patterns)
    if result.ok:
        return result
    gi = result.gitignore_path
    to_add = result.missing
    if not gi.exists():
        gi.write_text(_build_new_gitignore(to_add), encoding="utf-8")
    else:
        with gi.open("a", encoding="utf-8") as f:
            existing = gi.read_text(encoding="utf-8")
            if existing and not existing.endswith("\n"):
                f.write("\n")
            f.write("\n# Added by docstrap gitignore-check --fix\n")
            for pat in to_add:
                f.write(f"{pat}\n")
    return check(project_root, patterns=patterns)


def _equivalent(pattern: str) -> str:
    """The form two spellings of one ignore rule share.

    `drafts` and `drafts/` ignore the same directory. Git treats the
    second as directory-only and the first as either, so they are not
    identical rules — but for docstrap's question, "is this directory
    ignored?", both answer yes. Reading them as different is what made
    a hand-written line for a draft link look missing and
    would have had `--fix` append a second rule beneath it.

    Leading `./` is stripped for the same reason.
    """
    text = pattern.strip()
    if text.startswith("./"):
        text = text[2:]
    return text.rstrip("/")


def _read_effective_lines(gi: Path) -> set[str]:
    """Read .gitignore, strip comments/whitespace, return set of patterns."""
    result: set[str] = set()
    for raw in gi.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        result.add(line)
    return result


def _build_new_gitignore(patterns: list[str]) -> str:
    header = "# Created by docstrap gitignore-check --fix\n\n"
    body = "\n".join(patterns) + "\n"
    return header + body
