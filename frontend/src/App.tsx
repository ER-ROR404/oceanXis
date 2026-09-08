import { useState } from 'react';
import { Header } from './components/layout/Header';
import { StatusBanner } from './components/layout/StatusBanner';
import { Footer } from './components/layout/Footer';
import { RegionDateDepthSelector } from './components/controls/RegionDateDepthSelector';
import { OceanMap, type LayerMode } from './components/map/OceanMap';
import { ProfileChart } from './components/profile/ProfileChart';
import { ExplainLocation } from './components/profile/ExplainLocation';
import { ArgoValidationPanel } from './components/validation/ArgoValidationPanel';
import { REGION_LABELS, useOceanExplorer } from './hooks/useOceanExplorer';
import { formatLatLon } from './utils/latlon';
import type { ExplainerInput } from './utils/explain';

const skeletonClass =
  'flex h-full min-h-56 items-center justify-center rounded-lg border border-zinc-800 bg-zinc-900/40 text-sm text-zinc-500';

/**
 * OceanEmbed dashboard (design spec §4-§10). Header + status strip + explorer
 * controls + Leaflet field + vertical profile/explainer + ARGO validation,
 * all driven by the typed /api/v1 client. Every degraded state is honest: the
 * status strip, per-panel empty states and the footer never fabricate data.
 */
export default function App() {
  const {
    region,
    date,
    depth,
    dates,
    availabilityState,
    latestAvailable,
    provenance,
    scope,
    mapEnvelope,
    profileEnvelope,
    selected,
    status,
    bannerDetail,
    busyMap,
    busyProfile,
    setRegion,
    setDate,
    setDepth,
    selectCell,
  } = useOceanExplorer();
  const [layer, setLayer] = useState<LayerMode>('temperature');

  const mapPayload = mapEnvelope?.payload ?? null;
  const profilePayload = profileEnvelope?.payload ?? null;

  const mapArea = () => {
    if (dates.length === 0 && availabilityState === 'loading') {
      return <div data-testid="map-skeleton" className={skeletonClass}>Loading available dates...</div>;
    }
    if (dates.length === 0 && availabilityState === 'error') {
      return (
        <div data-testid="map-error-state" className={skeletonClass}>
          Could not reach the OceanEmbed backend.
        </div>
      );
    }
    if (dates.length === 0) {
      const scopeLabel = scope ? REGION_LABELS[scope.region] : null;
      return (
        <div
          data-testid="empty-region-state"
          className="flex h-full min-h-56 flex-col items-center justify-center gap-3 rounded-lg border border-zinc-800 bg-zinc-900/40 p-6 text-center"
        >
          <p className="text-sm text-zinc-300">
            No data is currently available for <span className="font-semibold">{REGION_LABELS[region]}</span>.
          </p>
          {scope && (
            <button
              type="button"
              onClick={() => setRegion(scope.region)}
              className="rounded-md border border-teal-800 bg-teal-950/40 px-3 py-1.5 text-sm text-teal-300 focus:outline-none focus:ring-2 focus:ring-teal-600/40"
            >
              Return to {scopeLabel}
            </button>
          )}
        </div>
      );
    }
    if (busyMap && !mapPayload) {
      return <div data-testid="map-skeleton" className={skeletonClass}>Loading temperature field...</div>;
    }
    if (!mapPayload) {
      return (
        <div data-testid="map-error-state" className={skeletonClass}>
          The field could not be loaded. {bannerDetail ?? ''}
        </div>
      );
    }
    return <OceanMap payload={mapPayload} layer={layer} onCellClick={selectCell} />;
  };

  const layerCaption = () => {
    if (!mapPayload) return null;
    const field = layer === 'temperature' ? 'Temperature' : 'Uncertainty (sigma)';
    return (
      <p className="text-xs text-zinc-500">
        <span data-testid="field-caption">
          {field} at <span className="font-mono-data">{mapPayload.depth === 0 ? '0' : mapPayload.depth}</span> m
        </span>
        <span className="mx-2 text-zinc-700">|</span>
        <span className="font-mono-data">{mapPayload.date}</span>
        {latestAvailable && (
          <>
            <span className="mx-2 text-zinc-700">|</span>
            <span>
              Latest available: <span data-testid="latest-available" className="font-mono-data">{latestAvailable}</span>
            </span>
          </>
        )}
      </p>
    );
  };

  const provenanceLine = () =>
    provenance ? (
      <p data-testid="provenance-line" className="text-xs text-zinc-500">
        {provenance}
      </p>
    ) : null;

  const profileArea = () => {
    if (!selected) {
      return (
        <p className="text-sm text-zinc-500">Click an ocean cell on the field to inspect its vertical temperature profile.</p>
      );
    }
    if (busyProfile && !profilePayload) {
      return <div data-testid="profile-skeleton" className={skeletonClass}>Loading profile...</div>;
    }
    if (!profilePayload) {
      return (
        <p className="text-sm text-zinc-400">
          No vertical profile is available for this location. The point may be land or an uncovered grid cell.
        </p>
      );
    }
    const explainInput: ExplainerInput = {
      region: profilePayload.region,
      date: profilePayload.date,
      depths: profilePayload.depths,
      temps: profilePayload.temperatures,
      sigma: profilePayload.sigma,
    };
    return (
      <div className="space-y-4">
        <ProfileChart
          depths={profilePayload.depths}
          temps={profilePayload.temperatures}
          sigma={profilePayload.sigma}
        />
        <ExplainLocation input={explainInput} />
      </div>
    );
  };

  return (
    <div className="flex min-h-[100dvh] flex-col bg-zinc-950 text-zinc-50">
      <Header />
      <StatusBanner status={status} detail={bannerDetail} />

      <main className="mx-auto w-full max-w-[1400px] flex-1 space-y-4 px-4 py-4 md:px-6">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <RegionDateDepthSelector
            region={region}
            date={date}
            depth={depth}
            dates={dates}
            onRegionChange={setRegion}
            onDateChange={setDate}
            onDepthChange={setDepth}
          />
          <div
            role="group"
            aria-label="Map layer"
            className="flex items-center rounded-md border border-zinc-700 bg-zinc-900 p-0.5"
          >
            {(['temperature', 'uncertainty'] as LayerMode[]).map((mode) => (
              <button
                key={mode}
                type="button"
                aria-pressed={layer === mode}
                onClick={() => setLayer(mode)}
                className={
                  layer === mode
                    ? 'rounded px-3 py-1.5 text-xs font-medium text-zinc-950 bg-teal-400 focus:outline-none focus:ring-2 focus:ring-teal-600/40'
                    : 'rounded px-3 py-1.5 text-xs text-zinc-400 hover:text-zinc-200 focus:outline-none focus:ring-2 focus:ring-teal-600/40'
                }
              >
                {mode === 'temperature' ? 'Temperature' : 'Uncertainty'}
              </button>
            ))}
          </div>
        </div>

        <section aria-label="Ocean field" className="space-y-1.5">
          {layerCaption()}
          {provenanceLine()}
          <div className="relative z-0 h-[420px] overflow-hidden rounded-lg border border-zinc-800">{mapArea()}</div>
        </section>

        <section aria-label="Selected cell" data-testid="selected-cell" className="text-sm text-zinc-300">
          {selected ? (
            <p>
              Selected cell <span className="font-mono-data">{formatLatLon(selected.lat, selected.lon)}</span>
              <span className="mx-2 text-zinc-700">|</span>
              <span className="font-mono-data">{date}</span>
            </p>
          ) : (
            <p className="text-zinc-500">No cell selected.</p>
          )}
        </section>

        <div className="grid gap-4 lg:grid-cols-2">
          <section aria-label="Vertical profile" className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-zinc-400">
              Vertical profile
            </h2>
            {profileArea()}
          </section>

          <ArgoValidationPanel />
        </div>
      </main>

      <Footer />
    </div>
  );
}