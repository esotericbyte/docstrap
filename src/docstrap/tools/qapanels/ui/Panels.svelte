<!--
  Panels.svelte — the three-panel Q&A mode.

  Three panels, in this order: the question list on top, the answer editor
  below it, the rendered document third. The selection is what binds
  them — picking a question in the list switches the editor to that
  question's answer and the reference to that question's document.

  The instrument takes the view, which is what makes it an instrument
  rather than a tool. Escape closes it and hands the page back.

  Where it sits is its host's business, not its own: it fills the box it
  is mounted in. On a documentation page that box is the fixed
  full-viewport root `index.ts` creates; in the viewer shell it is the
  right drawer. The shell also says where the
  reference panel's pages are, because there `window.location` is the
  shell's own URL and not a page of the project.

  The scope is an explicit choice in the header, not an inference from
  what comes back. It defaults to the
  document the instrument was opened on — the reader is looking at
  something, and that something's questions are what is wanted — with the
  whole project as the deliberate wider view. Both are URLs the
  declaration resolved; nothing here builds one.

  Finish is here, once, at the foot of the question list — not under each
  answer, where it covered the field and had to be pressed per question.
  One press submits every draft in scope; `finish.ts` holds its rules.
-->
<script lang="ts">
  import { onMount } from 'svelte';

  import {
    apiStatus,
    describeApiFailure,
    type DocstrapGlobal,
  } from '../../../sphinx/ui/docstrap';
  import AnswerEditor from './AnswerEditor.svelte';
  import {
    describeReport,
    finishState,
    pendingDrafts,
    submitDrafts,
    type Draft,
    type FinishReport,
  } from './finish';
  import QuestionList from './QuestionList.svelte';
  import Reference from './Reference.svelte';
  import type {
    AnswersDoneNotice,
    AnswersDoneResult,
    Delivery,
    QuestionDocument,
    QuestionListing,
    Selection,
    SubmitResult,
  } from './types';
  import { selectionId } from './types';

  let {
    d,
    onclose,
    referenceBase,
  }: {
    d: DocstrapGlobal;
    onclose: () => void;
    /** Where this project's pages are, ending in `/`. Omitted on a
     *  documentation page, which works it out from its own URL. */
    referenceBase?: string | null;
  } = $props();

  let listing = $state<QuestionListing | null>(null);
  let loadError = $state('');
  let selection = $state<Selection | null>(null);
  let editor = $state<ReturnType<typeof AnswerEditor> | null>(null);
  /** The last submission's delivered artifact, shown in the header. */
  let delivery = $state<Delivery | null>(null);
  /** The last "answers done" press, shown briefly beside its prompt. */
  let doneNotice = $state<AnswersDoneNotice | null>(null);
  let doneBusy = $state<string | null>(null);
  let doneTimer: number | null = null;
  /** Whether the editor holds typing its autosave has not written yet. */
  let unsaved = $state(false);
  let finishing = $state(false);
  /** What the last Finish came to, shown beside it. */
  let finishReport = $state<FinishReport | null>(null);

  // The declaration resolved this page's URLs for the instrument — the
  // project-wide read and write, and the same collection narrowed to
  // this document. There is nothing to append to either: a tool never
  // assembles a path, which is the part that once wrote derivatives into
  // a directory the project does not link to.
  const prefix = $derived(d.tools.route('qapanels'));
  const documentPrefix = $derived(d.tools.altRoute('qapanels'));

  // The requirement is that the scope be an explicit choice
  // rather than project-wide by omission. The default is the document, because the instrument is opened
  // while reading something and that something's questions are what is
  // wanted; the project is the deliberate wider view.
  //
  // A page with no document scope to offer — an aggregate index — has no
  // altRoute, and there the project scope is the only honest answer.
  let scope = $state<'document' | 'project'>('document');
  const canScopeToDocument = $derived(documentPrefix !== null);
  const readUrl = $derived(
    scope === 'document' && documentPrefix !== null ? documentPrefix : prefix
  );

  // Read once when the mode opens. Deliberately not an `$effect`: this
  // both reads and rewrites `selection`, and an effect that did that
  // would re-run itself every time a question was picked.
  onMount(() => {
    void reload();
  });

  async function reload(): Promise<void> {
    if (!readUrl) {
      loadError = 'No project context on this page.';
      return;
    }
    try {
      const next = await d.api<QuestionListing>(readUrl);
      listing = next;
      loadError = '';
      // Keep the selection pointing at the same question across a
      // reload, so answering does not throw the reader out of place.
      if (selection) {
        const again = find(next, selection.docSlug, selection.label);
        if (again) selection = again;
      }
    } catch (err) {
      d.silenceOfflineError(err);
      loadError = readFailure(err, readUrl);
    }
  }

  /**
   * What to say about a failed read — and, above all, what NOT to say.
   *
   * This asked after the server whatever went wrong. That is right for
   * exactly one of the cases `describeApiFailure` distinguishes and
   * actively misleading for the rest: a server that answered 404 is
   * plainly running, and pointing the reader at it hid a routing defect
   * that made every document below a project's docs_root unreadable
   * here. A status code means docstrap answered; only the absence of one
   * means it did not.
   */
  function readFailure(err: unknown, url: string): string {
    const subject =
      scope === 'document'
        ? `this document (${d.ctx.docSlug ?? 'unknown'})`
        : 'this project';
    const blame = apiStatus(err) === null ? '' : ` Nothing was read for ${subject}.`;
    return `Could not read the questions: ${describeApiFailure(err, url)}${blame}`;
  }

  function find(from: QuestionListing, docSlug: string, label: string): Selection | null {
    for (const entry of from.documents) {
      if (entry.docSlug !== docSlug) continue;
      for (const question of entry.questions) {
        if (question.label !== label) continue;
        return {
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
        };
      }
    }
    return null;
  }

  function select(next: Selection): void {
    if (selection && selectionId(selection.docSlug, selection.label) === selectionId(next.docSlug, next.label)) {
      editor?.focus();
      return;
    }
    // Switching IS the save event for the answer being left, which is
    // the autosave contract's shape: a context change flushes the outgoing
    // document and loads the incoming one. `load` does both.
    selection = next;
    editor?.load(next);
    editor?.focus();
  }

  /** The one write: a draft from the editor, or a submission from Finish. */
  async function post(
    docSlug: string,
    label: string,
    text: string,
    submitted: boolean
  ): Promise<SubmitResult> {
    if (!prefix) throw new Error('no project context');
    return d.api<SubmitResult>(prefix, {
      method: 'POST',
      body: {
        doc_slug: docSlug,
        label,
        answer: text,
        // False on every autosave and true only from Finish. The server
        // stores the flag; nothing downstream sees a draft.
        submitted,
      },
    });
  }

  async function save(target: Selection, text: string): Promise<void> {
    await post(target.docSlug, target.label, text, false);
    // The listing carries each question's stored answer and whether it
    // has a draft, and those just changed — which is also what tells
    // Finish there is something to submit. Re-read rather than patching
    // a copy: the listing is a scan and is meant to be disposable.
    await reload();
  }

  const drafts = $derived(pendingDrafts(listing));
  const finishButton = $derived(
    finishState(drafts, unsaved, selection ? selection.submitted : false, finishing)
  );

  /**
   * Finish: submit every draft in scope. The editor settles first, so
   * the store holds what is on screen and no pending autosave can land
   * afterwards and write a draft back over a submission; the listing is
   * re-read so the drafts submitted are the ones the store holds.
   */
  async function finish(): Promise<void> {
    if (finishing) return;
    finishing = true;
    finishReport = null;
    try {
      await editor?.settle();
      await reload();
      const report = await submitDrafts(
        pendingDrafts(listing),
        async (draft: Draft) => {
          const result = await post(draft.docSlug, draft.label, draft.answer, true);
          // A submission delivers an artifact beside the document.
          // Say where it went and what version it stamped — a delivery
          // nobody is told about is no delivery. The last one stands for
          // the press; each document's own is beside it on disk.
          if (result?.addendum) delivery = result.addendum;
        },
        (err) => {
          d.silenceOfflineError(err);
          return describeApiFailure(err, prefix);
        }
      );
      finishReport = report;
      await reload();
    } finally {
      finishing = false;
    }
  }

  /**
   * "Answers done" for one document. Answers save
   * continuously and this submits nothing: it waits for any pending
   * autosave to land, so the store holds what is on screen, then asks the
   * server to run the configured command once. Whatever came back is
   * shown briefly; there is no retry.
   */
  async function answersDone(entry: QuestionDocument): Promise<void> {
    const url = entry.answersDoneRoute;
    if (!url || doneBusy) return;
    doneBusy = entry.docSlug;
    let notice: AnswersDoneNotice;
    try {
      await editor?.settle();
      const result = await d.api<AnswersDoneResult>(url, { method: 'POST' });
      notice = result.ok
        ? { docSlug: entry.docSlug, ok: true, text: 'Sent' }
        : { docSlug: entry.docSlug, ok: false, text: result.error };
    } catch (err) {
      d.silenceOfflineError(err);
      notice = { docSlug: entry.docSlug, ok: false, text: describeApiFailure(err, url) };
    } finally {
      doneBusy = null;
    }
    doneNotice = notice;
    if (doneTimer !== null) window.clearTimeout(doneTimer);
    doneTimer = window.setTimeout(
      () => {
        doneNotice = null;
        doneTimer = null;
      },
      notice.ok ? 3000 : 8000
    );
  }

  /** Switching scope re-reads. The outgoing answer is flushed first,
   *  the same way switching question does — a context change is a save
   *  event, not a discard. */
  function setScope(next: 'document' | 'project'): void {
    if (scope === next) return;
    editor?.flush();
    scope = next;
    void reload();
  }

  function close(): void {
    editor?.flush();
    onclose();
  }

  /** Save whatever answer is pending, now. A host about to replace this
   *  instance — the shell re-pinning its questions document — calls it
   *  first, the same way a scope or question change flushes. */
  export function flush(): void {
    editor?.flush();
  }

  function onKeydown(event: KeyboardEvent): void {
    if (event.key === 'Escape') {
      event.preventDefault();
      close();
    }
  }

  // The reference panel reads the built site. This page is one of its
  // pages, so its own URL says where the others are: strip this page's
  // own doc slug off the path and what is left is the project's base.
  function projectBase(): string | null {
    const slug = d.ctx.docSlug;
    if (!slug) return null;
    const suffix = `${slug}.html`;
    const here = window.location.pathname;
    return here.endsWith(suffix) ? here.slice(0, here.length - suffix.length) : null;
  }

  const referenceUrl = $derived.by(() => {
    if (!selection) return null;
    const base = referenceBase === undefined ? projectBase() : referenceBase;
    return base === null ? null : `${base}${selection.docSlug}.html`;
  });

  // The header said "{count} open" while counting every question found,
  // answered or not. The server now reports both, and open means nobody
  // has finished answering it — a draft is still open.
  const count = $derived(listing ? listing.count : 0);
  const open = $derived(listing ? listing.open : 0);
</script>

<svelte:window onkeydown={onKeydown} />

<section class="panels docstrap-chrome" aria-label="Q&A panels">
  <header class="bar">
    <span class="title">Questions — {listing ? listing.title : ''}</span>
    <!-- The scope is said out loud, not inferred from what happens to
         come back. -->
    <span class="scope" role="group" aria-label="Question scope">
      <button
        type="button"
        class:on={scope === 'document' && canScopeToDocument}
        disabled={!canScopeToDocument}
        title={canScopeToDocument
          ? 'Only the questions this document poses'
          : 'This page is not a document, so it has no questions of its own'}
        onclick={() => setScope('document')}>This document</button>
      <button
        type="button"
        class:on={scope === 'project' || !canScopeToDocument}
        title="Every question this project's documents pose"
        onclick={() => setScope('project')}>Whole project</button>
    </span>
    <span class="count">{open} open of {count}</span>
    {#if delivery}
      <span
        class="delivered"
        title="Answer addendum written to {delivery.path}"
        >delivered · {delivery.version}</span>
    {/if}
    <button type="button" class="close" onclick={close} title="Close (Esc)">Close</button>
  </header>

  {#if loadError}
    <p class="error">{loadError}</p>
  {/if}

  <div class="panel panel-list">
    <QuestionList
      documents={listing ? listing.documents : []}
      selected={selection}
      onselect={select}
      onanswersdone={answersDone}
      notice={doneNotice}
      busy={doneBusy}
    >
      {#snippet footer()}
        <!-- Below the last question, in the list's own flow, so it can
             never sit over a field. -->
        <div class="finish-row">
          <button
            type="button"
            class="finish"
            disabled={finishButton.disabled}
            title={finishButton.title}
            onclick={finish}>{finishButton.label}</button>
          <span class="finish-note" aria-live="polite">
            {#if finishing}
              Submitting…
            {:else if finishReport}
              <span class:failed={finishReport.failed.length > 0}
                >{describeReport(finishReport)}</span>
            {:else if finishButton.disabled}
              Nothing to submit.
            {:else if drafts.length > 0}
              {drafts.length} draft{drafts.length === 1 ? '' : 's'} not yet submitted.
            {:else}
              The answer being typed is saved first, then submitted.
            {/if}
          </span>
        </div>
      {/snippet}
    </QuestionList>
  </div>

  <div class="panel panel-editor">
    <AnswerEditor bind:this={editor} bind:unsaved {selection} {save} />
  </div>

  <div class="panel panel-reference">
    <Reference url={referenceUrl} path={selection ? selection.path : ''} />
  </div>
</section>

<style>
  .panels {
    height: 100%;
    display: flex;
    flex-direction: column;
    background: #f6f7f9;
    color: #1a1a1a;
    font-family:
      system-ui,
      -apple-system,
      'Segoe UI',
      sans-serif;
  }
  .bar {
    flex: 0 0 auto;
    display: flex;
    align-items: center;
    gap: 0.9em;
    padding: 0.45em 0.9em;
    background: #26333f;
    color: #f2f5f8;
    font-size: 0.9em;
  }
  .title {
    font-weight: 600;
  }
  .scope {
    display: inline-flex;
    border: 1px solid rgba(255, 255, 255, 0.3);
    border-radius: 0.2em;
    overflow: hidden;
  }
  .scope button {
    padding: 0.2em 0.7em;
    border: 0;
    background: none;
    color: inherit;
    font: inherit;
    font-size: 0.88em;
    cursor: pointer;
    opacity: 0.7;
  }
  .scope button + button {
    border-left: 1px solid rgba(255, 255, 255, 0.3);
  }
  .scope button:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.12);
  }
  .scope button.on {
    background: rgba(255, 255, 255, 0.22);
    opacity: 1;
    font-weight: 600;
  }
  .scope button:disabled {
    opacity: 0.35;
    cursor: default;
  }
  .delivered {
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 0.8em;
    padding: 0.15em 0.5em;
    border-radius: 0.2em;
    background: rgba(127, 211, 155, 0.22);
  }
  .count {
    margin-right: auto;
    opacity: 0.75;
    font-variant-numeric: tabular-nums;
  }
  .close {
    padding: 0.25em 0.8em;
    border: 1px solid rgba(255, 255, 255, 0.35);
    border-radius: 0.2em;
    background: none;
    color: inherit;
    font: inherit;
    cursor: pointer;
  }
  .close:hover {
    background: rgba(255, 255, 255, 0.12);
  }
  .finish-row {
    display: flex;
    align-items: center;
    gap: 0.75em;
    padding: 0.6em 0.9em 0.5em;
    margin-top: 0.5em;
    border-top: 1px solid #dfe3e8;
  }
  .finish {
    flex: 0 0 auto;
    padding: 0.3em 1em;
    border: 1px solid #4a7bb6;
    border-radius: 0.2em;
    background: #4a7bb6;
    color: #fff;
    font: inherit;
    font-size: 0.88em;
    cursor: pointer;
  }
  .finish:hover:not(:disabled) {
    background: #3a6ba6;
  }
  .finish:disabled {
    opacity: 0.5;
    cursor: default;
  }
  .finish-note {
    min-width: 0;
    font-size: 0.8em;
    opacity: 0.8;
  }
  .finish-note .failed {
    color: #a02020;
  }
  .error {
    flex: 0 0 auto;
    margin: 0;
    padding: 0.5em 0.9em;
    background: #fbe9e9;
    color: #7a1e1e;
    font-size: 0.85em;
  }
  .panel {
    min-height: 0;
    background: #fff;
    border-top: 1px solid #dfe3e8;
  }
  /* Shares of the host's height, not the viewport's: the overlay's host
     is the viewport, so there these are the 28vh and 22vh they were. */
  .panel-list {
    flex: 0 0 28%;
  }
  .panel-editor {
    flex: 0 0 22%;
  }
  .panel-reference {
    flex: 1 1 auto;
  }

  @media (prefers-color-scheme: dark) {
    .panels {
      background: #12171c;
      color: #e6e8ea;
    }
    .panel {
      background: #1a2027;
      border-top-color: #2c353f;
    }
    .error {
      background: #3a2020;
      color: #f2c0c0;
    }
    .finish-row {
      border-top-color: #2c353f;
    }
    .finish-note .failed {
      color: #f08b8b;
    }
  }
</style>
