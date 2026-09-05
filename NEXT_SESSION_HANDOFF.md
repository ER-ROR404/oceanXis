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

### 1. Wait for GLORYS download (blocker)
- Monitor: `pgrep -af download_historical` + `ls data/processed/bay_of_bengal/glorys_temperature/ | grep -c '\.nc$'` (expect 9)
- Verify depth range: file names must say `0.49-1452.25m` (NOT `0.49-902.34m`) — that confirms the depth fix is live.
- When all 9 clean files exist and process exits → proceed.

### 2. Rebuild tensors (5 min)
```bash
source .venv/bin/activate
python scripts/build_training_dataset.py --region bay_of_bengal --output-dir data/tensors
```
- Expect X: [~730, 7, 69, 81], Y: [~730, 15, 69, 81], mask: [69, 81].
- Verify no duplicate timestamps, normalization_stats.json regenerated from training-only window.
- NOTE: legacy 2024-06-01 proof file remains in dirs; excluded via timestamp intersection (they won't match 2022-2023 range).

### 3. Local CPU smoke train (10 min)
```bash
python ml/scripts/train_colab_entry.py --config ml/configs/hybrid_v1.yaml --data-dir data/tensors/bay_of_bengal --artifacts-dir /tmp/opencode/smoke --epochs 2 --check
```
- Confirm finite decreasing loss (regression: previously NaN→0 collapse), best.pt/latest.pt, run_manifest.json.

### 4. Commit + push
- Commit today's work: copernicus fix+tests, build-script filter+tests, DepthDecoder odd-grid fix+tests, masked-loss Trainer fix+tests, train_colab_entry wiring+tests, hybrid_v1.yaml, notebook.
- Update SYSTEM_MEMORY_DUMP.md + CHANGELOG.

### 5. Colab T4 full training (2-4 h)
- Open `colab/oceanembed_training.ipynb`; upload `data-engineering.tar.gz` of tensors to Drive; Cell 6 trains with `ml/configs/hybrid_v1.yaml`.
- Target: 100 epochs, convlstm_hidden=128, batch 8, lr 1e-3, patience 15, NLL loss.

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
