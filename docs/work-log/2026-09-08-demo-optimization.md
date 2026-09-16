# Demo Video Optimization / Feature Freeze — 2026-09-08

Status: **READY FOR DEMO SHOOT**

Scope: frontend-only polish to make the core OceanEmbed value obvious in the first
30–60 seconds of a demo video. Feature freeze respected — no model, backend,
science-pipeline, or contract changes. Small, reversible UI edits only.
NOT committed (working tree intentionally left with untracked deliverables).

## 1. Current UX problems found (pre-change audit)

1. **Hero communicated nothing.** Header said "Subsurface Ocean Explorer" +
   "Research prototype · Historical reconstruction" — a viewer in the first
   30–60 s never learned *what* the product does (surface observations →
   subsurface temperature reconstruction).
2. **Map caption was a de-emphasized one-liner.** "Temperature at 100 m | date |
   Latest available: …" — no "Predicted Subsurface Temperature" title, no °C
   units label, no "0.25° reconstruction grid" note, no region/availability
   window ("Bay of Bengal · Available: …").
3. **Overclaimed uncertainty in the vertical profile.** The shaded band was
   labeled "95% uncertainty band" with Z = 1.96 (two-sided normal interval).
   The Phase 6 scientific audit established that **no uncertainty calibration
   was ever performed** (§13 spec gap in `2026-09-08-phase6-scientific-audit.md`),
   so a "95%" claim implies a calibrated coverage guarantee that does not exist.
4. **"What goes into OceanEmbed?" provenance panel was missing.** The 7 LOCKED
   surface channels and the honest "multi-source satellite-derived and ocean
   observation products" framing were nowhere on screen.
5. **Model pipeline explainer was missing.** No expandable CNN → ConvLSTM →
   15-depth reconstruction explanation for demo audiences.
6. **ARGO panel heading buried the independence framing.** "ARGO validation"
   heading; "independent ARGO floats" only appeared mid-sentence.

## 2. Changes made

| Screen | Change |
|---|---|
| 1 Hero | Added hero tagline under the wordmark: **"Satellite-derived Surface Observations → Subsurface Temperature Reconstruction"** (`Header.tsx`). |
| 2 Map | Replaced the thin caption with a proper section title: **"Predicted Subsurface Temperature — 100 m"** + subtitle **"0.25° reconstruction grid · temperature in °C"**; added an availability-window chip **"Bay of Bengal · Available: 2022-01-01 → 2023-12-31"** (driven by the live `/availability` report). Uncertainty layer title: "Model Uncertainty (σ) — {depth} m". `Latest available` and provenance line preserved. |
| 3 Profile | Uncertainty band re-labeled as **±1σ model-uncertainty estimate** (Z 1.96 → 1.0), chart aria-label "Temperature profile with model uncertainty band (±1σ)", caption "Model uncertainty estimate (±1σ) from the reconstruction model output." Explain-this-location sentence now "Model uncertainty estimate is ±X deg C near the surface (1 sigma)." No calibrated-95% implication anywhere. |
| 4 ARGO | Heading upgraded to **"Independent ARGO validation"** (Aug–Dec 2023 window, 291 profiles / 285 matched / 3,958 depth observations, RMSE 1.35 °C, bias +0.61 °C, corr 0.990 all already rendered). Correlation is never called "99% accuracy". Highest-error disclosure (75–150 m, warm bias up to +2.2 °C) retained as designed. |
| 5 Provenance (new) | New **"What goes into OceanEmbed?"** panel: the 7 LOCKED channels (SST, SSS, SSH/SLA, Current U, Current V, Wind U, Wind V) with the multi-source wording; footnote: currents/winds combine satellite-observed and model-analysis products. |
| 6 Pipeline (new) | New expandable **"How does OceanEmbed work?"** panel: 7 surface variables → Data harmonization → 7-day temporal context → CNN → ConvLSTM → 15-depth reconstruction → Temperature + uncertainty (mirrors the deployed inference path, T=7). |

No scientific claims expanded anywhere; all wording stays traceable to the repo
canonical facts (7 LOCKED channels, 15 depths, 0.25°, BoB-first region).

## 3. Files changed

Frontend only (all reversible):

- `frontend/src/components/layout/Header.tsx` — hero tagline
- `frontend/src/App.tsx` — map-section title block + availability window + new Science section (imports/wiring)
- `frontend/src/components/profile/ProfileChart.tsx` — Z=1, aria-label, ±1σ caption
- `frontend/src/utils/explain.ts` — ±1σ sentence, Z=1
- `frontend/src/components/validation/ArgoValidationPanel.tsx` — "Independent ARGO validation" heading/aria-label
- `frontend/src/components/science/InputProvenancePanel.tsx` — NEW
- `frontend/src/components/science/ModelFlowExplainer.tsx` — NEW
- Tests: `profile.test.tsx`, `e2e-explorer.test.tsx`, `layout.test.tsx`,
  `validation.test.tsx`, `app.test.tsx` updated; `science-panels.test.tsx` NEW

Backend/ML/data-engineering: **zero files changed** (feature freeze).

## 4. Tests added / updated

TDD RED→GREEN cycle used throughout.

- `profile.test.tsx` — buildExplanation now asserts the ±1σ "model uncertainty" sentence and rejects any `/95%/`; `buildBandData` bounds recomputed for ±1σ (29.15/29.85 from 29.5±0.35); new ProfileChart test asserts the "(±1σ)" aria-label and the uncertainty caption.
- `e2e-explorer.test.tsx` — hero tagline; map-title "Predicted Subsurface Temperature … 100 m" + map-subtitle "0.25° reconstruction grid"; availability-window chip (both the 5-date mock and the 730-date live simulation → "2022-01-01 → 2023-12-31"); "Independent ARGO validation"; the two science panels' presence; and a new guard test: the rendered page never contains `/95%/`, "satellite measurements", or "% accuracy".
- `layout.test.tsx` — Header hero-tagline test.
- `validation.test.tsx` — heading updated; new test: ARGO panel never implies a calibrated 95% confidence interval (note: real depth-wise RMSE values such as 0.95 are legitimate data and are not flagged).
- `app.test.tsx` — hero tagline present even in the offline degraded state.
- `science-panels.test.tsx` — NEW: provenance panel renders all 7 channels + multi-source wording + rejects "satellite measurements"/95%; pipeline explainer lists all deployed steps.

## 5. Test results

```
npx vitest run            → 9 files, 102 tests, all passed
npm run test:coverage     → All files: 97.67% statements · 87.93% branches ·
                            94.2% functions · 97.67% lines   (gate ≥ 80% ✓)
```

RED phase: 11 tests failed exactly as intended before implementation; all green
after the minimal GREEN implementation (no tests weakened — assertions were
tightened to the honest framing).

Backend (146) and ML (37) suites: not re-run — zero backend/ML files changed;
the repo-wide gate is unaffected by frontend-only edits.

## 6. Build result

```
npm run build  → tsc + vite build succeeded in 9.0s
  dist/index.html                   0.74 kB │ gzip: 0.48 kB
  dist/assets/index-*.css          23.39 kB │ gzip: 5.10 kB
  dist/assets/index-*.js          813.34 kB │ gzip: 241.36 kB
```
Pre-existing warning only: single chunk > 500 kB (no code-splitting configured
in this prototype; out of scope for a demo-optimization feature freeze).

## 7. Exact demo flow (verified)

1. Open app → hero: **OCEANEMBED · Satellite-derived Surface Observations → Subsurface Temperature Reconstruction** · "Research prototype · Historical reconstruction" · "North Indian Ocean · 0.25°".
2. Controls default to **Bay of Bengal**, date auto-selected to **2023-09-01** (first date ≥ 2023-09-01 from the live 730-date report), depth **100 m**.
3. Map section title: **Predicted Subsurface Temperature — 100 m**, subtitle **0.25° reconstruction grid · temperature in °C**, window chip **Bay of Bengal · Available: 2022-01-01 → 2023-12-31**.
4. Click an ocean cell (e.g. 15.25°N, 87.5°E) → **Vertical Profile**: 15 canonical depths, real reconstructed temperatures (29.4 °C surface → 6.5 °C @ 1000 m), **±1σ model-uncertainty band** with explicit caption; "Explain this location" sentences including the ±1σ statement; footer honesty line.
5. **Independent ARGO validation** panel: Aug 2023–Dec 2023, 285/291 matched, 3,958 depth observations, RMSE 1.35 °C, bias +0.61 °C, corr 0.990, per-depth table, and the honest thermocline limitation (75–150 m, warm bias up to +2.2 °C).
6. Scroll: **What goes into OceanEmbed?** (7 channels, multi-source wording) and expandable **How does OceanEmbed work?** (pipeline diagram).
7. Failure states preserved: switching to Arabian Sea / North Indian Ocean shows the honest no-data empty state; no dates outside 2022-01-01…2023-12-31 are offered.

## 8. Chosen verified demo date

**2023-09-01** — live-verified end-to-end through the Vite proxy against the
running stack (ml:8080, backend:8000, Vite:5173):

- `/availability` → bay_of_bengal available, **730 dates, 2022-01-01 → 2023-12-31**; arabian_sea/north_indian_ocean `no_data`.
- `/ocean/map?region=bay_of_bengal&date=2023-09-01&depth=100` → `model_prediction`, 5,293 ocean cells, values 1.19–28.87 °C (strong thermocline contrast), σ 1.45–15.80.
- `/ocean/profile?region=bay_of_bengal&date=2023-09-01&latitude=15.25&longitude=87.5` → `model_prediction`, 15 depths, surface 29.41 °C → 6.48 °C @ 1000 m, σ 0.23–1.82.

Why this date: it is the app's own preferred default; it falls inside the ARGO
validation window (Aug–Dec 2023), so the demo's map/profile narrative and the
ARGO comparison refer to the same period; and it is well inside the served
2022–2023 coverage.

## 9. Remaining weaknesses

1. **No real-browser visual pass in this session.** The UI flow is fully covered
   by the jsdom integration suite and the API flow is live-verified through the
   Vite proxy, but a human/screen-recording pass (Playwright or manual) is
   recommended to confirm pixel-level layout before the final shoot.
2. **413-line profile/explainer copy is instructive, not a polished "tour".**
   The two new science panels are static copy — deliberately not an animated
   walkthrough (feature freeze; animations must not obscure the science).
3. **Chunk size warning (>500 kB)** — pre-existing; cosmetic for a demo build.
4. **No calibration exists** (§13 spec gap, Phase 6 audit) — the UI now correctly
   labels uncertainty as *a ±1σ model estimate*, never a guaranteed interval;
   the honest caveat belongs in the demo script voiceover.
5. **Correlation 0.99** is shown with the existing honest framing (not a
   conventional held-out accuracy); a narrator must not paraphrase it as
   "99% accuracy".

## 10. Confirmation: no scientific claims expanded

- Same 7 LOCKED inputs, 15 output depths, 0.25° grid, BoB-first coverage.
- No new metrics, datasets, regions, or model claims introduced.
- Uncertainty claim was **tightened** (95% → ±1σ model estimate), never widened.
- ARGO numbers unchanged and traceable to the committed asset
  (`frontend/src/assets/validation/argo_validation_summary.json`).
- No realtime/forecasting wording added; "Research prototype · Historical
  reconstruction" status retained everywhere.

## 11. Confirmation: no fabricated data introduced

- All map/profile values verified live (model_prediction) or come from the
  committed fallback cache — no new fixtures invented.
- Unsupported regions (Arabian Sea, NIO) remain explicitly `no_data`; the demo
  cache is labeled "Demo data · not the live model" when the service is offline.
- No dates are offered outside the served window (out-of-window requests 404).
- The only "95%" strings now live in code comments explaining why we must NOT
  use 95% — none render.

---

### Final status: **READY FOR DEMO SHOOT**

Frontend-only, reversible UI improvements; 102/102 tests green; coverage
97.7%; build green; hero flow live-verified through the Vite proxy; chosen demo
date 2023-09-01 verified live. No scientific claims expanded, no fabricated data.