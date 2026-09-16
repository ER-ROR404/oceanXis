import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DepthColumn } from './DepthColumn';

const depths = [0, 5, 10, 20, 30, 50, 75, 100, 125, 150, 200, 300, 500, 700, 1000];
const temps = [28.9, 28.8, 28.6, 28.2, 27.9, 27.2, 25.1, 22.4, 20.1, 18.3, 15.2, 12.1, 9.4, 8.1, 6.2];
const sigma = [0.4, 0.4, 0.4, 0.5, 0.5, 0.7, 1.1, 1.0, 0.9, 0.8, 0.5, 0.3, 0.2, 0.2, 0.2];

describe('DepthColumn (hero depth output, 15 real levels)', () => {
  it('renders all 15 real depth planes with real temperatures and ±1σ', () => {
    render(<DepthColumn depths={depths} temps={temps} sigma={sigma} />);
    expect(screen.getByTestId('depth-column')).toBeInTheDocument();
    for (const d of depths) {
      expect(screen.getByTestId(`depth-plane-${d}`)).toBeInTheDocument();
    }
    expect(screen.getByTestId('depth-plane-100')).toHaveTextContent('22.4');
    expect(screen.getByTestId('depth-plane-100')).toHaveTextContent('±');
  });

  it('never claims 95% confidence (uncalibrated ±1σ only)', () => {
    render(<DepthColumn depths={depths} temps={temps} sigma={sigma} />);
    expect(screen.getByTestId('depth-column').textContent).not.toMatch(/95%/);
    expect(screen.getByTestId('depth-column').textContent).toMatch(/±1σ/);
  });

  it('is honest about missing cells (no fabricated band)', () => {
    render(
      <DepthColumn
        depths={depths}
        temps={temps.map((t, i) => (i === 0 ? null : t))}
        sigma={sigma}
      />,
    );
    expect(screen.getByTestId('depth-plane-0')).toHaveTextContent(/no data/i);
  });
});
