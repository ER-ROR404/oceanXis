import type { PredictionStatus } from '../../types/contracts';

interface StatusBannerProps {
  status: PredictionStatus | null;
  /** Overrides the status's default detail when the caller has specifics (no-data region, error message). */
  detail?: string | null;
}

const STATUS_COPY: Record<Exclude<PredictionStatus, null>, { label: string; detail: string; tone: string }> = {
  model_prediction: {
    label: 'Live model',
    detail: 'Served by the hybrid_v1 inference service.',
    tone: 'border-teal-800 bg-teal-950/60 text-teal-300',
  },
  cached_data: {
    label: 'Served from cache',
    detail: 'Same result from a recent request (60 s TTL).',
    tone: 'border-teal-800/60 bg-zinc-900 text-teal-400',
  },
  fallback_demo: {
    label: 'Demo data',
    detail: 'Model service offline; pre-built cache, not the live model.',
    tone: 'border-amber-800/70 bg-amber-950/40 text-amber-300',
  },
  unavailable: {
    label: 'Unavailable',
    detail: 'No data for this region or date right now.',
    tone: 'border-red-900 bg-red-950/40 text-red-300',
  },
};

/** Honest status strip. aria-live so the status change is announced. Absent status keeps a reserved slot so the layout never jumps. */
export function StatusBanner({ status, detail }: StatusBannerProps) {
  if (status === null) {
    return (
      <div data-testid="status-banner" className="h-8 px-6" aria-hidden="true" aria-live="polite">
        &nbsp;
      </div>
    );
  }
  const copy = STATUS_COPY[status];
  return (
    <div
      data-testid="status-banner"
      aria-live="polite"
      className={`flex items-center gap-3 px-6 py-2 text-xs border-b ${copy.tone}`}
    >
      <span className="font-semibold">{copy.label}</span>
      <span className="opacity-90">{detail ?? copy.detail}</span>
    </div>
  );
}