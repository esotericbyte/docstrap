"""The task tool's view: the ``docstrap-tasks`` directive.

The directive names the task file beside the page — ``spec.py`` is the
format — and renders it where the author put it::

    ```{docstrap-tasks} tasks.json
    ```

Like the data table, two things come out in one wrapper. A plain HTML
table of every task grouped by project, which is the document: it reads
on a page opened on its own and in print. And the same tasks as data,
with the vocabularies and their symbols, which the client reads to draw
the grouped, drillable list inside the viewer. Nothing is fetched for the
list; only the decisions are, because they change while the page is open.

A row holds only its own task's properties. A task in a tangle of
overlapping work links to its own section of the overlaps page (the
``overlaps`` option, ``overlaps`` beside this page by default); the
comparison of the tasks lives there and nowhere in this table.

A task's ``page`` is resolved here, at build time, by the same rule the
data table resolves a link with (``datatable.views.resolve_target``).
"""
from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.util.docutils import SphinxDirective

from docstrap.tools.datatable.views import display, resolve_target, script_json
from docstrap.tools.tasks import spec

WRAPPER_CLASS = "docstrap-tasks"
DATA_CLASS = "docstrap-tasks-data"
STATIC_CLASS = "docstrap-tasks-static"

#: The plain table's columns: the key each cell carries, which is the
#: drawn list's own key for that column (``ui/tasks.ts``) and what the
#: shared column layout (``ui/tasks.css``) is written against, and the
#: label.
_COLUMNS = (
    ("id", "Task"),
    ("title", "Title"),
    ("unit", "Unit"),
    ("filed", "Filed"),
    ("last_activity", "Last activity"),
    ("state", "State"),
    ("work", "Work"),
    ("stuck", "Stuck"),
    ("alignment", "Alignment"),
    ("done_elsewhere", "Done elsewhere"),
    ("lifecycle_stage", "Stage"),
    ("recommendation", "Latest recommendation"),
)


def _symbol(field: str, values: list[str]) -> str:
    symbols = spec.VOCABULARY[field].get("symbols", {})
    shown = display(values, symbols).strip()
    if not shown:
        return ""
    return f'<span title="{html.escape(display(values), quote=True)}">{html.escape(shown)}</span>'


def _project_order(project: str) -> tuple[int, str]:
    # `none` is the contract's word for a task that belongs to no project;
    # it goes last, the way an empty value does everywhere else.
    return (1 if project in ("", "none") else 0, project.casefold())


def _wrap(text: str) -> str:
    return f'<span class="wrap">{html.escape(text)}</span>' if text else ""


def _cells(task: spec.Task, link: str | None, tangle: str | None) -> list[str]:
    ident = html.escape(task.id)
    if link is not None:
        ident = f'<a class="reference" href="{html.escape(link, quote=True)}">{ident}</a>'
    # Cut short to one line by the stylesheet, so the whole id is on hover.
    ident = f'<span class="task-id" title="{html.escape(task.id, quote=True)}">{ident}</span>'
    if tangle is not None:
        ident += (
            f'<a class="reference tangle" href="{html.escape(tangle, quote=True)}" '
            f'title="{html.escape(task.tangle, quote=True)}">overlaps</a>'
        )
    stage = ""
    if task.lifecycle_stage:
        stage = (
            f'<span title="{html.escape(task.lifecycle_evidence, quote=True)}">'
            f"{html.escape(task.lifecycle_stage)}</span>"
        )
    latest = task.latest_recommendation
    recommendation = ""
    if latest is not None:
        meta = " · ".join(p for p in (latest.date, latest.by) if p)
        recommendation = (
            f'<span title="{html.escape(latest.note, quote=True)}">'
            f'<span class="action">{html.escape(latest.action)}</span>'
            f'<span class="meta">{html.escape(meta)}</span></span>'
        )
    return [
        ident,
        _wrap(task.title),
        _wrap(task.unit),
        html.escape(task.filed),
        html.escape(task.last_activity),
        html.escape(task.state),
        _symbol("work", [task.work] if task.work else []),
        _symbol("stuck", [task.stuck] if task.stuck else []),
        _symbol("alignment", [task.alignment] if task.alignment else []),
        _symbol("done_elsewhere", [task.done_elsewhere] if task.done_elsewhere else []),
        stage,
        recommendation,
    ]


def render(
    tasks: spec.TaskFile, links: dict[str, str], tangles: dict[str, str] | None = None
) -> str:
    """The wrapper, the data, and the plain table grouped by project, as HTML.

    ``links`` maps a task id to the URL its page resolved to; a task
    missing from it is shown unlinked. ``tangles`` maps a task id to the
    URL of its own section on the overlaps page — the task's membership
    of a tangle, and nothing about the other tasks in it.
    """
    tangles = tangles or {}
    payload: dict[str, Any] = {
        "generated": tasks.generated,
        "vocabulary": spec.VOCABULARY,
        "tasks": [
            {
                **task.to_payload(),
                "link": links.get(task.id),
                "tangle_link": tangles.get(task.id),
            }
            for task in tasks.tasks
        ],
    }

    groups: dict[str, list[spec.Task]] = {}
    for task in tasks.tasks:
        groups.setdefault(task.project, []).append(task)

    head = "".join(
        f'<th class="head" data-key="{key}">{html.escape(label)}</th>' for key, label in _COLUMNS
    )
    body: list[str] = []
    for project in sorted(groups, key=_project_order):
        held = groups[project]
        body.append(
            f'<tr class="group"><th colspan="{len(_COLUMNS)}"><span class="heading">'
            f"{html.escape(project or 'none')} ({len(held)})</span></th></tr>"
        )
        for task in held:
            cells = "".join(
                f'<td data-key="{key}">{c}</td>'
                for (key, _), c in zip(
                    _COLUMNS, _cells(task, links.get(task.id), tangles.get(task.id))
                )
            )
            body.append(f"<tr>{cells}</tr>")

    return (
        f'<div class="{WRAPPER_CLASS}">'
        f'<script type="application/json" class="{DATA_CLASS}">'
        f"{script_json(payload)}</script>"
        f'<div class="{STATIC_CLASS} table-wrapper">'
        f'<table class="docutils align-default">'
        f"<thead><tr>{head}</tr></thead>"
        f"<tbody>{''.join(body)}</tbody>"
        f"</table></div></div>"
    )


class DocstrapTasksDirective(SphinxDirective):
    """Render a task file as the list the task tool groups and drills into."""

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False
    #: ``overlaps``: the page whose sections a task's ``tangle`` names,
    #: relative to this one; ``overlaps`` beside it when not given.
    option_spec: dict[str, Any] = {"overlaps": directives.unchanged_required}

    def run(self) -> list[nodes.Node]:
        argument = self.arguments[0]
        relative, absolute = self.env.relfn2path(argument)
        # A change to the task file rebuilds the page that shows it.
        self.env.note_dependency(relative)
        try:
            tasks = spec.load(Path(absolute))
        except spec.TaskFileError as exc:
            raise self.error(f"docstrap-tasks {argument}: {exc}") from exc

        links: dict[str, str] = {}
        for task in tasks.tasks:
            if task.page:
                url = resolve_target(self, task.page, "docstrap-tasks")
                if url is not None:
                    links[task.id] = url

        tangles: dict[str, str] = {}
        if any(task.tangle_section for task in tasks.tasks):
            overlaps = resolve_target(
                self, self.options.get("overlaps", "overlaps"), "docstrap-tasks"
            )
            if overlaps is not None:
                for task in tasks.tasks:
                    if task.tangle_section:
                        tangles[task.id] = f"{overlaps}#{task.tangle_section}"
        return [nodes.raw("", render(tasks, links, tangles), format="html")]
