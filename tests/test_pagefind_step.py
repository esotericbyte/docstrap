"""The search index step finds pagefind through the upstream package, or says what to install."""
from __future__ import annotations

from pathlib import Path

from docstrap import pagefind_step


def test_the_binary_comes_from_the_upstream_package():
    """`pagefind[bin]` is a dependency, so a plain install finds a binary."""
    binary = pagefind_step.find_pagefind_binary()
    assert binary is not None and binary.is_file()


def test_with_no_binary_the_step_is_skipped_naming_the_package(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(pagefind_step, "get_executable", lambda: None)
    ok, note = pagefind_step.run_pagefind(tmp_path)
    assert not ok
    assert "`pagefind[bin]`" in note


def test_a_bin_package_without_its_binary_counts_as_none(monkeypatch):
    def missing():
        raise FileNotFoundError("no binary")

    monkeypatch.setattr(pagefind_step, "get_executable", missing)
    assert pagefind_step.find_pagefind_binary() is None
