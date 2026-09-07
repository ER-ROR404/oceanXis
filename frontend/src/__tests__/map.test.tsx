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

import { viridis, uncertaintyColor, rgbString, nearestIndex } from '../components/map/colorScales';
import { OceanMap } from '../components/map/OceanMap';
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
});