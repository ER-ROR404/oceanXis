import { fieldDomain, uncertaintyColor, viridis, type RGB } from './colorScales';

export type CellLayerMode = 'temperature' | 'uncertainty';

/**
 * One sampled field on the real 0.25° grid, ready to render.
 *
 * ``colors[latIndex][lonIndex]`` is the cell color, or ``null`` where the API
 * reported land / no data. Null cells stay transparent so the basemap
 * coastline shows through — the field hugs the real coast instead of painting
 * a rectangle.
 */
export interface FieldGrid {
  lats: number[];
  lons: number[];
  colors: (RGB | null)[][];
}

/** Minimal map surface the canvas layer needs (satisfied by Leaflet maps). */
export interface CanvasMapLike {
  on(ev: string, fn: () => void): unknown;
  off(ev: string, fn: () => void): unknown;
  getSize(): { x: number; y: number };
  getPanes(): { overlayPane: HTMLElement };
  latLngToContainerPoint(latlng: [number, number]): { x: number; y: number };
  containerPointToLayerPoint(p: [number, number]): { x: number; y: number };
}

const scheduleFrame = (fn: () => void): number => window.setTimeout(fn, 0) as unknown as number;

const cancelFrame = (id: number): void => window.clearTimeout(id);

/** Half a grid step, so a cell's true bounds can be derived from its center. */
function halfStep(axis: number[]): number {
  if (axis.length >= 2) {
    const step = Math.abs(axis[1] - axis[0]);
    if (Number.isFinite(step) && step > 0) return step / 2;
  }
  return 0.125; // 0.25° grid fallback; never invents cell positions.
}

const isFiniteNumber = (x: number | null): x is number => x !== null && Number.isFinite(x);

/** Number of grid rows drawn per interpolation strip (bounds Mercator warp). */
const STRIP_ROWS = 6;

/** Cells over which the field fades at the domain edge (1 = hard edge). */
const EDGE_FEATHER_CELLS = 1.25;

/**
 * Real API grid → per-cell colors. One entry per cell; null/NaN/non-finite
 * cells (land, missing data) map to ``null`` so they are never painted and
 * never enter the color domain.
 */
export function buildFieldGrid(
  values: (number | null)[][],
  sigma: (number | null)[][],
  latitudes: number[],
  longitudes: number[],
  mode: CellLayerMode,
): FieldGrid {
  // Uncertainty uses the fixed σ scale; temperature normalizes over the true
  // valid domain (fieldDomain already excludes nulls).
  const { min, max } = mode === 'temperature' ? fieldDomain(values) : { min: 0, max: 1 };
  const span = max - min > 1e-9 ? max - min : 1;
  const colors: (RGB | null)[][] = values.map((row, r) =>
    row.map((v, c) => {
      const s = sigma[r]?.[c] ?? null;
      if (!isFiniteNumber(v) || !isFiniteNumber(s)) return null;
      const t = mode === 'temperature' ? (v - min) / span : Math.min(1, s / 3.0);
      return mode === 'temperature' ? viridis(t) : uncertaintyColor(t);
    }),
  );
  return { lats: latitudes, lons: longitudes, colors };
}

/**
 * Projection-bound field renderer.
 *
 * The 0.25° grid is painted into a 1 px-per-cell offscreen buffer (null cells
 * transparent) and then blitted onto the map with image smoothing. Cells are
 * therefore continuously interpolated — a smooth field, not a grid of hard
 * squares — while every cell still lands at its true geographic position.
 * Rows are blitted in latitude strips so the non-linear Web-Mercator vertical
 * mapping stays accurate; the horizontal axis is linear in longitude, so the
 * strip spans the domain exactly.
 *
 * This is not an <img> or an L.imageOverlay: the canvas is owned by the layer,
 * sized to the viewport and driven entirely by the live projection.
 */
export class CellCanvas {
  private canvas: HTMLCanvasElement | null = null;
  private map: CanvasMapLike | null = null;
  private rafId = 0;
  private opacity: number;

  constructor(
    private field: FieldGrid | null,
    options: { opacity?: number } = {},
  ) {
    this.opacity = options.opacity ?? 0.85;
  }

  attach(map: CanvasMapLike): void {
    if (this.map) this.detach();
    this.map = map;
    const canvas = document.createElement('canvas');
    canvas.style.position = 'absolute';
    canvas.style.pointerEvents = 'none';
    canvas.style.opacity = String(this.opacity);
    canvas.setAttribute('aria-hidden', 'true');
    map.getPanes().overlayPane.appendChild(canvas);
    this.canvas = canvas;
    for (const ev of ['move', 'zoom', 'viewreset', 'resize']) map.on(ev, this.scheduleRedraw);
    this.redraw();
  }

  detach(): void {
    if (this.rafId) {
      cancelFrame(this.rafId);
      this.rafId = 0;
    }
    if (this.map) {
      for (const ev of ['move', 'zoom', 'viewreset', 'resize']) this.map.off(ev, this.scheduleRedraw);
    }
    this.canvas?.remove();
    this.canvas = null;
    this.map = null;
  }

  /** Swap the field (date/depth/layer switches) without reattaching. */
  setField(field: FieldGrid | null): void {
    this.field = field;
    this.redraw();
  }

  setOpacity(opacity: number): void {
    this.opacity = opacity;
    if (this.canvas) this.canvas.style.opacity = String(opacity);
  }

  private scheduleRedraw = (): void => {
    if (this.rafId) cancelFrame(this.rafId);
    this.rafId = scheduleFrame(() => {
      this.rafId = 0;
      this.redraw();
    });
  };

  /**
   * Paint the grid into a 1 px-per-cell buffer, north-up (the API grid runs
   * south→north). Alpha falls off over the last cells at the domain edge so
   * the coverage boundary fades into the basemap rather than ending on a line.
   */
  private buildGridBuffer(): { buffer: HTMLCanvasElement; nLat: number; nLon: number } | null {
    const field = this.field;
    if (!field) return null;
    const nLat = field.lats.length;
    const nLon = field.lons.length;
    if (nLat === 0 || nLon === 0) return null;

    const buffer = document.createElement('canvas');
    buffer.width = nLon;
    buffer.height = nLat;
    const ctx = buffer.getContext('2d');
    if (!ctx || typeof ctx.createImageData !== 'function' || typeof ctx.putImageData !== 'function') {
      return null;
    }
    const image = ctx.createImageData(nLon, nLat);
    for (let r = 0; r < nLat; r++) {
      const outRow = nLat - 1 - r; // north-up buffer
      for (let c = 0; c < nLon; c++) {
        const color = field.colors[r]?.[c] ?? null;
        const idx = (outRow * nLon + c) * 4;
        if (!color) {
          image.data[idx + 3] = 0; // land / missing → fully transparent
          continue;
        }
        const edgeDistance = Math.min(r, c, nLat - 1 - r, nLon - 1 - c);
        const alpha = Math.min(1, (edgeDistance + 0.5) / EDGE_FEATHER_CELLS);
        image.data[idx] = color[0];
        image.data[idx + 1] = color[1];
        image.data[idx + 2] = color[2];
        image.data[idx + 3] = Math.round(255 * alpha);
      }
    }
    ctx.putImageData(image, 0, 0);
    return { buffer, nLat, nLon };
  }

  private redraw(): void {
    const map = this.map;
    const canvas = this.canvas;
    if (!map || !canvas) return;
    const size = map.getSize();
    const dpr = typeof window !== 'undefined' && window.devicePixelRatio ? window.devicePixelRatio : 1;
    canvas.width = Math.max(1, Math.round(size.x * dpr));
    canvas.height = Math.max(1, Math.round(size.y * dpr));
    canvas.style.width = `${size.x}px`;
    canvas.style.height = `${size.y}px`;
    const origin = map.containerPointToLayerPoint([0, 0]);
    canvas.style.left = `${origin.x}px`;
    canvas.style.top = `${origin.y}px`;
    const ctx = canvas.getContext('2d');
    // Minimal test contexts provide a stub without drawing methods.
    if (!ctx || typeof ctx.drawImage !== 'function' || typeof ctx.setTransform !== 'function') return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, size.x, size.y);

    const grid = this.buildGridBuffer();
    if (!grid) return;
    const { buffer, nLat, nLon } = grid;
    const lats = this.field!.lats;
    const lons = this.field!.lons;
    const half = halfStep(lats);
    const latMid = lats[Math.floor(lats.length / 2)] ?? lats[0];

    // Horizontal extent: longitude is linear in Web Mercator, so one projection
    // is exact for every row.
    const west = map.latLngToContainerPoint([latMid, lons[0]]).x;
    const east = map.latLngToContainerPoint([latMid, lons[nLon - 1]]).x;
    const width = east - west;
    if (!Number.isFinite(width) || width === 0) return;

    if ('imageSmoothingEnabled' in ctx) ctx.imageSmoothingEnabled = true;

    for (let start = 0; start < nLat; start += STRIP_ROWS) {
      const rows = Math.min(STRIP_ROWS, nLat - start);
      // Buffer rows are north-up; grid rows run south→north (ascending).
      const gridTop = nLat - 1 - start; // northernmost grid row in strip
      const gridBottom = nLat - 1 - (start + rows - 1); // southernmost
      const northEdge = lats[gridTop] + half;
      const southEdge = lats[gridBottom] - half;
      const yTop = map.latLngToContainerPoint([northEdge, latMid]).y;
      const yBottom = map.latLngToContainerPoint([southEdge, latMid]).y;
      if (yBottom < 0 || yTop > size.y) continue; // culled strip
      ctx.drawImage(buffer, 0, start, nLon, rows, west, yTop, width, yBottom - yTop);
    }
  }
}
