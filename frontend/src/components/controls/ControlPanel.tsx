import type { Coordinates, Region } from '../../types/contracts';
import { REGION_IDS } from '../../types/contracts';
import { REGION_LABELS } from '../../hooks/useOceanExplorer';
import type { LayerMode } from '../map/OceanMap';
import { LocationPicker } from './LocationPicker';

interface ControlPanelProps {
  layer: LayerMode;
  region: Region;
  coordinates: Coordinates | null;
  onLayerChange: (layer: LayerMode) => void;
  onRegionChange: (region: Region) => void;
  onPick: (lat: number, lon: number) => void;
  onResetView: () => void;
}

const controlClass =
  'w-full rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1.5 text-xs text-zinc-100 ' +
  'focus:outline-none focus:ring-2 focus:ring-teal-600/40';

/**
 * Floating reference-style control stack: layer, region, keyboard location
 * inspection, reset view. Every option comes from live API state.
 */
export function ControlPanel({
  layer,
  region,
  coordinates,
  onLayerChange,
  onRegionChange,
  onPick,
  onResetView,
}: ControlPanelProps) {
  return (
    <div data-testid="control-panel" aria-label="Map controls" className="w-52 space-y-3 rounded-lg border border-zinc-700/80 bg-zinc-950/85 p-3 backdrop-blur-sm">
      <div>
        <p className="mb-1 text-[10px] font-medium uppercase tracking-wider text-zinc-500">Layer</p>
        <div role="group" aria-label="Map layer" className="flex items-center rounded-md border border-zinc-700 bg-zinc-900 p-0.5">
          {(['temperature', 'uncertainty'] as LayerMode[]).map((mode) => (
            <button
              key={mode}
              type="button"
              aria-pressed={layer === mode}
              onClick={() => onLayerChange(mode)}
              className={layer === mode ? 'flex-1 rounded bg-teal-400 px-2 py-1 text-[11px] font-medium text-zinc-950' : 'flex-1 rounded px-2 py-1 text-[11px] text-zinc-400 hover:text-zinc-200'}
            >
              {mode === 'temperature' ? 'Temperature' : 'Uncertainty'}
            </button>
          ))}
        </div>
      </div>

      <div>
        <p className="mb-1 text-[10px] font-medium uppercase tracking-wider text-zinc-500">Region</p>
        <select aria-label="Region" value={region} onChange={(e) => onRegionChange(e.target.value as Region)} className={controlClass}>
          {REGION_IDS.map((r) => (
            <option key={r} value={r}>
              {REGION_LABELS[r]}
            </option>
          ))}
        </select>
      </div>

      <div>
        <p className="mb-1 text-[10px] font-medium uppercase tracking-wider text-zinc-500">Location</p>
        <LocationPicker coordinates={coordinates} onPick={onPick} />
      </div>

      <button
        type="button"
        onClick={onResetView}
        className="w-full rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1.5 text-xs text-zinc-400 hover:text-zinc-200"
      >
        Reset view
      </button>
    </div>
  );
}
