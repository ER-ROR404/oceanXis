/**
 * Typed mirror of the committed ARGO validation summary asset
 * (frontend/src/assets/validation/argo_validation_summary.json, Phase 4).
 * The runtime guard lives in utils/validation.ts; these types describe the
 * decoded, trusted shape.
 */

export interface DepthwiseMetric {
  n: number;
  rmse_c: number;
  bias_c: number;
  correlation: number;
}

export interface ArgoValidationSummary {
  model_version: string;
  validation_window: { start: string; end: string };
  profiles: {
    loaded: number;
    matched: number;
    unmatched: number;
    unmatched_reasons: Record<string, number>;
    depth_observations: number;
  };
  /** Overall block has no sample count (depth-wise rows carry n). */
  overall: Omit<DepthwiseMetric, 'n'>;
  /** Keyed by the decimal string of the canonical depth (e.g. "75"). */
  depth_wise: Record<string, DepthwiseMetric>;
  /** Canonical depth order for rows that actually have validation data. */
  depthOrder: number[];
  limitations: string;
  source_work_log: string;
}