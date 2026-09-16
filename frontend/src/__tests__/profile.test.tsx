import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';

import { buildExplanation } from '../utils/explain';
import { ExplainLocation } from '../components/profile/ExplainLocation';
import { buildBandData, ProfileChart } from '../components/profile/ProfileChart';
import { CANONICAL_DEPTHS } from '../types/contracts';

// A representative Bay of Bengal summer profile: warm isothermal surface,
// sharp thermocline ~60-80 m, cooling to ~11 °C by 300 m.
const PROFILE = {
  region: 'Bay of Bengal' as const,
  date: '2023-06-15',
  depths: CANONICAL_DEPTHS,
  temps: [29.5, 29.3, 29.1, 29.0, 28.7, 27.9, 24.8, 18.2, 14.6, 12.9, 11.4, 9.8, 8.6, 7.4, 6.1] as (
    | number
    | null
  )[],
  sigma: [0.35, 0.36, 0.37, 0.4, 0.55, 0.9, 1.35, 1.6, 1.65, 1.6, 1.5, 1.3, 1.1, 0.95, 0.8] as (
    | number
    | null
  )[],
};

describe('buildExplanation', () => {
  it('reports reconstructed surface temperature with one decimal', () => {
    const r = buildExplanation(PROFILE);
    expect(r.sentences.join(' ')).toContain('29.5');
  });

  it('flags a sharp thermocline with its depth', () => {
    const r = buildExplanation(PROFILE);
    expect(r.sentences.join(' ')).toMatch(/thermocline/i);
  });

  it('states the model uncertainty estimate (±1σ) instead of a calibrated 95% band', () => {
    const r = buildExplanation(PROFILE);
    const text = r.sentences.join(' ');
    expect(text).toMatch(/±/);
    expect(text).toMatch(/sigma|standard deviation/i);
    expect(text).toMatch(/model uncertainty/i);
    expect(text).not.toMatch(/95%/);
  });

  it('falls back honestly when the column has no data', () => {
    const r = buildExplanation({
      ...PROFILE,
      temps: CANONICAL_DEPTHS.map(() => null),
      sigma: CANONICAL_DEPTHS.map(() => null),
    });
    expect(r.sentences.join(' ')).toMatch(/no model output/i);
  });

  it('detects weak stratification for a uniform column', () => {
    const r = buildExplanation({
      ...PROFILE,
      temps: CANONICAL_DEPTHS.map(() => 28.0),
    });
    expect(r.sentences.join(' ')).toMatch(/weakly stratified/i);
  });
});

describe('ExplainLocation', () => {
  it('renders the deterministic sentences and the honesty line', () => {
    render(<ExplainLocation input={PROFILE} />);
    expect(screen.getByText(/Reconstruction from a statistical model/i)).toBeInTheDocument();
    expect(screen.getByText(/not an observation/i)).toBeInTheDocument();
  });
});

describe('buildBandData', () => {
  it('produces one banded point per canonical depth with ±1σ bounds', () => {
    const band = buildBandData(PROFILE.depths, PROFILE.temps, PROFILE.sigma);
    expect(band).toHaveLength(CANONICAL_DEPTHS.length);
    expect(band[0]).not.toBeNull();
    const first = band[0]!;
    // 29.5 - 1.0*0.35 = 29.15, 29.5 + 1.0*0.35 = 29.85 (±1σ, not ±1.96σ)
    expect(first.lo).toBeCloseTo(29.15, 2);
    expect(first.hi).toBeCloseTo(29.85, 2);
    expect(first.lo).toBeLessThan(first.temp);
    expect(first.hi).toBeGreaterThan(first.temp);
  });

  it('skips null cells instead of fabricating a band', () => {
    const band = buildBandData(
      CANONICAL_DEPTHS,
      [null, ...PROFILE.temps.slice(1)],
      PROFILE.sigma,
    );
    expect(band[0]).toBeNull();
    expect(band[1]).not.toBeNull();
  });

  it('orders depth ascending for the chart (surface at top)', () => {
    const band = buildBandData(PROFILE.depths, PROFILE.temps, PROFILE.sigma);
    const depths = band.filter(Boolean).map((p) => p!.depth);
    expect(depths[0]).toBeLessThan(depths[depths.length - 1]);
  });
});

type CanonicalDepth = (typeof CANONICAL_DEPTHS)[number];

/** Pixel y coordinate of every model-level marker, in data order. */
function markerY(container: HTMLElement): number[] {
  return Array.from(container.querySelectorAll('.recharts-line-dots circle')).map((c) =>
    Number(c.getAttribute('cy')),
  );
}

describe('ProfileChart depth mapping', () => {
  it('renders all 15 model levels as markers', () => {
    const { container } = render(
      <div style={{ width: 600, height: 400 }}>
        <ProfileChart depths={PROFILE.depths} temps={PROFILE.temps} sigma={PROFILE.sigma} />
      </div>,
    );
    expect(markerY(container)).toHaveLength(CANONICAL_DEPTHS.length);
  });

  it('places each marker at its real depth, not at its array index', () => {
    const { container } = render(
      <div style={{ width: 600, height: 400 }}>
        <ProfileChart depths={PROFILE.depths} temps={PROFILE.temps} sigma={PROFILE.sigma} />
      </div>,
    );
    const ys = markerY(container);
    const at = (depth: CanonicalDepth) => ys[CANONICAL_DEPTHS.indexOf(depth)];
    const span = at(1000) - at(0);
    expect(span).toBeGreaterThan(100);
    // Every level sits at depth/1000 of the 0-1000 m span (proportional, real
    // depth coordinates). An index-based axis would put 1000 m at index 14/15.
    CANONICAL_DEPTHS.forEach((depth) => {
      expect((at(depth) - at(0)) / span).toBeCloseTo(depth / 1000, 2);
    });
  });

  it('inverts the depth axis so the surface is at the top', () => {
    const { container } = render(
      <div style={{ width: 600, height: 400 }}>
        <ProfileChart depths={PROFILE.depths} temps={PROFILE.temps} sigma={PROFILE.sigma} />
      </div>,
    );
    const ys = markerY(container);
    const at = (depth: CanonicalDepth) => ys[CANONICAL_DEPTHS.indexOf(depth)];
    expect(at(0)).toBeLessThan(at(5));
    expect(at(1000)).toBeGreaterThan(at(200));
    // 0 m at the top, 1000 m at the bottom of the plot area.
    const surface = container.querySelector('.recharts-surface');
    expect(at(0)).toBeLessThan(Number(surface?.getAttribute('height')) / 2);
  });

  it('maps temperature to x, so the curve follows the real profile', () => {
    const { container } = render(
      <div style={{ width: 600, height: 400 }}>
        <ProfileChart depths={PROFILE.depths} temps={PROFILE.temps} sigma={PROFILE.sigma} />
      </div>,
    );
    const xs = Array.from(container.querySelectorAll('.recharts-line-dots circle')).map((c) =>
      Number(c.getAttribute('cx')),
    );
    // Warmest level (29.5 @ 0 m) right of the coldest (6.1 @ 1000 m).
    expect(xs[0]).toBeGreaterThan(xs[xs.length - 1]);
  });
});

describe('ProfileChart', () => {
  it('renders a recharts surface with temperature axis label', () => {
    const { container } = render(
      <div style={{ width: 600, height: 400 }}>
        <ProfileChart
          depths={PROFILE.depths}
          temps={PROFILE.temps}
          sigma={PROFILE.sigma}
        />
      </div>,
    );
    expect(container.querySelector('.recharts-surface')).not.toBeNull();
    expect(screen.getAllByText(/temperature/i).length).toBeGreaterThan(0);
  });

  it('labels the chart as a model uncertainty band (±1σ), never 95%', () => {
    const { container } = render(
      <div style={{ width: 600, height: 400 }}>
        <ProfileChart
          depths={PROFILE.depths}
          temps={PROFILE.temps}
          sigma={PROFILE.sigma}
        />
      </div>,
    );
    expect(
      container.querySelector('[aria-label="Temperature profile with model uncertainty band (±1σ)"]'),
    ).not.toBeNull();
    expect(screen.getByTestId('uncertainty-caption')).toHaveTextContent(/model uncertainty/i);
    expect(screen.getByTestId('uncertainty-caption')).not.toHaveTextContent(/95/);
  });

  it('labels the smooth curve as visual interpolation between model levels', () => {
    render(
      <div style={{ width: 600, height: 400 }}>
        <ProfileChart
          depths={PROFILE.depths}
          temps={PROFILE.temps}
          sigma={PROFILE.sigma}
        />
      </div>,
    );
    expect(screen.getByTestId('interpolation-note')).toHaveTextContent(/visual interpolation/i);
    expect(screen.getByTestId('interpolation-note')).toHaveTextContent(/15 model levels/i);
  });
});