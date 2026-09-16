import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render } from '@testing-library/react';

// Mock Leaflet before importing components that use it. vi.hoisted keeps the
// mock factories free of top-level closure references (vitest hoisting).
const { mapInstance, rectangleMock, overlayPane, popupMock } = vi.hoisted(() => {
  const overlayPane = document.createElement('div');
  const popupInstance = {
    setLatLng: vi.fn().mockReturnThis(),
    setContent: vi.fn().mockReturnThis(),
    openOn: vi.fn().mockReturnThis(),
  };
  const popupMock = vi.fn(() => popupInstance);
  const mapInstance = {
    setView: vi.fn().mockReturnThis(),
    on: vi.fn().mockReturnThis(),
    off: vi.fn().mockReturnThis(),
    remove: vi.fn().mockReturnThis(),
    invalidateSize: vi.fn().mockReturnThis(),
    fitBounds: vi.fn().mockReturnThis(),
    closePopup: vi.fn().mockReturnThis(),
    getSize: vi.fn(() => ({ x: 800, y: 600 })),
    getPanes: vi.fn(() => ({ overlayPane })),
    latLngToContainerPoint: vi.fn(([lat, lon]: [number, number]) => ({ x: lon, y: -lat })),
    containerPointToLayerPoint: vi.fn(([x, y]: [number, number]) => ({ x, y })),
  };
  const rectangleMock = vi.fn().mockImplementation(() => ({
    addTo: vi.fn(),
    remove: vi.fn(),
  }));
  return { mapInstance, rectangleMock, overlayPane, popupMock };
});

vi.mock('leaflet', () => ({
  default: {
    map: vi.fn(() => mapInstance),
    tileLayer: vi.fn(() => ({ addTo: vi.fn() })),
    rectangle: rectangleMock,
    popup: popupMock,
    control: { zoom: vi.fn(() => ({ addTo: vi.fn() })) },
  },
  map: vi.fn(() => mapInstance),
  tileLayer: vi.fn(() => ({ addTo: vi.fn() })),
  rectangle: rectangleMock,
  popup: popupMock,
  control: { zoom: vi.fn(() => ({ addTo: vi.fn() })) },
}));

import { viridis, uncertaintyColor, rgbString, nearestIndex, fieldDomain } from '../components/map/colorScales';
import { OceanMap, cellBounds, gridBounds } from '../components/map/OceanMap';
import type { MapPayload } from '../types/contracts';

const PAYLOAD: MapPayload = {
  region: 'bay_of_bengal',
  date: '2023-06-15',
  coordinates: { latitude: [10.0, 10.25], longitude: [88.0, 88.25, 88.5] },
  channel: 'temperature',
  depth: 0,
  values: [
    [29.1, 29.0, 28.9],
    [28.8, 28.7, 28.6],
  ],
  sigma: [
    [0.4, 0.4, 0.5],
    [0.5, 0.5, 0.6],
  ],
  metadata: {
    model_version: 'hybrid_v1',
    data_source: 'test',
    preprocessing_version: 'v1',
    cached: false,
    timestamp: '2026-09-06T12:00:00Z',
  },
};

describe('colorScales', () => {
  it('viridis spans dark purple (0) to bright yellow (1)', () => {
    const lo = viridis(0);
    const hi = viridis(1);
    expect(lo[0] < hi[0]).toBe(true);
    expect(hi[2]).toBeLessThan(lo[2]);
    expect(hi[1]).toBeGreaterThan(100);
  });

  it('uncertainty goes yellow (low) to red (high)', () => {
    expect(rgbString(uncertaintyColor(0))).toMatch(/^rgb\(/);
    const [r0, g0, b0] = uncertaintyColor(0);
    const [r1, g1, b1] = uncertaintyColor(1);
    // Yellow->red: red stays hot, green and blue collapse.
    expect(r0).toBeGreaterThan(200);
    expect(r1).toBeGreaterThan(200);
    expect(g1).toBeLessThan(g0);
    expect(b1).toBeLessThan(b0);
  });

  it('clamps out-of-range inputs', () => {
    expect(viridis(-5)).toEqual(viridis(0));
    expect(viridis(2)).toEqual(viridis(1));
  });
});

describe('nearestIndex', () => {
  it('returns the closest grid-center index', () => {
    expect(nearestIndex([10.0, 10.25, 10.5], 10.2)).toBe(1);
    expect(nearestIndex([10.0, 10.25, 10.5], 11.0)).toBe(2);
  });
});

describe('OceanMap', () => {
  beforeEach(() => {
    (Object.values(mapInstance) as ReturnType<typeof vi.fn>[]).forEach((fn) => {
      if (typeof fn.mockClear === 'function') fn.mockClear();
    });
    rectangleMock.mockClear();
    overlayPane.innerHTML = '';
  });

  it('renders the Leaflet host div with an aria label', () => {
    const onCellClick = vi.fn();
    const { container } = render(
      <OceanMap payload={PAYLOAD} layer="temperature" onCellClick={onCellClick} />,
    );
    expect(container.querySelector('[aria-label="Ocean map"]')).not.toBeNull();
  });

  it('attaches a single canvas layer (no image overlays, no stretched <img>)', () => {
    render(<OceanMap payload={PAYLOAD} layer="temperature" onCellClick={() => {}} />);
    expect(overlayPane.querySelectorAll('canvas')).toHaveLength(1);
  });

  it('reuses the same canvas across layer and payload switches', () => {
    const { rerender } = render(<OceanMap payload={PAYLOAD} layer="temperature" onCellClick={() => {}} />);
    rerender(<OceanMap payload={PAYLOAD} layer="uncertainty" onCellClick={() => {}} />);
    rerender(<OceanMap payload={{ ...PAYLOAD, date: '2023-06-16' }} layer="uncertainty" onCellClick={() => {}} />);
    // One canvas element: values swap, nothing reattaches.
    expect(overlayPane.querySelectorAll('canvas')).toHaveLength(1);
    expect(mapInstance.invalidateSize).toHaveBeenCalled();
  });

  it('fits the viewport to the served domain on load, not on depth-only change', () => {
    const { rerender } = render(<OceanMap payload={PAYLOAD} layer="temperature" onCellClick={() => {}} />);
    expect(mapInstance.fitBounds).toHaveBeenCalledTimes(1);
    // Same region+date, new depth slice: viewport untouched (§35).
    rerender(<OceanMap payload={{ ...PAYLOAD, depth: 200 }} layer="temperature" onCellClick={() => {}} />);
    expect(mapInstance.fitBounds).toHaveBeenCalledTimes(1);
    // New date: refit to the domain (§5).
    rerender(<OceanMap payload={{ ...PAYLOAD, date: '2023-06-16' }} layer="temperature" onCellClick={() => {}} />);
    expect(mapInstance.fitBounds).toHaveBeenCalledTimes(2);
  });

  it('refits on an explicit reset-view signal without reattaching the canvas', () => {
    const { rerender } = render(<OceanMap payload={PAYLOAD} layer="temperature" resetSignal={0} onCellClick={() => {}} />);
    const fits = (mapInstance.fitBounds as ReturnType<typeof vi.fn>).mock.calls.length;
    rerender(<OceanMap payload={PAYLOAD} layer="temperature" resetSignal={1} onCellClick={() => {}} />);
    expect((mapInstance.fitBounds as ReturnType<typeof vi.fn>).mock.calls.length).toBe(fits + 1);
    expect(overlayPane.querySelectorAll('canvas')).toHaveLength(1);
  });

  it('registers click + hover handlers that resolve the nearest cell', () => {
    render(<OceanMap payload={PAYLOAD} layer="temperature" selected={null} onCellClick={() => {}} onHover={() => {}} />);
    expect(mapInstance.on).toHaveBeenCalledWith('click', expect.any(Function));
    expect(mapInstance.on).toHaveBeenCalledWith('mousemove', expect.any(Function));
  });

  it('reports hovered cell value + sigma for the compact tooltip', () => {
    const onHover = vi.fn();
    render(<OceanMap payload={PAYLOAD} layer="temperature" selected={null} onCellClick={() => {}} onHover={onHover} />);
    const move = mapInstance.on.mock.calls.find((c) => c[0] === 'mousemove')?.[1] as
      | ((e: { latlng: { lat: number; lng: number }; containerPoint: { x: number; y: number } }) => void)
      | undefined;
    expect(move).toBeDefined();
    move!({ latlng: { lat: 10.2, lng: 88.2 }, containerPoint: { x: 50, y: 60 } });
    expect(onHover).toHaveBeenCalledWith(
      expect.objectContaining({ lat: 10.25, lon: 88.25, value: 28.7, sigma: 0.5, x: 50, y: 60 }),
    );
  });

  it('draws no domain frame: only the selected cell gets a rectangle', () => {
    render(<OceanMap payload={PAYLOAD} layer="temperature" selected={null} onCellClick={() => {}} onHover={() => {}} />);
    // No box around the field; valid cells alone define the visible layer.
    expect(rectangleMock).not.toHaveBeenCalled();
    expect(gridBounds(PAYLOAD.coordinates)).toEqual([
      [10.0, 88.0],
      [10.25, 88.5],
    ]);
  });

  it('draws a selected-cell rectangle snapped to the 0.25° cell', () => {
    render(<OceanMap payload={PAYLOAD} layer="temperature" selected={{ lat: 10.25, lon: 88.25 }} onCellClick={() => {}} onHover={() => {}} />);
    expect(rectangleMock).toHaveBeenCalledWith(
      expect.arrayContaining([expect.arrayContaining([expect.any(Number), expect.any(Number)])]),
      expect.objectContaining({ color: '#2dd4bf' }),
    );
    expect(cellBounds(10.25, 88.25)).toEqual([
      [10.125, 88.125],
      [10.375, 88.375],
    ]);
  });
  it('opens a value popup with the snapped coordinate and reading on click', () => {
    const onCellClick = vi.fn();
    render(<OceanMap payload={PAYLOAD} layer="temperature" onCellClick={onCellClick} />);
    popupMock.mockClear();
    const handler = mapInstance.on.mock.calls.find((c) => c[0] === 'click')?.[1] as (e: { latlng: { lat: number; lng: number } }) => void;
    handler({ latlng: { lat: 10.2, lng: 88.2 } });
    expect(popupMock).toHaveBeenCalledTimes(1);
    expect(onCellClick).toHaveBeenCalledWith(10.25, 88.25);
  });

  it('resolves a click to the nearest grid cell and reports it via onCellClick', () => {
    const onCellClick = vi.fn();
    render(<OceanMap payload={PAYLOAD} layer="temperature" onCellClick={onCellClick} />);
    const handler = mapInstance.on.mock.calls.find((c) => c[0] === 'click')?.[1] as (e: { latlng: { lat: number; lng: number } }) => void;
    handler({ latlng: { lat: 10.2, lng: 88.2 } });
    expect(onCellClick).toHaveBeenCalledWith(10.25, 88.25);
  });

  it('fieldDomain uses valid ocean values exactly (no padding artifacts)', () => {
    expect(fieldDomain([[null, null]])).toEqual({ min: 0, max: 1 });
    const uniform = fieldDomain([[10.0, 10.0]]);
    expect(uniform.min).toBeLessThan(10.0);
    expect(uniform.max).toBeGreaterThan(10.0);
    // Null land is excluded; min/max are the true valid extremes.
    expect(fieldDomain([[null, 20.0], [30.0, null]])).toEqual({ min: 20.0, max: 30.0 });
  });
});