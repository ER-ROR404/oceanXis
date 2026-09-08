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

const Z = 1.96; // 95% two-sided normal interval

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

/**
 * Vertical thermal profile: temperature on the horizontal axis, depth on the
 * vertical axis inverted (surface at top). The shaded band is the sigma-derived
 * 95% interval (DESIGN.md: honest uncertainty framing).
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

  const yMin = Math.min(...data.map((p) => p.depth));
  const yMax = Math.max(...data.map((p) => p.depth));

  return (
    <div data-testid="profile-chart" className="h-64 w-full" role="img" aria-label="Temperature profile with 95% uncertainty band">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart
          data={data}
          margin={{ top: 8, right: 24, bottom: 8, left: 8 }}
        >
          <defs>
            <linearGradient id="bandGradient" x1="0" y1="0" x2="0" y2="0">
              <stop offset="0%" stopColor="#2dd4bf" stopOpacity={0.35} />
              <stop offset="100%" stopColor="#2dd4bf" stopOpacity={0.15} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#27272a" strokeDasharray="3 3" />
          <XAxis
            dataKey="temp"
            type="number"
            domain={['dataMin - 1', 'dataMax + 1']}
            tick={axisTick}
            label={{ value: 'Temperature (deg C)', position: 'insideBottom', offset: -2, fill: '#a1a1aa', fontSize: 11 }}
            stroke="#3f3f46"
          />
          <YAxis
            dataKey="depth"
            type="number"
            reversed
            domain={[yMin, yMax]}
            tick={axisTick}
            label={{ value: 'Depth (m)', angle: -90, position: 'insideLeft', fill: '#a1a1aa', fontSize: 11 }}
            stroke="#3f3f46"
          />
          <Tooltip
            formatter={(value: number | string, _name: string) => [Number(value).toFixed(1), 'deg C']}
            labelFormatter={(v) => `${v} m`}
            contentStyle={{ background: '#18181b', border: '1px solid #3f3f46', borderRadius: 8, fontSize: 12 }}
          />
          <Area
            dataKey="band"
            stroke="none"
            fill="url(#bandGradient)"
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="temp"
            stroke="#2dd4bf"
            strokeWidth={2}
            dot={{ r: 2.5, fill: '#2dd4bf', strokeWidth: 0 }}
            isAnimationActive={false}
          />
          <ReferenceLine y={200} stroke="#52525b" strokeDasharray="4 4" />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}