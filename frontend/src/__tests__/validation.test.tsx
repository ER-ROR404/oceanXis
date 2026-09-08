import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';

import { ArgoValidationPanel } from '../components/validation/ArgoValidationPanel';
import { CANONICAL_DEPTHS } from '../types/contracts';
import { parseArgoSummary } from '../utils/validation';
import argoJson from '../assets/validation/argo_validation_summary.json';

describe('parseArgoSummary (contract discipline)', () => {
  it('parses the committed asset into the typed summary', () => {
    const s = parseArgoSummary(argoJson);
    expect(s.model_version).toBe('hybrid_v1');
    expect(s.profiles.matched).toBe(285);
    expect(s.overall.rmse_c).toBeCloseTo(1.3533, 4);
  });

  it('returns depth entries in canonical order (0, 5, 10, ..., 1000)', () => {
    const s = parseArgoSummary(argoJson);
    expect(s.depthOrder).toEqual([...CANONICAL_DEPTHS]);
    expect(s.depth_wise['1000'].rmse_c).toBeCloseTo(0.1635, 4);
  });

  it('rejects a summary missing the overall block', () => {
    const { overall: _drop, ...rest } = argoJson as unknown as Record<string, unknown>;
    expect(() => parseArgoSummary(rest)).toThrow(/overall/i);
  });

  it('rejects profiles where matched + unmatched does not equal loaded', () => {
    const bad = {
      ...(argoJson as unknown as Record<string, unknown>),
      profiles: { ...(argoJson.profiles as object), loaded: 2, matched: 1, unmatched: 0 },
    };
    expect(() => parseArgoSummary(bad)).toThrow(/equal loaded/i);
  });

  it('rejects a non-string limitations field', () => {
    const bad = { ...(argoJson as unknown as Record<string, unknown>), limitations: 42 };
    expect(() => parseArgoSummary(bad)).toThrow(/limitations/i);
  });

  it('rejects a non-string source_work_log field', () => {
    const bad = { ...(argoJson as unknown as Record<string, unknown>), source_work_log: 42 };
    expect(() => parseArgoSummary(bad)).toThrow(/source_work_log/i);
  });

  it('rejects non-finite metrics', () => {
    const bad = JSON.parse(JSON.stringify(argoJson)) as typeof argoJson;
    bad.overall.rmse_c = NaN;
    expect(() => parseArgoSummary(bad)).toThrow(/finite/i);
  });
});

describe('ArgoValidationPanel', () => {
  it('renders the overall RMSE, bias and correlation readouts', () => {
    render(<ArgoValidationPanel />);
    expect(screen.getByText(/1\.35/)).toBeInTheDocument();
    expect(screen.getByText(/0\.61/)).toBeInTheDocument();
    expect(screen.getByText(/0\.990/)).toBeInTheDocument();
  });

  it('renders one depth row per canonical depth', () => {
    render(<ArgoValidationPanel />);
    // surface and deepest canonical depths present as row headers
    expect(screen.getByText('0 m')).toBeInTheDocument();
    expect(screen.getByText('1000 m')).toBeInTheDocument();
    const rows = screen.getAllByRole('row');
    // header + 15 depth rows
    expect(rows).toHaveLength(CANONICAL_DEPTHS.length + 1);
  });

  it('surfaces the honest sparse-coverage fact for depth 0 (n=25)', () => {
    render(<ArgoValidationPanel />);
    expect(screen.getByText('25')).toBeInTheDocument();
  });

  it('shows the ARGO profile match coverage', () => {
    render(<ArgoValidationPanel />);
    expect(screen.getByText(/285 of 291/)).toBeInTheDocument();
  });

  it('renders the limitations callout (thermocline warm bias, no hiding)', () => {
    render(<ArgoValidationPanel />);
    expect(screen.getByText(/warm bias up to \+2\.2/)).toBeInTheDocument();
    expect(screen.getByText(/thermocline/i)).toBeInTheDocument();
  });

  it('frames itself as aggregate, depth-wise validation', () => {
    render(<ArgoValidationPanel />);
    expect(screen.getByText(/aggregate, depth-wise/i)).toBeInTheDocument();
  });

  it('never claims realtime or forecasting', () => {
    render(<ArgoValidationPanel />);
    const text = screen.getByTestId('argo-validation-panel').textContent ?? '';
    expect(text.toLowerCase()).not.toMatch(/forecast/);
    expect(text.toLowerCase()).not.toMatch(/realtime|real-time/);
  });

  it('skips the row animation under prefers-reduced-motion but still renders readouts', () => {
    vi.stubGlobal(
      'matchMedia',
      vi.fn().mockReturnValue({ matches: true, addEventListener: vi.fn(), removeEventListener: vi.fn() }),
    );
    render(<ArgoValidationPanel />);
    expect(screen.getByText('ARGO validation')).toBeInTheDocument();
    expect(screen.getByText(/1\.35/)).toBeInTheDocument();
    expect(screen.getByText(/285 of 291/i)).toBeInTheDocument();
    vi.unstubAllGlobals();
  });
});