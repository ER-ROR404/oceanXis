import { useEffect, useState } from 'react';
import { ControlPanel } from '../components/controls/ControlPanel';
import { DateBar } from '../components/controls/DateBar';
import { DepthRail } from '../components/controls/DepthRail';
import { OceanMap, type LayerMode, type MapHover } from '../components/map/OceanMap';
import { MapColorbar } from '../components/map/MapColorbar';
import { DepthColumn } from '../components/depth/DepthColumn';
import { ProfileChart } from '../components/profile/ProfileChart';
import { ExplainLocation } from '../components/profile/ExplainLocation';
import type { ExplainerInput } from '../utils/explain';
import { REGION_LABELS, type OceanExplorer } from '../hooks/useOceanExplorer';
import { formatLatLon } from '../utils/latlon';

type ProfileView = 'curve' | 'levels';

/**
 * Reference-viewer style explorer: a full-viewport Bay of Bengal map with
 * floating title/colorbar, control panel, depth rail and date stepper.
 * Click a cell → value popup + profile overlay. Driven by /api/v1.
 */
export function ExplorerPage({ explorer }: { explorer: OceanExplorer }) {
  const {
    region, date, depth, dates, availability, availabilityState,
    scope, mapEnvelope, profileEnvelope, selected,
    busyMap, busyProfile, setRegion, setDate, setDepth, selectCell, clearSelection,
  } = explorer;
  const [layer, setLayer] = useState<LayerMode>('temperature');
  const [profileView, setProfileView] = useState<ProfileView>('curve');
  const [hover, setHover] = useState<MapHover | null>(null);
  const [resetSignal, setResetSignal] = useState(0);
  const mapPayload = mapEnvelope?.payload ?? null;
  const profilePayload = profileEnvelope?.payload ?? null;

  useEffect(() => {
    setHover(null);
  }, [mapEnvelope]);

  const mapTitle =
    layer === 'temperature'
      ? `Predicted Subsurface Temperature · ${depth} m`
      : `Prediction Uncertainty · ${depth} m`;

  const fieldArea = () => {
    if (dates.length === 0 && availabilityState === 'loading') {
      return <div data-testid="map-skeleton" className="flex h-full items-center justify-center text-sm text-zinc-500">Loading available dates...</div>;
    }
    if (dates.length === 0 && availabilityState === 'error') {
      return <div data-testid="map-error-state" className="flex h-full items-center justify-center text-sm text-zinc-500">Could not reach the OceanEmbed backend.</div>;
    }
    if (dates.length === 0) {
      const scopeLabel = scope ? REGION_LABELS[scope.region] : null;
      return (
        <div data-testid="empty-region-state" className="flex h-full flex-col items-center justify-center gap-3 p-6 text-center">
          <p className="text-sm text-zinc-300">
            No data available for <span className="font-semibold">{REGION_LABELS[region]}</span>.
          </p>
          {scope && (
            <button type="button" onClick={() => setRegion(scope.region)} className="rounded-md border border-teal-800 bg-teal-950/40 px-3 py-1.5 text-sm text-teal-300">
              Return to {scopeLabel}
            </button>
          )}
        </div>
      );
    }
    if (busyMap && !mapPayload) {
      return <div data-testid="map-skeleton" className="flex h-full items-center justify-center text-sm text-zinc-500">Loading temperature field...</div>;
    }
    if (!mapPayload) {
      return <div data-testid="map-error-state" className="flex h-full items-center justify-center text-sm text-zinc-500">The field could not be loaded.</div>;
    }
    return (
      <>
        <OceanMap payload={mapPayload} layer={layer} selected={selected} onCellClick={selectCell} onHover={setHover} resetSignal={resetSignal} />
        {hover && (
          <div
            data-testid="map-hover"
            aria-live="polite"
            className="pointer-events-none absolute z-[700] rounded-md border border-zinc-700 bg-zinc-950/90 px-2.5 py-1.5 font-mono-data text-xs leading-tight text-zinc-100"
            style={{ left: Math.min(hover.x + 14, 240), top: Math.max(hover.y - 10, 8) }}
          >
            <div className="text-teal-300">{formatLatLon(hover.lat, hover.lon)}</div>
            <div>{hover.value === null ? 'land' : `${hover.value.toFixed(2)} °C`}</div>
            <div className="text-zinc-500">{mapPayload.depth} m</div>
          </div>
        )}
      </>
    );
  };

  const profilePanel = () => {
    if (!selected) return null;
    let body: React.ReactNode;
    if (busyProfile && !profilePayload) {
      body = <div data-testid="profile-skeleton" className="flex h-64 items-center justify-center text-sm text-zinc-500">Reconstructing profile…</div>;
    } else if (!profilePayload) {
      body = <p className="text-sm text-zinc-400">No profile here. The point may be land or an uncovered cell.</p>;
    } else {
      const explainInput: ExplainerInput = {
        region: profilePayload.region,
        date: profilePayload.date,
        depths: profilePayload.depths,
        temps: profilePayload.temperatures,
        sigma: profilePayload.sigma,
      };
      body = (
        <div className="space-y-3">
          <div data-testid="selected-cell">
            <p data-testid="profile-location" className="font-mono-data text-sm font-semibold text-teal-300">
              {formatLatLon(profilePayload.lat, profilePayload.lon)}
              <span className="mx-2 font-normal text-zinc-700">|</span>
              <span className="font-normal">{date}</span>
            </p>
          </div>
          <div className="rounded-lg border border-zinc-800 bg-zinc-950/80 p-3">
            <ProfileChart depths={profilePayload.depths} temps={profilePayload.temperatures} sigma={profilePayload.sigma} />
          </div>
          <div className="flex gap-2" role="group" aria-label="Profile values">
            <button
              type="button"
              aria-expanded={profileView === 'levels'}
              onClick={() => setProfileView(profileView === 'levels' ? 'curve' : 'levels')}
              className="rounded-md border border-zinc-700 bg-zinc-900 px-3 py-1.5 text-xs text-zinc-300 hover:text-zinc-100"
            >
              {profileView === 'levels' ? 'Hide values' : 'Exact values'}
            </button>
          </div>
          {profileView === 'levels' && (
            <DepthColumn depths={profilePayload.depths} temps={profilePayload.temperatures} sigma={profilePayload.sigma} />
          )}
          <ExplainLocation input={explainInput} />
        </div>
      );
    }
    return (
      <aside aria-label="Location analysis" className="absolute bottom-3 right-20 top-3 z-[600] w-[min(360px,calc(100%-6rem))] overflow-y-auto rounded-lg border border-zinc-700/80 bg-zinc-950/92 p-4 backdrop-blur-sm">
        <div className="mb-2 flex items-baseline justify-between gap-2">
          <div>
            <h2 className="text-sm font-semibold text-zinc-200">Subsurface temperature</h2>
            <p className="text-[11px] text-zinc-500">15 model levels · 0–1000 m</p>
          </div>
          <button
            type="button"
            aria-label="Close profile panel"
            onClick={clearSelection}
            className="rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1 text-xs text-zinc-400 hover:text-zinc-100"
          >
            ×
          </button>
        </div>
        {body}
      </aside>
    );
  };

  const cellCount = (() => {
    if (!mapPayload) return null;
    let n = 0;
    for (const row of mapPayload.values) for (const v of row) if (v !== null) n += 1;
    return n;
  })();

  return (
    <div data-testid="explorer-page" className="flex min-h-0 flex-1 flex-col">
      <div className="relative min-h-[540px] flex-1">
        <div className="absolute inset-0">
          {fieldArea()}
        </div>

        {mapPayload && (
          <div className="pointer-events-none absolute left-1/2 top-3 z-[500] flex -translate-x-1/2 flex-col items-center gap-1.5">
            <div className="text-center">
              <h2 data-testid="map-title" className="text-base font-semibold tracking-tight text-zinc-100 drop-shadow-[0_1px_4px_rgba(0,0,0,0.9)]">{mapTitle}</h2>
              <p data-testid="map-subtitle" className="text-xs text-zinc-400 drop-shadow-[0_1px_3px_rgba(0,0,0,0.9)]">Bay of Bengal · 0.25° reconstruction grid</p>
            </div>
            <div className="pointer-events-auto">
              <MapColorbar layer={layer} values={mapPayload.values} sigma={mapPayload.sigma} />
            </div>
          </div>
        )}

        <div className="absolute left-3 top-3 z-[500]">
          <ControlPanel
            layer={layer}
            region={region}
            coordinates={mapPayload?.coordinates ?? null}
            onLayerChange={setLayer}
            onRegionChange={setRegion}
            onPick={selectCell}
            onResetView={() => setResetSignal((n) => n + 1)}
          />
        </div>

        <div className="absolute right-3 top-1/2 z-[500] max-h-[70%] -translate-y-1/2 overflow-y-auto">
          <DepthRail depth={depth} onDepthChange={setDepth} />
        </div>

        <div className="absolute bottom-3 left-1/2 z-[500] -translate-x-1/2">
          <DateBar date={date} dates={dates} onDateChange={setDate} />
        </div>

        {mapPayload && !selected && (
          <div className="pointer-events-none absolute bottom-3 left-3 z-[500] rounded-md border border-zinc-700/80 bg-zinc-950/85 px-3 py-1.5 text-xs text-zinc-400 backdrop-blur-sm">
            Click the map to inspect the 0–1000 m profile.
          </div>
        )}

        {profilePanel()}
      </div>

      <div className="border-t border-zinc-800 bg-zinc-950/80">
        <div className="mx-auto flex w-full max-w-[1400px] flex-wrap items-center gap-x-4 gap-y-1 px-4 py-2 font-mono-data text-[11px] text-zinc-500 md:px-6">
          {mapPayload && cellCount !== null && (
            <span data-testid="map-stats" className="text-zinc-300">
              {depth} m · {cellCount.toLocaleString()} valid ocean cells · 0.25° grid · {date}
            </span>
          )}
          <span className="text-zinc-600">hybrid_v1</span>
          {(() => {
            const entry = availability?.regions.find((r) => r.region === region);
            return entry?.status === 'available' && entry.date_start
              ? <span data-testid="availability-window" className="text-teal-400/90">{REGION_LABELS[region]} · {entry.date_start} → {entry.date_end}</span>
              : null;
          })()}
        </div>
      </div>
    </div>
  );
}
