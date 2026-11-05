"""Build orchestrator: scan a .docstrap, dispatch each project, aggregate.

The aggregate landing page is built via Sphinx + furo (the same theme
individual project pages use) so the whole site is visually consistent.
Proper external aggregate module integration (with cross-project search,
tag index, backlinks) comes later.

**An aggregate page is an index too, and it is composed like one.** It
used to be assembled as markdown and handed to Sphinx to parse back,
a step that has been removed. What it lists —
which projects built and which failed — is knowledge only the run that
just performed them has, so it cannot come from the file index; it
travels in the generated conf.py as a plain model and
:class:`docstrap.sphinx.composed.AggregatePageParser` builds the page
from it. No markdown at any stage, here either.
"""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from docstrap.config import DocstrapConfig
from docstrap.layouts import build_project
from docstrap.layouts.base import BuildResult, LayoutError
from docstrap.layouts.markdown import write_conf_py, write_marker
from docstrap.scan import ScannedProject, scan
from docstrap.sphinx import composed
from docstrap.sphinx_build import sphinx_build_command
from docstrap.viewer import manifest as viewer


@dataclass
class BuildReport:
    """Summary of a single-store build run."""

    site_root: Path
    successes: list[BuildResult]
    failures: list[tuple[str, LayoutError]]
    #: What each built project is called, by slug — the viewer's
    #: navigator lists projects by title, and the scan already had them.
    projects: dict[str, ScannedProject] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return len(self.successes) + len(self.failures)


@dataclass
class MultiStoreReport:
    """Summary of a build across every registered store."""

    site_root: Path
    per_store: list[tuple[Path, DocstrapConfig, BuildReport]]
    load_errors: list[tuple[Path, Exception]]


def build_all(
    config: DocstrapConfig,
    out_dir: Path,
    only_project: str | None = None,
    publish_viewer: bool = True,
    site_root: Path | None = None,
) -> BuildReport:
    """Build every project (or one) declared in the config into out_dir.

    ``publish_viewer`` puts the viewer shell at ``out_dir``'s root. A
    multi-store build turns it off here and publishes once, at the
    super-aggregate's root, listing every store — and names that root as
    ``site_root``, so the pages built here still lead into the shell.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    if site_root is None and publish_viewer:
        site_root = out_dir

    # A list, not the scan's generator: it is read again after the loop,
    # for the titles the viewer lists projects by.
    projects: list[ScannedProject] = list(scan(config))
    if only_project is not None:
        projects = [p for p in projects if p.slug == only_project]
        if not projects:
            raise LayoutError(f"No project with slug `{only_project}` in config.")

    successes: list[BuildResult] = []
    failures: list[tuple[str, LayoutError]] = []

    for project in projects:
        try:
            result = build_project(project, out_dir, site_root)
            successes.append(result)
        except LayoutError as e:
            failures.append((project.slug, e))

    # The store's landing page is the site's root page only when the
    # shell is published beside it, so only then does it lead into it.
    _build_aggregate(
        out_dir, config, successes, failures, entrance=publish_viewer, site_root=site_root
    )

    report = BuildReport(
        site_root=out_dir,
        successes=successes,
        failures=failures,
        projects={p.slug: p for p in projects},
    )
    if publish_viewer:
        viewer.publish(
            out_dir, viewer.compose(config.title, [_store_site(config, report, "")])
        )
    return report


def _store_site(config: DocstrapConfig, report: BuildReport, prefix: str) -> viewer.StoreSite:
    """One store as the viewer lists it. ``prefix`` is its directory, or ``''``."""
    projects = []
    for result in report.successes:
        scanned = report.projects.get(result.project_slug)
        projects.append(
            viewer.ProjectSite(
                slug=result.project_slug,
                title=scanned.title if scanned else result.project_slug,
                base=viewer.project_base(prefix, result.project_slug),
                icon=(scanned.icon or "") if scanned else "",
            )
        )
    return viewer.StoreSite(
        title=config.title,
        icon=config.icon or "",
        landing=f"{prefix}index.html",
        projects=tuple(projects),
    )


def build_stores(
    store_paths: list[Path],
    out_dir: Path,
) -> MultiStoreReport:
    """Build every registered store into its own subdir; write a super-aggregate.

    Layout:
      <out_dir>/index.html                       ← super-aggregate (all stores)
      <out_dir>/<store-slug>/index.html          ← per-store aggregate
      <out_dir>/<store-slug>/<project-slug>/...  ← project pages
    """
    from docstrap.config import DocstrapConfigError, load as load_docstrap

    out_dir.mkdir(parents=True, exist_ok=True)
    per_store: list[tuple[Path, DocstrapConfig, BuildReport]] = []
    load_errors: list[tuple[Path, Exception]] = []

    for store_path in store_paths:
        try:
            store_config = load_docstrap(store_path)
        except (DocstrapConfigError, FileNotFoundError, OSError) as e:
            load_errors.append((store_path, e))
            continue
        store_slug = _store_slug(store_config, store_path)
        store_out = out_dir / store_slug
        report = build_all(
            store_config, store_out, publish_viewer=False, site_root=out_dir
        )
        per_store.append((store_path, store_config, report))

    _build_super_aggregate(out_dir, per_store, load_errors)
    viewer.publish(
        out_dir,
        viewer.compose(
            "Docstrap",
            [
                _store_site(cfg, report, f"{_store_slug(cfg, path)}/")
                for path, cfg, report in per_store
            ],
        ),
    )
    _run_pagefind_step(out_dir)
    return MultiStoreReport(site_root=out_dir, per_store=per_store, load_errors=load_errors)


def _run_pagefind_step(site_root: Path) -> None:
    """Best-effort pagefind index over the aggregate site."""
    from docstrap.pagefind_step import run_pagefind

    ok, note = run_pagefind(site_root)
    # We don't raise on failure — search index is nice-to-have.
    # The note gets printed by the CLI wrapper via a side channel:
    # simplest is to write it into a marker file the CLI can read.
    marker = site_root / "_scratch" / "_pagefind_status.txt"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(("ok: " if ok else "skip: ") + note + "\n", encoding="utf-8")


def _store_slug(config: DocstrapConfig, path: Path) -> str:
    """Slug for a store's top-level output subdir. Falls back to a filesystem hash."""
    # Prefer the config's title (docstrap-friendly names in the URL).
    from docstrap.slugs import slugify

    return slugify(config.title) or path.parent.name


def _build_super_aggregate(
    out_dir: Path,
    per_store: list[tuple[Path, DocstrapConfig, BuildReport]],
    load_errors: list[tuple[Path, Exception]],
) -> None:
    """Sphinx+furo aggregate that lists every store and its projects."""
    scratch_dir = out_dir / "_scratch" / "_super_aggregate"
    if scratch_dir.exists():
        shutil.rmtree(scratch_dir)
    scratch_dir.mkdir(parents=True, exist_ok=True)

    write_conf_py(
        scratch_dir,
        "Docstrap",
        aggregate=_super_aggregate_model(per_store, load_errors),
        viewer_base=viewer.site_base(out_dir, out_dir),
    )
    write_marker(scratch_dir, composed.AGGREGATE_MARKER_NAME)

    result = subprocess.run(
        sphinx_build_command("-b", "html", "-q", str(scratch_dir), str(out_dir)),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        # Fallback if the super aggregate build itself fails.
        _write_fallback_super_index(out_dir, per_store, load_errors)


#: The client-side search widget the super-aggregate carries. Raw HTML
#: because that is what it is; it degrades to nothing when the pagefind
#: index was not generated.
_PAGEFIND_WIDGET = (
    '<link rel="stylesheet" href="pagefind/pagefind-ui.css">'
    '<div id="docstrap-search" style="margin: 1em 0;"></div>'
    '<script src="pagefind/pagefind-ui.js"></script>'
    '<script>window.addEventListener("DOMContentLoaded", () => {'
    '  if (window.PagefindUI) {'
    '    new PagefindUI({ element: "#docstrap-search", showSubResults: true });'
    '  }'
    '});</script>'
)


def _super_aggregate_model(
    per_store: list[tuple[Path, DocstrapConfig, BuildReport]],
    load_errors: list[tuple[Path, Exception]],
) -> dict[str, Any]:
    """The top-level page's model: every store, and what it built.

    Links are raw HTML anchors rather than markdown or references, and
    that predates this change for a reason worth keeping written down:
    they point at built `index.html` files that are not documents of the
    Sphinx run composing this page, and MyST resolved such a link as an
    internal reference and broke it.
    """
    blocks: list[dict[str, Any]] = []
    for store_path, cfg, report in per_store:
        slug = _store_slug(cfg, store_path)
        heading = f"{cfg.icon} {cfg.title}" if cfg.icon else cfg.title
        notes: list[str] = []
        if report.failures:
            notes.append(
                f"{len(report.failures)} project(s) failed to build; "
                f"see {slug} landing."
            )
        blocks.append({
            "heading": heading,
            "short": cfg.short or "",
            "lead": f'<a href="{slug}/index.html">{slug} landing</a>',
            "links": [
                f'<a href="{slug}/{r.project_slug}/index.html">{r.project_slug}</a>'
                f' — <small>{_html_escape(r.notes)}</small>'
                for r in report.successes
            ],
            "notes": notes,
        })
    if load_errors:
        blocks.append({
            "heading": "Load errors",
            "links": [
                f"<strong>{_html_escape(str(path))}</strong>: {_html_escape(str(err))}"
                for path, err in load_errors
            ],
        })
    return {
        "title": "Docstrap",
        "short": "Aggregated documentation across all registered `.docstrap` stores.",
        "raw_html": viewer.entrance_html() + _PAGEFIND_WIDGET,
        "blocks": blocks,
    }


def _write_fallback_super_index(
    out_dir: Path,
    per_store: list[tuple[Path, DocstrapConfig, BuildReport]],
    load_errors: list[tuple[Path, Exception]],
) -> None:
    """Bare-HTML fallback if the super-aggregate Sphinx build fails."""
    lines: list[str] = [
        "<!doctype html>",
        "<html><head><meta charset='utf-8'><title>Docstrap</title></head><body>",
        "<h1>Docstrap</h1>",
    ]
    for store_path, cfg, report in per_store:
        slug = _store_slug(cfg, store_path)
        lines.append(f"<h2>{_html_escape(cfg.title)}</h2>")
        lines.append(f'<p><a href="{slug}/index.html">{slug} landing</a></p>')
        if report.successes:
            lines.append("<ul>")
            for r in report.successes:
                lines.append(
                    f'<li><a href="{slug}/{r.project_slug}/index.html">{r.project_slug}</a></li>'
                )
            lines.append("</ul>")
    if load_errors:
        lines.append("<h2>Load errors</h2><ul>")
        for path, err in load_errors:
            lines.append(f"<li><strong>{_html_escape(str(path))}</strong>: {_html_escape(str(err))}</li>")
        lines.append("</ul>")
    lines.append("</body></html>")
    (out_dir / "index.html").write_text("\n".join(lines), encoding="utf-8")


def _build_aggregate(
    out_dir: Path,
    config: DocstrapConfig,
    successes: list[BuildResult],
    failures: list[tuple[str, LayoutError]],
    entrance: bool = False,
    site_root: Path | None = None,
) -> None:
    """Build the aggregate landing page via Sphinx + furo.

    Runs a separate sphinx-build against a scratch dir containing the
    same conf.py template used for individual markdown-layout projects.
    Output lands at the site root, sharing visual style with project
    pages. Individual project subdirectories under out_dir are
    untouched — sphinx-build writes only its own outputs.
    """
    scratch_dir = out_dir / "_scratch" / "_aggregate"
    if scratch_dir.exists():
        shutil.rmtree(scratch_dir)
    scratch_dir.mkdir(parents=True, exist_ok=True)

    write_conf_py(
        scratch_dir,
        config.title,
        config.exclude_dirs,
        aggregate=_aggregate_model(config, successes, failures, entrance),
        viewer_base=viewer.site_base(out_dir, site_root),
    )
    write_marker(scratch_dir, composed.AGGREGATE_MARKER_NAME)

    result = subprocess.run(
        sphinx_build_command("-b", "html", "-q", str(scratch_dir), str(out_dir)),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        # Aggregate build failed. Don't fail the whole run — fall back
        # to a minimal HTML index so users still see a landing page.
        _write_fallback_index(out_dir, config, successes, failures)


def _aggregate_model(
    config: DocstrapConfig,
    successes: list[BuildResult],
    failures: list[tuple[str, LayoutError]],
    entrance: bool = False,
) -> dict[str, Any]:
    """One store's landing page: the projects it built, and what failed.

    ``entrance`` adds the way into the viewer, for a landing page that is
    the site's root page.
    """
    blocks: list[dict[str, Any]] = []
    if successes:
        blocks.append({
            "heading": "Projects",
            "links": [
                f'<a href="{r.project_slug}/index.html">{r.project_slug}</a>'
                f' — <small>{_html_escape(r.notes)}</small>'
                for r in successes
            ],
        })
    if failures:
        blocks.append({
            "heading": "Build failures",
            "links": [
                f"<strong>{_html_escape(slug)}</strong>: {_html_escape(str(err))}"
                for slug, err in failures
            ],
        })
    return {
        "title": f"{config.icon} {config.title}" if config.icon else config.title,
        "short": config.short or "",
        "raw_html": viewer.entrance_html() if entrance else "",
        "blocks": blocks,
    }


def _write_fallback_index(
    out_dir: Path,
    config: DocstrapConfig,
    successes: list[BuildResult],
    failures: list[tuple[str, LayoutError]],
) -> None:
    """Bare-HTML fallback if Sphinx aggregate build itself fails."""
    lines: list[str] = ["<!doctype html>",
        f"<html><head><meta charset='utf-8'><title>{_html_escape(config.title)}</title></head>",
        "<body>", f"<h1>{_html_escape(config.title)}</h1>"]
    if config.short:
        lines.append(f"<p><em>{_html_escape(config.short)}</em></p>")
    if successes:
        lines.append("<h2>Projects</h2><ul>")
        for r in successes:
            lines.append(f"<li><a href='{r.project_slug}/index.html'>{_html_escape(r.project_slug)}</a></li>")
        lines.append("</ul>")
    if failures:
        lines.append("<h2>Build failures</h2><ul>")
        for slug, err in failures:
            lines.append(f"<li><strong>{_html_escape(slug)}</strong>: {_html_escape(str(err))}</li>")
        lines.append("</ul>")
    lines.append("</body></html>")
    (out_dir / "index.html").write_text("\n".join(lines), encoding="utf-8")


def _html_escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
