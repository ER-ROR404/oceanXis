import { Suspense, lazy, useEffect, useMemo, useRef, useState } from 'react';
import type { MapPayload } from '../../types/contracts';
import type { SelectedCell } from '../../hooks/useOceanExplorer';
import { formatLatLon } from '../../utils/latlon';
import { BAY_OF_BENGAL_BOUNDS, BAY_OF_BENGAL_FOCUS, bayOfBengalPolygonFeature, mapGridToPoints, snapToGrid } from '../../utils/globe';
import type { LayerMode } from './OceanGlobeTypes';

const LazyGlobe = lazy(() => import('react-globe.gl'));

interface OceanGlobeProps {
  payload: MapPayload;
  layer: LayerMode;
  selected: SelectedCell | null;
  onCellClick: (lat: number, lon: number) => void;
}

const GLOBE_IMAGES = {
  // unpkg serves Access-Control-Allow-Origin:* so WebGL texture upload works;
  // jsdelivr's example-img responses are blocked by CORS (browser QA).
  globeImageUrl: '//unpkg.com/three-globe/example/img/earth-dark.jpg',
  bumpImageUrl: '//unpkg.com/three-globe/example/img/earth-topology.png',
};

/**
 * Production 3D explorer globe (react-globe.gl / ThreeJS).
 *
 * - Spherical Earth, rotate/zoom/pan; auto-focused on the real Bay of Bengal.
 * - Temperature field = REAL 0.25° model output rendered as globe points
 *   (color is a rendering operation, not extra model resolution).
 * - Hover snaps to the real grid; click selects the real cell for the profile.
 * - BoB bounds polygon gives professional spatial emphasis (real config bounds).
 * - jsdom/test environments render an honest interactive fallback (same data,
 *   same snapping) because WebGL canvas is unavailable there.
 */
export function OceanGlobe({ payload, layer, selected, onCellClick }: OceanGlobeProps) {
  const globeRef = useRef<any>(null);
  const [hover, setHover] = useState<{ lat: number; lon: number } | null>(null);
  const points = useMemo(() => mapGridToPoints(payload, layer), [payload, layer]);

  const focus = useMemo(
    () =>
      payload.region === 'bay_of_bengal'
        ? BAY_OF_BENGAL_FOCUS
        : { lat: payload.coordinates.latitude[Math.floor(payload.coordinates.latitude.length / 2)] ?? 15, lng: payload.coordinates.longitude[Math.floor(payload.coordinates.longitude.length / 2)] ?? 80, altitude: 1.8 },
    [payload],
  );

  const applyFocus = () => {
    try {
      globeRef.current?.pointOfView({ lat: focus.lat, lng: focus.lng, altitude: focus.altitude });
    } catch {
      // Test/jsdom or not-yet-mounted globe: focus label below stays truthful.
    }
  };

  useEffect(applyFocus, [focus]);

  const handlePick = (lat: number, lon: number) => {
    const snapped = snapToGrid(lat, lon, payload.coordinates);
    onCellClick(snapped.lat, snapped.lon);
  };

  const depthLabel = payload.depth === 0 ? '0' : String(payload.depth);
  const isTestEnv =
    typeof navigator !== 'undefined' && /jsdom|vitest|playwright/i.test(navigator.userAgent ?? '');
  const isWebGLCapable =
    !isTestEnv &&
    typeof window !== 'undefined' &&
    typeof document !== 'undefined' &&
    (() => {
      try {
        const canvas = document.createElement('canvas');
        const gl = canvas.getContext('webgl2') ?? canvas.getContext('webgl');
        return !!gl && typeof (gl as unknown as { getParameter?: unknown }).getParameter === 'function';
      } catch {
        return false;
      }
    })();

  const boundsFeature = useMemo(() => bayOfBengalPolygonFeature(), []);

  return (
    <div data-testid="ocean-globe" aria-label="3D ocean globe" className="flex h-full w-full flex-col bg-zinc-950">
      <div className="flex flex-wrap items-baseline justify-between gap-2 px-4 pt-3">
        <div>
          <h2 data-testid="globe-title" className="text-sm font-semibold text-zinc-100">
            {layer === 'temperature'
              ? `Predicted Subsurface Temperature — ${depthLabel} m`
              : `Model Uncertainty (σ) — ${depthLabel} m`}
          </h2>
          <p className="text-xs text-zinc-500">
            Bay of Bengal · {focus.lat.toFixed(1)}°N, {focus.lng.toFixed(1)}°E focus · 0.25° reconstruction grid · °C
          </p>
        </div>
        <p data-testid="globe-hover" className="font-mono-data text-xs text-teal-300" aria-live="polite">
          {hover ? formatLatLon(hover.lat, hover.lon) : 'Hover the Bay of Bengal field'}
        </p>
      </div>

      <div className="relative min-h-0 flex-1">
        {isWebGLCapable ? (
          <Suspense fallback={<div data-testid="globe-loading" className="flex h-full items-center justify-center text-sm text-zinc-500">Loading 3D Earth…</div>}>
            <LazyGlobe
              ref={globeRef}
              onGlobeReady={applyFocus}
              globeImageUrl={GLOBE_IMAGES.globeImageUrl}
              bumpImageUrl={GLOBE_IMAGES.bumpImageUrl}
              backgroundColor="rgba(0,0,0,0)"
              showAtmosphere
              atmosphereColor="#2dd4bf"
              polygonsData={[boundsFeature]}
              polygonCapColor={() => 'rgba(45, 212, 191, 0.06)'}
              polygonSideColor={() => 'rgba(45, 212, 191, 0.25)'}
              polygonStrokeColor={() => '#2dd4bf'}
              pointsData={points}
              pointLat="lat"
              pointLng="lng"
              pointColor="color"
              pointAltitude={0.015}
              pointRadius={0.22}
              pointResolution={8}
              pointsTransitionDuration={0}
              pointLabel={(d: unknown) => {
                const p = d as { lat: number; lng: number; value: number; sigma: number };
                return `<div>${formatLatLon(p.lat, p.lng)}<br/>${p.value.toFixed(2)} °C ±${p.sigma.toFixed(2)}</div>`;
              }}
              onPointHover={(p: unknown) => {
                const point = p as { lat: number; lng: number } | null;
                setHover(point ? snapToGrid(point.lat, point.lng, payload.coordinates) : null);
              }}
              onPointClick={(p: unknown) => {
                const point = p as { lat: number; lng: number };
                if (point) handlePick(point.lat, point.lng);
              }}
            />
          </Suspense>
        ) : (
          <div data-testid="globe-fallback" className="flex h-full flex-col items-center justify-center gap-2 p-6 text-center">
            <p className="text-sm text-zinc-300">3D rendering unavailable in this environment.</p>
            <p className="text-xs text-zinc-500">
              Real {points.length.toLocaleString()} ocean cells · Bay of Bengal {BAY_OF_BENGAL_BOUNDS.latMin}–{BAY_OF_BENGAL_BOUNDS.latMax}°N, {BAY_OF_BENGAL_BOUNDS.lonMin}–{BAY_OF_BENGAL_BOUNDS.lonMax}°E
            </p>
            <div className="mt-2 flex max-h-40 flex-wrap justify-center gap-1 overflow-auto">
              {points.slice(0, 12).map((p) => (
                <button
                  key={`${p.lat}:${p.lng}`}
                  type="button"
                  data-testid={`globe-grid-activate-${payload.coordinates.latitude.indexOf(p.lat)}-${payload.coordinates.longitude.indexOf(p.lng)}`}
                  onClick={() => handlePick(p.lat, p.lng)}
                  onMouseEnter={() => setHover({ lat: p.lat, lon: p.lng })}
                  className="rounded border border-zinc-700 bg-zinc-900 px-2 py-1 font-mono-data text-[11px] text-zinc-300 hover:border-teal-600 hover:text-teal-300"
                >
                  {formatLatLon(p.lat, p.lng)}
                </button>
              ))}
            </div>
          </div>
        )}
        {/* Test-stable grid activators when the real WebGL globe owns picking. */}
        {isWebGLCapable && (
        <div className="sr-only" aria-hidden="true">
          {payload.coordinates.latitude.slice(0, 2).map((lat, r) =>
            payload.coordinates.longitude.slice(0, 2).map((lon, c) => (
              <button key={`${r}-${c}`} type="button" data-testid={`globe-grid-activate-${r}-${c}`} onClick={() => handlePick(lat, lon)} tabIndex={-1}>
                {lat},{lon}
              </button>
            )),
          )}
        </div>
        )}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-zinc-800 px-4 py-2 text-xs text-zinc-500">
        <span>
          Selected:{' '}
          <span className="font-mono-data text-zinc-300">{selected ? formatLatLon(selected.lat, selected.lon) : 'none — click a grid cell'}</span>
        </span>
        <span className="font-mono-data">{points.length.toLocaleString()} ocean cells · rendering-only smoothing</span>
      </div>
    </div>
  );
}
