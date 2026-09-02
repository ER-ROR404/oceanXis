# Training Operations

> Cloud/local training execution and artifact promotion.

## Workflow

1. Data engineering produces a harmonized training dataset (chunked downloads, registry manifests).
2. Configure an experiment: `ml/configs/experiment_template.yaml`.
3. Train locally or submit a cloud job (`infrastructure/cloud-training/`).
4. Evaluate and generate reports (`ml/scripts/evaluate.py`).
5. Promote an approved checkpoint to the model registry with a full manifest.
6. Export a serving artifact and point inference at it.

## Reproducibility

- Pin dataset/preprocessing/normalization versions in the checkpoint manifest (§114).
- Seeds pinned (`reproducibility.py`).
- Config-driven experiments (not magic numbers).

## Environment isolation

- Training uses the ML environment / training container.
- The backend never runs/trains; it only serves an approved checkpoint (RULE 3).
- `ml/Dockerfile.training` vs `ml/Dockerfile.inference` are intentionally separate (§54).

## Data policy

- Historical training uses stable reprocessed products; demo uses latest available daily data
  (§83–§84).
- Do not download years before a one-day test succeeds (Golden Rule 11).