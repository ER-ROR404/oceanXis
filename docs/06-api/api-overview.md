# API Overview

> Backend API architecture and endpoint organization.
> Authoritative contract: `contracts/api/openapi.yaml`.

## Architecture

- FastAPI backend, prefix `/api`, versioned under `/api/v1`.
- Pydantic request/response models in `backend/app/schemas/` mirror `contracts/api/*.schema.json`.
- Responses conform to `contracts/` (RULE 6).

## Endpoint groups

| Group | Purpose |
|-------|---------|
| `/api/health` | Service health (cheap; model-loaded + cache-accessible check) |
| `/api/metadata` | Dataset/model/application metadata |
| `/api/ocean` | Ocean map/data endpoints |
| `/api/profiles` | Grid-cell vertical profile endpoints |
| `/api/predictions` | Prediction retrieval (map + profile payloads) |
| `/api/model` | Model version and status |

## Conceptual endpoints (exact names not locked — §63)

```text
GET /api/ocean/history?region=...&start_date=...&end_date=...
GET /api/ocean/map?region=...&date=...&depth=...
GET /api/ocean/profile?region=...&date=...&latitude=...&longitude=...
GET /api/ocean/metadata
GET /api/ocean/health
GET /api/model/version
```

## Key behaviors

- Region/date/depth/grid-cell validated (invalid → standardized error).
- Credentials never exposed in responses; internal dataset IDs not leaked (§64).
- Cached data preferred; Copernicus only via backend integration layer.