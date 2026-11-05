// The viewer's left drawer — `ui/navigatorPane.ts` under Node: how wide it
// opens, what a resize remembers, and what its tab does.
//
// The dragging and collapsing themselves are Zag's splitter; what is held
// here is the shell's own part of it. Run by `npm test` in
// packages/docstrap, and by `tests/test_viewer.py`, which is how `pytest`
// reaches it.
import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  DEFAULT_WIDTH,
  MAX_WIDTH,
  MIN_WIDTH,
  NAV_PANEL,
  PANELS,
  STORAGE_KEY,
  TRIGGER,
  readWidth,
  toggle,
  writeWidth,
  type Collapsible,
} from '../../src/docstrap/viewer/ui/navigatorPane.ts';

function memory(initial: Record<string, string> = {}) {
  const items = new Map(Object.entries(initial));
  return {
    items,
    getItem: (key: string) => items.get(key) ?? null,
    setItem: (key: string, value: string) => void items.set(key, value),
  };
}

const refusing = {
  getItem(): string | null {
    throw new Error('SecurityError');
  },
  setItem(): void {
    throw new Error('QuotaExceededError');
  },
};

/** A drawer that records what the tab asked of it. */
function drawer(collapsed: boolean): Collapsible & { calls: string[] } {
  const calls: string[] = [];
  return {
    calls,
    isPanelCollapsed: (id) => id === NAV_PANEL && collapsed,
    collapsePanel: (id) => {
      calls.push(`collapse ${id}`);
      collapsed = true;
    },
    expandPanel: (id) => {
      calls.push(`expand ${id}`);
      collapsed = false;
    },
  };
}

test('the drawer opens wider than the fixed column it replaced', () => {
  // The column was minmax(18rem, 22rem).
  assert.equal(DEFAULT_WIDTH, '26rem');
  assert.equal(readWidth(null), DEFAULT_WIDTH);
  assert.equal(readWidth(memory()), DEFAULT_WIDTH);
});

test('the drawer is a collapsible panel with bounds, resized by one trigger', () => {
  const [nav, rest] = PANELS;
  assert.equal(nav.id, NAV_PANEL);
  assert.equal(nav.collapsible, true);
  assert.equal(nav.collapsedSize, 0);
  assert.equal(nav.minSize, MIN_WIDTH);
  assert.equal(nav.maxSize, MAX_WIDTH);
  assert.equal(nav.resizeBehavior, 'preserve-pixel-size');
  assert.equal(TRIGGER, `${NAV_PANEL}:${rest.id}`);
});

test('a resize is remembered in pixels and opens the drawer at that width', () => {
  const storage = memory();
  writeWidth(storage, 25, 1600);
  assert.equal(storage.items.get(STORAGE_KEY), '400');
  assert.equal(readWidth(storage), '400px');
  writeWidth(storage, 37.5, 1600);
  assert.equal(readWidth(storage), '600px');
});

test('a collapsed drawer or an unmeasured window is never remembered as a width', () => {
  const storage = memory({ [STORAGE_KEY]: '400' });
  writeWidth(storage, 0, 1600);
  writeWidth(storage, 25, 0);
  assert.equal(storage.items.get(STORAGE_KEY), '400');
});

test('a remembered value that is not a width falls back to the default', () => {
  for (const junk of ['', 'wide', '-20', '0', 'NaN', 'Infinity']) {
    assert.equal(readWidth(memory({ [STORAGE_KEY]: junk })), DEFAULT_WIDTH, junk);
  }
});

test('a browser that refuses storage still gets a drawer', () => {
  assert.equal(readWidth(refusing), DEFAULT_WIDTH);
  assert.doesNotThrow(() => writeWidth(refusing, 25, 1600));
});

test('the tab closes an open drawer and opens a closed one', () => {
  const open = drawer(false);
  toggle(open);
  assert.deepEqual(open.calls, [`collapse ${NAV_PANEL}`]);
  toggle(open);
  assert.deepEqual(open.calls, [`collapse ${NAV_PANEL}`, `expand ${NAV_PANEL}`]);

  const closed = drawer(true);
  toggle(closed);
  assert.deepEqual(closed.calls, [`expand ${NAV_PANEL}`]);
});
