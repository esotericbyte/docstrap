"""User-level directory resolution via platformdirs.

Centralised so every module reaches for paths through the same helpers.
"""
from __future__ import annotations

from pathlib import Path

from platformdirs import PlatformDirs

_dirs = PlatformDirs(appname="docstrap", appauthor=False)


def config_dir() -> Path:
    """User config directory. Contains config.yaml, cached settings."""
    return Path(_dirs.user_config_dir)


def data_dir() -> Path:
    """User data directory. Contains build output, DBs, drafts."""
    return Path(_dirs.user_data_dir)


def cache_dir() -> Path:
    """User cache directory. Regenerable derived artefacts."""
    return Path(_dirs.user_cache_dir)


def state_dir() -> Path:
    """User state directory. Logs, run history."""
    return Path(_dirs.user_state_dir)


def user_config_file() -> Path:
    """Path to the top-level user config file."""
    return config_dir() / "config.yaml"


def metadata_db_path() -> Path:
    """Path to the docstrap metadata SQLite database."""
    return data_dir() / "metadata.db"


def annotations_db_path() -> Path:
    """Path to the docstrap annotations SQLite database (separate file)."""
    return data_dir() / "annotations.db"


def build_output_dir() -> Path:
    """Where docstrap writes the aggregate site output."""
    return data_dir() / "site"


def ensure_dirs() -> None:
    """Create all user-level docstrap directories if they don't exist.

    A plugin's own directories are its business: ``docstrap init`` asks
    each enabled plugin to make them (:func:`docstrap.plugins.init`).
    """
    for d in (config_dir(), data_dir(), cache_dir(), state_dir(), build_output_dir()):
        d.mkdir(parents=True, exist_ok=True)
