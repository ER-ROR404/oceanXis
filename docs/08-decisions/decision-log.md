# Decision Log

> Consolidated project decisions. ADRs live in `docs/02-architecture/architecture-decisions/` and
> carry full rationale; this file is an index plus status summary.

## Architecture Decision Records

| ADR | Topic | Status |
|-----|-------|--------|
| ADR-001 | Copernicus Marine as primary data provider | Accepted |
| ADR-002 | FastAPI backend | Accepted |
| ADR-003 | PyTorch ML framework | Accepted |
| ADR-004 | Surface-only inference (no subsurface leak) | Accepted / LOCKED |
| ADR-005 | GLORYS as training/reference target | Accepted / LOCKED |
| ADR-006 | ARGO as independent validation | Accepted / LOCKED |
| ADR-007 | Temporal data split (no random split) | Accepted |
| ADR-008 | Regional MVP (Bay of Bengal / Arabian Sea) | Accepted |

## Status summary (from SYSTEM_MEMORY_DUMP.md §156)

| Item | Status |
|------|--------|
| Data provider | SELECTED — Copernicus Marine |
| API mechanism | SELECTED — Python Toolbox (`copernicusmarine`) |
| Authentication | ESTABLISHED — backend/server-side |
| MVP regions | SELECTED — Bay of Bengal, Arabian Sea |
| Surface inputs | LOCKED — 7 channels |
| Target | LOCKED — 15 depth temperatures |
| Grid / frequency | LOCKED — 0.25° × 0.25°, daily |
| Training target | SELECTED — GLORYS |
| Independent validation | SELECTED — ARGO |
| Model | BASELINE RECOMMENDED — CNN encoder–decoder |
| Advanced model | OPTIONAL — attention / ViT / depth conditioning |
| Uncertainty | OPTIONAL DIFFERENTIATOR |
| Frontend | RECOMMENDED — React + TypeScript + Vite |
| Backend | RECOMMENDED — FastAPI + Python |
| ML | RECOMMENDED — PyTorch + xarray + NumPy |
| Database | NOT LOCKED |
| Deployment | NOT LOCKED |
| Exact dataset IDs | MUST BE VERIFIED BEFORE DOWNLOAD (RULE 7) |
| Exact training period | MUST BE VERIFIED AFTER DATA COVERAGE MATRIX |
| Exact neural hyperparameters | MUST BE EXPERIMENTALLY SELECTED |

## How to add a decision

1. Create/update an ADR in `docs/02-architecture/architecture-decisions/`.
2. Update this index.
3. Do NOT silently rewrite `SYSTEM_MEMORY_DUMP.md` (it preserves history).