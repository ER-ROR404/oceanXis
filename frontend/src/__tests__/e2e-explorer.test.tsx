import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import App from '../App';
import { ApiError, ContractError } from '../api/client';
import { descriptionOf } from '../hooks/useOceanExplorer';
import { CANONICAL_DEPTHS } from '../types/contracts';

/**
 * Task 7c: critical user flow — history -> map -> cell click -> profile ->
 * explainer -> ARGO validation — plus honest degraded states (region with no
 * data, land-cell profile miss). The real Leaflet OceanMap is stubbed with a
 * button that fires onCellClick(lat, lon); everything else (hook, client,
 * charts, panels) runs for real against a mocked /api/v1 backend.
 */

vi.mock('../components/map/OceanMap', () => ({
  OceanMap: (props: { onCellClick: (lat: number, lon: number) => void }) => (
    <button type="button" data-testid="map-host" onClick={() => props.onCellClick(15.25, 87.5)}>
      map
    </button>
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

    // Date select backfilled from /ocean/history, defaulted inside the window.
    const dateSelect = (await screen.findByLabelText('Date')) as HTMLSelectElement;
    expect(dateSelect.value).toBe('2023-09-07');
    expect(screen.getByLabelText('Region')).toHaveValue('bay_of_bengal');
    expect(screen.getByLabelText('Depth')).toHaveValue('100');

    // Map envelope drives the status banner (fallback_demo -> honest "Demo data").
    expect(await screen.findByText('Demo data')).toBeInTheDocument();
    expect(await screen.findByTestId('map-host')).toBeInTheDocument();

    // fetch used the canonical depth 100 for the map request.
    expect(mapUrlLog.some((u) => u.includes('/ocean/map') && u.includes('depth=100'))).toBe(true);
  });

  it('walks map cell click -> profile -> explainer -> ARGO validation', async () => {
    mockBackend();
    render(<App />);

    await screen.findByTestId('map-host');

    fireEvent.click(screen.getByTestId('map-host'));

    // Selected-cell readout, mono and precise.
    expect(await screen.findByTestId('selected-cell')).toHaveTextContent('15.25°N, 87.50°E');

    // Profile chart with the 95% band renders from the profile envelope.
    expect(
      await screen.findByLabelText('Temperature profile with 95% uncertainty band'),
    ).toBeInTheDocument();

    // Deterministic explainer.
    expect(screen.getByLabelText('Explain this location')).toBeInTheDocument();
    expect(screen.getByText('Explain this location')).toBeInTheDocument();

    // ARGO validation panel always on screen, overall RMSE rendered.
    expect(screen.getByTestId('argo-validation-panel')).toBeInTheDocument();
    expect(screen.getByText('ARGO validation')).toBeInTheDocument();
    expect(screen.getByText(/1\.35/)).toBeInTheDocument();
  });

  it('switches region to one with no data and shows an honest unavailable state', async () => {
    mockBackend();
    render(<App />);
    await screen.findByTestId('map-host');

    fireEvent.change(screen.getByLabelText('Region'), { target: { value: 'arabian_sea' } });

    // Honest banner + dedicated no-data empty state.
    expect(await screen.findByText('Unavailable')).toBeInTheDocument();
    const emptyState = await screen.findByTestId('empty-region-state');
    expect(within(emptyState).getByText(/no demo data/i)).toBeInTheDocument();
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

    expect(await screen.findByText(/no vertical profile/i)).toBeInTheDocument();
    expect(screen.queryByLabelText('Temperature profile with 95% uncertainty band')).toBeNull();
  });

  it('surfaces a backend contract violation honestly instead of rendering malformed data', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes('/ocean/history')) {
          return jsonResponse({ region: 'bay_of_bengal', dates: BOB_DATES });
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
});