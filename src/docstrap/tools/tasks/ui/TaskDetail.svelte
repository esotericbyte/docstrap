<!--
  TaskDetail.svelte — one task opened under its row.

  What the row has no room for — why it is held or blocked, its plan, the
  evidence it is done elsewhere, every recommendation with its note — and
  the one decision a person can make on this task. One task, one decision:
  there is no control here, or anywhere in the tool, that acts on more
  than the task it sits under.
-->
<script lang="ts">
  import Save from '@lucide/svelte/icons/save';

  import type { Decision } from './types';
  import type { Task } from './tasks.ts';

  let {
    task,
    decision,
    actions,
    onsave,
  }: {
    task: Task;
    decision: Decision | null;
    /** Null when this page can record no decision: no route, or the
     *  decisions could not be read. */
    actions: string[] | null;
    /** Resolves to an error to show, or null once it is stored. */
    onsave: (action: string, note: string) => Promise<string | null>;
  } = $props();

  // Seeded once from what is stored: this is the person's own edit from
  // then on, and a stored decision arriving later must not overwrite it.
  // svelte-ignore state_referenced_locally
  let action = $state(decision?.action ?? '');
  // svelte-ignore state_referenced_locally
  let note = $state(decision?.note ?? '');
  let busy = $state(false);
  let outcome = $state<{ ok: boolean; text: string } | null>(null);

  const changed = $derived(
    action !== '' && (action !== (decision?.action ?? '') || note.trim() !== (decision?.note ?? ''))
  );

  async function save(): Promise<void> {
    if (!changed || busy) return;
    busy = true;
    const error = await onsave(action, note);
    busy = false;
    outcome = error === null ? { ok: true, text: 'Saved' } : { ok: false, text: error };
  }

  const facts = $derived(
    [
      ['Hold', task.hold_reason],
      ['Blocked by', task.blocked_by.join(', ')],
      ['Plan', task.plan],
      ['Evidence', task.done_evidence],
      ['Stage', [task.lifecycle_stage, task.lifecycle_evidence].filter(Boolean).join(': ')],
    ].filter(([, value]) => value)
  );
</script>

<div class="detail">
  {#if facts.length}
    <dl>
      {#each facts as [term, value] (term)}
        <dt>{term}</dt>
        <dd>{value}</dd>
      {/each}
    </dl>
  {/if}

  {#if task.recommendations.length || task.latest_recommendation}
    <ol class="recommendations">
      {#each task.recommendations.length ? task.recommendations : [task.latest_recommendation!] as r, i (i)}
        <li>
          <span class="action">{r.action}</span>
          <span class="meta">{r.date} · {r.by}</span>
          {#if r.note}<span class="note">{r.note}</span>{/if}
        </li>
      {/each}
    </ol>
  {/if}

  {#if actions}
    <form
      class="decide"
      onsubmit={(event) => {
        event.preventDefault();
        void save();
      }}
    >
      <div class="choices" role="radiogroup" aria-label="Decision on {task.id}">
        {#each actions as choice (choice)}
          <label class:chosen={action === choice}>
            <input type="radio" name="decision-{task.id}" value={choice} bind:group={action} />
            {choice}
          </label>
        {/each}
      </div>
      <textarea name="note-{task.id}" rows="2" placeholder="Note" bind:value={note}></textarea>
      <div class="actions">
        {#if decision}
          <span class="meta">{decision.action ?? '—'} · {decision.decidedAt}</span>
        {/if}
        {#if outcome}
          <span class="outcome" class:failed={!outcome.ok} aria-live="polite">{outcome.text}</span>
        {/if}
        <button type="submit" class="save" disabled={!changed || busy}>
          <Save size={14} aria-hidden="true" />Save
        </button>
      </div>
    </form>
  {/if}
</div>

<style>
  .detail {
    display: flex;
    flex-direction: column;
    gap: 0.6em;
    padding: 0.4em 0.2em 0.6em;
    white-space: normal;
  }
  dl {
    display: grid;
    grid-template-columns: max-content 1fr;
    gap: 0.2em 0.8em;
    margin: 0;
  }
  dt {
    color: var(--color-foreground-secondary, #666);
  }
  dd {
    margin: 0;
  }
  .recommendations {
    margin: 0;
    padding-left: 1.4em;
  }
  .recommendations li + li {
    margin-top: 0.2em;
  }
  .action {
    font-weight: 600;
  }
  .meta {
    color: var(--color-foreground-secondary, #666);
    font-variant-numeric: tabular-nums;
  }
  .note::before {
    content: ' — ';
  }
  .decide {
    display: flex;
    flex-direction: column;
    gap: 0.4em;
    max-width: 48em;
  }
  .choices {
    display: flex;
    flex-wrap: wrap;
    gap: 0.3em;
  }
  .choices label {
    display: inline-flex;
    align-items: center;
    padding: 0.15em 0.6em;
    border: 1px solid var(--color-background-border, #c4c4c4);
    border-radius: 1em;
    background: var(--color-background-primary, #fff);
    cursor: pointer;
  }
  .choices label:hover {
    background: var(--color-background-hover, #f2f2f2);
  }
  .choices label.chosen {
    border-color: var(--color-brand-primary, #4a7bb6);
    background: var(--color-brand-primary, #4a7bb6);
    color: var(--color-background-primary, #fff);
  }
  .choices input {
    position: absolute;
    opacity: 0;
    pointer-events: none;
  }
  .choices label:has(input:focus-visible) {
    outline: 2px solid var(--color-brand-primary, #4a7bb6);
    outline-offset: 1px;
  }
  textarea {
    padding: 0.3em 0.5em;
    border: 1px solid var(--color-background-border, #c4c4c4);
    border-radius: 0.25em;
    background: var(--color-background-primary, #fff);
    color: var(--color-foreground-primary, #222);
    font: inherit;
    resize: vertical;
  }
  .actions {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 0.6em;
  }
  .outcome {
    color: var(--color-foreground-secondary, #666);
  }
  .outcome.failed {
    color: var(--color-problematic, #b00);
  }
  .save {
    display: inline-flex;
    align-items: center;
    gap: 0.35em;
    padding: 0.25em 0.8em;
    border: 1px solid var(--color-brand-primary, #4a7bb6);
    border-radius: 0.25em;
    background: var(--color-brand-primary, #4a7bb6);
    color: var(--color-background-primary, #fff);
    font: inherit;
    cursor: pointer;
  }
  .save:disabled {
    opacity: 0.45;
    cursor: default;
  }
</style>
