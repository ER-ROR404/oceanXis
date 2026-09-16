<div align="center">

# OceanEmbed

**Satellite-embedding deep learning framework for reconstructing subsurface ocean temperature from surface observations.**

Ministry of Earth Sciences (MoES) · INCOIS · SIH 2026

[![Tests](https://img.shields.io/badge/tests-443%20passed-brightgreen)](#testing)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

</div>

---

OceanEmbed is a surface-observation-driven deep learning system that harmonizes seven daily ocean variables onto a 0.25° grid, learns a latent representation of the North Indian Ocean surface state, and reconstructs temperature at 15 standard subsurface depths (0–1000 m). It validates against GLORYS reanalysis and independent ARGO float observations, then exposes the result as an interactive scientific data product.

## Capabilities

| Capability | Description |
|:-----------|:------------|
| **Multi-variable ingestion** | Ingests 7 surface channels: SST, SSS, SSH/SLA, current U/V, wind U/V from Copernicus Marine datasets |
| **Spatial harmonization** | Resamples all variables onto a unified 0.25° daily grid covering the North Indian Ocean (5–30°N, 45–105°E) |
| **Temporal encoding** | Processes a 7-day surface sequence through a CNN + ConvLSTM architecture to capture ocean dynamics |
| **Subsurface reconstruction** | Predicts temperature at 15 standard depths (0, 5, 10, 20, 30, 50, 75, 100, 125, 150, 200, 300, 500, 700, 1000 m) |
| **Uncertainty quantification** | Outputs a per-cell ±1σ model uncertainty estimate derived from learned variance |
| **Independent validation** | Validates against ARGO floats (285/291 matched profiles, RMSE 1.35°C, bias +0.61°C, correlation 0.99) |
| **Interactive visualization** | Leaflet-based map with per-cell rendering, depth profiling, and uncertainty exploration |
| **Honest data sourcing** | All data provenance is disclosed; no fabricated scores, no fake real-time claims |

## Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│                     7 Surface Channels                          │
│         SST · SSS · SSH/SLA · Current U/V · Wind U/V           │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                    harmonization
                           │
                           ▼
              ┌────────────────────────┐
              │   Daily 0.25° Tensor   │
              │       [7, H, W]        │
              └───────────┬────────────┘
                          │
                   7-day sequence
                          │
                          ▼
              ┌────────────────────────┐
              │    Surface Encoder     │
              │    (CNN → Embedding)   │
              └───────────┬────────────┘
                          │
                          ▼
              ┌────────────────────────┐
              │     Ocean Embedding    │
              │   (latent repr.)       │
              └───────────┬────────────┘
                          │
                          ▼
              ┌────────────────────────┐
              │     Depth Decoder      │
              │  (ConvLSTM → 15-depth) │
              └───────────┬────────────┘
                          │
                          ▼
              ┌────────────────────────┐
              │  Temperature [15,H,W]  │
              │  + Uncertainty [15,H,W]│
              │   0–1000 m, 15 levels  │
              └───────────┬────────────┘
                          │
                ┌─────────┴─────────┐
                ▼                   ▼
        ┌──────────────┐   ┌──────────────┐
        │ GLORYS target │   │ ARGO (indep.)│
        │  (training)   │   │ (validation) │
        └──────────────┘   └──────────────┘
```

## Repository Structure

| Directory | Purpose |
|:----------|:--------|
| `backend/` | FastAPI application — ingestion, preprocessing, inference, profile & prediction APIs |
| `ml/` | PyTorch training, evaluation, and inference package |
| `data-engineering/` | Copernicus Marine data acquisition and harmonization |
| `frontend/` | React + TypeScript + Vite interactive dashboard |
| `contracts/` | Versioned API, data, and ML interface contracts |
| `config/` | Domain, runtime, and dataset configuration |
| `database/` | Alembic migrations and seed data |
| `docs/` | Engineering documentation (architecture, decisions, operations) |
| `scripts/` | Dataset building, demo cache generation, verification |
| `infrastructure/` | Docker, Terraform, Kubernetes skeletons (production target) |

## UI Components

The frontend has two pages, each built from composable scientific components.

### Explorer Page

The primary workspace — a full-viewport map of the Bay of Bengal with floating controls.

| Component | Function | Output |
|:----------|:---------|:-------|
| **OceanMap** | Leaflet map with a custom `CellCanvas` layer that renders each 0.25° grid cell as a color-coded rectangle. No stretched rasters — each cell is individually projected. | Color-coded temperature or uncertainty field on a dark basemap |
| **MapColorbar** | Horizontal color scale positioned over the map. Domain derived from real loaded field data. | Visual reference for temperature (°C) or uncertainty (±1σ) values |
| **ControlPanel** | Floating panel with layer toggle (temperature/uncertainty), region selector, location picker, and reset view. | Controls the active visualization layer and geographic context |
| **DepthRail** | Vertical rail of 15 canonical model depths (0–1000 m). Active depth highlighted. | Selects which depth slice to display on the map |
| **DateBar** | Previous/next stepper with direct-jump select dropdown. Walks real availability dates. | Navigates through available reconstruction dates |
| **ProfileChart** | Recharts `ComposedChart` showing temperature (horizontal) vs depth (vertical, inverted). Includes ±1σ uncertainty band. | Vertical thermal profile with uncertainty envelope for a clicked cell |
| **DepthColumn** | Detailed table of all 15 depth levels with color-coded bars, exact temperature values, and ±1σ uncertainty. | Numerical depth profile for detailed inspection |
| **ExplainLocation** | Deterministic text summary of a clicked location's profile characteristics. No LLM involved. | Natural-language explanation of the local water column |
| **StatusBanner** | Honest data-source indicator: `model_prediction`, `cached_data`, `fallback_demo`, or `unavailable`. | Tells the user whether they're seeing live model output or cached data |

**Interaction flow:**
1. Map loads with temperature field at a selected depth and date
2. Hover a cell → coordinate + temperature tooltip
3. Click a cell → Leaflet popup with value + side panel opens with 15-depth profile, uncertainty band, depth column, and location explanation
4. Toggle layer → switches between temperature and uncertainty visualization
5. Change depth → map updates to the selected depth slice
6. Change date → map updates to the selected date

### Validation & Model Page

Scientific credibility documentation — every number traced to committed data assets.

| Component | Function | Output |
|:----------|:---------|:-------|
| **InputProvenancePanel** | Lists the 7 surface input channels with full variable names and provenance disclosure. | Honest catalog of what the model consumes |
| **ModelFlowExplainer** | Expandable pipeline visualization: 7 variables → harmonization → CNN → ConvLSTM → 15-depth reconstruction. | Step-by-step model architecture explanation |
| **ArgoValidationPanel** | Independent ARGO float validation: aggregate RMSE, bias, correlation, depth-wise table with per-depth statistics, and disclosed limitations. | Quantitative validation against independent observations |
| **RmseDepthChart** | Bar chart of RMSE by depth from the ARGO validation summary. | Depth-wise error profile visualization |

**Validation results (from committed ARGO summary):**

| Metric | Value |
|:-------|:------|
| Matched profiles | 285 / 291 |
| Depth observations | ~4,275 |
| RMSE | 1.35 °C |
| Bias | +0.61 °C |
| Correlation | 0.99 |
| Known limitation | 75–150 m thermocline region has higher error and warm bias |

## Quick Start

### Prerequisites

- Python 3.11
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Node.js 20+ / npm

### Install

```bash
make setup                  # creates .venv + installs backend, ml, data-engineering
cd frontend && npm install  # frontend dependencies
```

### Configure

```bash
cp .env.example .env        # .env is gitignored
```

Copernicus credentials in `.env` are only used by the data-ingestion pipeline. The demo works without them.

The one frontend setting that matters:

```bash
VITE_API_BASE_URL=/api/v1  # must include /v1, keep it relative
```

> ⚠️ `VITE_API_BASE_URL=http://localhost:8000/api` (missing `/v1`) bakes a broken, cross-origin
> API base into the build. Prefer the relative default. This is the most common setup trap.

### Run

**Option A — single port (recommended):**

```bash
# 1. ML inference service (live predictions)
TENSOR_DIR=data/tensors REGION=bay_of_bengal \
  CHECKPOINT_PATH=data/checkpoints/hybrid_v1/best.pt \
  HYBRID_CFG_PATH=ml/configs/hybrid_v1.yaml \
  .venv/bin/python -m oceanembed.serving.server &

# 2. Build frontend
cd frontend && npm run build && cd ..

# 3. Backend + static UI on :8000
cd backend
OCEANEMBED_MODEL_SERVICE_URL=http://127.0.0.1:8080 \
  ../.venv/bin/python -m uvicorn app.main:create_app --factory \
  --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000/**

**Option B — dev servers (hot reload):**

```bash
# Terminal 1
cd backend && ../.venv/bin/python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000

# Terminal 2
cd frontend && npm run dev    # http://localhost:5173
```

### Data Assets (not committed)

| Asset | Path | Produced by |
|:------|:-----|:------------|
| Tensor store (730 days, BoB) | `data/tensors/bay_of_bengal/{X,Y,mask}.zarr` | `scripts/build_training_dataset.py` |
| Model checkpoint (epoch 83) | `data/checkpoints/hybrid_v1/best.pt` | `colab/oceanembed_training.ipynb` |
| Pre-built demo cache (31 dates) | `artifacts/demo_cache/` | `ml/scripts/build_demo_cache.py` |

Without ML assets, the backend serves pre-built demo cache data, honestly labelled as `fallback_demo`.

## Testing

```bash
# Full suite
make test           # pytest across backend + ml + data-engineering
make lint           # ruff check + ruff format --check
make test-all       # lint + tests + contract verification

# Backend only
cd backend && ../.venv/bin/python -m pytest tests/unit tests/api

# Frontend
cd frontend
npm test            # vitest (jsdom)
npm run build       # tsc + vite build
```

> **Check status (verified 2026-09-13).** `make test` is green (**443 passed**) and the frontend
> suite/build are green. Two repo-level checks are currently red for **pre-existing** reasons
> unrelated to the demo path:
>
> - `make lint` — ruff debt spread across older files (e.g. `scripts/verify_data_contract.py`,
>   `data-engineering/src/oceanembed_data/*`); the files changed for this demo are clean.
> - `make test-all` — the contract step flags every `verified: true` entry in
>   `config/datasets.yaml` as lacking `describe()` evidence (RULE 7). It stays red until that
>   evidence is recorded, by design (it must not silently trust an unverified dataset ID).

## Key Constraints

- Copernicus credentials stay **backend-only** — never in frontend code or Git
- Dataset IDs are **verified** via `copernicusmarine.describe()` — never guessed
- Train/test split is **temporal** — no random splitting of ocean time series
- Normalization statistics come from **training data only**
- No fabrication of data, dataset IDs, validation scores, or ARGO comparisons
- Subsurface variables never feed inference inputs (RULE 8)

## Non-Goals (MVP)

OceanEmbed is a *complementary* learned reconstruction pathway, not a replacement for numerical ocean modelling. This MVP does not include:

- Hardware or cyclone/tsunami forecasting
- GODAS replacement or operational forecasting claims
- Real-time or near-real-time data serving
- LLM chatbot features

## Troubleshooting

| Symptom | Cause / fix |
|:--------|:------------|
| UI loads but shows "Could not reach the OceanEmbed backend" | API base wrong or backend down. Set `VITE_API_BASE_URL=/api/v1`, rebuild the frontend, check `/api/v1/health`. |
| Map renders as a solid rectangle over the whole domain | Ocean-mask regression — see `build_ocean_mask` in `scripts/build_training_dataset.py` and `backend/tests/api/test_map.py::TestMapFieldFollowsCoastline`. |
| Map/profile return `fallback_demo` | The ML service is down or `OCEANEMBED_MODEL_SERVICE_URL` is unset; the pre-built cache is served (labelled honestly). |
| `503 MODEL_NOT_LOADED` for a non-cached date | Live service down **and** the date isn't in the demo cache. Start the ML service or pick a cached date. |
| `404 DATA_NOT_AVAILABLE` for a region | Only `bay_of_bengal` has a tensor store; other regions are declared but unserved. |
| `404` on an `/api/...` path | Unknown route returns the contract error envelope (`UNKNOWN_ERROR`), never the SPA shell. |

## Governance

| Document | Purpose |
|:---------|:--------|
| `AGENTS.md` | AI agent operating rules and architecture boundaries |
| `CONTRIBUTING.md` | Contribution standards, commit conventions, PR requirements |
| `SECURITY.md` | Security and credential governance |
| `SYSTEM_MEMORY_DUMP.md` | Historical project decisions and constraints |
| `OPENCODE_SDL_CONTRACT.md` | SDLC compliance and code generation contract |

## License

MIT

---

<div align="center">

**OceanEmbed** — Reconstructing the ocean beneath the surface.

</div>

