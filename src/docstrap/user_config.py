"""User-level config: the list of registered .docstrap stores.

Lives at ~/.config/docstrap/config.yaml (via platformdirs). The user
config's job is to remember which .docstrap files this user wants
aggregated together. Individual .docstrap files still describe their
own projects; the user config is the outer index.

The same file is the installation level of the one settings surface —
`sources` and `plugins` — which :mod:`docstrap.settings` reads and is
the only code to write. This module keeps the stores list, and saves it
through that module, so a save never disturbs a key it does not own.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from docstrap import paths


@dataclass
class UserConfig:
    """Contents of ~/.config/docstrap/config.yaml."""

    version: int = 1
    stores: list[Path] = field(default_factory=list)
    # The command the "answers done" prompt runs, as an argv list run
    # without a shell. None means unset, and then the prompt
    # is not offered at all; absent is never written back.
    answers_done_command: list[str] | None = None

    def to_dict(self) -> dict:
        """The keys this module owns. None means remove the key."""
        return {
            "version": self.version,
            "stores": [str(s) for s in self.stores],
            "answers_done_command": (
                list(self.answers_done_command)
                if self.answers_done_command is not None else None
            ),
        }


def load() -> UserConfig:
    """Load the user config, or return an empty one if none exists."""
    path = paths.user_config_file()
    if not path.exists():
        return UserConfig()
    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    stores = [Path(s) for s in (raw.get("stores") or [])]
    answers_done = raw.get("answers_done_command")
    return UserConfig(
        version=int(raw.get("version", 1)),
        stores=stores,
        answers_done_command=_argv(answers_done),
    )


def _argv(value: object) -> list[str] | None:
    """A non-empty list of strings, or None for anything else.

    An argv list is what is run, so a bare string is not accepted: it
    would have to be split by somebody's notion of a shell, and nothing
    here runs one.
    """
    if not isinstance(value, list) or not value:
        return None
    if not all(isinstance(part, str) and part for part in value):
        return None
    return list(value)


def save(cfg: UserConfig) -> None:
    """Write this module's keys to the user config, leaving every other as found.

    Creates the file and its parent directories if needed. Goes through
    :func:`docstrap.settings.write_user_fields`, the one writer, so the
    `sources` and `plugins` a person wrote — and their comments — survive.
    """
    from docstrap import settings

    settings.write_user_fields(cfg.to_dict())


def add_store(docstrap_path: Path) -> tuple[UserConfig, bool]:
    """Add a .docstrap file path to the user's stores list.

    Returns (new_config, added) where `added` is False if the store was
    already registered (idempotent).
    """
    resolved = docstrap_path.resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"No .docstrap file at {resolved}")
    cfg = load()
    if resolved in cfg.stores:
        return cfg, False
    cfg.stores.append(resolved)
    save(cfg)
    return cfg, True


def remove_store(docstrap_path: Path) -> tuple[UserConfig, bool]:
    """Remove a .docstrap file path from the stores list.

    Returns (new_config, removed) where `removed` is False if the path
    wasn't in the list.
    """
    resolved = docstrap_path.resolve()
    cfg = load()
    if resolved not in cfg.stores:
        return cfg, False
    cfg.stores.remove(resolved)
    save(cfg)
    return cfg, True
