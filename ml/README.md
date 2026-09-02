# ml/

**OceanEmbed model training and inference (PyTorch).**

## Scope

```text
ML dataset → training → checkpoint → evaluation → export → registry → backend inference
```

Runs independently of the frontend (RULE 4). GLORYS is the training/reference target; ARGO is
independent validation (RULE 9). Subsurface GLORYS variables are **never** inference inputs (RULE 8).

## Layout

```text
src/oceanembed/
  data/            PyTorch Dataset/DataLoader/manifests/samplers (temporal split, no leakage)
  preprocessing/   loader, QC, temporal, spatial, regrid, masking, normalization (train-only stats)
  models/          oceanembed, encoder, decoder, depth_embedding, uncertainty, baselines
  losses/          masked_mse (primary), huber, depth_weighted, physics_regularization, uncertainty_nll
  training/        trainer, optimizer, scheduler, callbacks, checkpointing, reproducibility
  evaluation/      metrics (RMSE/bias/corr), depth-wise, spatial, ARGO, baseline comparison, reports
  inference/       predictor, postprocess (denormalize+mask), profile
  registry/        model_registry, artifact_registry, manifests
configs/           baseline.yaml, cnn_v1.yaml, experiment_template.yaml
scripts/           train.py, evaluate.py, infer.py, export_model.py, validate_checkpoint.py
tests/             dataset, preprocessing, shapes, losses, metrics, inference (~80% gate)
```

## Contracts

- Consumes `contracts/ml/model-input.schema.json` (RULE 5).
- Produces `contracts/ml/model-output.schema.json` [B,15,H,W] temperature (degC).
- Checkpoints carry `contracts/ml/checkpoint-manifest.schema.json`; never committed to Git (RULE 13).

## Environment

`ml/pyproject.toml` — PyTorch + scientific stack, isolated from the backend.
See `docs/05-ml/` and `docs/07-operations/training-operations.md`.

> **Pre-build stage:** structure is in place; implementation lands in the coding phase.