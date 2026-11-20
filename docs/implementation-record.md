# docstrap — implementation record

Reconciled against the code on `main` at commit `47d7de7` on 2026-09-01. This is the record of what
was planned for docstrap and what actually landed. It used to be a forward schedule of four numbered
phases with sanity gates and day estimates; every one of them is behind the code, so the schedule was
removed rather than annotated. `git show 47d7de7:docs/plans/docstrap-mvp.md` is the record of it —
that is the path this file had until it was renamed — and the decisions inside it that outlived the
schedule are archived at
[`docs/archive/superseded-2026-09-01.md`](archive/superseded-2026-09-01.md) §2.

**This document looks backwards. It is not a schedule and no longer proposes one.** What comes next
is [`docs/roadmap.md`](roadmap.md), which names work by what
it delivers and by the version state it would land in. The framing this file was written in — a march
of numbered phases toward a first usable release — is retired: docstrap is installed through the
stable path, dogfooded daily, and building twelve projects across three registered stores, so "the
work so far" is a delivered tool rather than a run-up to one.

Design reference: `docs/spec.md`, reconciled in the same pass. Where the two documents
disagreed, the code decided.

**A version is `x.y.z` and nothing else** — `VERSIONING.md` §2.1, 2026-08-26 — and a phase number
standing alone is not a status, a version, or a name for a body of work. Where the original schedule
is described below it is described by what it contained, not by its numbering. docstrap is at
**`0.0.3`**.

## §1 Where the work stands

Everything the original schedule planned has landed except the annotation client, and a substantial
body of work landed that it never planned. Dates and commits below are from `git log`.

### §1.1 Landed as planned

1. **Package skeleton and CLI foundation** — `packages/docstrap/` as a uv workspace member; the
   Typer CLI; the `.docstrap` parser handling both workspace and standalone modes; layout dispatch
   with `markdown` and `sphinx` wired up and `mkdocs`/`quarto` stubbed to a clear not-implemented
   error; the bundled MyST+Sphinx `conf.py`; `sphinxcontrib-mermaid`; static serving.
   (`35062e6`, 2026-08-25.)
2. **Metadata and annotations stores, and the app-server API** — two SQLite files, not two tables in
   one; `/api/documents/<id>` and `/api/documents/<id>/state`; the W3C Web Annotation Protocol
   subset; `docstrap status` and `docstrap tag` writing directly to the DB with no server required.
3. **Promdance storage** — per-project storage under the promdance root, the project-side symlink,
   and `gitignore-check`.
4. **The Sphinx-extension research spike** — `packages/docstrap/docs/notes/sphinx-extension-research.md`.
   It still exists and is still accurate about Sphinx mechanics, but it is written in terms of the
   three separately-named widget extensions that §1.2 below replaced.
5. **The three on-page widgets** — status badge, questions form, sentence-and-section reviewer, with
   the answer and review files they write. The behaviour survived intact through the refactor of
   §1.2; the modules, the client source and the injection mechanism did not.
6. **The authoring Claude skill**, and `docstrap init` installing skills to `~/.claude/skills/`.
7. **`docstrap doctor`** — still outstanding when the schedule was written, shipped 2026-08-27
   (`0dae407`). It is narrower than planned in one direction and wider in another: it answers "which
   documents does no project own?" through the strapdance chain, showing the provenance of every
   verdict, and it reports firstmate operational homes as an environment check. It does not validate
   `.docstrap` files or check that an aggregate directory exists, which the plan had also listed.
   `--interactive` and `--fix-plan` both exist; nothing is ever moved.
8. **The lifecycle-status Claude skill** — also outstanding when the schedule was written, shipped
   2026-08-27 (`b867d37`), with the two-gate rule intact.

### §1.2 Landed differently

1. **Vanilla JS became Svelte, and three plugins became a declaration surface.** The captain decided
   *"svelte unless it's truely tiny"* on 2026-08-27, and the tool declaration refactor landed the
   same day (`b9968ba`, then `02c0d33`). The plan had specified `docstrap.sphinx.status_widget`,
   `qa_widget` and `review_widget` as three Sphinx extensions with three hand-written JS files and a
   shared `_common.py` scaffold. What exists is `docstrap.tools.<id>/`, one directory per tool with a
   declaration in it, from which the route prefix, the launcher offer, the bundle names and the
   generated `conf.py` `extensions` list are all derived. Built bundles are committed, so installing
   needs Python only.
2. **One launcher replaced three floating buttons.** Not planned at all; it is the defect the
   refactor was for. Each widget had been injecting its own button into the same corner with no
   arbitration.
3. **The aggregate is docstrap's own.** The plan's handoff "to the external aggregate module
   (whatever exists in the current docsite implementation)" never happened. docstrap builds its own
   per-store and super-aggregate index pages with the projects' own theme, and Pagefind indexes the
   result. The gate that a `.docstrap` at the workspace root should produce a site "equivalent (or
   better) to the current hand-curated `docs-site/`" went with it; nothing in the code or the tests
   compares the two.
4. **The promdance CLI group became a separate console script.** `docstrap promdance init` is not a
   command — storage is created on demand during a markdown-layout build. `add` and `list` were
   never built. `promdance backup` exists instead, and operates across the whole project space rather
   than within one `.docstrap`.
5. **Skills ship inside the package**, at `src/docstrap/skills/`, not at `packages/docstrap/skills/`
   as every mention in the original plan had it. The installer copies them out of the installed
   distribution.
6. **The version went down, not up.** The plan's last deliverable was a bump to `0.1.0` and a
   release tag. The captain set docstrap to `0.0.3` instead (`1a7476e`, 2026-08-26) and wrote
   `VERSIONING.md` to say why: `0.1.0` was aspirational, written ahead of the work that would have
   justified it, and entering the `0.y.z` era is a deliberate statement that the tool has settled.
   No release tags exist in the repository yet, so the tag half is also unmet.

### §1.3 Landed outside the plan

1. **`ignore: true` declarations** (`e9d14cf`, 2026-08-26) — a directory and its subtree skipped by
   every discovery scan, and **firstmate operational-home detection** (`214f817`) offering to write
   one. Runtime scans obey only the declaration; detection is a setup suggestion.
2. **Hidden directories skipped in scans** (`ff51a2f`, 2026-08-26).
3. **`promdance backup`** (`6a6ede6`, 2026-08-25) — one git repository under docstrap's data dir,
   mirroring discovered draft directories and committing only on change. No remotes, no pushes.
4. **The stable install path** (`665688f`, 2026-08-26) — `scripts/docstrap-stable.sh` and
   `docstrap --version` reporting version, executable, install kind, and for a stable install the ref
   and commit it came from.
5. **The versioning policy** (`3eb3445`, 2026-08-26) — `VERSIONING.md`: number format, the pre-1.0
   eras, tag spelling, and the version-bump commit convention.
6. **The strapdance front-matter reader** (`985d7d8`, 2026-08-26) — the shared document-context
   standard for docstrap and promdance, one reader implementation used by both runtimes, reading a
   `strapdance` namespace with a fallback chain to position and content. It never writes. Doctor's
   verdicts come from it.
7. **One owner for slugs and for promdance storage** (`edbb042`, 2026-08-27) — `docstrap.slugs` is
   the only thing in docstrap that turns text into a name, and `docstrap.paths` is the only place the
   promdance path is composed. Two of each had silently orphaned submitted answers and made
   `docstrap init` report a draft root nothing wrote to.
8. **Sphinx resolved from docstrap's own environment** (`573435b`, 2026-08-27) — invoked as
   `sys.executable -m sphinx`, so an isolated `uv tool install` and `uv run docstrap` resolve
   dependencies the same way.
9. **A project's README reaches the site** (`4d552b6`, 2026-08-28) — the markdown layout brings in
   the README a level above `docs_root` as one further document, including a `.txt` README wrapped
   verbatim in a literal block.
10. **Multi-store builds** — the user-level registry at `~/.config/docstrap/config.yaml`,
    `docstrap stores`, and `docstrap build` with no arguments meaning "every store I have
    registered", with a super-aggregate above them.
11. **Expected CLI errors handled as errors** (`47d7de7`, 2026-08-28) — an invalid `.docstrap` is
    reported as a config error naming the file and offering `ignore: true`, not as a traceback.
12. **Question extraction** (`00b58df`, 2026-09-01) — `docstrap questions [PATH]` lists the open
    questions a document or a tree poses, found by the author's own `Q1`/`Q2`/`Q3` numbering and by
    no interpretation of question marks at all. Three rules, nothing to tune, no false positives by
    construction; the accepted cost is that an unnumbered question is invisible.
    `packages/docstrap/docs/finding-questions.md` has the rules and the corpus measurement. The
    convention it reads is now recorded in `AGENTS.md`, and this document and the specification both
    carry their open items as numbered questions because of it.
13. **An answer counts when it is submitted** (2026-09-14) — the first step of
    [`docs/plans/0001-answer-loop.md`](plans/0001-answer-loop.md), closing roadmap §4.11 items 1, 2
    and 3 with one mechanism. `answers.put` now requires every caller to say whether the write is a
    draft or a submission and gives that argument no default; the instrument's autosave writes
    drafts, its new **Finish** button submits, and `answers.submitted()` is what every consumer reads.
    The specification's §8.1.3 is the rule.

    **Differing from the plan in one respect the plan did not reach:** the `submitted` field is
    tri-state rather than boolean. A row that carries no such field — every row written before this
    landed — counts as submitted, because storing an answer *was* finishing it under the rule those
    rows were written under. The alternative would have retroactively turned ten real platform
    decisions in `~/dkp/promdance/answers.md` into drafts, two of which nothing has acted on yet. An
    absent field is never written back either, so those rows survive a rewrite of the file byte for
    byte; that was verified against the real store, read-only, before the step was called done.
14. **A submitted answer may be revised** (2026-09-14) — the plan's step 2, closing roadmap §4.11
    item 3. A later answer supersedes rather than being rejected, and the answer it displaces is kept
    in a second promdance file, `answers-history.md`, so the earlier decision is recoverable rather
    than lost. Specification §8.1.4.

    **Two things the plan did not reach.** It asked for one definition of what makes a question still
    open, and the honest default it named — open until the work it gates is closed — is not something
    docstrap can observe: it sees documents, not the work a decision feeds. So docstrap never refuses
    a revision, and what makes that safe is the record rather than a gate.

    And step 1 had introduced a defect that only revision exposes: a draft written into the answer's
    own text would erase the standing decision from every consumer for as long as its author spent
    retyping it. A draft therefore lives in its own field beside the submitted answer, not on top of
    it. That is why `Answer.text` now means the submitted prose specifically, and `editable_text` is
    what goes back in front of whoever is answering.
15. **The panel is scoped deliberately** (2026-09-14) — the plan's step 3, closing roadmap §4.11
    item 5. The qapanels collection is readable project-wide and narrowed to one document, and the
    instrument's header is where the reader says which; it defaults to the document it was opened on.
    Specification §7.6(1).

    **Wider than the plan described, in one place.** The plan read the shape off `routes.py`'s own
    header and expected the second route to be mounted there. Mounting it there would have put a path
    in the server's table that no declaration derived, which is exactly what
    `test_server_route_table_equals_what_the_declarations_derive` exists to catch — so the second
    scope became a declaration field, `also_scoped_to`, and `route_prefixes` became the tuple that
    test compares against. The launcher resolves both into the page (`route` and `altRoute`), so
    choosing a scope in the browser is still choosing between two URLs the declaration produced.
16. **Answers are readable over the API** (2026-09-14) — the plan's step 4, closing the API half of
    roadmap §4.11 item 4. `/api/answers/<project>` and `/api/answers/<project>/<doc-slug>` return a
    project's questions paired with the answers they have, with `?include=all|answered|open`.
    Specification §8.2.

    **One thing the plan named and one it did not.** It named the endpoint. What it did not say is
    where the pairing would live: `docstrap.questions` reads `Q<n>` labels and knows nothing of
    answers, `docstrap.answers` is emphatic that it is not an index of questions, and the qapanels
    route had quietly become the only place the two were matched up. Putting a second matcher in the
    server would have been the defect the single-owner rules exist to prevent, so the pairing moved
    out into `docstrap.pairing` and both surfaces now project it — the instrument for editing, the API for
    reading. The difference between those projections is load-bearing: the editing one hands a writer
    their unsubmitted draft back, and the reading one shows no draft at all.

    The API is the **server's** rather than a tool's, alongside metadata and annotations, so a
    consumer of decisions need not know which tool happens to exist. It is read-only; writing stays
    where a person is answering.
17. **The answer is rendered beneath the question** (2026-09-14) — the plan's step 5, closing the
    reading half of roadmap §4.11 item 4 and with it the whole of that item. A new tool, `answered`:
    the build marks each `Q<n>` block in the rendered doctree, and the client hangs that question's
    current answer off the mark, reading `/api/answers` live. Specification §7.7.

    **The choice the plan left open was build *or* serve time, and it is both.** Marking is a build
    step because finding a question in rendered HTML from the browser would be DOM scraping against a
    rule `docstrap.questions` already owns; resolving is a serve step because answers change
    constantly and a document does not rebuild when they do, and a stale decision shown as current is
    worse in a decision system than no decision shown. The consequence is accepted and stated in the
    spec: a page served with no docstrap behind it is the document its author wrote, unmarked.

    `docstrap.questions` grew one public function, `label_of`, so the marker asks the owner of the
    label rule rather than carrying a second copy of it. Rules 2 and 3 come from `find` on the source,
    so a superseded earlier run, a quoted label and a fenced one are left alone exactly as
    `docstrap questions` leaves them.

    **Verified short of the browser.** A real `sphinx-build` proves the marks, which labels get one
    and which do not, and that the source file is byte-identical afterwards; a real `docstrap serve`
    proves the page ships the marks and the bundle, and that the API returns this document's pair.
    The note appearing under each question in a browser was **not** confirmed: neither browser bridge
    was reachable in the environment this landed in, and both bundled Chrome binaries were missing
    system libraries. §7 of `docs/tools-and-instruments.md` records it as outstanding.
18. **The loop delivers an artifact** (2026-09-14) — the plan's step 6, closing roadmap §4.11 item 6
    and with it the last of the six findings. Submitting an answer writes
    `<doc-slug>__answers.md` beside the document in promdance: a stable path a citation keeps
    resolving to, every question the document poses with its answer or its open marker, and an
    `answered_version` digest in the front-matter. Specification §8.3.

    **The version is the part the plan named least precisely and that mattered most.** "A version of
    the document recording that it was answered" could have meant a versioned copy of the document or
    a new column in the metadata database; it is neither. It is a digest of the answered *state*,
    recorded beside the document — over which questions have answers and what those answers say, and
    over nothing else. dkp's contract stamp needs it to move when a decision moves and at no other
    time, and that is the property it has.

    **A real run found a defect the tests had not.** The digest originally included each answer's
    submission time, so pressing Finish twice on unedited text moved the version — a consumer would
    have re-stamped a contract because someone clicked again. The store already treated that as a
    non-event, superseding nothing; the version now agrees with the store. The test that pins it was
    written after the run, not before, and says so.

    Delivery is deliberately **not** part of the answer's success: the answer is already stored by the
    time delivery runs, so a failed delivery reports an absent artifact rather than a failed write.
    Reporting failure there would invite a retry of a write that succeeded, which against a
    superseding store means a second history entry for one decision.

19. **A build stopped writing into project trees** (2026-09-17) — the markdown layout composed its
    section pages by walking a scratch tree of symlinks with `followlinks=True`, so the writes went
    through the links and landed in the repositories being built: fifty-five tracked `index.md` files
    across `platformshoes`, `rlp`, `trk_tdp`, `dkp` and `formizer`. Specification §7.8 states the
    invariant this violated, and §0 now carries it alongside the two properties it belongs with.

    **The fix is a mirrored scratch tree rather than a rule about where not to write.** Directories
    in the build are made by the build; only leaf files are symlinks, so there is no symlinked
    directory left for a composed page to be written through. The walk additionally does not follow
    links, and every generated write goes through a guard that resolves its destination and refuses
    anything outside the build — three mechanisms where one would do, because the structural one can
    be broken by a later change without anyone noticing and the guard cannot.

    `_ensure_docs_dir_exists` went with it. It created a project's `docs_root` when it was missing
    and left a placeholder document there; a missing directory is now reported on the landing page
    and in the build's notes, and nothing is created.

    Two things **differed from the brief**. The brief asked for section pages composed on the fly or
    held as managed documents in docstrap's own stores; the mirror is the first of those and it
    turned out to be a smaller change than either sounded, because the pages were already being
    composed correctly — only the destination was wrong. And promdance is mirrored the same way
    rather than mounted as one symlink, which the brief did not ask for: storage is docstrap's own,
    but a page composed into it persists, is read back as a landing page the next build must not
    overwrite, and goes stale there exactly as `rlp/docs/specs/index.md` did in a project.

    **A finding, from building the real workspace to check.** Six projects built and not one tracked
    file moved — but the build did leave three `promdance` symlinks showing as untracked in
    `git status`, because `platformshoes`' own `.gitignore` names neither `promdance/` nor
    `docstrap-build/`. `docstrap gitignore-check` requires both; it is a command somebody runs, and
    on this repository nobody has. The link is a symlink to a user-specific absolute path rather
    than a generated document, so it is a much smaller problem than the `index.md` files and it is
    not what this work was about — but "a build never writes into a project tree" would have been
    slightly untrue as stated, and §7.8.2 now states the gap instead of assuming it away. A test
    fingerprints a project tree before and after a build and holds the exception to that one entry.

    **`docstrap generated-indexes`** came with it: the same walk, reporting instead of writing, so
    the per-repository cleanups have something deterministic to drive from (§7.8.4, roadmap §4.12).
    It claims a file only when the file is byte-identical to what a build composes now. That is
    strict on purpose and strict in the safe direction — `rlp/docs/specs/index.md` is docstrap's own
    stale output and still comes back unclaimed — because the previous attempt to separate generated
    from authored read their prose and classified them wrongly.

    **One consequence worth knowing.** A composed section page's `docstrap-source-path` meta tag now
    points into the build rather than at a file in the project, because the page no longer has a file
    in the project. Real documents are unaffected: they are symlinks and resolve to their source as
    before. A page docstrap composed is not a document anyone authored, so a derivative aimed at one
    lands in the build area and does not survive a rebuild — which is the correct place for it and a
    change from landing in somebody's repository.

20. **The store became a git repository with a remote, and the backup that guards it started
    working** (2026-09-17) — spec §8.4, §8.5, §8.6, §8.7. Four things landed together because they
    are one dependency chain.

    **`promdance backup` had never once completed.** It aborted at its default root on a duplicate
    slug before copying anything, so the 93 draft files it was the safety net for had no safety net.
    The duplicate was not two projects: it was `apps/gsheets-pub` seen through `~/trk_tdp` and again
    through a linked worktree at `~/wt/trk_tdp/id-cohorts`, both symlinking one store entry.
    Identity is now a canonical directory — `projectfinder.canonical_dir` resolves a path through
    `git rev-parse --git-common-dir` to its position in the main working tree — and sources merge on
    the directory the drafts live in, so two paths onto one directory are one source. Two genuinely
    different directories on one destination is still an error.

    Three store entries were also backed up by nothing: `docs` and `winrun`, because discovery
    dropped `kind == "related"`, and `rl_deployment`, a uv workspace member that is not a git
    repository and that no project-space walk could find — it held six real drafts. The fix is
    general rather than three patches: discovery is now the **union** of project space and the store
    itself, so anything in the store is backed up whether or not something claims it.

    Destinations are now unique by construction too, in two namespaces — `store/<entry>` and
    `projects/<canonical path>`. That came from running it: `~/rlp` is half-interned, and its real
    promdance directory and the empty store entry `ronin-ledger-panels` collided on one slug and
    aborted the run a second time. A safety net that can refuse to run is the defect, so the
    destination is derived from a filesystem path, which two directories cannot share.

    **The store is a git repository.** `docstrap.storegit` initialises it, configures its remote,
    commits and pushes. Initialising adds `.git/` and writes no file in among the drafts. Committing
    and pushing is both a command and a hook on `backup`, and §8.4.4 says why both.

    **And docstrap creates no repository** — the captain simplified that away the same day, after
    asking what comparable tools actually do. The user creates the repository under their own
    account, on the service they chose, hands docstrap the URL and the keys, and *that* is the
    explicit choice; an agreement to sign would be, in his word, "overt". So the earlier plan to
    create `esotericbyte/promdance-xomcomen` with `gh-axi` was withdrawn before it ran, and
    `promdance-<machine>` — still derived from the host through `docstrap.slugs`, so this
    workstation produces `promdance-xomcomen` rather than that being a constant — became a
    *suggestion* the command offers rather than a name it imposes.

    The check he asked for first found chezmoi doing the identical thing: user content relocated
    into `~/.local/share/chezmoi` and reached by indirection, with a diff and a dry run instead of a
    consent step. Nothing heavier exists to copy. **The result is that this branch has no
    outward-facing step at all** — no API client, no token, no CLI to shell out to, and nothing that
    reaches a hosting service on its own initiative.

    **Interning is reachable.** `ensure_promdance`, `gitignore.check`, `gitignore.fix` and
    `find_gitignores_missing_promdance` all already existed and no command could call any of them,
    which is why the captain had to add a `promdance` line to `rlp`'s `.gitignore` by hand. His
    correction — *"that 'fix' should have been unecessary"* — is the whole diagnosis. `promdance
    intern` now does the wiring, and `gitignore.check` reads his hand-written `promdance` as
    satisfying `promdance/`, so a repair does not append a second rule underneath somebody's.

    **What deliberately did not land.** Interning a project that already holds a real `promdance/`
    directory would have to *move* content out of that repository, and `intern` never moves a file:
    it reports such a project and leaves it exactly as found (§8.6). That is ordinary unbuilt work
    rather than a gate — roadmap §4.15 — and the shape it should take when built is chezmoi's, show
    before move. Item five of the captain's note, archiving a promoted prompt off a strapdance header
    change, has a named place at §8.8 and nothing in it, at his direction.

    **One shape chosen for later.** GitHub is one provider among several intended, so nothing above
    `docstrap.forge` knows a provider exists. With creation gone, that boundary is two textual
    methods — the URL a name would have, and whether two URLs are one repository — and a second
    implementation ships with it: plain git, for a host docstrap knows nothing about, which is what a
    user choosing their own service actually needs. A test fingerprints the boundary so a leak fails
    the suite. The `pluggy` plugin system itself is named in §8.7 and not built.

21. **An index became transient, transparent and HTML-only** (2026-09-17) — the captain read item 19
    above and went further the same night: *"no the generated indexs should be transient and
    transparent... the index shoud be only in html not in md files."* Item 19 moved the section pages
    from the project into the build; this removes them as files altogether. Specification §7.8 is the
    account and §5.2 is the table.

    **It superseded item 19 without contradicting it.** Composing into the build was right as far as
    it went, and the part of it that holds — the mirrored scratch tree, the guard on every generated
    write, promdance mirrored rather than mounted — is unchanged. What changed is that the composed
    page is no longer a *file*.

    **The hard part was named before it was solved, and the answer is a marker.** Sphinx's `toctree`
    is a markdown construct and section pages existed as markdown because that is how furo's sidebar
    gets built. `Builder.read_doc` is `@final` and reads its source from disk, so there is no
    supported way to hand Sphinx a document that is not on disk — but `source_suffix` and
    `app.add_source_parser` are supported, and a parser may compose whatever it likes. A section page
    is now a zero-byte `index.docstrap-section` in the build's scratch tree whose parser builds the
    document from `sectionindex.compose` as docutils nodes. Zero warnings, full sidebar, same theme.

    **What it cost, stated rather than approximated**, because the captain asked to be told. One
    empty file per section exists inside the build. Reaching literal zero needs private Sphinx state
    — `env._pickled_doctree_cache`, a `Project` subclass rewriting the docname-to-path bijection, or
    a `Path` subclass whose `read_text` lies — which for an integrator means a tool that breaks on a
    point release. `html_additional_pages` is public and does give zero files, but such a page is in
    no toctree, so the sidebar loses its structure: that is losing the navigation, which was not on
    offer. §7.8.2 lists all four rejections.

    **Two things differed from the brief.** The brief's fallback allowed markdown inside docstrap's
    own area if the engine required it; it did not, so the fallback was not taken. And the aggregate
    pages of §2 were not in the brief at all — they are indexes too, they were the second markdown
    file a build wrote, and they went the same way, with their model travelling in the generated
    `conf.py` because what they list is knowledge only the run that performed the builds has.

    **The table is its own, in the same database.** `content_observations` was the obvious candidate
    and is wrong three times over (§5.2.1); a separate database file would push the rename join into
    Python for no gain (§5.2.2). Adding a *table* is also the one schema change that is safe while
    §4.18's upgrade path does not exist, because `CREATE TABLE IF NOT EXISTS` reaches databases that
    already exist and an added column does not. That asymmetry is now in `metadata.py`'s docstring.

    **The cost argument was checked rather than taken on faith**, since it is the captain's licence
    for having no cache. Indexing 5 000 documents across 50 projects: 0.65 s. Composing all 450
    section pages from the table: 0.27 s. Indexing one 100-document project: 0.01 s, against 3.06 s
    for the sphinx-build that publishes it — 0.4%. He is right. Two hot spots turned up while
    measuring and both were fixed rather than tolerated: `strapdance.read_context` reloads the
    enclosing `.docstrap` per document at 1.7 ms, so `strapdance.read_title` runs the title chain and
    stops; and a per-file `get_document_by_path` opened a connection each time at 222 µs, so
    `metadata.ids_by_path` answers in one query.

    **`generated_indexes` kept working by being frozen.** It recognised committed files by comparing
    them against the live composer, and the live composer now emits no bytes. Its recogniser is a
    deliberate copy describing what builds up to 0.0.3 wrote — finished, shared with nothing, correct
    forever because the thing it describes will never change again (§7.8.4).

    **One consequence worth knowing, measured on docstrap's own docs.** A project's `index.md` used
    to be *copied* into a generated landing page, so its relative links resolved inside the build. It
    is now a symlink like every other document, and MyST resolves a relative link through the link
    into the project, which is not in the build — so it emits `myst.xref_missing`. Every link still
    renders correctly and every target exists; the warning is cosmetic. But it is ten more of them on
    this project's landing page, joining the eighteen the other documents already produced from
    exactly the same cause. The landing page stopped being the anomaly rather than becoming one, and
    the underlying warning predates all of this work.

    **Seventeen files went from this repository**, driven from the report and confirmed by reading
    each one before deleting it. Roadmap §4.12 has what that pass established for the four
    repositories still to do.

22. **A document's identity reaches the server intact** (2026-09-23) — every document-targeted tool
    route was unreachable on every document below a project's `docs_root`, and said so as
    `is docstrap serve running?` while the server was running. `projectscope.document_slug`
    deliberately makes a document's identity its path below `docs_root` with the suffix dropped,
    `proposals/0002-the-upgrade-path`; the routes spelled that identity as one path segment, the
    launcher percent-encoded the separator into `%2F`, nothing matched, and the browser got a 404.
    Across the captain's six built projects, 666 of 686 published pages are nested. Only
    `packages__docstrap` — the project the instrument was developed against — keeps most of its
    documents at the root, which is why it looked like it worked.

    **The identity was not flattened.** The obvious repair was to put `document_slug` through
    `docstrap.slugs.slugify`, making it one segment and leaving every route untouched; the captain
    declined it, because a document management tool handles paths. So the route carries a path. The
    declaration keeps its own spelling, which is what the launcher fills in for the browser, and
    `declaration.as_server_path` marks the one parameter that spans separators for the router. The
    launcher quotes a document slug with `/` safe and a project slug with nothing safe, which is the
    difference between an identity that is a path and one that is a segment.

    **The collision that reopened was closed deliberately, not argued away.**
    `tools/qapanels/routes.py` had recorded at length that a greedy `{doc_slug}` makes
    `…/{project}/qa` and `…/{project}/{doc_slug}/qa` mutually capturable. They stay apart because a
    project URL has exactly one segment after the project and a document URL has two or more — and
    that holds only while no route reaches deeper than a base plus one static collection.
    `declaration.check_route_separation` enforces exactly that over every path a tool returns, and
    `mounting.mount_all` calls it, so a tool that declared its way into the ambiguity fails at
    startup rather than silently answering for another tool's endpoint.

    **Four routes were broken, not one.** The panels' document read and the server's
    `/api/answers/{project}/{doc}` were 404; the qa tool's write and the review tool's write were
    405. The `answered` tool's read fires on every page load with nothing launched, so a nested
    document silently showed no answers under any question — the store was fine and nobody could see
    it. All four now answer; addendum and review FILENAMES are still flattened through the one
    slugifier, because a filename is one segment and an identity is not.

    **Why nothing caught it.** `test_tool_declarations.py` compared the server's route table against
    the templates the declarations derive — template against template, never filled in — and both
    browser runs in `docs/tools-and-instruments.md` §7 used flat sample projects.
    `tests/test_nested_document_routes.py` fills the templates in with a real document two levels
    down and drives the real router; `tests/test_rendered_page.py` now builds a nested page and
    asserts on the offer payload in its head. Removing either half of the fix fails them.

    **Two further findings from the same report landed with it.** A store's landing page carried
    `docstrap-project="fleet-queue"`, slugified from the heading "Fleet queue" — a name addressing
    no store, no directory and no promdance entry, which 404ed when anything was launched there. An
    aggregate belongs to no project; it is now given none, and the launcher already knew to offer
    nothing where there is no workpiece. The title fallback stays for a site built on somebody's own
    `conf.py`, which does have a project docstrap never scanned. And the client's
    `is docstrap serve running?` had grown into four surfaces and was right in one of them;
    `describeApiFailure` now says it only when the call produced no response at all, and a test
    holds it to the single place.

23. **A docs tree holds no index file at all** (2026-09-30) — the captain looked at what was still
    committed thirteen days after item 21 and closed the exception item 21 had left standing:
    *"index files in docs are not allowed and shoudl be removed. that is the defect... that whole
    index file polution of the doucment directories was a horrrible idea"*, and then *"do strap must
    create them ephmerally. as part of it's build in it's own directories. you can clean those all
    up. no index.md in docs/ trees. At all. period."* Specification §7.8.6 is the rule.

    **The unimplemented part of item 21 was the third sentence of the original instruction.** *"any
    index.md files should be purged"* — item 21 stopped the writing and purged the seventeen files
    docstrap claimed, and left every file it did not claim where it was, under a rule that a
    directory holding an `index.md` has a landing page of its own. So the instruction was two thirds
    done and read as finished.

    **Three code changes, and the third is the one with teeth.** The "user wrote their own index"
    check is gone from `_write_section_markers` and from the project root, so every directory gets
    the page docstrap composes. `composed._extend_root` and its `doctree-read` hook went with the
    case they existed for rather than being left to guard a state that cannot arise. And
    `_mirror_tree` does not link an index file into the build at all, which is what stops one in a
    tree shadowing the composed page at the same docname — without it, `source_suffix` order decides
    which of two files claims `index`, and `.md` wins.

    **Nine more files went from this repository**, listed in the branch's report: seven one-line
    "Docs directory placeholder" files under `apps/` and `packages/`, docstrap's own hand-written
    `docs/index.md`, and the `docs/notes/index.md` that item 21's pass had correctly declined to
    claim. That last one had already done the harm the rule exists to prevent: it listed two of the
    three documents beside it, so the third was in no toctree and off the site. A composed page is
    read from `file_index`, so there is no hand-kept list to fall behind.

    **A refused file is named rather than ignored.** On the project's landing page through the same
    `docstrap_root_note` that reports a missing `docs_root`, and in the build result's notes. The
    original writes were never announced anywhere, which is why the first notice of them was a dirty
    `git status` in somebody else's repository — the reporting is the part that stops a third
    recurrence being discovered the same way.

    **And the rule got an executable form.** `scripts/check-no-index-md.py` fails if an index file is
    committed into a documentation tree, reads declared `docs_root` entries as well as directories
    named `docs`, and is self-contained so the four repositories still carrying the pollution can run
    it as-is. `tests/test_no_index_md_in_docs_trees.py` holds both ends: no build writes one, and
    none is committed.

    **One thing was deliberately not extended, and it was ruled rather than assumed.** `docs-site/`
    is a hand-maintained Sphinx source root whose `index.md` is its `master_doc` and whose four
    section pages are its whole navigation; it is a site's assembly point rather than a document
    directory, and docstrap does not build it. Deleting its five files would have satisfied the
    letter of a rule written about generated ones and broken `sphinx-build docs-site` and
    `scripts/build-docs.sh` with no replacement in hand. They are kept, reported by the check without
    failing it, and the check's own output carries the reason — a master document against a generated
    index in a document directory — so the exemption cannot be removed by somebody reading a bare
    count. Spec §7.8.6's last two paragraphs and spec Q10. The captain's wording is absolute and this
    is the one place it can be read either way, which is why it is written down where it can be
    overturned on purpose.

    **Item 21's last finding is now moot.** The ten `myst.xref_missing` warnings it measured came
    from a project's `index.md` being symlinked rather than copied, so its relative links resolved
    through the link into a project outside the build. Nothing reads such a file now, so the warnings
    are gone with it — and so is the small cost item 21 recorded.

24. **The viewer shell** (2026-10-04) — `docs/proposals/0004-the-viewer-shell.md`, approved and built
    the same day. One Svelte application on a page of its own, `viewer.html` at a built site's root:
    a navigator listing every project and document the build published, with the pinned questions
    document above it; the selected page in a frame in the middle; and the qapanels instrument's
    three panels in a right drawer whose state does not follow the middle region. Skeleton,
    Tailwind and Lucide arrived with it, as development dependencies of the shell's build only.

    **What the navigator reads is a manifest the build writes**, `_viewer/manifest.json`, composed by
    `docstrap.viewer.manifest` from the file index and from `launcher.offer_payload` called with each
    document's own page context — so the question routes the drawer uses are the ones the page
    carries, and `tests/test_viewer.py` compares them page by page. It is not a tool and has no
    declaration: that would have put Skeleton on every documentation page.

    **It landed differently in four places, each found by looking at it in a browser.** The missing
    scroll bar the captain reported was not the layout: remembered visibility is shared with framed
    pages, so the reference panel's page got the overlay's scroll lock, which is now keyed on the
    panels actually being mounted (proposal §3.2) — reproduced against `main`'s stylesheet and gone
    with the fix. Skeleton's global `label` utility landed on the hosted question list and hid every
    question's text; it is no longer generated, and a test fails if any unscoped rule in the shell's
    stylesheet names a class the hosted panels use. Skeleton's tree aligns its children to the start,
    so the tree took its widest title and the navigator scrolled sideways. And the middle region
    became a component of its own, `DocumentView.svelte`, owning the frame, its loading and its two
    failures — "docstrap answered 404" and "nothing answered", both in `describeApiFailure`'s words —
    with the question drawer likewise its own `QuestionDrawer.svelte`, so the shell root holds layout
    and state and nothing else.

    **The browser run used puppeteer-core, not `chrome-devtools-axi`.** The bridge still fails every
    page-level call with `pageId` required (§7 of `docs/tools-and-instruments.md`), and Playwright's
    Chromium still lacks `libnss3` and `libnspr4`. Those two libraries were fetched with
    `apt-get download` and unpacked into task scratch rather than installed, which was enough to run
    Chromium headless against a real multi-store build served by `docstrap serve` in a redirected
    home. What it saw is the proposal's §11.

25. **The viewer entrance** (2026-10-08) — the captain's ask: *"the front page might need to load
    inside the view itself. there should be a viewer entrance that loads the viewer with
    instructions to load the root page of the site."* The shell already read its hash as the page
    for the middle region and fell back to the root page without one, so the entrance is an address
    and not a new page: `viewer.html#index.html`, named once as `docstrap.viewer.manifest.ENTRANCE`.
    What was missing was the way in and the front page's place in the navigator. The site's root
    page — the super-aggregate, or a single-store build's landing page — now carries "Open this site
    in the viewer", linking to the entrance; a store landing page under a multi-store build does
    not, because the shell is not beside it. In the shell, the root page is a row of its own at the
    top of the navigator, selected when it is showing, except where a store's row already is that
    page. The link is hidden inside the shell's own frame, where it would nest a viewer in the
    viewer; only that link is hidden, because whether a framed page's other apparatus belongs there
    is the proposal's open Q2.

    **Checked in a browser** at 2560 × 1440 against a multi-store build of this repository's root
    store served by `docstrap serve` in a redirected home: the link on the site index opens the shell
    with `index.html` in the frame and the front-page row selected, and with the link hidden in the
    frame. A link followed inside the frame moves the selection off the row, and selecting the row
    brings the front page back. `chrome-devtools-axi` worked this time through a wrapper, kept in
    task scratch, that starts `chrome-devtools-mcp` with `--no-page-id-routing` and points it at
    Playwright's Chromium with the same two scratch-unpacked libraries.

26. **Promdance reports where its directories belong** (2026-10-10) — spec §4.3, §8.9. The captain's
    ask: *"The promdance project needs commands like scan and status docstrap has"*, with the rule
    that a promdance directory belongs at repository roots and at every uv workspace app or package
    with a docs folder. `docstrap.placement` owns that rule; `promdance scan` lists the places and how
    each is wired, `promdance status` now covers them rather than only declared projects, and
    `promdance backup` reads the members the rule adds. The projects root is a user-config setting,
    `promdance_projects_root`, defaulting to the home directory so nothing changed on the day.

    **The backup abort was already gone.** The queued item said `promdance backup` still aborted at
    its default root on a worktree's duplicate slug; item 20 had fixed that on 2026-09-17, and a
    read-only discovery at the real `$HOME` merged all 35 sources without a collision. What landed
    here is a test of it at the *default* root, which no test had held — the default had been read
    from the real home at import time, so a test could not exercise it without scanning the real one.

    **What running it found.** On the workstation it lists 42 places — 16 linked into the store, 4
    real directories, 22 absent — and `status` showed two things nobody had seen. Two member symlinks,
    `trk_tdp/apps/gsheets-pub/promdance` and `platformshoes/packages/docstrap/promdance`, are
    *committed* to git, so no ignore line can help them. And `promdance/`, the line `intern` writes,
    never matches the symlink `intern` places: git sees a symlink as a file. `status` asks git rather
    than reading `.gitignore`, so it reports both; `intern` is unchanged.

27. **A page opens itself in the viewer** (2026-10-12) — `docs/tools-and-instruments.md` §3.2. The
    captain's ask: a button on each published page that loads the viewer in its place, so the shell
    does not auto-load, suppressed by state inside the viewer, injected by the Sphinx build — and
    carrying the page in its most basic form, `?doc-url=<encoded url>`. A page opened directly now
    runs one dependency-free script and fetches no Svelte runtime: every tool script is on the page
    with a type no browser runs, and the button's script turns them on only inside a frame. That
    also retires the empty three-panel overlay a page opened directly could come up in, since the
    instrument no longer runs there. The shell reads `?doc-url=` (through `ui/queryParam.svelte.ts`,
    a `createSubscriber` over `popstate` and `hashchange`), follows it when it changes, writes it as
    its own record, and still accepts the older `#page`; the entrance became
    `viewer.html?doc-url=index.html`.

    **Landed differently from the brief in one respect: the address is built, not found.** The
    button's URL is composed in Python from the manifest's own `page_url`, which needed the build to
    say where each Sphinx run's output sits below the site root — `docstrap_viewer_base`, threaded
    from `build_all` through `build_project`. Stylesheets are not held back (the qa gate is CSS), and
    no server handler was added: the shell reads `?doc-url=` itself, so the site still works served
    as plain files.

    **Checked in a browser**, puppeteer-core and headless Chrome with the two scratch-unpacked
    libraries of item 24, against a multi-store sample build served as static files: the direct page
    fetched only the button script and drew the button; pressing it opened the shell on that page,
    whose frame was marked `framed`, drew no button, and fetched and ran all seven held scripts with
    the launcher showing; a hash typed into the open shell, history back, and a `popstate` onto a new
    `?doc-url=` each moved the middle region; an off-site `doc-url` fell back to the root page.

28. **Data tables** (2026-10-13) — `docs/datatable.md`. The captain's ask: *"Give me some active
    filterable and sortable tables for the open tasks in the docstrap summary page"*, for firstmate's
    task census, built as a generic tool rather than a census one. `docstrap.tools.datatable` provides
    the `docstrap-datatable` directive naming a JSON file of columns and rows beside the page. The
    build renders the plain table, which is the document, and embeds the data the tool draws the
    sortable, filterable table from inside the viewer. Link targets naming documents are resolved by
    the build, so a generator writes `tasks/<id>` and never a site URL.

    **Landed with a TypeScript test runner.** The sort and filter rules are a DOM-free module tested
    under Node's own runner with type stripping — no new dependency — via `npm test`, and
    `tests/test_datatable.py` runs the same suite so `pytest` covers it. Cell text is the one rule
    written in both languages, and a shared fixture holds the two to one answer. A `sort` key in the
    table file was considered and left out: the file's row order is the default order, so ordering
    has one owner. Checked in a browser; `docs/tools-and-instruments.md` §7 has the run.

29. **The task tool** (2026-10-13) — `docs/tasks.md`. The captain's ask, answering a question about
    a dedicated tool instead of a general table: *"yes and it should be able to categorize by project
    or by status and drill down to just part of the list"*, and *"latest recommendation"*, with the
    standing direction that the primary organisation is the project. `docstrap.tools.tasks` provides
    the `docstrap-tasks` directive over the `tasks.json` firstmate writes beside the page, which it
    only reads, ignoring keys it does not know as the contract requires. The list groups by project
    and unit or by state or stuck, drills into a group with a breadcrumb back, and keeps the grouping
    and drill-down in the viewer's address beside `?doc-url=`. Sorting and filtering are the data
    table's own module, made generic over the row type rather than copied; the build's link
    resolution is likewise shared, moved to `datatable.views.resolve_target`.

    **A decision is an answer.** One per task, keyed `<doc-id>:task/<task-id>` on the page holding the
    directive, written submitted through `docstrap.answers`, so superseding and history are the
    store's own. The tool's `decisions` collection reads and writes them; there is no bulk write. The
    "answers done" notice is the existing prompt, whose route the tool is handed, not a second one.
    Saving a decision delivers no addendum, because the addendum is what a document's questions
    decided. The grouping, drill-down and address rules are a DOM-free module tested under Node and
    reached from `pytest`. Checked in a browser; `docs/tools-and-instruments.md` §7 has the run.

30. **Both tables on TanStack Table, and a task list laid out within the page** (2026-10-14) —
    `docs/tasks.md` §4.4 and §4.5. The captain, on the task list: *"the "task" column is what is
    throwing off the layout. it's too wide relative to the others. Also the table should have a
    contaning div or component that has a max height"*, having declined to widen the page past the
    theme's text width, and asking why a hand-rolled table had been built rather than TanStack's.
    The page the captain had been reading was the census opened on its own, which runs no tool, so
    what was seen was the plain table; inside the viewer the tool was mounting.

    **Sorting, filtering, the search, facet counts, grouping, collapsing and column sizes are now
    TanStack Table's** (`@tanstack/svelte-table` 9.3, Svelte 5), for the data table and the task list
    alike. `datatable/ui/grid.ts` is the one place a docstrap column becomes a TanStack column and the
    search becomes TanStack's global filter over a hidden column, so every term is matched across the
    row as before; `datatable/ui/table.ts` keeps only what a column and a cell are and how two cells
    compare, and the hand-written sort, filter and facet functions are gone. `FilterBar.svelte` is the
    one filter bar both tools draw, reading and writing the table's own state. TanStack is headless,
    so tools keep Svelte's scoped styles and Skeleton stays out of them. TanStack groups in the order a
    group first appears, so the task list hands it the tasks already in group order. The tool build
    now defines `process.env.NODE_ENV`, which TanStack reads and a library build leaves in place. Each
    bundle carries its own TanStack, about 35 kB gzipped between the two
    (`docs/tools-and-instruments.md` §5.1).

    **The task list keeps the theme's width.** Every column has a fixed width (`tasks.ts` `SIZES`),
    the task column 150 px with the id cut short and whole on hover; the table sits in its own box,
    at most 85% of the window high, scrolling both ways with a sticky header row and a sticky task
    column. The Unit column is dropped under project grouping, where units are already the headings.
    The plain table is laid out by the same stylesheet and widths. The directive's output changed, so its Sphinx `env_version` was
    bumped to make existing builds render it again. Checked in a browser against firstmate's 117-task
    census, through the viewer and opened directly.

31. **One settings surface: sources with roles and mounts, and a `plugins` block** (2026-10-30) —
    stage 1 of `docs/plans/0002-promdance-separation-and-source-settings.md`, §5 and §8.1.
    `docstrap.settings` resolves `sources` and `plugins` across the user config, the top of a
    `.docstrap` and one entry in it, and is the one writer of both files, through ruamel.yaml's
    round-trip mode (a new dependency). A source is a `path`, a `role` and an optional `mount`; the
    first mounts at the project root and the rest at their own path, so every existing document
    identity is unchanged. `docs_root` is shorthand for one `documentation` source, and `config.py`,
    `cli.register` and `doctor` no longer default a folder name. The build mirrors each source at its
    mount, stores its role in `file_index.grouping` with no column added (`docs`/`drafts` rows became
    `documentation`/`draft`), and groups the landing page by role; a `draft` source is not walked by
    `ProjectScope.documents`. Promdance reads `plugins.promdance.enabled` and `projects_root`; its
    draft area is mirrored as one more source, role `draft`, mount `promdance`.

    **Landed differently in one respect: the compatibility rule.** A user config that states neither
    `sources` nor `plugins` — or no user config at all — has not migrated, and is read exactly as
    before: the `docs` default, the old `promdance:` keys where they stand, promdance on when nothing
    says. Building this repository's `.docstrap` with the code before and after the change, in an
    isolated home, gave byte-identical HTML and identical index rows apart from the role values.
    Once the user config carries the new shape, an old-shape key anywhere is a load error naming
    `docstrap config migrate`, which is a dry run printing the diff unless given `--apply`.
    `plugins.promdance.members` is written by migrate but not yet read; placement still applies its
    built-in member rule, which the value states.

32. **The plugin seam, with promdance as an internal plugin** (2026-10-31) — stage 2 of
    `docs/plans/0002-promdance-separation-and-source-settings.md`, §4. `docstrap.plugins` declares
    the six hooks on pluggy (now a direct dependency) and owns one `PluginManager`, which loads the
    `docstrap.plugins` entry-point group and calls each per-project hook through
    `subset_hook_caller` with the plugins the settings do not enable left out.
    `promdance_plugin.py` implements all six: the build's `ensure_promdance` call, the choice of
    what to mirror under the `promdance` mount, the draft root that `tools/derivatives.py` was (now
    deleted), the `.gitignore` line, the store path `docstrap init` created, and doctor's
    shared-entry survey. The store path helpers moved from `paths.py` to `promdance_paths.py`.
    `docstrap.drafts.draft_root` asks the hook first, then the project's declared `draft` source if
    that folder exists, and otherwise there is none and a writer refuses. `sphinx/answer_drafts.py`
    replaces `promdance_answers.py` and reads the draft source's mount from the generated `conf.py`.
    The tool route base is `/api/tools/...`. A test fences every module outside the promdance files
    from importing one or naming promdance in code.

    **Landed differently in five respects.** First, promdance is registered "internally" by an
    entry point in docstrap's own `pyproject.toml`, not by a `register` call, so `docstrap.plugins`
    names no plugin and stage 3 moves one line. Second, the old-shape keys `config migrate` and the
    load error still read are spelled in one frozen module, `legacy_settings.py`, which the fence
    exempts by name; the fence reads code only, as the forge fingerprint test does, so prose may
    still say promdance. Third, a related directory's own `promdance/` is now a `draft` source
    rather than skipped by name: it is still not wired and not walked, but it is mirrored, which
    surfaced the refused `index.md` note on `winrun`'s landing page. Fourth, the drafts caption is
    the role, `Drafts`, where it was `Drafts (promdance)`, as plan §4 says. Fifth, `docstrap doctor`
    lost `--projects-root`, because hook 6 takes doctor's root only; the projects root is promdance's
    setting. Building this repository's `.docstrap` before and after, in an isolated home, gave HTML
    that differs only by the route base, the two rebuilt bundles' cache hashes, the caption, and
    that note. The launcher does not yet withhold a derivative-writing tool from a project with no
    draft root; every project has one while promdance is on, and a write without one is refused.
33. **One Finish, below the questions** (2026-11-04) — spec §7.6(2), §8.1.3. Finish sat under each
    answer, over the bottom of the field, and submitted that one answer; the captain answered thirteen
    questions on a page and all thirteen stayed drafts. The editor's button is gone and autosave is
    unchanged. One Finish at the foot of the question list submits every draft in scope, one at a time
    through the existing per-answer route — there is no batch route, and none was added — and says how
    many it submitted and which failed. Its rules are `tools/qapanels/ui/finish.ts`, run under Node by
    `tests/qapanels/finish.test.ts`. The answer store and its format are untouched.
34. **The firstmate questions document** (2026-11-20) — `packages/docstrap/docs/fm-questions.md`.
    Every project promdance is on for gets `fm/questions.md` in its store entry, scaffolded by the
    promdance plugin's prepare hook when absent and never overwritten. It is reached in the project
    as `promdance/fm/questions.md`. The questions are ordinary `Q<n>` items opening with firstmate's
    `FMQ-<PROJECT>-NNN` reference, answered through the question panels. It was planned under
    `promdance/` and landed as the document `fm/questions`: a draft file has no document identity,
    so the plugin contributes the `fm/` directory as a second, non-draft source, and a mount may not
    lie inside `promdance`. No docstrap change and no pin bump.

### §1.4 Not landed

1. **The annotation client.** The store and its API subset are complete; nothing writes to them. This
   is the only deliverable from the original schedule still outstanding.
2. **End-to-end integration tests across the whole flow** — promote a draft, see the badge update,
   answer a question, submit a review, see annotations persist. The suite covers the pieces
   thoroughly (declarations against their consumers, the launcher offer rule, a real `sphinx-build`
   asserting the page carries no injected chrome, a whole new tool stood up through the extension
   seams alone, the strapdance reader against real fixture files, README inclusion, slug and storage
   ownership, skill install, promdance backup). The single end-to-end pass through all of them does
   not exist, and the interactive half is deliberately outside `tests/` because it needs a browser —
   it was driven instead against a real built sample site in headless Chrome, scripted so it can be
   repeated. `packages/docstrap/docs/tools-and-instruments.md` §7 records what that run asserted.
3. **`docstrap doctor` validating `.docstrap` files and checking the aggregate directory exists** —
   §1.1(7).
4. **`docstrap register` offering to include workspace members** at a uv workspace root. A
   workspace-mode `.docstrap` is written by hand.

## §2 The original completion criteria, checked

These six clauses were written as the test for calling a milestone done. Three of them are superseded
— the `docs-site/` equivalence gate, the `0.1.0` tag, and doctor's configuration checks — and the
rest are better read now as descriptions of a tool that works than as a gate it has to pass. Two are
unmet, and they are carried in the roadmap as deliverables rather than as things holding a release
shut.

1. `packages/docstrap/` is a working uv workspace member; `uv sync` at the root installs it into the
   shared environment and `uv run docstrap --help` prints the CLI. **Met.**
2. Both Claude skills are installable by `docstrap init` and invokable from Claude Code. **Met.**
3. A `.docstrap` at the workspace root produces an aggregate site, served by `docstrap serve`, with
   status badges, question forms and review widgets working against a running server. **Met**, and
   verified interactively rather than in `tests/`.
4. `docstrap doctor` runs against platformshoes and reports the current ambiguities in top-level
   docs. **Met.**
5. The annotation client exists and annotations persist end to end. **Not met**, and the only gap
   left from the original schedule.
6. A named, installable release state. **Not met**: no release tag exists in the repository. What
   that release should be numbered is decided by `VERSIONING.md` §2.3 — bump when you want to name a
   state you can go back to and install — and **when to call it is the captain's, not this
   document's.**

## §3 Where sequencing lives now

Not here. [`docs/roadmap.md`](roadmap.md) is where the next
deliverables and the version states they would land in are written; this document stops at the record
of what happened.

The original schedule's suggested next work — inotify daemon, then MkDocs and Quarto, then MCP
server, then the editor SPA, then team workflows and CI/CD — was written before any of the work in
§1.3 existed and has not been re-confirmed since, so it is not carried forward. Two of its entries
moved under the code rather than by decision, and both are picked up in the roadmap: the CI/CD entry
contradicts `VERSIONING.md` §1, which puts CI, a package index, publishing and release automation
permanently out of scope; and the MkDocs and Quarto stubs are the reason the vanilla-JavaScript
constraint on tools existed, so reviving them reopens a decision the Svelte conversion closed.

Prioritising against use rather than against a schedule was the position when this document was
written and is still the position — the difference is that there is now a real user exercising the
tool daily, and the next binding constraint is theirs to name.

## Open questions

Numbered so `docstrap questions` finds them, separately from the section numbers above. The
specification and the roadmap carry their own sets; these are the ones about sequencing rather than
design.

**Q1.** The annotation client is the only deliverable from the original schedule still outstanding
(§1.4), and the store it would write to is complete and unexercised. Does it stay on the roadmap as
work to be scheduled, or is the store left as it is until something other than the original schedule
asks for a writer?

**Q2.** No release tag exists in the repository. `VERSIONING.md` §2.3 says to bump when you want to
name a state you can go back to and install — is this that state, and if so is it `0.0.4` or the
`0.1.0` that §2.2 reserves for a tool that has settled?

**Q3.** MkDocs and Quarto layouts are still stubs, and their absence is what let the vanilla-JS
constraint on tools be withdrawn. Reviving them would reopen that decision. Retire the two layouts
outright, or keep them as roadmap?

**Q4.** The interactive verification of the tools runs in headless Chrome, scripted but outside
`tests/` because a browser is not a dependency this package should acquire
(`packages/docstrap/docs/tools-and-instruments.md` §7). Should the planned end-to-end integration
test be built anyway, or is that script the answer and the plan's deliverable retired?

**Q5.** `VERSIONING.md` §3.3 records a latent defect in `scripts/docstrap-stable.sh`: with no ref it
resolves the newest tag by tree content rather than by name, so the first tag of any other package
will silently resolve to it. The one-line fix is written out there and must land before a second
package is tagged. Should it land now, ahead of any tagging at all?
