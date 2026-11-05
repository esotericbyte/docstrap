"""A decision on one task, as it is spelled in the answer store.

The answer store (:mod:`docstrap.answers`) is the
only thing that reads or writes the answer file; this module decides
nothing about the format. It says which key a task decision hangs on and
what the answer's prose holds, in one place, so the route that writes a
decision and the route that reads it back cannot spell it differently —
and so firstmate, reading the file, has one rule to follow.

**The key** is the answer store's own, ``<doc-id>:<label>``:

``<doc-id>``
    the metadata store's id for the page that mounts the tool — the page
    holding the ``docstrap-tasks`` directive, not the task's own page.
    The answer row's ``document`` field is that page's path as the
    project records it, which is also what the "answers done" command is
    given as ``--document``.

``<label>``
    ``task/`` followed by the task id, exactly as ``tasks.json`` spells
    it. The prefix keeps a task decision apart from a ``Q<n>`` question
    answered in the same document.

So deciding on task ``widget-rename-h141`` from
``docs/triage/index.md`` is stored under
``01J9F4V4T4XW9A0RCM6QK2S8YZ:task/widget-rename-h141``, with
``label: task/widget-rename-h141`` and
``document: docs/triage/index.md`` in its index row.

**The prose** is the action on its own first line, and the note, if any,
after one blank line::

    action: close-duplicate

    Same work as widget-h12; keep that one.

Every decision is written submitted: the person pressed Save. Deciding
again supersedes, and the earlier decision moves to the history file,
which is the store's ordinary behaviour.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from docstrap import answers as answer_store
from docstrap.tools.tasks.spec import VOCABULARY

#: What a decision's label starts with. The rest is the task id.
LABEL_PREFIX = "task/"

#: The actions a decision may take: every recommendation action, plus
#: keep — leave the task as it is.
ACTIONS: tuple[str, ...] = (*VOCABULARY["action"]["values"], "keep")

_ACTION_LINE = re.compile(r"^action: (?P<action>\S+)$")


class DecisionError(ValueError):
    """A decision this tool will not record."""


@dataclass(frozen=True, slots=True)
class Decision:
    task_id: str
    #: None when the stored prose does not open with an action line —
    #: someone edited the answer file by hand.
    action: Optional[str]
    note: str
    decided_at: str

    def to_json(self) -> dict[str, object]:
        return {"action": self.action, "note": self.note, "decidedAt": self.decided_at}


def label_for(task_id: str) -> str:
    """The answer label a decision on ``task_id`` is stored under."""
    task_id = task_id.strip()
    if not task_id or re.search(r"[\s:#]", task_id):
        raise DecisionError(f"{task_id!r} is not a task id a decision can be keyed on")
    return f"{LABEL_PREFIX}{task_id}"


def task_id_of(label: str) -> Optional[str]:
    """The task a label decides on, or None for a label that is not a decision."""
    if label.startswith(LABEL_PREFIX) and len(label) > len(LABEL_PREFIX):
        return label[len(LABEL_PREFIX) :]
    return None


def text_for(action: str, note: str) -> str:
    """The answer prose for a decision."""
    if action not in ACTIONS:
        raise DecisionError(f"{action!r} is not one of {', '.join(ACTIONS)}")
    note = note.strip()
    return f"action: {action}" + (f"\n\n{note}" if note else "")


def parse_text(text: str) -> tuple[Optional[str], str]:
    """``(action, note)`` from answer prose; action None when it has no action line."""
    first, _, rest = text.strip().partition("\n")
    match = _ACTION_LINE.match(first.strip())
    if match is None:
        return None, text.strip()
    return match.group("action"), rest.strip()


def record(
    project: str, *, doc_id: str, document: str, task_id: str, action: str, note: str
) -> Decision:
    """Store one decision on one task, superseding any earlier one."""
    stored = answer_store.put(
        project,
        doc_id=doc_id,
        label=label_for(task_id),
        document=document,
        text=text_for(action, note),
        submitted=True,
    )
    return _decision(task_id.strip(), stored)


def on_page(project: str, doc_id: str) -> dict[str, Decision]:
    """Every decision recorded from one page, by task id."""
    found: dict[str, Decision] = {}
    for answer in answer_store.submitted(project):
        if answer.doc_id != doc_id:
            continue
        task_id = task_id_of(answer.label)
        if task_id is not None:
            found[task_id] = _decision(task_id, answer)
    return found


def _decision(task_id: str, answer: answer_store.Answer) -> Decision:
    action, note = parse_text(answer.text)
    return Decision(
        task_id=task_id,
        action=action,
        note=note,
        decided_at=answer.submitted_at or answer.answered_at,
    )
