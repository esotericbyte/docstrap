---
title: Every kind of question mark that is not a question
---

# docstrap doctor — what it reports, and what it will not do

`docstrap doctor` answers one question about a workspace: which documents
does no project actually own? It reports them, it can write a proposal
script, and it changes nothing else. Ever.

## 1 Why does this matter?

Because a document nobody owns is a document nobody builds. That is the
whole of it.

A document is **ambiguously scoped** when its position's answer to
"which project owns this?" came from the workspace root — or from nothing
at all.

> would it make sense for the encrpyted part to be only the secrets and
> have secrets.encrypted or secrets.plaintext ? Add an index of projects
> by full origin. Is that reasonable?

## 2 Frequently asked

**Does doctor ever move a file?** No. It reports and proposes; it does not
act.

**What does `--fix-plan` write?** One shell script nobody has run. It
refuses to overwrite anything.

## 3 What it can answer

It replaces the file-based directory with something that can answer
questions like:

- Which pitches are in evaluation right now, ordered by complexity?
- For project X, what's the ratio of delivered to withdrawn work?

## 4 An example of the convention

An open-questions section is written like this:

```markdown
## 9 Open questions

Q1. Should this fixture's fenced example be collected? It must not be.
Q2. Nor this one.
```

The convention is described in Q1 and Q2 of the proposal, and a turn that
carries answers confirms them: "I heard Q3=X, Q5=Y — confirm?"
