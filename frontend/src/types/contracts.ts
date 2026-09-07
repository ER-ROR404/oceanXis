/**
 * Typed mirrors of the versioned backend contracts (contracts/api/*.schema.json).
 *
 * Keep in lockstep with backend app schemas. The runtime contract guards live
 * in api/client.ts; these types describe the *decoded, trusted* shapes.
 */

export type Region = 'bay_of_bengal' | 'arabian_sea' | 'north_indian_ocean';

export type OceanChannel = 'temperature';

/** Canonical depth order, meters (LOCKED by problem statement). */
export const CANONICAL_DEPTHS = [
  0, 5, 10, 20, 30, 50, 75, 100, 125, 150, 200, 300, 500, 700, 1000,
] as const;
export type Depth = (typeof CANONICAL_DEPTHS)[number];

export const REGION_IDS: Region[] = ['bay_of_bengal', 'arabian_sea', 'north_indian_ocean'];

export type PredictionStatus = 'model_prediction' | 'cached_data' | 'fallback_demo' | 'unavailable';

export interface MapMetadata {
  model_version: string;
  data_source: string;
  preprocessing_version: string;
  cached: boolean;
  timestamp: string;
}

export interface Coordinates {
  latitude: number[];
  longitude: number[];
}

/** ocean-map.schema.json payload. values/sigma are 2D [lat][lon]; null = land. */
export interface MapPayload {
  region: Region;
  date: string;
  coordinates: Coordinates;
  channel: OceanChannel;
  depth: Depth;
  values: (number | null)[][];
  sigma: (number | null)[][];
  metadata: MapMetadata;
}

/** ocean-profile.schema.json payload. depths/temperatures/sigma have 15 entries. */
export interface ProfilePayload {
  region: Region;
  date: string;
  lat: number;
  lon: number;
  depths: number[];
  temperatures: (number | null)[];
  sigma: (number | null)[];
  metadata: MapMetadata;
}

export interface EnvelopeMetadata {
  model_version: string;
  generated_at: string;
  channel_status?: Record<string, 'available' | 'missing' | 'cached'>;
}

/** prediction.schema.json envelope. */
export interface PredictionEnvelope<T> {
  status: PredictionStatus;
  payload: T;
  metadata: EnvelopeMetadata;
}

/** error.schema.json envelope. */
export interface ErrorPayload {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}

/** GET /ocean/history response. */
export interface HistoryResponse {
  region: string;
  dates: string[];
}