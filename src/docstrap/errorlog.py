"""The error log: where a build puts what is worth knowing but is not output.

A condition that does not stop a build is not an error, and it does not
belong in the build's output either — not on a page, and not in the
result the store's landing page and the CLI print beside every project.
Put there, it crowds out what the reader came for. It is written here
instead, one timestamped line per warning, in the user state directory
(:func:`docstrap.paths.state_dir`).

Writing a warning never fails a build: a log that cannot be written is
skipped, because the output matters more than the note about it.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from docstrap import paths

_FILENAME = "errors.log"


def path() -> Path:
    """Where the error log is, whether or not anything has been written."""
    return paths.state_dir() / _FILENAME


def warn(message: str) -> None:
    """Append one ``WARNING`` line to the error log. Never raises."""
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"{stamp} WARNING {' '.join(message.split())}\n"
    target = path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as log:
            log.write(line)
    except OSError:
        pass
