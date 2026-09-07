import type { Depth as DepthValue, Region } from '../../types/contracts';
import { CANONICAL_DEPTHS, REGION_IDS } from '../../types/contracts';

interface RegionDateDepthSelectorProps {
  region: Region;
  date: string;
  depth: number;
  dates: string[];
  onRegionChange: (region: Region) => void;
  onDateChange: (date: string) => void;
  onDepthChange: (depth: number) => void;
}

const controlClass =
  'rounded-md border border-zinc-700 bg-zinc-900 px-2.5 py-1.5 text-sm text-zinc-100 ' +
  'focus:outline-none focus:ring-2 focus:ring-teal-600/40 focus:ring-offset-2 focus:ring-offset-zinc-950';

/** Controls row: region (from REGION_IDS), date (available dates), depth (canonical 15). */
export function RegionDateDepthSelector({
  region,
  date,
  depth,
  dates,
  onRegionChange,
  onDateChange,
  onDepthChange,
}: RegionDateDepthSelectorProps) {
  return (
    <div className="flex flex-wrap items-end gap-3">
      <label className="flex flex-col gap-1 text-xs font-medium text-zinc-400">
        Region
        <select
          aria-label="Region"
          className={controlClass}
          value={region}
          onChange={(e) => onRegionChange(e.target.value as Region)}
        >
          {REGION_IDS.map((r) => (
            <option key={r} value={r}>
              {r.replace(/_/g, ' ')}
            </option>
          ))}
        </select>
      </label>

      <label className="flex flex-col gap-1 text-xs font-medium text-zinc-400">
        Date
        <select
          aria-label="Date"
          className={controlClass}
          value={date}
          onChange={(e) => onDateChange(e.target.value)}
        >
          {dates.map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </select>
      </label>

      <label className="flex flex-col gap-1 text-xs font-medium text-zinc-400">
        Depth
        <select
          aria-label="Depth"
          className={controlClass}
          value={String(depth)}
          onChange={(e) => onDepthChange(Number(e.target.value))}
        >
          {CANONICAL_DEPTHS.map((d) => (
            <option key={d} value={d}>
              {d === 0 ? 'Surface (0 m)' : `${d} m`}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}

export type { DepthValue, Region };