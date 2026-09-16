import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import App from '../App';

// Map-first explorer: stub Leaflet (no map engine in jsdom) with the same
// selection contract; the optional globe tab renders its honest fallback.
vi.mock('../components/map/OceanMap', () => ({
  OceanMap: (props: { onCellClick: (lat: number, lon: number) => void }) => (
    <div data-testid="map-host" onClick={() => props.onCellClick(5.0, 80.0)}>
      map
    </div>
  ),
}));

const availResponse = {
  regions: [
    {
      region: 'bay_of_bengal',
      status: 'available',
      dates: ['2023-09-01', '2023-09-02'],
      date_start: '2023-09-01',
      date_end: '2023-09-02',
      depths: [0, 5, 10, 20, 30, 50, 75, 100, 125, 150, 200, 300, 500, 700, 1000],
      variables: ['SST', 'SSS', 'SSH/SLA', 'current_U', 'current_V', 'wind_U', 'wind_V'],
      grid: { n_lat: 2, n_lon: 2, n_depths: 15 },
      model_version: 'hybrid_v1',
      trained_on: '2023-12-31',
      data_version: 'bay_of_bengal-2022-2023-v1',
      checkpoint: { file: 'best.pt', epoch: 83, val_loss: 0.3714623343872113, generated_at: '2026-09-06T13:48:16+00:00' },
    },
    {
      region: 'arabian_sea',
      status: 'no_data',
      dates: [],
      date_start: null,
      date_end: null,
      depths: [],
      variables: [],
      grid: null,
      model_version: 'hybrid_v1',
      trained_on: '2023-12-31',
      data_version: 'bay_of_bengal-2022-2023-v1',
      checkpoint: null,
    },
    {
      region: 'north_indian_ocean',
      status: 'no_data',
      dates: [],
      date_start: null,
      date_end: null,
      depths: [],
      variables: [],
      grid: null,
      model_version: 'hybrid_v1',
      trained_on: '2023-12-31',
      data_version: 'bay_of_bengal-2022-2023-v1',
      checkpoint: null,
    },
  ],
  model: { version: 'hybrid_v1', trained_on: '2023-12-31', data_version: 'bay_of_bengal-2022-2023-v1' },
  generated_at: '2023-09-02T00:00:00Z',
};

function mapEnvelope() {
  return {
    status: 'model_prediction',
    payload: {
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
    },
    metadata: { model_version: 'hybrid_v1', generated_at: '2023-09-01T00:00:00Z' },
  };
}

describe('Explorer navigation + map-first views', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('opens on the map explorer, keeps validation off the main page, and navigates', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((url: string) => {
        if (String(url).includes('/availability')) {
          return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(availResponse) });
        }
        if (String(url).includes('/ocean/map')) {
          return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(mapEnvelope()) });
        }
        return Promise.reject(new Error(`unexpected ${url}`));
      }),
    );

    render(<App />);
    // Map is the sole spatial view; no globe toggle exists anymore.
    expect(await screen.findByTestId('map-host')).toBeInTheDocument();
    expect(screen.queryByTestId('ocean-globe')).toBeNull();
    expect(screen.queryByRole('button', { name: /^globe$/i })).toBeNull();
    // Main explorer answers WHERE/WHEN/HOW DEEP — not RMSE.
    const explorer = screen.getByTestId('explorer-page');
    expect(explorer.textContent).not.toMatch(/RMSE/);
    // Minimal nav exists.
    expect(screen.getByRole('button', { name: /ocean explorer/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /validation.*model/i })).toBeInTheDocument();
    // Navigate to the credibility page.
    fireEvent.click(screen.getByRole('button', { name: /validation.*model/i }));
    expect(await screen.findByTestId('validation-page')).toBeInTheDocument();
    expect(screen.getByTestId('validation-page').textContent).toMatch(/1\.35/);
  });

  it('keeps unsupported regions unavailable (no fake Arabian Sea globe data)', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((url: string) => {
        if (String(url).includes('/availability')) {
          return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(availResponse) });
        }
        if (String(url).includes('/ocean/map')) {
          return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(mapEnvelope()) });
        }
        return Promise.reject(new Error(`unexpected ${url}`));
      }),
    );
    render(<App />);
    expect(await screen.findByTestId('map-host')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Region'), { target: { value: 'arabian_sea' } });
    expect(await screen.findByTestId('empty-region-state')).toBeInTheDocument();
  });
});
