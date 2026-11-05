<!--
  DocumentView.svelte — the middle region: one published page, in a frame.

  The frame is the precedent `Reference.svelte` set:
  what is read is exactly what was published, by the renderer that
  published it, and a frame is a separate document, so furo's styles and
  the shell's Tailwind never meet.

  This component owns the frame and everything about it, so the shell
  root holds layout and nothing else:

    loading     A requested page is checked before the frame is pointed
                at it. That one request is what can tell "docstrap
                answered, and has no such page" from "nothing answered"
                — a frame cannot, because both arrive as a load event.
    arriving    A page the reader reached by a link INSIDE the frame was
                never requested. When it loads, its own navigation entry
                says what status it came with, and where it is is
                reported up — to the tree's highlight, and to nothing
                that could touch the question drawer.
    failing     Both failures are worded by `describeApiFailure`, the one
                place allowed to say `docstrap serve` is not running, and
                only when no response came back at all. A 404 is said to
                be a 404. Whether the panel layer should draw that line
                is an open ruling; this region draws it the way the
                shared wording already does, and adds no third wording.
    entrance    The root page's link into the viewer is hidden in this
                frame, where following it would nest a viewer in the
                viewer. Only that link: whether the page's other
                apparatus belongs here is an open question, and
                hiding `.docstrap-chrome` would answer it.
    scrolling   The framed page is its own document and scrolls itself,
                inside this region; this region never grows the shell.
                Every newly requested page opens at its top, as any
                navigation does.
-->
<script lang="ts">
  import TriangleAlert from '@lucide/svelte/icons/triangle-alert';

  import { describeApiFailure } from '../../sphinx/ui/docstrap';
  import { siteRelative } from './site';
  import type { PageRequest } from './types';

  /** `manifest.ENTRANCE_CLASS`; `test_viewer.py` holds the two to one name. */
  const SUPPRESS_ENTRANCE = '.docstrap-viewer-entrance { display: none !important; }';

  let {
    request,
    siteBase,
    title,
    onarrive,
  }: {
    request: PageRequest | null;
    /** The site root, which every manifest URL is relative to. */
    siteBase: string;
    /** What the frame is showing, for its accessible name. */
    title: string;
    /** The frame is now showing this site-relative page. */
    onarrive: (relative: string) => void;
  } = $props();

  type Phase = 'idle' | 'loading' | 'shown' | 'failed';

  let phase = $state<Phase>('idle');
  let failure = $state('');
  /** What the frame has been told to load. Only a checked request
   *  writes it — never a link followed inside the frame. */
  let src = $state('');
  let frame = $state<HTMLIFrameElement | null>(null);

  // Requests can overtake each other when the reader clicks quickly;
  // only the newest one may point the frame anywhere.
  let latest: PageRequest | null = null;

  $effect(() => {
    if (request) void open(request);
  });

  async function open(next: PageRequest): Promise<void> {
    latest = next;
    phase = 'loading';
    failure = '';
    let error: unknown = null;
    try {
      const response = await fetch(next.url, { method: 'HEAD', cache: 'no-store' });
      if (!response.ok) error = { response };
    } catch (err) {
      error = err;
    }
    if (latest !== next) return;
    if (error !== null) {
      phase = 'failed';
      failure = describeApiFailure(error, next.url);
      return;
    }
    // The frame may have followed links away from the page its `src`
    // names, and setting an attribute to the value it already has does
    // not navigate. So a repeated request navigates the frame itself.
    if (src === next.url && frame?.contentWindow) {
      frame.contentWindow.location.assign(new URL(next.url, siteBase).href);
    } else {
      src = next.url;
    }
  }

  /** The frame loaded something — a requested page or one reached by a
   *  link inside it. Find out what, and whether it arrived whole. */
  function onLoad(): void {
    if (!src) return;
    let href: string | null = null;
    let status = 0;
    try {
      const win = frame?.contentWindow ?? null;
      href = win?.location.href ?? null;
      const entry = win?.performance.getEntriesByType('navigation')[0] as
        | (PerformanceNavigationTiming & { responseStatus?: number })
        | undefined;
      status = entry?.responseStatus ?? 0;
      const doc = win?.document;
      if (doc?.head) {
        const style = doc.createElement('style');
        style.textContent = SUPPRESS_ENTRANCE;
        doc.head.append(style);
      }
    } catch {
      // A page off this site: nothing to read and nothing to report.
    }
    if (status >= 400) {
      phase = 'failed';
      failure = describeApiFailure({ response: { status } }, href);
    } else {
      phase = 'shown';
    }
    const relative = href ? siteRelative(href, siteBase) : null;
    if (relative !== null) onarrive(relative);
  }

  function retry(): void {
    if (latest) void open({ url: latest.url });
  }
</script>

<div class="relative h-full min-h-0">
  {#if src}
    <iframe
      bind:this={frame}
      {src}
      {title}
      class="block h-full w-full border-0 bg-white"
      class:invisible={phase === 'failed'}
      onload={onLoad}
    ></iframe>
  {/if}

  {#if phase === 'failed'}
    <div class="absolute inset-0 flex items-center justify-center overflow-y-auto p-8">
      <div class="card preset-tonal-error flex max-w-xl flex-col gap-3 p-6" role="alert">
        <p class="flex items-center gap-2 font-semibold">
          <TriangleAlert class="size-5 shrink-0" />
          This page could not be shown
        </p>
        <p class="text-sm">{failure}</p>
        <div>
          <button type="button" class="btn preset-filled min-h-10" onclick={retry}>Try again</button>
        </div>
      </div>
    </div>
  {:else if phase === 'loading' && !src}
    <p class="absolute inset-0 flex items-center justify-center opacity-60">Loading…</p>
  {/if}
</div>
