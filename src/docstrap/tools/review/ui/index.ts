// docstrap review tool — entry point.
//
// Walks the rendered DOM for prose sentences and headings (marks.ts),
// mounts a tri-state Mark at each one, and mounts the submit bar. On
// submit the marks go to the route the declaration resolved for this
// page and the returned file path is copied to the clipboard.
//
// This tool used to inject its own floating button into the corner.
// That affordance is gone: it registers show/hide with the single
// launcher, which owns what is showing. The tool is declared
// default_visible=False, so it stays off until asked for — the same
// behaviour the floating button gave, from one place instead of three.
import { mount, unmount } from 'svelte';

import { requireDocstrap } from '../../../sphinx/ui/docstrap';
import Mark from './Mark.svelte';
import SubmitBar from './SubmitBar.svelte';
import {
  proseRoot,
  sectionSites,
  sentenceSites,
  type SectionMark,
  type SentenceMark,
} from './marks';

const TOOL = 'review';
const ACTIVE_CLASS = 'docstrap-review-active';

const d = requireDocstrap(TOOL);

if (d) {
  let sentenceMarks: SentenceMark[] = [];
  let sectionMarks: SectionMark[] = [];
  let mounted: ReturnType<typeof mount>[] = [];

  function show(): void {
    if (!d!.ctx.project || !d!.ctx.docSlug) return;
    if (document.body.classList.contains(ACTIVE_CLASS)) return;
    document.body.classList.add(ACTIVE_CLASS);

    sentenceMarks = [];
    sectionMarks = [];
    const root = proseRoot();

    // Headings first, then sentences: the sentence walk splits text
    // nodes, and doing it after the headings keeps the two passes from
    // seeing each other's insertions.
    for (const site of sectionSites(root)) {
      sectionMarks.push(site.record);
      mounted.push(
        mount(Mark, {
          target: site.parent as Element,
          anchor: site.anchor ?? undefined,
          props: {
            kind: 'section' as const,
            onmark: (state) => {
              site.record.mark = state;
            },
          },
        })
      );
    }
    for (const site of sentenceSites(root)) {
      sentenceMarks.push(site.record);
      mounted.push(
        mount(Mark, {
          target: site.parent as Element,
          anchor: site.anchor ?? undefined,
          props: {
            kind: 'sentence' as const,
            onmark: (state) => {
              site.record.mark = state;
            },
          },
        })
      );
    }

    mounted.push(
      mount(SubmitBar, {
        target: document.body,
        props: { d: d!, sentenceMarks, sectionMarks },
      })
    );
  }

  function hide(): void {
    document.body.classList.remove(ACTIVE_CLASS);
    mounted.forEach((instance) => unmount(instance));
    mounted = [];
    sentenceMarks = [];
    sectionMarks = [];
  }

  d.tools.register(TOOL, { show, hide });
}
