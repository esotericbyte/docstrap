<!--
  TaskList.svelte — the task list: grouped, drilled into, sorted, filtered.

  Mounted in place of the plain table the `docstrap-tasks` directive
  rendered, from the same data. The controls are apparatus and carry
  `.docstrap-chrome`, so print shows the list and not its filters.

  The table is TanStack Table's (`@tanstack/svelte-table`): it sorts,
  filters, searches, counts each facet, groups, collapses and sizes the
  columns, from the column definitions `grid.ts` makes of docstrap's.
  Which columns there are, the groups' order, what a drill-down keeps and
  how the view is written into the address is `tasks.ts`. This holds the
  reader's place, draws the rows TanStack hands back, and talks to the
  decisions route.
-->
<script lang="ts">
  import Activity from '@lucide/svelte/icons/activity';
  import ArrowDown from '@lucide/svelte/icons/arrow-down';
  import ArrowUp from '@lucide/svelte/icons/arrow-up';
  import ArrowUpDown from '@lucide/svelte/icons/arrow-up-down';
  import CheckCheck from '@lucide/svelte/icons/check-check';
  import ChevronDown from '@lucide/svelte/icons/chevron-down';
  import ChevronRight from '@lucide/svelte/icons/chevron-right';
  import CircleCheck from '@lucide/svelte/icons/circle-check';
  import FolderTree from '@lucide/svelte/icons/folder-tree';
  import GitMerge from '@lucide/svelte/icons/git-merge';
  import Layers from '@lucide/svelte/icons/layers';
  import { createTable } from '@tanstack/svelte-table';
  import { onMount } from 'svelte';
  import { SvelteSet } from 'svelte/reactivity';

  import { describeApiFailure, type DocstrapGlobal } from '../../../sphinx/ui/docstrap';
  import FilterBar from '../../datatable/ui/FilterBar.svelte';
  import { features, gridOptions, leafCount } from '../../datatable/ui/grid';
  import { cellText, type Column } from '../../datatable/ui/table.ts';
  import TaskDetail from './TaskDetail.svelte';
  import {
    NO_PROJECT,
    columnDefs,
    columns as columnsFor,
    crumbs,
    drillInto,
    groupSteps,
    groupingFor,
    inGroupOrder,
    narrow,
    readView,
    toRow,
    visibility,
    writeView,
    type GroupBy,
    type Step,
    type TaskData,
    type TaskRow,
    type View,
  } from './tasks.ts';
  import type {
    AnswersDoneResult,
    Decision,
    DecisionStored,
    PageDecisions,
  } from './types';

  let {
    data,
    docstrap,
    route,
    address,
  }: {
    data: TaskData;
    docstrap: DocstrapGlobal;
    /** The decisions route on this page, or null: nothing can be decided. */
    route: string | null;
    /** The window whose address carries the view. */
    address: Window;
  } = $props();

  // The data is the page's and never changes while it is open.
  // svelte-ignore state_referenced_locally
  const vocabulary = data.vocabulary;
  // svelte-ignore state_referenced_locally
  const rows = data.tasks.map(toRow);
  const defs = columnDefs(vocabulary);

  // svelte-ignore state_referenced_locally
  let view = $state<View>(readView(new URLSearchParams(address.location.search)));

  const shown = $derived(columnsFor(vocabulary, view.group, view.drill));
  /** The drill-down narrows what the table is given; the filters narrow
   *  what it shows. Ordered so TanStack's groups come in the list's order. */
  const narrowed = $derived(inGroupOrder(narrow(rows, view.drill), view.group, vocabulary));

  const table = createTable({
    features,
    columns: defs,
    get data() {
      return narrowed;
    },
    getRowId: (row: TaskRow) => row.task.id,
    ...gridOptions,
    initialState: {
      // Every group open; collapsing one is the reader's.
      expanded: true,
      columnPinning: { start: ['id'], end: [] },
    },
    state: {
      get grouping() {
        return groupingFor(view.group);
      },
      get columnVisibility() {
        return visibility(vocabulary, shown);
      },
    },
  });

  /** Opened tasks: a row's detail, which is not a TanStack expansion —
   *  that is the groups'. */
  const opened = new SvelteSet<string>();

  // The view goes into the address whenever it moves, beside whatever
  // else is there — the viewer's `?doc-url=` stays as it is. Replaced,
  // not pushed: a reader moving about the list is not navigating.
  $effect(() => {
    const location = address.location;
    const params = writeView(new URLSearchParams(location.search), view).toString();
    const next = `${location.pathname}${params ? `?${params}` : ''}${location.hash}`;
    if (next !== `${location.pathname}${location.search}${location.hash}`) {
      address.history.replaceState(address.history.state, '', next);
    }
  });

  function go(drill: Step[]): void {
    view = { group: view.group, drill };
  }

  function drill(steps: Step[]): void {
    go(drillInto(view.drill, steps));
  }

  function setGroup(group: GroupBy): void {
    view = { group, drill: view.drill };
  }

  function same(a: Step[], b: Step[]): boolean {
    return a.length === b.length && a.every((s, i) => s.dim === b[i].dim && s.value === b[i].value);
  }

  function toggle(set: SvelteSet<string>, key: string): void {
    if (set.has(key)) set.delete(key);
    else set.add(key);
  }

  // --- decisions -------------------------------------------------------

  let decisions = $state<Record<string, Decision>>({});
  let actions = $state<string[] | null>(null);
  let answersDoneRoute = $state<string | null>(null);
  let loadError = $state('');

  onMount(() => {
    void load();
  });

  async function load(): Promise<void> {
    if (!route) return;
    try {
      const page = await docstrap.api<PageDecisions>(route);
      decisions = page.decisions;
      actions = page.actions;
      answersDoneRoute = page.answersDoneRoute;
    } catch (err) {
      docstrap.silenceOfflineError(err);
      loadError = describeApiFailure(err, route);
    }
  }

  async function decide(taskId: string, action: string, note: string): Promise<string | null> {
    if (!route) return 'this page has no decisions route';
    try {
      const stored = await docstrap.api<DecisionStored>(route, {
        method: 'POST',
        body: { task_id: taskId, action, note },
      });
      decisions = { ...decisions, [stored.taskId]: stored.decision };
      return null;
    } catch (err) {
      docstrap.silenceOfflineError(err);
      return describeApiFailure(err, route);
    }
  }

  let doneBusy = $state(false);
  let doneNotice = $state<{ ok: boolean; text: string } | null>(null);
  let doneTimer: number | null = null;

  /** "Answers done" for this page: the configured
   *  command, run once by the server. Decisions are saved as they are
   *  made, so there is nothing to wait for first. */
  async function answersDone(): Promise<void> {
    const url = answersDoneRoute;
    if (!url || doneBusy) return;
    doneBusy = true;
    let notice: { ok: boolean; text: string };
    try {
      const result = await docstrap.api<AnswersDoneResult>(url, { method: 'POST' });
      notice = result.ok ? { ok: true, text: 'Sent' } : { ok: false, text: result.error };
    } catch (err) {
      docstrap.silenceOfflineError(err);
      notice = { ok: false, text: describeApiFailure(err, url) };
    } finally {
      doneBusy = false;
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

  // --- drawing ---------------------------------------------------------

  function stepLabel(step: Step): string {
    if (step.dim === 'stuck') {
      const symbol = vocabulary.stuck.symbols?.[step.value];
      return symbol ? `${symbol} ${step.value}` : step.value;
    }
    if (step.dim === 'project') return step.value || NO_PROJECT;
    return step.value || '—';
  }

  const sorting = $derived(table.atoms.sorting.get());

  function ariaSort(column: Column): 'ascending' | 'descending' | 'none' | undefined {
    if (!column.sortable) return undefined;
    const entry = sorting.find((s: { id: string }) => s.id === column.key);
    if (!entry) return 'none';
    return entry.desc ? 'descending' : 'ascending';
  }

  /** The width TanStack holds a column to, and where a pinned one sticks. */
  function place(id: string): string {
    const live = table.getColumn(id);
    if (!live) return '';
    const width = `width:${live.getSize()}px;min-width:${live.getSize()}px;max-width:${live.getSize()}px`;
    return live.getIsPinned() === 'start' ? `${width};left:${live.getStart('start')}px` : width;
  }

  const span = $derived(shown.length);
  const tableWidth = $derived(shown.reduce((sum, c) => sum + (table.getColumn(c.key)?.getSize() ?? 0), 0));
  const rendered = $derived(table.getRowModel().rows);
</script>

{#snippet symbol(column: Column, row: TaskRow)}
  {@const value = row.cells[column.key]}
  <span title={cellText(value)}>{cellText(value, column.symbols).trim()}</span>
{/snippet}

{#snippet cell(column: Column, row: TaskRow)}
  {@const task = row.task}
  {#if column.key === 'project'}
    <button type="button" class="drill" onclick={() => drill([{ dim: 'project', value: task.project }])}
      >{task.project || NO_PROJECT}</button>
  {:else if column.key === 'unit'}
    {#if task.unit}
      <span class="wrap"
        ><button
          type="button"
          class="drill"
          onclick={() =>
            drill([
              { dim: 'project', value: task.project },
              { dim: 'unit', value: task.unit },
            ])}>{task.unit}</button
        ></span>
    {/if}
  {:else if column.key === 'state'}
    {#if task.state}
      <button type="button" class="drill" onclick={() => drill([{ dim: 'state', value: task.state }])}
        >{task.state}</button>
    {/if}
  {:else if column.key === 'stuck'}
    {#if task.stuck}
      <button
        type="button"
        class="drill"
        title={task.stuck}
        onclick={() => drill([{ dim: 'stuck', value: task.stuck }])}
        >{cellText(task.stuck, column.symbols)}</button>
    {/if}
  {:else if column.key === 'lifecycle_stage'}
    {#if task.lifecycle_stage}
      <span title={task.lifecycle_evidence}>{task.lifecycle_stage}</span>
    {/if}
  {:else if column.key === 'recommendation'}
    {@const latest = task.latest_recommendation}
    {#if latest}
      <span title={latest.note}
        ><span class="action">{latest.action}</span><span class="meta"
          >{[latest.date, latest.by].filter(Boolean).join(' · ')}</span
        ></span>
    {/if}
  {:else if column.type === 'symbol'}
    {@render symbol(column, row)}
  {:else if column.type === 'text'}
    {@const text = cellText(row.cells[column.key])}
    {#if text}<span class="wrap">{text}</span>{/if}
  {:else}
    {cellText(row.cells[column.key])}
  {/if}
{/snippet}

{#snippet taskId(row: TaskRow)}
  {@const task = row.task}
  {@const open = opened.has(task.id)}
  <span class="id-cell">
    <button
      type="button"
      class="icon"
      aria-expanded={open}
      aria-label="{open ? 'Close' : 'Open'} {task.id}"
      onclick={() => toggle(opened, task.id)}
    >
      {#if open}<ChevronDown size={14} aria-hidden="true" />{:else}<ChevronRight
          size={14}
          aria-hidden="true"
        />{/if}
    </button>
    {#if decisions[task.id]}
      <span class="decided" title="{decisions[task.id].action ?? ''} · {decisions[task.id].decidedAt}"
        ><CircleCheck size={13} aria-hidden="true" /></span>
    {/if}
    <span class="task-id" title={task.id}
      >{#if task.link}<a class="reference" href={task.link}>{task.id}</a>{:else}{task.id}{/if}</span
    >
    {#if task.tangle_link}
      <a
        class="reference tangle"
        href={task.tangle_link}
        title="Duplicate and overlapping work: {task.tangle}"
        aria-label="{task.id} on the overlaps page"><GitMerge size={13} aria-hidden="true" /></a
      >
    {/if}
  </span>
{/snippet}

{#snippet heading(row: any)}
  {@const first = row.getLeafRows().find((r: any) => !r.getIsGrouped())?.original as TaskRow}
  {@const steps = groupSteps(view.drill, view.group, row.depth, first.task)}
  {@const step = steps.find((s) => s.dim === row.groupingColumnId) ?? steps[steps.length - 1]}
  {@const shut = !row.getIsExpanded()}
  <tr class={row.depth === 0 ? 'group' : 'unit'}>
    <th colspan={span}>
      <span class="heading">
        <button
          type="button"
          class="icon"
          aria-expanded={!shut}
          aria-label="{shut ? 'Expand' : 'Collapse'} {stepLabel(step)}"
          onclick={() => row.toggleExpanded()}
        >
          {#if shut}<ChevronRight size={14} aria-hidden="true" />{:else}<ChevronDown
              size={14}
              aria-hidden="true"
            />{/if}
        </button>
        {#if same(steps, view.drill)}
          <span class="name" title={stepLabel(step)}>{stepLabel(step)}</span>
        {:else}
          <button type="button" class="name drill" title={stepLabel(step)} onclick={() => go(steps)}
            >{stepLabel(step)}</button>
        {/if}
        <span class="badge">{leafCount(row)}</span>
      </span>
    </th>
  </tr>
{/snippet}

<FilterBar {table} columns={shown} total={narrowed.length}>
  {#snippet before()}
    <span class="segmented" role="group" aria-label="Group by">
      <button
        type="button"
        aria-pressed={view.group === 'project'}
        onclick={() => setGroup('project')}><FolderTree size={14} aria-hidden="true" />Project</button>
      <button
        type="button"
        aria-pressed={view.group !== 'project'}
        onclick={() => setGroup(view.group === 'project' ? 'state' : view.group)}
        ><Activity size={14} aria-hidden="true" />Status</button>
    </span>
    {#if view.group !== 'project'}
      <span class="segmented" role="group" aria-label="Status">
        <button type="button" aria-pressed={view.group === 'state'} onclick={() => setGroup('state')}
          >State</button>
        <button type="button" aria-pressed={view.group === 'stuck'} onclick={() => setGroup('stuck')}
          >Stuck</button>
      </span>
    {/if}
  {/snippet}
  {#snippet after()}
    {#if answersDoneRoute}
      {#if doneNotice}
        <span class="notice" class:failed={!doneNotice.ok} aria-live="polite">{doneNotice.text}</span>
      {/if}
      <button type="button" class="done" disabled={doneBusy} onclick={answersDone}
        ><CheckCheck size={14} aria-hidden="true" />Answers done</button>
    {/if}
  {/snippet}
</FilterBar>
{#if loadError}
  <p class="load-error docstrap-chrome" role="alert">{loadError}</p>
{/if}

<nav class="crumbs docstrap-chrome" aria-label="Drill-down">
  {#if view.drill.length}
    <button type="button" class="drill" onclick={() => go([])}
      ><Layers size={14} aria-hidden="true" />All</button>
  {:else}
    <span class="here"><Layers size={14} aria-hidden="true" />All</span>
  {/if}
  {#each crumbs(view.drill) as crumb, i (i)}
    <ChevronRight size={13} class="sep" aria-hidden="true" />
    {#if i === view.drill.length - 1}
      <span class="here" aria-current="location">{stepLabel(crumb.step)}</span>
    {:else}
      <button type="button" class="drill" onclick={() => go(crumb.drill)}>{stepLabel(crumb.step)}</button>
    {/if}
  {/each}
</nav>

<div class="table-wrapper">
  <table class="docutils align-default sized" style="width:{tableWidth}px">
    <thead>
      <tr>
        {#each shown as column (column.key)}
          {@const live = table.getColumn(column.key)}
          <th
            class="head"
            data-type={column.type}
            data-key={column.key}
            aria-sort={ariaSort(column)}
            style={place(column.key)}
          >
            <button type="button" class="sort" onclick={() => live?.toggleSorting()}>
              <span>{column.label}</span>
              {#if !live?.getIsSorted()}
                <ArrowUpDown size={13} class="idle" aria-hidden="true" />
              {:else if live.getIsSorted() === 'asc'}
                <ArrowUp size={13} aria-hidden="true" />
              {:else}
                <ArrowDown size={13} aria-hidden="true" />
              {/if}
            </button>
          </th>
        {/each}
      </tr>
    </thead>
    <tbody>
      {#each rendered as row (row.id)}
        {#if row.getIsGrouped()}
          {@render heading(row)}
        {:else}
          {@const task = row.original as TaskRow}
          {@const open = opened.has(task.task.id)}
          <tr class:open>
            {#each shown as column (column.key)}
              <td data-type={column.type} data-key={column.key} style={place(column.key)}
                >{#if column.key === 'id'}{@render taskId(task)}{:else}{@render cell(column, task)}{/if}</td
              >
            {/each}
          </tr>
          {#if open}
            <tr class="detail-row">
              <td colspan={span}>
                <TaskDetail
                  task={task.task}
                  decision={decisions[task.task.id] ?? null}
                  {actions}
                  onsave={(action, note) => decide(task.task.id, action, note)}
                />
              </td>
            </tr>
          {/if}
        {/if}
      {/each}
    </tbody>
  </table>
</div>

<style>
  .segmented {
    display: inline-flex;
    border: 1px solid var(--color-background-border, #c4c4c4);
    border-radius: 0.25em;
    overflow: hidden;
  }
  .segmented button {
    display: inline-flex;
    align-items: center;
    gap: 0.35em;
    padding: 0.25em 0.6em;
    border: none;
    background: var(--color-background-primary, #fff);
    color: var(--color-foreground-primary, #222);
    font: inherit;
    font-size: 0.85em;
    cursor: pointer;
  }
  .segmented button + button {
    border-left: 1px solid var(--color-background-border, #c4c4c4);
  }
  .segmented button:hover {
    background: var(--color-background-hover, #f2f2f2);
  }
  .segmented button[aria-pressed='true'] {
    background: var(--color-brand-primary, #4a7bb6);
    color: var(--color-background-primary, #fff);
  }
  .done {
    display: inline-flex;
    align-items: center;
    gap: 0.35em;
    padding: 0.25em 0.6em;
    border: 1px solid var(--color-background-border, #c4c4c4);
    border-radius: 0.25em;
    background: var(--color-background-primary, #fff);
    color: var(--color-foreground-primary, #222);
    font: inherit;
    font-size: 0.85em;
    cursor: pointer;
  }
  .done:hover {
    background: var(--color-background-hover, #f2f2f2);
  }
  .done:disabled {
    opacity: 0.5;
    cursor: default;
  }
  .notice {
    font-size: 0.85em;
    color: var(--color-foreground-secondary, #666);
  }
  .notice.failed,
  .load-error {
    color: var(--color-problematic, #b00);
  }
  .load-error {
    margin: 0 0 0.5em;
    font-size: 0.85em;
  }
  .crumbs {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.3em;
    margin: 0 0 0.5em;
    font-size: 0.9em;
  }
  .crumbs :global(.sep) {
    opacity: 0.5;
  }
  .crumbs .here {
    display: inline-flex;
    align-items: center;
    gap: 0.3em;
    font-weight: 600;
  }
  .drill {
    display: inline-flex;
    align-items: center;
    gap: 0.3em;
    padding: 0;
    border: none;
    background: none;
    color: var(--color-link, #2962ff);
    font: inherit;
    cursor: pointer;
    text-align: left;
  }
  .drill:hover {
    text-decoration: underline;
  }
  td .drill {
    color: inherit;
  }
  td .drill:hover {
    color: var(--color-link, #2962ff);
  }
  .icon {
    display: inline-flex;
    align-items: center;
    padding: 0.1em;
    border: none;
    background: none;
    color: var(--color-foreground-secondary, #666);
    cursor: pointer;
  }
  tr.unit th {
    padding-left: 1.6em;
    font-weight: 500;
  }
  .heading {
    display: inline-flex;
    align-items: center;
    gap: 0.4em;
  }
  .badge {
    min-width: 1.4em;
    padding: 0 0.4em;
    border-radius: 0.7em;
    background: var(--color-background-border, #ddd);
    color: var(--color-foreground-primary, #222);
    font-size: 0.85em;
    font-weight: 400;
    text-align: center;
    font-variant-numeric: tabular-nums;
  }
  .id-cell {
    display: flex;
    align-items: center;
    gap: 0.2em;
  }
  /* The opener and the decided mark keep their size; the id takes what
     is left and is cut short there. */
  .id-cell > .icon,
  .id-cell > .decided,
  .id-cell > :global(.tangle) {
    flex: none;
  }
  .id-cell > :global(.task-id) {
    flex: 1 1 auto;
  }
  .decided {
    display: inline-flex;
    vertical-align: middle;
    color: var(--color-brand-primary, #4a7bb6);
  }
  .sort {
    display: inline-flex;
    align-items: center;
    gap: 0.3em;
    padding: 0;
    border: none;
    background: none;
    color: inherit;
    font: inherit;
    font-weight: inherit;
    text-align: left;
    cursor: pointer;
  }
  .sort :global(.idle) {
    opacity: 0.35;
  }
  .sort:hover :global(.idle) {
    opacity: 0.8;
  }
  tr.open td {
    border-bottom-color: transparent;
  }
</style>
