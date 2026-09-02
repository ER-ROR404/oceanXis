# database/

**OceanEmbed database — Alembic migrations + seed data.**

Stores **metadata and application state only** (dataset registry, ingestion jobs, predictions,
model registry, jobs). Large ocean tensors / checkpoints live in object storage, not here.

## Migrations

```text
migrations/versions/
  0001_initial_schema.py
  0002_dataset_registry.py
  0003_ingestion_jobs.py
  0004_prediction_registry.py
  0005_model_registry.py
```

- Applied migrations are **never edited** (RULE 15). Add `0006_<change>.py` instead.
- `env.py` connects Alembic to the backend's SQLAlchemy metadata.

## Seeds

```text
seed/seed_regions.py      canonical regions (config/regions.yaml)
seed/seed_depths.py       canonical 15 depths (config/depths.yaml)
seed/seed_variables.py    canonical 7 input variables (config/variables.yaml)
```

Seeds must match the canonical config so DB state can never drift from contracts.

## Target DB

PostgreSQL for staging/production; SQLite (local/test). See `config/environments/*.yaml`.

> **Pre-build stage:** policy documented; migrations/seed code land with the backend in the coding phase.