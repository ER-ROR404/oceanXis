# Implementation Plan: OceanEmbed — End-to-End Build (Colab-Powered Training)

> Status: PLAN (authority for the coding phase)
> Companion: `AGENTS.md`, `OPENCODE_SDL_CONTRACT.md`, `SYSTEM_MEMORY_DUMP.md`, `docs/**`, `contracts/**`,
> `config/model.yaml`, `config/training.yaml`, `ml/configs/*.yaml`.
> Golden Rule 11: **No frontend before the data pipeline + model are proven.**

---

## 0. What this plan covers

OceanEmbed (SIH26066) is currently a **pre-build skeleton**: docs, contracts, config, and directory
structures exist, but **no application/ML/data code has been written** (verified: no `.py` source
under `ml/src`, `data-engineering/src`, `backend/app`, `frontend/src`).

This plan takes the skeleton to a working **regional MVP** with two critical team decisions:

1. **Model training runs in Google Colab (GPU)** — not locally, not in cloud-training jobs.
   Code/config shared between local/OpenCode and Colab via **GitHub**; checkpoints live in Drive/object
   storage; only manifests + metrics are pushed back.
2. **Model architecture is a staged CNN → CNN+ConvLSTM hybrid (ADR-010)** — do NOT lock CNN-only.
   - **Stage 1 — CNN baseline** (single-day `[B,7,H,W] → [B,15,H,W]`): proves the pipeline + scores.
   - **Stage 2 — CNN + ConvLSTM hybrid (PRIMARY)** (window `[B,T,7,H,W] → [B,15,H,W]`): captures
     temporal evolution of the daily surface state, per the base literature (Su et al. 2022 ConvLSTM).

> **Memory-dump interpretation note (ADR-010):** "start with CNN baseline before Transformer/ViT"
> stays correct as an **implementation order**, but must NOT be read as "final model = CNN only".
> Decision: **CNN = baseline; CNN + ConvLSTM = primary candidate; Transformer/attention = optional
> experiment** (§17–§20 remain optional future work only).

### Repository (git management)

- **Remote**: `origin → https://github.com/ER-ROR404/oceanXis.git` (private, populated with skeleton).
- **Default branch**: `main` (protected — no direct pushes; all changes land via reviewed PRs).
- **Branch strategy**: short-lived branches per unit of work.
  - Features/implementation: `feat/<phase>-<short-description>` (e.g. `feat/p1-dataset-catalog`).
  - Fixes: `fix/<short-description>`.
  - Experiments (ML runs): `experiment/<name>` — **never merged to `main`**; results recorded in
    `experiments/registry.yaml` + `experiments/reports/` on a normal branch instead.
- **Commit convention**: Conventional Commits — `feat|fix|refactor|docs|test|chore|perf|ci:` each
  small and atomic (see `CONTRIBUTING.md`).
- **Never commit**: secrets (`.env`), datasets (`*.nc/.zarr`), checkpoints (`*.pt/.pth`), generated
  artifacts — enforced by the strict `.gitignore` (RULE 12/13/14).
- **Code review**: every PR reviewed (AI `code-reviewer` expected per `AGENTS.md`; human for
  `contracts/`, `docs/02-architecture/`, `database/migrations/`).
- **Colab → GitHub**: Colab pulls the repo, pushes only small manifest/metrics JSON on a normal
  branch; checkpoints/data stay out of Git (§4).

---

## 1. Requirements (from problem statement + decisions)

- 7 surface input channels (LOCKED order, variables.yaml): SST, SSS, SSH/SLA, current_U, current_V,
  wind_U, wind_V.
- 15 output depths (LOCKED order, depths.yaml): 0,5,10,20,30,50,75,100,125,150,200,300,500,700,1000 m.
- Grid 0.25°×0.25°, daily, North Indian Ocean 5–30°N / 45–105°E; MVP regions Bay of Bengal & Arabian Sea.
- GLORYS = training/reference target; ARGO = independent validation (RULE 9).
- Metrics: RMSE, bias, correlation (overall + depth-wise).
- Baseline comparison required for credibility (climatology + Stage-1 CNN).
- **Software-only** (no hardware); **Colab = GPU training host** (ADR-009).
- **No checkpoints, datasets, or secrets in Git** (RULE 12/13/14).
- **Frontend built last**, and only after pipeline + model proven (Golden Rule 11).

### Agreement / status markers used below
- `LOCKED` — required by problem statement or established decision (do not change).
- `CONFIRMED` — verified from an authoritative source.
- `PROPOSED` — recommended engineering design, tunable via config only.
- `UNRESOLVED` — must verify before implementing.

---

## 2. End-to-end architecture

```text
frontend (React+TS+Vite)   --HTTPS/JSON-->   backend (FastAPI)
   RULE 1/2: never Copernicus creds/direct       |
                                                 v
                 copernicusmarine  <- data-engineering (catalog/copernicus/harmonize/provenance)
                                                 |
                                     harmonized daily 0.25° tensors  [time, 7, H, W] / [time, 15, H, W]
                                                 |
                                     ML dataset (PyTorch windows) ---> Colab GPU training (GitHub sync)
                                                 |
                                     checkpoint + manifest  ->  model-registry (metadata only)
                                                 |
                                     backend inference (serves approved checkpoint)
                                                 |
                                                 v
                                           ocean dashboard
```

- RULE 3: backend never trains; Colab runs the training stack, backend serves an approved checkpoint.
- RULE 4: ML package (`ml/`) runs standalone in Colab — no frontend/backend imports.
- RULE 5/6/20, Golden 17/18: contract-safe tensor shapes, channel/depth ordering, API responses.
- RULE 10/11, ADR-007: temporal-only split; normalization statistics from training data only.

---

## 3. ML architecture specification (UNAMBIGUOUS — implement exactly this)

> This section is the **single source of truth for shapes/dims/loss/split** so OpenCode does not
> guess. Config files (`config/model.yaml`, `config/training.yaml`, `ml/configs/*.yaml`) mirror it.

### 3.1 Stage 1 — CNN baseline (PROPOSED baseline, built first)

```text
Input:  float32 [B, 7, H, W]        # one day, 7 surface channels
  Conv2D(7→32,  k=3, pad=1) + BatchNorm + ReLU
  Conv2D(32→64, k=3, pad=1) + BatchNorm + ReLU
  Conv2D(64→128,k=3, pad=1) + BatchNorm + ReLU
  Conv2D(128→128,k=3,pad=1) + ReLU
  → Ocean Embedding [B, 128, H, W]
  Decoder:
  Conv2D(128→128,k=3,pad=1) + ReLU
  Conv2D(128→64, k=3, pad=1) + ReLU
  Conv2D(64→32,  k=3, pad=1) + ReLU
  Conv2D(32→15,  k=3, pad=1)
Output: float32 [B, 15, H, W]      # 15 depths for that day
```

- Purpose: scientific baseline + proves the full data/Colab pipeline before adding time (Golden 12).
- Loss: MaskedMSE (same as Stage 2; §3.5).
- Note: this matches the recommended CNN encoder–decoder of SYSTEM_MEMORY_DUMP §17.

### 3.2 Stage 2 — CNN + ConvLSTM hybrid (PRIMARY, ADR-010)

```text
Input:  float32 [B, T, 7, H, W]    # T = lookback window of daily surface fields (T=10 default)
  ┌─ per-time-step spatial encoder (shared weights) ─┐
  │  Conv2D(7→32,  k=3, pad=1) + BN + ReLU           │
  │  Conv2D(32→64, k=3, pad=1) + BN + ReLU           │
  │  Conv2D(64→128,k=3, pad=1) + BN + ReLU           │
  └──────────────────────────────────────────────────┘
  → surface features [B, T, 128, H, W]
  ↓
  Stacked ConvLSTM (spatial + temporal jointly):
    ConvLSTMCell(128→128, k=3, pad=1)  (2 stacked layers; returns final-timestep hidden state)
  → latent spatio-temporal embedding [B, 128, H, W]
  ↓
  Decoder (same as Stage 1):
  Conv2D(128→128) + ReLU → Conv2D(128→64) + ReLU → Conv2D(64→32) + ReLU → Conv2D(32→15)
Output: float32 [B, 15, H, W]       # 15 depths for the TARGET day (last day of the window)
```

- **Why ConvLSTM over plain LSTM**: our data are spatial grids (`H×W`); a plain LSTM would flatten
  spatial info. ConvLSTM keeps convolutions inside the recurrent cell (Su et al. 2022).
- **Why hybrid over CNN-only**: daily data → time carries information. CNN-only sees "today → T";
  hybrid sees "Day-N … Today → temporal+spatial → T" (mesoscale/eddy evolution, §3 literature note).

### 3.3 Locked tensor dims & shapes (Stage 2)

| Symbol | Value | Status |
|--------|-------|--------|
| `B`    | batch size (config, default 8) | PROPOSED (config) |
| `T`    | lookback window = **10 days** | PROPOSED (config `lookback_days`) — fixed for v1 |
| `C_in` | 7 surface channels | LOCKED |
| `C_out`| 15 depths | LOCKED |
| `H, W` | region grid dims (0.25°) — e.g. BoB ≈ 68×80, AS ≈ 80×120 | LOCKED by region |
| Encoder | 7→32→64→128 (k=3, pad=1, BN+ReLU) | PROPOSED (config) |
| ConvLSTM | 2 layers, hidden 128, k=3 | PROPOSED (config) |
| Decoder | 128→64→32→15 | PROPOSED (config) |

Shapes:
- Stage 1: `[B,7,H,W] → [B,15,H,W]`
- Stage 2: `[B,10,7,H,W] → [B,128,H,W] → [B,15,H,W]` (ConvLSTM collapses time)

### 3.4 Data windowing / split (LOCKED: temporal only, RULE 10, ADR-007)

- Dataset stores daily tensors `[time, 7, H, W]` + targets `[time, 15, H, W]`.
- **Sample (Stage 2)** = window ending at target day `d`: inputs `X[d-T+1 .. d]` (T days), target
  `Y[d]`. Windows require `T` consecutive valid days; a day with missing inputs is skipped/bridged
  per `docs/04-data/missing-data-policy.md` (mask, never fill with garbage).
- **Split (LOCKED temporal):** dates, not rows.
  - TRAIN: earliest period (illustrative example only — exact years after coverage verification: §126).
  - VAL: later period.
  - TEST: latest held-out period (untouched during tuning, §89).
- **Leakage guard:** normalization stats computed on TRAIN only (RULE 11); a window at a fold boundary
  never overlaps the next fold's dates; ARGO validation independent (RULE 9).

### 3.5 Loss (LOCKED primary: MaskedMSE)

```text
L = mean( mask * (prediction - target)^2 )
```

- Mask = valid-ocean-cell mask (land/cloud/missing excluded; §36–37).
- Alternatives (config-only, post-baseline): Huber, depth-weighted, uncertainty NLL (§22–25).
- Evaluation metrics (LOCKED): RMSE, bias, Pearson correlation; computed overall + per-depth
  (§27–28); baseline comparison vs climatology + Stage-1 CNN (§30).

### 3.6 Normalization (LOCKED)

- z-score per channel from **training data only** (RULE 11): `x_norm = (x - mean)/std`.
- mean/std saved as artifacts; inverse transform applied before serving °C (§38–39).

### 3.7 Recommended training recipe (PROPOSED, config-driven)

- Optimizer: Adam, lr=1e-3; scheduler: ReduceLROnPlateau (patience 5, factor 0.5).
- Epochs: config (100 max), early stopping on validation masked RMSE (patience 15).
- Seeds pinned via `reproducibility.py` (seed=42). GRADIENT clip 1.0.
- Hardware: Colab GPU (ADR-009); `ml/tests` must pass on CPU locally first.

### 3.8 Implement in this order (two-stage, per team decision)

1. **Stage 1 CNN baseline** — proves `[7,H,W]→[15,H,W]` + full pipeline (tests green on CPU).
2. **Stage 2 ConvLSTM hybrid** — add temporal encoder/ConvLSTM (tests green on CPU), then train on
   Colab GPU and **compare Stage 1 vs Stage 2 + climatology** (credibility: §30, §91).
3. Transformer/attention (U-Net skips, depth-conditioned, uncertainty head) — **only after** Stage 2
   works (§19–20, §21).

---

## 4. Colab ↔ GitHub sync workflow (ADR-009)

### 4.1 Model of operation
1. **Local/OpenCode** authors all code (`ml/src`, `ml/configs`, `ml/scripts`, tests) and pushes to GitHub.
2. **Colab notebook** (`colab/oceanembed_training.ipynb`) at the start of each run:
   - verifies/installs the `ml/` deps (GPU torch),
   - clones the repo (or `git pull`),
   - mounts Drive for harmonized tensors + checkpoint output,
   - runs training with a pinned experiment config,
   - writes checkpoint to Drive (never Git), pushes a **manifest + metrics** back to GitHub.
3. **OpenCode** pulls the manifest/metrics, records the experiment, and can promote a checkpoint to the
   model registry (metadata only) so the backend can serve it.

### 4.2 What goes to GitHub vs stays out
| Goes to GitHub (code/config/manifest) | Stays OUT of Git (RULE 12/13/14) |
|---------------------------------------|----------------------------------|
| `ml/src/**`, `ml/scripts/**`, `ml/configs/**` | `*.pt`, `*.pth`, `*.ckpt` checkpoints |
| `colab/**` notebook + setup | `.env`, Copernicus credentials |
| experiment configs, evaluation reports (CSV/JSON) | raw/processed `.nc`/`.zarr` tensors |
| checkpoint **manifest** (sha256, metrics, data version) | large data blobs |

### 4.3 New files to create
- `colab/oceanembed_training.ipynb` — entry point that syncs repo + runs training on Colab GPU.
- `colab/requirements.txt` — Colab install set (mirrors `ml/pyproject.toml` gpu extras).
- `ml/scripts/train_colab_entry.py` — thin, notebook-friendly training entry (reads a config; writes
  checkpoint + manifest + metrics to a writable artifact dir).
- `ml/scripts/push_manifest.py` — uploads manifest + metrics JSON to a small Git-committed `results/` tree.

> All three must be **Colab-safe**: no local-only imports, no absolute paths, config/artifacts via
> env/args (`OPENCODE_SDL_CONTRACT.md` Phase 4). Test the exact run path locally on CPU first.

---

## 5. Phase 0 — Decisions / ADRs + Colab scaffolding

1. **Create ADR-009 Colab-as-GPU-training-host** (File: `docs/02-architecture/architecture-decisions/ADR-009-colab-training.md`)
   - Action: record Colab-GPU + GitHub-sync decision; note `infrastructure/cloud-training/` retained
     only as a future option.
   - Why: `AGENTS.md` requires ADR before code when an earlier assumption changes.
   - Dependencies: none. Risk: Low.
2. **Create/refine ADR-010 CNN+ConvLSTM hybrid** (File: `.../ADR-010-cnn-lstm-hybrid.md`)
   - Action: staged decision — CNN baseline first, CNN+ConvLSTM primary, Transformer optional
     experiment. Include memory-dump interpretation note (§0).
   - Why: architecture is now a team decision, not "CNN only".
   - Dependencies: none. Risk: Low.
3. **Add Colab folder + notebook skeleton** (File: `colab/oceanembed_training.ipynb`, `colab/requirements.txt`)
   - Action: minimal notebook that clones repo, sets PYTHONPATH to `ml/src`, runs `import oceanembed`.
   - Why: prove GitHub sync + import path.
   - Dependencies: Steps 1–2. Risk: Low.
4. **Colab-safe training entry stub** (File: `ml/scripts/train_colab_entry.py`)
   - Action: read config path from arg/env; import `oceanembed.training`; guarded placeholder run.
   - Dependencies: Step 3. Risk: Low.

**Exit gate (Phase 0):** From Colab, a notebook cell clones the repo and `import oceanembed` succeeds.

---

## 6. Phase 1 — Data engineering: prove one-day regional pipeline (first!)

Per Golden Rule 10/11: **one-day test before mass download; no model before data is proven.**

1. **Dataset discovery + verification** (File: `data-engineering/src/oceanembed_data/catalog.py`,
   script `scripts/discover.py` / `verify_datasets.py`)
   - Action: `copernicusmarine.describe()` for each candidate ID in `config/datasets.yaml`; verify
     variables/units/coverage/resolution/availability; set `verified: true` + `verified_at`; update
     `docs/04-data/dataset-registry.md` in the same commit (RULE 7).
   - Dependencies: Phase 0. Risk: **High** (Copernicus auth + catalogue drift).
2. **Copernicus ingestion wrapper** (File: `src/oceanembed_data/copernicus.py`)
   - Action: `subset()` region/date filtering, retries, `logging`, error handling; `subset_split_on`
     chunking.
   - Dependencies: Step 1. Risk: Medium.
3. **Regions + harmonization** (File: `src/oceanembed_data/regions.py`, `harmonization.py`)
   - Action: map `config/regions.yaml`; regrid to 0.25°, canonical channel ordering (variables.yaml),
     land/sea + validity masks, unit/coordinate normalization, daily UTC temporal alignment.
   - Dependencies: Steps 1–2. Risk: Medium.
4. **One-day regional proof** (File: `scripts/download_region.py`)
   - Action: download 1–7 days Bay of Bengal, all 7 inputs + GLORYS target; validate
     `[time,7,H,W]`/`[time,15,H,W]` shapes.
   - Dependencies: Steps 1–3. Risk: Medium.
5. **Provenance + manifest** (File: `src/oceanembed_data/provenance.py`, `scripts/generate_manifest.py`)
   - Dependencies: Step 4. Risk: Low.
6. **Tests** (File: `data-engineering/tests/`) — TDD: regridding ordering, masks, shapes, provenance.
   - Dependencies: Steps 2–5. Risk: Low.

**Exit gate (Phase 1):** one full day for Bay of Bengal exists as `[7,H,W]` inputs + `[15,H,W]`
GLORYS target; data-engineering tests pass; datasets registered `verified: true`.

---

## 7. Phase 2 — Dataset build for a small training period (Colab-executable)

1. **Historical download** (File: `scripts/download_historical.py`)
   - Action: chunked (year/month) bounded period downloads (1–2 years first) to `data/processed/`.
   - Dependencies: Phase 1. Risk: Medium (volume/network).
2. **Combine + build tensors** (File: `scripts/build_training_dataset.py`)
   - Action: assemble `[time,7,H,W]` + `[time,15,H,W]` + masks; **train-only normalization stats**
     stored as artifacts (RULE 11).
   - Dependencies: Step 1. Risk: Medium.
3. **Manifests** (File: `scripts/generate_manifest.py`)
   - Action: dataset manifest (version, sources, dates, split assignment) per schema.
   - Dependencies: Step 2. Risk: Low.
4. **Colab dataset hosting** — keep tensors on Drive/Zarr; notebook accesses path via env/config.

**Exit gate (Phase 2):** committed dataset manifest with TRAIN/VAL/TEST periods; tensors reproducible.

---

## 8. Phase 3 — ML package, Stage 1: CNN baseline (TDD, CPU-green)

Build `ml/` from scratch with TDD. This is the code Colab runs (phase 4 later).

- **Model files** (`ml/src/oceanembed/models/`): `cnn.py` (Stage 1 encoder–decoder),
  `oceanembed.py` (assemblies), `baselines.py` (climatology).
- **Loss** (`losses/`): `masked_mse.py` primary; `huber.py`, `depth_weighted.py`, `uncertainty_nll.py`
  for later.
- **Data** (`data/`): `dataset.py` (single-day samples + masks), `samplers.py` (temporal split,
  ADR-007), `dataloader.py`.
- **Preprocessing** (`preprocessing/`): loader/QC/temporal/spatial/regrid/masking/normalization
  (train-only stats).
- **Training** (`training/`): trainer, optimizer, scheduler, checkpointing, callbacks, reproducibility.
- **Evaluation** (`evaluation/`): metrics (RMSE/bias/corr), depth-wise, spatial, ARGO
  (independent), baseline comparison, reports.
- **Inference** (`inference/`): predictor, postprocess (denormalize+mask), profile.
- **Registry** (`registry/`): model_registry, artifact_registry, manifests.
- **Scripts** (`ml/scripts/`): train.py, evaluate.py, infer.py, export_model.py, validate_checkpoint.py
  + Colab entries (§4.3).
- **Configs** (`ml/configs/`): `cnn_v1.yaml` (Stage 1; from `config/model.yaml` +
  `config/training.yaml`).
- **Tests** (`ml/tests/`, ~80%): shape/contract `[7,H,W]→[15,H,W]`, temporal split ordering,
  normalization train-only, no-target-in-input, metric correctness, inference denormalization.

**Exit gate (Stage 1):** `pytest ml` green on CPU; `train.py --config cnn_v1.yaml` runs end-to-end on
a tiny dataset; checkpoint + manifest produced outside Git.

---

## 9. Phase 4 — ML package, Stage 2: CNN + ConvLSTM hybrid (PRIMARY, TDD, CPU-green)

Extends Stage 1 with temporal modeling — architecture exactly as §3.2.

- **Model files** (`ml/src/oceanembed/models/`): `convlstm.py` (ConvLSTMCell + stacked layers),
  `hybrid.py` (per-timestep encoder → ConvLSTM → decoder assembly).
- **Data** (`data/`): `window_dataset.py` — builds `[B,T,7,H,W]` windows ending at target day;
  windows need T consecutive valid days; **window never straddles a fold boundary** (ADR-007).
- **Configs** (`ml/configs/`): `hybrid_v1.yaml` with `lookback_days: 10`, ConvLSTM `[128,128]`, k=3.
- **Tests** (`ml/tests/`, ~80%): shape/contract `[B,10,7,H,W]→[B,15,H,W]`, window correctness,
  fold-boundary leakage test, train-only normalization, metrics, denormalization.

**Exit gate (Stage 2):** `pytest ml` green on CPU; `train.py --config hybrid_v1.yaml` runs end-to-end
on a tiny 10-day-window dataset; Stage-1 CNN still green.

---

## 10. Phase 5 — Colab GPU training + GitHub round-trip (Stage 1 → Stage 2)

1. **Colab real run** (File: `colab/oceanembed_training.ipynb`)
   - Action: clone/pull; mount Drive for tensors + checkpoints; install `colab/requirements.txt`;
     run Stage 1 (`cnn_v1.yaml`) then Stage 2 (`hybrid_v1.yaml`); log loss/epoch, GPU stats.
   - Dependencies: Phases 3–4, Phase 2 dataset. Risk: **High** — Colab runtime limits/quotas.
2. **Evaluate + manifest push** (File: `ml/scripts/evaluate.py`, `push_manifest.py`)
   - Action: RMSE/bias/corr depth-wise + ARGO validation; write `experiments/reports/` +
     manifest (small text); commit via GitHub.
   - Dependencies: Step 1. Risk: Medium.
3. **Record experiments** (File: `experiments/registry.yaml`) — per-run config hash, data version,
   metrics, checkpoint ref (not binary). Dependencies: Step 2. Risk: Low.
4. **Baseline comparison** (`evaluation/baseline_comparison.py`)
   - Action: climatology vs Stage-1 CNN vs Stage-2 hybrid. Dependencies: Steps 1–2. Risk: Low.

**Exit gate (Phase 5):** Stage-2 hybrid trained with quantified depth-wise RMSE/bias/correlation,
ARGO-validated, compared against climatology + Stage-1 CNN; manifest committed (binary outside Git).

---

## 11. Phase 6 — Model registry + backend inference (serve approved checkpoint)

1. **Export serving artifact** (File: `ml/scripts/export_model.py`)
   - Action: torchscript/ONNX/pickled artifact + inputs/outputs spec (Stage 2 — windowed input!);
     store in object storage / `model-registry/models/` (gitkept, binary not committed).
2. **Registry entry** (File: `model-registry/registry.yaml`) — version, artifact_uri, sha256,
   trained_on, evaluation.
3. **Backend app** (File: `backend/app/` — `main.py`, `core/config.py`, `schemas/`,
   `services/inference.py`, `integrations/storage.py`, `api/v1/*`)
   - Action: FastAPI `/api/ocean/map`, `/profile`, `/health`, `/api/model/version`; Pydantic schemas
     per `contracts/api/*`; **inference consumes a T-day lookback window** per model-input contract
     (RULE 5); light-weight inference module only (RULE 3).
4. **Backend tests** (File: `backend/tests/`) — endpoint↔contract, config validation, no-cred
   leakage, inference mock. Dependencies: Step 3. Risk: Low.

**Exit gate (Phase 6):** `/api/ocean/profile?region=bay_of_bengal&lat=..&lon=..&date=..` returns a
valid `ocean-profile.schema.json` payload from the approved Stage-2 checkpoint; no secrets exposed.

---

## 12. Phase 7 — Frontend dashboard (last, Golden Rule 11)

Only after Phases 5–6 prove pipeline + model.

1. **Bootstrap** (File: `frontend/package.json`, `src/main.tsx`, `App.tsx`, `vite.config.*`)
   - React+TS+Vite; typed API client per `contracts/api/*`.
2. **Controls** (`src/components/controls/`) — region (BoB/AS), date, depth slider.
3. **Map** (`src/components/map/`) — predicted temperature at depth (Leaflet/MapLibre).
4. **Profile** (`src/components/profile/`) — 15-depth profile on grid-cell click (+ optional
   uncertainty, ARGO comparison).
5. **State + hooks** (`src/state/`, `src/hooks/`).
6. **Validation panel** (`src/components/validation/`).
7. **Frontend tests** — React Testing Library.
8. **Integration** — docker-compose backend+frontend.

**Exit gate (Phase 7):** user opens dashboard → region/date/depth → map → grid-cell → 15-depth profile.

---

## 13. Phase 8 — Hardening, observability, packaging (optional if time)

- Env-driven config validation (`backend/app/core/config.py`); `.env` never committed.
- Structured logging + error envelopes per `contracts/api/error.schema.json`.
- Docker images (backend/frontend/inference); observability stubs.
- Finalize `docs/05-ml/model-card.md` with **real** numbers (never invented).

---

## 14. Testing strategy summary

- **Unit**: shapes/contracts, split ordering, window correctness, normalization, metrics, losses,
  configs, API schemas.
- **Integration**: data-eng day proof; backend↔contract; Colab entry on CPU.
- **E2E**: Colab run (GPU) → manifest → backend serves → frontend renders.
- **Coverage**: ≥80% backend + ML (`pytest-cov`); frontend component tests.
- **Colab-safety test**: every `ml` entry point runs on a clean CPU env with only `colab/requirements.txt`.

## 15. Risks & mitigations

- **Copernicus auth / catalogue drift (RULE 7)** → Phase 1 `describe()` proof first; creds env-only.
- **Colab runtime/GPU quota/timeouts** → bounded epochs, per-epoch checkpointing, Drive persistence,
  resumable notebook; Colab-safe deps.
- **ConvLSTM memory at [B,10,128,H,W]** → start BoB (68×80); batch 8; reduce B or T if OOM
  (config-only).
- **Window starvation at fold starts** → windows need T consecutive valid days; ensure periods ≥ T
  days; mask/skip per missing-data policy (never fabricate).
- **Data volume for download** → one-day proof first; chunked `subset_split_on`.
- **Normalization/leakage** → train-only stats in build script (Phase 2→3→4).
- **Checkpoints in Git** → strict `.gitignore`; only manifests/metrics pushed.
- **Frontend too early** → Phase 7 explicitly gated behind Phases 5–6.

## 16. Success criteria (definition of done)

- [ ] Phase 0 gate: Colab clones repo + `import oceanembed` works.
- [ ] Phase 1 gate: one-day BoB `[7,H,W]`/`[15,H,W]` dataset + registered datasets.
- [ ] Stage 1 gate: `ml` tests green on CPU; CNN baseline trains end-to-end locally.
- [ ] Stage 2 gate: ConvLSTM hybrid tests green on CPU; hybrid trains on tiny 10-day windows.
- [ ] Phase 5 gate: Colab-trained Stage-2 hybrid with depth-wise metrics + ARGO + baseline
      comparison (vs climatology + Stage-1 CNN) + committed manifest (binary outside Git).
- [ ] Phase 6 gate: backend serves `/api/ocean/profile` from approved checkpoint, contract-valid.
- [ ] Phase 7 gate: dashboard renders map + profile from the model.
- [ ] All tests pass; coverage ≥80% backend/ML; no secrets/datasets/checkpoints committed.