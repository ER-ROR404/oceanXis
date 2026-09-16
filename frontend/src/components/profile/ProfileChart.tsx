import { CANONICAL_DEPTHS } from '../../types/contracts';
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from 'recharts';

export interface BandPoint {
  depth: number;
  temp: number;
  lo: number;
  hi: number;
  /** Range accessor for recharts Area (verified: Area.js getComposedData toggles isRange for array values). */
  band: [number, number];
}

const Z = 1; // ±1σ model-uncertainty band (σ from the model log-var output; NOT a calibrated 95% interval — calibration was never performed, §13 spec gap)

/**
 * One banded point per canonical depth, surface first (ascending depth).
 * Null cells are skipped (honest: no fabricated band).
 */
export function buildBandData(
  depths: readonly (number | null)[],
  temps: readonly (number | null)[],
  sigma: readonly (number | null)[],
): (BandPoint | null)[] {
  return depths.map((depth, i) => {
    const t = temps[i];
    const s = sigma[i];
    if (depth === null || t === null || s === null) return null;
    const lo = t - Z * s;
    const hi = t + Z * s;
    return { depth, temp: t, lo, hi, band: [lo, hi] };
  });
}

interface ProfileChartProps {
  depths: readonly (number | null)[];
  temps: readonly (number | null)[];
  sigma: readonly (number | null)[];
}

const axisTick = {
  fontSize: 11,
  fill: '#a1a1aa', // zinc-400
  fontFamily: 'inherit',
};

// Full canonical water column (contract-locked depths), fixed so the depth axis
// always reads 0-1000 m at true proportional spacing even when a level is
// missing (honest: the gap shows as a missing marker, never as a shifted axis).
const DEPTH_MIN = CANONICAL_DEPTHS[0];
const DEPTH_MAX = CANONICAL_DEPTHS[CANONICAL_DEPTHS.length - 1];

/**
 * Vertical thermal profile: temperature on the horizontal (value) axis, depth
 * on the vertical axis, surface at top.
 *
 * The chart is a recharts `layout="vertical"` chart on purpose: in that layout
 * the X axis is the *value* axis (temperature) and every marker's Y coordinate
 * is read from the Y axis `dataKey` — i.e. the real depth in metres — so the 15
 * model levels sit at their true, proportionally spaced depths. In the default
 * horizontal layout recharts plots a series' own dataKey on the Y axis, which
 * would put temperature on the depth axis (all levels crushed near 0 m).
 *
 * The shaded band is the ±1σ model-uncertainty estimate (σ from the model
 * output; not a calibrated 95% interval — none exists, see phase-6 audit
 * §calibration), drawn horizontally around each level's temperature.
 */
export function ProfileChart({ depths, temps, sigma }: ProfileChartProps) {
  const data = buildBandData(depths, temps, sigma).filter((p): p is BandPoint => p !== null);

  if (data.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-zinc-500">
        No profile data for this cell.
      </div>
    );
  }

  // Temperature domain from the real values, widened to keep the ±1σ band
  // inside the plot.
  const tMin = Math.min(...data.map((p) => p.lo));
  const tMax = Math.max(...data.map((p) => p.hi));

  return (
    <div>
      <div data-testid="profile-chart" className="h-64 w-full" role="img" aria-label="Temperature profile with model uncertainty band (±1σ)">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart
          layout="vertical"
          data={data}
          margin={{ top: 8, right: 24, bottom: 8, left: 8 }}
        >
          <defs>
            <linearGradient id="bandGradient" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#2dd4bf" stopOpacity={0.35} />
              <stop offset="100%" stopColor="#2dd4bf" stopOpacity={0.15} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#27272a" strokeDasharray="3 3" />
          <XAxis
            dataKey="temp"
            type="number"
            domain={[tMin - 1, tMax + 1]}
            tick={axisTick}
            tickFormatter={(v: number) => Number(v).toFixed(1)}
            label={{ value: 'Temperature (deg C)', position: 'insideBottom', offset: -2, fill: '#a1a1aa', fontSize: 11 }}
            stroke="#3f3f46"
          />
          <YAxis
            dataKey="depth"
            type="number"
            domain={[DEPTH_MIN, DEPTH_MAX]}
            padding={{ top: 8, bottom: 8 }}
            tick={axisTick}
            tickFormatter={(v: number) => String(v)}
            label={{ value: 'Depth (m)', angle: -90, position: 'insideLeft', fill: '#a1a1aa', fontSize: 11 }}
            stroke="#3f3f46"
          />
          <Tooltip
            formatter={(value: number | string | [number, number], name: string) =>
              Array.isArray(value)
                ? [`${value[0].toFixed(1)} – ${value[1].toFixed(1)}`, name]
                : [`${Number(value).toFixed(1)}`, name]
            }
            labelFormatter={(v) => `${v} m`}
            contentStyle={{ background: '#18181b', border: '1px solid #3f3f46', borderRadius: 8, fontSize: 12 }}
          />
          <Area
            dataKey="band"
            name="±1σ range"
            stroke="none"
            fill="url(#bandGradient)"
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="temp"
            name="temperature"
            stroke="#2dd4bf"
            strokeWidth={2}
            dot={{ r: 2.5, fill: '#2dd4bf', strokeWidth: 0 }}
            isAnimationActive={false}
          />
          <ReferenceLine y={200} stroke="#52525b" strokeDasharray="4 4" />
        </ComposedChart>
      </ResponsiveContainer>
      </div>
      <p data-testid="uncertainty-caption" className="mt-1 text-[10px] uppercase tracking-wider text-zinc-600">
        Model uncertainty estimate (±1σ) from the reconstruction model output.
      </p>
      <p data-testid="interpolation-note" className="mt-0.5 text-[10px] uppercase tracking-wider text-zinc-700">
        Visual interpolation between the 15 model levels.
      </p>
    </div>
  );
}
