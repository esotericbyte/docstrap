// docstrap-common.js — shared client services for docstrap tools.
//
// Loaded first (registered by tool_support.add_common_asset). Exposes a
// small global object `window.docstrap` with fetch helpers, per-page
// metadata read from the injected <meta> tags, and — the part tools
// attach to — `window.docstrap.tools`, the visibility API.
//
// EXTENSION POINTS defined here. These are the whole client-side
// surface a tool may use.
//
//   docstrap.tools.register(id, {show, hide})
//       A tool declares its two visibility handlers and nothing else.
//       Called at script-evaluation time, not on ready: the launcher
//       decides when to call show().
//   docstrap.tools.route(id)
//       The concrete URL of that tool's API on this page, resolved from
//       its declaration at build time. A tool never assembles a path.
//   docstrap.tools.altRoute(id)
//       The same for a tool that declared a SECOND scope, or null. The
//       qapanels instrument is the one that has one: its collection read
//       narrowed to this document, beside the project-wide read. Choosing
//       a scope is choosing between two resolved URLs, not editing one.
//   docstrap.tools.isVisible(id) / setVisible(id, on) / hideAll()
//       The visibility state itself. The launcher is the UI over this;
//       it holds no state of its own, so a second control (a keyboard
//       shortcut, a future three-panel mode) can drive the same state
//       without either one becoming the owner.
//   docstrap.tools.onChange(fn)
//       Notification when visibility changes, for anything rendering it.
//   docstrap.api / onReady / silenceOfflineError
//       Shared services every tool needs from the page.
//
// Nothing here knows the id of any particular tool.
(function () {
  'use strict';

  function getMeta(name) {
    var el = document.querySelector('meta[name="' + name + '"]');
    return el ? el.getAttribute('content') : null;
  }

  var ctx = {
    docId: getMeta('docstrap-doc-id'),
    project: getMeta('docstrap-project'),
    docSlug: getMeta('docstrap-doc-slug'),
    sourcePath: getMeta('docstrap-source-path'),
  };

  // Same-origin API base. Tools can override via
  // <meta name="docstrap-api-base"> if the site is proxied.
  var apiBase = getMeta('docstrap-api-base') || '';

  function api(path, options) {
    var url = apiBase + path;
    var opts = options || {};
    opts.headers = opts.headers || {};
    if (opts.body && typeof opts.body !== 'string') {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(opts.body);
    }
    return fetch(url, opts).then(function (response) {
      if (!response.ok) {
        var err = new Error('docstrap API error: ' + response.status);
        err.response = response;
        throw err;
      }
      var ct = response.headers.get('Content-Type') || '';
      return ct.indexOf('application/json') >= 0
        ? response.json()
        : response.text();
    });
  }

  // Silence handler for expected-offline API failures (tools should
  // degrade gracefully when the docstrap server isn't running).
  function silenceOfflineError(err) {
    // Fetch throws TypeError('Failed to fetch') when the server is down.
    if (err && err.name === 'TypeError') return null;
    // 404 on a doc that isn't in metadata: also silent.
    if (err && err.response && err.response.status === 404) return null;
    // Anything else, log for debugging but don't disrupt the page.
    console.warn('docstrap:', err);
    return null;
  }

  function onReady(fn) {
    if (document.readyState !== 'loading') {
      fn();
    } else {
      document.addEventListener('DOMContentLoaded', fn);
    }
  }

  // --- the visibility API ------------------------------------------------

  var OFFERS_ELEMENT_ID = 'docstrap-tool-offers';
  var STORAGE_KEY = 'docstrap:tool-visibility';

  var handlers = {};
  var listeners = [];
  var visible = {};
  var offersCache = null;
  var started = false;

  // The offer list is computed at build time from each tool's
  // declaration and serialised into the page. Read lazily: this script
  // may evaluate before the element it reads.
  function offers() {
    if (offersCache !== null) return offersCache;
    offersCache = [];
    var el = document.getElementById(OFFERS_ELEMENT_ID);
    if (el) {
      try {
        var parsed = JSON.parse(el.textContent || '[]');
        if (Array.isArray(parsed)) offersCache = parsed;
      } catch (e) {
        console.warn('docstrap: unreadable tool offers', e);
      }
    }
    return offersCache;
  }

  function offer(id) {
    var all = offers();
    for (var i = 0; i < all.length; i++) {
      if (all[i].id === id) return all[i];
    }
    return null;
  }

  function route(id) {
    var o = offer(id);
    return (o && o.route) || null;
  }

  function altRoute(id) {
    var o = offer(id);
    return (o && o.altRoute) || null;
  }

  function readStored() {
    try {
      return JSON.parse(window.localStorage.getItem(STORAGE_KEY) || '{}') || {};
    } catch (e) {
      return {};
    }
  }

  function writeStored(state) {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (e) {
      // Private browsing, or storage disabled. Visibility is then
      // per-page-load, which is a fine degradation.
    }
  }

  function isVisible(id) {
    return visible[id] === true;
  }

  function setVisible(id, on) {
    on = !!on;
    if (visible[id] === on) return;
    var o = offer(id);
    if (!o) return; // not offered here — nothing to show
    visible[id] = on;

    if (o.visibilityClass) {
      document.body.classList.toggle(o.visibilityClass, on);
    }
    var h = handlers[id];
    if (h) {
      try {
        (on ? h.show : h.hide)();
      } catch (e) {
        console.warn('docstrap: tool "' + id + '" failed to ' +
          (on ? 'show' : 'hide'), e);
      }
    }

    var stored = readStored();
    stored[id] = on;
    writeStored(stored);
    notify(id, on);
  }

  function hideAll() {
    offers().forEach(function (o) {
      setVisible(o.id, false);
    });
  }

  function onChange(fn) {
    listeners.push(fn);
  }

  function notify(id, on) {
    listeners.forEach(function (fn) {
      try {
        fn(id, on);
      } catch (e) {
        console.warn('docstrap: visibility listener failed', e);
      }
    });
  }

  function register(id, h) {
    handlers[id] = h;
  }

  // Apply each offered tool's remembered state, falling back to what
  // its declaration says. Idempotent; the launcher calls it on ready.
  function start() {
    if (started) return;
    started = true;
    var stored = readStored();
    offers().forEach(function (o) {
      var want =
        Object.prototype.hasOwnProperty.call(stored, o.id)
          ? stored[o.id] === true
          : o.defaultVisible === true;
      // Force the transition: `visible` starts empty, so setVisible
      // only acts when `want` is true. Seed the false case so the body
      // class is definitely off.
      if (!want && o.visibilityClass) {
        document.body.classList.remove(o.visibilityClass);
      }
      visible[o.id] = !want;
      setVisible(o.id, want);
    });
  }

  window.docstrap = {
    ctx: ctx,
    apiBase: apiBase,
    api: api,
    silenceOfflineError: silenceOfflineError,
    onReady: onReady,
    tools: {
      register: register,
      offers: offers,
      offer: offer,
      route: route,
      altRoute: altRoute,
      isVisible: isVisible,
      setVisible: setVisible,
      hideAll: hideAll,
      onChange: onChange,
      start: start,
    },
  };
})();
