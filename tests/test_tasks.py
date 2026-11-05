"""The task tool: the task file, the directive, the decision key, the route.

Four halves, the way the data table and the answer loop are proved.

The task file is firstmate's contract, read and never written here, so
`spec.parse` is tested as plain data: unknown keys are ignored as the
contract requires, and what is refused names where.

The directive is proved by a real `sphinx-build` over a nested source
tree — the page one directory below the root, its task pages one further
down — and the assertions are on the HTML: the plain table grouped by
project, and the data the client takes over.

The decision is an answer in the project's answer store, and the key it
hangs on is what firstmate reads, so it is asserted literally:
`<doc-id of the page>:task/<task id>`. The route is reached through the
real `make_app`, as `test_answers_done.py` reaches the qapanels routes.

The columns, grouping, drill-down and the address are `ui/tasks.ts`, tested
under Node against a real TanStack table by `tests/tasks/tasks.test.ts`;
the last test here runs that suite.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from html import unescape
from pathlib import Path

import pytest
from fastapi import HTTPException
from starlette.routing import Match

from docstrap import answers as answer_store
from docstrap import metadata as meta
from docstrap import user_config
from docstrap.config import load
from docstrap.scan import ScannedProject, scan
from docstrap.server import make_app
from docstrap.tools import registry
from docstrap.tools.tasks import decisions, spec
from docstrap.tools.tasks.routes import DecisionSubmission
from docstrap.tools.tasks.views import DATA_CLASS, STATIC_CLASS, WRAPPER_CLASS

PACKAGE = Path(__file__).resolve().parents[1]


def _task(task_id: str, **fields) -> dict:
    return {"id": task_id, **fields}


# --- the task file -----------------------------------------------------------


def test_absent_fields_read_as_empty():
    parsed = spec.parse({"tasks": [_task("fm-1")]})
    assert parsed.generated == ""
    (task,) = parsed.tasks
    assert task.title == "" and task.unit == "" and task.filed == ""
    assert task.blocked_by == () and task.lifecycle_stage == "" and task.tangle == ""
    assert task.latest_recommendation is None and task.recommendations == ()


def test_unknown_keys_are_ignored_as_the_contract_requires():
    parsed = spec.parse(
        {
            "generated": "2026-10-13T12:00:00Z",
            "schema": 2,
            "tasks": [
                _task(
                    "fm-1",
                    colour="red",
                    latest_recommendation={"action": "hold", "date": "2026-10-13", "why": "x"},
                )
            ],
        }
    )
    assert parsed.tasks[0].latest_recommendation == spec.Recommendation(
        action="hold", note="", date="2026-10-13", by=""
    )
    assert "colour" not in parsed.tasks[0].to_payload()


def test_a_value_outside_the_vocabulary_is_kept():
    (task,) = spec.parse({"tasks": [_task("fm-1", state="parked", work="art")]}).tasks
    assert (task.state, task.work) == ("parked", "art")


def test_a_task_carries_no_other_tasks_duplicate_of_is_not_read():
    """A row holds only its own task's properties; how tasks overlap is
    told on the overlaps page, which `tangle` names a section of."""
    (task,) = spec.parse(
        {"tasks": [_task("fm-1", done_elsewhere="likely", duplicate_of=["fm-2"])]}
    ).tasks
    assert "duplicate_of" not in task.to_payload()
    assert "fm-2" not in json.dumps(task.to_payload())
    assert "duplicates" not in spec.VOCABULARY["done_elsewhere"]["values"]


def test_a_task_flagged_as_overlapping_nothing_has_no_tangle_section():
    tasks = spec.parse(
        {
            "tasks": [
                _task("a", tangle="tangle-dev-server-ci"),
                _task("b", tangle=spec.NOT_OVERLAPPING),
                _task("c"),
            ]
        }
    ).tasks
    assert [t.tangle_section for t in tasks] == ["tangle-dev-server-ci", "", ""]


@pytest.mark.parametrize(
    ("data", "names"),
    [
        ([], "JSON object"),
        ({}, "tasks"),
        ({"tasks": {}}, "tasks"),
        ({"generated": 3, "tasks": []}, "generated"),
        ({"tasks": ["fm-1"]}, "tasks[0]"),
        ({"tasks": [{}]}, "tasks[0].id"),
        ({"tasks": [_task("a b")]}, "tasks[0].id"),
        ({"tasks": [_task("a:b")]}, "tasks[0].id"),
        ({"tasks": [_task("a"), _task("a")]}, "tasks[1].id"),
        ({"tasks": [_task("a", title=3)]}, "tasks[0].title"),
        ({"tasks": [_task("a", filed="10/01/2026")]}, "tasks[0].filed"),
        ({"tasks": [_task("a", blocked_by="b")]}, "tasks[0].blocked_by"),
        ({"tasks": [_task("a", lifecycle_stage=2)]}, "tasks[0].lifecycle_stage"),
        ({"tasks": [_task("a", latest_recommendation="hold")]}, "latest_recommendation"),
        (
            {"tasks": [_task("a", recommendations=[{"date": "soon"}])]},
            "tasks[0].recommendations[0].date",
        ),
    ],
)
def test_a_task_file_this_tool_cannot_show_is_refused_naming_where(data, names):
    with pytest.raises(spec.TaskFileError, match=re.escape(names)):
        spec.parse(data)


def test_load_names_a_file_that_is_not_json(tmp_path: Path):
    path = tmp_path / "tasks.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(spec.TaskFileError, match="is not JSON"):
        spec.load(path)
    with pytest.raises(spec.TaskFileError, match="cannot read"):
        spec.load(tmp_path / "absent.json")


# --- the directive, through a real build -------------------------------------

CONF = """\
project = "Sample Project"
extensions = {extensions!r}
master_doc = "index"
html_theme = "alabaster"
"""

INDEX = """\
# Sample

```{toctree}
triage/index
triage/tasks/alpha-1
triage/tasks/fm-1
```
"""

PAGE = """\
# Triage

Before the list.

```{docstrap-tasks} tasks.json
```

After the list.
"""

TASKS = {
    "generated": "2026-10-13T12:00:00Z",
    "tasks": [
        _task(
            "fm-1",
            title="Tidy <the> & launcher",
            project="firstmate",
            unit="bin",
            state="held",
            filed="2026-09-02",
            last_activity="2026-10-12",
            work="code",
            stuck="captain",
            alignment="drifted",
            done_elsewhere="likely",
            duplicate_of=["alpha-1"],
            lifecycle_stage="branch",
            lifecycle_evidence="Worktree <fm/x> exists",
            tangle="tangle-launcher",
            page="tasks/fm-1",
            latest_recommendation={
                "action": "close-duplicate",
                "note": "Same as alpha-1",
                "date": "2026-10-13",
                "by": "firstmate",
            },
        ),
        _task(
            "none-1",
            title="Loose",
            project="none",
            tangle=spec.NOT_OVERLAPPING,
            page="tasks/none-1",
        ),
        _task("alpha-1", title="Rename", project="alpha", unit="", page="tasks/alpha-1"),
    ],
}


def _build(source: Path) -> tuple[subprocess.CompletedProcess, Path]:
    out = source.parent / "out"
    result = subprocess.run(
        [sys.executable, "-m", "sphinx", "-q", "-b", "html", str(source), str(out)],
        capture_output=True,
        text=True,
    )
    return result, out


def _source(root: Path, tasks: object) -> Path:
    src = root / "src"
    (src / "triage" / "tasks").mkdir(parents=True)
    extensions = ["myst_parser", *registry.sphinx_extensions()]
    (src / "conf.py").write_text(CONF.format(extensions=extensions), encoding="utf-8")
    (src / "index.md").write_text(INDEX, encoding="utf-8")
    (src / "triage" / "index.md").write_text(PAGE, encoding="utf-8")
    for name in ("alpha-1", "fm-1"):
        (src / "triage" / "tasks" / f"{name}.md").write_text(f"# {name}\n", encoding="utf-8")
    (src / "triage" / "overlaps.md").write_text("# Overlaps\n", encoding="utf-8")
    (src / "triage" / "tasks.json").write_text(json.dumps(tasks), encoding="utf-8")
    return src


@pytest.fixture(scope="module")
def build(tmp_path_factory) -> tuple[subprocess.CompletedProcess, Path]:
    result, out = _build(_source(tmp_path_factory.mktemp("tasks"), TASKS))
    assert result.returncode == 0, result.stderr or result.stdout
    return result, out


@pytest.fixture(scope="module")
def page(build) -> str:
    _, out = build
    return (out / "triage" / "index.html").read_text(encoding="utf-8")


def _payload(page: str) -> dict:
    match = re.search(
        rf'<script type="application/json" class="{DATA_CLASS}">(.*?)</script>', page, re.S
    )
    assert match, "the data the client takes over is in the page"
    return json.loads(match.group(1))


def _plain(page: str) -> str:
    match = re.search(rf'<div class="{STATIC_CLASS} table-wrapper">(.*?)</div>', page, re.S)
    assert match, "the plain table is in the page"
    return match.group(1)


def test_the_list_is_rendered_where_the_directive_is(page: str):
    assert (
        page.index("Before the list.")
        < page.index(f'<div class="{WRAPPER_CLASS}">')
        < page.index("After the list.")
    )


def test_the_plain_table_is_grouped_by_project_with_none_last(page: str):
    groups = [
        unescape(g)
        for g in re.findall(
            r'<tr class="group"><th [^>]*><span class="heading">(.*?)</span></th>', _plain(page)
        )
    ]
    assert groups == ["alpha (1)", "firstmate (1)", "none (1)"]


def _cells(plain: str, task_id: str) -> dict[str, str]:
    [row] = [r for r in re.findall(r"<tr>(<td .*?)</tr>", plain) if f">{task_id}<" in r]
    return dict(re.findall(r'<td data-key="([a-z_]+)">(.*?)</td>', row))


def test_the_plain_table_reads_with_no_script(page: str):
    plain = _plain(page)
    headers = [unescape(h) for h in re.findall(r'<th class="head" data-key="[a-z_]+">(.*?)</th>', plain)]
    assert headers == [
        "Task",
        "Title",
        "Unit",
        "Filed",
        "Last activity",
        "State",
        "Work",
        "Stuck",
        "Alignment",
        "Done elsewhere",
        "Stage",
        "Latest recommendation",
    ]
    cells = _cells(plain, "fm-1")
    assert cells["id"] == (
        '<span class="task-id" title="fm-1"><a class="reference" href="tasks/fm-1.html">fm-1</a></span>'
        '<a class="reference tangle" href="overlaps.html#tangle-launcher" '
        'title="tangle-launcher">overlaps</a>'
    )
    assert "tangle" not in _cells(plain, "none-1")["id"], "overlapping nothing, no link"
    assert "tangle" not in _cells(plain, "alpha-1")["id"]
    assert cells["title"] == '<span class="wrap">Tidy &lt;the&gt; &amp; launcher</span>'
    assert cells["unit"] == '<span class="wrap">bin</span>'
    assert cells["work"] == '<span title="code">🔨</span>'
    assert cells["stuck"] == '<span title="captain">⏳</span>'
    assert cells["done_elsewhere"] == '<span title="likely">♻️</span>'
    assert cells["lifecycle_stage"] == '<span title="Worktree &lt;fm/x&gt; exists">branch</span>'
    assert "alpha-1" not in "".join(v for k, v in cells.items() if k != "recommendation"), (
        "no other task's id in the row"
    )
    assert cells["recommendation"] == (
        '<span title="Same as alpha-1"><span class="action">close-duplicate</span>'
        '<span class="meta">2026-10-13 · firstmate</span></span>'
    )


def test_the_plain_table_lays_out_by_the_drawn_lists_column_keys(page: str):
    """The plain table's cells carry the keys `ui/tasks.ts` gives its
    columns, which is what the shared `ui/tasks.css` lays both out by."""
    plain = _plain(page)
    assert re.findall(r'<th class="head" data-key="([a-z_]+)">', plain) == [
        "id",
        "title",
        "unit",
        "filed",
        "last_activity",
        "state",
        "work",
        "stuck",
        "alignment",
        "done_elsewhere",
        "lifecycle_stage",
        "recommendation",
    ]
    assert _cells(plain, "alpha-1")["unit"] == "", "no unit, no wrapper"


def test_the_column_layout_is_in_the_stylesheet_the_plain_table_gets():
    """Unscoped, so it reaches the table the directive rendered: on a page
    opened on its own, no script of this tool runs to style it."""
    declaration = registry.get("tasks")
    css = (registry.static_directory(declaration) / declaration.css_bundle).read_text(encoding="utf-8")
    for rule in (
        ".docstrap-tasks .table-wrapper",
        ".docstrap-tasks .task-id",
        ".docstrap-tasks-static th[data-key='id'] { width:",
        "table-layout: fixed",
    ):
        assert rule in css, rule


def test_the_data_carries_the_tasks_their_links_and_the_symbols(page: str):
    payload = _payload(page)
    assert payload["generated"] == "2026-10-13T12:00:00Z"
    assert payload["vocabulary"] == json.loads(json.dumps(spec.VOCABULARY))
    by_id = {t["id"]: t for t in payload["tasks"]}
    assert [t["id"] for t in payload["tasks"]] == ["fm-1", "none-1", "alpha-1"], "the file's order"
    assert by_id["fm-1"]["link"] == "tasks/fm-1.html"
    assert "duplicate_of" not in by_id["fm-1"]
    assert by_id["fm-1"]["tangle_link"] == "overlaps.html#tangle-launcher"
    assert by_id["fm-1"]["lifecycle_stage"] == "branch"
    assert by_id["none-1"]["tangle_link"] is None
    assert by_id["fm-1"]["latest_recommendation"]["action"] == "close-duplicate"


def test_a_task_page_the_build_lacks_is_warned_about_and_unlinked(build, page: str):
    result, _ = build
    assert "docstrap-tasks: link target 'tasks/none-1' names no document" in result.stderr
    assert {t["id"]: t["link"] for t in _payload(page)["tasks"]}["none-1"] is None


def test_a_task_file_this_tool_cannot_show_fails_the_build(tmp_path: Path):
    result, _ = _build(_source(tmp_path, {"tasks": [{"title": "no id"}]}))
    output = result.stderr + result.stdout
    assert "docstrap-tasks tasks.json" in output
    assert "tasks[0].id" in output


def test_the_tool_is_declared_and_its_bundles_are_built():
    declaration = registry.get("tasks")
    assert declaration.route_prefixes == ("/api/tools/{project}/{doc_slug}/decisions",)
    static = registry.static_directory(declaration)
    assert (static / declaration.js_bundle).is_file()
    assert (static / declaration.css_bundle).is_file()


# --- the decision, in the answer store ---------------------------------------


def test_a_decision_is_spelled_as_its_documentation_says():
    assert decisions.label_for("alpha-hosted-apps-rename-h141") == "task/alpha-hosted-apps-rename-h141"
    assert decisions.task_id_of("task/fm-1") == "fm-1"
    assert decisions.task_id_of("Q1") is None
    assert decisions.text_for("close-done", "  landed in 1a2b3c \n") == (
        "action: close-done\n\nlanded in 1a2b3c"
    )
    assert decisions.text_for("keep", "") == "action: keep"
    assert decisions.parse_text("action: hold\n\nwait for Q3") == ("hold", "wait for Q3")
    assert decisions.parse_text("edited by hand") == (None, "edited by hand")


def test_the_actions_are_the_recommendations_plus_keep():
    assert decisions.ACTIONS == (
        "close-done",
        "close-duplicate",
        "close-obsolete",
        "reshape",
        "dispatch",
        "hold",
        "ask",
        "keep",
    )
    with pytest.raises(decisions.DecisionError):
        decisions.text_for("delete", "")
    with pytest.raises(decisions.DecisionError):
        decisions.label_for("two words")


# --- the route, against the real app -----------------------------------------

PROJECT_PATH = "packages/thing"
PROJECT_SLUG = "packages__thing"

DOCSTRAP_YAML = f"""\
version: 1
title: A Store
projects:
  - path: {PROJECT_PATH}
    title: The Thing
    layout: markdown
    sources:
      - path: docs
        role: documentation
      - path: drafts
        role: draft
"""

TRIAGE = """\
# Triage

```{docstrap-tasks} tasks.json
```

## Open questions

**Q1.** Is a question on this page kept apart from the decisions?
"""

RECORDER = """\
import json, sys
with open(sys.argv[1], "w", encoding="utf-8") as f:
    json.dump(sys.argv[2:], f)
"""


@pytest.fixture
def project(tmp_path: Path, user_dirs: Path) -> ScannedProject:
    store = tmp_path / "store"
    docs = store / PROJECT_PATH / "docs"
    (docs / "triage").mkdir(parents=True)
    (docs / "triage" / "index.md").write_text(TRIAGE, encoding="utf-8")
    (store / PROJECT_PATH / "drafts").mkdir()
    (store / ".docstrap").write_text(DOCSTRAP_YAML, encoding="utf-8")
    user_config.add_store(store / ".docstrap")
    return [p for p in scan(load(store / ".docstrap")) if p.kind == "project"][0]


def _call(path: str, method: str = "GET", **kwargs):
    """Call the handler `make_app` would reach for this method and path."""
    app = make_app(Path("/nonexistent-site-root"))
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": [],
        "path_params": {},
        "root_path": "",
    }
    for route in app.router.routes:
        match, child = route.matches(scope)
        if match is Match.FULL:
            return route.endpoint(**child["path_params"], **kwargs)
    raise AssertionError(f"no route matched {method} {path}")


def _url(doc_slug: str = "triage/index") -> str:
    return registry.get("tasks").route_prefix.format(project=PROJECT_SLUG, doc_slug=doc_slug)


def _decide(task_id: str, action: str, note: str = "") -> dict:
    return _call(
        _url(), "POST", payload=DecisionSubmission(task_id=task_id, action=action, note=note)
    )


def test_a_page_nobody_has_decided_on_has_no_decisions_and_registers_nothing(
    project: ScannedProject,
):
    body = _call(_url())
    assert body == {
        "decisions": {},
        "actions": list(decisions.ACTIONS),
        "answersDoneRoute": None,
    }
    page = Path(project.root_dir) / "docs" / "triage" / "index.md"
    assert meta.get_document_by_path(str(page.resolve())) is None


def test_a_decision_is_keyed_on_the_page_and_the_task(project: ScannedProject):
    stored = _decide("fm-1", "close-done", "landed in 1a2b3c")

    page = Path(project.root_dir) / "docs" / "triage" / "index.md"
    doc_id = meta.get_document_by_path(str(page.resolve())).id
    assert stored["key"] == f"{doc_id}:task/fm-1"
    assert stored["taskId"] == "fm-1"
    assert stored["decision"]["action"] == "close-done"

    [answer] = answer_store.submitted(PROJECT_SLUG)
    assert answer.key == f"{doc_id}:task/fm-1"
    assert answer.label == "task/fm-1"
    assert answer.document == "docs/triage/index.md"
    assert answer.text == "action: close-done\n\nlanded in 1a2b3c"
    assert answer.submitted is True

    assert _call(_url())["decisions"] == {
        "fm-1": {
            "action": "close-done",
            "note": "landed in 1a2b3c",
            "decidedAt": answer.submitted_at,
        }
    }


def test_deciding_again_supersedes_and_keeps_the_earlier_one(project: ScannedProject):
    _decide("fm-1", "hold", "wait")
    _decide("fm-1", "dispatch")
    [answer] = answer_store.submitted(PROJECT_SLUG)
    assert answer.text == "action: dispatch"
    [earlier] = answer_store.history(PROJECT_SLUG, answer.key)
    assert earlier.text == "action: hold\n\nwait"
    assert _call(_url())["decisions"]["fm-1"]["action"] == "dispatch"


def test_one_decision_per_task(project: ScannedProject):
    _decide("fm-1", "keep")
    _decide("alpha-1", "ask", "which plan?")
    found = _call(_url())["decisions"]
    assert {task: d["action"] for task, d in found.items()} == {"fm-1": "keep", "alpha-1": "ask"}


def test_an_answer_to_a_question_on_the_page_is_not_a_decision(project: ScannedProject):
    page = Path(project.root_dir) / "docs" / "triage" / "index.md"
    answer_store.put(
        PROJECT_SLUG,
        doc_id=answer_store.document_id_for(page, PROJECT_SLUG),
        label="Q1",
        document="docs/triage/index.md",
        text="Yes.",
        submitted=True,
    )
    _decide("fm-1", "keep")
    assert list(_call(_url())["decisions"]) == ["fm-1"]


@pytest.mark.parametrize(
    ("task_id", "action"), [("fm-1", "delete"), ("two words", "keep"), ("a:b", "keep")]
)
def test_a_decision_this_tool_will_not_record_is_400(
    project: ScannedProject, task_id: str, action: str
):
    with pytest.raises(HTTPException) as caught:
        _decide(task_id, action)
    assert caught.value.status_code == 400
    assert not answer_store.store_path(PROJECT_SLUG).exists()


def test_an_unknown_page_is_404(project: ScannedProject):
    with pytest.raises(HTTPException) as caught:
        _call(_url("nowhere"))
    assert caught.value.status_code == 404


def test_answers_done_is_the_existing_prompt_for_this_page(
    project: ScannedProject, tmp_path: Path
):
    """The route the page is handed is the qapanels document-scope POST,
    and pressing it runs the configured command with this page's path —
    the `document` every decision on the page is stored under."""
    record = tmp_path / "argv.json"
    script = tmp_path / "command.py"
    script.write_text(RECORDER, encoding="utf-8")
    cfg = user_config.load()
    cfg.answers_done_command = [sys.executable, str(script), str(record)]
    user_config.save(cfg)

    route = _call(_url())["answersDoneRoute"]
    assert route == registry.get("qapanels").route_prefixes[1].format(
        project=PROJECT_SLUG, doc_slug="triage/index"
    )
    _decide("fm-1", "keep")
    assert _call(route, "POST") == {"ok": True, "exitStatus": 0, "error": ""}
    [answer] = answer_store.submitted(PROJECT_SLUG)
    assert json.loads(record.read_text(encoding="utf-8")) == [
        "--project",
        PROJECT_SLUG,
        "--document",
        answer.document,
    ]


# --- the client's rules, under Node ------------------------------------------


def _node() -> str | None:
    node = shutil.which("node")
    if node is None:
        return None
    version = subprocess.run([node, "--version"], capture_output=True, text=True).stdout
    match = re.match(r"v(\d+)\.(\d+)", version)
    # Type stripping arrived in 22.6.
    if not match or (int(match.group(1)), int(match.group(2))) < (22, 6):
        return None
    return node


def test_the_grouping_drill_down_and_address_rules_pass_under_node():
    node = _node()
    if node is None:
        pytest.skip("needs Node 22.6 or later, for --experimental-strip-types")
    result = subprocess.run(
        [node, "--experimental-strip-types", "--test", "tests/tasks/tasks.test.ts"],
        cwd=PACKAGE,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
