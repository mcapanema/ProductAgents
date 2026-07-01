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
