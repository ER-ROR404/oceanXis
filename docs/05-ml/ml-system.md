# ML System

> Complete ML lifecycle: dataset creation through deployment.
> Source: SYSTEM_MEMORY_DUMP.md §85–§129, §143–§145.

## Lifecycle

```text
data engineering
    ↓ harmonized daily 0.25° tensors
ML dataset (PyTorch Dataset/DataLoader)
    ↓ temporal split (TRAIN/VAL/TEST)  [ADR-007, RULE 10]
normalization (TRAIN-ONLY statistics) [RULE 11]
    ↓
training (CNN encoder–decoder baseline)
    ↓ validation (no early-stopping on test) [§88]
checkpoint + manifest            [contracts/ml/checkpoint-manifest.schema.json]
    ↓
evaluation (RMSE, bias, correlation; depth-wise; spatial; ARGO) [docs/05-ml/evaluation-policy.md]
    ↓
export / model registry          [registry.yaml; checkpoints NOT in Git (RULE 13)]
    ↓
inference / serving              [docs/02-architecture/ml-serving-flow.md]
```

## Independence

The ML package is **independently executable** — it must run without importing frontend/backend
application code (RULE 4, Rule 4). Entry points: `ml/scripts/train.py`, `evaluate.py`, `infer.py`,
`export_model.py`, `validate_checkpoint.py`.

## Principles

- Start simple (CNN baseline) before any Transformer/ViT (Decision 20).
- Baseline comparisons required for credibility (§30, §91).
- Reproducibility via seeds, pinned config, and manifests (§114).
- No fabricated scores, data, or ARGO matches (Golden Rules 1–4, 21).