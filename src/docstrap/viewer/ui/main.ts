// The viewer shell's entry.
//
// `docstrap-common.js` is imported for its side effect and is not
// changed by being here: it puts `window.docstrap` on this page exactly
// as it does on every documentation page, so the qapanels components the
// shell hosts get the same `api` and `silenceOfflineError` they always
// have. On this page it finds no meta tags and no offers, which is
// correct — the shell is not a document. What the panels are pointed at
// comes from the manifest instead (`questions.ts`).
import '../../sphinx/static/docstrap-common.js';
import { mount } from 'svelte';

import App from './App.svelte';
import './app.css';

const target = document.getElementById('docstrap-viewer');
if (target) mount(App, { target });
