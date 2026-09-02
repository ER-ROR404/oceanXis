# ADR-002: FastAPI backend

- **Status:** Accepted
- **Date:** project inception (SIH26066)
- **Owner:** backend

## Context

The backend must expose the scientific app as HTTP API, integrate with the Copernicus Python
Toolbox, xarray, and a PyTorch inference runtime, and keep the frontend separate.

## Decision

Use **Python 3 + FastAPI** for the application backend (with Pydantic validation, uvicorn server).

## Alternatives considered

- Node/Express, Go, Java — would break the single-language scientific stack
  (Copernicus client, xarray, PyTorch).
- Flask/Django — workable, but FastAPI provides typed schemas + async + OpenAPI generation.

## Consequences

- Backend remains part of the Python scientific ecosystem (RULE 69 of the intended design).
- API schemas are enforced via Pydantic and mirrored by `contracts/api/`.
- Copernicus credentials stay server-side behind FastAPI.

## References
- SYSTEM_MEMORY_DUMP.md §61, §69, §134 (Decision 28).