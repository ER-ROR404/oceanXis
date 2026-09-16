export interface ExplainerInput {
  region: string;
  date: string;
  depths: readonly (number | null)[];
  temps: readonly (number | null)[];
  sigma: readonly (number | null)[];
}

export interface Explanations {
  sentences: string[];
}

const Z = 1; // ±1σ model-uncertainty band. NOT 1.96: no calibrated 95% interval exists (phase-6 audit §calibration never performed).

function formatTemp(t: number): string {
  return t.toFixed(1);
}

/**
 * Deterministic, evidence-traceable "Explain this location" text.
 * NO LLM, no stochastic output. Every sentence derives from the actual profile
 * arrays (temperature, sigma) plus the canonical gradient. RULE 21: every claim
 * traceable to data.
 */
export function buildExplanation({ depths, temps, sigma }: ExplainerInput): Explanations {
  const sentences: string[] = [];

  // First non-null temperature = surface estimate.
  const sst = temps.find((t) => t !== null) ?? null;

  if (sst === null) {
    return {
      sentences: [
        'This location has no model output for the selected date.',
        'The reconstruction is not available for this grid cell.',
      ],
    };
  }

  sentences.push(
    `Surface temperature is reconstructed as ${formatTemp(sst)} deg C.`,
  );

  // Sharpest temperature drop across adjacent usable depths (thermocline).
  const pts = temps
    .map((t, i) => ({ depth: depths[i] ?? i, t }))
    .filter((x): x is { depth: number; t: number } => x.t !== null);

  const thermocline = findThermocline(pts);
  if (thermocline) {
    sentences.push(
      `A sharp thermocline is estimated near ${thermocline.depth} m, where temperature falls about ${formatTemp(thermocline.drop)} deg C.`,
    );
  } else {
    sentences.push('The water column is weakly stratified and nearly uniform.');
  }

  // ±1σ model-uncertainty estimate using the sigma array (not a calibrated interval).
  const sigmaNearSurface = sigma.find((s) => s !== null && s > 0);
  if (sigmaNearSurface !== null && sigmaNearSurface !== undefined) {
    sentences.push(
      `Model uncertainty estimate is ±${formatTemp(Z * sigmaNearSurface)} deg C near the surface (1 sigma).`,
    );
  } else {
    sentences.push('No uncertainty estimate is available for this cell.');
  }

  // Honesty line is rendered by the component footer, not duplicated in data.

  return { sentences };
}

interface ThermoclineFinding {
  depth: number;
  drop: number;
}

/** Detect the sharpest temperature drop between adjacent non-null depths. */
function findThermocline(pts: { depth: number; t: number }[]): ThermoclineFinding | null {
  if (pts.length < 2) return null;
  let best: ThermoclineFinding | null = null;
  for (let i = 1; i < pts.length; i++) {
    const drop = pts[i - 1].t - pts[i].t;
    if (drop >= 3.0 && (!best || drop > best.drop)) {
      best = { depth: pts[i - 1].depth, drop };
    }
  }
  return best;
}