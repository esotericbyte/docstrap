// queryParam.svelte.ts — one query-string parameter of this page's own
// address, as a reactive value.
//
// Self-contained and depends on nothing but Svelte, so another Svelte
// app can lift the file as it is. It is the shape Svelte's own
// `svelte/reactivity/window` values have: `createSubscriber` wraps the
// browser's location events, and reading `current` inside an effect or
// a derived re-runs it when the address changes under the page — back
// and forward through history, or an edited hash. The libraries that do
// this more fully (sveltekit-search-params, runed's useSearchParams)
// are built on SvelteKit's router, which a plain Vite app does not have.
//
// It only reads. A page writing its own state into the address does it
// with `history.replaceState`, which fires no event, and that is right:
// a page recording where it is, is not the address changing under it.
import { createSubscriber } from 'svelte/reactivity';

export class QueryParam {
  readonly name: string;

  #subscribe = createSubscriber((update) => {
    window.addEventListener('popstate', update);
    window.addEventListener('hashchange', update);
    return () => {
      window.removeEventListener('popstate', update);
      window.removeEventListener('hashchange', update);
    };
  });

  constructor(name: string) {
    this.name = name;
  }

  /** The parameter's decoded value in the address now, or null. */
  get current(): string | null {
    this.#subscribe();
    return new URLSearchParams(window.location.search).get(this.name);
  }
}
