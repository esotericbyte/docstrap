// docstrap status tool — entry point.
//
// Fetches GET /api/documents/<id>/state and mounts the badge before the
// first <h1>. Silently no-ops if no doc-id meta tag is present or the
// docstrap server isn't reachable.
//
// It injects no affordance of its own. It registers show/hide with the
// single launcher and does nothing to the page until told to show. Its
// declaration says default_visible, so on an untouched page the badge
// still appears on load exactly as it did before.
import { mount, unmount } from 'svelte';

import { requireDocstrap } from '../../../sphinx/ui/docstrap';
import Badge from './Badge.svelte';

const TOOL = 'status';

interface DocumentState {
  id: string;
  current_status?: string;
}

const d = requireDocstrap(TOOL);

if (d) {
  let badge: ReturnType<typeof mount> | null = null;

  function show(): void {
    const docId = d!.ctx.docId;
    if (!docId) {
      // No metadata for this page — nothing to badge. Silent by design.
      return;
    }
    d!
      .api<DocumentState>(`/api/documents/${encodeURIComponent(docId)}/state`)
      .then(renderBadge)
      .catch(d!.silenceOfflineError);
  }

  function hide(): void {
    if (badge) {
      unmount(badge);
      badge = null;
    }
  }

  function renderBadge(state: DocumentState | null): void {
    if (!state || !state.current_status) return;
    // The reader may have hidden the tool while the fetch was in
    // flight; don't draw chrome for a tool that is no longer showing.
    if (!d!.tools.isVisible(TOOL)) return;
    if (badge) return;

    const h1 = document.querySelector('h1');
    if (!h1) return;

    // Anchored on the h1's first child so the badge lands before the
    // title text, which is where it has always been.
    badge = mount(Badge, {
      target: h1,
      anchor: h1.firstChild ?? undefined,
      props: { status: state.current_status, docId: state.id },
    });
  }

  d.tools.register(TOOL, { show, hide });
}
