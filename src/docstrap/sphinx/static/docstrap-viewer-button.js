// docstrap-viewer-button.js — a published page's way into the viewer.
//
// The one docstrap script a page runs on its own. It depends on nothing
// and loads nothing until it knows where the page is, and the answer is
// the page's state, written onto the root element for the stylesheet:
//
//   data-docstrap-view="page"    Opened directly. The page draws one
//                                button, which replaces it with the
//                                viewer showing this same page. No tool
//                                runs, so no Svelte runtime is fetched.
//   data-docstrap-view="framed"  Inside a frame — the viewer's middle
//                                region, or a reference panel inside
//                                the viewer. No button, and the tools
//                                this page carries are turned on.
//
// The tools are on the page already, as <script> tags of a type no
// browser runs (`tool_support.DEFERRED_SCRIPT_TYPE`), so Sphinx wrote
// their URLs and checksums like any other asset's. Turning them on is
// replacing each with a real script, in page order. `docstrap-common.js`
// is the first of them and every tool waits on its `onReady`, which has
// passed by then and so runs at once.
//
// The address the button follows is composed at build time, beside the
// manifest the viewer reads (`viewer.manifest.open_in_viewer_href`), and
// arrives in a meta tag. A page with no viewer above it has no tag and
// gets no button. Names shared with Python are held to one spelling by
// tests/test_viewer.py.
(function () {
  'use strict';

  var STATE_ATTRIBUTE = 'data-docstrap-view';
  var META_NAME = 'docstrap-open-in-viewer';
  var DEFERRED_TYPE = 'text/x-docstrap-deferred';
  var BUTTON_CLASS = 'docstrap-open-in-viewer';
  var LABEL = 'Open in the viewer';

  // Lucide's `library` — the mark the viewer's own header carries.
  var ICON =
    '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" ' +
    'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" ' +
    'stroke-linejoin="round" aria-hidden="true">' +
    '<path d="m16 6 4 14"/><path d="M12 6v14"/><path d="M8 8v12"/><path d="M4 4v16"/></svg>';

  var framed = window.self !== window.top;
  document.documentElement.setAttribute(STATE_ATTRIBUTE, framed ? 'framed' : 'page');

  function onReady(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }

  function runDeferredScripts() {
    var held = document.querySelectorAll('script[type="' + DEFERRED_TYPE + '"]');
    for (var i = 0; i < held.length; i++) {
      var script = document.createElement('script');
      script.src = held[i].src;
      // Inserted scripts are async by default; these must run in order.
      script.async = false;
      held[i].parentNode.replaceChild(script, held[i]);
    }
  }

  function drawButton() {
    var meta = document.querySelector('meta[name="' + META_NAME + '"]');
    var href = meta && meta.getAttribute('content');
    if (!href) return;
    var link = document.createElement('a');
    link.className = BUTTON_CLASS + ' docstrap-chrome';
    link.href = href;
    link.title = LABEL;
    link.setAttribute('aria-label', LABEL);
    link.innerHTML = ICON;
    document.body.appendChild(link);
  }

  onReady(framed ? runDeferredScripts : drawButton);
})();
