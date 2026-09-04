# ADR-011: 3-Mode Product Vision (Map + Profile + Validation)

- **Status:** Accepted (team decision)
- **Date:** 2026-09-04 (SIH26066 build)
- **Owner:** product

## Context

The earlier product vision had 2 modes: depth map and vertical profile.
Those are good visualization modes but do not constitute a winning solution
against 500+ teams building "Copernicus data → CNN/ConvLSTM → 15-depth temperature map."

The team defined a 4-layer winning solution:
1. Reconstruction Engine (7 surface → subsurface)
2. Scientific Validation (independent ARGO observations)
3. Uncertainty / Confidence (calibrated uncertainty per cell)
4. Operational Explorer (map + profile)

And 3 product modes that implement these layers.

## Decision

Define OceanEmbed as having **3 product modes**:

1. **Mode 1 — Spatial Map Mode:** Region → Date → Depth → temperature map + confidence/uncertainty layer.
2. **Mode 2 — Vertical Profile Mode:** Click cell → 15-depth profile + ARGO comparison + per-profile RMSE/Bias/Correlation.
3. **Mode 3 — Scientific Validation Mode:** Judge-facing summary with overall RMSE/Bias/Correlation, ARGO coverage, spatial error map.

## Consequences

- `docs/01-product/product-vision.md` — authoritative product vision (created).
- `docs/01-product/user-workflows.md` — updated to reflect 3 modes.
- `docs/01-product/product-requirements.md` — FR-7 and FR-10 upgraded from PROPOSED to CORE.
- Frontend (Phase 7) must implement all 3 modes.
- Backend must serve uncertainty + validation data alongside predictions.

## References

- `docs/01-product/product-vision.md` — full specification.
- ADR-012 (uncertainty as core), ADR-013 (physics-aware loss).
