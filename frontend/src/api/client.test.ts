import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { ApiClient, ApiError, ContractError } from '../api/client';

const MAP_OK = {
  status: 'model_prediction',
  payload: {
    region: 'bay_of_bengal',
    date: '2023-06-15',
    coordinates: { latitude: [10.0, 10.25], longitude: [88.0, 88.25, 88.5] },
    channel: 'temperature',
    depth: 0,
    values: [
      [29.1, 29.0, null],
      [28.9, 28.8, 28.7],
    ],
    sigma: [
      [0.4, 0.4, null],
      [0.4, 0.4, 0.4],
    ],
    metadata: {
      model_version: 'hybrid_v1',
      data_source: 'hybrid_v1 model inference (trained on GLORYS12v1 reanalysis)',
      preprocessing_version: 'p2-harmonize-v1',
      cached: false,
      timestamp: '2026-09-06T12:00:00Z',
    },
  },
  metadata: { model_version: 'hybrid_v1', generated_at: '2026-09-06T12:00:00Z' },
};

const PROFILE_OK = {
  status: 'model_prediction',
  payload: {
    region: 'bay_of_bengal',
    date: '2023-06-15',
    lat: 10.25,
    lon: 88.25,
    depths: [0, 5, 10, 20, 30, 50, 75, 100, 125, 150, 200, 300, 500, 700, 1000],
    temperatures: [29.0, 28.5, 28.0, 27.0, 26.0, 20.0, 14.0, 12.0, 11.0, 10.0, 9.0, 8.0, 6.5, 5.2, 4.0],
    sigma: [0.4, 0.4, 0.5, 0.6, 0.7, 1.0, 1.2, 1.4, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.5],
    metadata: {
      model_version: 'hybrid_v1',
      data_source: 'hybrid_v1 model inference (trained on GLORYS12v1 reanalysis)',
      preprocessing_version: 'p2-harmonize-v1',
      cached: false,
      timestamp: '2026-09-06T12:00:00Z',
    },
  },
  metadata: { model_version: 'hybrid_v1', generated_at: '2026-09-06T12:00:00Z' },
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  });
}

describe('ApiClient', () => {
  let client: ApiClient;
  beforeEach(() => {
    client = new ApiClient('http://localhost:8000/api/v1');
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('getMap decodes a model_prediction envelope into typed payload', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(MAP_OK)));
    const env = await client.getMap('bay_of_bengal', '2023-06-15', 0);
    expect(env.status).toBe('model_prediction');
    const p = env.payload;
    expect(p.depth).toBe(0);
    expect(p.values[0][2]).toBeNull();
    expect(p.sigma[0][2]).toBeNull();
    expect(p.values).toHaveLength(2);
    expect(p.sigma[0]).toHaveLength(3);
    expect(p.metadata.cached).toBe(false);
  });

  it('getProfile decodes 15-depth profile with sigma', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(PROFILE_OK)));
    const env = await client.getProfile('bay_of_bengal', '2023-06-15', 10.25, 88.25);
    expect(env.status).toBe('model_prediction');
    expect(env.payload.temperatures).toHaveLength(15);
    expect(env.payload.sigma).toHaveLength(15);
    expect(env.payload.lat).toBe(10.25);
  });

  it('rejects a payload missing sigma as ContractError (never blindly renders)', async () => {
    const malformed = { ...MAP_OK, payload: { ...MAP_OK.payload, sigma: undefined } };
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(malformed)));
    await expect(client.getMap('bay_of_bengal', '2023-06-15', 0)).rejects.toBeInstanceOf(ContractError);
  });

  it('maps 404 DATA_NOT_AVAILABLE into ApiError with contract code', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse(
          {
            error: { code: 'DATA_NOT_AVAILABLE', message: 'No data.', details: { region: 'bay_of_bengal' } },
          },
          404,
        ),
      ),
    );
    const err = await client.getMap('bay_of_bengal', '2030-01-01', 0).catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.code).toBe('DATA_NOT_AVAILABLE');
    expect(err.status).toBe(404);
  });

  it('maps 503 MODEL_NOT_LOADED into ApiError', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse(
          { error: { code: 'MODEL_NOT_LOADED', message: 'Model down' } },
          503,
        ),
      ),
    );
    const err = await client.getProfile('bay_of_bengal', '2023-06-15', 10.0, 88.0).catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.code).toBe('MODEL_NOT_LOADED');
    expect(err.status).toBe(503);
  });

  it('getHistory decodes region dates', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse({ region: 'bay_of_bengal', dates: ['2023-06-15', '2023-06-16'] }),
      ),
    );
    const hist = await client.getHistory('bay_of_bengal');
    expect(hist.region).toBe('bay_of_bengal');
    expect(hist.dates).toContain('2023-06-15');
  });

  it('throws ContractError on non-object error envelope', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ nope: true }, 500)));
    await expect(client.getMap('bay_of_bengal', '2023-06-15', 0)).rejects.toBeInstanceOf(ContractError);
  });
});