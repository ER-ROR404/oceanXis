# ADR-003: PyTorch as the ML framework

- **Status:** Accepted
- **Date:** project inception (SIH26066)
- **Owner:** ml

## Context

The ML pipeline needs a framework for a CNN encoder–decoder (surface encoder → ocean embedding →
depth decoder), with future uncertainty and attention options.

## Decision

Use **PyTorch** as the ML framework. Supporting stack: NumPy, xarray, pandas, scipy, scikit-learn,
NetCDF4/h5netcdf/Zarr as required.

## Alternatives considered

- TensorFlow/Keras — viable, but PyTorch keeps a coherent Python scientific stack and clean
  custom-loop control for masked losses and temporal splits.
- JAX — more experimental than needed for the MVP.

## Consequences

- ML environment is isolated from the backend (ADRs/RULES: backend never contains training code).
- Loss (masked MSE), evaluation (RMSE/bias/correlation), and inference run in PyTorch.
- Training and inference images are separated (`ml/Dockerfile.training|inference`).

## References
- SYSTEM_MEMORY_DUMP.md §70, §134 (Decision 20).