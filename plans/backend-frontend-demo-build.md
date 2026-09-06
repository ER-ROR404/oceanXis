# Plan: Production-Grade Backend + Frontend + Demo Build (Phase 2)

**Status:** REVIEWED — v0.2 (adversarial gate passed)
**Created:** 2026-09-06
**Plan file:** `plans/backend-frontend-demo-build.md`
**Target:** Local demo (Option A): `docker compose up` on the laptop, judges view
dashboard at `http://localhost:5173`.
**Review history:** v0.1 → v0.2 fixed (1) `data/proof/` is gitignored
(`.gitignore:100`) so ARGO summary moves to `frontend/src/assets/validation/`;
(2) parallelism corrected (Phase 3 depends on Phase 2); (3) demo cache output
pinned to gitignored `artifacts/demo_cache/`.

---

## 0. Context (read before anything else)

**Repository truth hierarchy:** `AGENTS.md` → `OPENCODE_SDL_CONTRACT.md` →
`SYSTEM_MEMORY_DUMP.md` → `docs/` → `contracts/` → implementation.

**LOCKED scientific facts (must not be violated by software):**
- Inputs: 7 surface channels (SST, SSS, SSH/SLA, cur U, cur V, wind U, wind V).
- Outputs: temperature at 15 canonical depths (0, 5, 10, 20, 30, 50, 75, 100,
  125, 150, 200, 300, 500, 700, 1000 m) — `config/depths.yaml` is the
  source of truth, do not reorder (RULE 20).
- Grid 0.25°, daily, North Indian Ocean; application regions `bay_of_bengal`,
  `arabian_sea`, `north_indian_ocean` — `config/regions.yaml`.
- Training set 2018-2023, validation 2024, test 2025; temporal-locked split
  (RULE 10); normalization statistics from training only (RULE 11).
- ARGO is independent validation only (RULE 9). GLORYS subsurface variables
  must never become inference inputs (RULE 8).
- The model already exists and is validated: `hybrid_v1` best val NLL 0.3715
  (epoch 59/100, early-stopped 74). ARGO validation: **285/285 matched, 6
  unmatched (all land), overall RMSE 1.3533, bias +0.6121, corr 0.99,
  n=3958**. Weakness: thermocline 75-150 m (RMSE 1.2-2.8, warm bias).
  Full report: Drive only (`MyDrive/oceanembed/artifacts/argo_report.json`).

**Standing rules (SELECTED, non-exhaustive — read AGENTS.md fully):**
- RULE 1/2: frontend never touches Copernicus credentials or Copernicus directly.
- RULE 3: backend never contains training code; inference runtime allowed.
- RULE 6: API responses conform to `contracts/api/*.schema.json`.
- RULE 7: dataset IDs verified, never guessed.
- RULE 12/13/14: no large datasets, checkpoints, or secrets in Git.
- RULE 14: secrets only via env vars / secret manager.
- RULE 15: applied migrations never edited.
- RULE 16: no new dependency when an existing one solves the problem.
- Tests first (TDD), 80% line coverage backend/ML, ruff clean.

---

## 1. Goal & Non-Goals

### Goal
A locally-runnable, production-grade demo: React dashboard → FastAPI backend
(`/api/v1` per `contracts/api/openapi.yaml`) → ml-inference service (torch,
serving the trained `hybrid_v1` checkpoint over local Zarr tensors) → postgres.
All responses contract-validated. Judges can pan a map of predicted subsurface
temperature, click a cell for a 15-depth profile (with uncertainty band from
`log_var`), and see the ARGO validation panel.

### Non-goals (explicitly OUT of scope for this pass)
- Live Copernicus ingestion in the demo path (no credentials needed at runtime;
  tensors already local). Copernicus client stays in backend deps for future.
- Re-training, bias calibration (deferred; documented in work-log).
- Live realtime capability claims (contract `trained_on` used instead).
- arabian_sea live model serving (no local tensors + no checkpoint coverage —
  see §5.8 for honest 404 handling).

---

## 2. Design Decisions (verified against repo)

| # | Decision | Evidence | Status |
|---|----------|----------|--------|
| D1 | 4-service docker compose: backend :8000, ml-inference :8080, frontend :5173, database | `docker-compose.yml` skeleton already declares this | LOCKED (follow skeleton) |
| D2 | Backend excludes torch (RULE 3 isolation). Inference lives in `ml/src/oceanembed/serving` package | `backend/pyproject.toml` deps list has no torch; comment says "inference runtime" is backend-adjacent but env isolation says ML env holds torch | LOCKED — ml-inference service hosts inference; backend calls it over HTTP |
| D3 | Inference reuses `OceanEmbedDataset.build_window(t)` + `get_day_of_year()` instead of re-implementing windowing/normalization | `ml/src/oceanembed/data/dataset.py` lines 119-163; already used by ARGO validation | LOCKED (RULE 16) |
| D4 | Checkpoint load: `ckpt.get("best_model_state") or ckpt.get("model_state_dict")`, `map_location="cpu"` | `ml/scripts/evaluate_argo.py` lines 122-124 (proven in validation run) | LOCKED |
| D5 | Model construction from `ml/configs/hybrid_v1.yaml`; NO hardcoded dims | `evaluate_argo.py` lines 112-120 pattern | LOCKED |
| D6 | CPU inference is acceptable: single 7-day window over BoB grid is small; ARGO validation (285 profiles) already ran on Colab CPU | validation run | CONFIRMED |
| D7 | Demo covers bay_of_bengal only (local tensors exist). arabian_sea → `DATA_NOT_AVAILABLE` (404 envelope) until tensors+checkpoint coverage exist | `data/tensors/` local: `bay_of_bengal/` exists; no `arabian_sea/` | CONFIRMED — honest 404, never fabricated |
| D8 | Map/profile endpoints wrap payloads in `PredictionEnvelope` (`status`, `payload`, `metadata`) per `contracts/api/prediction.schema.json` — declared as "Prediction payload envelope for map/profile endpoints" | `contracts/api/prediction.schema.json` lines 2-5 | LOCKED — follow prediction.schema.json |
| D9 | Channel availability reported per-input via `metadata.channel_status`; missing channels NEVER zero-filled silently — they must be reported | `prediction.schema.json` lines 26-31; error codes `CHANNEL_UNAVAILABLE` | LOCKED |
| D10 | ARGO panel reads committed metrics JSON (frontend asset) — NOT a new backend endpoint | `experiments/reports/*` is gitignored and `data/proof/` is gitignored (`.gitignore:100`); `frontend/src/assets/validation/` is tracked | LOCKED — summary JSON lives in frontend assets |
| D11 | No new backend endpoint for ARGO; frontend imports the JSON directly | avoids contract drift, keeps API surface = openapi.yaml exactly | PROPOSED |
| D12 | Rate limiting: implement lightweight in-process limiter (cachetools-based) on map/profile — NO new dependency (RULE 16) | backend already depends on `cachetools>=5.3` | PROPOSED |

**Contract change (escaped the earlier matrix):**
- **C1:** `contracts/api/openapi.yaml` 200-responses for `/ocean/map` and
  `/ocean/profile` currently `$ref` `ocean-map.schema.json` /
  `ocean-profile.schema.json` directly, while `prediction.schema.json`
  mandates the envelope for "map/profile endpoints". **RESOLUTION:** update
  openapi.yaml 200 responses to `$ref: prediction.schema.json` (which embeds
  map/profile payloads via oneOf). This is a contract change —
  **human review required per CONTRIBUTING.md**. The alternative (breaking
  prediction.schema.json) contradicts the newer, more specific schema.

---

## 3. Architecture

```
Browser (React+Vite, :5173)
  │  GET /api/v1/*            (CORS: localhost:5173)
  ▼
backend (FastAPI, :8000)        app/  (no torch — RULE 3)
  ├─ /health                    → health.schema.json
  ├─ /ocean/history             → {region, dates[]}
  ├─ /ocean/map                 → PredictionEnvelope{ocean-map payload}
  ├─ /ocean/profile             → PredictionEnvelope{ocean-profile payload}
  ├─ /ocean/metadata            → honest metadata (trained_on, no realtime claim)
  ├─ /model/version             → contract shape
  ├─ app/services/inference_client.py   httpx → ml-inference :8080
  └─ app/services/demo_cache.py         fallback_demo when model unreachable
        │ HTTP POST /predict {region,date}
        ▼
ml-inference (FastAPI+torch, :8080)   ml/src/oceanembed/serving/
  ├─ InferenceService: OceanEmbedDataset.build_window + OceanEmbedNet(best.pt)
  └─ returns mu [1,15,H,W] + log_var [1,15,H,W]  (raw °C, land=NaN via mask)
        │
        ▼
local tensors: data/tensors/bay_of_bengal/{X,Y,mask}.zarr + normalization_stats.json
        │ (read-only; gitignored *.zarr)
        ▼
database (postgres:16-alpine)  — app_metadata table (model_version,
                                 trained_on) seeded by alembic migration
```

**Data flow for one map request:**
1. `GET /api/v1/ocean/map?region=bay_of_bengal&date=2023-06-15&depth=100`
2. Backend validates (region enum, date format, depth ∈ 15 canonical, via
   `config/regions.yaml` + `config/depths.yaml` — NOT hardcoded).
3. Check in-memory TTL cache (cachetools) → hit: `status: cached_data`.
4. Miss: call ml-inference `/predict` (payload includes date → service builds
   window ending at that date, runs model, masks land cells with NaN).
5. Backend slices depth plane, wraps in PredictionEnvelope
   `status: model_prediction`, `metadata.channel_status: available` × 7.
6. ml-inference down → `status: fallback_demo` from pre-built demo cache
   (built ahead by `ml/scripts/build_demo_cache.py`) or `unavailable` +
   `503` envelope if neither works. Response shape NEVER changes.

**Contract conformance:** every handler stamps its response with
`metadata.model_version` + `generated_at`; tests validate responses against
`contracts/api/*.schema.json` via `jsonschema`.

---

## 4. Ground-Truth API Surface (from contracts/api/openapi.yaml — verified)

| Endpoint | Params | Success | Errors |
|---|---|---|---|
| `GET /health` | — | `health.schema.json` | — |
| `GET /ocean/history` | `region` (enum 3) | `{region, dates: [date]}` | 400 |
| `GET /ocean/map` | `region`, `date` (YYYY-MM-DD), `depth` (enum 15, default 0) | envelope→ocean-map | 400/404/503 |
| `GET /ocean/profile` | `region`, `date`, `latitude` (0..32), `longitude` (43..107) | envelope→ocean-profile | 400/404/503 |
| `GET /ocean/metadata` | — | app_name, app_version, regions[], model_version, data_freshness | 503 |
| `GET /model/version` | — | model_version, trained_on, data_version | — |

Error envelope: `error.schema.json` — codes `INVALID_REGION, INVALID_DATE,
INVALID_DEPTH, INVALID_COORDINATE, DATA_NOT_AVAILABLE, CHANNEL_UNAVAILABLE,
MODEL_NOT_LOADED, INFERENCE_FAILED, UNKNOWN_ERROR`.

**Ocean-map payload:** `{region, date, coordinates:{lat[],lon[]}, channel:"temperature",
values: number[][], metadata:{model_version, data_source, preprocessing_version, cached, timestamp}}`.
Land cells = NaN (mask from `mask.zarr`).

**Ocean-profile payload:** `{region, date, lat, lon, depths[15], temperatures[15]
(number|null — null when unavailable, NEVER fabricated), metadata}`.

---

## 5. Implementation Steps

> Execution order: Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6.
> **Parallelism:** after Phase 1, Phase 2 (ml serving) and Phase 4 (ARGO
> assets, data-only) and Phase 5 scaffolding (frontend, needs contracts only)
> can run in parallel — no file overlap. Phase 3 depends on Phase 2
> (InferenceClient). Phase 6 last.
> Each phase ends green: tests + ruff + (where applicable) build.
> TDD: write failing test, implement, refactor. 80% coverage.

---

### PHASE 1 — Backend core: config, health, envelope, metadata, db migration (app/)

> **STATUS: COMPLETE (2026-09-06)** — 44 tests pass, 97% coverage (target 80%),
> ruff clean across `app/ tests/ scripts/ migrations/`, all 4 Phase 1 routes
> mounted under `/api/v1` and contract-validated, alembic migration
> `001793ad4c22` verified upgrade→downgrade→seed on sqlite and postgres.
> Notes: alembic script dir named `migrations/` (a local `alembic/` dir shadowed
> the installed package); `InferenceClient.available_dates` stub returns `[]`
> (honest "no coverage served yet") so `/ocean/history` is 200-with-empty-list
> in Phase 1 (Phase 2 fills dates from the model service); `app_metadata` is
> seeded by `backend/scripts/seed_metadata.py` from `Settings` (idempotent UPSERT).

**Step 1.1 — Backend skeleton & settings** (File: `backend/app/core/config.py`,
`backend/app/main.py`)
- Action: `Settings(BaseSettings)` — `model_service_url: str =
  "http://ml-inference:8080"`, `demo_cache_dir: Path` (default
  `../artifacts/demo_cache`), CORS origins list, `app_version`,
  model version; `create_app()` FastAPI factory mounting routers under
  `/api/v1`, CORS middleware, request-ID middleware (uuid), structlog-style
  logging config (stdlib logging, no new dep).
- Why: single settings object keeps every service/test on the same config path.
- Dependencies: none.
- Risk: Low.
- Tests: `backend/tests/unit/test_config.py` (env override, defaults),
  `tests/api/test_health.py` (see 1.3).
- Verify: `cd backend && .venv/bin/pytest tests/ -q` (venv per module; use
  root `.venv` gate per Makefile), `ruff check app tests`.

**Step 1.2 — Contract-validated schemas & error envelope**
(File: `backend/app/schemas/` — `common.py`, `map.py`, `profile.py`,
`history.py`, `metadata.py`, `error.py`)
- Action: Pydantic v2 models mirroring `contracts/api/*.schema.json` exactly;
  `ApiError` exception + handler translating to `error.schema.json` codes;
  custom exceptions `InvalidRegionError`, `InvalidDateError`,
  `InvalidDepthError`, `InvalidCoordinateError`, `DataNotAvailableError`,
  `ChannelUnavailableError`, `ModelNotLoadedError`, `InferenceFailedError`.
- Why: RULE 6 — responses conform to contracts; stable machine-readable codes.
- Dependencies: Step 1.1 (app factory for handler registration).
- Risk: Low. Care: `profile.temperatures` nullable — never nullable→0 coercion.
- Tests: `tests/unit/test_error_codes.py` (each code → correct HTTP + envelope),
  `tests/unit/test_schemas_conform.py` (serialize sample payloads, validate
  against contract JSON via `jsonschema` — add `jsonschema` to
  `backend/pyproject.toml` dev deps; RULE 16 check: not present today, needed
  for contract tests).
- Verify: ruff + pytest green.

**Step 1.3 — /health, /ocean/history, /ocean/metadata, /model/version**
(File: `backend/app/api/v1/routes/` — `health.py`, `history.py`,
`metadata.py`, `model_version.py`)
- Action: `/health` checks: `api`(ok), `model_loaded`(probe ml-inference
  `/health` via InferenceClient — degraded if unreachable, never down),
  `cache_accessible`(demo cache dir writable → ok/degraded), `database`
  (`SELECT 1` → ok/degraded). `/ocean/history` returns dates from the region's
  Zarr `time` coordinate (via InferenceClient `available_dates()`), ordered,
  ISO-8601. `/ocean/metadata` + `/model/version` return honest values from
  `app_metadata` DB row / config: `model_version: "hybrid_v1"`,
  `trained_on: "2023-12-31"` (train period end — NOT realtime), `data_version`
  from manifest.
- Why: liveness must never trigger expensive downloads (contract says so);
  history is contract-typed; metadata honesty is a judging criterion.
- Dependencies: 1.1, 1.2; `app/services/inference_client.py` (Step 2.2 —
  see inter-package note below).
- Risk: Medium — health must be truthful under partial failure. Handle
  httpx.ConnectError → degraded, not 500.
- Tests: `tests/api/test_health.py`, `tests/api/test_history.py`,
  `tests/api/test_metadata.py` (assert envelope + contract-validate via
  jsonschema).

**Step 1.4 — Database bootstrap (postgres)**
(File: `backend/app/database/` — `session.py`, `models.py`;
`backend/alembic/` — env.py, `versions/0001_create_app_metadata.py`)
- Action: SQLAlchemy 2.0 engine/session (sync for simplicity), `app_metadata`
  table (key/value: model_version, trained_on, data_version, argo_summary_uri);
  alembic init + first migration; seed script `backend/scripts/seed_metadata.py`
  (CLI: `alembic upgrade head && python -m backend.scripts.seed_metadata`).
- Why: RULE 7 (verified IDs), RULE 15 (never edit applied migrations), health
  needs a real DB check; migration proves production workflow.
- Dependencies: 1.1.
- Risk: Low-Medium — DB may be down during tests; make tests use
  dependency-injected session or in-memory sqlite, DB check tolerates failure.
- Tests: `tests/integration/test_database.py` (session roundtrip with sqlite),
  migration test (upgrade head on ephemeral postgres or skip-if-no-DB).
- Verify: `alembic upgrade head` locally with compose DB running.

> **Inter-package note:** Step 1.3 needs `InferenceClient` (backend service)
> which is written in Phase 2. Order: do 1.1→1.4 with a minimal
> `InferenceClient` stub (returns `ModelNotLoadedError`) so Phase 1 is
> green on its own; Phase 2 fills in the real HTTP client. Alternative:
> build 2.1/2.2 before 1.3. Dependency graph keeps 1.3 last in Phase 1.

**Phase 1 exit criteria:** all backend tests pass, ruff clean,
`curl localhost:8000/api/v1/health` returns contract-shaped JSON,
`alembic upgrade head` + seed works against compose DB, jsonschema validation
tests green for all implemented routes.

---

### PHASE 2 — ML inference service (ml/src/oceanembed/serving/ + backend HTTP client)

**Step 2.1 — InferenceService core** (File: `ml/src/oceanembed/serving/service.py`)
- Action:
  ```python
  class InferenceService:
      def __init__(self, region_dir, checkpoint_path, cfg)  # cfg=hybrid_v1 model block
      # dataset = OceanEmbedDataset(region_dir, temporal_window=T, normalize=True)
      # model = OceanEmbedNet(in_channels=7, out_channels=15,
      #                       convlstm_hidden=cfg..., convlstm_layers=cfg...)
      # ckpt = torch.load(checkpoint_path, map_location="cpu")
      # state = ckpt.get("best_model_state") or ckpt.get("model_state_dict")
      def available_dates() -> list[str]       # from dataset.X.time
      def predict(date: str) -> tuple[mu, log_var, mask]
          # t = index of date in time coords
          # x = dataset.build_window(t)             [T,C,H,W] normalized (train stats)
          # with torch.no_grad(): mu, log_var = model(x.unsqueeze(0))   ← NO coords
          # mask from dataset.mask → NaN on land
      def predict_profile(date, lat, lon) -> temperatures[15]  # nearest cell; NaN → None
  ```
  **CRITICAL (verified 2026-09-06 against trainer + argo validator):** the trained
  model is called with `model(x)` and NO `day_of_year`/`lat`/`lon`. The coord
  encoder + input projection exist in the architecture (`use_seasonal: true`
  flags in config) but were **never trained** — `Trainer.train_one_epoch` calls
  `self.model(x_batch)` (trainer.py:109, 138) and `ArgoValidator._predict_cell`
  calls `self.model(x_win)` (argo.py:232). Passing coords into the untrained
  `input_proj` corrupts predictions. Inference MUST mirror these call sites
  exactly. (A forward pass with coords fails even to run: lat is expected as
  [H,W]/[B,H,W] 2-D grid, not 1-D.)
- Why: windowing/normalization/temporal math already tested (126 tests green) —
  reusing it is RULE 16 + zero-hallucination (no re-derivation of indexing).
- Dependencies: none (ml package). Uses existing `models/reconstruction_net.py`
  (verified signatures: forward(x) → (mu, log_var), B×15×H×W).
- Risk: Low-Medium. Edge cases: date outside tensor range → raise
  `DataNotAvailableError`; nearest-cell land → None profile temperatures.
- Tests: `ml/tests/unit/serving/test_service.py` — tiny region fixture +
  synthetic checkpoint: predict returns (mu, log_var) shapes, masked land =
  NaN, profile lands → Nones, out-of-range date raises. **Regression guard:
  assert forward is called WITHOUT coords** (mock model, assert call kwargs
  empty) so the trained path can't silently drift.
- Verify: `.venv/bin/pytest ml/tests/unit/serving/ -q` (NOTE: torch import must
  not leak into backend tests — ml env owns inference).

**Step 2.2 — Inference HTTP server + backend client**
(File: `ml/src/oceanembed/serving/server.py`; `backend/app/services/inference_client.py`)
- Action:
  - ml side: FastAPI on :8080 — `GET /health` (model loaded? → 200 ok /
    503 MODEL_NOT_LOADED), `POST /predict {region, date}` → 200
    `{mu: [[...]], log_var: [[...]], dates: [...], series_id}` or 404
    DATA_NOT_AVAILABLE / 503 MODEL_NOT_LOADED. Region→dir mapping from
    `config/regions.yaml` (data dir path from env `TENSOR_DIR`);
    `python -m oceanembed.serving.server` entrypoint.
  - backend side: `InferenceClient` (httpx ASGI/real) — `health()`,
    `predict_map(region,date)`, `available_dates(region)`, TTL cache
    (cachetools) — raises typed ApiErrors on non-200. Never trusts response
    without re-validating against contract shape.
- Why: HTTP boundary enforces RULE 3 (backend never imports torch);
  serializing as raw floats keeps ml-inference brain-dead simple and testable.
- Dependencies: 2.1; backend deps: httpx (already dev dep; promote to main
  deps in pyproject).
- Risk: Medium — wire format is a new interface; pin exact JSON field names
  and version the contract in `contracts/ml/inference-rpc.schema.json`
  (create it; mirrors checkpoints + prediction shapes).
- Tests: ml `tests/unit/serving/test_server.py` (TestClient, fake service);
  backend `tests/unit/test_inference_client.py` (mock transport: success,
  connect error → ModelNotLoaded, malformed → InferenceFailed, cached hit
  returns without second call).
- Verify: both packages' tests green.

**Step 2.3 — Local demo cache builder** (File: `ml/scripts/build_demo_cache.py`)
- Action: CLI `python ml/scripts/build_demo_cache.py --region bay_of_bengal
  --checkpoint data/checkpoints/hybrid_v1/best.pt --start 2023-06-01 --end
  2023-12-31 --step 7d --out artifacts/demo_cache/` → for each date, run
  `InferenceService.predict`, save per-depth map arrays (npz or zarr, NaN land)
  + `manifest.json` (model_version, trained_on, date range, channel_status
  from normalization_stats.json presence, masked_land_count). Output goes to
  `artifacts/demo_cache/` — safe: `artifacts/` is gitignored (`.gitignore:39`)
  and `*.zarr` is ignored (line 23); no new ignore rule needed.
- Why: `fallback_demo` contract status needs an offline data path for the
  demo when the model service isn't running; also serves as CI/verification
  artifact proving model loads and produces sane outputs on the laptop.
- Dependencies: 2.1 (imports service).
- Risk: Low — pure batch script; run time trivial for ~30 dates on CPU.
- Tests: `ml/tests/unit/serving/test_demo_cache.py` (build → reload → shapes,
  masked counts stable, manifest fields present).
- Verify: run the builder once, inspect a map for sane range (~15-30 °C).

**Phase 2 exit criteria:** ml serving unit tests pass, backend client tests
pass, demo cache builds successfully, `POST /predict` returns contract-shaped
payload for a real date (manual curl), no torch import anywhere under
`backend/`.

---

### PHASE 3 — Map/profile routes + envelope + caching + rate limit (backend)

**Step 3.1 — /ocean/map handler** (File: `backend/app/api/v1/routes/map.py`)
- Action: validate region/date/depth (enums from config, NOT hardcoded);
  InferenceClient.predict_map → slice `depth` plane → build
  `ocean-map` payload (`coordinates` from X.latitude/longitude values) →
  wrap in PredictionEnvelope; set `status` = `model_prediction` (live),
  `cached_data` (TTL cache hit), `fallback_demo` (from demo cache dir when
  model down), `unavailable` (503) when neither; `channel_status` = available
  for all 7 or missing (never silently zero-filled — D9).
- Why: contract surface; honest status taxonomy is the whole point of
  prediction.schema.json.
- Dependencies: 1.2 (schemas), 2.2 (client).
- Risk: Medium — envelope correctness (status semantics + metadata fields)
  is the judge-visible surface.
- Tests: `tests/api/test_map.py` — valid map (live mock), cache hit path,
  fallback_demo path (mock client down + demo cache fixture), 404 date,
  400 depth, 503 both-down; every response validated against
  `prediction.schema.json` + `ocean-map.schema.json` via jsonschema.
- Verify: ruff + pytest.

**Step 3.2 — /ocean/profile handler** (File: `backend/app/api/v1/routes/profile.py`)
- Action: validate region/date/lat(0..32)/lon(43..107) per openapi bounds;
  client.predict_profile → 15 depths plumbed from `config/depths.yaml`;
  None for land/missing (never 0.0 — RULE: never fabricate); wrap in
  envelope; same status taxonomy + TTL cache.
- Why: contract `ocean-profile.schema.json` (temperatures nullable).
- Dependencies: 1.2, 2.2, 3.1 (shared envelope helper).
- Risk: Medium — nearest-cell semantics must be documented in response
  metadata or endpoint doc; null vs 0 is a testable invariant.
- Tests: `tests/api/test_profile.py` — land cell → None entries (assert no 0.0
  in output), valid cell, error codes, envelope conformance, jsonschema
  validation against both schemas.
- Verify: pytest green.

**Step 3.3 — Rate limiting + hardening** (File: `backend/app/core/ratelimit.py`)
- Action: lightweight per-IP token bucket on map/profile using cachetools
  (e.g., 30 req/min); 429 → error envelope code `RATE_LIMITED` — NOTE: error
  schema has no RATE_LIMITED code today → either add code to
  error.schema.json via the C1 contract update (same PR), or use
  `UNKNOWN_ERROR` (bad). **Decision: extend error.schema.json enum with
  `RATE_LIMITED` as part of C1.** Structured request logging; security headers
  middleware (X-Content-Type-Options etc.).
- Why: production-grade API hygiene; judges probe for exactly this.
- Dependencies: 1.2, C1 contract update.
- Risk: Low.
- Tests: `tests/api/test_ratelimit.py` (burst → 429 envelope), headers present.

**Phase 3 exit criteria:** map/profile endpoints fully contract-conformant
(both live + fallback paths), rate limited, all tests green, manual curl
against running stack returns valid envelopes.

---

### PHASE 4 — ARGO validation assets + metadata seeding for the panel

**Step 4.1 — ARGO summary JSON** (File: `frontend/src/assets/validation/argo_validation_summary.json`;
schema at `contracts/validation/argo-summary.schema.json`)
- Action: hand-write (from committed work-log
  `docs/work-log/2026-09-06-argo-validation.md` — the numbers are already
  repo-official): overall + per-depth rmse/bias/correlation, matched/unmatched
  counts, unmatched reasons (6× land), validation window, a `limitations`
  string (thermocline warm bias, depth-0 sparse n=25). Keep Drive-only full
  records untouched. **Location is deliberate:** `data/proof/` is gitignored
  (`.gitignore:100`) so the summary lives under `frontend/src/assets/validation/`
  (tracked, co-versioned with the panel that consumes it). Add a small JSON
  Schema at `contracts/validation/argo-summary.schema.json` for the panel.
- Why: RULE 9 honesty surfacing; full profile records stay Drive-only (RULE 12).
- Dependencies: none (data only).
- Risk: Low. Ensure numbers EXACTLY match the work-log (no new calculation —
  copying verified values is not inventing data; recalculating would violate
  the "no invented scores" rule if done sloppily). **Regression lock:** a
  test asserts the JSON equals the committed work-log values, so re-edits
  can't silently drift.
- Tests: `data-engineering/tests/test_argo_summary_schema.py` or a small
  pytest validating the JSON against its schema + exact-value regression
  against work-log.
- Verify: `python -m json.tool` + schema check.

**Step 4.2 — Seed app_metadata + demo cache wiring** (File:
`backend/scripts/seed_metadata.py`; `backend/app/services/demo_cache.py`)
- Action: seed `app_metadata` row (model_version=hybrid_v1, trained_on=2023-12-31,
  data_version from checkpoint manifest fields already known); demo cache
  reader maps (region,date) → prebuilt arrays with `status=fallback_demo` and
  honest `metadata.channel_status`.
- Dependencies: 1.4, 2.3.
- Risk: Low.
- Tests: reading seeded row; cache reader falls back cleanly to unavailable.

**Phase 4 exit criteria:** `frontend/src/assets/validation/argo_validation_summary.json`
committed + schema-validated + exact-value regression vs work-log; seeding an
idempotent second time; demo cache works as fallback_demo via API (curl with
ml-inference stopped).

---

### PHASE 5 — Frontend dashboard (frontend/, React+TS+Vite)

**Step 5.0 — Scaffold** (File: `frontend/package.json`, `vite.config.ts`,
`tsconfig.json`, `src/main.tsx`, `src/App.tsx`)
- Action: Vite react-ts template (npm create vite), deps kept minimal:
  react, react-dom, leaflet, recharts (chart), no UI framework bloat.
  Dev proxy `/api` → `http://localhost:8000`.
- Why: greenfield (frontend is skeleton-only today — verified: no
  package.json); keep dep surface small (RULE 16 analog for frontend).
- Dependencies: none.
- Risk: Low.
- Verify: `npm run dev` serves, `npm run build` passes, `tsc --noEmit` clean.

**Step 5.1 — API client + types** (File: `frontend/src/api/client.ts`,
`frontend/src/types/contracts.ts`)
- Action: hand-written TS types mirroring the contract schemas; typed
  `fetch` helpers `getHealth`, `getHistory`, `getMap`, `getProfile`,
  `getMetadata`, `getModelVersion`; centralized error decode from
  `error.schema.json` envelope; `PredictionEnvelope` discrimination on
  `status` (model_prediction / cached_data / fallback_demo / unavailable →
  distinct UI banners).
- Why: single typed gateway; envelope status → honest UI states.
- Dependencies: 5.0, contract C1 (envelope).
- Risk: Low.
- Tests: `src/api/client.test.ts` with mocked fetch (vitest) — statuses →
  typed results, error envelope → typed ApiError.

**Step 5.2 — Map panel** (File: `frontend/src/components/map/OceanMap.tsx`,
`frontend/src/components/map/ColorScale.tsx`, `frontend/src/hooks/useOceanMap.ts`)
- Action: Leaflet map over BoB bounds; raster layer from `values[][]` with
  NaN→transparent; viridis-style continuous color scale (hand-rolled, no new
  dep); click cell → lat/lon → profile fetch; depth selector (15 depths);
  date slider bound to `/ocean/history` dates; region dropdown (bay_of_bengal,
  arabian_sea → expected honest 404 banner: "no data in demo scope").
- Why: the map is the demo's centerpiece; honest empty states on arabian_sea.
- Dependencies: 5.1.
- Risk: Medium (Leaflet + canvas overlay perf on 69×81 grid is trivial —
  verified grid size; color scale aesthetics).
- Tests: component tests with fixture payloads (render, NaN pixels skipped,
  status banner variants, 404 arabian_sea state).

**Step 5.3 — Profile panel** (File: `frontend/src/components/profile/ProfileChart.tsx`,
`frontend/src/hooks/useOceanProfile.ts`)
- Action: Recharts depth-vs-temperature scatter/line, y-axis reversed
  (0 m top), uncertainty band from `log_var` (95% band = ±1.96·sqrt(exp)).
  Null temperatures → gap, never 0-line. Header shows cell + date + status.
- Why: contract's uncertainty output → judge-visible value; null handling is
  a correctness invariant.
- Dependencies: 5.1.
- Risk: Low.
- Tests: fixture profile w/ nulls renders gaps; band renders; tooltip labels.

**Step 5.4 — ARGO validation panel** (File: `frontend/src/components/validation/
ArgoPanel.tsx`; imports `frontend/src/assets/validation/argo_validation_summary.json`
from Step 4.1)
- Action: table of per-depth metrics (rmse/bias/corr) + overall card +
  limitations callout (thermocline warm bias, n=25 at 0 m).
- Why: RULE 9 surfacing; judges see honest evaluation, not just pretty maps.
- Dependencies: 4.1 (JSON), 5.0.
- Risk: Low.
- Tests: renders table rows from fixture; limitations text present.

**Step 5.5 — Layout, header, status banner, routing** (File:
`frontend/src/components/layout/*`, `frontend/src/App.tsx` routes)
- Action: app header (app name, model version from /model/version, health dot
  from /health), global status banner (live/cached/fallback/unavailable +
  channel_status tooltip), simple react-router (2 routes: Map / Validation),
  footer with honest "not realtime, trained_on 2023-12-31" line.
- Why: production feel + honesty framing.
- Dependencies: 5.2-5.4.
- Risk: Low.
- Tests: smoke render + link nav.

**Phase 5 exit criteria:** `npm run build` + `tsc --noEmit` + vitest green;
manual walkthrough: map renders BoB temp at depth 100 for 2023-07-01,
click → 15-depth profile, ARGO panel numeric, arabian_sea shows honest
"no data" state, status banner shows `model_prediction`.

---

### PHASE 6 — Docker wiring, E2E, docs, merge

**Step 6.1 — Dockerfiles** (Files: `infrastructure/docker/backend.Dockerfile`,
`ml-inference.Dockerfile`, `frontend.Dockerfile` — dir currently has only
`.gitkeep`)
- Action:
  - ml-inference: python:3.11-slim + `ml/pyproject.toml` install + torch CPU
    wheel pin (crowd-sourced CPU index — verify exact wheel per docs, pin
    version), non-root user, `CMD python -m oceanembed.serving.server`,
    env `TENSOR_DIR=/data` `MODEL_PATH=/models`, read-only mounts.
  - backend: python:3.11-slim + `backend/pyproject.toml`, non-root, uvicorn.
  - frontend: node:22-alpine build → nginx:alpine serving `dist`, reverse
    proxy `/api` → backend:8000 (so browser hits same-origin — CORS stays
    strict).
- Why: compose skeleton references exactly these three files today (verified);
  non-root + read-only = production hygiene.
- Dependencies: all prior phases.
- Risk: Medium (wheel pinning/hash; verify torch CPU wheel URL before
  writing — do NOT guess).
- Verify: `docker compose build` succeeds.

**Step 6.2 — compose wiring** (File: `docker-compose.yml` — extend skeleton)
- Action: wire env vars (MODEL_PATH=/models, TENSOR_DIR=/data,
  DATABASE_URL=postgres://oceanembed:oceanembed@database/oceanembed),
  named volumes `model-registry:/models:ro`, `tensor-data:/data:ro`,
  demo-cache volume, healthchecks (backend: curl /api/v1/health; frontend: nginx;
  database already declared), depends_on chains, restart: unless-stopped.
- Why: judges run ONE command (`docker compose up --build`).
- Dependencies: 6.1.
- Risk: Low-Medium (volume paths must match Dockerfile EXPOSE/env).
- Verify: `docker compose up -d --build && docker compose ps` all healthy.

**Step 6.3 — E2E smoke + docs** (Files: `docs/work-log/2026-09-07-demo-build.md`,
`docs/runbooks/demo-quickstart.md` — create runbooks dir if absent;
update `README.md` top section with the one-command demo)
- Action: scripted smoke: `GET /api/v1/health`=ok → `GET /ocean/map` for
  2023-07-01 depth 100 returns `model_prediction` envelope + non-NaN land-masked
  values → `GET /ocean/profile` at a BoB cell → 15 temps → frontend `/`
  loads (grep page title), ARGO panel numbers present; screenshot.
  Quickstart: place `best.pt` at `data/checkpoints/hybrid_v1/best.pt`,
  build demo cache, `docker compose up`.
- Why: definition of done = reproducible one-command demo + docs updated
  (CONTRIBUTING.md), work-log capture (knowledge capture rule).
- Dependencies: 6.2.
- Risk: Low.
- Verify: script passes end-to-end; screenshots saved to
  `experiments/reports/demo/` (gitignored, Drive export later).

**Step 6.4 — Contract update C1 + review + merge**
- Action: add `RATE_LIMITED` to `error.schema.json`; update openapi.yaml
  map/profile 200 refs → `prediction.schema.json`; create
  `contracts/ml/inference-rpc.schema.json`; run repo-wide gates (Makefile
  targets, ruff, pytest backend+ml+data-engineering), security-reviewer pass
  (auth/CORS/headers/rate-limit/error hygiene), code-reviewer pass,
  require human review of contracts per CONTRIBUTING.md; conventional commit
  series on `feat/backend-frontend-demo`.
- Why: contracts are the contract; human review is mandatory for `contracts/`.
- Dependencies: all.
- Risk: Medium — contract drift must be caught before merge (guard: CI test
  asserting `contracts/api` schemas are what handlers validate against).
- Verify: CI green on the branch; `git log --oneline` shows small atomic
  commits.

**Phase 6 exit criteria:** `docker compose up --build` → healthy stack,
smoke script passes, docs updated, contracts updated + human-reviewed,
all test suites green (backend, ml, data-engineering, frontend), security +
code review comments resolved, merged to `main`.

---

## 6. Testing Strategy (aggregate)

- **Backend (app/):** pytest + httpx ASGI transport. Unit: config, error
  codes, schemas-conform-to-contracts (jsonschema). API: health/history/
  map/profile/metadata/model-version envelopes + status taxonomies + 429.
  Integration: DB session roundtrip (sqlite), migration upgrade, demo-cache
  fallback path. Target coverage ≥ 80% (`pytest --cov=app`).
- **ML serving:** `ml/tests/unit/serving/*` — service (shape/mask/None/raises),
  server (status codes, malformed req), demo cache builder. ML suite stays
  python-heavy; torch CPU only, no GPU path required (D6).
- **Frontend:** vitest + @testing-library/react — client (mocked fetch),
  components (fixtures incl. null-temp profile, land NaN map, arabian_sea 404,
  4 status banners), smoke nav. Gate: `npm run build && tsc --noEmit &&
  vitest run`.
- **E2E:** Phase 6.3 script (curl API + frontend load + screenshot), run
  against compose stack.
- **Contract tests (shared):** every API test double-validates responses
  against `contracts/api/*.json` — this is the anti-drift guard.

---

## 7. Risks & Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| torch CPU wheel pinning guess | Medium | Verify wheel URL/hash from official PyTorch docs before writing Dockerfile (0-guess rule); fall back to `pip install torch --index-url https://download.pytorch.org/whl/cpu` with pinned version |
| Contract drift (openapi vs prediction.schema.json) | High (known) | C1 update in one PR; jsonschema-validated responses in CI protect forever after |
| arabian_sea has no local tensors → judge clicks it | Certain | Honest `DATA_NOT_AVAILABLE` envelope + frontend "expected — demo scope bay_of_bengal" banner (D7) |
| best.pt missing on laptop until user downloads | High | Phase 2 blocked on it → user action list at top; tests use synthetic checkpoint so code still TDD-verifiable |
| Demo cache perf if step=1d over 2018-2023 | Low | Default `--step 7d` + date window; cache is meant for fallback only, live path is primary |
| lat/lon bounds in openapi (0..32, 43..107) vs BoB grid edges | Medium | Validate via region bounds from `config/regions.yaml` + grid coords from X; return INVALID_COORDINATE outside data grid with clear message |
| Throwing away NaN→0 in normalization already proven | None | build_window already NaN→0s inputs (dataset.py `_normalize_x`) — output masking via mask.zarr is separate and correct |
| Test isolation (torch import in backend tests) | Medium | Keep serving imports strictly in ml package; backend client uses httpx only; CI runs per-module gates |

---

## 8. Anti-Pattern Checklist (audit before each PR)

- [ ] No training code in `backend/` (RULE 3) — grep `import torch` in backend → must be absent.
- [ ] No hardcoded region bounds / depths / channels — all from `config/*.yaml` + contract enums.
- [ ] No fabricated temperatures: null/NaN semantics ONLY via mask; never 0.0 filler.
- [ ] No secrets, zarr tensors, `*.pt` in Git (`.gitignore` lines 23, 27-29, 40 verified).
- [ ] Duration >4 levels nested logic → refactor; functions <50 lines.
- [ ] Immutable data handling: never mutate input arrays in services (copy before transform).
- [ ] Every new endpoint has a test asserting contract conformance.
- [ ] No new dependency without RULE 16 justification in the PR body.

---

## 9. Open Questions for User (before Phase 1 kickoff)

1. **Contract change C1** (envelope on map/profile + `RATE_LIMITED` error
   code): OK to update `contracts/api/*` in this branch (requires human
   review per CONTRIBUTING.md)? — proposed: yes, single PR.
2. **best.pt download:** please place `best.pt` at
   `data/checkpoints/hybrid_v1/best.pt` (gitignored) from Drive — Phase 2
   live-path verification depends on it (tests use synthetic checkpoints
   regardless).
3. **BoB-only demo scope** (arabian_sea 404s honestly): acceptable for the
   MVP demo, or should we download arabian_sea tensors + train a booster
   first (adds days)? — proposed: BoB-only now, arabian_sea later.
4. **Frontend dep budget:** leaflet + recharts OK (no UI framework), or do
   you want a shadcn/ui-style kit? — proposed: minimal.