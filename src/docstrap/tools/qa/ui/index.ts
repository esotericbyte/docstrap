// docstrap qa tool — entry point.
//
// The qa directive emits a <div class="docstrap-questions"> holding the
// author's prompt plus a .docstrap-questions-form with a textarea and a
// submit button. When the tool shows, this replaces the contents of
// each of those forms with the AnswerForm component, which renders the
// same controls and knows how to submit them.
//
// The prompt is authored content and always reads. The form is the
// tool's chrome: showing and hiding it is the launcher's business, done
// through the body visibility class in qa.css.
import { mount } from 'svelte';

import { requireDocstrap } from '../../../sphinx/ui/docstrap';
import AnswerForm from './AnswerForm.svelte';
import './qa.css';

const TOOL = 'qa';

const d = requireDocstrap(TOOL);

if (d) {
  let wired = false;

  function show(): void {
    if (wired) return;
    wired = true;
    document.querySelectorAll('.docstrap-questions').forEach(wireWidget);
  }

  function hide(): void {
    // The component stays mounted; the form is out of the page by CSS
    // and cannot be submitted because it cannot be reached. Nothing to
    // tear down, and re-showing costs nothing.
  }

  function wireWidget(widget: Element): void {
    const questionId = widget.getAttribute('data-question-id') || '';
    const promptEl = widget.querySelector('.docstrap-questions-prompt');
    const form = widget.querySelector('.docstrap-questions-form');
    if (!questionId || !form) return;

    // The directive's controls are the no-JavaScript rendering of this
    // form. Clear them and let the component own the same wrapper, so
    // the launcher's CSS gate keeps applying to the same element.
    form.replaceChildren();
    mount(AnswerForm, {
      target: form,
      props: {
        d: d!,
        questionId,
        prompt: promptEl ? promptEl.textContent || '' : '',
      },
    });
  }

  d.tools.register(TOOL, { show, hide });
}
