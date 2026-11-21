# 0001 — Repairing the answer loop

Written 2026-09-14, from one real run: eight questions exported into a project, answered by the captain,
travelling correctly and closing the right work, with six things broken around them. `docs/roadmap.md`
§4.11 states the findings; this plan orders the work.

**All six steps were carried out on 2026-09-14, in this order.** What each delivered, and where it
differed from what is written below, is in `docs/implementation-record.md` §1.3(13)–(18); what the tool
now does is in `docs/docstrap_on_2026-09-01.md` §8.1.3, §8.1.4, §7.6(1), §8.2, §7.7 and §8.3, one per step. This document
is kept as the record of the ordering and the reasoning that produced it, not as outstanding work. One
thing it asked for is **not** done: the `answered` tool of step 5 has had no in-browser run, which
`docs/tools-and-instruments.md` §7 records as outstanding.

The ordering is not arbitrary. **One step makes three of the findings cheap**, and two steps are
prerequisites for everything after them.

## §1 What is wrong, in dependency order

Roadmap §4.11's six findings, regrouped by what they need rather than by how they were noticed.

1. **When an answer counts** — findings 1, 2 and 3. It counts on first autosave, there is no way to
   signal completion, and once counted it cannot be revised.
2. **What the surfaces can see** — findings 4 and 5. The panel is scoped to the project rather than the
   document, and nothing anywhere pairs a question with its answer.
3. **What the loop produces** — finding 6. Nothing. An answer is stored and never delivered.

Group 3 depends on group 2, which depends on an API that does not exist yet. Group 1 depends on
nothing and relieves the most damage, so it goes first.

## §2 Step 1 — an answer is final when it is submitted

**Delivers:** a finish action in the panel, and a stored answer that carries whether it was submitted.

This is the captain's finish button, and it is the fix for three findings rather than one. With an
explicit submit, "when does an answer count" stops being a guess: it counts when a person says so. The
settle window that would otherwise be needed becomes unnecessary, and revision before submission is free
because nothing has counted yet.

**Proves it:** an answer typed in pieces produces no consumer-visible event until submit, and the same
answer submitted produces exactly one.

**Unblocks:** the firstmate bridge, which is disarmed today precisely because every autosave read as an
answer. Its adapter then consumes submitted answers only — a change in that repository, dependent on
this step exposing the distinction.

## §3 Step 2 — a submitted answer may be revised while its question is open

**Delivers:** supersession. A later answer replaces an earlier one rather than being rejected.

A captain rewriting his own reply is ordinary. Today it requires a hand repair, because the recorded
decision no longer matches what is offered. The rule needs one definition - what makes a question still
open - and the honest default is that a question is open until the work it gates is closed.

**Proves it:** answer, submit, answer differently, submit; the second is what everything downstream
reads, and the first is recoverable rather than lost.

## §4 Step 3 — the panel is scoped deliberately

**Delivers:** the document-targeted read, and an explicit choice of scope in the instrument.

Independent of steps 1 and 2; it could land first. Both halves are already present in the code that
lacks them: `routes.py`'s header names `/api/promdance/{project}/{doc_slug}/<collection>` as the
document-targeted form, and `Panels.svelte` already holds `d.ctx.docSlug` and uses it for the reference
pane while ignoring it for the fetch.

Default to document scope, because the instrument is opened while reading something and that
something's questions are what is wanted. Project scope stays available as the deliberate wider view.

**Proves it:** opening the panel on two documents in one project shows two different lists.

## §5 Step 4 — answers are readable over the API

**Delivers:** an endpoint that returns questions paired with their current answers. `/api/promdance/…`
returns 404 for answers today.

Prerequisite for everything after it, and the point at which "the store is a markdown file" stops being
every consumer's problem.

**Proves it:** a caller that is not the browser can ask what is answered without parsing markdown.

## §6 Step 5 — the pair is rendered

**Delivers:** each question shown with its current answer beneath it, and an unmistakable marker on the
ones still open.

Roadmap §4.11 item 4 is the finding. `docs/docstrap_on_2026-09-01.md` §0 forbids writing into the source document and that
stays true: this is resolved at build or serve time, not appended to anything. Not appended was allowed
to become not linked, and this is where that is corrected.

**Proves it:** a reader of the question document can tell an answered question from an open one without
leaving the page.

## §7 Step 6 — the loop delivers an artifact

**Delivers:** an answer addendum generated beside the original, a version of the document recording that
it was answered, and a record citable from wherever the decision is acted on.

The captain's finding, in his words: "it's a pregnancy with no delivery." A decision that leaves no
artifact has been stored rather than delivered, and three things already assume otherwise - documents as
the unit of value in `docs/docstrap_on_2026-09-01.md` §0, the documentation-first practice, and dkp's contract stamp
deriving from a document's hash so that an answered question moves a version.

The key needed already exists: an answer hangs on `<document-id>:<label>` and survives a rename.

**Proves it:** answering a question produces something a person can cite, and the document's version
reflects that it was answered.

## §8 What this plan does not include

The URL resolver of roadmap §4.9 - given a document, return the link to hand someone. It is adjacent and
independently useful, and step 5 gives it a natural home, but it is not required by any step here.

Nor does it include the MCP surface of §4.10. Step 4's API is the thing MCP would expose, so §4.10
follows this plan rather than competing with it.
