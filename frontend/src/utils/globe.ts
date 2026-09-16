import type { Coordinates, MapPayload } from '../types/contracts';
import { fieldDomain, nearestIndex, rgbString, uncertaintyColor, viridis } from '../components/map/colorScales';
import type { LayerMode } from '../components/globe/OceanGlobeTypes';

export const GRID_STEP = 0.25;

export const BAY_OF_BENGAL_BOUNDS = { latMin: 5, latMax: 22, lonMin: 80, lonMax: 100 } as const;

/** Globe camera focus: real BoB center (13.5N, 90E), close enough to read the 0.25° field. */
export const BAY_OF_BENGAL_FOCUS = { lat: 13.5, lng: 90, altitude: 1.8 } as const;

export interface BayOfBengalFeature {
  type: 'Feature';
  geometry: { type: 'Polygon'; coordinates: [number, number][][] };
  properties: Record<string, never>;
}

/**
 * Closed GeoJSON polygon of the REAL Bay of Bengal reconstruction bounds
 * (config/regions.yaml via BAY_OF_BENGAL_BOUNDS). globe.gl polygons require
 * Feature/Polygon data; the ring is closed ([lon,lat] first == last).
 */
export function bayOfBengalPolygonFeature(): BayOfBengalFeature {
  const { lonMin, lonMax, latMin, latMax } = BAY_OF_BENGAL_BOUNDS;
  return {
    type: 'Feature',
    geometry: {
      type: 'Polygon',
      coordinates: [
        [
          [lonMin, latMin],
          [lonMax, latMin],
          [lonMax, latMax],
          [lonMin, latMax],
          [lonMin, latMin],
        ],
      ],
    },
    properties: {},
  };
}

export function isInBayOfBengal(lat: number, lon: number): boolean {
  return (
    lat >= BAY_OF_BENGAL_BOUNDS.latMin &&
    lat <= BAY_OF_BENGAL_BOUNDS.latMax &&
    lon >= BAY_OF_BENGAL_BOUNDS.lonMin &&
    lon <= BAY_OF_BENGAL_BOUNDS.lonMax
  );
}

/** Snap arbitrary hover coords to the real backend grid (mirrors profile semantics). */
export function snapToGrid(lat: number, lon: number, coords: Coordinates): { lat: number; lon: number } {
  const latRow = nearestIndex(coords.latitude, lat);
  const lonCol = nearestIndex(coords.longitude, lon);
  return { lat: coords.latitude[latRow], lon: coords.longitude[lonCol] };
}

export interface GlobePoint {
  lat: number;
  lng: number;
  value: number;
  sigma: number;
  color: string;
}

/**
 * Flatten the real [lat][lon] reconstruction plane into globe points.
 * Null (land) cells are skipped — never fabricated. Color is a rendering
 * operation over the real field domain, not additional model resolution.
 */
export function mapGridToPoints(payload: MapPayload, layer: LayerMode): GlobePoint[] {
  const { coordinates, values, sigma } = payload;
  const { min, max } = fieldDomain(values);
  const span = max - min;
  const points: GlobePoint[] = [];
  for (let r = 0; r < values.length; r++) {
    for (let c = 0; c < (values[r]?.length ?? 0); c++) {
      const v = values[r][c];
      const s = sigma[r]?.[c] ?? null;
      if (v === null || v === undefined || s === null || s === undefined) continue;
      const lat = coordinates.latitude[r];
      const lon = coordinates.longitude[c];
      if (lat === undefined || lon === undefined) continue;
      const rgb = layer === 'temperature' ? viridis((v - min) / span) : uncertaintyColor(Math.min(1, s / 3.0));
      points.push({ lat, lng: lon, value: v, sigma: s, color: rgbString(rgb) });
    }
  }
  return points;
}
