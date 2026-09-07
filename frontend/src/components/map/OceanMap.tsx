import { useEffect, useRef } from 'react';
import L from 'leaflet';
import type { MapPayload } from '../../types/contracts';
import { rasterize, nearestIndex } from './colorScales';

export type LayerMode = 'temperature' | 'uncertainty';

interface OceanMapProps {
  payload: MapPayload;
  layer: LayerMode;
  onCellClick: (lat: number, lon: number) => void;
}

/**
 * Leaflet map showing the gridded temperature or uncertainty field.
 *
 * Temperature uses the viridis scale; uncertainty the yellow->red scale
 * (frontend/DESIGN.md). Land cells stay transparent (honest: no fabricated
 * values). A click on the field resolves the nearest grid cell and reports the
 * snapped center, matching backend profile semantics.
 */
export function OceanMap({ payload, layer, onCellClick }: OceanMapProps) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);
  const overlaysRef = useRef<Record<LayerMode, L.ImageOverlay | null>>({
    temperature: null,
    uncertainty: null,
  });
  const clickRef = useRef(onCellClick);
  clickRef.current = onCellClick;

  useEffect(() => {
    const host = hostRef.current;
    if (!host || mapRef.current) return;

    const map = L.map(host, { attributionControl: false, zoomControl: true }).setView(
      [15, 80],
      5,
    );
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; OpenStreetMap &copy; CARTO',
      maxZoom: 8,
    }).addTo(map);
    mapRef.current = map;

    map.on('click', (e: L.LeafletMouseEvent) => {
      const { payload: p } = { payload };
      const latRow = nearestIndex(p.coordinates.latitude, e.latlng.lat);
      const lonCol = nearestIndex(p.coordinates.longitude, e.latlng.lng);
      clickRef.current(
        p.coordinates.latitude[latRow],
        p.coordinates.longitude[lonCol],
      );
    });
  }, []);

  // Build the two raster overlays (temperature + uncertainty) whenever the
  // payload reference changes; then apply the active-layer visibility.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const { coordinates, values, sigma } = payload;
    const h = values.length;
    const w = values[0]?.length ?? 0;
    if (h === 0 || w === 0) return;

    const bounds = L.latLngBounds(
      [coordinates.latitude[h - 1], coordinates.longitude[0]],
      [coordinates.latitude[0], coordinates.longitude[w - 1]],
    );

    const makeOverlay = (mode: LayerMode): L.ImageOverlay => {
      const rgba = rasterize(values, sigma, mode);
      const url = renderDataUrl(rgba, w, h);
      return L.imageOverlay(url, bounds, { opacity: 0.85, interactive: true });
    };

    (Object.keys(overlaysRef.current) as LayerMode[]).forEach((m) => {
      const prev = overlaysRef.current[m];
      if (prev) {
        prev.remove();
        overlaysRef.current[m] = null;
      }
    });

    (['temperature', 'uncertainty'] as LayerMode[]).forEach((m) => {
      const ov = makeOverlay(m);
      overlaysRef.current[m] = ov;
      ov.addTo(map);
    });
    map.invalidateSize();
  }, [payload]);

  // Active-layer toggle: keep both rasters, show only the requested one.
  useEffect(() => {
    overlaysRef.current.temperature?.setOpacity(layer === 'temperature' ? 0.85 : 0);
    overlaysRef.current.uncertainty?.setOpacity(layer === 'uncertainty' ? 0.85 : 0);
  }, [layer]);

  useEffect(() => {
    return () => {
      mapRef.current?.remove();
      mapRef.current = null;
      overlaysRef.current = { temperature: null, uncertainty: null };
    };
  }, []);

  return (
    <div
      ref={hostRef}
      aria-label="Ocean map"
      className="h-[420px] w-full rounded-lg border border-zinc-800 bg-zinc-900"
    />
  );
}

/** Render the RGBA raster to an inline PNG data URL for imageOverlay. */
export function renderDataUrl(rgba: Uint8ClampedArray | null, w: number, h: number): string {
  if (rgba === null) return '';
  const canvas = document.createElement('canvas');
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext('2d');
  if (!ctx) return ''; // non-canvas test env: transparent overlay is honest no-op
  const img = ctx.createImageData(w, h);
  img.data.set(rgba);
  ctx.putImageData(img, 0, 0);
  return canvas.toDataURL('image/png');
}