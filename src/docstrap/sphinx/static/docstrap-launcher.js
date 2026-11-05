// docstrap-launcher.js — the single visibility control.
//
// One control owns what is showing. Before this, each widget injected
// its own floating button into the same corner with no arbitration;
// that is the defect being removed.
//
// It renders the offer list the build computed from the declarations —
// it does not decide what is offerable, because that rule reads the
// declarations and belongs where the declarations are. It holds no
// visibility state either: `docstrap.tools` owns that, and this is a UI
// over it. Both of those are deliberate, so that a second control could
// exist without either becoming the owner.
//
// A tool is a checkbox: it works in place, so it toggles. An instrument
// is a button: it replaces or leaves the view, so it launches.
//
// Dismissing the launcher removes it from the page entirely. With every
// tool hidden and the launcher dismissed there is no tool chrome left
// at all — the page reads as a plain document, which is what matters if
// it is ever shared. Alt+T brings it back.
(function () {
  'use strict';
  var d = window.docstrap;
  if (!d) {
    console.warn('docstrap-launcher: common bundle missing');
    return;
  }

  var DISMISSED_KEY = 'docstrap:launcher-dismissed';
  var root = null;
  var panel = null;

  d.onReady(function () {
    // Apply remembered visibility first, so tools are in the right
    // state whether or not the launcher itself is on the page.
    d.tools.start();
    if (!d.tools.offers().length) return; // nothing valid here
    if (!isDismissed()) render();
    document.addEventListener('keydown', function (e) {
      if (e.altKey && !e.ctrlKey && !e.metaKey && (e.key === 't' || e.key === 'T')) {
        e.preventDefault();
        if (root) {
          dismiss();
        } else {
          setDismissed(false);
          render();
          togglePanel(true);
        }
      }
    });
  });

  function isDismissed() {
    try {
      return window.localStorage.getItem(DISMISSED_KEY) === '1';
    } catch (e) {
      return false;
    }
  }

  function setDismissed(on) {
    try {
      if (on) window.localStorage.setItem(DISMISSED_KEY, '1');
      else window.localStorage.removeItem(DISMISSED_KEY);
    } catch (e) {
      // storage unavailable; dismissal is then per-page-load
    }
  }

  function dismiss() {
    setDismissed(true);
    if (root) {
      root.remove();
      root = null;
      panel = null;
    }
  }

  function render() {
    if (root) return;
    root = document.createElement('div');
    root.className = 'docstrap-launcher docstrap-chrome';

    var button = document.createElement('button');
    button.type = 'button';
    button.className = 'docstrap-launcher-button';
    button.setAttribute('aria-expanded', 'false');
    button.title = 'Docstrap tools (Alt+T to dismiss)';
    button.textContent = 'Tools';

    panel = document.createElement('div');
    panel.className = 'docstrap-launcher-panel';
    panel.hidden = true;

    button.addEventListener('click', function () {
      togglePanel(panel.hidden);
    });

    panel.appendChild(buildList());
    panel.appendChild(buildFooter());

    root.appendChild(panel);
    root.appendChild(button);
    document.body.appendChild(root);

    // Keep the button's active look in step with whatever changed the
    // state — this control, or anything else driving docstrap.tools.
    d.tools.onChange(function () {
      syncButton(button);
      syncInputs();
    });
    syncButton(button);
  }

  function togglePanel(open) {
    if (!panel) return;
    panel.hidden = !open;
    var button = root.querySelector('.docstrap-launcher-button');
    if (button) button.setAttribute('aria-expanded', open ? 'true' : 'false');
    if (open) syncInputs();
  }

  function buildList() {
    var list = document.createElement('div');
    list.className = 'docstrap-launcher-list';

    d.tools.offers().forEach(function (o) {
      list.appendChild(
        o.kind === 'instrument' ? buildInstrumentRow(o) : buildToolRow(o)
      );
    });
    return list;
  }

  function buildToolRow(o) {
    var row = document.createElement('label');
    row.className = 'docstrap-launcher-row';
    row.title = o.summary || o.title;

    var input = document.createElement('input');
    input.type = 'checkbox';
    input.className = 'docstrap-launcher-check';
    input.dataset.toolId = o.id;
    input.checked = d.tools.isVisible(o.id);
    input.addEventListener('change', function () {
      d.tools.setVisible(o.id, input.checked);
    });

    var text = document.createElement('span');
    text.textContent = o.title;

    row.appendChild(input);
    row.appendChild(text);
    return row;
  }

  // An instrument leaves the standard view, so it gets an action rather
  // than a toggle. Its handler is registered the same way a tool's is;
  // the launcher calls show() and lets the instrument take the view.
  function buildInstrumentRow(o) {
    var row = document.createElement('div');
    row.className = 'docstrap-launcher-row docstrap-launcher-row-instrument';
    row.title = o.summary || o.title;

    var action = document.createElement('button');
    action.type = 'button';
    action.className = 'docstrap-launcher-launch';
    action.textContent = o.title;
    action.addEventListener('click', function () {
      d.tools.setVisible(o.id, true);
    });

    row.appendChild(action);
    return row;
  }

  function buildFooter() {
    var footer = document.createElement('div');
    footer.className = 'docstrap-launcher-footer';

    var hideAll = document.createElement('button');
    hideAll.type = 'button';
    hideAll.className = 'docstrap-launcher-hide-all';
    hideAll.textContent = 'Hide all';
    hideAll.title = 'Hide every tool; the page reads as a plain document';
    hideAll.addEventListener('click', function () {
      d.tools.hideAll();
      syncInputs();
    });

    var dismissBtn = document.createElement('button');
    dismissBtn.type = 'button';
    dismissBtn.className = 'docstrap-launcher-dismiss';
    dismissBtn.textContent = 'Dismiss';
    dismissBtn.title = 'Remove the launcher from the page (Alt+T to bring back)';
    dismissBtn.addEventListener('click', function () {
      d.tools.hideAll();
      dismiss();
    });

    footer.appendChild(hideAll);
    footer.appendChild(dismissBtn);
    return footer;
  }

  function syncInputs() {
    if (!panel) return;
    panel
      .querySelectorAll('.docstrap-launcher-check')
      .forEach(function (input) {
        input.checked = d.tools.isVisible(input.dataset.toolId);
      });
  }

  function syncButton(button) {
    var anyOn = d.tools.offers().some(function (o) {
      return d.tools.isVisible(o.id);
    });
    button.classList.toggle('docstrap-launcher-button-active', anyOn);
  }
})();
