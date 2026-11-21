# Research

Open threads of inquiry that are not ready to become a specification, a proposal, or code. A
research note surveys, reasons and poses questions; it does not decide. The captain decides.

A research note is **not**:

1. A verbatim archive of a prompt — those go to `../notes/`.
2. A committed design — committed designs are `docs/docstrap_on_2026-09-01.md` and the package pages
   beside this directory (`../doctor.md`, `../tools-and-instruments.md`). The package page
   `strapdance-front-matter.md` was retired on 2026-11-20.
3. A decision. An open question here is answered by the captain, never by an agent writing an answer
   into the document.

A research note **is**:

1. A topic and a question the package keeps an open mind about.
2. An evolving body of measured findings — counts taken from the real repositories, values read out
   of the real code — with the measurement method stated so it can be re-run.
3. A potential source of work: a thread can become a section of the specification, an entry in
   `docs/roadmap.md`, or a recorded decision not to pursue it.

## File naming

`NNNN-short-topic.md`. Numbered independently of `../notes/`. Numbers are never reused.

## Anatomy

Front matter follows `_template.md`. Bodies use the deep dotted section numbering the package's other
pages use (`## 1`, `### 3.2`), and cross-references take the form `§3.2`.

Every note ends with an **Open questions** section whose items are labelled `Q1.`, `Q2.`, `Q3.` —
the workspace convention, and the exact form `docstrap questions` finds. The Q enumeration is
deliberately separate from the section number-line.

## Status meanings

1. **Open** — actively being thought about; new entries expected.
2. **Dormant** — parked; will be revisited if related work surfaces it.
3. **Spawned** — the thread produced a specification section, a roadmap entry, or an implementation;
   the note links to it.
4. **Concluded** — the question has been answered and the answer lives somewhere authoritative.
5. **Withdrawn** — decided not to pursue, kept so the same path is not re-walked unknowingly.

## Index

| # | Topic | Status | Last updated |
|---|---|---|---|
| 0001 | [Front-matter superseding directories, and where per-project documentation is filed](0001-front-matter-supersedes-directories.md) | Open | 2026-09-01 |
