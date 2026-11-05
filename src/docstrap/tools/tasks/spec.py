"""The task file: what a ``docstrap-tasks`` directive reads.

``tasks.json`` beside the page, written by firstmate and only read here.
The contract is firstmate's (``TASKS-JSON-CONTRACT.md`` in its task-census
data). In short::

    {
      "generated": "2026-10-13T12:00:00Z",
      "tasks": [
        {"id": "fm-1", "title": "...", "project": "alpha", "unit": "apps/players",
         "state": "queued", "filed": "2026-10-01", "last_activity": "2026-10-12",
         "work": "code", "stuck": "ready", "alignment": "aligned",
         "done_elsewhere": "no", "lifecycle_stage": "specified",
         "lifecycle_evidence": "...", "tangle": "tangle-dev-server-ci",
         "page": "tasks/fm-1",
         "latest_recommendation": {"action": "dispatch", "note": "...",
                                   "date": "2026-10-13", "by": "firstmate"},
         "recommendations": [...]}
      ]
    }

**Unknown keys are ignored**, at the top and in every task, because the
contract says so: the writer may add a field before this reader knows of
it. A value outside a field's vocabulary is kept and shown as written,
for the same reason. ``duplicate_of`` is one of those: it names other
tasks, and a row holds only properties of its own task. How tasks overlap
is told on the overlaps page, which ``tangle`` names a section of. What is refused, naming where, is a file this tool
cannot show at all — not an object, a task with no id, an id twice, an
id that could not key a decision, a field of the wrong type, a date that
is not a day.

The vocabularies and the symbols are here and nowhere else. The page
carries them to the client, so the plain table and the tool draw the same
symbol for the same value from one definition.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: Each enumerated field: its values in the order they sort, group and
#: are offered in, and the symbol shown for each when it has one.
#: Symbols are `SCHEMA.md`'s, in firstmate's task-census data.
VOCABULARY: dict[str, dict[str, Any]] = {
    "state": {"values": ["queued", "held", "blocked", "in_flight"]},
    "work": {
        "values": ["code", "docs", "docs+code", "data-config", "investigation", "decision"],
        "symbols": {
            "code": "🔨",
            "docs": "📝",
            "docs+code": "🔨📝",
            "data-config": "🔧",
            "investigation": "🔍",
            "decision": "❓",
        },
    },
    "stuck": {
        "values": ["ready", "captain", "blocked", "needs-plan", "external", "stalled"],
        "symbols": {
            "ready": "▶️",
            "captain": "⏳",
            "blocked": "🔒",
            "needs-plan": "🧭",
            "external": "🌐",
            "stalled": "💤",
        },
    },
    "alignment": {
        "values": ["aligned", "drifted", "obsolete", "no-plan"],
        "symbols": {"aligned": "🟢", "drifted": "🟡", "obsolete": "🔴", "no-plan": "⚪"},
    },
    "done_elsewhere": {
        "values": ["yes", "likely", "no"],
        "symbols": {"yes": "✅", "likely": "♻️", "no": ""},
    },
    # The furthest point any part of the task's own scope has reached.
    "lifecycle_stage": {"values": ["filed", "specified", "branch", "landed", "deployed"]},
    "action": {
        "values": [
            "close-done",
            "close-duplicate",
            "close-obsolete",
            "reshape",
            "dispatch",
            "hold",
            "ask",
        ]
    },
}

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

#: A task id keys a decision in the answer store, whose key halves are
#: split on `:` and whose section headings end at whitespace.
_ID = re.compile(r"^[^\s:#]+$")

_TEXT_FIELDS = (
    "title",
    "project",
    "unit",
    "state",
    "hold_reason",
    "work",
    "stuck",
    "alignment",
    "plan",
    "done_elsewhere",
    "done_evidence",
    "lifecycle_stage",
    "lifecycle_evidence",
    "tangle",
    "page",
)
_DATE_FIELDS = ("filed", "last_activity")
_LIST_FIELDS = ("blocked_by",)

#: The `tangle` a task carries when the census flagged it and it overlaps
#: nothing: no section to link to.
NOT_OVERLAPPING = "tangle-not-overlapping"


class TaskFileError(ValueError):
    """The task file is not one this tool can show."""


@dataclass(frozen=True, slots=True)
class Recommendation:
    action: str
    note: str
    date: str
    by: str

    def to_payload(self) -> dict[str, str]:
        return {"action": self.action, "note": self.note, "date": self.date, "by": self.by}


@dataclass(frozen=True, slots=True)
class Task:
    """One task, every contract field present; absent text reads as empty."""

    id: str
    title: str
    project: str
    unit: str
    state: str
    hold_reason: str
    blocked_by: tuple[str, ...]
    filed: str
    last_activity: str
    work: str
    stuck: str
    alignment: str
    plan: str
    done_elsewhere: str
    done_evidence: str
    lifecycle_stage: str
    lifecycle_evidence: str
    #: The anchor of the task's own section on the overlaps page, or empty.
    tangle: str
    page: str
    latest_recommendation: Recommendation | None
    recommendations: tuple[Recommendation, ...]

    @property
    def tangle_section(self) -> str:
        """The overlaps page section the task belongs to, or empty: none."""
        return "" if self.tangle == NOT_OVERLAPPING else self.tangle

    def to_payload(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "project": self.project,
            "unit": self.unit,
            "state": self.state,
            "hold_reason": self.hold_reason,
            "blocked_by": list(self.blocked_by),
            "filed": self.filed,
            "last_activity": self.last_activity,
            "work": self.work,
            "stuck": self.stuck,
            "alignment": self.alignment,
            "plan": self.plan,
            "done_elsewhere": self.done_elsewhere,
            "done_evidence": self.done_evidence,
            "lifecycle_stage": self.lifecycle_stage,
            "lifecycle_evidence": self.lifecycle_evidence,
            "tangle": self.tangle,
            "latest_recommendation": (
                self.latest_recommendation.to_payload()
                if self.latest_recommendation
                else None
            ),
            "recommendations": [r.to_payload() for r in self.recommendations],
        }


@dataclass(frozen=True, slots=True)
class TaskFile:
    generated: str
    #: In the file's order.
    tasks: tuple[Task, ...]


def load(path: Path) -> TaskFile:
    """Read and check the task file at ``path``."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise TaskFileError(f"cannot read {path}: {exc.strerror or exc}") from exc
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise TaskFileError(f"{path} is not JSON: {exc}") from exc
    return parse(data)


def parse(data: Any) -> TaskFile:
    """Check a decoded task file and return it with absent fields empty."""
    if not isinstance(data, dict):
        raise TaskFileError("the task file must be a JSON object")
    generated = data.get("generated", "")
    if not isinstance(generated, str):
        raise TaskFileError("generated: must be a string")
    raw_tasks = data.get("tasks")
    if not isinstance(raw_tasks, list):
        raise TaskFileError("tasks: must be a list")
    tasks = tuple(_task(raw, f"tasks[{i}]") for i, raw in enumerate(raw_tasks))
    seen: set[str] = set()
    for i, task in enumerate(tasks):
        if task.id in seen:
            raise TaskFileError(f"tasks[{i}].id: {task.id!r} appears twice")
        seen.add(task.id)
    return TaskFile(generated=generated, tasks=tasks)


def _text(raw: dict[str, Any], name: str, where: str) -> str:
    value = raw.get(name)
    if value is None:
        return ""
    if not isinstance(value, str):
        raise TaskFileError(f"{where}.{name}: must be a string")
    return value


def _list(raw: dict[str, Any], name: str, where: str) -> tuple[str, ...]:
    value = raw.get(name)
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise TaskFileError(f"{where}.{name}: must be a list of task ids")
    return tuple(value)


def _recommendation(raw: Any, where: str) -> Recommendation:
    if not isinstance(raw, dict):
        raise TaskFileError(f"{where}: must be an object")
    fields = {name: _text(raw, name, where) for name in ("action", "note", "date", "by")}
    if fields["date"] and not _DATE.match(fields["date"]):
        raise TaskFileError(f"{where}.date: {fields['date']!r} is not a YYYY-MM-DD date")
    return Recommendation(**fields)


def _task(raw: Any, where: str) -> Task:
    if not isinstance(raw, dict):
        raise TaskFileError(f"{where}: must be an object")
    task_id = raw.get("id")
    if not isinstance(task_id, str) or not task_id:
        raise TaskFileError(f"{where}.id: must be a non-empty string")
    if not _ID.match(task_id):
        raise TaskFileError(
            f"{where}.id: {task_id!r} holds whitespace, ':' or '#', so it cannot "
            f"key a decision"
        )
    text = {name: _text(raw, name, where) for name in _TEXT_FIELDS}
    dates = {name: _text(raw, name, where) for name in _DATE_FIELDS}
    for name, value in dates.items():
        if value and not _DATE.match(value):
            raise TaskFileError(f"{where}.{name}: {value!r} is not a YYYY-MM-DD date")
    lists = {name: _list(raw, name, where) for name in _LIST_FIELDS}

    latest = raw.get("latest_recommendation")
    history = raw.get("recommendations")
    if history is not None and not isinstance(history, list):
        raise TaskFileError(f"{where}.recommendations: must be a list")
    return Task(
        id=task_id,
        **text,
        **dates,
        **lists,
        latest_recommendation=(
            None
            if latest is None
            else _recommendation(latest, f"{where}.latest_recommendation")
        ),
        recommendations=tuple(
            _recommendation(r, f"{where}.recommendations[{i}]")
            for i, r in enumerate(history or [])
        ),
    )
