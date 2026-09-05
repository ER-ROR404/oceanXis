# Product Requirements

Converted from the SIH26066 problem statement into implementable product requirements.
Requirement IDs are referenced by acceptance criteria, tests, and PRs.

## Functional requirements

### FR-1 — Region-first interaction
- [ ] User selects a region: `bay_of_bengal` or `arabian_sea` (see `config/regions.yaml`).
- [ ] Backend maps the region to authoritative geographic bounds.
- [ ] Invalid region → standardized API error.

### FR-2 — Date selection
- [ ] User selects a date.
- [ ] System retrieves or loads processed daily data for the requested date.
- [ ] Invalid/unavailable date → standardized API error (fallback to cached data per FR-9).

### FR-3 — Depth selection
- [ ] User selects one of the 15 canonical depths.
- [ ] Map shows predicted subsurface temperature at the selected depth.

### FR-4 — Temperature map
- [ ] Render predicted temperature field over the selected region for the selected date/depth.
- [ ] Provide a legend / color scale.
- [ ] Respect the ocean mask (land excluded).

### FR-5 — Grid-cell drill-down (profile)
- [ ] User clicks a 0.25° grid cell.
- [ ] Backend returns the 15-depth vertical temperature profile at that cell.
- [ ] Frontend renders depth vs temperature chart.
- [ ] Where model predicts uncertainty: show uncertainty interval (FR-7).

### FR-6 — Surface inputs summary (drill-down)
- [ ] Profile response includes the surface input values at the selected cell.

### FR-7 — Uncertainty (CORE — upgraded from PROPOSED per ADR-012)
- [ ] Temperature + uncertainty per depth for every prediction.
- [ ] Display calibrated uncertainty (±X.X °C), not an invented "confidence %".
- [ ] Confidence layer on map: user switches between Temperature / Confidence / Prediction Error views.
- [ ] Uncertainty head: Gaussian heteroscedastic (μ, log σ²) trained with NLL loss.

### FR-8 — Model metadata
- [ ] Response includes `model_version` (+ preprocessing/normalization versions where available).
- [ ] `GET /api/model/version`-style endpoint exposes model/status metadata.

### FR-9 — Resilient data access
- [ ] If Copernicus is unavailable: return cached latest data, do not invent values.
- [ ] If a variable is unavailable: mark the channel unavailable (do not silently zero-fill).
- [ ] Health checks must not trigger expensive external downloads.

### FR-10 — Scientific Validation View (CORE — upgraded from PROPOSED per ADR-011/012)
- [ ] Predicted vs GLORYS profile comparison (training reference).
- [ ] Predicted vs ARGO profile where independent observations exist (never fabricated).
- [ ] Per-profile RMSE / bias / correlation calculated and displayed.
- [ ] Depth-wise RMSE / bias / correlation panel for the evaluated model.
- [ ] Spatial prediction error map (green=low, yellow=moderate, red=high error).
- [ ] ARGO coverage indicator (what % of region has independent validation).
- [ ] **Mode 3 — Scientific Validation Mode**: judge-facing summary view with all metrics.

## Non-functional requirements

### NFR-1 — Security
- [ ] Copernicus credentials are backend-only; never in frontend, Git, logs, or API responses.
- [ ] No secrets committed (`.env` ignored; `.env.example` placeholders only).

### NFR-2 — Boundaries
- [ ] Frontend never calls Copernicus directly (RULE 2).
- [ ] Backend never contains model-training code (RULE 3).
- [ ] ML inference consumes the canonical model-input contract (RULE 5).

### NFR-3 — Data integrity
- [ ] Dataset IDs verified via `describe()`, not guessed (RULE 7).
- [ ] All harmonized tensors conform to `contracts/data/` and `contracts/ml/`.
- [ ] Train/val/test split is temporal (RULE 10); normalization from training data only (RULE 11).

### NFR-4 — Scientific honesty
- [ ] No fabricated data, dataset IDs, metrics, or ARGO comparisons.
- [ ] No claim of "real-time" or "operational" without verified latency.
- [ ] Model-derived current products labeled as such (not "pure satellite").
- [ ] OceanEmbed positioned as complementary to GODAS, not a replacement.

### NFR-5 — Reproducibility (MVP)
- [ ] Dataset manifest records provenance (source, dataset_id, version, preprocessing).
- [ ] Model artifacts carry version + config + metrics (see `docs/05-ml/checkpoint-policy.md`).
- [ ] A fallback demo dataset exists so the demo never dies with live ingestion.

### NFR-6 — MVP constraints
- [ ] Keep the MVP regional (Bay of Bengal / Arabian Sea) and demonstrable in ~36h.
- [ ] Prove the data pipeline before building the frontend (Golden Rule 10).

## Requirement sources
- LOCKED items trace to the official SIH26066 problem statement (see `problem-statement.md`).
- PROPOSED items are team recommendations (uncertainty, ARGO UI comparison, depth maps).