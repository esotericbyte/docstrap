# docstrap — roadmap

Written 2026-09-01, against `main` at commit `f504754`. It says what comes next for a tool that is
already in use, in terms of what each piece of work delivers and which version state it would land
in.

This file sits in `plans/`. It was written in `proposals/` and said there that promoting it was the
captain's act rather than the document's claim; he performed it on 2026-09-07, together with the
specification. The folder rule accordingly now reads as approved.

Two companion documents, both reconciled against the code on 2026-09-01 and both in `plans/`:
[`docs/docstrap_on_2026-09-01.md`](docstrap_on_2026-09-01.md) is a dated description of what
docstrap did as of that reconciliation, and
[`docs/implementation-record.md`](implementation-record.md) is the
record of what has landed and how it differed from what was planned. This roadmap does not restate
either. Where all three disagree, `packages/docstrap/` is above them.

## §1 The starting point is a working tool

docstrap is at `0.0.3` and is used daily. It is installed through the stable path —
`scripts/docstrap-stable.sh install <ref>`, which puts a pinned `~/.local/bin/docstrap` on PATH from
a git ref rather than from whatever the working copy happens to be — and `docstrap --version` reports
which of the two installs answered. It builds every store in the user-level registry: three stores
holding twelve projects between them as of this writing, including its own workspace, and it is the
tool that publishes the document you are reading.

So nothing below is work toward a first usable release. The tool is useful now; the roadmap is about
where it gets better, and about naming states worth going back to.

What is already carrying that weight, all of it on `origin`: promdance backup; `ignore: true`
declarations honoured by every discovery scan, with the firstmate operational-home check that offers
to write one; the stable dogfood install; the `x.y.z` version policy, at `0.0.3`; the strapdance
front-matter reader shared with promdance; tool declaration objects with a single visibility
launcher; Sphinx resolved from docstrap's own environment; `docstrap doctor` and the lifecycle skill;
one owner for slugs and one for promdance storage; the Svelte conversion of the tool UI; a project's
README reaching its site; expected CLI errors reported as errors rather than tracebacks; and
`docstrap questions`, scoped to one project per run. §1 of
`docs/implementation-record.md` is the itemised account, with commits and dates.

## §2 How work is named here

1. **Versions are `x.y.z` and nothing else.** `VERSIONING.md` §2.1 is the policy and it is already in
   force: a version is three integers, no suffixes and no labels, and a release tag is spelled
   `docstrap-v<x.y.z>`.
2. **A phase is named by what it delivers**, in a phrase a reader can check against the code — "a
   client that writes to the annotation store", "one end-to-end pass through the whole flow". A bare
   phase number is not a name; it says only how many things came before it, which is the one fact
   nobody needs.
3. **Alpha labels already committed elsewhere in the repositories stay where they are.** Such a label
   scopes a *component's* own maturity, which is a real thing to say about a component. It is not a
   position in an overall schedule, and this roadmap does not extend the series or hunt down existing
   uses.

## §3 The next release state

`VERSIONING.md` §2.3 gives one trigger for moving the number: bump when you want to name a state you
can go back to and install. docstrap is in the `0.0.z` era, so the next release state is `0.0.4`, and
entering `0.y.z` is a deliberate statement that the tool has settled rather than something reached by
counting. **When to call either is the captain's, and this roadmap does not call it** — the
implementation record's Q2 is where that question lives.

Three things belong to whichever release comes next rather than to a later one.

1. **The index is transient, transparent and HTML-only, and it has landed.** `docs/docstrap_on_2026-09-01.md` §7.8 is
   the account: no build produces markdown anywhere, `file_index` (§5.2) is what a published
   directory contains, and the seventeen `index.md` files earlier builds left in this repository are
   gone (§4.12). It is listed here rather than below because it is done and it is part of what
   `0.0.4` would name, not work under consideration.
2. **Tag resolution filtered by name.** `scripts/docstrap-stable.sh`, given no ref, resolves the most
   recent tag whose *tree* contains `packages/docstrap`. In a workspace every commit contains every
   package, so the first tag of any other package silently resolves to it and installs a plausible
   wrong version with no error. `VERSIONING.md` §3.3 has the one-line fix written out. It must land
   before a second package is tagged, and today no package is tagged at all, so the cheapest moment
   is before the first tag exists.
3. **The first annotated tag.** No release tag exists in the repository. Until one does, the stable
   install path's no-ref form refuses and asks for an explicit ref, which is correct behaviour but
   means every dogfood install names a commit by hand.

## §4 Deliverables under consideration

Each entry names what it would deliver, what state it is in, and what it is waiting on. The order is
the order they are written in, not a queue: none of these has been scheduled.

### §4.1 One end-to-end pass through the whole flow

Promote a draft, see the badge update, answer a question, submit a review, see the derivative land.
The suite already covers the pieces thoroughly — declarations against their consumers, the launcher
offer rule, a real `sphinx-build` asserting the built page carries no injected chrome, a whole new
tool stood up through the extension seams alone, the strapdance reader against fixture files, README
inclusion, slug and storage ownership, skill install, promdance backup. The single pass through all
of them does not exist.

**The surface that pass runs against was built on 2026-09-07**: the three-panel Q&A instrument of
`docs/docstrap_on_2026-09-01.md` §7.6, with the keyed answer store of its §8.1 underneath it. Answering a
question end to end — select it in the list, type into the editor, watch it autosave, reload and find
it under the same key — is now a real path through the flow rather than a described one, and
`packages/docstrap/tests/test_answers.py` walks it against a built project. What is still missing is
the *single* pass that crosses every piece in one run, which is what this deliverable names.

The interactive half is deliberately outside `tests/`, because a browser is not a dependency this
package should acquire; it was driven against a real built sample site in headless Chrome, scripted
so it can be repeated, and `packages/docstrap/docs/tools-and-instruments.md` §7 records what that run
asserted. Whether the scripted run *is* the answer or the automated test should be built anyway is
open as the implementation record's Q4, so this deliverable is described here and not sized.

### §4.2 A client that writes to the annotation store

The annotations database and the W3C Web Annotation Protocol subset are complete and nothing writes
to them. The Annotorious embed was specified and never implemented; that specification was removed
from the live documents on 2026-09-01 and is at
[`docs/archive/superseded-2026-09-01.md`](archive/superseded-2026-09-01.md).
The captain confirmed on 2026-09-07 that the store is Annotorious's and that Annotorious remains the
intended client (the specification's Q4). It is a real external dependency and adding it is not
scheduled, so this is still a store waiting for its writer rather than a dated build.

### §4.3 The aggregate affordances nothing replaced

Cross-project tag index, backlinks, cross-project cross-linking and a recent-updated feed were
expected from an external aggregate module that was never adopted. docstrap grew its own aggregate
instead and none of the four came with it. Whether they are still wanted is open as the
specification's Q3; if they are, they are aggregate-build work rather than tool work, and they land
wherever the aggregate is built.

### §4.4 Two small completions in commands that already exist

`docstrap doctor` answers "which documents does no project own?" through the strapdance chain and
reports firstmate homes as an environment check. It does not validate `.docstrap` files or check that
an aggregate directory exists, both of which were planned. Separately, `docstrap register` does not
offer to include workspace members at a uv workspace root, so a workspace-mode `.docstrap` is written
by hand. Neither is blocked on a decision; both are small and neither has been asked for by use.

### §4.5 Layout coverage, decided before implemented

`mkdocs` and `quarto` are stubs that raise a not-implemented error naming the project. Their absence
is what let the vanilla-JavaScript constraint on tool UI be withdrawn, so reviving them reopens a
decision the Svelte conversion closed. That makes this a decision to take deliberately rather than by
starting to implement; the implementation record's Q3 asks whether to retire the two layouts outright
or keep them.

### §4.6 Projects discovered rather than hand-listed

**docstrap is a project tool, not a repo tool.** A repository is a container; the unit docstrap
publishes, names and reasons about is a project, and one repository routinely holds several. Today
`scan` reads a `projects:` list somebody wrote by hand, which makes the tool's central unit a thing a
person has to remember to declare.

Discovery derives it instead. `ignore` is honoured first, unchanged: a `.docstrap` carrying
`ignore: true` stops the walk at that directory and its whole subtree. Where it is not set, docstrap
looks for directories containing a `pyproject.toml`, and **each of those is a separate project** —
one rule covering the uv workspace and the single-package repository alike. A project's documents are
either the repository's top-level `docs/`, or a `docs/` sitting beside that project's own
`pyproject.toml`.

The name is the package's, not the directory's. Under `[project]` in a `pyproject.toml`, the `name`
key is the project name, and the `readme` key is also of interest. That name is what agents see in
docstrap front matter, so it is an interface rather than an implementation detail, and it carries a
uniqueness rule with two strengths: across repositories a project name should *usually* be unique, and
within one repository it *absolutely* must be. Where it is not, the default naming rule cannot be
applied, and in this version the developer is asked to resolve it rather than the tool guessing.

**A project with no documents directory is still a project.** Decided by the captain on 2026-09-12.

**`stop_dirs` stops the walk, and it is one list rather than a set of special cases.** It holds
patterns matched against a directory's own name, and descent halts at any level on a match. The default
is `["tests", ".*"]`.

Both defaults earn their place from the tree rather than from taste. `tests` is there because discovery
finds manifests and test data is full of them: `packages/docstrap/tests/fixtures/` alone holds five
`pyproject.toml` files, two of them declaring projects both named `alpha`, so without the stop docstrap
registers its own fixtures as projects and then trips its own within-repository uniqueness rule on
them. `.*` is there because no dotted directory ever holds a project: `.venv`, `.pytest_cache`,
`.svelte-kit`, `.vite-temp`, `.doctrees`, `.git`, `.claude` and six more appear within three levels of
the captain's repositories, and every one is machinery. Measured across all seven repositories on
2026-09-12, the two together exclude exactly those five manifests and nothing wanted.

Patterns rather than literal names is what keeps this one field: `.*` cannot be expressed as a name,
and a repository that wants something else out of discovery adds an entry here rather than asking for
another rule. It also generalises to the discovery walk what the scanner already applies to
config-relative paths (`docs/docstrap_on_2026-09-01.md` §3).

It is a **walk** rule, not a predicate applied to a path. The distinction matters: docstrap's own suite
points the scanner at `tests/fixtures/workspace` as its root, and that walk begins below the `tests`
directory and never meets it. A rule written as "reject any path containing `tests`" would break the
tests that prove discovery works.

It is also distinct from `exclude_dirs`, which names directories skipped inside a documents tree once a
project is known. `stop_dirs` decides whether a project is found at all.

Two tiers, which the current single `projects:` field conflates:

1. **The per-repository map**, `projects`, maintained in that repository's own `.docstrap` file — a
   map from project name to that project's documents directory. It describes one repository and it is
   kept up to date there.
2. **The cross-repository list**, assembled from every `.docstrap` across every registered repository.
   It is not repository-local material and does not belong in any one `.docstrap`; where it lives —
   the metadata database, or a YAML file under `~/.local` — is not settled here.

Python under uv is the rule above. **JavaScript is wanted in the same release**, and its marker and
name key are Q7 below rather than assumed. **Rust follows soon and is not the same shape**: cargo
projects carry `examples` sub-projects, and a crate may ship a library, an application, or both as its
main product. The captain's words are that Rust projects are "more tightly related than the uv python
workspaces", so one-manifest-one-project does not transfer unmodified. Whether Rust arrives as a
plugin or a built-in, and whether other ecosystems need a plugin surface at all, is open.

### §4.7 Metadata that survives a move

**A broken path should not have a database entry, and a document that moved should be followed rather
than dumped.** Status, tags, and the key an answer hangs on all attach to a document's identity, so a
rename that detaches them loses work that was never about the path.

**Git is the best source for this**, and docstrap's own history is the worked example. The metadata
database still points at `docs/plans/docstrap-mvp.md`, a path that stopped existing on 2026-09-01. Git
has that move recorded as `R070` in commit `b95c7d8` — a rename detected at seventy percent
similarity. The information docstrap lost was in git the whole time. The four documents moved into this
directory on 2026-09-12 are a second, larger fixture: same repository, four renames, content unchanged.

The limit belongs in the design rather than in a later surprise. Git does not *record* renames; it
infers them by similarity when asked, defaulting to fifty percent. A rename that also rewrites the file
falls below that threshold and reads as a delete plus an add. So git recovers the ordinary case and not
the heavily-edited one. Several algorithms could do better, and the captain's observation is that most
of them require prior planning: an identity written into the document survives any amount of editing,
and git is the recovery path for documents that never got one.

### §4.8 The orphaned pool, and a collector for it

§4.7's "otherwise". A metadata row whose document cannot be resolved to a move does not become a
deletion and does not stay live. It moves into an **orphaned pool**, which is ignored — not published,
not counted, not reported as a live document — unless something recovers it, and its entries are
eventually discarded.

Three states rather than two is what lets §4.7's first sentence be true without losing data: the broken
path leaves the live table immediately, and the metadata still gets a window in which a recovery can
claim it.

How long that window is **does not matter and will be configurable**. What the pool needs instead is a
**garbage collector that takes arguments and cleans the oldest records when the pool gets big**, and a
**flag when it exceeds roughly two megabytes**. Size is the trigger worth watching, not age.

### §4.9 A command that hands out the link

**docstrap should print the URL for a document, so whoever produced it can hand that link to whoever
must act on it.** Nothing does today. An agent that writes a question document into a project can name
the file and stop; turning it into something the captain can open means registering the project,
running a build, starting the server, and assembling a path by hand from knowledge of the site's layout.
The captain's words on watching that happen, 2026-09-12: "this is what docstrap should do - it should
give you the link that you can give to me."

The gap is exactly where the firstmate bridge stops on purpose. That adapter's own contract says it
names *which* document is relevant and emits no anchor and no href, because it does not own the site's
URL structure. That reasoning is right and it leaves the other half unclaimed: docstrap owns the URL
structure and offers no way to ask for one.

What it needs is a resolver — given a path to a document inside a registered project, return the URL it
is served at — plus the same answer surfacing wherever a document is already named, so `questions` and
`status` can carry a link rather than a path. Two details matter. The answer must be available **without
a running server**, since the URL is knowable from the site layout and the caller may be arming a review
the captain opens later. And it must state plainly when the document has not been built yet, rather than
returning a URL that will 404.

This sits close to the mission note of 2026-09-12: easing communication between actors is most of what a
link does.

### §4.10 An MCP server, built with FastMCP

**docstrap exposes its capabilities over MCP.** Decided by the captain, 2026-09-12, naming FastMCP as
the implementation. This reverses `docs/docstrap_on_2026-09-01.md` §0.2, which lists an MCP server under what is not in
scope; that listing predates the mission statement of the same day.

The reason is in that mission: format and delivery are to be optimised for **both human developers and
agents**. Today the human half has a built site, a search index, a launcher and three panels, while the
agent half has a command line it must shell out to. An agent that wants the open questions in a project
runs a process and parses its output. That asymmetry is the gap.

It also settles §4.9 for agent callers. A human needs a URL to open; an agent needs the document and can
use the URL for citation. One tool returning both means the link question is answered once for each
audience in the way that audience needs it.

**The boundary that keeps this from becoming a second implementation.** MCP is a transport over
capabilities that already exist or are already specified, never a parallel copy of them. Question
discovery is the strapdance reader's, the answer store is `docstrap.answers`', metadata is the metadata
database's, and URL resolution will be §4.9's. Each keeps its single owner and the MCP surface calls it.
A tool that reads the answer file itself, or re-derives a question, is the mistake this paragraph exists
to name.

The surface worth having is small and follows from that: list the projects a user aggregates, list a
project's documents, read one, list its open questions, submit an answer through the same intake the
panels use, and resolve a document to its URL. What it must not do is write to a source document —
`docs/docstrap_on_2026-09-01.md` §0's two properties hold here exactly as they hold for every tool, and an MCP client is a
better-armed caller than a browser, not a more privileged one.

### §4.11 The answer loop, from a real run

Eight questions were exported into a project on 2026-09-12 and answered by the captain on 2026-09-13,
through the ordinary store. The answers travelled correctly and closed the right work. Six things the
run exposed, in the order they hurt.
[`docs/plans/0001-answer-loop.md`](plans/0001-answer-loop.md) ordered the repair and cites these
numbers, so they keep them.

**All six were closed on 2026-09-14**, by that plan's six steps in order. Each item below says which
step closed it and which section of the specification now states the behaviour. The findings are kept
rather than deleted because they are the record of what one real run cost, and because the plan and
the implementation record both cite them by number.

1. **An answer counted the moment it was first saved.** The editor autosaves, so a reply was read at
   three characters - "NO!" - and that closed the decision. Everything typed afterwards was refused,
   correctly, because the recorded decision no longer matched. The same thing happened to the next
   question at "NO. It should not. There are". **Closed** on 2026-09-14 by the explicit submit of the
   plan's step 1: an autosave writes a draft, nothing downstream sees a draft, and the quiet-period
   alternative was not needed. Specification §8.1.3.
2. **There was no way to finish.** The captain's words: "There needs to be a finish button to end the
   process in the interface." Without one, anything consuming answers had to guess when a person was
   done, and guessing is what produced item 1. **Closed** by the same step: the instrument's Finish
   button is the only thing that submits.
3. **A recorded answer could not be revised.** A captain rewriting his own reply while the question is
   still visibly open is ordinary, and it required a hand repair of the record. Revision *before*
   submission came free with step 1, because nothing has counted yet. **Closed** on 2026-09-14 by the
   plan's step 2 for revision *after* submission: a later answer supersedes rather than being
   rejected, the answer it displaces is kept in `answers-history.md` beside the current ones, and a
   revision being typed sits beside the standing decision rather than erasing it while it is typed.
   Specification §8.1.4.
4. **The question document and its answers are not connected in any surface.** Checked on the real
   build of 2026-09-13: the rendered page carries no answer text, no link to the store, and no
   indication that any question has been answered; the store is not published into the site at all; and
   `/api/promdance/answers` returns 404. The binding exists in exactly one place, the store's own
   `## <document-id>:<label> - <path>` heading, and it points from the store to the document. Nothing
   points back, and nothing renders either direction.

   **Closed** on 2026-09-14 by the plan's steps 4 and 5. Step 4: `/api/answers/<project>` and
   `/api/answers/<project>/<doc-slug>` return the pair, so a consumer that is not the browser can ask
   what is answered without parsing markdown (specification §8.2). Step 5: the `answered` tool marks
   each `Q<n>` in the rendered page at build time and hangs its current answer off it at serve time,
   so a reader can tell an answered question from an open one without leaving the page
   (specification §7.7). Nothing is written into the document; §0 holds unchanged.

5. **The panel was scoped to the project, never to the document.** It registered one read handler,
   `list_questions(project)`, which took no document argument, so opening the instrument while reading
   one document listed every question in the project. **Closed** on 2026-09-14 by the plan's step 3,
   on the captain's requirement that the choice be explicit — **document scoped or project scoped**,
   deliberately, rather than project-wide by omission. The collection is now readable under both
   bases, the second declared as `also_scoped_to` so the derived route table still accounts for every
   mounted path, and the panel's header is where the choice is made. It defaults to the document.
   Specification §7.6(1).
6. **Nothing closed the loop.** An answer landed in the store and no record was produced: no addendum
   to the document, no new version of it, no artifact anyone would cite. The captain, 2026-09-14:
   "it's a pregnancy with no delivery." **Closed** the same day by the plan's step 6: submitting an
   answer writes `<doc-slug>__answers.md` beside the document in promdance, at a stable path a
   citation keeps resolving to, carrying an `answered_version` digest that moves when a decision moves
   and at no other time. Specification §8.3.

Item 4 was the structural one, and item 6 is what made it matter. §0 promises that nothing is altered in
place and that tools produce derivatives beside the original, so appending answers into the question
document was correctly forbidden — but **"not appended" had been allowed to become "not linked"**.
Derivative beside the original is a storage rule, not a reason for the reading surface to show one
without the other. And a question document is a request for a decision: a decision that leaves no
artifact has not been delivered, it has only been stored, which satisfies neither documents-as-the-unit-
of-value, nor the documentation-first practice, nor dkp's contract stamp deriving from a document's hash.

Both were repaired without writing into the question document, which §0 still forbids. The reading
surface resolves the pair at serve time against a build-time anchor (§7.7); the same pairing is readable
over the API, so a consumer other than the browser can ask what is answered without parsing a markdown
file (§8.2); and a submission now delivers an addendum beside the original carrying a version that moves
when a decision moves (§8.3). The key that made all of it possible already existed: an answer hangs on
`<document-id>:<label>`, which survives a rename.

### §4.12 Removing the index files earlier builds left in five repositories

No build writes markdown for a section page any more, anywhere (`docs/docstrap_on_2026-09-01.md` §7.8), which stops
fifty-five tracked `index.md` files from growing to fifty-six but removes none of them. The removals
are one commit per repository — `platformshoes`, `rlp`, `trk_tdp`, `dkp`, `formizer` — and they had
to wait for the fix to land, because a rebuild before it would have recreated whatever was deleted.

**`platformshoes` is done, in two passes.** Seventeen files went on the branch that landed §7.8.2,
driven from the report and not from anybody's reading of them. Nine more went when the captain closed
the exception the first pass had left standing (§7.8.6): seven package-docs placeholders, docstrap's
own `docs/index.md`, and the `docs/notes/index.md` the first pass had deliberately left alone. The
rest are in the other four repositories and are not this repository's business.

**The rule the other four have to meet is now the absolute one**, not "the files docstrap claims".
The scrub script below removes what docstrap claims, which is a safe subset;
`scripts/check-no-index-md.py` is what says whether a repository has finished, and it fails on every
index file in a documentation tree whoever wrote it. Run the script for the easy deletions, then the
check, then decide by hand about whatever the check still names.

**`scripts/scrub-docstrap-generated-indexes.sh` is what does the remaining four.** It asks
`docstrap generated-indexes --json` which files docstrap claims, removes only those, stages them with
`git rm`, and commits and pushes nothing. It dry-runs by default and refuses a repository with a
dirty tracked tree. Same contract as the `platformshoes` pass, which was driven from the same JSON by
hand before the script existed.

`docstrap generated-indexes` is what each of the rest is driven from, and its output does not need
reading twice: `generated` is byte-identical to what those builds wrote and is a safe deletion;
`divergent` is a file docstrap declines to claim and a person decides, which is where stale output of
an older build and another tool's page both land, deliberately (§7.8.4). The two things not to do are
already known, because both have been done: do not classify these files by grepping their prose, and
do not repair a stale one silently.

Two things the `platformshoes` pass established that the others will meet too. **The report reaches
only directories a `.docstrap` declares**, so an `index.md` under a directory no project names is
absent from its output rather than cleared by it — nine of the thirty-one tracked files here were in
that position, and all nine turned out on reading to be authored. And a file that *is* docstrap's
output with one line appended by hand comes back `divergent`, correctly: `packages/docstrap/docs/
notes/index.md` was that case. It was left alone by the first pass and deleted by the second, which
is the difference the absolute rule makes — a `divergent` finding is no longer a reason to keep a
file, only a reason not to let a script delete it unread.

Nothing about this is scheduled here. It is one command's output and four small commits, and it is
somebody's afternoon rather than a deliverable that needs designing.

### §4.13 A watcher, so a document is indexed because it appeared

`docs/docstrap_on_2026-09-01.md` §11(4) is a long-standing intent and §7.8.5 is now the requirement it answers:
indexing is the tool's job, it is automatic, and the trigger is file creation rather than somebody
running a build. A watcher observes creation, movement and deletion under a project's `docs_root`,
writes the one path that changed into `file_index`, and leaves it there — never carrying its own copy
of the rules, and writing into the build area like everything else.

**Both seams now exist rather than being intended.** `fileindex.record` and `fileindex.forget_path`
are one-path calls and were written that way round deliberately, with the whole-project `reconcile`
built from them, because the watcher is the caller that shapes the API (spec §5.2.4).
`sectionindex.compose` answers what a section contains from the table with no directory walk, so a
watcher that has seen one event does not need to look at the tree. There is nothing else to do on an
event: no cached page to invalidate and no staleness to detect, because a section page exists only
for the length of the Sphinx run that emits it.

What is undecided is everything around it: whether it is a daemon of its own or folded into
`docstrap serve`, what it does about the metadata database at the same moment, how it behaves when a
build is running underneath it, and what it does with a file that appears in a project no build has
ever indexed. The choice of watcher library is also open, and it is a dependency to declare rather
than assume — `inotify` is the mechanism named in §11(4), not a package that is installed.

### §4.14 Plugins for document types and workflows

An ADR, a specification, a research note and a draft answer are not one kind of document. They have
different lifecycles, different front-matter, different apparatus on the page and different ideas of
what "done" means. Today the layout handles the differences it knows about as special cases inside
itself, and that does not scale past the handful it already carries.

`docs/docstrap_on_2026-09-01.md` §7.9 names this as a direction and nothing more. The declaration object of §7.1 is the
obvious precedent — a tool is a directory with a declaration and three consumers read it — and a
document-type plugin would want the same property: one declaration, no consumer keeping a copy of
what it says. Nothing is designed, and the first real question is which document types actually
differ in ways worth modelling rather than which ones have different names.

### §4.15 Adopting a project's own promdance directory

`promdance intern` does the whole wiring except one step: where a project already holds a real
`promdance/` directory, completing the captain's creation sequence means **moving** its files into
the store, and `intern` never moves a file. Such a project is reported and left as found
(`docs/docstrap_on_2026-09-01.md` §8.6). Three repositories are in that state today.

There is no agreement gating this and no design question outstanding — the sequence has been settled
since 2026-09-15 (add to `.gitignore`, create the store directory, move the files, symlink) and the
move is what takes the drafts out of git. What is missing is a safe shape for performing it, because
a repair command that sweeps every registered project is the wrong place for a one-way change to
somebody's repository to happen for the first time.

The shape to copy is chezmoi's, which solves the identical problem: show exactly what would move
before moving it, and make the doing a separate act from the seeing. A per-project command rather
than a sweep, a dry run that lists the files, and a refusal when the store entry already holds
content, since merging two sets of drafts is not a repair.

### §4.16 A source-control plugin, with pluggy

`docs/docstrap_on_2026-09-01.md` §8.7. A connector for source-control providers other than GitHub is intended, and
`pluggy` is the likely mechanism. The boundary already exists: `docstrap.forge` defines the three
things a provider has to answer, every GitHub specific lives in one class behind it, and a test
fingerprints the boundary so a provider detail written above it fails the suite.

So this is not a refactor waiting to happen — it is a registration mechanism waiting to be wanted. It
becomes real when there is a second provider to register, and the first question then is whether the
three methods are the right three, which one real second implementation will answer better than any
amount of designing against none.

### §4.17 Archiving a promoted prompt

The fifth item of the captain's 2026-09-17 note: a system to archive used prompts and specifications
in the promdance git when they are promoted into `docs/`, triggered by a change in the strapdance
header. `docs/docstrap_on_2026-09-01.md` §8.8 is its named place and holds nothing, at his explicit direction — he said
he needs to think it through himself.

Now that the store is a git repository (§8.4), the "archive in the promdance git" half has somewhere
to happen. The undecided part is the trigger: which strapdance header change means *promoted, now
archive the original*. That is a question about the header vocabulary before it is a question about
archiving, and the vocabulary's status values come from a document's position
(the document that described them, `docs/strapdance-front-matter.md`, was retired on 2026-11-20). Waiting on
the captain.
### §4.18 An upgrade path, so being out of date is loud

**There is no upgrade path of any kind, and the way it fails is silence.** `PRAGMA user_version` is 0
on both databases, every table is created `IF NOT EXISTS` so an existing database never gains a
column, and no migration machinery exists. A user running a docstrap from today against a schema from
August gets no error: the code moves on and the data does not. Raised by the captain on 2026-09-17,
who named four axes that drift independently — the database schema, the strapdance vocabulary, the
instructions an adopting project carries, and the MCP server that is not built yet.

[`docs/proposals/0002-the-upgrade-path.md`](proposals/0002-the-upgrade-path.md) is the plan: a
manifest of named integers rather than one number, `PRAGMA user_version` as the store, an exact-match
comparison so a *newer* database refuses as loudly as an older one, and one explicit command that
migrates after taking a backup. It surveys the migration libraries first and rejects all of them, with
the reason for each. It sits in `proposals/` because the captain has not evaluated it, and it ends
with seven questions.

**§8.4's store is its fifth axis**, added the same day the other four were named. A git repository
with a remote is a third persistent state, and one that can travel between machines running different
docstraps — so an older docstrap can pull a store a newer one wrote, and git will merge it without an
opinion. That plan's §12 is the section: a layout version carried in a commit trailer, because §8.4.2
forbids writing any file in among the drafts; reads never refused, `commit` and `push` refused when
the store is ahead; and a layout migration that is a file move, so §4.15 above is already its answer.

**This is what §4.7 and §4.8 are waiting on**, whether or not they know it: metadata that survives a
move, and the orphaned pool's third state for a row, are both schema changes, and there is nowhere
safe to put a schema change until a version exists to number it against.

Surveying the live database for that proposal turned up something §4.8 should hear. **59 of the 64
document rows in `~/.local/share/docstrap/metadata.db` were written by one test** —
`test_tag_reports_metadata_error_without_traceback`, which omits the `user_dirs` fixture and so runs
`docstrap tag` against the real store — and every one of them points at a `/tmp` path that no longer
exists. Four rows point at a document that exists. The orphaned pool was designed with a garbage
collector and a two-megabyte flag before anyone had counted how many rows were already waiting for
it; those 57 are its first customers, and the test is a defect in its own right.

## §5 Deferred with the numbers already seen

**A shared runtime chunk across tool bundles.** Each tool bundle carries its own tree-shaken copy of
the Svelte runtime, so a page ships 105.7 kB raw where ES-module bundles sharing one chunk would ship
roughly 40 kB. The measurement is in `packages/docstrap/docs/tools-and-instruments.md` §5.1. The
captain has seen those numbers and deferred the change: it alters how a tool's bundle is *served*,
which is a declaration-surface decision rather than a build detail, and per-page cost has not yet
been the binding constraint on anything. Deferred is not rejected — the numbers do not change on
their own, so this returns when a page's weight is what someone is complaining about.

**Metadata for documents that live only in git.** Normal functioning scans the directories holding
`.docstrap` files when it collects new documents, and culls documents that have moved into git-only.
Keeping metadata alive for a document that exists in history but not in any scanned tree needs a way to
model that state in docstrap, and no such model exists. The captain deferred it on 2026-09-12: it is an
issue to think about rather than work to schedule, and §4.8's orphaned pool is what holds those rows in
the meantime.

`docs/docstrap_on_2026-09-01.md` §11 is the full list of what does not exist, each entry a statement of
absence rather than a commitment. Its ordering predates four of its own entries and has not been
re-confirmed, which is the specification's Q6.

## §6 What every deliverable inherits

These are settled and any work above is bound by them.

1. **Svelte is the default for a tool's UI**, compiled to the bundle its declaration names, with
   scoped component styles. Vanilla JavaScript survives only for genuinely tiny pieces. Built bundles
   are committed, so installing or running docstrap needs Python only; Node is a dependency of
   changing a tool's UI, not of using one. Skeleton remains for instruments, because a tool renders
   inside a page whose styling Sphinx and furo own.
2. **Questions are found by analysis, not by an index.** `docstrap questions` reads a document's own
   `Q1`/`Q2`/`Q3` labels at the end of the document and interprets no question mark, and a run is
   scoped to one project resolved through `docstrap.projectscope`. There is no index and no store of
   questions, and nothing above may introduce one: any listing is a scan, and a build artifact
   holding questions would be derived and disposable, never authoritative.
   `packages/docstrap/docs/finding-questions.md` has the three rules.
3. **Nothing is altered in place.** No tool, reader or command writes to a source document; tools
   produce a derivative beside the original. This is what makes it safe to point docstrap at a clone,
   a read-only checkout, or someone else's repository, and it is not negotiable for a new tool.
4. **One owner for a name, for a path, and for the answer store.** `docstrap.slugs` is the only thing
   that turns text into a name, `docstrap.paths` the only place a promdance path is composed, and
   `docstrap.answers` the only thing that reads or writes an answer file. A second implementation of
   the first two is what orphaned submitted answers once.
5. **No CI, no package index, no publishing, no release automation, no changelog.** `VERSIONING.md`
   §1 puts all of it permanently out of scope for this workspace. The specification's §11 still lists
   CI/CD integration as a roadmap item; the two statements contradict each other and the
   specification's Q5 is where that is asked.

## Open questions

Numbered so `docstrap questions` finds them, separately from the section numbers above. Questions
that already live in the specification or the plan are cited by number above rather than re-asked
here, so each is asked in one place. All three were answered by the captain on 2026-09-07; each keeps
its label and its number, with the answer written into the item, because a number is half of the key
an answer hangs on (`docs/docstrap_on_2026-09-01.md` §8.1.1).

**Q1.** The question-and-answer panels have no decided answer store. Submitted answers are appended
to `<doc-slug>_answers.md` in the project's promdance directory today, which is a derivative file and
not a store anything queries. Where do answers belong — the metadata database, the annotations
database under a questioning motivation, a promdance-side store of their own, or the file they
already land in?
**Answered 2026-09-07 — a promdance-side store of their own.** One keyed markdown file per project
with YAML front-matter, `<project-promdance>/answers.md`, owned by `docstrap.answers` and specified
in `docs/docstrap_on_2026-09-01.md` §8.1. Not the annotations database: that store is Annotorious's, which
`docstrap.annotations`' own docstring says, and its `creator` field models a different audience —
a reader of a deployed site, identified by the deploying organisation's user system, a Discord or
Telegram handle, or an email address — rather than whoever owns a document and decides its open
questions. The keying is the substance of the answer, and it is §8.1.1: the metadata store's document
id plus the question's own `Q<n>` label, so an answer survives the file being renamed and answering
twice supersedes rather than stacks.

**Q2.** The editor surface, if docstrap grows one, has a candidate already written next door:
`apps/laces-desktop/src/lib/Editor.svelte`. Extract it into a shared package both consume, vendor a
copy into docstrap and let the two diverge, or reimplement against docstrap's own needs?
**Answered 2026-09-07 — none of the three; a plain `<textarea>`.** The reusable thing across the
captain's surfaces is the autosave *behaviour*, not an editor component, so there is nothing to
extract, vendor or reimplement. docstrap's editor is a plain textarea with no editor library and no
new dependency, and it reproduces the behaviour recorded in
`packages/laces/docs/adr/0013-autosave-event-driven-firing.md` and
`packages/laces/docs/adr/0007-no-buttons-transitions-autosave.md`. Those ADRs are **cited, not
adopted**: they were written for laces and are accepted there, so docstrap references them as the
referent for its own implementation rather than restating them as docstrap decisions or copying their
text into a docstrap ADR.

**Q3.** The three-panel Q&A mode was scoped as a later phase in a numbered series that no longer
exists (`docs/docstrap_on_2026-09-01.md` §7.3). The launcher was deliberately built so a second control
could drive tool visibility without owning it, which is the seam three-panel mode was expected to use
(`packages/docstrap/docs/tools-and-instruments.md` §3). Where does it sit now — a deliverable in
§4 above, a deferred item in §5, or dropped?
**Answered 2026-09-07 — a deliverable now, and delivered.** Not deferred and not dropped. It is
`docstrap.tools.qapanels`, specified in `docs/docstrap_on_2026-09-01.md` §7.6, and it uses exactly the
launcher seam the question names: it is declared an instrument, so the launcher gives it a launch
action rather than a toggle and drives `docstrap.tools` visibility without owning it.

**Q4.** §4.6 states the Python discovery rule exactly: a directory containing a `pyproject.toml` is a
project, and its name is `[project].name`. JavaScript is wanted in the same release and its equivalent
is not stated. Is the marker `package.json`, and is the project name its `name` field?
