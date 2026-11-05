<!--
  AnswerEditor.svelte — panel two: the answer to the selected question,
  saving as you type.

  A plain <textarea>. No editor library, no new dependency: the reusable
  thing across surfaces is the autosave BEHAVIOUR, not an
  editor component.

  That behaviour is a shared contract, reproduced and not restated — see
  `autosave.ts`. The three pieces of it that live here
  rather than in the timer:

    autosave §1  the form-level `oninput` trigger, and the `$effect` on
                 the tracked state as the backstop for programmatic
                 changes — loading a different question's answer, say
    autosave §3  Ctrl/Cmd+S cancels the pending debounce and fires now
    autosave §4  the binary indicator: "Draft saved" after a save
                 completes, gone the instant any input fires. Absence is
                 the unsaved signal.

  What is NOT part of that contract: Finish. Autosaving is how the text survives, and
  it is not how an answer counts — the first real run read a reply at
  three characters because the two were the same event. Every save here writes a DRAFT, which nothing
  downstream can see. Finish is the only thing that submits, and it is
  not here: it is one button at the foot of the question list that
  submits every draft at once (`Panels.svelte`, `finish.ts`). It sat
  under this field once per answer, over the bottom of it, and thirteen
  answers stayed drafts because nobody pressed thirteen buttons.

  Rewriting a submitted answer is ordinary. The autosaved
  revision sits BESIDE the submitted answer rather than on top of it —
  retyping a reply must not make the recorded decision disappear from
  every consumer for as long as the retyping takes — and submitting it
  keeps the answer it replaces.
-->
<script lang="ts">
  import { untrack } from 'svelte';

  import { describeApiFailure } from '../../../sphinx/ui/docstrap';
  import { autosave } from './autosave';
  import type { Selection } from './types';
  import { selectionId } from './types';

  let {
    selection,
    save,
    unsaved = $bindable(false),
  }: {
    selection: Selection | null;
    /** Persist one draft. Resolves when the server has it. */
    save: (target: Selection, text: string) => Promise<void>;
    /** Whether there is typing the autosave has not written yet — what
     *  lets Finish count it before the debounce has fired. */
    unsaved?: boolean;
  } = $props();

  let text = $state('');
  let savedVisible = $state(false);
  let error = $state('');
  let editor: HTMLTextAreaElement | null = $state(null);

  /** Whether the question on screen already has a finished answer. */
  const isSubmitted = $derived(selection ? selection.submitted : false);
  /** A revision typed over a submitted answer, not yet submitted itself. */
  const revising = $derived(
    isSubmitted && selection !== null && text.trim() !== selection.submittedAnswer.trim()
  );
  const superseded = $derived(selection ? selection.supersededCount : 0);

  // What the store holds for the question on screen. The $effect
  // backstop fires only when the text differs from this, which is what
  // separates "something changed the content" from "the same content
  // arrived again" — a re-read after a save hands back a new selection
  // object carrying the answer that was just written, and treating that
  // as an edit made every save schedule the next one.
  let baseline = '';

  /** The autosave in flight, if any — what `settle` waits for. */
  let inflight: Promise<void> = Promise.resolve();

  const saver = autosave<{ target: Selection; text: string }>((held) => {
    inflight = send(held.target, held.text);
  });

  /** One draft save. The status line is the whole report of a failure. */
  async function send(target: Selection, value: string): Promise<void> {
    try {
      await save(target, value);
      baseline = value;
      error = '';
      if (!saver.pending()) unsaved = false;
      // autosave §4 — visible only after the save actually completed,
      // only if nothing has been typed since, and only while the answer
      // it confirms is still the one on screen.
      const current = selection
        ? selectionId(selection.docSlug, selection.label)
        : null;
      if (!saver.pending() && current === selectionId(target.docSlug, target.label)) {
        savedVisible = true;
      }
    } catch (err) {
      savedVisible = false;
      // The write's own URL belongs to Panels, which resolved it from
      // the declaration; what this knows is what came back. A server
      // that answered is never reported as a server that is not there.
      error = `Not saved — ${describeApiFailure(err)}`;
    }
  }

  function bump(): void {
    if (!selection) return;
    savedVisible = false;
    error = '';
    unsaved = true;
    saver.bump({ target: selection, text });
  }

  /** autosave §1 — the canonical trigger. One handler on the form. */
  function onFormInput(): void {
    bump();
  }

  /** autosave §1 — the backstop, for changes that fire no input event.
   *
   * The text is the only tracked dependency. The selection is read
   * untracked deliberately: a selection object arriving again with the
   * same content is not an edit, and tracking it turned every save into
   * the trigger for the next one.
   */
  $effect(() => {
    const value = text;
    untrack(() => {
      if (!selection) return;
      if (value === baseline) return;
      bump();
    });
  });

  /** autosave §3 — cancel the debounce, save immediately. */
  function onKeydown(event: KeyboardEvent): void {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
      event.preventDefault();
      saver.flush();
    }
  }

  /** Load the incoming answer, and flush whatever the outgoing one had. */
  export function load(next: Selection | null): void {
    saver.flush();
    savedVisible = false;
    error = '';
    baseline = next ? next.answer : '';
    text = baseline;
  }

  export function flush(): void {
    saver.flush();
  }

  /** Flush, and resolve once the store has whatever was pending. What a
   *  caller about to submit, or to say the answers are done, waits for. */
  export async function settle(): Promise<void> {
    saver.flush();
    await inflight;
  }

  export function focus(): void {
    editor?.focus();
  }
</script>

<div class="editor">
  {#if selection}
    <div class="prompt">
      <span class="label">{selection.label}</span>
      <span class="text">{selection.text}</span>
      {#if revising}
        <span
          class="state revising"
          title="The submitted answer stands until you submit this revision.">Revising</span>
      {:else if isSubmitted}
        <span class="state submitted" title="Submitted {selection.submittedAt ?? ''}"
          >Submitted</span>
      {:else}
        <span class="state open">Open</span>
      {/if}
      {#if superseded > 0}
        <span
          class="state kept"
          title="{superseded} earlier answer{superseded === 1 ? '' : 's'} kept in answers-history.md"
          >{superseded} superseded</span>
      {/if}
    </div>
    <!-- autosave §1: the form-level oninput is the canonical trigger. -->
    <form class="form" oninput={onFormInput} onsubmit={(e) => e.preventDefault()}>
      <textarea
        bind:this={editor}
        bind:value={text}
        onkeydown={onKeydown}
        spellcheck="true"
        placeholder="Answer in markdown. Drafts save as you type; Finish, below the questions, submits them."
      ></textarea>
    </form>
    <div class="controls">
      <p class="status" aria-live="polite">
        {#if error}
          <span class="error">{error}</span>
        {:else if savedVisible}
          <span class="saved">{revising ? 'Revision saved' : isSubmitted ? 'Submitted' : 'Draft saved'}</span>
        {/if}
      </p>
    </div>
  {:else}
    <p class="idle">Select a question above.</p>
  {/if}
</div>

<style>
  .editor {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 0;
    padding: 0.6em 0.9em 0.3em;
    box-sizing: border-box;
  }
  .prompt {
    display: flex;
    gap: 0.6em;
    align-items: baseline;
    margin-bottom: 0.5em;
    font-size: 0.92em;
  }
  .prompt .label {
    font-weight: 600;
    font-variant-numeric: tabular-nums;
  }
  .prompt .text {
    flex: 1 1 auto;
    min-width: 0;
    opacity: 0.9;
    font-size: 1.3em;
  }
  .state {
    flex: 0 0 auto;
    font-size: 0.75em;
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }
  .state.submitted {
    color: #1b5e2b;
  }
  .state.revising {
    color: #7a5b10;
  }
  .state.open {
    opacity: 0.6;
  }
  .state.kept {
    opacity: 0.55;
  }
  .form {
    flex: 1 1 auto;
    min-height: 0;
    display: flex;
  }
  textarea {
    flex: 1 1 auto;
    width: 100%;
    min-height: 6em;
    padding: 0.5em 0.65em;
    border: 1px solid #c4c4c4;
    border-radius: 0.2em;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 1.144em;
    line-height: 1.5;
    resize: none;
    box-sizing: border-box;
    background: inherit;
    color: inherit;
  }
  textarea:focus {
    outline: 2px solid #4a7bb6;
    outline-offset: -1px;
  }
  .controls {
    display: flex;
    align-items: center;
    gap: 0.75em;
    margin-top: 0.35em;
    min-height: 1.9em;
  }
  .status {
    margin: 0;
    font-size: 0.8em;
  }
  .saved {
    color: #1b5e2b;
  }
  .error {
    color: #a02020;
  }
  .idle {
    margin: auto;
    opacity: 0.6;
  }

  @media (prefers-color-scheme: dark) {
    textarea {
      border-color: #364252;
    }
    .saved,
    .state.submitted {
      color: #7fd39b;
    }
    .state.revising {
      color: #e0c27a;
    }
    .error {
      color: #f08b8b;
    }
  }
</style>
