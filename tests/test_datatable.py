"""The data table tool: the table file, the directive, and the client rules.

Three halves, the same way the other tools are proved.

The table file is plain data, so `spec.parse` is tested as plain data:
what it fills in, and every way it refuses a file, each refusal naming
the field. A refusal that does not say where is a build error nobody can
act on.

The directive is proved by a real `sphinx-build` over a nested source
tree — a page one directory below the root linking to a document one
further down, because a flat sample is how the nested-route defect lived
as long as it did. Assertions are on
the HTML that comes out: the plain table is there and reads with no
script, the data the client takes over is there and cannot close its own
element, and a link target is resolved by the build or warned about.

The sorting and filtering are TanStack Table's, given docstrap's column
rules by `ui/table.ts` and `ui/grid.ts`, and are tested in TypeScript,
under Node, by `tests/datatable/table.test.ts`. The last test here runs
that suite, so `pytest` alone covers all three.
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

from docstrap.tools import registry
from docstrap.tools.datatable import spec
from docstrap.tools.datatable.views import (
    DATA_CLASS,
    STATIC_CLASS,
    WRAPPER_CLASS,
    display,
    script_json,
)

PACKAGE = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures" / "datatable"


# --- the table file ----------------------------------------------------------


def test_a_column_gets_its_defaults():
    table = spec.parse({"columns": [{"key": "title", "type": "text"}], "rows": []})
    (column,) = table.columns
    assert column == spec.Column(
        key="title", label="title", type="text", sortable=True, filterable=False
    )
    assert column.to_payload() == {
        "key": "title",
        "label": "title",
        "type": "text",
        "sortable": True,
        "filterable": False,
    }


def test_every_column_type_and_option_is_read():
    table = spec.parse(
        {
            "columns": [
                {"key": "id", "label": "Task", "type": "link", "href": "page"},
                {"key": "filed", "label": "Filed", "type": "date", "filterable": True},
                {"key": "state", "type": "enum", "values": ["queued", "held"]},
                {
                    "key": "work",
                    "type": "symbol",
                    "sortable": False,
                    "symbols": {"code": "🔨"},
                    "values": ["code"],
                },
                {"key": "title", "type": "text"},
            ],
            "rows": [
                {
                    "id": "fm-1",
                    "page": "tasks/fm-1",
                    "filed": "2026-10-01",
                    "state": "queued",
                    "work": "code",
                    "title": "A task",
                    "duplicates": ["fm-2"],
                    "extra": 3,
                }
            ],
        }
    )
    link, date, enum, symbol, _ = table.columns
    assert link.href == "page"
    assert date.filterable
    assert enum.values == ("queued", "held")
    assert symbol.symbols == {"code": "🔨"} and not symbol.sortable
    assert table.rows[0]["extra"] == 3, "fields no column shows are kept, for links"


def test_a_missing_cell_and_a_null_date_are_allowed():
    spec.parse(
        {
            "columns": [{"key": "filed", "type": "date"}, {"key": "unit", "type": "text"}],
            "rows": [{"filed": None}, {}],
        }
    )


def test_a_date_may_carry_a_time():
    spec.parse(
        {"columns": [{"key": "at", "type": "date"}], "rows": [{"at": "2026-10-01T09:30:00Z"}]}
    )


@pytest.mark.parametrize(
    ("data", "names"),
    [
        ([], "JSON object"),
        ({"rows": []}, "columns"),
        ({"columns": [], "rows": []}, "columns"),
        ({"columns": [{"key": "a", "type": "text"}]}, "rows"),
        ({"columns": [{"key": "a", "type": "text"}], "rows": [], "sort": {}}, "'sort'"),
        ({"columns": ["a"], "rows": []}, "columns[0]"),
        ({"columns": [{"type": "text"}], "rows": []}, "columns[0].key"),
        ({"columns": [{"key": "a"}], "rows": []}, "columns[0].type"),
        ({"columns": [{"key": "a", "type": "number"}], "rows": []}, "'number'"),
        ({"columns": [{"key": "a", "type": "text", "wide": True}], "rows": []}, "'wide'"),
        (
            {"columns": [{"key": "a", "type": "text"}, {"key": "a", "type": "date"}], "rows": []},
            "columns[1].key",
        ),
        ({"columns": [{"key": "a", "type": "text", "sortable": "yes"}], "rows": []}, "sortable"),
        ({"columns": [{"key": "a", "type": "text", "values": ["x"]}], "rows": []}, "values"),
        ({"columns": [{"key": "a", "type": "enum", "values": [1]}], "rows": []}, "values"),
        ({"columns": [{"key": "a", "type": "symbol"}], "rows": []}, "symbols"),
        ({"columns": [{"key": "a", "type": "enum", "symbols": {}}], "rows": []}, "symbols"),
        ({"columns": [{"key": "a", "type": "text", "href": "p"}], "rows": []}, "href"),
        ({"columns": [{"key": "a", "type": "text"}], "rows": ["x"]}, "rows[0]"),
        ({"columns": [{"key": "a", "type": "text"}], "rows": [{"a": {"b": 1}}]}, "rows[0].a"),
        ({"columns": [{"key": "a", "type": "text"}], "rows": [{"a": [None]}]}, "rows[0].a"),
        ({"columns": [{"key": "d", "type": "date"}], "rows": [{"d": "10/01/2026"}]}, "rows[0].d"),
        ({"columns": [{"key": "d", "type": "date"}], "rows": [{"d": 20261001}]}, "rows[0].d"),
        (
            {"columns": [{"key": "a", "type": "link", "href": "p"}], "rows": [{"a": "x", "p": 3}]},
            "rows[0].p",
        ),
    ],
)
def test_a_malformed_table_file_is_refused_naming_where(data, names):
    with pytest.raises(spec.TableError, match=re.escape(names)):
        spec.parse(data)


def test_load_names_a_file_that_is_not_json(tmp_path: Path):
    path = tmp_path / "t.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(spec.TableError, match="is not JSON"):
        spec.load(path)
    with pytest.raises(spec.TableError, match="cannot read"):
        spec.load(tmp_path / "absent.json")


# --- what a cell reads as ----------------------------------------------------


def test_display_matches_the_fixture_the_client_is_held_to():
    """`views.display` and `table.ts` `cellText` are one rule written twice:
    once for the plain table the build draws, once for the table the client
    draws. Both are held to this one fixture."""
    cases = json.loads((FIXTURES / "cell-text.json").read_text(encoding="utf-8"))
    for case in cases:
        assert display(case["value"], case.get("symbols")) == case["text"], case


def test_script_json_cannot_end_its_script_element():
    text = script_json({"title": "</script><script>alert(1)</script> & <!--"})
    assert "<" not in text and ">" not in text and "&" not in text
    assert json.loads(text) == {"title": "</script><script>alert(1)</script> & <!--"}


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
triage/summary
triage/tasks/fm-1
```
"""

SUMMARY = """\
# Census

Before the table.

```{docstrap-datatable} census.json
```

After the table.
"""

TABLE = {
    "columns": [
        {"key": "id", "label": "Task", "type": "link", "href": "page", "filterable": True},
        {"key": "title", "label": "Title", "type": "text", "filterable": True},
        {"key": "filed", "label": "Filed", "type": "date"},
        {
            "key": "work",
            "label": "Work",
            "type": "symbol",
            "filterable": True,
            "symbols": {"code": "🔨", "docs": "📝"},
        },
        {"key": "duplicates", "label": "Duplicates", "type": "enum", "filterable": True},
    ],
    "rows": [
        {
            "id": "fm-1",
            "page": "tasks/fm-1",
            "title": "Fix <b> & friends",
            "filed": "2026-10-01",
            "work": "code",
            "duplicates": ["fm-2", "fm-3"],
        },
        {"id": "fm-2", "page": "tasks/fm-2.md#status", "title": "Gone", "work": "docs"},
        {"id": "ext", "page": "https://example.org/x", "title": "Elsewhere"},
        {"id": "fm-1-again", "page": "tasks/fm-1.md#status", "title": "Anchored"},
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


def _source(root: Path, table: object) -> Path:
    src = root / "src"
    (src / "triage" / "tasks").mkdir(parents=True)
    extensions = ["myst_parser", *registry.sphinx_extensions()]
    (src / "conf.py").write_text(CONF.format(extensions=extensions), encoding="utf-8")
    (src / "index.md").write_text(INDEX, encoding="utf-8")
    (src / "triage" / "summary.md").write_text(SUMMARY, encoding="utf-8")
    (src / "triage" / "tasks" / "fm-1.md").write_text("# fm-1\n\n## Status\n", encoding="utf-8")
    (src / "triage" / "census.json").write_text(json.dumps(table), encoding="utf-8")
    return src


@pytest.fixture(scope="module")
def build(tmp_path_factory) -> tuple[subprocess.CompletedProcess, Path]:
    source = _source(tmp_path_factory.mktemp("datatable"), TABLE)
    result, out = _build(source)
    assert result.returncode == 0, result.stderr or result.stdout
    return result, out


@pytest.fixture(scope="module")
def page(build) -> str:
    _, out = build
    return (out / "triage" / "summary.html").read_text(encoding="utf-8")


def _payload(page: str) -> dict:
    match = re.search(
        rf'<script type="application/json" class="{DATA_CLASS}">(.*?)</script>', page, re.S
    )
    assert match, "the data the client takes over is in the page"
    return json.loads(match.group(1))


def _plain_table(page: str) -> str:
    match = re.search(rf'<div class="{STATIC_CLASS} table-wrapper">(.*?)</div>', page, re.S)
    assert match, "the plain table is in the page"
    return match.group(1)


def test_the_table_is_rendered_where_the_directive_is(page: str):
    before = page.index("Before the table.")
    wrapper = page.index(f'<div class="{WRAPPER_CLASS}">')
    after = page.index("After the table.")
    assert before < wrapper < after


def test_the_plain_table_reads_with_no_script(page: str):
    table = _plain_table(page)
    headers = [unescape(h) for h in re.findall(r"<th [^>]*>(.*?)</th>", table)]
    assert headers == ["Task", "Title", "Filed", "Work", "Duplicates"]
    rows = re.findall(r"<tr>(.*?)</tr>", table.split("<tbody>")[1], re.S)
    assert len(rows) == 4
    first = re.findall(r"<td>(.*?)</td>", rows[0])
    assert first[1] == "Fix &lt;b&gt; &amp; friends", "cell text is escaped"
    assert first[2] == "2026-10-01"
    assert first[3] == '<span title="code">🔨</span>'
    assert first[4] == "fm-2, fm-3"


def test_the_data_carries_the_columns_and_only_their_cells(page: str):
    payload = _payload(page)
    assert [c["key"] for c in payload["columns"]] == ["id", "title", "filed", "work", "duplicates"]
    assert payload["columns"][3]["symbols"] == {"code": "🔨", "docs": "📝"}
    first = payload["rows"][0]
    assert first["cells"] == {
        "id": "fm-1",
        "title": "Fix <b> & friends",
        "filed": "2026-10-01",
        "work": "code",
        "duplicates": ["fm-2", "fm-3"],
    }
    assert "page" not in first["cells"], "a field no column shows is not shipped"
    assert payload["rows"][2]["cells"]["filed"] is None


def test_a_document_target_resolves_to_its_built_page(page: str):
    payload = _payload(page)
    assert payload["rows"][0]["links"] == {"id": "tasks/fm-1.html"}
    assert payload["rows"][3]["links"] == {"id": "tasks/fm-1.html#status"}
    assert '<a class="reference" href="tasks/fm-1.html">fm-1</a>' in _plain_table(page)


def test_a_target_with_a_scheme_is_used_as_written(page: str):
    assert _payload(page)["rows"][2]["links"] == {"id": "https://example.org/x"}


def test_a_target_naming_no_document_is_warned_about_and_unlinked(build, page: str):
    result, _ = build
    assert "'tasks/fm-2.md#status' names no document" in result.stderr
    assert _payload(page)["rows"][1]["links"] == {}
    assert "<td>fm-2</td>" in _plain_table(page)


def test_a_malformed_table_file_fails_the_build_naming_the_field(tmp_path: Path):
    broken = {"columns": [{"key": "a", "type": "number"}], "rows": []}
    result, _ = _build(_source(tmp_path, broken))
    output = result.stderr + result.stdout
    assert "docstrap-datatable census.json" in output
    assert "columns[0].type" in output


def test_the_tool_is_declared_and_its_bundles_are_built():
    declaration = registry.get("datatable")
    assert declaration.route_prefixes == (), "the rows are in the page; nothing is served"
    static = registry.static_directory(declaration)
    assert (static / declaration.js_bundle).is_file()
    assert (static / declaration.css_bundle).is_file()


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


def test_the_sort_and_filter_rules_pass_under_node():
    node = _node()
    if node is None:
        pytest.skip("needs Node 22.6 or later, for --experimental-strip-types")
    result = subprocess.run(
        [node, "--experimental-strip-types", "--test", "tests/datatable/table.test.ts"],
        cwd=PACKAGE,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


# --- the census example ------------------------------------------------------

CENSUS_COLUMNS = [
    "id",
    "title",
    "project",
    "unit",
    "filed",
    "last_activity",
    "state",
    "work",
    "stuck",
    "alignment",
    "done_elsewhere",
    "duplicates",
    "recommendation",
]


def test_the_census_example_builds_with_every_task_linked(tmp_path: Path):
    """`tests/fixtures/datatable/census` is the shape a generator is
    expected to write: a summary page, its table file, and a
    detail page per task one directory down."""
    src = tmp_path / "src"
    shutil.copytree(FIXTURES / "census", src)
    extensions = ["myst_parser", *registry.sphinx_extensions()]
    conf = CONF.format(extensions=extensions).replace('"index"', '"census"')
    (src / "conf.py").write_text(conf, encoding="utf-8")

    result, out = _build(src)
    assert result.returncode == 0, result.stderr or result.stdout
    assert "names no document" not in result.stderr

    payload = _payload((out / "census.html").read_text(encoding="utf-8"))
    assert [c["key"] for c in payload["columns"]] == CENSUS_COLUMNS
    for row in payload["rows"]:
        assert row["links"] == {"id": f"tasks/{row['cells']['id']}.html"}
        assert (out / row["links"]["id"]).is_file()
