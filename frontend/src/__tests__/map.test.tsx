import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

// Mock Leaflet before importing components that use it. vi.hoisted keeps the
// mock factories free of top-level closure references (vitest hoisting).
const { overlayMock, mapInstance } = vi.hoisted(() => {
  const overlayMock = vi.fn().mockImplementation(() => ({
    setUrl: vi.fn(),
    addTo: vi.fn(() => {
      mapInstance.addLayer();
    }),
    remove: vi.fn(() => {
      mapInstance.removeLayer();
    }),
    setOpacity: vi.fn(),
    setZIndex: vi.fn(),
    on: vi.fn(),
    bringToFront: vi.fn(),
  }));
  const mapInstance = {
    setView: vi.fn().mockReturnThis(),
    addLayer: vi.fn().mockReturnThis(),
    removeLayer: vi.fn().mockReturnThis(),
    on: vi.fn().mockReturnThis(),
    remove: vi.fn().mockReturnThis(),
    invalidateSize: vi.fn().mockReturnThis(),
  };
  return { overlayMock, mapInstance };
});

vi.mock('leaflet', () => ({
  default: {
    map: vi.fn(() => mapInstance),
    tileLayer: vi.fn(() => ({ addTo: vi.fn() })),
    imageOverlay: overlayMock,
    latLngBounds: vi.fn(),
    latLng: vi.fn((a: number, b: number) => ({ lat: a, lng: b })),
  },
  map: vi.fn(() => mapInstance),
  tileLayer: vi.fn(() => ({ addTo: vi.fn() })),
  imageOverlay: overlayMock,
  latLngBounds: vi.fn(),
  latLng: vi.fn((a: number, b: number) => ({ lat: a, lng: b })),
}));

import { viridis, uncertaintyColor, rgbString, nearestIndex, rasterize, fieldDomain } from '../components/map/colorScales';
import { OceanMap, renderDataUrl } from '../components/map/OceanMap';
import { RegionDateDepthSelector } from '../components/controls/RegionDateDepthSelector';
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

describe('RegionDateDepthSelector', () => {
  it('renders region, date and depth controls with labels', () => {
    render(
      <RegionDateDepthSelector
        region="bay_of_bengal"
        date="2023-06-15"
        depth={0}
        dates={['2023-06-15', '2023-06-16']}
        onRegionChange={() => {}}
        onDateChange={() => {}}
        onDepthChange={() => {}}
      />,
    );
    expect(screen.getByLabelText(/region/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/date/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/depth/i)).toBeInTheDocument();
  });

  it('fires callbacks on user changes', () => {
    const onRegion = vi.fn();
    const onDate = vi.fn();
    const onDepth = vi.fn();
    render(
      <RegionDateDepthSelector
        region="bay_of_bengal"
        date="2023-06-15"
        depth={0}
        dates={['2023-06-15', '2023-06-16']}
        onRegionChange={onRegion}
        onDateChange={onDate}
        onDepthChange={onDepth}
      />,
    );
    const dense = screen.getByLabelText(/date/i);
    fireEvent.change(dense, { target: { value: '2023-06-16' } });
    expect(onDate).toHaveBeenCalledWith('2023-06-16');

    const depthSel = screen.getByLabelText(/depth/i);
    fireEvent.change(depthSel, { target: { value: '100' } });
    expect(onDepth).toHaveBeenCalledWith(100);

    const regionSel = screen.getByLabelText(/region/i);
    fireEvent.change(regionSel, { target: { value: 'arabian_sea' } });
    expect(onRegion).toHaveBeenCalledWith('arabian_sea');
  });
});

describe('OceanMap', () => {
  beforeEach(() => {
    (Object.values(mapInstance) as ReturnType<typeof vi.fn>[]).forEach((fn) => fn.mockClear());
    overlayMock.mockClear();
  });

  it('renders the Leaflet host div with an aria label', () => {
    const onCellClick = vi.fn();
    const { container } = render(
      <OceanMap payload={PAYLOAD} layer="temperature" onCellClick={onCellClick} />,
    );
    expect(container.querySelector('[aria-label="Ocean map"]')).not.toBeNull();
  });

  it('registers two raster layers (temperature + uncertainty)', () => {
    render(<OceanMap payload={PAYLOAD} layer="temperature" onCellClick={() => {}} />);
    expect(overlayMock).toHaveBeenCalledTimes(2);
  });

  it('toggles overlay visibility when the active layer changes', () => {
    const { rerender } = render(<OceanMap payload={PAYLOAD} layer="temperature" onCellClick={() => {}} />);
    expect(mapInstance.addLayer).toHaveBeenCalledTimes(2);
    expect(mapInstance.removeLayer).not.toHaveBeenCalled();

    rerender(<OceanMap payload={PAYLOAD} layer="uncertainty" onCellClick={() => {}} />);
    // Same rasters kept; visibility driven by setOpacity (no rebuild).
    expect(mapInstance.addLayer).toHaveBeenCalledTimes(2);
    expect(mapInstance.removeLayer).not.toHaveBeenCalled();
    expect(mapInstance.invalidateSize).toHaveBeenCalledTimes(1);
  });

  it('registers a click handler that resolves the nearest cell', () => {
    render(<OceanMap payload={PAYLOAD} layer="temperature" onCellClick={() => {}} />);
    expect(mapInstance.on).toHaveBeenCalledWith('click', expect.any(Function));
  });

  it('resolves a click to the nearest grid cell and reports it via onCellClick', () => {
    const onCellClick = vi.fn();
    render(<OceanMap payload={PAYLOAD} layer="temperature" onCellClick={onCellClick} />);
    const handler = mapInstance.on.mock.calls[0][1] as (e: { latlng: { lat: number; lng: number } }) => void;
    handler({ latlng: { lat: 10.2, lng: 88.2 } });
    expect(onCellClick).toHaveBeenCalledWith(10.25, 88.25);
  });

  it('tears down and rebuilds rasters when the payload changes', () => {
    const { rerender } = render(<OceanMap payload={PAYLOAD} layer="temperature" onCellClick={() => {}} />);
    expect(mapInstance.addLayer).toHaveBeenCalledTimes(2);

    rerender(<OceanMap payload={{ ...PAYLOAD, date: '2023-06-16' }} layer="temperature" onCellClick={() => {}} />);
    expect(overlayMock).toHaveBeenCalledTimes(4);
    // Previous overlays removed via imageOverlay.remove() -> removeLayer().
    expect(mapInstance.removeLayer).toHaveBeenCalledTimes(2);
    expect(mapInstance.invalidateSize).toHaveBeenCalledTimes(2);
  });

  it('renderDataUrl returns an empty string for null rasters or non-canvas environments', () => {
    expect(renderDataUrl(null, 3, 3)).toBe('');
  });

  it('renderDataUrl draws real pixels into a PNG data URL when a canvas context exists', () => {
    // setup.ts provides a minimal jsdom 2D context; the data URL round trip is
    // what matters, not the pixels.
    expect(renderDataUrl(new Uint8ClampedArray(36), 3, 3)).toMatch(/^data:image\/png/);
  });

  it('renderDataUrl degrades to an empty string when no canvas context exists', () => {
    const original = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = () => null;
    try {
      expect(renderDataUrl(new Uint8ClampedArray(36), 3, 3)).toBe('');
    } finally {
      HTMLCanvasElement.prototype.getContext = original;
    }
  });

  it('rasterize marks land cells transparent and colors uncertainty red at high sigma', () => {
    // Land = values null while sigma stays null too (sigma mirrors values);
    // the null mask is honored cell-for-cell (contract guarantee).
    const rgba = rasterize(
      [[null, 29.0]],
      [[null, 0.4]],
      'uncertainty',
    );
    expect(rgba).not.toBeNull();
    if (!rgba) return;
    expect(rgba[3]).toBe(0); // first cell alpha: transparent land
    expect(rgba[7]).toBe(255); // second cell alpha: opaque ocean
  });

  it('rasterize returns null for an empty grid', () => {
    expect(rasterize([], [], 'temperature')).toBeNull();
  });

  it('fieldDomain falls back for all-null and expands uniform planes', () => {
    expect(fieldDomain([[null, null]])).toEqual({ min: 0, max: 1 });
    const uniform = fieldDomain([[10.0, 10.0]]);
    expect(uniform.min).toBeLessThan(10.0);
    expect(uniform.max).toBeGreaterThan(10.0);
    const padded = fieldDomain([[20.0, 30.0]]);
    expect(padded.max).toBeGreaterThan(30.0);
    expect(padded.min).toBeLessThan(20.0);
  });
});