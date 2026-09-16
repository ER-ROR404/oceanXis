import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { OceanGlobe } from './OceanGlobe';
import type { MapPayload } from '../../types/contracts';

function fakePayload(): MapPayload {
  return {
    region: 'bay_of_bengal',
    date: '2023-09-01',
    coordinates: { latitude: [5.0, 5.25], longitude: [80.0, 80.25] },
    channel: 'temperature',
    depth: 100,
    values: [
      [28.5, 28.1],
      [27.9, null],
    ],
    sigma: [
      [0.4, 0.5],
      [0.5, null],
    ],
    metadata: {
      model_version: 'hybrid_v1',
      data_source: 'hybrid_v1 model inference (trained on GLORYS12v1 reanalysis)',
      preprocessing_version: 'v1',
      cached: false,
      timestamp: '2023-09-01T00:00:00Z',
    },
  };
}

describe('OceanGlobe (real spherical explorer)', () => {
  it('loads the globe focused on the Bay of Bengal with the real heatmap label', () => {
    render(<OceanGlobe payload={fakePayload()} layer="temperature" selected={null} onCellClick={() => {}} />);
    expect(screen.getByTestId('ocean-globe')).toBeInTheDocument();
    expect(screen.getByTestId('ocean-globe').textContent).toMatch(/Bay of Bengal/);
    expect(screen.getByTestId('ocean-globe').textContent).toMatch(/Predicted Subsurface Temperature/);
    expect(screen.getByTestId('ocean-globe').textContent).toMatch(/100 m/);
  });

  it('forwards snapped grid clicks (no arbitrary coordinates)', () => {
    let clicked: { lat: number; lon: number } | null = null;
    render(
      <OceanGlobe
        payload={fakePayload()}
        layer="temperature"
        selected={null}
        onCellClick={(lat, lon) => {
          clicked = { lat, lon };
        }}
      />,
    );
    fireEvent.click(screen.getByTestId('globe-grid-activate-0-0'));
    expect(clicked).toEqual({ lat: 5.0, lon: 80.0 });
  });
});
