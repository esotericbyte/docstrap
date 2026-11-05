// docstrap.ts — a typed view of the client extension points.
//
// `docstrap-common.js` puts `window.docstrap` on the page before any
// tool bundle runs. This module is only the type of that object plus a
// guarded accessor; it adds no behaviour and ships no code of its own
// beyond the guard, so the extension points stay defined in one place
// (docstrap-common.js) and are described in one place here.
//
// It sits beside the shared client assets rather than inside any tool,
// for the same reason they do: it belongs to no tool. It names none
// either — a tool passes its own id in.

export interface DocstrapCtx {
  docId: string | null;
  project: string | null;
  /** The document's identity: its PATH below the project's docs_root with
   *  the suffix dropped — `proposals/0002-the-upgrade-path`. Nested is the
   *  normal case; the separators are part of the identity. */
  docSlug: string | null;
  sourcePath: string | null;
}

/** A document identity, encoded for a URL path.
 *
 * `encodeURIComponent` on the whole slug is the bug this exists to stop
 * being rewritten: it turns the separators into `%2F`, which spells a
 * one-segment name that no route matches and no project declares. Each
 * segment is encoded, and the separators are left as separators.
 *
 * Only for the SERVER's own APIs (`/api/answers/…`, `/api/documents/…`),
 * which a tool addresses directly because they belong to no tool. A
 * tool's own route is resolved from its declaration by
 * `docstrap.tools.route()` and is never assembled in the browser.
 */
export function encodeDocSlug(slug: string): string {
  return slug.split('/').map(encodeURIComponent).join('/');
}

/** The HTTP status a failed `api()` call carries, or null when there is none.
 *
 * `docstrap-common.js` hangs the `Response` off the error it throws, so a
 * server that answered can be told from a server that was not there:
 * `fetch` rejects with a `TypeError` and no response when nothing is
 * listening. The difference matters to what a tool says out loud — a 404
 * from a responding docstrap is a routing, document or tool-context
 * problem, and reporting it as "is `docstrap serve` running?" sends the
 * reader to check a thing that is already true.
 */
export function apiStatus(err: unknown): number | null {
  const response = (err as { response?: { status?: unknown } } | null | undefined)
    ?.response;
  return typeof response?.status === 'number' ? response.status : null;
}

/** What a tool should say about a failed API call.
 *
 * One wording, in one place, because every tool had grown the same
 * sentence — `is docstrap serve running?` — and every tool was wrong in
 * the same way. A 404 or a 405 from a responding server says the URL
 * names nothing it serves, which is a route, a document identity or a
 * page-context problem; sending the reader to restart a server that is
 * already answering is how one broken URL read as a dead tool for a day.
 *
 * `url` is optional: a surface that did not assemble the URL itself says
 * the rest of the truth without it.
 */
export function describeApiFailure(err: unknown, url?: string | null): string {
  const status = apiStatus(err);
  if (status === null) {
    return 'could not reach docstrap — is `docstrap serve` running?';
  }
  const at = url ? ` at ${url}` : '';
  if (status === 404 || status === 405) {
    return (
      `docstrap answered ${status} — it serves nothing${at}. A route, a ` +
      `document identity or this page's project context is wrong; the ` +
      `server is fine.`
    );
  }
  return `docstrap answered ${status}${at}.`;
}

export interface ToolOffer {
  id: string;
  title: string;
  kind: 'tool' | 'instrument';
  target: 'document' | 'project';
  summary: string;
  defaultVisible: boolean;
  visibilityClass: string;
  route: string | null;
  /** The URL of a declared second scope, or null when there is none or
   *  this page cannot fill its template. */
  altRoute: string | null;
}

/** The two handlers a tool declares, and nothing else. */
export interface ToolHandlers {
  show: () => void;
  hide: () => void;
}

export interface DocstrapTools {
  register(id: string, handlers: ToolHandlers): void;
  offers(): ToolOffer[];
  offer(id: string): ToolOffer | null;
  route(id: string): string | null;
  altRoute(id: string): string | null;
  isVisible(id: string): boolean;
  setVisible(id: string, on: boolean): void;
  hideAll(): void;
  onChange(fn: (id: string, on: boolean) => void): void;
  start(): void;
}

export interface DocstrapGlobal {
  ctx: DocstrapCtx;
  apiBase: string;
  api<T = unknown>(path: string, options?: RequestInit & { body?: unknown }): Promise<T>;
  silenceOfflineError(err: unknown): null;
  onReady(fn: () => void): void;
  tools: DocstrapTools;
}

declare global {
  interface Window {
    docstrap?: DocstrapGlobal;
  }
}

/**
 * The shared bundle, or null with a warning naming the caller.
 *
 * Every tool opened with this guard before the build existed and every
 * tool still does: a page that somehow loaded a tool without the common
 * bundle degrades to doing nothing rather than throwing into the
 * reader's console on every page.
 */
export function requireDocstrap(toolId: string): DocstrapGlobal | null {
  const d = window.docstrap;
  if (!d) {
    console.warn(`docstrap-${toolId}: common bundle missing`);
    return null;
  }
  return d;
}
