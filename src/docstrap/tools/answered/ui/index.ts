// docstrap answered tool — entry point.
//
// The serve half of the answered tool. The build marked each question
// block in this page's rendered HTML with `docstrap-question` and a class
// naming its label; this reads `/api/answers/{project}/{doc_slug}` and
// mounts one note after each marked block.
//
// It composes no path. `/api/answers/…` is the SERVER's API, not a tool's,
// so there is no declaration route to resolve — the same arrangement the
// status badge has with `/api/documents`, and the reason this tool
// declares `api_collection=None`. The project and doc slugs come from the
// page's own meta tags, which is where every tool gets its context.
//
// Silent when the server is not running. A published page with no docstrap
// behind it is the document its author wrote, unmarked, which is the
// correct degradation: this tool shows what the store knows, and with no
// store reachable it knows nothing.
import { mount, unmount } from 'svelte';

import { encodeDocSlug, requireDocstrap } from '../../../sphinx/ui/docstrap';
import AnswerNote from './AnswerNote.svelte';
import type { AnsweredQuestion, AnswersListing } from './types';

const TOOL = 'answered';
const BLOCK_CLASS = 'docstrap-question';

const d = requireDocstrap(TOOL);

if (d) {
  let mounted: ReturnType<typeof mount>[] = [];

  /** The label the build wrote onto a block, or null. */
  function labelOf(el: Element): string | null {
    for (const name of Array.from(el.classList)) {
      if (name.startsWith(`${BLOCK_CLASS}-`)) {
        // `docstrap-question-q1` → `Q1`. docutils lowercased it.
        return name.slice(BLOCK_CLASS.length + 1).toUpperCase();
      }
    }
    return null;
  }

  function show(): void {
    const project = d!.ctx.project;
    const docSlug = d!.ctx.docSlug;
    if (!project || !docSlug) return;

    // Nothing marked on this page means it poses no questions. Don't ask
    // the server about a document with nothing to say.
    if (!document.querySelector(`.${BLOCK_CLASS}`)) return;

    d!
      .api<AnswersListing>(
        // The project is one segment; the document identity is a path,
        // and `encodeDocSlug` keeps its separators separators. Encoding
        // the whole slug spelled `proposals%2F0002-…`, which matched
        // nothing: this tool then rendered no answers under any question
        // in any nested document, silently, on every page load.
        `/api/answers/${encodeURIComponent(project)}/${encodeDocSlug(docSlug)}`
      )
      .then(render)
      .catch(d!.silenceOfflineError);
  }

  function hide(): void {
    for (const note of mounted) unmount(note);
    mounted = [];
  }

  function render(listing: AnswersListing | null): void {
    if (!listing) return;
    // The reader may have hidden the tool while the fetch was in flight;
    // don't draw chrome for a tool that is no longer showing.
    if (!d!.tools.isVisible(TOOL)) return;
    if (mounted.length) return;

    const byLabel = new Map<string, AnsweredQuestion>();
    for (const question of listing.questions) byLabel.set(question.label, question);

    for (const block of Array.from(document.querySelectorAll(`.${BLOCK_CLASS}`))) {
      const label = labelOf(block);
      if (!label) continue;
      const question = byLabel.get(label);
      if (!question) continue;
      // After the block, never inside it: the question as its author
      // wrote it is left exactly as the page rendered it.
      const holder = document.createElement('div');
      block.insertAdjacentElement('afterend', holder);
      mounted.push(mount(AnswerNote, { target: holder, props: { question } }));
    }
  }

  d.tools.register(TOOL, { show, hide });
}
