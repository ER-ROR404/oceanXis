import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Header } from '../components/layout/Header';
import { StatusBanner } from '../components/layout/StatusBanner';
import { Footer } from '../components/layout/Footer';
import type { PredictionStatus } from '../types/contracts';

const STATUS_TEXT: Record<PredictionStatus, RegExp> = {
  model_prediction: /Live model/i,
  cached_data: /Served from cache/i,
  fallback_demo: /Demo data/i,
  unavailable: /Unavailable/i,
};

describe('Header', () => {
  it('renders the OCEANEMBED wordmark and explorer label', () => {
    render(<Header />);
    expect(screen.getByText('OCEANEMBED')).toBeInTheDocument();
    expect(screen.getByText('Subsurface Ocean Explorer')).toBeInTheDocument();
  });

  it('labels the product as a historical reconstruction, never realtime', () => {
    render(<Header />);
    expect(screen.getByText(/Research prototype/i)).toBeInTheDocument();
    expect(screen.getByText(/Historical reconstruction/i)).toBeInTheDocument();
    expect(screen.queryByText(/realtime|live now/i)).toBeNull();
  });

  it('states the core value in the hero tagline', () => {
    render(<Header />);
    expect(screen.getByTestId('hero-tagline')).toHaveTextContent(
      'Satellite-derived Surface Observations → Subsurface Temperature Reconstruction',
    );
  });
});

describe('StatusBanner', () => {
  it.each(['model_prediction', 'cached_data', 'fallback_demo', 'unavailable'] as PredictionStatus[])(
    'renders an honest label for status %s',
    (status) => {
      render(<StatusBanner status={status} />);
      expect(screen.getByText(STATUS_TEXT[status])).toBeInTheDocument();
    },
  );

  it('tells the truth for fallback_demo: not the live model', () => {
    render(<StatusBanner status="fallback_demo" />);
    expect(screen.getByText(/not the live model/i)).toBeInTheDocument();
  });

  it('renders reserved min-height placeholder when absent (no layout jump)', () => {
    const { container } = render(<StatusBanner status={null} />);
    // aria-hidden placeholder keeps banner area height stable.
    const placeholder = container.querySelector('[aria-hidden="true"]');
    expect(placeholder).not.toBeNull();
    expect(placeholder).toHaveClass(/h-8/);
  });

  it('exposes aria-live for status changes', () => {
    const { container } = render(<StatusBanner status="cached_data" />);
    expect(container.querySelector('[aria-live="polite"]')).not.toBeNull();
  });
});

describe('Footer', () => {
  it('carries the static honest modeled-reconstruction line', () => {
    render(<Footer />);
    expect(screen.getByText(/Modeled reconstruction; trained on data through 2023-12-31\./i)).toBeInTheDocument();
  });

  it('contains zero em-dashes in UI copy', () => {
    render(<Footer />);
    const { container } = render(<Footer />);
    expect(container.textContent).not.toContain('—');
  });
});