<!--
  QuestionList.svelte — panel one: the project's open questions, with
  single selection.

  Grouped by document, in the order the scan returned them. A question
  whose answer was submitted is marked; the mark is read off the answer
  store, not off the document, because the document is where questions
  live and the store is where answers do.

  The mark follows submission and not storage. A question with an
  unfinished draft against it is still open, and saying otherwise is what
  the Finish button exists to prevent.

  Each document's title row carries its "answers done" prompt when the
  server resolved a route for one, and only then — no route means no
  command is configured. One per document, never
  one per question.

  Below the last question sits whatever `footer` the host passes — the
  panels' one Finish. It is in the list's own flow and scrolls with it.
-->
<script lang="ts">
  import CheckCheck from '@lucide/svelte/icons/check-check';
  import type { Snippet } from 'svelte';

  import type { AnswersDoneNotice, QuestionDocument, Selection } from './types';
  import { selectionId } from './types';

  let {
    documents,
    selected,
    onselect,
    onanswersdone,
    notice = null,
    busy = null,
    footer,
  }: {
    documents: QuestionDocument[];
    selected: Selection | null;
    onselect: (selection: Selection) => void;
    onanswersdone: (entry: QuestionDocument) => void;
    /** The last press, shown beside the prompt it came from. */
    notice?: AnswersDoneNotice | null;
    /** The document whose press is in flight, if any. */
    busy?: string | null;
    /** Rendered below the last question. */
    footer?: Snippet;
  } = $props();

  function pick(entry: QuestionDocument, index: number): void {
    const question = entry.questions[index];
    onselect({
      docSlug: entry.docSlug,
      path: entry.path,
      label: question.label,
      text: question.text,
      section: question.section,
      key: question.key,
      answer: question.answer,
      answeredAt: question.answeredAt,
      submittedAnswer: question.submittedAnswer,
      submitted: question.submitted,
      submittedAt: question.submittedAt,
      hasDraft: question.hasDraft,
      draftedAt: question.draftedAt,
      supersededCount: question.supersededCount,
    });
  }

  function isSelected(docSlug: string, label: string): boolean {
    return (
      selected !== null && selectionId(selected.docSlug, selected.label) === selectionId(docSlug, label)
    );
  }
</script>

<div class="list">
  <div role="listbox" aria-label="Open questions">
    {#each documents as entry (entry.docSlug)}
      <div class="group">
        <div class="group-title">
          <span class="path">{entry.path}</span>
          {#if entry.answersDoneRoute}
            {#if notice && notice.docSlug === entry.docSlug}
              <span class="notice" class:failed={!notice.ok} aria-live="polite">{notice.text}</span>
            {/if}
            <button
              type="button"
              class="done"
              disabled={busy !== null}
              onclick={() => onanswersdone(entry)}
              ><CheckCheck size={14} aria-hidden="true" />Answers done</button>
          {/if}
        </div>
        {#each entry.questions as question, index (question.label)}
          <button
            type="button"
            role="option"
            aria-selected={isSelected(entry.docSlug, question.label)}
            class="row"
            class:selected={isSelected(entry.docSlug, question.label)}
            onclick={() => pick(entry, index)}
          >
            <span class="label">{question.label}</span>
            <span class="text">{question.text}</span>
            {#if question.submitted}
              <span class="answered" title="Submitted {question.submittedAt ?? ''}"
                >submitted</span>
              {#if question.hasDraft}
                <span class="drafted" title="Revision saved {question.draftedAt ?? ''}"
                  >revising</span>
              {/if}
            {:else if question.hasDraft}
              <span class="drafted" title="Draft saved {question.draftedAt ?? ''}"
                >draft</span>
            {/if}
          </button>
        {/each}
      </div>
    {:else}
      <p class="empty">This project's documents pose no numbered questions.</p>
    {/each}
  </div>
  {@render footer?.()}
</div>

<style>
  .list {
    overflow-y: auto;
    height: 100%;
    padding: 0.25em 0;
  }
  .group + .group {
    margin-top: 0.75em;
  }
  .group-title {
    display: flex;
    align-items: center;
    gap: 0.6em;
    padding: 0.3em 0.9em;
    position: sticky;
    top: 0;
    background: inherit;
  }
  .path {
    flex: 1 1 auto;
    min-width: 0;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 0.78em;
    letter-spacing: 0.02em;
    opacity: 0.7;
  }
  .done {
    flex: 0 0 auto;
    display: inline-flex;
    align-items: center;
    gap: 0.35em;
    padding: 0.15em 0.7em;
    border: 1px solid #4a7bb6;
    border-radius: 0.2em;
    background: none;
    color: #4a7bb6;
    font: inherit;
    font-size: 0.8em;
    cursor: pointer;
  }
  .done:hover:not(:disabled) {
    background: rgba(74, 123, 182, 0.16);
  }
  .done:disabled {
    opacity: 0.5;
    cursor: default;
  }
  .notice {
    flex: 0 1 auto;
    min-width: 0;
    font-size: 0.8em;
    color: #1b5e2b;
  }
  .notice.failed {
    color: #a02020;
  }
  .row {
    display: flex;
    align-items: baseline;
    gap: 0.6em;
    width: 100%;
    text-align: left;
    padding: 0.35em 0.9em;
    border: 0;
    border-left: 3px solid transparent;
    background: none;
    color: inherit;
    font: inherit;
    font-size: 0.9em;
    cursor: pointer;
  }
  .row:hover {
    background: rgba(127, 127, 127, 0.12);
  }
  .row.selected,
  .row.selected:hover {
    border-left-color: #4a7bb6;
    background: rgba(74, 123, 182, 0.32);
    box-shadow: inset 0 0 0 1px rgba(74, 123, 182, 0.55);
  }
  .label {
    flex: 0 0 auto;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
  }
  .text {
    flex: 1 1 auto;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .answered,
  .drafted {
    flex: 0 0 auto;
    font-size: 0.75em;
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }
  .answered {
    color: #1b5e2b;
  }
  .drafted {
    opacity: 0.55;
    font-style: italic;
  }

  @media (prefers-color-scheme: dark) {
    .answered,
    .notice {
      color: #7fd39b;
    }
    .notice.failed {
      color: #f08b8b;
    }
    .row.selected,
    .row.selected:hover {
      border-left-color: #7ea6d6;
      background: rgba(126, 166, 214, 0.28);
      box-shadow: inset 0 0 0 1px rgba(126, 166, 214, 0.55);
    }
    .done {
      border-color: #7ea6d6;
      color: #7ea6d6;
    }
  }
  .empty {
    margin: 0;
    padding: 1em 0.9em;
    opacity: 0.7;
  }
</style>
