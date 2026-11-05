<!--
  FilterBar.svelte — the controls over a TanStack table: the search, a
  multi-select per enum or symbol column, a date range per date column,
  clearing them, and how many rows pass.

  Every control reads and writes the table's own state — its global
  filter and its column filters — so what the bar shows and what the
  table filters by cannot disagree. Which options a column offers and
  what each counts is `grid.ts` `facetsOf`, over TanStack's faceting.

  The bar is apparatus and carries `.docstrap-chrome`, so print shows the
  table and not its filters. A tool adds its own controls through the
  `before` and `after` snippets.
-->
<script lang="ts">
  import Search from '@lucide/svelte/icons/search';
  import X from '@lucide/svelte/icons/x';
  import type { Snippet } from 'svelte';

  import FacetMenu from './FacetMenu.svelte';
  import { facetsOf, isFaceted, isRanged, isSearched } from './grid';
  import type { Column, DateRange } from './table';

  let {
    table,
    columns,
    total,
    before,
    after,
  }: {
    // A TanStack table built on `grid.ts`'s features.
    table: any;
    /** The columns whose filters the bar offers. */
    columns: Column[];
    /** The rows there are before any filter: the count's denominator. */
    total: number;
    before?: Snippet;
    after?: Snippet;
  } = $props();

  const facets = $derived(columns.filter(isFaceted));
  const dates = $derived(columns.filter(isRanged));
  const searchable = $derived(columns.some(isSearched));

  const query = $derived((table.atoms.globalFilter.get() as string | undefined) ?? '');
  const filtering = $derived(table.atoms.columnFilters.get().length > 0 || query.trim() !== '');
  const passing = $derived(table.getFilteredRowModel().rows.length);

  function chosen(key: string): string[] {
    return (table.getColumn(key)?.getFilterValue() as string[] | undefined) ?? [];
  }

  function range(key: string): DateRange {
    return (table.getColumn(key)?.getFilterValue() as DateRange | undefined) ?? { from: '', to: '' };
  }

  function setRange(key: string, end: 'from' | 'to', value: string): void {
    table.getColumn(key)?.setFilterValue({ ...range(key), [end]: value });
  }

  function clear(): void {
    table.setColumnFilters([]);
    table.setGlobalFilter('');
  }
</script>

<div class="bar docstrap-chrome">
  {@render before?.()}
  {#if searchable}
    <label class="search">
      <Search size={14} aria-hidden="true" />
      <input
        type="search"
        name="search"
        placeholder="Search"
        bind:value={() => query, (v) => table.setGlobalFilter(v)}
      />
    </label>
  {/if}
  {#each facets as column (column.key)}
    <FacetMenu
      {column}
      options={facetsOf(table, column)}
      bind:chosen={() => chosen(column.key), (v) => table.getColumn(column.key)?.setFilterValue(v)}
    />
  {/each}
  {#each dates as column (column.key)}
    <span class="range" role="group" aria-label={column.label}>
      <span class="range-label">{column.label}</span>
      <input
        type="date"
        name="{column.key}-from"
        aria-label="{column.label} from"
        bind:value={() => range(column.key).from, (v) => setRange(column.key, 'from', v)}
      />
      <span aria-hidden="true">–</span>
      <input
        type="date"
        name="{column.key}-to"
        aria-label="{column.label} to"
        bind:value={() => range(column.key).to, (v) => setRange(column.key, 'to', v)}
      />
    </span>
  {/each}
  {#if filtering}
    <button type="button" class="clear" title="Clear filters" onclick={clear}>
      <X size={14} aria-hidden="true" />
    </button>
  {/if}
  <span class="count" aria-live="polite">{passing} of {total}</span>
  {@render after?.()}
</div>

<style>
  .bar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5em;
    margin: 1em 0 0.5em;
  }
  .search {
    display: inline-flex;
    align-items: center;
    gap: 0.35em;
    padding: 0.2em 0.5em;
    border: 1px solid var(--color-background-border, #c4c4c4);
    border-radius: 0.25em;
    background: var(--color-background-primary, #fff);
    color: var(--color-foreground-secondary, #666);
  }
  .search input {
    width: 12em;
    border: none;
    outline: none;
    background: transparent;
    color: var(--color-foreground-primary, #222);
    font: inherit;
    font-size: 0.85em;
  }
  .range {
    display: inline-flex;
    align-items: center;
    gap: 0.3em;
    font-size: 0.85em;
    color: var(--color-foreground-secondary, #666);
  }
  .range input {
    padding: 0.15em 0.3em;
    border: 1px solid var(--color-background-border, #c4c4c4);
    border-radius: 0.25em;
    background: var(--color-background-primary, #fff);
    color: var(--color-foreground-primary, #222);
    font: inherit;
  }
  .clear {
    display: inline-flex;
    align-items: center;
    padding: 0.3em;
    border: 1px solid var(--color-background-border, #c4c4c4);
    border-radius: 0.25em;
    background: var(--color-background-primary, #fff);
    color: var(--color-foreground-secondary, #666);
    cursor: pointer;
  }
  .clear:hover {
    background: var(--color-background-hover, #f2f2f2);
  }
  .count {
    margin-left: auto;
    font-size: 0.85em;
    color: var(--color-foreground-secondary, #666);
    font-variant-numeric: tabular-nums;
  }
</style>
