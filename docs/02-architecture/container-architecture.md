# Container Architecture

> Reference: SYSTEM_MEMORY_DUMP.md §61, §150.

## Containers (target)

| Container | Technology | Responsibilities |
|-----------|-----------|------------------|
| `frontend` | React + TypeScript + Vite | Region/date/depth selectors, temperature map, click-to-profile, validation panels |
| `backend` | FastAPI (Python) | Validation, region mapping, auth-boundary enforcement, caching, Copernicus service, preprocessing, ML inference calls, prediction store, health |
| `ml-inference` | PyTorch serving runtime | Load approved checkpoint → predict `[B,15,H,W]` → denormalize → mask |
| `database` | PostgreSQL | Metadata + application state (dataset registry, ingestion jobs, predictions, model registry) |
| object storage | Filesystem/object store | NetCDF/Zarr raw + processed + prediction rasters + checkpoints (outside Git) |

## External systems

- Copernicus Marine (Toolbox: `login`, `describe`, `subset`, `get`) — accessed **only** via the backend integration layer.
- GLORYS / ARGO — target and independent-validation data planes (data engineering layer).

## Architecture flow

```text
               ┌──────────────────────┐
               │     Frontend         │   React + TypeScript
               └──────────┬───────────┘
                          │ HTTPS/JSON (contracts/api/openapi.yaml)
                          ▼
               ┌──────────────────────┐
               │      FastAPI         │   Application Backend
               └──────────┬───────────┘
            ┌─────────────┴──────────────┐
            │                            │
            ▼                            ▼
   ┌────────────────┐          ┌──────────────────┐
   │   Storage /    │          │ ML Inference     │   ml-inference container
   │  DB + Objects  │          │ Service          │
   └────────────────┘          └────────┬─────────┘
                                        │
                                        ▼
                               ┌─────────────────┐
                               │ Model Registry  │   registry.yaml + artifact store
                               └─────────────────┘
```

## Data plane

```text
Copernicus → Data Engineering → Object Storage → Training Dataset
        → Cloud/GPU Training → Evaluation → Model Registry
        → Approved Model → Inference Service
```

## Deployment topology (MVP)

For the 36-hour MVP, a single host + `docker-compose` is sufficient:

- `backend` + `ml-inference` as Python processes or two containers.
- `database`: SQLite acceptable for MVP; PostgreSQL for multi-service (see `config/environments/`).
- `frontend`: dev server (Vite) or static build served by a lightweight web server.
- No Kubernetes for the MVP (RULE 18). `infrastructure/kubernetes/` exists only for the
  production-grade target architecture.