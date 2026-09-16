import { CANONICAL_DEPTHS, type Depth } from '../../types/contracts';

interface DepthRailProps {
  depth: number;
  onDepthChange: (depth: number) => void;
}

/**
 * Reference-viewer style vertical depth rail: exactly the 15 canonical
 * model depths, surface first. Compact buttons, keyboard accessible, the
 * active slice highlighted. No invented levels.
 */
export function DepthRail({ depth, onDepthChange }: DepthRailProps) {
  return (
    <div data-testid="depth-rail" aria-label="Map depth levels" role="group" className="flex flex-col gap-0.5 rounded-md border border-zinc-700/80 bg-zinc-950/85 p-1 backdrop-blur-sm">
      {CANONICAL_DEPTHS.map((d: Depth) => (
        <button
          key={d}
          type="button"
          aria-label={d === 0 ? 'Surface · 0 m' : `${d} m`}
          aria-pressed={depth === d}
          onClick={() => onDepthChange(d)}
          className={
            depth === d
              ? 'rounded bg-teal-400 px-2 py-[3px] font-mono-data text-[11px] font-semibold text-zinc-950'
              : 'rounded px-2 py-[3px] font-mono-data text-[11px] text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200'
          }
        >
          {d === 0 ? 'Surface' : d}
        </button>
      ))}
    </div>
  );
}
