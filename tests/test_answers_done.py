"""The "answers done" prompt: one command, run once, only when configured.

Routes are reached through Starlette's own matcher
against the real `make_app`, as `test_answers_api.py` reaches them, and the
URL each one is reached at is the one the listing handed the page — so a
test that passes here is the click that works in the panel.

The command is a real executable written into the test's own directory.
It records the argv it was given and nothing else, so what is asserted is
what a receiver would actually see.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException
from starlette.routing import Match

from docstrap import answers_done, user_config
from docstrap import answers as answer_store
from docstrap.config import load
from docstrap.scan import ScannedProject, scan
from docstrap.server import make_app
from docstrap.tools import registry
from docstrap.tools.qapanels.routes import AnswerSubmission

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

SPEC = """\
# The thing

## Open questions

**Q1.** Which storage layout?
"""

NESTED = """\
# A nested proposal

## Open questions

**Q1.** Does a nested document get its own prompt?
"""

RECORDER = """\
import json, sys
with open(sys.argv[1], "w", encoding="utf-8") as f:
    json.dump(sys.argv[2:], f)
"""

FAILER = """\
import sys
sys.stderr.write("intake refused the notice\\n")
sys.exit(3)
"""

SLEEPER = """\
import time
time.sleep(5)
"""

UI = Path(answers_done.__file__).parent / "tools" / "qapanels"


@pytest.fixture
def project(tmp_path: Path, user_dirs: Path) -> ScannedProject:
    store = tmp_path / "store"
    docs = store / PROJECT_PATH / "docs"
    (docs / "proposals").mkdir(parents=True)
    (docs / "spec.md").write_text(SPEC, encoding="utf-8")
    (docs / "proposals" / "0001-nested.md").write_text(NESTED, encoding="utf-8")
    (store / PROJECT_PATH / "drafts").mkdir()
    (store / ".docstrap").write_text(DOCSTRAP_YAML, encoding="utf-8")
    user_config.add_store(store / ".docstrap")
    scanned = [p for p in scan(load(store / ".docstrap")) if p.kind == "project"]
    return scanned[0]


def _configure(tmp_path: Path, source: str, *extra: str) -> None:
    script = tmp_path / "command.py"
    script.write_text(source, encoding="utf-8")
    cfg = user_config.load()
    cfg.answers_done_command = [sys.executable, str(script), *extra]
    user_config.save(cfg)


def _call(path: str, method: str = "GET", **kwargs):
    """Call the handler `make_app` would reach for this path."""
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


def _listing(doc_slug: str | None = None) -> dict:
    declaration = registry.get("qapanels")
    project_prefix, document_prefix = declaration.route_prefixes
    if doc_slug is None:
        return _call(project_prefix.format(project=PROJECT_SLUG))
    return _call(document_prefix.format(project=PROJECT_SLUG, doc_slug=doc_slug))


def _route(listing: dict, doc_slug: str) -> str | None:
    return next(d for d in listing["documents"] if d["docSlug"] == doc_slug)["answersDoneRoute"]


# --- unset: no prompt, and nothing to call -----------------------------------


def test_unset_offers_no_prompt_on_any_document(project: ScannedProject):
    listing = _listing()
    assert listing["documents"]
    assert all(d["answersDoneRoute"] is None for d in listing["documents"])
    assert _route(_listing("spec"), "spec") is None


def test_unset_refuses_the_route_rather_than_pretending_it_ran(project: ScannedProject):
    declaration = registry.get("qapanels")
    url = declaration.route_prefixes[1].format(project=PROJECT_SLUG, doc_slug="spec")
    with pytest.raises(HTTPException) as caught:
        _call(url, "POST")
    assert caught.value.status_code == 404
    assert "answers_done_command" in caught.value.detail


# --- configured: one prompt per document, and the command it runs ------------


def test_configured_offers_one_route_per_document(project: ScannedProject, tmp_path: Path):
    _configure(tmp_path, RECORDER, str(tmp_path / "argv.json"))
    listing = _listing()
    routes = {d["docSlug"]: d["answersDoneRoute"] for d in listing["documents"]}
    assert routes == {
        "spec": f"/api/tools/{PROJECT_SLUG}/spec/qa",
        # A document's identity is a path, and its route carries it as one.
        "proposals/0001-nested": f"/api/tools/{PROJECT_SLUG}/proposals/0001-nested/qa",
    }
    # The document scope offers the same route for its one document.
    assert _route(_listing("spec"), "spec") == routes["spec"]


def test_the_command_gets_the_project_and_the_answer_stores_document_path(
    project: ScannedProject, tmp_path: Path
):
    record = tmp_path / "argv.json"
    _configure(tmp_path, RECORDER, str(record))
    # An answer first, so the path the store records can be compared with
    # the path the command was handed: the receiver finds answers by it.
    _call(
        registry.get("qapanels").route_prefix.format(project=PROJECT_SLUG),
        "POST",
        payload=AnswerSubmission(doc_slug="proposals/0001-nested", label="Q1", answer="Yes."),
    )
    [stored] = answer_store.read(PROJECT_SLUG)

    result = _call(_route(_listing(), "proposals/0001-nested"), "POST")

    assert result == {"ok": True, "exitStatus": 0, "error": ""}
    assert json.loads(record.read_text(encoding="utf-8")) == [
        "--project",
        PROJECT_SLUG,
        "--document",
        stored.document,
    ]
    assert stored.document == "docs/proposals/0001-nested.md"


def test_pressing_it_writes_no_answer(project: ScannedProject, tmp_path: Path):
    """The prompt submits nothing; answers save on their own."""
    _configure(tmp_path, RECORDER, str(tmp_path / "argv.json"))
    _call(_route(_listing(), "spec"), "POST")
    assert not answer_store.store_path(PROJECT_SLUG).exists()


def test_a_failing_command_reports_its_own_error(project: ScannedProject, tmp_path: Path):
    _configure(tmp_path, FAILER)
    result = _call(_route(_listing(), "spec"), "POST")
    assert result == {"ok": False, "exitStatus": 3, "error": "intake refused the notice"}


def test_a_missing_command_is_reported_not_raised(project: ScannedProject, tmp_path: Path):
    cfg = user_config.load()
    cfg.answers_done_command = [str(tmp_path / "no-such-command")]
    user_config.save(cfg)
    result = _call(_route(_listing(), "spec"), "POST")
    assert result["ok"] is False
    assert result["exitStatus"] is None
    assert "no-such-command" in result["error"]


def test_a_command_that_hangs_is_cut_off(
    project: ScannedProject, tmp_path: Path, monkeypatch
):
    monkeypatch.setattr(answers_done, "TIMEOUT_SECONDS", 0.5)
    _configure(tmp_path, SLEEPER)
    result = _call(_route(_listing(), "spec"), "POST")
    assert result["ok"] is False
    assert "did not finish" in result["error"]


def test_an_unknown_document_is_404(project: ScannedProject, tmp_path: Path):
    _configure(tmp_path, RECORDER, str(tmp_path / "argv.json"))
    url = registry.get("qapanels").route_prefixes[1].format(
        project=PROJECT_SLUG, doc_slug="nowhere"
    )
    with pytest.raises(HTTPException) as caught:
        _call(url, "POST")
    assert caught.value.status_code == 404
    assert not (tmp_path / "argv.json").exists()


# --- the setting --------------------------------------------------------------


def test_the_setting_is_an_argv_list_and_absent_is_never_written(user_dirs: Path):
    user_config.save(user_config.UserConfig())
    text = user_config.paths.user_config_file().read_text(encoding="utf-8")
    assert "answers_done_command" not in text

    user_config.paths.user_config_file().write_text(
        "version: 1\nanswers_done_command: fm-procevent-docstrap.sh notice\n",
        encoding="utf-8",
    )
    # A bare string would need a shell to split it, and nothing runs one.
    assert user_config.load().answers_done_command is None

    cfg = user_config.UserConfig(answers_done_command=["/bin/notify", "notice"])
    user_config.save(cfg)
    assert user_config.load().answers_done_command == ["/bin/notify", "notice"]


# --- the prompt ---------------------------------------------------------------


def test_the_prompt_renders_only_where_the_server_offered_a_route():
    """One per document, gated on the route the listing carries.

    The gate sits outside the questions loop, so the prompt can never
    become a per-question button, and the committed bundle carries it.
    """
    source = (UI / "ui" / "QuestionList.svelte").read_text(encoding="utf-8")
    gate = source.index("{#if entry.answersDoneRoute}")
    prompt = source.index("Answers done</button>")
    questions = source.index("{#each entry.questions")
    assert gate < prompt < questions

    bundle = (UI / "static" / registry.get("qapanels").js_bundle).read_text(encoding="utf-8")
    assert "answersDoneRoute" in bundle and "Answers done" in bundle, (
        "the committed build is stale"
    )
