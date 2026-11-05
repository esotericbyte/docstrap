// questions.ts — the `DocstrapGlobal` the hosted panels are handed.
//
// `Panels.svelte` reads its project, its document and its two routes off
// the `window.docstrap` of the page it is mounted on. In the shell that
// page is the shell, which is no document, so the panels are handed a
// view of the real object whose context and routes are the PINNED
// document's — taken from the manifest, where Python resolved them with
// the same function the document's own page used. The client still
// assembles no path; choosing a questions document is choosing a
// manifest entry, as choosing a scope in the panels is choosing between
// two resolved URLs. Everything else — `api`, `silenceOfflineError`, the
// visibility API — is the real one, untouched.

import type { DocstrapGlobal, ToolOffer } from '../../sphinx/ui/docstrap';
import type { Pinned } from './types';

export function questionsGlobal(real: DocstrapGlobal, pin: Pinned): DocstrapGlobal {
  const offer = pin.document.questions as ToolOffer;
  const mine = (id: string): ToolOffer | null => (id === offer.id ? offer : null);
  return {
    ...real,
    ctx: {
      docId: null,
      project: pin.project.slug,
      docSlug: pin.document.docname,
      sourcePath: null,
    },
    tools: {
      ...real.tools,
      offers: () => [offer],
      offer: mine,
      route: (id) => mine(id)?.route ?? null,
      altRoute: (id) => mine(id)?.altRoute ?? null,
    },
  };
}
