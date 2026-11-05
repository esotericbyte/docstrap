<!--
  AnswerNote.svelte — one question's state, and its answer if it has one.

  Mounted after the block the build marked, once per question. It is the
  reading half of the answered tool: a reader of a question document can
  tell an answered question from an open one, and read the answer, without
  leaving the page.

  It renders a DERIVATIVE. Nothing here is in the document; the document
  still says exactly what its author wrote — nothing is altered in place —
  which is the reason answering is safe to point at a read-only checkout.
-->
<script lang="ts">
  import type { AnsweredQuestion } from './types';

  let { question }: { question: AnsweredQuestion } = $props();

  /** The date alone. The time of day is not what a reader wants here. */
  function day(stamp: string | null): string {
    if (!stamp) return '';
    const at = stamp.indexOf('T');
    return at > 0 ? stamp.slice(0, at) : stamp;
  }
</script>

<aside
  class="docstrap-chrome answer-note"
  class:answered={question.answered}
  class:open={!question.answered}
>
  {#if question.answered}
    <p class="head">
      <span class="mark answered">Answered</span>
      <span class="when">{day(question.submittedAt ?? question.answeredAt)}</span>
      {#if question.answeredBy}<span class="who">{question.answeredBy}</span>{/if}
      {#if question.superseded > 0}
        <span
          class="revised"
          title="{question.superseded} earlier answer{question.superseded === 1
            ? ''
            : 's'} kept in answers-history.md"
          >revised {question.superseded}×</span>
      {/if}
    </p>
    <div class="prose">{question.answer}</div>
  {:else}
    <p class="head">
      <span class="mark open">Open — not yet answered</span>
    </p>
  {/if}
</aside>

<style>
  .answer-note {
    margin: 0.5em 0 1.25em;
    padding: 0.5em 0.9em;
    border-left: 3px solid;
    border-radius: 0 0.2em 0.2em 0;
    font-size: 0.94em;
  }
  .answer-note.answered {
    border-left-color: #2e7d43;
    background: rgba(46, 125, 67, 0.07);
  }
  .answer-note.open {
    border-left-color: #b08318;
    background: rgba(176, 131, 24, 0.07);
  }
  .head {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 0.7em;
    margin: 0;
    font-size: 0.82em;
  }
  .mark {
    text-transform: uppercase;
    letter-spacing: 0.07em;
    font-weight: 700;
  }
  .mark.answered {
    color: #2e7d43;
  }
  .mark.open {
    color: #8a6412;
  }
  .when,
  .who,
  .revised {
    opacity: 0.7;
    font-variant-numeric: tabular-nums;
  }
  .prose {
    margin-top: 0.45em;
    /* The answer is markdown someone typed. It is shown as written,
       newlines and all, rather than re-parsed: this tool renders a
       decision, and quietly reinterpreting one as markup is a way to
       change what it says. */
    white-space: pre-wrap;
  }

  @media (prefers-color-scheme: dark) {
    .answer-note.answered {
      background: rgba(127, 211, 155, 0.09);
      border-left-color: #7fd39b;
    }
    .answer-note.open {
      background: rgba(224, 194, 122, 0.09);
      border-left-color: #e0c27a;
    }
    .mark.answered {
      color: #7fd39b;
    }
    .mark.open {
      color: #e0c27a;
    }
  }

  @media print {
    .answer-note {
      border-left-color: #666;
      background: none;
    }
  }
</style>
