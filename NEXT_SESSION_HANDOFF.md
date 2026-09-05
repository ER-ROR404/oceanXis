# Session Handoff — 5 September 2026

## Current State

**Phase 3.3 DONE (partially)** — Real data pipeline activated + critical neural training bugs fixed.

### Data status
- Multi-day Copernicus download (PID-portion) launched: **2-year BoB 2022-01-01→2023-12-31**, all 8 datasets, 3-month chunks.
- Completed: SST, SSS, SSH, current_U, current_V, wind_U, wind_V (10 files each).
- **GLORYS re-download in progress (v2)**: v1 was capped at `maximum_depth=1000` → native levels only reached 902.34m, so the 1000m canonical target silently used 902m data. Fixed via `GLORYS_DOWNLOAD_MAX_DEPTH_M=1500` (contract constant) + vertical interpolation in `harmonize_glorys_target`. v2 uses `--skip-inputs` (only GLORYS, ~9 chunks × ~10min). Log: `/tmp/opencode/download_glorys_v2.log`.
- Existing tensors in `data/tensors/bay_of_bengal/` are the OLD 1-day proof (2024-06-01). MUST be rebuilt when download completes.

**IMPORTANT — GLORYS depth contract (fixed this session):**
- GLORYS native vertical grid is irregular (0.49, 1.54, 2.6, …, 902.3, 1062.4, 1245.3, 1452.3m @ max_depth=1500).
- `harmonize_glorys_target` now LINERALY INTERPOLATES to the exact 15 canonical depths (0, 5, 10, …, 1000m). 0m maps to the shallowest native level (top model level ≈ surface).
- It now RAISES `ValueError` if the native grid can't bracket 1000m — never extrapolate (SMD Rule 1).
- Old nearest-neighbor selection was WRONG (offset targets up to 57m: 700m←643.6m); removed from the harmonize path.

### Test status
```
164 tests passing (83 ML + 81 data-engineering)
├── ml/tests/test_nll_loss.py                14/14  (masked loss: NaN targets, NaN at valid-cell depths, 3D mask)
├── ml/tests/test_reconstruction_net.py      29/29  (odd-grid exact-size decoder)
├── ml/tests/test_training_pipeline.py       19/19  (NaN train/val, masked metrics)
├── ml/tests/test_train_colab_entry.py        6/6   (real training entry)
├── data-engineering/test_harmonization.py   26/26  (+5 vertical interpolation RED→GREEN)
├── data-engineering/test_copernicus.py      13/13  (describe() v2.x fix + GLORYS depth contract)
└── data-engineering/test_build_script.py    10/10  (find_nc_files cleanup)
```

## Critical fixes this session (TDD, RED→GREEN)
1. **DepthDecoder odd-grid bug** — model output 64×80 for real BoB grid 69×81 (3× MaxPool2d→×8 can't reproduce odd dims). Fixed: exact-size interpolate in final decoder stage. 3 regression tests.
2. **NaN targets/train collapse** — GLORYS is ~37% NaN (land+shelf+deep). Unmasked NLL → NaN loss → collapse to 0 (0×NaN in autograd backward). Fixed: `masked_nll_loss` effective mask = `mask AND finite(target)`, targets sanitized, used in train_epoch AND validate; metrics masked+NaN-safe.
3. **GLORYS depth interpolation** — nearest-level selection off by up to 57m; now linear interpolation to exact canonical depths, ValueError if 1000m unbracketed. +5 tests.
4. **GLORYS download depth** — `maximum_depth=1500` via contract constant `GLORYS_DOWNLOAD_MAX_DEPTH_M`. +1 test.
5. Copernicus describe() v2.x fix (+11 tests); build-script duplicate/partial filtering (+10 tests); train_colab_entry real training (+6 tests).

### 1. ✅ DONE — GLORYS download complete (9 succeeded, 0 failed)
- All 9 files `0.49-1452.25m` (depth fix live), log `/tmp/opencode/download_glorys_v2.log`, no partial/temp files.

### 2. ✅ DONE — Tensors rebuilt (2-year BoB)
```bash
python scripts/build_training_dataset.py --region bay_of_bengal --output-dir data/tensors
```
- X: [730, 7, 69, 81], Y: [730, 15, 69, 81], mask: [69, 81] (5293/5589 valid cells).
- Time range exactly 2022-01-01 → 2023-12-31 (730 days; both years non-leap).
- NaN: X 22.8%, Y 37.3%; Y finite fraction 0.727 → 0.533 with depth (shelf cells).
- normalization_stats.json: per-channel z-score, computed from training-only window (RULE 11).
- **Tensor stores live at `data/tensors/bay_of_bengal/`** (X.zarr Y.zarr mask.zarr normalization_stats.json). NOTE: build script writes to `data/tensors/{region}` by default; if you pass `--output-dir data/tensors` it writes FLAT (did this once, moved into bay_of_bengal/).
- NOTE: legacy 2024-06-01 proof nc files still in input dirs — excluded by `compute_common_times` (intersects ALL inputs AND target axis; new fix this session, 4 tests).

### 3. ✅ DONE — Local CPU smoke train (regression gate PASSED)
```bash
python ml/scripts/train_colab_entry.py --config /tmp/opencode/hybrid_v1_smoke.yaml --data-dir data/tensors/bay_of_bengal --artifacts-dir /tmp/opencode/smoke
# smoke config = hybrid_v1.yaml with epochs: 2 (sed 100 -> 2)
```
- train_loss 213.7 → 93.6 → 54.4 (3 epochs), val_loss 129.5 → 67.7 → 43.9 — **all finite, decreasing** (NaN-collapse regression gate passed).
- Y is raw Kelvin (~300K), X is z-scored → loss magnitudes look large; that's expected scale, not a bug. Deep depths (500-1000m) RMSE 3-5K, surface ~22K at epoch 2.
- NOTE: `--epochs N` is NOT a CLI arg (errors) — epochs come from config `training.epochs`.

### 4. ✅ DONE — Committed (3 commits this session)
- `7ac1ec7` fix: GLORYS vertical interpolation + NaN-safe masked NLL + download depth contract
- `2b76d5a` docs: handoff update
- `7f94228` fix: tensor common-time axis must include GLORYS target days
- 168 tests passing (83 ML + 85 data-engineering).

### 5. Colab T4 full training (2-4 h) — NEXT BLOCKER
- Open `colab/oceanembed_training.ipynb`; upload `data-engineering.tar.gz` of tensors to Drive; Cell 6 trains with `ml/configs/hybrid_v1.yaml`.
- Target: 100 epochs, convlstm_hidden=128, batch 8, lr 1e-3, patience 15, NLL loss.
- To package tensors for Drive: `tar czf /tmp/opencode/tensors_bob.tar.gz -C data/tensors bay_of_bengal` (~need X+Y+mask+normalization_stats.json; check notebook cell 5 for expected layout).
- Expect val_nll to start high (~130) and decrease; don't judge by absolute value (Kelvin targets).

### 6. ARGO validation + demo path (Phase 6-9)
- ARGO holds out until after first GLORYS-validated checkpoint.

---

## Key files to read next

1. **`docs/superpowers/specs/2026-09-04-ml-architecture-design-v2.1.md`** — AUTHORITATIVE ML spec (29 sections)
2. **`AGENTS.md`** — Operating rules (esp. RULE 10 temporal splits, RULE 11 train-only normalization)
3. **`SYSTEM_MEMORY_DUMP.md`** — Project history
4. **`config/datasets.yaml`** — Verified dataset IDs
5. **`ml/configs/hybrid_v1.yaml`** — Primary config for real run
6. **`ml/scripts/train_colab_entry.py`** — Real training entry (--check/--data-dir/--gpu)

---

## Quick commands

```bash
source .venv/bin/activate
python -m pytest ml/tests/ data-engineering/tests/ -q          # full suite (158)
python -m pytest ml/tests/test_training_pipeline.py -v         # NaN/masked regression
python -m pytest ml/tests/test_reconstruction_net.py -v        # odd-grid regression
python scripts/build_training_dataset.py --region bay_of_bengal --output-dir data/tensors
python ml/scripts/train_colab_entry.py --config ml/configs/hybrid_v1.yaml --data-dir data/tensors/bay_of_bengal --artifacts-dir /tmp/opencode/smoke --check
```

---

## Decision log (updated)

- **Architecture:** CNN + ConvLSTM (spec v2.1 §7-§12); final decoder stage interpolates to EXACT grid size (odd dims supported)
- **Loss:** MASKED NLL primary — land/shallow cells excluded with NaN-safe sanitization (real GLORYS data demands it); physics constraints optional (spec v2.1 §14)
- **Uncertainty:** Aleatoric via σ² = softplus(log_var) + ε (spec v2.1 §15)
- **Split:** Train 2018-2023 / Val 2024 / Test 2025 planned; **current 2-year window: 2022-2023 train/val temporal_locked 80/20** (ADR-008 regional MVP expansion)
- **Normalization:** Z-score from training data only, NaN→0 fill (spec v2.1 §17)
- **Training host:** Google Colab free T4 GPU (ADR-009)

---

## Blocker

**GLORYS multi-month download in progress** — the only remaining blocker for the first real training run. Everything else is ready.
