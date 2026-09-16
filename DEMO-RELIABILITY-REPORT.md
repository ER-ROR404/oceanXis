# Demo Reliability Checkpoint — Phase 5.1

Date: 2026-09-08
Scope: P0 capability-hardening changeset on `feat/phase5-frontend-completion` (availability endpoint, region-guarded serving, availability-driven explorer UI, provenance labeling).

## 1. Changeset inspection (Task 1)

| Item | Result |
|---|---|
| Total files | 27 (21 modified + 6 untracked). Note: user brief said 28; actual count is 27. |
| Secrets / credentials | None found in diff. Only occurrence is a benign "no credentials" docstring in `backend/app/api/v1/routes/metadata.py`. |
| Large data / checkpoints / caches staged | None. `.gitignore` covers `.venv/`, `*.pt`, `artifacts/`, `checkpoints/`, `data/tensors/`. |
| Unrelated / accidental changes | None found. Every modified file belongs to the P0 scope (availability, region guard, provenance, docs). |
| `backend/uv.lock` | 540 KB, generated 2026-09-08 10:07 +0530 by `uv run`. The repo tracks **no** `uv.lock` anywhere (`git ls-files` finds none). It is a generated artifact, not an intentionally tracked file. |

## 2. Reliability scenarios (Task 2)

Stack under test: ml `:8080` (REGION=bay_of_bengal, checkpoint `data/checkpoints/hybrid_v1/best.pt`), backend `:8000` (uvicorn, `OCEANEMBED_MODEL_SERVICE_URL=http://localhost:8080`), Vite `:5173` proxy.

| Scenario | Request | Result |
|---|---|---|
| **A.** BoB 2022-01-15, depth 100 m | `GET /ocean/map?region=bay_of_bengal&date=2022-01-15&depth=100` | **PASS** — 200, `status=model_prediction`, grid 69×81, echoed date correct |
| **B.** BoB 2023-01-15, depth 100 m | same, `date=2023-01-15` | **PASS** — 200, `model_prediction`, 69×81 |
| **C.** BoB 2023-12-31 (last available date), depth 100 m | same, `date=2023-12-31` | **PASS** — 200, `model_prediction`, 69×81 |
| **D.** Arabian Sea — honest no-data | `GET /availability` → `region=arabian_sea`, `status=no_data`, 0 dates | **PASS** (availability report is honest) |
| | `GET /ocean/map?region=arabian_sea&date=2023-09-01&depth=100` | **FAIL (BLOCKER)** — returns HTTP 200 `model_prediction` with a payload: the **exact same values and coordinates as bay_of_bengal** (byte-for-byte identical), re-labeled `arabian_sea`. Prediction fabricated for an unserved region. |
| **E.** North Indian Ocean — honest no-data | `GET /availability` → `status=no_data`, 0 dates | **PASS** (availability report is honest) |
| | `GET /ocean/map?region=north_indian_ocean&date=2023-09-01&depth=100` | **FAIL (BLOCKER)** — identical fabrication as D. |
| **F.** Full user flow (region → date → depth → map → cell → 15-depth profile → uncertainty → ARGO) | map depth 0 / depth 100 + profile via Vite proxy | **PASS** — map `model_prediction` with 2-D sigma grid [69][81] per selected depth; profile returns 15 temperatures + 15 sigma with snapped lat/lon. Cell-click → profile → explainer → ARGO panel chain covered by automated e2e suite (94/94 vitest, `walk-map-cell-click-profile-explainer-argo` + ARGO panel RMSE assertion). |
| **G.** Vite proxy chain (not direct backend) | `http://localhost:5173/api/v1/ocean/map`, `/ocean/profile`, `/availability` | **PASS** — proxy forwards correctly; identical envelopes to direct backend for all verified calls. |

### D/E detail — the fabrication bug

- Root cause: `ml/src/oceanembed/serving/server.py:139` (`/predict`) and `:174` (`/predict_profile`) guard `req.region not in REGIONS`, where `REGIONS` is the **declared** region list. Any declared-but-unserved region (arabian_sea, north_indian_ocean) passes, and the service predicts with its loaded tensor store (bay_of_bengal), echoing `"region": req.region` in the response.
- Proof: `GET /ocean/map?region=arabian_sea&date=2023-09-01&depth=100` and `region=bay_of_bengal&date=2023-09-01&depth=100` return **identical `coordinates` and `values`** (verified by comparison script). Payload claims `region=arabian_sea`, coordinates 5–22°N / 80–100°E (the BoB store's grid).
- Why tests did not catch it: `ml/tests/unit/serving/test_server.py` only covers `region="atlantis"` (not in `REGIONS`) → 404. There is **no test for a declared-but-unserved region**, which is exactly the failing case.
- Why the demo UI is still safe: the explorer hook derives `dates=[]` for no-data regions and never dispatches a map/profile request (guarded by `if (!date) return` in both effects; verified in `useOceanExplorer.ts:153-157, 165, 189`). The empty-region state is shown instead. The fabrication is reachable **only via direct API calls** — meaningfully the checkpoint's D/E test path.

### Smallest safe fix (not applied yet, per checkpoint rules)

1. **Root cause, ml server (~2 lines):** in `/predict` and `/predict_profile`, replace the region guard with a compare against the actually served store:
   `if req.region != svc.region_dir.name: → 404 DATA_NOT_AVAILABLE` (plus a new ml test: `region="arabian_sea"` → 404, `code=DATA_NOT_AVAILABLE`).
2. **Optional defense-in-depth (backend):** `InferenceClient.predict_map` / `predict_profile` should validate the echoed response region equals the requested region (mirroring the existing `available_dates` region guard) and raise `InferenceFailedError` on mismatch → map route falls into its honest error path.

## 3. Failure behavior — ML service stopped (Task 3)

Procedure: `kill` the ml server; verified `GET /health` → 000 (down); exercised backend; restarted ml; re-verified.

| Check | Result |
|---|---|
| `GET /availability` with ml down | **PASS** — BoB degrades to `available` with the **31 demo-cache dates** (2023-06-01..2023-12-28, `checkpoint: best.pt`), NOT the stale 730. arabian_sea / north_indian_ocean stay `no_data`. No fabricated data. |
| Map for a cached date (2023-10-05, depth 0) via proxy | **PASS** — HTTP 200 `status=fallback_demo`, `cached=True`, `data_source="Pre-built demo cache (hybrid_v1 checkpoint)"` (honest labeling, UI shows "not the live model" banner copy). |
| Map for a date in range but not cached (2023-10-01 — not offered by the UI) | **PASS** — HTTP 503 `MODEL_NOT_LOADED` envelope, `fallback="demo cache miss"`, `cause="model_not_loaded"`. Honest; no fabrication. |
| Profile with ml down | **PASS** — HTTP 503 honest error envelope (profile route has no demo fallback; the selected-cell panel shows the honest miss copy). |
| Frontend crash / stale data | Covered by automated suite: `layout.test.tsx` (fallback_demo → "not the live model") and e2e suites for unavailable/envelope-error states; no crash paths observed. |
| Restore | **PASS** — ml restarted (health 200, region bay_of_bengal, 730 dates); availability back to 730; map back to `model_prediction`. |

## 4. Provenance verification (Task 4)

| Requirement | Evidence | Result |
|---|---|---|
| "Research prototype" / "Historical reconstruction" | `Header.tsx:14` renders the chip; asserted in `layout.test.tsx` and e2e | **PASS** |
| BoB currently available | Date selector populated with 730 dates + `data-testid="latest-available"` = 2023-12-31 + provenance line | **PASS** |
| Range 2022-01-01..2023-12-31 | Live `/availability`: 730 dates, first/last verified; e2e 730-date test | **PASS** |
| Checkpoint provenance (hybrid_v1, best.pt, epoch 83) | Live `/availability` region entry: `checkpoint.file=best.pt, epoch=83, val_loss=0.37146, generated_at=2026-09-06T13:48:16+00:00`; UI `provenance-line` renders `hybrid_v1 · best.pt · epoch 83 · val_loss ... · data through 2023-12-31` (asserted `/epoch 83/i`) | **PASS** |
| Validation NOT presented as conventional held-out test set | UI copy: ARGO panel = "Aggregate, depth-wise validation against independent ARGO floats", "Modeled reconstruction; aggregate validation, not cell-exact." `dataset.py` docstring documents temporal `val_fraction` holdout, **no held-out test year** (2022-2023 full-store training). No "test set" language anywhere in UI | **PASS** |
| No realtime / "yesterday" / forecasting claims | `layout.test.tsx` asserts absence of `/realtime|live now/i`; `validation.test.tsx` asserts absence of `/realtime|real-time/i`; header/footer/provenance copy checked | **PASS** |
| Fallback honestly labeled | `StatusBanner` "Model service offline; pre-built cache, not the live model." asserted in layout.test | **PASS** |

## 5. Test suites (commands used)

| Suite | Command | Result |
|---|---|---|
| Backend | `.venv/bin/python -m pytest backend/tests` (from repo root; `backend/.venv` has a broken `.pth`) | **146 passed** |
| ML serving | `.venv/bin/python -m pytest ml/tests/unit/serving/test_server.py` | **15 passed** |
| Frontend unit + e2e | `npx vitest run` (frontend/) | **94 passed / 8 files** |
| Frontend coverage | `npx vitest run --coverage` | Lines **97.57%**, Stmts 97.57%, Branch 87.58%, Funcs 94.02% (≥ 80% gate) |
| Frontend build | `npm run build` | **PASS** (5.03 s, chunk-size warning only) |

## 6. Issues

1. **BLOCKER — API fabricates predictions for declared-but-unserved regions** (`arabian_sea`, `north_indian_ocean`): direct `/ocean/map` and `/ocean/profile` return bay_of_bengal data re-labeled as the requested region, HTTP 200 `model_prediction`. Scenarios D/E fail on the direct-API path. The UI cannot reach this path (availability-driven, verified in the hook), so the demo flow itself is safe, but the API is not honest as required by the checkpoint. Fix: region guard vs `svc.region_dir.name` in the two ml handlers + a regression test (see §2); optional backend echo-region validation.
2. **Test gap** (same root cause): no ml test for a declared-but-unserved region.
3. **Cleanup — `backend/uv.lock`**: generated by `uv run`; should NOT be committed. Smallest safe fix: add `uv.lock` to `.gitignore` (repo may keep per-Python-env lockfiles out of Git by policy; root `uv.lock` is likewise untracked).
4. Minor (non-blocking): demo-cache days are weekly Wednesdays; the UI offers exactly the cached list so selection stays consistent. Profile has no demo-cache fallback (503 when ml is down) — honest but a degraded-state UX consideration for a future iteration, not a reliability defect.
5. Minor (documentation): `contracts/ml/inference-rpc.schema.json` health `dates` description references the request `region`; acceptable doc-level note, no schema change needed.

## 7. Commit recommendation

**NOT READY FOR COMMIT** while the D/E fabrication bug is open. The demo UI flow itself verifies green across all scenarios (A–C, F–G, failover, provenance), so the fix is contained: apply the ml region-guard change + regression test (§2, smallest safe fix), re-run ml + backend suites, and re-verify D/E.

### Files safe to commit (after the fix + `.gitignore` change)
All 26 files except `backend/uv.lock`:

- New: `backend/app/services/availability.py`, `backend/app/api/v1/routes/availability.py`, `backend/tests/api/test_availability.py`, `contracts/api/availability.schema.json`, `docs/work-log/2026-09-08-p0-capability.md`.
- Modified: `backend/app/api/v1/router.py`, `backend/app/api/v1/routes/history.py`, `backend/app/api/v1/routes/metadata.py`, `backend/app/services/cache.py`, `backend/app/services/inference_client.py`, `backend/tests/api/test_health_history_metadata.py`, `backend/tests/unit/test_cache.py`, `backend/tests/unit/test_inference_client.py`, `frontend/src/App.tsx`, `frontend/src/api/client.ts`, `frontend/src/api/client.test.ts`, `frontend/src/components/layout/Header.tsx`, `frontend/src/hooks/useOceanExplorer.ts`, `frontend/src/types/contracts.ts`, `frontend/src/__tests__/e2e-explorer.test.tsx`, `frontend/src/__tests__/layout.test.tsx`, `ml/src/oceanembed/serving/server.py`, `ml/tests/unit/serving/test_server.py`, `ml/src/oceanembed/data/dataset.py`, `contracts/ml/inference-rpc.schema.json`, `config/datasets.yaml`.

### Files to exclude
- `backend/uv.lock` (uv-generated, not intentionally tracked). Add `uv.lock` to `.gitignore`.

### Recommended commit messages (conventional)
- `feat: expose region-scoped availability with checkpoint provenance` (includes `backend/uv.lock` exclusion via `.gitignore` chore).
- `fix: refuse predictions for regions the model service does not serve` (the D/E fix).
- If committed as one unit after the fix: `feat: region-scoped availability, provenance labeling and honest degraded serving (P0 capability)`.

**Overall status: demo reliability GREEN for the user-visible flow (scenarios A–C, F, G, failover, provenance); NOT GREEN for direct-API region integrity (scenarios D, E). Blocking issue requires the two-line ml guard before commit.**