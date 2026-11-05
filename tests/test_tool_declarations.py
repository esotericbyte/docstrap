"""The declaration is read once and drives all three consumers.

The point of the declaration object is that the server, the launcher and
the build all read the same small statement and none of them keeps a
second copy of what it says. These tests hold each consumer against the
declarations rather than against a literal, so a consumer that grew its
own copy would disagree and fail.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from docstrap.tools import mounting, registry
from docstrap.tools.declaration import (
    DeclarationError,
    Kind,
    RouteCollisionError,
    Target,
    ToolDeclaration,
    as_declared_path,
    as_server_path,
    check_route_separation,
)
from docstrap.tools.launcher import PageContext, offers_for

# The three tools this refactor moved. Named here because the test is
# about them specifically; nothing in src/ names them.
MOVED_TOOLS = {"status", "review", "qa"}


def test_the_three_tools_are_discovered_not_registered():
    """No registration list — the directories are the registration."""
    found = {d.id for d in registry.iter_declarations()}
    assert MOVED_TOOLS <= found


@pytest.mark.parametrize("tool_id", sorted(MOVED_TOOLS))
def test_each_tool_owns_a_directory(tool_id: str):
    """One directory per tool, holding everything that belongs to it."""
    declaration = registry.get(tool_id)
    directory = registry.tool_directory(declaration)
    assert directory.is_dir()
    assert (directory / "declaration.py").is_file()
    assert (directory / "__init__.py").is_file()
    assert (directory / "static").is_dir()


# --- consumer 1: the server derives the route prefix ------------------------


def test_server_route_table_equals_what_the_declarations_derive():
    """The server holds no path of its own; it mounts what is declared.

    Equality, not containment. A tool that hangs a sub-path off its own
    prefix is not merely untidy: a project-targeted prefix plus a segment
    has exactly the shape of a document-targeted prefix, so
    `/api/tools/{project}/qa/answers` is captured by the qa tool's
    `/api/tools/{project}/{doc_slug}/answers`. Keeping every tool on
    the path its declaration derived is what rules that out, and a tool
    needing two operations distinguishes them by method.

    Compared in the ROUTER's spelling, which is the one a mounted path
    actually reads. The declaration's own spelling is what the launcher
    fills in for the browser; `as_server_path` is the single translation
    between them, so this is still one shape written down once.
    """
    from docstrap.server import make_app

    app = make_app(Path("/nonexistent-site-root"))
    mounted = sorted(
        {
            route.path
            for route in app.routes
            if getattr(route, "path", "").startswith("/api/tools")
        }
    )
    declared = sorted(
        {
            prefix
            for prefixes in mounting.declared_server_route_prefixes().values()
            for prefix in prefixes
        }
    )
    assert mounted == declared
    assert declared, "at least one tool should own an API"


# --- the document parameter carries a path, and the scopes stay apart -------


def test_the_document_parameter_spans_separators_on_the_server():
    """A document's identity is a path, so the route carries a path.

    The declaration's spelling and the router's differ in exactly this
    one place, which is what `as_server_path` exists to say.
    """
    qa = registry.get("qa")
    assert qa.route_prefix == "/api/tools/{project}/{doc_slug}/answers"
    assert qa.server_route_prefix == "/api/tools/{project}/{doc_slug:path}/answers"
    assert as_server_path(qa.route_prefix) == qa.server_route_prefix
    assert as_declared_path(qa.server_route_prefix) == qa.route_prefix


def test_every_declared_route_is_a_base_plus_one_static_collection():
    """The condition the two scopes stay separable under.

    `check_route_separation` is run at mount time; this is the same
    statement held against the declarations rather than against a
    started server, so a new tool breaking it fails here first.
    """
    check_route_separation(
        prefix
        for prefixes in mounting.declared_server_route_prefixes().values()
        for prefix in prefixes
    )


def test_a_sub_path_under_the_project_base_is_refused():
    """The collision the greedy document parameter would otherwise allow.

    `…/{project}/qa/answers` and `…/{project}/{doc_slug:path}/answers`
    with `doc_slug` equal to `qa` are the same URL. Before the parameter
    carried a path this was an argument from segment counts; now it is
    checked, and a tool that declared its way into it cannot start.
    """
    with pytest.raises(RouteCollisionError):
        check_route_separation(["/api/tools/{project}/qa/answers"])
    with pytest.raises(RouteCollisionError):
        check_route_separation(["/api/tools/{project}/{doc_slug}/a/b"])
    with pytest.raises(RouteCollisionError):
        check_route_separation(["/api/elsewhere/{project}/answers"])


def test_mounting_refuses_a_tool_that_breaks_the_separation(monkeypatch):
    """The guard runs where it matters: at mount, not only in a test."""
    from fastapi import FastAPI

    bad = ToolDeclaration(
        id="deep",
        title="Deep",
        kind=Kind.TOOL,
        target=Target.PROJECT,
        entry="fake.deep",
        api_collection="things",
    )

    class _Module:
        @staticmethod
        def register(app, declaration):
            # A tool writing its own sub-path down — the thing the
            # declaration's derived prefixes exist to prevent. It is a
            # legal FastAPI route and a broken route table.
            path = f"{declaration.route_prefix}/extra"

            @app.get(path)
            def handler(project: str) -> dict:  # pragma: no cover
                return {}

            return (path,)

    monkeypatch.setattr(mounting, "_routes_module", lambda d: _Module)
    with pytest.raises(RouteCollisionError):
        mounting.mount_all(FastAPI(), [bad])


def test_route_prefix_is_derived_from_target_and_collection():
    qa = registry.get("qa")
    review = registry.get("review")
    assert qa.route_prefix == "/api/tools/{project}/{doc_slug}/answers"
    assert review.route_prefix == "/api/tools/{project}/{doc_slug}/reviews"
    # Same target, so the same base; only the declared collection differs.
    assert qa.route_prefix.rsplit("/", 1)[0] == review.route_prefix.rsplit("/", 1)[0]


def test_a_tool_owning_no_collection_mounts_nothing():
    """The badge reads the shared documents API, so it declares no prefix."""
    status = registry.get("status")
    assert status.api_collection is None
    assert status.route_prefix is None
    assert "status" not in mounting.declared_route_prefixes()


def test_project_target_derives_a_shorter_prefix():
    """The target picks the base — this is the rule, not a per-tool case."""
    project_tool = ToolDeclaration(
        id="sweep",
        title="Sweep",
        kind=Kind.INSTRUMENT,
        target=Target.PROJECT,
        entry="somewhere.sweep",
        api_collection="findings",
    )
    assert project_tool.route_prefix == "/api/tools/{project}/findings"


def test_a_second_scope_is_declared_and_derived_like_the_first():
    """The qapanels instrument reads at two scopes, both from the base map.

    A tool that mounted an
    undeclared second path would slip past
    `test_server_route_table_equals_what_the_declarations_derive`, which
    is why the second scope is a declaration field rather than something
    the routes module decides.
    """
    panels = registry.get("qapanels")
    assert panels.target is Target.PROJECT
    assert panels.also_scoped_to is Target.DOCUMENT
    assert panels.route_prefixes == (
        "/api/tools/{project}/qa",
        "/api/tools/{project}/{doc_slug}/qa",
    )
    # Its own target first, and neither shape can capture the other:
    # they differ in segment count.
    project_prefix, document_prefix = panels.route_prefixes
    assert project_prefix == panels.route_prefix
    assert document_prefix.count("/") == project_prefix.count("/") + 1


def test_a_second_scope_needs_a_collection_and_must_differ():
    with pytest.raises(DeclarationError):
        ToolDeclaration(
            id="nocollection",
            title="No collection",
            kind=Kind.TOOL,
            target=Target.PROJECT,
            entry="somewhere.nocollection",
            also_scoped_to=Target.DOCUMENT,
        )
    with pytest.raises(DeclarationError):
        ToolDeclaration(
            id="samescope",
            title="Same scope",
            kind=Kind.TOOL,
            target=Target.PROJECT,
            entry="somewhere.samescope",
            api_collection="things",
            also_scoped_to=Target.PROJECT,
        )


# --- consumer 2: the launcher reads kind and target -------------------------


def test_every_moved_tool_is_offered_on_a_document_page():
    context = PageContext(project="Docs", doc_slug="notes/a")
    offered = {d.id for d in offers_for(context)}
    assert MOVED_TOOLS <= offered


def test_nothing_is_offered_without_a_workpiece():
    assert offers_for(PageContext()) == ()


# --- consumer 3: the build names the bundles --------------------------------


@pytest.mark.parametrize("tool_id", sorted(MOVED_TOOLS))
def test_bundle_names_come_from_the_declaration(tool_id: str):
    """The file on disk is the name the declaration derives, not a literal."""
    declaration = registry.get(tool_id)
    static = registry.static_directory(declaration)
    assert declaration.js_bundle == f"docstrap-{tool_id}.js"
    assert (static / declaration.js_bundle).is_file()
    assert (static / declaration.css_bundle).is_file()


@pytest.mark.parametrize("tool_id", sorted(MOVED_TOOLS))
def test_the_frontend_build_is_told_where_to_write_by_the_declaration(tool_id: str):
    """`build-tools.mjs` spells no tool id and no filename; this is why.

    The manifest is derived: the tool's directory locates the source and
    the output, and the declaration names both bundles. A Node build
    that had grown its own copy of either would disagree with this.
    """
    from docstrap.tools import frontend

    declaration = registry.get(tool_id)
    directory = registry.tool_directory(declaration)
    targets = {entry["id"]: entry for entry in frontend.build_targets()}

    assert tool_id in targets, "a converted tool must have ui/index.ts"
    target = targets[tool_id]
    assert target["entry"] == str(directory / "ui" / "index.ts")
    assert target["outDir"] == str(directory / "static")
    assert target["jsBundle"] == declaration.js_bundle
    assert target["cssBundle"] == declaration.css_bundle


def test_a_tool_with_no_ui_directory_is_simply_not_built():
    """Hand-written client source stays legitimate for a tiny tool."""
    from docstrap.tools import frontend

    built = {entry["id"] for entry in frontend.build_targets()}
    declared = {d.id for d in registry.iter_declarations()}
    assert built <= declared


def test_bundle_names_cannot_collide():
    """Unique ids, so unique bundles — Sphinx flattens every static dir."""
    bundles = [d.js_bundle for d in registry.iter_declarations()]
    assert len(bundles) == len(set(bundles))


def test_generated_extensions_list_comes_from_declarations():
    from docstrap.layouts.markdown import conf_extensions

    extensions = conf_extensions()
    for declaration in registry.iter_declarations():
        assert declaration.entry in extensions
    # The launcher follows the tools so they have registered assets
    # before it, and the viewer button follows everything, because it is
    # what runs every script registered before it inside the viewer.
    assert extensions[-2:] == ["docstrap.sphinx.launcher", "docstrap.sphinx.viewer_button"]
    tools = [d.entry for d in registry.iter_declarations()]
    assert max(extensions.index(entry) for entry in tools) < len(extensions) - 2


# --- the declaration rejects what it cannot honour --------------------------


def test_declaration_rejects_a_bad_id():
    with pytest.raises(DeclarationError):
        ToolDeclaration(
            id="Not An Id",
            title="x",
            kind=Kind.TOOL,
            target=Target.DOCUMENT,
            entry="a.b",
        )


def test_declaration_rejects_a_missing_entry_point():
    with pytest.raises(DeclarationError):
        ToolDeclaration(
            id="ok",
            title="x",
            kind=Kind.TOOL,
            target=Target.DOCUMENT,
            entry="",
        )
