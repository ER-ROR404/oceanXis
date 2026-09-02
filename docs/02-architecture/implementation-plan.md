# Implementation Plan: OceanEmbed — End-to-End Build (Colab-Powered Training)

> Status: PLAN (authority for the coding phase)
> Companion: `AGENTS.md`, `OPENCODE_SDL_CONTRACT.md`, `SYSTEM_MEMORY_DUMP.md`, `docs/**`, `contracts/**`.
> Golden Rule 11: **No frontend before the data pipeline + model are proven.**

---

## 0. What this plan covers

OceanEmbed (SIH26066) is currently a **pre-build skeleton**: docs, contracts, config, and directory
structures exist, but **no application/ML/data code has been written** (verified: no `.py` source
under `ml/src`, `data-engineering/src`, `backend/app`, `frontend/src`).

This plan takes the skeleton to a working **regional MVP** with a critical constraint chosen by the
team:

> **Model training runs in Google Colab (GPU), not locally, not in cloud-training jobs.**
> Code and config are shared between local/OpenCode and Colab via **GitHub** (clone/pull in Colab,
> push checkpoint manifests/metrics back).

This replaces the earlier `infrastructure/cloud-training/` GPU-job assumption (see note in §4 /
need for an ADR in Phase 0).

### Repository (git management)

- **Remote**: `origin → https://github.com/ER-ROR404/oceanXis.git` (fresh/empty at start of build).
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
  branch; checkpoints/data stay out of Git (§3).

---

## 1. Requirements (from problem statement + decisions)

- 7 surface input channels: SST, SSS, SSH/SLA, current U, current V, wind U, wind V.
- 15 output depths: 0,5,10,20,30,50,75,100,125,150,200,300,500,700,1000 m.
- Grid 0.25°×0.25°, daily, North Indian Ocean 5–30°N / 45–105°E; MVP regions Bay of Bengal & Arabian Sea.
- GLORYS = training/reference target; ARGO = independent validation.
- Metrics: RMSE, bias, correlation (overall + depth-wise).
- Baseline comparison (climatology) for credibility.
- **Software-only** (no hardware); **Colab = GPU training host**.
- **No checkpoints, datasets, or secrets in Git** (RULE 12/13/14).
- **Frontend built last**, and only after pipeline + model proven (Golden Rule 11).

### Agreement / status markers used below
- `LOCKED` — required by problem statement or established decision.
- `CONFIRMED` — verified from an authoritative source.
- `PROPOSED` — recommended engineering design.
- `UNRESOLVED` — must verify before implementing.

---

## 2. Architecture (unchanged boundaries, one Colab adjustment)

```text
frontend (React+TS+Vite)   --HTTPS/JSON-->   backend (FastAPI)
   RULE 1/2: never Copernicus creds/direct       |
                                                v
                copernicusmarine  <- data-engineering (catalog/copernicus/harmonize/provenance)
                                                |
                                    harmonized daily 0.25° tensors
                                                |
                                    ML dataset (PyTorch) ---> Colab GPU training (GitHub sync)
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
- RULE 5/6/20, Golden 17/18: contracts for tensor shapes, channel/depth ordering, API responses.

---

## 3. Colab ↔ GitHub sync workflow (new decision, applied throughout)

This is the mechanism that makes Colab the GPU host while keeping `AGENTS.md`/OpenCode the editor.

### 3.1 Model of operation
1. **Local/OpenCode** authors all code (`ml/src`, `ml/configs`, `ml/scripts`, tests) and pushes to GitHub.
2. **Colab notebook** (`colab/oceanembed_training.ipynb`) at the start of each run:
   - verifies/installs the `ml/` deps (GPU torch),
   - clones the repo (or `git pull`),
   - runs a **datasets/blob or Google Drive** mount for the harmonized training tensors,
   - runs training with a pinned experiment config,
   - writes checkpoint to Drive/gist **not to Git**, and pushes a **manifest + metrics** back to GitHub.
3. **OpenCode** pulls the manifest/metrics, records the experiment, and can promote a checkpoint to the
   model registry (metadata only) so the backend can serve it.

### 3.2 What goes to GitHub vs stays out
| Goes to GitHub (code/config/manifest) | Stays OUT of Git (RULE 12/13/14) |
|---------------------------------------|----------------------------------|
| `ml/src/**`, `ml/scripts/**`, `ml/configs/**` | `*.pt`, `*.pth`, `*.ckpt` checkpoints |
| `colab/**` notebook + setup | `.env`, Copernicus credentials |
| experiment configs, evaluation reports (CSV/JSON) | raw/processed `.nc`/`.zarr` tensors |
| checkpoint **manifest** (sha256, metrics, data version) | large data blobs |

### 3.3 New files to create
- `colab/oceanembed_training.ipynb` — entry point that syncs repo + runs training on Colab GPU.
- `colab/requirements.txt` — Colab install set (mirrors `ml/pyproject.toml` gpu extras).
- `ml/scripts/train_colab_entry.py` — thin, notebook-friendly training entry that reads a config
  and writes checkpoint + manifest + metrics to a writable artifact dir (Drive/xarray store).
- `ml/scripts/push_manifest.py` — uploads manifest + metrics JSON to a `results/` tree that is
  committed to GitHub (small text only).

> All three must be **Colab-safe**: no imports that exist only locally, absolute-path-free, and
> read config/artifacts from env or args (`OPENCODE_SDL_CONTRACT.md` Phase 4). Test the exact run
> path locally with CPU before running on Colab GPU.

---

## 4. Phase 0 — Decision / ADR + Colab workflow scaffolding

Goal: record the Colab decision and prove the Colab↔GitHub loop with a trivial run.

1. **Create ADR-009 Colab-as-GPU-training-host** (File: `docs/02-architecture/architecture-decisions/ADR-009-colab-training.md`)
   - Action: ADR recording that training runs in Colab GPU (not `cloud-training` GPU jobs), with
     GitHub sync for code and Drive for checkpoints. Note impact on `infrastructure/cloud-training/`
     (retain as optional future path only).
   - Why: `AGENTS.md` requires recording architectural changes via ADR before code changes; this
     changes an earlier assumption.
   - Dependencies: None. Risk: Low.

2. **Add Colab folder + notebook skeleton** (File: `colab/oceanembed_training.ipynb`, `colab/requirements.txt`)
   - Action: minimal notebook that clones repo, sets PYTHONPATH to `ml/src`, and runs
     `oceanembed` import smoke test.
   - Why: prove GitHub sync + import path before real training.
   - Dependencies: Step 1. Risk: Low.

3. **Colab-safe training entry stub** (File: `ml/scripts/train_colab_entry.py`)
   - Action: read config path from arg/env; import `oceanembed.training`; placeholder run guarded
     with try/except + `logging`.
   - Why: establish the exact entry the notebook calls (Phase 4 safety).
   - Dependencies: Step 2. Risk: Low.

**Exit gate (Phase 0):** From Colab, a notebook cell clones the repo and `import oceanembed` succeeds.

---

## 5. Phase 1 — Data engineering: prove one-day regional pipeline (LOCKED first)

Per Golden Rule 10/11: **one-day test before mass download; no model before data is proven.**

1. **Dataset discovery + verification** (File: `data-engineering/src/oceanembed_data/catalog.py`,
   script `scripts/discover.py` / `verify_datasets.py`)
   - Action: call `copernicusmarine.describe()` for each candidate ID in `config/datasets.yaml`;
     verify variables, units, coverage, resolution, availability; set `verified: true` + `verified_at`;
     update `docs/04-data/dataset-registry.md` in the same commit (RULE 7).
   - Why: never guess dataset IDs (RULE 7).
   - Dependencies: Phase 0. Risk: **High** — Copernicus auth + catalogue drift; do in Colab or a
     machine with network to Copernicus.

2. **Copernicus ingestion wrapper** (File: `src/oceanembed_data/copernicus.py`)
   - Action: `subset()` with region/date filtering, retries, `logging`, error handling; supports
     `subset_split_on` chunking.
   - Why: single place that knows Copernicus (RULE 2/7).
   - Dependencies: Step 1. Risk: Medium.

3. **Regions + harmonization** (File: `src/oceanembed_data/regions.py`, `harmonization.py`)
   - Action: map `config/regions.yaml` bounds; regrid every product to 0.25°, canonical channel
     ordering (variables.yaml), land/sea + validity mask, unit/coordinate normalization,
     temporal alignment (daily UTC convention).
   - Why: tensor contract demands `[7,H,W]` aligned to the 0.25° grid.
   - Dependencies: Steps 1–2. Risk: Medium.

4. **One-day regional proof script** (File: `scripts/download_region.py`)
   - Action: download 1–7 days for Bay of Bengal, all 7 inputs + GLORYS target; write NetCDF/Zarr
     under `data/processed/`; validate shapes `[7,H,W]`/`[15,H,W]`.
   - Why: proves the pipeline end-to-end for one day (Golden Rule 10/11).
   - Dependencies: Steps 1–3. Risk: Medium.

5. **Provenance + manifest** (File: `src/oceanembed_data/provenance.py`, `scripts/generate_manifest.py`)
   - Action: record lineage per sample/asset per `contracts/data/provenance.schema.json`.
   - Why: every scientific claim traceable (Golden Rule 16/21).
   - Dependencies: Step 4. Risk: Low.

6. **Unit/integration tests** (File: `data-engineering/tests/`)
   - Action: TDD — regridding ordering, mask correctness, snapshot/day shape contract, provenance.
   - Why: `OPENCODE_SDL_CONTRACT` Phase 4 + 80% target.
   - Dependencies: Steps 2–5. Risk: Low.

**Exit gate (Phase 1):** one full day for Bay of Bengal exists as `[7,H,W]` inputs + `[15,H,W]`
GLORYS target; `make test` passes for data-engineering; datasets registered `verified: true`.

---

## 6. Phase 2 — Dataset build for a small training period (Colab-executable)

Scales the Phase 1 proof into a training dataset, keeping everything Colab-compatible.

1. **Historical download script** (File: `scripts/download_historical.py`)
   - Action: chunked (year/month) downloads for a bounded period (e.g., 1–2 years first); writes to
     `data/processed/`.
   - Why: establish temporal split via **date periods**, not random (RULE 10).
   - Dependencies: Phase 1. Risk: Medium — data volume/network.

2. **Combine + build tensors** (File: `scripts/build_training_dataset.py`)
   - Action: assemble `[time,7,H,W]` and `[time,15,H,W]` arrays with valid-data masks; **compute
     normalization (mean/std) from training portion only** and store as artifacts (RULE 11).
   - Why: no leakage; normalization train-only (RULE 11, §38–39).
   - Dependencies: Step 1. Risk: Medium.

3. **Manifests** (File: `scripts/generate_manifest.py`)
   - Action: dataset manifest (version, sources, dates, split assignment) per schema.
   - Why: reproducibility + Colab pulls versioned data (§78, §80, §114).
   - Dependencies: Step 2. Risk: Low.

4. **ML datasets/loaders consumed by Colab** (init in Phase 3; loaders reference this dataset).

**Exit gate (Phase 2):** a committed dataset manifest with TRAIN/VAL periods; tensors reproducible.

---

## 7. Phase 3 — ML package: models, losses, training, evaluation (Colab-hosted training)

Build `ml/` from scratch with TDD. This is the code Colab runs.

**Model files** (`ml/src/oceanembed/`):
- `models/oceanembed.py`, `encoder.py`, `decoder.py`, `baselines.py` — CNN encoder–decoder per
  `model-architecture.md` baseline (§17); U-Net/depth-conditioned only after baseline works (§18–20).

**Loss files** (`losses/`): `masked_mse.py` (primary), `huber.py`, `depth_weighted.py`, `uncertainty_nll.py`.

**Data files** (`data/`): `dataset.py` (PyTorch Dataset), `samplers.py` (temporal split), `dataloader.py`.

**Preprocessing** (`preprocessing/`): `loader.py`, `qc.py`, `temporal.py`, `spatial.py`, `regrid.py`,
`masking.py`, `normalization.py` (train-only stats).

**Training** (`training/`): `trainer.py`, `optimizer.py`, `scheduler.py`, `checkpointing.py`,
`callbacks.py`, `reproducibility.py` (seeds).

**Evaluation** (`evaluation/`): `metrics.py` (RMSE/bias/corr), `depth_wise.py`, `spatial.py`,
`argo.py` (independent validation), `baseline_comparison.py`, `reports.py`.

**Inference** (`inference/`): `predictor.py`, `postprocess.py` (denormalize+mask), `profile.py`.

**Registry** (`registry/`): `model_registry.py`, `artifact_registry.py`, `manifests.py`.

**Scripts** (`ml/scripts/`): `train.py`, `evaluate.py`, `infer.py`, `export_model.py`,
`validate_checkpoint.py`, plus Colab entries from §3.3.

**Configs** (`ml/configs/`): populate `baseline.yaml`, `cnn_v1.yaml` from `config/model.yaml` +
`config/training.yaml`.

**Tests** (`ml/tests/`, TDD, ~80%): shape/contract (`[7,H,W]`→`[15,H,W]`), temporal split ordering,
normalization train-only, no-target-in-input, metric correctness (RMSE/bias/corr), inference
denormalization.

> Even though Colab trains, `ml/tests` must pass **locally on CPU** so Colab can import the same
> code cache-free (`OPENCODE_SDL_CONTRACT` Phase 4: Colab compatibility).

**Exit gate (Phase 3):** `pytest ml` green on CPU; `ml/scripts/train.py --config baseline.yaml` runs
end-to-end on a tiny dataset; a checkpoint + manifest is produced outside Git.

---

## 8. Phase 4 — Colab GPU training + GitHub round-trip

The pivotal Phase: real training on Colab, results back in the repo.

1. **Colab notebook real run** (File: `colab/oceanembed_training.ipynb`)
   - Action: clone/pull repo; mount Drive for tensors + checkpoints; install `colab/requirements.txt`;
     run `train_colab_entry.py --config ml/configs/baseline.yaml`; log loss/epoch, GPU stats.
   - Why: establishes the reproducible Colab training loop.
   - Dependencies: Phase 3 (code), Phase 2 (dataset). Risk: High — Colab runtime limits, GPU quotas.

2. **Evaluate + manifest push** (File: `ml/scripts/evaluate.py` → report; `ml/scripts/push_manifest.py`)
   - Action: compute RMSE/bias/corr depth-wise + ARGO validation; write `experiments/reports/`
     + `model-registry` manifest (small text); commit via GitHub.
   - Why: results are reproducible and traceable; ARGO independent (RULE 9).
   - Dependencies: Step 1. Risk: Medium.

3. **Record experiment** (File: `experiments/registry.yaml`)
   - Action: entry per run with config hash, data version, metrics, checkpoint ref (not the binary).
   - Why: versioned experiment tracking (§113–114).
   - Dependencies: Step 2. Risk: Low.

4. **Baseline comparison** (File: `ml/src/oceanembed/evaluation/baseline_comparison.py`)
   - Action: train climatology baseline; compare OceanEmbed vs climatology.
   - Why: credibility (Golden Rule 11, §30/91).
   - Dependencies: Step 1–2. Risk: Low.

**Exit gate (Phase 4):** a trained checkpoint with quantified depth-wise RMSE/bias/correlation,
validated (incl. ARGO), a baseline comparison, and a manifest committed — **checkpoint binary stays
out of Git** (RULE 13).

---

## 9. Phase 5 — Model registry + backend inference (serve approved checkpoint)

1. **Export serving artifact** (File: `ml/scripts/export_model.py`)
   - Action: torchscript/ONNX or pickled artifact + inputs/outputs spec; store in object storage /
     `model-registry/models/` (gitkept, binary not committed).
   - Why: separates training from serving (RULE 3).
   - Dependencies: Phase 4. Risk: Medium.

2. **Registry entry** (File: `model-registry/registry.yaml`)
   - Action: register approved version with `artifact_uri`, `sha256`, trained_on, evaluation.
   - Why: canonical promotion path (checkpoint-policy.md).
   - Dependencies: Step 1. Risk: Low.

3. **Backend app scaffolding** (File: `backend/app/` — `main.py`, `core/config.py`, `schemas/`,
   `services/inference.py`, `integrations/storage.py`, `api/v1/*`)
   - Action: FastAPI app with `/api/ocean/map`, `/profile`, `/health`, `/api/model/version`;
     Pydantic schemas matching `contracts/api/*`;
     load checkpoint via `core/config` (env-driven), serve via a **separate light-weight inference
     module** (does not import the training stack, RULE 3).
   - Why: orchestration layer; API responses conform to contracts (RULE 6).
   - Dependencies: Steps 1–2, Phase 4. Risk: Medium.

4. **Backend tests** (File: `backend/tests/`)
   - Action: endpoint contract tests against `contracts/api/*.schema.json`, config validation, no-cred
     leakage, inference runtime mock.
   - Why: `OPENCODE_SDL_CONTRACT` Phase 4 + RULE 1/2.
   - Dependencies: Step 3. Risk: Low.

**Exit gate (Phase 5):** `/api/ocean/profile?region=bay_of_bengal&lat=..&lon=..&date=..` returns a
valid `ocean-profile.schema.json` payload from the approved checkpoint; no secrets exposed.

---

## 10. Phase 6 — Frontend dashboard (last, per Golden Rule 11)

Only after Phase 4/5 prove pipeline + model.

1. **Frontend bootstrap** (File: `frontend/package.json`, `src/main.tsx`, `App.tsx`, `vite.config.*`)
   - Action: React+TS+Vite; typed API client consuming `contracts/api/*` (`src/api`, `src/types`).
   - Dependencies: Phase 5 API. Risk: Low/Medium.

2. **Region/date/depth controls** (File: `src/components/controls/`)
   - Action: select Bay of Bengal / Arabian Sea, date, depth slider.
   - Dependencies: Step 1. Risk: Low.

3. **Map view** (File: `src/components/map/`) — predicted temperature at depth (Leaflet/MapLibre).
4. **Profile view** (File: `src/components/profile/`) — 15-depth vertical profile on grid-cell click
   (+ optional uncertainty, + ARGO comparison).
5. **State + hooks** (File: `src/state/`, `src/hooks/useOceanMap.ts`, `useOceanProfile.ts`, `useMetadata.ts`).
6. **Validation panel** (File: `src/components/validation/`).
7. **Frontend tests** (File: `frontend/src/**/__tests__/`) — React Testing Library.
8. **Integration** — docker-compose wiring backend+frontend.

**Exit gate (Phase 6):** user opens the dashboard, picks region/date/depth, sees the map, clicks a
grid cell, and sees the 15-depth profile from the model.

---

## 11. Phase 7 — Hardening, observability, packaging (optional if time)

- Env-driven config validation (`backend/app/core/config.py`); `.env` never committed.
- Logging (structured) + error envelopes per `contracts/api/error.schema.json`.
- Docker images for backend + frontend + inference; `infrastructure/docker/*`, compose.
- Observability stubs (`observability/`) if time.
- Finalize `docs/05-ml/model-card.md` with **real** numbers (never invented).

---

## 12. Testing strategy summary

- **Unit**: shapes/contracts, split ordering, normalization, metrics, losses, configs, API schemas.
- **Integration**: data-eng day proof; backend endpoint↔contract; Colab entry on CPU.
- **E2E**: Colab notebook run (GPU) → manifest → backend serves → frontend renders profile.
- **Coverage**: ≥80% backend + ML (`pytest-cov`); frontend component tests.
- **Colab-safety test**: every `ml` entry point runs on a **clean CPU env with only `colab/requirements.txt`**.

## 13. Risks & mitigations

- **Copernicus auth / catalogue drift (RULE 7)** → Phase 1 describe() proof first; creds env-only.
- **Colab runtime/GPU quota/timeouts** → bounded epochs, checkpoint every epoch, Drive persistence;
  notebook resumable; keep Colab-safe deps (no local-only imports).
- **Data volume for download** → one-day proof before mass download; chunked `subset_split_on`.
- **Normalization/leakage** → train-only stats computed in build script, stored as artifacts (Phase 2→3).
- **Checkpoints in Git** → strict `.gitignore` (`*.pt` etc.); only manifests/metrics pushed.
- **Frontend too early** → Phase 6 is explicitly gated behind Phases 4–5.

## 14. Success criteria (definition of done)

- [ ] Phase 0 gate: Colab can clone repo and import `oceanembed`.
- [ ] Phase 1 gate: one-day Bay of Bengal `[7,H,W]`/`[15,H,W]` dataset + registered datasets.
- [ ] Phase 3 gate: `ml` tests green on CPU; baseline trains end-to-end locally.
- [ ] Phase 4 gate: Colab-trained checkpoint with depth-wise metrics + ARGO validation + baseline
      comparison + committed manifest (binary outside Git).
- [ ] Phase 5 gate: backend serves `/api/ocean/profile` from approved checkpoint, contract-valid.
- [ ] Phase 6 gate: dashboard renders map + profile from the model.
- [ ] All tests pass; coverage ≥80% backend/ML; no secrets/datasets/checkpoints committed.
