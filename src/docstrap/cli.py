"""docstrap CLI entry point.

Typer-based command surface. Alpha 1 wires up subcommands as stubs; each is
filled in during the alpha's implementation steps.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

app = typer.Typer(
    name="docstrap",
    help="Publish documentation projects to an aggregate site.",
    no_args_is_help=True,
    add_completion=False,
)

stores_app = typer.Typer(
    name="stores",
    help="Manage the user-level list of registered .docstrap stores.",
    no_args_is_help=True,
)
app.add_typer(stores_app, name="stores")

config_app = typer.Typer(
    name="config",
    help="The user config and `.docstrap` files, as one settings surface.",
    no_args_is_help=True,
)
app.add_typer(config_app, name="config")


def _version_callback(value: bool) -> None:
    if not value:
        return
    from docstrap.version import format_version_info

    typer.echo(format_version_info())
    raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        help="Show docstrap version, executable path, and install origin.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """Publish documentation projects to an aggregate site."""


@app.command("help")
def help_command(ctx: typer.Context) -> None:
    """Show this message and exit. Same as `docstrap --help`."""
    parent = ctx.parent
    typer.echo((parent or ctx).get_help())


@stores_app.command("list")
def stores_list() -> None:
    """List every .docstrap store the user has registered."""
    from docstrap import user_config

    cfg = user_config.load()
    if not cfg.stores:
        typer.echo("(no stores registered — use `docstrap stores add <path>`)")
        return
    for s in cfg.stores:
        marker = "✓" if s.exists() else "✗"
        typer.echo(f"  {marker}  {s}")


@stores_app.command("add")
def stores_add(
    path: Path = typer.Argument(..., help="Path to a .docstrap file to register."),
) -> None:
    """Register a .docstrap file in the user config."""
    from docstrap import user_config

    resolved = path.resolve()
    try:
        cfg, added = user_config.add_store(resolved)
    except FileNotFoundError as e:
        typer.secho(str(e), err=True, fg="red")
        raise typer.Exit(code=2)
    if added:
        typer.echo(f"registered: {resolved}")
    else:
        typer.echo(f"already registered: {resolved}")
    typer.echo(f"{len(cfg.stores)} store(s) total.")


@stores_app.command("remove")
def stores_remove(
    path: Path = typer.Argument(..., help="Path to a .docstrap file to deregister."),
) -> None:
    """Remove a .docstrap file from the user config."""
    from docstrap import user_config

    resolved = path.resolve()
    cfg, removed = user_config.remove_store(resolved)
    if removed:
        typer.echo(f"deregistered: {resolved}")
    else:
        typer.echo(f"not in stores list: {resolved}")
    typer.echo(f"{len(cfg.stores)} store(s) remain.")


@config_app.command("migrate")
def config_migrate(
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--apply",
        help="Show what would change (the default), or write it.",
    ),
) -> None:
    """Rewrite the user config and registered stores into the settings shape.

    `promdance:` becomes `plugins.promdance.enabled` — absent becomes
    `true`, so this machine keeps the behaviour it has — and
    `promdance_projects_root` becomes `plugins.promdance.projects_root`.
    The user config gains `sources` with the `docs` default the stores
    rely on, and promdance's `members` rule. Every registered `.docstrap`
    has its `promdance:` keys moved the same way.

    Moves no file and touches no database. Comments, key order and
    indentation are kept. Running it again changes nothing.
    """
    from docstrap import settings
    from docstrap.config import DocstrapConfigError

    try:
        changes = settings.migrate(write=not dry_run)
    except DocstrapConfigError as e:
        typer.secho(str(e), err=True, fg="red")
        raise typer.Exit(code=1)
    if not changes:
        typer.echo("nothing to migrate: the settings are already in the new shape.")
        return
    verb = "would change" if dry_run else "changed"
    for change in changes:
        typer.echo(f"{verb} {change.path}")
        for line in change.changes:
            typer.echo(f"  {line}")
        if dry_run:
            typer.echo(change.diff())
    if dry_run:
        typer.echo("dry run: nothing written. Run `docstrap config migrate --apply` to write it.")


@app.command()
def init(
    install_skills: Optional[bool] = typer.Option(
        None,
        "--install-skills/--no-install-skills",
        help="Install docstrap skill files to ~/.claude/skills/. Prompts if unset.",
    ),
) -> None:
    """First-run setup: create user-level directories, databases, and Claude skills."""
    from docstrap import annotations, metadata, paths, plugins

    paths.ensure_dirs()
    plugin_dirs = plugins.init()
    metadata_path = metadata.initialize()
    annotations_path = annotations.initialize()
    typer.echo(f"config dir:      {paths.config_dir()}")
    typer.echo(f"data dir:        {paths.data_dir()}")
    typer.echo(f"cache dir:       {paths.cache_dir()}")
    typer.echo(f"state dir:       {paths.state_dir()}")
    typer.echo(f"site out:        {paths.build_output_dir()}")
    for label, directory in plugin_dirs:
        typer.echo(f"{label + ':':<17}{directory}")
    typer.echo(f"metadata DB:     {metadata_path}")
    typer.echo(f"annotations DB:  {annotations_path}")

    installed = _install_claude_skills(install_skills)
    if installed:
        typer.echo(f"claude skills:   installed to {installed}")
    typer.echo("initialized.")


def _install_claude_skills(install_flag: Optional[bool]) -> Optional[Path]:
    """Copy docstrap skill files into ~/.claude/skills/.

    * install_flag=True  → install unconditionally.
    * install_flag=False → skip.
    * install_flag=None  → prompt.

    Returns the target directory if any skill was installed, else None.
    Existing files are only overwritten with confirmation.
    """
    import shutil

    from docstrap import paths as _paths  # noqa: F401 — kept for parity

    # Skills ship inside the installed package under docstrap/skills/.
    skills_src = Path(__file__).parent / "skills"
    if not skills_src.exists() or not any(skills_src.glob("*.md")):
        # No skills packaged yet — nothing to install.
        return None

    if install_flag is None:
        install_flag = typer.confirm(
            "Install docstrap Claude skills to ~/.claude/skills/?",
            default=True,
        )
    if not install_flag:
        return None

    target_dir = Path.home() / ".claude" / "skills"
    target_dir.mkdir(parents=True, exist_ok=True)

    for skill in sorted(skills_src.glob("*.md")):
        dest = target_dir / skill.name
        if dest.exists():
            same = dest.read_bytes() == skill.read_bytes()
            if same:
                continue
            replace = typer.confirm(
                f"  overwrite existing {dest}?", default=False
            )
            if not replace:
                typer.echo(f"  skipped:   {skill.name}")
                continue
        shutil.copy2(skill, dest)
        typer.echo(f"  installed: {skill.name}")

    return target_dir


@app.command("firstmate-ignore-check")
def firstmate_ignore_check(
    root: Path = typer.Option(
        Path.home(),
        "--root",
        help="Directory to scan for firstmate operational homes.",
    ),
    write: Optional[bool] = typer.Option(
        None,
        "--write/--no-write",
        help="Write or decline suggested .docstrap ignore declarations without prompting.",
    ),
) -> None:
    """Offer `.docstrap ignore: true` for detected firstmate operational homes."""
    from docstrap.config import DOCSTRAP_FILENAME, ignores_tree
    from docstrap.firstmate import detect_firstmate_homes, ensure_ignore_declaration

    homes = detect_firstmate_homes(root)
    if not homes:
        typer.echo("no firstmate operational homes found")
        return

    typer.echo(f"{len(homes)} firstmate operational home(s) found")
    typer.echo(
        "matched shape: AGENTS.md plus bin/fm-*.sh plus projects/"
    )
    typer.echo(
        "reason: firstmate project copies can double-count projects during discovery"
    )

    for home in homes:
        target = home.path / DOCSTRAP_FILENAME
        typer.echo(f"found: {home.path}")
        typer.echo(f"  AGENTS.md: {home.agents_file}")
        typer.echo(f"  projects:  {home.projects_dir}")
        typer.echo(f"  scripts:   {', '.join(p.name for p in home.bin_scripts)}")

        if ignores_tree(home.path):
            typer.echo(f"  already ignored by {target}")
            continue

        should_write = write
        if should_write is None:
            should_write = typer.confirm(
                f"Write ignore: true to {target}?",
                default=False,
            )
        if should_write:
            changed = ensure_ignore_declaration(home.path)
            typer.echo(f"  {'wrote' if changed else 'already present'}: {target}")
        else:
            typer.echo(f"  declined: {target}")


@app.command()
def doctor(
    root: Path = typer.Option(Path("."), "--root", help="Where to start looking."),
    docs_dir: Optional[str] = typer.Option(
        None,
        "--docs-dir",
        help="Docs directory name under the workspace root (default: the "
             "first source the `.docstrap` states, else the user config's).",
    ),
    firstmate_root: Optional[Path] = typer.Option(
        None,
        "--firstmate-root",
        help="Where to look for firstmate operational homes (default: --root).",
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        help="Ask, per finding, which directory should own it. Shapes the "
             "--fix-plan output only; nothing is moved either way.",
    ),
    fix_plan: Optional[Path] = typer.Option(
        None,
        "--fix-plan",
        help="Write a proposal shell script to this path. Refuses to overwrite.",
    ),
) -> None:
    """Report ambiguously-scoped top-level documents. Never moves anything.

    A document is ambiguously scoped when the strapdance chain's answer to
    "which project owns this?" came from the workspace root — or from
    nothing at all. Every finding is reported with the chain step and the
    provenance that produced it.

    Doctor reports and proposes; it does not act. The exit code is 0 even
    when there are findings: a report of what is, is not a failure.
    """
    from docstrap import doctor as doctor_mod

    report = doctor_mod.examine(
        root,
        docs_directory=docs_dir,
        firstmate_root=firstmate_root,
    )

    typer.echo(f"root:            {report.root}")
    typer.echo(f"workspace root:  {report.workspace_root}  ({report.workspace_detail})")
    typer.echo(f"docs directory:  {report.docs_dir or '(no source stated)'}")
    if not report.docs_dir_exists:
        typer.echo("  (no such directory — nothing to examine)")
    typer.echo(f"examined:        {len(report.examined)} document(s)")
    typer.echo("")

    if report.ambiguities:
        typer.echo(f"ambiguously-scoped documents ({len(report.ambiguities)}):")
        # Grouped by why they are ambiguous: the reason is a property of the
        # chain answer, not of the document, so stating it per document
        # buries sixteen findings under sixteen copies of one sentence.
        for source, findings in _group_by_source(report.ambiguities):
            typer.echo("")
            typer.echo(f"  [{source.value}] {findings[0].reason}")
            for finding in findings:
                typer.secho(f"  ✗  {finding.relative_path}", fg="yellow")
                typer.echo(f"       project:  {finding.project or '(none)'}")
                typer.echo(f"       chain:    {finding.chain}")
    else:
        typer.secho("  ✓  every examined document is scoped to a project.", fg="green")
    typer.echo("")

    typer.echo("environment:")
    unignored = report.unignored_firstmate
    for finding in report.firstmate:
        if finding.already_ignored:
            typer.echo(f"  ✓  firstmate home already ignored: {finding.path}")
        else:
            typer.secho(f"  ✗  firstmate operational home not ignored: {finding.path}", fg="yellow")
    if not report.firstmate:
        typer.echo("  ✓  no firstmate operational homes below the examined root.")
    if unignored:
        typer.echo(
            "     remedy: docstrap firstmate-ignore-check --root <dir>  "
            "(that command writes; doctor does not)"
        )
    for finding in report.plugin_findings:
        if finding.ok:
            typer.echo(f"  ✓  {finding.message}")
        else:
            typer.secho(f"  ✗  {finding.message}", fg="yellow")
    typer.echo("")

    destinations: dict[str, str] = {}
    if interactive and report.ambiguities:
        typer.echo(
            "Choose a destination directory for each finding, relative to the "
            "workspace root. Blank leaves it undecided. Nothing is moved: the "
            "answers only shape the --fix-plan script."
        )
        for finding in report.ambiguities:
            answer = typer.prompt(
                f"  destination for {finding.relative_path}",
                default="",
                show_default=False,
            ).strip()
            if answer:
                destinations[finding.relative_path] = answer
        typer.echo("")

    if fix_plan is not None:
        try:
            written = doctor_mod.write_fix_plan(report, fix_plan, destinations)
        except doctor_mod.FixPlanExists as e:
            typer.secho(str(e), err=True, fg="red")
            raise typer.Exit(code=1)
        typer.echo(f"fix plan written (not run): {written}")
    elif report.ambiguities:
        typer.echo("Re-run with --fix-plan <path> to write a proposal script.")

    typer.echo("doctor reports and proposes only. Nothing was modified.")


def _group_by_source(ambiguities):
    """Findings grouped by their ProjectSource, in first-seen order."""
    grouped: dict = {}
    for finding in ambiguities:
        grouped.setdefault(finding.source, []).append(finding)
    return list(grouped.items())


@app.command()
def projectfinder(
    root: Path = typer.Option(Path("."), "--root", help="Directory to scan."),
    all: bool = typer.Option(False, "--all", help="Include repos that already have a .docstrap."),
) -> None:
    """Walk below --root and report candidate git repositories without a .docstrap."""
    from docstrap import projectfinder as pf

    candidates = pf.find(root)
    shown = 0
    for c in candidates:
        if c.has_docstrap and not all:
            continue
        mark = "✓" if c.has_docstrap else " "
        typer.echo(f"  {mark}  {c.path}")
        shown += 1
    total_new = sum(1 for c in candidates if not c.has_docstrap)
    typer.echo("")
    typer.echo(f"{len(candidates)} git repo(s) found; {total_new} without .docstrap.")


@app.command()
def register(
    path: Path = typer.Option(Path("."), "--path", help="Directory to register."),
    title: Optional[str] = typer.Option(None, "--title", help="Human-readable title."),
    layout: str = typer.Option("markdown", "--layout", help="One of: sphinx, mkdocs, markdown, quarto."),
    docs_root: Optional[str] = typer.Option(
        None,
        "--docs-root",
        help="Docs directory (relative to path). Unset, the file states none and "
             "the user config's `sources` decide.",
    ),
    force: bool = typer.Option(False, "--force", help="Overwrite an existing .docstrap."),
) -> None:
    """Create a .docstrap file at --path with sensible defaults."""
    from docstrap.config import DOCSTRAP_FILENAME, VALID_LAYOUTS

    if layout not in VALID_LAYOUTS:
        typer.secho(
            f"Invalid layout `{layout}`; must be one of {sorted(VALID_LAYOUTS)}",
            err=True, fg="red",
        )
        raise typer.Exit(code=2)
    target = (path / DOCSTRAP_FILENAME).resolve()
    if target.exists() and not force:
        typer.secho(f"{target} already exists. Use --force to overwrite.", err=True, fg="red")
        raise typer.Exit(code=1)
    resolved_title = title or typer.prompt("Title", default=path.resolve().name)

    from docstrap import settings

    fields = {"version": 1, "title": resolved_title, "layout": layout}
    if docs_root is not None:
        fields["docs_root"] = docs_root
    settings.create_docstrap(target, fields)
    typer.echo(f"created {target}")

    # Auto-register the new .docstrap in the user's stores list.
    from docstrap import user_config

    _, added = user_config.add_store(target)
    if added:
        typer.echo(f"registered in user stores list.")
    else:
        typer.echo(f"already in user stores list.")


@app.command("gitignore-check")
def gitignore_check(
    fix: bool = typer.Option(False, "--fix", help="Add missing entries."),
    project_root: Path = typer.Option(Path("."), "--project-root", help="Project root to check."),
) -> None:
    """Verify the current project's .gitignore has docstrap-relevant entries."""
    from docstrap import gitignore

    result = gitignore.fix(project_root) if fix else gitignore.check(project_root)
    typer.echo(f".gitignore: {result.gitignore_path}")
    if not result.exists:
        typer.echo("  (file does not exist)" + ("  → will be created" if fix else ""))
    for pat in result.present:
        typer.echo(f"  ✓  {pat}")
    for pat in result.missing:
        typer.echo(f"  ✗  {pat}  (missing)")
    if result.ok:
        typer.echo("all required patterns present.")
    elif not fix:
        typer.echo(f"{len(result.missing)} missing. Re-run with --fix to add them.")
        raise typer.Exit(code=1)


@app.command()
def scan(
    config: Optional[Path] = typer.Option(None, "--config", help="Path to .docstrap file."),
) -> None:
    """Read .docstrap; list projects that will be built."""
    from docstrap import scan as scan_mod

    config_path = _resolve_config_path(config)
    docstrap_cfg = _load_config_for_cli(config_path)
    typer.echo(f"config: {config_path}")
    typer.echo(f"title:  {docstrap_cfg.title}")
    typer.echo(f"mode:   {'workspace' if docstrap_cfg.is_workspace_mode else 'standalone'}")
    typer.echo("")
    for p in scan_mod.scan(docstrap_cfg):
        kind_label = "" if p.kind == "project" else f" [{p.kind}]"
        typer.echo(f"  {p.slug:40s}  {p.layout:10s}  {p.title}{kind_label}")
        # `docs:` is the source at the project root, in the form the
        # generated-index scrub script reads; every other source follows.
        if p.docs_dir is not None:
            typer.echo(f"    docs: {p.docs_dir}")
        elif not p.sources:
            typer.echo("    sources: none stated")
        for source in p.sources:
            if source.mount:
                typer.echo(f"    source: {source.path}  ({source.role}, mount {source.mount})")


def _resolve_config_path(explicit: Optional[Path]) -> Path:
    """Find the .docstrap file to use: explicit path, or search upward from cwd."""
    from docstrap import config as cfg_mod

    if explicit is not None:
        return explicit.resolve()
    found = cfg_mod.find_config(Path.cwd())
    if found is None:
        typer.secho(
            "No .docstrap file found in current directory or ancestors.",
            err=True, fg="red",
        )
        raise typer.Exit(code=2)
    return found


def _load_config_for_cli(config_path: Path):
    """Load a .docstrap file for a CLI command, rendering input errors cleanly."""
    from docstrap import config as cfg_mod

    try:
        return cfg_mod.load(config_path)
    except cfg_mod.DocstrapConfigError as e:
        typer.secho(_format_config_error(config_path, e), err=True, fg="red")
        raise typer.Exit(code=2)


def _format_config_error(config_path: Path, error: Exception) -> str:
    detail = str(error)
    lower_detail = detail.lower()
    if "invalid yaml" in lower_detail:
        problem = "The file could not be parsed as YAML."
    elif "yaml mapping at top level" in lower_detail:
        problem = "The file must be a YAML mapping: key/value pairs at the top level."
    else:
        problem = "The file is not a valid .docstrap configuration."

    return "\n".join(
        [
            f"Invalid .docstrap config: {config_path}",
            problem,
            "",
            "If this directory should be ignored by docstrap, write:",
            "  ignore: true",
            "",
            f"Details: {detail}",
        ]
    )


@app.command()
def build(
    config: Optional[Path] = typer.Option(None, "--config", help="Path to a single .docstrap file (single-store mode)."),
    project: Optional[str] = typer.Option(None, "--project", help="Build one project only (single-store mode)."),
    out: Optional[Path] = typer.Option(None, "--out", help="Override output directory."),
) -> None:
    """Build docs.

    - With --config: single-store mode. Reads that .docstrap only.
    - Without --config: multi-store mode. Reads every store registered
      in the user config (see `docstrap stores`).
    """
    from docstrap import build as build_mod
    from docstrap import paths, user_config

    out_dir = (out or paths.build_output_dir()).resolve()

    if config is not None or project is not None:
        # Single-store mode (explicit --config or --project selection).
        config_path = _resolve_config_path(config)
        docstrap_cfg = _load_config_for_cli(config_path)
        typer.echo(f"config: {config_path}")
        typer.echo(f"out:    {out_dir}")
        typer.echo("")
        report = build_mod.build_all(docstrap_cfg, out_dir, only_project=project)
        for r in report.successes:
            typer.secho(f"  ✓ {r.project_slug:40s}  {r.notes}", fg="green")
        for slug, err in report.failures:
            typer.secho(f"  ✗ {slug:40s}  {err}", fg="red")
        typer.echo("")
        typer.echo(f"{len(report.successes)} built, {len(report.failures)} failed. Site root: {report.site_root}")
        if report.failures:
            raise typer.Exit(code=1)
        return

    # Multi-store mode.
    user_cfg = user_config.load()
    if not user_cfg.stores:
        typer.secho(
            "No stores registered. Add one with `docstrap stores add <path>` or use --config <path>.",
            err=True, fg="red",
        )
        raise typer.Exit(code=2)
    typer.echo(f"stores: {len(user_cfg.stores)} registered")
    typer.echo(f"out:    {out_dir}")
    typer.echo("")
    multi = build_mod.build_stores(user_cfg.stores, out_dir)
    for store_path, cfg, report in multi.per_store:
        typer.echo(f"  [{cfg.title}]  ({store_path})")
        for r in report.successes:
            typer.secho(f"    ✓ {r.project_slug:40s}  {r.notes}", fg="green")
        for slug, err in report.failures:
            typer.secho(f"    ✗ {slug:40s}  {err}", fg="red")
    for store_path, err in multi.load_errors:
        typer.secho(f"  ✗ load-error {store_path}: {err}", fg="red")
    typer.echo("")
    total_ok = sum(len(r.successes) for _, _, r in multi.per_store)
    total_fail = sum(len(r.failures) for _, _, r in multi.per_store) + len(multi.load_errors)
    typer.echo(f"{total_ok} projects built, {total_fail} failed across {len(multi.per_store)} store(s). Site root: {multi.site_root}")
    if total_fail:
        raise typer.Exit(code=1)


@app.command()
def serve(
    port: int = typer.Option(8765, "--port", help="Port to serve on (default 8765)."),
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind."),
    site: Optional[Path] = typer.Option(None, "--site", help="Override site root."),
) -> None:
    """Start the docstrap app server (static site + API)."""
    from docstrap import paths, server

    site_root = (site or paths.build_output_dir()).resolve()
    typer.echo(f"serving {site_root} at http://{host}:{port}/")
    server.run(site_root, host=host, port=port)


# --- metadata CLI: status / tag --------------------------------------------


def _lookup_document_for_path(target_path: Path):
    """Resolve a filesystem path to a metadata Document, creating if needed.

    Uses the enclosing .docstrap project (via projectfinder) to determine
    the project slug. If no .docstrap is found, the project slug falls
    back to the file's immediate parent directory name.
    """
    from docstrap import metadata as meta

    abs_target = target_path.expanduser().resolve()
    if not abs_target.exists():
        raise typer.BadParameter(f"path does not exist: {abs_target}")

    existing = meta.get_document_by_path(str(abs_target))
    if existing is not None:
        return existing

    # Derive a project slug from the nearest ancestor with a .docstrap.
    project_slug: Optional[str] = None
    for ancestor in [abs_target.parent, *abs_target.parents]:
        if (ancestor / ".docstrap").exists():
            project_slug = ancestor.name
            break
    if project_slug is None:
        project_slug = abs_target.parent.name

    return meta.get_or_create_document(project_slug, str(abs_target))


@app.command()
def status(
    path: Path = typer.Argument(..., help="Path to the document."),
    new_status: Optional[str] = typer.Argument(
        None,
        metavar="[STATUS]",
        help=(
            "New status. Omit to report the current status. "
            "Valid: draft, proposal, spec, plan, active, archived."
        ),
    ),
) -> None:
    """Report or change a document's status. Direct DB write; no server required."""
    from docstrap import metadata as meta

    doc = _lookup_document_for_path(path)
    if new_status is None:
        typer.echo(f"{doc.current_path}")
        typer.echo(f"  project:  {doc.project}")
        typer.echo(f"  status:   {doc.current_status}")
        typer.echo(f"  tags:     {', '.join(doc.tags) if doc.tags else '(none)'}")
        typer.echo(f"  id:       {doc.id}")
        return
    try:
        doc = meta.set_status(doc.id, new_status, source="user")
    except meta.MetadataError as e:
        typer.secho(str(e), err=True, fg="red")
        raise typer.Exit(code=2)
    typer.echo(f"{doc.current_path}: status → {doc.current_status}")


@app.command()
def tag(
    path: Path = typer.Argument(..., help="Path to the document."),
    tags: list[str] = typer.Argument(
        None,
        metavar="[TAG]...",
        help="Tags to set (replaces existing). Omit to report current tags.",
    ),
) -> None:
    """Set or report tags on a document. Direct DB write; no server required."""
    from docstrap import metadata as meta

    doc = _lookup_document_for_path(path)
    if not tags:
        if doc.tags:
            typer.echo(f"{doc.current_path}: {', '.join(doc.tags)}")
        else:
            typer.echo(f"{doc.current_path}: (no tags)")
        return
    try:
        doc = meta.set_tags(doc.id, tags)
    except meta.MetadataError as e:
        typer.secho(str(e), err=True, fg="red")
        raise typer.Exit(code=2)
    typer.echo(f"{doc.current_path}: tags → {', '.join(doc.tags)}")


@app.command()
def questions(
    path: Path = typer.Argument(
        Path("."), help="A markdown document, or a directory inside one project."
    ),
    as_json: bool = typer.Option(
        False, "--json", help="Emit the findings as JSON instead of a report."
    ),
    every: bool = typer.Option(
        False,
        "--all",
        help="Include earlier `Q<n>` runs, not only the one at the end.",
    ),
) -> None:
    """List the `Q<n>`-numbered questions one project's documents pose.

    The numbering is the marker: an item is a question when its author
    labelled it `Q1`, `Q2`, `Q3`. Nothing is inferred from a question mark,
    so nothing here is a guess. See `docstrap.questions` for the three rules
    that define what counts.

    A directory is read in its project's context, not walked raw: the
    project that owns it is resolved from `.docstrap`, and only the
    documents that project declares are read — its `docs_root`, minus its
    `exclude_dirs` and any subtree declaring `ignore: true`. A path holding
    more than one project has no single context, and is reported as such
    rather than answered library-wide.
    """
    from docstrap import projectscope
    from docstrap import questions as questions_mod

    target = path.resolve()
    if not target.exists():
        typer.secho(f"no such path: {target}", err=True, fg="red")
        raise typer.Exit(code=2)

    scope = None
    documents: list[Path] = []
    if target.is_file():
        found = questions_mod.find(target)
        results = [found] if found or every else []
    else:
        from docstrap import config as cfg_mod

        try:
            scope = projectscope.resolve(target)
        except cfg_mod.DocstrapConfigError as e:
            config_path = cfg_mod.find_config(target)
            typer.secho(
                _format_config_error(config_path or target, e), err=True, fg="red"
            )
            raise typer.Exit(code=2)
        except projectscope.ScopeError as e:
            typer.secho(str(e), err=True, fg="red")
            raise typer.Exit(code=2)
        documents = scope.documents(under=target)
        results = questions_mod.scan(documents)

    def items(document) -> tuple:
        return document.all_labelled if every else document.questions

    if as_json:
        import json

        payload = [
            {
                "path": str(document.path),
                "questions": [
                    {
                        "label": q.label,
                        "number": q.number,
                        "line": q.line,
                        "section": q.section,
                        "checkbox": q.checkbox,
                        "text": q.text,
                    }
                    for q in items(document)
                ],
            }
            for document in results
        ]
        typer.echo(json.dumps(payload, indent=2))
        return

    if scope is not None:
        kind = "" if scope.kind == "project" else f" [{scope.kind}]"
        typer.echo(f"project: {scope.slug}  ({scope.title}){kind}")
        if not documents:
            declared = ", ".join(
                str(s.path) for s in scope.project.published_sources
            ) or "no source at all"
            typer.echo(
                f"no documents here; {scope.slug} declares its documents "
                f"under {declared}"
            )
        typer.echo("")

    base = scope.root_dir if scope is not None else target
    total = 0
    for document in results:
        found_items = items(document)
        if not found_items:
            continue
        total += len(found_items)
        try:
            shown = document.path if target.is_file() else document.path.relative_to(base)
        except ValueError:
            shown = document.path
        typer.secho(f"{shown}", fg="cyan")
        section = None
        for q in found_items:
            if q.section != section:
                section = q.section
                typer.echo(f"    under: {section or '(no heading)'}")
            typer.echo(f"  {q.label:>4}  line {q.line:<5}  {q.text}")
        typer.echo("")

    counted = len([d for d in results if items(d)])
    where = f" in project {scope.slug}" if scope is not None else ""
    typer.echo(f"{total} question(s) in {counted} document(s){where}")


@app.command("generated-indexes")
def generated_indexes(
    path: Path = typer.Argument(
        Path("."), help="A directory inside the one project to report on."
    ),
    as_json: bool = typer.Option(
        False, "--json", help="Emit the findings as JSON instead of a report."
    ),
    every: bool = typer.Option(
        False,
        "--all",
        help="Include the paths a build writes to where no file is present.",
    ),
    show_diff: bool = typer.Option(
        False,
        "--diff",
        help="For a file docstrap does not claim, show it against what a "
        "build composes, so a person can see which it is.",
    ),
) -> None:
    """Report the `index.md` files an earlier build wrote into this project.

    Builds up to 0.0.3 composed their section pages through symlinks and
    landed them in the project; the cleanup of what they left needs to
    know which files are docstrap's. The answer comes from what docstrap
    knows and nothing else: the paths those builds wrote to, and the
    exact bytes they wrote there. A file that matches is `generated`. A
    file that does not is `divergent` and is not claimed — stale output
    of an older build, another tool's page, and a page somebody wrote all
    look the same from here, so the report says so and `--diff` hands
    over the evidence.

    The site still has its section pages. They are composed during the
    Sphinx run and written out as HTML; no build produces markdown for
    one anywhere. This reports what earlier builds left behind.

    Scoped to one project, so an `index.md` under a directory no
    `.docstrap` declares is outside its reach and absent from its output
    rather than cleared by it.

    This command reads. It deletes nothing and repairs nothing.
    """
    from docstrap import config as cfg_mod
    from docstrap import generated_indexes as report_mod
    from docstrap import projectscope

    target = path.resolve()
    if not target.exists():
        typer.secho(f"no such path: {target}", err=True, fg="red")
        raise typer.Exit(code=2)
    if target.is_file():
        target = target.parent

    try:
        scope = projectscope.resolve(target)
    except cfg_mod.DocstrapConfigError as e:
        config_path = cfg_mod.find_config(target)
        typer.secho(_format_config_error(config_path or target, e), err=True, fg="red")
        raise typer.Exit(code=2)
    except projectscope.ScopeError as e:
        typer.secho(str(e), err=True, fg="red")
        raise typer.Exit(code=2)

    findings = report_mod.scan(scope)
    shown = [
        f for f in findings
        if every or f.state != report_mod.ABSENT
    ]

    if as_json:
        import json

        typer.echo(json.dumps(
            {
                "project": scope.slug,
                "docs_dir": str(scope.docs_dir),
                "findings": [
                    {
                        "path": str(f.path),
                        "display": f.display,
                        "state": f.state,
                        "detail": f.detail,
                        "docstrap_wrote_it": f.is_docstrap,
                    }
                    for f in shown
                ],
            },
            indent=2,
        ))
        return

    kind = "" if scope.kind == "project" else f" [{scope.kind}]"
    typer.echo(f"project: {scope.slug}  ({scope.title}){kind}")
    typer.echo(f"docs root: {scope.docs_dir}")
    typer.echo("")

    colours = {
        report_mod.GENERATED: "yellow",
        report_mod.DIVERGENT: "red",
        report_mod.AUTHORED: "green",
        report_mod.ABSENT: "white",
    }
    for finding in shown:
        typer.secho(f"{finding.state:<10}", fg=colours.get(finding.state), nl=False)
        typer.echo(f"{finding.display}")
        typer.echo(f"            {finding.detail}")
        if show_diff:
            body = report_mod.diff(finding, scope)
            for line in body.splitlines():
                typer.echo(f"            | {line}")
    if shown:
        typer.echo("")

    claimed = [f for f in findings if f.is_docstrap]
    unclaimed = [f for f in findings if f.state == report_mod.DIVERGENT]
    typer.echo(
        f"{len(claimed)} file(s) docstrap wrote and claims; "
        f"{len(unclaimed)} at a path an earlier build wrote to that docstrap does "
        f"not claim."
    )
    typer.echo(
        "Nothing was changed. A build of this project writes no file into it, and "
        "composes no markdown anywhere."
    )


if __name__ == "__main__":
    app()
