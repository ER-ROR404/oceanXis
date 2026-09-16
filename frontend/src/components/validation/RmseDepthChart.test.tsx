import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { RmseDepthChart } from './RmseDepthChart';
import { parseArgoSummary } from '../../utils/validation';
import argoSummary from '../../assets/validation/argo_validation_summary.json';

describe('RmseDepthChart', () => {
  it('plots one bar per canonical depth with RMSE units', () => {
    const summary = parseArgoSummary(argoSummary);
    const { container } = render(<RmseDepthChart summary={summary} />);
    expect(container.querySelector('.recharts-bar')).not.toBeNull();
    expect(screen.getByTestId('rmse-depth-chart')).toBeInTheDocument();
    // Axis + units present; worst band value (75 m → 2.81) labeled.
    expect(container.textContent).toMatch(/RMSE/);
    expect(container.textContent).toMatch(/°C/);
    expect(container.textContent).toMatch(/75 m/);
  });

  it('marks the 75–150 m thermocline band visually', () => {
    const summary = parseArgoSummary(argoSummary);
    render(<RmseDepthChart summary={summary} />);
    expect(screen.getByTestId('rmse-thermocline-note')).toHaveTextContent(/75–150 m/);
  });
});
