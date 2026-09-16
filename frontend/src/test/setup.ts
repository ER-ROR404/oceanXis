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

// jsdom can't render canvas pixels. Provide a minimal working 2D context so
// renderDataUrl's real drawing path executes in tests; the pixel contents are
// irrelevant, only the data-URL round trip matters.
if (typeof HTMLCanvasElement !== 'undefined') {
  Object.defineProperty(HTMLCanvasElement.prototype, 'getContext', {
    writable: true,
    configurable: true,
    value: () => ({
      createImageData: (w: number, h: number) => ({ data: new Uint8ClampedArray(w * h * 4) }),
      putImageData: () => {},
    }),
  });
  // jsdom's toDataURL logs "Not implemented" and returns null without the
  // native canvas package; stub a deterministic data URL instead.
  Object.defineProperty(HTMLCanvasElement.prototype, 'toDataURL', {
    writable: true,
    configurable: true,
    value: () => 'data:image/png;base64,',
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
