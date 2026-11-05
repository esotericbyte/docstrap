<!--
  FacetMenu.svelte — the multi-select filter of one enum or symbol column.

  A button naming the column, and under it a checkbox per value with how
  many rows that value would give. Nothing chosen means no filter. Which
  options there are and what they count is `grid.ts` `facetsOf`; this
  only draws them and reports what is chosen.
-->
<script lang="ts">
  import ChevronDown from '@lucide/svelte/icons/chevron-down';

  import type { FacetOption } from './grid';
  import { NONE, type Column } from './table';

  let {
    column,
    options,
    chosen = $bindable(),
  }: { column: Column; options: FacetOption[]; chosen: string[] } = $props();

  let open = $state(false);
  let root: HTMLElement | undefined = $state();

  function toggle(value: string, on: boolean): void {
    chosen = on ? [...chosen, value] : chosen.filter((v) => v !== value);
  }

  function onPointerDown(event: PointerEvent): void {
    if (open && root && !root.contains(event.target as Node)) open = false;
  }

  function onKeyDown(event: KeyboardEvent): void {
    if (open && event.key === 'Escape') open = false;
  }
</script>

<svelte:document onpointerdown={onPointerDown} onkeydown={onKeyDown} />

<div class="facet" bind:this={root}>
  <button
    type="button"
    class="trigger"
    class:active={chosen.length > 0}
    aria-expanded={open}
    aria-label="{column.label} filter"
    onclick={() => (open = !open)}
  >
    <span>{column.label}</span>
    {#if chosen.length > 0}<span class="chosen">{chosen.length}</span>{/if}
    <ChevronDown size={14} aria-hidden="true" />
  </button>
  {#if open}
    <div class="menu" role="group" aria-label={column.label}>
      {#each options as option (option.value)}
        <label class:empty={option.count === 0}>
          <input
            type="checkbox"
            name={column.key}
            value={option.value}
            checked={chosen.includes(option.value)}
            onchange={(event) => toggle(option.value, event.currentTarget.checked)}
          />
          {#if column.symbols}<span class="symbol">{option.label}</span>{/if}
          <span class="value">{option.value === NONE ? '—' : option.value}</span>
          <span class="count">{option.count}</span>
        </label>
      {/each}
    </div>
  {/if}
</div>

<style>
  .facet {
    position: relative;
  }
  .trigger {
    display: inline-flex;
    align-items: center;
    gap: 0.35em;
    padding: 0.25em 0.6em;
    border: 1px solid var(--color-background-border, #c4c4c4);
    border-radius: 0.25em;
    background: var(--color-background-primary, #fff);
    color: var(--color-foreground-primary, #222);
    font: inherit;
    font-size: 0.85em;
    cursor: pointer;
  }
  .trigger:hover {
    background: var(--color-background-hover, #f2f2f2);
  }
  .trigger.active {
    border-color: var(--color-brand-primary, #4a7bb6);
  }
  .chosen {
    min-width: 1.3em;
    padding: 0 0.3em;
    border-radius: 0.65em;
    background: var(--color-brand-primary, #4a7bb6);
    color: var(--color-background-primary, #fff);
    font-size: 0.85em;
    text-align: center;
  }
  .menu {
    position: absolute;
    z-index: 20;
    top: calc(100% + 0.25em);
    left: 0;
    min-width: 12em;
    max-height: 22em;
    overflow-y: auto;
    padding: 0.3em 0;
    border: 1px solid var(--color-background-border, #c4c4c4);
    border-radius: 0.25em;
    background: var(--color-background-primary, #fff);
    box-shadow: 0 0.3em 1em rgba(0, 0, 0, 0.15);
  }
  label {
    display: flex;
    align-items: center;
    gap: 0.45em;
    padding: 0.2em 0.7em;
    font-size: 0.85em;
    white-space: nowrap;
    cursor: pointer;
  }
  label:hover {
    background: var(--color-background-hover, #f2f2f2);
  }
  label.empty {
    color: var(--color-foreground-muted, #888);
  }
  .value {
    flex: 1;
  }
  .count {
    color: var(--color-foreground-secondary, #666);
    font-variant-numeric: tabular-nums;
  }
</style>
