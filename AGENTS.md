# AGENTS.md

This file provides guidance to agents working with code in this repository.

## Running the Suites

```bash
uv run pytest
npm test
```

`npm ci` is needed before `uv run pytest`, because part of the suite runs the TypeScript tests under
Node. The README's "Install" section has the setup.

**That suite used to write to the live database.** Until 2026-10-27 several tests ran against the real
`~/.local/share/docstrap/metadata.db`, and `test_cli_errors.py::test_tag_reports_metadata_error_without_traceback`
left one permanent row per run, pointing at a `/tmp` path. `tests/conftest.py` now gives every test a
throwaway home. The rows stay: on 2026-09-17 that was **59 of its 64 document rows**; four rows point
at a document that exists. So do not read a row count there as a count of real documents, and do not
assume the file is only ever written by a person using the tool. There is no backup of that file.
`docs/proposals/0002-the-upgrade-path.md` opening fact 7 has the detail.

## The Databases Have No Upgrade Path — a table is safe, a column is not

`PRAGMA user_version` is 0 on both `metadata.db` and `annotations.db`, every table is created
`CREATE TABLE IF NOT EXISTS`, and there is no migration machinery. **An existing database therefore
never gains a column and nothing says so** — change `metadata.SCHEMA` and a user's data silently
stays on the old shape. Do not add a column to either `SCHEMA` expecting existing databases to pick
it up.

Adding a **table** is the one exception and it is load-bearing: the schema is replayed on every open,
so a table missing from an existing database is created by that replay and reaches every database
already out there. `file_index` was added on those grounds. `src/docstrap/metadata.py`'s docstring
states the asymmetry; `docs/proposals/0002-the-upgrade-path.md` is the plan for fixing the rest
(under evaluation, not approved) and `docs/roadmap.md` §4.18 is its entry. Its §12 covers the
promdance store, which is a third persistent state with the same problem and no schema to stamp.

## Docstrap Tool UI — there is a frontend build

A docstrap tool's on-page UI is Svelte, compiled from `src/docstrap/tools/<id>/ui/` into that tool's
`static/` under the filename its declaration derives. **The built files are committed, and nothing
rebuilds them for you**: after changing anything under a tool's `ui/`, run `npm run build` and commit
the changed bundles, or the tests pass against stale output. See the README's "Install" section, and
`docs/tools-and-instruments.md` §1.1 for why tools are Svelte and why Skeleton is for instruments
only.

`TypeError: Cannot read properties of undefined (reading 'onerror')` from inside Svelte's runtime,
on a tool that works unminified, is the build target and not your component — that error is thrown
*by* the error handler and replaces the real one. `docs/tools-and-instruments.md` §5.2.

## A Document Is Addressed By Its Path, and a Project By Its Slug

A document's identity is its **path** below the project's `docs_root` with the suffix dropped —
`proposals/0002-the-upgrade-path` — produced by `projectscope.document_slug` and carried in the
page's `docstrap-doc-slug` meta tag. **Never slugify it to make a URL fit**; that was proposed and
declined, because a document management tool handles paths. Tool routes carry it as a path
(`declaration.as_server_path`), and the launcher quotes it with `/` safe while a project slug is
quoted with nothing safe. Spelling it as one segment 404ed every document-targeted tool on every
nested document — 666 of 686 published pages — while blaming `docstrap serve`.

A **tool route is a base plus one static collection and nothing deeper.** That is what keeps
`…/{project}/{collection}` and `…/{project}/{doc_slug}/{collection}` from capturing each other now
the document parameter is greedy; `declaration.check_route_separation` refuses a deeper route at
mount time. Operations are distinguished by method, never by a sub-path.

A page that belongs to **no** project carries none, and nothing invents one from a title — that is
how a store's front page came to advertise a project that did not exist. `tool_support` guesses a
slug only for a non-aggregate build with no scanned slug. `docs/tools-and-instruments.md` §2 has both
rules; `tests/test_nested_document_routes.py` and `tests/test_page_project_context.py` hold them.

In the client, only `src/docstrap/sphinx/ui/docstrap.ts` may say `docstrap serve` is not running, and
only when a call produced no response at all. A status code means the server answered;
`describeApiFailure` is the one wording and a test holds it to that one file.

A project is addressed by its SLUG, never its title. The build carries the scanned slug into the
generated `conf.py` as `docstrap_project_slug`; tool routes read it back from the page context.

## Open Questions Are Numbered `Q1`, `Q2`, `Q3`

A document's open questions go in a section at its end, each item labelled `Q<n>.` — an enumeration
kept separate from section numbering. That convention is load-bearing: `docstrap questions [PATH]`
finds a document's questions by the label alone and interprets no question mark, so an unnumbered
question is invisible to it. Follow the convention when writing docs here.

A run is scoped to ONE project: a directory argument resolves through `docstrap.projectscope` to the
project that owns it and reads only that project's declared documents, so the workspace root has no
single context and is refused rather than answered library-wide.
`docs/finding-questions.md` has the three rules, the scoping, and why prose analysis was rejected.

## An Index Is HTML, Never Markdown — and a Build Writes Nothing Into a Project

**No docstrap build produces markdown.** Not in a project, not in the build, not as a temporary file.
A section page, a project's landing page and a store's aggregate page are composed as docutils nodes
during the Sphinx run and written out as HTML. What a build puts in its scratch tree is a `conf.py`
and a zero-byte `index.docstrap-section` marker per section, whose parser
(`src/docstrap/sphinx/composed.py`) composes the page.
`docs/docstrap_on_2026-09-01.md` §7.8.2 is the mechanism, the alternatives rejected, and the one cost.

A build also reads a project and never writes into one: the layout mirrors `docs_root` as real
directories with symlinked *files*, so there is no symlinked directory to write through, and
`_write_generated` refuses any destination outside the build.

What a published directory contains comes from the `file_index` table (spec §5.2), owned by
`src/docstrap/fileindex.py`, filled as the build mirrors. `sectionindex.compose`
answers from it and touches no filesystem. **Nothing is cached**: indexing 100 documents costs 0.4%
of the build that publishes them, so do not add invalidation, staleness checks or a cache layer.

**Indexing is not optional and is never an agent's job.** Every published directory gets a section
page, composed by the tool. A design that asks a person or an agent to maintain an index is the thing
§7.8 rules out.

`docstrap generated-indexes [PATH]` reports which `index.md` files earlier builds left in a project.
Its recogniser is **frozen** — `generated_indexes.legacy_markdown`, a deliberate copy of what builds
up to 0.0.3 wrote, shared with nothing, because a recogniser of the past has to keep describing the
past. It claims a file only when it is byte-identical to those bytes; stale docstrap output and
another tool's page both come back unclaimed, deliberately. Never classify these by reading their
prose; that was tried and it classified them wrongly. It reaches only directories a `.docstrap`
declares, so a file it does not mention is not a file it cleared.

## One Owner — Slugs, Promdance Storage, and the Answer Loop

Each of these has exactly one owner, because having two of the first two silently orphaned
submitted answers and made `docstrap init` report a draft root nothing wrote to. Section numbers
here are in `docs/docstrap_on_2026-09-01.md`.

1. **Slugs** — `src/docstrap/slugs.py`, a thin wrapper over `python-slugify`
   adding the one docstrap rule (a path separator becomes `__`). Nothing else turns text into a
   name; a test fails if a second slugifier appears.
2. **Promdance storage** — promdance's `src/promdance/paths.py`. Drafts live under
   `~/.local/share/promdance/<slug>`, deliberately outside docstrap's own data dir. Promdance is a
   separate package whose consuming workspace is platformshoes, so its files are not in this
   repository.
3. **Answers** — `src/docstrap/answers.py`, one keyed markdown file per project at
   `<project-promdance>/answers.md`. Its writers (the qa tool, the qapanels instrument, the task
   tool's decisions) go through it. An answer is keyed on the metadata store's document id plus the
   question's own `Q<n>` label, so it survives a rename and answering twice supersedes. §8.1.
   An answer carries whether it was **submitted**, and that field is tri-state: absent means a row
   written before the distinction existed and counts as submitted. Absent is never written back, so
   the ten real answers in `~/dkp/promdance/answers.md` survive a rewrite byte for byte. §8.1.3.
4. **Pairing questions with answers** — `src/docstrap/pairing.py`. `questions.py`
   reads `Q<n>` labels and knows nothing of answers; `answers.py` is emphatic that it is not an index
   of questions. This is the one place the two are put side by side, and both surfaces project it:
   the qapanels route for EDITING (a writer gets their draft back) and `/api/answers` for READING (no
   draft, ever). §8.2. Named `pairing` and not `qa` because `tools/qa/` is the answering form tool.
5. **Section pages** — `src/docstrap/sectionindex.py`, which decides what a section
   page contains (`compose`, from the file index, touching no filesystem) and which directories are
   sections (`is_section_dir`, and `sites` over it). It never writes. The build, the
   `generated-indexes` report and the planned watcher all call it; a second implementation would mean
   a report that disagrees with the build about which files are the build's.
6. **The delivered artifact** — `src/docstrap/addendum.py`. A submission writes
   `<doc-slug>__answers.md` beside the document, at a stable path, carrying an `answered_version`
   digest over what was decided and nothing else. Both writers call the one function. §8.3.
7. **The store's own git** — promdance's `src/promdance/storegit.py`. Init, remote, commit,
   push, and nothing else. §8.4.
8. **Source-control provider specifics** — `src/docstrap/forge.py`. A test fails
   if `github.com` or a provider CLI appears in any other module. §8.7.
9. **The file index** — `src/docstrap/fileindex.py`, the only reader or writer of
   the `file_index` table. Written one path at a time (`record`, `forget_path`) with the
   whole-project `reconcile` built from those, because a watcher only ever knows one path. Spec §5.2
   says why it is its own table and how a rename survives it.

## Promdance: docstrap Creates No Repository

The promdance store at `~/.local/share/promdance/` is a git repository. **The user creates its
remote** — their account, their service, their name — and hands docstrap the URL with
`promdance store remote <url>`; run it bare for a suggested name. Nothing in docstrap reaches a
hosting service on its own initiative, and that is the design rather than a gap: choosing the host
and handing over a key *is* the consent, so there is no agreement flow to build.
`docs/docstrap_on_2026-09-01.md` §8.4.3.

Backup identity is a canonical directory, never a slug: `projectfinder.canonical_dir` resolves a path
through `git rev-parse --git-common-dir`, and backup destinations are named from the store entry or
from the content's own filesystem path. Naming them by slug is why `promdance backup` had never once
completed a run.

## Governing Documents — folders carry weight, and stale text is deleted

A document in `docs/plans/` has been evaluated and approved; one in `docs/proposals/` is under
evaluation and is NOT approved. Weight follows the folder.

When a governing document falls behind the code, **remove or archive the stale text — do not mark it
superseded and leave it in place.** Git is the record of what it used to say; an agent reading the
live file still reads whatever is left there. Substantive removals go to `docs/archive/`, which
docstrap's default `exclude_dirs` keeps out of the built site — see
`docs/archive/superseded-2026-09-01.md`.

`docs/docstrap_on_2026-09-01.md` is cited by section number from this file and from other documents
in this repository. Do not renumber it.

## Naming Work — no MVP framing, no bare phase numbers

docstrap is a delivered tool: installed through the stable path, dogfooded, building twelve projects
across three registered stores. **Do not write anything that treats the present state as
pre-product** or as a march toward a first usable release; "MVP" is retired as a framing.

Name work by the version state it lands in (`x.y.z`, nothing else) or by a phrase saying what it
delivers. A phase number standing alone is never a name. An "Alpha N" label already committed
somewhere scopes that *component's* own maturity and is left where it is — do not extend the series
and do not hunt existing uses down.

Three docstrap documents, each with one job: `docs/docstrap_on_2026-09-01.md` is what the tool does,
`docs/implementation-record.md` is what landed and how it differed from what was planned, and
`docs/roadmap.md` is what comes next. Sequencing goes in the roadmap and nowhere else. An open
question is answered by the captain, never by an agent writing an answer into a document.

## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.
