import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ValidationPage } from '../pages/ValidationPage';

describe('ValidationPage (real scientific credibility, no aspirational claims)', () => {
  it('shows model overview, inputs, ARGO validation, uncertainty and provenance', () => {
    render(<ValidationPage availability={null} />);
    expect(screen.getByTestId('validation-page')).toBeInTheDocument();
    expect(screen.getByTestId('validation-page').textContent).toMatch(/CNN \+ ConvLSTM/);
    expect(screen.getByTestId('validation-page').textContent).toMatch(/7-day/);
    expect(screen.getByTestId('validation-page').textContent).toMatch(/15-depth/);
    expect(screen.getByTestId('validation-page').textContent).toMatch(/0\.25/);
    for (const v of ['SST', 'SSS', 'SSH', 'Current U', 'Current V', 'Wind U', 'Wind V']) {
      expect(screen.getByTestId('validation-page').textContent).toMatch(new RegExp(v));
    }
  });

  it('displays the real ARGO numbers and the thermocline weakness honestly', () => {
    render(<ValidationPage availability={null} />);
    const text = screen.getByTestId('validation-page').textContent ?? '';
    expect(text).toMatch(/291/);
    expect(text).toMatch(/285/);
    expect(text).toMatch(/3,958/);
    expect(text).toMatch(/1\.35/);
    expect(text).toMatch(/0\.61/);
    expect(text).toMatch(/0\.990/);
    expect(text).toMatch(/75.*150|thermocline/i);
  });

  it('explains ±1σ without claiming calibrated 95% confidence or real-time capability', () => {
    render(<ValidationPage availability={null} />);
    const text = screen.getByTestId('validation-page').textContent ?? '';
    expect(text).toMatch(/±1σ/);
    expect(text).toMatch(/must not be read as 95%/);
    expect(text).not.toMatch(/calibrated 95% confidence interval/i);
    expect(text).not.toMatch(/real-?time/i);
  });

  it('shows real model provenance (hybrid_v1 / best.pt / epoch 83)', () => {
    render(<ValidationPage availability={null} />);
    const text = screen.getByTestId('validation-page').textContent ?? '';
    expect(text).toMatch(/hybrid_v1/);
    expect(text).toMatch(/best\.pt/);
    expect(text).toMatch(/83/);
  });

  it('never shows aspirational 2018–2023 training claims', () => {
    render(<ValidationPage availability={null} />);
    const text = screen.getByTestId('validation-page').textContent ?? '';
    expect(text).not.toMatch(/2018.*2023/);
  });
});
