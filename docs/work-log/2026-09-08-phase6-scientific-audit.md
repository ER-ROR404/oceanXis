# Work Log — 2026-09-08: Phase 6 Scientific Validation Audit (evidence-based)

> **Purpose:** Answers the Phase 6 audit questions using ONLY evidence present in this repository.
> Every claim below cites a repo file (path:line range). No external knowledge was substituted;
> where the repository does not contain evidence for a claim, the answer says so explicitly.
>
> **Method:** read-only review. No code, config, or git state was modified, staged, or committed.

---

## 1. Evidence inventory (files consulted)

| Domain | Files |
|--------|-------|
| Config (canonical truth) | `config/variables.yaml`, `config/depths.yaml`, `config/regions.yaml`, `config/datasets.yaml`, `config/training.yaml`, `config/model.yaml`, `ml/configs/hybrid_v1.yaml` |
| ADRs | `docs/02-architecture/architecture-decisions/ADR-004` (surface-only), `005` (GLORYS target), `006` (ARGO validation), `007` (temporal split), `008` (regional MVP), `010` (CNN+ConvLSTM), `011` (3 modes), `012` (uncertainty+ARGO core) |
| ML implementation | `ml/src/oceanembed/data/dataset.py`, `ml/src/oceanembed/serving/service.py`, `ml/src/oceanembed/serving/server.py`, `ml/src/oceanembed/models/reconstruction_net.py`, `ml/src/oceanembed/evaluation/argo.py` (via service.py imports) |
| Evaluation artifacts | `experiments/reports/argo_validation_2026-09-06.json`, `docs/work-log/2026-09-06-argo-validation.md`, `frontend/src/assets/validation/argo_validation_summary.json`, `experiments/registry.yaml`, `experiments/README.md` |
| Backend | `backend/app/services/cache.py` (sigma conversion), `backend/app/services/availability.py`, `backend/app/schemas/map.py`, `backend/app/schemas/profile.py` |
| Frontend copy | `frontend/src/components/validation/ArgoValidationPanel.tsx`, `frontend/src/components/layout/Header.tsx`, `frontend/src/components/layout/Footer.tsx`, `frontend/src/utils/explain.ts` |
| Contracts | `contracts/ml/model-input.schema.json`, `contracts/ml/model-output.schema.json`, `contracts/validation/argo-summary.schema.json`, `contracts/api/availability.schema.json` (via `docs/work-log/2026-09-08-p0-capability.md`) |
| Domain/design docs | `docs/superpowers/specs/2026-09-04-ml-architecture-design-v2.1.md`, `docs/03-domain/scientific-assumptions.md`, `docs/03-domain/ocean-domain.md`, `docs/04-data/data-sources.md`, `docs/04-data/dataset-registry.md`, `docs/04-data/preprocessing-pipeline.md`, `docs/05-ml/model-card.md`, `docs/05-ml/evaluation-policy.md`, `docs/05-ml/training-policy.md`, `docs/01-product/scope-and-non-goals.md`, `docs/01-product/product-vision.md`, `docs/01-product/problem-statement.md`, `SYSTEM_MEMORY_DUMP.md` §99 (GODAS), `README.md` |
| Work logs | `docs/work-log/2026-09-08-p0-capability.md`, `docs/work-log/2026-09-06-argo-validation.md` |

---

## 2. Answers to the 11 audit questions

### Q1. What is the model trained against? Is GLORYS the only training target?

**Answer:** Yes — GLORYS reanalysis is the only training/reference target.

- `config/datasets.yaml:71-78` — `glorys_temperature: selected_dataset_id: "cmems_mod_glo_phy_my_0.083deg_P1D-m"`, variable `thetao`, note "GLORYS12 daily physics reanalysis… NOT NRT (~1–2 mo latency)", role `training_target`.
- `config/datasets.yaml:80-87` — ARGO has role `validation` (independent only), `selected_dataset_id: null` (raw GDAC profiles preferred); it is **never a training target**.
- `ADR-005-glorys-training-target.md:13-15` — "Use GLORYS … as the dense training/reference target."
- `config/variables.yaml:46` — "GLORYS subsurface temperature is the training/reference target, NEVER an inference input (RULE 8)."
- `dataset.py:8-19` — input tensor `X [time,channel,lat,lon]` = 7 surface channels; target `Y [time,depth,lat,lon]` = 15 depth temperatures (GLORYS-derived); ARGO appears nowhere in the store.
- Dataset ID verified via `copernicusmarine.describe()` + `subset(dry_run=True)` on 2026-09-02 (`config/datasets.yaml:4-6`; `docs/04-data/data-sources.md:36`; `dataset-registry.md:25`).

**Judged implication (evidence-restricted):** the model is trained against a reanalysis (a model+assimilation product), so its skill is bounded by GLORYS quality; the ARGO comparison is the only observation-based check. This is fully disclosed in the repo.

### Q2. What are the exact inputs? Are they truly the 7 surface "satellite" channels?

**Answer:** Exactly 7 channels, LOCKED ordering, but the phrase "satellite" must be qualified: two of the seven are multi-source products containing model-derived components.

- `config/variables.yaml:5-42` — LOCKED channel list/index: SST(0), SSS(1), SSH/SLA(2), current_U(3), current_V(4), wind_U(5), wind_V(6); `input_channels: 7`.
- Spec `docs/superpowers/specs/2026-09-04-ml-architecture-design-v2.1.md:27-40` — same 7 variables, harmonized to 0.25°×0.25° daily.
- Verified dataset IDs (`config/datasets.yaml:21-69`; `dataset-registry.md:13-24`):
  - SST — `METOFFICE-GLO-SST-L4-REP-OBS-SST` (orbit reprocessed OSTIA; 0.05°, daily)
  - SSS — `cmems_obs-mob_glo_phy-sss_my_multi_P1D` (multi-sat reprocessed)
  - SSH/SLA — `cmems_obs-sl_glo_phy-ssh_my_allsat-l4-duacs-0.125deg_P1D` (altimetry L4)
  - Currents U/V — `cmems_obs-mob_glo_phy-cur_my_0.25deg_P1D-m`, note at `datasets.yaml:56`: "MY observation currents uo/vo (total, geostrophic+Ekman+tide); train/val/test — **DISCLOSE components, not 'pure satellite'**"
  - Wind U/V — `cmems_obs-wind_glo_phy_my_l4_0.125deg_PT1H`, note at `datasets.yaml:66`: "MY L4 gridded scatterometer+**model**"
- `docs/03-domain/scientific-assumptions.md:18` (A8) — "Current products may be multi-source (incl. model-derived Ekman components) and must be disclosed; not 'pure satellite'"; `:28` — '"Satellite-only" labeling of multi-source current products (REJECTED — A8)'.
- `docs/05-ml/model-card.md:32` — "Multi-source current product includes model-derived components (disclosed, not 'pure satellite')."

**Judged implication:** the demo/web copy must say "7 surface observations" or list the products, never "7 satellite channels". Repo copy already does this (Mode-3 panel: "independent ARGO floats"; header: "Historical reconstruction"; no "satellite-only" wording found in shipped UI copy).

### Q3. How is data split? Is there leakage?

**Answer:** Strictly temporal-locked; no random shuffling; MVP has a temporal validation holdout and **no held-out test year** (documented, deliberate for the 36-hour MVP scope).

- `config/training.yaml:5-11` — `method: temporal_locked` ("NO random temporal split — RULE 10"), train/val/test 0.8/0.1/0.1, `test_untouched_during_tuning: true`.
- `config/datasets.yaml:13-19` — split policy comment: future multi-year store = train 2018-01-01..2023-12-31 | validation 2024 | test 2025; **MVP tensor store (bay_of_bengal) covers 2022-01-01..2023-12-31 (730 daily days), "used in full with a temporal holdout (val_fraction), no held-out test year."**
- `dataset.py:8-13` — same statement in the code docstring; `create_dataloaders` (`dataset.py:171-211`) splits sample indices in order, "Training data comes first, validation data comes after (no shuffling across time)"; `shuffle=False` in both loaders.
- **No fold-boundary straddling, by construction:** a window ending at sample `n_train-1` covers days `[n_train-T, n_train-1]`; the first validation sample covers `[n_train, n_train+T-1]` — no window spans the boundary (`dataset.py:111-115`, `202-203`).
- **Normalization policy:** train-only per `config/training.yaml:22-25` (RULE 11), `training-policy.md:17-21`. The consumer (`dataset.py:81-95,143-159`) loads a precomputed `normalization_stats.json` and z-scores only `X` (never `Y`), NaN→0 for land. **Audit caveat:** the file itself is produced by the upstream data build (outside the repo — `docs/work-log/2026-09-06-argo-validation.md:91-92` lists it under Drive artifacts), so the *actual* computation slice is not re-verifiable from repo evidence; the policy and consumer are compliant.
- **Validation window used for checkpoint selection:** last 20% of the 730-day store = **2023-08-10..2023-12-31** (matches `experiments/reports/argo_validation_2026-09-06.json:7` and the windowed-samples `val_fraction: 0.2` in `ml/configs/hybrid_v1.yaml:26`). Checkpoint best.pt (epoch 83, val_loss ≈ 0.3715) was chosen by `early_stopping: monitor: validation_masked_rmse` (`config/training.yaml:47-50`).
- `ADR-007-temporal-data-split.md:12-29` — rationale and rules.

**Judged implication:** leakage from temporal autocorrelation is addressed (windows end on the target day, in-order). The honest limitation is the **absence of an untouched test year** — no estimate of generalization to an unseen *period* beyond one validation slice; ARGO covers that role partially as an external observer on the same window.

### Q4. What is the ARGO validation methodology? Is it real and independent?

**Answer:** Yes — end-to-end real, independent, and honestly reported. This is the strongest scientific evidence in the repo.

Pipeline and provenance:
- `docs/work-log/2026-09-06-argo-validation.md:8-19` — Cell A: GDAC index `ar_index_global_prof.txt` (3,382,424 rows) → 295 profiles in Bay of Bengal within the held-out window 2023-08-10..2023-12-31 → 291 usable (4 skipped "no valid levels"; QC gate working) → `artifacts/argo_profiles.json` (aoml, coriolis, csio, incois DACS). Cell B: `evaluate_argo.py --config ml/configs/hybrid_v1.yaml --checkpoint best.pt …` → 285/291 matched (6 unmatched, all `land`).
- Independence (RULE 9): `work-log:69-70` — "ARGO profiles used for validation are **never training inputs**." ARGO is absent from `X/Y/mask` tensors (`dataset.py:16-19`).
- Matching protocol: by date + location, interpolated to the 15 canonical depths; no depth extrapolation — canonical depths outside a float's sampled range → NaN with n=0 (`work-log:66-68`); land-cell matches reported as `matched:false, reason:"land"`, never dropped (`work-log:63-65`); per-profile traceability (`source_id`, date, lat/lon, reason) (`work-log:61-62`).
- Results (`experiments/reports/argo_validation_2026-09-06.json:8-33` + `frontend/src/assets/validation/argo_validation_summary.json`):

  - Profiles: loaded 291, matched 285, unmatched 6 (land); depth-level observations scored **3,958**.
  - Overall: **RMSE 1.3533 °C, bias +0.6121 °C (warm), correlation 0.99**.
  - Depth-wise (RMSE °C): 0 m n=25 0.41 · 5 m 0.47 · 10 m 0.52 · 20 m 0.66 · 30 m 0.95 · 50 m 1.80 · **75 m 2.81 · 100 m 2.65 · 125 m 1.86** · 150 m 1.25 · 200 m 0.64 · 300 m 0.26 · 500 m 0.19 · 700 m 0.20 · 1000 m 0.16.
- Honest interpretation recorded in repo (`work-log:76-85`; summary JSON `limitations` field): skill strong near surface (0–30 m) and deep (300–1000 m); the **thermocline band (75–150 m) is the weak zone: RMSE 1.2–2.8 °C, warm bias up to +2.2 °C**; overall corr 0.99 is driven by strong deep-variance match while near-surface corr is low because near-surface variance is small.
- `contracts/validation/argo-summary.schema.json:5` — summary values are "copied verbatim from the committed work-log — never recalculated".

**Judged caveats (all visible in repo):** single region (BoB), single ~5-month window (2023-08-10..2023-12-31), 291 profiles; depth-0 has only n=25 (only profiles sampling exactly 0 m); raw per-profile records live outside the repo (Drive, RULE 12/13, `work-log:87-92`); no ARGO coverage in the Arabian Sea.

### Q5. What does sigma mean? Is the uncertainty calibrated?

**Answer:** sigma = the model's predicted **aleatoric** per-cell standard deviation from a Gaussian-NLL head; **empirical calibration of the uncertainty is required by the spec but has NOT been performed/recorded in this repo.**

- Semantics: `ml/src/oceanembed/models/reconstruction_net.py:284-318,399-401` — decoder has separate `mu_head` and `log_var_head`; returns `(mu, log_var)`. Spec §11 (`2026-09-04-ml-architecture-design-v2.1.md:428-463`) — "The uncertainty represents the model's estimated observation/process noise at each location and depth", σ² = softplus(raw)+ε numerical safety, trained with Gaussian NLL.
- Wire conversion: `backend/app/services/cache.py:27-29` — `sigma = sqrt(exp(log_var))`; documented in `backend/app/schemas/map.py:40-43` ("sigma = sqrt(exp(log_var)); … raw log_var stays internal").
- UI semantics: `frontend/src/utils/explain.ts:13,58-63` — `Z = 1.96` ("95% two-sided normal interval"); sentence "Typical 95% uncertainty band is +/- X deg C near the surface."
- **Spec requirement not met by repo evidence:** spec §13 (`...v2.1.md:499-527`) — "The model must be evaluated for calibration… We will report **empirical coverage**, not assume '1σ = 68%'… Required outputs: Coverage @ 1σ, Coverage @ 2σ, Reliability/calibration plot. **Calibration is a result, not a guaranteed property.**"
- **No calibration artifact exists in the repo:** `experiments/reports/` contains only the ARGO RMSE report; grep for calibration across work-logs/experiments finds only a future-work mention (`docs/work-log/2026-09-06-argo-validation.md:85` — "depth-dependent bias calibration" as next-iteration target). The 1.96σ "95%" phrasing in `explain.ts` is therefore an **unvalidated Gaussian assumption**, not an empirically demonstrated coverage.

**Judged implication:** the uncertainty signal itself is real model output (per-cell, from trained head), but the demo should say "model estimated uncertainty" and avoid guaranteeing "95% coverage" unless calibration (coverage@1σ/2σ vs ARGO) is computed and reported. This is a *strength as honesty* (the pipeline exposes real σ) and a *gap as calibration evidence*.

### Q6. What is the model architecture — as trained and as served?

**Answer:** OceanEmbedNet = CNN spatial encoder + 1-layer ConvLSTM (hidden 128) + depth decoder with μ and log-var heads; input `[B, T=7, 7, H, W]` → output `[B, 15, H, W]`.

- Code: `reconstruction_net.py:321-433` — coord/seasonal encoder (configurable) → CNNEncoder 3 stages (32→64→128, 3×3, BN, ReLU, MaxPool) → ConvLSTMBlock (layers=1, hidden=128) → DepthDecoder (128→64→32 + μ/log_var 1×1 heads), exact-size interpolate for odd grids (69×81 BoB).
- Training config actually used: `ml/configs/hybrid_v1.yaml:10-19` — `in_channels: 7, out_channels: 15, uncertainty: true, convlstm_hidden: 128, convlstm_layers: 1, use_seasonal: true, use_spatial: true`; `data.temporal_window: 7`; `val_fraction: 0.2`; loss `nll` (`:29`).
- Serving mirrors training: `ml/src/oceanembed/serving/service.py:23-26` `TEMPORAL_WINDOW = 7` ("Matching the value the model was trained with; constructing the dataset with a different window would silently change inputs and corrupt the prediction"); `:95-115` builds OceanEmbedNet from cfg (`convlstm_hidden` 128, `layers` 1) and loads best.pt.
- **CRITICAL documented quirk:** `service.py:1-11` — the coord/seasonal encoder and `input_proj` "were never trained"; training/eval call `model(x_batch)` with NO `day_of_year`/`lat`/`lon` (trainer.py:109,138; evaluation/argo.py:232); inference must (and does) mirror that — `service.py:137` `mu, log_var = self.model(x_win)`. So `use_seasonal/use_spatial: true` in config is not actually active at inference.

**Documented code-vs-docs divergences (flagged, not fixed — read-only audit):**
| Doc | States | Deployed reality (repo evidence) |
|-----|--------|----------------------------------|
| `config/model.yaml:15,35-38` | `lookback_days: 10`, ConvLSTM `[128,128]` 2 layers, `uncertainty.enabled: false` | T=7, 1 layer × 128, uncertainty head active (`hybrid_v1.yaml`, `service.py`, `reconstruction_net.py`) |
| `ADR-010-cnn-lstm-hybrid.md:38` | Stage-2 primary T=10 days | T=7 (spec v2.1 §5 primary; `service.py:26`) |
| `config/model.yaml`/ADR-010 | `input_proj`/coords expected | coords not trained; inference call-site mirrored without coords (`service.py:2-11`) |
| `experiments/registry.yaml` | documented registry | `experiments: []` — empty (scaffolding only, `experiments/README.md:17-18` "populated during ML coding phase") |

Spec §5 (`...v2.1.md:221-235`) states T=7 is "an engineering/scientific hypothesis, not a proven optimum" — the repo never claims T was optimized.

### Q7. What limitations are documented for the model?

Answer — documented in repo (model-card + ARGO work log + domain docs):
- `docs/05-ml/model-card.md:29-33` — skill expected to degrade with depth (measure, don't assume); missing/cloudy data handled via masks, gaps reported not fabricated; **multi-source currents disclosed**; **"No real-time/operational claim without latency verification."**
- ARGO work log interpretation (`2026-09-06-argo-validation.md:76-85`) — thermocline band 75–150 m: RMSE 1.2–2.8 °C, warm bias to +2.2 °C; identified next-iteration target.
- Scope: only bay_of_bengal has a tensor store; arabian_sea / north_indian_ocean are declared but no_data (`docs/work-log/2026-09-08-p0-capability.md:17`, live-verified availability). MVP restriction is deliberate (`ADR-008-regional-mvp.md`, `SYSTEM_MEMORY_DUMP.md` §152.20 "36-hour MVP regional and demonstrable").
- No held-out test year (Q3); normalization-stats provenance external (Q3).
- GLORYS is a reanalysis with ~1–2-month latency — no nowcast/real-time framing without an ADR (`docs/04-data/data-sources.md:48-50`).
- Frontend honesty line: `frontend/src/components/layout/Footer.tsx:2` "Modeled reconstruction; trained on data through 2023-12-31."; header chip "Research prototype · Historical reconstruction" (`Header.tsx:14`); ARGO panel "Modeled reconstruction; aggregate validation, not cell-exact." (`ArgoValidationPanel.tsx:123`).
- Assumptions explicitly rejected: random splits, monotonic temperature decrease, "satellite-only" currents, real-time claims (`scientific-assumptions.md:25-30`).

### Q8. How does this differ from GODAS / is GODAS replaced?

**Answer:** Repo consistently positions OceanEmbed as a **complementary learned pathway, explicitly not a GODAS replacement**; no quantitative GODAS comparison has been performed or recorded.

- `SYSTEM_MEMORY_DUMP.md§99` (lines 2744-2765): GODAS = physical ocean model + data assimilation + multiple observations; OceanEmbed = surface state + learned latent representation + deep learning; "OceanEmbed should not attempt to duplicate all of GODAS."
- `README.md:43` — "no GODAS replacement… OceanEmbed is a *complementary* learned reconstruction pathway".
- `docs/01-product/scope-and-non-goals.md:22,31-34` — not a non-goal to replace INCOIS/GODAS; explicit table: GODAS = physics model + assimilation vs OceanEmbed = learned surface→subsurface estimator.
- `docs/05-ml/model-card.md:16` — "not a replacement for GODAS/numerical models."
- `docs/01-product/product-vision.md:207` — positioning table row "Replace GODAS → Position as complementary".
- GODAS comparison experiment: spec v2.1 defers it (`...v2.1.md:19` "GODAS comparison remain optional/deferred"); the v1 design doc says "If GODAS is not accessible, state this as a limitation and compare to climatology instead" (`2026-09-04-ml-architecture-design.md:670-675`). **Repo evidence: no GODAS data access recorded and no GODAS-vs-ARGO comparison number exists in the repo** (registry empty; baseline comparison `[climatology, persistence]` is *configured* in `hybrid_v1.yaml:41` but **no baseline report exists**).

**Judged implication:** the narrative position is sound and fully documented; but any pitch must not claim accuracy above/versus GODAS — the repo has no such comparison. State "complementary research pathway validated against ARGO; GODAS comparison deferred".

### Q9. Claim audit table — every demo/README claim vs. repo evidence

| # | Claim (found in repo copy or proposed pitch) | Verdict | Evidence |
|---|----------------------------------------------|---------|----------|
| 1 | "15-depth subsurface temperature reconstruction" | ✅ TRUE as served | `config/depths.yaml:5-20`; output `[B,15,H,W]` (`reconstruction_net.py:401`; contract `model-output.schema.json:23`) |
| 2 | "0.25°×0.25° daily grid" | ✅ TRUE for the served MVP grid (69×81 BoB, 730 daily days) | `config/regions.yaml:7-9`; 69×81 live (`p0-capability.md:14`); native source resolutions (0.05° SST, 0.125° SLA/wind, 0.25° currents, 0.083° GLORYS) are regridded onto 0.25° — A12 marks 0.25° as PROPOSED baseline assumption (`scientific-assumptions.md:22`) |
| 3 | "7 surface observations as inputs" | ✅ TRUE; but **never "7 satellite channels"** | `config/variables.yaml:5-44`; currents/wind multi-source disclosed (`datasets.yaml:56,66`; A8) |
| 4 | "GLORYS as training/reference target" | ✅ TRUE | Q1 evidence |
| 5 | "Independent ARGO validation — RMSE 1.35 °C" | ✅ TRUE as computed (285 profiles, 3,958 obs, held-out window) | `argo_validation_2026-09-06.json:8-17`; must be presented with depth-wise table (thermocline 2.8 °C) |
| 6 | "Overall correlation 0.99" | ✅ TRUE with context | summary `limitations` text: driven by deep variance; near-surface corr low (`argo_validation_summary.json:38`) |
| 7 | "Uncertainty/confidence per cell" | ⚠️ PARTIAL — real per-cell aleatoric σ, but "95%" band is an unvalidated Gaussian assumption | Q5 |
| 8 | "Operational / real-time" | ❌ REJECTED in repo; not shipped | header "Research prototype · Historical reconstruction" (`Header.tsx:14`); `data-sources.md:48-50` GLORYS latency; `scientific-assumptions.md:29` |
| 9 | "Fills subsurface observation gaps" | ⚠️ Not substantiated by repo evidence as an accuracy claim; repo avoids this wording | no such claim found in shipped copy; honest gaps are masked as NaN/None (`service.py:140-143`; `map.py` schema) |
| 10 | "Works for the North Indian Ocean" | ⚠️ PARTIAL — domain LOCKED in config (5–30°N, 45–105°E, `regions.yaml:12-19`); only BoB has data today; NIO/AS truthfully report no_data | `p0-capability.md:17`; live availability |
| 11 | "Generalizes beyond Bay of Bengal" | ❌ UNSUPPORTED — no spatial holdout experiment, no AS tensors | registry empty; no experiment reports besides ARGO |
| 12 | "AI-powered"/"smart" marketing | ⚠️ Avoid; repo describes a learned CNN+ConvLSTM reconstruction, with explicit honesty constraints | spec v2.1 §7-§10; `AGENTS.md` rules (no LLM features) |
| 13 | "Beats baselines (climatology/CNN/GODAS)" | ❌ UNSUPPORTED — baselines configured but never run/recorded | `hybrid_v1.yaml:41`; `evaluation-policy.md:26-37` requires comparison; registry `experiments: []` |
| 14 | "Temporal integrity respected" | ✅ TRUE | `dataset.py:171-211`; ADR-007; no fold boundary straddling |
| 15 | "ARGO never used in training" | ✅ TRUE | RULE 9 (`AGENTS.md`), `work-log:69-70`, ARGO absent from tensors |

### Q10. Fifteen judge questions with repo-backed answers (Q10)

1. **"Is your ARGO validation independent or did you train on ARGO?"** → Independent. ARGO appears nowhere in X/Y/mask tensors (`dataset.py:16-19`); config role `validation` (`datasets.yaml:80-87`); work-log states "never training inputs" (line 70).
2. **"Show me the held-out test set."** → None in the MVP (documented). Validation = temporal holdout 2023-08-10..2023-12-31 used for checkpoint selection; external check = ARGO on the same window. Future split (2018-23/2024/2025) is the locked long-term design (`datasets.yaml:13-19`).
3. **"Did you tune on the test set?"** → There is no test set; tuning used the temporal validation slice (early stopping monitor `validation_masked_rmse`, `training.yaml:47-50`).
4. **"Why 0.99 correlation but near-surface correlation ~0.3?"** → Repo documents it: deep variance dominates the pooled correlation; near-surface absolute errors are small (`argo_validation_summary.json:38`). Present depth-wise.
5. **"Why is thermocline RMSE so high at 75-150 m?"** → Sharpest gradients; warm bias up to +2.2 °C documented as next-iteration target (`work-log:76-85`).
6. **"Your currents/winds are called 'satellite' — really?"** → They are not; repo discloses multi-obs (geostrophic+Ekman+tide) currents and scatterometer+model winds (`datasets.yaml:56,66`; A8). Say "surface observations".
7. **"Are your sigma bands calibrated?"** → Model-estimated aleatoric σ; empirical coverage (spec §13) not yet computed — the UI "95%" band is an assumption, flagged in this audit (Q5).
8. **"Can I reproduce your training?"** → Mostly: configs (`hybrid_v1.yaml`), dataset code, train entry (`ml/scripts/train_colab_entry.py`), seed 42 deterministic settings (`training.yaml:65-68`); checkpoints/tensors on Drive (RULE 12/13); registry empty (weakness).
9. **"Does it work in the Arabian Sea?"** → Not demonstrated: no data. Availability endpoint truthfully returns no_data (`p0-capability.md:17`). Spatial holdout is a documented *optional* experiment (`evaluation-policy.md:51`).
10. **"Is this real-time?"** → No. Historical reconstruction through 2023-12-31 (`Footer.tsx:2`); GLORYS ~1–2-month latency (`data-sources.md:48`). No nowcast claim.
11. **"Why is the served window T=7 when model.yaml says 10?"** → Documented divergence: deployed config + dataset + serving all use T=7 (spec §5 primary); `model.yaml`/ADR-010 are stale docs (Q6 table).
12. **"What did you compare against?"** → No baseline numbers in repo — climatology/persistence/CNN configured but not run/recorded (registry empty). Honest answer: "configured, not yet computed."
13. **"How does it differ from GODAS?"** → Complementary, documented (Q8); no quantitative GODAS comparison.
14. **"Where are the raw ARGO profiles and per-profile records?"** → Drive artifacts (`work-log:87-92`), not committed (RULE 12/13); the committed summary mirrors the work log verbatim (`argo-summary.schema.json:5`).
15. **"Which product would this be in the real world?"** → Repo answer: a research prototype / complementary learned pathway for regions and windows with verified data, not an operational service (`model-card.md:14-16`; scope-and-non-goals).

### Q11. Winning position — what should (and should not) be claimed

**What the repo supports (claim these):**
1. A physics-informed *learned* inverse: 7 daily surface observations → 15-depth temperature field, CNN+ConvLSTM, temporal window 7, at 0.25° on a real Bay of Bengal grid (69×81, 730 days).
2. **Independent, real ARGO validation** — 285 float profiles / 3,958 depth observations in a held-out temporal window, reported *depth-wise and honestly*: overall RMSE 1.35 °C, warm bias +0.61 °C, corr 0.99, with the thermocline weakness (up to 2.8 °C) disclosed rather than averaged away.
3. **Scientific integrity as the differentiation**: temporal-locked splits, no ARGO in training, no fabricated values, masked gaps reported as missing, multi-source inputs disclosed, provenance recorded, real per-cell uncertainty output.
4. **Complementarity, not replacement**: positioned against GODAS/INCOIS as a fast, transparent, uncertainty-aware learned pathway.

**What the repo does NOT support (do not claim):**
- Operation/real-time/nowcast status; Arabian Sea or North-Indian-Ocean skill; generalization beyond BoB; superiority over GODAS or over baseline methods (no baseline comparison exists in repo); calibrated "95%" coverage (unvalidated).

**Draft narrative tone (evidence-derived):**
> "OceanEmbed is a research prototype that reconstructs Bay of Bengal subsurface temperature at 15 depths from 7 daily surface observations using a CNN+ConvLSTM, validated against 285 independent ARGO profiles (RMSE 1.35 °C; thermocline bias identified and disclosed), with strict temporal splitting and per-cell uncertainty. It is complementary to — not a replacement for — operational ocean modelling."

---

## 3. Findings summary

**Strengths (evidence-backed):** real independent ARGO pipeline; honest depth-wise metrics incl. weak band; strict temporal splits; no-fabrication discipline end-to-end; multi-source inputs disclosed; URL/API-contract discipline; UI honesty copy; verified dataset IDs; documented uncertainty contract.

**Gaps (evidence-backed):**
1. No held-out test year (MVP scope, documented).
2. No baseline comparison results recorded (registry empty) — configured only.
3. No uncertainty calibration report (spec §13 required; not delivered).
4. Docs/code divergences: T window (7 vs 10), ConvLSTM depth (1 vs 2), uncertainty flag, coord-encoder not trained — `config/model.yaml` + ADR-010 stale vs `hybrid_v1.yaml`/code.
5. No GODAS/quantitative-vs-existing comparison.
6. ARGO coverage single-region/single-window; depth-0 thin (n=25).
7. Normalization-stats computation provenance external to repo (policy + consumer compliant).

**Recommended follow-ups (not performed — read-only):** (a) run and record climatology/persistence/CNN baselines; (b) compute empirical σ coverage @1σ/2σ vs ARGO and adjust UI copy to "model-estimated uncertainty"; (c) align `config/model.yaml`/ADR-010 with deployed reality or re-run with T=10; (d) record experiments in `experiments/registry.yaml`; (e) if time allows, a BoB→AS spatial-holdout experiment before any generalization claim.