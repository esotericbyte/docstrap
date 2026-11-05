"""One slugifier: `docstrap.slugs`, and the names it gives stay put.

The defect it guards: a second slugifier in the tools, handed a project's
title rather than its slug, wrote answers and reviews to a directory the
project never links to, and nothing errored. The end-to-end proof of that
chain, through promdance's store, is promdance's
`tests/test_storage_owner.py`; this module holds the ownership itself.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from docstrap import paths
from docstrap.slugs import slugify


PACKAGE = Path(paths.__file__).parent


def _sources() -> list[Path]:
    return sorted(PACKAGE.rglob("*.py"))


def test_only_the_slug_module_reaches_for_the_slug_library():
    offenders = [
        path.name
        for path in _sources()
        if path.name != "slugs.py"
        and "from slugify import" in path.read_text(encoding="utf-8")
    ]
    assert offenders == []


def test_no_hand_rolled_slugifier_survives():
    """Both removed implementations, matched by their own source."""
    for fingerprint in ('c.isalnum() or c in "-_."', 'def _slugify('):
        offenders = [
            path.name
            for path in _sources()
            if fingerprint in path.read_text(encoding="utf-8")
        ]
        assert offenders == [], fingerprint


# --- the slugs themselves stay put -------------------------------------------


@pytest.mark.parametrize(
    "value,expected",
    [
        # Directory names that stores already hold on disk. Adopting a
        # library must not rename any of them.
        ("apps/review-app", "apps__review-app"),
        ("apps/review-app-classic", "apps__review-app-classic"),
        ("apps/sheets-pub", "apps__sheets-pub"),
        ("apps/desktop-app", "apps__desktop-app"),
        ("apps/old-pipeline", "apps__old-pipeline"),
        ("packages/docstrap", "packages__docstrap"),
        ("packages/widgets", "packages__widgets"),
        ("packages/gadgets", "packages__gadgets"),
        ("docs", "docs"),
        ("toolbox", "toolbox"),
        ("Widgetry", "widgetry"),
        # Behaviour the old implementation also had.
        ("My Project Title", "my-project-title"),
        ("docs.v2/index", "docs-v2__index"),
        ("data_kit/amrs", "data_kit__amrs"),
        (r"windows\path", "windows__path"),
        # Behaviour it did not: transliteration instead of a non-ASCII
        # directory name, and never an empty path component.
        ("Café Über", "cafe-uber"),
        ("", "unnamed"),
        ("---", "unnamed"),
    ],
)
def test_slugs_are_what_the_directories_on_disk_are_named(value: str, expected: str):
    assert slugify(value) == expected


@pytest.mark.parametrize(
    "value",
    ["apps/review-app", "Review App", "docs.v2/index", "Café Über", ""],
)
def test_slugifying_a_slug_changes_nothing(value: str):
    """Callers hand slugs back through; a second pass must not move them."""
    once = slugify(value)
    assert slugify(once) == once
