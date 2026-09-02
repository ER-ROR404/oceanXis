# Observability Architecture

> Reference: SYSTEM_MEMORY_DUMP.md §121–§123.

## Principles

- **Log** operational context, not secrets.
- **Health checks** must be cheap (no external downloads).
- ML/data observability matters as much as application observability for a scientific product.

## What to log

Per ingestion/inference operation:

```text
ingestion start/end, dataset ID, date, region, bytes/files
preprocessing time, inference time, model version, errors
```

Never log: passwords, tokens, credentials (§121).

## Health endpoints

- `GET /api/health` — API process alive, model loaded, data cache accessible.
- Optional: Copernicus connectivity probe — must not trigger expensive data downloads (§123).

## Signals

| Area | Metrics (target) |
|------|------------------|
| Backend | request latency, error rate, health status |
| Ingestion | success/failure count, data freshness (latest available date), bytes fetched, cache hits |
| ML inference | inference latency, model version served, NaN/invalid-output rate, prediction timestamps |

## Dashboards / alerts

- `observability/grafana/dashboards/`: backend, ingestion, ml-inference.
- `observability/alerts/`: backend, ingestion, ml.
- `observability/prometheus/prometheus.yml`: scrape configuration (target).

## Demo resilience

The primary "observability" requirement for the hackathon is that live-app failures are visible and
the demo degrades gracefully to cached data (§120, §122):

- Copernicus unavailable → serve cached latest data; mark as cached.
- Variable unavailable → mark channel unavailable; never zero-fill silently.
- Model inference fails → clear error; never display fabricated scientific values.