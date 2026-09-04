# ADR-013: Physics-Aware Loss as Technical Differentiator

- **Status:** Accepted (team decision)
- **Date:** 2026-09-04 (SIH26066 build)
- **Owner:** ml

## Context

A pure black-box CNN+ConvLSTM is easy for another team to reproduce. The team identified
physics-aware training constraints as a differentiator that makes the reconstruction more
scientifically constrained without claiming physical perfection.

Ocean temperature profiles have vertical structure that should be physically plausible.
Random vertical jumps (e.g., 28→27.9→27.8→19→27.5°C) are suspicious and indicate
model error that can be penalized during training.

## Decision

Add a **vertical smoothness regularization term** to the training loss:

```
L_total = L_MSE (masked)
        + λ₁ × L_vertical_smoothness
        + λ₂ × L_masked_data
```

Where `L_vertical_smoothness` penalizes large temperature differences between adjacent
depth levels that are physically implausible.

This is a **training-time constraint**, not a post-processing filter. The model learns
to produce vertically consistent profiles.

## Scope

- Implement after the deterministic MaskedMSE baseline works (Golden Rule 12).
- λ₁ is a config hyperparameter, tuned experimentally.
- Do NOT over-constrain: ocean temperature can change non-monotonically with depth
  (thermocline, halocline effects). The loss penalizes extreme discontinuities, not
  all vertical variation.
- Do NOT claim this makes the model "physically perfect" — it makes reconstruction
  "more scientifically constrained."

## Consequences

- New loss module: `ml/src/oceanembed/losses/vertical_smoothness.py`.
- Configurable via `config/training.yaml` (λ₁ weight).
- Evaluation must compare: baseline MSE vs MSE + physics-aware loss.
- Documentation must be honest about what this does and doesn't guarantee.

## References

- `docs/01-product/product-vision.md` — §"Physics-Aware Loss".
- SYSTEM_MEMORY_DUMP.md §24 (optional physics-aware loss).
- ADR-011 (product vision), ADR-012 (uncertainty as core).
