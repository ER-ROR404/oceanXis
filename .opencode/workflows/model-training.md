# Model-Training Workflow

Safe workflow for changing models/training.

## Rules specific to model work

- RULE 8 — GLORYS subsurface never an inference input.
- RULE 9 — ARGO independent validation only.
- RULE 10 — temporal split; test untouched during tuning.
- RULE 11 — normalization from training data only.
- RULE 13 — no checkpoints in Git; use manifests + artifact store.
- Golden Rule 21 — every claimed metric traceable; never invent validation scores.

## Steps

1. Read `docs/05-ml/` (system, architecture, features, training, evaluation, tracking,
   checkpoint policy, model card).
2. Define the experiment in an `ml/configs/<experiment>.yaml` + `experiments/registry.yaml` entry.
3. Write tests first: tensor shape/contract, split temporal ordering, normalization trained-only,
   no-target-in-input, metrics correctness.
4. Train the smallest local experiment (small epochs) to sanity-check shapes/loss.
5. Evaluate: RMSE/bias/correlation overall + depth-wise, spatial, ARGO validation, baselines.
6. Export: reproducible checkpoint via `ml/scripts/export_model.py` + manifest
   (`contracts/ml/checkpoint-manifest.schema.json`). Register in `model-registry/registry.yaml`.
7. Update `docs/05-ml/model-card.md` with results + limitations (no invented scores).
8. Verify: `ml/tests` + `make lint`; contract validation.

Never promote a checkpoint without a manifest + evaluation.