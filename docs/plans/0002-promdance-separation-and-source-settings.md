# Plan 0002 — Promdance as a plugin, and source folders from settings

Plan, approved by the captain on 2026-10-30 from proposal 0005 (written 2026-10-29). The stages in §8.2 are the build order; stages 1 and 2 are built, and `docs/implementation-record.md` §1.3(31) and §1.3(32) record how they landed.

## §1 Purpose

Promdance is its own subsystem. It manages a draft store, interning, backup and the store's git, and
it is not part of documentation publishing. Today its command still ships inside the docstrap
package (`docstrap.promdance:app`), and docstrap's build, answer store, addendum and review route
call into it. This plan does two things.

First, it moves promdance into its own package. Docstrap stops importing it, and the two meet at a
plugin seam that docstrap defines and promdance implements. A user or a project turns promdance on
through docstrap's existing settings, and the promdance CLI writes those settings for them.

Second, it takes the built-in folder names out of docstrap. Where a project's documents are, and
what role each folder plays, is read from the user config and overridden by the project's
`.docstrap` file. This follows the 2026-09-15 ruling: a directory's role is not derivable from its
name, the vocabulary of roles is open, and there is one configuration surface, not two.

Both changes land on the same surface. A plugin's settings and a project's source folders live in
the same two files that already exist, `~/.config/docstrap/config.yaml` and `.docstrap`.

## §2 What exists today

The coupling is wider than the four import sites:

1. `layouts/markdown.py` imports `ensure_promdance` and `installation_setting`. A build wires each
   project to the store and mirrors the project's `promdance/` under a `promdance` mount.
2. `answers.py`, `addendum.py` and `tools/review/routes.py` import `promdance_project_root` from
   `tools/derivatives.py`. Every answer, addendum and review record is written into the project's
   promdance store entry.

The name `promdance` is also built into the following:

1. `paths.py`, which owns the store path and creates it during `docstrap init`.
2. `config.py`, `user_config.py` and `scan.py`, which carry the tri-state `promdance` field at three
   levels plus `promdance_projects_root`.
3. `projectscope.NEVER_WALKED` and the build mirror's `skip_names`.
4. `gitignore.REQUIRED_PATTERNS`.
5. `sphinx/promdance_answers.py`, `fileindex.DRAFTS` and `sectionindex.DRAFTS_CAPTION`.
6. `doctor.py`, through `placement.shared_entries`.
7. The tool route base, `/api/promdance/{project}`, in `tools/declaration.py`.
8. `placement.py` and `storegit.py`, which are promdance's own logic sitting in docstrap.

Built-in folder names appear in four places. `docs` is the default `docs_root` in `config.py` (twice)
and in `cli.register`, and is `doctor.DEFAULT_DOCS_DIRECTORY`. `apps`, `packages` and `docs` together
form the member rule in `placement.py`.

## §3 Promdance as its own package

`packages/promdance/` becomes a uv workspace member with its own `pyproject.toml`, `src/promdance/`,
tests and README. It holds `promdance.py` (the CLI, split into modules as it moves), `placement.py`,
`storegit.py`, the store-path helpers now in `paths.py`, and the 7 test modules that import these.
`find_gitignores_missing_promdance` and backup move with it. The console script becomes
`promdance = promdance.cli:app`.

The dependency runs one way: promdance depends on docstrap, and docstrap never imports promdance.
Promdance uses docstrap's public modules where docstrap is the one owner: `slugs`, `config`, `scan`,
`projectfinder`, `strapdance`, `gitignore`, `forge` and the new `settings`. A test in docstrap fails
if any `docstrap` module imports `promdance`. The pattern is the same as the `forge` fingerprint
test.

The answer loop stays in docstrap. `answers.py`, `pairing.py`, `addendum.py`, `answers_done.py` and
the qa, qapanels, review and tasks tools are docstrap features. Promdance only provides the place
where their files are written.

What stays the same: the store at `~/.local/share/promdance/`, each project's `promdance/` symlink,
the `promdance` command and every subcommand, and the backup repository at
`~/.local/share/docstrap/promdance-backups`. Promdance builds that last path from
`docstrap.paths.data_dir()`, and it is the only place promdance writes inside docstrap's data
directory.

## §4 The plugin seam

The mechanism is **pluggy**, which the spec has named for this since §8.7 and which is already in
the lock through pytest. `docstrap.plugins` declares the hookspecs and owns one `PluginManager`. It
loads installed plugins with pluggy's `load_setuptools_entrypoints("docstrap.plugins")`. A package
declares itself under that entry-point group, and promdance declares
`promdance = "promdance.plugin"`.

**Being installed does not turn a plugin on.** A plugin runs for a project only when settings enable
it there (§5.3). Docstrap calls a per-project hook through pluggy's `subset_hook_caller`, which
removes the plugins not enabled for that project. Docstrap writes none of its own filtering.

The hooks are listed below. Each names the code it replaces.

1. `docstrap_prepare_project(project, settings)` runs before a project's build mirrors anything.
   Promdance's implementation is today's `ensure_promdance`, with the same opt-out and worktree
   rules. This replaces `layouts/markdown.py`'s import of `ensure_promdance` and
   `installation_setting`.
2. `docstrap_project_sources(project, settings) -> list[Source]` lets a plugin add source folders to
   a project (§5.1). Promdance returns one folder with role `draft` and mount `promdance`. Its path
   is the project's own `promdance/` if that exists, and otherwise the store entry, which is today's
   `promdance_content_src` rule. This replaces that selection in `markdown.py`, the `"promdance"`
   entry in `skip_names`, and the one in `projectscope.NEVER_WALKED`.
3. `docstrap_draft_root(project_slug) -> Path | None` is a `firstresult` hook that says where a
   project's derivatives are written. Promdance returns the store entry and creates it, as
   `promdance_project_root` does today. `docstrap.drafts.draft_root` asks the hook first. If no
   plugin answers, it falls back to the project's declared `draft` source, and failing that it
   returns nothing. This replaces the `promdance_project_root` import in `answers.py`, `addendum.py`
   and `tools/review/routes.py`, so `tools/derivatives.py` goes away. A project with no draft root
   is not offered the tools that write derivatives, which the launcher's existing offer rule already
   supports.
4. `docstrap_gitignore_patterns() -> list[str]` contributes `.gitignore` lines. Promdance contributes
   `promdance`. This replaces the entry in `gitignore.REQUIRED_PATTERNS`.
5. `docstrap_init() -> list[tuple[str, Path]]` creates a plugin's directories during `docstrap init`
   and returns them as labelled paths to report. This replaces the store path in `paths.ensure_dirs`
   and the `promdance:` line `cli.init` prints.
6. `docstrap_doctor_report(root) -> list[Finding]` adds plugin findings to `docstrap doctor`. This
   replaces doctor's call to `placement.survey` and `placement.shared_entries`, and the `promdance`
   lines in `cli.doctor`.

Two couplings become docstrap concepts rather than hooks. `sphinx/promdance_answers.py` becomes
`sphinx/answer_drafts.py`, which keeps a draft answer off the published page. It finds the answer
file under the mount of the project's `draft` source, not under a hard-coded `promdance`. The
`DRAFTS` grouping and its caption become the source's role (§5.2).

The tool route base in `declaration._TARGET_ROUTE_BASE` changes from `/api/promdance/...` to
`/api/tools/...`. Tool clients get their routes from the declarations, so this is a change to one
mapping and does not reach the client code.

## §5 Source folders and their roles, on the one settings surface

### §5.1 The `sources` field

A **source** is a folder that a project publishes, with a role:

1. `path` is relative to the project root. It is required.
2. `role` is a word from an open vocabulary such as `documentation`, `planning` or `draft`. It is
   required, because docstrap is told a folder's role rather than guessing it from the name.
3. `mount` is where the folder appears in the built site and in document identity. It is optional.
   By default the first source in the effective list mounts at the project root, and every other
   source mounts at its own `path`.

The first-source default is what keeps every existing document identity the same. A project whose
`docs_root` was `docs` still has `proposals/0002-the-upgrade-path` and not
`docs/proposals/0002-the-upgrade-path`. A document in any other source is identified by its mount
plus its path below that source. That is how a draft is already named today: `promdance/notes`.

`sources` can be stated at three levels, and the most specific level that states a list wins whole.
The lists are not merged:

1. **Installation**: `sources` in the user config.
2. **Repository**: `sources` at the top level of a `.docstrap` file.
3. **Project**: `sources` on one `projects:` entry, or on one `related_directories` entry.

Sources contributed by plugins (§4 hook 2) are added after that. `docs_root: X` remains a valid
shorthand for `sources: [{path: X, role: documentation}]`, so the twelve existing projects need no
edit. **Docstrap has no built-in folder name.** If nothing states a list, the project has no
sources, and the landing page reports that the same way it reports a missing `docs_root` today.
Nothing creates the folder. A related directory with neither field keeps today's rule, which is that
the directory itself is the source.

```yaml
# ~/.config/docstrap/config.yaml
version: 1
stores: [/home/user/src/example/.docstrap]
sources:
  - {path: docs, role: documentation}
plugins:
  promdance:
    enabled: true
    projects_root: ~/src
    members: ["apps/*", "packages/*"]
```

```yaml
# .docstrap in a repository that keeps specifications apart from documentation
version: 1
title: example
sources:
  - {path: spec, role: planning}
  - {path: docs, role: documentation}
projects:
  - path: packages/tool
    sources:
      - {path: docs, role: documentation}
    plugins:
      promdance: {enabled: false}
```

### §5.2 What docstrap does with a role

Docstrap gives special behaviour to one role. A `draft` source is published under its own group on
the project landing page. It is never walked as a document by `ProjectScope.documents` or
`docstrap questions`, and it is the fallback draft root of §4 hook 3.

Every other role, including `documentation` and any word a project invents, is published, is
walked, and gets its own group on the landing page with the role as the caption.

The role is stored in `file_index.grouping`, the existing `TEXT` column that holds `docs` and
`drafts` today. **No column is added**, as the no-upgrade-path rule requires. `exclude_dirs` and
`exclude_file_suffixes` apply inside every source. The build mirrors each source into the scratch
tree at its mount, which generalises today's single `promdance` mount. A directory that is itself a
declared source is skipped by the mirror of the source that contains it.

### §5.3 The `plugins` field

`plugins` is a mapping from a plugin's name to that plugin's settings block. It is valid at the same
three levels as `sources`. Docstrap reads one key from a block, `enabled`. It keeps the tri-state
semantics of spec §8.5, where an absent value means that level said nothing and the more specific
level wins. Docstrap passes every other key to the plugin, unread, merged key by key with the more
specific level winning. The plugin validates its own keys.

A plugin is enabled for a project when the most specific level that states `enabled` says `true`.
If no level states it, the plugin is not enabled.

For promdance this keeps the opt-out the captain ruled on. Once the installation level says
`enabled: true`, every repository and project is on unless it says otherwise. The change is that a
machine where promdance was installed but never enabled runs none of its code. That follows from
promdance no longer being part of docstrap.

Promdance's own keys:

1. `projects_root` replaces the user config's `promdance_projects_root`.
2. `members` is a list of globs, relative to a repository root, that name candidate workspace
   members. A candidate counts as a member when it holds a folder named by its effective `sources`.
   This replaces `placement.MEMBER_GROUPS` and `DOCS_DIRNAME`, so placement has no built-in folder
   names either.

### §5.4 One owner for settings

`docstrap.settings` resolves the three levels for `sources` and `plugins`, and it is the only code
that writes to either file. Writes go through **ruamel.yaml** round-trip mode, so a person's
comments and key order survive. The current `yaml.safe_dump` in `user_config.save` would discard
them. `config.py` keeps parsing, and `user_config.py` keeps the stores list.

ruamel.yaml is a new dependency. It will be added with `uv add` in the stage that needs it, and the
captain will be told first.

## §6 The promdance CLI writes the integration setting

1. `promdance enable [--user | --repository PATH | --project PATH]` writes
   `plugins.promdance.enabled: true` at the chosen level. With no flag it writes at user level.
2. `promdance disable` takes the same flags and writes `false`.
3. `promdance settings` reports the effective value at each level, and which level decided.

These commands call `docstrap.settings.write_plugin_setting(level, target, "promdance", key, value)`
and never edit a file themselves. Each one is idempotent and prints the file and the line it
changed.

`docstrap plugins` lists the installed plugins and where each one is enabled.

`scripts/docstrap-stable.sh` installs promdance into docstrap's tool environment
(`uv tool install … --with promdance`), so the plugin can be imported wherever docstrap runs.

## §7 A clean documentation set for docstrap

`packages/docstrap/docs/guide/` is written from the code as it stands after these stages, for a
reader who has never seen this workspace. It could seed a public repository unchanged:

1. `README.md`: what docstrap is, installing it, and a first build in five minutes.
2. `concepts.md`: projects, stores, sources and roles, document identity as a path, section pages,
   and tools versus instruments.
3. `configuration.md`: the user config and `.docstrap` reference, covering `sources`, `plugins`,
   `exclude_*`, the three levels and the precedence rule.
4. `cli.md`: every `docstrap` command.
5. `questions-and-answers.md`: `Q<n>` labels, the answer store, submission, and the addendum.
6. `front-matter.md`: the strapdance namespace and its fallback chain.
7. `tools.md`: writing a tool, covering the declaration, routes and the UI build.
8. `plugins.md`: the hookspecs of §4, the entry-point group, and promdance as the worked example.

Promdance gets its own `packages/promdance/README.md` with its commands and settings.

The guide contains no private project, host, machine or person names and no home-directory paths.
A test in `tests/` holds a deny list and fails if any guide file matches it. The deny list lives
outside the guide so that the list itself is not published.

`docstrap_on_2026-09-01.md`, `implementation-record.md` and `roadmap.md` keep their jobs and their section numbers.
The guide describes how to use the tool. The spec keeps the decisions and the evidence behind them.

## §8 Migration and stages

### §8.1 Migration

`docstrap config migrate [--dry-run]` makes these changes:

1. It rewrites the user config. `promdance` becomes `plugins.promdance.enabled`, and an absent value
   becomes `true` so the current machine keeps its opt-out behaviour. `promdance_projects_root`
   becomes `plugins.promdance.projects_root`. It adds `members: ["apps/*", "packages/*"]`, and it
   adds `sources: [{path: docs, role: documentation}]` so that every `.docstrap` relying on the old
   implicit `docs` default keeps building the same tree.
2. It rewrites `promdance:` in each registered store's `.docstrap`, at the top level and on each
   entry, to `plugins.promdance.enabled`.
3. It reports every file it changed. It moves no file and touches no database.

An old-shape `promdance:` key that is still present afterwards is a load error naming
`docstrap config migrate`. It is not read silently, which follows roadmap §4.18: being out of date
should be loud.

No stored data moves. The store, the answer files, the addenda, the symlinks and `metadata.db` stay
where they are, because hook 3 returns the same path `promdance_project_root` returns today.

### §8.2 Stages

Each stage leaves the suite green and the live installation building.

1. **One settings surface.** Build `docstrap.settings`, `sources`, roles and mounts, the `plugins`
   block, ruamel round-trip writes and `docstrap config migrate`. Promdance stays in the package and
   reads its setting from the new block.
2. **The seam in place.** Build `docstrap.plugins` and the six hooks, with promdance registered as
   an internal plugin. Rename the route base and replace the `answer_drafts` extension. After this
   stage no docstrap module outside the promdance files names promdance.
3. **Promdance moves out.** Create `packages/promdance`, move the console script, the modules and
   the 7 test modules, add the entry point and the import-fence test, and update the stable install.
   Correct `AGENTS.md`, whose "One owner" items 2 and 7 will then name moved files.
4. **The documents.** Write the guide set and its deny-list test, and bring `docstrap_on_2026-09-01.md` §3, §4.3, §8
   and §10 into line with the code. Keep the section numbers and archive the stale text.

## §9 Architecture and tradeoffs

This design puts a project's draft area on the same surface as every other source folder: it is one
source with role `draft`. That is why a project without promdance can still declare a draft folder
and get the answer loop, and why promdance needs only six narrow hooks rather than a layout of its
own.

It costs three things:

1. **Mount-prefixed identities.** A document in any source other than the first is identified by a
   mount-prefixed path. Moving a folder up or down the `sources` list changes its documents'
   identities. Answers survive that, because they are keyed on the metadata document id. URLs do
   not.
2. **Two descriptions of the tool.** The guide and the spec both describe what the tool does, and
   they can drift apart.
3. **A one-time change for fresh installs.** A new machine has to run `promdance enable` once,
   because docstrap no longer turns promdance on by itself.

## Open questions

**Q1.** On a machine where promdance is installed but has never been enabled, should promdance stay
off until `promdance enable` is run, as §5.3 has it, even though promdance has been opt-out
everywhere until now?

**Q2.** Which licence will the public repository carry? The package declares `proprietary` today.
The guide's text does not depend on the answer, but its `README.md` will state it.
