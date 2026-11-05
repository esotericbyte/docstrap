"""Shared fixtures: real document trees, copied somewhere they can be read.

The fixture documents in ``tests/fixtures`` are ordinary files on disk and
the tests read them as such — no mocked filesystem, no synthesised
front-matter strings standing in for documents.

They are copied into ``tmp_path`` for each test rather than read in place
for two reasons. The copy is outside any git repository, so the ``created``
/ ``updated`` history step falls to filesystem mtime deterministically
instead of depending on whether the fixture happens to be committed yet;
and a test that somehow wrote to a document would damage a throwaway copy
rather than the fixture, which matters for a reader whose central promise
is that it never writes.
"""
from __future__ import annotations

import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixture_tree(tmp_path: Path):
    """Copy a named tree out of tests/fixtures and return its new root."""

    def _copy(name: str) -> Path:
        destination = tmp_path / name
        shutil.copytree(FIXTURES / name, destination)
        return destination

    return _copy


@pytest.fixture
def collection(fixture_tree) -> Path:
    """The `.docstrap` collection fixture: a docs tree with a config."""
    return fixture_tree("collection")


@pytest.fixture
def workspace(fixture_tree) -> Path:
    """The uv workspace fixture: a root, two members, root-level prompts."""
    return fixture_tree("workspace")


@pytest.fixture
def question_workspace(fixture_tree) -> Path:
    """Two sibling projects and a related directory, all posing questions.

    Alpha carries the awkward cases a project declares away — an
    `exclude_dirs` directory, a subtree with its own `ignore: true`, a
    draft, and a document outside `docs_root` — so a scoped run over it has
    to get both what it collects and what it leaves alone right.
    """
    return fixture_tree("question-workspace")


@pytest.fixture
def doctor_workspace(fixture_tree) -> Path:
    """The doctor fixture: a workspace-root `docs/` of mixed scoping.

    Two documents nothing scopes, one scoped by front-matter, one inside a
    member, one under `archive/`, and a README outside `docs/` — so a run
    of doctor over it has to get both the finding and the not-a-finding
    right.
    """
    return fixture_tree("doctor-workspace")


def _redirect_home(home: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for variable, name in (
        ("XDG_DATA_HOME", "share"),
        ("XDG_CONFIG_HOME", "config"),
        ("XDG_CACHE_HOME", "cache"),
        ("XDG_STATE_HOME", "state"),
    ):
        directory = home / ".local" / name
        directory.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv(variable, str(directory))
    monkeypatch.setenv("HOME", str(home))
    return home


@pytest.fixture
def user_dirs(tmp_path: Path, monkeypatch) -> Path:
    """Redirect the user-level directories at a throwaway home.

    Real drafts live in the real home; a test that built a project there
    would write promdance storage into it.
    """
    return _redirect_home(tmp_path / "home", monkeypatch)


@pytest.fixture(scope="session", autouse=True)
def _session_home(tmp_path_factory) -> Iterator[Path]:
    """A throwaway home under the module-scoped fixtures as well.

    Several modules build a site once, in a Sphinx subprocess, from a
    module-scoped fixture — which runs before any function-scoped one can
    redirect anything, and wrote the real ``metadata.db`` while it did.
    """
    with pytest.MonkeyPatch.context() as monkeypatch:
        yield _redirect_home(tmp_path_factory.mktemp("session-home"), monkeypatch)


@pytest.fixture(autouse=True)
def _never_the_real_home(user_dirs: Path) -> Path:
    """Every test runs against a throwaway home, asked for or not.

    A build writes the file index into the metadata store and attaches
    promdance storage, and both resolve through the home directory. Tests
    that built without asking for ``user_dirs`` left rows in the real
    ``metadata.db`` and entries in the real promdance store; this makes
    the redirect the default rather than something each test remembers.
    """
    return user_dirs
