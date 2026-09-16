import { describe, it, expect } from 'vitest';
import {
  BAY_OF_BENGAL_BOUNDS,
  BAY_OF_BENGAL_FOCUS,
  GRID_STEP,
  bayOfBengalPolygonFeature,
  isInBayOfBengal,
  mapGridToPoints,
  snapToGrid,
} from '../utils/globe';
import type { MapPayload } from '../types/contracts';

function fakePayload(): MapPayload {
  return {
    region: 'bay_of_bengal',
    date: '2023-09-01',
    coordinates: { latitude: [5.0, 5.25, 5.5], longitude: [80.0, 80.25, 80.5] },
    channel: 'temperature',
    depth: 100,
    values: [
      [28.5, 28.7, null],
      [28.1, null, 27.9],
      [27.5, 27.6, 27.8],
    ],
    sigma: [
      [0.4, 0.5, null],
      [0.6, null, 0.5],
      [0.4, 0.4, 0.3],
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

describe('globe utils (real 0.25° grid, real BoB bounds)', () => {
  it('exposes the locked 0.25° step', () => {
    expect(GRID_STEP).toBe(0.25);
  });

  it('focuses the Bay of Bengal at its real geographic center', () => {
    // Bounds: lon 80..100, lat 5..22 (config/regions.yaml). Center = 13.5N, 90E.
    expect(BAY_OF_BENGAL_BOUNDS).toEqual({ latMin: 5, latMax: 22, lonMin: 80, lonMax: 100 });
    expect(BAY_OF_BENGAL_FOCUS.lat).toBeCloseTo(13.5, 5);
    expect(BAY_OF_BENGAL_FOCUS.lng).toBeCloseTo(90, 5);
  });

  it('maps only real ocean cells to globe points (null land skipped, no fake cells)', () => {
    const points = mapGridToPoints(fakePayload(), 'temperature');
    // 3x3 = 9 cells minus 2 land nulls = 7 ocean points.
    expect(points).toHaveLength(7);
    for (const p of points) {
      expect(p.value).not.toBeNull();
      expect(typeof p.color).toBe('string');
    }
  });

  it('snaps hover coordinates to the real grid (backend semantics)', () => {
    const payload = fakePayload();
    const snapped = snapToGrid(5.1, 80.1, payload.coordinates);
    expect(snapped).toEqual({ lat: 5.0, lon: 80.0 });
  });

  it('identifies in-bounds vs out-of-bounds coordinates', () => {
    expect(isInBayOfBengal(15.25, 87.5)).toBe(true);
    expect(isInBayOfBengal(0, 0)).toBe(false);
  });

  it('builds a valid closed GeoJSON polygon from the real BoB bounds', () => {
    const feature = bayOfBengalPolygonFeature();
    expect(feature.type).toBe('Feature');
    expect(feature.geometry.type).toBe('Polygon');
    const ring = feature.geometry.coordinates[0];
    // Closed ring: 4 corners + repeat of the first, in [lon, lat] order.
    expect(ring).toHaveLength(5);
    expect(ring[0]).toEqual(ring[4]);
    expect(ring[0]).toEqual([BAY_OF_BENGAL_BOUNDS.lonMin, BAY_OF_BENGAL_BOUNDS.latMin]);
  });
});
