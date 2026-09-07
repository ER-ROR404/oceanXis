export type RGB = [number, number, number];

/** Clamp t to [0, 1]. */
function clamp01(t: number): number {
  if (t !== t) return 0; // NaN -> 0
  return Math.min(1, Math.max(0, t));
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

// Viridis anchor stops (approximation of the matplotlib viridis colormap),
// DESIGN.md: temperature layer = viridis.
const VIRIDIS: RGB[] = [
  [68, 1, 84],
  [72, 35, 116],
  [64, 67, 135],
  [52, 94, 141],
  [41, 120, 142],
  [32, 144, 140],
  [34, 167, 132],
  [68, 190, 112],
  [121, 209, 81],
  [189, 222, 38],
  [253, 231, 37],
];

/** Temperature layer color: viridis(t), t = value normalized to field range. */
export function viridis(t: number): RGB {
  const u = clamp01(t) * (VIRIDIS.length - 1);
  const i = Math.floor(u);
  const j = Math.min(i + 1, VIRIDIS.length - 1);
  const f = u - i;
  return [
    Math.round(lerp(VIRIDIS[i][0], VIRIDIS[j][0], f)),
    Math.round(lerp(VIRIDIS[i][1], VIRIDIS[j][1], f)),
    Math.round(lerp(VIRIDIS[i][2], VIRIDIS[j][2], f)),
  ];
}

// Uncertainty layer: yellow (low sigma) -> red (high sigma), DESIGN.md locked.
const CONFIDENCE_LO: RGB = [253, 224, 71]; // yellow-300
const CONFIDENCE_HI: RGB = [220, 38, 38]; // red-600

/** Uncertainty layer color: 0 = low sigma (yellow), 1 = high sigma (red). */
export function uncertaintyColor(t: number): RGB {
  const u = clamp01(t);
  return [
    Math.round(lerp(CONFIDENCE_LO[0], CONFIDENCE_HI[0], u)),
    Math.round(lerp(CONFIDENCE_LO[1], CONFIDENCE_HI[1], u)),
    Math.round(lerp(CONFIDENCE_LO[2], CONFIDENCE_HI[2], u)),
  ];
}

const MIN_MAX = 0.05; // avoid pure-white temp extremes; keep visual range stable.

/**
 * Domain for a temperature plane: min/max over non-null cells, expanded by a
 * small pad so the legend extremes stay readable.
 */
export function fieldDomain(values: (number | null)[][]): { min: number; max: number } {
  let min = Infinity;
  let max = -Infinity;
  for (const row of values) {
    for (const v of row) {
      if (v === null) continue;
      if (v < min) min = v;
      if (v > max) max = v;
    }
  }
  if (!Number.isFinite(min) || !Number.isFinite(max)) return { min: 0, max: 1 };
  if (max - min < 1e-6) return { min: min - 1, max: max + 1 };
  const pad = (max - min) * MIN_MAX;
  return { min: min - pad, max: max + pad };
}

/** Convert a [lat][lon] number|null grid into RGBA rows for a canvas. */
export function rasterize(
  values: (number | null)[][],
  sigma: (number | null)[][],
  layer: 'temperature' | 'uncertainty',
): Uint8ClampedArray | null {
  const h = values.length;
  const w = values[0]?.length ?? 0;
  if (h === 0 || w === 0) return null;
  const { min, max } = fieldDomain(values);
  const span = max - min;
  const out = new Uint8ClampedArray(h * w * 4);
  for (let r = 0; r < h; r++) {
    for (let c = 0; c < w; c++) {
      const v = values[r][c];
      const s = sigma[r][c];
      const idx = (r * w + c) * 4;
      if (v === null || s === null) {
        out[idx + 3] = 0; // transparent land
        continue;
      }
      const rgb =
        layer === 'temperature'
          ? viridis((v - min) / span)
          : uncertaintyColor(Math.min(1, s / 3.0));
      out[idx] = rgb[0];
      out[idx + 1] = rgb[1];
      out[idx + 2] = rgb[2];
      out[idx + 3] = 255;
    }
  }
  return out;
}

export function rgbString(rgb: RGB): string {
  return `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`;
}

/** Index of the grid center closest to target (mirrors backend snap). */
export function nearestIndex(values: number[], target: number): number {
  const i = values.reduce((best, v, i, arr) => (Math.abs(v - target) < Math.abs(arr[best] - target) ? i : best), 0);
  return i;
}