# Clearing the docstrap decision backlog

Status: PROPOSAL, 2026-09-30. Under evaluation and NOT approved — the folder says so.

Twenty-one rulings on the questions three docstrap holds put to the captain, decided here by reasoning
against the code rather than parked for him. **Every ruling below is a recommendation he may overturn.**
Nothing in this document has been written into `docs/docstrap_on_2026-09-01.md` or into
`docs/proposals/0002-the-upgrade-path.md`, because an open question in those documents is answered by
the captain and never by an agent writing an answer into them. This file is the separate place the
reasoning can live without pretending to be his decision.

---

## Contents

1. [What this is, and the one rule it obeys](#s1)
2. [Method](#s2)
3. [The enumeration, and why it is not eighteen](#s3)
4. [Summary table](#s4)
5. [The Q&A surface rulings — `docstrap-qa-survey-h21`](#s5)
6. [The specification rulings — `docstrap-spec-questions-h98`](#s6)
7. [The upgrade-path rulings — `docstrap-upgrade-rulings-h99`](#s7)
8. [Classification, and the shape of what was left](#s8)
9. [Work implied, to be filed](#s9)
10. [Findings about the questions themselves](#s10)
11. [Open questions](#open-questions)

---

(s1)=
## §1 What this is, and the one rule it obeys

Three captain holds carry questions that earlier docstrap work could not settle: the Q&A surface survey
(`docstrap-qa-survey-h21`), the specification's own open questions (`docstrap-spec-questions-h98`), and
the upgrade-path plan's (`docstrap-upgrade-rulings-h99`). They had been waiting as a block. This document
rules on all of them.

The one rule it obeys is the project's: **an open question is answered by the captain, never by an agent
writing an answer into a document.** So `docs/docstrap_on_2026-09-01.md` Q3 still reads as an open question in `docs/docstrap_on_2026-09-01.md`,
and `0002-the-upgrade-path.md` Q6 still reads as an open one there. What changed is that each now has a
reasoned recommendation, with its evidence and its falsifier, in a document he can accept, amend or reject
in one pass instead of twenty-one.

A ruling here becomes his answer only when he says so. The mechanism for that already exists and is not
this file: `fm-captain-hold.sh answer` records his exact words, and the corpus convention writes the
resolution into the question's own item, keeping its label and its number (`docs/docstrap_on_2026-09-01.md` §8.1.1, and the
note above its Q1).

(s2)=
## §2 Method

Each ruling follows the same five steps, in this order. The question exactly as it was posed, quoted and
cited. Each live option with the strongest case for it, including the one being rejected. Then an attack on
the preferred answer — what breaks it, what it costs, what would have to be true for it to be wrong. Then
the ruling and the evidence that decided it. Then the falsifier: the observation that would reverse it.

Everything is grounded in measured reality, and where a document and the code disagree the code wins and
the disagreement is recorded as a finding. That mattered more than expected: §10 lists eleven places where
a governing document describes a state the repository no longer has, including two where the question's own
premise is now false.

Three things were run rather than read, all with `HOME` and the XDG directories redirected into task scratch
so nothing touched the captain's live state. The full docstrap suite (469 tests). A complete build of all six
projects the root `.docstrap` declares, with `sphinx-build`'s stderr captured — the build counts warnings and
throws the text away, so a wrapper kept it. And the four commands `0002`'s Q2 names, each against an empty
throwaway home, to see which of them creates a database at all.

The live databases and the promdance store were read read-only and were not modified. `metadata.db` held 78
document rows and 522 file-index rows before this work and holds 78 and 522 after it.

(s3)=
## §3 The enumeration, and why it is not eighteen

The task named eighteen rulings: three from h21, eight from h98, seven from h99. Enumerated exactly against
the holds and the documents they came from, the real figures are different in both directions, and the
difference is itself a finding.

**h21 carries four questions, not three.** `data/docstrap-qa-survey-h21/report.md` §11 poses Q1 through Q4
with hold keys `question-source`, `answer-store`, `editor-reuse` and `mvp-phase`. The task named the last
three. `question-source` — whether questions stay authored as inline directives with a build-time index — is
ruled at §5.1 below.

**h98 carries thirteen labelled questions, and the hold is right where a later audit said it was wrong.**
`docs/docstrap_on_2026-09-01.md` has `**Q1.**` through `**Q13.**` at lines 1730–1824. The hold body's claim of "THIRTEEN
questions" was contradicted on 2026-09-17 by `data/hold-reconcile-h104/report.md` §4.3.12, which found eight
and reported that Q9 through Q13 "do not exist in that file, or anywhere else in his tree." That audit was
accurate when written and was overtaken the same day: commit `97292f3`, dated 2026-09-17, is what added
Q9–Q13. The hold caught up and the audit of the hold did not.

**Three of those thirteen are already answered, in the file, by the captain.** Q1 carries "Answered
2026-09-07 — it moves", Q2 carries "Answered by the captain on 2026-08-28 … one shared vocabulary", and Q4
carries "Answered 2026-09-07 — it is Annotorious's store." They are not ruled here; re-ruling a question the
captain has settled is the opposite of the job. They are used as evidence, and Q2's and Q4's answers turn out
to decide two other questions outright.

So the arithmetic is 4 + 13 + 7 = 24 labelled items, of which 3 are already his, leaving **21 live rulings**.
All 21 are ruled below.

(s4)=
## §4 Summary table

Confidence is the strength of the evidence, not enthusiasm. **High** means the code or a run settles it and
a reasonable person reading the same evidence would land in the same place. **Medium** means the reasoning is
sound and the evidence is real but a different weighting of costs could defensibly go the other way.

| # | Question | Ruling | Conf. |
|---|---|---|---|
| §5.1 | h21 Q1 `question-source` — inline directives plus a build-time question index? | Neither branch. Questions stay authored in the document, found by `Q<n>` label, and there is **no index** — a per-request scan. Already shipped. | High |
| §5.2 | h21 Q2 `answer-store` — answers into a queryable store (the annotations DB)? | Moved, but not there. A keyed markdown store, `answers.md`, keyed on document id + `Q<n>`, superseding. The annotations DB was refused by the captain at spec Q4. | High |
| §5.3 | h21 Q3 `editor-reuse` — extract, vendor, or reimplement the laces editor? | A fourth option, already taken: **reimplemented in Svelte/TS with laces' ADRs cited, not adopted.** | High |
| §5.4 | h21 Q4 `mvp-phase` — does the three-panel mode enter the MVP or become Alpha 5? | Void. Both options name a vocabulary retired on 2026-09-01. The mode shipped 2026-09-14 in the `0.0.z` era. | High |
| §6.1 | spec Q3 — tag index, backlinks, cross-project linking, recent-updated feed still wanted? | Keep all four unbuilt. Not unwanted — unsupported: one tagged document exists and it was deleted, and cross-document links do not resolve yet. | Medium |
| §6.2 | spec Q5 — §11's CI/CD entry or `VERSIONING.md` §1? | `VERSIONING.md` §1 stands. Split the entry: headless runs survive as product, CI and release automation are out permanently. | High |
| §6.3 | spec Q6 — is §11's priority order still right? | Wrong question. **Stop ordering §11.** Sequencing belongs to the roadmap and nowhere else. | High |
| §6.4 | spec Q7 — remove the two empty store entries? | No, not as posed. Sixteen of 23 entries are empty, none is tracked, and `markdown-store` is **recreated by the suite today** — the question's premise is false. | High |
| §6.5 | spec Q8 — should `from_web/` be in the store's history? | It is not a draft, so it does not belong in a drafts store. Move it out rather than exclude it. One narrow preference flagged as Q1. | Medium |
| §6.6 | spec Q9 — delete `docs/notes/index.md` or keep it authored? | Delete it. It has already dropped a real document from the site, which is the failure the composed-index rule exists to prevent. | High |
| §6.7 | spec Q10 — declare those directories, or are they outside the site? | Outside, and declare nothing by hand. Roadmap §4.6 already owns this. Its counts are stale: 14 tracked, not 31. | Medium |
| §6.8 | spec Q11 — is a zero-byte marker acceptable permanently? | Yes. Verified: 23 markers, every one zero bytes, zero authored markdown in the build. | High |
| §6.9 | spec Q12 — `file_index` in the metadata store, or its own file? | Keep it there, and make its migration **drop-and-rebuild**, never a data migration. | Medium |
| §6.10 | spec Q13 — make relative cross-document links resolve in the build? | Yes, but that is the second fix. First **report warnings by code**: two real warnings are hiding in docstrap's own count right now. | High |
| §7.1 | upgrade Q1 — is the metadata set the one vocabulary? | Yes; §5.1 already said so. The three directory-derived values are not statuses — move them to the `kind` axis. `archive`/`archived` is a live near-miss. | Medium |
| §7.2 | upgrade Q2 — exempt the read-only commands from the version refusal? | No exemption needed. **None of the three named commands opens a database.** Proven by running them. | High |
| §7.3 | upgrade Q3 — should the derivative be a fix-plan script? | Its discipline, not its medium. A proposed file to diff, because this edits prose; `fix_plan` writes `git mv`s. | Medium |
| §7.4 | upgrade Q4 — should a schema change force a package bump? | No. Take the plan's own third option: record the package version as data. | High |
| §7.5 | upgrade Q5 — give `annotations.db` the same refuse-and-migrate treatment? | No. Recreate on mismatch. Its only row is a `smoketest` row from 2026-08-18. | High |
| §7.6 | upgrade Q6 — should the first upgrade clear the test rows? | Yes, and the predicate is mechanical — but only after §7.7, or they come back. It is 73 of 78 now, not 59 of 64. | High |
| §7.7 | upgrade Q7 — is a test writing to live user state a defect class worth a standing rule? | Yes, and make it autouse. All three persistent states are affected, two leaks are still live, and 469 tests pass fully redirected. | High |

(s5)=
## §5 The Q&A surface rulings — `docstrap-qa-survey-h21`

All four of these are settled by the same fact, and it is the largest single finding of this task: **the
survey is obsolete.** It is dated 2026-08-25 and measured the three-panel mode at "roughly 15% built", with
"no question list, no selection model, no read-back of answers, no panel layout, and no save-as-you-type",
and named write-only answers as "the single hardest blocker."

Every one of those was built between 2026-09-13 and 2026-09-14. `src/docstrap/tools/qapanels/` holds
`Panels.svelte`, `QuestionList.svelte`, `AnswerEditor.svelte`, `Reference.svelte` and `autosave.ts`; commit
`0859ddc` is "answers are readable over the API", `e3ebe42` is "an answer counts when a person presses
Finish", `05cde0d` is "a submitted answer may be revised, and the earlier one is kept", and `3c4db1f` is "the
Q&A panel is scoped deliberately, and defaults to the document."

So these four are not decided by my judgement. They were decided by implementation, five weeks ago, and the
hold simply never went back to look. What follows records what the decision turned out to be, because a hold
that is answered by shipped code still has to be closed by someone reading the code.

### §5.1 h21 Q1 — `question-source`

**The question, as posed** (`data/docstrap-qa-survey-h21/report.md` §11): "Do questions stay authored as
inline `docstrap-questions` directives, with docstrap indexing them at build time to populate the list
panel? Yes means the smallest change: keep the directive, add a build-time collector that emits a
per-project question index, and panel 1 reads that. No means questions move into a store and are authored
elsewhere, which is a larger change and orphans the existing directive."

**The case for yes (index at build time).** Panel 1 needs a list, and a list wants a source it can read
cheaply. A build already walks every document, so collecting `Q<n>` labels while it walks costs one pass
over bytes already in memory. An index also makes cross-project questions answerable, which a per-document
scan cannot do without opening every project.

**The case for no (questions move into a store).** If questions are rows, they get identity, ordering and
status for free, and the answer store can carry a foreign key instead of a text label. Every question-shaped
feature afterwards — a count, a filter, a "what is unanswered across everything" view — becomes a query
rather than a scan.

**The case for the third thing, which is what happened.** Neither. `docstrap.questions` reads `Q<n>` labels
from documents; `docstrap.pairing` puts questions beside answers; and the qapanels route says outright that
"the question listing is a **scan**, performed per request by `docstrap.pairing.pair` … It is derived and
disposable: nothing caches it and nothing treats it as authoritative." `pairing.py`'s own docstring: "**The
pairing introduces no index.**"

**Attacking it.** A per-request scan is O(project) on every panel open, and the cost grows with the corpus.
If the captain opens the project-wide view over twelve projects, that is twelve project scans per open with
no cache. The measured counterweight is the build's own indexing cost, recorded in `AGENTS.md`: indexing 100
documents costs 0.4% of the build that publishes them. Scanning is cheap enough that caching it would be the
premature optimisation, and the design says so explicitly rather than by omission. What would make this
wrong is a corpus large enough for a panel open to feel slow — not the present one.

**Ruling.** Neither branch. Questions stay authored in the document, the marker is the author's own `Q<n>`
label rather than the directive alone, and **there is no index of them anywhere** — the list is a scan
performed per request and thrown away. Decided by the code: `pairing.py`, `tools/qapanels/routes.py`, and
`docs/finding-questions.md`.

**What would reverse it.** A panel open that is perceptibly slow, or a feature that genuinely needs to ask a
question about questions without reading the documents — "how many unanswered questions across all twelve
projects" asked often enough to matter. Either turns the scan into an index.

### §5.2 h21 Q2 — `answer-store`

**The question, as posed** (§11): "Do answers move into a queryable store (the existing annotations DB)
rather than the append-only `_answers.md` file? Panel 2 needs load-current-answer and update-in-place; the
current file format supports neither. Yes means spec §2 and §7.2 change and the markdown file becomes a
derived export rather than the store of record. No means a parser has to be written over the markdown
format, and concurrent-append semantics have to be defined."

**The case for the annotations database.** It exists, it is complete, its schema is a W3C subset, and it has
a `creator` column and stable ids. Answers would get update-in-place for nothing, a real query surface, and
one less bespoke format. The survey's own recommendation leaned this way because the alternative was writing
a markdown parser.

**The case against, which the captain made himself.** `docs/docstrap_on_2026-09-01.md` Q4, answered 2026-09-07: the
annotations database "was built for that client" — Annotorious — and "answers to a document's questions do
not go there: they go to the keyed answer file of §8.1." The reason given is a modelling one rather than a
convenience one: `creator` models "whoever is reading a deployed site", while "an answer to a `Q<n>` is a
decision by whoever owns the document, not a reader's remark on it." Two different audiences, two different
things.

**What shipped, and it is a third option.** `src/docstrap/answers.py`: one file per project at
`<project-promdance>/answers.md`, YAML front-matter carrying the index and the body carrying the prose, keyed
on the metadata store's document id plus the question's own label — `01J9F4V4T4XW9A0RCM6QK2S8YZ:Q4`.
"**Writing a key twice supersedes.** The row is replaced and the body section rewritten in place. Nothing
appends, which is the defect this replaced." The read path exists: `GET /api/answers/{project}` and
`/api/answers/{project}/{doc_slug}`.

So both of the question's requirements — load-current-answer and update-in-place — are met, and neither
branch was taken. The markdown file is the store of record and it is keyed, which is the property the
question was really asking for. "Queryable" turned out to be separable from "a database".

**Attacking it.** A markdown file with a YAML index is a database with none of a database's guarantees: no
transactions, no concurrent-write safety, and a corrupted front-matter block loses the index for every answer
in the project at once. The document-id key depends on the metadata store, so an answer's key is only as
stable as a row in a database that currently holds 73 test rows out of 78. And "one file per project" means
every answer in a project shares a write lock that does not exist.

The counter is that the failure this design replaced was worse and was real: keying on a slug orphaned
submitted answers when `docs/proposals/docstrap.md` was promoted, and treating a question id as decorative
italic text stacked duplicate sections. Between a format with weak concurrency and a format that silently
loses answers, the first is the better failure. And the concurrency risk is bounded by the actual writer
population, which is one person and two code paths that both go through `answers.py`.

**Ruling.** Answers moved out of the append-only per-document file, and the store they moved into is keyed
markdown rather than a database — the annotations database specifically refused, by the captain, for reasons
of what it models. Decided on evidence: `answers.py`, `server.py`'s `/api/answers` routes, and spec Q4's
recorded answer.

**What would reverse it.** A second concurrent writer — a team bridge, a second person answering, the MCP
server writing answers — makes the missing write lock real rather than theoretical. `docs/notes/organization_2026_9_11.md`
shows the captain thinking about exactly that ("create a promdance bridge with a team to get feedback"), so
this falsifier is closer than the rest.

### §5.3 h21 Q3 — `editor-reuse`

**The question, as posed** (§11): "Is the answer editor built by extracting `Editor.svelte` into a shared
workspace package, by vendoring a copy into a new docstrap frontend, or by reimplementing the ADR-0013
behaviour in vanilla JS? My recommendation is vendor-now-extract-later (§6.3), but the three options have
materially different costs and the choice is his."

**The case for extracting.** One editor, one place, both surfaces get every future fix. It is the answer that
is still right in two years.

**The case for vendoring.** It is the cheapest thing that works and it defers the packaging question until
there is a second consumer to design for. The survey recommended it.

**The case for reimplementing in vanilla JS.** At the time, docstrap had no build step, no module system and
no component boundary — the survey measured that precisely — so importing a Svelte component meant
introducing frontend tooling to a Python package for one textarea.

**What shipped, and again it is not one of the three.** `src/docstrap/tools/qapanels/ui/autosave.ts` is
docstrap's own implementation, roughly ninety lines, in TypeScript, driving a Svelte component — and its
header states the model explicitly: "The BEHAVIOUR implemented here is laces', and it is CITED rather than
adopted. … They were written for laces and they are accepted there, so docstrap points at them and does not
restate them as decisions of its own. There is no docstrap ADR duplicating them, deliberately: one autosave
behaviour across the captain's surfaces, described in one place."

It then reproduces ADR-0013 clause by clause: event-driven not clock-driven, an 800 ms debounce named as a
tuned constant rather than a contract, Ctrl/Cmd+S flushing immediately, and a binary indicator whose absence
is the unsaved signal. The vanilla-JS constraint that made option three ugly was withdrawn — `docs/docstrap_on_2026-09-01.md`
§11 item 5 records why: it "was protecting portability to layouts that do not exist."

The distinction this draws is worth keeping. Sharing *code* couples two packages' release cycles; sharing a
*decision* couples nothing and still gets one behaviour across both surfaces. The question offered three
degrees of code-sharing and the answer was to share the decision instead.

**Attacking it.** Two implementations of one behaviour will drift, and the citation does not prevent it —
nothing fails if laces changes ADR-0013's threshold and docstrap's constant stays at 800. That is a real
cost and it is unmitigated: there is no test that reads the ADR. The counterweight is that the shared thing
is small (a debounce and an indicator rule) and the alternative — a workspace package dependency from a
Python distribution onto a Svelte library — is a large, permanent piece of build coupling for it. And
`docs/tools-and-instruments.md` §5.1 already shows the bundle cost of shared Svelte runtime work is a
declaration-surface decision rather than a build detail, which is exactly what extraction would have forced
early.

**Ruling.** Reimplemented, in TypeScript and Svelte rather than vanilla JS, with laces' two ADRs cited as the
governing decisions and no code shared. Decided on evidence: `autosave.ts`, `AnswerEditor.svelte`, and spec
§11 item 5's record of the vanilla-JS constraint being withdrawn.

**What would reverse it.** A third surface needing the same editor, which turns two implementations into
three and makes extraction pay. Or an observed drift between laces' behaviour and docstrap's that confuses
the captain using both.

### §5.4 h21 Q4 — `mvp-phase`

**The question, as posed** (§11): "Does the three-panel mode enter the MVP, or become Alpha 5 / post-MVP? It
is the spec's own §11 roadmap item 1 ('Editor SPA'), which MVP explicitly excluded. Pulling it forward is
legitimate but it is a scope change to a written plan, and it should be a decision rather than a drift."

**Why both options are unavailable.** Both name a vocabulary that has been retired, and retired by decision
rather than by drift. `docs/plans/docstrap-mvp.md` stopped existing on 2026-09-01; `docs/archive/superseded-2026-09-01.md`
is the record. `VERSIONING.md` §2.1: "'Alpha N' is retired as a version label. It may still appear in prose
as a historical fact … but it is never a status, never a version." `docs/docstrap_on_2026-09-01.md` line 9: "**This describes a
tool in use, not a specification being built toward.**" And `AGENTS.md`: "**Do not write anything that treats
the present state as pre-product**; 'MVP' is retired as a framing. … A phase number standing alone is never a
name."

So there is no MVP for the mode to enter, and no Alpha 5 for it to become.

**And the underlying scope question is moot too**, because the thing shipped. The mode exists at
`src/docstrap/tools/qapanels/`, it is reachable, and `docs/plans/0001-answer-loop.md` is the plan recorded as
carried out (commit `2f32227`). A question asking whether to schedule work that is finished has no live
branch.

**Attacking it.** Calling a question void can be a way of dodging it, so it is worth asking what real
decision was inside it. There was one: whether pulling an "Editor SPA"-adjacent feature forward ahead of the
written plan was legitimate. That is answerable and the answer is that it happened and was recorded as a plan
(`0001-answer-loop.md`) rather than as drift — which is precisely what the question asked for. The residue is
not a decision but a bookkeeping act: §11 item 3 still lists "Editor SPA — a full editor for content, not
just answers", and that entry is now narrower than it reads, because the answers half exists.

**Ruling.** Void as posed. The framing was retired on 2026-09-01 and the mode shipped on 2026-09-14 in the
`0.0.z` era, named by what it delivered rather than by a phase. Decided on evidence.

**What would reverse it.** Nothing about the mode. Only the captain reinstating phase labels as a planning
vocabulary, which `VERSIONING.md` §2.1 and `AGENTS.md` both currently forbid.

(s6)=
## §6 The specification rulings — `docstrap-spec-questions-h98`

### §6.1 spec Q3 — the aggregate affordances

**The question, as posed** (`docs/docstrap_on_2026-09-01.md` Q3): "Tag index, backlinks, cross-project cross-linking and a
recent-updated feed were expected from the aggregate module that was never adopted, and nothing replaced them
when docstrap grew its own aggregate. Are they still wanted?"

**The case for yes.** All four are ordinary documentation-site affordances, the aggregate they belong to
exists, and three of the four have their data already: `documents.tags` is a column, `updated_at` is a
column, and the build knows every document's path. Roadmap §4.3 keeps the item alive and scopes it correctly
as "aggregate-build work rather than tool work".

**The case for no.** Four features nobody has missed in the month since they were noticed missing is
evidence about how much they are wanted. Each adds surface to an aggregate page that currently does one thing
well.

**What the measurement says, and it reframes the question.** The live metadata store holds **one** document
with any tags at all. It is `/home/johnh/platformshoes/docs/plans/docstrap-mvp.md`, tagged
`["alpha2", "docstrap", "mvp"]` — a file deleted on 2026-09-01, carrying two terms from the retired phase
vocabulary. Of the five non-residue document rows, the other four have `tags: []`.

So a cross-project tag index today would index one tag set, belonging to a document that does not exist, in a
vocabulary that has been retired.

Backlinks and cross-project cross-linking are worse placed than that. A complete build of the six declared
projects emits **94 `myst.xref_missing` warnings** — cross-document links do not resolve *inside* a single
project's build today (§6.10). Cross-*project* linking is two steps past a thing that is currently broken.

**Attacking the ruling.** "No data yet" is a self-fulfilling argument: nobody tags documents because tags do
nothing, and tags do nothing because nobody tags documents. A tag index might be the thing that makes tagging
worth doing, and the measurement I am leaning on is a consequence of the feature's absence rather than
independent evidence against it. That is a fair objection and it is why this ruling is Medium rather than
High. What blunts it is that only four real documents are registered in the store at all — the bottleneck is
registration, not presentation, and a tag index over four documents would not change anyone's behaviour.

**Ruling.** Keep all four unbuilt, and record the reason as *unsupported* rather than *unwanted*. Two of the
four sit on a link-resolution layer that emits 94 unresolved-reference warnings per build, and the other two
sit on a registration layer holding four real documents and one stale tag set. Roadmap §4.3's framing stands;
what should change is the stated reason, from an open want to a named prerequisite.

**What would reverse it.** Documents actually carrying tags — say twenty real documents with tag sets someone
uses — or §6.10's link fix landing, which removes the objection for backlinks and cross-project linking in one
act.

### §6.2 spec Q5 — CI/CD against `VERSIONING.md`

**The question, as posed** (`docs/docstrap_on_2026-09-01.md` Q5): "§11 lists CI/CD integration as a roadmap item, while
`VERSIONING.md` §1 puts CI, a package index, publishing and release automation permanently out of scope for
this workspace. Which of the two statements stands?"

**The case for §11.** A spec's roadmap is where a tool records what it might become, and headless operation
is a genuine docstrap capability: building without a browser, publishing a built site to a static host. None
of that is about releasing a Python package.

**The case for `VERSIONING.md`.** It is a workspace-root governing document, and its wording is not a
preference but a decision: "Also out of scope, permanently and by decision: no CI, no package index, no
publishing, no release automation, no `CHANGELOG.md`." It gives a reason, too — there are no downstream
consumers, so each would be a second thing to keep true.

**Attacking the obvious ruling.** The obvious ruling is "`VERSIONING.md` wins, delete the entry", and it is
slightly wrong, because §11 item 8 conflates three different things under one heading: "headless runs,
artifact publishing, static-host publish targets." `VERSIONING.md` §1 is a document about how package
versions move, and the scope it closes is the workspace's own release process. Publishing a documentation
*site* that docstrap built to a static host is not publishing a *package* to an index; it is the tool's
output, and it is a product feature that `VERSIONING.md` never addressed. Deleting the whole entry would lose
a real capability on the strength of a rule that does not reach it.

**Ruling.** `VERSIONING.md` §1 stands, and it stands unqualified for what it actually covers: no CI, no
package index, no release automation for anything in this workspace. Spec §11 item 8 should be split rather
than deleted — headless runs and static-host publish targets survive as docstrap product capabilities;
artifact publishing as a release mechanism goes, permanently. Decided on evidence: the phrase "permanently
and by decision" in a root governing document beats a roadmap entry whose own text already concedes the
conflict has "not been reconciled with it."

**What would reverse it.** The captain adding a downstream consumer — anyone installing docstrap from an
index rather than from the stable-install script — which removes the stated reason for the whole of
`VERSIONING.md` §1's exclusion.

### §6.3 spec Q6 — the ordering of §11

**The question, as posed** (`docs/docstrap_on_2026-09-01.md` Q6): "The ordering of §11 has not been re-confirmed since the
original spec was written, and four of its entries did not exist then. Is the priority order still right?"

**The case for re-confirming it.** Fourteen entries in a rough priority order is useful orientation, and
re-reading them once is cheap.

**Why that is the wrong act.** The section's own header already answers the question and then undermines the
premise: "Ordered by rough priority … Priority order below has not been re-confirmed since the original spec
was written; **treat the ordering as stale even though the contents are current.** Sequencing is not this
document's job — `docs/roadmap.md` is where the entries that are actually next get named."

So §11 simultaneously claims an order and disclaims it. And the project's rule is unambiguous: `AGENTS.md`
states that "Sequencing goes in the roadmap and nowhere else." An ordering in the spec is a second sequencing
surface, which is the thing that rule exists to prevent.

Re-confirming the order would therefore repair the symptom and keep the defect. It would also go stale again,
on the same mechanism, the next time an entry is added — the question would return.

**Attacking it.** Removing the ordering loses information: some of these fourteen genuinely matter more than
others, and a flat list says nothing. But that information belongs in the roadmap, which has it — §4.1
through §4.18 are sequenced, and several §11 entries are named there. The spec's job is to say what does not
exist; the roadmap's job is to say what is next. A flat inventory does the first job completely.

**Ruling.** Do not re-confirm the order — **remove it.** Drop "Ordered by rough priority" and the staleness
disclaimer with it, and let §11 be an unordered inventory of what does not exist, with sequencing left
entirely to the roadmap. This retires the question permanently rather than answering it once. Decided on
evidence: §11's own self-contradicting header, and `AGENTS.md`'s one-sequencing-surface rule.

**What would reverse it.** A reader needing priority and not finding it in the roadmap — which would be a
gap in the roadmap, and the fix would still be there rather than here.

### §6.4 spec Q7 — the two empty store entries

**The question, as posed** (`docs/docstrap_on_2026-09-01.md` Q7, abridged to its operative parts): "Two entries in the
promdance store, `isolated-tool-store` and `markdown-store`, were written by docstrap's own test suite rather
than by anybody drafting. Both are empty directories … **and they predate the `user_dirs` fixture that now
redirects XDG directories at a throwaway home, so no test can create another.** … **What would be done, if
it were an agent's call: delete both, and nothing else.** … It is not an agent's call, because the store is
the one directory in this system whose contents are irreplaceable, and 'it looked empty' is precisely the
reasoning that should never be enough to delete something there. Should they be removed?"

**The case for deleting them.** They hold nothing, nothing links to them, and `promdance status` will keep
listing them as store entries no project claims. The question itself records that this is what an agent would
do.

**The case for leaving them.** The store is the one irreplaceable directory in the system, and emptiness is
weak evidence of worthlessness.

**Three measurements, and the first two dismantle the premise.**

First, **sixteen of the 23 store entries are empty**, not two. Only seven hold any file at all: `trk_tdp`
(48), `dkp` (17), `formizer` (13), `datatime` (9), `rl_deployment` (7), `docs` (1), `winrun` (1). The other
sixteen — including `apps__eos-review`, `packages__docstrap`, `packages__laces`, `ronin-ledger-panels`,
`dkp-platform-landing-plan` and `unnamed` — are empty for the ordinary reason that `promdance intern` creates
an entry and drafting fills it later. So emptiness does not distinguish the two named entries from fourteen
legitimate ones, and singling them out rests entirely on a provenance claim the store does not record.

Second, **the premise that no test can create another is false, and I falsified it by accident.** Running the
suite with `HOME` and XDG redirected into task scratch created `markdown-store` in the throwaway store. It is
produced by `tests/test_sphinx_resolution.py::test_sphinx_builds_use_docstrap_environment_not_path`, which
builds a project titled "Markdown Store" and takes only `tmp_path` and `monkeypatch` — it does not request
`user_dirs`. That test is current. `markdown-store` is not residue that predates the fixture; it is
regenerated on every run that lacks it.

Third, **nothing is tracked.** `git ls-files` in the store returns zero files for every empty entry, which is
the mechanical consequence of git recording no empty directory — as Q7 itself notes. So "removing them from
the store's history" is a no-op; only a filesystem directory exists.

`isolated-tool-store` is the different case: no current test produces it, so it is genuine historical
residue. The question treats the two as one thing and they are not.

**Attacking the ruling.** The counter-argument is that none of this makes deletion *wrong* — the two
directories still hold nothing, and `rmdir` on an empty directory is about as safe as an act gets. True. My
ruling is not that deletion is dangerous; it is that deletion is the wrong *shape* of answer, because it
treats a recurring symptom as a one-off and because the reporting complaint it is meant to fix is not about
emptiness at all.

**Ruling.** No, not as posed. Three things instead. Fix the test isolation first (§7.7), because
`markdown-store` returns on the next unisolated run and a cleanup that undoes itself is not a cleanup.
Deleting `isolated-tool-store` alone is safe and harmless but buys nothing, since nothing tracks it and
sixteen entries look the same. And the actual complaint — `promdance status` listing entries no project
claims — is about being *unclaimed*, not about being *empty*; fourteen empty entries are claimed and correct.
That distinction is the fix worth filing. Decided on evidence: the store listing, `git ls-files`, and a
reproduction of the supposedly impossible case.

**What would reverse it.** Finding that `promdance status` already distinguishes claimed from unclaimed, in
which case the reporting half is done and the residue is purely cosmetic. Or the captain simply wanting the
two directories gone regardless, which is his to say and costs nothing once §7.7 lands.

### §6.5 spec Q8 — `from_web/` in the store's history

**The question, as posed** (`docs/docstrap_on_2026-09-01.md` Q8, abridged): "`trk_tdp/from_web/` is 26 files and 5.4 MB of a
saved Gemini web page … and it is the great majority of the store by size; everything else together is 536
KB. It is not a draft. … it carries the captain's personal Google address seven times, Google's own public
browser API keys … and sixteen WSL `:Zone.Identifier` alternate-data-stream files. No private key, no session
cookie, no credential of his anywhere in the store … So nothing here is dangerous on a machine — but it is
the one thing in the store that is neither a draft nor obviously his to publish, and it would be the bulk of
what a first push sends. **It is committed locally and nothing has been pushed** … Should `from_web/` be in
the store's history before that happens, and if not, should it be removed from the store or only from what is
tracked?"

**Measurements, updated.** `from_web/` is 5.4 MB of an 8.6 MB store — 63% by size, so "the great majority" is
still fair. It is **32 tracked files**, not 26. The "everything else together is 536 KB" figure is stale by
roughly six times: everything else is now about 3.2 MB. Nothing has been pushed; the store's log ends at
`d39e879` and no remote is configured.

**The case for leaving it tracked.** `docs/docstrap_on_2026-09-01.md` §8.4.2 is emphatic and the rule is load-bearing:
`promdance store commit` **forces** `git add`, because "a file in the store exists nowhere else, so there are
no exclusions." The live `promdance/dkp/.gitignore` reads `*`, and honouring it would have silently dropped
sixteen real drafts from a commit that reported success. An exclusion for `from_web/` is exactly the kind of
carve-out that rule exists to forbid.

**The case for removing it from tracking.** It is the bulk of what a first push sends, it is not a draft, and
it carries the captain's personal email address thirty-two files deep into a repository whose whole purpose
is to be pushed somewhere eventually.

**The synthesis, and why it beats both.** Both options accept a false premise — that `from_web/` has to be
either tracked or excluded *while staying in the store*. §8.4.2's rule is sound precisely because of its
stated reason: a file in the store exists nowhere else. That reason is what makes exclusions dangerous. It is
also what identifies the real defect here: `from_web/` is not a draft, so the store is the wrong place for
it, and the fix is not an exclusion but a **move**. Take it out of the store into ordinary storage, and it
stops being tracked without any exclusion existing, and §8.4.2 keeps its absolute form.

**Attacking it.** A move is more work than `git rm --cached`, and it touches the one directory whose contents
are irreplaceable — so it must be a move, verified, not a delete. There is also a real possibility I am wrong
about what it is *for*: if the captain saved that page as source material for a `trk_tdp` draft, then it is
draft-adjacent and being beside the drafts is the point, and my "not a draft" reasoning is too literal. That
is the one thing evidence here cannot settle, and it is Q1 in §11 below.

**Ruling.** It should not be in the store, and therefore not in its history — but the act is to move it out
of the store rather than to untrack it in place, so that no exclusion is created and §8.4.2 stays absolute.
The bytes are kept; nothing is deleted. The window for doing this cheaply is open because nothing has been
pushed and no remote exists, and it closes the moment one does. Medium confidence, with the narrow preference
flagged as Q1.

**What would reverse it.** The captain saying `from_web/` is source material he wants beside the `trk_tdp`
drafts — in which case it stays, tracked, and the only remaining question is whether he minds his email
address travelling with it to whatever host he eventually names.

### §6.6 spec Q9 — `docs/notes/index.md`

**The question, as posed** (`docs/docstrap_on_2026-09-01.md` Q9): "`packages/docstrap/docs/notes/index.md` is docstrap's own
generated section page with one line appended by hand — the composer sorts its entries and the file has
`2026-09-12-mission-statement` after `sphinx-extension-research` rather than before, added by commit
`5e18bf9`. It is therefore `divergent` and was left alone during the §7.8 purge, correctly, because the rule
is strict in the safe direction. Now that no build composes a page for a directory holding a user's
`index.md`, this file has quietly become that project's authored section landing and will never be
refreshed. Delete it and let the section be composed, or keep it as an authored page?"

**The case for keeping it.** It works, it renders, and a hand-written landing page can say things a composed
listing cannot. Deleting a tracked file to let a tool regenerate something is the kind of act that wants a
deliberate decision, which is why the question exists.

**The case for deleting it.** `AGENTS.md`, on the composed-index rule: "**Indexing is not optional and is
never an agent's job.** Every published directory gets a section page, composed by the tool. A design that
asks a person or an agent to maintain an index is the thing §7.8 rules out."

**And it has already failed, in exactly that way.** The file's toctree lists two documents:
`sphinx-extension-research` and `2026-09-12-mission-statement`. The directory holds three. `2026-09-17-promdance-todo.md`
was added by commit `190dae8` — "note the captain's promdance to-do, verbatim" — and the hand-maintained
toctree was never updated. The build says so out loud:

```
packages__docstrap/notes/2026-09-17-promdance-todo.md: WARNING: document isn't included in any toctree [toc.not_included]
```

I confirmed the mechanism in the build tree. `_scratch/packages__docstrap/notes/` has **no**
`index.docstrap-section` marker, because `index.md` is present and `is_document_file`'s docstring states the
rule — "A user's own `index.md` is excluded because it *becomes* a section's landing rather than appearing
inside it." So the authored file wins, and the captain's own note is published as `notes/2026-09-17-promdance-todo.html`
while being reachable from nothing.

That is not a hypothetical risk that the file "will never be refreshed". It went stale within days of being
made authoritative, and it dropped a document the captain specifically asked to be recorded.

**Attacking it.** If the captain wants prose on that landing page — an introduction to what the notes are —
deletion loses it, and composition alone cannot provide it. That is the one thing that would make this wrong.
But it is not what the file contains: the file is a title and a toctree, with no prose at all. There is
nothing there to lose. If he wants prose there later, the answer is a way to have both a composed listing and
an authored preamble, not a hand-maintained toctree.

**Ruling.** Delete it and let the section be composed. Decided on evidence: the file is a bare toctree with no
authored prose, it has already dropped a real document from the site's navigation, and the project's own rule
says an index a person maintains is the thing the composed-index design exists to remove.

**What would reverse it.** Authored prose actually wanted on that page, which changes the question from
"authored or composed" to "how do we compose a page with a preamble."

### §6.7 spec Q10 — the undeclared `index.md` files

**The question, as posed** (`docs/docstrap_on_2026-09-01.md` Q10): "Nine of the thirty-one `index.md` files tracked in
`platformshoes` sit in directories no `.docstrap` declares — `apps/ccpane`, `apps/charmoji`, `apps/pd`,
`packages/git_id`, `packages/object-brewer-ui`, `packages/repo-migrations`, and `docs-site/formizer`,
`docs-site/laces`, `docs-site/object-brewer`, `docs-site/pitches`. `generated-indexes` cannot reach them and
did not report on them; read by hand they are all authored, six of them a one-line 'Docs directory
placeholder' that is not docstrap's stub. Should those directories be declared projects so the report covers
them, or are they deliberately outside the site?"

**The numbers are stale in three ways, and one of them is internal.** The repository tracks **14** `index.md`
files, not 31 — the one-time scrubber (commit `0f82afd`) and the §7.8 purge removed the generated ones after
Q10 was written, so its denominator was consumed by the very work that followed it. Its own list contains
**ten** paths while calling them nine. And it omits `docs-site/index.md`, which is also in an undeclared
directory, making the true figure eleven of fourteen.

The list itself is accurate. The root `.docstrap` declares four projects — `packages/docstrap`,
`packages/laces`, `packages/object-brewer`, `apps/laces-desktop` — and two related directories, `docs` and
`winrun`. Everything Q10 names is outside that.

**The case for declaring them.** The report would cover them, and a workspace member with a `docs/` directory
looks like a project.

**The case for leaving them undeclared.** Six of the files are a one-line placeholder, which is what a
directory looks like before anyone has written documentation in it. Declaring a project to make a report
cover a placeholder inverts the purpose: the declaration is what says "this is published", not a
bookkeeping device for a linter's reach.

**And the work already exists.** Roadmap §4.6 is "Projects discovered rather than hand-listed." Hand-listing
ten more projects now is precisely the labour that entry exists to remove, and doing it by hand would make
§4.6's eventual arrival a migration rather than a feature.

`docs-site/` is a separate case worth naming rather than folding in: it is another published site with its
own `conf.py` (the h21 survey recorded that it loads only `myst_parser` and `sphinx_design`, none of
docstrap's extensions). Its four subdirectory indexes are that site's own pages, not undeclared docstrap
sections.

**Attacking it.** "Roadmap §4.6 will handle it" is the weakest kind of answer — it defers rather than
decides, and §4.6 has no date. If §4.6 never lands, these eleven files stay outside every report
indefinitely. The counter is that being outside the report is the correct state for them, not a gap: they are
authored placeholders in directories nobody publishes, and `generated-indexes` is specifically a report about
what *builds* wrote. Its inability to reach a file no build ever touched is not a blind spot.

**Ruling.** They are deliberately outside the site, and nothing should be declared by hand. `docs-site/` is a
separate published site and its indexes are its own. Q10's counts should be corrected or the question retired
— at 14 tracked files with 11 outside, the proportion it was built on no longer holds. Medium confidence:
the reasoning is sound but it rests on inferring intent from a one-line placeholder, and the captain knows
which of those six he means to publish.

**What would reverse it.** Any of those six directories gaining real documentation, which makes it a project
that should be declared whether or not §4.6 has landed.

### §6.8 spec Q11 — the zero-byte section marker

**The question, as posed** (`docs/docstrap_on_2026-09-01.md` Q11): "A build's scratch tree now holds one zero-byte
`index.docstrap-section` marker per section instead of composed markdown, which is why 'HTML only' cost
nothing in navigation (§7.8.2). Reaching literal zero files needs private Sphinx internals and was refused on
those grounds. Is an empty marker inside the build acceptable as the permanent shape, or should docstrap
accept the coupling — or stop using Sphinx's toctree for section navigation — to remove it?"

**The case for removing it.** "No markdown in the build" is nearly absolute, and a marker file is a small
asterisk on an otherwise clean claim.

**The case for accepting it.** The two alternatives are both worse by a wide margin. Depending on private
Sphinx internals buys a cosmetic win with an upgrade hazard — the class of coupling that breaks on a minor
release, silently. Abandoning the toctree means reimplementing section navigation, which is the one thing
Sphinx is unambiguously good at, to delete an empty file.

**What the build actually produces.** I verified it rather than taking §7.8.2's word:

```
markers found:                     23
markers larger than zero bytes:     0
real markdown files in the build:   0
markdown symlinks in the build:    94
```

So the claim in `AGENTS.md` — "What a build puts in its scratch tree is a `conf.py` and a zero-byte
`index.docstrap-section` marker per section" — holds exactly. Every marker is zero bytes, and there is no
authored markdown anywhere in the build; all 94 markdown files are symlinks into the projects.

The marker is also carrying real semantic weight rather than being a wart. Its absence is what tells the
build that a directory has a user's own `index.md` and must not be composed over — that is the mechanism
§6.6 turns on, and I confirmed it by finding no marker in `notes/`. A zero-byte file whose presence *is* the
signal is a reasonable design, not a leftover.

**Attacking it.** The honest cost is that "docstrap writes no markdown into a build" needs the qualifier "but
it writes one empty non-markdown marker per section", and a future reader may find that qualifier annoying.
That is a documentation cost, not a design one, and §7.8.2 already pays it.

**Ruling.** Accept the empty marker as the permanent shape. Decided on evidence: 23 markers at zero bytes
each and zero authored markdown in a full six-project build, against two alternatives that trade a cosmetic
gain for either private-API coupling or a reimplementation of toctree navigation. The marker additionally
encodes the has-authored-index signal, so removing it would need that signal moved somewhere else.

**What would reverse it.** Sphinx growing a public API for contributing a page to the toctree without a
source file, which would make zero files reachable without private internals.

### §6.9 spec Q12 — where `file_index` lives

**The question, as posed** (`docs/docstrap_on_2026-09-01.md` Q12): "`file_index` is written by a build against
`~/.local/share/docstrap/metadata.db`, so building a project is now a write to the metadata store as well as
a read of the project. That is what makes the table answerable without the filesystem and what a watcher will
write into. It is also a new source of rows in a database whose document rows are 59 of 64 test residue
awaiting a ruling (Q7's neighbourhood). Is a build writing index rows into the metadata store the right
arrangement, or should the index live in a file of its own that can be deleted without opening that
database?"

**The case for its own file.** `metadata.db` holds the one genuinely irreplaceable thing in docstrap —
status history, path history and content observations, with no backup. `file_index` is wholly derived and a
rebuild costs one build. Keeping the disposable thing out of the irreplaceable file means it can be deleted
freely, and it keeps a build from writing to the file that must be handled carefully.

**The case for keeping it in the metadata store.** The planned watcher (§11 item 4, roadmap §4.13) writes one
changed path into `file_index` and updates document metadata in the same event, and one database means one
transaction. `file_index.document_id` links an indexed file to its metadata row. A second database means a
second `user_version` axis, and `0002` already manages five.

**The measurement, which cuts against the coupling argument.** Of 522 `file_index` rows, **3** have a
non-null `document_id`; 519 are null. There is no `FOREIGN KEY` declared — the column is a plain
`document_id TEXT`. So the join the co-location argument rests on is 0.6% populated today, and it is not
enforced.

**Attacking my own ruling.** That measurement is weaker evidence than it looks, and I nearly over-read it.
`document_id` is sparse because document *registration* is sparse — four real documents are registered in the
whole workspace — not because the link is a bad idea. As registration grows the join becomes real, so "only
three rows" is a fact about the registration gap rather than about the schema. Anyone weighing the watcher's
transactional needs more heavily than I do would keep the table where it is without hesitation, and they
would not be wrong.

**Ruling.** Keep `file_index` in the metadata store. The watcher's one-transaction requirement is a real
design constraint, the `document_id` link is sparse-but-intended rather than vestigial, and a second database
adds a version axis for a table that does not need its own lifecycle. But adopt the half of the question's
worry that is correct: because the table is wholly derived and `reconcile` rebuilds it per project, its
upgrade treatment should be **drop-and-rebuild, never a data migration** — stamp the version, empty the
table, let the next build refill it. That gives the disposability the separate-file option was reaching for
without giving up transactional locality, and it keeps migration code from ever having to reshape 522
regenerable rows.

The question's framing that a build writing to the metadata store is suspicious *because* the store holds
test residue does not survive §7.6 and §7.7: the residue is an isolation defect with a one-line fix and a
mechanical predicate, and it is not an argument about where a derived table belongs.

**What would reverse it.** The watcher landing without needing a cross-table transaction, which removes the
main argument for co-location. Or `file_index` growing large enough that it dominates the backup `docstrap
upgrade` must take — at 522 rows in a 400 KB file, it is nowhere near that.

### §6.10 spec Q13 — the cross-reference warnings

**The question, as posed** (`docs/docstrap_on_2026-09-01.md` Q13): "A relative markdown link between documents emits
`myst.xref_missing` on every docstrap build, because the documents are symlinks and MyST resolves the link
through the link into the project, which is not in the build. The links all render correctly and every target
exists, so it is noise — but it is 28 warnings on docstrap's own docs alone, and a build's warning count is
what its notes report, so a real warning would be hiding in it. Ten of the 28 are new … Is making relative
cross-document links resolve inside the build worth doing, and if so should the fix be a MyST/Sphinx setting
or a change to how documents reach the scratch tree?"

**The case for fixing it.** 28 warnings per build hides real ones, and the question says so.

**The case for leaving it.** The links render correctly and every target exists, so the warnings are
cosmetic. Changing how documents reach the scratch tree is the riskiest part of the build.

**What a full build actually emits.** I captured `sphinx-build`'s stderr, which the build counts and
discards (`layouts/markdown.py:733` is `warnings = (result.stderr or "").count("WARNING")`):

| code | count |
|---|---:|
| `myst.xref_missing` | 94 |
| `myst.header` | 78 |
| `toc.no_title` | 27 |
| `toc.not_included` | 4 |
| **total** | **203** |

Per project: `packages__docstrap` 29, `packages__laces` 41, `packages__object-brewer` 24, `docs` 109,
`apps__laces-desktop` 0, `winrun` 0.

Two things follow, and they point at a different fix than the one the question proposes.

**First, Q13's premise is materially incomplete.** `myst.xref_missing` is 94 of 203 — 46%. Fixing it would
leave 109 warnings still hiding things. The question treats the noise as one thing and it is four.

**Second, the harm it predicts has already happened.** docstrap's own 29 warnings are 27 `xref_missing` and
**2 `toc.not_included`** — and those two are real:

```
packages__docstrap/notes/2026-09-17-promdance-todo.md: WARNING: document isn't included in any toctree
packages__docstrap/research/_template.md:              WARNING: document isn't included in any toctree
```

The first is the captain's own promdance note (§6.6), published but reachable from nothing. In the `docs`
project, all 27 `toc.no_title` warnings are one underlying defect amplified —
`docs/notes/organization_2026_9_11.md` has no heading at all, it begins with indented prose, so Sphinx
reports "no link will be generated" and that document is unreachable too. Both are the captain's own writing.

So the question's hypothetical — "a real warning would be hiding in it" — is not a risk. Two of his documents
are invisible in the built site right now, and both said so in a warning that the build reduced to a number.

**Attacking the ruling.** Reporting warnings by code does not *fix* anything — the 94 unresolved links remain
and the noise stays. Someone could reasonably say this substitutes a report for a repair. The answer is
sequencing, not substitution: the report costs almost nothing (the text is already in hand at
`markdown.py:733` and thrown away), it surfaces the real warnings immediately without fixing any noise, and
it is the only one of the two that helps on the *next* build. The link fix is still worth doing and is still
the larger win; it is simply not the first thing.

**Ruling.** Yes, making relative cross-document links resolve inside the build is worth doing — 94 warnings
is the largest single category and it degrades every build's signal. But that is the second fix. The first is
to **report warnings by code rather than as a bare count**, because it is nearly free, because it immediately
surfaces the four `toc.not_included` and 27 `toc.no_title` warnings that the count is currently hiding, and
because two of the captain's documents are unreachable today on exactly that mechanism. On the question's
second half — setting or scratch-tree change — the evidence points at the scratch tree, since the cause is
that MyST resolves through a symlink into a project that is not in the build, and no MyST setting changes
where a symlink points; but that is a design question for the work item rather than something this ruling
settles.

**What would reverse it.** Finding that the warning text is not reliably available where the count is taken
— it is, at `markdown.py:733` — or a MyST setting that makes symlinked relative links resolve, which would
make the cheap fix and the real fix the same act.

(s7)=
## §7 The upgrade-path rulings — `docstrap-upgrade-rulings-h99`

These seven come from `docs/proposals/0002-the-upgrade-path.md`, which is under evaluation and not approved.
Its §7 says of the package version that it is "deliberately not solved here", and its Open Questions preamble
says "None is answered here; each is the captain's." Ruling on them does not approve the plan.

One figure in the plan is already stale and it matters for Q6: §3.3 describes "the live 94 KB database", and
`metadata.db` is now 400 KB.

### §7.1 upgrade Q1 — the one status vocabulary

**The question, as posed** (`0002` Q1): "`docs/docstrap_on_2026-09-01.md` §5.1 states one shared status vocabulary, but
`metadata.VALID_STATUSES` holds `draft, proposal, spec, plan, active, archived` while
`strapdance.STATUS_BY_DIRECTORY` resolves to `done`, `reusable` and `reference`, none of which is in that
set. Is the metadata set the one vocabulary, with the strapdance directory mappings to be brought into it?
(§4.4 — this blocks the vocabulary axis and nothing else.)"

**Half of this the captain has already answered.** `docs/docstrap_on_2026-09-01.md` §5.1, recording his 2026-08-28 decision:
"There is **one shared status vocabulary**, the six values above" — the six being metadata's. So the metadata
set is the one vocabulary, and that half is settled and should not be re-put to him.

**The live half is what to do about the three values that are not in it**, and it is a genuine contradiction
between two current documents. `strapdance-front-matter.md` (retired on 2026-11-20) §3.2 is titled "**`status` is an open
vocabulary**" and says "Write whatever you want. There is no enum, nothing is rejected." §5.1 says the
vocabulary is closed at six. §5.1 tries to reconcile them — the reader "still preserves an unrecognised value
verbatim … because the reader never writes" — and that reconciliation works for *arbitrary* values a person
typed. It does not cover values docstrap's own code manufactures.

**And there is a fourth mismatch nobody has named.** §3.2's table lists `archive` as a status value.
`VALID_STATUSES` holds `archived`. A near-miss of one letter, in a table that reads as authoritative, which
the database would reject.

**What the code does with them.** I traced it, because whether these values reach the database changes the
severity completely. `meta.set_status` is called from exactly two places — `server.py:212` and `cli.py:649` —
and both pass a status the user supplied. Nothing passes strapdance's derived value into the store. So the
three out-of-vocabulary values never enter `metadata.db`; the contradiction is confined to what the reader
*reports*.

**The case for widening `VALID_STATUSES` to nine.** It is one edit, it makes both documents true, and it
respects that `reusable` and `reference` express something real — retention intent — that the six do not.

**The case for narrowing `STATUS_BY_DIRECTORY` instead, which is what I prefer.** Look at what those three
values mean in §3.2's own table: `reusable` is "kept to run again" and is implied by `templates/`;
`reference` is "kept to consult" and is implied by `memories/` and `notes/`. Those are descriptions of what
*kind* of document it is, and the `kind` axis already carries them — `KIND_BY_DIRECTORY` maps `templates` →
`template`, `memories` → `memory`, `notes` → `note`. A template's lifecycle status is `active`: it is in use.
Its reusability is its kind. So two of the three are a kind wearing a status's name, and the third, `done`,
is a lifecycle value the six already express as `archived`.

Narrowing therefore removes all four mismatches at once and shrinks `STATUS_BY_DIRECTORY` to a single
entry (`done` → `archived`), while widening would grow a closed set by three values that duplicate the kind
axis and would leave `archive`/`archived` still wrong.

**Attacking it.** Information is lost at the edges. A document in `templates/` currently reports status
`reusable`; afterwards it reports `active` with kind `template`, and anyone reading only the status field
sees less. Also `notes/` → `reference` is doing something the kind axis does *not* quite say: `note` is a
form, `reference` is a reason for keeping it. If the captain wants a retention axis that is independent of
both lifecycle and form, three values are genuinely needed and narrowing is the wrong move — that is the one
thing that would make this wrong, and it is a product preference rather than a fact.

**Ruling.** Yes, the metadata six are the one vocabulary — §5.1 already settled that and it should be cited
rather than re-asked. The directory mappings should **not** be brought into it; they should be moved off the
status axis, because `reusable` and `reference` are kinds the `kind` axis already derives, and `done` is
`archived` under another name. Separately, `strapdance-front-matter.md` (retired on 2026-11-20) §3.2's heading and its `archive` row
both contradict §5.1 in the live tree and need correcting either way. Medium confidence, because the
narrowing rests on a judgement about what those three words are *for*.

**What would reverse it.** The captain wanting retention expressed as a status independent of lifecycle and
kind, in which case widen `VALID_STATUSES` to nine and fix `archive` → `archived` instead.

### §7.2 upgrade Q2 — exempting the read-only commands

**The question, as posed** (`0002` Q2): "§3.1 refuses to open a database that is behind, on every command.
Should the read-only commands — `questions`, `doctor`, `--version` — be exempted and allowed to run when they
touch only tables the old schema already had?"

**The case for exempting them.** Being unable to run `docstrap --version` because a database is behind is
absurd — the refusal message tells you which docstrap release can read the file, and `--version` is how you
find out which one you have. That is a bootstrap deadlock.

**The case against.** A per-command exemption requires knowing which tables and columns each command touches,
and keeping that knowledge true forever. The failure mode is sharp and silent: a command gains a column read,
nobody updates its exemption, and it reads a column the old schema does not have.

**The measurement that dissolves most of the question.** I ran each of the three against an empty throwaway
home and looked for a database:

```
docstrap --version      -> databases created: 0
docstrap questions PATH -> databases created: 0
docstrap doctor         -> databases created: 0
docstrap stores         -> databases created: 0
docstrap tag DOC review -> databases created: 1   (~/.local/share/docstrap/metadata.db)
```

**None of the three commands the question names opens a database at all.** `questions` imports only
`projectscope` and `docstrap.questions` — it is a pure document scan, and `pairing.py` (which does touch
metadata) is not on its path. `doctor` reads the strapdance chain and the filesystem. `--version` reads
package metadata. Since the schema check happens on open, and they never open, they cannot be blocked.

§3.1's wording is already correct on this point and already exempts them by construction: "every entry point
**that opens a database** checks first."

**The honest residue.** One read path does open a database: `docstrap status <doc>` used to *report* rather
than change, since it is one command for both ("Report or change a document's status"). That is the only case
the question is really about.

**Attacking the ruling.** For that one case the exemption is genuinely cheap — a report of
`documents.current_status` touches a column every version of the schema has had. Refusing it is mild
user-hostility for no data-safety gain. The counter is that the exemption's value is one command's
convenience while its cost is a column-level audit per command that must stay correct across every future
schema change, and the remedy the refusal names is a single deliberate command. A stale read is also not
harmless in the way it looks: reporting a status from a schema docstrap knows is outdated is a wrong answer
delivered confidently, which is worse than a refusal naming the fix.

**Ruling.** No exemption. Keep the refusal uniform across every entry point that opens a database, which is
what §3.1 already says. The three commands the question names need no exemption because they never open one —
proven by running them — and that fact delivers most of the convenience the exemption was reaching for. The
plan should state the `docstrap status`-in-report-mode case explicitly rather than leaving it implied, since
it is the only command the rule actually bites.

**What would reverse it.** `docstrap upgrade` turning out slow or risky enough that people defer it and want
read access meanwhile, or a read-only DB-touching command becoming a daily surface.

### §7.3 upgrade Q3 — the shape of the derivative

**The question, as posed** (`0002` §5.4, which states it): "*What* the derivative is — a proposed diff, a
block to paste, an `AGENTS.md.docstrap-proposed` beside the file, or a fix-plan script in doctor's existing
shape — is **Q3**. All four are defensible and the choice is the captain's. What is not open is that it
produces something a person then applies."

**What exists to reuse.** `doctor --fix-plan` is built and disciplined. `write_fix_plan` refuses to
overwrite, writes one file and creates nothing else, chmods it 0755, and the generated script opens with
"docstrap WROTE this file and RAN NONE OF IT. Nothing has been moved, edited, or deleted." Every move whose
destination nobody chose stays commented out, "so a plan run without further thought does nothing at all."
That discipline is exactly right and should be reused.

**The case for the fix-plan script.** It exists, it is the project's one established pattern for "docstrap
proposes, a person applies", and reusing it adds no concepts. A script is self-applying; a proposed file needs
an apply step that does not exist.

**The case for a proposed file.** It is diffable by machine, which a script is not.

**The distinction that decides it.** `fix_plan` renders `git mv` lines — it is a *file-move* planner, and a
shell script is the natural medium for moves. An instructions update is a **text edit inside a file**. A
generated script that rewrites prose inside `AGENTS.md` means heredocs or `sed`, which is both harder to
review than the change it performs and fragile against any hand-edit the file has since received. The medium
does not transfer even though the discipline does.

**Attacking it.** A proposed full file needs a person to run `diff` and then `mv`, which is two steps where
the script is one, and "the apply step does not exist" is a real cost I am waving at. It is small — `diff`
and `mv` are not new tools — but it is a cost. The stronger objection is that I am choosing on a medium-fit
argument when the captain may simply prefer one artifact type across all of docstrap's outputs, and
consistency has value I am discounting.

**Ruling.** Take the fix-plan's **discipline** and not its medium: one file, beside the original, refusing to
overwrite, carrying the same header stating that docstrap wrote it and applied nothing. Make that file
`AGENTS.md.docstrap-proposed` — a complete proposed replacement a person diffs and moves into place — rather
than a shell script, because the operation is a prose edit and a generated text-rewriting script is harder to
review than the diff it is trying to produce. This also keeps the project's rule intact: `AGENTS.md` is never
written by docstrap. Medium confidence; all four options remain defensible and this is a judgement about fit.

**What would reverse it.** The instructions update turning out to be a delimited block docstrap owns rather
than a whole-file edit — a block is safely scriptable, and then the fix-plan medium transfers after all.

### §7.4 upgrade Q4 — schema versions and the package version

**The question, as posed** (`0002` §7): "What is *not* settled is whether a schema change should nonetheless
force a release bump, so that 'which docstrap can read this database' has an answer a human can act on —
§3.2's refusal would like to say 'install docstrap 0.0.6 or later', and it can only say that if a schema
version maps to a release. Against: it re-couples the two number-lines this section just separated. A third
option gets the message without the coupling — the migration step records the package version it ran under,
as data, without the package version driving anything. This plan is written so all three stay possible. It is
**Q4**."

**The case for forcing a bump.** §3.2's refusal message is only actionable if it can name a release. "This
database needs a newer docstrap" without a number sends the user to read git log.

**The case against.** §7 makes it well: `VERSIONING.md` §2.3's trigger is "bump when you want to name a state
you can go back to and install", and forcing a bump on schema change creates a second, competing trigger. The
version becomes a clock, which §7 says it is not.

**The case for the third option, which the document already articulates.** Record the package version the
migration ran under, as data in the database. Then the refusal can say "this file was last migrated by
docstrap 0.0.5; install 0.0.5 or later" — a concrete, actionable answer — and nothing about the package
version drives anything. It gets the whole benefit of coupling with none of the coupling.

**Attacking it.** It is not free: it needs a column or a metadata row to store the stamp, and the stamp is
only as useful as the last migration. A database never migrated has no stamp, so the first refusal after the
first upgrade lands still cannot name a release. That gap is real but it is bounded — §3.3 case 2 stamps
today's live database at version 1 during the first migration, so it acquires a stamp the first time
`docstrap upgrade` runs, and before that there is nothing to be behind. The deeper objection is that I am
picking the option the document's own author already favoured, which is agreement rather than adjudication.
I can only note that the reasoning stands on its own and I checked it against `VERSIONING.md` §2.3 directly.

**Ruling.** No — a schema change should not force a package version bump. Take the third option: the
migration step records the package version it ran under, as data, and §3.2's refusal reads that stamp to name
a release. Decided on evidence: `VERSIONING.md` §2.3 defines one bump trigger and §6 records that no release
tag exists in the repository at all, so a schema-driven bump would be inventing releases to satisfy a message
that a stored stamp answers directly.

**What would reverse it.** The stamp proving insufficient in practice — a user holding a database whose stamp
names a release that was never tagged, which is possible while `VERSIONING.md` §6's no-tags state persists.

### §7.5 upgrade Q5 — the annotations database

**The question, as posed** (`0002` Q5): "§2.1 versions the two databases apart and gives both the same
refuse-and-migrate treatment. `annotations.db` holds one row against a store `docs/docstrap_on_2026-09-01.md` §6 calls complete
and unexercised. Should it get that same treatment, rather than the cheaper rule that a version mismatch may
recreate it?"

**The case for the same treatment.** Uniformity is cheap to reason about, and a rule that says "this database
is precious and that one is not" invites the mistake of applying the wrong one. If Annotorious is added and
real annotations accumulate, the file becomes user data and the cheap rule becomes data loss.

**The case for the cheaper rule.** Refuse-and-migrate exists to protect history that cannot be reconstructed.
`annotations.db` has none.

**What the one row is.** I read it:

```
id         urn:docstrap:annotation:478cb0e7-fe30-47ec-8aa2-6e0e683344a0
target_doc docstrap://document/test-1
body_json  {"type": "TextualBody", "value": "trial annotation", ...}
creator    smoketest
created_at 2026-08-18T19:47:34+00:00
```

`creator` is `smoketest`, the target is `test-1`, the body is "trial annotation", and the file's mtime is
still 2026-08-18 — it has not been touched since. So `annotations.db` holds **zero real user data**, and its
only row is residue from a smoke test.

That is also a finding about §7.7 below: the plan says "two of the three persistent states" hold rows nobody
meant to keep. It is three of three.

**Attacking it.** The moment Annotorious is added, this ruling is wrong, and it will be wrong silently —
nothing will announce that the file has become precious. That is a genuine hazard and it is why the ruling has
to carry a trigger rather than just a decision. The mitigation is cheap: the recreate rule should be
conditional on the file being empty of real rows, not on which file it is. A database with annotations in it
gets the careful treatment automatically, whatever its name.

**Ruling.** No — `annotations.db` should not get refuse-and-migrate. A version mismatch may recreate it. But
express the rule as a property rather than as a filename: recreate is permitted when the file holds no rows a
client wrote, which is true today and stops being true the moment one does. Decided on evidence: the single
row is a `smoketest` row, nothing has written to the file in six weeks, and spec §6/Q4 records that the
intended client has not been added.

**What would reverse it.** Annotorious being added, or any real annotation appearing — which the
property-based form of the rule detects on its own.

### §7.6 upgrade Q6 — the test rows in the live database

**The question, as posed** (`0002` Q6): "Fact 7: 59 of the 64 document rows in the live `metadata.db` were
written by one test and point at `/tmp` paths that no longer exist. Should the first upgrade also clear them
— a destructive act on the only copy of the data, which is why it is asked rather than planned — or should
they be left for `docs/roadmap.md` §4.8's orphaned pool to collect when that is built?"

**Updated measurement, and the numbers have moved.** It is **73 of 78**, not 59 of 64:

```
documents rows:                                     78
  project = 'test_tag_reports_metadata_erro0'
  and current_path LIKE '/tmp/pytest-of-johnh%':    73
  remaining:                                         5
paths that exist on disk:                            4
```

The residue's `created_at` runs from 2026-08-28 to **2026-09-23**. It grew by 14 rows in the 13 days since
the figure of 59 was recorded. **This is not historical residue. It is an open leak, still writing.**

**The five survivors, for completeness.** Four real documents — one `formizer` index and three `dkp`
research/questions documents — and one row pointing at
`/home/johnh/platformshoes/docs/plans/docstrap-mvp.md`, which stopped existing on 2026-09-01. That last is
the broken path roadmap §4.7 and `0002` §2 both describe, and it is genuinely a case for §4.8's orphaned pool:
a real row whose document moved or died.

**The case for leaving it to the orphaned pool.** §4.8 is the designed answer to "a metadata row whose
document cannot be resolved", it loses nothing, and it avoids a destructive statement in the first migration.

**The case for clearing it in the first upgrade.** §4.8 does not exist and has no date. Meanwhile 94% of the
document table is residue, which makes every count docstrap reports about itself wrong by more than an order
of magnitude, and it will keep growing.

**The fact that changes the risk calculus.** The plan asks this rather than planning it because clearing rows
is "a destructive act on the only copy of the data" — the concern being that judgement is needed to tell
residue from real data. It is not. The provenance is recorded *in the data*: the `project` column literally
holds `test_tag_reports_metadata_erro0`, the truncated name of the test that wrote it. The predicate
`project = 'test_tag_reports_metadata_erro0' AND current_path LIKE '/tmp/pytest-of-johnh%'` selects exactly 73
rows and **cannot** select any of the five others. It is mechanical, checkable, and reviewable before it runs.

**Attacking it.** Two real objections. First, the predicate is only safe while no real project is named
`test_tag_reports_metadata_erro0` and no real document lives under `/tmp/pytest-of-johnh` — both absurd, but
the predicate should be asserted to select 73 and to leave 5 before it deletes anything, rather than trusted.
Second and more seriously: **clearing is pointless before the leak is closed.** Delete 73 rows today and the
next unisolated run starts refilling them at roughly one per run. Ordering matters here more than the
decision does.

**Ruling.** Yes, clear them — but not as the first upgrade's opening act. Close the leak first (§7.7), then
clear, and then it stays cleared. The destructiveness concern that made this the captain's is substantially
answered by the data itself: the rows carry their own provenance in the `project` column, so a mechanical
predicate separates residue from real data with no judgement, and it should be run as an assertion (expect 73
selected, 5 retained) rather than as a bare `DELETE`. The one row that genuinely wants §4.8's orphaned pool is
the `docstrap-mvp.md` row, which is a real document that stopped existing — exactly what the pool is for.

**What would reverse it.** The predicate failing its assertion — selecting a count other than 73, or touching
a row whose path is outside `/tmp/pytest-of-johnh`. Either means the residue is not as uniform as measured and
the whole act should stop.

### §7.7 upgrade Q7 — tests writing to live user state

**The question, as posed** (`0002` Q7): "Two of the three persistent states were found on 2026-09-17,
independently, to hold rows nobody meant to keep, both written by docstrap's own test suite: 59 document rows
in `metadata.db` (fact 7) and the two empty store entries `docs/docstrap_on_2026-09-01.md` Q7 asks about. Is a test that writes
to live user state a defect class worth a standing rule — a suite-wide assertion that no test touches a real
XDG directory — rather than two separate cleanups?"

**The case for two separate cleanups.** Two known instances is not obviously a class, and a suite-wide
assertion is machinery. Fixing the two tests is a smaller change.

**The case for the standing rule.** It is the one thing that stops recurrence, and recurrence is the whole
problem.

**Four measurements, and they settle it.**

*It is three of three, not two of three.* `annotations.db`'s only row is `creator = 'smoketest'` (§7.5). Every
persistent state docstrap has holds test or smoke residue.

*Both leaks are live, not historical.* Running the suite with `HOME` and XDG redirected wrote exactly **one**
document row — `project = 'test_tag_reports_metadata_erro0'`, path under `/tmp/pytest-of-johnh` — identical in
shape to the 73 live ones. One run, one row; 73 rows, 73 unisolated runs. The same run **created
`markdown-store`** in the throwaway promdance store, which falsifies spec Q7's claim that "no test can create
another." Both leaks would have hit the captain's real data had I not redirected.

*The isolation is opt-in and mostly not taken.* `user_dirs` exists in `conftest.py` and redirects HOME and
all four XDG variables — but it is a plain fixture, requested per test, with **no autouse guard**. Of 34 test
files, 14 reference it and 17 do not. `test_cli_errors.py::test_tag_reports_metadata_error_without_traceback`
takes `(tmp_path, monkeypatch)` and writes the metadata row; `test_sphinx_resolution.py::test_sphinx_builds_use_docstrap_environment_not_path`
takes `(tmp_path, monkeypatch)` and writes the store entry. And `test_skill_install.py` carries its own
`_redirect_home` helper — a **second implementation** of the same isolation, which is the one-owner defect
`AGENTS.md` names elsewhere, applied to test isolation. So the suite has three states: uses `user_dirs`, rolls
its own, or has none.

*The fix is provably safe.* The full suite under a redirected `HOME` and all four XDG variables:

```
469 passed in 33.51s
```

**No test needs the real directories.** An autouse guard breaks nothing — that is measured, not argued.

**Attacking it.** An autouse fixture is a blunt instrument: it silently changes the environment for every
test, including ones a future author writes expecting the real home, and a test that genuinely needs the real
XDG directories would fail confusingly. That is the honest cost, and it is small here because no such test
exists today and because a test that wants the real home can be given an explicit opt-out that has to be
written down. The weaker part of my position is the word "assertion" in the question versus "autouse" in my
answer: an assertion detects, autouse prevents. Prevention is better, but an assertion additionally catches a
test that opts out and then writes, so the right answer uses both rather than choosing.

**Ruling.** Yes — it is a defect class and it is worth a standing rule, and the rule should be **autouse
redirection plus an assertion**, not one or the other. Autouse `user_dirs` so isolation is the default and
cannot be forgotten; keep an assertion that no test touched a real XDG path so a deliberate opt-out cannot
leak silently; and fold `test_skill_install.py`'s `_redirect_home` into the one owner. Decided on evidence:
all three persistent states hold residue, two leaks are demonstrably still writing today, isolation is opt-in
and not taken by half the suite, and 469 tests pass fully redirected so the fix costs nothing.

This is the ruling §6.4 and §7.6 depend on. Both of those are cleanups that undo themselves until this lands.

**What would reverse it.** A test that legitimately requires the real XDG directories — none exists today,
and the 469-pass run is the evidence.

(s8)=
## §8 Classification, and the shape of what was left

**Decided on evidence — 14.** §5.1, §5.2, §5.3, §5.4, §6.2, §6.3, §6.4, §6.6, §6.8, §6.10, §7.2, §7.4, §7.5,
§7.7. In these the code, a run, or a governing document the captain already signed settles it, and a
reasonable person reading the same evidence lands in the same place. Four of the fourteen (§5.1–§5.4) were
settled by shipped implementation before this task began.

**Decided on judgement, reasoning exposed — 5.** §6.7, §6.9, §7.1, §7.3, §7.6. Real evidence, sound
reasoning, but a different weighting of costs could defensibly go the other way. §6.9 is the closest call:
the sparse `document_id` argues for separation and the watcher's transactionality argues against, and I
weighted the watcher more heavily. §7.6 is judgement only about *ordering* — the decision to clear is
evidence-backed.

**Genuinely the captain's — 2, and both narrowed to one sentence.** §6.1 and §6.5. Both carry a ruling, so
neither is parked; what remains is a preference no evidence can settle, stated as Q1 and Q2 below.

**That the third category is this small is a claim, so here is the check.** I did not shrink it by ruling
confidently on thin evidence. Eleven of the twenty-one turned out to be answerable because something had
*already* happened that nobody had gone back to look at — four shipped features, three captain answers
already written into `docs/docstrap_on_2026-09-01.md`, two governing-document decisions (`VERSIONING.md` §1 and §2.1), and two
premises that measurement falsified outright. The questions were not hard. They were stale, and staleness
reads as difficulty when nobody re-measures.

The two that remain are genuinely his, and they are both about *want* rather than fact: whether four
aggregate affordances are still wanted, and what a saved web page in his drafts store is for. No amount of
reading the repository answers either.

(s9)=
## §9 Work implied, to be filed

This task decides; it does not implement. Nothing below was done. These are described, not sequenced —
sequencing belongs to `docs/roadmap.md` and nowhere else, so whoever files them decides the order there.

1. **Autouse test isolation, plus the assertion, plus one owner** (§7.7). Make `user_dirs` autouse; assert no
   test touched a real XDG path; fold `test_skill_install.py::_redirect_home` into it. Prerequisite for items
   2 and 3, which undo themselves without it.
2. **Clear the 73 residue rows** (§7.6), as an assertion that expects 73 selected and 5 retained, not a bare
   `DELETE`. After item 1.
3. **Delete `isolated-tool-store`, and make `promdance status` distinguish unclaimed from merely empty**
   (§6.4). The reporting half is the part that matters; fourteen empty entries are correct.
4. **Report build warnings by code rather than as a count** (§6.10). The text is already in hand at
   `layouts/markdown.py:733` and discarded. This surfaces the two real warnings currently hidden.
5. **Two unreachable documents** (§6.6, §6.10). `docs/notes/2026-09-17-promdance-todo.md` is in no toctree and
   `docs/notes/organization_2026_9_11.md` has no heading, so neither is reachable in the built site. Both are
   the captain's own writing. Item 6 fixes the first; the second needs a heading.
6. **Delete `packages/docstrap/docs/notes/index.md`** (§6.6) and let the section be composed.
7. **Make relative cross-document links resolve in the build** (§6.10) — 94 warnings, the largest category.
   The cause is symlink resolution into a project outside the build, so the scratch tree is the likely seam.
8. **Move `trk_tdp/from_web/` out of the promdance store** (§6.5), without creating a `.gitignore` exclusion,
   and without deleting bytes. Gated on Q1.
9. **Move `STATUS_BY_DIRECTORY`'s three values onto the `kind` axis** (§7.1), leaving `done` → `archived`;
   and correct `strapdance-front-matter.md` (retired on 2026-11-20) §3.2's "open vocabulary" heading and its `archive` row, which
   contradict `docs/docstrap_on_2026-09-01.md` §5.1 in the live tree.
10. **Document edits that follow from rulings**, all of them corrections to text the code has overtaken:
    split spec §11 item 8 (§6.2); remove §11's priority ordering (§6.3); correct or retire spec Q10's counts
    (§6.7); restate spec Q3's reason as a prerequisite rather than an open want (§6.1); record `file_index`'s
    migration as drop-and-rebuild in `0002` (§6.9); state the `docstrap status`-in-report-mode case in `0002`
    §3.1 (§7.2); correct `0002` §3.3's "94 KB" and its "two of the three persistent states" (§7.5); and
    correct spec Q1's recorded answer, which says the file moved into `docs/plans/` when it sits at
    `docs/docstrap_on_2026-09-01.md` (§10).
11. **Close the three holds.** All 21 live items now have a ruling; `fm-captain-hold.sh answer` is the path
    once the captain has said which he accepts.

(s10)=
## §10 Findings about the questions themselves

Eleven places where a governing document describes a state the repository no longer has. Two of them are a
question's own premise, which means the question could not have been answered as asked.

1. **spec Q7's premise is false.** "They predate the `user_dirs` fixture … so no test can create another" —
   `markdown-store` was created by the current suite during this task (§6.4).
2. **`0002` Q7 undercounts itself.** "Two of the three persistent states" — it is three of three;
   `annotations.db`'s only row is a `smoketest` row (§7.5).
3. **The h21 survey is obsolete in its central finding.** "Roughly 15% built … answers today are write-only"
   — the mode shipped 2026-09-13/14 (§5).
4. **`0002` Q6's figure moved.** 59 of 64 is now 73 of 78, and it grew by 14 rows in 13 days (§7.6).
5. **spec Q10's denominator is stale and its own count is internally wrong.** "Nine of the thirty-one" — 14
   are tracked, and the list holds ten paths, omitting an eleventh (§6.7).
6. **spec Q13's composition is wrong.** 28 `xref_missing` on docstrap's docs is 27, and `xref_missing` is 94
   of 203 warnings workspace-wide rather than the whole of the noise (§6.10).
7. **spec Q8's comparison figure is stale by six times.** "Everything else together is 536 KB" — about 3.2 MB
   now; and it is 32 tracked files, not 26 (§6.5).
8. **`0002` §3.3 describes "the live 94 KB database".** It is 400 KB (§7).
9. **spec Q1's recorded answer names the wrong destination.** It says the captain promoted this file into
   `docs/plans/`; `docs/plans/` holds only `0001-answer-loop.md` and the spec sits at `docs/spec.md` (renamed
   `docs/docstrap_on_2026-09-01.md` on 2026-11-20). The
   decision (out of `proposals/`) was carried out; the recorded description of where it landed was not
   corrected.
10. **`strapdance-front-matter.md` (retired on 2026-11-20) §3.2 contradicts `docs/docstrap_on_2026-09-01.md` §5.1 head-on.** "`status` is an open
    vocabulary … There is no enum" against "one shared status vocabulary, the six values above" (§7.1).
11. **`hold-reconcile-h104` §4.3.12 is itself out of date**, and instructively: it declared spec Q9–Q13
    nonexistent on 2026-09-17, the same day commit `97292f3` added them (§3).

Two observations about the pattern, offered because the task asked for findings about the questions rather
than only answers to them.

**The questions were composed from notes and not re-measured before being put.** That is the same mechanism
`hold-reconcile-h104` §1 identified in September — "firstmate composed questions from its own notes instead
of from his repositories" — and it is still operating, including inside that report. Every stale figure above
was cheap to check: a `git ls-files`, a `SELECT count(*)`, one build.

**Four of the twenty-one were answered by shipped code that nobody went back to read.** A hold does not
notice when the work it gates gets done. That is worth a mechanism rather than a resolution — re-measuring a
hold's premise before putting it to the captain would have closed §5.1 through §5.4 without his involvement
at all, and would have caught §6.4's false premise before it was asked.

One caveat on my own evidence, recorded rather than buried: `pagefind` was not on `PATH` in this environment,
so `pagefind_step` skipped silently (it is best-effort by design) and the build produced no `_pagefind`
index. Cross-project search therefore was not exercised here, and the h21 survey's claim that it is ready for
the reference panel is neither confirmed nor contradicted by this task.

---

## Open questions

Two, and both are narrow by construction: each carries a ruling above, so answering is a confirmation or a
correction rather than a decision from scratch. Numbered so `docstrap questions` finds them.

**Q1.** §6.5 rules that `trk_tdp/from_web/` — 5.4 MB, 32 tracked files, 63% of the promdance store — should
be moved out of the store rather than untracked in place, on the reasoning that it is not a draft and a
drafts store is the wrong home for it. The one thing the repository cannot say is what it is *for*. Is it
source material you keep deliberately beside the `trk_tdp` drafts, rather than a saved page that landed in
the store incidentally? If it is, it stays where it is and the only live question becomes whether you mind
your personal email address travelling in it to whatever remote you eventually name.

**Q2.** §6.1 rules that the tag index, backlinks, cross-project cross-linking and recent-updated feed stay
unbuilt, because the layers they sit on hold four registered documents and one stale tag set and emit 94
unresolved-link warnings per build — unsupported rather than unwanted. That reasoning establishes they are not
*next*. It cannot establish whether you still want them at all. Do you?
