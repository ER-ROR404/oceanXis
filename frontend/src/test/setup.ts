import '@testing-library/jest-dom';

// Polyfill window.matchMedia if missing in jsdom
if (typeof window !== 'undefined' && !window.matchMedia) {
  Object.defineProperty(window, 'matchMedia', {
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
}

// Polyfill ResizeObserver (recharts ResponsiveContainer requires it in jsdom).
// Fire the callback synchronously with a fixed viewport so charts render.
if (typeof globalThis !== 'undefined' && !('ResizeObserver' in globalThis)) {
  class ResizeObserverMock {
    private cb: (entries: { contentRect: { width: number; height: number } }[]) => void;
    constructor(cb: (entries: { contentRect: { width: number; height: number } }[]) => void) {
      this.cb = cb;
    }
    observe() {
      this.cb([{ contentRect: { width: 800, height: 400 } }]);
    }
    unobserve() {}
    disconnect() {}
  }
  (globalThis as Record<string, unknown>).ResizeObserver = ResizeObserverMock;
}
