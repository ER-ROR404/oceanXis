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

  it('includes a 95% uncertainty band statement', () => {
    const r = buildExplanation(PROFILE);
    expect(r.sentences.join(' ')).toMatch(/95%/);
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
  it('produces one banded point per canonical depth with 95% bounds', () => {
    const band = buildBandData(PROFILE.depths, PROFILE.temps, PROFILE.sigma);
    expect(band).toHaveLength(CANONICAL_DEPTHS.length);
    expect(band[0]).not.toBeNull();
    const first = band[0]!;
    // 29.5 - 1.96*0.35 = 28.81..., 29.5 + 1.96*0.35 = 30.18...
    expect(first.lo).toBeCloseTo(28.81, 1);
    expect(first.hi).toBeCloseTo(30.19, 1);
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
});