<!--
  Reference.svelte — panel three: the rendered document the selected
  question came from, scrollable, read only.

  It is the built site's own page in an <iframe>, so what is read here is
  exactly what is published — no second renderer and nothing to keep in
  step. Same origin, so the frame's own tool chrome is suppressed once it
  loads: everything a tool draws that is apparatus rather than document
  carries `.docstrap-chrome`, which is the documented category and means one
  rule covers every tool without naming any of them.
-->
<script lang="ts">
  let { url, path }: { url: string | null; path: string } = $props();

  const SUPPRESS_CHROME = '.docstrap-chrome { display: none !important; }';

  function onLoad(event: Event): void {
    const frame = event.currentTarget as HTMLIFrameElement;
    try {
      const doc = frame.contentDocument;
      if (!doc || doc.getElementById('docstrap-qapanels-suppress')) return;
      const style = doc.createElement('style');
      style.id = 'docstrap-qapanels-suppress';
      style.textContent = SUPPRESS_CHROME;
      doc.head.appendChild(style);
    } catch {
      // A page served from somewhere else. The reference still reads;
      // it just keeps its own chrome.
    }
  }
</script>

<div class="reference">
  {#if url}
    <iframe src={url} title="Rendered {path}" onload={onLoad}></iframe>
  {:else}
    <p class="note">
      No rendered page for <code>{path}</code>. The reference panel reads the built
      site, so it needs this project to have been built and served by
      <code>docstrap serve</code>.
    </p>
  {/if}
</div>

<style>
  .reference {
    height: 100%;
    min-height: 0;
    display: flex;
  }
  iframe {
    flex: 1 1 auto;
    width: 100%;
    height: 100%;
    border: 0;
    background: #fff;
  }
  .note {
    margin: auto;
    max-width: 34em;
    padding: 1em;
    opacity: 0.75;
    font-size: 0.9em;
  }
  @media (prefers-color-scheme: dark) {
    iframe {
      background: #14181d;
    }
  }
</style>
