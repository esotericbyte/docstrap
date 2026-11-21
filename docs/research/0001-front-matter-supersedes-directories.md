---
research: 0001
title: Front-matter superseding directories, and where per-project documentation is filed
status: Open
started: 2026-09-01
last_updated: 2026-09-01
related_specs:
  - "/home/johnh/firstmate/data/spec-context-frontmatter.md"
  - "docs/docstrap_on_2026-09-01.md"
  # packages/docstrap/docs/strapdance-front-matter.md was retired on 2026-11-20.
related_notes: []
related_code:
  - "packages/docstrap/src/docstrap/strapdance.py"
  - "packages/docstrap/src/docstrap/metadata.py"
  - "packages/docstrap/src/docstrap/config.py"
---

# RN-0001 — Front-matter superseding directories, and where per-project documentation is filed

This note surveys, reasons, and poses questions. It decides nothing, it changes no code, no
vocabulary and no layout, and it does not resolve the questions it raises. Every count in §4 was
taken from the working copies under `/home/johnh/firstmate/projects/` on 2026-09-01 and the method is
stated so the numbers can be re-taken.

## 1 The question

Front-matter was designed to be adoptable: §2.2 of the specification says "no existing document has
to be touched to participate", and the fallback chain reads meaning out of directory names so that
untouched documents still resolve. That was the right property for arrival. It is a different
property from the one now being asked for, which is *supersession* — a project that has adopted
front-matter should stop having its directories read as declarations. Two things follow that the
current design does not have: a way for a project to say it has crossed over, and a statement of
what directories are for afterwards. A third thing surfaces once the crossing is examined: the
vocabulary the chain reads out of directories has its two axes crossed, and the crossing is an
artefact of where the vocabulary came from.

Separately but not unrelatedly, the workspaces themselves do not agree on where a project's
documentation is filed. That is measurable, and §4 measures it.

## 2 What triggered it

2.1 The captain, on the transition: "when a project transitions from directories to frontmatter …
the old directories are no longer used for that project." And the corollary, in the same breath:
"The design of the frontmatter needs to also design how directories are used." Directories do not
disappear when they stop carrying status and kind — they still hold files, and something has to say
what holding files is *for*.

2.2 The captain, on the filing system: "There also needs to be a better project filing system for
workspace repositories. Either a `docs/<project>` as a directory or as a symlink into the
`apps/<project>` or `package/<project>` … the layout of these workspaces is also very
inconsistent."

2.3 The captain's diagnosis of why the vocabulary is crossed, which §3.3 tests rather than assumes:
the vocabulary was derived from the folder layout that front-matter is meant to supersede, so it
inherited the folders' limits.

## 3 What the code actually does

Everything in this section was read out of the modules; nothing is taken on faith.

### 3.1 There is no notion of a project having crossed over

`read_context` in `packages/docstrap/src/docstrap/strapdance.py` resolves each field independently
through the chain, per field, per document. `_resolve_kind` takes step 1 (an explicit value in the
`strapdance` namespace, or a bare compatibility key) and otherwise falls to
`KIND_BY_DIRECTORY.get(parent.lower())`. `_resolve_status` does the same against
`STATUS_BY_DIRECTORY` and `HOLD_DIRECTORY`. Neither consults the project, the `.docstrap` file, or
any per-project state. The reader does not take a "this project has adopted front-matter" argument
and there is nowhere to put one: `read_context` accepts `path`, `collection_root` and `text`.

The consequence is that adoption is per *document* and never per *project*. A project can convert
nine documents out of ten and the tenth still resolves `kind` from its directory, silently, with
provenance `POSITION` — which is correct behaviour under today's design and exactly the behaviour the
captain's transition rule says should stop. There is also no way for the reader to report the gap: a
document that resolves by position is indistinguishable from one that has not been converted yet,
because it *is* one, and nothing marks the project as having claimed to be finished converting.

`ExaminationState` (§4 of the specification, `ExaminationState` in the module) is the only crossing
that exists today, and it is per-document and about a person's attention, not about a project's
regime. `NOT_EXAMINED` / `DECLINED` / `CLASSIFIED` answers "has anybody looked at this document",
not "does this project still let its folders speak."

### 3.2 The two tables, verbatim

`KIND_BY_DIRECTORY` maps, in the module's own order: `drafts`/`draft` → `draft`,
`proposals`/`proposal` → `proposal`, `plans`/`plan` → `plan`, `notes`/`note` → `note`, `adr`/`adrs` →
`adr`, `research` → `research`, `spec`/`specs` → `spec`, `templates`/`template` → `template`,
`memories`/`memory` → `memory`. Nine kinds.

`STATUS_BY_DIRECTORY` maps `done` → `done`, `templates` → `reusable`, `memories` → `reference`,
`notes` → `reference`. `HOLD_DIRECTORY` (`hold`) resolves to `active` with provenance explaining
that hold is not a distinct value. `DEFAULT_STATUS` is `active`.

### 3.3 The axes are crossed, and the diagnosis holds

Three of the nine kinds are not kinds. `draft`, `proposal` and `plan` describe where a document
stands in a life, not what sort of document it is. The test is whether a document can move between
them without being rewritten: a proposal that is approved becomes a plan, and this workspace's own
governing rule says so — `CLAUDE.md`, "a document in `plans/` has been evaluated and approved; one in
`proposals/` is under evaluation and is NOT approved. Weight follows the folder." Weight is status.
The same file, unedited, carries a different weight in a different folder. Those three are positions
in a life sitting in the kind table.

Two of the four statuses are not statuses. `templates/` → `reusable` and `memories/` → `reference`
describe what the document *is*: a template is reusable by nature and stays reusable for its whole
life, and a memory is reference by nature and does not stop being reference. Neither can change
without the document becoming a different sort of document. Those are kinds sitting in the status
table — and both directory names are *also* in the kind table, mapping to `template` and `memory`.

So the crossing is not a matter of interpretation; it is visible in the code as an overlap.
`templates`, `memories` and `notes` appear in both tables. A document in `notes/` resolves to
kind `note` and status `reference` from the same single directory name, which is the whole
mechanism showing its seam: one name, asked to answer two questions, answers both from one
position. Verified by running the reader on a real file — `packages/laces/docs/notes/index.md`
resolves `kind='note' [position] parent directory notes` and `status='reference' [position] parent
directory notes`.

The captain's diagnosis survives the test. A file sits in exactly one directory. A scheme read off
directory names therefore cannot separate two independent axes, because there is only one slot to
read. Given one slot, whoever wrote the tables had to put each folder's meaning *somewhere*, and the
folders that carry a life-position went into `kind` while the folders that carry a nature went into
`status` — each landing in whichever table the folder's *other* meaning was not already occupying.
The vocabulary is not confused about what kinds and statuses are; it is the shape a two-axis
vocabulary takes when it is read out of a one-axis medium. Front-matter has two slots and no such
constraint, which is precisely why supersession is the moment to fix it — and precisely why fixing
it cannot be done inside the directory tables.

Two further seams worth recording, both consequences of the same one-slot problem:

1. `archive` is the one suggested status in the specification's §3B.4 table with "none today" in the
   *directory that already implies it* column. Yet `archive/` is the most consistently present
   lifecycle directory in the workspaces (§4.3 — five of six repositories have one), and docstrap's
   response to it is `DEFAULT_EXCLUDE_DIRS = ("archive", "deprecated")` in `config.py`, which drops
   those documents from the built site entirely. The one status with no directory is the one
   directory everybody has, and it is currently handled by exclusion rather than by status.
2. `research` is in the kind table with no plural alternative, while `adr` and `adrs`, `spec` and
   `specs`, and every lifecycle name have both forms. That is a small inconsistency, but it is the
   kind of inconsistency a hand-maintained directory-name table accumulates and a field cannot.

### 3.4 A third vocabulary, in the database, agreeing with neither

`metadata.VALID_STATUSES` is `{"draft", "proposal", "spec", "plan", "active", "archived"}`, closed
and enforced on write (`metadata.py`, and `docs/docstrap_on_2026-09-01.md` §5 which specifies it).
The strapdance status vocabulary is open, and its suggested values are `active`, `done`, `archive`,
`reusable`, `reference`.

Line the three up and the disagreement is structural, not cosmetic:

| value | in `KIND_BY_DIRECTORY` | in strapdance status | in `metadata.VALID_STATUSES` |
|---|---|---|---|
| `draft` | yes, as a kind | no | yes, as a status |
| `proposal` | yes, as a kind | no | yes, as a status |
| `plan` | yes, as a kind | no | yes, as a status |
| `spec` | yes, as a kind | no | yes, as a status |
| `active` | no | yes (default) | yes |
| `done` | no | yes | no |
| `archive` / `archived` | no | `archive`, suggested | `archived` |
| `reusable` | no (`template` is the kind) | yes | no |
| `reference` | no (`memory`, `note` are the kinds) | yes | no |

The database calls `draft`, `proposal`, `spec` and `plan` statuses. The chain calls the same four
words kinds. Both are reading the same folders. The database's position is the one that matches the
`CLAUDE.md` folder rule quoted in §3.3 — which suggests the crossing in §3.3 is not a coin-flip but a
provable misfiling, since the workspace's own governing rule and the workspace's own database both
treat those four as lifecycle. `docs/docstrap_on_2026-09-01.md` §5.1 records that nothing reconciles the
two vocabularies and declines to decide which is authoritative; that open question (§5.1's, carried
as `Q2` in that document) is upstream of this note and is not re-asked here. What this note adds is
that the disagreement is not merely *unreconciled* — the two vocabularies file the same four words
under different axes, so reconciling them means choosing an axis, not choosing a winner.

### 3.5 What the reader does to documents that already carry front-matter for other reasons

Two behaviours interact in a way that matters for the transition. `BARE_COMPAT_FIELDS` lets the
reader take `title`, `kind`, `status`, `project` and four others from *un-namespaced* top-level keys.
`_examination_state` computes state from the `strapdance` namespace alone. So a document with a bare
`status:` key is `NOT_EXAMINED` and simultaneously has an `EXPLICIT` status.

This is observable in the workspace right now, not hypothetically. `packages/laces/docs/research/`
notes carry a front-matter convention of their own — `research:`, `title:`, `status: Open` — written
for the LACES research index, predating strapdance and meaning something else. Running the reader on
`packages/laces/docs/research/0001-schema-evolution.md` yields:

```
kind     = 'research'      [position] parent directory `research`
status   = 'Open'          [explicit] bare key `status` (compatibility)
project  = 'packages__laces'
state:   not_examined
```

`Open` is not in the strapdance suggestions and not in `metadata.VALID_STATUSES`. Nothing is wrong by
any single rule — the status vocabulary is deliberately open, and §3A.4 says bare keys are read for
compatibility — but the composite result is that nine of the eleven files in that one directory have
an explicit lifecycle status that no lifecycle vocabulary recognises, taken from a field that meant
"is this research thread still being worked on". This note's own front-matter follows that same
convention, so this file resolves the same way; it is left as-is deliberately, because §3 of this
note is about what the code does and an example in the tree is worth more than a description.

The transition rule interacts with this directly: if adopting front-matter means "directories no
longer speak for this project", then a project full of documents whose front-matter belongs to a
*different* namespace has adopted nothing, and the reader cannot currently tell the difference.

### 3.6 The one page the kind table cannot classify

`packages/docstrap/docs/strapdance-front-matter.md` (retired on 2026-11-20) — the hand-written page that defines the kind
vocabulary — sits directly in `docs/` and resolves to `kind = None [unknown] parent directory docs
maps to no known kind; not guessed`. The document that defines classification by directory cannot be
classified by directory, because it is not filed in one of the nine. That is not a defect; it is the
coverage limit of §4 measured on a sample of one, and §4.4 measures it on 581.

## 4 What the repositories actually look like

### 4.1 Method

Six repositories under `/home/johnh/firstmate/projects/` were read directly on 2026-09-01:
`platformshoes`, `rlp`, `trk_tdp`, `dkp`, `formizer`, `ronin-ledger`. Nothing was generalised
from platformshoes. For each: every directory named `docs` at any depth (excluding `.git`,
`node_modules`, `.venv`, and any path under `tests/fixtures/`) was located; every `*.md` beneath each
was counted; every `.docstrap` within three levels was read; every symlink in the top two levels was
resolved. "Kind-mapped" means the markdown file's immediate parent directory name, lower-cased, is a
key in `KIND_BY_DIRECTORY`. Test fixtures are excluded throughout: `packages/docstrap/tests/fixtures`
contains six further `docs/` trees holding 27 markdown files, and counting docstrap's own test data
as documentation would inflate `platformshoes` by a quarter.

### 4.2 The survey

| Repository | Root `docs/`? | Root-`docs/` md | Member `docs/` dirs | Member md | `.docstrap`? | What it declares | Member `docs/` undeclared | Loose md at repo root | Site config |
|---|---|---|---|---|---|---|---|---|---|
| `platformshoes` | yes, no loose files | 29 | 13 (`packages/*`, `apps/*`, `winrun`) | 84 | yes, workspace mode | 4 projects + 2 `related_directories` (`docs`, `winrun`) | 8 of 13 | 5 | none (built via `docs-site/`) |
| `rlp` | yes, 3 loose | 22 | 4 (`apps/*`) | 7 | **no** | — | 4 of 4 | 2 | none |
| `trk_tdp` | yes, 3 loose | 88 | 4 (`apps/*`) | 24 | yes, workspace mode | 4 projects + 1 `related_directory` (`docs`) | 0 of 4 | 3 | none |
| `dkp` | yes, 1 loose | 100 | 1 (`rl_deployment/docs`) | 3 | **no** | — | 1 of 1 | 2 | none |
| `formizer` | yes, 3 loose, has `index.md` | 116 | 0 | 0 | **no** | — | — | 3 | `mkdocs.yml` |
| `ronin-ledger` | yes, **15 loose** | 81 | 0 | 0 | **no** | — | — | 4 | none |

Immediate subdirectories of each root `docs/`, verbatim, because the spread is the finding:

| Repository | Subdirectories of `docs/` | of which named in either table |
|---|---|---|
| `platformshoes` | `archive`, `biz_ideas`, `notes`, `pitches`, `plans`, `proposals` | 3 of 6 |
| `rlp` | `adr`, `archive`, `plans`, `proposal`, `research` | 4 of 5 |
| `trk_tdp` | `adr`, `data-findings`, `domain`, `images`, `math`, `notes`, `portal`, `projects`, `proposals`, `swatches`, `tdp_web`, `time_line` | 3 of 12 |
| `dkp` | `adr`, `archive`, `changes`, `client_deployment`, `hosted_apps`, `logs`, `misc`, `notes`, `plans`, `research`, `specs` | 5 of 11 |
| `formizer` | `archive`, `design`, `external`, `plans`, `research`, `review`, `specification` | 2 of 7 |
| `ronin-ledger` | `STOP_NO_ACTION_NOTES_ONLY`, `adr`, `archive`, `client_deployment`, `eval`, `guides`, `notes`, `plans`, `proposals`, `verification_db` | 4 of 10 |

Per-member layout inside `platformshoes`, the only repository with enough members to show a pattern —
and it shows there is not one:

| Member | Contents of its `docs/` |
|---|---|
| `packages/laces` | `adr/ notes/ plans/ research/ spec/` — five lifecycle-and-kind directories |
| `packages/object-brewer` | `README.md concept/ examples/ notes/ research/ spec/` |
| `packages/docstrap` | flat: four `.md` pages + `notes/` (this directory is the fifth thing in it) |
| `packages/dev-project-organizer` | `proposals/` only |
| `winrun` | `index.md proposals/` |
| `packages/git_id`, `packages/repo-migrations`, `packages/object-brewer-ui`, `apps/laces-desktop`, `apps/ccpane`, `apps/pd`, `apps/charmoji` | a single generated `index.md` each |
| `apps/devphase` | a single `devphase_spec.md`, no `index.md` |

### 4.3 What the survey shows

Six repositories, six distinct layouts. No two of the six agree on the combination of (root `docs/`
shape, per-member `docs/`, `.docstrap` presence, site config):

1. `platformshoes` — workspace, root `docs/` kept clean of loose files, thirteen member `docs/`
   directories of which eight are undeclared, built through a hand-maintained `docs-site/`.
2. `trk_tdp` — workspace, all four member `docs/` declared, root `docs/` with the widest subdirectory
   spread of any repository (twelve, of which three are recognised).
3. `rlp` — workspace shape with `apps/` and `packages/`, four member `docs/` directories, and no
   `.docstrap` at all, so docstrap sees none of it.
4. `dkp` — single-`src/` project, no `.docstrap`, a hundred markdown files in a root `docs/`
   with its own `DOC_RULES.yaml`, and one member `docs/` hanging off a deployment subdirectory.
5. `formizer` — single-`src/` project with its own `mkdocs.yml` and a `docs/index.md`, so it is
   already a published documentation site by a different mechanism.
6. `ronin-ledger` — no `apps/` or `packages/` containers, no `.docstrap`, fifteen markdown files
   loose at the top of `docs/`, four more loose at the repo root, and a directory named
   `STOP_NO_ACTION_NOTES_ONLY` which is an instruction to agents encoded as a folder name — the
   clearest single illustration in the survey of directories being used to carry meaning no
   vocabulary anticipates.

Two of six repositories have a `.docstrap`. Of the twenty-two member `docs/` directories across the
six, thirteen are undeclared: five because the repository has no `.docstrap` at all (`rlp` four,
`dkp` one) and eight because `platformshoes`'s `.docstrap` does not list them. Five of six
repositories have `docs/archive/`; `trk_tdp` is the exception.

### 4.4 Coverage of the directory scheme, measured

Across all 554 markdown files in all `docs/` trees of the six repositories, 248 (45%) sit in a
directory whose name is a key in `KIND_BY_DIRECTORY`. The other 306 resolve `kind` to an explicit
unknown. Per repository:

| Repository | md in `docs/` trees | kind-mapped by directory | share |
|---|---|---|---|
| `platformshoes` | 113 | 74 | 65% |
| `rlp` | 29 | 19 | 66% |
| `trk_tdp` | 112 | 51 | 46% |
| `dkp` | 103 | 47 | 46% |
| `formizer` | 116 | 37 | 32% |
| `ronin-ledger` | 81 | 20 | 25% |
| **total** | **554** | **248** | **45%** |

Fifty-six distinct directory names hold markdown across the six root `docs/` trees. Seven of them are
in `KIND_BY_DIRECTORY` — `adr`, `notes`, `plans`, `proposal`, `proposals`, `research`, `specs`. The
other forty-nine names carry whatever their author meant and the chain reads none of it. Sixty-six
of the 554 files (12%) sit in a directory named in *both* tables (`notes`, `templates`, `memories`),
which is the §3.3 overlap counted rather than argued.

The number that bears on the transition rule is 45%. The fallback chain was justified by §2.2 —
existing repositories "already carry the metadata in their directory names" — and on the captain's
actual repositories it carries it for slightly under half of the documents. That does not make the
chain wrong; being right 45% of the time for free, with honest `UNKNOWN` for the rest, is a good
trade for arrival. It does mean the directory scheme is not a fallback that a project can be assumed
to be resting on comfortably before it converts, and the two repositories with the highest coverage
(`platformshoes`, `rlp` at 65%) are the two whose documentation is most recently organised. The
coverage is a measure of recent tidying, not of a durable convention.

## 5 The options, weighed against that evidence

### 5.1 What directories are for after supersession

The question the captain posed — what are directories FOR once they no longer carry status and kind —
has at least these answers visible in the survey, and they are not mutually exclusive.

1. **Nothing but shelving.** Directories become arbitrary, chosen for browsing comfort, and carry no
   machine meaning at all. §4.4 says this costs the 45%, all at once, for every unconverted document.
2. **Scope, not classification.** A directory says *whose* documents these are, never *what* they
   are. This is what `.docstrap` `projects[].path` and `docs_root` already do, and what
   `_resolve_project` already reads. Under this answer the kind and status tables go away and the
   project chain stays, which is a clean split because `project` is the one field whose §3B.2 chain
   the specification already defends as genuinely positional.
3. **Exclusion and visibility.** Directories continue to control what is built and shown —
   `exclude_dirs` (`archive`, `deprecated`), `exclude_file_suffixes`, `ignore`. This meaning is
   already separate from kind and status, already lives in `config.py` rather than in the chain, and
   the §3.3(1) `archive` seam suggests it is doing lifecycle work in disguise.
4. **A default for new documents.** A directory suggests front-matter to write rather than being read
   as front-matter — which respects §3B.4B ("suggestion is never storage") and would make
   `KIND_BY_DIRECTORY` an authoring aid instead of a resolution step.

Answers 2, 3 and 4 can all be true at once and are all consistent with "the old directories are no
longer used for that project", because none of them is *resolution*. The note does not pick.

### 5.2 How a project would declare it has crossed over

Three places could hold the declaration, each already existing:

1. **The `.docstrap` file**, alongside `layout`, `docs_root` and `exclude_dirs`. It is per-project by
   construction, `_resolve_docstrap_project` already finds the nearest one for any document, and
   `config.py` already parses it. Cost: `read_context` currently resolves without loading project
   config for `kind` and `status`, and four of six surveyed repositories have no `.docstrap` at all,
   so the declaration would be unavailable exactly where the directories are least tidy.
2. **A per-directory marker document**, the way `index.md` already marks a user-authored section
   page. Cost: it is a new file convention in a note whose subject is that there are too many.
3. **The metadata database**, which already holds per-document status and path history. Cost: the
   reader is deliberately file-only and stateless; making resolution depend on a database would
   break "one implementation, two runtimes" in a way §4 of the specification exists to prevent.

There is a fourth possibility that needs no declaration at all: make the transition per-document and
strict, so that a document carrying *any* `strapdance` namespace resolves only from front-matter and
never from position, and count a project as crossed when every document in it is `CLASSIFIED` or
`DECLINED`. That is attractive because `ExaminationState` already computes exactly that per document
and `docstrap doctor` already walks projects. It is unattractive because it makes conversion
all-or-nothing per file — a document declaring only `relates_to` would lose its directory-derived
kind — and because §3.5 shows that "carries a `strapdance` namespace" and "carries front-matter" are
not the same thing in this workspace.

### 5.3 `docs/<project>` as a real directory

Under this option the workspace root grows `docs/<project>/` for each member and the member's own
`docs/` goes away or becomes the same place.

What the survey says for it: a single tree is the shape most repositories are closest to already.
Four of six have no member `docs/` worth speaking of (`formizer` and `ronin-ledger` have none,
`dkp` has one, `rlp` has four holding seven files between them). Eight of the thirteen
`platformshoes` member `docs/` directories hold exactly one file, and seven of those eight files are
a generated `index.md`. Consolidating those costs almost nothing because they contain almost
nothing.

What the survey says against it: the two members that hold real documentation — `packages/laces` at
45 files with five subdirectories, `packages/object-brewer` at 19 — are the two where documentation
lives next to the code it describes, and both are packages that could plausibly be extracted to their
own repository, at which point their documentation should travel with them. Moving them to
`docs/laces/` puts the documentation on the workspace's side of a boundary the package might later
cross. It also collides with `formizer`, where `mkdocs.yml` and `docs/index.md` already claim
`docs/` for a different tool.

### 5.4 `docs/<project>` as a symlink into `apps/` or `packages/`

Under this option `docs/<project>` is a symlink to `packages/<project>/docs`, so documentation stays
with its code and the workspace still gets one place to look.

The precedent is observable rather than hypothetical, and there are two instances of it in this
workspace, pointing in opposite directions.

The first is `platformshoes/docs-site/`, which is exactly this design, already built and already
committed: `laces-docs -> ../packages/laces/docs`, `object-brewer-docs ->
../packages/object-brewer/docs`, `workspace-docs -> ../docs`, plus two single-file symlinks
(`object-brewer-readme.md -> ../packages/object-brewer/README.md`). Three observable costs come with
it. The naming is `<project>-docs`, not `<project>`, because the symlink shares a directory with real
directories of the same names (`laces/`, `object-brewer/`, `formizer/` all exist beside their
`-docs` links) — so the flat namespace forced a suffix. The set is hand-maintained and has drifted:
`docs-site/` links two member `docs/` trees, the workspace `docs/`, and one tree from outside the
repository, while `.docstrap` declares four projects and thirteen member `docs/` directories actually
exist — three different subsets of the same workspace, none of them derived from another. And that
outside link, `formizer-docs -> ../../formizer/docs`, escapes the repository into a sibling checkout,
so it resolves on this machine and nowhere else.

The second is the promdance project-side view, specified in `docs/docstrap_on_2026-09-01.md` §8(2) as "a
symlink to the canonical location" created by `ensure_promdance`, which "never overwrites: a real
directory, or a symlink pointing somewhere else, is left exactly as found." In the four surveyed
repositories that have a `promdance/` entry — `platformshoes`, `rlp`, `dkp`, `ronin-ledger` —
the entry is a plain directory in all four. Zero of four are the specified symlink. The
never-overwrite rule is correct and protective, and the observable consequence is that a
symlink-based layout does not converge on its own: where something was already there, the design
simply does not apply, permanently and silently, and nothing reports the divergence.

That is the real cost to weigh, and it is not "symlinks are fragile on Windows" (though `winrun/`
exists in this workspace, so that is live too). It is that a symlink layout has to be *established*
by a tool that is allowed to replace what it finds, and every safety rule that makes such a tool
acceptable also makes it decline to converge.

### 5.5 The third option the survey suggests and nobody named

Neither option addresses the thing the survey actually measures. Four of six repositories have no
`.docstrap`, and in `platformshoes` eight of thirteen member `docs/` directories are undeclared. The
inconsistency is not primarily in *where the directories are* — it is that nothing declares them, so
docstrap sees a hand-written subset. `.docstrap` already has the vocabulary for either physical
layout (`path`, `docs_root`, `related_directories`), which means both §5.3 and §5.4 are questions
about the filesystem while the measured gap is a question about declaration. A generated declaration
would also match §6.2 of the specification, which already says a per-collection index, if wanted, is
generated from the documents and never hand-maintained — a rule `docs-site/` currently violates.

## 6 Open questions

Numbered so `docstrap questions` finds them; the enumeration is deliberately separate from the
section numbers above. None of these is answered here.

**Q1.** Should a project declare that it has crossed over to front-matter — in its `.docstrap`, as
§5.2(1) sketches — or should the crossing be inferred per document from the presence of a
`strapdance` namespace, as §5.2's fourth possibility sketches? The two differ in what happens to a
document that declares only `relates_to`: under a project-level declaration it loses its
directory-derived kind because the project crossed, and under per-document inference it loses it
because the document did.

**Q2.** After supersession, which of the four jobs in §5.1 do directories keep — shelving only,
scope, exclusion and visibility, or a suggested default for new documents? More than one can be
kept; the question is which, because the answer determines whether `KIND_BY_DIRECTORY` is deleted,
demoted to an authoring suggestion, or left in place for unconverted projects only.

**Q3.** `draft`, `proposal` and `plan` are in the kind table but the workspace's own folder rule and
`metadata.VALID_STATUSES` both treat them as lifecycle (§3.3, §3.4). Are they statuses that were
misfiled as kinds, and if so, what is the *kind* of a document currently sitting in `plans/` — is
there one, or is `kind` simply unknown for most of the captain's documents?

**Q4.** `templates/` → `reusable` and `memories/` → `reference` are in the status table but describe
what a document permanently is (§3.3). Are `template` and `memory` the kinds and `reusable` and
`reference` redundant, or is `reference` a real lifecycle state that a document can enter and leave —
a plan that is finished with but kept to consult, for instance?

**Q5.** `archive` is the one suggested status with no directory in the specification's table, yet
five of six repositories have `docs/archive/` and docstrap handles it by excluding it from the build
(§3.3(1)). Should `archive/` imply a status rather than an exclusion, and does that change what
`exclude_dirs` means?

**Q6.** Nine of the eleven files in `packages/laces/docs/research/` carry a bare `status:` from a
different, older convention, which the reader takes as an explicit strapdance status of `Open` while
still reporting the document as `not_examined` (§3.5). Is a bare key from a foreign convention
supposed to win the field, or should the compatibility read in `BARE_COMPAT_FIELDS` be narrowed once
a project has crossed over?

**Q7.** Should `docs/<project>` be a real directory (§5.3) or a symlink into `apps/`/`packages/`
(§5.4)? The survey's bearing on it: eight of thirteen `platformshoes` member `docs/` directories hold
one file and would consolidate for free, while the two that hold real documentation are the two most
likely to be extracted to their own repositories.

**Q8.** Zero of the four existing `promdance/` entries are the symlink the specification calls for,
because `ensure_promdance` correctly refuses to replace what it finds (§5.4). If `docs/<project>`
becomes a symlink layout, is docstrap permitted to establish it over existing real directories, and
if not, what reports the divergence?

**Q9.** Is the inconsistency to be fixed physically or declaratively? Four of six repositories have
no `.docstrap` and thirteen of twenty-two member `docs/` directories are undeclared (§4.3), so a
uniform filesystem layout and a uniform declaration are different projects with different costs. Is
the goal that every workspace *looks* the same on disk, or that docstrap *sees* all of every
workspace?

**Q10.** `formizer` already publishes through its own `mkdocs.yml` with a `docs/index.md`, and
`dkp` carries its own `docs/DOC_RULES.yaml`. Are these repositories in scope for a uniform
filing system at all, or are they out of scope until they adopt `.docstrap`?
