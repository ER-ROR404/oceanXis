# ADR-006: ARGO as independent validation

- **Status:** Accepted (LOCKED by problem statement recommendation)
- **Date:** project inception (SIH26066)
- **Owner:** ml / backend

## Context

Credibility demands evaluation against independent observations, not just the gridded reanalysis
used as the training target.

## Decision

Use **ARGO** as the independent validation source. ARGO is not a required frontend input and is not
an inference input. Validation matches model predictions to ARGO profiles by date and location,
interpolates to the 15 depths, and computes RMSE/bias/correlation.

## Rules

- ARGO remains independent validation data (RULE 9).
- No fabricated ARGO matches; gaps are reported as missing (Golden Rules 4, 21).

## Alternatives considered

- Moorings/ships — sparse; ARGO gives broad regional coverage.

## Consequences

- Backend validation service needs an ARGO lookup capability (geo + date).
- Demo shows ARGO comparison only where data genuinely permits.

## References
- SYSTEM_MEMORY_DUMP.md §32, §95, §134 (Decision 13–14).