/**
 * Typed HTTP client for the OceanEmbed FastAPI backend (/api/v1).
 *
 * Responses are never trusted blindly (RULE 6 discipline): every payload is
 * runtime-validated against the contract shape before it is typed. Malformed
 * payloads raise ContractError; HTTP error envelopes map to ApiError with the
 * backend's contract code + status preserved for the UI status taxonomy.
 */

import type {
  AvailabilityResponse,
  CheckpointProvenance,
  Depth,
  HistoryResponse,
  MapPayload,
  PredictionEnvelope,
  ProfilePayload,
  Region,
  RegionAvailability,
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

/**
 * Profile depth axis: exactly the canonical 15 standard depths, in canonical
 * order (meters). A wire array of array-indexes (0..14) or a reordered list
 * would silently pair the wrong temperature with each depth, so it is rejected
 * instead of being substituted.
 */
function expectProfileDepths(value: unknown): Depth[] {
  if (!Array.isArray(value) || value.length !== CANONICAL_DEPTHS.length) {
    throw new ContractError(`profile depths: expected ${CANONICAL_DEPTHS.length} canonical depths`);
  }
  for (let i = 0; i < CANONICAL_DEPTHS.length; i++) {
    if (value[i] !== CANONICAL_DEPTHS[i]) {
      throw new ContractError('profile depths: must be the canonical depths in metres, in order');
    }
  }
  return value as Depth[];
}

function expectProfilePayload(value: unknown): ProfilePayload {
  const p = requireObject(value, 'profile payload');
  if (!REGION_IDS.includes(p['region'] as Region)) throw new ContractError('profile: unknown region');
  if (typeof p['date'] !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(p['date'])) {
    throw new ContractError('profile: invalid date');
  }
  if (!isNumberLike(p['lat']) || !isNumberLike(p['lon'])) throw new ContractError('profile: invalid lat/lon');
  const depths = expectProfileDepths(p['depths']);
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
    depths,
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

function expectCheckpoint(value: unknown): CheckpointProvenance {
  const c = requireObject(value, 'checkpoint');
  for (const field of ['file', 'epoch', 'val_loss', 'generated_at'] as const) {
    if (!(field in c)) throw new ContractError(`checkpoint missing required field: ${field}`);
  }
  if (
    typeof c['file'] !== 'string' ||
    typeof c['epoch'] !== 'number' ||
    typeof c['val_loss'] !== 'number' ||
    typeof c['generated_at'] !== 'string'
  ) {
    throw new ContractError('checkpoint: invalid field type');
  }
  return {
    file: c['file'] as string,
    epoch: c['epoch'] as number,
    val_loss: c['val_loss'] as number,
    generated_at: c['generated_at'] as string,
  };
}

/** Availability report: NEVER trust the wire (RULE 6). Reject unknown regions,
 * malformed dates, and any entry that claims data it cannot have. */
function expectAvailability(value: unknown): AvailabilityResponse {
  const b = requireObject(value, 'availability report');
  if (!Array.isArray(b['regions']) || b['regions'].length === 0) {
    throw new ContractError('availability: regions must be a non-empty array');
  }
  const regions = b['regions'].map(expectRegionAvailability);
  const model = requireObject(b['model'], 'model');
  for (const field of ['version', 'trained_on', 'data_version'] as const) {
    if (typeof model[field] !== 'string') throw new ContractError(`availability model: missing ${field}`);
  }
  if (typeof b['generated_at'] !== 'string') throw new ContractError('availability: missing generated_at');
  return {
    regions,
    model: {
      version: model['version'] as string,
      trained_on: model['trained_on'] as string,
      data_version: model['data_version'] as string,
    },
    generated_at: b['generated_at'] as string,
  };
}

function expectRegionAvailability(value: unknown): RegionAvailability {
  const r = requireObject(value, 'region availability');
  if (!REGION_IDS.includes(r['region'] as Region)) throw new ContractError('availability: unknown region id');
  if (r['status'] !== 'available' && r['status'] !== 'no_data') {
    throw new ContractError('availability: invalid status');
  }
  const dates = r['dates'];
  if (!Array.isArray(dates) || !dates.every((d) => typeof d === 'string')) {
    throw new ContractError('availability: dates must be an array of strings');
  }
  if (r['status'] === 'available') {
    if ((dates as string[]).length === 0) throw new ContractError('availability: available region has no dates');
    if (!(dates as string[]).every((d) => /^\d{4}-\d{2}-\d{2}$/.test(d))) {
      throw new ContractError('availability: invalid date');
    }
    const grid = requireObject(r['grid'], 'grid');
    for (const field of ['n_lat', 'n_lon', 'n_depths'] as const) {
      if (typeof grid[field] !== 'number') throw new ContractError(`grid missing required field: ${field}`);
    }
    if (r['checkpoint'] === null || r['checkpoint'] === undefined) {
      throw new ContractError('availability: available region must carry checkpoint provenance');
    }
  } else if ((dates as string[]).length > 0) {
    throw new ContractError('availability: no_data region cannot carry dates');
  }
  const afterOptional = (v: unknown, missing: unknown): string | null =>
    v === null || v === undefined ? (missing as string | null) : (v as string);

  const dateStart = afterOptional(r['date_start'], dates[0] ?? null);
  const dateEnd = afterOptional(r['date_end'], dates[(dates as string[]).length - 1] ?? null);
  return {
    region: r['region'] as Region,
    status: r['status'] as RegionAvailability['status'],
    dates: dates as string[],
    date_start: dateStart !== null && /^\d{4}-\d{2}-\d{2}$/.test(dateStart) ? dateStart : null,
    date_end: dateEnd !== null && /^\d{4}-\d{2}-\d{2}$/.test(dateEnd) ? dateEnd : null,
    depths: r['status'] === 'available' ? [...CANONICAL_DEPTHS] : [],
    variables: (Array.isArray(r['variables']) && r['variables'].every((v) => typeof v === 'string')
      ? r['variables']
      : []) as string[],
    grid: r['status'] === 'available' ? (r['grid'] as unknown as RegionAvailability['grid']) : null,
    model_version: typeof r['model_version'] === 'string' ? r['model_version'] : '',
    trained_on: typeof r['trained_on'] === 'string' ? r['trained_on'] : '',
    data_version: typeof r['data_version'] === 'string' ? r['data_version'] : '',
    checkpoint: r['status'] === 'available' ? expectCheckpoint(r['checkpoint']) : null,
  };
}

/**
 * Default per-request timeout. A hung backend must degrade honestly instead of
 * leaving the explorer stuck on a loading skeleton forever.
 */
export const REQUEST_TIMEOUT_MS = 15_000;

export class ApiClient {
  constructor(
    readonly baseUrl: string,
    private readonly timeoutMs: number = REQUEST_TIMEOUT_MS,
  ) {}

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

  async getAvailability(): Promise<AvailabilityResponse> {
    const body = await this._request('/availability');
    return expectAvailability(body);
  }

  /**
   * Fetch with an abort-based timeout. The whole request (connect + body read)
   * is bounded, and a timeout is reported distinctly from an unreachable host so
   * the UI can say "did not respond in time" rather than freezing.
   */
  private async _request(path: string): Promise<unknown> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutMs);
    try {
      let resp: Response;
      try {
        resp = await fetch(`${this.baseUrl}${path}`, {
          headers: { accept: 'application/json' },
          signal: controller.signal,
        });
      } catch (cause) {
        throw this._networkError(controller.signal.aborted, cause);
      }

      let body: unknown;
      try {
        body = await resp.json();
      } catch (cause) {
        // An abort that lands while reading the body is still a timeout.
        if (controller.signal.aborted) throw this._networkError(true, cause);
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
    } finally {
      clearTimeout(timer);
    }
  }

  /** Honest network failure: timeout and unreachable are different causes. */
  private _networkError(timedOut: boolean, cause: unknown): ApiError {
    return timedOut
      ? new ApiError(0, 'NETWORK_TIMEOUT', 'The OceanEmbed backend did not respond in time.', {
          cause: String(cause),
        })
      : new ApiError(0, 'NETWORK_FAILURE', 'Could not reach the OceanEmbed backend.', { cause: String(cause) });
  }
}