// grid.ts — docstrap's columns on TanStack Table, with no DOM and no Svelte.
//
// TanStack Table (`@tanstack/table-core`, through `@tanstack/svelte-table`
// in a component) owns the row models: sorting, column filters, the search,
// facet counts, grouping, expansion and column sizes. What it cannot know is
// docstrap's own column declaration (`table.ts`'s `Column`) — what a type
// means, how an enum or symbol column orders its values, that an empty cell
// sorts last either way, that a search is every term somewhere in the row —
// and that is all this module says. It turns a declaration into a TanStack
// column definition and the reader's filter choices into TanStack's filter
// values; it never re-sorts or re-filters a row itself.
//
// Headless: TanStack draws nothing, so a tool still draws its own markup
// with its own scoped styles.
//
// Under Node, `tests/datatable/grid.test.ts` drives a real TanStack table
// built from these definitions with `constructTable`.

import {
  columnFacetingFeature,
  columnFilteringFeature,
  columnGroupingFeature,
  columnPinningFeature,
  columnSizingFeature,
  columnVisibilityFeature,
  createExpandedRowModel,
  createFacetedRowModel,
  createFacetedUniqueValues,
  createFilteredRowModel,
  createGroupedRowModel,
  createSortedRowModel,
  globalFilteringFeature,
  rowExpandingFeature,
  rowSortingFeature,
  tableFeatures,
} from '@tanstack/table-core';
import type { ColumnDef, FilterFn, Row as TanRow, SortFn } from '@tanstack/table-core';

import {
  NONE,
  cellText,
  cellValues,
  compareCells,
  rank,
  type Cell,
  type Column,
  type DateRange,
  type Row,
} from './table.ts';

/** Every TanStack feature a docstrap table uses, registered once. */
export const gridFeatures = {
  columnVisibilityFeature,
  columnSizingFeature,
  columnPinningFeature,
  columnFilteringFeature,
  globalFilteringFeature,
  filteredRowModel: createFilteredRowModel(),
  columnFacetingFeature,
  facetedRowModel: createFacetedRowModel(),
  facetedUniqueValues: createFacetedUniqueValues(),
  columnGroupingFeature,
  groupedRowModel: createGroupedRowModel(),
  rowSortingFeature,
  sortedRowModel: createSortedRowModel(),
  rowExpandingFeature,
  expandedRowModel: createExpandedRowModel(),
};

export const features = tableFeatures(gridFeatures);
export type Features = typeof features;

/** The hidden column the search box reads: see `searchColumn`. */
export const SEARCH = '_search';

function isEmpty(value: Cell | undefined): boolean {
  return cellValues(value).every((v) => v === NONE);
}

/** A choice filter: the row has one of the chosen values. */
export const choiceFilter: FilterFn<any, any> = Object.assign(
  (row: TanRow<any, any>, columnId: string, chosen: string[]) =>
    row.getUniqueValues(columnId).some((v) => chosen.includes(v as string)),
  { autoRemove: (chosen: unknown) => !Array.isArray(chosen) || chosen.length === 0 }
);

/** A date filter: the row's day is inside the range, either end open. */
export const rangeFilter: FilterFn<any, any> = Object.assign(
  (row: TanRow<any, any>, columnId: string, range: DateRange) => {
    const day = cellText(row.getValue(columnId) as Cell).slice(0, 10);
    if (day === '') return false;
    if (range.from !== '' && day < range.from) return false;
    if (range.to !== '' && day > range.to) return false;
    return true;
  },
  { autoRemove: (range: DateRange | undefined) => !range || (range.from === '' && range.to === '') }
);

/** The search: every whitespace-separated term somewhere in the row. */
export const searchFilter: FilterFn<any, any> = Object.assign(
  (row: TanRow<any, any>, columnId: string, query: string) => {
    const haystack = String(row.getValue(columnId) ?? '');
    return query
      .toLowerCase()
      .split(/\s+/)
      .filter(Boolean)
      .every((term) => haystack.includes(term));
  },
  { autoRemove: (query: unknown) => typeof query !== 'string' || query.trim() === '' }
);

/** Whether a column takes part in the text search. */
export function isSearched(column: Column): boolean {
  return column.filterable && (column.type === 'text' || column.type === 'link');
}

/** Whether a column is filtered by a choice of its values. */
export function isFaceted(column: Column): boolean {
  return column.filterable && (column.type === 'enum' || column.type === 'symbol');
}

/** Whether a column is filtered by a date range. */
export function isRanged(column: Column): boolean {
  return column.filterable && column.type === 'date';
}

/** A docstrap column as a TanStack column.
 *
 * The value is the cell, or undefined when it is empty, so TanStack puts
 * empty cells last in both directions (`sortUndefined: 'last'`); the
 * comparison is `table.ts`'s `compareCells`, ascending, which TanStack
 * reverses for descending. A cell's distinct values are its unique
 * values, so a list cell counts once under each of its values in a facet. */
export function columnDef<R extends Row>(column: Column, size?: number): ColumnDef<Features, R, any> {
  const sortFn: SortFn<any, any> = (a, b, id) =>
    compareCells(a.getValue(id) as Cell, b.getValue(id) as Cell, column);
  return {
    id: column.key,
    header: column.label,
    accessorFn: (row: R) => {
      const value = row.cells[column.key];
      return isEmpty(value) ? undefined : value;
    },
    getUniqueValues: (row: R) => cellValues(row.cells[column.key]),
    enableSorting: column.sortable,
    sortFn,
    sortUndefined: 'last',
    sortDescFirst: false,
    enableColumnFilter: isFaceted(column) || isRanged(column),
    filterFn: isRanged(column) ? rangeFilter : choiceFilter,
    enableGlobalFilter: false,
    enableGrouping: true,
    ...(size !== undefined ? { size, minSize: size, maxSize: size } : {}),
    meta: { column },
  } as ColumnDef<Features, R, any>;
}

/** The hidden column the search reads: every searched column's text,
 *  lowercased, one per line, so a term never spans two cells. */
export function searchColumn<R extends Row>(columns: Column[]): ColumnDef<Features, R, any> {
  const searched = columns.filter(isSearched);
  return {
    id: SEARCH,
    accessorFn: (row: R) =>
      searched.map((c) => cellText(row.cells[c.key]).toLowerCase()).join('\n'),
    enableSorting: false,
    enableColumnFilter: false,
    enableGlobalFilter: true,
    enableGrouping: false,
  } as ColumnDef<Features, R, any>;
}

/** The table options every docstrap table shares. */
export const gridOptions = {
  globalFilterFn: searchFilter,
  getColumnCanGlobalFilter: (column: { id: string }) => column.id === SEARCH,
  enableSortingRemoval: true,
  enableMultiSort: false,
  groupedColumnMode: false as const,
};

export interface FacetOption {
  value: string;
  /** The value as shown: its symbol for a symbol column. */
  label: string;
  /** Rows having it among those every OTHER filter lets through. */
  count: number;
}

const collator = new Intl.Collator(undefined, { numeric: true, sensitivity: 'base' });

/** The options a choice filter offers, in order, with TanStack's counts.
 *
 * `present` is every value the rows hold before any filter; `counts` is
 * the column's faceted unique values, taken by TanStack over the rows
 * every other filter lets through. Every present value is offered, plus
 * any already chosen, so narrowing one filter never makes another's
 * choice disappear. Order is the column's declared `values`, then the
 * rest alphabetically, with the empty value last. */
export function facetOptions(
  column: Column,
  present: Iterable<unknown>,
  counts: Map<unknown, number>,
  chosen: string[]
): FacetOption[] {
  const values = new Set<string>(chosen);
  for (const v of present) values.add(v as string);
  return [...values]
    .sort((a, b) => {
      if (a === NONE || b === NONE) return a === b ? 0 : a === NONE ? 1 : -1;
      const ra = rank(column, a);
      const rb = rank(column, b);
      if (ra !== rb) return ra < rb ? -1 : 1;
      return collator.compare(a, b);
    })
    .map((value) => ({
      value,
      label: value === NONE ? '' : cellText(value, column.symbols),
      count: counts.get(value) ?? 0,
    }));
}

/** A choice filter's options on a live table: the values the rows hold
 *  before any filter, counted under every other filter. */
export function facetsOf(table: any, column: Column): FacetOption[] {
  const live = table.getColumn(column.key);
  const present = new Set<unknown>();
  for (const row of table.getCoreRowModel().rows) {
    for (const v of row.getUniqueValues(column.key)) present.add(v);
  }
  const chosen = (live?.getFilterValue() as string[] | undefined) ?? [];
  return facetOptions(column, present, live?.getFacetedUniqueValues() ?? new Map(), chosen);
}

/** How many records a group row holds: its leaves, not the groups between.
 *  TanStack's `getLeafRows` lists the nested group rows too. */
export function leafCount(row: { subRows: any[] }): number {
  return row.subRows.reduce((n, sub) => n + (sub.subRows.length ? leafCount(sub) : 1), 0);
}
