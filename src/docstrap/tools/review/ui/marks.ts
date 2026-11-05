// marks.ts — the review record, and how the rendered page is walked to
// find the places a mark can go.
//
// Pure TypeScript: this is DOM analysis, not view. The components draw
// the marks and the submit bar; this decides where marks belong and
// what text each one is standing for. Keeping the two apart is what
// makes the sentence heuristic reviewable on its own.

export type MarkState = '' | 'check' | 'x';

export interface SentenceMark {
  mark: MarkState;
  text: string;
}

export interface SectionMark {
  mark: MarkState;
  id: string;
  text: string;
}

/** Where one mark goes: a parent, the node to insert before, its record. */
export interface MarkSite<Record> {
  parent: Node;
  anchor: Node | null;
  record: Record;
}

// Selectors for prose we walk. Anything inside these is skipped.
const SKIP_SELECTOR =
  'pre, code, a, h1, h2, h3, h4, h5, h6, .headerlink, .docstrap-launcher';

// Rough sentence boundary. Handles ". ", "? ", "! " followed by
// uppercase-or-quote-or-open-bracket. Not perfect for abbreviations.
const SENT_RE = /([.?!])\s+(?=[A-Z"'“(\[])/g;

function isInSkip(node: Node): boolean {
  let el: Element | null =
    node.nodeType === Node.TEXT_NODE
      ? node.parentElement
      : (node as Element);
  while (el && el !== document.body) {
    if (el.matches && el.matches(SKIP_SELECTOR)) return true;
    el = el.parentElement;
  }
  return false;
}

/** The region of the page that carries the document's prose. */
export function proseRoot(): Element {
  return (
    document.querySelector('article') ||
    document.querySelector('main') ||
    document.body
  );
}

/** One site per h2/h3/h4, the mark appended inside the heading. */
export function sectionSites(root: Element): MarkSite<SectionMark>[] {
  const sites: MarkSite<SectionMark>[] = [];
  root.querySelectorAll('h2, h3, h4').forEach((heading) => {
    sites.push({
      parent: heading,
      anchor: null,
      record: {
        mark: '',
        id: heading.id || '',
        text: heading.textContent!.replace(/¶$/, '').trim(),
      },
    });
  });
  return sites;
}

/**
 * One site per sentence boundary in the prose.
 *
 * Splits the text nodes as it goes — a mark sits between two text
 * nodes, so the split has to happen before anything can be inserted.
 * The record's text is the tail of the sentence the mark follows,
 * which is what a reader of the submitted review needs to recognise it.
 */
export function sentenceSites(root: Element): MarkSite<SentenceMark>[] {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      if (isInSkip(node)) return NodeFilter.FILTER_REJECT;
      if (!node.textContent!.trim()) return NodeFilter.FILTER_REJECT;
      return NodeFilter.FILTER_ACCEPT;
    },
  });

  const textNodes: Text[] = [];
  let n: Node | null;
  while ((n = walker.nextNode())) textNodes.push(n as Text);

  const sites: MarkSite<SentenceMark>[] = [];
  textNodes.forEach((textNode) => {
    const text = textNode.textContent!;
    const boundaries: number[] = [];
    let m: RegExpExecArray | null;
    SENT_RE.lastIndex = 0;
    while ((m = SENT_RE.exec(text)) !== null) {
      boundaries.push(m.index + m[1].length); // position after the . ? or !
    }
    if (boundaries.length === 0) return;

    const parent = textNode.parentNode!;
    let current = textNode;
    let offsetAdjust = 0;
    boundaries.forEach((absPos) => {
      const localPos = absPos - offsetAdjust;
      if (localPos <= 0 || localPos >= current.textContent!.length) return;
      const rest = current.splitText(localPos);
      sites.push({
        parent,
        anchor: rest,
        record: { mark: '', text: current.textContent!.trim().slice(-140) },
      });
      offsetAdjust += current.textContent!.length;
      current = rest;
    });
  });
  return sites;
}
