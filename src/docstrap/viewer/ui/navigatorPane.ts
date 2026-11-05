// navigatorPane.ts — the left drawer's width and open state, with no DOM
// and no Svelte.
//
// The resizing and collapsing are Zag's splitter, the state machine
// Skeleton's own components are built on; Skeleton ships no splitter
// component, so the shell drives the machine directly. What is the
// shell's own is here: how wide the drawer starts and may go, what is
// remembered between visits, and what the drawer's tab does. It imports
// no DOM, so `tests/viewer/navigatorPane.test.ts` runs it under Node.
import type { PanelData, PanelSize } from '@zag-js/splitter';

/** The drawer's panel and the panel holding everything to its right. */
export const NAV_PANEL = 'navigator';
export const REST_PANEL = 'rest';
/** The one resize trigger between them. */
export const TRIGGER = `${NAV_PANEL}:${REST_PANEL}` as const;

/** Wide enough for a nested document path without truncating most rows. */
export const DEFAULT_WIDTH = '26rem';
export const MIN_WIDTH = '14rem';
export const MAX_WIDTH = '60%';

/** The per-viewer remembered width, in this browser only. */
export const STORAGE_KEY = 'docstrap.viewer.navigatorWidth';

export const PANELS: PanelData[] = [
  {
    id: NAV_PANEL,
    minSize: MIN_WIDTH,
    maxSize: MAX_WIDTH,
    collapsible: true,
    collapsedSize: 0,
    // The window resizing changes the document's width, not the drawer's.
    resizeBehavior: 'preserve-pixel-size',
  },
  { id: REST_PANEL },
];

type Reader = Pick<Storage, 'getItem'>;
type Writer = Pick<Storage, 'setItem'>;

/** The page's `localStorage`, or null where reading it throws. */
export function viewerStorage(): Storage | null {
  try {
    return globalThis.localStorage ?? null;
  } catch {
    return null;
  }
}

/** The width the drawer opens at: the remembered one, else the default. */
export function readWidth(storage: Reader | null): PanelSize {
  let stored: string | null = null;
  try {
    stored = storage?.getItem(STORAGE_KEY) ?? null;
  } catch {
    return DEFAULT_WIDTH;
  }
  const px = stored === null ? NaN : Number(stored);
  return Number.isFinite(px) && px > 0 ? `${Math.round(px)}px` : DEFAULT_WIDTH;
}

/** Remember the drawer's width after a resize, in pixels so a later
 *  window of another size opens it at the same width. A collapsed
 *  drawer is not a width and is never remembered. */
export function writeWidth(storage: Writer | null, percent: number, groupWidth: number): void {
  if (!(percent > 0) || !(groupWidth > 0)) return;
  try {
    storage?.setItem(STORAGE_KEY, String(Math.round((percent / 100) * groupWidth)));
  } catch {
    // A browser that refuses storage keeps the default next time.
  }
}

/** The part of the splitter's API the drawer's tab uses. */
export interface Collapsible {
  isPanelCollapsed(id: string): boolean;
  collapsePanel(id: string): void;
  expandPanel(id: string): void;
}

/** The tab: opens a closed drawer and closes an open one. */
export function toggle(api: Collapsible): void {
  if (api.isPanelCollapsed(NAV_PANEL)) api.expandPanel(NAV_PANEL);
  else api.collapsePanel(NAV_PANEL);
}
