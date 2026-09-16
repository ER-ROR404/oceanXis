import { useMemo } from 'react';
import { rgbString, viridis } from '../map/colorScales';

interface DepthColumnProps {
  depths: readonly (number | null)[];
  temps: readonly (number | null)[];
  sigma: readonly (number | null)[];
}

/**
 * Hero depth output: honest 3D water-column of the 15 REAL predicted levels.
 *
 * Each row is one model sample plane (surface at top, 1000 m at bottom).
 * Temperature is encoded by color (viridis over the real profile domain) and
 * exact value; uncertainty is the ±1σ model estimate per level. No fake
 * continuous volume is implied: missing cells render as "no data", and rows
 * are evenly spaced sample markers — not interpolated measurements.
 */
export function DepthColumn({ depths, temps, sigma }: DepthColumnProps) {
  const domain = useMemo(() => {
    const vals = temps.filter((t): t is number => t !== null);
    if (vals.length === 0) return { min: 0, max: 1 };
    const min = Math.min(...vals);
    const max = Math.max(...vals);
    if (max - min < 1e-6) return { min: min - 1, max: max + 1 };
    return { min, max };
  }, [temps]);

  const rows = depths.map((depth, i) => {
    const t = temps[i] ?? null;
    const s = sigma[i] ?? null;
    const ok = depth !== null && t !== null && s !== null;
    const color = ok ? rgbString(viridis((t - domain.min) / (domain.max - domain.min || 1))) : 'transparent';
    return { depth, t, s, ok, color };
  });
  const valid = rows.filter((r) => r.ok);
  if (valid.length === 0) {
    return (
      <div data-testid="depth-column" className="flex h-64 items-center justify-center text-sm text-zinc-500">
        No profile data for this cell.
      </div>
    );
  }

  return (
    <div data-testid="depth-column" aria-label="Ocean depth profile column" className="overflow-hidden rounded-lg border border-zinc-800">
      <div className="border-b border-zinc-800 bg-zinc-950/80 px-4 py-2">
        <p className="text-xs font-semibold uppercase tracking-wider text-zinc-300">Ocean depth profile</p>
        <p className="text-[11px] text-zinc-500">15 model levels · 0–1000 m · temperature in °C ±1σ model uncertainty</p>
      </div>
      <ol className="divide-y divide-zinc-800/70 bg-gradient-to-b from-zinc-900/60 via-zinc-950 to-zinc-950">
        {rows.map((r, i) =>
          r.ok && r.depth !== null && r.t !== null && r.s !== null ? (
            <li
              key={`${r.depth}-${i}`}
              data-testid={`depth-plane-${r.depth}`}
              title={`${r.depth} m — ${r.t.toFixed(2)} °C ±${r.s.toFixed(2)} (±1σ model estimate)`}
              className="flex items-center gap-3 px-4 py-[7px] transition-colors hover:bg-teal-950/20"
            >
              <span className="w-14 shrink-0 font-mono-data text-xs text-zinc-400">{r.depth} m</span>
              <span
                aria-hidden="true"
                className="h-5 shrink-0 rounded-sm border border-white/10"
                style={{ width: `${Math.max(8, Math.min(160, ((r.t - domain.min) / (domain.max - domain.min || 1)) * 160))}px`, background: r.color }}
              />
              <span className="font-mono-data text-sm text-zinc-100">{r.t.toFixed(1)}°C</span>
              <span className="font-mono-data text-xs text-zinc-500">±{r.s.toFixed(2)}</span>
              <span className="ml-auto hidden font-mono-data text-[11px] text-zinc-600 sm:inline">level {i + 1}/15</span>
            </li>
          ) : (
            <li key={`missing-${i}`} data-testid={`depth-plane-${depths[i] ?? i}`} className="flex items-center gap-3 px-4 py-[7px] text-xs text-zinc-600">
              <span className="w-14 shrink-0 font-mono-data">{depths[i]} m</span>
              <span>no data for this level</span>
            </li>
          ),
        )}
      </ol>
      <p className="border-t border-zinc-800 bg-zinc-950/80 px-4 py-2 text-[10px] uppercase tracking-wider text-zinc-600">
        Model uncertainty estimate (±1σ) from the reconstruction model output.
      </p>
    </div>
  );
}
