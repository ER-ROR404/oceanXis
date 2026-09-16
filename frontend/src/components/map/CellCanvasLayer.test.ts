import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  CellCanvas,
  buildFieldGrid,
  type CanvasMapLike,
  type FieldGrid,
} from './CellCanvasLayer';
import { rgbString, viridis } from './colorScales';

const LATS = [10.0, 10.25, 10.5];
const LONS = [88.0, 88.25, 88.5];
const VALUES = [
  [29.1, 29.0, null],
  [28.8, null, 28.6],
  [28.5, 28.4, 28.3],
];
const SIGMA = [
  [0.4, 0.4, null],
  [0.5, null, 0.6],
  [0.4, 0.4, 0.3],
];

/** Fake map: 200 px per degree, data lands inside the 800×600 viewport. */
function fakeMap(): CanvasMapLike & { handlers: Record<string, (() => void)[]> } {
  const handlers: Record<string, (() => void)[]> = {};
  const overlayPane = document.createElement('div');
  return {
    handlers,
    on: vi.fn((ev: string, fn: () => void) => {
      (handlers[ev] ??= []).push(fn);
      return undefined as never;
    }),
    off: vi.fn((ev: string, fn: () => void) => {
      handlers[ev] = (handlers[ev] ?? []).filter((h) => h !== fn);
      return undefined as never;
    }),
    getSize: () => ({ x: 800, y: 600 }),
    getPanes: () => ({ overlayPane }),
    latLngToContainerPoint: ([lat, lon]: [number, number]) => ({ x: (lon - 87) * 200, y: (11 - lat) * 200 }),
    containerPointToLayerPoint: ([x, y]: [number, number]) => ({ x, y }),
  };
}

interface CapturedImage {
  width: number;
  height: number;
  data: Uint8ClampedArray;
}

function recordingCtx() {
  const rec = {
    images: [] as CapturedImage[],
    draws: [] as { sw: number; sh: number; destW: number; destH: number; x: number; y: number }[],
    smoothing: false,
    setTransform: vi.fn(),
    clearRect: vi.fn(),
    save: vi.fn(),
    restore: vi.fn(),
    drawImage: (_buffer: HTMLCanvasElement, ...rest: number[]) => {
      // offscreen → main blit: (buffer, sx, sy, sw, sh, dx, dy, dw, dh)
      if (rest.length === 8) {
        const [, , sw, sh, dx, dy, dw, dh] = rest;
        rec.draws.push({ sw, sh, destW: dw, destH: dh, x: dx, y: dy });
      }
    },
    createImageData: (w: number, h: number) => ({ width: w, height: h, data: new Uint8ClampedArray(w * h * 4) }),
    putImageData: (image: CapturedImage) => {
      rec.images.push(image);
    },
  };
  return rec;
}

function stubCanvasCtx(rec: ReturnType<typeof recordingCtx>) {
  const original = HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext = ((() => ({
    setTransform: rec.setTransform,
    clearRect: rec.clearRect,
    save: rec.save,
    restore: rec.restore,
    drawImage: rec.drawImage,
    createImageData: rec.createImageData,
    putImageData: rec.putImageData,
    get imageSmoothingEnabled() {
      return rec.smoothing;
    },
    set imageSmoothingEnabled(v: boolean) {
      rec.smoothing = v;
    },
  })) as unknown) as typeof original;
  return () => {
    HTMLCanvasElement.prototype.getContext = original;
  };
}

/** Alpha of the grid cell at grid row r (south→north) and column c. */
function alphaAt(rec: ReturnType<typeof recordingCtx>, r: number, c: number, nLat = LATS.length, nLon = LONS.length): number {
  const img = rec.images.at(-1);
  if (!img) return -1;
  const outRow = nLat - 1 - r; // buffer is north-up
  return img.data[(outRow * nLon + c) * 4 + 3];
}

/** Reconstruct the painted mask (grid-oriented, south→north) from the buffer. */
function paintedMask(rec: ReturnType<typeof recordingCtx>, nLat: number, nLon: number): boolean[][] {
  const img = rec.images.at(-1);
  if (!img) return [];
  return Array.from({ length: nLat }, (_, r) => {
    const outRow = nLat - 1 - r; // buffer is north-up
    return Array.from({ length: nLon }, (_, c) => img.data[(outRow * nLon + c) * 4 + 3] > 0);
  });
}

// Placed inside the fake map's 200 px/° viewport (lon 87–91, lat 8–11).
const COAST_LATS = [9.0, 9.25, 9.5, 9.75, 10.0, 10.25];
const COAST_LONS = [88.0, 88.25, 88.5, 88.75, 89.0, 89.25, 89.5, 89.75];

/**
 * A realistic 6×8 coastline: northern landmass, a coastal strip on the west and
 * an interior island — so the ocean mask is NOT a border-only rectangle.
 */
function coastlineGrid(): { grid: FieldGrid; ocean: boolean[][] } {
  const nLat = COAST_LATS.length;
  const nLon = COAST_LONS.length;
  const ocean = Array.from({ length: nLat }, () => Array<boolean>(nLon).fill(true));
  const landAt = (r: number, c: number) => {
    ocean[r][c] = false;
  };
  for (let c = 0; c < nLon; c++) landAt(nLat - 1, c); // northern landmass
  for (let c = 0; c < 4; c++) landAt(4, c);
  for (let c = 0; c < 2; c++) landAt(3, c);
  landAt(2, 0);
  landAt(2, 4); // interior island
  const colors = ocean.map((row) => row.map((isOcean) => (isOcean ? viridis(0.5) : null)));
  return { grid: { lats: COAST_LATS, lons: COAST_LONS, colors }, ocean };
}

describe('buildFieldGrid (real API grid → per-cell colors, no interpolation of data)', () => {
  it('maps valid ocean cells and nulls out land/missing cells', () => {
    const grid = buildFieldGrid(VALUES, SIGMA, LATS, LONS, 'temperature');
    expect(grid.colors).toHaveLength(3);
    expect(grid.colors[0][2]).toBeNull(); // null land
    expect(grid.colors[1][1]).toBeNull(); // null land
    expect(grid.colors[2][2]).not.toBeNull();
    expect(grid.lats).toBe(LATS);
    expect(grid.lons).toBe(LONS);
  });

  it('colors cells from valid ocean values only (viridis over the true domain)', () => {
    const grid = buildFieldGrid(VALUES, SIGMA, LATS, LONS, 'temperature');
    // True valid domain: min 28.3, max 29.1 → hottest cell (29.1) is viridis(1).
    expect(grid.colors[0][0]).toEqual(viridis(1));
    expect(rgbString(grid.colors[0][0]!)).toBe(rgbString(viridis(1)));
  });

  it('skips NaN and non-finite cells (never painted, never in scale)', () => {
    const grid = buildFieldGrid(
      [[29.0, null, Number.NaN, Number.POSITIVE_INFINITY]],
      [[0.4, null, 0.4, 0.4]],
      [10.0],
      [88.0, 88.25, 88.5, 88.75],
      'temperature',
    );
    expect(grid.colors[0].filter((c) => c !== null)).toHaveLength(1);
    expect(grid.colors[0][0]).toEqual(viridis(1));
  });

  it('renders uncertainty cells from the sigma plane', () => {
    const grid = buildFieldGrid(VALUES, SIGMA, LATS, LONS, 'uncertainty');
    expect(grid.colors[0][0]).not.toBeNull();
    expect(grid.colors[0][2]).toBeNull();
  });
});

describe('CellCanvas (projection-bound interpolated field, no image overlay)', () => {
  let restoreCtx: (() => void) | null = null;
  let rec = recordingCtx();

  beforeEach(() => {
    restoreCtx?.();
    rec = recordingCtx();
    restoreCtx = stubCanvasCtx(rec);
    document.body.innerHTML = '';
  });

  it('renders a 1 px-per-cell buffer with land fully transparent', () => {
    const map = fakeMap();
    const layer = new CellCanvas(buildFieldGrid(VALUES, SIGMA, LATS, LONS, 'temperature'), { opacity: 0.85 });
    layer.attach(map);
    // Grid painted into a 3×3 buffer.
    expect(rec.images).toHaveLength(1);
    expect(rec.images[0].width).toBe(3);
    expect(rec.images[0].height).toBe(3);
    // Land cells (0,2) and (1,1) are transparent; ocean cells are opaque-ish.
    expect(alphaAt(rec, 0, 2)).toBe(0);
    expect(alphaAt(rec, 1, 1)).toBe(0);
    expect(alphaAt(rec, 1, 0)).toBeGreaterThan(0);
    layer.detach();
  });

  it('blits the buffer in latitude strips with image smoothing (continuous field)', () => {
    const map = fakeMap();
    const layer = new CellCanvas(buildFieldGrid(VALUES, SIGMA, LATS, LONS, 'temperature'), {});
    layer.attach(map);
    expect(rec.draws.length).toBeGreaterThan(0);
    expect(rec.smoothing).toBe(true);
    for (const d of rec.draws) {
      expect(d.destW).toBeGreaterThan(0);
      expect(d.destH).toBeGreaterThan(0);
    }
    layer.detach();
  });

  it('culls strips outside the viewport', () => {
    const map = fakeMap();
    map.getSize = () => ({ x: 10, y: 10 });
    const layer = new CellCanvas(buildFieldGrid(VALUES, SIGMA, LATS, LONS, 'temperature'), {});
    layer.attach(map);
    expect(rec.draws).toHaveLength(0);
    layer.detach();
  });

  it('redraws on pan/zoom without rebuilding data and detaches cleanly', () => {
    const map = fakeMap();
    const layer = new CellCanvas(buildFieldGrid(VALUES, SIGMA, LATS, LONS, 'temperature'), {});
    layer.attach(map);
    const initial = rec.draws.length;
    expect(initial).toBeGreaterThan(0);
    map.handlers['move']?.forEach((h) => h());
    return new Promise<void>((resolve) => {
      window.setTimeout(() => {
        expect(rec.draws.length).toBeGreaterThan(initial);
        layer.detach();
        expect(map.getPanes().overlayPane.childElementCount).toBe(0);
        expect(map.handlers['move'] ?? []).toHaveLength(0);
        resolve();
      });
    });
  });

  it('setField swaps values without reattaching (depth/layer switches)', () => {
    const map = fakeMap();
    const layer = new CellCanvas(buildFieldGrid(VALUES, SIGMA, LATS, LONS, 'temperature'), {});
    layer.attach(map);
    const before = rec.images.length;
    layer.setField(buildFieldGrid(VALUES, SIGMA, LATS, LONS, 'uncertainty'));
    expect(rec.images.length).toBeGreaterThan(before);
    // Same canvas element reused.
    expect(map.getPanes().overlayPane.childElementCount).toBe(1);
    layer.detach();
  });

  it('clears honestly when the field is null (no data)', () => {
    const map = fakeMap();
    const layer = new CellCanvas(null, {});
    layer.attach(map);
    expect(rec.draws).toHaveLength(0);
    expect(rec.images).toHaveLength(0);
    layer.detach();
  });

  it('renders a coastline: land cells are skipped and the field is not a rectangle', () => {
    const map = fakeMap();
    const { grid, ocean } = coastlineGrid();
    const layer = new CellCanvas(grid, {});
    layer.attach(map);

    const nLat = COAST_LATS.length;
    const nLon = COAST_LONS.length;
    const painted = paintedMask(rec, nLat, nLon);

    // 1. Land cells are skipped exactly (transparent); ocean cells are painted.
    expect(painted).toEqual(ocean);
    expect(painted).toHaveLength(nLat);

    // 2. Not a full rectangle: there is land strictly inside the domain
    //    (a border-only mask would leave every interior cell painted), and the
    //    field is neither empty nor completely filled.
    const interiorLand = painted
      .slice(1, -1)
      .some((row) => row.slice(1, -1).some((isPainted) => !isPainted));
    expect(interiorLand).toBe(true);
    expect(painted.flat().some(Boolean)).toBe(true);
    expect(painted.flat().every(Boolean)).toBe(false);

    // 3. It actually got blitted to the map canvas (not just boxed up).
    expect(rec.draws.length).toBeGreaterThan(0);
    layer.detach();
  });
});
