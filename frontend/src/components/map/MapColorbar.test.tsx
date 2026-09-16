import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MapColorbar } from './MapColorbar';

const VALUES = [
  [28.5, 28.1],
  [27.9, null],
];
const SIGMA = [
  [0.4, 0.5],
  [0.5, null],
];

describe('MapColorbar', () => {
  it('shows a horizontal temperature scale with true min/max and °C', () => {
    render(<MapColorbar layer="temperature" values={VALUES} sigma={SIGMA} />);
    const bar = screen.getByTestId('map-legend');
    expect(bar.textContent).toMatch(/°C/);
    expect(bar.textContent).toMatch(/27\.9/);
    expect(bar.textContent).toMatch(/28\.5/);
  });

  it('switches to ±1σ units for the uncertainty layer', () => {
    render(<MapColorbar layer="uncertainty" values={VALUES} sigma={SIGMA} />);
    const bar = screen.getByTestId('map-legend');
    expect(bar.textContent).toMatch(/±1σ/);
    expect(bar.textContent).toMatch(/°C/);
  });
});
