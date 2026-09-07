/**
 * Typed HTTP client for the OceanEmbed FastAPI backend (/api/v1).
 *
 * Responses are never trusted blindly (RULE 6 discipline): every payload is
 * runtime-validated against the contract shape before it is typed. Malformed
 * payloads raise ContractError; HTTP error envelopes map to ApiError with the
 * backend's contract code + status preserved for the UI status taxonomy.
 */

import type {
  Depth,
  HistoryResponse,
  MapPayload,
  PredictionEnvelope,
  ProfilePayload,
  Region,
} from '../types/contracts';
import { CANONICAL_DEPTHS, REGION_IDS } from '../types/contracts';

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly details?: Record<string, unknown>;

  constructor(status: number, code: string, message: string, details?: Record<string, unknown>) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

export class ContractError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ContractError';
  }
}

const isNumberLike = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);
const isNullOrNumber = (v: unknown): v is number | null => v === null || isNumberLike(v);

function requireObject(value: unknown, what: string): Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    throw new ContractError(`${what}: expected an object`);
  }
  return value as Record<string, unknown>;
}

function expectMetadata(value: unknown): Record<string, unknown> {
  const meta = requireObject(value, 'metadata');
  for (const field of ['model_version', 'data_source', 'preprocessing_version', 'cached', 'timestamp']) {
    if (!(field in meta)) throw new ContractError(`metadata missing required field: ${field}`);
  }
  if (typeof meta.cached !== 'boolean') throw new ContractError('metadata.cached must be boolean');
  return meta;
}

function expectGrid(value: unknown, what: string): (number | null)[][] {
  if (!Array.isArray(value) || value.length === 0) throw new ContractError(`${what}: expected non-empty grid`);
  const rows = value as unknown[];
  const firstLen = rows[0] as unknown[];
  if (!Array.isArray(firstLen)) throw new ContractError(`${what}: expected [lat][lon] rows`);
  for (const row of rows) {
    if (!Array.isArray(row) || row.length !== firstLen.length) {
      throw new ContractError(`${what}: ragged grid rows`);
    }
    for (const v of row) if (!isNullOrNumber(v)) throw new ContractError(`${what}: non-numeric cell`);
  }
  return rows as (number | null)[][];
}

function expectDepthList(value: unknown, what: string): (number | null)[] {
  if (!Array.isArray(value) || value.length !== CANONICAL_DEPTHS.length) {
    throw new ContractError(`${what}: expected ${CANONICAL_DEPTHS.length} entries`);
  }
  for (const v of value) if (!isNullOrNumber(v)) throw new ContractError(`${what}: non-numeric value`);
  return value as (number | null)[];
}

function expectCoordinates(value: unknown): { latitude: number[]; longitude: number[] } {
  const coords = requireObject(value, 'coordinates');
  const lat = coords['latitude'];
  const lon = coords['longitude'];
  if (!Array.isArray(lat) || !Array.isArray(lon) || lat.length === 0 || lon.length === 0) {
    throw new ContractError('coordinates: expected non-empty latitude/longitude arrays');
  }
  if (!lat.every(isNumberLike) || !lon.every(isNumberLike)) {
    throw new ContractError('coordinates: non-numeric grid value');
  }
  return { latitude: lat as number[], longitude: lon as number[] };
}

function expectMapPayload(value: unknown): MapPayload {
  const p = requireObject(value, 'map payload');
  const coordinates = expectCoordinates(p['coordinates']);
  const values = expectGrid(p['values'], 'values');
  const sigma = expectGrid(p['sigma'], 'sigma');
  if (sigma.length !== values.length || sigma[0].length !== values[0].length || sigma[0].length === 0) {
    throw new ContractError('sigma must mirror values cell-for-cell');
  }
  if (!REGION_IDS.includes(p['region'] as Region)) throw new ContractError('map: unknown region');
  if (typeof p['date'] !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(p['date'])) {
    throw new ContractError('map: invalid date');
  }
  if (p['channel'] !== 'temperature') throw new ContractError('map: unknown channel');
  if (!CANONICAL_DEPTHS.includes(p['depth'] as Depth)) throw new ContractError('map: invalid depth');
  // sigma mirrors values: identical null placement (backend guarantees it).
  for (let r = 0; r < values.length; r++) {
    for (let c = 0; c < values[r].length; c++) {
      if ((values[r][c] === null) !== (sigma[r][c] === null)) {
        throw new ContractError('sigma null mask must match values');
      }
    }
  }
  return {
    region: p['region'] as Region,
    date: p['date'] as string,
    coordinates,
    channel: 'temperature',
    depth: p['depth'] as Depth,
    values,
    sigma,
    metadata: expectMetadata(p["metadata"]) as unknown as MapPayload["metadata"],
  };
}

function expectProfilePayload(value: unknown): ProfilePayload {
  const p = requireObject(value, 'profile payload');
  if (!REGION_IDS.includes(p['region'] as Region)) throw new ContractError('profile: unknown region');
  if (typeof p['date'] !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(p['date'])) {
    throw new ContractError('profile: invalid date');
  }
  if (!isNumberLike(p['lat']) || !isNumberLike(p['lon'])) throw new ContractError('profile: invalid lat/lon');
  const temperatures = expectDepthList(p['temperatures'], 'temperatures');
  const sigma = expectDepthList(p['sigma'], 'sigma');
  for (let i = 0; i < temperatures.length; i++) {
    if ((temperatures[i] === null) !== (sigma[i] === null)) {
      throw new ContractError('sigma null mask must match temperatures');
    }
  }
  return {
    region: p['region'] as Region,
    date: p['date'] as string,
    lat: p['lat'] as number,
    lon: p['lon'] as number,
    depths: [...CANONICAL_DEPTHS],
    temperatures,
    sigma,
    metadata: expectMetadata(p["metadata"]) as unknown as ProfilePayload["metadata"],
  };
}

function expectEnvelope(value: unknown, kind: 'map' | 'profile'): PredictionEnvelope<MapPayload | ProfilePayload> {
  const env = requireObject(value, 'envelope');
  const status = env['status'];
  const STATUSES = ['model_prediction', 'cached_data', 'fallback_demo', 'unavailable'];
  if (typeof status !== 'string' || !STATUSES.includes(status)) {
    throw new ContractError(`envelope: unknown status ${String(status)}`);
  }
  const meta = requireObject(env['metadata'], 'envelope metadata');
  if (typeof meta['model_version'] !== 'string' || typeof meta['generated_at'] !== 'string') {
    throw new ContractError('envelope metadata: missing model_version/generated_at');
  }
  const payload =
    kind === 'map'
      ? expectMapPayload(env['payload'])
      : expectProfilePayload(env['payload']);
  return {
    status: status as PredictionEnvelope<MapPayload | ProfilePayload>['status'],
    payload,
    metadata: meta as unknown as PredictionEnvelope<MapPayload | ProfilePayload>["metadata"],
  };
}

export class ApiClient {
  constructor(readonly baseUrl: string) {}

  async getMap(region: Region, date: string, depth: Depth): Promise<PredictionEnvelope<MapPayload>> {
    const params = new URLSearchParams({ region, date, depth: String(depth) });
    const body = await this._request(`/ocean/map?${params}`);
    return expectEnvelope(body, 'map') as PredictionEnvelope<MapPayload>;
  }

  async getProfile(region: Region, date: string, lat: number, lon: number): Promise<PredictionEnvelope<ProfilePayload>> {
    const params = new URLSearchParams({
      region,
      date,
      latitude: String(lat),
      longitude: String(lon),
    });
    const body = await this._request(`/ocean/profile?${params}`);
    return expectEnvelope(body, 'profile') as PredictionEnvelope<ProfilePayload>;
  }

  async getHistory(region: Region): Promise<HistoryResponse> {
    const body = await this._request(`/ocean/history?region=${encodeURIComponent(region)}`);
    const b = requireObject(body, 'history');
    if (typeof b['region'] !== 'string') throw new ContractError('history: missing region');
    if (!Array.isArray(b['dates']) || !b['dates'].every((d) => typeof d === 'string')) {
      throw new ContractError('history: dates must be an array of strings');
    }
    return { region: b['region'] as string, dates: b['dates'] as string[] };
  }

  private async _request(path: string): Promise<unknown> {
    let resp: Response;
    try {
      resp = await fetch(`${this.baseUrl}${path}`, { headers: { accept: 'application/json' } });
    } catch (cause) {
      throw new ApiError(0, 'NETWORK_FAILURE', 'Could not reach the OceanEmbed backend.', { cause: String(cause) });
    }

    let body: unknown;
    try {
      body = await resp.json();
    } catch {
      throw new ContractError(`non-JSON response (${resp.status}) from ${path}`);
    }

    if (!resp.ok) {
      const err = requireObject(body, 'error envelope');
      const error = requireObject(err['error'], 'error');
      const code = error['code'];
      const message = error['message'];
      if (typeof code !== 'string' || typeof message !== 'string') {
        throw new ContractError('error envelope missing code/message');
      }
      throw new ApiError(resp.status, code, message, error['details'] as Record<string, unknown> | undefined);
    }
    return body;
  }
}