"""Which project a path belongs to, and which documents that project owns.

A project declares where its documents are — its `sources`, or the
`docs_root` shorthand for one — which directory
names are not documentation — `exclude_dirs` — and, through a nested
`.docstrap` carrying `ignore: true`, which subtrees are off limits
entirely. A bare directory walk honours none of that: it descends whatever
the filesystem holds and reports one undifferentiated pile spanning every
project in the workspace.

This module is the alternative. It resolves a path to the one project that
owns it, using :func:`docstrap.scan.scan` — the same enumeration the build
uses, so a project's document set here is the set the site would publish —
and then enumerates that project's documents and nothing else. A sibling
project's documents are unreachable from a resolved scope, which is the
entire point.

Nothing here reads a document. What a document *contains* is somebody
else's question; see :mod:`docstrap.questions`.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

from docstrap import config as config_mod
from docstrap import scan as scan_mod
from docstrap.projectfinder import SKIP_DIRS
from docstrap.scan import ScannedProject

#: Document extensions a project's scope collects. The corpus is markdown.
DOCUMENT_SUFFIXES: tuple[str, ...] = (".md", ".markdown")

#: Directory names never walked, whatever a project declares: vendored
#: and build trees. A folder of drafts is not one of them by name — it is
#: a source with the role `draft`, declared or added by a plugin, and is
#: off limits because of that role.
NEVER_WALKED = frozenset(SKIP_DIRS)


#: Path steps a document identity never contains. A slug is a *relative*
#: path below `docs_root` with the suffix dropped, so an absolute step, a
#: traversal step and a Windows separator are all shapes no document has.
_NOT_IN_A_DOCUMENT_SLUG = frozenset({"", ".", ".."})


def is_document_slug(slug: str) -> bool:
    """Whether ``slug`` is shaped like something ``document_slug`` returns.

    A document's identity is its path below ``docs_root`` with the suffix
    dropped — ``proposals/0002-the-upgrade-path``. It carries separators
    and that IS the identity; flattening it into one segment is the thing
    this project declined to do, because a document management tool
    handles paths.

    What such an identity never carries is an empty segment, a ``.`` or
    ``..`` step, a leading or trailing separator, or a backslash. Those
    are the shapes a route's greedy path parameter can catch and hand on,
    so the one module that says what a document identity is says which
    ones are not one.

    Not a security boundary — :meth:`ProjectScope.document_for_slug`
    resolves by comparing against the project's own documents and never
    composes a path out of a slug, so a traversal step could not escape
    anything even if it got through. This keeps the answer honest rather
    than accidental.
    """
    if not slug or slug != slug.strip() or "\\" in slug:
        return False
    return all(step not in _NOT_IN_A_DOCUMENT_SLUG for step in slug.split("/"))


class ScopeError(Exception):
    """A path could not be resolved to exactly one project."""


class NoProjectContext(ScopeError):
    """Nothing above the path declares a project."""


class OutsideAnyProject(ScopeError):
    """A config was found, but it declares no project holding this path."""


class SpansProjects(ScopeError):
    """The path holds more than one project, so there is no single context.

    A workspace root is the ordinary case. Reporting across all of them at
    once is the library-wide behaviour this module exists to prevent, so
    the caller is asked to name one instead.
    """

    def __init__(self, target: Path, projects: tuple[ScannedProject, ...]):
        self.target = target
        self.projects = projects
        listing = "\n".join(
            f"  {p.slug:40s}  {p.title}" for p in projects
        )
        super().__init__(
            f"{target} spans {len(projects)} projects, so there is no one "
            f"project context to report.\n"
            f"Name a project's directory (or a document inside it):\n{listing}"
        )


@dataclass(frozen=True)
class ProjectScope:
    """One project, and the documents it declares — the walkable boundary."""

    project: ScannedProject
    config_path: Path

    @property
    def slug(self) -> str:
        return self.project.slug

    @property
    def title(self) -> str:
        return self.project.title

    @property
    def kind(self) -> str:
        return self.project.kind

    @property
    def root_dir(self) -> Path:
        return self.project.root_dir

    @property
    def docs_dir(self) -> Path | None:
        """The source mounted at the project root, or None when none is."""
        return self.project.docs_dir

    @cached_property
    def sources(self):
        """The declared sources, then those the enabled plugins add.

        The same list a build mirrors, so a draft folder a plugin adds is
        off limits here exactly as it is unpublished as a document there.
        Asking creates nothing (:func:`docstrap.plugins.project_sources`).
        """
        from docstrap import plugins

        return tuple(self.project.sources) + plugins.project_sources(self.project)

    def contains(self, path: Path) -> bool:
        """True when ``path`` is the project's root or lies beneath it."""
        return _within(path, self.root_dir)

    def display_path(self, path: Path) -> str:
        """``path`` written the way a person refers to it in this project.

        Relative to the project root when it is inside it, absolute
        otherwise. For display and for recording where something was;
        nothing keys on it, because a path does not survive a rename.
        """
        resolved = path.resolve()
        try:
            return resolved.relative_to(self.root_dir.resolve()).as_posix()
        except ValueError:
            return str(resolved)

    def document_slug(self, path: Path) -> str | None:
        """The docname the build gives ``path``, or None if it gives it none.

        The same identifier the rendered page carries in its
        ``docstrap-doc-slug`` meta tag, which is how anything holding a
        built page can name the source document it came from. A document
        in a source is named by that source's mount plus its path below
        the source with the suffix dropped — for the source mounted at the
        project root, just the path. Where sources nest, the innermost
        holding the document names it. A draft source's files are not
        documents the project has published, so they are named nothing
        here. The project's README, which lives a level above, is the one
        document named otherwise — the markdown layout symlinks it into
        the build as `readme`.
        """
        resolved = path.resolve()
        holding = _holding_source(self.sources, resolved)
        if holding is None or holding.is_draft:
            readme = self.project.readme_path
            if readme is not None and readme.resolve() == resolved:
                return "readme"
            return None
        return holding.identity(resolved)

    def document_for_slug(self, slug: str) -> Path | None:
        """The document that ``document_slug`` would name ``slug``, or None.

        Resolved by asking each of the project's own documents for its
        slug rather than by composing a path out of the slug: a slug that
        names nothing the project declares must come back as nothing, and
        composing would happily point outside the project.

        A slug of a shape :func:`is_document_slug` rejects is answered
        without the walk. It could not match anyway — the comparison is
        against slugs this class produced — but the routes hand this
        whatever a greedy path parameter caught, and saying no to a
        malformed identity in the one place that knows what a document
        identity is beats each route deciding for itself.
        """
        if not is_document_slug(slug):
            return None
        for document in self.documents():
            if self.document_slug(document) == slug:
                return document
        return None

    def documents(self, under: Path | None = None) -> list[Path]:
        """The project's markdown documents, in a stable order.

        The set is what the project declares: everything under each of
        its sources except a draft one, plus its README when it keeps one
        outside them — what a build publishes, less the drafts. Excluded
        directories, ignored subtrees, hidden directories, and a directory
        that is itself a declared source are pruned; the last is walked
        in its own right, or not at all when it holds drafts.

        ``under`` narrows the result to one subtree of the project without
        widening it: a path outside the project yields nothing.
        """
        declared = frozenset(str(s.path) for s in self.sources)
        found: list[Path] = []
        for source in (s for s in self.sources if not s.is_draft):
            found.extend(
                _walk(source.path, self.project.exclude_dirs, declared - {str(source.path)})
            )

        readme = self.project.readme_path
        if readme is not None and readme.suffix.lower() in DOCUMENT_SUFFIXES:
            found.append(readme)

        excluded_suffixes = tuple(
            s.lower() for s in self.project.exclude_file_suffixes
        )
        if excluded_suffixes:
            found = [
                p for p in found
                if not p.name.lower().endswith(excluded_suffixes)
            ]

        if under is not None:
            target = under.resolve()
            found = [p for p in found if _within(p, target)]

        return sorted(set(found))


def scopes(config: config_mod.DocstrapConfig, config_path: Path) -> list[ProjectScope]:
    """Every project the config declares, projects and related alike."""
    return [ProjectScope(project=p, config_path=config_path) for p in scan_mod.scan(config)]


def resolve(target: Path) -> ProjectScope:
    """The one project that owns ``target``.

    The `.docstrap` above ``target`` decides, and the projects it declares
    are enumerated by the ordinary scan. A path inside a project resolves
    to that project — the deepest one, when projects nest. A directory
    holding exactly one project resolves to it as well, since the context
    is still unambiguous. Anything else raises: there is no such thing here
    as a result spanning two projects.
    """
    target = Path(target).resolve()

    config_path = config_mod.find_config(target)
    if config_path is None:
        raise NoProjectContext(
            f"No {config_mod.DOCSTRAP_FILENAME} above {target}, so there is no "
            f"project context.\n"
            f"Point at a document, or register the project with "
            f"`docstrap register`."
        )

    config = config_mod.load(config_path)
    found = scopes(config, config_path)
    if not found:
        raise NoProjectContext(
            f"{config_path} declares no project to report on"
            + (" (`ignore: true`)." if config.ignore else ".")
        )

    owning = [s for s in found if s.contains(target)]
    if owning:
        return max(owning, key=lambda s: len(s.root_dir.parts))

    inside = [s for s in found if _within(s.root_dir, target)]
    if len(inside) == 1:
        return inside[0]
    if inside:
        raise SpansProjects(target, tuple(s.project for s in inside))

    raise OutsideAnyProject(
        f"{target} belongs to no project declared in {config_path}."
    )


class UnknownProjectSlug(ScopeError):
    """No registered store declares a project with this slug."""


def resolve_slug(slug: str) -> ProjectScope:
    """The one project with this slug, across the user's registered stores.

    The server-side counterpart of :func:`resolve`. A request arrives
    holding the project **slug** a built page carries — never a path, and
    never a title — so the lookup starts from the registered-stores list,
    the same outer index ``docstrap build`` reads when given no arguments.

    A slug declared by two stores is an error rather than a first-match:
    two projects answering to one name is the shape that let derivatives
    land in a directory the project does not link to, and guessing which
    one was meant would put them back there.
    """
    from docstrap import user_config

    found: list[ProjectScope] = []
    for store in user_config.load().stores:
        store = Path(store).expanduser()
        if not store.exists():
            continue
        try:
            config = config_mod.load(store)
        except Exception:  # noqa: BLE001 — one bad store must not end the sweep
            continue
        found.extend(s for s in scopes(config, store) if s.slug == slug)

    if not found:
        raise UnknownProjectSlug(
            f"no registered store declares a project with the slug {slug!r}. "
            f"Register it with `docstrap stores add <path-to-.docstrap>`."
        )
    if len(found) > 1:
        where = ", ".join(sorted(str(s.config_path) for s in found))
        raise UnknownProjectSlug(
            f"the slug {slug!r} is declared by more than one registered store "
            f"({where}), so it names no one project."
        )
    return found[0]


def _holding_source(sources, resolved: Path):
    """The innermost source whose directory holds ``resolved``, or None."""
    holding = [s for s in sources if _within(resolved, s.path)]
    return max(holding, key=lambda s: len(s.path.parts)) if holding else None


def _walk(
    docs_dir: Path,
    exclude_dirs: tuple[str, ...],
    other_sources: frozenset[str] = frozenset(),
) -> list[Path]:
    """Every document under ``docs_dir``, the pruned trees left alone.

    Pruning is by directory, so a subtree is skipped whole: an excluded
    name, a hidden name, a build or vendored name, a directory whose own
    `.docstrap` declares `ignore: true`, or one of ``other_sources`` —
    another declared source, which is not this one's to walk.
    """
    if not docs_dir.is_dir():
        return []

    excluded = {name.lower() for name in exclude_dirs}
    found: list[Path] = []
    queue = [docs_dir]
    seen: set[Path] = set()

    while queue:
        current = queue.pop()
        real = current.resolve()
        if real in seen:
            continue
        seen.add(real)
        try:
            entries = sorted(current.iterdir())
        except OSError:
            continue
        for entry in entries:
            if entry.is_dir():
                name = entry.name
                if name.startswith(".") or name in NEVER_WALKED:
                    continue
                if name.lower() in excluded:
                    continue
                if config_mod.ignores_tree(entry):
                    continue
                if other_sources and str(entry.resolve()) in other_sources:
                    continue
                queue.append(entry)
            elif entry.suffix.lower() in DOCUMENT_SUFFIXES:
                found.append(entry)
    return found


def _within(path: Path, ancestor: Path) -> bool:
    """True when ``path`` is ``ancestor`` or lies beneath it."""
    try:
        path.resolve().relative_to(ancestor.resolve())
    except ValueError:
        return False
    return True
