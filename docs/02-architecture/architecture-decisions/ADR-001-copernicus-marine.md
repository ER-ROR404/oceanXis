# ADR-001: Copernicus Marine as primary data provider

- **Status:** Accepted
- **Date:** project inception (SIH26066)
- **Owner:** data-engineering / backend

## Context

OceanEmbed needs a scientific, programmatic ocean-data source capable of regional/time/variable
subsetting for both historical training data and recent-daily inference data.

## Decision

Use **Copernicus Marine** as the primary data provider, accessed through the **`copernicusmarine`
Python Toolbox** (`login`, `describe`, `subset`, `get`). All access goes through the backend
integration layer; the frontend never calls Copernicus.

## Alternatives considered

- Direct FTP/file downloads — heavier, less targeted, error-prone.
- Other gridded providers — no Toolbox-style programmatic subsetting.
- Frontend-direct API access — rejected (credential exposure, RULE 1/2).

## Consequences

- Dataset IDs must be **verified** via `describe()` before use (RULE 7) — they change.
- Credentials are backend-only, server-side.
- Latency is dataset-specific; "real-time" is never claimed without verification.
- Regional subsets are practical for the MVP (doc `docs/04-data/`).

## References
- SYSTEM_MEMORY_DUMP.md §44–§48, §134 (Decision 1–5).