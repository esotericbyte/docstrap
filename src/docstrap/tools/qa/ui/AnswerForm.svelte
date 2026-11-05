<!--
  AnswerForm.svelte — the answering apparatus under an author's question.

  The `docstrap-questions` directive renders this form server-side so a
  page built without ever running JavaScript still reads correctly (and
  so the launcher's CSS gate can hide it before any script runs). This
  component takes that markup over when the tool shows, rendering the
  same controls and adding the submit behaviour.

  It renders the contents of `.docstrap-questions-form`, not the wrapper:
  the wrapper is the directive's, it carries `.docstrap-chrome`, and the
  launcher's `body.docstrap-show-qa` rule in qa.css gates it. That gate
  is on server-rendered markup, so it cannot be a scoped rule.
-->
<script lang="ts">
  import { describeApiFailure, type DocstrapGlobal } from '../../../sphinx/ui/docstrap';

  let {
    d,
    questionId,
    prompt,
  }: { d: DocstrapGlobal; questionId: string; prompt: string } = $props();

  type StatusKind = '' | 'ok' | 'error' | 'pending';

  let answer = $state('');
  let statusKind = $state<StatusKind>('');
  let statusText = $state('');
  let busy = $state(false);

  function say(kind: StatusKind, message: string): void {
    statusKind = kind;
    statusText = message;
  }

  function submit(): void {
    const trimmed = answer.trim();
    if (!trimmed) {
      say('error', 'Answer is empty.');
      return;
    }
    // A tool never assembles a path; this is the URL the declaration
    // resolved for this page.
    const url = d.tools.route('qa');
    if (!url) {
      say('error', 'No project/doc context.');
      return;
    }

    busy = true;
    say('pending', 'Submitting…');

    d.api<{ written_to?: string }>(url, {
      method: 'POST',
      body: { question_id: questionId, question: prompt, answer: trimmed },
    })
      .then((result) => {
        say('ok', `Saved to ${result.written_to || 'the draft root'}`);
        answer = '';
      })
      .catch((err) => {
        d.silenceOfflineError(err);
        say('error', `Submit failed — ${describeApiFailure(err, url)}`);
      })
      .finally(() => {
        busy = false;
      });
  }
</script>

<textarea
  class="docstrap-questions-answer"
  placeholder="Your answer…"
  rows="4"
  bind:value={answer}></textarea>
<div class="docstrap-questions-controls">
  <button
    type="button"
    class="docstrap-questions-submit"
    disabled={busy}
    onclick={submit}>Submit</button>
  <span class="docstrap-questions-status" data-kind={statusKind} aria-live="polite"
    >{statusText}</span>
</div>

<style>
  .docstrap-questions-answer {
    display: block;
    width: 100%;
    min-height: 3.5em;
    padding: 0.4em 0.6em;
    border: 1px solid #c4c4c4;
    border-radius: 0.2em;
    font-family: inherit;
    font-size: 0.95em;
    resize: vertical;
    box-sizing: border-box;
  }
  .docstrap-questions-controls {
    margin-top: 0.5em;
    display: flex;
    align-items: center;
    gap: 0.75em;
  }
  .docstrap-questions-submit {
    padding: 0.3em 0.9em;
    border: 1px solid #4a7bb6;
    background: #4a7bb6;
    color: white;
    border-radius: 0.2em;
    cursor: pointer;
    font-size: 0.9em;
  }
  .docstrap-questions-submit:hover { background: #3a6ba6; }
  .docstrap-questions-submit:disabled { opacity: 0.6; cursor: default; }

  .docstrap-questions-status { font-size: 0.85em; }
  [data-kind='ok']      { color: #1b5e2b; }
  [data-kind='error']   { color: #a02020; }
  [data-kind='pending'] { color: #7a5b10; }

  @media (prefers-color-scheme: dark) {
    .docstrap-questions-answer {
      background: #16202b;
      color: #e0e0e0;
      border-color: #364252;
    }
  }
</style>
