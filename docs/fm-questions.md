# The firstmate questions document

Each project docstrap builds with promdance on has one document holding the questions firstmate is
waiting on the captain to answer about that project. It lives in the project's promdance store
entry. The build creates it from a template when it is missing, and its questions are answered with
the same question-and-answer tools as any other document's numbered questions. The code is
`packages/promdance/src/promdance/fmquestions.py`, called from the promdance plugin's two build
hooks. Its tests are `packages/promdance/tests/test_fmquestions.py`.

## Contents

1. Purpose
2. Where the document is
3. What the build does
4. The format
5. How the questions are answered
6. What a writer of the content must hold to
7. Architecture and tradeoffs
8. Not built

## 1 Purpose

Firstmate holds questions for the captain across every project it works in, and gives each one a
reference, `FMQ-<PROJECT>-NNN`, that it issues once and never reuses. Those questions need a page
per project where the captain can read them with links to the documents they concern and answer
them. They change often, so the page must not live in a project's repository, where every update
would dirty the repository's git. Promdance is the area for exactly that: a per-project store
outside every repository, which each project reaches through its `promdance/` link.

## 2 Where the document is

The file is `fm/questions.md` in the project's store entry, so on Linux it is
`~/.local/share/promdance/<slug>/fm/questions.md`. Inside the project it is reached through the
link as `promdance/fm/questions.md`. On the built site, and to every tool, it is the document
`fm/questions`, published at `<project>/fm/questions.html`. The project's landing page lists it
under its own caption, "Firstmate questions".

The site name is `fm/questions` and not `promdance/fm/questions` for the reason §7.1 gives.

## 3 What the build does

### 3.1 It places the scaffold

The promdance plugin's `docstrap_prepare_project` hook runs before a build mirrors anything. After it
wires the store entry, as it always did, it writes the template of §4.1 to `fm/questions.md` in that
entry when no file is there. It never overwrites one, so the document firstmate fills in survives
every later build unchanged.

It writes under the same two guards that decide whether the entry is wired at all
(`promdance.cli.build_wires`). Promdance must be on for the project, at whichever of project,
repository or installation states it (spec §8.5), and the project must not be inside a linked git
worktree, whose entry is the main checkout's. A related directory gets no document, as it gets no
store entry.

### 3.2 It publishes the document as a source of its own

The plugin's `docstrap_project_sources` hook, which already contributes the store entry as the
`draft` source mounted at `promdance`, also contributes the entry's `fm/` directory. That second
source is mounted at `fm` with the role `firstmate-questions`. It is contributed whenever the
directory exists, without creating anything, as the hook requires. The build skips a source lying
inside another when it mirrors the outer one, so the page is published once, at `fm/questions`, and
not a second time under `promdance/`.

## 4 The format

### 4.1 The template

The scaffold is a title naming the project, two short paragraphs saying what the page is, a section
showing how an entry is written, and a `Questions` section that says there are none yet. The
example entry in the template sits in a fenced block, so a fresh scaffold poses no question to any
tool. `fmquestions.TEMPLATE` is its text.

### 4.2 An entry

An entry is one numbered question in the form `docstrap.questions` reads (`finding-questions.md`).
It is followed by an indented paragraph of references, separated from it by a blank line. The
question item opens with the firstmate reference. The references paragraph carries three links: the
project's repository, its specification and the proposal the question concerns. These are the two
example entries the end-to-end test builds and answers:

```markdown
- [ ] **Q1.** FMQ-WIDGET-001: Should the widget store keep its drafts in the promdance store?

  References: [repository](https://example.invalid/owner/widget),
  {doc}`spec </spec>`, {doc}`proposal </proposals/0001-draft-storage>`

- [x] **Q2.** FMQ-WIDGET-002: Is the widget's schema version stamped on every open?

  References: [repository](https://example.invalid/owner/widget),
  {doc}`spec </spec>`, {doc}`proposal </proposals/0001-draft-storage>`
```

The blank line before the references matters. The question finder ends an item at the first blank
line, so the question's text, as the panels show it, is the reference and the sentence and nothing
else. The indented paragraph still renders inside the same list item.

### 4.3 References

A link to one of the project's own documents uses the `{doc}` role with a leading `/` and the
document's slug, its path in the published project without a suffix: `` {doc}`spec </spec>` ``. A
plain markdown link to a `.md` file does not resolve from this page, because the page's source sits
in the store and not beside the documents it links to. A `{doc}` target that does not exist builds
with a warning and renders as unlinked text. The repository link is an ordinary URL.

## 5 How the questions are answered

Nothing here is a new tool. The document has a document identity, so every surface that answers
numbered questions in other documents answers these:

1. The question panels (spec §7.6), opened on the page or across the project.
2. The Answers tool (spec §7.7), which shows each answer beneath its question on the page.
3. `/api/answers` and `docstrap questions`, which list the questions with their answers.

An answer is keyed on the document's metadata id and the entry's `Q<n>` label (spec §8.1.1). Each
answer lands in the project's `answers.md` in its store entry. A submitted answer also writes the
addendum (spec §8.3) to the project's draft root, the store entry itself, as
`fm__questions__answers.md`. It sits in the draft source and not in `fm/`, so it is published as a
draft and never read as a second question document.

## 6 What a writer of the content must hold to

These are the conditions under which the questions stay answerable and their answers stay attached:

1. Write to `fm/questions.md` in the project's store entry, replacing the line `No questions yet.`
   under `## Questions` with entries in the form of §4.2. Do not write into a project's own
   `promdance/` when that is a real directory rather than the link; the build reads the store's copy.
2. Number each entry so that `Q<n>` has `n` equal to the reference's `NNN` without leading zeros.
   The finder returns only the last run of labels that ascend by one, so the numbers must start at
   `Q1` and have no gaps. This requires firstmate's per-project series to start at 001 and to be
   gapless.
3. Never delete or renumber an entry. A settled question is ticked `[x]` and stays. Deleting one
   breaks the run and hides every later question. Renumbering one moves its stored answer onto
   another question, because the label is half of the answer's key.
4. Keep the question itself on the item's first lines, with no blank line inside it, and the
   references in the indented paragraph after the blank line.
5. The `<PROJECT>` part of a reference is firstmate's name for the project. docstrap does not read
   it and does not check it. The page names the project's docstrap slug in its opening paragraph
   for matching.

## 7 Architecture and tradeoffs

### 7.1 Why the site name is `fm/questions`

The store entry is a `draft` source, and docstrap gives a draft file no document identity:
`projectscope` names it nothing and walks past it. Every answer route resolves its document through
those calls, so a file published at `promdance/fm-questions` was a page whose answers were all
refused. Two alternatives were weighed.

The first was an exception inside docstrap letting a plugin name particular files in its draft
source as documents. That needs a change in docstrap's own repository and a new pin. The second,
which was taken, keeps the file in the store and contributes its directory as a non-draft source.
That needs nothing from docstrap but the plugin seam it already has. A source's mount may not lie
inside another, so the mount cannot be `promdance/fm`, and the published name is `fm/questions`.
The file itself is still promdance's, in the store, and never in a repository.

### 7.2 Why `Q<n>` labels and not the `docstrap-questions` directive

The directive keys an answer on its own `:question-id:`, which could have been the firstmate
reference itself, with no numbering rule to keep. But directive questions are answered only by the
inline form on the page. The question panels, `/api/answers` and `docstrap questions` list only
`Q<n>` items, so directive questions would be invisible where the captain answers questions in bulk.
Numbered items keep this document on the one question flow every other document uses. The cost is
§6(2) and §6(3): the label has to track the reference, and an entry can never be removed.

### 7.3 Why the role is `firstmate-questions`

A role other than `draft` is what gives the document an identity. A role other than
`documentation` gives it its own group on the project's landing page rather than mixing it with the
project's documents. Roles are an open vocabulary and docstrap treats only `draft` specially, so
nothing else changes.

### 7.4 What the `fm` mount takes

The `fm` mount is a slot docstrap owns at the top of the published project. A project whose own
documentation root has a top-level `fm/` directory would have that directory shadowed in the site.
A project that declares a source mounted at `fm` keeps it, and its firstmate questions are not
added, because a declared source wins its mount.

## 8 Not built

Populating the questions is not part of this change. Firstmate writes each project's entries,
their references and their links from its own registry, in a separate pass, under the conditions
of §6. Until then every project's document is the bare scaffold.
