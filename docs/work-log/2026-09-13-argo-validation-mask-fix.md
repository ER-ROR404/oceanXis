# Work Log — 2026-09-13: ARGO re-validation after the ocean-mask fix (reproduction)

> **Purpose:** Re-run the independent ARGO validation (RULE 9) against the **corrected
> ocean mask** and confirm whether the committed validation summary still holds.
> **Result: reproduced exactly** — overall and all 15 depth levels are identical to
> `docs/work-log/2026-09-06-argo-validation.md`. The committed summary is left unchanged.
>
> The committed asset `frontend/src/assets/validation/argo_validation_summary.json` and
> `experiments/reports/argo_validation_2026-09-06.json` therefore remain valid.

## 1. Why a re-run was needed

The ocean validity mask in the tensor store was wrong: `scripts/build_training_dataset.py`
built it with `np.isfinite(x).any(axis=(0, 1))` ("any channel valid at any time"), marking
**94.7%** of the Bay of Bengal box as ocean, so the served field rendered as a rectangle.
It was corrected to require **every** input channel valid for a majority of the record
(`build_ocean_mask`), giving **68.7%** ocean (3,841 / 5,589 cells) that follows the real
coastline. See `scripts/build_training_dataset.py` + `data-engineering/tests/test_build_script.py`.

Because the masked cell set changed, the ARGO matched/unmatched set could change (a float near
a newly-masked coastal cell could flip to `land`), so the validation was re-run rather than
assumed.

## 2. What was unchanged (why the numbers should hold)

- Model weights (`best.pt`, epoch 83) — untouched.
- Input tensor `X` and `normalization_stats.json` — untouched (the checkpoint was trained with
  these stats; regenerating them would shift inference inputs, so they are deliberately kept).
- Therefore **ocean-cell predictions are unchanged**; only additional land cells are now masked
  to `NaN`. ARGO floats sit in the ocean, so the scored cells are the same.

## 3. Reproduction (public GDAC; no credentials)

The raw ARGO profiles are not committed (RULE 12/13). They were re-acquired from the public
GDAC and the evaluation re-run end-to-end:

```bash
# 1. Global profile index (public) — gz is 58 MB vs 316 MB plain
curl -sL -o /tmp/opencode/ar_index_global_prof.txt.gz \
  https://data-argo.ifremer.fr/ar_index_global_prof.txt.gz
gunzip -kf /tmp/opencode/ar_index_global_prof.txt.gz

# 2. Acquire BoB profiles for the tensor store's temporal validation window
python data-engineering/scripts/acquire_argo.py \
  --region-id bay_of_bengal --regions-yaml config/regions.yaml \
  --tensor-store data/tensors/bay_of_bengal \
  --index-file /tmp/opencode/ar_index_global_prof.txt \
  --gdac-cache /tmp/opencode/argo_gdac \
  --out /tmp/opencode/argo/profiles.json --download

# 3. Re-evaluate the checkpoint with the corrected mask
python ml/scripts/evaluate_argo.py \
  --config ml/configs/hybrid_v1.yaml \
  --checkpoint data/checkpoints/hybrid_v1/best.pt \
  --data-dir data/tensors/bay_of_bengal \
  --argo-profiles /tmp/opencode/argo/profiles.json \
  --artifacts-dir /tmp/opencode/argo
```

Acquisition: index **3,386,130 rows** → **295** profiles in the BoB bounds within the
validation window **2023-08-10 .. 2023-12-31** → **291 usable** (3 skipped "no valid levels").
Same 291 usable profiles as the original run.

## 4. Result — identical to the committed summary

| Metric | Re-run (corrected mask) | Committed (2026-09-06) |
|--------|------------------------|------------------------|
| Profiles loaded / matched / unmatched | 291 / 285 / 6 (all `land`) | 291 / 285 / 6 (all `land`) |
| Depth-level observations scored | 3,958 | 3,958 |
| **Overall RMSE** | **1.3533 °C** | 1.3533 °C |
| **Overall bias** | **+0.6121 °C** | +0.6121 °C |
| **Overall correlation** | **0.99** | 0.99 |

Depth-wise RMSE/bias/n**/correlation at every canonical depth (0, 5, 10, 20, 30, 50, 75, 100,
125, 150, 200, 300, 500, 700, 1000 m) also match to within 1e-9. In particular the
thermocline weakness is unchanged (75 m RMSE 2.8054 °C / bias +2.1687 °C; 100 m RMSE
2.6497 °C / bias +2.1635 °C), and the 6 unmatched profiles are still the same coastal cells
reported as `land`, never dropped.

## 5. Conclusion & honesty notes

- The corrected mask does **not** change the ARGO independent validation. The committed
  summary (`frontend/src/assets/validation/argo_validation_summary.json`) and experiment
  report are confirmed valid and unchanged.
- The numbers remain independent of GLORYS: ARGO is used only for validation (RULE 9), matched
  by date/location, no depth extrapolation.
- Raw profiles + full per-profile report live outside Git (RULE 12/13):
  `/tmp/opencode/argo/{profiles.json,argo_report.json}` for this run; Drive artifacts for the
  original run.
- Only BoB has a tensor store; no spatial-holdout generalization claim is made.
