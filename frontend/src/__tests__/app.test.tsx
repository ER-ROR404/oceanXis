import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import App from '../App';

describe('App Root Component', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('renders header, honest footer and a deterministic unavailable state when offline', async () => {
    // Deterministic offline backend: fetch rejects like a network failure. The
    // app must degrade to an honest unavailable state, never a spinner forever.
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('connect ECONNREFUSED')));

    render(<App />);
    expect(screen.getByText('OCEANEMBED')).toBeInTheDocument();
    expect(screen.getByText('Subsurface Ocean Explorer')).toBeInTheDocument();
    expect(
      screen.getByText(/Modeled reconstruction; trained on data through 2023-12-31\./i),
    ).toBeInTheDocument();

    // History fetch fails -> honest unavailable status with the backend message
    // (the message appears in both the status strip and the field panel).
    expect(await screen.findByText('Unavailable')).toBeInTheDocument();
    expect((await screen.findAllByText('Could not reach the OceanEmbed backend.')).length).toBeGreaterThan(0);
  });
});