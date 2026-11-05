// site.ts — the manifest turned into what the navigator draws.
//
// Pure functions over the manifest: the tree the left drawer renders, the
// node a page URL belongs to, and the questions document a shell URL
// names. No DOM and no fetch here.

import type { Manifest, ManifestDocument, ManifestProject, Pinned } from './types';

export interface SiteNode {
  id: string;
  name: string;
  /** The page selecting this node shows in the middle region. */
  url: string;
  kind: 'site' | 'store' | 'project' | 'section' | 'document';
  /** For a document that poses questions: what pinning it pins. */
  pin: Pinned | null;
  children?: SiteNode[];
}

/** One id per node, unique across stores and projects. */
export function documentId(projectSlug: string, docname: string): string {
  return `${projectSlug}::${docname}`;
}

function bySortKey(a: ManifestDocument, b: ManifestDocument): number {
  return a.sortKey.localeCompare(b.sortKey) || a.docname.localeCompare(b.docname);
}

/**
 * A project's documents as a tree, following each entry's own parent.
 *
 * The shape comes from the file index the build wrote, which is the
 * shape of the published site; nothing here splits a path or invents a
 * name. The project's root section (`index`, listed by nothing) is the
 * project node itself, so it is not repeated as a child.
 */
function projectNode(project: ManifestProject): SiteNode {
  const byParent = new Map<string, ManifestDocument[]>();
  for (const doc of project.documents) {
    const siblings = byParent.get(doc.parent) ?? [];
    siblings.push(doc);
    byParent.set(doc.parent, siblings);
  }

  function children(parent: string): SiteNode[] {
    return (byParent.get(parent) ?? []).sort(bySortKey).map((doc) => {
      const node: SiteNode = {
        id: documentId(project.slug, doc.docname),
        name: doc.title,
        url: doc.url,
        kind: doc.kind === 'section' ? 'section' : 'document',
        pin: doc.questions ? { project, document: doc } : null,
      };
      if (doc.kind === 'section') node.children = children(doc.docname);
      return node;
    });
  }

  const root = project.documents.find((doc) => doc.parent === '');
  return {
    id: `project::${project.slug}`,
    name: project.title,
    url: project.landing,
    kind: 'project',
    pin: null,
    children: root ? children(root.docname) : [],
  };
}

/**
 * The navigator's tree. The root itself is never drawn; its children are
 * the rows.
 *
 * The site's root page — what the viewer entrance asks for — is a row of
 * its own at the top, so it is selected and highlighted like any other
 * page. Not when a store's landing page is that same page, as in a
 * single-store build: the store's row already is it.
 */
export function siteTree(manifest: Manifest): SiteNode {
  const stores: SiteNode[] = manifest.stores.map((store, index) => ({
    id: `store::${index}`,
    // The store's configured icon is content, not an icon the shell
    // draws; the tree's own icons come from Lucide.
    name: store.title,
    url: store.landing,
    kind: 'store',
    pin: null,
    children: store.projects.map(projectNode),
  }));
  const front: SiteNode[] = manifest.stores.some((store) => store.landing === manifest.landing)
    ? []
    : [{ id: 'front', name: manifest.title, url: manifest.landing, kind: 'site', pin: null }];
  return {
    id: 'root',
    name: manifest.title,
    url: manifest.landing,
    kind: 'store',
    pin: null,
    children: [...front, ...stores],
  };
}

/**
 * A site-relative path in one spelling, whoever wrote it.
 *
 * The manifest escapes what Python's `quote` escapes and a browser's
 * location escapes what the browser does; the two disagree about
 * characters like `(`. Decoding each segment gives both one spelling.
 */
export function normalPath(path: string): string {
  return path
    .split('/')
    .map((segment) => {
      try {
        return decodeURIComponent(segment);
      } catch {
        return segment;
      }
    })
    .join('/');
}

/** Every drawn node, keyed by the normalised site-relative URL of its
 *  page. The undrawn root is left out, so a page always maps to a row. */
export function nodesByUrl(root: SiteNode): Map<string, SiteNode> {
  const map = new Map<string, SiteNode>();
  function walk(node: SiteNode): void {
    const key = normalPath(node.url);
    if (!map.has(key)) map.set(key, node);
    node.children?.forEach(walk);
  }
  root.children?.forEach(walk);
  return map;
}

/** The ids from the root down to `id`, excluding the root itself. */
export function pathTo(root: SiteNode, id: string): string[] {
  const trail: string[] = [];
  function walk(node: SiteNode): boolean {
    if (node.id === id) return true;
    for (const child of node.children ?? []) {
      trail.push(child.id);
      if (walk(child)) return true;
      trail.pop();
    }
    return false;
  }
  return walk(root) ? trail : [];
}

/** The pin a `?questions=<project>/<docname>` value names, if any. */
export function findPin(manifest: Manifest, value: string | null): Pinned | null {
  if (!value) return null;
  const cut = value.indexOf('/');
  if (cut < 0) return null;
  const slug = value.slice(0, cut);
  const docname = value.slice(cut + 1);
  for (const store of manifest.stores) {
    for (const project of store.projects) {
      if (project.slug !== slug) continue;
      const document = project.documents.find((doc) => doc.docname === docname);
      if (document?.questions) return { project, document };
    }
  }
  return null;
}

export function pinValue(pin: Pinned): string {
  return `${pin.project.slug}/${pin.document.docname}`;
}

/**
 * A frame's location as a normalised site-relative path, the key
 * `nodesByUrl` uses.
 *
 * `siteBase` is the directory the shell's page is in, which is the site
 * root. A directory URL is its index page, the way the static server
 * answers it. Anything outside the site — or not yet loaded — is null.
 */
export function siteRelative(href: string, siteBase: string): string | null {
  let url: URL;
  try {
    url = new URL(href);
  } catch {
    return null;
  }
  const base = new URL(siteBase);
  if (url.origin !== base.origin || !url.pathname.startsWith(base.pathname)) return null;
  let path = url.pathname.slice(base.pathname.length);
  if (path === '' || path.endsWith('/')) path += 'index.html';
  return normalPath(path);
}

/**
 * The page an address asks the middle region for, site-relative, or null.
 *
 * Two spellings are accepted. `?doc-url=` is the shell's own, and what
 * every published page's button writes: the page's URL, encoded — the
 * site-relative URL the manifest lists it by, or a full URL on this
 * site. The page in the hash is the older form, kept for links already
 * made; the shell never writes a hash, so one that is there is a new
 * instruction and wins. A URL off this site asks for nothing: the shell
 * frames this site's pages and no one else's.
 */
export function requestedPage(
  docUrl: string | null,
  hash: string,
  siteBase: string
): string | null {
  let asked = docUrl;
  if (hash.length > 1) {
    try {
      asked = decodeURIComponent(hash.slice(1));
    } catch {
      asked = hash.slice(1);
    }
  }
  if (!asked) return null;
  let href: string;
  try {
    href = new URL(asked, siteBase).href;
  } catch {
    return null;
  }
  return siteRelative(href, siteBase);
}
