import {
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';
import type { ArgoValidationSummary } from '../../types/validation';

interface RmseDepthChartProps {
  summary: ArgoValidationSummary;
}

const THERMOCLINE = new Set([75, 100, 125, 150]);

/**
 * RMSE by depth: one bar per REAL canonical level (categorical axis — depths
 * are unevenly spaced, so no continuous scale is implied). The 75–150 m
 * thermocline band is colored amber; the rest teal. Same numbers as the
 * detailed table below; this chart is the visual entry point (§27).
 */
export function RmseDepthChart({ summary }: RmseDepthChartProps) {
  const data = summary.depthOrder.map((depth) => ({
    depth: `${depth} m`,
    rmse: summary.depth_wise[String(depth)]?.rmse_c ?? null,
    band: THERMOCLINE.has(depth),
  }));

  return (
    <div data-testid="rmse-depth-chart" className="mt-3">
      <div className="h-56 w-full" role="img" aria-label="RMSE by depth bar chart">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 12, bottom: 8, left: 8 }}>
            <CartesianGrid stroke="#27272a" strokeDasharray="3 3" />
            <XAxis
              dataKey="depth"
              tick={{ fontSize: 10, fill: '#a1a1aa' }}
              interval={1}
              stroke="#3f3f46"
            />
            <YAxis
              tick={{ fontSize: 11, fill: '#a1a1aa' }}
              label={{ value: 'RMSE (°C)', angle: -90, position: 'insideLeft', fill: '#a1a1aa', fontSize: 11 }}
              stroke="#3f3f46"
            />
            <Tooltip
              formatter={(value: number | string) => [`${Number(value).toFixed(2)} °C`, 'RMSE']}
              contentStyle={{ background: '#18181b', border: '1px solid #3f3f46', borderRadius: 8, fontSize: 12 }}
            />
            <Bar dataKey="rmse" isAnimationActive={false}>
              {data.map((d, i) => (
                <Cell key={i} fill={d.band ? '#f59e0b' : '#2dd4bf'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p data-testid="rmse-thermocline-note" className="mt-1 text-[11px] text-zinc-500">
        Amber bars mark the 75–150 m thermocline band with the highest error.
      </p>
    </div>
  );
}
