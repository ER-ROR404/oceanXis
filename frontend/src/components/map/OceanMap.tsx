import { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import type { Coordinates, MapPayload } from '../../types/contracts';
import type { SelectedCell } from '../../hooks/useOceanExplorer';
import { nearestIndex } from './colorScales';
import { CellCanvas, buildFieldGrid, type CanvasMapLike } from './CellCanvasLayer';
import { GRID_STEP } from '../../utils/globe';

export type LayerMode = 'temperature' | 'uncertainty';

export interface MapHover {
  lat: number;
  lon: number;
  value: number | null;
  sigma: number | null;
  /** Container pixel position for the tooltip. */
  x: number;
  y: number;
}

type SnappedCell = { lat: number; lon: number; value: number | null; sigma: number | null };

/** Value popup at the clicked cell (reference-viewer point inspection). */
function openValuePopup(map: L.Map, cell: SnappedCell, payload: MapPayload): void {
  const reading =
    cell.value === null || cell.sigma === null
      ? 'no data'
      : `${cell.value.toFixed(2)} °C ±${cell.sigma.toFixed(2)}`;
  L.popup({ closeButton: true, maxWidth: 240 })
    .setLatLng([cell.lat, cell.lon])
    .setContent(
      `<div style="font-family:monospace;font-size:12px;line-height:1.5">` +
        `<div style="color:#2dd4bf;font-weight:600">${cell.lat.toFixed(2)}°N · ${cell.lon.toFixed(2)}°E</div>` +
        `<div>${reading}</div>` +
        `<div style="opacity:.6">${payload.depth} m · ${payload.date}</div></div>`,
    )
    .openOn(map);
}

interface OceanMapProps {
  payload: MapPayload;
  layer: LayerMode;
  selected?: SelectedCell | null;
  onCellClick: (lat: number, lon: number) => void;
  onHover?: (hover: MapHover | null) => void;
  /** Increment to refit the viewport to the reconstruction domain. */
  resetSignal?: number;
}

/** Leaflet bounds of one 0.25° cell centered on (lat, lon). */
export function cellBounds(lat: number, lon: number): [[number, number], [number, number]] {
  const half = GRID_STEP / 2;
  return [
    [lat - half, lon - half],
    [lat + half, lon + half],
  ];
}

/** Leaflet bounds of the full reconstruction grid (south-west, north-east). */
export function gridBounds(coordinates: Coordinates): [[number, number], [number, number]] {
  const lats = coordinates.latitude;
  const lons = coordinates.longitude;
  return [
    [Math.min(...lats), Math.min(...lons)],
    [Math.max(...lats), Math.max(...lons)],
  ];
}

function snapCell(payload: MapPayload, lat: number, lon: number): SnappedCell {
  const latRow = nearestIndex(payload.coordinates.latitude, lat);
  const lonCol = nearestIndex(payload.coordinates.longitude, lon);
  return {
    lat: payload.coordinates.latitude[latRow],
    lon: payload.coordinates.longitude[lonCol],
    value: payload.values[latRow]?.[lonCol] ?? null,
    sigma: payload.sigma[latRow]?.[lonCol] ?? null,
  };
}

/**
 * Leaflet map showing the gridded temperature or uncertainty field.
 *
 * The field is rendered by a projection-bound canvas layer that interpolates
 * between the real 0.25° cells — never a stretched raster image, never a
 * domain-frame box. Land and missing cells stay transparent, so the basemap
 * coastline shows through and the temperature layer hugs the coast. Click and
 * hover resolve the nearest grid cell and report the snapped center, matching
 * backend profile semantics. The selected cell is outlined with a teal
 * rectangle.
 */
export function OceanMap({ payload, layer, selected = null, onCellClick, onHover, resetSignal = 0 }: OceanMapProps) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);
  const cellLayerRef = useRef<CellCanvas | null>(null);
  const markerRef = useRef<L.Rectangle | null>(null);
  const payloadRef = useRef(payload);
  payloadRef.current = payload;
  const clickRef = useRef(onCellClick);
  clickRef.current = onCellClick;
  const layerRef = useRef(layer);
  layerRef.current = layer;
  const hoverRef = useRef<((hover: MapHover | null) => void) | null>(onHover ?? null);
  hoverRef.current = onHover ?? null;
  const fitKeyRef = useRef<string | null>(null);

  useEffect(() => {
    const host = hostRef.current;
    if (!host || mapRef.current) return;

    let map: L.Map | null = null;
    try {
      map = L.map(host, { attributionControl: false, zoomControl: false }).setView(
        [13.5, 90],
        5,
      );
      L.control.zoom({ position: 'bottomright' }).addTo(map);
      L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ',
        maxZoom: 10,
      }).addTo(map);
    } catch {
      return; // non-Leaflet test env: host div + legend still render honestly.
    }
    mapRef.current = map;

    const cells = new CellCanvas(null, { opacity: 0.85 });
    cells.attach(map as unknown as CanvasMapLike);
    cellLayerRef.current = cells;

    map.on('click', (e: L.LeafletMouseEvent) => {
      const current = payloadRef.current;
      const cell = snapCell(current, e.latlng.lat, e.latlng.lng);
      openValuePopup(map, cell, current);
      clickRef.current(cell.lat, cell.lon);
    });
    map.on('mousemove', (e: L.LeafletMouseEvent) => {
      if (!hoverRef.current) return;
      const cell = snapCell(payloadRef.current, e.latlng.lat, e.latlng.lng);
      hoverRef.current({ ...cell, x: e.containerPoint.x, y: e.containerPoint.y });
    });
    map.on('mouseout', () => {
      hoverRef.current?.(null);
    });
  }, []);

  // Field data: rebuild the interpolated color grid whenever the payload or
  // the active layer changes. The same canvas is reused — no reattach. Viewport
  // framing only on region/date change (user pan/zoom kept).
  useEffect(() => {
    const map = mapRef.current;
    const cells = cellLayerRef.current;
    if (!map || !cells) return;
    const { coordinates, values, sigma } = payload;
    if (values.length === 0 || (values[0]?.length ?? 0) === 0) return;
    cells.setField(buildFieldGrid(values, sigma, coordinates.latitude, coordinates.longitude, layerRef.current));
    // Stale point popups never outlive their data.
    try {
      map.closePopup();
    } catch {
      // Non-Leaflet test env: no-op.
    }

    const fitKey = `${payload.region}|${payload.date}`;
    if (fitKeyRef.current !== fitKey) {
      fitKeyRef.current = fitKey;
      try {
        map.fitBounds(gridBounds(coordinates), { padding: [12, 12], animate: false });
      } catch {
        // Test envs without a real view: bounds still computed honestly.
      }
    }
    map.invalidateSize();
  }, [payload, layer]);

  // Explicit reset-view signal (§21): refit without touching data or cells.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || resetSignal <= 0) return;
    try {
      map.fitBounds(gridBounds(payloadRef.current.coordinates), { padding: [12, 12], animate: false });
    } catch {
      // Non-Leaflet test env: no-op.
    }
  }, [resetSignal]);

  // Selected-cell outline: redrawn without touching the field cells.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    markerRef.current?.remove();
    markerRef.current = null;
    if (!selected) return;
    const marker = L.rectangle(cellBounds(selected.lat, selected.lon), {
      color: '#2dd4bf',
      weight: 2,
      fill: false,
      interactive: false,
    });
    marker.addTo(map);
    markerRef.current = marker;
  }, [selected, payload]);

  useEffect(() => {
    return () => {
      markerRef.current?.remove();
      markerRef.current = null;
      cellLayerRef.current?.detach();
      cellLayerRef.current = null;
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, []);

  return (
    <div
      ref={hostRef}
      data-testid="map-host"
      aria-label="Ocean map"
      className="h-full min-h-[420px] w-full bg-zinc-900"
    />
  );
}
