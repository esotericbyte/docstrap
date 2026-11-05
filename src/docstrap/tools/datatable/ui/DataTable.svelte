<!--
  DataTable.svelte — one sortable, filterable table.

  Mounted in place of the plain table the `docstrap-datatable` directive
  rendered, from the same data. The controls above it are apparatus and
  carry `.docstrap-chrome`, so print shows the table and not its filters;
  the table is the document.

  The table is TanStack Table's (`@tanstack/svelte-table`): it sorts,
  filters, searches and counts each facet, from the column definitions
  `grid.ts` makes of the declared columns. This draws the rows it hands
  back.
-->
<script lang="ts">
  import ArrowDown from '@lucide/svelte/icons/arrow-down';
  import ArrowUp from '@lucide/svelte/icons/arrow-up';
  import ArrowUpDown from '@lucide/svelte/icons/arrow-up-down';
  import { createTable } from '@tanstack/svelte-table';

  import FilterBar from './FilterBar.svelte';
  import { SEARCH, columnDef, features, gridOptions, searchColumn } from './grid';
  import { cellText, type Column, type Row, type TableData } from './table';

  let { data }: { data: TableData } = $props();

  // The data is the page's and never changes while it is open.
  // svelte-ignore state_referenced_locally
  const columns = data.columns;
  // svelte-ignore state_referenced_locally
  const rows = data.rows;

  const table = createTable({
    features,
    columns: [...columns.map((c) => columnDef<Row>(c)), searchColumn<Row>(columns)],
    data: rows,
    ...gridOptions,
    initialState: { columnVisibility: { [SEARCH]: false } },
  });

  function ariaSort(column: Column): 'ascending' | 'descending' | 'none' | undefined {
    if (!column.sortable) return undefined;
    const sorted = table.getColumn(column.key)?.getIsSorted();
    if (!sorted) return 'none';
    return sorted === 'asc' ? 'ascending' : 'descending';
  }
</script>

{#snippet cell(row: Row, column: Column)}
  {@const value = row.cells[column.key]}
  {#if column.type === 'link' && row.links[column.key]}
    <a class="reference" href={row.links[column.key]}>{cellText(value)}</a>
  {:else if column.type === 'symbol' && column.symbols}
    <span title={cellText(value)}>{cellText(value, column.symbols)}</span>
  {:else}
    {cellText(value)}
  {/if}
{/snippet}

<FilterBar {table} {columns} total={rows.length} />

<div class="table-wrapper scroll">
  <table class="docutils align-default">
    <thead>
      <tr>
        {#each columns as column (column.key)}
          {@const live = table.getColumn(column.key)}
          <th class="head" data-type={column.type} aria-sort={ariaSort(column)}>
            {#if column.sortable}
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
            {:else}
              {column.label}
            {/if}
          </th>
        {/each}
      </tr>
    </thead>
    <tbody>
      {#each table.getRowModel().rows as row (row.id)}
        <tr>
          {#each columns as column (column.key)}
            <td data-type={column.type}>{@render cell(row.original, column)}</td>
          {/each}
        </tr>
      {/each}
    </tbody>
  </table>
</div>

<style>
  .scroll {
    overflow-x: auto;
  }
  table {
    width: 100%;
    font-size: 0.85em;
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
    cursor: pointer;
    white-space: nowrap;
  }
  .sort :global(.idle) {
    opacity: 0.35;
  }
  .sort:hover :global(.idle) {
    opacity: 0.8;
  }
  td[data-type='date'] {
    font-variant-numeric: tabular-nums;
  }
  /* A key, a day or one of a few values reads as one piece; prose wraps. */
  td[data-type='link'],
  td[data-type='date'],
  td[data-type='enum'],
  td[data-type='symbol'] {
    white-space: nowrap;
  }
  td[data-type='text'] {
    min-width: 12em;
  }
  td[data-type='symbol'] {
    text-align: center;
  }
</style>
