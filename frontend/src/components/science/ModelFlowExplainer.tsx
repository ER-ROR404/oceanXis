import { Workflow } from 'lucide-react';

/** Deployed pipeline, mirroring backend inference (docs + audit: T=7, CNN->ConvLSTM, 15-depth head). */
const STEPS = [
  '7 surface variables',
  'Data harmonization',
  '7-day temporal context',
  'CNN',
  'ConvLSTM',
  '15-depth reconstruction',
  'Temperature + uncertainty',
];

/**
 * Demo spec Screen 6: expandable explanation of how OceanEmbed works.
 * Static copy of the deployed pipeline — no new claims, no exaggeration.
 */
export function ModelFlowExplainer() {
  return (
    <details
      data-testid="model-flow-explainer"
      className="rounded-lg border border-zinc-800 bg-zinc-900/40"
    >
      <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-3 text-sm font-semibold text-zinc-200 [&::-webkit-details-marker]:hidden">
        <Workflow className="h-4 w-4 text-teal-400" aria-hidden="true" />
        How does OceanEmbed work?
      </summary>
      <div className="border-t border-zinc-800 px-4 py-3">
        <ol className="flex flex-wrap items-center gap-2 text-xs text-zinc-400">
          {STEPS.map((step, i) => (
            <li key={step} className="flex items-center gap-2">
              <span className="rounded-md border border-zinc-700 bg-zinc-950/60 px-2.5 py-1">
                {step}
              </span>
              {i < STEPS.length - 1 && (
                <span className="text-zinc-600" aria-hidden="true">
                  →
                </span>
              )}
            </li>
          ))}
        </ol>
        <p className="mt-3 text-xs text-zinc-500">
          A CNN encodes the harmonized surface fields and a ConvLSTM models their 7-day temporal
          context; the decoder reconstructs a temperature profile — with a model uncertainty
          estimate — at all 15 canonical depths.
        </p>
      </div>
    </details>
  );
}