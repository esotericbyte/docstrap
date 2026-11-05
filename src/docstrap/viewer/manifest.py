"""What the viewer shell is told about a built site, and putting it there.

The shell's navigator lists every store, project and document a build
published, and its question drawer needs the qapanels routes for the
document pinned there. Both come from here, written once per build as
``_viewer/manifest.json`` in the site root.

**Composed from what the build already knows, not from a walk.** A
project's documents and sections are its ``file_index`` rows
(:mod:`docstrap.fileindex`), which the build reconciled while it
mirrored the project — the same rows :mod:`docstrap.sectionindex`
composes section pages from. A document's question routes come from
:func:`docstrap.tools.launcher.offer_payload` called with the very
:class:`~docstrap.tools.launcher.PageContext` its page gets, so the URLs
in the manifest are the URLs in the pages by construction and the
client still assembles no API path.

**Written into the build, never into a project**, and JSON rather than
markdown. It is a build output like the HTML beside it, not a cache: the
next build rewrites it, so there is nothing to invalidate.

A project built by a layout that fills no file index — a site on the
author's own ``conf.py`` — is listed with its landing page and no
documents. That is the truth about what docstrap indexed, not a gap to
fill by walking the HTML.
"""
from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote

from docstrap import fileindex
from docstrap.tools import launcher
from docstrap.tools.launcher import PageContext
from docstrap.tools.qapanels.declaration import DECLARATION as QUESTIONS

#: The shell's page, at the site root so every URL in the manifest is
#: relative to the page that reads it.
SHELL_PAGE = "viewer.html"

#: Everything else the shell ships, and the manifest, live under this.
ASSET_DIR = "_viewer"

#: The manifest's path below the site root.
MANIFEST_PATH = f"{ASSET_DIR}/manifest.json"

#: The site's root page, which the manifest names as its landing.
ROOT_PAGE = "index.html"

#: The query parameter naming the page in the shell's middle region,
#: site-relative and URL-encoded. It is the shell's own record of which
#: page is there, so an address carrying it is an instruction rather
#: than a second page. The shell also still accepts the older form, the
#: page in the hash, and rewrites it into this one.
DOC_URL_PARAM = "doc-url"

#: The viewer entrance: the shell, told to show the root page in its
#: middle region, so the front page arrives in the frame like any other
#: document.
ENTRANCE = f"{SHELL_PAGE}?{DOC_URL_PARAM}={ROOT_PAGE}"

#: The meta tag a published page carries its way into the viewer in.
#: The page's own script, ``docstrap-viewer-button.js``, reads it; that
#: script and this constant are held to one name by ``test_viewer.py``.
OPEN_IN_VIEWER_META = "docstrap-open-in-viewer"

#: The entrance link's class. The shell hides it inside its own frame,
#: where following it would put a viewer inside the viewer.
ENTRANCE_CLASS = "docstrap-viewer-entrance"

#: Bumped when the manifest's shape changes in a way the shell reads.
MANIFEST_VERSION = 1

#: The committed build of ``ui/``. ``build-tools.mjs`` writes it.
STATIC_DIR = Path(__file__).parent / "static"

#: The client source the frontend build compiles into :data:`STATIC_DIR`.
UI_DIR = Path(__file__).parent / "ui"


@dataclass(frozen=True)
class ProjectSite:
    """One project as the build published it.

    ``base`` is the site-relative URL of the project's directory, ending
    in ``/`` — ``my-store/packages__docstrap/`` in a multi-store
    build, ``packages__docstrap/`` in a single-store one.
    """

    slug: str
    title: str
    base: str
    icon: str = ""


@dataclass(frozen=True)
class StoreSite:
    """One store's landing page and the projects it built."""

    title: str
    landing: str
    projects: tuple[ProjectSite, ...]
    icon: str = ""


def project_base(prefix: str, slug: str) -> str:
    """Where a project's pages are, below ``prefix`` (``''`` or ``'store/'``)."""
    return f"{prefix}{quote(slug, safe='')}/"


def entrance_html() -> str:
    """The root page's way into the viewer, or ``''`` when there is no shell.

    Raw HTML, like the aggregate's other links, and for the same reason:
    the target is not a document of the Sphinx run composing the page.
    Every other page gets its way in from its own script instead
    (:func:`open_in_viewer_href`).
    ``target="_top"`` because a frame that kept it — the qapanels
    reference panel — must not grow a viewer of its own; the shell's own
    frame hides the link instead. It carries ``docstrap-chrome`` because
    it is apparatus, not content.
    """
    if not (STATIC_DIR / SHELL_PAGE).is_file():
        return ""
    return (
        f'<p class="{ENTRANCE_CLASS} docstrap-chrome">'
        f'<a href="{ENTRANCE}" target="_top">Open this site in the viewer</a></p>'
    )


def site_base(directory: Path, site_root: Optional[Path]) -> Optional[str]:
    """Where ``directory`` sits below the site the shell is published at.

    In the spelling :func:`project_base` uses — ``store/project/``, or
    ``''`` for the site root itself — so a page's URL composed from it
    is the URL the manifest lists. None when there is no shell to open:
    no site root was named, or the shell has never been built.
    """
    if site_root is None or not (STATIC_DIR / SHELL_PAGE).is_file():
        return None
    relative = directory.resolve().relative_to(site_root.resolve())
    return "".join(f"{quote(part, safe='')}/" for part in relative.parts)


def open_in_viewer_href(base: str, docname: str) -> str:
    """The address, relative to a page, of the shell showing that page.

    ``base`` is the page's build below the site root (:func:`site_base`),
    and ``docname`` its Sphinx page name. The page is ``docname.html``
    in its build's output directory, so it is that many directories
    below the build, and the build ``base``'s depth below the site root.
    """
    up = "../" * (base.count("/") + docname.count("/"))
    target = quote(page_url(base, docname), safe="")
    return f"{up}{SHELL_PAGE}?{DOC_URL_PARAM}={target}"


def page_url(base: str, docname: str) -> str:
    """A page's site-relative URL.

    The docname is a PATH and its separators are the identity, so they
    stay separators; every other reserved character is escaped.
    """
    return f"{base}{quote(docname, safe='/')}.html"


def _questions_offer(project: str, docname: str) -> Optional[dict[str, Any]]:
    """The qapanels offer this document's page carries, or None."""
    context = PageContext(project=project, doc_slug=docname)
    if not launcher.is_valid_here(QUESTIONS, context):
        return None
    return launcher.offer_payload(QUESTIONS, context)


def _documents(project: ProjectSite, db_path: Optional[Path]) -> list[dict[str, Any]]:
    entries = fileindex.list_project(project.slug, db_path)
    documents: list[dict[str, Any]] = []
    for entry in entries:
        documents.append(
            {
                "docname": entry.docname,
                "title": entry.title or entry.docname.rsplit("/", 1)[-1],
                "kind": entry.kind,
                "parent": entry.parent_docname,
                "grouping": entry.grouping,
                "sortKey": entry.sort_key,
                "url": page_url(project.base, entry.docname),
                # Only a document poses questions. A section page is
                # composed by the build and holds none of its own.
                "questions": (
                    None
                    if entry.is_section
                    else _questions_offer(project.slug, entry.docname)
                ),
            }
        )
    return documents


def compose(
    title: str,
    stores: list[StoreSite],
    db_path: Optional[Path] = None,
) -> dict[str, Any]:
    """The manifest for a site whose root landing page is :data:`ROOT_PAGE`."""
    return {
        "version": MANIFEST_VERSION,
        "title": title,
        "landing": ROOT_PAGE,
        "stores": [
            {
                "title": store.title,
                "icon": store.icon,
                "landing": store.landing,
                "projects": [
                    {
                        "slug": project.slug,
                        "title": project.title,
                        "icon": project.icon,
                        "base": project.base,
                        "landing": f"{project.base}index.html",
                        "documents": _documents(project, db_path),
                    }
                    for project in store.projects
                ],
            }
            for store in stores
        ],
    }


def publish(site_root: Path, model: dict[str, Any]) -> Optional[Path]:
    """Put the shell and its manifest into ``site_root``. Returns the page.

    The shell's own asset directory is replaced wholesale: it is the
    shell's and nothing else's, and replacing it is what keeps a
    previous build's hashed bundles from piling up beside the current
    ones. Returns None, writing nothing, when the shell has never been
    built — a checkout without ``static/`` still builds its documents.
    """
    page = STATIC_DIR / SHELL_PAGE
    if not page.is_file():
        return None
    assets = site_root / ASSET_DIR
    if assets.exists():
        shutil.rmtree(assets)
    shutil.copytree(STATIC_DIR / ASSET_DIR, assets)
    shutil.copy2(page, site_root / SHELL_PAGE)
    (site_root / MANIFEST_PATH).write_text(
        json.dumps(model, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    return site_root / SHELL_PAGE
