import type { AvailabilityResponse } from '../types/contracts';
import { ArgoValidationPanel } from '../components/validation/ArgoValidationPanel';
import { InputProvenancePanel } from '../components/science/InputProvenancePanel';
import { ModelFlowExplainer } from '../components/science/ModelFlowExplainer';
import { parseArgoSummary } from '../utils/validation';
import argoSummary from '../assets/validation/argo_validation_summary.json';

interface ValidationPageProps {
  availability: AvailabilityResponse | null;
}

/**
 * Scientific credibility page. Every number comes from the committed ARGO
 * summary asset or the live /availability report — never aspirational windows
 * (no 2018–2023 claims), never calibrated-95% language, never real-time.
 */
export function ValidationPage({ availability }: ValidationPageProps) {
  const summary = parseArgoSummary(argoSummary);
  const bayEntry = availability?.regions.find((r) => r.region === 'bay_of_bengal');
  const checkpoint = bayEntry?.checkpoint;

  return (
    <div data-testid="validation-page" className="mx-auto w-full max-w-[1100px] space-y-6 px-4 py-6 md:px-6">
      <header className="space-y-1">
        <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-teal-400">Model</p>
        <h1 className="text-2xl font-semibold tracking-tight text-zinc-50">OceanEmbed Hybrid v1</h1>
        <p className="max-w-[65ch] text-sm leading-relaxed text-zinc-400">
          Satellite-embedding reconstruction of subsurface ocean temperature. This page explains what the
          model is, what it consumes, how it was validated, and where it is weak.
        </p>
      </header>

      <section aria-label="Architecture" className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {[
          ['Architecture', 'CNN + ConvLSTM'],
          ['Temporal context', '7-day surface sequence'],
          ['Output', '15-depth profile · 0–1000 m'],
          ['Grid', '0.25° daily'],
          ['Domain served', 'Bay of Bengal · 5–22°N, 80–100°E'],
        ].map(([k, v]) => (
          <div key={k} className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-3">
            <p className="text-[10px] uppercase tracking-wider text-zinc-500">{k}</p>
            <p className="mt-1 text-sm font-medium text-zinc-100">{v}</p>
          </div>
        ))}
      </section>

      <section aria-label="Input variables" className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4">
        <h2 className="text-sm font-semibold text-zinc-200">Input variables · 7 surface channels</h2>
        <div className="mt-2">
          <InputProvenancePanel />
        </div>
        <p className="mt-2 text-xs text-zinc-500">Channel order locked by contract; subsurface fields never feed inference inputs.</p>
      </section>

      <section aria-label="Training and validation window" className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4">
        <h2 className="text-sm font-semibold text-zinc-200">Training / validation reality</h2>
        <p className="mt-1 text-sm text-zinc-400">
          Independent ARGO validation window: {summary.validation_window.start} to {summary.validation_window.end}{' '}
          (temporal held-out). Served data window{bayEntry?.date_start ? `: ${bayEntry.date_start} → ${bayEntry.date_end}` : ' loads from the live availability report.'}
        </p>
      </section>

      <section aria-label="Science context" className="space-y-4">
        <ModelFlowExplainer />
      </section>

      <ArgoValidationPanel />

      <section aria-label="Thermocline weakness" className="rounded-lg border border-amber-900/60 bg-amber-950/20 p-4">
        <h2 className="text-sm font-semibold text-amber-200">Known limitation</h2>
        <p className="mt-1 text-sm leading-relaxed text-amber-200/80">
          The 75–150 m thermocline region has higher error and warm bias. See the depth table above for exact values.
        </p>
      </section>

      <details className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4">
        <summary className="cursor-pointer text-sm font-semibold text-zinc-200">Uncertainty · ±1σ model uncertainty</summary>
        <p className="mt-2 max-w-[65ch] text-sm leading-relaxed text-zinc-400">
          Each predicted cell carries a learned ±1σ model uncertainty estimate derived from the model
          variance output. It is not a calibrated confidence interval and must not be read as 95%
          confidence — calibration was never performed.
        </p>
      </details>

      <section aria-label="Model provenance" className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4">
        <h2 className="text-sm font-semibold text-zinc-200">Model provenance</h2>
        <dl className="mt-2 grid gap-2 font-mono-data text-xs text-zinc-300 sm:grid-cols-2">
          <div><dt className="text-zinc-500">model_version</dt><dd>hybrid_v1</dd></div>
          <div><dt className="text-zinc-500">checkpoint</dt><dd>{checkpoint?.file ?? 'best.pt'}</dd></div>
          <div><dt className="text-zinc-500">epoch</dt><dd>{checkpoint?.epoch ?? 83}</dd></div>
          <div><dt className="text-zinc-500">val_loss</dt><dd>{checkpoint ? String(checkpoint.val_loss) : '0.3714623343872113'}</dd></div>
        </dl>
        <p className="mt-2 text-[11px] text-zinc-600">Source: live /availability checkpoint when reachable, else the served manifest values above.</p>
      </section>
    </div>
  );
}
