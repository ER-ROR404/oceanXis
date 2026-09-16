import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import App from '../App';
import { ApiError, ContractError } from '../api/client';
import { descriptionOf } from '../hooks/useOceanExplorer';
import { CANONICAL_DEPTHS } from '../types/contracts';

/**
 * Critical user flow — history -> map -> cell click -> profile ->
 * explainer -> Validation & Model (ARGO) — plus honest degraded states.
 * The Leaflet OceanMap is stubbed with the same selection contract
 * (onCellClick(lat, lon) with snapped grid centers); everything else (hook,
 * client, charts, panels) runs for real against a mocked /api/v1 backend.
 */

vi.mock('../components/map/OceanMap', () => ({
  OceanMap: (props: { payload: { depth: number }; onCellClick: (lat: number, lon: number) => void }) => (
    <div data-testid="map-host" onClick={() => props.onCellClick(15.25, 87.5)}>
      map
    </div>
  ),
}));

const MAP_PAYLOAD = {
  region: 'bay_of_bengal',
  date: '2023-09-07',
  coordinates: { latitude: [15.0, 15.25, 15.5], longitude: [87.25, 87.5, 87.75] },
  channel: 'temperature',
  depth: 100,
  values: [
    [28.4, 28.6, 28.5],
    [28.2, 28.3, 28.1],
    [27.9, 28.0, 27.8],
  ],
  sigma: [
    [0.5, 0.4, 0.5],
    [0.4, 0.4, 0.4],
    [0.4, 0.4, 0.5],
  ],
  metadata: {
    model_version: 'hybrid_v1',
    data_source: 'demo cache',
    preprocessing_version: 'v1',
    cached: true,
    timestamp: '2026-09-08T00:00:00Z',
  },
};

const PROFILE_PAYLOAD = {
  region: 'bay_of_bengal',
  date: '2023-09-07',
  lat: 15.25,
  lon: 87.5,
  depths: [...CANONICAL_DEPTHS],
  temperatures: [29.2, 28.9, 28.5, 28.0, 27.2, 24.0, 19.5, 16.0, 14.5, 13.2, 11.8, 9.5, 7.2, 5.8, 4.6],
  sigma: [0.4, 0.4, 0.5, 0.5, 0.7, 1.1, 1.4, 1.5, 1.6, 1.7, 1.9, 2.1, 2.3, 2.4, 2.6],
  metadata: {
    model_version: 'hybrid_v1',
    data_source: 'demo cache',
    preprocessing_version: 'v1',
    cached: true,
    timestamp: '2026-09-08T00:00:00Z',
  },
};

const BOB_DATES = ['2023-06-01', '2023-07-06', '2023-08-03', '2023-09-07', '2023-12-28'];

/** Truthful availability envelope: only bay_of_bengal is currently served. */
function availabilityFor(dates: string[]) {
  const sorted = [...dates].sort();
  const bobEntry = {
    region: 'bay_of_bengal',
    status: 'available',
    dates: sorted,
    date_start: sorted[0] ?? null,
    date_end: sorted[sorted.length - 1] ?? null,
    depths: [...CANONICAL_DEPTHS],
    variables: ['SST', 'SSS', 'SSH/SLA', 'current_U', 'current_V', 'wind_U', 'wind_V'],
    grid: { n_lat: 69, n_lon: 81, n_depths: 15 },
    model_version: 'hybrid_v1',
    trained_on: '2023-12-31',
    data_version: 'bay_of_bengal-2022-2023-v1',
    checkpoint: { file: 'best.pt', epoch: 83, val_loss: 0.3715, generated_at: '2026-09-06T13:48:16+00:00' },
  };
  const noData = (region: string) => ({
    region,
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
  });
  return {
    regions: [bobEntry, noData('arabian_sea'), noData('north_indian_ocean')],
    model: { version: 'hybrid_v1', trained_on: '2023-12-31', data_version: 'bay_of_bengal-2022-2023-v1' },
    generated_at: '2026-09-08T00:00:00Z',
  };
}

let profileMode: 'ok' | 'land' = 'ok';
let mapUrlLog: string[] = [];

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  });
}

function mockBackend() {
  mapUrlLog = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      mapUrlLog.push(url);
      if (url.includes('/availability')) {
        return jsonResponse(availabilityFor(BOB_DATES));
      }
      if (url.includes('/ocean/history')) {
        const region = new URL(url, 'http://backend.test').searchParams.get('region');
        return jsonResponse({ region, dates: region === 'bay_of_bengal' ? BOB_DATES : [] });
      }
      if (url.includes('/ocean/map')) {
        return jsonResponse({
          status: 'fallback_demo',
          payload: { ...MAP_PAYLOAD },
          metadata: { model_version: 'hybrid_v1', generated_at: '2026-09-08T00:00:00Z' },
        });
      }
      if (url.includes('/ocean/profile')) {
        if (profileMode === 'land') {
          return jsonResponse(
            { error: { code: 'DATA_NOT_AVAILABLE', message: 'No profile for this land cell.', details: {} } },
            404,
          );
        }
        return jsonResponse({
          status: 'fallback_demo',
          payload: { ...PROFILE_PAYLOAD },
          metadata: { model_version: 'hybrid_v1', generated_at: '2026-09-08T00:00:00Z' },
        });
      }
      return jsonResponse({ error: { code: 'NOT_FOUND', message: 'unknown route' } }, 404);
    }),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('useOceanExplorer error mapping', () => {
  it('keeps ApiError messages verbatim for the status strip', () => {
    expect(descriptionOf(new ApiError(503, 'MODEL_NOT_LOADED', 'Model down'))).toBe('Model down');
  });

  it('explains contract violations and arbitrary failures honestly', () => {
    expect(descriptionOf(new ContractError('bad shape'))).toMatch(/contract/i);
    expect(descriptionOf(new Error('boom'))).toBe(
      'Unexpected error while contacting the OceanEmbed backend.',
    );
  });
});

describe('Ocean Explorer end-to-end journey', () => {
  beforeEach(() => {
    profileMode = 'ok';
  });

  it('loads history, defaults the date, renders the demo field and honest banner', async () => {
    mockBackend();
    render(<App />);

    // Header + footer honest line on every screen.
    expect(screen.getByText('OCEANEMBED')).toBeInTheDocument();
    expect(screen.getByText(/Modeled reconstruction; trained on data through 2023-12-31\./i)).toBeInTheDocument();

    // Hero tagline states the core value in the first second of the demo.
    expect(screen.getByTestId('hero-tagline')).toHaveTextContent(
      'Satellite-derived Surface Observations → Subsurface Temperature Reconstruction',
    );

    // The product is honestly marked as a historical reconstruction, never realtime.
    expect(await screen.findByText(/Historical reconstruction/i)).toBeInTheDocument();
    expect(screen.getByText(/Research prototype/i)).toBeInTheDocument();

    // Date select backfilled from the availability report, defaulted inside the window.
    const dateSelect = (await screen.findByLabelText('Date')) as HTMLSelectElement;
    expect(dateSelect.value).toBe('2023-09-07');
    expect(screen.getByLabelText('Region')).toHaveValue('bay_of_bengal');
    expect(screen.getByRole('button', { name: '100 m' })).toHaveAttribute('aria-pressed', 'true');

    // Map envelope drives the status banner (fallback_demo -> honest "Demo data").
    expect(await screen.findByText('Demo data')).toBeInTheDocument();
    expect(await screen.findByTestId('map-host')).toBeInTheDocument();

    // Provenance strip: compact map stats replace the audit trail on Explorer.
    expect(await screen.findByTestId('map-stats')).toHaveTextContent(/100 m/);
    expect(screen.getByTestId('map-stats')).toHaveTextContent(/9 valid ocean cells/);
    expect(screen.getByTestId('map-stats')).toHaveTextContent(/0\.25° grid/);
    expect(screen.getByText('hybrid_v1')).toBeInTheDocument();

    // fetch used the canonical depth 100 for the map request.
    expect(mapUrlLog.some((u) => u.includes('/ocean/map') && u.includes('depth=100'))).toBe(true);

    // Map section title: "Predicted Subsurface Temperature · 100 m" + grid note.
    expect(screen.getByTestId('map-title')).toHaveTextContent('Predicted Subsurface Temperature · 100 m');
    expect(screen.getByTestId('map-title')).not.toHaveTextContent(/95/);
    expect(screen.getByTestId('map-subtitle')).toHaveTextContent(/Bay of Bengal/);
    expect(screen.getByTestId('map-subtitle')).toHaveTextContent(/0\.25° reconstruction grid/);

    // Availability window chip: region + full served date range.
    expect(screen.getByTestId('availability-window')).toHaveTextContent(
      'Bay of Bengal · 2023-06-01 → 2023-12-28',
    );
  });

  it('walks globe cell click -> profile -> explainer, then ARGO validation on its own page', async () => {
    mockBackend();
    render(<App />);

    await screen.findByTestId('map-host');

    fireEvent.click(screen.getByTestId('map-host'));

    // Selected-cell readout, mono and precise.
    expect(await screen.findByTestId('selected-cell')).toHaveTextContent('15.25°N, 87.50°E');

    // Profile chart is the primary representation (curve with ±1σ band).
    expect(
      await screen.findByLabelText('Temperature profile with model uncertainty band (±1σ)'),
    ).toBeInTheDocument();

    // Exact values disclosure reveals the authoritative 15 model values.
    expect(screen.queryByTestId('depth-column')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: /exact values/i }));
    expect(await screen.findByTestId('depth-column')).toBeInTheDocument();

    // Deterministic explainer.
    expect(screen.getByLabelText('Explain this location')).toBeInTheDocument();
    expect(screen.getByText('Explain this location')).toBeInTheDocument();

    // The explorer answers WHERE/WHAT — evaluation lives on Validation & Model.
    expect(screen.queryByTestId('argo-validation-panel')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: /validation.*model/i }));

    // ARGO validation panel on its own page, overall RMSE rendered.
    expect(screen.getByTestId('argo-validation-panel')).toBeInTheDocument();
    expect(screen.getByText('Independent ARGO validation')).toBeInTheDocument();
    expect(screen.getByText(/1\.35/)).toBeInTheDocument();

    // Provenance + model explainer frame the science for the demo.
    expect(screen.getByText('What goes into OceanEmbed?')).toBeInTheDocument();
    expect(screen.getByText('SST')).toBeInTheDocument();
    expect(screen.getByText('SSH/SLA')).toBeInTheDocument();
    expect(screen.getByText(/Multi-source satellite-derived and ocean observation/i)).toBeInTheDocument();
    expect(screen.getByText('How does OceanEmbed work?')).toBeInTheDocument();
    expect(screen.getByText('CNN')).toBeInTheDocument();
    expect(screen.getByText('ConvLSTM')).toBeInTheDocument();
  });

  it('switches region to one with no data and shows an honest unavailable state', async () => {
    mockBackend();
    render(<App />);
    await screen.findByTestId('map-host');

    fireEvent.change(screen.getByLabelText('Region'), { target: { value: 'arabian_sea' } });

    // Honest banner + dedicated no-data empty state.
    expect(await screen.findByText('Unavailable')).toBeInTheDocument();
    const emptyState = await screen.findByTestId('empty-region-state');
    expect(within(emptyState).getByText(/No data available/i)).toBeInTheDocument();
    expect(screen.queryByTestId('map-host')).toBeNull();

    // Returning to Bay of Bengal recovers the map without a reload.
    fireEvent.change(screen.getByLabelText('Region'), { target: { value: 'bay_of_bengal' } });
    expect(await screen.findByTestId('map-host')).toBeInTheDocument();
  });

  it('reports a land-cell profile miss honestly instead of crashing', async () => {
    profileMode = 'land';
    mockBackend();
    render(<App />);
    await screen.findByTestId('map-host');

    fireEvent.click(screen.getByTestId('map-host'));

    expect(await screen.findByText(/No profile here/i)).toBeInTheDocument();
    expect(screen.queryByLabelText('Temperature profile with model uncertainty band (±1σ)')).toBeNull();
  });

  it('surfaces a backend contract violation honestly instead of rendering malformed data', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes('/availability')) {
          return jsonResponse(availabilityFor(BOB_DATES));
        }
        if (url.includes('/ocean/map')) {
          // Malformed: sigma missing. The client must reject it (ContractError)
          // and the UI must show the contract message, never raw payload.
          return jsonResponse({
            status: 'fallback_demo',
            payload: { ...MAP_PAYLOAD, sigma: undefined },
            metadata: { model_version: 'hybrid_v1', generated_at: '2026-09-08T00:00:00Z' },
          });
        }
        return jsonResponse({ error: { code: 'NOT_FOUND', message: 'unknown route' } }, 404);
      }),
    );
    render(<App />);

    expect(await screen.findByText('Unavailable')).toBeInTheDocument();
    // The contract message appears in the status strip and the field panel.
    expect((await screen.findAllByText(/did not match the OceanEmbed contract/i)).length).toBeGreaterThan(0);
    expect(screen.queryByTestId('map-host')).toBeNull();
  });

  it('drives the date selector from the full live availability report (730 dates), not the 31-date demo cache', async () => {
    // Simulate the live model-service tensor store: daily 2022-01-01..2023-12-31.
    const liveDates = Array.from({ length: 730 }, (_, i) => {
      const d = new Date(Date.UTC(2022, 0, 1 + i));
      return d.toISOString().slice(0, 10);
    });
    expect(liveDates[0]).toBe('2022-01-01');
    expect(liveDates[liveDates.length - 1]).toBe('2023-12-31');

    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes('/availability')) {
          return jsonResponse(availabilityFor(liveDates));
        }
        if (url.includes('/ocean/map')) {
          // The live service answers: model_prediction, not fallback_demo.
          return jsonResponse({
            status: 'model_prediction',
            payload: { ...MAP_PAYLOAD, date: url.includes('date=2023-09-01') ? '2023-09-01' : MAP_PAYLOAD.date },
            metadata: { model_version: 'hybrid_v1', generated_at: '2026-09-08T00:00:00Z' },
          });
        }
        if (url.includes('/ocean/profile')) {
          return jsonResponse({
            status: 'model_prediction',
            payload: { ...PROFILE_PAYLOAD },
            metadata: { model_version: 'hybrid_v1', generated_at: '2026-09-08T00:00:00Z' },
          });
        }
        return jsonResponse({ error: { code: 'NOT_FOUND', message: 'unknown route' } }, 404);
      }),
    );

    render(<App />);

    // Every one of the 730 daily dates is offered — the demo-cache limitation
    // (31 weekly dates) is gone.
    const dateSelect = (await screen.findByLabelText('Date')) as HTMLSelectElement;
    expect(dateSelect.options.length).toBe(730);
    // Preferred default: first date >= the warm late-summer window.
    expect(dateSelect.value).toBe('2023-09-01');

    // Live-service status shown, full coverage surfaced (2023-12-31, not the
    // demo-cache max 2023-12-28) and no realtime implication anywhere.
    expect(await screen.findByText('Live model')).toBeInTheDocument();
    expect(dateSelect.options[dateSelect.options.length - 1].value).toBe('2023-12-31');

    // Availability window surfaces the full served range on the demo title.
    expect(screen.getByTestId('availability-window')).toHaveTextContent(
      'Bay of Bengal · 2022-01-01 → 2023-12-31',
    );
  });

  it('never shows a 95% claim or the forbidden "7 satellite measurements" phrase', async () => {
    mockBackend();
    render(<App />);

    await screen.findByTestId('map-host');

    // Profile step: select a cell, reveal exact values so column + explainer render.
    fireEvent.click(screen.getByTestId('map-host'));
    fireEvent.click(await screen.findByRole('button', { name: /exact values/i }));
    await screen.findByTestId('depth-column');

    const text = document.body.textContent ?? '';
    expect(text).not.toMatch(/95%/);
    expect(text).not.toMatch(/satellite measurements/i);
    // Correlation is never presented as a percentage accuracy claim.
    expect(text).not.toMatch(/99%|% accuracy/i);
  });
});

describe('Map depth vs profile depth separation (§38)', () => {
  beforeEach(() => {
    profileMode = 'ok';
  });

  it('map depth 100 m shows 100 m values; 200 m refetches only the map slice', async () => {
    mockBackend();
    render(<App />);
    await screen.findByTestId('map-host');

    expect(screen.getByTestId('map-title')).toHaveTextContent('Predicted Subsurface Temperature · 100 m');
    expect(mapUrlLog.some((u) => u.includes('/ocean/map') && u.includes('depth=100'))).toBe(true);

    fireEvent.click(screen.getByRole('button', { name: '200 m' }));
    expect(await screen.findByTestId('map-title')).toHaveTextContent(
      'Predicted Subsurface Temperature · 200 m',
    );
    expect(mapUrlLog.some((u) => u.includes('/ocean/map') && u.includes('depth=200'))).toBe(true);
    expect(screen.getByTestId('map-stats')).toHaveTextContent(/200 m/);
  });

  it('profile always spans the 15 canonical levels regardless of map depth', async () => {
    mockBackend();
    render(<App />);
    await screen.findByTestId('map-host');

    fireEvent.click(screen.getByTestId('map-host'));
    fireEvent.click(await screen.findByRole('button', { name: /exact values/i }));
    const planes = await screen.findAllByTestId(/^depth-plane-/);
    expect(planes).toHaveLength(15);
    expect(screen.getByTestId('depth-plane-0')).toBeInTheDocument();
    expect(screen.getByTestId('depth-plane-1000')).toBeInTheDocument();

    // Changing the map slice must not collapse the water column.
    fireEvent.click(screen.getByRole('button', { name: '200 m' }));
    expect((await screen.findAllByTestId(/^depth-plane-/))).toHaveLength(15);
    expect(screen.getByTestId('depth-plane-0')).toBeInTheDocument();
    expect(screen.getByTestId('depth-plane-1000')).toBeInTheDocument();
  });

  it('uncertainty mode changes title and legend units', async () => {
    mockBackend();
    render(<App />);
    await screen.findByTestId('map-host');

    fireEvent.click(screen.getByRole('button', { name: /^uncertainty$/i }));
    expect(await screen.findByTestId('map-title')).toHaveTextContent('Prediction Uncertainty · 100 m');
    expect(screen.getByTestId('map-legend').textContent).toMatch(/±1σ/);
    expect(screen.getByTestId('map-legend').textContent).toMatch(/°C/);

    fireEvent.click(screen.getByRole('button', { name: /^temperature$/i }));
    expect(await screen.findByTestId('map-title')).toHaveTextContent(
      'Predicted Subsurface Temperature · 100 m',
    );
  });

  it('temperature legend shows °C with real field min/max', async () => {
    mockBackend();
    render(<App />);
    await screen.findByTestId('map-host');
    const legend = await screen.findByTestId('map-legend');
    expect(legend.textContent).toMatch(/°C/);
    expect(legend.textContent).toMatch(/27\.8/);
    expect(legend.textContent).toMatch(/28\.6/);
  });

  it('keeps Bay of Bengal domain terminology consistent', async () => {
    mockBackend();
    render(<App />);
    await screen.findByTestId('map-host');
    // Served-product chrome identifies the Bay of Bengal, not the whole NIO.
    expect(screen.getByText('Bay of Bengal · 0.25°')).toBeInTheDocument();
    expect(screen.getByTestId('map-subtitle')).toHaveTextContent(/Bay of Bengal/);
    expect(screen.getByTestId('map-title')).not.toHaveTextContent(/North Indian Ocean/);
    expect(screen.getByTestId('map-stats').textContent).not.toMatch(/North Indian Ocean/);
  });

  it('map is the sole spatial view with a reset-view control', async () => {
    mockBackend();
    render(<App />);
    await screen.findByTestId('map-host');
    expect(screen.queryByTestId('ocean-globe')).toBeNull();
    // Reset view refits the domain without touching data.
    fireEvent.click(screen.getByRole('button', { name: /reset view/i }));
    expect(await screen.findByTestId('map-host')).toBeInTheDocument();
  });

  it('date change reloads map and profile for the new day', async () => {
    mockBackend();
    render(<App />);
    await screen.findByTestId('map-host');
    fireEvent.click(screen.getByTestId('map-host'));
    await screen.findByTestId('profile-location');
    expect(screen.getByTestId('profile-location').textContent).toMatch(/2023-09-07/);

    mapUrlLog.length = 0;
    fireEvent.change(screen.getByLabelText('Date'), { target: { value: '2023-08-03' } });
    expect(mapUrlLog.some((u) => u.includes('/ocean/map') && u.includes('date=2023-08-03'))).toBe(true);
  });
});