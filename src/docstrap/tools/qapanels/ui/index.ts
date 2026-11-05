// docstrap qapanels instrument — entry point.
//
// Registers show/hide with the single launcher and nothing else. The
// launcher reads `kind: instrument` off the declaration and gives this a
// launch action rather than a toggle, so it opens when asked and never
// before — `default_visible` is false, and it replaces the view.
//
// That is the seam: a second control driving
// `docstrap.tools` visibility without owning it. This instrument owns no
// visibility state either; closing it asks the launcher to turn it off,
// so the launcher's checkbox, "Hide all", and this panel's own Close
// button all move the same one piece of state.
import { mount, unmount } from 'svelte';

import { requireDocstrap } from '../../../sphinx/ui/docstrap';
import Panels from './Panels.svelte';
import './qapanels.css';

const TOOL = 'qapanels';

const d = requireDocstrap(TOOL);

if (d) {
  // The reference panel loads one of this site's own pages in an iframe,
  // and that page loads this bundle too. Registering no-op handlers
  // inside a frame keeps the mode from opening inside its own reference
  // panel. (The frame's chrome is suppressed separately, in Reference.)
  const framed = window.self !== window.top;

  let root: HTMLElement | null = null;
  let app: ReturnType<typeof mount> | null = null;

  function show(): void {
    if (framed || root) return;
    root = document.createElement('div');
    root.className = 'docstrap-qapanels-root docstrap-chrome';
    document.body.appendChild(root);
    app = mount(Panels, {
      target: root,
      props: { d: d!, onclose: () => d!.tools.setVisible(TOOL, false) },
    });
  }

  function hide(): void {
    if (app) {
      void unmount(app);
      app = null;
    }
    if (root) {
      root.remove();
      root = null;
    }
  }

  d.tools.register(TOOL, { show, hide });
}
