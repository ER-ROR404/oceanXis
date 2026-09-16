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

/**
 * Domain for a temperature plane: exact min/max over VALID (non-null)
 * ocean cells. No padding: the legend must show true data extremes (§11).
 * Null land/missing cells never enter the scale (§10).
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
  return { min, max };
}

export function rgbString(rgb: RGB): string {
  return `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`;
}

/** Index of the grid center closest to target (mirrors backend snap). */
export function nearestIndex(values: number[], target: number): number {
  const i = values.reduce((best, v, i, arr) => (Math.abs(v - target) < Math.abs(arr[best] - target) ? i : best), 0);
  return i;
}