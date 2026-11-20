# The task tool

The `docstrap-tasks` directive puts firstmate's open tasks on a page from the `tasks.json` beside it.
Inside the viewer the reader groups them by project or by status, drills into one part of the list
and links to that part, sorts and filters, and records one decision per task. The decision lands in
the project's answer store, where firstmate reads it.

The tool is `docstrap.tools.tasks`. Unlike the data table it knows what its rows are: tasks, in the
shape firstmate's contract gives them.

## 1 The directive

````markdown
```{docstrap-tasks} tasks.json
```
````

The one argument is the task file's path, relative to the page. There are no options and no body.
The build reads the file when the page is built and again whenever the file changes.

## 2 The task file

`tasks.json` is written by firstmate and only read here. The contract is firstmate's, in
`TASKS-JSON-CONTRACT.md` in its task-census data, and `tools/tasks/spec.py` is the reader. The shape:

```json
{
  "generated": "2026-10-13T12:00:00Z",
  "tasks": [
    {"id": "fm-12", "title": "...", "project": "dkp", "unit": "apps/players",
     "state": "held", "hold_reason": "...", "blocked_by": [],
     "filed": "2026-10-01", "last_activity": "2026-10-12",
     "work": "code", "stuck": "captain", "alignment": "aligned", "plan": "docs/roadmap.md",
     "done_elsewhere": "likely", "done_evidence": "...",
     "lifecycle_stage": "branch", "lifecycle_evidence": "...", "tangle": "tangle-dev-server-ci",
     "page": "tasks/fm-12",
     "latest_recommendation": {"action": "close-duplicate", "note": "...",
                               "date": "2026-10-13", "by": "firstmate"},
     "recommendations": [{"action": "...", "note": "...", "date": "...", "by": "..."}]}
  ]
}
```

**Unknown keys are ignored**, at the top and in every task, because the contract says so. A value
outside a field's vocabulary is kept and shown as written. A field that is absent reads as empty.
What fails the build, naming the JSON path, is a file the tool cannot show at all: not an object, no
`tasks` list, a task with no `id`, the same id twice, an id holding whitespace, `:` or `#` (it could
not key a decision, §5), a field of the wrong type, or a date that is not `YYYY-MM-DD`.

A task's `page` is resolved by the build exactly as a data table's link target is
(`datatable.md` §2.4): `tasks/fm-12` becomes that document's built URL, and a page the build does not
have is a warning and an unlinked id.

A row holds only properties of its own task; no other task's id or field appears in it. The
contract's `duplicate_of` names other tasks, so the tool does not read it. How tasks duplicate or
overlap is told on the overlaps page, one section per tangle, and a task's `tangle` is the anchor of
its own section there. The build resolves the page — the directive's `overlaps` option, `overlaps`
beside the task page when not given — and a task with a `tangle` gets a small link to
`<overlaps>#<tangle>` beside its id. `tangle-not-overlapping` marks a task the census flagged that
overlaps nothing, and gets no link. `lifecycle_stage` (`filed`, `specified`, `branch`, `landed`,
`deployed`) is how far the task's own scope has got, with `lifecycle_evidence` on hover and in the
opened row.

The symbols are the tool's, from firstmate's census schema, defined once in `spec.VOCABULARY` and
carried to the page so the plain table and the drawn list cannot disagree:

1. work — 🔨 code, 📝 docs, 🔨📝 docs+code, 🔧 data-config, 🔍 investigation, ❓ decision.
2. stuck — ▶️ ready, ⏳ captain, 🔒 blocked, 🧭 needs-plan, 🌐 external, 💤 stalled.
3. alignment — 🟢 aligned, 🟡 drifted, 🔴 obsolete, ⚪ no-plan.
4. done elsewhere — ✅ yes, ♻️ likely, blank for no.

## 3 What the page carries

As with the data table, the build renders the tasks twice inside one wrapper: a plain HTML table
grouped by project, which is what a page opened on its own and print show, and the same tasks as
data in a `<script type="application/json">`. Inside the viewer the tool sets the plain table aside
and draws the list; hiding the tool from the launcher puts the plain table back. The controls carry
`.docstrap-chrome`.

A page opened on its own runs no tool (`tools-and-instruments.md` §3.2), so there the list is the
plain table. What the directive renders is pickled into each page's doctree, so a change to it bumps
the extension's `env_version` (`tools/tasks/__init__.py`); without that, an existing build would go
on serving the old markup until the page's source changed.

The list itself is never fetched. The decisions are, from the tool's own route, because they change
while the page is open.

## 4 Reading the list

### 4.1 Grouping

The list is grouped by **project** by default, projects alphabetically with `none` last, and under
each project by **unit**, the project-wide tasks (no unit) after the named units. Grouping by
**status** groups by `state` or by `stuck`, a toggle between the two, in the vocabulary's order. Every
group shows how many tasks are in it under the filters as they stand, and collapses. When the list is
grouped by status and not drilled into a project, a Project column is shown. A Unit column is shown
only when the list is grouped by status: grouped by project, the units are the headings the rows sit
under.

The grouping, collapsing and counting are TanStack Table's (§4.4), grouping on the project and unit
columns or on the state or stuck column. TanStack places groups in the order they first appear, so
the tool hands it the tasks already in the order above (`tasks.ts` `inGroupOrder`), and a sort orders
the tasks inside each group while the groups stay where they are. Under project grouping most units
hold one task, so a sort there changes little; grouped by status it orders each group's tasks.

### 4.2 Drilling down

Clicking a group's name narrows the list to that group: a project, a unit inside a project, a state
or a stuck reason. Clicking a project, unit, state or stuck value in a row does the same. Each step
adds to the drill-down, so a project and then a state is that project's tasks in that state. A
breadcrumb above the list goes back to any step, or to the whole list.

### 4.3 The address

The grouping and the drill-down are kept in the viewer's address, beside `?doc-url=`, so a
drill-down can be linked:

```text
viewer.html?doc-url=…/triage/open.html&tasks-group=stuck&tasks-in=project:dkp&tasks-in=stuck:captain
```

`tasks-group` is `state` or `stuck` and is absent for the default, project. `tasks-in` repeats, one
`<dimension>:<value>` per step, outermost first; the dimensions are `project`, `unit`, `state` and
`stuck`, and a unit step counts only after a project step. A view at rest writes nothing. The address
is replaced, not pushed, so moving about the list adds no history. Search, filters and sort are not
in the address.

### 4.4 Sorting and filtering

The table is TanStack Table's (`@tanstack/svelte-table`), the same base as the data table: its row
models sort, filter, search, count each facet, group and collapse, and hold each column to its width.
`tools/datatable/ui/grid.ts` turns a docstrap column declaration into a TanStack column — how a type
compares, empty cells last in both directions, a list cell counted under each of its values — and the
tasks are datatable rows to it. TanStack is headless: the tool still draws its own markup with its own
scoped styles (`tools-and-instruments.md` §1.1). Every column sorts; a header cycles ascending,
descending, off. The search box reads id, title, unit and the done-elsewhere and lifecycle evidence, shown or not,
and a row passes when every term is somewhere in it. Multi-selects filter work, stuck, alignment, done elsewhere,
lifecycle stage and the latest recommendation's action, each option counted under the other
filters. Filed and last activity each take a date range. The columns are id (linking to the task's
page), title, unit, filed, last activity, state, work, stuck, alignment, done elsewhere, lifecycle stage and the
latest recommendation's action, date and author, with its note on hover.

### 4.5 Layout

The theme's text width is kept; the list does not widen the page. The table sits in a box of its own
with a maximum height (85% of the window), scrolls inside it both ways, and holds its header row and
its task column in place while it does. An opened task's detail is held to the box's width and left
edge, so it reads without scrolling sideways.

Every column has a fixed width, `tasks.ts` `SIZES`, which TanStack holds the drawn list to: the task
column is 150 px, the id never wraps and is cut short with the whole id on hover; title (300 px) and
unit (190 px) wrap inside their width; dates, state and the symbol columns take what they need. The
plain table is given the same widths by `ui/tasks.css`, which is the one stylesheet both tables are
laid out by, keyed on the `data-key` every cell of both carries; a test holds its widths to `SIZES`.

Opening a row shows what the row has no room for: the hold reason, what blocks it, the plan, the
evidence, the lifecycle stage with its evidence, and every recommendation with its note.

## 5 A decision on one task

An opened row offers one decision on that task: one of `close-done`, `close-duplicate`,
`close-obsolete`, `reshape`, `dispatch`, `hold` or `ask` — the recommendation actions — or `keep`,
and a note. Save stores it. There is no bulk action anywhere: a decision is always made on the one
row it sits under. A decided row is marked.

### 5.1 How a decision is keyed

A decision is an answer in the project's answer store, `<project-promdance>/answers.md`
(`spec.md` §8.1), written through `docstrap.answers` like every other answer.
`tools/tasks/decisions.py` is the one place the spelling below is written down.

The **key** is `<doc-id>:task/<task-id>`. `<doc-id>` is the metadata store's id for the page that
holds the `docstrap-tasks` directive — not the task's own page — and `<task-id>` is the id exactly as
`tasks.json` spells it. The row's `label` is `task/<task-id>` and its `document` is that page's path
as the project records it, for example `docs/triage/open.md`. The `task/` prefix keeps a decision
apart from a `Q<n>` answered on the same page.

The **prose** is the action alone on its first line, then, when there is a note, one blank line and
the note:

```text
action: close-duplicate

Same work as dkp-hosted-apps-h12; keep that one.
```

Every decision is written **submitted** (`submitted: true`, with `submitted_at`), because a person
pressed Save. Deciding again on the same task supersedes: the row and its section are replaced, and
the earlier decision moves to `answers-history.md`, which is the store's ordinary behaviour
(§8.1.4). So firstmate finds the current decision on a task by reading the rows of `answers.md` whose
`label` is `task/<task-id>` and whose `document` is the page, and the action from the first line of
that row's section.

Nothing is delivered beside the page when a decision is saved. The answer addendum (§8.3) records what
a document's questions decided, and a task decision is not one.

### 5.2 Saying the decisions are done

When `answers_done_command` is configured, the toolbar carries **Answers done**. It is the existing
prompt (`spec.md` §8.10): it posts to the Q&A panels' document-scope route for this page, and the
server runs the command once with `--project <slug> --document <the page's path>` — the same
`document` every decision on the page is stored under. Unset, it is not shown.

### 5.3 The route

The tool owns the `decisions` collection under the document base:
`GET /api/promdance/{project}/{doc_slug}/decisions` returns the decisions recorded on the page by
task id, the actions offered, and the "answers done" route or null; `POST` with
`{"task_id", "action", "note"}` records one. Reading registers nothing in the metadata store; the
first decision on a page does. An action outside the list, or a task id that could not be keyed, is a
400.

## 6 Where the rules live

The task file is read by `tools/tasks/spec.py`, the directive in `tools/tasks/views.py` renders it,
and `tools/tasks/decisions.py` and `tools/tasks/routes.py` are the decision and its route. The
columns and their widths, the group order, drilling down and the address are
`tools/tasks/ui/tasks.ts`, a module with no DOM in it; the TanStack column definitions it builds on
are `tools/datatable/ui/grid.ts`, and the filter bar both tools draw is
`tools/datatable/ui/FilterBar.svelte`. `tests/tasks/tasks.test.ts` tests it under Node against a real
TanStack table built the way the page builds one; `npm test` runs it, and so does `pytest` through
`tests/test_tasks.py`, which also builds the directive through a real nested `sphinx-build` and drives
the route through the real app.
