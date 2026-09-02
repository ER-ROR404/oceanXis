# backend/

**OceanEmbed application backend — FastAPI orchestration layer.**

- Serves the HTTP API (`/api/v1`) to the frontend.
- Is the **only** component that talks to Copernicus (RULE 1–2); credentials stay server-side.
- Descends fetched ocean data into model-ready, harmonized inputs; performs inference; returns
  profiles/maps conforming to `contracts/api/*` (RULE 6).
- **Never contains model-training code** (RULE 3). Training lives in `ml/`.

## Layout

```text
app/
  main.py                  FastAPI app construction
  api/                     routers (v1: health, metadata, ocean, profiles, predictions, model)
  schemas/                 Pydantic request/response models (mirror contracts/)
  services/                ingestion, preprocessing, inference, profile, prediction, validation, cache
  integrations/
    copernicus/            ONLY place that knows Copernicus Toolbox details
    argo/                  independent-validation data (RULE 9)
    storage/               object/NetCDF storage access
  domain/                  regions, variables, depths, units (from config/)
  database/                SQLAlchemy session + ORM models (metadata/state, not big tensors)
  core/                    config, logging, security, telemetry
  workers/                 async ingestion/inference/validation jobs
tests/                     unit/, integration/, api/ (~80% coverage gate)
```

## Environment

`backend/pyproject.toml` — FastAPI/Pydantic/SQLAlchemy/Copernicus/xarray. See
`../docs/07-operations/local-development.md` and `../AGENTS.md` (environment isolation).

## Rules

- Responses must conform to `contracts/api/*.schema.json` (RULE 6).
- Dataset IDs are verified, never hard-coded (RULE 7, `config/datasets.yaml`).
- No training stack here (RULE 3).

> **Pre-build stage:** structure is in place; implementation lands in the coding phase
> (start with the Copernicus one-day regional proof).