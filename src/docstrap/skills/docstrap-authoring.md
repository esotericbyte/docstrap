---
name: docstrap-authoring
description: Guide Claude when authoring or editing documentation in docstrap-managed repositories. Covers MyST directive/role invocation of Sphinx features, {eval-rst} escape hatch templates for RST-only features, cross-referencing across the MyST/RST boundary, mermaid diagram syntax, and the docstrap widget directives (docstrap-questions, docstrap-datatable, docstrap-tasks).
trigger:
  - Editing .md files under a docs/ directory in a repo that has a .docstrap file
  - User asks about MyST, Sphinx, docstrap syntax, or how to use a Sphinx feature from Markdown
---

# docstrap authoring

Documentation in docstrap-managed repositories is authored in **MyST-Markdown** (the CommonMark superset the `myst-parser` Sphinx extension consumes). MyST gives you almost every Sphinx feature from a Markdown file. This skill covers the invocation syntax, an `{eval-rst}` escape hatch for the small set of RST-only features, cross-referencing, mermaid diagrams, and docstrap's own widget directives.

## Directives — three syntaxes

MyST recognises Sphinx directives in three surface forms. Prefer them in this order.

### Colon fence (recommended for most cases)

```
:::{note}
This is a note admonition. Body content goes here, may span
multiple paragraphs, and may contain nested MyST.
:::
```

Options as an inline map:

```
:::{figure} /images/foo.png
:alt: Foo
:width: 60%

Caption text goes below the directive with a blank line between.
:::
```

### Backtick fence (interchangeable with colon fence)

```
```{note}
Same as the colon-fence form; use whichever your file already uses.
```
```

Use backticks when the body contains colon-fenced blocks (avoids fence collisions).

### Inline roles

```
Use {ref}`section-label` for cross-references and {doc}`../plans/foo` for whole-doc links.
```

Roles are single-line; directives are block-level.

## The `{eval-rst}` escape hatch

Some RST-only features have no MyST-native equivalent — most notably `list-table`, complex `figure` combinations, and third-party directives that MyST doesn't recognise. Use `{eval-rst}`:

```
```{eval-rst}
.. list-table:: Comparison
   :header-rows: 1
   :widths: 20 40 40

   * - Option
     - Pros
     - Cons
   * - A
     - Simple
     - Rigid
   * - B
     - Flexible
     - Configurable
```
```

RST inside `{eval-rst}` follows normal RST rules — three-space indent for directive content, blank lines between directive and body.

Templates for the most common RST-only cases:

**list-table** (for tables with rich cell content):

```
```{eval-rst}
.. list-table::
   :header-rows: 1

   * - Header 1
     - Header 2
   * - Cell 1
     - Cell 2
```
```

**Complex figure with substitution**:

```
```{eval-rst}
.. |arch| image:: /images/arch.png
   :width: 100%

.. figure:: /images/main.png
   :alt: System overview
   :align: center

   |arch|

   Caption paragraph.
```
```

**Third-party directive**:

```
```{eval-rst}
.. mermaid::

   graph LR
     A --> B
     B --> C
```
```

(Though mermaid has a MyST-native form — see below.)

## Cross-referencing across MyST/RST

### Referencing headings

Add an explicit label using MyST's `(label)=` syntax before a heading:

```
(intro-section)=
## Introduction
```

Then reference from anywhere in the same project:

```
See {ref}`intro-section` for background.
```

References work identically from MyST and from `{eval-rst}` blocks.

### Referencing other documents

```
Full doc: {doc}`../plans/foo`
Section in another doc: {ref}`bar-section`
```

### Auto-generated heading anchors

`myst_heading_anchors = 4` is enabled in docstrap's config, so every heading up to level 4 gets an implicit slug. Reference with:

```
See [The point](#the-point) — auto-slug from a level-N heading.
```

Prefer explicit `(label)=` when the anchor should be stable across heading text changes.

## Mermaid diagrams

Docstrap's config sets `myst_fence_as_directive = ["mermaid"]`, so a plain fenced code block with `mermaid` as the language is rendered as a diagram:

````
```mermaid
graph LR
  A[Start] --> B{Decision}
  B -->|yes| C[Do X]
  B -->|no|  D[Do Y]
```
````

Sequence diagrams, class diagrams, state diagrams, ER diagrams, and gantt charts all work. See mermaid's own docs for syntax per diagram type. No special handling — the fence is enough.

## Docstrap widget directives

Docstrap ships three Sphinx extensions loaded by default in the markdown layout. Each renders interactive elements in the built HTML.

### Q&A widget: `docstrap-questions`

Embeds a form target in the rendered page. Submissions POST to docstrap's app server (`/api/tools/<project>/<doc-slug>/answers`) and are kept in the project's draft root: the directory an enabled plugin provides, or else the project's declared `draft` source.

```
```{docstrap-questions}
:question-id: q-tradeoffs-1
:prompt: What tradeoffs matter most for approach X versus approach Y?
```
```

- `question-id` is required and must be unique within the document.
- `prompt` is the visible question text. If omitted, the block body is used as the prompt.
- Answers are kept in `answers.md` in the draft root, and each answered document gets `<doc-slug>__answers.md` beside it there.

### Data table: `docstrap-datatable`

Puts a sortable, filterable table on the page from a JSON file beside it. The one argument is the file's path, relative to the page.

````
```{docstrap-datatable} census.json
```
````

The file is `{"columns": [...], "rows": [...]}`. Each column has a `key`, a `label`, a `type` (`text`, `date`, `enum`, `symbol` or `link`), and optionally `sortable` (default true) and `filterable` (default false); an enum or symbol column may list `values` in order, a symbol column maps values to `symbols`, and a link column may name the row field holding its target in `href`. A link target naming a document relative to the page (`tasks/fm-12`) is resolved to its built page. Unknown keys and malformed values fail the build naming the field.

### Task list: `docstrap-tasks`

Puts firstmate's open tasks on the page from the `tasks.json` firstmate writes beside it. The one argument is the file's path, relative to the page. The file is firstmate's to write; do not hand-edit it.

````
```{docstrap-tasks} tasks.json
```
````

Inside the viewer the list groups by project or status, drills into a group, sorts, filters, and records one decision per task in the project's answer store.

### Status badge (automatic)

No directive needed. The status tool injects a per-page meta tag with the document's docstrap ID; the status badge appears next to the H1 automatically when the docstrap app server is running.

### Sentence-checkmark review (automatic, opt-in per session)

No directive needed. Open the "Tools" launcher in the corner and tick **Review**. That enables per-sentence tri-state marks (empty / ✓ / ✗) and per-section marks. On submit, a timestamped review file lands in the project's draft root with YAML frontmatter carrying the marks.

### The tools launcher

Every on-page tool is shown and hidden from one control in the corner. "Hide all" turns everything off and "Dismiss" removes the launcher itself, at which point the page reads as a plain document — worth doing before sharing a rendered page. Alt+T brings the launcher back.

## Frontmatter (YAML at top of file)

MyST accepts YAML frontmatter that becomes docutils metadata:

```
---
title: The proper title (overrides the H1)
author: A. Author
tags:
  - proposal
  - architecture
---

# The document
```

Docstrap does not read this frontmatter for status/tags — those live in the metadata DB. Frontmatter is for Sphinx-side rendering only.

## Small gotchas

- **Blank lines matter.** MyST requires blank lines between directives and their content, before and after headings, and around block-level constructs. When a block silently doesn't render, look for a missing blank line first.
- **Indent inside `{eval-rst}` is three spaces**, not four. Copying Python code style into RST leads to silently-ignored options.
- **`:ref:` targets need to be unique across the whole project.** Prefix with the document slug (`(myproject-intro)=`) for large multi-doc projects to avoid collisions.
- **Mermaid inside a `{note}` admonition** works but sometimes renders below the admonition due to CSS layering. Prefer top-level mermaid blocks.
- **Cross-document references use forward slashes** even on Windows: `{doc}`../plans/foo`, not backslashes.

## When authoring, always

1. Preserve the file's existing directive style (colon fences vs backtick fences) — don't mix.
2. Add `(label)=` before headings that will be referenced.
3. Escape user-visible angle brackets when quoting HTML in prose (`\<script\>`).
4. Test locally with `docstrap build` before committing significant structural changes.
5. If a directive appears not to work, check `docstrap build`'s Sphinx warnings — they usually name the file and line.
