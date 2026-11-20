# docstrap — superseded design material, removed 2026-09-01

Retired sections lifted out of `docs/proposals/docstrap.md` (promoted to `docs/spec.md`
on 2026-09-07) and `docs/plans/docstrap-mvp.md` (renamed
`docs/implementation-record.md` on 2026-09-01) when
those two were reconciled against the code on `main` at commit `47d7de7`.

Nothing here describes docstrap as it is. It is kept because each item was a real design decision
that was later decided differently, and the decision is easier to read here than to reconstruct from
a diff. **Do not implement anything on this page.** For what docstrap does, read the two live
documents, and `packages/docstrap/` above them.

`docs/archive/` is in docstrap's default `exclude_dirs`, so this page is not published to the site.

Removed material that was merely wrong in detail — a port number, a flag, "adds tags" where the code
replaces them — is not reproduced here. It was deleted, and `git log` has it.

## 1 From the specification

### 1.0 §0 Genesis — removed as history

The specification opened with a distillation of the session that produced it, headed "§0 Genesis". It
was accurate about that session and is now the least reliable part of the document, because it
described the intended shape of a tool that has since been built differently. Three of its claims
were superseded outright: that every substantial capability is delegated to an existing tested system
including "an existing aggregate module" and Annotorious (§1.1 and §1.3 below), that docstrap is
"glue code" (the tool declaration surface, the launcher and the strapdance reader are docstrap's own
architecture, not glue), and its list of what MVP excludes.

The section numbers after it closed up. Nothing in the code cites §0, §1 or §2 of the specification;
the numbers the code does cite — §3, §4, §5, §6, §9 — were preserved unchanged.

### 1.1 The external aggregate module — never adopted

Removed from §1 and §2. The specification's central delegation claim.

> Aggregate site (cross-project navigation, search, tag index, backlinks, recent-updated feed) is an
> external module already proven in the current platformshoes `docs-site/` setup. docstrap invokes
> it; docstrap does not reimplement it.

And from §1: "…and hands the built output off to an existing external aggregate module for
cross-project navigation, search, and cross-linking."

No such module was ever integrated and no handoff exists in the code. What replaced it: two further
Sphinx passes over generated index pages sharing the projects' own furo theme, and Pagefind for
search. Live account in §2 of the specification.

Four capabilities the external module was expected to bring did not arrive with the replacement and
have no successor: **tag index, backlinks, a recent-updated feed, and cross-linking between
projects.** Whether they are still wanted is undecided; that is recorded in the live §11, not here.

### 1.2 Three named Sphinx plugins, in vanilla JavaScript — superseded 2026-08-27

Removed from §1, §7 and its subsections. The original design named three extensions and pinned each
to a hand-written client file:

> **Three docstrap Sphinx plugins**, shipped in the docstrap package as extensions loadable via
> `extensions = [..., "docstrap.sphinx.status_widget", "docstrap.sphinx.qa_widget",
> "docstrap.sphinx.review_widget"]` in a project's `conf.py`.

with `src/docstrap/sphinx/status_widget.py`, `qa_widget.py`, `review_widget.py` and
`static/docstrap-status.js`, `docstrap-qa.js`, `docstrap-review.js`, and each widget injecting its
own floating button.

Two decisions retired it.

1. **The tool declaration surface**, 2026-08-27 (`b9968ba`). A tool is a directory carrying a
   declaration; the route prefix, the launcher offer, the bundle names and the `conf.py`
   `extensions` list are all derived from it. `server.py` names no tool URL, and no registration
   list exists to forget to append to. The three per-widget floating buttons became one launcher.
2. **Svelte**, captain, 2026-08-27: *"svelte unless it's truely tiny."* The no-build-step rule was
   protecting MkDocs and Quarto portability — a capability that does not exist, since both layouts
   raise not-implemented — while the cost of hand-written UI was paid on every tool, every day.

The live account is §7 of the specification and `packages/docstrap/docs/tools-and-instruments.md`.

### 1.3 The Annotorious embed — specified, not built

Removed from §1, §6 and §7. The specification counted an embedded Annotorious client as in-scope for
MVP:

> **Annotorious embed:** The docstrap Sphinx plugins also inject the Annotorious client `<script>`
> on rendered pages, configured to point at docstrap's app-server API endpoints from §6. Users
> annotate with Annotorious's UI (highlight, comment, tag); annotations persist in the annotations
> DB.

The server half shipped and is live: the annotations database, and the W3C Web Annotation Protocol
subset that serves it. The browser half was never written, so nothing writes to that database today.
Recorded in the live §6 as an absence rather than kept here as a plan.

### 1.4 Per-project promdance git repositories — superseded 2026-08-25

Removed from §8.

> **Docstrap-side canonical location:** `~/.local/share/promdance/<project-slug>/` — this is its own
> git repository (`git init` at creation; user configures its own remote if they want distributed
> backup).

The storage path survived; the per-directory `git init` did not. `docstrap.promdance.ensure_promdance`
creates the directory and does not initialise a repository in it. Backup is instead one git
repository at `~/.local/share/docstrap/promdance-backups`, into which `promdance backup` mirrors
every discovered draft directory and commits only when something changed. "User configures its own
remote" went with it: the backup command never adds a remote and never pushes.

### 1.5 The `docstrap promdance` command group — retired

Removed from §4.

> `docstrap promdance init` — creates the promdance directory structure for the current project (see §8).
> `docstrap promdance add <name>` — creates a new draft file in promdance.
> `docstrap promdance list` — lists drafts.

`init` was displaced: storage is created on demand during a markdown-layout build. `add` and `list`
were never built — creating a draft is creating a file, and listing them is `ls`. A separate
`promdance` console script carrying `backup` is what exists instead.

### 1.6 `docstrap register` offering workspace members — specified, not built

Removed from §4: "If invoked at a uv workspace root, offers to include workspace members." A
workspace-mode `.docstrap` is written by hand.

### 1.7 `docstrap doctor` as a configuration sanity check — superseded 2026-08-27

Removed from §4: "sanity checks: `.docstrap` valid, aggregate directory exists, ambiguously-scoped
top-level docs listed with cleanup suggestions."

The third clause is what shipped, by a different route: doctor answers "which documents does no
project own?" through the strapdance reader's chain, and reports the provenance of every answer. The
first two clauses — validating a `.docstrap` and checking the aggregate directory exists — were not
built and nothing replaced them.

### 1.8 "No frontmatter, no sidecars" — overtaken 2026-08-26

Removed from §5: "No frontmatter, no sidecars — content files are pure content."

Half of it holds and is stated in the live §5: docstrap still never writes to a source document. But
front-matter is now *read*. The strapdance standard (`985d7d8`) lets a document declare its kind,
status, project and relations under a `strapdance:` namespace, and doctor's verdicts come from that
chain. Absence remains a valid state, so no document has to be touched to participate.

## 2 From the implementation plan

### 2.1 The four-alpha phasing, with sanity gates and estimates

The plan's entire §1–§4 was a forward schedule: four alphas, each with a deliverables list, a
concrete sanity gate and a day estimate. All four are behind the code — Alpha 4 listed the doctor
command and the lifecycle skill as pending, and both shipped on 2026-08-27 — and the estimates
describe work that is done.

The phasing is not reproduced item by item here; `git show 47d7de7:docs/plans/docstrap-mvp.md` is
the record, and it is a better one than a paraphrase. Two things about it are worth keeping in
prose, because they are decisions rather than schedule.

1. **The gates were real and most of them were met.** The Alpha 2 research spike produced
   `packages/docstrap/docs/notes/sphinx-extension-research.md`, which still exists and is still
   accurate about Sphinx mechanics, though it is written in terms of the three named widgets of §1.2
   above.
2. **"Alpha N" is retired as a status.** `VERSIONING.md` §2.1, 2026-08-26: a version is `x.y.z` and
   nothing else. Alpha N may appear in prose as a historical fact — "introduced in Alpha 3" stays
   true — but it is never a status and never a version. Alpha 3 is `0.0.3`.

### 2.2 The 0.1.0 target — reversed 2026-08-26

Removed from the plan's §4 ("Version bump to `0.1.0` in `packages/docstrap/pyproject.toml`. Tag
release.") and from its §5 ("Package version tagged `0.1.0`").

The captain moved docstrap *down* to `0.0.3` (`1a7476e`), and `VERSIONING.md` §6 says why: `0.1.0`
was aspirational, written in advance of the work that would have justified it. Under §2.2 of that
policy, `0.1.0` is a deliberate statement that the tool has settled, entered on purpose rather than
reached by counting. docstrap is in the `0.0.z` era, where only `z` moves.

No release tags exist in the repository yet, so "tag release" is also unmet.

### 2.3 The `docs-site/` equivalence gate

Removed from the plan's §1 and §5: that a `.docstrap` at the workspace root should produce an
aggregate site "equivalent (or better) to the current hand-curated `docs-site/`".

It went with the external aggregate module (§1.1 above). docstrap builds its own aggregate now, and
there is nothing in the code or the tests that compares the output to `docs-site/`.

### 2.4 The skills path

Removed throughout: `packages/docstrap/skills/`. The skills ship inside the installed package, at
`packages/docstrap/src/docstrap/skills/`, because `docstrap init` copies them out of the installed
distribution rather than out of a source checkout.
