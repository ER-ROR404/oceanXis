# ADR-005: GLORYS as training/reference target

- **Status:** Accepted (LOCKED by problem statement)
- **Date:** project inception (SIH26066)
- **Owner:** ml / data-engineering

## Context

A dense gridded target is needed to train the surface→subsurface reconstruction.

## Decision

Use **GLORYS** (Global Ocean Reanalysis, `GLOBAL_MULTIYEAR_PHY_001_030` family, dataset ID to be
verified via `describe()`) as the dense training/reference target. GLORYS temperature is mapped onto
the 15 standard depths on the 0.25° grid.

## Constraints

- GLORYS subsurface temperature is the **training target**, never an inference input (ADR-004).
- The exact current dataset ID **must be verified** through `copernicusmarine.describe()` before
  production use (RULE 7).

## Alternatives considered

- Other reanalyses — GLORYS is explicitly recommended by the problem statement.

## Consequences

- Training data production requires a coherent, overlap-verified multi-product stack (§126–§127).
- Evaluation against ARGO keeps the model honest beyond the reanalysis target.

## References
- SYSTEM_MEMORY_DUMP.md §31, §52, §126–§127, §134 (Decision 12).