<!--
  Mark.svelte — one tri-state review mark: empty → ✓ → ✗.

  One of these is mounted after each qualifying sentence boundary and
  one at each h2/h3/h4. It owns its own state and reports every change
  back through `onmark`, so the submit bar reads a plain list of records
  rather than scraping data attributes off the DOM.

  It carries `.docstrap-chrome` because it is apparatus rather than
  document — that is what keeps it out of print and lets anything reason
  about tool chrome as a category.
-->
<script lang="ts">
  import type { MarkState } from './marks';

  const STATES: MarkState[] = ['', 'check', 'x'];
  const GLYPHS: Record<MarkState, string> = { '': '·', check: '✓', x: '✗' };

  let {
    kind,
    onmark,
  }: { kind: 'sentence' | 'section'; onmark: (state: MarkState) => void } = $props();

  let state = $state<MarkState>('');

  function advance(event: MouseEvent): void {
    event.stopPropagation();
    state = STATES[(STATES.indexOf(state) + 1) % STATES.length];
    onmark(state);
  }
</script>

<!-- Pointer-only, as this control has always been. Giving it a keyboard
     activation would be a behaviour change, not a conversion. -->
<!-- svelte-ignore a11y_click_events_have_key_events -->
<span
  class="docstrap-review-ctrl docstrap-chrome docstrap-review-{kind}"
  data-kind={kind}
  data-state={state}
  role="button"
  tabindex="0"
  title="Click: empty → ✓ → ✗. {kind} review mark."
  onclick={advance}>{GLYPHS[state]}</span>

<style>
  .docstrap-review-ctrl {
    display: inline-block;
    min-width: 1.1em;
    margin: 0 0.15em;
    padding: 0 0.2em;
    font-size: 0.85em;
    color: #999;
    cursor: pointer;
    border-radius: 0.2em;
    vertical-align: baseline;
    user-select: none;
  }
  .docstrap-review-ctrl:hover { background: #eef4fa; color: #333; }
  .docstrap-review-ctrl[data-state='check'] { color: #1b5e2b; background: #d4edda; }
  .docstrap-review-ctrl[data-state='x']     { color: #a02020; background: #f5d0d0; }

  .docstrap-review-ctrl[data-kind='section'] {
    margin-left: 0.5em;
    font-size: 0.7em;
    vertical-align: middle;
  }

  @media (prefers-color-scheme: dark) {
    .docstrap-review-ctrl       { color: #6b7681; }
    .docstrap-review-ctrl:hover { background: #263242; color: #e0e0e0; }
  }
</style>
