---
research: 0002
title: Terms for document state, chunk identity, and deferred choice, with their fields of origin
status: Open
started: 2026-10-05
last_updated: 2026-10-05
related_specs:
  - "docs/spec.md"
  - "docs/strapdance-front-matter.md"
  - "docs/proposals/0002-the-upgrade-path.md"
related_notes:
  - "docs/research/0001-front-matter-supersedes-directories.md"
related_code:
  - "packages/docstrap/src/docstrap/viewer/manifest.py"
  - "/home/johnh/firstmate/bin/fm-procevent-docstrap.sh"
---

THIS DOCUMENT IS A RESEARCH NOTE. ITS DEFINITIONS ARE NORMATIVE FOR THE VOCABULARY ONLY. NO SYSTEM DESIGN, MECHANISM, OR IMPLEMENTATION IS APPROVED BY ANYTHING WRITTEN HERE.

# RN-0002 — Terms for document state, chunk identity, and deferred choice, with their fields of origin

## 1 The question

A conversation on 2026-10-04 and 2026-10-05 produced a working vocabulary for three entangled concerns: how a document's status can be made to bind on a reader that is an agent, how a document's parts can keep identity while the document is re-edited and re-enumerated, and how a choice can be moved out of a specification so it is settled later by configuration rather than by committing to it now. The terms came from at least nine different fields and several were coined in the conversation itself. Some of them collide: the same word carries different meanings in two of the contributing fields, and two different words name nearly the same thing.

This note records each term, the field it comes from, what it shall mean when used here, and how it operates. It poses; it decides nothing. Where two terms collide, §10 says how they are to coexist rather than choosing between them.

## 2 What triggered it

The captain, on the failure of two earlier attempts to make a document's status bind:

> The docstrap / strapdance plan of using frontmatter failed. The prompting rules that say don't act on a proposal FAILS. When proposals are started they need to have a preamble. Maybe that will not fail.

And his proposed replacement, quoted exactly because its wording is the mechanism:

> IF THIS DOCUMENT IS IN THE PROPOSAL STATE IT'S NOT YET APPROVED FOR IMPLIMENTATION UNTIL THIS MESSAGE IS REMOVED.

Both earlier failures were observed rather than supposed. Front matter failed because an agent pointed at a document reads its body and treats a metadata block as plumbing. The prompting rule failed in this very conversation: firstmate was told, in its own standing instructions, that a proposal is not authorization, and then told a worker to implement a feature "as the corrected proposal describes" — promoting an unapproved document to a specification, in the same session in which it had recorded the rule forbidding it.

On the wider intent:

> I want that MCP to inject the preambles based on the metadata in the database. That separates the preambles to be separate from content in one way but part of it in another way.

> Firstmate tasks often also create proposals, and also revise old specs that are in conflict with new ones. But if it's producing specs in md files not through an mcp then it leaves it free to decied how to use the document produceed. This problem would need to be solved cleanly.

The authorized-context half of that design is named **specavator** and is deliberately out of scope here (§11).

## 3 Conventions used by this note

Obligation words follow RFC 2119, from IETF standards engineering: MUST and SHALL mark a requirement, SHOULD a strong default that may be departed from with reason, MAY a genuine option. They are used here only about the use of a term, never about the system.

Each entry gives the term, the field it originates in, a normative definition, and how it operates — the mechanical consequence of the term, not a restatement of the definition. A term marked **coined here** has no prior field; it was invented in the source conversation and §10 or its own entry says what it would have to be reconciled with if it is kept.

## 4 Document status, and authority over a reader

### 4.1 Proposal

*Field: docstrap's own document lifecycle.*

A document that argues a position and is not approved for implementation. A proposal MUST NOT be treated as a specification, and work items MUST NOT be derived from it.

*How it operates:* it is a readable artifact with no authority. Its presence at a readable path is precisely the hazard this note exists to address, because authority is currently inferred from readability.

### 4.2 Plan

*Field: docstrap's own document lifecycle.*

An approved document from which work items may be derived. The transition from proposal to plan is the approval event.

*How it operates:* it is the only document state from which task creation is licensed. The captain stated the pipeline as proposal, then plan, then work items, and that nothing skips the middle step.

### 4.3 Preamble

*Field: coined here, by analogy with a statutory preamble in legislative drafting.*

A block of text at the head of a document body, carried in the content rather than beside it, which states the document's status in the imperative and whose removal constitutes the transition out of that status.

*How it operates:* it collapses state and enforcement into one artifact. There is no separate status field to keep synchronised with the document, because deleting the sentence *is* the state change. It is also mechanically checkable: a fixed string can be searched for, so a tool can refuse to treat a document as a plan while the line is present, and can flag a document filed as a plan that still carries it. This is the property neither front matter nor a prompting rule had — front matter was never checked against behaviour, and a prompting rule cannot be checked at all.

### 4.4 In-band and out-of-band

*Field: telecommunications signalling; adopted in protocol design.*

In-band information travels inside the same channel as the content. Out-of-band information travels beside it.

*How it operates:* this is the distinction that explains the observed failures. Front matter is out-of-band, so a reader consuming the body never encounters it. A preamble is in-band. An MCP that injects a preamble from database metadata makes a record that is stored out-of-band arrive in-band, which is the captain's "separate from content in one way but part of it in another".

### 4.5 Read path

*Field: systems and storage engineering.*

The set of locations from which a document may be retrieved and treated as authority by an agent or a person.

*How it operates:* status can only bind if the read path is controlled. A document file at a path an agent can be pointed at is in the read path regardless of what any record says about its status.

### 4.6 Staging location

*Field: software release engineering.*

A location deliberately outside the read path, where an artifact exists before it is promoted.

*How it operates:* an approval gate without a staging location has no mechanical effect, because the unapproved artifact is already retrievable. Promotion is the act of moving an artifact from staging into the read path.

### 4.7 Approval gate

*Field: process control; software release engineering.*

A control point an artifact MUST pass before it enters the read path.

*How it operates:* it converts status from a description into a precondition. Its strength is exactly the strength of the read-path control behind it.

### 4.8 Authorized context

*Field: coined here; cognate with a security principal or a capability in access control.*

An execution context that is permitted to change documents. Contexts outside it may read but MUST NOT write.

*How it operates:* it relocates the question from "did the agent follow the rule" to "could the agent have done otherwise". A rule that depends on an agent's compliance failed twice already; a context that lacks write capability cannot fail in that way.

### 4.9 Specifications-as-source

*Field: coined here by analogy with infrastructure-as-code and docs-as-code.*

A discipline in which the specification is the authored source artifact and every other representation — rendered site, extracted task, injected preamble — is derived from it.

*How it operates:* derived representations MUST be reproducible from the source and MUST NOT be edited in place, on pain of the two drifting.

### 4.10 Normative, and the normative rule set

*Field: IETF standards engineering for the keyword register; legal theory and deontic logic for the broader sense.*

A normative statement imposes an obligation, permission or prohibition rather than describing a state of affairs. A normative rule set is a body of such statements applied to documents.

*How it operates:* a rule set that is normative can be evaluated against an artifact to yield a verdict. A descriptive statement cannot, which is why "this is a proposal" is weaker than "this MUST NOT be implemented".

### 4.11 Normative hierarchy

*Field: legal theory; legal informatics.*

An ordering among governing documents establishing which prevails where two apply to the same subject.

*How it operates:* it is what makes the captain's case mechanical — "if a document is older and in its context subject to other documents". Without a declared ordering, a conflict between two approved documents can only be resolved by a reader noticing it.

### 4.12 Derogation

*Field: law.*

The rule by which one norm yields to another: a later norm over an earlier one, a specific norm over a general one, a higher norm over a lower one.

*How it operates:* it supplies the resolution procedure the hierarchy in §4.11 only orders. The three classical forms are directly applicable to a document set that accumulates revisions.

## 5 Chunk identity, and change over structure

### 5.1 Authored chunk

*Field: coined here, to separate two senses of "chunk" that collide (§10.1).*

A unit of a document the author wrote as a unit: a paragraph, a section, a document, a collection.

*How it operates:* it is the unit a human or an agent refers to, tags, approves, or marks as provisional. Its boundaries are semantic and are chosen by the author.

### 5.2 Stored chunk, and content-addressed chunking

*Field: content-addressable storage; deduplicating backup systems and IPFS.*

A byte range identified by the hash of its content, whose boundaries are chosen by a chunker rather than by the author.

*How it operates:* identity follows content, so an unchanged chunk has an unchanged name and change is localised to the chunks that actually differ. This is what makes "track it in detail" affordable: a diff is a set difference over names rather than a comparison of whole documents.

### 5.3 Merkle tree

*Field: cryptography, after Ralph Merkle.*

A tree in which every non-leaf node is the hash of its children, so the root hash commits to the entire structure and contents.

*How it operates:* two collections can be compared by one hash; where roots differ, descent locates the difference in logarithmic rather than linear work. It also yields tamper-evidence: no part can change without the root changing.

### 5.4 Merkle trie

*Field: cryptography combined with the trie, a prefix tree from data structures.*

A Merkle structure whose shape is a trie — keyed by path rather than by position — so each node is addressed by the sequence of path components leading to it.

*How it operates:* the distinction from §5.3 is not pedantry here. Path-keying is what the captain's addressing already is: collection, then section, then paragraph. In a trie the key is stable under reordering of siblings, whereas a positionally indexed tree is not. That is precisely the property §5.8 needs.

### 5.5 Fixity

*Field: archival science and digital preservation.*

The verifiable property of an object being unchanged from a recorded state.

*How it operates:* it is the archival name for what §5.3 provides, and it supplies the vocabulary for the thing an approval needs to assert — that *this* content was what was approved, checkable later without trusting the record.

### 5.6 Patch identity and patch theory

*Field: version-control theory, as realised in Darcs and Pijul.*

A model in which a change is a first-class named object with its own identity, and a version is a set of changes rather than a sequence of snapshots.

*How it operates:* it makes "the same change" recognisable in two different lineages, which is what comparing experimental development paths (§7.3) requires. A snapshot model can only tell you two trees differ.

### 5.7 Positional reference versus stable identifier

*Field: naming and addressing theory; the specific failure was observed in this system.*

A positional reference names a thing by where it sits. A stable identifier names it by an identity that survives movement.

*How it operates:* this is a proven defect here, not a hypothetical. docstrap's question adapter records that `Q<n>` is a position and not an identity, so narrowing a question set renumbers it and an answer written before a re-export answers whatever used to occupy that label. The adapter's mitigation is to refuse to trust the label at all: it keeps a private label-to-task map and re-baselines its read position whenever the mapping changes.

### 5.8 Enumeration, and enumeration-history mapping

*Field: Sphinx and docutils supply the enumeration; the mapping is coined here.*

Enumeration is the generated numbering of sections and items. An enumeration-history mapping is a record relating the numbering of one version to the numbering of another, so a reference taken against the old numbering can be resolved against the new.

*How it operates:* it generalises the §5.7 mitigation from questions to every numbered reference. A cross-reference of the form §3.2.4 becomes resolvable across a renumbering instead of silently pointing at different prose.

### 5.9 Re-baselining

*Field: this system's own term, from the docstrap question adapter.*

Treating what a store already holds as delivered, and reading forward from that point, when the mapping a reader depended on has changed.

*How it operates:* it is the conservative response to a lost correspondence: rather than guess which old label means which new one, declare the past consumed. It is cheap and it loses information, which is exactly why §5.8 is wanted.

### 5.10 Tagging

*Field: information science; content management.*

Attaching classifying labels to a unit of content.

*How it operates:* the captain's design integrates tagging with the rule set — rule sets stay separate documents but are "integrated with content tagging of chunks in how they function", so a tag is what selects which rules apply to a chunk. A tag is therefore not decoration; it is the predicate a rule matches on.

### 5.11 Envelope format, with embedded markup

*Field: data serialisation and document engineering; the include mechanism is docutils'.*

A container format carrying units of another markup inside it. Here: a YAML structure embedding chunks of Markdown and reStructuredText includes.

*How it operates:* it lets structure, metadata and tags be machine-addressable in the envelope while authored prose stays in the markup a writer actually writes. The cost is two parsers and a boundary at which escaping and line-numbering must be defined.

## 6 Deferred choice, and variability

### 6.1 Software product line engineering

*Field: software engineering; the term is the Software Engineering Institute's.*

The practice of building a family of related applications from a shared platform in which what is common is standardised and what differs is managed explicitly rather than forked.

*How it operates:* it is the discipline the captain's strategy belongs to. Its central activity is deciding, across a defined family, which choices are standardised and which stay open.

### 6.2 Mass customization

*Field: manufacturing and operations management; borrowed into product-line engineering.*

Producing variants from a standardised core, rather than either one rigid product or many bespoke ones.

*How it operates:* it names the goal rather than a mechanism, and supplies the economic argument: variants must be cheap to produce or the platform is not paying for itself.

### 6.3 Commonality and variability analysis

*Field: software product line engineering.*

The analysis that establishes what members of a family share and where they legitimately differ.

*How it operates:* it is a precondition for everything else in §6, because a variation point can only be named once variability has been located. The captain's insistence that "that group needs to be well-defined and focused" is this analysis's scoping step.

### 6.4 Variation point

*Field: software product line engineering.*

A place in an architecture where variation among family members is permitted, named in the design rather than discovered later.

*How it operates:* naming it is the whole value. An unnamed place where members differ becomes a fork; a named one becomes a parameter.

### 6.5 Extension point

*Field: framework and plugin architecture.*

A published interface at which a party outside the core may attach behaviour.

*How it operates:* near-synonymous with §6.4 but distinguished by audience and commitment — a variation point serves the family's own members and may be refactored, while an extension point is a public contract with outside implementers. §10.3 keeps them apart.

### 6.6 Binding time

*Field: software product line engineering; the underlying notion is from compiler and language theory.*

The moment at which a variation point is resolved: specification, compile, build, deployment, configuration, or runtime.

*How it operates:* this is the precise name for what the captain described as moving choices out of the specification. The choice is not eliminated; its binding time is pushed later. Each later binding time buys flexibility and costs a mechanism that must exist to carry the choice.

### 6.7 Last responsible moment

*Field: lean software development, from lean manufacturing.*

The latest point at which a decision can be deferred without the deferral itself costing more than deciding would.

*How it operates:* it is the principle that tells you *when* to defer, as against §6.6 which only says what deferral is. It is pointedly not the last possible moment.

### 6.8 Ports and adapters, also called hexagonal architecture

*Field: software architecture, after Alistair Cockburn.*

A structure in which a core expresses its needs as ports and all outside systems are reached through adapters implementing them.

*How it operates:* it is the established name for the captain's "data and metadata adapters". Its consequence is that the core's behaviour is defined without reference to any particular outside system, so substituting one is a configuration act rather than a rewrite.

### 6.9 Injectable middleware

*Field: web framework architecture, in the WSGI, ASGI and Express lineage; the injection half is dependency injection, from object-oriented design.*

A composable stage inserted into a processing pipeline, supplied from outside rather than named by the code it affects.

*How it operates:* it makes behaviour addable without editing the thing it affects, which is the behavioural counterpart to §6.10's presentational one.

### 6.10 Skinning, also called theming

*Field: user interface design; the captain's analogy is a webpage stylesheet.*

Variability confined to presentation, resolved at configuration or runtime, which cannot alter behaviour.

*How it operates:* the analogy carries a hard limit worth stating, because the limit is the value. A stylesheet cannot change what a page does. Skinning is therefore the safest variation point to defer and the one that cannot absorb a behavioural choice, so a choice that looks presentational but changes an outcome does not belong here.

### 6.11 Convention over configuration

*Field: framework design, popularised by Ruby on Rails.*

Supplying a standard default so that only departures need to be expressed.

*How it operates:* it is the gentler form of the whole strategy and often the right first move: standardise now, and discover later whether a variation point is actually wanted. It is what the captain described as deciding later "if it needs to be customized".

### 6.12 Intended permanence

*Field: coined here; adjacent to retention and appraisal in archival science.*

A declared expectation of how long a unit of content is meant to last — from provisional, through revisable, to settled.

*How it operates:* it is a property of an authored chunk, and it is a tag in the §5.10 sense, so a rule set can treat a provisional chunk differently from a settled one without either being a separate document.

### 6.13 Degrees of agent assistance

*Field: coined here; adjacent to levels of automation in human factors engineering.*

A declared expectation of how much an agent may do to a unit of content, from read-only, through suggest, to change.

*How it operates:* it is the per-chunk form of §4.8's whole-context question, and it is likewise a tag. It is what allows a single document to contain prose an agent may revise and prose it may not.

## 7 Provenance, versions and experiments

### 7.1 Provenance

*Field: archival science; standardised for data by the W3C PROV model as entities, activities and agents.*

A record of what an artifact was derived from, by what activity, and on whose authority.

*How it operates:* PROV's three-part shape is directly usable: a document version is an entity, a revision is an activity, and the authorized context (§4.8) is the agent. Having a standard model matters mainly because it already answers how to express derivation and attribution without inventing a schema.

### 7.2 Variant provenance

*Field: product-line engineering combined with §7.1.*

Provenance that records not only lineage but which variation-point bindings distinguish one variant from another.

*How it operates:* it is what makes two side-by-side approved versions comparable in terms of *why* they differ rather than only *that* they differ.

### 7.3 Experiment tracking

*Field: machine-learning engineering.*

Recording each trial with the configuration that produced it so trials can be compared after the fact.

*How it operates:* it is the established shape for the captain's case of an agent authorised to try several development paths and compare them. The requirement it imposes is that the differing specification be captured *before* the trial runs, since a trial whose inputs were not recorded cannot be compared, only observed.

### 7.4 Progressive specification

*Field: coined here; adjacent to incremental and iterative development, and to specification refinement in formal methods.*

Development in which a specification is extended or refined over successive versions rather than a new unit being specified from scratch.

*How it operates:* it is why multiple retained versions are a requirement rather than a convenience: the current text alone cannot say which parts are new, which were refined, and which are untouched and still approved.

### 7.5 Specification-level branch prediction

*Field: coined here, borrowing the name from CPU microarchitecture.*

Recording, at the point a specification branches, which way it is expected to go, so work can proceed before the branch resolves.

*How it operates:* the borrowed name carries a useful implication and a warning. The implication is that a prediction must be cheap to be wrong about, which means the work done on a prediction must be identifiable and discardable. The warning is that in its home field a misprediction costs a pipeline flush, and the analogue here is discarded work — so the value depends entirely on how cleanly predicted work can be separated from settled work.

### 7.6 "Try and see" detail

*Field: coined here.*

Content marked as provisional and to be settled by trying it rather than by reasoning further.

*How it operates:* it is a tag in the §5.10 sense and a value of §6.12. For it to be more than tone, it MUST be distinguishable mechanically from settled content, because the failure mode of the whole family of mechanisms in §4 is a reader treating provisional text as authority.

### 7.7 Requirements traceability

*Field: requirements engineering.*

Maintained links between a requirement and the artifacts that derive from or satisfy it.

*How it operates:* it is the structure that makes §7.8 possible. Without links, impact can only be assessed by reading everything.

### 7.8 Change impact analysis

*Field: software maintenance and requirements engineering.*

Determining, from a proposed change, which other artifacts are affected.

*How it operates:* with §4.11's ordering and §7.7's links, the captain's case becomes tractable: an approved change to a governing document yields a derived set of other approved documents whose conformance is now in question. The analysis identifies them; it does not decide what to do about them.

## 8 Prompt-layer terms

### 8.1 Model-pinned context

*Field: coined here, from the captain's "a known specific model which may be defined as part of the system".*

A prompt context authored against one named model, whose behaviour is part of the system's definition rather than an environmental accident.

*How it operates:* it makes the rule set's effect testable, because the thing being tested includes the reader. It also makes model substitution a declared change rather than a silent one. The candidates named were Claude Sonnet and, as lower-cost readers, Haiku, Gemini Flash and DeepSeek.

### 8.2 Intermediate form

*Field: compiler theory, where it is the intermediate representation between front end and back end.*

A representation that is neither the authored source nor the final consumed artifact, designed to be convenient for the transformations performed on it.

*How it operates:* in this system the envelope of §5.11 is an intermediate form, and so is whatever a rule set is compiled into before being evaluated. The compiler analogy's value is its separation: many front ends and many back ends can meet at one intermediate form, which is what allows a low-cost model to consume what a higher-cost one produced.

## 9 Terms that collide, and how they are to coexist

**9.1 chunk.** Content-addressable storage means a hash-named byte range whose boundaries a chunker chose. The authoring sense means a unit a writer wrote. These are different objects with different boundaries and MUST NOT be conflated; this note uses **authored chunk** (§5.1) and **stored chunk** (§5.2). One authored chunk may span several stored chunks and vice versa.

**9.2 binding.** Product-line engineering's **binding time** (§6.6) is when a variation is resolved. User-interface **data binding** is a connection between a value and a widget. Only the former sense is used here, always spelled "binding time".

**9.3 variation point against extension point.** Kept distinct per §6.4 and §6.5: the first is internal to the family and refactorable, the second is a public contract.

**9.4 plan.** docstrap's lifecycle state (§4.2) against the ordinary noun. Where the state is meant, it SHOULD be written as the document state explicitly, because "a plan for X" otherwise reads as prose.

**9.5 tag.** Content tagging (§5.10) against a version-control tag naming a commit. Distinguish as **content tag** and **VCS tag** wherever both could be read.

**9.6 normative.** The RFC 2119 keyword register against the legal-theoretic sense of a norm. These are compatible — the keywords are a notation for obligations — and both senses are in use here, the first in §3 and the second in §4.11 and §4.12.

**9.7 tree against trie.** Both Merkle structures, distinguished in §5.3 and §5.4. The distinction is load-bearing because only the path-keyed form is stable under sibling reordering.

**9.8 provenance.** The informal "where it came from" against the W3C PROV model. Where the model is meant, §7.1's three-part vocabulary SHOULD be used, so that derivation and attribution are not re-invented.

**9.9 skinning.** Presentational variability only, per §6.10. The term MUST NOT be stretched to cover behavioural variability, which is §6.9's business.

## 10 Fields to read, consolidated

Software product line engineering, for §6 entire. Requirements engineering, for traceability and impact analysis. Version-control theory in its patch-identity branch, for §5.6. Content-addressable storage and cryptographic data structures, for §5.2 through §5.4. Archival science, for fixity, provenance and appraisal. Legal theory and legal informatics, with deontic logic behind them, for normative hierarchy and derogation. Lean software development, for the last responsible moment. Software architecture in its hexagonal and dependency-injection lineages, for adapters and middleware. Document engineering, with docutils, Sphinx and MyST as the concrete instances, for enumeration and includes. Standards engineering, for the RFC 2119 register. Machine-learning engineering, for experiment tracking. Human factors engineering, for levels of automation. Compiler theory, for intermediate forms.

## 11 Deliberately out of scope

**specavator** is the project named as the authorized context of §4.8. It is early-stage, has no repository on this machine, and is not registered in any project list here. Surveying its existing documents is a separate piece of work in a separate context, by the captain's direction, so that docstrap's own concerns stay the subject of this note. What this note owes specavator is the vocabulary above; what it must not do is guess at its design.

## 12 Open questions

**Q1.** Should the preamble of §4.3 be authored into the document by whoever creates it, given that an injected-only preamble is absent from the file on disk and therefore absent for any reader that does not come through the injecting layer?

**Q2.** Should an authored chunk's intended permanence of §6.12 and its degrees of agent assistance of §6.13 be one tag axis rather than two, given that in every case discussed so far a more provisional chunk was also one an agent was more free to change?
