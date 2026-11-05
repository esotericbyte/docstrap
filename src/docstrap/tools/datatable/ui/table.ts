// table.ts — what a data table's columns and cells are, with no DOM and
// no Svelte.
//
// A column's declaration, a cell's text and distinct values, and how two
// cells of one column compare. Sorting and filtering are TanStack Table's,
// given these rules by `grid.ts`. It imports nothing, so it runs under
// Node directly (`npm test`), and nothing in it can depend on a page.
//
// The data is what the `docstrap-datatable` directive embeds in the page
// (`views.render`): the columns as the table file declared them, and per
// row the cell values plus the URL each link cell goes to, already
// resolved by the build.

export type ColumnType = 'text' | 'date' | 'enum' | 'symbol' | 'link';

export type Scalar = string | number | boolean | null;
export type Cell = Scalar | Scalar[];

export interface Column {
  key: string;
  label: string;
  type: ColumnType;
  sortable: boolean;
  filterable: boolean;
  /** Enum and symbol columns: the order values sort and are offered in. */
  values?: string[];
  /** Symbol columns: what each value is shown as. */
  symbols?: Record<string, string>;
}

export interface Row {
  cells: Record<string, Cell>;
  /** Link column key → the URL that cell goes to. */
  links: Record<string, string>;
}

export interface TableData {
  columns: Column[];
  rows: Row[];
}

export interface DateRange {
  /** `YYYY-MM-DD`, inclusive, or empty for open. */
  from: string;
  to: string;
}

/** The option standing for a cell with no value. */
export const NONE = '';

const collator = new Intl.Collator(undefined, { numeric: true, sensitivity: 'base' });

function scalarText(value: Scalar): string {
  if (value === null) return '';
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  return String(value);
}

/** A cell as text, through a symbol column's map when given one.
 *
 * `views.display` in Python is the same rule — the build draws the plain
 * table with it — and a test holds the two to the same outputs. */
export function cellText(value: Cell | undefined, symbols?: Record<string, string>): string {
  if (value === undefined || value === null) return '';
  if (Array.isArray(value)) {
    return value.map((v) => cellText(v, symbols)).join(symbols ? ' ' : ', ');
  }
  const text = scalarText(value);
  return symbols ? (symbols[text] ?? text) : text;
}

/** The distinct values a cell holds, as filter options see them. */
export function cellValues(value: Cell | undefined): string[] {
  if (value === undefined || value === null) return [NONE];
  if (Array.isArray(value)) {
    const values = value.filter((v) => v !== null).map(scalarText);
    return values.length ? [...new Set(values)] : [NONE];
  }
  const text = scalarText(value);
  return [text];
}

/** Where a value comes in its column's declared order; undeclared last. */
export function rank(column: Column, value: string): number {
  const index = column.values ? column.values.indexOf(value) : -1;
  return index < 0 ? Number.POSITIVE_INFINITY : index;
}

/** Order two non-empty cells of one column, ascending. */
export function compareCells(a: Cell, b: Cell, column: Column): number {
  switch (column.type) {
    case 'date':
      return cellText(a) < cellText(b) ? -1 : cellText(a) > cellText(b) ? 1 : 0;
    case 'enum':
    case 'symbol': {
      const first = (c: Cell) => cellValues(c)[0];
      const ra = rank(column, first(a));
      const rb = rank(column, first(b));
      if (ra !== rb) return ra < rb ? -1 : 1;
      return collator.compare(first(a), first(b));
    }
    default:
      if (typeof a === 'number' && typeof b === 'number') return a - b;
      return collator.compare(cellText(a), cellText(b));
  }
}
