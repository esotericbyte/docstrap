// docstrap datatable tool — entry point.
//
// The `docstrap-datatable` directive renders each table twice inside one
// wrapper: as a plain HTML table, which is the document and reads with no
// script at all, and as JSON in a `<script type="application/json">`.
// When the tool shows, this reads the JSON, sets the plain table aside and
// mounts the sortable, filterable DataTable in its place. Hiding the tool
// puts the plain table back, so with the tool hidden the page is the page
// its author built.
//
// Nothing is fetched and no route is used: the rows are already in the
// page. That is why the declaration owns no collection.
import { mount, unmount } from 'svelte';

import { requireDocstrap } from '../../../sphinx/ui/docstrap';
import DataTable from './DataTable.svelte';
import type { TableData } from './table';

const TOOL = 'datatable';
const WRAPPER = '.docstrap-datatable';
const DATA = ':scope > .docstrap-datatable-data';
const PLAIN = ':scope > .docstrap-datatable-static';

const d = requireDocstrap(TOOL);

if (d) {
  interface Mounted {
    app: ReturnType<typeof mount>;
    holder: HTMLElement;
    plain: HTMLElement;
  }
  const mounted = new Map<Element, Mounted>();

  function show(): void {
    document.querySelectorAll(WRAPPER).forEach((wrapper) => {
      if (mounted.has(wrapper)) return;
      const script = wrapper.querySelector(DATA);
      const plain = wrapper.querySelector<HTMLElement>(PLAIN);
      if (!script || !plain) return;
      let data: TableData;
      try {
        data = JSON.parse(script.textContent || '');
      } catch (err) {
        // The build wrote this JSON itself, so this is a defect and not a
        // reader's problem: the plain table stays, and the console says why.
        console.warn('docstrap-datatable: unreadable table data', err);
        return;
      }
      const holder = document.createElement('div');
      wrapper.appendChild(holder);
      // Inline rather than `hidden`: the theme gives `.table-wrapper` a
      // display of its own, which would outrank the attribute.
      plain.style.display = 'none';
      mounted.set(wrapper, { app: mount(DataTable, { target: holder, props: { data } }), holder, plain });
    });
  }

  function hide(): void {
    for (const { app, holder, plain } of mounted.values()) {
      unmount(app);
      holder.remove();
      plain.style.display = '';
    }
    mounted.clear();
  }

  d.tools.register(TOOL, { show, hide });
}
