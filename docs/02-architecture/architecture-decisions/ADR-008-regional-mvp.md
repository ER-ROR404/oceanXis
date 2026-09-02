# ADR-008: Regional MVP scope

- **Status:** Accepted
- **Date:** project inception (SIH26066)
- **Owner:** product / ml / data-engineering

## Context

The full North Indian Ocean domain (5°N–30°N, 45°E–105°E) at 0.25° daily over multiple years is too
much data and compute for a 36-hour proof. The problem statement explicitly expects a Proof-of-Concept
over Bay of Bengal and/or Arabian Sea.

## Decision

Scope the MVP to two application regions:

```text
Bay of Bengal:  min_lon 80°E, max_lon 100°E, min_lat 5°N, max_lat 22°N
Arabian Sea:    min_lon 45°E, max_lon 75°E, min_lat 5°N, max_lat 25°N
```

Both use the identical Copernicus access mechanism — they are not separate systems.

## Consequences

- Data volumes stay tractable; regional subsets are the unit of work.
- The official North Indian Ocean grid/conventions are preserved in `config/` so full-domain
  expansion remains possible.
- Product narrative stays regional and demonstrable (Golden Rule 20).

## References
- SYSTEM_MEMORY_DUMP.md §11–§12, §119, §134 (Decision 7).