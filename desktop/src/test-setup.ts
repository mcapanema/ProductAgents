import "@testing-library/jest-dom";

// antd's Table calls useBreakpoint(), which calls window.matchMedia; jsdom doesn't implement it.
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
});

// antd Table's scrollbar-size measurement calls getComputedStyle(elt, "::-webkit-scrollbar");
// jsdom implements the zero/one-arg form but throws "Not implemented" for the pseudo-element
// form. Delegate to the real implementation for the normal case (e.g. theme.ts's readVars())
// and return an empty CSSStyleDeclaration-like stub only for the pseudo-element case.
const realGetComputedStyle = window.getComputedStyle.bind(window);
window.getComputedStyle = ((elt: Element, pseudoElt?: string | null) =>
  pseudoElt ? ({ getPropertyValue: () => "" } as unknown as CSSStyleDeclaration) : realGetComputedStyle(elt)) as typeof window.getComputedStyle;

// antd Input.TextArea (via rc-textarea/@rc-component/resize-observer) constructs a
// ResizeObserver to track its own size; jsdom doesn't implement the API at all.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
Object.defineProperty(window, "ResizeObserver", {
  writable: true,
  value: ResizeObserverStub,
});

// Node 22+ ships its own experimental global `localStorage`, inert unless the process is
// started with --localstorage-file (accessing it just yields `undefined`, no working
// Storage). Vitest's jsdom bridge mirrors window properties onto globalThis but skips any
// key already present there unless it's on its own allowlist (localStorage isn't), so that
// inert Node global wins over jsdom's real implementation for both `localStorage` and
// `window.localStorage` (vitest aliases window to globalThis).
// ponytail: guarded on the inert-global symptom (no working setItem), ceiling = this Node
// (26.3.0) + vitest (2.1.9) combo; once a vitest upgrade adds localStorage to its mirror
// allowlist (or Node's global stops shadowing jsdom's), this check sees a working
// implementation and no-ops itself out — delete this block once that's confirmed.
if (typeof globalThis.localStorage?.setItem !== "function") {
  // Swap in a minimal in-memory Storage so code under test (e.g. Sidebar's collapse-state
  // persistence) can use localStorage normally.
  class MemoryStorage implements Storage {
    private store = new Map<string, string>();
    get length() {
      return this.store.size;
    }
    clear() {
      this.store.clear();
    }
    getItem(key: string) {
      return this.store.has(key) ? this.store.get(key)! : null;
    }
    key(index: number) {
      return Array.from(this.store.keys())[index] ?? null;
    }
    removeItem(key: string) {
      this.store.delete(key);
    }
    setItem(key: string, value: string) {
      this.store.set(key, String(value));
    }
  }
  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    value: new MemoryStorage(),
  });
}
