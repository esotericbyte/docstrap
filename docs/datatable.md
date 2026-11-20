# Data tables

The `docstrap-datatable` directive puts a table on a page from a JSON file beside it. Inside the
viewer the reader can sort it by any sortable column, narrow it with a multi-select per enum or
symbol column, a search box over the text columns and a range per date column, and see how many rows
are left. A link cell goes to another page, so a summary table can lead to a detail page per row.

The tool is `docstrap.tools.datatable`. It is generic: nothing in it knows what the rows are.

## 1 The directive

````markdown
```{docstrap-datatable} census.json
```
````

The one argument is the table file's path, relative to the page — or to the source root when it
starts with `/`, as every Sphinx path argument is. There are no options and no body. The build reads
the file when the page is built and again whenever the file changes.

## 2 The table file

One JSON object with two keys, `columns` and `rows`, and no others.

```json
{
  "columns": [
    {"key": "id", "label": "Task", "type": "link", "href": "page", "filterable": true},
    {"key": "title", "label": "Title", "type": "text", "filterable": true},
    {"key": "filed", "label": "Filed", "type": "date", "filterable": true},
    {"key": "state", "label": "State", "type": "enum", "filterable": true,
     "values": ["queued", "held", "blocked", "in_flight"]},
    {"key": "work", "label": "Work", "type": "symbol", "filterable": true,
     "values": ["code", "docs"], "symbols": {"code": "🔨", "docs": "📝"}}
  ],
  "rows": [
    {"id": "fm-12", "page": "tasks/fm-12", "title": "Sortable tables", "filed": "2026-10-13",
     "state": "queued", "work": "code"}
  ]
}
```

### 2.1 Columns

Columns show in the order listed. Each is an object with these keys, and a key not listed here is
an error rather than ignored, so a misspelt option fails the build instead of quietly doing nothing.

1. `key` — required, unique. The row field the column shows.
2. `label` — the header. Defaults to the key.
3. `type` — required. One of `text`, `date`, `enum`, `symbol`, `link`; §2.2.
4. `sortable` — `true` by default.
5. `filterable` — `false` by default. What filtering means depends on the type; §2.2.
6. `values` — enum and symbol only, optional. The order values sort in and are offered in; values
   not listed come after them, alphabetically.
7. `symbols` — symbol only, required. Maps each value to what is shown for it. A value with no
   entry is shown as itself, and a value mapped to `""` shows as a blank cell.
8. `href` — link only, optional. The row field holding the link target, when the cell's own value is
   the text and not the target.

### 2.2 Column types

A `text` column sorts naturally, so `fm-2` comes before `fm-10`, and numbers sort as numbers. When
filterable it takes part in the search box, which keeps a row only when every word typed appears in
one of the searched columns, ignoring case.

A `date` column holds `YYYY-MM-DD`, optionally followed by a time, and sorts chronologically. When
filterable it gets a from–to range, inclusive at both ends and open at an empty one; a row with no
date is kept only while the range is empty.

An `enum` column sorts by its declared `values`. When filterable it gets a multi-select listing every
value present, each with the number of rows it would give with the other filters as they are. A row
is kept when its value is one of those chosen; nothing chosen means no filter.

A `symbol` column is an enum shown through its `symbols` map. The cell carries the value as its
tooltip and the multi-select shows symbol and value side by side.

A `link` column shows its value as a link. It sorts and searches as text.

### 2.3 Rows

Rows show in the file's order until the reader sorts, and sorting back off restores it — so the file's
order is the default order, and a generator chooses it.

A cell is a string, a number, a boolean, `null`, or a list of those. A missing field is `null`. An
empty cell sorts last in both directions. A list shows its items joined with commas — space-separated
for a symbol column — and a multi-select keeps a row when any item is chosen. Fields no column names
are allowed and not shipped to the page; that is where a link column's `href` field lives.

### 2.4 Link targets

A target naming a document is written relative to the page, with or without its suffix and with an
optional `#anchor`: `tasks/fm-12`, `tasks/fm-12.md#status`. The build turns it into that document's
built URL, so the table file never has to know how the site spells a page. A target naming no
document in the build is a build warning, and its cell shows unlinked.

A target with a scheme (`https:`, `mailto:`), or starting with `/` or `#`, is used as written.

## 3 What the page carries

The build renders the table twice inside one wrapper: as a plain HTML table, and as the same data in
a `<script type="application/json">`. The plain table is the document. It is what a page opened on
its own shows, since such a page runs no tool (`tools-and-instruments.md` §3.2), and it is what
prints. Inside the viewer the tool sets it aside and draws the sortable table from the data; hiding
the tool from the launcher puts the plain table back.

Nothing is fetched and the tool owns no route. The controls above the table carry `.docstrap-chrome`,
so print shows the table without them.

A malformed table file fails the build with the JSON path of what is wrong —
`columns[3].type: 'number' is not one of text, date, enum, symbol, link`. A table that half-rendered
a file it could not read would be a table that is wrong without saying so.

## 4 A census-shaped example

`tests/fixtures/datatable/census/` is a summary page, its table file and a detail page per row one
directory down, in the shape of firstmate's task census: one row per open task, the task id linking
to its detail page, and the columns `title`, `project`, `unit`, `filed`, `last_activity`, `state`,
`work`, `stuck`, `alignment`, `done_elsewhere`, `duplicates` and `recommendation`.
`tests/test_datatable.py` builds it and checks every task links to a page that exists.

## 5 Where the rules live

The table file is read and checked by `tools/datatable/spec.py`, and the directive in
`tools/datatable/views.py` renders it. Sorting and filtering are TanStack Table's
(`@tanstack/svelte-table`), headless, so the tool draws its own markup with scoped styles:
`tools/datatable/ui/table.ts` is what a column and a cell are and how two cells compare, and
`tools/datatable/ui/grid.ts` turns each declared column into a TanStack column and the search into
TanStack's global filter. The task tool builds on the same two modules and the same
`FilterBar.svelte`. `tests/datatable/table.test.ts` drives a real TanStack table built from them under
Node — `npm test` runs it, and so does `pytest` through `tests/test_datatable.py`. How a cell reads as text is written twice,
once in Python for the plain table and once in TypeScript for the drawn one, and both are held to
`tests/fixtures/datatable/cell-text.json`.
