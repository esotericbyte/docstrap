"""What a real Sphinx build actually puts on the page.

A real build, not a simulated one: sphinx-build over a real source
directory with the tool extensions loaded, then assertions on the HTML
that comes out. That is the only way to be sure the assets are
registered, the offer payload lands in the head, and — the property
to keep — a page with every tool hidden reads as a plain document.

"Hidden" here means the state a shared page is in: the HTML as built,
before any JavaScript runs. Every piece of tool apparatus is either
injected by a tool's show() or gated behind the launcher's visibility
class, so the built page carries none of it. The interactive half —
toggling in a browser — is covered by a manual check, not here.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

from docstrap.sphinx.launcher import OFFERS_ELEMENT_ID
from docstrap.tools import registry

PAGE = """\
# Sample Page

First sentence here. Second sentence follows it.

## A section

More prose in the section. It has two sentences.

```{docstrap-questions}
:question-id: q-1
:prompt: What tradeoffs matter?
```
"""

# A minimal conf rather than the layout's own, so the test exercises the
# tool extensions and not the layout's optional MyST extras.
CONF = """\
project = "Sample Project"
extensions = {extensions!r}
master_doc = "index"
html_theme = "alabaster"
"""


#: A page two directories down. Every earlier browser run used a flat
#: sample project, which is why none of them could see that a document
#: below the root was unreachable — 666 of 686 pages in a real
#: multi-project site are nested.
#: This site is no longer flat.
NESTED_PAGENAME = "proposals/drafts/0002-the-upgrade-path"


@pytest.fixture(scope="module")
def built_site(tmp_path_factory) -> Path:
    """Build a site with every declared tool loaded, and a nested page."""
    root = tmp_path_factory.mktemp("site")
    src, out = root / "src", root / "out"
    src.mkdir()
    (src / "index.md").write_text(PAGE, encoding="utf-8")
    nested = src / NESTED_PAGENAME
    nested.parent.mkdir(parents=True)
    nested.with_suffix(".md").write_text(PAGE, encoding="utf-8")
    extensions = ["myst_parser", *registry.sphinx_extensions()]
    (src / "conf.py").write_text(CONF.format(extensions=extensions), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "sphinx", "-q", "-b", "html", str(src), str(out)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    return out


@pytest.fixture(scope="module")
def html(built_site: Path) -> str:
    return (built_site / "index.html").read_text(encoding="utf-8")


# --- the build ships what the declarations name ------------------------------


def test_every_declared_bundle_reaches_the_built_site(built_site: Path):
    static = built_site / "_static"
    for declaration in registry.iter_declarations():
        assert (static / declaration.js_bundle).is_file(), declaration.id
        assert (static / declaration.css_bundle).is_file(), declaration.id
    assert (static / "docstrap-common.js").is_file()
    assert (static / "docstrap-launcher.js").is_file()


def test_the_page_carries_the_offer_payload(html: str):
    assert OFFERS_ELEMENT_ID in html
    assert 'name="docstrap-project"' in html
    assert 'name="docstrap-doc-slug"' in html


# --- a page below the root carries a path, all the way into the head --------


@pytest.fixture(scope="module")
def nested_html(built_site: Path) -> str:
    return (built_site / f"{NESTED_PAGENAME}.html").read_text(encoding="utf-8")


def test_a_nested_page_declares_its_identity_as_a_path(nested_html: str):
    """The meta tag is the docname, and a docname below the root has a path.

    This was always true and was never the broken part. It is asserted
    here so the other half — the URL built from it — is held against
    something real rather than against a literal both sides could drift
    from together.
    """
    assert (
        f'<meta name="docstrap-doc-slug" content="{NESTED_PAGENAME}">' in nested_html
    )


def test_a_nested_page_offers_urls_that_spell_the_path(nested_html: str):
    """The end of the loop: what the browser is handed on a nested page.

    Every document-targeted route resolved into this page's offer list
    used to carry `proposals%2Fdrafts%2F…`, which matched nothing and
    404ed while the panel blamed `docstrap serve`. A `%2F` anywhere in
    the offers block is that defect returning.
    """
    import json

    payload = re.search(
        rf'id="{OFFERS_ELEMENT_ID}"[^>]*>(.*?)</script>', nested_html, re.S
    )
    assert payload is not None, "the offers block should be in the head"
    offers = json.loads(payload.group(1))
    assert offers, "a page with a project and a document offers something"

    urls = [
        url
        for offer in offers
        for url in (offer.get("route"), offer.get("altRoute"))
        if url
    ]
    assert urls, "at least one tool resolves a URL on a document page"
    for url in urls:
        assert "%2F" not in url
    # The document-targeted ones end at this document's own path.
    document_urls = [url for url in urls if NESTED_PAGENAME in url]
    assert document_urls
    for url in document_urls:
        assert f"/{NESTED_PAGENAME}/" in url


# --- one launcher, no per-widget floating buttons ---------------------------


def test_only_one_place_in_the_client_blames_the_server():
    """A 404 from a responding docstrap is not `docstrap serve` being down.

    Four surfaces had grown the same sentence and all four were wrong in
    the same way, which is what turned one broken URL into a day of
    looking at the wrong thing. The wording now lives in
    `sphinx/ui/docstrap.ts`'s `describeApiFailure`, which says it only
    when the call produced no response at all.

    Source, not bundles: a built file is the source compiled, and
    asserting on both would only ever catch a stale build twice.
    """
    package = Path(registry.__file__).parent.parent
    offenders = sorted(
        str(path.relative_to(package))
        for path in package.rglob("*")
        if path.suffix in {".ts", ".svelte"}
        and "/static/" not in path.as_posix()
        and re.search(r"is\s+`?docstrap serve`?\s+running", path.read_text("utf-8"))
    )
    assert offenders == ["sphinx/ui/docstrap.ts"]


def test_no_per_widget_floating_button_survives_anywhere():
    """The affordance being removed. Gone from source, not just unused."""
    package = Path(registry.__file__).parent.parent
    offenders = [
        path
        for path in package.rglob("*")
        if path.suffix in {".js", ".css", ".py"}
        and "docstrap-review-toggle" in path.read_text(encoding="utf-8")
    ]
    assert offenders == []


def test_exactly_one_launcher_asset_ships(built_site: Path):
    launchers = sorted(p.name for p in (built_site / "_static").glob("*launcher*"))
    assert launchers == ["docstrap-launcher.css", "docstrap-launcher.js"]


# --- a page with every tool hidden reads as a plain document ----------------


CHROME_MARKERS = [
    "docstrap-launcher",          # the launcher's own control
    "docstrap-status-badge",      # the status tool's badge
    "docstrap-review-ctrl",       # the review tool's marks
    "docstrap-review-submit-bar",  # the review tool's submit bar
]


def _body_of(html: str) -> str:
    match = re.search(r"<body[^>]*>(.*)</body>", html, re.S)
    assert match, "no body in built page"
    return match.group(1)


@pytest.mark.parametrize("marker", CHROME_MARKERS)
def test_the_built_page_body_carries_no_injected_tool_chrome(html: str, marker: str):
    """Every one of these exists only once a tool is told to show."""
    assert marker not in _body_of(html)


def test_the_body_carries_no_visibility_class(html: str):
    """Nothing is showing until the launcher applies remembered state."""
    body_tag = re.search(r"<body[^>]*>", html).group(0)
    for declaration in registry.iter_declarations():
        assert declaration.visibility_class not in body_tag


def test_the_only_tool_apparatus_in_the_body_is_marked_as_chrome(html: str):
    """The qa form is in the HTML because its author put a question there.

    It is apparatus rather than document, so it carries the shared
    `docstrap-chrome` class and is gated behind the launcher's
    visibility class in CSS — with the tool hidden the question reads as
    a plain prompt with nothing to submit.
    """
    body = _body_of(html)
    assert 'class="docstrap-questions-form docstrap-chrome"' in body
    # The author's prompt is document content and stays visible.
    assert "What tradeoffs matter?" in body


def test_the_qa_form_is_gated_behind_the_launchers_visibility_class(built_site: Path):
    css = (built_site / "_static" / "docstrap-qa.css").read_text(encoding="utf-8")
    qa = registry.get("qa")
    # Hidden by default, revealed only under the launcher's body class.
    assert ".docstrap-questions-form {\n  display: none;" in css
    assert f"body.{qa.visibility_class} .docstrap-questions-form {{\n  display: block;" in css


def test_chrome_is_excluded_from_print(built_site: Path):
    """A saved or printed copy of a page is a document, not a workbench."""
    css = (built_site / "_static" / "docstrap.css").read_text(encoding="utf-8")
    assert "@media print" in css
    assert ".docstrap-chrome" in css


# --- the moved behaviour is still there -------------------------------------


def test_the_question_directive_still_renders_its_form(html: str):
    body = _body_of(html)
    assert 'class="docstrap-questions"' in body
    assert 'data-question-id="q-1"' in body
    assert 'class="docstrap-questions-answer"' in body
    assert 'class="docstrap-questions-submit"' in body


def test_the_section_the_review_tool_marks_is_present(html: str):
    """The review tool marks h2/h3/h4 at runtime; the headings must exist."""
    assert "<h2>" in html or "<h2 " in html


# --- a page with no viewer above it -----------------------------------------


def test_a_page_with_no_viewer_above_it_carries_no_way_in(html: str):
    """No shell was named for this build, so there is nowhere to open.

    The button script is still on the page and still holds the tools
    back; with no address to follow it simply draws nothing.
    """
    from docstrap.viewer.manifest import OPEN_IN_VIEWER_META

    assert f'name="{OPEN_IN_VIEWER_META}"' not in html
    assert re.search(r'<script src="_static/docstrap-viewer-button\.js[?"]', html)
