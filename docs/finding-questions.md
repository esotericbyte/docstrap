# Finding the questions a document poses

`docstrap questions` lists the open questions in a document. It finds them by reading the author's
own numbering — `Q1`, `Q2`, `Q3` — and by nothing else.

## 1 Why the numbering, and not the question marks

A question mark is not a question posed to a reader. Across the 222 markdown documents in this
workspace there are 206 lines carrying one, and the great majority are not asking the reader
anything:

1. A heading phrased as a question that the section below it answers.
2. A question asked and answered in the very next sentence — `…which documents does no project
   actually own? It reports them, …`.
3. A question inside a quotation. Every proposal here opens with the captain's own prompt quoted
   verbatim, questions included; those are the questions that *caused* the document.
4. A question inside a code block or an example — including examples of the question convention
   itself.
5. A "why does this matter?" transition.
6. An FAQ entry with its answer directly beneath it.
7. A list of the questions a *product* will answer, introduced by "…can answer questions like:".
8. Notation: `project_id?` for an optional field, `?key=value` in a URL, `"??"` in a git status.

Separating those from the real thing by analysing the prose is possible but never certain, and an
uncertain list is worse than a short one: a list polluted with rhetorical hits is not trusted twice.

The numbering sidesteps the whole problem. It is an established convention in this workspace —
questions get their own enumeration, `Q1` `Q2` `Q3`, deliberately separate from section numbering so
a question is never confused with a section — and an author who wrote `Q1.` has already done the
classification by hand. The detector is therefore deterministic. There is nothing in it to tune and
nothing to argue with, which is the point.

## 2 The three rules

These are the whole specification. They live in `packages/docstrap/src/docstrap/questions.py`.

1. **A question is a block whose first line opens with a `Q<n>` label.** The label may be emphasised
   (`**Q1.**`), carried on a bullet (`- **Q1.**`), or carried on a task-list item (`- [ ] **Q1.**`).
   The separator after the number is `.`, `:`, or `)`, and at least one space follows it. The item
   runs to the next blank line, so a question wrapped over four lines is one question — and an item
   holding four question marks is still one question, because it is one thing a reader answers.
2. **Labels inside fenced code, blockquotes, front-matter, and headings do not count.** Nor does a
   `Q3` mentioned mid-sentence: the label has to open the block.
3. **The questions are the ones at the end.** Items whose numbers ascend by one form a run, and the
   *last* run in the document is what is returned. A document that was revised in place and carries
   a superseded `Q1…Q3` above its current set reports only the current set; the superseded run stays
   available on `DocumentQuestions.all_labelled`. A section after the run — `## 9 Risks` — does not
   hide it.

## 3 What this deliberately does not do

It does not find an unlabelled question in the prose, however genuine. `docs-site/_session-status.md`
poses two real open decisions as `###`-level headings with no `Q` label, and this finder reports
neither. That is the accepted cost of rule 2 and of having no false positives at all.

It also does not judge whether a labelled question is still open. `Q2. **Data-repo name.**
*Resolved: `wt2go-data`.*` is reported like any other, because deciding otherwise would be a guess.
The item's text is returned in full, so the resolution marker is visible to whoever reads the list.

A general classifier over the prose could be added later without disturbing any of this — it would
be a second source of candidates, not a change to these rules.

## 4 The result belongs to one project

A question run is scoped to a project, and never to the library. Pointed at a directory, the command
resolves the one project that owns it and reads that project's documents — not the directory's files.

### 4.1 How the project is resolved

`docstrap.projectscope.resolve` walks up for the nearest `.docstrap` and enumerates what it declares
with `docstrap.scan.scan` — the same enumeration the build uses, so the documents read here are the
documents the site would publish. A path inside a project resolves to that project, the deepest one
when projects nest. A directory holding exactly one project resolves to it too, since the context is
still unambiguous. A related directory is its own context like any project.

Two cases raise rather than answer. A path holding *several* projects — a workspace root is the
ordinary one — has no single project context, and reporting across all of them at once is precisely
the library-wide behaviour this scoping removes; the command lists the projects and asks for one. A
path no project declares has no context either, and saying so is more useful than walking it as if a
directory were a project.

### 4.2 What the scope excludes

The project's own declarations decide, which is the substance of the change: a directory walk
honoured none of them.

1. **`docs_root`.** A project's documents are the ones under the directory it declares, plus its
   README when it keeps one outside that directory — the two sources `docstrap.scan` already names.
   A markdown file elsewhere in the repository is not one of the project's documents.
2. **`exclude_dirs`.** A directory the config excludes is pruned whole, at any depth. `archive/` and
   `deprecated/` are the defaults; a config naming others gets those instead.
3. **`ignore: true`.** A subtree carrying its own `.docstrap` with an ignore declaration is pruned
   whole. That is how a vendored or borrowed directory, or a firstmate home, says it is not part of
   the project around it.
4. **Drafts, vendored and build trees.** Anything under a `promdance/` path, plus the directories
   `docstrap.projectfinder.SKIP_DIRS` names, and any hidden directory.

There is no index and no store behind any of this. Questions live in the documents and are read when
somebody asks; a listing is a scan, and anything a build emits from one is derived and disposable.

## 5 Running it

```bash
docstrap questions packages/laces         # one project, resolved from .docstrap
docstrap questions docs/proposals         # one subtree of one project
docstrap questions docs/proposals/x.md    # one document
docstrap questions packages/laces --json  # machine-readable
docstrap questions packages/laces --all   # include superseded runs
```

Pointing at a single document reads that document and asks nothing about projects — naming a file is
already unambiguous about what is wanted.

## 6 What it finds in this workspace

As of 2026-09-01, run once per project over this workspace:

| project | documents that pose questions | questions found |
|---|---|---|
| `docs` (workspace-level docs) | 10 | 66 |
| `packages__laces` | 2 | 9 |
| `winrun` | 1 | 3 |
| `packages__docstrap` | 0 | 0 |
| `packages__object-brewer` | 0 | 0 |
| `apps__laces-desktop` | 0 | 0 |
| **total** | **13** | **78** |

The unscoped walk this replaced reports 96 questions across 17 documents over the same tree today —
it was 85 across 15 before the two governing documents took their own `Q1…Qn` sections. The 18 that
no longer appear are not misses; each was outside some project's declared boundary. Twelve are in
`docs/proposals/archive/`, which `exclude_dirs` excludes. Four are in `apps/devphase` and two in
`llm-tune/`, directories no `.docstrap` declares as a project — those now resolve to no context
rather than being folded into a library-wide pile. This tool's own test fixtures were being walked
too, and are outside `packages/docstrap`'s `docs_root`.

The detector's precision is unchanged, because the detector is unchanged: an independent `grep -E`
for the label shapes over each project's documents returns the same lines the command does. Because
the rule is the label and the label is unambiguous, precision and recall against the convention are
both exact by construction. The honest caveat is that the *convention* is what is being measured — a
question the author never numbered is invisible to this tool, by design (§3).
