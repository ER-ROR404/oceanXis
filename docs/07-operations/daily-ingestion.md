# Daily Ingestion

> Daily data-ingestion operations and recovery behavior.
> Source: SYSTEM_MEMORY_DUMP.md §49, §59–§60.

## Pipeline (operational, proposed)

```text
scheduler → check latest available date
    → identify missing inputs
    → fetch required regional products (cache-first)   [§60]
    → cache raw data
    → QC → harmonization (§55)
    → model inference
    → prediction validation checks
    → save prediction
    → update dashboard
```

## Cache policy

- Cache key: `region + variable + date + dataset_version`.
- Do not re-request cached data.
- Cache raw + harmonized tensors + prediction rasters outside Git (RULE 12).

## Chunking (historical)

- Split requests by variable/day/month/year where helpful (`subset_split_on`) — §57.
- Regional subsetting keeps volume tractable (ADR-008).

## Freshness & latency

- Do not claim "real-time" without verification (§50, §129).
- Wording: "latest available daily ocean observations."

## Recovery

- If Copernicus unavailable → serve cached latest data (marked cached).
- If a variable unavailable → mark channel unavailable; never zero-fill (§122).
- Health checks don't trigger expensive downloads (§123).
- Fallback demo dataset guarantees the demo survives ingestion failures (§120).