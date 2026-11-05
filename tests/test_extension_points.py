"""Adding a tool goes through the named extension points, or the design failed.

The weak version of this test would check that adding a tool touches no
file outside its own directory. That is circumventable — a tool could
satisfy it by reaching into another module at runtime, which is worse
than an honest edit. So the test is about the API instead.

A whole new tool is built here from nothing: a package on ``sys.path``
with a declaration, a routes module, and a static bundle. It is then run
through every consumer — discovery, the server, the launcher, the
Sphinx asset registration — using only the documented extension points.
No docstrap module is patched, subclassed, or reached into. If a
consumer needed a special case for it, one of these would fail.

The extension points exercised:

1. ``ToolDeclaration``                         — the declaration itself
2. ``registry.discover_in``                    — registration by directory
3. ``routes.register(app, declaration)``       — the server seam
4. ``tool_support.register_tool_assets``       — the build seam
5. ``launcher.offers_for`` / ``offer_payload`` — the launcher seam
6. ``declaration.visibility_class``            — the CSS visibility seam
"""
from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pytest

from docstrap.sphinx import tool_support
from docstrap.tools import mounting, registry
from docstrap.tools.declaration import Kind, Target
from docstrap.tools.launcher import PageContext, offer_payload, offers_for

PACKAGE = "exttools"
TOOL = "glossary"

DECLARATION_SRC = f'''\
"""Declaration: a tool that did not exist when the seams were written."""
from docstrap.tools.declaration import Kind, Target, ToolDeclaration

DECLARATION = ToolDeclaration(
    id="{TOOL}",
    title="Glossary",
    kind=Kind.INSTRUMENT,
    target=Target.PROJECT,
    entry="{PACKAGE}.{TOOL}",
    api_collection="glossaries",
    default_visible=False,
    summary="Collect the terms this project defines.",
)
'''

ROUTES_SRC = '''\
"""The new tool's server routes — the same seam the real tools use."""
from docstrap.tools.declaration import ToolDeclaration


def register(app, declaration: ToolDeclaration) -> tuple[str, ...]:
    path = declaration.route_prefix

    @app.post(path)
    def collect(project: str) -> dict:
        return {"project": project}

    return (path,)
'''

INIT_SRC = f'''\
"""The new tool's Sphinx entry point."""
from docstrap.sphinx.tool_support import register_tool_assets
from {PACKAGE}.{TOOL}.declaration import DECLARATION


def setup(app):
    register_tool_assets(app, DECLARATION)
    return {{"version": "0.1.0"}}
'''


class FakeSphinxApp:
    """The surface a tool's setup() is allowed to touch, and no more."""

    def __init__(self) -> None:
        self.config = type("Config", (), {"html_static_path": []})()
        self.js_files: list[str] = []
        self.js_attributes: dict[str, dict[str, str]] = {}
        self.css_files: list[str] = []
        self.config_values: dict[str, object] = {}

    def add_js_file(self, name: str, **attributes: str) -> None:
        self.js_files.append(name)
        self.js_attributes[name] = attributes

    def add_css_file(self, name: str) -> None:
        self.css_files.append(name)

    def add_config_value(self, name: str, default: object, rebuild: str) -> None:
        self.config_values[name] = default


@pytest.fixture
def foreign_tool(tmp_path: Path):
    """A tool package built from scratch, outside docstrap entirely."""
    root = tmp_path / PACKAGE
    tool_dir = root / TOOL
    (tool_dir / "static").mkdir(parents=True)
    (root / "__init__.py").write_text("", encoding="utf-8")
    (tool_dir / "__init__.py").write_text(INIT_SRC, encoding="utf-8")
    (tool_dir / "declaration.py").write_text(DECLARATION_SRC, encoding="utf-8")
    (tool_dir / "routes.py").write_text(ROUTES_SRC, encoding="utf-8")
    (tool_dir / "static" / f"docstrap-{TOOL}.js").write_text(
        textwrap.dedent(
            f"""\
            (function () {{
              var d = window.docstrap;
              d.tools.register('{TOOL}', {{ show: function () {{}}, hide: function () {{}} }});
            }})();
            """
        ),
        encoding="utf-8",
    )
    (tool_dir / "static" / f"docstrap-{TOOL}.css").write_text(
        f"body.docstrap-show-{TOOL} .glossary {{ display: block; }}\n",
        encoding="utf-8",
    )

    sys.path.insert(0, str(tmp_path))
    try:
        yield root
    finally:
        sys.path.remove(str(tmp_path))
        for name in list(sys.modules):
            if name == PACKAGE or name.startswith(PACKAGE + "."):
                del sys.modules[name]


@pytest.fixture
def declaration(foreign_tool: Path):
    found = registry.discover_in(PACKAGE, foreign_tool)
    assert len(found) == 1, "the directory alone should have registered it"
    return found[0]


# --- 1 & 2: it registers by existing -----------------------------------------


def test_a_directory_with_a_declaration_is_a_tool(declaration):
    assert declaration.id == TOOL
    assert declaration.kind is Kind.INSTRUMENT
    assert declaration.target is Target.PROJECT


def test_discovery_needs_no_edit_to_a_list(foreign_tool: Path):
    """Nothing was appended anywhere; the package was merely laid out."""
    assert registry.discover_in(PACKAGE, foreign_tool)


# --- 3: the server seam ------------------------------------------------------


def test_the_new_tool_mounts_through_the_route_seam(declaration):
    from fastapi import FastAPI

    app = FastAPI()
    mounted = mounting.mount_all(app, [declaration])
    # Its target chose the base; its declared collection named the leaf.
    assert mounted == ("/api/tools/{project}/glossaries",)
    assert declaration.route_prefix in {
        getattr(route, "path", None) for route in app.routes
    }


def test_the_server_needed_no_change_to_serve_it(declaration):
    """The prefix falls out of the declaration, as it does for the real tools."""
    assert mounting.declared_route_prefixes()  # the real ones still resolve
    assert declaration.route_prefix == "/api/tools/{project}/glossaries"


# --- 4: the build seam -------------------------------------------------------


def test_the_new_tools_assets_register_under_its_declared_names(declaration):
    import importlib

    app = FakeSphinxApp()
    module = importlib.import_module(declaration.entry)
    module.setup(app)

    assert declaration.js_bundle in app.js_files
    assert declaration.css_bundle in app.css_files
    assert str(registry.static_directory(declaration)) in app.config.html_static_path
    # The shared bundle came along without the tool asking for it.
    assert "docstrap-common.js" in app.js_files
    # Both are held back until the page is inside the viewer.
    for name in (declaration.js_bundle, "docstrap-common.js"):
        assert app.js_attributes[name] == {"type": tool_support.DEFERRED_SCRIPT_TYPE}
    # As did the project-slug config value every tool addresses by.
    assert tool_support.PROJECT_SLUG_CONFIG in app.config_values


# --- 5: the launcher seam ----------------------------------------------------


def test_the_launcher_offers_it_where_its_target_is_satisfied(declaration):
    on_a_project = PageContext(project="Docs", doc_slug="index")
    assert declaration in offers_for(on_a_project, [declaration])


def test_the_launcher_withholds_it_where_its_target_is_not(declaration):
    lone_page = PageContext(project=None, doc_slug="index")
    assert offers_for(lone_page, [declaration]) == ()


def test_the_client_payload_needs_no_new_field(declaration):
    """It is described entirely by fields the existing tools also use."""
    payload = offer_payload(declaration, PageContext(project="Docs"))
    assert payload["kind"] == "instrument"
    assert payload["route"] == "/api/tools/Docs/glossaries"
    assert payload["visibilityClass"] == f"docstrap-show-{TOOL}"


# --- 6: no special cases in the shared code ----------------------------------

SHARED_MODULES = [
    "docstrap/server.py",
    "docstrap/sphinx/tool_support.py",
    "docstrap/sphinx/launcher.py",
    "docstrap/sphinx/viewer_button.py",
    "docstrap/tools/registry.py",
    "docstrap/tools/mounting.py",
    "docstrap/tools/launcher.py",
    "docstrap/tools/declaration.py",
    "docstrap/layouts/markdown.py",
]


@pytest.mark.parametrize("relative", SHARED_MODULES)
def test_no_shared_module_imports_a_specific_tool(relative: str):
    """A shared module that knows a tool's name has a special case in it."""
    source_root = Path(registry.__file__).parent.parent.parent
    text = (source_root / relative).read_text(encoding="utf-8")
    for declaration in registry.iter_declarations():
        assert declaration.entry not in text, f"{relative} names {declaration.id}"


SHARED_CLIENT_ASSETS = [
    "docstrap/sphinx/static/docstrap-common.js",
    "docstrap/sphinx/static/docstrap-launcher.js",
    "docstrap/sphinx/static/docstrap-viewer-button.js",
    "docstrap/sphinx/static/docstrap.css",
]


@pytest.mark.parametrize("relative", SHARED_CLIENT_ASSETS)
def test_no_shared_client_asset_names_a_specific_tool(relative: str):
    """The launcher renders offers; it does not know what it is rendering."""
    source_root = Path(registry.__file__).parent.parent.parent
    text = (source_root / relative).read_text(encoding="utf-8")
    for declaration in registry.iter_declarations():
        for literal in (f"'{declaration.id}'", f'"{declaration.id}"'):
            assert literal not in text, f"{relative} names {declaration.id}"
