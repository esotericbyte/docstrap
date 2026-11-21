# The Annotorious embed as a tool — how it might be done

**A note, not a specification and not a plan.** Recorded at the captain's request on 2026-10-10, on the
backlog item "docstrap: Annotorious embed as a tool on the new declaration surface": *"launch a worker
to suggest how this might be done in a note"*. It suggests a shape; nothing here is approved, nothing is
scheduled, and the questions at the end are the captain's to answer. Sequencing, if it comes, belongs
in `docs/roadmap.md` §4.2, which is this item's entry.

## 1 What exists, and the one finding that changes the framing

The server half is built and has never been exercised by a client: the `annotations` table of
`docs/docstrap_on_2026-09-01.md` §6, owned by `docstrap.annotations`, and the W3C Web Annotation Protocol subset on
`/api/annotations` in `server.py` (GET by `?target=`, POST, PATCH and DELETE by id). The captain ruled
on 2026-09-07 that this store is Annotorious's (`docs/docstrap_on_2026-09-01.md` §6 and its Q4).

**Annotorious itself annotates images, not text.** `@annotorious/annotorious` 3.9.4 describes itself
on npm as "image annotation functionality"; its Svelte bindings pull in OpenSeadragon, a deep-zoom
image viewer. The same project's *text* annotator is published under the Recogito name as
`@recogito/text-annotator` (4.3.6, BSD-3-Clause, 2026-10-01), and it is built on `@annotorious/core`
3.x — the same annotation model, store, event names and W3C format adapter. A docstrap page is text.

So "the Annotorious embed" for a docstrap document is, concretely, the Annotorious family's text
annotator, and the image annotator only becomes relevant if figures are ever to be annotated. The note
proceeds on that reading. It is Q1 because the captain's ruling named the library, and confirming
that the text annotator falls under that ruling is not a call a worker makes.

The older RecogitoJS (`@recogito/recogito-js` 1.8.4, Preact-based) is the predecessor and is not
suggested.

## 2 The declaration

The tool is a directory, `src/docstrap/tools/annotate/`, laid out exactly as
`docs/tools-and-instruments.md` §5 describes, with one declaration:

```python
DECLARATION = ToolDeclaration(
    id="annotate",
    title="Annotations",
    kind=Kind.TOOL,
    target=Target.DOCUMENT,
    entry="docstrap.tools.annotate",
    # No collection of its own. The store and its W3C API are the
    # server's (docs/docstrap_on_2026-09-01.md §6), the arrangement the status badge has
    # with /api/documents and the answered tool has with /api/answers.
    api_collection=None,
    default_visible=False,
    summary="Highlight passages and comment on them.",
)
```

Each field is a consequence rather than a choice, and the reasoning is worth having in one place.

### 2.1 It is a tool, and it targets a document

Highlighting a passage and commenting beside it leaves the page you were reading as the page you are
looking at — an overlay or popover is still a tool by the boundary test of
`tools-and-instruments.md` §1. Every annotation hangs on one document, so the target is `DOCUMENT`.

### 2.2 It owns no collection, and that is what keeps the route rules intact

`api_collection=None` is the decisive line. The annotation API is the server's and lives at
`/api/annotations`, outside both declared route bases, so a tool that tried to own it would fail
`check_route_separation` at mount time — correctly, since a second route onto one store is a second
way to write it. Two shipped tools already read a server-owned API this way, and their declarations
carry the same comment. The consequence is that `docstrap.tools.route("annotate")` is `null` and the
client names `/api/annotations` itself, as the status badge names `/api/documents`.

### 2.3 Off until asked for

It is the reader's choice to start marking up a document, as it is for the review tool. A page with
the tool hidden must read as a plain document (`tools-and-instruments.md` §3.1), and highlights
drawn over the prose are apparatus.

## 3 The client

`ui/index.ts` registers `show` and `hide` with the launcher and does nothing until `show`. On `show` it
does four things.

1. **Finds the workpiece.** The annotatable container is the rendered article body, not the page:
   furo's sidebars, the launcher and every `.docstrap-chrome` element must be outside what is
   annotated. The text annotator honours a `not-annotatable` class on elements inside its container,
   so the tool marks the chrome it does not want selected rather than hunting for a perfectly bounded
   element.
2. **Names the document.** The W3C target's `source` is `docstrap://document/<metadata-id>`, the form
   `docs/docstrap_on_2026-09-01.md` §6 gives for `target_doc`, read from the page's existing doc-id context (`ctx.docId`).
   Keying on the metadata id rather than the path is what lets an annotation survive the document being
   renamed, the same property `docstrap.answers` relies on.
3. **Loads what exists.** `createTextAnnotator(container, { adapter: W3CTextFormat(source, container) })`,
   then `GET /api/annotations?target=<source>` and `setAnnotations` with the result.
4. **Writes what changes.** The annotator's `createAnnotation`, `updateAnnotation` and
   `deleteAnnotation` events map one to one onto POST, PATCH and DELETE. The client generates the id
   and POSTs it, which the store already accepts.

`hide` destroys the annotator, which removes its highlights, so the page is plain again.

**The comment popup is the tool's own Svelte component.** The text annotator ships selection and
highlighting and no editor UI in its vanilla form; its ready-made popups are React. A small Svelte
component mounted on the annotator's selection event — a text box, save, delete — is the part of
this tool that is actually written, and it is Svelte with scoped styles per
`tools-and-instruments.md` §1.1, with icons from Lucide.

The library's own stylesheet (690 bytes minified) is global and must stay global, because the
annotator's highlight elements are not Svelte's. That is the case `ui/<id>.css` exists for, "rules that
must be global, with a reason".

## 4 What the store needs before a client writes to it

Exercising the API end to end for this note — a W3C text annotation of the shape the adapter produces,
against an isolated database — gave four results.

1. **POST, GET and PATCH work** and round-trip `TextQuoteSelector` and `TextPositionSelector` intact.
2. **DELETE is broken on the server side.** `delete_annotation` returns
   `JSONResponse(status_code=204, content=None)`, which serialises the body `null` against a
   zero Content-Length; the client receives a 204 and uvicorn raises
   `LocalProtocolError: Too much data for declared Content-Length` on every delete. It should be a bare
   `Response(status_code=204)`.
3. **POSTing an id that already exists is a 500**, an uncaught `sqlite3.IntegrityError`. A client that
   retries after a dropped response would hit it; it should be a 409.
4. **Nothing in `tests/` touches `/api/annotations`.** A small server test belongs with the first two
   repairs, and the repairs are the right first commit whatever else is decided — they are defects in
   shipped code, independent of which client arrives.

The fifth item is a ruling rather than a defect. `docs/proposals/0003-clearing-the-decision-backlog.md`
§7.5 rules that `annotations.db` need not get refuse-and-migrate because it holds no rows a client
wrote, and says outright that "the moment Annotorious is added, this ruling is wrong". 0003 is a
proposal, so that ruling is not approved either, but whichever upgrade rule is in force when this tool
lands has to be checked against it in the same change, because this tool is the trigger it names.

## 5 Per-page cost, which is the real design question

A tool ships with every page (`tools-and-instruments.md` §1.1(1)). Bundled the way `build-tools.mjs`
builds — minified IIFE, `es2022` — the text annotator and its W3C adapter alone come to **64.3 kB,
23.6 kB gzipped**, before the Svelte runtime the popup brings, which §5.1 puts at roughly 30 kB per
bundle. That makes this the heaviest tool by a margin, paid on every page view by every reader who
never turns it on.

There are three ways to carry it.

1. **Ship it like the others.** Simple, and consistent with what is built. The cost is roughly
   doubling the per-page weight of the tools.
2. **Load the library on `show()`.** The tool's bundle becomes a thin shell, and the annotator arrives
   only when a reader turns the tool on. An IIFE library build inlines dynamic imports, so this needs
   the declaration's asset surface to name an on-demand asset next to the per-page one. By the test of
   `tools-and-instruments.md` §4 that is a real extension point rather than a one-off: the qapanels
   instrument is an instrument that already ships on every page for exactly this lack (§5.1).
3. **Take the ES-module lever of §5.2(2) first.** Shared chunks plus native dynamic import solve both
   the shared Svelte runtime and on-demand loading, at the cost of `register_tool_assets` emitting
   `<script type="module">` — the decision §5.2 says should be taken deliberately.

This note's suggestion is (2) if the tool is built before the module decision and (3) if after, and
not (1). It is Q3, because it is a change to the declaration surface and not to this tool.

## 6 Smaller things the build would meet

**Who `creator` is.** On a local `docstrap serve` there is no identity, while `docs/docstrap_on_2026-09-01.md` §6 says
`creator` models a reader of a *deployed* site, identified by the deploying organisation's user system.
The text annotator accepts a `user` option and the store will record whatever is sent. Leaving it
empty locally loses nothing that can be recovered later; inventing an identity scheme here would be
deciding the deployed case by accident. Q4.

**A page with no metadata id.** The launcher's offer rule reads kind and target only, so the tool is
offered on every document page, while an annotation needs the document's metadata id. On a page without
one the tool should do nothing, which is what the status badge does. Creating the id on first
annotation, as the answers path creates one on first answer, is an alternative with a write in it. Q5.

**Annotations go stale when the text changes, and docstrap's documents change.** The adapter stores a
quote selector (the exact text with a little prefix and suffix) and a character-offset selector. After
an edit the offsets are wrong and the quote may no longer be found; an annotation whose quote is gone
cannot be anchored and the annotator draws nothing for it. They are still in the store. A list of the
annotations that did not anchor on this page is a natural later addition, and what it should look like
is a later question.

**The review tool selects text too.** Both tools answer to a reader dragging across prose. Whether the
two may be visible at once, and what a selection means when they are, should be settled by trying it
rather than in advance; the launcher already lets either be hidden.

**The viewer shell.** `docs/proposals/0004-the-viewer-shell.md` shows the published page in an
`<iframe>` that shares the page's tool-visibility state. The tool would therefore run inside the
frame like any other tool, with nothing special required — worth confirming in the browser run, not
designing for.

**Verification.** `test_tool_declarations.py` and `test_extension_points.py` pick a new declaration up
on their own. A browser run of the kind `tools-and-instruments.md` §7 records — select, comment,
reload, edit, delete, hide all, console clean — is the evidence the tool works, and the environment
note there about the browser bridges still applies.

## 7 Suggested order

1. Repair DELETE and the duplicate-id POST and add the server test (§4). Independent of everything else.
2. Settle Q1 through Q3, which decide the library and how it is loaded.
3. Build the tool as §2 and §3 describe, with whichever loading §5 lands on.
4. Re-examine the `annotations.db` upgrade ruling in the same change (§4).
5. Drive it in a browser and record the run in `tools-and-instruments.md` §7.

## Open questions

**Q1.** Does the captain's 2026-09-07 ruling that the store is Annotorious's cover
`@recogito/text-annotator`, the Annotorious project's text annotator built on `@annotorious/core`,
given that `@annotorious/annotorious` itself annotates images?

**Q2.** Should image annotation with `@annotorious/annotorious` be in scope for figures in documents,
or left out until there is a need?

**Q3.** Should the declaration surface gain an on-demand asset so that this tool's library loads only
when the tool is shown, rather than shipping roughly 64 kB more on every page?

**Q4.** Should `creator` stay empty for annotations made on a local `docstrap serve` until a deployed
site has a user system to fill it from?

**Q5.** On a document page with no metadata id, should the tool stay inert rather than create the id on
the first annotation?
