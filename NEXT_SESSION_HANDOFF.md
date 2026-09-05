# Session Handoff — 5 September 2026

## Current State

**Phase 3.3 DONE (partially)** — Real data pipeline activated + critical neural training bugs fixed.

### Critical fixes this session (all TDD, RED→GREEN)
1. **DepthDecoder odd-grid bug** — model output 64×80 for real BoB grid 69×81 (3× MaxPool2d+scale×8). Fixed: exact-size interpolate in final decoder stage. 3 regression tests (`test_real_bog_grid_odd_dims`, `test_full_domain_odd_grid`, `test_decoder_odd_grid_exact_size`).
2. **NaN targets poison training** — GLORYS is 37% NaN (land+shallow). Unmasked `GaussianNLLLoss` → NaN loss → NaN gradients (0×NaN in autograd backward). Fixed: Trainer now uses `masked_nll_loss` (mask-aware, target sanitized with `torch.where(mask.bool(), target, 0)` BEFORE computing NLL), validate() metrics masked+NaN-safe. 5 new tests.
3. **NaN inputs spread through conv** — X land cells NaN → mu 100% NaN → learning signal 0. Fixed: `_normalize_x` zero-fills NaN after z-score (0 = neutral land). 1 new test.
4. **Copernicus describe() bug** — v2.x API rejects username/password in describe(). Fixed + 11 tests.
5. **train_colab_entry.py** — real training wired (run_training, --data-dir). 6 tests.
6. **build_training_dataset.py** — excludes `_(1).nc` dupes + partial writes. 10 tests.

### Data status
- Multi-day Copernicus download (PID-portion) launched: **2-year BoB 2022-01-01→2023-12-31**, all 8 datasets, 3-month chunks.
- Completed: SST, SSS, SSH, current_U, current_V, wind_U, wind_V (10 files each).
- In progress at end of session: **GLORYS temperature ~4/9 chunks** (each ~311MB, ~10 min each; copernicusmarine 2.4.1 with S3, transient connection-pool warnings are benign).
- Log: `/tmp/opencode/download_2022_2023.log`. Process: `setsid nohup python scripts/download_historical.py --region bay_of_bengal --start 2022-01-01 --end 2023-12-31 --chunk-months 3`.
- Existing tensors in `data/tensors/bay_of_bengal/` are the OLD 1-day proof (2024-06-01). MUST be rebuilt when download completes.

### Test status
```
158 tests passing (77 ML + 81 data-engineering)
├── ml/tests/test_nll_loss.py                12/12  (masked loss NaN-safe, 3D mask support)
├── ml/tests/test_reconstruction_net.py      29/29  (odd-grid exact-size decoder)
├── ml/tests/test_training_pipeline.py       19/19  (NaN train/val, masked metrics)
├── ml/tests/test_train_colab_entry.py        6/6   (real training entry)
└── data-engineering/tests/                  81 tests (copernicus 11 + build_script 10 + rest)
```

---

## Immediate next steps (in order)

### 1. Wait for GLORYS download (blocker)
- Monitor: `pgrep -af download_historical` + `find data/processed/bay_of_bengal/glorys_temperature -name '*.nc' ! -name '*.nc.*' | wc -l` (expect 9)
- When all 8 dirs have ~10 clean files and process exits → proceed.

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
