# Deployment Architecture

> Describes how OceanEmbed is deployed across environments.
> **Deployment provider is NOT LOCKED** (SYSTEM_MEMORY_DUMP.md §148). Everything here is PROPOSED.

## Environments

| Environment | Purpose | Stack |
|-------------|---------|-------|
| `local` | Developer workstation; full pipeline proof | `docker-compose.yml` + `docker-compose.dev.yml`, SQLite or local PostgreSQL |
| `test` | CI integration tests | isolated `docker-compose.test.yml`, ephemeral PostgreSQL |
| `staging` | Pre-release validation | hosted backend + ml-inference + frontend + managed DB (target `PROPOSED`) |
| `production` | Post-hackathon target (not MVP) | managed infrastructure (target `PROPOSED`) |

## MVP deployment (36-hour)

1. Data engineering runs offline: downloads regional daily data via Copernicus Toolbox, harmonizes
   to `[7,H,W]` tensors, saves to object storage.
2. Training runs (local or GPU box/cloud): CNN baseline → checkpoint + manifest → model registry.
3. Backend exposes API; ml-inference serves the approved checkpoint.
4. Frontend (static build) talks only to the backend.
5. Fallback: cached verified data + cached predictions guarantee the demo runs even if Copernicus is
   unreachable.

## Production target (not MVP)

- Containerized services behind a reverse proxy / ingress.
- Managed PostgreSQL; object storage for rasters/checkpoints.
- Secrets via managed secret store (never env-dumped secrets in image layers).
- Infrastructure-as-Code skeletons: `infrastructure/terraform/`, `infrastructure/kubernetes/`
  (only if an architectural reason emerges — RULE 18 `UNRESOLVED`).

## Health / readiness

- `GET /api/health` verifies: API process alive, model loaded, data cache accessible.
- Health checks must NOT trigger Copernicus downloads or other expensive external calls.
- `docker compose` services define `healthcheck` gates (see `docker-compose.yml`).

## Credentials

- Copernicus credentials supplied via server-side env vars / secret manager only.
- `config/environments/*.yaml` hold non-secret references; real secrets never enter config files.