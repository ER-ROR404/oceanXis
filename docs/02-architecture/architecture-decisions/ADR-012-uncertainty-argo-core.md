# ADR-012: Uncertainty and ARGO Validation as Core Features

- **Status:** Accepted (team decision)
- **Date:** 2026-09-04 (SIH26066 build)
- **Owner:** product/ml

## Context

Earlier, uncertainty (FR-7) and ARGO comparison (FR-10) were marked PROPOSED — nice to have
if time permits. The product vision upgrade recognizes these as **core differentiators** that
separate a No.1 solution from a prototype.

A pure "CNN → temperature map" is easy to reproduce. Adding calibrated uncertainty and
independent validation makes the reconstruction scientifically defensible.

## Decision

Upgrade from PROPOSED to **CORE**:
- **Uncertainty:** Gaussian heteroscedastic head (μ, log σ²) trained with NLL loss.
  Displayed as ±X.X °C on profiles; confidence/error layers on maps.
- **ARGO validation:** Per-profile RMSE/Bias/Correlation when ARGO data exists.
  Spatial ARGO coverage indicator. Never fabricated.
- **Validation Mode (Mode 3):** Judge-facing summary with all metrics.

## Consequences

- Model architecture gains an uncertainty head (after deterministic baseline works).
- Loss function: `L_total = L_MSE + λ × L_NLL` (configurable).
- Backend must serve uncertainty alongside temperature predictions.
- Frontend must render confidence layers (Mode 1), per-profile comparison (Mode 2),
  and validation summary (Mode 3).
- ARGO data pipeline: raw GDAC profiles matched by date/location (or CORA-OA fallback).

## References

- `docs/01-product/product-vision.md` — §"Technical Differentiators".
- SYSTEM_MEMORY_DUMP.md §21 (uncertainty), §32 (ARGO role), §94 (uncertainty display).
- ADR-011 (3-Mode Product Vision).
