"""The qa tool's view: the ``docstrap-questions`` directive.

Renders a form widget at the location the doc author places it.
Submissions POST to the tool's declared route and are kept in the
project's answer store, in its draft root.

MyST-Parser auto-recognises Sphinx-registered directives, so both

.. code-block:: rst

   .. docstrap-questions::
      :question-id: q-1
      :prompt: What tradeoffs matter for approach X?

and its MyST equivalent

.. code-block:: markdown

   ```{docstrap-questions}
   :question-id: q-1
   :prompt: What tradeoffs matter for approach X?
   ```

work from the same directive class.
"""
from __future__ import annotations

import html

from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.util.docutils import SphinxDirective


class DocstrapQuestionsDirective(SphinxDirective):
    """Emit a Q&A form target that the docstrap-qa.js tool enhances."""

    has_content = True
    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {
        "question-id": directives.unchanged_required,
        "prompt": directives.unchanged,
    }

    def run(self) -> list[nodes.Node]:
        qid = self.options.get("question-id", "").strip()
        prompt = self.options.get("prompt", "").strip()
        content_body = "\n".join(self.content).strip()

        if not qid:
            raise self.error("docstrap-questions requires :question-id: option")

        # Body content, if present, is used as the visible prompt when
        # :prompt: isn't set (long-form questions belong in the body).
        visible_prompt = prompt or content_body or "(no prompt provided)"

        qid_e = html.escape(qid, quote=True)
        prompt_e = html.escape(visible_prompt, quote=False)

        # The prompt is authored content and stays on the page whatever
        # the launcher says. The answering apparatus below it is the
        # tool's chrome, and the launcher's visibility class gates it
        # in CSS — see docstrap-qa.css.
        markup = (
            f'<div class="docstrap-questions" data-question-id="{qid_e}">'
            f'<p class="docstrap-questions-prompt">{prompt_e}</p>'
            f'<div class="docstrap-questions-form docstrap-chrome">'
            f'<textarea class="docstrap-questions-answer" '
            f'placeholder="Your answer…" rows="4"></textarea>'
            f'<div class="docstrap-questions-controls">'
            f'<button type="button" class="docstrap-questions-submit">Submit</button>'
            f'<span class="docstrap-questions-status" aria-live="polite"></span>'
            f"</div>"
            f"</div>"
            f"</div>"
        )
        return [nodes.raw("", markup, format="html")]
