# Sphinx extension research spike — notes

Research spike deliverable for the docstrap MVP work formerly labelled Alpha 2. Answers the four bullet questions so the Sphinx-plugin implementation (`status_widget`, `qa_widget`, `review_widget`) could proceed without discovering these patterns from scratch. The alpha phasing it was written against was removed from `docs/implementation-record.md` on 2026-09-01; that record's §1.1 records this spike as delivered.

Not a spec — a working note. Concrete API shapes, small code sketches, links to authoritative references. Post-implementation, this note can be superseded by the actual plugin docs.

> **Superseded in part.** The Sphinx API findings below still hold. The file layout in §3 does not: the three widgets have since moved to one-directory-per-tool under `src/docstrap/tools/`, each with its own declaration, and the per-widget floating buttons were replaced by a single visibility launcher. See [Tools and instruments](../tools-and-instruments.md) for the current architecture and the extension points. The §4 observation that the client assets should stay framework-agnostic was right, and is now stated as a constraint on tools specifically.

## §1 Hooking `html-page-context` to inject `<script>` and `<meta>` tags

Sphinx's `html-page-context` event fires once per output HTML page, immediately before the template is rendered. Signature:

```python
def on_html_page_context(
    app,        # Sphinx application object
    pagename,   # str, page's document name (no extension, no slash prefix)
    templatename, # str, Jinja2 template being used ('page.html' typically)
    context,    # dict, template context — MUTABLE
    doctree,    # docutils.nodes.document or None (index pages don't have one)
) -> None | str:
    ...
```

Return value: `None` to keep the default template, or a string to switch to a different template name.

### Two injection modes

**Global injection (every page).** Preferred for docstrap widget scripts, since every rendered doc page needs the status badge, Q&A hooks, and review widget. Use `Sphinx.add_js_file()` and `Sphinx.add_css_file()` in the extension's `setup()`:

```python
def setup(app):
    app.add_js_file("docstrap-status.js")
    app.add_js_file("docstrap-qa.js")
    app.add_js_file("docstrap-review.js")
    app.add_css_file("docstrap.css")
```

Sphinx adds `<script>` / `<link rel="stylesheet">` tags to every generated HTML file automatically. Files must live under a directory registered as a static path (§3).

**Per-page conditional injection.** Only inject when a specific meta tag or condition applies. Two mechanisms coexist:

1. **`metatags` context key.** Append raw HTML into `context["metatags"]`; that string is rendered inside `<head>`. Good for `<meta>` tags carrying document IDs:

    ```python
    def on_html_page_context(app, pagename, templatename, context, doctree):
        doc_id = _lookup_document_id(pagename)
        if doc_id:
            existing = context.get("metatags", "")
            context["metatags"] = existing + f'<meta name="docstrap-doc-id" content="{doc_id}">\n'
    ```

2. **`body_tag` / template-context strings.** Less common; append into `context["body"]` before body content is composed. Overkill for docstrap's needs.

Register the handler in `setup()`:

```python
def setup(app):
    app.connect("html-page-context", on_html_page_context)
    app.add_js_file("docstrap-status.js")
    ...
```

### Concrete pattern for docstrap widgets

Each widget wants a page-level meta tag (`docstrap-doc-id`, `docstrap-project`, `docstrap-status`) so the JS can call `/api/documents/<id>` for state. Inject those in `html-page-context`; include the JS globally via `add_js_file`.

Reference: <https://www.sphinx-doc.org/en/master/extdev/appapi.html#sphinx.application.Sphinx.add_js_file>, <https://www.sphinx-doc.org/en/master/extdev/appapi.html#event-html-page-context>.

## §2 Custom directive that emits form HTML at build time

Sphinx directives are subclasses of `sphinx.util.docutils.SphinxDirective` (preferred over raw `docutils.parsers.rst.Directive` because it gives you `self.env`, `self.config`, and the running `app`). A directive's `run()` returns a list of docutils nodes.

To emit raw HTML output at build time:

```python
from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.util.docutils import SphinxDirective


class DocstrapQuestionsDirective(SphinxDirective):
    """Renders a form target for the Q&A widget.

    RST:   .. docstrap-questions::
              :question-id: q-1
              :prompt: What are the tradeoffs of X vs Y?

    MyST:  ```{docstrap-questions}
              :question-id: q-1
              :prompt: What are the tradeoffs of X vs Y?
              ```
    """

    has_content = True
    required_arguments = 0
    optional_arguments = 0
    option_spec = {
        "question-id": directives.unchanged_required,
        "prompt": directives.unchanged,
    }

    def run(self):
        qid = self.options.get("question-id", "")
        prompt = self.options.get("prompt", "")
        # Rendered HTML target for the JS to enhance.
        html = (
            f'<div class="docstrap-questions" '
            f'data-question-id="{qid}">'
            f'<p class="docstrap-questions-prompt">{prompt}</p>'
            f'<textarea class="docstrap-questions-answer" '
            f'placeholder="Your answer..."></textarea>'
            f'<button class="docstrap-questions-submit">Submit</button>'
            f"</div>"
        )
        return [nodes.raw("", html, format="html")]


def setup(app):
    app.add_directive("docstrap-questions", DocstrapQuestionsDirective)
```

MyST-Parser auto-recognises directives registered with Sphinx, so the same class works from both `.rst` and `.md` sources — no separate registration.

**Node vs raw HTML.** `nodes.raw(format='html')` is the simplest path when the output is fixed HTML with slot-fills. For more structured output that participates in Sphinx's index/toctree/xref machinery, define a custom node class (`nodes.Element` subclass) and register HTML translator visitors — overkill here.

**HTML escaping.** `SphinxDirective` does not auto-escape option values into HTML — the directive is responsible. Use `html.escape()` on any user-supplied strings before interpolating into `data-*` attributes or visible text. Above sketch omits it for brevity; the real implementation must escape.

Reference: <https://www.sphinx-doc.org/en/master/extdev/tutorial.html>, <https://docutils.sourceforge.io/docs/howto/rst-directives.html>.

## §3 Including static JS/CSS assets in a Sphinx extension

Extension-bundled statics use `app.connect("builder-inited", ...)` to register a static path relative to the extension's own directory, then reference by filename with `add_js_file()` / `add_css_file()`.

Pattern:

```python
import os


def _register_static_path(app):
    ext_dir = os.path.dirname(__file__)
    static_dir = os.path.join(ext_dir, "static")
    if static_dir not in app.config.html_static_path:
        app.config.html_static_path.append(static_dir)


def setup(app):
    app.connect("builder-inited", _register_static_path)
    app.add_js_file("docstrap-status.js")
    app.add_js_file("docstrap-qa.js")
    app.add_js_file("docstrap-review.js")
    app.add_css_file("docstrap.css")
    ...
```

Directory layout for the docstrap extension package:

```
src/docstrap/sphinx/
├── __init__.py
├── _common.py               # shared helpers (fetch pattern, dom helpers)
├── status_widget.py         # exposes setup(app) — registers status widget
├── qa_widget.py             # setup(app) — registers the .. docstrap-questions:: directive + JS
├── review_widget.py         # setup(app) — sentence-checkmark widget
└── static/
    ├── docstrap-status.js
    ├── docstrap-qa.js
    ├── docstrap-review.js
    └── docstrap.css
```

When Sphinx copies static files into `_static/` in the built site, the extension-provided files appear alongside the theme's own — namespace them (`docstrap-*.js`, `docstrap.css`) to prevent collisions.

**Load order.** `add_js_file()` inserts scripts in registration order. For inter-widget helpers (`_common.js`), register that file *first*. Or use `add_js_file(filename, defer=True)` to opt into `defer` for load ordering that survives async network conditions.

Reference: <https://www.sphinx-doc.org/en/master/extdev/appapi.html#sphinx.application.Sphinx.add_js_file>, <https://www.sphinx-doc.org/en/master/usage/configuration.html#confval-html_static_path>.

## §4 How the pattern generalises to (or diverges from) MkDocs and Quarto

The Sphinx extension model above translates onto MkDocs and Quarto imperfectly. Not a blocker for docstrap MVP (Sphinx-only for the widgets) but relevant to the post-MVP roadmap item "MkDocs and Quarto plugin equivalents" in the spec.

### §4.1 MkDocs

Plugin API: subclass `mkdocs.plugins.BasePlugin`, override lifecycle methods. Load via `plugins:` in `mkdocs.yml`.

- **Script/CSS injection.** No direct `add_js_file()` equivalent. Two paths: (1) plugin config extends the `extra_javascript` / `extra_css` lists in `mkdocs.yml` before build; (2) `on_post_page(html, page, config)` hook mutates the rendered HTML string. The `extra_javascript` path is cleaner; static files ship inside the plugin's package and get copied via `on_files(files, config)`.

- **Per-page meta tag injection.** `on_page_markdown(markdown, page, config, files)` runs on the source Markdown; `on_page_content(html, page, config, files)` runs on rendered HTML. Meta tags belong in the `<head>`, which isn't in the page's `html` — need to mutate at `on_post_template(output, template_name, config)` or override the template. Less ergonomic than Sphinx's `metatags` context key.

- **Custom directive equivalent.** MkDocs does not have Sphinx directives. Closest analog: `on_page_markdown` preprocessor plugin that recognises a custom fenced block (e.g. ` ```docstrap-questions ` ) or shortcode (e.g. `{{ docstrap_questions(...) }}`) and substitutes HTML. Uses regex or a Markdown-it plugin. More work than Sphinx directives, less semantically clean.

- **Load order and site build hooks.** Plugin lifecycle is well-defined (`on_config`, `on_files`, `on_nav`, `on_page_markdown`, `on_page_content`, `on_post_page`, `on_post_build`). Roughly equivalent expressive power to Sphinx events; different mental model.

Reference: <https://www.mkdocs.org/dev-guide/plugins/>.

### §4.2 Quarto

Very different model — Quarto uses **Lua filters** (Pandoc AST manipulations) and **shortcodes** (`{{< shortcode arg >}}` syntax replaced at render time). Extensions live under `_extensions/<name>/` in the project. No Python plugin API; the extension language is Lua.

- **Script/CSS injection.** Extensions declare `format:` blocks in their `_extension.yml` that map to the target output format (HTML). Static assets go under the extension dir; Quarto copies them during rendering.

- **Custom directive equivalent.** Shortcodes are the closest: `{{< docstrap-questions id="q-1" prompt="..." >}}` triggers a Lua function that emits HTML. Less flexible than Sphinx directives on option parsing but very lightweight.

- **Docstrap-in-Quarto would be a Lua-side reimplementation** of the widget behaviour, sharing the JS assets and the backend API but not the directive code. Not a small port.

Reference: <https://quarto.org/docs/extensions/>.

### §4.3 Implication for docstrap

- Alpha 3 targets Sphinx only. That's the right first-release scope.
- Post-MVP MkDocs support: plausible with the plugin-lifecycle patterns above; the widgets' JS assets and backend API are reusable across, only the injection glue differs.
- Post-MVP Quarto support: bigger lift; would benefit from batching with any other Lua-extension work in the workspace rather than being taken on solo.
- The shared JS files (`docstrap-*.js`) should be written to be framework-agnostic — they interact with the DOM and docstrap's HTTP API, not with any Sphinx-specific machinery. That decision keeps future MkDocs/Quarto ports cheap.

## §5 Small unknowns worth flagging before implementation

- **Meta tag content vs data-attributes.** For the widget JS to find its document ID, `<meta name="docstrap-doc-id">` in the head vs `<body data-docstrap-doc-id="...">` are both viable. Meta tags are cleaner semantically; data-attributes are trivial to read from JS (`document.body.dataset.docstrapDocId`). Lean: data-attributes on `<body>`. Consequence: injection happens in `html-page-context` by mutating `context["body_tag_attrs"]` if it exists, otherwise by an alternative template hook.

- **CSRF for POST/PATCH endpoints.** The app server is local-loopback only per spec, so CSRF is not on the immediate threat model, but if it ever binds to non-localhost, CSRF discipline (SameSite cookies, tokens) becomes real. Flag for Alpha 4 hardening.

- **Textarea persistence in Q&A widget.** If the user types an answer and reloads the page before submitting, the text is lost. Session-storage save-as-you-type is a small UX improvement; not in Alpha 3 scope unless it's trivial to add.

- **Review widget sentence detection.** The spec says "identifies prose (skipping `<pre>`, `<code>`, `<a>`, headings, section-number spans), places a tri-state control after each qualifying sentence-ending period." Sentence tokenisation in JS: rough regex on `.` `?` `!` boundaries handles 95% of cases and breaks on abbreviations. Acceptable for MVP; can be tightened later.

## §6 Bottom line for Alpha 3 estimation

The Sphinx side is well-understood; no research surprises. The three widgets share:

- A common `setup(app)` pattern (register static, add JS files, connect events).
- A common `html-page-context` hook that injects the doc-ID and project meta tags.
- A common `<meta>` / `data-*` mechanism for JS-side lookup.

Building `_common.py` first (shared helpers) then each widget-specific `setup(app)` + JS bundle is the sequence the plan already suggests. Each widget after the scaffold: 1–2 days feels right.
