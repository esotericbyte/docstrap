<!--
  App.svelte — the viewer shell.

  Three regions, always side by side: the navigator on the left, the
  selected published page in a frame in the middle, the qapanels
  instrument's three panels on the right. docstrap is a workstation tool,
  so there is one width class and no breakpoint.

  Two pieces of state, and nothing couples them:

    `pinned` — the questions document. Only pinning changes it, and it is
               all the right drawer reads.
    `here`   — the page in the middle. Selecting in the tree or following
               a link inside the frame changes it, and the drawer never
               sees it.

  So navigating the middle cannot close, re-read or reset the drawer.
  Collapsing either drawer hides it and never unmounts it: the panels
  hold the answer being typed and a pending autosave.

  The left drawer is resizable and collapsible: Zag's
  splitter owns the dragging and the collapsing, `navigatorPane.ts` owns
  the widths and what is remembered, and a thin tab on the drawer's edge
  — at the window's edge when it is closed — opens and closes it.

  This component holds the layout and the two pieces of state, and
  composes three children that own their regions: `Navigator`,
  `DocumentView` (the frame, its loading and its failures) and
  `QuestionDrawer` (the hosted panels).

  Every region owns its overflow: the shell is exactly the
  viewport's height, each region scrolls inside itself, and the page
  itself never grows. The body is not the scroll element, deliberately,
  because three regions must scroll independently.
-->
<script lang="ts">
  import ChevronLeft from '@lucide/svelte/icons/chevron-left';
  import ChevronRight from '@lucide/svelte/icons/chevron-right';
  import Library from '@lucide/svelte/icons/library';
  import PanelLeft from '@lucide/svelte/icons/panel-left';
  import PanelRight from '@lucide/svelte/icons/panel-right';
  import { AppBar } from '@skeletonlabs/skeleton-svelte';
  import * as splitter from '@zag-js/splitter';
  import { normalizeProps, useMachine } from '@zag-js/svelte';
  import { onMount, untrack } from 'svelte';

  import { describeApiFailure, requireDocstrap } from '../../sphinx/ui/docstrap';
  import DocumentView from './DocumentView.svelte';
  import Navigator from './Navigator.svelte';
  import QuestionDrawer from './QuestionDrawer.svelte';
  import {
    findPin,
    nodesByUrl,
    normalPath,
    pathTo,
    pinValue,
    requestedPage,
    siteTree,
    type SiteNode,
  } from './site';
  import {
    NAV_PANEL,
    PANELS,
    REST_PANEL,
    TRIGGER,
    readWidth,
    toggle,
    viewerStorage,
    writeWidth,
  } from './navigatorPane';
  import { QueryParam } from './queryParam.svelte';
  import type { Manifest, PageRequest, Pinned } from './types';

  const MANIFEST_URL = '_viewer/manifest.json';
  const PIN_PARAM = 'questions';
  /** `viewer.manifest.DOC_URL_PARAM`; `test_viewer.py` holds the two to one name. */
  const DOC_URL_PARAM = 'doc-url';
  const docUrl = new QueryParam(DOC_URL_PARAM);

  const real = requireDocstrap('viewer');

  /** The site root: the directory this page is in. */
  const siteBase = new URL('.', window.location.href).href;

  let manifest = $state<Manifest | null>(null);
  let loadError = $state('');

  const tree = $derived(manifest ? siteTree(manifest) : null);
  const byUrl = $derived(tree ? nodesByUrl(tree) : new Map<string, SiteNode>());

  /** The latest request for a page in the middle region. */
  let request = $state<PageRequest | null>(null);
  /** Where the middle region actually is, site-relative. */
  let here = $state('');
  let expanded = $state<string[]>([]);
  let pinned = $state<Pinned | null>(null);
  let rightOpen = $state(true);

  // The left drawer. Its width is read once, so the machine's initial
  // size never changes under it; afterwards the machine owns the size.
  const storage = viewerStorage();
  const openWidth = readWidth(storage);
  let groupWidth = $state(0);
  const split = useMachine(splitter.machine, () => ({
    id: 'docstrap-viewer-split',
    panels: PANELS,
    defaultSize: [openWidth],
    onResizeEnd: ({ size }) => writeWidth(storage, size[0], groupWidth),
  }));
  const splitApi = $derived(splitter.connect(split, normalizeProps));
  const leftOpen = $derived(!splitApi.isPanelCollapsed(NAV_PANEL));
  const toggleLeft = () => toggle(splitApi);

  let drawer = $state<ReturnType<typeof QuestionDrawer> | null>(null);

  const currentNode = $derived(here ? (byUrl.get(normalPath(here)) ?? null) : null);

  onMount(() => {
    void load();
  });

  async function load(): Promise<void> {
    if (!real) {
      loadError = 'The docstrap client did not load, so the shell cannot run.';
      return;
    }
    try {
      manifest = await real.api<Manifest>(MANIFEST_URL);
    } catch (err) {
      loadError = `Could not read the site's manifest: ${describeApiFailure(err, MANIFEST_URL)}`;
      return;
    }
    // The shell's own URL carries both pieces of state, as two fields,
    // so a reload restores both and they stay independent there too.
    const params = new URLSearchParams(window.location.search);
    pinned = findPin(manifest, params.get(PIN_PARAM));
    // Stores start open: a store is a heading, and the projects under it
    // are the first thing anyone looks for.
    expanded = (tree?.children ?? []).map((store) => store.id);
    // `?doc-url=` names the middle region's page: the viewer entrance
    // and every published page's button ask for their page with it.
    const start = requestedPage(
      new URLSearchParams(window.location.search).get(DOC_URL_PARAM),
      window.location.hash,
      siteBase
    );
    show(start ?? manifest.landing);
  }

  // The address changed under the open shell — back or forward through
  // history, or a hash typed into it. Only the events `docUrl` listens
  // to re-run this; the shell's own writes below fire none, so what it
  // records about itself never comes back here as a request.
  $effect(() => {
    const asked = docUrl.current;
    untrack(() => {
      if (!manifest) return;
      const wanted = requestedPage(asked, window.location.hash, siteBase);
      if (wanted !== null && normalPath(wanted) !== normalPath(here)) show(wanted);
    });
  });

  /** Ask the middle region for a page. Nothing else moves. */
  function show(url: string): void {
    request = { url };
    here = url;
    reveal(url);
  }

  /** The middle region reached a page — perhaps by a link inside it.
   *  Only the tree is told; the drawer never is. */
  function arrived(relative: string): void {
    here = relative;
    reveal(relative);
  }

  /** Open the tree down to the node for `url`, so the reader can see it. */
  function reveal(url: string): void {
    const node = byUrl.get(normalPath(url));
    if (!node || !tree) return;
    const trail = pathTo(tree, node.id).slice(0, -1);
    const missing = trail.filter((id) => !expanded.includes(id));
    if (missing.length) expanded = [...expanded, ...missing];
  }

  function pin(next: Pinned): void {
    if (pinned && pinValue(pinned) === pinValue(next)) {
      rightOpen = true;
      return;
    }
    // Re-pinning replaces the panels. Their outgoing answer is saved
    // first, the way switching question or scope saves it.
    drawer?.flush();
    pinned = next;
    rightOpen = true;
  }

  function unpin(): void {
    drawer?.flush();
    pinned = null;
  }

  // Write both pieces of state to the shell's URL whenever either moves.
  // The page goes in `?doc-url=`, and any hash that asked for it is
  // dropped, so the address always has the one spelling.
  $effect(() => {
    if (!manifest) return;
    const params = new URLSearchParams(window.location.search);
    if (pinned) params.set(PIN_PARAM, pinValue(pinned));
    else params.delete(PIN_PARAM);
    params.set(DOC_URL_PARAM, here);
    const next = `${window.location.pathname}?${params.toString()}`;
    if (next !== `${window.location.pathname}${window.location.search}${window.location.hash}`) {
      history.replaceState(null, '', next);
    }
  });

  const columns = $derived(
    [
      'minmax(0, 1fr)',
      rightOpen ? 'minmax(30rem, 38%)' : null,
    ]
      .filter(Boolean)
      .join(' ')
  );
</script>

<div class="shell bg-surface-50-950 text-surface-950-50 grid h-dvh grid-rows-[auto_minmax(0,1fr)] overflow-hidden">
  <AppBar class="border-surface-200-800 border-b px-3 py-1.5">
    <AppBar.Toolbar class="grid-cols-[auto_1fr_auto] items-center gap-3">
      <AppBar.Lead>
        <button
          type="button"
          class="btn-icon size-10 {leftOpen ? 'preset-tonal' : 'hover:preset-tonal'}"
          aria-label={leftOpen ? 'Hide the navigator' : 'Show the navigator'}
          aria-pressed={leftOpen}
          title={leftOpen ? 'Hide the navigator' : 'Show the navigator'}
          onclick={toggleLeft}><PanelLeft class="size-5" /></button>
      </AppBar.Lead>
      <AppBar.Headline class="flex min-w-0 items-center gap-2">
        <Library class="size-5 shrink-0 opacity-70" />
        <span class="font-semibold">{manifest ? manifest.title : 'docstrap'}</span>
        {#if currentNode && currentNode.name !== manifest?.title}
          <span class="truncate opacity-70">— {currentNode.name}</span>
        {/if}
      </AppBar.Headline>
      <AppBar.Trail>
        <button
          type="button"
          class="btn-icon size-10 {rightOpen ? 'preset-tonal' : 'hover:preset-tonal'}"
          aria-label={rightOpen ? 'Hide the questions' : 'Show the questions'}
          aria-pressed={rightOpen}
          title={rightOpen ? 'Hide the questions' : 'Show the questions'}
          onclick={() => (rightOpen = !rightOpen)}><PanelRight class="size-5" /></button>
      </AppBar.Trail>
    </AppBar.Toolbar>
  </AppBar>

  <div class="min-h-0 overflow-hidden" bind:clientWidth={groupWidth} {...splitApi.getRootProps()}>
    <!-- The splitter styles its panel inline, `overflow: hidden` included,
         so the tree scrolls in an aside inside the panel. -->
    <div class="min-h-0" {...splitApi.getPanelProps({ id: NAV_PANEL })}>
      <aside
        class="region border-surface-200-800 h-full min-w-0 overflow-x-hidden overflow-y-auto border-r"
        aria-label="Navigator"
        inert={!leftOpen}
      >
        {#if tree}
          <Navigator
            {tree}
            currentId={currentNode ? currentNode.id : null}
            {expanded}
            {pinned}
            onselect={(node) => show(node.url)}
            onshow={show}
            onexpand={(ids) => (expanded = ids)}
            onpin={pin}
            onunpin={unpin}
          />
        {:else if loadError}
          <p class="p-4 text-sm">{loadError}</p>
        {:else}
          <p class="p-4 text-sm opacity-70">Reading the site…</p>
        {/if}
      </aside>
    </div>

    <!-- The drawer's edge: a strip to drag, and the tab that opens and
         closes the drawer. The tab is the strip's sibling, not its child,
         so pressing it never starts a drag. -->
    <div class="edge relative z-10 flex shrink-0">
      <div
        class="resize-trigger hover:bg-primary-500/40 data-dragging:bg-primary-500/60 data-focus:bg-primary-500/40 h-full w-1.5 outline-none"
        aria-label="Resize the navigator"
        {...splitApi.getResizeTriggerProps({ id: TRIGGER })}
      ></div>
      <button
        type="button"
        class="drawer-tab bg-surface-200-800 hover:preset-tonal-primary border-surface-300-700 absolute top-1/2 left-0 flex h-16 w-4 -translate-y-1/2 items-center justify-center rounded-r-md border border-l-0"
        aria-label={leftOpen ? 'Close the navigator' : 'Open the navigator'}
        aria-expanded={leftOpen}
        title={leftOpen ? 'Close the navigator' : 'Open the navigator'}
        onclick={toggleLeft}
      >
        {#if leftOpen}<ChevronLeft class="size-3.5" />{:else}<ChevronRight class="size-3.5" />{/if}
      </button>
    </div>

    <div
      class="grid min-h-0 min-w-0 overflow-hidden"
      style:grid-template-columns={columns}
      {...splitApi.getPanelProps({ id: REST_PANEL })}
    >
      <main class="region min-h-0 min-w-0 overflow-hidden" aria-label="Document">
        <DocumentView
          {request}
          {siteBase}
          title={currentNode ? currentNode.name : 'The selected document'}
          onarrive={arrived}
        />
      </main>

      <aside
        class="region border-surface-200-800 min-h-0 min-w-0 overflow-hidden border-l"
        hidden={!rightOpen}
        aria-label="Questions"
      >
        {#if real}
          <QuestionDrawer bind:this={drawer} {real} {pinned} onclose={() => (rightOpen = false)} />
        {/if}
      </aside>
    </div>
  </div>

  <!-- The tablet target's landscape preference. Portrait on a coarse
       pointer only: orientation is the viewport's aspect, and a tall
       desktop window must never see this. A message, not a layout. -->
  <div class="portrait-note bg-surface-50-950/95 fixed inset-0 z-50 items-center justify-center p-8">
    <p class="card preset-tonal max-w-md p-6 text-center text-lg">
      The docstrap viewer needs landscape. Turn the device sideways for the navigator, the
      document and the questions side by side.
    </p>
  </div>
</div>

<style>
  .portrait-note {
    display: none;
  }
  @media (orientation: portrait) and (pointer: coarse) {
    .portrait-note {
      display: flex;
    }
  }
</style>
