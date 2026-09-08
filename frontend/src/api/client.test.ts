import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { ApiClient, ApiError, ContractError } from '../api/client';
import { CANONICAL_DEPTHS } from '../types/contracts';

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

  const AVAILABILITY_OK = {
    regions: [
      {
        region: 'bay_of_bengal',
        status: 'available',
        dates: ['2022-01-01', '2023-12-31'],
        date_start: '2022-01-01',
        date_end: '2023-12-31',
        depths: [...CANONICAL_DEPTHS],
        variables: ['SST', 'SSS', 'SSH/SLA', 'current_U', 'current_V', 'wind_U', 'wind_V'],
        grid: { n_lat: 69, n_lon: 81, n_depths: 15 },
        model_version: 'hybrid_v1',
        trained_on: '2023-12-31',
        data_version: 'bay_of_bengal-2022-2023-v1',
        checkpoint: { file: 'best.pt', epoch: 83, val_loss: 0.3715, generated_at: '2026-09-06T13:48:16+00:00' },
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
    ],
    model: { version: 'hybrid_v1', trained_on: '2023-12-31', data_version: 'bay_of_bengal-2022-2023-v1' },
    generated_at: '2026-09-08T00:00:00Z',
  };

  it('getAvailability decodes region capabilities and model provenance', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(AVAILABILITY_OK)));
    const avail = await client.getAvailability();
    expect(avail.regions).toHaveLength(2);
    const bob = avail.regions.find((r) => r.region === 'bay_of_bengal');
    expect(bob).toBeDefined();
    expect(bob!.status).toBe('available');
    expect(bob!.dates).toEqual(['2022-01-01', '2023-12-31']);
    expect(bob!.date_start).toBe('2022-01-01');
    expect(bob!.checkpoint).toEqual({
      file: 'best.pt',
      epoch: 83,
      val_loss: 0.3715,
      generated_at: '2026-09-06T13:48:16+00:00',
    });
    expect(avail.model.version).toBe('hybrid_v1');
    const arabian = avail.regions.find((r) => r.region === 'arabian_sea');
    expect(arabian!.status).toBe('no_data');
    expect(arabian!.dates).toEqual([]);
    expect(arabian!.grid).toBeNull();
  });

  // Loose mutation handle: tests deliberately violate the contract, so the
  // wire shape is treated as untyped (never trusted).
  const mutant = () =>
    structuredClone(AVAILABILITY_OK) as unknown as { regions: Array<Record<string, unknown>> };

  it('getAvailability rejects an unknown region id (never trusts the report)', async () => {
    const bad = mutant();
    bad.regions[0].region = 'atlantis';
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(bad)));
    await expect(client.getAvailability()).rejects.toBeInstanceOf(ContractError);
  });

  it('getAvailability rejects an entry missing status', async () => {
    const bad = mutant();
    bad.regions[0].status = undefined;
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(bad)));
    await expect(client.getAvailability()).rejects.toBeInstanceOf(ContractError);
  });

  it('getAvailability rejects non-string dates on an available entry', async () => {
    const bad = mutant();
    bad.regions[0].dates = ['2023-09-07', 42];
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(bad)));
    await expect(client.getAvailability()).rejects.toBeInstanceOf(ContractError);
  });

  it('getAvailability rejects a malformed grid', async () => {
    const bad = mutant();
    bad.regions[0].grid = { n_lat: 69 };
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(bad)));
    await expect(client.getAvailability()).rejects.toBeInstanceOf(ContractError);
  });

  it('getAvailability rejects a no_data entry that claims dates', async () => {
    const bad = mutant();
    bad.regions[1].status = 'no_data';
    bad.regions[1].dates = ['2023-06-01'];
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(bad)));
    await expect(client.getAvailability()).rejects.toBeInstanceOf(ContractError);
  });

  it('getAvailability rejects an available entry without checkpoint provenance', async () => {
    const bad = mutant();
    bad.regions[0].checkpoint = null;
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(bad)));
    await expect(client.getAvailability()).rejects.toBeInstanceOf(ContractError);
  });

  it('throws ContractError on non-object error envelope', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ nope: true }, 500)));
    await expect(client.getMap('bay_of_bengal', '2023-06-15', 0)).rejects.toBeInstanceOf(ContractError);
  });

  it('throws ContractError when the response body is not JSON', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response('<html>proxy error</html>', { status: 502 })),
    );
    await expect(client.getMap('bay_of_bengal', '2023-06-15', 0)).rejects.toBeInstanceOf(ContractError);
  });

  it('throws ContractError when an error envelope lacks code/message', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse({ error: { oops: 'unstructured' } }, 500)),
    );
    await expect(client.getMap('bay_of_bengal', '2023-06-15', 0)).rejects.toBeInstanceOf(ContractError);
  });

  it('throws ContractError on ragged grid rows', async () => {
    const ragged = { ...MAP_OK, payload: { ...MAP_OK.payload, values: [[1, 2], [3]] } };
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(ragged)));
    await expect(client.getMap('bay_of_bengal', '2023-06-15', 0)).rejects.toBeInstanceOf(ContractError);
  });

  it('throws ContractError on a non-canonical depth value', async () => {
    const bad = { ...MAP_OK, payload: { ...MAP_OK.payload, depth: 42 } };
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(bad)));
    await expect(client.getMap('bay_of_bengal', '2023-06-15', 0)).rejects.toBeInstanceOf(ContractError);
  });

  it('throws ContractError when metadata.cached is not a boolean', async () => {
    const bad = {
      ...MAP_OK,
      payload: { ...MAP_OK.payload, metadata: { ...MAP_OK.payload.metadata, cached: 'yes' } },
    };
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(bad)));
    await expect(client.getMap('bay_of_bengal', '2023-06-15', 0)).rejects.toBeInstanceOf(ContractError);
  });

  it('throws ContractError when sigma does not mirror the values null mask', async () => {
    // values[0][2] is null (land) but sigma[0][2] is a number: mask mismatch.
    const bad = { ...MAP_OK, payload: { ...MAP_OK.payload, sigma: [[0.4, 0.4, 0.4], [0.4, 0.4, 0.4]] } };
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(bad)));
    await expect(client.getMap('bay_of_bengal', '2023-06-15', 0)).rejects.toBeInstanceOf(ContractError);
  });

  it('throws ContractError when the map payload is not an object', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ ...MAP_OK, payload: 'nope' })));
    await expect(client.getMap('bay_of_bengal', '2023-06-15', 0)).rejects.toBeInstanceOf(ContractError);
  });

  it('throws ContractError on an unknown region id', async () => {
    const bad = { ...MAP_OK, payload: { ...MAP_OK.payload, region: 'atlantis' } };
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(bad)));
    await expect(client.getMap('bay_of_bengal', '2023-06-15', 0)).rejects.toBeInstanceOf(ContractError);
  });

  it('throws ContractError on a non-temperature channel', async () => {
    const bad = { ...MAP_OK, payload: { ...MAP_OK.payload, channel: 'salinity' } };
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(bad)));
    await expect(client.getMap('bay_of_bengal', '2023-06-15', 0)).rejects.toBeInstanceOf(ContractError);
  });

  it('throws ContractError on a malformed ISO date', async () => {
    const bad = { ...MAP_OK, payload: { ...MAP_OK.payload, date: '2023-06-15T00:00:00Z' } };
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(bad)));
    await expect(client.getMap('bay_of_bengal', '2023-06-15', 0)).rejects.toBeInstanceOf(ContractError);
  });

  it('throws ContractError on a sigma grid whose shape differs from values', async () => {
    const bad = { ...MAP_OK, payload: { ...MAP_OK.payload, sigma: [[0.4]] } };
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(bad)));
    await expect(client.getMap('bay_of_bengal', '2023-06-15', 0)).rejects.toBeInstanceOf(ContractError);
  });

  it('throws ContractError on an empty values grid', async () => {
    const bad = { ...MAP_OK, payload: { ...MAP_OK.payload, values: [], sigma: [] } };
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(bad)));
    await expect(client.getMap('bay_of_bengal', '2023-06-15', 0)).rejects.toBeInstanceOf(ContractError);
  });

  it('throws ContractError on non-numeric coordinates', async () => {
    const bad = {
      ...MAP_OK,
      payload: { ...MAP_OK.payload, coordinates: { latitude: [10, 'x'], longitude: [88] } },
    };
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(bad)));
    await expect(client.getMap('bay_of_bengal', '2023-06-15', 0)).rejects.toBeInstanceOf(ContractError);
  });

  it('throws ContractError on a non-numeric profile latitude', async () => {
    const bad = { ...PROFILE_OK, payload: { ...PROFILE_OK.payload, lat: '10' } };
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(bad)));
    await expect(client.getProfile('bay_of_bengal', '2023-06-15', 10.0, 88.0)).rejects.toBeInstanceOf(
      ContractError,
    );
  });
});