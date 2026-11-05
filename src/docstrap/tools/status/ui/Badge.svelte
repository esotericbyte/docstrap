<!--
  Badge.svelte — this document's docstrap status, beside its title.

  Rendered into the <h1> as its first child, so the status reads inline
  before the title text. It carries `.docstrap-chrome`
  because it is apparatus rather than document, which is what keeps it
  out of print and out of a shared copy of the page.

  The colour variants are selected by `data-status`, an attribute the
  component writes, rather than by a class name assembled at runtime.
  Both forms are on the element: the attribute so the scoped stylesheet
  can be matched statically against the markup, and the long-standing
  `docstrap-status-<state>` class so any stylesheet outside docstrap
  that already targets it keeps working.
-->
<script lang="ts">
  let { status, docId }: { status: string; docId: string } = $props();
</script>

<span
  class="docstrap-status-badge docstrap-chrome docstrap-status-{status}"
  data-status={status}
  data-doc-id={docId}
  title="docstrap status: {status}">{status}</span>

<style>
  /* Theme-agnostic so it works on top of Furo, Alabaster, or whichever
     HTML theme the layout picks. */
  .docstrap-status-badge {
    display: inline-block;
    margin-right: 0.6em;
    padding: 0.05em 0.55em;
    border-radius: 0.9em;
    font-size: 0.55em;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    vertical-align: middle;
    border: 1px solid transparent;
    background: #eee;
    color: #333;
  }
  [data-status='draft']    { background: #fff3cd; color: #6b5210; border-color: #eec14f; }
  [data-status='proposal'] { background: #cfe8ff; color: #1a4b7d; border-color: #6ea9d9; }
  [data-status='spec']     { background: #d4edda; color: #1b5e2b; border-color: #6bbf7c; }
  [data-status='plan']     { background: #ffe4c7; color: #7a3d10; border-color: #d68a45; }
  [data-status='active']   { background: #e2d5ff; color: #4a2680; border-color: #8b6ed4; }
  [data-status='archived'] { background: #e2e2e2; color: #555;    border-color: #a8a8a8; }
</style>
