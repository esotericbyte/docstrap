"""The viewer shell: what a build publishes for it, and what it may not break.

The shell is a page of its own beside a built site, told
what the site contains by ``_viewer/manifest.json``. Three things are
held here because a browser is not a test dependency:

1. **The manifest is the site.** Every page the build published is in it
   and nothing it lists is missing — a navigator that covered only the
   pages near the one in front of you would be a different, worse thing.
2. **Its question routes are the pages' own.** The shell hands the
   hosted panels routes from the manifest, so they must be byte-for-byte
   what each document's page carries, or the drawer would read something
   the page itself would not.
3. **The shell's styling cannot reach what it hosts, and the overlay's
   scroll lock cannot reach a frame.** Both were real defects, found by
   looking at the shell in a browser on 2026-10-04.
4. **The site leads into the shell.** The root page links to the viewer
   entrance, which asks the shell for that same root page.
5. **Every page leads into the shell, and nothing heavier.** A page
   opened on its own runs one small script, which draws a button into
   the shell showing that same page; the tools it carries run only once
   it is inside the shell, where the button is never drawn.
6. **The navigator is a drawer you can widen.** Its
   widths, what is remembered and what its tab does run under Node in
   ``tests/viewer/navigatorPane.test.ts``; the shell's wiring of them to
   Zag's splitter is held here. The dragging was seen in a browser.
7. **A navigator title wraps; it is never cut short.**
   The rows and the halved indent are held here against the source and
   the committed stylesheet. The wrapping was seen in a browser at the
   drawer's opening width.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from docstrap import build, fileindex
from docstrap.config import load
from docstrap.tools import frontend
from docstrap.viewer import manifest as viewer

PROJECT_PATH = "packages/widget"
PROJECT_SLUG = "packages__widget"

DOCSTRAP_YAML = f"""\
version: 1
title: Sample Store
projects:
  - path: {PROJECT_PATH}
    title: Widget
    layout: markdown
    docs_root: docs
"""

# Nested on purpose: a flat sample proves the 3 % case.
TREE = {
    f"{PROJECT_PATH}/docs/guide.md": "# Guide\n\nTop level.\n\n## Open questions\n\n**Q1.** Is it?\n",
    f"{PROJECT_PATH}/docs/specs/census.md": "# Census\n\nA spec.\n",
    f"{PROJECT_PATH}/docs/plans/rollout/phase.md": "# Phase (one)\n\nNested deeper.\n",
}

QAPANELS_UI = Path(viewer.__file__).parent.parent / "tools" / "qapanels" / "ui"

#: The pages Sphinx writes beside the documents, which are not documents.
SPHINX_PAGES = {"genindex.html", "search.html"}


def _store(root: Path) -> Path:
    store = root / "store"
    for relative, content in TREE.items():
        path = store / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    (store / ".docstrap").write_text(DOCSTRAP_YAML, encoding="utf-8")
    return store


def _redirect_home(monkeypatch: pytest.MonkeyPatch, home: Path) -> None:
    """The `user_dirs` fixture, for a module-scoped build."""
    for variable, name in (
        ("XDG_DATA_HOME", "share"),
        ("XDG_CONFIG_HOME", "config"),
        ("XDG_CACHE_HOME", "cache"),
        ("XDG_STATE_HOME", "state"),
    ):
        directory = home / ".local" / name
        directory.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv(variable, str(directory))
    monkeypatch.setenv("HOME", str(home))


@pytest.fixture(scope="module")
def site(tmp_path_factory: pytest.TempPathFactory):
    """One single-store build, shared: building is the slow part."""
    root = tmp_path_factory.mktemp("viewer")
    with pytest.MonkeyPatch.context() as monkeypatch:
        _redirect_home(monkeypatch, root / "home")
        store = _store(root)
        out = root / "site"
        build.build_all(load(store / ".docstrap"), out)
        entries = fileindex.list_project(PROJECT_SLUG)
        model = json.loads((out / viewer.MANIFEST_PATH).read_text(encoding="utf-8"))
        yield out, model, entries


def _project(model: dict) -> dict:
    [store] = model["stores"]
    [project] = store["projects"]
    return project


def _published_pages(site_root: Path, project_base: str) -> set[str]:
    root = site_root / project_base
    return {
        f"{project_base}{path.relative_to(root).as_posix()}"
        for path in root.rglob("*.html")
        if not any(part.startswith("_") for part in path.relative_to(root).parts)
        and path.name not in SPHINX_PAGES
    }


def _doc_url(address: str) -> tuple[str, str]:
    """An address into the shell, split into its page and the page asked for."""
    from urllib.parse import parse_qs, urlsplit

    parts = urlsplit(address)
    [asked] = parse_qs(parts.query)[viewer.DOC_URL_PARAM]
    return parts.path, asked


def _unquote(url: str) -> str:
    from urllib.parse import unquote

    return unquote(url)


# --- 1. the manifest is the site ---------------------------------------------


def test_the_manifest_lists_every_page_the_build_published(site):
    """Both directions: nothing published is missing, nothing listed is absent."""
    out, model, _entries = site
    project = _project(model)
    listed = {_unquote(doc["url"]) for doc in project["documents"]}
    assert listed == _published_pages(out, project["base"])
    for doc in project["documents"]:
        assert (out / _unquote(doc["url"])).is_file(), doc["url"]


def test_the_manifest_is_the_file_index_and_nothing_else(site):
    """The navigator's tree is the build's own index, entry for entry."""
    _out, model, entries = site
    project = _project(model)
    assert [
        (doc["docname"], doc["parent"], doc["kind"]) for doc in project["documents"]
    ] == [(e.docname, e.parent_docname, e.kind) for e in entries]
    assert {doc["docname"] for doc in project["documents"]} >= {
        "guide",
        "specs/census",
        "plans/rollout/phase",
    }


def test_store_and_project_landings_are_real_pages(site):
    out, model, _entries = site
    [store] = model["stores"]
    assert store["landing"] == "index.html"
    assert (out / store["landing"]).is_file()
    project = _project(model)
    assert project["base"] == f"{PROJECT_SLUG}/"
    assert project["title"] == "Widget"
    assert (out / project["landing"]).is_file()


# --- 2. the routes are the pages' own ----------------------------------------


def _page_offer(page: Path, tool_id: str) -> dict | None:
    html = page.read_text(encoding="utf-8")
    match = re.search(
        r'<script[^>]*id="docstrap-tool-offers"[^>]*>(.*?)</script>', html, re.S
    )
    assert match, f"{page} carries no offers"
    for offer in json.loads(match.group(1)):
        if offer["id"] == tool_id:
            return offer
    return None


def test_question_routes_are_what_each_page_carries(site):
    """Resolved by Python, once, with the same context the page got."""
    out, model, _entries = site
    documents = [d for d in _project(model)["documents"] if d["kind"] == "document"]
    assert documents
    for doc in documents:
        page_offer = _page_offer(out / _unquote(doc["url"]), "qapanels")
        assert doc["questions"] == page_offer, doc["docname"]
        # Nested documents keep their separators: the defect of 2026-09-23.
        if "/" in doc["docname"]:
            assert "%2F" not in doc["questions"]["altRoute"]


def test_a_section_page_offers_nothing_to_pin(site):
    _out, model, _entries = site
    sections = [d for d in _project(model)["documents"] if d["kind"] == "section"]
    assert sections
    assert all(d["questions"] is None for d in sections)


# --- the shell itself ----------------------------------------------------------


def test_the_shell_is_published_at_the_site_root(site):
    out, _model, _entries = site
    page = out / viewer.SHELL_PAGE
    assert page.is_file()
    html = page.read_text(encoding="utf-8")
    referenced = re.findall(r'(?:src|href)="\./([^"]+)"', html)
    assert referenced, "the shell page references none of its assets"
    for relative in referenced:
        assert (out / relative).is_file(), relative
    shipped = {p.name for p in (viewer.STATIC_DIR / viewer.ASSET_DIR).iterdir()}
    published = {p.name for p in (out / viewer.ASSET_DIR).iterdir()}
    assert published == shipped | {Path(viewer.MANIFEST_PATH).name}


def test_the_frontend_build_writes_where_publish_reads():
    """One set of names, read by both sides of the build."""
    target = frontend.shell_target()
    assert target["outDir"] == str(viewer.STATIC_DIR)
    assert target["root"] == str(viewer.UI_DIR)
    assert target["page"] == viewer.SHELL_PAGE
    assert target["assetsDir"] == viewer.ASSET_DIR
    assert (viewer.UI_DIR / viewer.SHELL_PAGE).is_file()


def test_the_shell_is_not_a_tool():
    """No declaration: it would put Skeleton on every documentation page."""
    built = {entry["id"] for entry in frontend.build_targets()}
    assert frontend.shell_target()["id"] not in built


def test_a_multi_store_build_publishes_one_shell_at_the_top(tmp_path: Path, user_dirs: Path):
    store = _store(tmp_path)
    out = tmp_path / "site"
    build.build_stores([store / ".docstrap"], out)
    model = json.loads((out / viewer.MANIFEST_PATH).read_text(encoding="utf-8"))
    [entry] = model["stores"]
    prefix = entry["landing"].rsplit("/", 1)[0] + "/"
    assert (out / entry["landing"]).is_file()
    [project] = entry["projects"]
    assert project["base"] == f"{prefix}{PROJECT_SLUG}/"
    assert _published_pages(out, project["base"]) == {
        _unquote(doc["url"]) for doc in project["documents"]
    }
    assert (out / viewer.SHELL_PAGE).is_file()
    assert not (out / prefix / viewer.SHELL_PAGE).exists(), "one shell, at the top"
    # The super-aggregate is the root page and leads in; the store's own
    # landing page has no shell beside it, so it must not.
    assert _entrance_links(out / viewer.ROOT_PAGE) == [viewer.ENTRANCE]
    assert _entrance_links(out / entry["landing"]) == []
    # Every page, at every depth, leads to the one shell at the top.
    pages = [viewer.ROOT_PAGE, entry["landing"], project["landing"]]
    pages += [_unquote(doc["url"]) for doc in project["documents"]]
    for relative in pages:
        assert _opens_itself(out, relative), relative


# --- 3. nothing reaches what the shell hosts, or what it frames -------------


def _hosted_class_names() -> set[str]:
    names: set[str] = set()
    for source in QAPANELS_UI.glob("*.svelte"):
        text = source.read_text(encoding="utf-8")
        for match in re.finditer(r'class="([^"{]*)"', text):
            names.update(match.group(1).split())
        names.update(re.findall(r"class:([\w-]+)", text))
    return names


def test_no_unscoped_shell_rule_names_a_class_the_hosted_panels_use():
    """Skeleton's global `label` utility once hid every question's text.

    Svelte scopes the panels' own rules, so a rule carrying a `svelte-`
    hash is theirs. Any other rule in the shell's stylesheet that names
    one of their classes lands on them.
    """
    [stylesheet] = (viewer.STATIC_DIR / viewer.ASSET_DIR).glob("*.css")
    css = stylesheet.read_text(encoding="utf-8")
    names = _hosted_class_names()
    assert "label" in names, "the check has lost track of the panels' classes"
    offenders = []
    for selectors in re.findall(r"([^{}]+)\{", css):
        for selector in selectors.split(","):
            selector = selector.strip()
            if selector.startswith("@") or "svelte-" in selector:
                continue
            for name in names:
                if re.search(r"\." + re.escape(name) + r"(?![\w-])", selector):
                    offenders.append((name, selector))
    assert offenders == []


def test_the_overlay_locks_only_a_page_that_holds_it():
    """A framed page shares remembered visibility but never the panels.

    Keyed on the body class alone, the lock froze the reference panel's
    page — the "bottom section has no scroll bar" of 2026-10-04 — and
    would freeze every page the shell frames.
    """
    for css in (
        (QAPANELS_UI / "qapanels.css").read_text(encoding="utf-8"),
        (QAPANELS_UI.parent / "static" / "docstrap-qapanels.css").read_text(encoding="utf-8"),
    ):
        locks = re.findall(r"(body\.docstrap-show-qapanels[^{]*)\{\s*overflow:\s*hidden", css)
        assert locks, "the overlay no longer locks the page behind it"
        for selector in locks:
            assert ":has(> .docstrap-qapanels-root)" in selector, selector


# --- 4. the site leads into the shell -----------------------------------------


def _entrance_links(page: Path) -> list[str]:
    html = page.read_text(encoding="utf-8")
    return re.findall(
        r'<p class="' + re.escape(viewer.ENTRANCE_CLASS) + r'[^"]*"><a href="([^"]+)" target="_top">',
        html,
    )


def test_the_entrance_asks_the_shell_for_the_root_page(site):
    """The shell reads `?doc-url=` as the page to show; the entrance names the root."""
    out, model, _entries = site
    page, wanted = _doc_url(viewer.ENTRANCE)
    assert page == viewer.SHELL_PAGE
    assert wanted == model["landing"] == viewer.ROOT_PAGE
    assert (out / page).is_file()
    assert (out / wanted).is_file()


def test_the_root_page_leads_into_the_viewer(site):
    out, _model, _entries = site
    assert _entrance_links(out / viewer.ROOT_PAGE) == [viewer.ENTRANCE]


def test_no_project_page_carries_the_entrance(site):
    """Only the root page has the shell beside it."""
    out, model, _entries = site
    for doc in _project(model)["documents"]:
        assert _entrance_links(out / _unquote(doc["url"])) == [], doc["docname"]


def test_the_shell_hides_the_entrance_by_the_class_python_writes():
    """Inside the shell's frame the link would nest a viewer in the viewer."""
    rule = "." + viewer.ENTRANCE_CLASS + " {"
    assert rule in (viewer.UI_DIR / "DocumentView.svelte").read_text(encoding="utf-8")
    [bundle] = (viewer.STATIC_DIR / viewer.ASSET_DIR).glob("*.js")
    assert rule in bundle.read_text(encoding="utf-8"), "the committed build is stale"


# --- 5. every page leads into the shell, and runs nothing heavier ------------

STATIC = Path(viewer.__file__).parent.parent / "sphinx" / "static"
BUTTON_JS = STATIC / "docstrap-viewer-button.js"
BUTTON_CSS = STATIC / "docstrap-viewer-button.css"


def _open_in_viewer(page: Path) -> str | None:
    html = page.read_text(encoding="utf-8")
    match = re.search(
        r'<meta name="' + re.escape(viewer.OPEN_IN_VIEWER_META) + r'" content="([^"]*)">', html
    )
    return None if match is None else match.group(1).replace("&amp;", "&")


def _opens_itself(site_root: Path, relative: str) -> bool:
    """The page's button reaches the site's one shell, asking for this page."""
    from posixpath import dirname, join, normpath

    href = _open_in_viewer(site_root / relative)
    assert href is not None, f"{relative} carries no way into the viewer"
    target, asked = _doc_url(href)
    reached = normpath(join(dirname(relative), target))
    return reached == viewer.SHELL_PAGE and _unquote(asked) == relative


def test_every_page_opens_itself_in_the_viewer(site):
    """The button asks the shell for the very page it is on, by the manifest's URL.

    Built from `page_url`, the function the manifest lists pages by, so
    the shell is handed a URL its navigator knows, and the depth back up
    to the shell is the page's own plus its project's.
    """
    out, model, _entries = site
    project = _project(model)
    assert _opens_itself(out, viewer.ROOT_PAGE)
    assert _opens_itself(out, project["landing"])
    for doc in project["documents"]:
        assert _opens_itself(out, _unquote(doc["url"])), doc["docname"]
        _page, asked = _doc_url(_open_in_viewer(out / _unquote(doc["url"])))
        assert asked == doc["url"]


def _scripts(page: Path) -> list[tuple[str, str]]:
    """Every docstrap script on a page, as (filename, type) in page order."""
    html = page.read_text(encoding="utf-8")
    found = []
    for attributes in re.findall(r"<script([^>]*)>", html):
        src = re.search(r'src="([^"?]+)', attributes)
        if src is None or not Path(src.group(1)).name.startswith("docstrap"):
            continue
        kind = re.search(r'type="([^"]+)"', attributes)
        found.append((Path(src.group(1)).name, kind.group(1) if kind else ""))
    return found


def test_a_page_opened_on_its_own_runs_only_the_button(site):
    """No Svelte runtime is fetched until the reader asks for the viewer.

    Every tool bundle carries its own copy of the runtime. They are all
    still on the page — the viewer turns them on — but as scripts of a
    type no browser fetches or runs, so the one script that does run is
    the dependency-free button.
    """
    from docstrap.sphinx.tool_support import DEFERRED_SCRIPT_TYPE
    from docstrap.tools import registry

    out, model, _entries = site
    page = out / _unquote(_project(model)["documents"][0]["url"])
    scripts = _scripts(page)
    runnable = [name for name, kind in scripts if kind in ("", "text/javascript")]
    assert runnable == ["docstrap-viewer-button.js"]
    held = [name for name, kind in scripts if kind == DEFERRED_SCRIPT_TYPE]
    expected = {"docstrap-common.js", "docstrap-launcher.js"}
    expected |= {declaration.js_bundle for declaration in registry.iter_declarations()}
    assert set(held) == expected
    # The shared client runs first inside the viewer; every tool waits on it.
    assert held[0] == "docstrap-common.js"
    # The button runs after the scripts it turns on are in the page.
    assert [name for name, _ in scripts][-1] == "docstrap-viewer-button.js"


def test_the_button_script_reads_the_names_python_writes():
    from docstrap.sphinx.tool_support import DEFERRED_SCRIPT_TYPE

    source = BUTTON_JS.read_text(encoding="utf-8")
    assert f"'{viewer.OPEN_IN_VIEWER_META}'" in source
    assert f"'{DEFERRED_SCRIPT_TYPE}'" in source


def test_the_button_is_drawn_only_on_a_page_opened_on_its_own():
    """Inside the viewer the button never appears, whichever runs first.

    The state is the page's own: the script marks the root element
    `page` at the top level and `framed` inside a frame, draws the button
    only in the first case, and turns the tools on only in the second.
    The stylesheet hides the button unless the mark says `page`, so a
    frame shows none even before the script has run.
    """
    source = BUTTON_JS.read_text(encoding="utf-8")
    assert "var framed = window.self !== window.top;" in source
    assert "setAttribute(STATE_ATTRIBUTE, framed ? 'framed' : 'page')" in source
    assert "onReady(framed ? runDeferredScripts : drawButton);" in source
    css = BUTTON_CSS.read_text(encoding="utf-8")
    assert ".docstrap-open-in-viewer {\n  display: none;\n}" in css
    shown = re.findall(r"^(html\[[^\]]+\]) \.docstrap-open-in-viewer \{", css, re.M)
    assert shown == ['html[data-docstrap-view="page"]']


def test_the_shell_follows_its_address_once_open():
    """A changed `?doc-url=` or hash moves the open shell's middle region.

    `QueryParam` re-reads the address on `popstate` and `hashchange`, and
    the shell reads `?doc-url=` through it under the name Python writes.
    """
    query_param = (viewer.UI_DIR / "queryParam.svelte.ts").read_text(encoding="utf-8")
    assert "addEventListener('popstate', update)" in query_param
    assert "addEventListener('hashchange', update)" in query_param
    app = (viewer.UI_DIR / "App.svelte").read_text(encoding="utf-8")
    assert f"const DOC_URL_PARAM = '{viewer.DOC_URL_PARAM}';" in app
    assert "new QueryParam(DOC_URL_PARAM)" in app
    [bundle] = (viewer.STATIC_DIR / viewer.ASSET_DIR).glob("*.js")
    built = bundle.read_text(encoding="utf-8")
    assert "hashchange" in built and f'"{viewer.DOC_URL_PARAM}"' in built, (
        "the committed build is stale"
    )


def test_a_path_that_spells_the_tag_name_does_not_suppress_the_tag(tmp_path: Path):
    """The guard against a second tag reads the attribute, not the bare name.

    Found by building under a scratch directory whose name contained
    `docstrap-open-in-viewer`: the page's source-path tag carried it, and
    a substring check took that for the button's own tag and left every
    page without one.
    """
    from docstrap.sphinx import viewer_button

    app = type("App", (), {"config": type("Config", (), {"docstrap_viewer_base": "p/"})()})()
    context = {
        "metatags": f'<meta name="docstrap-source-path" content="/tmp/{viewer.OPEN_IN_VIEWER_META}/a.md">'
    }
    viewer_button._on_html_page_context(app, "a", "page.html", context, None)
    assert context["metatags"].count(f'name="{viewer.OPEN_IN_VIEWER_META}"') == 1
    viewer_button._on_html_page_context(app, "a", "page.html", context, None)
    assert context["metatags"].count(f'name="{viewer.OPEN_IN_VIEWER_META}"') == 1


def test_the_navigator_drawer_rules_pass_under_node():
    node = shutil.which("node")
    version = subprocess.run([node, "--version"], capture_output=True, text=True).stdout if node else ""
    match = re.match(r"v(\d+)\.(\d+)", version)
    # Type stripping arrived in 22.6.
    if not match or (int(match.group(1)), int(match.group(2))) < (22, 6):
        pytest.skip("needs Node 22.6 or later, for --experimental-strip-types")
    result = subprocess.run(
        [node, "--experimental-strip-types", "--test", "tests/viewer/navigatorPane.test.ts"],
        cwd=Path(__file__).resolve().parent.parent,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_the_navigator_is_a_drawer_with_one_tab_and_a_resize_handle():
    """The tab opens and closes the drawer; the strip beside it resizes it.

    The tab is the strip's sibling, so pressing it never starts a drag,
    and the tree scrolls in an aside inside the splitter's panel because
    the splitter styles the panel itself `overflow: hidden`. Collapsing
    keeps the navigator mounted and makes it inert.
    """
    app = (viewer.UI_DIR / "App.svelte").read_text(encoding="utf-8")
    assert "useMachine(splitter.machine" in app
    assert "defaultSize: [openWidth]" in app
    assert "onResizeEnd: ({ size }) => writeWidth(storage, size[0], groupWidth)" in app
    assert "const leftOpen = $derived(!splitApi.isPanelCollapsed(NAV_PANEL));" in app
    assert app.count("onclick={toggleLeft}") == 2, "the drawer tab and the app bar's button"
    edge = app[app.index('<div class="edge'):app.index("</button>", app.index('<div class="edge'))]
    trigger = edge[edge.index("<div\n"):edge.index("></div>")]
    assert "getResizeTriggerProps({ id: TRIGGER })" in trigger
    assert "toggleLeft" not in trigger
    panel = app.index("getPanelProps({ id: NAV_PANEL })")
    aside = app.index('aria-label="Navigator"')
    assert panel < aside and "overflow-y-auto" in app[panel:aside]
    assert "inert={!leftOpen}" in app[aside:]
    assert "hidden={!leftOpen}" not in app

    [bundle] = (viewer.STATIC_DIR / viewer.ASSET_DIR).glob("*.js")
    built = bundle.read_text(encoding="utf-8")
    assert "docstrap.viewer.navigatorWidth" in built and "Open the navigator" in built, (
        "the committed build is stale"
    )


def test_a_navigator_title_wraps_in_its_row_under_a_halved_indent():
    """No row truncates; every row's title wraps after its icon.

    Skeleton steps each tree level six spacing units. The shell's
    stylesheet steps three, and the committed build carries that rule.
    """
    nav = (viewer.UI_DIR / "Navigator.svelte").read_text(encoding="utf-8")
    assert "truncate" not in nav.split("</script>", 1)[1]
    assert nav.count('leading-6 break-words">{node.name}</span>') == 2, "a folder row and a document row"
    assert nav.count('class="min-h-9 items-start"') == 2, "icons and the pin stay on the first line"

    css = (viewer.UI_DIR / "app.css").read_text(encoding="utf-8")
    assert "--tree-step: calc(var(--spacing) * 3);" in css
    assert css.count("(var(--depth) - 1) * var(--tree-step)") == 3, "the folder, the document, the guide"

    [bundle] = (viewer.STATIC_DIR / viewer.ASSET_DIR).glob("*.css")
    built = bundle.read_text(encoding="utf-8")
    assert "--tree-step:calc(var(--spacing) * 3)" in built, "the committed build is stale"
    assert built.count("(var(--depth) - 1) * var(--tree-step)") == 3
