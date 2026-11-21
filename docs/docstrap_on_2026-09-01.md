# docstrap on 2026-09-01

A dated description of docstrap, not a specification. It was reconciled against the code on `main` at
commit `47d7de7` on 2026-09-01, and every section describes what docstrap did as of that reconciliation.
Material describing something abandoned or shipped differently was removed, not annotated; the removals are archived at
[`docs/archive/superseded-2026-09-01.md`](archive/superseded-2026-09-01.md), and
`git log` has the rest.

**This describes a tool in use, not a specification being built toward.** It was titled an MVP
specification; that framing is retired, because docstrap is installed through the stable path, is
dogfooded daily, and builds twelve projects across three registered stores. Nothing here is a
prospectus for a first usable release, and no section describes a stage on the way to one. What comes
*next* is a separate document: [`docs/roadmap.md`](roadmap.md), which
names work by what it delivers and by the version state it would land in.

Where this document and `docs/implementation-record.md` disagreed, the code decided.
Neither document is the other's authority; `packages/docstrap/` is above both.

Section numbers §3 (`.docstrap` schema), §4 (CLI), §5 (metadata), §6 (annotations) and §9 (skills)
are load-bearing — `config.py`, `cli.py`, `paths.py`, `metadata.py`, `annotations.py`, `server.py`
and `tests/test_skill_install.py` cite them, and they are unchanged. §7, §10 and §11 also keep their
subjects. Only §0–§2 moved, because the old §0 (a distillation of the originating session) was
removed as history and the two sections after it closed up; nothing cites those numbers.

**This file lives in `plans/`.** It was written in `proposals/`, which contradicted both its title
and the way the code cites it as settled fact. The captain promoted it on 2026-09-07, along with
[`docs/roadmap.md`](roadmap.md); the folder rule now says what was already
true, that this document has been evaluated and approved.

## §0 Concept

docstrap discovers documentation projects through `.docstrap` files, builds each project's docs via
Sphinx, and aggregates them into one cross-project site. Document metadata — id, project, status,
tags — lives in a SQLite database. Annotations live in a second SQLite database with its own W3C
Web Annotation API. On-page apparatus is layered into the rendered HTML by **tools**, each of which
is a directory carrying a declaration (§7).

Rendering, aggregation and markup are delegated where something proven exists: Sphinx renders,
MyST-Parser is the authoring syntax, `sphinxcontrib-mermaid` draws diagrams, Pagefind indexes for
search, furo themes it. docstrap is the glue and the apparatus.

Three properties hold everywhere and are the reason any of this is safe to point at someone else's
repository. **Nothing is altered in place**: no tool, no reader, no command writes to a source
document. **The tools produce derivatives** — an answer file, a review record, an edit instruction —
beside the original rather than in it. And **a build never writes into a project tree**: it reads a
project and composes its output where it owns the ground, so nothing docstrap generates arrives in a
project's commit cycle. The third was violated for as long as the markdown layout walked a tree of
symlinks and wrote through them; §7.8 is the statement of the rule and the account of what that cost.

### §0.1 In scope

1. The app server (FastAPI): the built static site at `/` and the local JSON API at `/api/*`. One
   process, one port.
2. Two console scripts: `docstrap` (§4.1) and `promdance` (§4.4).
3. The `.docstrap` config file (§3), and a user-level registry of the `.docstrap` files this user
   aggregates together.
4. The metadata database (§5), the annotations database and API (§6), the per-project answer store
   (§8.1), and the addendum a submission delivers (§8.3).
5. Sphinx integration (§7): MyST with `{eval-rst}` pass-through, mermaid, furo, and the declared
   apparatus — the status badge, the questions tool, the review tool, the answer marker and the
   three-panel Q&A instrument — each reaching the generated `conf.py` from its own declaration.
6. The strapdance front-matter reader (§7.4) was removed on 2026-11-21.
7. Promdance storage and backup (§8).
8. Two Claude skills (§9), installed by `docstrap init`.

### §0.2 Not in scope

Editor SPA, inotify daemon, MCP server, MkDocs and Quarto plugin equivalents, team workflows, CI/CD
integration, section-by-section status. §11 is the full list with what is known about each. "Not in
scope" here means not built, and for the watcher it means only that: it is long-standing intent and
the intended mechanism for §7.8.5, listed because no line of it exists yet.

The Annotorious client embed belongs on this list too. The annotations database and its API shipped
for it (§6) and the browser client was never built, so nothing writes to that database today.

## §1 System shape

One Python process on the user's machine. `GET /` and everything under it serves the built aggregate
site. `GET/POST/PATCH/DELETE /api/*` handles metadata, annotation storage, the answers read of §8.2,
and each tool's own collections. The static site mounts last so `/api/*` wins.

The server names no tool's URL. Every tool route is mounted from that tool's declaration by
`docstrap.tools.mounting.mount_all`, and the shape of the path is derived in
`ToolDeclaration.route_prefix` (§7.1). `docstrap serve` binds `127.0.0.1:8765` by default.

Sphinx is invoked as `sys.executable -m sphinx` rather than as a `sphinx-build` binary found on
PATH: a `uv tool install` exposes only `docstrap` on PATH, and resolving Sphinx through the running
interpreter keeps an isolated tool install and `uv run docstrap` on the same dependency resolution.
`docstrap.sphinx_build.sphinx_build_command` is where every invocation gets its argv.

## §2 Aggregation and search

docstrap builds its own aggregate. There is no external aggregate module and no handoff to one.

1. **Per-store aggregate** — `docstrap.build._build_aggregate` composes a page listing the store's
   projects and builds it with the same generated `conf.py` and furo theme the markdown layout uses,
   so the landing page and the project pages are one site. An aggregate page is an index as well, so
   it is composed the way §7.8.2 composes one: no markdown, a model carried in the generated
   `conf.py` because what it lists — which projects built and which failed — is knowledge only the
   run that performed them has. If that build fails, a bare-HTML fallback index is written rather
   than failing the run.
2. **Super-aggregate** — `_build_super_aggregate` does the same one level up, listing every
   registered store and linking into each store's landing page, with the same fallback. The output
   layout is `<out>/index.html`, `<out>/<store-slug>/index.html`,
   `<out>/<store-slug>/<project-slug>/…`.
3. **Search** — Pagefind, run over the finished site by `docstrap.pagefind_step` and surfaced by a
   widget on the super-aggregate index. Best-effort: if the binary is absent the index is skipped, a
   note is left in `_scratch/_pagefind_status.txt`, and the widget stays invisible.

Cross-project tag index, backlinks, and a recent-updated feed do not exist. They were expected from
the module that was never adopted, and nothing replaced them; see §11.

## §3 The `.docstrap` file

Every workspace or standalone repo that wants to be part of docstrap's aggregate has a `.docstrap`
file at its root. For a uv workspace, one root `.docstrap` lists each workspace member independently;
docstrap does not walk into each member looking for its own. For a standalone repo, the single
`.docstrap` at the root describes that repo.

`packages/docstrap/src/docstrap/config.py` is the authority on this schema; what follows is its index.

```yaml
# .docstrap — workspace mode
version: 1

title: platformshoes
short: My infra + tools workspace
icon: 🥾
priority: 10                # sort order in the aggregate landing spine

projects:
  - path: packages/laces
    title: LACES
    short: Pitch and idea capture system
    icon: 🎯
    layout: sphinx           # sphinx | mkdocs | markdown | quarto
    docs_root: docs          # where the project's docs live relative to path
  - path: packages/object-brewer
    title: Object Brewer
  - path: apps/laces-desktop

# Optional: extra directories to include as if they were projects.
related_directories:
  - path: notes/
    title: Session notes
```

For a **standalone repo**, drop the `projects:` array and put the same fields at the top level:

```yaml
version: 1
title: formizer
short: Form-schema authoring and validation
icon: 📝
priority: 40
layout: markdown
docs_root: docs
```

### §3.1 Fields

1. `version` — integer, and must be `1`. Any other value is a load error naming the supported
   version rather than a best-effort parse.
2. `title` — human display name. Optional: defaults to the name of the directory holding the
   `.docstrap` file.
3. `short` — one-line description for the aggregate card.
4. `icon` — emoji or short glyph.
5. `priority` — sort order in the aggregate spine, lower first.
6. `layout` — one of `sphinx`, `mkdocs`, `markdown` (docstrap's bundled MyST+Sphinx), `quarto`.
   Defaults to `markdown`. `mkdocs` and `quarto` are stubs that raise a not-implemented error naming
   the project and pointing at the two that work.
7. `docs_root` — directory relative to the entry containing the docs to build. Defaults to `docs`.
8. `projects` (workspace mode) — list of entries. Only `path` is required; `title` defaults to the
   last path segment, `layout` to `markdown`, `docs_root` to `docs`, so a minimal entry is
   `- path: packages/foo`. Each may also carry `short`, `icon`, `priority`.
9. `related_directories` — extra directories to publish that are not code projects. `path` and
   `title` are required; `docs_root` may be omitted, in which case the directory itself is the docs
   root.
10. `ignore` — boolean, default false. When true, that directory and its whole subtree are skipped by
    every discovery-style scan: project registration, promdance backup discovery, and `.gitignore`
    updates. The minimum useful `.docstrap` is therefore `version: 1` plus `ignore: true`, which is
    what `docstrap firstmate-ignore-check` offers to write. Deliberately declaration-only — nothing
    infers an ignore at runtime.
11. `exclude_dirs` — directory names skipped anywhere in the docs tree at any depth, both as a walk
    skip and as a generated Sphinx `exclude_patterns` entry. Defaults to `["archive", "deprecated"]`.
    An explicit empty list means exclude nothing; omitting the field means use the defaults.
12. `exclude_file_suffixes` — file extensions never indexed or displayed, so a docs tree sharing a
    directory with code does not publish the code. Defaults to a long list of code suffixes (`.py`,
    `.js`, `.ts`, `.sh`, `.go`, `.rs` and so on). A suffix given without its leading dot is corrected
    on load. Also decides whether a project's `README.txt` is publishable (§7.5).
13. `promdance` — boolean, and **tri-state on purpose**: present and `true`, present and `false`, or
    absent meaning this file says nothing. Promdance is opt-out, so absent is not a default value
    written down — it is the absence of a statement, and it does not out-vote a level that did state
    one. Valid both at the top level (the repository) and on one `projects:` entry (that project).
    §8.5 has the three levels and what happens when two of them disagree.

Two path rules live in the scanner rather than the schema. A config-relative path with a dotted
component (`.venv/thing`, `packages/.cache`) is skipped, and a project or related directory inside an
`ignore: true` subtree is skipped even when the config names it explicitly.

Fields accumulate as the tool grows. The schema stays tight.

## §4 CLI commands

Typer-based, two console scripts. Most commands are scoped to a single `.docstrap` file — the current
directory's, one found by walking up, or one named with `--config <path>`. `docstrap build` is the
exception: with no arguments it reads every registered store.

### §4.1 `docstrap`

1. `docstrap --version` — version, executable path, and install origin: `workspace-dev`, `stable`
   with the ref and commit it came from, or `unknown`. See §10.2.
2. `docstrap init` — first-run setup. Creates the user config, data, cache, state, site-output and
   promdance directories, initialises the two SQLite databases, prints every path it resolved, and
   offers to install the Claude skills of §9 to `~/.claude/skills/`. `--install-skills` /
   `--no-install-skills` answers without the prompt; an existing file is overwritten only on
   confirmation, and an identical one is skipped silently. Idempotent. It does not write
   `~/.config/docstrap/config.yaml`; that file appears the first time a store is registered.
3. `docstrap stores list | add <path> | remove <path>` — the user-level registry of `.docstrap`
   files at `~/.config/docstrap/config.yaml`. Individual `.docstrap` files still describe their own
   projects; this is the outer index, and it is what `docstrap build` reads when given no arguments.
4. `docstrap projectfinder [--root <path>] [--all]` — walks below `<path>` (default `.`) reporting
   git repositories without a `.docstrap`. Read-only. `--all` includes the ones that have one.
5. `docstrap register [--path] [--title] [--layout] [--docs-root] [--force]` — writes a `.docstrap`
   and adds it to the stores list. Only `title` prompts when unset, defaulting to the directory name.
   Refuses to overwrite without `--force`.
6. `docstrap gitignore-check [--fix] [--project-root <path>]` — verifies `promdance/` and
   `docstrap-build/` are ignored, adds them with `--fix`, and exits 1 when something is missing and
   `--fix` was not given. `docstrap.gitignore.REQUIRED_PATTERNS` is the list.
7. `docstrap scan [--config <path>]` — lists the projects a build would produce, each with slug,
   layout, title, kind (`project` or `related`) and docs directory.
8. `docstrap build [--config <path>] [--project <slug>] [--out <dir>]` — with `--config` or
   `--project`, builds that one store; with neither, builds every registered store into its own
   subdirectory and writes the super-aggregate above them. Dispatches per declared layout, then
   builds the aggregates and runs Pagefind (§2). Exits 1 if any project failed.
9. `docstrap serve [--port 8765] [--host 127.0.0.1] [--site <dir>]` — starts the app server.
10. `docstrap status <path> [STATUS]` — reports the document's project, status, tags and id; with a
    status argument, sets it. Direct DB write, no server required. The status must be one of the six
    in §5.
11. `docstrap tag <path> [TAG...]` — reports tags, or **replaces** the whole set with the tags given.
12. `docstrap doctor [--root] [--docs-dir] [--firstmate-root] [--interactive] [--fix-plan <path>]` —
    §4.2.
13. `docstrap firstmate-ignore-check [--root] [--write/--no-write]` — detects firstmate operational
    homes by their shape (`AGENTS.md` plus `bin/fm-*.sh` plus `projects/`) and offers to write
    `ignore: true` into a `.docstrap` there, because a firstmate home's project copies otherwise
    double-count during discovery. A setup suggestion only; runtime scans obey only what a
    `.docstrap` declares.
14. `docstrap questions [PATH] [--json] [--all]` — lists the open questions a document or a tree
    poses, found by the author's own `Q1`/`Q2`/`Q3` numbering and by nothing else. No question mark
    is interpreted, so there is nothing to tune and no false positive to argue with; the accepted
    cost is that an unnumbered question is invisible to it. `--all` includes a superseded earlier
    run. Drafts under any `promdance/` path are never walked. The three rules are in
    `packages/docstrap/docs/finding-questions.md`, and they are why this document's own open items
    carry `Q` labels at the end rather than sitting in prose.
15. `docstrap generated-indexes [PATH] [--json] [--all] [--diff]` — the `index.md` files earlier
    builds wrote into this project, and which of them docstrap claims. Read-only, and deliberately
    unwilling to guess: a file is `generated` only when it is byte-identical to what those builds
    wrote, so stale output of an older build and another tool's page both come back `divergent` and
    are left for a person. §7.8.4 is the rule, the frozen bytes it recognises, and the two files that
    motivate it. This is what the per-repository cleanups are driven from; it removes nothing itself,
    and it reaches only directories a `.docstrap` declares.

An invalid `.docstrap` is reported to the user as a config error naming the file, saying what was
wrong with it in a sentence, and offering `ignore: true` as the answer if the directory should not
have been scanned at all. Exit code 2.

### §4.2 `docstrap doctor`

Doctor answers one question about a workspace — **which documents does no project actually own?** —
and it answers it from each document's position rather than by inspecting configuration.

A document is ambiguously scoped when the chain's answer to "which project owns this?" came from the
workspace root, or from nothing at all. The chain has four possible answerers for `project` and three
of them are the same chain *step*, so the report names the answerer as well as the step: the nearest
enclosing `.docstrap` project entry and the uv workspace
member containing the document are real answers; the workspace root and "nothing above it at all"
are findings. Findings are grouped by which of those produced them, because the reason is a property
of the answer rather than of the document.

Alongside that it reports the environment: firstmate operational homes below the root, ignored or
not, with the remedy named as the command that writes rather than doctor itself.

Doctor reports and proposes; it never moves anything, and it exits 0 even with findings, because a
report of what is, is not a failure. `--interactive` asks which directory should own each finding and
shapes the `--fix-plan` output only. `--fix-plan <path>` writes a proposal shell script and refuses to
overwrite. `packages/docstrap/docs/doctor.md` is the full account.

### §4.3 `promdance`

A second console script, because it operates across the whole project space rather than within one
`.docstrap`.

`promdance intern [--root] [--dry-run]` wires every project promdance is on for up to the store:
creates the store entry, places the `promdance/` symlink, and adds the `promdance/` line to
`.gitignore`. With no `--root` the registered stores are the set of projects — which is what "repo by
repo, project by project" means — and with one, every `.docstrap` below it is read instead, so a tree
that is not registered yet can still be repaired. Idempotent: a correct project reports nothing to
do. It **never moves a file**; a project whose `promdance/` is a real directory is reported and left
exactly as found, per §8.6.

`promdance scan [--root]` lists every place a promdance directory belongs under the projects root —
each repository root, each `apps/*` or `packages/*` workspace member there with a `docs` folder, and
each directory a `.docstrap` declares — and for each says whether its `promdance` entry exists and is
linked into the store, and which store entry. `--root` stands in for the configured projects root.
Reads only. §8.9 is the rule.

`promdance status [--root]` reports the store repository's state and, for every one of those places,
its resolved promdance setting, how it is wired, and whether git ignores its `promdance` entry. With
no `--root` the registered stores are read as well, so a project they declare outside the projects
root is still reported. Reads only.

`promdance backup [--root] [--storage-root] [--store-root] [--dry-run] [--fix-gitignores]
[--store-commit] [--store-push]`
scans the project-space root (default the projects root of §8.9, which is `$HOME` unless configured),
reading each repository root and its workspace members with a `docs` folder, and mirrors each discovered `promdance/` directory into a
local git repository under docstrap's data directory, and commits only when the mirrored drafts
changed. Sources come from both project space and the store, merged on the directory the drafts live
in (§8). It reads the live draft directories; it does not move them, delete them, or rewrite project
symlinks. Its walk never descends through symlinked directories, but a discovered project's own
`promdance` entry may be a symlink, in which case it is resolved once and the target's content
copied. `--dry-run` reports the planned copies, commits and `.gitignore` changes without writing
anything, and leaves the store's own git untouched. It also commits and pushes the store by default
(§8.4.4); `--no-store-commit` and `--no-store-push` opt out, and neither creates a repository
anywhere.

**Destinations are unique by construction**, in two namespaces, because the alternative is a safety
net that can refuse to run. A directory in the store lands at `store/<entry>`; a directory that is
not in the store — a project whose `promdance/` is still its own — lands at `projects/<its own
path>`. The path of the directory holding the drafts, which two directories cannot share: a slug put
`~/rlp`'s real directory and the empty store entry `ronin-ledger-panels` on top of each other, and
the *canonical* root put `~/platformshoes/promdance` and its worktree's on top of each other, which
is right for identity and wrong for backup — two checkouts are one project, but their un-interned
promdance directories hold different content and both are unprotected. A genuine overwrite is still
refused, but by an invariant check that should never fire rather than by a rule that regularly did.

**Repairing `.gitignore` files is off by default.** The walk below `--root` finds every `.gitignore`
in the tree, which at a real `$HOME` is forty files in repositories that have nothing to do with
promdance; writing a line into all of them is not what a backup is for, and nobody had seen it
happen because the command had never completed a run. Backup reports them and names `promdance
intern`, which repairs only the projects docstrap knows about. `--fix-gitignores` asks for the sweep
deliberately.

`promdance store` is the store's own git repository:

1. `store init [--store-root] [--branch]` — make the store a git repository. Idempotent, and adds
   `.git/` and nothing else (§8.4.2).
2. `store remote [URL] [--owner] [--name] [--configuration] [--https] [--provider]` — with a URL,
   point `origin` at the repository you created. With none, report the current remote and suggest a
   name for somebody who has not chosen one. Creates nothing anywhere (§8.4.3).
3. `store commit [-m] [--push]` — stage and commit everything; commits nothing when nothing changed.
4. `store push` — push the current branch, setting upstream. Refuses rather than guesses when there
   is no remote, no commit, or no branch, and names what is missing.
5. `store status` — report the repository's state. Reads only.

## §5 Metadata SQLite

One file at `~/.local/share/docstrap/metadata.db`. Owned by docstrap; nothing else writes to it. WAL
mode for concurrent access. `docstrap.metadata.SCHEMA` is the authority; every table is created
`IF NOT EXISTS`.

```sql
CREATE TABLE documents (
  id             TEXT PRIMARY KEY,          -- ULID: 26-char Crockford base32
  project        TEXT NOT NULL,             -- project slug
  current_path   TEXT NOT NULL,
  current_status TEXT NOT NULL,             -- denormalised newest status
  title          TEXT,
  tags           TEXT,                       -- JSON array
  created_at     TEXT NOT NULL,
  updated_at     TEXT NOT NULL
);
CREATE INDEX documents_current_path ON documents(current_path);
CREATE INDEX documents_project      ON documents(project);

CREATE TABLE path_history (
  seq          INTEGER PRIMARY KEY AUTOINCREMENT,
  document_id  TEXT NOT NULL REFERENCES documents(id),
  path         TEXT NOT NULL,
  moved_at     TEXT NOT NULL,
  source       TEXT NOT NULL                -- 'create' | 'rename' | 'external-detect'
);

CREATE TABLE status_history (
  seq          INTEGER PRIMARY KEY AUTOINCREMENT,
  document_id  TEXT NOT NULL REFERENCES documents(id),
  status       TEXT NOT NULL,               -- draft|proposal|spec|plan|active|archived
  content_hash TEXT NOT NULL,               -- git hash-object at transition
  changed_at   TEXT NOT NULL,
  source       TEXT NOT NULL                -- 'user' | 'import'
);

CREATE TABLE content_observations (
  seq          INTEGER PRIMARY KEY AUTOINCREMENT,
  document_id  TEXT NOT NULL REFERENCES documents(id),
  content_hash TEXT NOT NULL,
  observed_at  TEXT NOT NULL,
  observed_at_path TEXT NOT NULL
);
CREATE INDEX content_observations_by_hash ON content_observations(content_hash);

CREATE TABLE file_index (
  project        TEXT NOT NULL,             -- project slug
  docname        TEXT NOT NULL,             -- site-relative name, no suffix
  path           TEXT NOT NULL,             -- absolute, in the project
  parent_docname TEXT NOT NULL,             -- the section page that lists it
  kind           TEXT NOT NULL,             -- 'document' | 'section'
  grouping       TEXT NOT NULL,             -- 'docs' | 'drafts'
  title          TEXT NOT NULL,
  sort_key       TEXT NOT NULL,             -- the entry's own filename
  content_hash   TEXT NOT NULL,             -- git hash-object; '' for a section
  document_id    TEXT,                      -- documents(id) when there is one
  observed_at    TEXT NOT NULL,
  PRIMARY KEY (project, docname)
);
CREATE INDEX file_index_parent ON file_index(project, parent_docname);
CREATE INDEX file_index_hash   ON file_index(content_hash);
CREATE INDEX file_index_path   ON file_index(path);
```

The status column carries a **closed** vocabulary, enforced on write: `draft`, `proposal`, `spec`,
`plan`, `active`, `archived`. `metadata.VALID_STATUSES` is where that rule lives.

No `in_git` column and no cached git state — docstrap queries git at operation time when it needs a
comparison, because git is the source of truth for git.

docstrap never writes to a content file. It read front-matter through §7.4 until that reader was removed on 2026-11-21.

### §5.1 One status vocabulary, two places it is written

Settled by the captain on 2026-08-28 and recorded here on 2026-09-07. There is **one shared status
vocabulary**, the six values above. The metadata database and strapdance front-matter were two places
the same vocabulary was written down, not two vocabularies, until the strapdance reader was removed on 2026-11-21;
the metadata database is now the only one, and the two consequences below describe the time before that.

Two consequences, and they are the whole of the decision.

1. **The write commands keep the two in step going forward.** A command that changes a document's
   status is responsible for leaving the metadata store and the document's front-matter saying the
   same thing from that point on.
2. **An asymmetry between them is reported as a finding, never silently backfilled.** A document
   already holding `strapdance.status: ROADMAP` in front-matter and `proposal` in the database is a
   finding to report, in the way `docstrap doctor` reports what it finds. Nothing rewrites either
   side to agree with the other on its own.

The strapdance reader's own behaviour was unchanged by this: until its removal it preserved an unrecognised value
verbatim rather than rejecting it (`packages/docstrap/docs/strapdance-front-matter.md` §3.2, retired on 2026-11-20), because
the reader never wrote and reporting a value it does not recognise requires reading it first.

### §5.2 The file index

`file_index` is what a published directory contains, answerable without touching the filesystem. The
captain asked for it on 2026-09-17, in the same breath as removing generated markdown: *"files can be
indexed in a database table with paths and hashes."* `docstrap.fileindex` is its one owner and §7.8.3
is what reads it.

It is the one **derived and disposable** table in this database. Drop it and the next build fills it
in; nothing is lost, because everything in it is a restatement of what is on disk. Every other table
here is a system of record. That difference is why the questions below were worth asking rather than
assuming.

#### §5.2.1 Why not `content_observations`

It was the obvious candidate — it already carries a document id, a content hash and a path — and it
is wrong for three separate reasons, any one of which is sufficient.

1. It is an append-only **log**, one row per time a document's bytes were seen. Answering "what is in
   this directory now" from it means selecting the latest observation per document and then
   establishing that the document still exists: a query over history pretending to be a query over
   state.
2. Its `document_id` is a foreign key, so every indexed file would need a `documents` row first.
   Indexing a docs tree would mint a ULID for every markdown file in it — into a store whose document
   rows are already 59 of 64 test residue awaiting the captain's ruling.
3. Mixing a disposable projection into a system-of-record table means a reader can no longer tell
   which rows may be discarded. The distinction is worth a table.

#### §5.2.2 Why the same database, all the same

Because the rename requirement is a join. `documents` and `path_history` live here, and a separate
file would push that join into Python, need a second connection owner, a second schema and a second
entry in `docstrap.paths` — for no gain. The captain's own phrasing pointed the same way: *"a join
table or json column in the database."*

Adding a *table* is also the one schema change that is safe while §4.18's upgrade path does not
exist. `metadata.SCHEMA` is replayed with `CREATE TABLE IF NOT EXISTS` on every open, so a table
missing from an existing database is created by the replay and reaches every database already out
there. A **column** added to a table that already exists is not, and silently is not. That asymmetry
is written into `metadata.py`'s own docstring, because it is the difference between this change being
safe and it being the defect `docs/proposals/0002-the-upgrade-path.md` exists to fix.

#### §5.2.3 How a rename survives

Two ways, and which applies depends on whether the metadata store knows the file.

1. **It has a `documents` row.** `document_id` carries the identity, and the rename is handled where
   renames are already handled: `documents.current_path` moves and `path_history` gains a row. The
   index row is re-keyed on the new docname and still points at the same document. The index keeps no
   history of its own — a second history is the thing that orphans records.
2. **It has none**, which is the ordinary case for a file nobody has tagged. Then `content_hash` is
   the identity: the same bytes under a new path are a move rather than a deletion and an unrelated
   arrival. `file_index_hash` is what makes that lookup cheap and `fileindex.by_content_hash` is the
   query.

`document_id` deliberately declares no `REFERENCES`. A derived projection must never be able to
refuse a write to the system of record, and with `PRAGMA foreign_keys = ON` a stale index row would
do exactly that.

#### §5.2.4 Written one path at a time

`fileindex.record` puts one entry in place and `fileindex.forget` / `fileindex.forget_path` take one
out. `fileindex.reconcile` is built from those and adds only *"and delete what I did not mention"*;
it is what a build calls, because a build has just looked at the whole tree anyway.

The primitives are the one-path calls rather than the whole-project one because the watcher of
`docs/roadmap.md` §4.13 will only ever know one path at a time. There is no invalidation to perform
alongside the write and no cache to sweep, because nothing downstream of this table is stored.

## §6 Annotations SQLite

Separate file at `~/.local/share/docstrap/annotations.db`. Separate file rather than separate tables,
so annotations can be backed up, migrated, or replaced independently of metadata. Stores W3C Web
Annotation JSON-LD documents; ids are opaque URNs.

```sql
CREATE TABLE annotations (
  id           TEXT PRIMARY KEY,             -- annotation URI
  target_doc   TEXT NOT NULL,                -- docstrap://document/<id>
  motivation   TEXT,                          -- assessing | commenting | questioning | etc.
  body_json    TEXT NOT NULL,                 -- serialized W3C body
  target_json  TEXT NOT NULL,                 -- serialized W3C target (selectors)
  creator      TEXT,
  created_at   TEXT NOT NULL,
  updated_at   TEXT NOT NULL
);
CREATE INDEX annotations_target_doc ON annotations(target_doc);
```

The app server exposes a **minimum subset of the W3C Web Annotation Protocol**: `GET
/api/annotations?target=<doc-uri>`, `POST /api/annotations`, `PATCH /api/annotations/<id>`, `DELETE
/api/annotations/<id>`. Not the full protocol — no annotation containers, no LDN inbox, no
pagination.

**This store is Annotorious's**, settled by the captain on 2026-09-07. It was built for that client —
`docstrap.annotations`' own module docstring says the API subset is "enough for Annotorious to read
and write" — and Annotorious remains the intended client. The client is a real external dependency
and has not been added; the store and its API are therefore complete and unexercised, which is the
state and not a plan. When the embed is built is not decided here; see §11.

**Answers to a document's questions do not belong here.** They are keyed to a question and go to the
answer store of §8.1. Two reasons, and the second is the load-bearing one. The store is Annotorious's
by the paragraph above, so a second writer with an unrelated shape would be squatting in it. And
`creator` models a different audience: an annotation comes from whoever is reading the deployed site
— a user-system id belonging to the deploying organisation, a Discord or Telegram handle, an email
address — while an answer to a `Q<n>` comes from whoever owns the document and is a decision about
it, not a reader's remark on it.

## §7 Sphinx integration and the tools

Sphinx is the render engine. A project with `layout: sphinx` brings its own `conf.py` and docstrap
invokes it without modification. A project with `layout: markdown` gets docstrap's bundled
configuration, generated per build into a scratch directory: MyST with `colon_fence`, `deflist`,
`fieldlist`, `tasklist`, `linkify`, `smartquotes`, `substitution` and inline/block attributes;
heading anchors to depth 4; ```` ```mermaid ```` fences routed through the `sphinxcontrib.mermaid`
directive; the furo theme; and source copying turned off so raw markdown is not published.

**Authoring** is MyST-Parser. Every Sphinx directive and role is invokable from MyST via the
fenced-directive syntax, and `{eval-rst}` gives full RST pass-through for the rest. Section numbering
is Sphinx's `sectnum` or the toctree `:numbered:` option.

The generated `conf.py` carries `docstrap_project_slug`, the scanned slug, distinct from the
human-readable `project` title. The tools read it back from the page context. A tool addressing a
project by its title wrote derivatives into a directory the project does not link to, and nothing
errored — which is why the slug is carried explicitly.

### §7.1 A tool is a directory with a declaration

The on-page apparatus is organised into **tools**. A tool is usable from the standard document view:
it works in place, and the page you were reading is still the page you are looking at — an overlay or
a popover is still a tool. An **instrument** brings up a separate component or navigates away. The
boundary test is only that.

Each tool has one small declaration in `declaration.py` in its own directory, and the declaration is
the single source of truth. Three consumers read it and none keeps a copy of what it says.

1. **The server** derives the route prefix. The target picks the base and the tool names the
   collection it owns, so a document-targeted tool declaring `api_collection="reviews"` gets
   `/api/promdance/{project}/{doc_slug}/reviews`. A tool owning no collection declares
   `api_collection=None` and mounts nothing. A tool that serves its collection under the *other*
   base as well declares `also_scoped_to`, and `route_prefixes` is then both; the server's route
   table is compared against exactly that, so nothing can mount a path no declaration produced.
   `{doc_slug}` carries a **path**, because a document's identity is its path below `docs_root`
   with the suffix dropped (§7.1). The declaration's spelling is what the launcher fills in for the
   browser and `as_server_path` marks the parameter for the router; nothing flattens the identity.
   The two bases stay distinguishable by segment count, which holds only while no route is deeper
   than a base plus one static collection — `check_route_separation` refuses one that is, at mount
   time, so the ambiguity a greedy parameter reopens cannot be declared into existence.
2. **The launcher** reads `kind` and `target` to decide whether to offer the tool where the reader is
   standing. A project-targeted tool is never offered on a lone page with no project to act on.
3. **The build** names the bundles `docstrap-<id>.js` and `docstrap-<id>.css`, and builds the
   generated `conf.py` `extensions` list from the declarations, so a new tool reaches the built site
   without the layout template being edited.

Adding a tool is adding a directory; removing one is deleting it. There is no registration list, so
forgetting to append to one cannot happen. `packages/docstrap/docs/tools-and-instruments.md` is the
full account, including the enumerated extension points a tool may use and the rule that it may use
nothing else.

**A tool's UI is Svelte**, compiled to the bundle its declaration names, with scoped component
styles. This replaced an earlier vanilla-JavaScript, no-build-step rule on the captain's decision of
2026-08-27 — *"svelte unless it's truely tiny"*. Two things still follow from the tool/instrument
boundary: per-page cost is a tool's problem and not an instrument's, since a tool is registered on
every rendered page and runs on every page shown inside the viewer — a page opened on its own runs
only the button that opens it there (`docs/tools-and-instruments.md` §3.2); and Skeleton is for instruments only, because a tool renders inside a page whose
styling Sphinx and furo own. Built bundles are committed, so installing or running docstrap needs
Python only — Node is a dependency of *changing* a tool's UI, not of using one.

**One launcher owns what is showing.** Before it, each widget injected its own floating button into
the same corner with no arbitration. The decision of what to offer is computed in Python and
serialised into the page; the client renders what it is given and never needs to know a tool exists.
Visibility persists in `localStorage`, and each declaration's `default_visible` decides what happens
before anyone has said otherwise. A page with every tool hidden reads as a plain document, and that
is held up by three things: the built HTML carries no tool chrome at all, "Dismiss" removes the
launcher itself (Alt+T brings it back), and anything a tool puts on the page that is apparatus rather
than document carries `.docstrap-chrome`, which is excluded from print.

### §7.2 The pieces of apparatus

1. **status** (`docstrap.tools.status`) — target document, no collection of its own, visible by
   default. Renders the document's docstrap status as a badge beside the page title, read from the
   shared `/api/documents` metadata API. Degrades to nothing when the app server is not running.
2. **qa** (`docstrap.tools.qa`) — target document, owns `answers`, visible by default. Provides the
   `docstrap-questions` directive, usable as `.. docstrap-questions::` in RST or
   ` ```{docstrap-questions} ` in MyST, requiring a `:question-id:`. The author's prompt is document
   content and always reads; the answering apparatus below it is chrome and is gated on the tool
   being shown, so with the tool hidden a question is a plain callout with nothing to submit.
   Submitting POSTs to the declared route, and docstrap writes the answer into the project's keyed
   answer store under the directive's own `:question-id:` (§8.1). Answering the same question twice
   supersedes the earlier answer.
3. **review** (`docstrap.tools.review`) — target document, owns `reviews`, hidden by default. Places
   a tri-state control (empty → ✓ → ✗ → empty) after each qualifying prose sentence, skipping
   `pre`, `code`, links, headings and the launcher's own chrome, and one further mark inside each
   `h2`/`h3`/`h4` for the section as a whole. On submit it writes
   `<doc-slug>_review-<timestamp>.md` to promdance: YAML front-matter carrying the machine-collected
   marks and counts, and a body with empty slots for the reader's reactions to the ✗ sentences.
4. **qapanels** (`docstrap.tools.qapanels`) — target **project**, also scoped to **document**, an
   **instrument** rather than a tool, owns `qa`, never visible by default. The three-panel Q&A mode of
   §7.6: the launcher gives it a launch action rather than a toggle, and it takes the view. It is the
   surface for answering a whole project's open questions in one sitting, and it writes through the
   same answer store the qa tool does (§8.1). It is the one tool that declares a second scope, so its
   collection is readable both project-wide and narrowed to one document; §7.6(1) is why.
5. **answered** (`docstrap.tools.answered`) — target **document**, a tool, owns no collection, visible
   by default. Marks each `Q<n>` in the rendered page and shows its current answer beneath it,
   reading the server's `/api/answers` of §8.2 rather than any collection of its own. §7.7 is what it
   does, and why it is two halves.
6. **datatable** (`docstrap.tools.datatable`) — target document, a tool, owns no collection, visible
   by default. Provides the `docstrap-datatable` directive, which names a JSON file beside the page
   holding columns and rows. The build renders it as a plain HTML table, which is the document, and
   embeds the same data for the tool to draw a sortable, filterable table from inside the viewer;
   link cells naming a document are resolved to its built URL at build time. Nothing is fetched.
   `packages/docstrap/docs/datatable.md` is the file format and the behaviour.
7. **tasks** (`docstrap.tools.tasks`) — target document, a tool, owns `decisions`, visible by
   default. Provides the `docstrap-tasks` directive, which names the `tasks.json` firstmate writes
   beside the page. The build renders a plain table grouped by project and embeds the tasks; inside
   the viewer the tool groups them by project and unit or by status, drills into a group with the
   drill-down kept in the viewer's address, sorts and filters with the data table's rules, and
   records one decision per task as an answer in the store of §8.1. `packages/docstrap/docs/tasks.md`
   is the behaviour and the decision key.

### §7.3 What is deliberately not built here

Build-time block provenance stamping, the quick-update tool that needs it, and the classifier
instrument. Each is a later phase, and the declaration surface landed first so the classifier would
not become the fourth widget bolting its own button into the same corner. The three-panel Q&A
instrument was on this list and is now built; §7.6 is what it does.

### §7.4 The strapdance front-matter reader

**The reader was removed on 2026-11-21, with every caller of it; nothing in docstrap reads a `strapdance`
namespace now. What follows describes it as it was.**

The shared document-context standard for docstrap and promdance: YAML front-matter under a single
`strapdance` namespace, with a fallback chain to the document's position and content when a field is
absent. **No document has to be touched to participate.**

There is **one reader implementation**,
`packages/docstrap/src/docstrap/strapdance.py`, used by both runtimes. A second implementation is
what caused the split-slug defect that orphaned submitted answers.

Every field resolves explicit → position → content → an outright stated unknown, and the reader
reports which step answered, so a consumer can always show what was declared against what was
inferred. It reads only its own namespace: every other top-level key is preserved byte for byte and
ignored, and an unrecognised namespace is never an error. **The reader never writes.** A malformed
block is reported through `ctx.errors` and the file left exactly as it was; the document still
resolves through the rest of the chain. Three states are distinguished: not yet examined, examined
and declined (a positive recorded fact, so a continual tool does not re-offer the same document
forever), and classified.

`packages/docstrap/docs/strapdance-front-matter.md` (retired on 2026-11-20) was the hand-authoring guide and the account of
the namespace, the chain, and the three states.

### §7.5 Project READMEs

A `docs_root: docs` entry points the build at `<project>/docs`, so a project's own `README.md` — one
level above it — was absent from the site. The markdown layout brings it in as one further document,
symlinking that single file into the build's scratch directory rather than exposing the project root.
It joins the Docs listing beside everything `docs_root` yields; it is not the landing page. The
landing page is composed (§7.8.2), and nothing in a docs tree displaces it — a docs tree holds no
index file at all (§7.8.6).

`README.md` and `README.txt` both count, matched case-insensitively, markdown preferred when both
exist. A `.txt` README is wrapped in a generated page carrying the text verbatim in a literal block,
because `.txt` is not markdown and the generated `conf.py` parses only `.md` and `.rst` — plain text
is published as written rather than reinterpreted as markup. A README whose suffix
`exclude_file_suffixes` excludes is not published, and a README already inside `docs_root` is not
added twice. `docstrap.scan.find_readme` decides all of it.

### §7.6 The three-panel Q&A mode

An instrument, `docstrap.tools.qapanels`, launched from the document view and taking the view when it
opens. It exists because a project's open questions are answered in one sitting rather than one page
at a time: the qa tool of §7.2(2) answers the question in front of you, and this answers the twenty
in the project.

Three panels, and the selection is what binds them.

1. **The question list.** The questions in scope, grouped by document, with single selection. The list
   is a **scan** performed per request through `docstrap.projectscope` and `docstrap.questions` — the
   same reading `docstrap questions` does, by the author's own `Q<n>` labels and by nothing else.
   There is no index and no store of questions, and this instrument introduces neither; the response
   is derived and disposable, which is the rule `packages/docstrap/docs/finding-questions.md` states
   and §8.1 keeps.

   **The scope is an explicit choice, and the header is where it is made.** The collection is readable
   under both bases — `/api/promdance/{project}/qa` for the whole project and
   `/api/promdance/{project}/{doc_slug}/qa` for one document — and the panel offers both. It **defaults
   to the document** it was opened on, because the instrument is opened while reading something and
   that something's questions are what is wanted; the project is the deliberate wider view, and on a
   page that is not a document (an aggregate index) it is the only one offered.

   The second base is declared, not improvised: `ToolDeclaration.also_scoped_to` names it, both
   prefixes come from the one `_TARGET_ROUTE_BASE` map, and `route_prefixes` is what the server's
   route table is compared against — so a tool that mounted an undeclared path fails the comparison.
   The launcher resolves both into the page as `route` and `altRoute`, so choosing a scope in the
   browser is choosing between two URLs the declaration produced rather than editing one. The write
   stays on the project base alone; an answer's payload already names the document it answers.

   This replaced a single project-wide read that took no document argument, so opening the instrument
   while reading one document listed every question in the project (roadmap §4.11 item 5).
2. **The answer editor.** A plain `<textarea>` following the selection, saving as you type. No editor
   library: the reusable thing here is the autosave *behaviour*, not an editor component. That
   behaviour is laces', specified in `packages/laces/docs/adr/0013-autosave-event-driven-firing.md`
   and `packages/laces/docs/adr/0007-no-buttons-transitions-autosave.md`, and docstrap **cites** those
   ADRs as its referent rather than restating them as decisions of its own — they were written for
   laces and they are accepted there. Event-driven, never a clock: a form-level `oninput` is the
   canonical trigger with a Svelte `$effect` on the tracked state as the backstop for programmatic
   changes, one debounce reset by every trigger firing one save per typing burst, Ctrl/Cmd+S
   cancelling the pending debounce and firing immediately, and a binary indicator whose absence is
   the unsaved signal. Every save it makes is a draft; submitting is the list's one Finish (§8.1.3).
3. **The document reference.** The rendered page the selected question was found in, scrollable, read
   only. It is the built site's own page in an `<iframe>`, so what is read here is exactly what is
   published.

The instrument writes nothing but answers, and it writes them where §8.1 says. It never alters a
source document, which is the property §0 states and every tool holds.

### §7.7 The answer beneath the question

A reader of a question document could not tell an answered question from an open one, could not see
the answer, and had no indication that anything had been answered at all. That is roadmap §4.11 item
4, and it is the structural one: §0 correctly forbids appending answers into the source, but **"not
appended" was allowed to become "not linked"**. Derivative beside the original is a storage rule, not
a reason for the reading surface to show one without the other.

The `answered` tool corrects it. Each `Q<n>` gets its current answer rendered beneath it, and each
unanswered one gets an unmistakable open marker. Nothing is written to the document; §0 holds
unchanged, and a build over a read-only checkout is still safe.

**Anchored at build, resolved at serve**, and the split is the design.

1. **The build** marks each `Q<n>` block in the rendered doctree with `docstrap-question` and a class
   naming its label. That is a rendering fact about the *derivative*, in the same way a heading anchor
   is — the source file is byte-identical afterwards. Which blocks get marked is not decided here:
   `docstrap.questions` owns the three rules and is asked, so the document's last ascending run is
   marked and a superseded earlier run, a quoted label, a fenced one and a `Q1` mentioned mid-sentence
   are all left alone exactly as `docstrap questions` leaves them.
2. **The client** reads `/api/answers/{project}/{doc_slug}` — the live store, through §8.2 — and
   mounts one note after each marked block. It composes no path beyond that server API, and it owns
   no collection: it shows what the store knows and is not a second way to read it.

Baking answers into the HTML at build time was rejected. Answers change constantly and a document
does not rebuild when they do, and a **stale decision shown as current is worse in a decision system
than no decision shown at all**. The consequence is the honest one: a page served with no docstrap
behind it is the document its author wrote, unmarked.

The note shows the answer as written, newlines and all, rather than re-parsing it as markup —
quietly reinterpreting a decision is a way to change what it says. It carries the date, the answerer
when one was named, and how many earlier answers were superseded (§8.1.4). It never shows a draft,
because §8.2 never returns one.

### §7.8 An index is transient, transparent, and only ever HTML

**A docstrap build produces no markdown.** Not in the project, not in the build, not in a scratch
directory, not as a temporary file deleted afterwards. A section page, a project's landing page and a
store's aggregate page are all pages docstrap decides rather than pages somebody wrote, and each of
them is composed as a document node tree and rendered straight to HTML. There is no markdown stage
and nothing markdown-shaped is written down at any point.

That is the captain's instruction of 2026-09-17 and it arrived in two parts. First: *"no the
generated indexs should be transient and transparent. 100 documents distributed over several
directories per project with even 50 projects is not that much processing. the index shoud be only in
html not in md files. any index.md files should be purged and a tranisent part of the system. files
can be indexed in a database table with paths and hashes."* Then, when asked whether a markdown step
could stay inside the build because Sphinx's `toctree` is a markdown construct: *"why cache as md if
the output is index html files? NO MD cache for indexes. Anything worth cacheing can be embeded the
html files that are generated or in a join table or json column in the database."*

The reasoning in that second answer is the better statement of the rule, so it is the one to keep:
**an intermediate that exists only to be converted is not earning its place.** The output is HTML. A
markdown step is a cache of the wrong thing in the wrong format, and the one docstrap had is the
artefact that leaked into five repositories.

**A docstrap build also never writes into a project tree.** Not an index, not a stub, not a
placeholder, not anything. This is the older and larger invariant, it is a requirement rather than an
implementation preference, and it is the third of the properties §0 names as the reason docstrap is
safe to point at someone else's repository. A build that mutates what it renders is not a renderer;
it is an editor nobody asked for, and its output arrives in the commit cycle of every project it
touches.

State the other half just as plainly, because neither change is a retreat. **Indexing is not optional
and it is not a person's job.** Every directory that is part of a site gets a section page, always,
composed by the tool with nobody asked to opt in, maintain a list, or remember a convention. A
documentation system whose completeness depends on an agent following a rule is not autonomous, and a
rule an agent follows is not deterministic. The defect was never *that* section pages exist — it was
where they were written, and then what they were written in.

#### §7.8.1 What went wrong

The markdown layout populated its scratch directory by symlinking each entry of the project's
`docs_root` into it, then walked that scratch directory with `os.walk(..., followlinks=True)` and
wrote an `index.md` into every subdirectory that had none. A symlinked *directory* is a hole through
the build into the repository behind it. The walk went through the hole, and the writes landed in
the projects — fifty-five such files tracked across `platformshoes`, `rlp`, `trk_tdp`, `dkp` and
`formizer`. Seven of them were committed in `rlp` under the message *"index.md in docs for docstrap
maybe are being added to the repo? this does not look right but moving forwared"*, which is the
system telling its author something was wrong and being overruled by the need to get on with the
day.

Two further consequences followed from the same mechanism and are worth naming, because each is a
reason the arrangement could not simply be tidied. A generated file was never regenerated — the
"user wrote their own index" check skipped any directory that already had one — so the first build's
output became permanent and went stale in place; `rlp/docs/specs/index.md` still says *(no documents
in this section)* and then lists one. And `_ensure_docs_dir_exists` wrote a second kind of file
entirely, creating a project's `docs_root` when it was missing and leaving a placeholder document in
it. That is the same defect in a smaller form: a directory that is not there in somebody's
repository is not docstrap's to create.

#### §7.8.2 How a page with no source becomes a page

This is the decision the "HTML only" instruction turns on, so it is recorded with what was rejected
and what it cost.

**The difficulty, stated plainly.** Sphinx's `toctree` is a markdown/rST construct, and section pages
existed as generated markdown *because that is how the sidebar gets built*. Furo's sidebar is the
global toctree; a document in no toctree is not in the sidebar and warns that it is not. So "no
markdown" means either that section pages leave Sphinx's toctree mechanism entirely, or that they
become Sphinx documents without being Sphinx *files*.

**What Sphinx allows.** `Builder.read_doc` is `@final` and its first act is
`env.doc2path(docname).read_text()`. There is no supported way to hand Sphinx a document that is not
on disk. What *is* supported, and documented, is choosing the **parser**: `source_suffix` maps a
suffix to a filetype and `app.add_source_parser` registers what parses it.

**What was chosen.** A section page is a **zero-byte marker** named `index.docstrap-section`, written
into the build's scratch tree and nowhere else, whose parser ignores the (empty) content entirely and
composes the page from `docstrap.sectionindex.compose` — a docutils `section`, a `title` and a
`sphinx.addnodes.toctree` built node by node. Sphinx renders it to `index.html` with the rest of the
site: same theme, same sidebar, same previous/next links, no warnings. The same mechanism with a
second filetype composes the aggregate pages of §2, whose model travels in the generated `conf.py`
because what they list — which projects built and which failed — is knowledge only the run that
performed them has.

A project's landing page is composed the same way and by the same marker, with no case for a project
that wrote its own. There used to be one: an `index.md` in `docs_root` was symlinked into the build,
read by Sphinx as the document it is, and had the navigation appended to its doctree on
`doctree-read`. §7.8.6 removed it — a docs tree is not allowed an index file — so the `doctree-read`
handler went with the case rather than being left to guard a state that cannot arise.

**What was rejected, and why.** Three ways to reach zero files were considered and all three buy it
at the price of private Sphinx state, which for an integrator is a tool that breaks on a point
release: writing synthesised doctrees into `env._pickled_doctree_cache` and
`env._write_doc_doctree_cache`; a `Project` subclass rewriting the docname-to-path bijection so many
docnames share one empty source; a `Path` subclass whose `read_text` returns composed content. A
fourth — `html_additional_pages`, which renders a template to a page with no source at all — is
public API and does work, but such a page is in no toctree, so the sidebar loses its structure and
every document under a section warns. That is losing the navigation, which was not on offer.

**The cost, stated rather than approximated.** One empty file per section exists inside the build's
scratch tree. It is not markdown, carries no index, cannot go stale, cannot be mistaken for a
document, and never leaves the build — but it is a file, and a literal reading of "transient and
transparent" would rather it were not there. Reaching zero costs the coupling above, and the captain
was explicit that a markdown intermediate was not an acceptable price; an empty marker is the
cheapest thing that is neither.

**And the tree itself is still mirrored** rather than symlinked whole, which is the older half of the
fix and unchanged. `_mirror_tree` walks the project's `docs_root` and, for every directory, makes a
real directory in the build; for every file, a symlink to the real document. Sphinx reads the same
bytes through the same docnames it always did, and there is no symlinked directory anywhere in the
build for a marker to be written through. A directory the site does not publish — dotted,
underscored, excluded, vendored — is linked rather than mirrored, because nothing is composed inside
it and nothing descends into it.

Two rules keep the invariant and either alone would be enough, which is deliberate: the one that
holds structurally can be broken by a future change without anyone noticing, and the one that holds
at the moment of writing cannot.

1. **There is nothing to write through.** Every directory in the build is one the build made. The
   section walk additionally does not follow symlinks, so a link that appeared anyway is a dead end.
2. **A generated write checks where it is going.** Every file the layout generates goes through
   `_write_generated`, which resolves the destination's parent directory and raises `LayoutError`
   unless it is inside the build. Nothing in the layout can reach that error today; it is there for
   the change that reintroduces a symlinked directory and does not notice.

A missing `docs_root` is now reported rather than created — on the landing page, and in the build
result's notes — and the promdance draft area is mirrored the same way as the docs tree. Storage is
docstrap's own, but a page composed *into* storage persists there, is read back as a landing page
the next build must not overwrite, and goes stale exactly as `rlp/docs/specs/index.md` did. Composing
into the build instead means a generated page cannot outlive the build that made it, anywhere.

#### §7.8.2.1 Nothing is cached, and the numbers say so

The captain's licence for recomputing rather than storing was a cost argument — *"100 documents
distributed over several directories per project with even 50 projects is not that much
processing"* — so it was measured rather than assumed.

| measured                                                            |        |
|---------------------------------------------------------------------|--------|
| index 5 000 documents across 50 projects (read, hash and title each) | 0.65 s |
| compose all 450 section pages from the table                         | 0.27 s |
| index one 100-document project                                       | 0.01 s |
| sphinx-build of that same project                                     | 3.06 s |

Indexing a project costs 0.4% of the build that publishes it. He is right, and there is therefore no
invalidation machinery, no staleness check and no cache layer — none of which would earn back what it
costs to own.

Two hot spots were found while measuring and both are fixed rather than tolerated, because either
would have made the recompute-always design look expensive when it is not. `strapdance.read_context`
reloaded the enclosing `.docstrap` and globbed the uv workspace per document — right for a reader that
wanted the whole context, 1.7 ms against 1.6 µs to hash the same bytes — so `strapdance.read_title`
ran the title chain and stopped (both were removed on 2026-11-21; a title is now the first heading, else
the filename). And a per-file
`get_document_by_path` opened a connection each time, at 222 µs a file, replaying the whole schema;
`metadata.ids_by_path` answers for every document in one query.

The one thing a build still puts in a project root is the `promdance` symlink of §8.2. It is a link
rather than content — the drafts behind it live outside the repository — it is never rewritten once
present, and it is not what this section is about. Nothing else is created, and a test holds the
build to exactly that by fingerprinting a project tree before and after.

**It is not quite git-invisible, though, and the gap should be stated rather than assumed away.**
`docstrap gitignore-check` requires `promdance/` be ignored, but it is a command somebody runs, not
something a build enforces: in a repository where it has not been run, the link a build creates shows
up in `git status` as an untracked entry. `platformshoes` is such a repository today — its
`.gitignore` names neither `promdance/` nor `docstrap-build/`. That is a smaller problem than a
committed generated document (a symlink to a user-specific absolute path is unlikely to be committed
by accident, and nothing regenerates it), but the honest statement of the invariant is that a build
composes no *document* into a project tree and attaches one git-ignorable link that the project is
expected to ignore.

That gap narrowed with §7.8.2 without being closed. A build's scratch tree used to hold composed
markdown, which in a repository whose `.gitignore` does not name `docstrap-build/` is a generated
document a person or a `git add -A` can see. It now holds empty markers, so there is no longer a
generated document anywhere a git repository can reach — but `docstrap-build/` is still untracked
rather than ignored, and `gitignore-check` is still a command somebody runs.

#### §7.8.3 One composer, for the build and for what comes after

`docstrap.sectionindex` owns two facts and is the only place either is decided: **what a section page
contains** (`compose`) and **which directories are sections** (`is_section_dir`, and `sites` over
it). Neither function writes, and `compose` no longer reads a directory at all — it asks the file
index of §5.2. Delete the project tree and it still answers, which is what makes the same composer
serve a build, a report and a watcher that has seen one event.

Three callers, one answer, no second implementation — because a second implementation of a docstrap
fact is what orphaned submitted answers once already, and here it would mean a report that disagrees
with the build about which files are the build's.

#### §7.8.4 Telling generated from authored, deterministically

Stopping the writing does not identify the fifty-five files already committed, and the per-repository
cleanups that remove them need a list they can trust. `docstrap generated-indexes [PATH]` (§4.1) is
that list. It decides from what docstrap knows rather than from what a file says:

1. **`generated`** — an earlier build wrote a page at this path and the file there is byte-identical
   to it. docstrap wrote it and claims it.
2. **`divergent`** — an earlier build wrote a page at this path and the file there is something else.
   docstrap does not claim it. `--diff` shows the file against what those builds wrote, and a person
   decides.
3. **`authored`** — an `index.md` at the root of a `docs_root` which is not the placeholder stub an
   older build left. docstrap does not claim it, so the report does not offer it for deletion; it is
   also not published, because §7.8.6 allows a docs tree no index file. Both facts are in the
   finding's note, and removing such a file is a decision a person makes.
4. **`absent`** — a path such a build wrote to with nothing there. That is now the ordinary state,
   and it is reported only on request.

**The bytes it recognises are frozen**, and that is the one thing about this report that changed with
§7.8.2. They used to come from the live composer, so the report's answer moved whenever the composer
did — and the composer has now moved so far that it produces no bytes at all.
`generated_indexes.legacy_markdown` is therefore a deliberate copy, shared with nothing, describing
what builds up to 0.0.3 emitted. It is finished: that will never change again, so a description of it
can be correct forever. A test holds it to reading only; nothing calls it to write. When the last of
the fifty-five is gone, this module and its command go with them.

The strictness of the second rule is the point of the design and it is strict in the safe direction.
`rlp/docs/specs/index.md` **is** docstrap's output, and it comes back `divergent` because it is stale
and no longer matches; `rlp/docs/adr/index.md` was written by a different tool, which is no longer in
use, and it comes back `divergent` from the same rule without the rule knowing anything about that
tool. Both are reported and left alone. An earlier attempt to separate these two by grepping their
prose classified them wrongly — which is the evidence for the rule, not an argument against it. The
report reads; it deletes nothing and repairs nothing.

**A file the report cannot reach is not a file it says nothing is wrong with.** The scan is scoped to
one project resolved through `docstrap.projectscope`, so an `index.md` in a directory no `.docstrap`
declares is outside its reach entirely and does not appear in its output at all. In `platformshoes`
that is nine of the thirty-one tracked — `apps/ccpane`, `apps/charmoji`, `apps/pd`,
`packages/git_id`, `packages/object-brewer-ui`, `packages/repo-migrations` and four pages under
`docs-site/`. A cleanup driven from this report covers what the report covers, and the rest is a
question about which directories should be declared projects, not about which files are docstrap's.

#### §7.8.5 Inclusion when a document appears, not when a build is run

The build composes the *current state* of a project's sections, and that is all it does. It is not
the only path by which a document is meant to join an index: **a new document is included because it
appeared**, not because somebody remembered to rebuild. The intended mechanism for that is the
filesystem watcher of §11(4), which docstrap has planned from the beginning — a process observing
creation events and recomposing the affected section page in the build area.

The design above leaves room for it rather than foreclosing it, and the seam is now a real one rather
than an intention. A watcher does not need a second copy of the composition rules and must not have
one; it needs two calls and both exist. `fileindex.record` puts the one path that appeared into the
table and `fileindex.forget_path` takes out the one that went — §5.2.4 — and
`sectionindex.compose` answers what the affected section now contains, from the table, with no
directory walk of its own. The one-path calls are the primitives and the whole-project `reconcile` is
built from them, deliberately that way round, because the watcher is the caller that shapes the API
and the build is the one that happens to have looked at everything already.

There is nothing else for a watcher to do on an event. There is no cached page to invalidate and no
staleness to detect, because a section page exists only for the length of the Sphinx run that emits
it. What the watcher is not free to do is the same thing the build is not free to do: its output goes
in the build area, never in the project.

#### §7.8.6 No index file in a documentation tree, at all

§7.8.2 stopped a build writing one and left the files that were already written in place, under an
exception: a directory carrying an `index.md` was taken to have a landing page of its own, and a
project's own `docs/index.md` opened its site. The captain closed the exception, 2026-09-30, on being
shown what was still committed — *"index files in docs are not allowed and shoudl be removed. that is
the defect... that whole index file polution of the doucment directories was a horrrible idea"* — and
then stated the rule in the form that governs: *"do strap must create them ephmerally. as part of
it's build in it's own directories. you can clean those all up. no index.md in docs/ trees. At all.
period."*

So the rule has three parts, and the third has no exceptions.

1. **Ephemeral, and in docstrap's own directories.** Unchanged from §7.8.2 and already true: every
   section page, every project landing page and every store aggregate page is composed during the
   build, inside the build's scratch tree, and rendered straight to HTML. No markdown at any stage,
   and nothing worth caching that is not either embedded in the HTML or a row in `file_index`.
2. **Nothing is written into a documentation tree.** Also already true, and also unchanged. What
   changed is the exception that sat beside it. There is no "the user wrote their own index" check
   any more, at the root or in a section: every directory gets the page docstrap composes.
   Removing it costs nothing, because with nothing generated into a tree the check had nothing left
   to protect — and it cost a great deal while it stood, which is §7.8.1's second consequence. A
   generated file was never regenerated, so the first build's output became permanent and went
   stale in place.
3. **A documentation tree holds no index file.** Not a generated one, not an authored one. A build
   that meets one does not publish it: `layouts.markdown._mirror_tree` does not link it into the
   scratch tree, so it is not a document of the run and cannot shadow the composed page at the same
   docname. `sectionindex.REFUSED_INDEX_FILES` is the two names, `index.md` and the `index.rst` that
   is the same file under another suffix.

**A refused file is named, never dropped in silence.** It appears on the project's landing page,
through the same `docstrap_root_note` that reports a missing `docs_root`, and in the build result's
notes. That is not politeness: the writes of §7.8.1 were never announced anywhere, so the first
notice anybody had of them was a dirty `git status` in somebody else's repository three months later.

**And a refused file is not deleted.** A build reads a project and writes nothing into one, and
deleting is a write. Removing the files is a commit in the repository that owns them —
`docstrap generated-indexes` (§7.8.4) reports which are docstrap's, and
`scripts/check-no-index-md.py` fails if one is committed into a tree again. That check is the
executable half of this section; `tests/test_no_index_md_in_docs_trees.py` holds both halves.

**What is not a documentation tree.** A Sphinx source root whose own `index.md` is its `master_doc`
is a site's assembly point rather than a document directory, and the check reports such a file
without failing on it — `platformshoes/docs-site/` is the case, five hand-written files that are
that site's entire navigation and that nothing generated or regenerates. The rule was written about
generated indexes going stale in a content tree, and this is not one.

The distinction is stated here, and the check **says why** rather than only that a file was exempt:
its report names the difference it turns on, a master document against a generated index in a
document directory. Both halves are deliberate. A bare count invites somebody to delete the five on
a literal reading of *"At all. period."*, and the whole failure mode of §7.8.1 was a file nobody
mentioned. If this exemption is ever to go, it should go because it was overturned and not because
it was never written down.

### §7.9 The shape this is growing toward

Two directions are named here because they bear on every decision above, and neither is built. **A
project indexing tool**: indexing is a first-class job of docstrap's own, automatic and triggered by
the filesystem, not a step in a build and never a task delegated to a person or an agent. And
**plugins for document types and workflows**: a document is not one kind of thing — an ADR, a
specification, a research note and a draft answer have different lifecycles, different front-matter
and different apparatus — and handling them is a plugin surface rather than a growing set of special
cases inside the layout.

Sequencing for both is [`docs/roadmap.md`](roadmap.md)'s job and is not stated here.

### §7.10 The viewer shell's layout

`viewer.html` at a built site's root is one Svelte application: an app bar, the navigator on the
left, the selected page in a frame in the middle, and the question panels on the right. Its design and
the browser run that checked it are
[`docs/proposals/0004-the-viewer-shell.md`](proposals/0004-the-viewer-shell.md).

1. **The shell fits the window.** It is exactly the viewport's height, the page never scrolls, and
   each region scrolls inside itself. The navigator's tree scrolls in its own pane.
2. **The navigator is a resizable drawer.** It opens 26rem wide. A drag handle on its right edge
   resizes it between 14rem and 60% of the window, and the width is remembered per viewer in that
   browser's storage. When the window is resized, the drawer keeps its width and the document's
   width changes. A thin vertical tab on the drawer's edge closes it. When the drawer is closed, the
   same tab sits at the window's left edge and opens it. The app bar's navigator button does the
   same. A closed drawer stays mounted, so the tree keeps what was expanded. The dragging and
   collapsing come from Zag's splitter (`@zag-js/splitter`, the machine library Skeleton's components
   are built on; Skeleton ships no splitter component). The widths, what is remembered and what the
   tab does are in `viewer/ui/navigatorPane.ts`.
3. **A title in the navigator wraps inside its own row.** No title is cut short or ends in an
   ellipsis. Its lines start after its icon at that row's indent, and the icon, the first line and the
   row's pin button stay on one line, with the pin at the row's right. Each level of the tree is
   indented three spacing units (0.75rem), half of Skeleton's tree-view default, so a document several
   folders deep keeps most of the drawer's width for its title; each open folder still draws its level
   guide under its chevron. The indent overrides Skeleton's tree-view rules in `viewer/ui/app.css`.
4. **The question drawer opens and closes from the app bar** and keeps its panels mounted while
   closed, so an answer being typed survives.

## §8 Promdance layout

Each project has a promdance directory for git-ignored drafts and generated files — answer files, the
answers they superseded, the addenda submissions deliver, review records.

1. **Canonical location** — `~/.local/share/promdance/<project-slug>/`, deliberately outside
   docstrap's own data directory, because drafts outlive any particular docstrap install.
2. **Project-side view** — `<project-root>/promdance/`, a symlink to the canonical location, ignored
   in the project's own `.gitignore` (which `docstrap gitignore-check` verifies).
3. **Symlink direction** — project → storage. The storage side is the actual content; the project
   directory exposes a symlink so editors and file browsers see drafts in the expected place.
4. **Consequence** — switching branches does not disturb drafts, because they are outside the
   project's git. docstrap discovers drafts by walking the promdance root, not project trees.

`docstrap.promdance.ensure_promdance` creates the storage on demand during a markdown-layout build,
and creates the project symlink when nothing is there already. It never overwrites: a real directory,
or a symlink pointing somewhere else, is left exactly as found.

**One owner for the storage path.** `docstrap.paths.promdance_project_dir` is the only place that
path is composed, and the slug in it is passed through `docstrap.slugs.slugify` there, so a caller
holding a title rather than a slug cannot land somewhere the project does not link to. `promdance.py`
used to compose the root itself, which is how `docstrap init` came to report a root that nothing ever
wrote to.

**One owner for slugs.** `docstrap.slugs.slugify` is a thin wrapper over `python-slugify` adding the
one docstrap rule, that a path separator becomes `__`. Nothing else in docstrap turns text into a
name, and no tool should; a test fails if a second slugifier appears.

**Backup** is one git repository at `~/.local/share/docstrap/promdance-backups`, written by
`promdance backup` (§4.3). Drafts are gitignored in their projects, which means git is not backing
them up, and this is a local answer to that; §8.4 is the other one. Backup pushes nowhere and needs
no account, which is why it survives as a separate mechanism now that the store has its own git:
a machine with no network and no credentials still gets a copy.

**Backup discovers from both sides.** The store is where a symlinked project's drafts actually are;
a project's own real `promdance/` directory is where a not-yet-interned project's drafts still are.
Reading only project space missed three store entries — two owned by `related_directories`, which
discovery dropped, and one a uv workspace member that is not a git repository and that nothing
found; that last one held six real drafts. Reading only the store would miss everything not yet
interned. So both are read and the results are merged on the directory the content actually lives
in.

**Identity is a canonical directory, not a slug.** A linked git worktree is a second checkout of one
repository, so its projects are the same projects at different paths. Comparing raw slugs read that
as a collision and aborted before copying anything, which is why no backup had ever been taken:
`~/wt/trk_tdp/id-cohorts/apps/gsheets-pub` and `~/trk_tdp/apps/gsheets-pub` are one project, and both
symlink one store entry. `docstrap.projectfinder.canonical_dir` resolves a directory through
`git rev-parse --git-common-dir` to its position in the main working tree, and sources are merged on
the resolved directory the drafts live in — so two paths onto one directory are one source, and the
path reported is the main checkout's. Where a source is mirrored to is then derived from that
directory rather than from a slug (§4.3), which removes the remaining collisions as a class.

### §8.1 The answer store, and the key an answer hangs on

Answered by the captain on 2026-09-07, closing the roadmap's Q1 and this document's Q4. **An answer
lives in a keyed markdown file with YAML front-matter, one per project, in that project's promdance
directory.** It does not live in the annotations database — that store is Annotorious's and its
`creator` models a different audience; §6 has the reasoning. It does not live in the metadata
database either, which is the system of record for *documents*.

`docstrap.answers` is the one owner of this file, in the sense §8 already uses for slugs and for the
storage path. The qa tool writes through it, the qapanels instrument writes through it, the task tool
records its decisions through it (`docs/tasks.md` §5.1), and a second implementation of the format is
the defect this section exists to prevent.

#### §8.1.1 The key

An answer is keyed by **the metadata store's document id and the question's own label inside that
document**, joined by a colon:

```
01J9F4V4T4XW9A0RCM6QK2S8YZ:Q4
```

The two halves are chosen for what each survives.

1. **The document id** is the ULID of §5, and it survives a rename. A path or a slug does not: a
   document moved from `proposals/` to `plans/` — which is exactly what happened to this file — keeps
   its id and loses its slug, and an answer keyed on the slug would be orphaned by the promotion.
   A document not yet in the metadata store is registered on first answer, the same resolve-or-create
   `docstrap status <path>` performs. Surviving a rename means the *id* is stable; keeping the
   store's `current_path` pointing at the moved file is the metadata store's own job, through
   `metadata.record_move`, and a document moved without telling docstrap is a new document to it. The
   key does not make that problem worse and does not solve it.
2. **The label** is the author's own. For a question found by analysis it is the `Q<n>` label the
   author wrote and `docstrap.questions` reads. For a question placed with the `docstrap-questions`
   directive it is that directive's required `:question-id:`. Both are the author's naming of a
   question within one document, and the id half keeps two documents' `Q1`s apart. A decision the
   task tool records is labelled `task/<task-id>`, the page listing the task being the document;
   `docs/tasks.md` §5.1.

**Every writer resolves the project through the registered stores.** A request carries the project
slug the built page declares, and `docstrap.projectscope.resolve_slug` turns that back into the
project — the same registered-stores list `docstrap build` reads when given no arguments. So a
project must be registered for its questions to be answerable, which is a real constraint and the
price of keying on identity: an answer's key needs the document, and finding the document means
knowing where the project is. A slug two registered stores both declare is an error rather than a
first match, for the same reason two owners of a name was one.

**The key introduces no index.** It is computed from the document and the label every time, so
`packages/docstrap/docs/finding-questions.md`'s rule holds unchanged: questions are found by scanning
documents, any listing is a scan, and nothing authoritative records what questions exist. The answer
file records answers, not questions — a key in it whose question has since been deleted is a stale
answer, not a question the store believes in.

A question renumbered by hand — `Q4` becoming `Q5` when a question above it is removed — changes the
key, and the earlier answer stays in the file under the old key. That is the accepted cost of keying
on the author's own label rather than on a generated identifier the author would have to maintain.

#### §8.1.2 The file

`<project-promdance>/answers.md`, resolved through `docstrap.paths.promdance_project_dir` like every
other promdance path. One file per project rather than one per document, because the key is
document-id-anchored: a per-document filename would be slug-anchored and would re-introduce the
orphaning the key removes.

Front-matter carries the index, one **flow-style** row per answer so a change to an answer's
metadata is one changed line in a diff. The prose lives in the body, as markdown, under a heading per
key:

```markdown
---
answers:
  - {key: '01J9F4V4T4XW9A0RCM6QK2S8YZ:Q4', document: docs/spec.md, label: Q4, answered_at: '2026-09-07T18:20:00+00:00'}
  - {key: '01J9F4V4T4XW9A0RCM6QK2S8YZ:Q2', document: docs/spec.md, label: Q2, answered_at: '2026-09-07T18:31:00+00:00'}
---

# Answers — docs

## 01J9F4V4T4XW9A0RCM6QK2S8YZ:Q4 — docs/spec.md

Yes. The annotations database was built for it.
```

Answer prose is **never** embedded in the YAML. A block scalar makes the answer unreadable to hand
edit and rewrites the whole block on any change; the captain rejected that shape for the same reason
the rows above are flow-style. What is in the front-matter is the index and the timestamps; what is
in the body is what someone wrote.

**The question's text is not stored.** A key names a document and a label; finding the question means
reading that document, which is the only place a question lives. Storing a snapshot would make this
file a partial index of questions, and there is not supposed to be one. The heading carries the
document path so a reader knows where to look, and everything after the key on that line is
decoration the store does not read back.

**Answering twice supersedes.** Writing the same key again replaces that key's row and that key's
body section in place. Nothing appends, and a second answer does not stack a second section under the
same question — which is what the earlier per-document answer file did, because a question id was
decorative italic text in it rather than a key.

The file is a promdance derivative, so it is outside the project's git and is backed up by
`promdance backup` (§4.3). Nothing about it is altered in place in a source document, which is what
lets any of this be pointed at a read-only checkout.

#### §8.1.3 When an answer counts

**An answer counts when a person says it is finished, and not before.** The three-panel instrument
autosaves, and until 2026-09-14 an autosave and a finished reply were the same event: the first real
run recorded a decision at three characters — "NO!" — and refused everything typed afterwards, because
the stored decision no longer matched what was offered. Roadmap §4.11 items 1, 2 and 3 are the three
faces of that one defect, and one mechanism closes all three.

Every write states which it is. `docstrap.answers.put` takes a `submitted` argument and **gives it no
default**, so no caller can leave the question implicit; a default here would be exactly the guess that
caused the damage. The instrument's autosave sends `submitted: false` and stores a draft; its **Finish**
button — the captain's "finish button to end the process in the interface" — sends `submitted: true`.
There is one Finish, below the last question in the list, and it submits every draft in scope, one write
per draft through the same route; its label is "Submit revisions" when any of them revises a submitted
answer, and it is disabled when there is nothing to submit. The editor has no submit control.
The `docstrap-questions` form tool has only a Submit control and so submits by construction.

A draft is stored, and that matters in both directions. The writer gets their own unfinished text back
when they return to the question, which is the whole point of autosaving it. Nothing else sees it:
**`docstrap.answers.submitted()` is the read every consumer uses**, and `read()` — which returns drafts
too — exists for the editor and for this file's own rewriting. A question with a draft against it is
still open, in the panel's header count and in its list mark alike.

**Three states, not two.** The `submitted` field in a row is `true`, `false`, or absent, and absent is
its own state rather than a synonym for false. A row written before this distinction existed counts as
submitted, because under the rule it was written under, storing an answer *was* finishing it — that is
how those answers travelled and closed work. Reading them as drafts would retroactively un-answer real
decisions, including two in `~/dkp/promdance/answers.md` that nothing has acted on yet. An absent field
is also never written back, so an untouched legacy row survives a rewrite of the file byte for byte.

#### §8.1.4 Revising a submitted answer

**A later answer supersedes an earlier one rather than being rejected.** A captain rewriting his own
reply is ordinary; it used to require a hand repair of the record, because the recorded decision no
longer matched what was offered (roadmap §4.11 item 3). docstrap does not model the work a question
gates and so cannot observe a question being closed, so it never refuses a revision. What makes that
safe is not a gate but a record: every answer a revision displaces is kept.

**A draft sits beside the submitted answer, not on top of it.** An answer's row carries the submitted
prose under `## <key>`; an unsubmitted revision carries its own under `## <key>#draft`, with a
`drafted_at` in the row. Retyping a reply must not make the existing decision vanish from every
consumer for as long as the retyping takes, which is exactly what a draft written into the answer's own
text would do. `answers.submitted()` therefore keeps returning the standing decision throughout, and
`Answer.editable_text` is what the editor gets — the revision in flight if there is one, so returning to
a question resumes where its author stopped rather than where the record stopped. Submitting spends the
draft; a draft that says what the submitted answer already says is not a revision and is not kept.

**Superseded answers live in a second file**, `<project-promdance>/answers-history.md`, in the same
format and written by the same owner. Not extra rows in `answers.md`: every consumer of that file reads
its rows as the project's current answers, and history rows among them would change what the file means.
An entry carries the prose, the timestamps the answer had, a `revision` counting from 1, and a
`superseded_at`; its body section is `## <key>#r<n>`. A key may appear there any number of times, and
`answers.history(project, key)` is how one question's earlier decisions are read back.

### §8.2 Reading what is answered

Roadmap §4.11 item 4 found that `/api/promdance/answers` returned 404: a decision could be stored and
there was no way to ask for one. **`/api/answers/<project>` and `/api/answers/<project>/<doc-slug>`
return a project's questions paired with the answers they have**, so "the store is a markdown file"
stops being every consumer's problem.

**The answers API is the server's, not a tool's.** The store has one owner, `docstrap.answers`, and
two tools write through it; a consumer asking what a project has decided should not have to know which
tool happens to exist, any more than it should have to parse markdown. That is the distinction
metadata and annotations already have. It is **read-only** here on purpose: writing an answer means
resolving a document, creating its metadata id if it has none, and saying whether the write is a draft
or a submission, all of which is a surface's job and belongs where a person is answering.

`?include=` takes `all` (the default), `answered` or `open`, and an unrecognised value is a 400 rather
than a silent fallback. The counts describe the project either way, not the filtered slice. An
unknown project slug, or a document slug the project does not declare, is a 404 — nothing would be
indistinguishable from "this poses no questions".

**No draft, ever.** Not the text, and not the fact that one exists. A consumer of this endpoint is
acting on decisions; an answer nobody has finished is not one, and publishing unfinished writing to an
audience its author has not shown it to is the reverse of what §8.1.3 is for. A submitted answer stays
published, unchanged, throughout a revision being typed over it. A superseded answer is **counted**
here and not republished; `answers-history.md` is where it is (§8.1.4).

The built site is the second place an answer file is published: the promdance mount carries
`answers.md`, and Sphinx renders it as a page. The same rule holds there. `docstrap.sphinx.promdance_answers`
replaces that page's source, in memory as Sphinx reads it, with `answers.publishable` — the submitted
answers alone, with neither a draft's text nor its row. Nothing is written, in the build or the store.

**One pairing, two projections.** `docstrap.pairing.pair` is the only thing that puts questions and answers
side by side — `docstrap.questions` reads `Q<n>` labels and nothing else, and `docstrap.answers` is
emphatic that it is not an index of questions, so the pairing belongs to neither and is its own
module. This endpoint serialises it for **reading**; the qapanels instrument serialises the same
computation for **editing**, where a writer does get their own draft back. Two deliberate views of one
scan is a different thing from two implementations of the pairing, and the second is what the
single-owner rules exist to prevent.

The pairing **introduces no index**. It is a scan, per call, derived and disposable: adding a question
to a document changes the next pairing with nothing told, and reading never registers a document in
the metadata store, because answering is what does that (§8.1.1).

### §8.3 The answer addendum — what the loop delivers

The captain, 2026-09-14, on a loop that had stored ten real decisions and produced nothing: *"it's a
pregnancy with no delivery."* A decision that leaves no artifact has been **stored rather than
delivered**, and three things already assumed otherwise — documents as the unit of value in §0, the
documentation-first practice, and dkp's contract stamp deriving from a document's hash so that an
answered question moves a version. That is roadmap §4.11 item 6.

**Submitting an answer writes an addendum**, one markdown file per answered document, beside the
original in promdance at `<project-promdance>/<doc-slug>__answers.md`. It is a derivative: the source
document is not touched, which is §0 and is the reason this is a file of its own rather than a section
appended to the question document.

The path is **stable and not timestamped**, so a citation made today still resolves tomorrow. The file
is rewritten whole on each submission rather than appended to, for the same reason the answer store is
(§8.1.2): appending stacks two records of one decision. It lists every question the document poses —
each answered one with its key, its submission time, the answerer when one was named, how many earlier
answers it superseded, and the answer reproduced as written in a block quote; each open one marked
open, because half of what a reader of this needs is what is still undecided.

**A draft delivers nothing**, because a draft decides nothing, and no draft ever appears in the file.

#### §8.3.1 `answered_version`

The front-matter carries `answered_version`, a short digest **over what was decided and nothing else**:
which questions have answers, and what those answers say. This is what "a version of the document
recording that it was answered" means here — a version of the *answered state*, recorded beside the
document. It is deliberately not a new column in the metadata database and deliberately not an edit to
the document.

Three things are excluded, each because including it would move the version when no decision had.

1. **The question's prose**, so rewording a question does not claim its answer changed.
2. **The generation time**, so regenerating an unchanged document yields an unchanged version.
3. **The submission time**, so pressing Finish again on text nobody edited is a re-affirmation rather
   than a decision. The store already agrees: it supersedes nothing in that case (§8.1.4). A real run
   is what found this; the version had the timestamp in it, and clicking Finish twice would have had a
   consumer re-stamping a contract for nothing.

The answer's **key** is included, so renumbering a question moves the version — correctly, because the
key an answer hangs on changed and that answer now belongs to a different question (§8.1.1).

#### §8.3.2 Delivery is not the answer

Both writers deliver through one function, so the artifact cannot come out differently depending on
which surface a person used — the same single-owner rule §8.1 has for the store.

**A failed delivery does not fail the submission.** By the time delivery runs the answer is already in
the store, and reporting the write as failed would invite a caller to retry a write that succeeded —
which against a superseding store means a second history entry for one decision. The surface is told
the delivery is absent and can say so; the panel shows the version it stamped when there is one.

The addendum is **as current as the last submission**. Nothing regenerates it when a question is
renumbered or deleted in the source, because nothing tells docstrap that happened; the next submission
against that document rewrites it whole. `generated_at` in the front-matter is how a reader sees how
old the statement is.

### §8.4 The store is a git repository with a remote

The store is where every draft actually lives, and it was the one directory in the captain's working
life that git was not backing up — drafts are gitignored in their projects precisely so branch
switches do not disturb them, and the consequence was 93 files with no history and no copy anywhere.
So: **the promdance store is a git repository with a remote, and the system commits and pushes to
it.** `docstrap.storegit` owns the four operations and nothing else does.

#### §8.4.1 The name is a suggestion, derived rather than imposed

**`promdance-<machine>`** — `promdance-xomcomen` on the captain's workstation. Settled 2026-09-17
with his own hedge on it, *"that rule is fine ... for now"*, and it is what docstrap **offers** to
somebody choosing a name. It is not a rule docstrap enforces: the repository is the user's, and a
user who names theirs something else has named it correctly (§8.4.3).

The path is deliberately absent from the name. The store's location is the XDG data directory for
that user on that machine; it is derivable rather than chosen, so putting it in the name would record
something nobody decided. What a name has to distinguish is *machines*, because that is what makes
two stores two stores.

A store held under a narrower-tree configuration takes that configuration's own name as a third
part — `promdance-xomcomen-wintercms-clients` — so the default store and a narrower one do not
suggest the same name.

The machine part is read from the host and passed through `docstrap.slugs.slugify` like every other
docstrap name; it is not a constant, and a machine reporting a host name that identifies nothing
(empty, `localhost`) is an **error** rather than a fallback, because suggesting `promdance-unnamed`
is worse than saying there is nothing to suggest.

#### §8.4.2 Initialising adds `.git/` and changes nothing else

`promdance store init` creates the store directory if absent and runs `git init` if there is no
repository. That is the whole of it. **No file is written in among the drafts** — no `.gitignore`, no
README, nothing: every entry beside `.git/` is a draft or a draft's directory, and writing a file in
there is the one thing this must not do. Where an exclusion is genuinely wanted it belongs in
`.git/info/exclude`, which is inside the directory initialising is allowed to add.

It is idempotent, and it names its initial branch explicitly so a machine whose git carries a
different `init.defaultBranch` still produces the same store.

Store commits carry their own committer identity, because the store is machine-local bookkeeping and
a machine with no global git identity must still be able to commit its own drafts.

**Every file in the store is tracked, and ignore rules are overridden to make sure of it.** A file
here exists nowhere else, so there is no such thing as one in it not worth keeping, and an exclusion
mechanism would only be a way to lose one. That is not hypothetical:
`~/.local/share/promdance/dkp/.gitignore` reads `*` with a few exceptions. It was written to keep a
scratch directory out of the *dkp project's* git and travelled into the store when that directory was
interned — and honouring it here would have meant sixteen real drafts silently absent from a commit
that reported success. A rule about somebody else's repository is not a rule about this one, so
`git add` is forced and such a file is committed as what it now is: content that came along with the
drafts.

#### §8.4.3 Docstrap does not create the repository — the consent is structural

**The user creates the repository**, under their own account, on the service they chose, under the
name they chose, and hands docstrap the URL and the credentials. Docstrap's job is to *use* them, to
say clearly what it needs when they are absent, and to **refuse rather than invent a repository on
somebody's account**.

The captain's reasoning, 2026-09-17, and it removed work rather than adding it: an agreement to sign
would be *"overt"* where the natural act is already explicit. *"This also could just part of the user
chooing the name and crating a repo under thier own user that it gives docstrap keys to use. The
choice of serivice is then explicit. since that must be done naturally it seems farily expcit."*
Choosing the host, creating the repository and handing over a key **is** the decision; asking for it
twice does not make it more informed. He also observed that most of what such an agreement would
cover is already covered by the OSS licences, and that adjacent trust being transitive is reasonable.

That was checked against what comparable tools do before being written down, at his instruction. The
closest precedent is chezmoi, which has the *same* shape — user content relocated into a
machine-shared XDG store at `~/.local/share/chezmoi`, reached through an apply/symlink indirection.
It has no agreement, no consent prompt and no registration: it has `chezmoi diff` and a dry run, so a
person can see what would happen before it does. Nothing heavier turned up anywhere, and docstrap's
own dependencies carry nothing of the kind. So the heavier mechanism is not adopted.

The consequence is a real simplification: **there is no outward-facing step in docstrap at all.**
Nothing reaches a hosting service on its own initiative, so there is nothing to guard, no API client,
no token for docstrap to hold, and no CLI for it to shell out to. `promdance store remote <url>`
writes a URL into `.git/config`, which is a local fact; `promdance store push` uses the credentials
git already has, and a failure to authenticate fails with git's own message, which names the host and
is the one a person can act on.

With no URL, `promdance store remote` reports the current remote and — for somebody who has not
chosen one — suggests the name of §8.4.1 and the URL it would have, saying plainly that docstrap
creates none of them. A remote already addressing that repository is left alone even when it is
spelled differently (`git@…:owner/name.git` and `https://…/owner/name` are one place), because
rewriting it every run would be churn rather than repair.

#### §8.4.4 Committing and pushing: a command *and* a hook, and why

The captain asked for a system that commits and pushes, not for a chore he has to remember. Both
shapes are built, and they answer different questions.

1. **The command** — `promdance store commit [--push]` and `promdance store push` — is for when you
   want it now, and is what a person or another tool calls.
2. **The hook** is on `promdance backup`, which already means *checkpoint every draft I have*.
   Committing the store belongs on that operation and is on by default; pushing to an
   already-configured remote is likewise on by default, because that is what "commiting all and
   pushing the changes" asks for. `--no-store-commit` and `--no-store-push` opt out.

It is **not** hooked to a build or to an answer submission. Those run from a web request, and turning
a click in the Q&A panel into a `git push` that can fail, block, or race another push is how an
interactive surface acquires an outage.

A store with no remote, or no repository yet, is **not an error** for the hook: it reports what is
missing and the backup still succeeds, because a machine that has not been given a remote yet still
wants its local safety net. What it never does is resolve the absence by creating something (§8.4.3).

### §8.5 Promdance is opt-out, at three levels

**Promdance is an opt-out component of docstrap**: on unless something says otherwise. The setting is
the `promdance` field, and it can be stated at three levels:

1. **Installation** — `promdance` in the user config at `~/.config/docstrap/config.yaml`.
2. **Repository** — `promdance` at the top level of a `.docstrap` file.
3. **Project** — `promdance` on one entry in that file's `projects:` list.

Each is **tri-state**. Absent is not `false`, and it is not `true` either: it means that level said
nothing. The distinction is load-bearing — if a `.docstrap` that never mentions promdance parsed as
`true`, an installation-level `promdance: false` would be silently overruled by every repository on
the machine. Absence is never written back to the user config, so a config that never mentioned
promdance survives a save byte for byte.

**When two levels disagree, the more specific one wins.** Project beats repository beats
installation, and anything stated beats the opt-out default. A repository that wants promdance off
everywhere writes `promdance: false` once at its top level and every project in it inherits that; one
project inside it that wants promdance on writes `promdance: true` on its own entry and gets it.
Reading it the other way round would make the per-project setting unexpressible, and per-project is
what was asked for.

The setting governs **interning** — whether docstrap wires a project up to the store — by either path
that wires: `promdance intern`, and a markdown-layout build, whose `ensure_promdance` creates no store
entry and no link for a project that opted out. Neither does that build wire a project in a linked git
worktree: the worktree's entry is its main checkout's (§8.9(2)), and a link there would put the live
store inside a second checkout. It does not govern **backup**: a project that opted out but still has
drafts on disk gets them backed up, because a safety net that skips content on the strength of a
config flag is not a safety net.

### §8.6 Interning, and the one step it does not take

Interning has two halves and they are not alike.

The first half is wiring a project that has nothing of its own at `promdance/`: create the store
entry, place the symlink, add the `promdance/` line to `.gitignore`. **This is what `promdance
intern` does**, for every project promdance is on for, idempotently. It is the half that makes the
captain's hand-written `.gitignore` line unnecessary, which was the whole point of it — his
correction to calling that line a standalone fix was *"that 'fix' should have been unecessary."*

The machinery it does the wiring with already existed: `ensure_promdance` created the store directory
and the symlink and deliberately never overwrote a real directory; `gitignore.check`, `gitignore.fix`
and `find_gitignores_missing_promdance` detected and repaired exactly the case he fixed by hand. The
defect was that **nothing could call any of them** — the CLI exposed `backup` and nothing else. So
this is a command over machinery that was already correct, not new machinery.

One detail of that repair earns its place: `promdance` and `promdance/` are read as the same rule.
They ignore the same directory, and reading them as different is what would have had a repair append
a second line underneath the captain's own. They do **not** ignore the same symlink: git sees a
symlink as a file, so `promdance/` never matches the link `intern` places, and only `promdance` does.
`promdance status` asks git rather than reading the file, and says so when that is the case (§8.9).

The second half is a project that already holds a real `promdance/` directory. Completing his
creation sequence there means **moving** its files into the store — and `intern` never moves a file.
A project in that state is **reported and left exactly as found**, every time.

That is not a gate, and there is no agreement behind it (§8.4.3 is where that question went, and the
answer was that it is unneeded). It is simply not built. Moving content out of a repository is a
one-way change to somebody's project, and a repair command that sweeps every registered project is
the wrong place for it to happen for the first time; the sequence is known and the work is ordinary,
so it is on the roadmap rather than in a section like this one. When it is built, the shape it should
take is chezmoi's: show what would move before moving it.

### §8.7 Source control is headed for a plugin surface

Docstrap is an integrator: it drives other people's tools rather than reimplementing them. Source
control is one such tool, and **GitHub is one provider among several intended, not the assumption**.
A connector for other source-control providers is intended, and the mechanism will likely be
[`pluggy`](https://pluggy.readthedocs.io/) — the same hook system Sphinx-adjacent Python tooling
already uses.

*That plugin system is not built here.* What is built is the seam it registers into, so there is
nothing to retrofit. `docstrap.forge` defines what a provider has to answer, and because docstrap
creates no repositories (§8.4.3) that turns out to be very small and purely textual:

1. the URL a repository of a given name **would** have, offered as a suggestion while a user is
   choosing a name, and
2. whether two URLs address one repository, so a remote spelled `https` is not rewritten to `ssh` on
   every run.

There is no API client, no credential and no network call behind this boundary — which is the
simplification §8.4.3 bought. Every GitHub specific docstrap knows is the URL shapes, and they live
in one class implementing the protocol and nowhere else. A second provider is a second class; no
caller above the boundary changes. A test asserts the boundary holds by fingerprint, so a provider
detail written above it fails the suite rather than quietly establishing a precedent.

A second implementation ships already, and it is the one that proves the model rather than a
placeholder: **plain git**, for a host docstrap knows nothing about. It cannot suggest a URL — there
is no host to suggest one on — and it compares remotes as text. Selecting it is how a user says *I
chose a service you have not heard of*, which has to be an ordinary case rather than an error,
because the user choosing the service is the whole model.

### §8.8 Archiving a promoted prompt — a named place, and nothing in it

The captain's 2026-09-17 note carries a fifth item: *"there aslo needs to be a system to archive used
prompts and spects in the promdance git when they are promoted to docs by changing some things in the
strapdance header."*

It is **not specified and not built**, at his explicit direction: he said he needs to think that one
through himself. This section exists so the idea has a number to be written into rather than being
rediscovered.

What is already known and bears on it: strapdance's header vocabulary (its reader was removed on 2026-11-21) carried a status that came
from a document's position — `done` from `done/`, `reusable` from `templates/`, `reference` from
`memories/` and `notes/` (see `docs/strapdance-front-matter.md`, retired on 2026-11-20). Which header change means "promoted,
now archive the original" is the undecided part, and it is a question about the vocabulary before it
is a question about the archiving. Now that the store is a git repository (§8.4), the "archive in the
promdance git" half has somewhere to happen; the trigger does not.

### §8.9 Where a promdance directory belongs

The captain's rule: a promdance directory belongs at **every repository root**, and at **every app or
package of a uv workspace that has a docs folder** — the directories `ls ~/*/packages/*/docs -ld &&
ls ~/*/apps/*/docs -ld` lists. It is read as `<repository>/apps/*/` and `<repository>/packages/*/`
holding a `docs` directory, for every repository below the projects root. A directory a `.docstrap`
declares — a project or a related directory — belongs too, rule or no rule, because `intern` already
puts one there. `docstrap.placement` is the one owner of the rule; `promdance scan` and `promdance
status` report it, and `promdance backup` reads the members it adds.

1. **The projects root is a setting.** `promdance_projects_root` in the user config at
   `~/.config/docstrap/config.yaml` names the directory the repositories live under, `~` expanded.
   Unset, it is the home directory, so nothing changes until somebody moves their repositories under
   `~/projects/` and says so. Absent is never written back. `--root` on a command stands in for it.
2. **A worktree is its main checkout.** `projectfinder.canonical_dir` folds a linked worktree onto
   the main working tree, so a worktree and its directories are never a place of their own; one whose
   main checkout lies outside the projects root is not under it and is not listed. A clone is a
   separate working tree and counts. Backup is the one reader that still visits each checkout,
   because two checkouts' own `promdance` directories are two directories (§4.3).
3. **A repository speaks through the `.docstrap` at its root.** A `.docstrap` deeper inside a
   checkout is that repository's content — docstrap's own test fixtures are the live case — and
   declares nothing here. One below the projects root and inside no repository speaks for its own
   directory; a registered store speaks wherever it is.
4. **Dotted directories and `ignore: true` subtrees are skipped**, as every docstrap walk skips them.

How a place stands is one of: linked into the store (and which entry), a real directory, a symlink
elsewhere, a broken symlink, or absent. Nothing in the rule writes. A member no `.docstrap` declares
has no slug to name a store entry from, so `intern` does not reach it, and `status` says so rather
than inventing a name.

**An entry name two places answer to is reported.** A name comes from a title or a member path, never
from where the directory is, so two places can arrive at one — two repositories that each relate a
`docs` directory both name `docs`. A place answers to its declared slug's entry and to the entry its
link reaches. `placement.shared_entries` finds a name more than one place answers to; `promdance
status` and `docstrap doctor` both report it, and neither repairs it.

**Whether git ignores the entry is git's answer**, not the text of `.gitignore`: `status` runs `git
check-ignore` on an entry that exists, and reports an entry git already tracks as committed, because
a committed path is not ignored whatever the file says. Only an absent entry at a repository root
falls back to reading `.gitignore` for the line.

### §8.10 Saying a document's answers are done

Answers save continuously (§7.6), and nothing in a stream of saves says a person has finished with
a document's questions. The **answers done** prompt says it. It is a notice and not a submission:
it writes no answer, decides nothing and delivers no addendum (§8.3). Its whole effect is to run one
command the installation names, so that something outside docstrap — a supervisor waiting on those
answers — can go and read them.

1. **The setting.** `answers_done_command` in the user config at `~/.config/docstrap/config.yaml`,
   an argv list. A bare string is not accepted, because splitting it would need a shell and none is
   run. Unset, the prompt is not offered anywhere. Absent is never written back.
2. **The prompt.** One per document, in that document's title row in the Q&A panels' question list
   (§7.6) — so once when the panels show one document, whether over a page or in the viewer's
   question drawer, and once per document in the project scope. Never one per question. It is shown
   only when the listing carries a route for it, and the listing carries one only when the setting
   is set. Pressing it first waits for any pending autosave to land, so the store holds what is on
   screen.
3. **The route.** `POST` on the qapanels document-scope collection,
   `/api/promdance/{project}/{doc_slug}/qa` — the same URL the document-scope read uses,
   distinguished by method and never by a sub-path. It runs the command once with
   `--project <project slug> --document <path>` appended, where the path is the document's path as
   the answer store records it (`ProjectScope.display_path`), with a 15-second timeout and no
   retry. It answers `{ok, exitStatus, error}`: the command's exit status, and its stderr when it
   failed. A command that cannot be started or does not finish is reported the same way, with no
   exit status. With the setting unset the route is a 404.
4. **One owner.** `docstrap.answers_done` holds the argument contract and runs the command;
   nothing else in docstrap spawns it.

## §9 Claude skills

Two skills ship inside the package at `packages/docstrap/src/docstrap/skills/`, and `docstrap init`
installs them to `~/.claude/skills/` (§4.1(2)). They live inside the installed distribution rather
than beside it because the installer copies them out of the installed package, not out of a source
checkout.

### §9.1 Authoring skill (`docstrap-authoring.md`)

MyST directive and role invocation of Sphinx features, the `{eval-rst}` escape hatch with concrete
templates for the RST-only cases, cross-referencing across the MyST/RST boundary, mermaid syntax, and
how the `docstrap-questions` directive appears in source. Read when helping author docstrap-managed
docs.

### §9.2 Lifecycle-status skill (`docstrap-lifecycle.md`)

Deliberately the narrowest skill in the package: it exists to make one operation possible and every
neighbouring operation impossible. It changes one document's lifecycle status, through the docstrap
CLI and never the database directly, and only when both gates are open — the user explicitly asked
for that change, and explicitly approved the specific document and the specific from-status →
to-status transition. Neither gate is inferable. It refuses to change status unprompted.

## §10 Package shape

`packages/docstrap/` is a uv workspace member of platformshoes, registered in the root
`pyproject.toml` and installed editable into the shared environment.

```
packages/docstrap/
  pyproject.toml            (version — the only place it is declared)
  package.json              (the frontend build; devDependencies only)
  build-tools.mjs           (one Svelte bundle per tool, named from its declaration)
  README.md
  docs/
    doctor.md, tools-and-instruments.md, strapdance-front-matter.md (retired 2026-11-20),
    finding-questions.md, notes/sphinx-extension-research.md
  src/docstrap/
    __init__.py             (empty)
    cli.py                  (Typer app: `docstrap`)
    version.py              (version + install-origin reporting)
    config.py               (.docstrap parser)
    user_config.py          (the registered-stores list)
    paths.py                (platformdirs resolution; owner of the promdance path)
    slugs.py                (the one slug function)
    scan.py                 (project enumeration; README discovery)
    build.py                (per-store and super-aggregate orchestration)
    sphinx_build.py         (argv for every Sphinx invocation)
    pagefind_step.py        (best-effort search index)
    layouts/                (base, markdown, sphinx; mkdocs and quarto are stubs)
    metadata.py             (metadata DB)
    fileindex.py            (the file index; §5.2)
    sectionindex.py         (what a section page contains, and which dirs get one; §7.8.3)
    generated_indexes.py    (the frozen recogniser for what older builds wrote; §7.8.4)
    annotations.py          (annotations DB)
    server.py               (FastAPI: static + API)
    frontmatter.py          (byte-for-byte front-matter split)
    doctor.py               (ambiguity report + fix-plan proposal)
    questions.py            (the Q-label question finder)
    promdance.py            (draft storage; the `promdance` CLI)
    projectfinder.py        (git-repo discovery)
    gitignore.py            (check + fix)
    firstmate.py            (operational-home detection)
    skills/                 (docstrap-authoring.md, docstrap-lifecycle.md)
    sphinx/
      composed.py           (pages docstrap composes, as nodes and never markdown; §7.8.2)
      launcher.py           (the single visibility launcher; not a tool)
      tool_support.py       (the build seams tools attach to)
      ui/docstrap.ts        (the typed client view; names no tool)
      static/               (docstrap-common.js, docstrap-launcher.js/.css, docstrap.css)
    tools/
      declaration.py        (ToolDeclaration, Kind, Target)
      registry.py           (discovery by directory)
      mounting.py           (mounts every declared tool's routes)
      launcher.py           (the offer rule)
      derivatives.py        (where a tool's derivative document goes)
      frontend.py           (what build-tools.mjs reads)
      status/ qa/ review/   (declaration.py, routes.py, views.py, ui/, static/)
      qapanels/             (the three-panel Q&A instrument; §7.6)
      answered/             (the answer beneath the question; §7.7)
    answers.py              (the keyed answer store; §8.1)
    pairing.py              (questions paired with their answers; §8.2)
    addendum.py             (what a submission delivers; §8.3)
  tests/
```

Runtime dependencies: `typer`, `fastapi`, `uvicorn`, `sphinx`, `myst-parser`,
`sphinxcontrib-mermaid`, `pyyaml`, `platformdirs`, `furo`, `pagefind`, `python-slugify`,
`linkify-it-py`. Dev: `pytest`. The frontend build's Svelte, Vite and plugin are npm devDependencies
of the package and are not needed to install or run it.

Two console scripts: `docstrap = docstrap.cli:app` and `promdance = docstrap.promdance:app`.

### §10.1 Versioning

The version is declared in exactly one place, the `version` field in `packages/docstrap/pyproject.toml`,
and runtime code reads it back through `importlib.metadata`. docstrap is at `0.0.3`.

`VERSIONING.md` at the workspace root is the policy: `x.y.z` with no suffixes, per-package and
independent, tags spelled `docstrap-v0.0.3`, a version bump as its own commit touching only that
field. In the `0.0.z` era only `z` moves; entering `0.y.z` is a deliberate statement that the tool
has settled, not something reached by counting. **"Alpha N" is retired as a version label** — it may
appear in prose as a historical fact, but it is never a status and never a version. Alpha 3 is
`0.0.3`.

### §10.2 The two installs

**Development** — `uv sync` then `uv run docstrap` at the workspace root, running the working copy.
Reports `install: workspace-dev`.

**Stable dogfood** — `scripts/docstrap-stable.sh install [REF]` installs `~/.local/bin/docstrap` with
`uv tool install` from a pinned git ref, so `docstrap` on PATH is not whatever happens to be in the
current working copy. Removed with `scripts/docstrap-stable.sh remove`. With no `REF` it resolves the
most recent tag containing `packages/docstrap`, and until a docstrap tag exists it refuses and asks
for an explicit ref. `docstrap --version` reports the version, path, install kind, and for a stable
install the ref and commit it came from, so the answering binary is always explicit.

`VERSIONING.md` §3.3 records a latent defect in that no-ref resolution: it selects by tree content,
not by tag name, so in a monorepo the first tag of any *other* package will silently resolve to it.
The one-line fix is written out there and must land before a second package is tagged.

There is no user install. docstrap is pre-1.0, is not published to any index, and nothing for
`uv tool install docstrap` to resolve exists.

### §10.3 Running the tests

A bare `uv run pytest` at the workspace root fails collection on other packages' tests. Run
docstrap's suite against the package directly:

```bash
uv run --project packages/docstrap pytest packages/docstrap/tests
```

That regenerates an untracked `packages/docstrap/uv.lock`, which is not committed.

## §11 Not built

Ordered by rough priority, and every entry is a statement of what does not exist rather than a
commitment to build it. Priority order below has not been re-confirmed since the original spec was
written; treat the ordering as stale even though the contents are current. Sequencing is not this
document's job — [`docs/roadmap.md`](roadmap.md) is where the entries
that are actually next get named, and several of these are named there.

1. **The annotation client.** The database and the W3C API subset exist and nothing writes to them.
   Annotorious is the intended client (§6) and is a real external dependency that has not been
   added. When it is built is not scheduled.
2. **Tag index, backlinks, cross-project cross-linking, recent-updated feed.** Expected from the
   external aggregate module that was never adopted, and not replaced when docstrap grew its own
   aggregate. Whether they are still wanted is undecided.
3. **Editor SPA** — a full editor for content, not just answers.
4. **inotify daemon** — a filesystem watcher keeping the metadata DB in sync with observed events,
   autobuilding on change, and composing a section page again when a document appears in its
   directory. Long-standing intent rather than a new idea, and the intended mechanism for §7.8.5's
   requirement that a document is included *because it appeared*: it is the difference between
   indexing that is automatic and indexing that waits for somebody to run something. It writes the
   one path that changed into `file_index` through `docstrap.fileindex` (§5.2.4) and shares
   `docstrap.sectionindex` with the build rather than carrying its own copy of the rules; its output
   goes in the build area like everything else. Both seams exist; the watcher does not. Not built.
5. **MkDocs and Quarto layouts.** Both are stubs raising a not-implemented error. Their absence is
   why the vanilla-JS constraint on tools could be withdrawn: it was protecting portability to
   layouts that do not exist.
6. **MCP server** — docstrap operations as MCP tools for any MCP-speaking client.
7. **Team workflows** — shared or federated DB, approval with a multi-signatory model.
8. **CI/CD integration** — headless runs, artifact publishing, static-host publish targets. Note that
   `VERSIONING.md` §1 puts CI, a package index, publishing and release automation permanently out of
   scope for this workspace, which bears on this entry and has not been reconciled with it.
9. **Section-by-section status** — status per heading rather than per document, via W3C annotations.
10. **Activity concept** — session-binding between Claude and specific docs, MCP polling for
    review-submit events.
11. **Build-time SVG for mermaid** — via `mermaid-cli`, for zero-runtime-JS rendering. Requires an
    npm/mmdc dependency.
12. **Copy-vs-symlink for promdance** — considered if the symlink model proves limiting. It has not.
13. **Block provenance stamping, the quick-update tool, and the classifier instrument** — §7.3.
14. **A shared Svelte runtime across tool bundles.** Each bundle carries its own
    tree-shaken copy. ES-module bundles sharing a chunk would cut them all to roughly a third,
    but it changes how a tool's bundle is *served*, which is a declaration-surface decision rather
    than a build detail. `packages/docstrap/docs/tools-and-instruments.md` §5.1 has the measurements.

## Open questions

Raised by the 2026-09-01 reconciliation and not resolvable from the code. Numbered so
`docstrap questions` finds them; the enumeration is deliberately separate from the section numbers
above.

An answered question keeps its label and its number. The answer is written into the item, in the
corpus's own way, so the resolution travels with the question wherever it is read — and so nothing is
renumbered, because a number is half of the key an answer hangs on (§8.1.1).

**Q1.** This file is titled a specification and is cited by section number from six modules and a
test, but it sat in `proposals/`, where the folder rule says a document is under evaluation and not
approved. Should it move to `plans/`, be retitled to match the folder it is in, or stay as it is with
the contradiction accepted?
**Answered 2026-09-07 — it moves.** The captain promoted this file and the roadmap into `docs/plans/`,
so the folder now says what the citations already assumed. Every inbound reference was rewritten to
the new path; no section was renumbered, because six modules and a test cite these numbers.

**Q2.** There are two status vocabularies and nothing reconciles them. `metadata.VALID_STATUSES` is
closed and rejects anything outside six values; the strapdance reader's (the reader was removed on 2026-11-21) is deliberately open and
preserves anything verbatim. One document can hold `strapdance.status: ROADMAP` in front-matter and
`proposal` in the database at the same time, and neither is wrong by its own rule. Is one
authoritative, or are they meant to stay separate?
**Answered by the captain on 2026-08-28, recorded here 2026-09-07 — one shared vocabulary.** The
database and the front-matter are two places the same vocabulary is written, not two vocabularies.
The write commands keep the two in step going forward, and an asymmetry already in the corpus is
reported as a finding, never silently backfilled. §5.1 is the full statement.

**Q3.** Tag index, backlinks, cross-project cross-linking and a recent-updated feed were expected
from the aggregate module that was never adopted, and nothing replaced them when docstrap grew its
own aggregate. Are they still wanted?

**Q4.** The annotations database and its W3C API subset are complete and nothing writes to them.
Is Annotorious still the intended client, or should the store wait for a different one?
**Answered 2026-09-07 — it is Annotorious's store.** It was built for that client, which
`docstrap.annotations`' own docstring says outright ("enough for Annotorious to read and write"), and
Annotorious is a real external dependency that has not been added yet. So answers to a document's
questions do not go there: they go to the keyed answer file of §8.1. The `creator` column models a
different audience — whoever is reading a deployed site, identified by the deploying organisation's
user system, a Discord or Telegram handle, or an email address — and an answer to a `Q<n>` is a
decision by whoever owns the document, not a reader's remark on it.

**Q5.** §11 lists CI/CD integration as a roadmap item, while `VERSIONING.md` §1 puts CI, a package
index, publishing and release automation permanently out of scope for this workspace. Which of the
two statements stands?

**Q6.** The ordering of §11 has not been re-confirmed since the original spec was written, and four
of its entries did not exist then. Is the priority order still right?

**Q7.** Two entries in the promdance store, `isolated-tool-store` and `markdown-store`, were written
by docstrap's own test suite rather than by anybody drafting. Both are empty directories — the runs
that made them are the ones that proved `ensure_promdance` creates storage on demand, and they
predate the `user_dirs` fixture that now redirects XDG directories at a throwaway home, so no test
can create another. They are committed in the store's first commit as the empty directories they are,
which costs nothing, since git records no empty directory. **What would be done, if it were an
agent's call: delete both, and nothing else.** They hold no content, nothing links to them, and
`promdance status` will keep listing them as store entries that no project claims. It is not an
agent's call, because the store is the one directory in this system whose contents are irreplaceable,
and "it looked empty" is precisely the reasoning that should never be enough to delete something
there. Should they be removed?

**Q8.** `trk_tdp/from_web/` is 26 files and 5.4 MB of a saved Gemini web page — `gemini - eos_app
.html` with its `_files/` directory — and it is the great majority of the store by size; everything
else together is 536 KB. It is not a draft. Looked at before the store's first commit, it carries the
captain's personal Google address seven times, Google's own public browser API keys (`AIzaSy…`, which
every Google page embeds and which are referrer-restricted, not his), and sixteen WSL
`:Zone.Identifier` alternate-data-stream files. No private key, no session cookie, no credential of
his anywhere in the store; `rl_deployment/drafts/staging-on-arrow.md` names Pulumi secret *keys* but
holds no values. So nothing here is dangerous on a machine — but it is the one thing in the store
that is neither a draft nor obviously his to publish, and it would be the bulk of what a first push
sends. **It is committed locally and nothing has been pushed**, because docstrap creates no remote
(§8.4.3): publication cannot happen until a repository is created by hand and named with `promdance
store remote <url>`. Should `from_web/` be in the store's history before that happens, and if not,
should it be removed from the store or only from what is tracked?

**Q9.** *Ruled, 2026-09-30.* This asked whether `packages/docstrap/docs/notes/index.md` — docstrap's
own generated section page with one line appended by hand, therefore `divergent` and left alone by
the §7.8 purge — should be deleted and the section composed, or kept as an authored page. The captain
ruled it out along with every other index file in a docs tree: *"no index.md in docs/ trees. At all.
period."* The file is deleted and §7.8.6 is the rule. The label stays because the questions here are
found by their labels and a gap in the run hides the ones above it.

**Q10.** The `index.md` files tracked in `platformshoes` that sat in directories no `.docstrap`
declares are down to four, all of them `docs-site/` section landings — `docs-site/formizer`,
`docs-site/laces`, `docs-site/object-brewer`, `docs-site/pitches`, beside `docs-site/index.md`
itself. `generated-indexes` cannot reach any of them and never reported on them; the six
"Docs directory placeholder" files that were in the same position — `apps/ccpane`, `apps/charmoji`,
`apps/pd`, `packages/git_id`, `packages/object-brewer-ui`, `packages/repo-migrations` — were deleted
under §7.8.6 along with the trees' declared ones. `docs-site/` is a hand-maintained Sphinx source
root rather than a document directory, which is why §7.8.6's check reports its files without failing
on them. Should those directories be declared projects so the report covers them, or are they
deliberately outside the site?

**Q11.** A build's scratch tree now holds one zero-byte `index.docstrap-section` marker per section
instead of composed markdown, which is why "HTML only" cost nothing in navigation (§7.8.2). Reaching
literal zero files needs private Sphinx internals and was refused on those grounds. Is an empty
marker inside the build acceptable as the permanent shape, or should docstrap accept the coupling —
or stop using Sphinx's toctree for section navigation — to remove it?

**Q12.** `file_index` is written by a build against `~/.local/share/docstrap/metadata.db`, so
building a project is now a write to the metadata store as well as a read of the project. That is
what makes the table answerable without the filesystem and what a watcher will write into. It is also
a new source of rows in a database whose document rows are 59 of 64 test residue awaiting a ruling
(Q7's neighbourhood). Is a build writing index rows into the metadata store the right arrangement, or
should the index live in a file of its own that can be deleted without opening that database?

**Q13.** A relative markdown link between documents emits `myst.xref_missing` on every docstrap
build, because the documents are symlinks and MyST resolves the link through the link into the
project, which is not in the build. The links all render correctly and every target exists, so it is
noise — but it is 28 warnings on docstrap's own docs alone, and a build's warning count is what its
notes report, so a real warning would be hiding in it. Ten of the 28 are new: a project's `index.md`
used to be copied into a generated landing page, so its links resolved inside the build, and it is
now a symlink like every other document. Is making relative cross-document links resolve inside the
build worth doing, and if so should the fix be a MyST/Sphinx setting or a change to how documents
reach the scratch tree?
