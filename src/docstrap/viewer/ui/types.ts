// types.ts — the shape of `_viewer/manifest.json`.
//
// Mirrors `docstrap.viewer.manifest.compose`. Every URL in it is relative
// to the site root, which is where the shell's page is, so a URL from the
// manifest can be handed to a frame as it is.

import type { ToolOffer } from '../../sphinx/ui/docstrap';

export interface ManifestDocument {
  /** The document's identity: its path below docs_root, suffix dropped. */
  docname: string;
  title: string;
  kind: 'document' | 'section';
  /** The section page that lists it; '' for the project's own root. */
  parent: string;
  grouping: string;
  sortKey: string;
  url: string;
  /** The qapanels offer this document's own page carries, routes
   *  resolved by Python. Null for a section, which poses no questions. */
  questions: ToolOffer | null;
}

export interface ManifestProject {
  slug: string;
  title: string;
  icon: string;
  /** Where this project's pages are, ending in `/`. */
  base: string;
  landing: string;
  documents: ManifestDocument[];
}

export interface ManifestStore {
  title: string;
  icon: string;
  landing: string;
  projects: ManifestProject[];
}

export interface Manifest {
  version: number;
  title: string;
  landing: string;
  stores: ManifestStore[];
}

/** The questions document: what the right drawer is pinned to. */
export interface Pinned {
  project: ManifestProject;
  document: ManifestDocument;
}

/** One request to show a page in the middle region. A new object every
 *  time, so asking again for a page the frame has since left navigates. */
export interface PageRequest {
  url: string;
}
