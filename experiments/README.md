# experiments/

**OceanEmbed experiment tracking (reproducible ML experiments).**

```text
registry.yaml                experiment IDs -> config/dataset/results
templates/experiment.yaml    standard experiment config structure
reports/                     generated reports (gitkept; outputs excluded)
```

## Rules

- Every experiment: ID, config hash, dataset manifest, preprocessing/normalization version,
  evaluation results (no invented scores — Golden Rule 21).
- Experiments never merged to `main` (branch: `experiment/<name>`).
- Policy: `docs/05-ml/experiment-tracking.md`.

> **Pre-build stage:** scaffolding + template; populated during ML coding phase.