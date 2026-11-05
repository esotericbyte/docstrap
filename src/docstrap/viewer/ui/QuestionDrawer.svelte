<!--
  QuestionDrawer.svelte — the right drawer: the qapanels instrument's three
  panels, pointed at the pinned questions document.

  The panels are hosted, not rewritten: the
  same `Panels.svelte` a documentation page mounts as an overlay, filling
  this drawer instead of the viewport, handed a `DocstrapGlobal` whose
  context and routes are the pinned document's (`questions.ts`) and told
  where that project's pages are for its reference panel.

  The only thing this reads is `pinned`. Nothing about the middle region
  reaches it, which is why reading elsewhere cannot close, re-read or
  reset it. A new pin is a new questions document and gets fresh panels;
  the outgoing answer is saved first, as switching question or scope
  already saves it.
-->
<script lang="ts">
  import type { DocstrapGlobal } from '../../sphinx/ui/docstrap';
  import Panels from '../../tools/qapanels/ui/Panels.svelte';
  import { questionsGlobal } from './questions';
  import { pinValue } from './site';
  import type { Pinned } from './types';

  let {
    real,
    pinned,
    onclose,
  }: {
    /** The page's own `window.docstrap`, untouched. */
    real: DocstrapGlobal;
    pinned: Pinned | null;
    /** The panels' Close button and Escape: collapse the drawer. */
    onclose: () => void;
  } = $props();

  let panels = $state<ReturnType<typeof Panels> | null>(null);

  const d = $derived(pinned ? questionsGlobal(real, pinned) : null);

  /** Save whatever answer is pending. The shell calls this before the
   *  pin changes, while the outgoing panels still exist. */
  export function flush(): void {
    panels?.flush();
  }
</script>

{#if pinned && d}
  {#key pinValue(pinned)}
    <Panels bind:this={panels} {d} referenceBase={pinned.project.base} {onclose} />
  {/key}
{:else}
  <div class="flex h-full items-center justify-center p-6">
    <p class="max-w-sm text-center opacity-75">
      No questions document is pinned. Pin one in the navigator, and its questions stay here
      while you read anything in the middle.
    </p>
  </div>
{/if}
