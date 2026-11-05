"""The "answers done" notice: one command, run once, when a person says so.

Answers save continuously; nothing
in that says a person has finished with a document's questions. The
prompt does, and pressing it runs the command named by
``answers_done_command`` in the user config, once, with the project and
the document it was pressed for. What the command does with that is its
own business — docstrap writes no notice anywhere itself.

The command is an argv list run without a shell, so nothing in a
project's slug or a document's path is ever interpreted. It gets a short
timeout and no retry: the person pressed once, and what came back —
success, or the command's own error — is reported to the page that
asked.

Unset is the ordinary case and not an error: the prompt is simply not
offered, which is why :func:`configured_command` exists apart from
:func:`run`.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Sequence

from docstrap import user_config

#: How long the command may take. A notice is a write, not a job.
TIMEOUT_SECONDS = 15


@dataclass(frozen=True, slots=True)
class Outcome:
    """What running the command came to."""

    ok: bool
    exit_status: int | None
    error: str

    def to_json(self) -> dict:
        return {"ok": self.ok, "exitStatus": self.exit_status, "error": self.error}


def configured_command() -> list[str] | None:
    """The configured argv, or None when the prompt is not to be offered."""
    return user_config.load().answers_done_command


def arguments(project: str, document: str) -> list[str]:
    """What is appended to the configured argv. The contract, in one place."""
    return ["--project", project, "--document", document]


def run(command: Sequence[str], project: str, document: str) -> Outcome:
    """Run ``command`` once for this project and document.

    ``document`` is the path the answer store records for it
    (:meth:`docstrap.projectscope.ProjectScope.display_path`), so the
    receiver can find that document's answers by the same name.
    """
    argv = [*command, *arguments(project, document)]
    try:
        completed = subprocess.run(
            argv,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return Outcome(False, None, f"{argv[0]} did not finish within {TIMEOUT_SECONDS}s")
    except OSError as exc:
        return Outcome(False, None, f"{argv[0]}: {exc.strerror or exc}")
    if completed.returncode == 0:
        return Outcome(True, 0, "")
    error = completed.stderr.strip() or f"{argv[0]} exited {completed.returncode}"
    return Outcome(False, completed.returncode, error)
