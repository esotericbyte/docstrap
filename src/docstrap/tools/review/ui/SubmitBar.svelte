<!--
  SubmitBar.svelte — the review tool's fixed panel: an optional summary,
  the submit button, and what happened.

  On submit it POSTs the marks to the route the declaration resolved for
  this page and copies the returned file path to the clipboard. It writes
  nothing to the document under review — a review is a derivative record
  beside the original.

  The floating corner button this tool used to inject is gone; launching
  is the launcher's business. This panel exists only while the tool is
  showing.
-->
<script lang="ts">
  import { describeApiFailure, type DocstrapGlobal } from '../../../sphinx/ui/docstrap';
  import type { SectionMark, SentenceMark } from './marks';

  let {
    d,
    sentenceMarks,
    sectionMarks,
  }: {
    d: DocstrapGlobal;
    sentenceMarks: SentenceMark[];
    sectionMarks: SectionMark[];
  } = $props();

  let summary = $state('');
  let status = $state('');
  let busy = $state(false);

  function submit(): void {
    // A tool never assembles a path; this is the URL the declaration
    // resolved for this page.
    const url = d.tools.route('review');
    if (!url) {
      status = 'No project/doc context.';
      return;
    }
    busy = true;
    status = 'Submitting…';

    d.api<{ written_to?: string }>(url, {
      method: 'POST',
      body: {
        sentence_marks: sentenceMarks.map((m) => ({ mark: m.mark, text: m.text })),
        section_marks: sectionMarks.map((m) => ({
          mark: m.mark,
          id: m.id,
          text: m.text,
        })),
        summary: summary.trim() || null,
      },
    })
      .then((result) => {
        status = `Saved to ${result.written_to || 'the draft root'} (path copied to clipboard)`;
        if (navigator.clipboard?.writeText && result.written_to) {
          navigator.clipboard.writeText(result.written_to).catch(() => {
            // silent — clipboard often fails on non-HTTPS
          });
        }
      })
      .catch((err) => {
        d.silenceOfflineError(err);
        status = `Submit failed — ${describeApiFailure(err, url)}`;
      })
      .finally(() => {
        busy = false;
      });
  }
</script>

<div class="docstrap-review-submit-bar docstrap-chrome">
  <textarea placeholder="Optional overall summary…" rows="2" bind:value={summary}
  ></textarea>
  <button type="button" disabled={busy} onclick={submit}>Submit review</button>
  <span class="docstrap-review-submit-status">{status}</span>
</div>

<style>
  .docstrap-review-submit-bar {
    position: fixed;
    right: 1em;
    bottom: 3.5em;
    width: 18em;
    padding: 0.6em 0.8em;
    background: white;
    border: 1px solid #c4c4c4;
    border-radius: 0.3em;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
    z-index: 999;
    display: flex;
    flex-direction: column;
    gap: 0.4em;
  }
  textarea {
    font-family: inherit;
    font-size: 0.85em;
    padding: 0.35em;
    border: 1px solid #c4c4c4;
    border-radius: 0.2em;
    box-sizing: border-box;
    resize: vertical;
  }
  button {
    padding: 0.3em 0.7em;
    border: 1px solid #4a7bb6;
    background: #4a7bb6;
    color: white;
    border-radius: 0.2em;
    cursor: pointer;
  }
  button:disabled { opacity: 0.6; cursor: default; }
  .docstrap-review-submit-status {
    font-size: 0.8em;
    color: #555;
  }

  @media (prefers-color-scheme: dark) {
    .docstrap-review-submit-bar { background: #16202b; color: #e0e0e0; border-color: #364252; }
    textarea { background: #202832; color: #e0e0e0; border-color: #364252; }
  }
</style>
