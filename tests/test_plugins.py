"""The plugin seam: six hooks, and docstrap naming no plugin.

Four things are held here:

1. **The fence.** No docstrap module imports promdance or names it in
   code, and importing every docstrap module loads none of promdance: the
   one way in is the plugin manager's entry-point load. The same shape as
   the forge fingerprint test. That promdance is found
   through the entry-point group, and what it does there, is held in
   promdance's own suite.
2. **Filtering.** A hook calls only the plugins the settings enable for
   that project, through pluggy's `subset_hook_caller`.
3. **The draft root.** A plugin's answer first, then a declared `draft`
   source, then none — and none is an error for a writer, not a directory
   invented for it.
4. **Draft sources as a concept.** A declared draft source publishes its
   answer store without drafts.
"""
from __future__ import annotations

import ast
import io
import subprocess
import sys
import tokenize
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from docstrap import answers, drafts, gitignore, paths, plugins
from docstrap.cli import app as docstrap_app
from docstrap.config import DRAFT_ROLE, Source, load
from docstrap.layouts import markdown
from docstrap.plugins import Finding, hookimpl
from docstrap.scan import scan

runner = CliRunner()

PACKAGE = Path(plugins.__file__).parent

#: The one other module that spells the word in code: the frozen record of
#: the settings shape before the `plugins` block, which `docstrap config
#: migrate` and the old-shape load error read. It describes the past, as
#: `generated_indexes`' recogniser does, and imports nothing of promdance's.
LEGACY_SHAPE = "legacy_settings.py"

#: The top-level package promdance is imported as.
PROMDANCE = "promdance"


# --- 1. the fence ---------------------------------------------------------------------


def _python_sources() -> list[Path]:
    return sorted(PACKAGE.rglob("*.py"))


def _ui_sources() -> list[Path]:
    """TypeScript and Svelte sources; the built bundles under `static/` are output."""
    return sorted(
        path
        for pattern in ("*.ts", "*.svelte")
        for path in PACKAGE.rglob(pattern)
        if "static" not in path.relative_to(PACKAGE).parts
    )


def _code_text(source: str) -> str:
    """``source`` with its docstrings and comments taken out.

    Prose may describe a plugin docstrap works alongside — a module's
    consumers, a migrated key's old spelling — without that being a
    dependency, so, as in the forge fingerprint test, only code counts.
    """
    docstrings = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            text = ast.get_docstring(node, clean=False)
            if text:
                docstrings.append(text)
    for text in docstrings:
        source = source.replace(text, "")
    return "".join(
        token.string
        for token in tokenize.generate_tokens(io.StringIO(source).readline)
        if token.type != tokenize.COMMENT
    )


def _names_promdance(source: str) -> bool:
    return PROMDANCE in _code_text(source).lower()


def _imported_modules(source: str) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
            found.update(f"{node.module}.{alias.name}" for alias in node.names)
    return found


def _imports_promdance(source: str) -> bool:
    return any(
        name == PROMDANCE or name.startswith(f"{PROMDANCE}.")
        for name in _imported_modules(source)
    )


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_the_fingerprint_is_real():
    """The fence is only worth anything if it can fail."""
    assert _names_promdance('PLUGIN = "promdance"\n')
    assert not _names_promdance(_read(PACKAGE / "plugins.py"))
    assert _imports_promdance("from promdance import placement\n")
    assert _imports_promdance("import promdance.cli\n")
    assert not _imports_promdance("from docstrap import placement\nimport promdancer\n")
    assert _code_text('"""promdance in prose."""\n# promdance\nx = 1\n').count("promdance") == 0
    assert "promdance" in _code_text('x = "promdance"\n')


def test_no_docstrap_module_names_promdance_in_code():
    offenders = [
        path.relative_to(PACKAGE).as_posix()
        for path in _python_sources()
        if path.name != LEGACY_SHAPE and _names_promdance(_read(path))
    ]
    assert offenders == []


def test_no_docstrap_module_imports_promdance():
    """The dependency runs one way, promdance onto docstrap."""
    offenders = [
        path.relative_to(PACKAGE).as_posix()
        for path in _python_sources()
        if _imports_promdance(_read(path))
    ]
    assert offenders == []


def test_importing_all_of_docstrap_loads_nothing_of_promdance():
    """The fence at run time: only the plugin manager brings promdance in.

    Every docstrap module is imported in a fresh interpreter, so an import
    reached indirectly — through a lazy import at module level, a package
    ``__init__`` or a dependency — is caught as well as a written one.
    Asking for the manager is the seam, and only then may promdance load.
    """
    probe = (
        "import importlib, pkgutil, sys\n"
        "import docstrap\n"
        "for m in pkgutil.walk_packages(docstrap.__path__, 'docstrap.'):\n"
        "    importlib.import_module(m.name)\n"
        f"print(sorted(n for n in sys.modules if n.split('.')[0] == {PROMDANCE!r}))\n"
    )
    run = subprocess.run(
        [sys.executable, "-c", probe], capture_output=True, text=True, check=False
    )
    assert run.returncode == 0, run.stderr
    assert run.stdout.strip() == "[]"


def test_the_legacy_shape_imports_nothing():
    imported = _imported_modules(_read(PACKAGE / LEGACY_SHAPE))
    assert not {m for m in imported if m.startswith("docstrap") or m.startswith(PROMDANCE)}


def test_no_tool_ui_source_names_promdance():
    offenders = [
        path.relative_to(PACKAGE).as_posix()
        for path in _ui_sources()
        if "promdance" in path.read_text(encoding="utf-8").lower()
    ]
    assert _ui_sources(), "the UI sources moved; point this test at them"
    assert offenders == []


def test_the_route_base_names_the_tools_not_a_plugin():
    from docstrap.tools import declaration

    assert set(declaration._TARGET_ROUTE_BASE.values()) == {
        "/api/tools/{project}/{doc_slug}",
        "/api/tools/{project}",
    }


# --- 2. filtering ------------------------------------------------------------------------


class _Probe:
    """A plugin that records what it was asked and answers every hook."""

    def __init__(self, root: Path):
        self.root = root
        self.calls: list[tuple[str, object]] = []

    @hookimpl
    def docstrap_prepare_project(self, project, settings):
        self.calls.append(("prepare", project.slug))

    @hookimpl
    def docstrap_project_sources(self, project, settings):
        self.calls.append(("sources", dict(settings["probe"])))
        return [Source(path=str(self.root / "probe-drafts"), role=DRAFT_ROLE, mount="probe")]

    @hookimpl
    def docstrap_draft_root(self, project_slug):
        self.calls.append(("draft_root", project_slug))
        target = self.root / "probe-store" / project_slug
        target.mkdir(parents=True, exist_ok=True)
        return target

    @hookimpl
    def docstrap_gitignore_patterns(self):
        return ["probe-link"]

    @hookimpl
    def docstrap_init(self):
        return [("probe", self.root / "probe-store")]

    @hookimpl
    def docstrap_doctor_report(self, root):
        return [Finding(ok=False, message=f"probe looked at {root}")]


@pytest.fixture
def probe(tmp_path: Path):
    instance = _Probe(tmp_path)
    (tmp_path / "probe-drafts").mkdir()
    (tmp_path / "probe-drafts" / "idea.md").write_text("# Idea\n", encoding="utf-8")
    pm = plugins.manager()
    pm.register(instance, name="probe")
    try:
        yield instance
    finally:
        pm.unregister(instance)


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _user_config(data: dict) -> None:
    _write(paths.user_config_file(), yaml.safe_dump(data))


def _registered_project(root: Path, docstrap: str, extra: dict | None = None):
    """One project, its store registered, the user config migrated."""
    config = _write(root / ".docstrap", docstrap)
    _user_config(
        {
            "version": 1,
            "stores": [str(config)],
            "sources": [{"path": "docs", "role": "documentation"}],
            "plugins": {"promdance": {"enabled": False}},
            **(extra or {}),
        }
    )
    (project,) = [p for p in scan(load(config)) if p.kind == "project"]
    return project


def test_a_plugin_runs_only_where_the_settings_turn_it_on(
    tmp_path: Path, user_dirs: Path, probe: _Probe
):
    """Installed is not on: the probe is asked nothing until a level says so."""
    off = _registered_project(tmp_path / "quiet", "version: 1\ntitle: quiet\n")
    assert "probe" in plugins.installed()
    assert plugins.project_sources(off) == ()
    plugins.prepare_project(off)
    assert probe.calls == []

    on = _registered_project(
        tmp_path / "asked",
        "version: 1\ntitle: asked\nplugins:\n  probe: {enabled: true, colour: blue}\n",
    )
    (added,) = plugins.project_sources(on)
    assert (added.role, added.mount) == (DRAFT_ROLE, "probe")
    assert ("sources", {"colour": "blue"}) in probe.calls


def test_the_more_specific_level_turns_a_plugin_off(
    tmp_path: Path, user_dirs: Path, probe: _Probe
):
    project = _registered_project(
        tmp_path / "repo",
        "version: 1\ntitle: r\nplugins:\n  probe: {enabled: true}\n"
        "projects:\n  - path: a\n    plugins:\n      probe: {enabled: false}\n",
    )
    assert plugins.enabled_for(project).keys() == set()
    assert plugins.project_sources(project) == ()


def test_the_three_hooks_without_a_project_follow_the_installation_level(
    tmp_path: Path, user_dirs: Path, probe: _Probe
):
    _user_config({"version": 1, "plugins": {"probe": {"enabled": True}}})
    assert gitignore.required_patterns() == ("probe-link", "docstrap-build/")
    assert ("probe", tmp_path / "probe-store") in plugins.init()
    assert Finding(ok=False, message=f"probe looked at {tmp_path}") in plugins.doctor_report(
        tmp_path
    )

    _user_config({"version": 1, "plugins": {"probe": {"enabled": False}}})
    assert gitignore.required_patterns() == ("docstrap-build/",)
    assert plugins.init() == []
    assert plugins.doctor_report(tmp_path) == []


def test_init_and_doctor_print_what_the_plugins_say(
    tmp_path: Path, user_dirs: Path, probe: _Probe
):
    _user_config({"version": 1, "plugins": {"probe": {"enabled": True}}})
    init = runner.invoke(docstrap_app, ["init", "--no-install-skills"])
    assert init.exit_code == 0, init.output
    assert f"probe:           {tmp_path / 'probe-store'}" in init.output
    assert "promdance:" not in init.output

    doctor = runner.invoke(docstrap_app, ["doctor", "--root", str(tmp_path)])
    assert doctor.exit_code == 0, doctor.output
    assert f"✗  probe looked at {tmp_path.resolve()}" in doctor.output


# --- 3. the draft root --------------------------------------------------------------------


def test_a_plugins_draft_root_comes_first(tmp_path: Path, user_dirs: Path, probe: _Probe):
    _registered_project(
        tmp_path / "repo",
        "version: 1\ntitle: r\nplugins:\n  probe: {enabled: true}\n"
        "sources:\n  - {path: docs, role: documentation}\n  - {path: mine, role: draft}\n",
    )
    (tmp_path / "repo" / "mine").mkdir()
    assert drafts.draft_root("r") == tmp_path / "probe-store" / "r"
    assert answers.store_path("r") == tmp_path / "probe-store" / "r" / "answers.md"


def test_with_no_plugin_the_declared_draft_source_is_the_draft_root(
    tmp_path: Path, user_dirs: Path
):
    _registered_project(
        tmp_path / "repo",
        "version: 1\ntitle: r\n"
        "sources:\n  - {path: docs, role: documentation}\n  - {path: mine, role: draft}\n",
    )
    (tmp_path / "repo" / "mine").mkdir()
    assert drafts.draft_root("r") == (tmp_path / "repo" / "mine").resolve()


def test_with_neither_there_is_no_draft_root_and_a_writer_says_so(
    tmp_path: Path, user_dirs: Path
):
    """Nothing invents a directory: not the store, not a declared folder."""
    _registered_project(
        tmp_path / "repo",
        "version: 1\ntitle: r\n"
        "sources:\n  - {path: docs, role: documentation}\n  - {path: mine, role: draft}\n",
    )
    assert drafts.draft_root("r") is None
    assert not (tmp_path / "repo" / "mine").exists()
    assert answers.read("r") == []
    with pytest.raises(answers.AnswerStoreError, match="no draft root"):
        answers.store_path("r")


# --- 4. draft sources as a concept ----------------------------------------------------------


DRAFT_ANSWERS = """\
---
docstrap_answers:
  - key: "01ABC:Q1"
    doc_id: "01ABC"
    label: "Q1"
    document: "spec"
    answered_at: "2026-10-01T00:00:00+00:00"
    submitted: false
    draft: "A DRAFT NOBODY SUBMITTED"
---
"""


def test_a_declared_draft_source_publishes_its_answer_store_without_drafts(
    tmp_path: Path, user_dirs: Path
):
    """`answer_drafts` reads the draft source's mount, not a fixed name."""
    project = _registered_project(
        tmp_path / "repo",
        "version: 1\ntitle: r\n"
        "sources:\n  - {path: docs, role: documentation}\n"
        "  - {path: thinking, role: draft, mount: ideas}\n",
    )
    _write(tmp_path / "repo" / "docs" / "spec.md", "# Spec\n")
    _write(tmp_path / "repo" / "thinking" / "answers.md", DRAFT_ANSWERS)

    result = markdown.build(project, tmp_path / "out")

    conf = (tmp_path / "out" / "_scratch" / project.slug / "conf.py").read_text(encoding="utf-8")
    assert "docstrap_draft_mount = 'ideas'" in conf
    page = (result.html_root / "ideas" / "answers.html").read_text(encoding="utf-8")
    assert "A DRAFT NOBODY SUBMITTED" not in page
