/**
 * Runtime contract guard for the ARGO validation summary asset.
 * Same discipline as api/client.ts (RULE 6): never trust external data blindly.
 * Unknown depth keys are ignored; missing canonical depths are simply absent
 * from depthOrder (honest: we only render what the summary actually contains).
 */

import { CANONICAL_DEPTHS } from '../types/contracts';
import type { ArgoValidationSummary, DepthwiseMetric } from '../types/validation';

function requireObject(value: unknown, what: string): Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    throw new Error(`argo summary: ${what} must be an object`);
  }
  return value as Record<string, unknown>;
}

function expectFinite(value: unknown, what: string): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    throw new Error(`argo summary: ${what} must be a finite number`);
  }
  return value;
}

function expectMetric(value: unknown, what: string): DepthwiseMetric {
  const m = requireObject(value, what);
  return {
    n: expectFinite(m['n'], `${what}.n`),
    rmse_c: expectFinite(m['rmse_c'], `${what}.rmse_c`),
    bias_c: expectFinite(m['bias_c'], `${what}.bias_c`),
    correlation: expectFinite(m['correlation'], `${what}.correlation`),
  };
}

export function parseArgoSummary(value: unknown): ArgoValidationSummary {
  const v = requireObject(value, 'summary');

  const model_version = v['model_version'];
  if (typeof model_version !== 'string' || model_version.length === 0) {
    throw new Error('argo summary: missing model_version');
  }

  const window = requireObject(v['validation_window'], 'validation_window');
  const start = window['start'];
  const end = window['end'];
  if (typeof start !== 'string' || typeof end !== 'string') {
    throw new Error('argo summary: invalid validation_window');
  }

  const profiles = requireObject(v['profiles'], 'profiles');
  const loaded = expectFinite(profiles['loaded'], 'profiles.loaded');
  const matched = expectFinite(profiles['matched'], 'profiles.matched');
  const unmatched = expectFinite(profiles['unmatched'], 'profiles.unmatched');
  const depth_observations = expectFinite(profiles['depth_observations'], 'profiles.depth_observations');
  if (matched + unmatched !== loaded) {
    throw new Error('argo summary: matched + unmatched must equal loaded');
  }
  const unmatched_reasons: Record<string, number> = {};
  const reasons = requireObject(profiles['unmatched_reasons'], 'profiles.unmatched_reasons');
  for (const [k, val] of Object.entries(reasons)) {
    unmatched_reasons[k] = expectFinite(val, `unmatched_reasons.${k}`);
  }

  const overall = requireObject(v['overall'], 'overall');
  const overallMetric: Omit<DepthwiseMetric, 'n'> = {
    rmse_c: expectFinite(overall['rmse_c'], 'overall.rmse_c'),
    bias_c: expectFinite(overall['bias_c'], 'overall.bias_c'),
    correlation: expectFinite(overall['correlation'], 'overall.correlation'),
  };

  const rawDepthwise = requireObject(v['depth_wise'], 'depth_wise');
  const depth_wise: Record<string, DepthwiseMetric> = {};
  for (const depth of CANONICAL_DEPTHS) {
    const key = String(depth);
    if (key in rawDepthwise) {
      depth_wise[key] = expectMetric(rawDepthwise[key], `depth_wise.${key}`);
    }
  }
  const depthOrder = CANONICAL_DEPTHS.filter((d) => String(d) in depth_wise);

  const limitations = v['limitations'];
  if (typeof limitations !== 'string' || limitations.length === 0) {
    throw new Error('argo summary: missing limitations');
  }
  const source_work_log = v['source_work_log'];
  if (typeof source_work_log !== 'string') {
    throw new Error('argo summary: missing source_work_log');
  }

  return {
    model_version,
    validation_window: { start, end },
    profiles: { loaded, matched, unmatched, unmatched_reasons, depth_observations },
    overall: overallMetric,
    depth_wise,
    depthOrder,
    limitations,
    source_work_log,
  };
}