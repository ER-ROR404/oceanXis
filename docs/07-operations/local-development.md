# Local Development

> Reproducible developer workstation setup.

## Prerequisites

- Python 3.11 (`.python-version`), `uv` (or `pip` + venv).
- Node 20 (frontend), `docker`/`docker compose` (optional, for stack).

## Setup

```bash
# 1. environments + shared tooling
uv venv .venv
. .venv/bin/activate
uv pip install -e .            # shared lint/test tooling only

# 2. module environments (isolated per AGENTS.md)
uv pip install -e backend
uv pip install -e ml
uv pip install -e data-engineering

# 3. environment variables
cp .env.example .env            # then fill placeholders (never commit .env)

# 4. verify environment
make verify-env
```

## Frontend

```bash
cd frontend
npm install
npm run dev                     # http://localhost:5173
```

## Backend (dev, hot reload)

```bash
. .venv/bin/activate
uvicorn app.main:app --app-dir backend --reload
```

## Tests / lint

```bash
make lint          # ruff check + format check
make test          # pytest (backend + ml + data-engineering)
make verify-contracts
```

## Docker stack

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

## Copernicus authentication (backend-only)

```bash
copernicusmarine login          # interactive; or set env vars below in .env
# COPERNICUSMARINE_SERVICE_USERNAME / COPERNICUSMARINE_SERVICE_PASSWORD
```

See `docs/07-operations/training-operations.md` / `data-engineering/scripts/` for the pipeline
entry points (Copernicus connection proof runs first — `docs/01-product/acceptance-criteria.md`).