# ADR-007: Temporal data split

- **Status:** Accepted
- **Date:** project inception (SIH26066)
- **Owner:** ml

## Context

Randomly splitting daily ocean grids into train/validation/test causes temporal leakage: nearby
dates are autocorrelated, so the "test" set would be memorized.

## Decision

Split strictly by **time**:

```text
TRAIN:     earlier period
VALIDATION: middle period
TEST:      latest held-out period
```

Example (illustrative only, exact years pending data coverage): `2020–2022 → 2023 → 2024`.
The test set remains untouched during hyperparameter/architecture selection.

## Related rules

- Normalization statistics computed from **training data only** (RULE 11).
- Optional spatial holdout is a separate experiment (region generalization).
- Samplers must never produce leakage across the temporal fold boundary (§90).

## Consequences

- Evaluation reflects the model's ability to generalize to unseen dates.
- Exact split years are decided only after verifying dataset coverage overlaps (§126).

## References
- SYSTEM_MEMORY_DUMP.md §33, §89, §134 (Decision 24).