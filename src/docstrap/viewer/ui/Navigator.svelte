<!--
  Navigator.svelte — the left drawer: the questions document on top, then
  every store, project and document the build published.

  Two different acts, and they move two different
  pieces of state. SELECTING a row shows its page in the middle region.
  PINNING a document makes it the questions document the right drawer
  answers. The pin control is always visible on every row that can be
  pinned — never revealed by hover, because a tablet has no hover — and
  it is sized for a finger.

  The tree's shape is the published site's: each node is a file-index
  entry under the section page that lists it (`site.ts`). Nothing here
  splits a path or names anything.
-->
<script lang="ts">
  import FileText from '@lucide/svelte/icons/file-text';
  import Folder from '@lucide/svelte/icons/folder';
  import House from '@lucide/svelte/icons/house';
  import Pin from '@lucide/svelte/icons/pin';
  import PinOff from '@lucide/svelte/icons/pin-off';
  import { TreeView, createTreeViewCollection } from '@skeletonlabs/skeleton-svelte';

  import type { SiteNode } from './site';
  import type { Pinned } from './types';

  let {
    tree,
    currentId,
    expanded,
    pinned,
    onselect,
    onshow,
    onexpand,
    onpin,
    onunpin,
  }: {
    tree: SiteNode;
    currentId: string | null;
    expanded: string[];
    pinned: Pinned | null;
    onselect: (node: SiteNode) => void;
    /** Show a page in the middle region without going through the tree. */
    onshow: (url: string) => void;
    onexpand: (ids: string[]) => void;
    onpin: (pin: Pinned) => void;
    onunpin: () => void;
  } = $props();

  const collection = $derived(
    createTreeViewCollection<SiteNode>({
      nodeToValue: (node) => node.id,
      nodeToString: (node) => node.name,
      rootNode: tree,
    })
  );

  function isPinned(node: SiteNode): boolean {
    return (
      pinned !== null &&
      node.pin !== null &&
      node.pin.project.slug === pinned.project.slug &&
      node.pin.document.docname === pinned.document.docname
    );
  }

  function select(details: { selectedNodes: SiteNode[] }): void {
    const node = details.selectedNodes[0];
    if (node) onselect(node);
  }

  /** The pin button sits inside a tree row; its click must not also
   *  select the row and move the middle region. */
  function pinClick(event: MouseEvent, node: SiteNode): void {
    event.stopPropagation();
    if (!node.pin) return;
    if (isPinned(node)) onunpin();
    else onpin(node.pin);
  }
</script>

<nav class="flex min-w-0 flex-col gap-3 p-3" aria-label="Projects and documents">
  <section class="card preset-tonal-primary p-3" aria-label="Questions document">
    <p class="text-xs font-semibold tracking-wide uppercase opacity-70">Questions document</p>
    {#if pinned}
      <div class="mt-1 flex items-start gap-2">
        <button
          type="button"
          class="min-h-9 min-w-0 flex-1 text-left font-semibold break-words hover:underline"
          title="Show it in the middle region"
          onclick={() => onshow(pinned!.document.url)}
        >
          {pinned.document.title}
          <span class="block text-xs font-normal opacity-70">{pinned.project.title}</span>
        </button>
        <button
          type="button"
          class="btn-icon preset-tonal size-9"
          title="Unpin — the drawer then answers nothing"
          aria-label="Unpin the questions document"
          onclick={onunpin}><PinOff class="size-4" /></button>
      </div>
    {:else}
      <p class="mt-1 text-sm opacity-80">
        Pin a document with <Pin class="inline size-4 align-text-bottom" /> to answer its questions
        on the right while you read anything in the middle.
      </p>
    {/if}
  </section>

  <TreeView
    {collection}
    selectedValue={currentId ? [currentId] : []}
    expandedValue={expanded}
    onSelectionChange={select}
    onExpandedChange={(details) => onexpand(details.expandedValue)}
  >
    <TreeView.Label class="sr-only">Projects and documents</TreeView.Label>
    <!-- Skeleton's root aligns its children to the start, so without a
         width the tree takes its widest title and the column scrolls
         sideways. Full width lets every title wrap inside its row. -->
    <TreeView.Tree class="w-full min-w-0">
      {#each collection.rootNode.children ?? [] as node, index (node.id)}
        {@render treeNode(node, [index])}
      {/each}
    </TreeView.Tree>
  </TreeView>
</nav>

{#snippet treeNode(node: SiteNode, indexPath: number[])}
  <TreeView.NodeProvider value={{ node, indexPath }}>
    {#if node.children}
      <TreeView.Branch>
        <!-- A title wraps under itself, after its icon; the chevron and
             the icon stay on its first line. -->
        <TreeView.BranchControl class="min-h-9 items-start">
          <TreeView.BranchIndicator class="flex h-6 shrink-0 items-center" />
          <TreeView.BranchText class="min-w-0 items-start">
            <span class="flex h-6 shrink-0 items-center"><Folder class="size-4" /></span>
            <span class="min-w-0 leading-6 break-words">{node.name}</span>
          </TreeView.BranchText>
        </TreeView.BranchControl>
        <TreeView.BranchContent>
          <TreeView.BranchIndentGuide />
          {#each node.children as child, childIndex (child.id)}
            {@render treeNode(child, [...indexPath, childIndex])}
          {/each}
        </TreeView.BranchContent>
      </TreeView.Branch>
    {:else}
      <!-- The first line is the pin button's height, so the icon, the
           title's first line and the pin share one centre and the rest of
           the title wraps below. -->
      <TreeView.Item class="min-h-9 items-start">
        <span class="flex h-9 shrink-0 items-center">
          {#if node.kind === 'site'}
            <House class="size-4" />
          {:else}
            <FileText class="size-4" />
          {/if}
        </span>
        <span class="min-w-0 flex-1 py-1.5 leading-6 break-words">{node.name}</span>
        {#if node.pin}
          <button
            type="button"
            tabindex="-1"
            class="btn-icon size-9 shrink-0 {isPinned(node) ? 'preset-filled-primary-500' : 'preset-tonal'}"
            title={isPinned(node)
              ? 'The questions document — unpin it'
              : 'Pin as the questions document'}
            aria-label={isPinned(node) ? `Unpin ${node.name}` : `Pin ${node.name}`}
            aria-pressed={isPinned(node)}
            onclick={(event) => pinClick(event, node)}><Pin class="size-4" /></button>
        {/if}
      </TreeView.Item>
    {/if}
  </TreeView.NodeProvider>
{/snippet}
