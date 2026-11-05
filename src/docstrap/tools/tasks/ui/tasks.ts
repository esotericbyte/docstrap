// tasks.ts — the task list's columns, grouping, drill-down and address,
// with no DOM and no Svelte.
//
// The components draw; TanStack Table owns the row models — sorting,
// filters, search, facet counts, grouping, collapsing and column sizes —
// through the datatable's `grid.ts`, which turns a docstrap column into a
// TanStack one. What is the task list's own is here: which columns there
// are and how wide, which columns it groups on and in what order the
// groups come, what a drill-down keeps, and how the view is written into
// the address. A task becomes a datatable row (`toRow`). It imports no
// DOM, so `tests/tasks/tasks.test.ts` runs it, and a real TanStack table
// built from it, under Node.
//
// The data is what the `docstrap-tasks` directive embeds in the page
// (`views.render`): the tasks as `tasks.json` holds them, each with the URL
// its page resolved to, and the vocabularies with their symbols.

import { SEARCH, columnDef, searchColumn, type Features } from '../../datatable/ui/grid.ts';
import type { Cell, Column, Row } from '../../datatable/ui/table.ts';
import type { ColumnDef } from '@tanstack/table-core';

export interface Vocab {
  /** The order values sort, group and are offered in. */
  values: string[];
  symbols?: Record<string, string>;
}

export type VocabField =
  | 'state'
  | 'work'
  | 'stuck'
  | 'alignment'
  | 'done_elsewhere'
  | 'lifecycle_stage'
  | 'action';
export type Vocabulary = Record<VocabField, Vocab>;

export interface Recommendation {
  action: string;
  note: string;
  date: string;
  by: string;
}

export interface Task {
  id: string;
  title: string;
  project: string;
  unit: string;
  state: string;
  hold_reason: string;
  blocked_by: string[];
  filed: string;
  last_activity: string;
  work: string;
  stuck: string;
  alignment: string;
  plan: string;
  done_elsewhere: string;
  done_evidence: string;
  /** filed | specified | branch | landed | deployed: how far the task's
   *  own scope has got, and what shows it. */
  lifecycle_stage: string;
  lifecycle_evidence: string;
  /** The anchor of its section on the overlaps page, or empty. */
  tangle: string;
  latest_recommendation: Recommendation | null;
  recommendations: Recommendation[];
  /** The task's page, resolved by the build, or null. */
  link: string | null;
  /** Its own section on the overlaps page, resolved by the build, or
   *  null: in no tangle. Names the task's membership, nothing about the
   *  other tasks in it. */
  tangle_link: string | null;
}

export interface TaskData {
  generated: string;
  vocabulary: Vocabulary;
  tasks: Task[];
}

/** A datatable row that still knows its task. */
export interface TaskRow extends Row {
  task: Task;
}

export type GroupBy = 'project' | 'state' | 'stuck';
/** What a drill-down step narrows on. A unit is only ever inside a project. */
export type Dimension = 'project' | 'unit' | 'state' | 'stuck';

export interface Step {
  dim: Dimension;
  value: string;
}

export interface View {
  group: GroupBy;
  /** The steps taken, outermost first. Empty: the whole list. */
  drill: Step[];
}

const GROUPINGS: GroupBy[] = ['project', 'state', 'stuck'];
const DIMENSIONS: Dimension[] = ['project', 'unit', 'state', 'stuck'];

/** The address parameters this tool owns. Everything else is left alone. */
export const GROUP_PARAM = 'tasks-group';
export const DRILL_PARAM = 'tasks-in';

/** The project the contract writes for a task that belongs to none. */
export const NO_PROJECT = 'none';

const collator = new Intl.Collator(undefined, { numeric: true, sensitivity: 'base' });

// --- rows ----------------------------------------------------------------

/** A task as a datatable row, so the datatable's sort and filter apply. */
export function toRow(task: Task): TaskRow {
  const cells: Record<string, Cell> = {
    id: task.id,
    title: task.title,
    project: task.project,
    unit: task.unit,
    filed: task.filed || null,
    last_activity: task.last_activity || null,
    state: task.state,
    work: task.work,
    stuck: task.stuck,
    alignment: task.alignment,
    done_elsewhere: task.done_elsewhere,
    lifecycle_stage: task.lifecycle_stage,
    recommendation: task.latest_recommendation?.action || null,
    evidence: [task.done_evidence, task.lifecycle_evidence].filter(Boolean).join(' '),
  };
  return { cells, links: task.link ? { id: task.link } : {}, task };
}

/** Every column the list has, in order, as the datatable declares them.
 *
 * Which are filterable is the tool's filter set: the search box covers
 * the filterable text and link columns — the evidence among them, which
 * is never shown — and the facets are the filterable symbol and enum
 * ones. */
export function allColumns(vocabulary: Vocabulary): Column[] {
  const symbol = (key: VocabField, label: string): Column => ({
    key,
    label,
    type: 'symbol',
    sortable: true,
    filterable: true,
    values: vocabulary[key].values,
    symbols: vocabulary[key].symbols ?? {},
  });
  return [
    { key: 'id', label: 'Task', type: 'link', sortable: true, filterable: true },
    { key: 'title', label: 'Title', type: 'text', sortable: true, filterable: true },
    { key: 'project', label: 'Project', type: 'enum', sortable: true, filterable: false },
    { key: 'unit', label: 'Unit', type: 'text', sortable: true, filterable: true },
    { key: 'filed', label: 'Filed', type: 'date', sortable: true, filterable: true },
    { key: 'last_activity', label: 'Last activity', type: 'date', sortable: true, filterable: true },
    {
      key: 'state',
      label: 'State',
      type: 'enum',
      sortable: true,
      filterable: false,
      values: vocabulary.state.values,
    },
    symbol('work', 'Work'),
    symbol('stuck', 'Stuck'),
    symbol('alignment', 'Alignment'),
    symbol('done_elsewhere', 'Done elsewhere'),
    {
      key: 'lifecycle_stage',
      label: 'Stage',
      type: 'enum',
      sortable: true,
      filterable: true,
      values: vocabulary.lifecycle_stage.values,
    },
    {
      key: 'recommendation',
      label: 'Latest recommendation',
      type: 'enum',
      sortable: true,
      filterable: true,
      values: vocabulary.action.values,
    },
    EVIDENCE,
  ];
}

/** The columns the list shows, in order.
 *
 * The project column is shown only when the list is neither grouped by
 * project nor drilled into one, and the unit column only when it is not
 * grouped by project: there the units are the headings the rows sit
 * under, and a column repeating its heading on every row is width spent
 * on nothing. The evidence is never shown. */
export function columns(vocabulary: Vocabulary, group: GroupBy, drill: Step[] = []): Column[] {
  const byProject = group === 'project';
  return allColumns(vocabulary).filter((c) => {
    if (c.key === EVIDENCE.key) return false;
    if (c.key === 'project') return !byProject && !drill.some((s) => s.dim === 'project');
    if (c.key === 'unit') return !byProject;
    return true;
  });
}

/** The column the search box also reads and the list never shows. */
export const EVIDENCE: Column = {
  key: 'evidence',
  label: 'Evidence',
  type: 'text',
  sortable: false,
  filterable: true,
};

/** Each shown column's width, in pixels at the list's type size: fixed,
 *  so no column is wider than what it holds is useful. The task id is
 *  compact and cut short with the whole id on hover; free text wraps
 *  inside its width; symbols, dates and states take what they need.
 *  `ui/tasks.css` gives the plain table the same widths, and a test
 *  holds the two together. */
export const SIZES: Record<string, number> = {
  id: 150,
  title: 300,
  project: 110,
  unit: 190,
  filed: 92,
  last_activity: 92,
  state: 84,
  work: 56,
  stuck: 56,
  alignment: 80,
  done_elsewhere: 80,
  lifecycle_stage: 84,
  recommendation: 150,
};

/** The TanStack columns of the list: every column, the hidden ones too,
 *  because a hidden column still groups and is still searched; and the
 *  search's own column, over the searched ones. */
export function columnDefs(vocabulary: Vocabulary): ColumnDef<Features, TaskRow, any>[] {
  const all = allColumns(vocabulary);
  return [...all.map((c) => columnDef<TaskRow>(c, SIZES[c.key])), searchColumn<TaskRow>(all)];
}

/** The visibility TanStack is given: every column not shown is hidden. */
export function visibility(vocabulary: Vocabulary, shown: Column[]): Record<string, boolean> {
  const keys = new Set(shown.map((c) => c.key));
  const hidden: Record<string, boolean> = {};
  for (const id of [...allColumns(vocabulary).map((c) => c.key), SEARCH]) {
    if (!keys.has(id)) hidden[id] = false;
  }
  return hidden;
}

// --- drilling down ---------------------------------------------------------

function fieldOf(task: Task, dim: Dimension): string {
  return task[dim];
}

/** The rows a drill-down keeps: those matching every step. */
export function narrow<R extends TaskRow>(rows: R[], drill: Step[]): R[] {
  return rows.filter((row) => drill.every((step) => fieldOf(row.task, step.dim) === step.value));
}

/** A drill-down with `steps` taken from `drill`.
 *
 * A step on a dimension already narrowed replaces that step, and a
 * different project drops the unit under the old one. A unit step with
 * no project before it is not a place the list can be, so it is dropped. */
export function drillInto(drill: Step[], steps: Step[]): Step[] {
  let next = drill.slice();
  for (const step of steps) {
    if (!DIMENSIONS.includes(step.dim)) continue;
    const at = next.findIndex((s) => s.dim === step.dim);
    if (at >= 0) {
      if (next[at].value === step.value) continue;
      next[at] = step;
      if (step.dim === 'project') next = next.filter((s) => s.dim !== 'unit');
    } else {
      if (step.dim === 'unit' && !next.some((s) => s.dim === 'project')) continue;
      next.push(step);
    }
  }
  return next;
}

/** The drill-down each breadcrumb goes back to, outermost first. */
export function crumbs(drill: Step[]): { step: Step; drill: Step[] }[] {
  return drill.map((step, i) => ({ step, drill: drill.slice(0, i + 1) }));
}

// --- grouping ----------------------------------------------------------------

/** The columns TanStack groups on: by project, the project and under it
 *  the unit; by status, the state or the stuck reason. */
export function groupingFor(group: GroupBy): string[] {
  return group === 'project' ? ['project', 'unit'] : [group];
}

function vocabOrder(values: string[] | undefined): (a: string, b: string) => number {
  return (a, b) => {
    if (a === '' || b === '') return a === b ? 0 : a === '' ? 1 : -1;
    const ra = values ? values.indexOf(a) : -1;
    const rb = values ? values.indexOf(b) : -1;
    const ka = ra < 0 ? Number.POSITIVE_INFINITY : ra;
    const kb = rb < 0 ? Number.POSITIVE_INFINITY : rb;
    if (ka !== kb) return ka < kb ? -1 : 1;
    return collator.compare(a, b);
  };
}

function projectOrder(a: string, b: string): number {
  const la = a === '' || a === NO_PROJECT;
  const lb = b === '' || b === NO_PROJECT;
  if (la !== lb) return la ? 1 : -1;
  return collator.compare(a, b);
}

/** The rows in the order their groups are shown; rows keep their given
 *  order inside a group.
 *
 * TanStack groups in the order a group first appears, and its sort keeps
 * that order among group rows that compare equal, so this is what orders
 * the groups. By project: projects alphabetically with `none` last, each
 * holding its units alphabetically with the project-wide (empty) unit
 * last. By state or stuck: the vocabulary's order, values outside it
 * after, alphabetically. */
export function inGroupOrder<R extends TaskRow>(rows: R[], group: GroupBy, vocabulary: Vocabulary): R[] {
  const keys: ((t: Task) => string)[] =
    group === 'project' ? [(t) => t.project, (t) => t.unit] : [(t) => t[group]];
  const orders =
    group === 'project' ? [projectOrder, vocabOrder(undefined)] : [vocabOrder(vocabulary[group]?.values)];
  return rows
    .map((row, index) => ({ row, index }))
    .sort((x, y) => {
      for (let i = 0; i < keys.length; i++) {
        const c = orders[i](keys[i](x.row.task), keys[i](y.row.task));
        if (c) return c;
      }
      return x.index - y.index;
    })
    .map(({ row }) => row);
}

/** The drill-down that narrows the list to one group: where the list
 *  already is, plus the step into the group `depth` levels down, read off
 *  any task in it. Following a group keeps the drill-down taken. */
export function groupSteps(drill: Step[], group: GroupBy, depth: number, task: Task): Step[] {
  const steps: Step[] =
    group === 'project'
      ? [
          { dim: 'project', value: task.project },
          { dim: 'unit', value: task.unit },
        ].slice(0, depth + 1) as Step[]
      : [{ dim: group, value: task[group] }];
  return drillInto(drill, steps);
}

// --- the address -------------------------------------------------------------

/** The view an address names. Anything it cannot read is left at rest. */
export function readView(params: URLSearchParams): View {
  const asked = params.get(GROUP_PARAM) as GroupBy | null;
  const group = asked && GROUPINGS.includes(asked) ? asked : 'project';
  const steps: Step[] = [];
  for (const raw of params.getAll(DRILL_PARAM)) {
    const at = raw.indexOf(':');
    if (at < 0) continue;
    const dim = raw.slice(0, at) as Dimension;
    if (!DIMENSIONS.includes(dim)) continue;
    steps.push({ dim, value: raw.slice(at + 1) });
  }
  return { group, drill: drillInto([], steps) };
}

/** `params` with this view written in and every other parameter kept.
 *
 * The default grouping writes nothing, so an address with no drill-down
 * and no grouping chosen carries no parameter of this tool's at all. */
export function writeView(params: URLSearchParams, view: View): URLSearchParams {
  const next = new URLSearchParams(params);
  next.delete(GROUP_PARAM);
  next.delete(DRILL_PARAM);
  if (view.group !== 'project') next.set(GROUP_PARAM, view.group);
  for (const step of view.drill) next.append(DRILL_PARAM, `${step.dim}:${step.value}`);
  return next;
}
