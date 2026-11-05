// autosave.ts — the debounce behind the answer editor.
//
// The BEHAVIOUR implemented here is a shared autosave contract, written
// down once for the surfaces that use it (event-driven firing; no save
// buttons, transitions or spinners). Docstrap reproduces that contract
// rather than restating it as a decision of its own.
//
// What the contract specifies, and what this reproduces:
//
//   §1  Event-driven, not a clock. A form-level `oninput` is the
//       canonical trigger; a Svelte `$effect` on the tracked state is
//       the backstop for changes that fire no input event. Every trigger
//       resets a single debounce, and one save fires per typing burst.
//   §2  The pause threshold is a tuned constant, not part of the
//       contract. 800 ms, the contract's starting value.
//   §3  Ctrl/Cmd+S cancels the pending debounce and fires immediately.
//   §4  A binary indicator. Visible after a save completes; gone the
//       moment any input fires. Absence is the unsaved signal — no
//       spinner, no "Saving…" in between.
//
// Its sidecar-specific clauses do not transfer:
// docstrap's round trip is the tool route its declaration resolved, and
// the server behind it is `docstrap.answers`.
//
// This module holds only the timer. What is being saved, and the state
// the indicator reflects, belong to the component.

/** autosave §2 — a tuned constant, refinable, not a contract. */
export const AUTOSAVE_DEBOUNCE_MS = 800;

export interface Autosave<T> {
  /** A trigger fired: remember what to save and restart the debounce. */
  bump(payload: T): void;
  /** autosave §3 — cancel the pending debounce and save now. */
  flush(): void;
  /** Drop anything pending without saving it. */
  cancel(): void;
  /** Whether a save is waiting on the debounce. */
  pending(): boolean;
}

/**
 * One debounce, reset by every trigger, firing `save` once per burst.
 *
 * `payload` is captured at bump time rather than read at fire time, so a
 * selection that changes while a save is pending flushes the answer the
 * user actually typed rather than whichever one is on screen when the
 * timer expires.
 */
export function autosave<T>(
  save: (payload: T) => void,
  delayMs: number = AUTOSAVE_DEBOUNCE_MS
): Autosave<T> {
  let timer: number | null = null;
  let payload: T | null = null;

  function clear(): void {
    if (timer !== null) {
      window.clearTimeout(timer);
      timer = null;
    }
  }

  return {
    bump(next: T): void {
      payload = next;
      clear();
      timer = window.setTimeout(() => {
        timer = null;
        const held = payload;
        payload = null;
        if (held !== null) save(held);
      }, delayMs);
    },
    flush(): void {
      clear();
      const held = payload;
      payload = null;
      if (held !== null) save(held);
    },
    cancel(): void {
      clear();
      payload = null;
    },
    pending(): boolean {
      return timer !== null;
    },
  };
}
