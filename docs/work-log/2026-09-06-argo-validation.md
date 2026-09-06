# Work Log — 2026-09-06: First complete ARGO independent validation (Cell B)

> **Purpose:** Records the first end-to-end ARGO validation of the trained OceanEmbed model
> against real, independent float profiles. Supersedes the drive-on manifest metrics
> (known bug: manifest RMSE/bias inflated by normalization-domain artifact — see below); the
> ARGO masked metrics are the authoritative evaluation per RULE 9.

## 1. Pipeline status (fully working end-to-end)

- **Cell A (acquire):** index `ar_index_global_prof.txt` 3,382,424 rows → 295 float profiles in
  Bay of Bengal within the held-out window **2023-08-10 .. 2023-12-31** (last 20% of the tensor
  store time axis, temporal order respected) → 291 usable profiles written to
  `artifacts/argo_profiles.json` (aoml, coriolis, csio, incois dacs).
  - 4 skipped with "no valid levels" (INCOIS `_001`/`_002` deployment/settling profiles;
    QC gate working as designed).
- **Cell B (evaluate):** `evaluate_argo.py --config ml/configs/hybrid_v1.yaml --checkpoint
  …/best.pt --data-dir …/data/bay_of_bengal --argo-profiles …/argo_profiles.json
  --artifacts-dir …/artifacts` → **285/291 matched (6 unmatched, all `land`)**, report written to
  `artifacts/argo_report.json`.

### Fixes that made it work (commits on `main`)

| Commit | Fix |
|--------|-----|
| `8aafa2a` | Real GDAC profiles: JULD CF-decode overflow → open with `decode_times=False, decode_timedelta=False`; empty-date index rows dropped silently |
| `1a02976` | `KeyError: 'lat'`: real tensor store uses `latitude`/`longitude` coords; validator now resolves either naming (`_coord_values`) |

## 2. Results (`best.pt`, hybrid_v1, CPU)

| Metric | Value |
|--------|-------|
| Profiles loaded | 291 |
| Matched / unmatched | 285 / 6 (all `land` — masked ocean cells; honest, not fabricated) |
| Depth-level observations scored | 3,958 |
| **Overall RMSE** | **1.3533 °C** |
| **Overall bias** | **+0.6121 °C** (warm bias) |
| **Overall correlation** | **0.99** |

### Depth-wise (LOCKED canonical depths)

| Depth (m) | n | RMSE (°C) | Bias (°C) | Corr |
|-----------|---|-----------|-----------|------|
| 0    |  25 | 0.4095 | +0.1514 | 0.577 |
| 5    | 283 | 0.4744 | +0.1855 | 0.292 |
| 10   | 284 | 0.5248 | +0.2646 | 0.264 |
| 20   | 284 | 0.6593 | +0.4291 | 0.259 |
| 30   | 284 | 0.9546 | +0.5171 | 0.134 |
| 50   | 283 | 1.8045 | +0.9234 | 0.512 |
| 75   | 283 | 2.8054 | +2.1687 | 0.707 |
| 100  | 283 | 2.6497 | +2.1635 | 0.732 |
| 125  | 283 | 1.8636 | +1.3009 | 0.724 |
| 150  | 283 | 1.2483 | +0.6362 | 0.715 |
| 200  | 281 | 0.6366 | +0.2097 | 0.695 |
| 300  | 278 | 0.2642 | −0.1303 | 0.624 |
| 500  | 276 | 0.1901 | −0.0672 | 0.468 |
| 700  | 276 | 0.1961 | −0.0516 | 0.315 |
| 1000 | 272 | 0.1635 | −0.0115 | 0.102 |

## 3. Sanity checks & honest reporting (Golden Rules 4, 21)

- **Profile traceability:** every record carries `source_id`, date, lat/lon, `matched`, and
  `reason`; e.g. all 15 cycles of `D2902394_288` match with proper 10-day cadence.
- **Land cells reported, not dropped:** 6 unmatched (`R2902764_136`, `R2902764_145`,
  `D2902769_132`, `D2902769_146`, `D1902670_009`, `D1902670_010`) sit in mask=0 cells near the
  southern BoB boundary — they appear in the report with `matched: false, reason: "land"`.
- **No depth extrapolation:** canonical depths outside a float's sampled range → NaN with n=0
  (e.g., only n=25 profiles sample exactly 0 m; deep canonical depths have smaller n as floats
  bottom out). Metrics over valid (prediction AND observation) cells only.
- **Split integrity:** validation window (2023-08-10..2023-12-31) is the temporal held-out slice;
  ARGO profiles used for validation are never training inputs (RULE 9).
- **Known manifest bug (unchanged):** `run_manifest.json` overall RMSE=3.93/bias=2.93 are an
  artifact of the manifest metric path (unmasked/denormalized-domain computation), not the true
  model skill; true pooled on-domain RMSE ≈ 1.0 and the ARGO independent RMSE above are the
  numbers that count.

## 4. Interpretation

- Skill is **strong at the surface (0–30 m: RMSE ≈ 0.4–1.0 °C)** and **strong deep
  (300–1000 m: RMSE ≈ 0.16–0.26 °C)**; the challenge band is the **thermocline (75–150 m:
  RMSE 1.2–2.8 °C with warm bias up to +2.2 °C)**. This matches physical expectation
  (sharpest gradients at the thermocline) and is reported honestly, not averaged away.
- Overall correlation 0.99 is driven by the strong deep-variance match; near-surface corr is low
  simply because near-surface variance is small (tiny absolute errors).
- The warm bias concentrated at 75–150 m is the clear next-iteration target
  (thermocline-aware loss / depth-dependent bias calibration).

## 5. Artifacts (Drive, not committed — RULE 12/13)

- `MyDrive/oceanembed/artifacts/argo_profiles.json` (291 profiles, provenance per record)
- `MyDrive/oceanembed/artifacts/argo_report.json` (this report, full per-profile records)
- `MyDrive/oceanembed/artifacts/best.pt`, `latest.pt` (checkpoints)
- `MyDrive/oceanembed/data/bay_of_bengal/{X,Y,mask}.zarr`, `normalization_stats.json` (tensors)