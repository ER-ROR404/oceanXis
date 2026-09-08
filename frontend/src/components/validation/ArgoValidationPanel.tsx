import { useRef } from 'react';
import gsap from 'gsap';
import { useGSAP } from '@gsap/react';
import { ShieldCheck } from 'lucide-react';

import type { ArgoValidationSummary } from '../../types/validation';
import { parseArgoSummary } from '../../utils/validation';
import argoSummary from '../../assets/validation/argo_validation_summary.json';

interface ArgoValidationPanelProps {
  /** Defaults to the committed Phase 4 asset; inject for tests. */
  summary?: ArgoValidationSummary;
}

const fmt = (v: number, digits: number): string => v.toFixed(digits);

/**
 * Aggregate, depth-wise ARGO validation (Mode 3, design spec). Sources the
 * committed summary only; never cell-exact, never realtime, no forecasting
 * claims (spec: "Aggregate depth-wise ARGO only").
 */
export function ArgoValidationPanel({ summary }: ArgoValidationPanelProps) {
  const s = summary ?? parseArgoSummary(argoSummary);
  const rowsRef = useRef<HTMLDivElement>(null);

  const reducedMotion =
    typeof window !== 'undefined' &&
    typeof window.matchMedia === 'function' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  useGSAP(
    () => {
      if (reducedMotion) return;
      const rows = rowsRef.current?.querySelectorAll('[data-argo-row]');
      if (!rows || rows.length === 0) return;
      gsap.fromTo(
        rows,
        { opacity: 0, y: 4 },
        { opacity: 1, y: 0, stagger: 0.06, duration: 0.3, ease: 'power2.out', overwrite: true },
      );
    },
    { scope: rowsRef },
  );

  const { overall, profiles, validation_window, depthOrder, depth_wise, limitations } = s;

  return (
    <section
      data-testid="argo-validation-panel"
      aria-label="ARGO validation"
      className="rounded-lg border border-zinc-800 bg-zinc-900/60 p-4"
    >
      <h3 className="mb-1 flex items-center gap-2 text-sm font-semibold text-zinc-200">
        <ShieldCheck className="h-4 w-4 text-teal-400" aria-hidden="true" />
        ARGO validation
        <span className="rounded-full border border-zinc-700 bg-zinc-950 px-2 py-0.5 text-[10px] font-medium text-zinc-400">
          {s.model_version}
        </span>
      </h3>
      <p className="text-xs text-zinc-500">
        Aggregate, depth-wise validation against independent ARGO floats,
        {validation_window.start} to {validation_window.end}. {profiles.matched} of {profiles.loaded}{' '}
        ARGO profiles matched ({profiles.depth_observations.toLocaleString()} depth observations).
      </p>

      <div className="mt-3 grid grid-cols-3 gap-3">
        <div className="rounded-md border border-zinc-800 bg-zinc-950/60 p-3">
          <p className="text-[10px] uppercase tracking-wider text-zinc-500">RMSE</p>
          <p className="font-mono-data text-lg text-zinc-100">
            {fmt(overall.rmse_c, 2)}&thinsp;°C
          </p>
        </div>
        <div className="rounded-md border border-zinc-800 bg-zinc-950/60 p-3">
          <p className="text-[10px] uppercase tracking-wider text-zinc-500">Bias</p>
          <p className="font-mono-data text-lg text-zinc-100">
            {fmt(overall.bias_c, 2)}&thinsp;°C
          </p>
        </div>
        <div className="rounded-md border border-zinc-800 bg-zinc-950/60 p-3">
          <p className="text-[10px] uppercase tracking-wider text-zinc-500">Correlation</p>
          <p className="font-mono-data text-lg text-zinc-100">{fmt(overall.correlation, 3)}</p>
        </div>
      </div>

      <div ref={rowsRef} className="mt-3 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-800 text-left text-[10px] uppercase tracking-wider text-zinc-500">
              <th className="py-1.5 pr-3 font-medium">Depth</th>
              <th className="py-1.5 pr-3 font-medium">n</th>
              <th className="py-1.5 pr-3 text-right font-medium">RMSE (°C)</th>
              <th className="py-1.5 pr-3 text-right font-medium">Bias (°C)</th>
              <th className="py-1.5 text-right font-medium">Corr</th>
            </tr>
          </thead>
          <tbody>
            {depthOrder.map((depth) => {
              const m = depth_wise[String(depth)];
              if (!m) return null;
              return (
                <tr
                  key={depth}
                  data-argo-row
                  className="border-b border-zinc-900 text-zinc-300 hover:bg-zinc-900/50"
                >
                  <td className="py-1.5 pr-3 font-mono-data text-zinc-100">{depth} m</td>
                  <td className="py-1.5 pr-3 font-mono-data">{m.n}</td>
                  <td className="py-1.5 pr-3 text-right font-mono-data">{fmt(m.rmse_c, 2)}</td>
                  <td className="py-1.5 pr-3 text-right font-mono-data">{fmt(m.bias_c, 2)}</td>
                  <td className="py-1.5 text-right font-mono-data">{fmt(m.correlation, 3)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="mt-3 rounded-md border border-amber-900/60 bg-amber-950/30 px-3 py-2 text-xs text-amber-200/90">
        {limitations}
      </p>

      <p className="mt-3 border-t border-zinc-800 pt-2 text-[10px] uppercase tracking-wider text-zinc-600">
        Modeled reconstruction; aggregate validation, not cell-exact.
      </p>
    </section>
  );
}