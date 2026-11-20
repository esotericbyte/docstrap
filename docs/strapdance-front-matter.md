# strapdance front-matter — writing it by hand

This is the shared context standard for docstrap and promdance. The full
specification is `data/spec-context-frontmatter.md` in the firstmate data
directory; this page is the part you need when you are editing a document
in nvim and want to know what to type.

The short version: markdown documents stay files, YAML front-matter
carries context, and everything you leave out is worked out from where
the document sits and what it says. **No document has to be touched to
participate.**

## 1 The namespace

Everything this standard owns lives under one top-level key, `strapdance`.

```markdown
---
strapdance:
  kind: proposal
  relates_to: [docs/adr/0009-hosted-app-routes.md]
  answers: type2-url-grammar
some_other_tool:
  whatever: it wants
title: a bare key this standard does not own
---

# The document starts here
```

Three consequences worth stating plainly.

1.1 The reader reads **only** its own namespace. Every other top-level key
is preserved byte for byte and ignored — key order, comments, spacing and
all. A namespace it does not recognise is never an error, so you can put
another tool's block in the same document and neither tool will disturb
the other.

1.2 Two tools may hold different values for the same idea in their own
namespaces. Neither is authoritative for the other and neither reconciles
them. That is the point of scoping, not a defect.

1.3 Bare, un-namespaced keys such as the `title` above are read as a
**compatibility fallback only**, and a namespaced value always beats a
bare one. The reader never writes a bare key, so it can never take a name
another tool may want.

## 2 The fallback chain

Every field resolves in this order and stops at the first hit.

1. **Explicit** — what the front-matter says. Namespaced first, then a
   bare key.
2. **Position** — the document's directory names and path.
3. **Content** — the document's own text.
4. **Unknown** — stated outright. Nothing is ever guessed silently.

The reader tells you which step answered, for every field, so a tool can
always show you what was declared versus what was inferred:

```python
from docstrap.strapdance import read_context

ctx = read_context(Path("docs/proposals/thing.md"))
ctx.kind.value    # 'proposal'
ctx.kind.step     # ChainStep.POSITION
ctx.kind.detail   # 'parent directory `proposals`'
```

## 3 The fields, and what happens when you omit them

| Field | Meaning | What you get if you leave it out |
|---|---|---|
| `id` | stable identifier | slug of the path relative to the collection root |
| `title` | human name | the first level-1 heading, else the filename de-slugged |
| `kind` | what sort of document | the parent directory name, mapped (see §3.1) |
| `status` | lifecycle state | see §3.2 |
| `project` | owning project | see §3.3 |
| `relates_to` | documents this one bears on | **nothing** — stays empty |
| `answers` | the question or document this responds to | **nothing** — stays empty |
| `created` / `updated` | dates | git history of the file; filesystem mtime when untracked |

`relates_to` and `answers` are the two fields with no honest fallback, and
they are exactly the two a directory could never express. They are the
reason the standard earns its keep. If you write nothing else, write
these.

Keep the field set this small. Anything derivable should be derived.

### 3.1 `kind` from the directory

`drafts/`, `proposals/`, `plans/`, `notes/`, `adr/`, `research/`, `spec/`,
`templates/` and `memories/` map to the singular kind. Singular directory
names work too. Any other parent directory leaves `kind` an explicit
unknown rather than a guess.

### 3.2 `status` is an open vocabulary

Write whatever you want. There is no enum, nothing is rejected, and an
unrecognised value is preserved verbatim — not coerced, not mapped, not
even case-normalised. These values simply already have a directory that
implies them:

| value | meaning | directory that implies it |
|---|---|---|
| `active` | in use now | default |
| `done` | finished | `done/` |
| `archive` | kept as record | none today |
| `reusable` | kept to run again | `templates/` |
| `reference` | kept to consult | `memories/`, `notes/` |

`hold/` means active-with-work-paused rather than a distinct value, so a
document there resolves to `active` and the provenance says why.

If no directory implies a status, the reader looks for a `Status:` line in
the document's opening lines — the shape the captain's own documents
already use:

```markdown
# The strapdance roadmap

Status: ROADMAP, 2026-08-25.
```

That yields `ROADMAP`, marked as coming from **content**, so a classifier
shows it as inferred. It is deliberately narrow: only the opening lines,
only outside fenced code, and only the first word. Failing that, `active`.

### 3.3 `project` — the field for a document at a repo root

A prompt or spec often sits at the root of a repo while actually belonging
to one workspace member. Position cannot express that, because the
position *is* the root. `project` is the only answer, and it names a uv
workspace member by its package name:

```markdown
---
strapdance:
  project: docstrap
---
```

When you omit it: the nearest enclosing `.docstrap` project entry, then
the uv workspace member whose directory contains the document, then the
workspace root. A root-level document with no `project` resolving to the
workspace root is honest rather than wrong.

## 4 Not examined, declined, classified

Three states, two of which look identical on disk:

1. **Not yet examined** — no `strapdance` key. Nobody has looked. The
   chain applies and everything still resolves.
2. **Examined and declined** — someone looked and decided this document
   carries no meaningful context, or should not carry front-matter:

   ```markdown
   ---
   strapdance:
     declined: true
   ---
   ```

   This is a positive recorded fact, not an absence. Without it, any
   continual tool re-offers the same half-finished document forever.
   A declined document is skipped by sweeps and classifiers and remains
   an entirely normal document in every other respect.
3. **Classified** — the namespace is present and carries at least one
   field.

An empty `strapdance: {}`, or one holding only `declined: false`, records
no decision and stays *not examined*.

## 5 What the reader will not do

5.1 **It never rewrites a document to add front-matter.** Absence is a
valid state. Materialising inferred metadata into your files is a
different actor's job — a sweep you run deliberately, which reports first
and round-trips foreign namespaces untouched.

5.2 **A malformed block is reported, not repaired.** Broken YAML, an
unterminated `---`, a `strapdance:` key that is a string instead of a
mapping: each is reported through `ctx.errors`, the file is left exactly
as it was, and the document still resolves through the rest of the chain.

5.3 **An unknown key is preserved and ignored**, never stripped.

## 6 Running the tests

docstrap is not currently a member of the platformshoes uv workspace, so
run its tests against the package directly from the workspace root:

```bash
uv run --project packages/docstrap pytest packages/docstrap/tests
```

The fixture documents in `packages/docstrap/tests/fixtures` are real
files; the tests copy them into a temporary directory and read them end to
end, including the round-trip proof that a document carrying a foreign
namespace and bare keys comes back byte for byte.
