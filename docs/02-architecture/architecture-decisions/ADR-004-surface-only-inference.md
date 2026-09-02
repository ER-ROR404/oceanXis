# ADR-004: Surface-only inference

- **Status:** Accepted (LOCKED by problem statement interpretation)
- **Date:** project inception (SIH26066)
- **Owner:** ml / backend

## Context

The problem statement defines the inverse problem: reconstruct subsurface temperature *from surface
satellite observations*. Subsurface reference data (GLORYS, ARGO) must not leak into inference.

## Decision

**Model inference inputs are surface observations only**: SST, SSS, SSH/SLA, current U, current V,
wind U, wind V. GLORYS subsurface temperature, ARGO profiles, subsurface salinity, and subsurface
currents are **never** inference inputs. GLORYS is a training target; ARGO is independent
validation (RULE 8/9).

## Alternatives considered

- Feeding subsurface fields as auxiliary inputs — rejected (cheats the inversion; leaks the target).

## Consequences

- Data-leakage audit is required before training (§105 checklist).
- Preprocessing must guarantee that only the 7 surface channels reach the model.
- ARGO comparison is strictly a post-hoc validation view.

## References
- SYSTEM_MEMORY_DUMP.md §31–§32, §104–§105, ADR-005, ADR-006.