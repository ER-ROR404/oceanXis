# observability/

**OceanEmbed observability — metrics, dashboards, alerts.**

```text
prometheus/prometheus.yml        metric collection
grafana/dashboards/              backend, ingestion, ml-inference
grafana/provisioning/            automated dashboard provisioning
alerts/                          backend, ingestion, ml
```

Covers application, data-ingestion, and model-serving health. Architecture:
`docs/02-architecture/observability-architecture.md`; operations: `docs/07-operations/monitoring.md`.

> **Pre-build stage:** scaffolding. Enable for local dev / steer to cloud per deployment phase.