# Tools and instruments

How docstrap's on-page apparatus is organised: what a tool is, what declares one, the extension
points a tool attaches to, and how to add one. The architecture is the captain's, settled
2026-08-27; this document is the implementation's account of it.

## 1 The two kinds

A **tool** is usable from the standard document view. It works in place, and the page you were
reading is still the page you are looking at. An overlay or a popover drawn on the page is still a
tool.

An **instrument** brings up a separate component, or navigates away from the standard main view. It
may sculpt the workpiece or measure how it stands up.

The boundary test is only this: if the standard document view is still the thing you are looking at,
it is a tool; if the view is replaced or left, it is an instrument.

### 1.1 Tools and instruments are both built; tools are Svelte

Tools were originally written in vanilla JavaScript with no build step, for MkDocs and Quarto
portability. **That constraint is withdrawn** (captain, 2026-08-27: "svelte unless it's truely
tiny"). It was protecting a capability that does not exist — the MkDocs and Quarto layouts are stubs
that raise not-implemented — while the cost of hand-written UI was paid on every tool, every day.

So **a tool's UI is Svelte**, compiled to the bundle its declaration names. Hand-written client
source survives only for pieces that are genuinely tiny; `docstrap-common.js` and
`docstrap-launcher.js` are still hand-written, and converting the launcher is a separate decision
from this one.

Two things the kind still decides, and they still follow from §1:

1. **Per-page cost is a tool's problem and not an instrument's.** A tool is registered on every
   rendered page, so what it weighs is paid on every page view inside the viewer; an instrument
   loads on demand. A page opened on its own runs no tool at all (§3.2). §5.1 records what the
   tools weigh and where the next lever is.
2. **Skeleton is for instruments only.** A tool renders inside a page whose styling Sphinx and the
   furo theme own, and a Tailwind-based toolkit risks collisions in both directions. Tools use
   Svelte's scoped component styles. An instrument owns its own view and may use Skeleton. A tool
   that draws a table builds it on TanStack Table (`@tanstack/svelte-table`), which is headless —
   it owns sorting, filtering, grouping and column sizes and draws nothing — so this rule holds:
   the data table and the task list share `tools/datatable/ui/grid.ts` and `FilterBar.svelte`.

## 2 The declaration

Each tool has one small declaration, in `declaration.py` in its own directory:

```python
from docstrap.tools.declaration import Kind, Target, ToolDeclaration

DECLARATION = ToolDeclaration(
    id="review",
    title="Review",
    kind=Kind.TOOL,
    target=Target.DOCUMENT,
    entry="docstrap.tools.review",
    api_collection="reviews",
    default_visible=False,
    summary="Mark sentences and sections, then submit a review record.",
)
```

`target` is what the tool is applied to — the workpiece. A document-targeted tool needs a document;
a project-targeted one needs a project, which is why a project-targeted classifier is never offered
on a lone page with no project to act on.

The declaration is the single source of truth. Three consumers read it, and none holds its own copy
of what it says.

1. **The server** derives the route prefix. The target picks the base and the tool names the
   collection it owns, so `Target.DOCUMENT` plus `api_collection="reviews"` gives
   `/api/promdance/{project}/{doc_slug}/reviews`. `server.py` contains no tool URL. A tool that owns
   no collection declares `api_collection=None` and mounts nothing — the status badge is one,
   because it reads the shared `/api/documents` metadata API rather than a namespace of its own. A
   tool serving its collection under the other base too declares `also_scoped_to`, and its
   `route_prefixes` is then both.
   `{project}` is the project's **slug**, never its title: the build carries the scanned slug into
   the generated `conf.py` as `docstrap_project_slug` and the page context reads it back. A tool
   addressing the project by its title wrote its derivatives into a directory the project does not
   link to, and nothing errored.
   A page that belongs to **no** project carries no project, and nothing invents one for it. A
   store's landing page lists projects and is not one; slugifying its title gave the captain's site
   front page `docstrap-project="fleet-queue"`, naming no store and no directory, so launching the
   panels there 404ed. `tool_support.is_aggregate_build` tells that case from a site built on
   somebody's own `conf.py`, which does have a project docstrap never scanned and where the title
   fallback stays. With no project the launcher offers nothing needing one, which is the correct
   answer and one it already knew how to give.
2. **The launcher** reads `kind` and `target` to decide whether to offer the tool where the reader is
   standing, and renders a toggle for a tool or a launch action for an instrument.
`{doc_slug}` is a **path**, not a segment. A document's identity is its path below the project's
`docs_root` with the suffix dropped — `proposals/0002-the-upgrade-path` — which is what
`projectscope.document_slug` returns and what the page carries in its `docstrap-doc-slug` meta tag.
The route carries it as a path (`{doc_slug:path}` to the router; `as_server_path` is the one
translation between the declaration's spelling and the router's) and the launcher percent-encodes
every reserved character except the separator. Spelling that identity as one segment is what made
every document-targeted tool 404 on every document below a project's root — 666 of 686 published
pages — while the panel reported the server as absent. It was not repaired by flattening the
identity: a document management tool handles paths.

A tool that owns a collection mounts **on its prefix**, distinguishing operations by method rather
than by a sub-path: the qapanels instrument reads with `GET` and writes with `POST` on
`/api/promdance/{project}/qa`. A sub-path is not merely untidy — a project prefix plus one segment has
exactly the shape of a document-targeted prefix, so `…/{project}/qa/answers` is captured by the qa
tool's `…/{project}/{doc_slug}/answers` with a `doc_slug` of `qa`, which is what happened.

**That is now checked rather than argued.** A project URL has exactly one segment after the project
and a document URL has two or more, so the two shapes stay disjoint — but only while no route
reaches deeper than a base plus one static collection. `declaration.check_route_separation` enforces
that over every path a tool returns, at mount time, and `mount_all` calls it, so a tool that declared
its way into the ambiguity cannot start the server.

A tool needing a **second scope** rather than a second operation declares it. `also_scoped_to` names
the other target, `route_prefixes` becomes both prefixes derived from the same base map, and the
routes module mounts what it is handed. The qapanels instrument is the one that does: its questions
listing is readable project-wide and narrowed to one document. Nothing else may mount a path outside
what its declaration derives, and `test_tool_declarations.py` compares the server's whole route table
against exactly that.

3. **The build** names the bundles: `docstrap-<id>.js` and `docstrap-<id>.css`. Because ids are
   unique, the flattening Sphinx does across every `html_static_path` entry is collision-free. The
   generated `conf.py` gets its `extensions` list from the declarations too, so a new tool reaches
   the built site without the layout template being edited.

## 3 The single visibility launcher

One control owns what is showing. Before this, each widget injected its own floating button into the
same corner with no arbitration; that was the defect removed here.

The launcher reads declarations, offers only what is valid for the current target, and lets the
reader show and hide each tool. Its state persists in `localStorage`, and each tool's
`default_visible` decides what happens before anyone has said otherwise.

The decision of *what to offer* lives in Python (`docstrap.tools.launcher`), not in the browser. The
build computes the offer list for a page and serialises it into a `<script type="application/json">`
in the head; `docstrap-launcher.js` renders what it is given. That keeps the target-validity rule in
one testable place, and it means the launcher's client code never needs to know a tool exists.

The launcher holds no visibility state of its own either — `window.docstrap.tools` owns that, and the
launcher is a UI over it. Both splits are deliberate: a second control (a keyboard shortcut today, a
three-panel mode later) can drive the same state without either becoming the owner.

### 3.1 A page with every tool hidden reads as a plain document

This matters if a page is ever shared. Three things hold it up:

1. Every piece of tool apparatus is either injected by that tool's `show()` or gated behind the
   launcher's `docstrap-show-<id>` body class. The HTML as built carries no tool chrome, so a page
   opened without JavaScript, or shared as a file, is already plain.
2. "Hide all" turns every tool off; "Dismiss" additionally removes the launcher from the page
   entirely. Alt+T brings it back.
3. Anything a tool puts on the page that is apparatus rather than document carries the shared
   `.docstrap-chrome` class, which is excluded from print.

The question directive is the one piece of tool markup that is in the built HTML, because its author
put a question in the document. The prompt is document content and always reads; the answering
apparatus below it carries `.docstrap-chrome` and is gated, so with the tool hidden a question reads
as a plain callout with nothing to submit.

### 3.2 A page opened on its own runs only the viewer button

Tools run inside the viewer shell and nowhere else. A published page opened directly is the
document and one small button, bottom right, that replaces it with the viewer showing that same
page — `viewer.html?doc-url=<the page's site-relative URL, encoded>`. Nothing on it loads Svelte.

The mechanism is one type attribute. Every tool bundle, `docstrap-common.js` and the launcher are
registered through `tool_support.add_deferred_js_file`, which gives their `<script>` tags the type
`text/x-docstrap-deferred`; a browser neither fetches nor runs a script of a type it does not know.
`docstrap-viewer-button.js`, the one script registered normally (by the `docstrap.sphinx.viewer_button`
extension, after the launcher), decides the page's state and writes it on the root element:
`data-docstrap-view="page"` at the top level, where it draws the button, and `"framed"` inside a
frame, where it replaces each held script with a real one, in page order. The button's stylesheet
shows it only under `page`, so it cannot appear inside the viewer whichever runs first. Stylesheets
are not held back: the qa form's gate is a CSS rule on the directive's own markup and has to hold
with no script at all.

The address is composed at build time, beside the manifest the viewer reads
(`viewer.manifest.open_in_viewer_href`), from where `docstrap build` says the build sits below the
site the shell is published at (`docstrap_viewer_base` in the generated `conf.py`). It arrives in a
`docstrap-open-in-viewer` meta tag; a page with no shell above it carries none and draws no button.

## 4 Extension points — the public surface

These are the seams a tool attaches to. **A tool must use these and nothing else.** It must not patch
another module's internals at runtime, and no shared module may carry a special case that only one
tool could ever use. Adding a tool may legitimately require adding or extending a hook here — the
question to ask of any new one is "would another tool or instrument need this same hook?" If yes,
define it, name it, document it in this section. If no, it is a one-off and the design is wrong.

### 4.1 Python

| Extension point | What it is for |
|---|---|
| `docstrap.tools.declaration.ToolDeclaration` | The declaration object itself. Everything below reads it. |
| `docstrap.tools.registry.discover_in(package, path)` | Registration by directory. Any importable package laid out this way is a tool source, so tools can ship from outside docstrap. |
| `<tool>.declaration.DECLARATION` | The module attribute discovery looks for. Its presence is the registration. |
| `<tool>.setup(app)` | The Sphinx entry point, named by `declaration.entry`. |
| `<tool>.routes.register(app, declaration)` | The server seam. Reads the path off the declaration it is handed and returns the paths it mounted. Optional; omit the module if the tool serves no API. |
| `docstrap.tools.mounting.mount_all(app, declarations=None)` | Mounts every declared tool's routes. The server calls this once and names no tool. |
| `docstrap.sphinx.tool_support.register_tool_assets(app, declaration)` | The build seam. Registers the tool's `static/` dir and whichever declared bundles it ships, the script held back until the page is inside the viewer. |
| `docstrap.sphinx.tool_support.add_deferred_js_file(app, filename)` | Registers a script that runs only inside the viewer (§3.2). Every tool script goes through it; a shared script a tool depends on must too. |
| `docstrap.sphinx.tool_support.inject_page_metatags(app, pagename, context)` | Puts the `docstrap-*` page metadata in the head. Cumulative and idempotent. |
| `docstrap.sphinx.tool_support.page_context(app, pagename)` | The page's `PageContext` — what workpieces are available here. |
| `docstrap.tools.launcher.is_valid_here` / `offers_for` / `offer_payload` | The offer rule and the client projection. Reads kind and target only. |
| `docstrap.tools.derivatives.promdance_project_root(slug)` | Where a tool's derivative document (an answer set, a review record) is written. Composes nothing itself — it asks `docstrap.paths`, the single owner of the promdance storage path. |
| `docstrap.projectscope.resolve_slug(slug)` | The project a request's slug names, resolved through the registered-stores list. A tool holding a page's project slug gets the project back without composing a path from it. |
| `ProjectScope.document_slug(path)` / `document_for_slug(slug)` / `display_path(path)` | The two directions between a source document and the docname its rendered page carries, plus how a path is written for a person. Both the qa tool and the qapanels instrument need them, which is why they are here and not in either. |
| `docstrap.answers` | The one owner of a project's answer file, and of the key an answer hangs on. Two tools write through it; nothing else reads or writes the format. `docs/spec.md` §8.1. |
| `docstrap.slugs.slugify(value)` | The one slug function. Nothing else in docstrap turns text into a name, and no tool should. |
| `docstrap.tools.registry.sphinx_extensions()` | What the generated `conf.py` `extensions` list is built from. |
| `<tool>/ui/index.ts` | The frontend build's registration, on the same "the directory is the registration" rule. A tool with no `ui/` is not built and keeps whatever is in its `static/`. |
| `docstrap.tools.frontend.build_targets()` | What `build-tools.mjs` reads: every tool that has a `ui/`, where its output goes, and the two filenames its declaration derives. Nothing on the Node side spells a tool id or a bundle name. |

### 4.2 Client

| Extension point | What it is for |
|---|---|
| `docstrap.tools.register(id, {show, hide})` | A tool declares its two visibility handlers and nothing else. Called at script-evaluation time; the launcher decides when to call `show()`. |
| `docstrap.tools.route(id)` | The concrete URL of that tool's API on this page, resolved from its declaration at build time. **A tool never assembles a path.** |
| `docstrap.tools.altRoute(id)` | The same for a tool that declared `also_scoped_to` — its collection under the other target's base — or `null`. Choosing a scope in the browser is choosing between two resolved URLs, not editing one. The qapanels instrument is the only tool with one. |
| `docstrap.tools.isVisible(id)` / `setVisible(id, on)` / `hideAll()` | The visibility state. |
| `docstrap.tools.offers()` / `offer(id)` | The offer list the build computed. |
| `docstrap.tools.onChange(fn)` | Notification when visibility changes. |
| `docstrap.api` / `onReady` / `silenceOfflineError` | Shared services: the fetch wrapper, DOM-ready, and the handler that keeps an absent server silent. |
| `declaration.visibility_class` → `body.docstrap-show-<id>` | The CSS visibility seam, for chrome that is in the HTML already rather than injected. |
| `html[data-docstrap-view]` | The page's state: `page` when opened on its own, `framed` inside the viewer. Written before any tool runs, so CSS can depend on it. |
| `.docstrap-chrome` | Marks an element as apparatus rather than document, so anything can reason about tool chrome as a category without enumerating tools. Excluded from print. |
| `sphinx/ui/docstrap.ts` → `requireDocstrap(id)` | The typed view of everything above, plus the guard every tool opens with. It belongs to no tool and names none; a tool passes its own id in. |

## 5 Adding a tool

Make a directory under `src/docstrap/tools/`, and write a declaration in it.

```
src/docstrap/tools/glossary/
├── __init__.py         # setup(app) — calls register_tool_assets(app, DECLARATION)
├── declaration.py      # DECLARATION = ToolDeclaration(...)
├── routes.py           # optional: register(app, declaration)
├── views.py            # optional: directives
├── ui/                 # SOURCE — Svelte components and the entry module
│   ├── index.ts        #   registers show/hide with the launcher
│   ├── Glossary.svelte
│   └── glossary.css    #   optional: rules that must be global, with a reason
└── static/             # BUILT — committed, so installing needs Python only
    ├── docstrap-glossary.js
    └── docstrap-glossary.css
```

That is the whole procedure. Discovery finds the directory, so there is no registration list to
append to and no way to forget one. The route prefix, the launcher offer, and the bundle names all
fall out of the declaration. `ui/index.ts` is likewise the registration for the frontend build:
`docstrap.tools.frontend` lists every tool that has one and tells `build-tools.mjs` where its output
goes and what the declaration calls it, so nothing on the Node side spells a tool id or a filename.

Removing a tool is deleting the directory.

### 5.1 Per-page cost

`npm run build` in `packages/docstrap` compiles `ui/` into `static/`, and prints what each bundle
weighs. What it printed when the three tools were converted, against what the hand-written versions
weighed:

| tool (js + css) | hand-written | Svelte | Svelte, gzipped |
|---|---|---|---|
| status | 3.2 kB | 32.3 kB | 12.5 kB |
| qa | 4.8 kB | 35.8 kB | 13.9 kB |
| review | 9.3 kB | 37.6 kB | 14.4 kB |
| **all three** | **17.2 kB** | **105.7 kB** | **40.8 kB** |

Two things moved those numbers on 2026-09-07. The qapanels instrument added a fourth bundle at
49.0 kB, and the build target of §5.2 took roughly 3.5 kB off each of the other three. 

On 2026-10-12 tools stopped running on a page opened on its own (§3.2), which is what moved the cost
a reader of a plain page pays. Measured on a nested page of a multi-store sample build, the docstrap
assets it fetches went from **203,038 B raw, 77,669 B gzipped** — seven scripts, five of them carrying
a Svelte runtime, and seven stylesheets — to **24,601 B raw, 8,907 B gzipped**: the 3.4 kB button
script and the same stylesheets plus the button's. Inside the viewer a page still loads every bundle,
so the shared-chunk lever of §5.2(2) is unchanged there.

On 2026-10-14 the data table and the task list moved onto TanStack Table, and each bundle carries its
own copy of it: `docstrap-datatable.js` went from 59,173 B (22,231 B gzipped) to 124,807 B (39,721 B),
and `docstrap-tasks.js` from 79,944 B (29,041 B) to 146,640 B (46,899 B) — about 35 kB gzipped more on
the first page a reader opens in the viewer, cached after that. Sharing one chunk between the two
(§5.2(2)) is the lever, now with a second library behind it.

### 5.2 The build target is not a detail

`build-tools.mjs` pins `target: 'es2022'`. Vite's default target downlevels native private class
fields (`#field`) into WeakMap plumbing, and Svelte 5's error boundary reads a private field from a
method that can run before the downlevelled assignment has happened.

The symptom is worth knowing because it names nothing useful. A tool mounts perfectly unminified and
throws `TypeError: Cannot read properties of undefined (reading 'onerror')` from inside Svelte's own
runtime once built — and because that throw happens *in the error handler*, it replaces whatever the
real error was. There is no stack frame in your component and no message about your code. If you ever
see that error, look at the build target before looking at what you wrote.

Nearly all of the increase is one tree-shaken copy of the Svelte runtime per bundle — the tool code
itself is 1.3–4.4 kB. Two ways to stop paying for it three times were considered and neither is
taken here:

1. A shared runtime in an IIFE that the bundles resolve against as a global. Measured: no saving at
   all, because a runtime exported wholesale cannot be tree-shaken and comes to as much as the three
   tree-shaken copies together.
2. ES-module bundles sharing a chunk. This does work — roughly 40 kB raw, 13 kB gzipped for all
   three — but it changes how a tool's bundle is *served*: `register_tool_assets` would have to emit
   `<script type="module">`. That is the declaration's asset surface, so it is a decision to take
   deliberately rather than a build detail to slip in. It is the obvious next lever, and it gets
   better with every tool added, not worse.

If a tool you are adding needs something the table in §4 does not have, add the hook there rather
than working around it — and apply the test in §4: a hook another tool would also need is a real
extension point; a hook only yours could use means the design is wrong and should be said so rather
than shipped.

`tests/test_extension_points.py` builds a whole new tool from scratch in a temporary package and runs
it through every consumer using only these seams. If a future change makes a special case necessary,
that test is where it will show up.

## 6 What this deliberately does not do

Nothing is altered in place, and that property is uniform: the front-matter reader never writes, the
tools never write to a source document, and the sweep only proposes. A tool produces an edit
instruction, a new draft, or a derivative document beside the original. That is what makes it safe to
point any of this at a clone, a read-only checkout, or someone else's repository.

Not built here, and each deliberately a later phase: build-time block provenance stamping, the
quick-update tool that needs it, and the classifier instrument. The refactor landed first so the
classifier would not become the fourth widget bolting its own button into the same corner. The
three-panel Q&A instrument was on that list and is now built — `docstrap.tools.qapanels`, and it uses
exactly the seam §3 said a second control would: it drives `docstrap.tools` visibility without owning
it.

## 7 Verification

The automated half is in `tests/`:

- `test_tool_declarations.py` — each declaration drives route prefix, launcher offer and bundle
  naming, checked against the consumers rather than against literals.
- `test_launcher.py` — the target-validity rule, over synthetic declarations of both kinds and both
  targets.
- `test_rendered_page.py` — a real `sphinx-build`, then assertions that the built HTML carries no
  injected tool chrome, that a page **below the root** resolves its tool URLs as paths, and that
  no per-widget floating button — and no second client surface claiming the server is down —
  survives anywhere in the source.
- `test_nested_document_routes.py` — every document-targeted route filled in with a real document
  two levels below `docs_root` and driven through the real matcher, plus the project scope proving
  it is not captured. `test_tool_declarations.py` compares templates; this compares URLs, which is
  the gap that let the nested-document defect live as long as it did.
- `test_page_project_context.py` — which page has a project. An aggregate is given none rather than
  one invented from its title; a foreign Sphinx site keeps its best-effort guess.
- `test_extension_points.py` — a new tool stood up through the seams alone.
- `test_datatable.py` — the data table's file format and its refusals, the directive through a real
  nested `sphinx-build`, and its sorting and filtering by running `tests/datatable/table.test.ts`
  under Node, which drives a real TanStack table built from `ui/table.ts` and `ui/grid.ts`.
- `test_tasks.py` — the task tool's reading of firstmate's `tasks.json` and its refusals, the
  directive through a real nested `sphinx-build`, a decision's key in the answer store asserted
  literally, the decisions route and the "answers done" route it hands out driven through the real
  app, and the columns, grouping, drill-down and address rules of `ui/tasks.ts` by running
  `tests/tasks/tasks.test.ts` under Node against a real TanStack table.

**Every sample project in a browser run here is flat, and that is a hole.** Neither run below has a
subdirectory, so neither could see that a document below `docs_root` was unreachable through every
document-targeted route — the defect repaired on 2026-09-23, which had been there since the feature
shipped. The two files above close it without a browser. A browser run made against a flat project
is proving the 3 % case; build the sample nested.

The interactive half is not in `tests/`: it needs a browser, and a browser is not a dependency this
package should acquire. It was driven instead against a real built sample site — a one-page Sphinx
build with every declared tool loaded, a `docstrap-questions` directive, two `h2` sections and a
fenced code block, registered in an isolated metadata DB with status `proposal` and served by
`docstrap.server` — in headless Chrome, scripted so it can be repeated. What it asserted, and what
it found, when the three tools became Svelte (2026-08-27, 33 of 34 checks passing; the one failure
was the page's own missing favicon):

- **status** — on load, with no interaction, the badge is the `h1`'s first child, reads `proposal`,
  carries `.docstrap-chrome`, and has its scoped palette applied (`rgb(207, 232, 255)`, the proposal
  colours). Hiding the tool removes it.
- **qa** — the launcher's `docstrap-show-qa` body class is set and the form computes to
  `display: block`; the textarea is the component's (it carries a `svelte-` scope class), not the
  directive's fallback markup; the author's prompt still reads. An empty answer is refused with
  "Answer is empty."; a real one POSTs, reports `Saved to …`, and clears the box. *(The file it
  writes changed on 2026-09-07: it is now the project's keyed `answers.md`, not a per-document
  append file. `tests/test_answers.py` is the executable half of that, and the run above is
  otherwise unchanged.)*
- **review** — nothing on the page until the tool is toggled on; then a mark at each of the two `h2`
  headings and four in the prose, none inside the code block. A mark cycles empty → ✓ → ✗ → empty.
  Submitting with one sentence on ✗, one section on ✓ and a summary wrote a review file whose
  frontmatter carried exactly those marks and whose body carried the reaction slot for the rejected
  sentence — the same format as before the conversion.
- **the launcher** — exactly one control, zero `.docstrap-review-toggle` buttons, three offers.
  "Hide all" left zero visible chrome; "Dismiss" removed the launcher, leaving a page whose rendered
  text was the title, the prose and the author's question prompt. Both survived a reload, and Alt+T
  brought the launcher back.
- **the console** — no errors and no warnings across the whole run.

The three-panel Q&A instrument was driven the same way when it landed on 2026-09-07, against a
registered two-document project built and served by docstrap itself — 39 checks, all passing:

- **the offer** — four pieces of apparatus offered, `qapanels` among them as an *instrument*, and the
  launcher gives it a launch action rather than a checkbox. Nothing of it is on the page until it is
  launched; opening it takes the view, and the root carries `.docstrap-chrome`.
- **the three panels** — the list holds the project's three `Q<n>` items grouped by their two
  documents and reports the count; picking one puts that question's answer in the editor and that
  question's *rendered page* in the reference frame, whose own tool chrome is suppressed. The editor
  is a bare `<textarea>` with no editor widget anywhere in it.
- **autosave** — nothing says "Autosaved" before anything is typed; the indicator is gone the instant
  input fires; nothing is written before the pause elapses; then one save lands and the indicator
  appears. Waiting a further 2.5 s wrote nothing more, which is the check that caught a save loop:
  re-reading the listing after a save handed the editor back the answer it had just written, and the
  backstop `$effect` counted that as an edit. Ctrl+S saved before the debounce would have fired.
- **the key** — the answer is in `answers.md` under `<doc-id>:<label>`; answering again left one row
  and one section, not two; a reload brought the answer back into the editor and marked the question
  answered in the list; and the same `Q1` in the other document got its own key.
- **the console** — no errors and no warnings across the whole run.

**The `answered` tool has not had its browser run yet.** It landed on 2026-09-14 with its build half
proved by a real `sphinx-build` (`tests/test_answered_marks.py`: which labels are marked, which are
not, and the source byte-identical afterwards) and its serving half proved as far as HTTP goes — the
page ships the marks and the bundle, and `/api/answers/{project}/{doc}` returns that page's pair. What
is outstanding is the last link: the note appearing under each question, the open marker reading as
one, and the console staying clean. Neither browser bridge was reachable in the environment it landed
in and both bundled Chrome binaries were missing system libraries, so it was not run rather than run
and passed. Drive it the way the two runs above were driven.

**The datatable tool was driven in a browser when it landed** on 2026-10-13, through
`chrome-devtools-axi` with the wrapper item 25 of the implementation record describes, against a
furo build of `tests/fixtures/datatable/census` framed so the tools run. The interactive table
replaced the plain one with the launcher offering `datatable`; a multi-select narrowed six rows to
two with the menu's counts taken under the other filters; a date header sorted ascending, then
descending, then back to file order, with `aria-sort` following; a search matched across the
searchable columns; hiding the tool restored the plain table and showing it again re-mounted the
drawn one; furo's dark theme carried through. The console held only the sample's missing favicon.

**The task tool was driven in a browser when it landed** on 2026-10-13, through `chrome-devtools-axi`
with the same kind of task-scratch wrapper, against `docstrap serve` in a redirected home over a
store holding a `tasks.json` of 117 tasks derived from firstmate's census and its 117 task pages. The
list replaced the plain table grouped by project and unit; clicking a project and then a unit
narrowed the list and wrote `tasks-in` beside `?doc-url=` in the viewer's address, and the breadcrumb
went back a step. Status grouping by state and by stuck regrouped inside the drill-down, and opening
the copied address in a fresh load restored the same part of the list. Search found a task by its
evidence alone; a facet, a date range and a column sort narrowed and ordered the groups with their
counts following; hiding and showing the tool swapped the plain table back and forth. A decision
saved from an opened row landed in `answers.md` under `<doc-id>:task/<task-id>` with the documented
prose and was marked on its row after a reload, and **Answers done** ran the configured command with
the page's project and path. Dark theme carried through, and the console was empty. The bridge's own
`screenshot` reported success and wrote nothing, so screenshots were taken with Playwright on the
same Chromium.

That run is also what found the route collision §2 now describes and the build target §5.2 now pins.
Neither was reachable from `tests/`: one needed the real matcher against every mounted tool, the
other needed the minified bundle in a real browser. What *is* covered without a browser is in
`tests/test_answers.py`, which is where the store's own contract lives.

**Both tables were driven again when they moved onto TanStack Table** on 2026-10-14, with Playwright's
headless Chromium (system NSS libraries unpacked into task scratch) against `docstrap serve` in a
redirected home over a copy of firstmate's real store, its census page of 117 tasks. Through the
viewer the list mounted with every control; a search narrowed 117 to 25, a stuck facet showed its
counts and narrowed to 88 with each group's count following, the clear button restored 117, status
grouping by state and by stuck regrouped and wrote `tasks-group`, a group's name drilled in and wrote
`tasks-in`, a group collapsed to its heading, last activity sorted both ways inside each group with
`aria-sort` following, and an opened task's detail stayed inside the box while the table was scrolled
sideways. Every column measured its `SIZES` width exactly, the task column 150 px. Opened directly,
the page ran no tool and showed the plain table at the same widths inside its scrolling box. The
data table, built from `tests/fixtures/datatable/census` in a
second scratch store, sorted both ways, searched and narrowed by a facet. The console held no error
or warning on either page.

**The path-aware routes of 2026-09-23 were verified without a browser, and the gap is worth naming.**
`chrome-devtools-axi` 0.1.29 is still unusable on this machine: `open` succeeds, then `snapshot`,
`eval` and `console` all fail with `Input validation error: Required at pageId` and `pages` reports
zero pages open. Playwright's bundled Chromium is still missing `libnss3` and `libnspr4`, which
cannot be installed without changing the system. So that work was proved three ways instead: the
Python suite above; a real `docstrap serve` over HTTP against a real build in an isolated `HOME`,
where the report's four 404/405 rows all return 200, the project scope still resolves to the project
handler, and an undeclared nested slug returns a 404 naming the slug; and the client helpers
(`encodeDocSlug`, `apiStatus`, `describeApiFailure`) exercised directly under Node. What remains
unproven is only what a browser can see: the panels rendering the listing they now receive, and the
console staying clean. It joins the `answered` tool's outstanding run above, on the same blocker.
