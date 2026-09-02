# Training Policy

> Training, validation, leakage, normalization, and reproducibility rules.
> Source: SYSTEM_MEMORY_DUMP.md §33, §38, §85–§89, §105.

## Data split (LOCKED: temporal only)

```text
TRAIN:     earlier period       (e.g. 2020–2022 illustrative)
VALIDATION: middle period       (e.g. 2023)
TEST:      latest held-out period (e.g. 2024)
```

Exact years chosen **only after coverage overlap verification** (§126).
No random temporal splits; test untouched during tuning (§89).

## Normalization (LOCKED)

- z-score normalization per channel: `x_norm = (x - mean) / std`.
- `mean`/`std` computed **from training data only** (RULE 11, §38).
- Stored as model artifacts; inverse applied before displaying °C (§39).

## Loss (MVP: MaskedMSE)

Primary: `L = mean(mask * (prediction - target)²)`.

Alternatives/advanced (not MVP-first): Huber, depth-weighted, physics-regularization,
uncertainty NLL — see `docs/05-ml/` and `ml/src/oceanembed/losses/`.

## Optimizer / scheduler (not locked)

Starting point: Adam, lr=1e-3 (tunable), optional ReduceLROnPlateau — engineering
choices, not locked (§87–§88).

## Reproducibility

- Seeds pinned via `reproducibility.py`.
- Preprocessing/normalization versions recorded in checkpoint manifest (§114).
- Dataset manifest + provenance accompany training samples (§78, §80).

## Leakage checklist (pre-training)

- target not in input; future obs not in past samples
- normalization train-only; val/test dates strictly later
- ARGO validation independent
- no target-derived features; no GLORYS subsurface channels in input