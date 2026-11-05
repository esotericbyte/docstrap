// docstrap task tool — entry point.
//
// The `docstrap-tasks` directive renders the tasks twice inside one
// wrapper: as a plain HTML table grouped by project, which is the document
// and reads with no script, and as JSON in a `<script type="application/json">`.
// When the tool shows, this reads the JSON, sets the plain table aside and
// mounts the task list in its place. Hiding the tool puts the plain table
// back.
//
// The list itself is never fetched; it is in the page. What is fetched is
// the decisions recorded on this page, from the tool's own route, because
// they change while the page is open.
import { mount, unmount } from 'svelte';

import { requireDocstrap } from '../../../sphinx/ui/docstrap';
import TaskList from './TaskList.svelte';
// The column layout both tables share, the plain one included: it has to
// apply where this script never runs. Emitted into the tool's stylesheet.
import './tasks.css';
import type { TaskData } from './tasks.ts';

const TOOL = 'tasks';
const WRAPPER = '.docstrap-tasks';
const DATA = ':scope > .docstrap-tasks-data';
const PLAIN = ':scope > .docstrap-tasks-static';

const d = requireDocstrap(TOOL);

/** The window whose address holds the view: the viewer's, when this page
 *  is framed inside it, so a drill-down is in the address a reader copies.
 *  The page's own when it is not, or when the frame cannot reach it. */
function addressWindow(): Window {
  try {
    if (window.top && window.top !== window && window.top.location.href) return window.top;
  } catch {
    // Another origin's frame: its address is not ours to write.
  }
  return window;
}

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
      let data: TaskData;
      try {
        data = JSON.parse(script.textContent || '');
      } catch (err) {
        // The build wrote this JSON itself, so this is a defect: the plain
        // table stays, and the console says why.
        console.warn('docstrap-tasks: unreadable task data', err);
        return;
      }
      const holder = document.createElement('div');
      wrapper.appendChild(holder);
      // Inline rather than `hidden`: the theme gives `.table-wrapper` a
      // display of its own, which would outrank the attribute.
      plain.style.display = 'none';
      const app = mount(TaskList, {
        target: holder,
        props: { data, docstrap: d!, route: d!.tools.route(TOOL), address: addressWindow() },
      });
      mounted.set(wrapper, { app, holder, plain });
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
