import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';

import { InputProvenancePanel } from '../components/science/InputProvenancePanel';
import { ModelFlowExplainer } from '../components/science/ModelFlowExplainer';

/** Demo spec Screen 5: "What goes into OceanEmbed?" — the 7 LOCKED channels. */
describe('InputProvenancePanel', () => {
  it('renders the heading and all 7 locked input channels', () => {
    render(<InputProvenancePanel />);
    expect(screen.getByText('What goes into OceanEmbed?')).toBeInTheDocument();
    for (const channel of ['SST', 'SSS', 'SSH/SLA', 'Current U', 'Current V', 'Wind U', 'Wind V']) {
      expect(screen.getByText(channel)).toBeInTheDocument();
    }
  });

  it('uses the multi-source satellite-derived and ocean observation framing', () => {
    render(<InputProvenancePanel />);
    const text = screen.getByTestId('input-provenance').textContent ?? '';
    expect(text).toMatch(/multi-source satellite-derived and ocean observation/i);
    expect(text).toMatch(/0\.25°/);
  });

  it('never claims all inputs are pure satellite measurements and never implies a 95% band', () => {
    render(<InputProvenancePanel />);
    const text = screen.getByTestId('input-provenance').textContent ?? '';
    expect(text.toLowerCase()).not.toMatch(/satellite measurements/);
    expect(text.toLowerCase()).not.toMatch(/95%/);
  });
});

/** Demo spec Screen 6: expandable model pipeline explanation. */
describe('ModelFlowExplainer', () => {
  it('renders the expandable explanation with the deployed pipeline steps', () => {
    render(<ModelFlowExplainer />);
    expect(screen.getByText('How does OceanEmbed work?')).toBeInTheDocument();
    const text = screen.getByTestId('model-flow-explainer').textContent ?? '';
    expect(text).toMatch(/7 surface variables/);
    expect(text).toMatch(/harmoniz/i);
    expect(text).toMatch(/7-day temporal context/);
    expect(text).toMatch(/CNN/);
    expect(text).toMatch(/ConvLSTM/);
    expect(text).toMatch(/15-depth reconstruction/);
    expect(text).toMatch(/temperature/i);
    expect(text).toMatch(/uncertainty/i);
  });
});