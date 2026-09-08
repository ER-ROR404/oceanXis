# Work Log — 2026-09-08: P0 capability hardening (availability + truthful coverage)

> **Purpose:** Records the P0 capability work on `feat/phase5-frontend-completion`:
> `GET /api/v1/availability`, dynamic date availability from the live model service
> (removing the 31-date demo-cache limitation), truthful per-region capability
> reporting, and the "historical reconstruction" product banner. No ML model
> changes, no fabricated data.

## 1. Verified facts that drive the implementation (RULE 7)

| Fact | Evidence |
|------|----------|
| Bay of Bengal tensor store = **730 daily days 2022-01-01..2023-12-31** | `data/tensors/bay_of_bengal/` (100 daily `.nc` files per month) |
| Grid 69×81 (0.25°), 7 surface channels, 15 depths (0–1000 m) | tensor store + `config/variables.yaml` |
| Demo cache = 31 weekly dates 2023-06-01..2023-12-28 | `artifacts/demo_cache/manifest.json` |
| Checkpoint `best.pt`, epoch 83, val_loss 0.3715, generated 2026-09-06 | `artifacts/demo_cache/manifest.json` `checkpoint` block |
| Only `bay_of_bengal` has data; `arabian_sea`/`north_indian_ocean` declared but empty | upstream data build |
| Latest inferable date 2023-12-31 | store coverage |

## 2. API changes (contracts updated)

- **`contracts/api/availability.schema.json` (new).** `GET /api/v1/availability`
  returns per-region entries: `{region, status: available|no_data, dates,
  date_start, date_end, depths, variables, grid, model_version, trained_on,
  data_version, checkpoint{file, epoch, val_loss, generated_at}}` plus root
  `model{version, trained_on, data_version}` and `generated_at`.
- **Dates cascade (precedence):** live model-service tensor-store dates, then
  demo-cache manifest fallback (`backend/app/services/availability.py`).
- **Region truthfulness:** ml service `/health` now reports its served `region`
  (≡ its tensor store); the backend returns `[]` for any requested region that
  does not match the served one (never guesses another region's dates).
  `metadata` now splits `regions` (servable today) from `regions_declared`
  (all 3 declared per problem statement).
- **No reneging on existing contracts:** map/profile/history/health envelopes
  unchanged; history delegating to the shared availability helper keeps its
  response shape identical.

## 3. Frontend behavior (all TDD, RED→GREEN)

- `getAvailability()` runtime-guarded client call (never trusts the wire: rejects
  unknown region ids, missing status, non-date strings, malformed grids,
  no_data entries that claim dates, available entries without checkpoint
  provenance).
- Date selector / "Latest available" now driven by the live availability report
  (730 options when the live service is connected), not the 31-date cache.
- Header chip: **Research prototype · Historical reconstruction**; field caption
  shows "Latest available: <date>"; provenance line (`model · best.pt · epoch N ·
  val_loss X · data through Y`). Regions without data show an honest
  "No data is currently available for <region>." empty state with a return link
  to the available region.

## 4. Verification

| Gate | Result |
|------|--------|
| Backend suite | 146 passed (`pytest backend/tests`) |
| ML serving unit tests | 15 passed |
| Frontend vitest | 94 passed, 8 files |
| Frontend coverage | 97.57% lines (80% gate) |
| `npm run build` (tsc + vite) | green |
| Live stack (ml :8080 + backend :8000 + vite :5173 proxy) | `/availability` = BoB available 730 dates 2022-01-01..2023-12-31, others no_data; live map `model_prediction` 69×81; response passes `availability.schema.json` validation |

## 5. Documentation corrections (truth vs. spec aspiration)

- `ml/src/oceanembed/data/dataset.py` docstring and `config/datasets.yaml`
  split-policy comment now state the **actual MVP store** (2022-01-01..2023-12-31,
  730 daily days, full-store training with temporal `val_fraction` holdout, no
  held-out test year). The 2018-2023/2024/2025 window split (spec §16) remains
  the LOCKED long-term design for the future multi-year store, not the MVP data.

## 6. Artifacts / scope notes

- No model training performed; model weights untouched (only the serving
  `/health` wire contract gained the additive `region` field).
- Timeline numbers (trained_on 2023-12-31, data_version
  `bay_of_bengal-2022-2023-v1`) come from the existing manifest, not invented.