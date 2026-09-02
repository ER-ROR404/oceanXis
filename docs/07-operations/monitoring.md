# Monitoring

> Application, data, and model monitoring.
> See also `docs/02-architecture/observability-architecture.md` and `observability/`.

## Application / API

- Health endpoint (`/api/health`): alive, model loaded, cache accessible.
- Request latency, error rate, unknown-error rate.

## Data / ingestion

- Latest available date per region/variable (data freshness).
- Ingestion success/failure, bytes fetched, cache hit rate.
- Missing channels / masked-out fractions.

## Model / inference

- Inference latency, model version served.
- Invalid-output rate (NaN / non-finite / mask violations) — at minimum sanity checks (§125).
- Depth-wise skill on the latest evaluation (RMSE/bias/correlation) — for reporting, not live alerting only.

## Alerts (observability/alerts/)

- `backend.yml` — service down, high error rate.
- `ingestion.yml` — stale data, repeated failures, cache miss spikes.
- `ml.yml` — inference failures, invalid-output anomaly.

## Demo resilience

Monitoring also enforces the golden rule: never display fabricated values — degraded states are
**visible and reported** (§120, §122).