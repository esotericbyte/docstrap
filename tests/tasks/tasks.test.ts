// The task tool's columns, grouping, drill-down and address rules —
// `ui/tasks.ts` under Node, with a real TanStack table built from it the
// way the page builds one, so sorting, filtering, the search and the
// groups are TanStack's as they are in the page.
//
// Run by `npm test` in packages/docstrap, and by `tests/test_tasks.py`,
// which is how `pytest` reaches it.
import assert from 'node:assert/strict';
import { test } from 'node:test';

import { readFileSync } from 'node:fs';
import { constructTable, tableFeatures } from '@tanstack/table-core';
import { storeReactivityBindings } from '@tanstack/table-core/store-reactivity-bindings';

import { gridFeatures, gridOptions, leafCount } from '../../src/docstrap/tools/datatable/ui/grid.ts';
import {
  DRILL_PARAM,
  GROUP_PARAM,
  SIZES,
  columnDefs,
  columns,
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
  type Task,
  type TaskRow,
  type Vocabulary,
} from '../../src/docstrap/tools/tasks/ui/tasks.ts';

const vocabulary: Vocabulary = {
  state: { values: ['queued', 'held', 'blocked', 'in_flight'] },
  work: { values: ['code', 'docs'], symbols: { code: '🔨', docs: '📝' } },
  stuck: {
    values: ['ready', 'captain', 'blocked', 'needs-plan', 'external', 'stalled'],
    symbols: { ready: '▶️', captain: '⏳', blocked: '🔒' },
  },
  alignment: { values: ['aligned', 'drifted'], symbols: { aligned: '🟢', drifted: '🟡' } },
  done_elsewhere: { values: ['yes', 'likely', 'no'], symbols: { yes: '✅', likely: '♻️', no: '' } },
  lifecycle_stage: { values: ['filed', 'specified', 'branch', 'landed', 'deployed'] },
  action: { values: ['close-done', 'dispatch', 'hold'] },
};

function task(fields: Partial<Task> & { id: string }): Task {
  return {
    title: '',
    project: 'alpha',
    unit: '',
    state: 'queued',
    hold_reason: '',
    blocked_by: [],
    filed: '',
    last_activity: '',
    work: 'code',
    stuck: 'ready',
    alignment: 'aligned',
    plan: '',
    done_elsewhere: 'no',
    done_evidence: '',
    lifecycle_stage: '',
    lifecycle_evidence: '',
    tangle: '',
    latest_recommendation: null,
    recommendations: [],
    link: null,
    tangle_link: null,
    ...fields,
  };
}

const tasks: Task[] = [
  task({ id: 'p-1', project: 'sample-platform', unit: 'packages/docstrap', state: 'held', stuck: 'captain' }),
  task({ id: 'd-1', project: 'alpha', unit: 'apps/players', state: 'queued' }),
  task({ id: 'n-1', project: 'none', unit: '', state: 'blocked', stuck: 'blocked' }),
  task({ id: 'd-2', project: 'alpha', unit: '', state: 'queued', done_evidence: 'landed in 1a2b3c' }),
  task({ id: 'd-3', project: 'alpha', unit: 'apps/players', state: 'mystery', stuck: 'captain' }),
  task({
    id: 'f-1',
    project: 'firstmate',
    unit: 'bin',
    state: 'in_flight',
    done_elsewhere: 'likely',
    lifecycle_stage: 'branch',
    lifecycle_evidence: 'worktree fm/dev-ci',
    tangle: 'tangle-dev-server-ci',
  }),
];
const rows = tasks.map(toRow);

const ids = (list: { task: Task }[]) => list.map((r) => r.task.id);

const features = tableFeatures({ coreReactivityFeature: storeReactivityBindings(), ...gridFeatures });

/** The list's TanStack table, built as `TaskList.svelte` builds it. */
function build(group: GroupBy = 'project', drill: Step[] = [], expanded = true): any {
  return constructTable({
    features,
    columns: columnDefs(vocabulary),
    data: inGroupOrder(narrow(rows, drill), group, vocabulary),
    getRowId: (row: TaskRow) => row.task.id,
    ...gridOptions,
    initialState: { expanded: expanded ? true : {} },
    state: {
      grouping: groupingFor(group),
      columnVisibility: visibility(vocabulary, columns(vocabulary, group, drill)),
    },
  } as any);
}

/** The ids the filters let through, in the file's order. */
const passing = (table: any) => table.getFilteredRowModel().rows.map((r: any) => r.id);

/** The groups as drawn: [value, records, and the next level or the ids]. */
function groups(table: any): unknown[] {
  const level = (list: any[]): unknown[] =>
    list.map((r) => [
      r.getLeafRows().find((l: any) => !l.getIsGrouped()).original.task[r.groupingColumnId],
      leafCount(r),
      r.subRows[0]?.getIsGrouped() ? level(r.subRows) : r.subRows.map((l: any) => l.id),
    ]);
  return level(table.getGroupedRowModel().rows);
}

// --- rows and columns --------------------------------------------------------

test('a task becomes a datatable row that keeps its task and its link', () => {
  const linked = toRow(task({ id: 'x', link: 'tasks/x.html', filed: '', last_activity: '2026-10-01' }));
  assert.deepEqual(linked.links, { id: 'tasks/x.html' });
  assert.equal(linked.cells.filed, null, 'an empty date is an empty cell, so it sorts last');
  assert.equal(linked.cells.last_activity, '2026-10-01');
  assert.equal(linked.task.id, 'x');
  assert.deepEqual(toRow(task({ id: 'y' })).links, {});
});

test('a row holds only its own task: no duplicates in done elsewhere', () => {
  assert.equal(rows[5].cells.done_elsewhere, 'likely');
  assert.equal(rows[5].cells.lifecycle_stage, 'branch');
  assert.ok(!Object.values(rows[5].cells).some((c) => String(c).includes('d-1')), 'no other task named');
});

test('the project column is shown only by status and outside a project', () => {
  const byProject = columns(vocabulary, 'project').map((c) => c.key);
  assert.deepEqual(byProject, [
    'id',
    'title',
    'filed',
    'last_activity',
    'state',
    'work',
    'stuck',
    'alignment',
    'done_elsewhere',
    'lifecycle_stage',
    'recommendation',
  ]);
  assert.deepEqual(columns(vocabulary, 'state').map((c) => c.key).slice(0, 4), [
    'id',
    'title',
    'project',
    'unit',
  ]);
  assert.ok(
    !columns(vocabulary, 'state', [{ dim: 'project', value: 'alpha' }]).some((c) => c.key === 'project'),
    'drilled into one project, every row is that project'
  );
});

test('the unit column is shown only when the units are not the headings', () => {
  assert.ok(!columns(vocabulary, 'project').some((c) => c.key === 'unit'), 'by project, a unit heads its rows');
  assert.ok(
    !columns(vocabulary, 'project', [{ dim: 'project', value: 'alpha' }]).some((c) => c.key === 'unit')
  );
  for (const group of ['state', 'stuck'] as const) {
    assert.ok(columns(vocabulary, group).some((c) => c.key === 'unit'), `by ${group}, a unit is a column`);
  }
});

test('the facets are work, stuck, alignment, done elsewhere, stage and recommendation', () => {
  const facets = columns(vocabulary, 'stuck')
    .filter((c) => c.filterable && (c.type === 'enum' || c.type === 'symbol'))
    .map((c) => c.key);
  assert.deepEqual(facets, ['work', 'stuck', 'alignment', 'done_elsewhere', 'lifecycle_stage', 'recommendation']);
  const ranges = columns(vocabulary, 'project')
    .filter((c) => c.filterable && c.type === 'date')
    .map((c) => c.key);
  assert.deepEqual(ranges, ['filed', 'last_activity']);
});

test('the search reads id, title, unit and evidence, shown or not', () => {
  for (const group of ['project', 'state'] as const) {
    const table = build(group);
    const search = (query: string) => {
      table.setGlobalFilter(query);
      return passing(table);
    };
    assert.deepEqual(search('1a2b3c'), ['d-2'], 'evidence is searched though never shown');
    assert.deepEqual(search('apps/players'), ['d-1', 'd-3'], `the unit, column or heading, by ${group}`);
    assert.deepEqual(search('f-1'), ['f-1']);
    assert.deepEqual(search('fm/dev-ci'), ['f-1'], 'the lifecycle evidence too');
    assert.deepEqual(search('apps d-3'), ['d-3'], 'every term, anywhere in the row');
  }
});

test('a lifecycle stage facet finds the tasks at that stage', () => {
  const table = build();
  table.getColumn('lifecycle_stage').setFilterValue(['branch']);
  assert.deepEqual(passing(table), ['f-1']);
});

test('the facets count each value under every other filter', () => {
  const table = build();
  table.getColumn('stuck').setFilterValue(['captain']);
  const stuck = table.getColumn('stuck').getFacetedUniqueValues();
  assert.equal(stuck.get('ready'), 3, 'its own filter does not narrow its counts');
  const work = table.getColumn('work').getFacetedUniqueValues();
  assert.equal(work.get('code'), 2, 'another filter does');
});

test('every shown column has a fixed size, and the task id is compact', () => {
  const table = build('state');
  for (const column of columns(vocabulary, 'state')) {
    assert.equal(table.getColumn(column.key).getSize(), SIZES[column.key], column.key);
  }
  assert.ok(SIZES.id < SIZES.title / 1.5, 'the id no longer outweighs the title');
});

test('the plain table is given the same widths as the drawn list', () => {
  const css = readFileSync(new URL('../../src/docstrap/tools/tasks/ui/tasks.css', import.meta.url), 'utf8');
  const plain = ['id', 'title', 'unit', 'filed', 'last_activity', 'state', 'work', 'stuck', 'alignment', 'done_elsewhere', 'lifecycle_stage', 'recommendation'];
  for (const key of plain) {
    const match = css.match(new RegExp(`\\.docstrap-tasks-static th\\[data-key='${key}'\\] \\{ width: (\\d+)px; \\}`));
    assert.ok(match, key);
    assert.equal(Number(match[1]), SIZES[key], key);
  }
  const total = css.match(/\.docstrap-tasks-static table \{\s*width: (\d+)px;/);
  assert.equal(Number(total?.[1]), plain.reduce((n, k) => n + SIZES[k], 0));
});

// --- grouping ----------------------------------------------------------------

test('by project: projects alphabetically, none last, each with its units', () => {
  assert.deepEqual(groups(build('project')), [
    [
      'alpha',
      3,
      [
        ['apps/players', 2, ['d-1', 'd-3']],
        ['', 1, ['d-2']],
      ],
    ],
    ['firstmate', 1, [['bin', 1, ['f-1']]]],
    ['sample-platform', 1, [['packages/docstrap', 1, ['p-1']]]],
    ['none', 1, [['', 1, ['n-1']]]],
  ]);
});

test('by state: the vocabulary order, then values outside it, and no empty group', () => {
  assert.deepEqual(
    groups(build('state')).map((g: any) => g[0]),
    ['queued', 'held', 'blocked', 'in_flight', 'mystery']
  );
});

test('by stuck: the vocabulary order', () => {
  assert.deepEqual(
    groups(build('stuck')).map((g: any) => [g[0], g[1]]),
    [
      ['ready', 3],
      ['captain', 2],
      ['blocked', 1],
    ]
  );
});

test('sorting orders the rows inside each group and leaves the groups in place', () => {
  const table = build('project');
  table.setSorting([{ id: 'id', desc: true }]);
  const drawn = table.getRowModel().rows.map((r: any) => (r.getIsGrouped() ? `[${r.depth}]` : r.id));
  assert.deepEqual(drawn, [
    '[0]', '[1]', 'd-3', 'd-1', '[1]', 'd-2',
    '[0]', '[1]', 'f-1',
    '[0]', '[1]', 'p-1',
    '[0]', '[1]', 'n-1',
  ]);
});

test('a group collapses to its heading', () => {
  const table = build('state');
  const queued = table.getRowModel().rows[0];
  queued.toggleExpanded();
  const drawn = table.getRowModel().rows.map((r: any) => r.id);
  assert.ok(!drawn.includes('d-1') && !drawn.includes('d-2'));
  assert.ok(drawn.includes('p-1'), 'the other groups stay open');
});

test('a group\'s count is its records under the filters', () => {
  const table = build('project');
  table.getColumn('stuck').setFilterValue(['captain']);
  assert.deepEqual(groups(table).map((g: any) => [g[0], g[1]]), [
    ['alpha', 1],
    ['sample-platform', 1],
  ]);
});

test('a group reached inside a drill-down keeps the drill-down in its steps', () => {
  const drill: Step[] = [{ dim: 'state', value: 'queued' }];
  const alpha = rows.find((r) => r.task.id === 'd-1')!.task;
  assert.deepEqual(groups(build('project', drill)).map((g: any) => g[0]), ['alpha']);
  assert.deepEqual(groupSteps(drill, 'project', 0, alpha), [
    { dim: 'state', value: 'queued' },
    { dim: 'project', value: 'alpha' },
  ]);
  assert.deepEqual(groupSteps([], 'project', 1, alpha), [
    { dim: 'project', value: 'alpha' },
    { dim: 'unit', value: 'apps/players' },
  ]);
  assert.deepEqual(groupSteps([], 'stuck', 0, alpha), [{ dim: 'stuck', value: 'ready' }]);
});

// --- drilling down -----------------------------------------------------------

test('narrowing keeps the rows matching every step', () => {
  assert.deepEqual(ids(narrow(rows, [])), ids(rows));
  assert.deepEqual(ids(narrow(rows, [{ dim: 'project', value: 'alpha' }])), ['d-1', 'd-2', 'd-3']);
  assert.deepEqual(
    ids(
      narrow(rows, [
        { dim: 'project', value: 'alpha' },
        { dim: 'unit', value: '' },
      ])
    ),
    ['d-2'],
    'the project-wide unit is a place to drill into too'
  );
  assert.deepEqual(
    ids(
      narrow(rows, [
        { dim: 'project', value: 'alpha' },
        { dim: 'stuck', value: 'captain' },
      ])
    ),
    ['d-3']
  );
});

test('a drill-down step replaces one on the same dimension', () => {
  const drill = drillInto([], [{ dim: 'state', value: 'held' }]);
  assert.deepEqual(drillInto(drill, [{ dim: 'state', value: 'queued' }]), [
    { dim: 'state', value: 'queued' },
  ]);
  assert.deepEqual(drillInto(drill, [{ dim: 'state', value: 'held' }]), drill, 'the same step twice is one step');
});

test('another project drops the unit under the old one', () => {
  const drill = drillInto([], [
    { dim: 'project', value: 'alpha' },
    { dim: 'unit', value: 'apps/players' },
  ]);
  assert.deepEqual(drillInto(drill, [{ dim: 'project', value: 'firstmate' }]), [
    { dim: 'project', value: 'firstmate' },
  ]);
});

test('a unit with no project is not a place the list can be', () => {
  assert.deepEqual(drillInto([], [{ dim: 'unit', value: 'bin' }]), []);
});

test('a breadcrumb goes back to the drill-down as it was at that step', () => {
  const drill = drillInto([], [
    { dim: 'project', value: 'alpha' },
    { dim: 'unit', value: 'apps/players' },
  ]);
  assert.deepEqual(
    crumbs(drill).map((c) => c.drill.length),
    [1, 2]
  );
  assert.deepEqual(crumbs(drill)[0].drill, [{ dim: 'project', value: 'alpha' }]);
  assert.deepEqual(crumbs([]), []);
});

// --- the address -------------------------------------------------------------

test('the view round-trips through the address and leaves doc-url alone', () => {
  const view = {
    group: 'stuck' as const,
    drill: [
      { dim: 'project' as const, value: 'alpha' },
      { dim: 'unit' as const, value: 'apps/players:v2' },
    ],
  };
  const params = writeView(new URLSearchParams('doc-url=triage%2Findex.html&questions=x'), view);
  assert.equal(params.get('doc-url'), 'triage/index.html');
  assert.equal(params.get('questions'), 'x');
  assert.equal(params.get(GROUP_PARAM), 'stuck');
  assert.deepEqual(params.getAll(DRILL_PARAM), ['project:alpha', 'unit:apps/players:v2']);
  assert.deepEqual(readView(new URLSearchParams(params.toString())), view);
});

test('the default view writes nothing of its own into the address', () => {
  const params = writeView(
    new URLSearchParams(`doc-url=a.html&${GROUP_PARAM}=state&${DRILL_PARAM}=state:held`),
    { group: 'project', drill: [] }
  );
  assert.equal(params.toString(), 'doc-url=a.html');
});

test('an address with nothing of this tool in it is the whole list by project', () => {
  assert.deepEqual(readView(new URLSearchParams('doc-url=a.html')), { group: 'project', drill: [] });
});

test('what the address holds that the tool cannot read is left at rest', () => {
  const params = new URLSearchParams();
  params.set(GROUP_PARAM, 'colour');
  params.append(DRILL_PARAM, 'colour:red');
  params.append(DRILL_PARAM, 'no-colon');
  params.append(DRILL_PARAM, 'unit:bin');
  params.append(DRILL_PARAM, 'state:held');
  assert.deepEqual(readView(params), { group: 'project', drill: [{ dim: 'state', value: 'held' }] });
});

test('a drill-down read from the address narrows the list it names', () => {
  const view = readView(new URLSearchParams(`${DRILL_PARAM}=project:alpha&${DRILL_PARAM}=unit:apps/players`));
  const table = build(view.group, view.drill);
  table.setSorting([{ id: 'id', desc: true }]);
  assert.deepEqual(
    table.getRowModel().rows.filter((r: any) => !r.getIsGrouped()).map((r: any) => r.id),
    ['d-3', 'd-1']
  );
});
