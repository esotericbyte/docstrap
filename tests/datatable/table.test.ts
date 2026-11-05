// The datatable tool's columns on TanStack Table — `ui/table.ts` (what a
// cell is) and `ui/grid.ts` (a docstrap column as a TanStack one) under
// Node, through a real TanStack table built the way `DataTable.svelte`
// builds it, so the sorting and filtering asserted here are TanStack's.
//
// Run by `npm test` in packages/docstrap, and by
// `tests/test_datatable.py`, which is how `pytest` reaches it.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

import { constructTable, tableFeatures } from '@tanstack/table-core';
import { storeReactivityBindings } from '@tanstack/table-core/store-reactivity-bindings';

import {
  columnDef,
  facetsOf,
  gridFeatures,
  gridOptions,
  isSearched,
  searchColumn,
} from '../../src/docstrap/tools/datatable/ui/grid.ts';
import {
  NONE,
  cellText,
  cellValues,
  type Column,
  type Row,
} from '../../src/docstrap/tools/datatable/ui/table.ts';

const columns: Column[] = [
  { key: 'id', label: 'Task', type: 'link', sortable: true, filterable: true },
  { key: 'title', label: 'Title', type: 'text', sortable: true, filterable: true },
  { key: 'unit', label: 'Unit', type: 'text', sortable: true, filterable: false },
  { key: 'filed', label: 'Filed', type: 'date', sortable: true, filterable: true },
  {
    key: 'state',
    label: 'State',
    type: 'enum',
    sortable: true,
    filterable: true,
    values: ['queued', 'held', 'blocked', 'in_flight'],
  },
  {
    key: 'work',
    label: 'Work',
    type: 'symbol',
    sortable: true,
    filterable: true,
    values: ['code', 'docs', 'docs+code'],
    symbols: { code: '🔨', docs: '📝', 'docs+code': '🔨📝' },
  },
  { key: 'duplicates', label: 'Duplicates', type: 'enum', sortable: false, filterable: true },
  { key: 'size', label: 'Size', type: 'text', sortable: true, filterable: false },
];

function row(cells: Row['cells']): Row {
  return { cells, links: {} };
}

const rows: Row[] = [
  row({ id: 'fm-10', title: 'Tidy the launcher', unit: null, filed: '2026-09-02', state: 'held', work: 'code', duplicates: [], size: 10 }),
  row({ id: 'fm-2', title: 'Write the census page', unit: 'docs', filed: '2026-10-01', state: 'queued', work: 'docs', duplicates: ['fm-9'], size: 2 }),
  row({ id: 'fm-9', title: 'Census summary', unit: 'docs', filed: null, state: 'blocked', work: 'docs+code', duplicates: ['fm-2'], size: 9 }),
  row({ id: 'fm-3', title: 'Launcher keyboard', unit: null, filed: '2026-08-15', state: 'queued', work: 'code', duplicates: [], size: 3 }),
];

test('cellText matches the shared fixture the Python renderer is held to', () => {
  const url = new URL('../fixtures/datatable/cell-text.json', import.meta.url);
  const cases = JSON.parse(readFileSync(url, 'utf8'));
  for (const { value, symbols, text } of cases) {
    assert.equal(cellText(value, symbols), text, JSON.stringify(value));
  }
});

test('cellValues gives the empty value for null and for an empty list', () => {
  assert.deepEqual(cellValues(null), [NONE]);
  assert.deepEqual(cellValues([]), [NONE]);
  assert.deepEqual(cellValues(['a', 'a', 'b']), ['a', 'b']);
  assert.deepEqual(cellValues(3), ['3']);
});

const features = tableFeatures({ coreReactivityFeature: storeReactivityBindings(), ...gridFeatures });

/** The table `DataTable.svelte` builds over these rows. */
function build(): any {
  return constructTable({
    features,
    columns: [...columns.map((c) => columnDef(c)), searchColumn(columns)],
    data: rows,
    ...gridOptions,
  } as any);
}

const shown = (table: any) => table.getRowModel().rows.map((r: any) => r.original.cells.id);

function sorted(key: string, desc = false): string[] {
  const table = build();
  table.setSorting([{ id: key, desc }]);
  return shown(table);
}

function filtered(set: (table: any) => void): string[] {
  const table = build();
  set(table);
  return shown(table);
}

const choose = (key: string, chosen: unknown) => (table: any) => table.getColumn(key).setFilterValue(chosen);
const search = (query: string) => (table: any) => table.setGlobalFilter(query);

test('no sort keeps the given order', () => {
  assert.deepEqual(shown(build()), ['fm-10', 'fm-2', 'fm-9', 'fm-3']);
});

test('text sorts naturally, so fm-2 comes before fm-10', () => {
  assert.deepEqual(sorted('id'), ['fm-2', 'fm-3', 'fm-9', 'fm-10']);
  assert.deepEqual(sorted('id', true), ['fm-10', 'fm-9', 'fm-3', 'fm-2']);
});

test('numbers sort as numbers', () => {
  assert.deepEqual(sorted('size'), ['fm-2', 'fm-3', 'fm-9', 'fm-10']);
});

test('dates sort chronologically with empty dates last in both directions', () => {
  assert.deepEqual(sorted('filed'), ['fm-3', 'fm-10', 'fm-2', 'fm-9']);
  assert.deepEqual(sorted('filed', true), ['fm-2', 'fm-10', 'fm-3', 'fm-9']);
});

test('enums sort by declared order, ties keeping the given order', () => {
  assert.deepEqual(sorted('state'), ['fm-2', 'fm-3', 'fm-10', 'fm-9']);
});

test('empty text cells sort last', () => {
  assert.deepEqual(sorted('unit', true), ['fm-2', 'fm-9', 'fm-10', 'fm-3']);
});

test('a column declared unsortable cannot be sorted', () => {
  const table = build();
  assert.equal(table.getColumn('duplicates').getCanSort(), false);
  assert.equal(table.getColumn('state').getCanSort(), true);
});

test('a header cycles ascending, descending, off', () => {
  const table = build();
  const filed = table.getColumn('filed');
  filed.toggleSorting();
  assert.equal(filed.getIsSorted(), 'asc');
  filed.toggleSorting();
  assert.equal(filed.getIsSorted(), 'desc');
  filed.toggleSorting();
  assert.equal(filed.getIsSorted(), false);
  table.getColumn('state').toggleSorting();
  assert.equal(filed.getIsSorted(), false, 'one column sorts at a time');
});

test('search matches every term, case-insensitively, over filterable text and link columns', () => {
  assert.deepEqual(filtered(search('CENSUS')), ['fm-2', 'fm-9']);
  assert.deepEqual(filtered(search('census page')), ['fm-2']);
  assert.deepEqual(filtered(search('fm-1')), ['fm-10']);
  // `unit` is not filterable, so it is not searched.
  assert.deepEqual(filtered(search('docs')), []);
});

test('a multi-select keeps rows having any chosen value', () => {
  assert.deepEqual(filtered(choose('state', ['queued', 'blocked'])), ['fm-2', 'fm-9', 'fm-3']);
  assert.deepEqual(filtered(choose('state', [])), ['fm-10', 'fm-2', 'fm-9', 'fm-3']);
});

test('a list cell matches by membership, and the empty value finds empty lists', () => {
  assert.deepEqual(filtered(choose('duplicates', ['fm-2'])), ['fm-9']);
  assert.deepEqual(filtered(choose('duplicates', [NONE])), ['fm-10', 'fm-3']);
});

test('a date range is inclusive, open at an empty end, and excludes undated rows', () => {
  const range = (from: string, to: string) => choose('filed', { from, to });
  assert.deepEqual(filtered(range('2026-09-02', '')), ['fm-10', 'fm-2']);
  assert.deepEqual(filtered(range('', '2026-09-02')), ['fm-10', 'fm-3']);
  assert.deepEqual(filtered(range('', '')), ['fm-10', 'fm-2', 'fm-9', 'fm-3']);
});

test('filters combine, and a column declared unfilterable offers none', () => {
  assert.deepEqual(
    filtered((table) => {
      search('launcher')(table);
      choose('state', ['queued'])(table);
    }),
    ['fm-3']
  );
  const table = build();
  assert.equal(table.getColumn('unit').getCanFilter(), false);
  assert.equal(table.getColumn('state').getCanFilter(), true);
});

test('a filter at rest is no filter at all', () => {
  const table = build();
  table.getColumn('state').setFilterValue([]);
  table.getColumn('filed').setFilterValue({ from: '', to: '' });
  table.setGlobalFilter('  ');
  assert.deepEqual(table.atoms.columnFilters.get(), []);
  table.getColumn('state').setFilterValue(['held']);
  assert.equal(table.atoms.columnFilters.get().length, 1);
});

test('the search needs a filterable text or link column', () => {
  assert.equal(columns.some(isSearched), true);
  assert.equal(columns.filter((c) => c.type !== 'text' && c.type !== 'link').some(isSearched), false);
});

test('facet options follow declared order, label symbols, and count under the other filters', () => {
  const table = build();
  table.getColumn('work').setFilterValue(['code']);
  table.setGlobalFilter('launcher');
  assert.deepEqual(facetsOf(table, columns[5]), [
    { value: 'code', label: '🔨', count: 2 },
    { value: 'docs', label: '📝', count: 0 },
    { value: 'docs+code', label: '🔨📝', count: 0 },
  ]);
});

test('facet options keep a chosen value nothing has, and put the empty value last', () => {
  const table = build();
  table.getColumn('duplicates').setFilterValue(['fm-77']);
  assert.deepEqual(
    facetsOf(table, columns[6]).map((o) => [o.value, o.count]),
    [['fm-2', 1], ['fm-9', 1], ['fm-77', 0], [NONE, 2]]
  );
});
