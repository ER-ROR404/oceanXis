# data-engineering/

**OceanEmbed data acquisition and harmonization.**

Responsibility: **acquire and transform trustworthy data — do NOT train models.**

```text
Copernicus → discover/verify → subset (region/date) → harmonize → validate → provenance/manifest
```

## Layout

```text
src/oceanembed_data/
  catalog.py       verified external dataset metadata (RULE 7)
  copernicus.py    Copernicus Toolbox ingestion (the only place that knows it)
  regions.py       regional extraction (config/regions.yaml)
  downloads.py     resilient download/retry
  harmonization.py harmonize products onto the 0.25° grid + canonical order
  validation.py    dataset integrity checks
  provenance.py    lineage records (contracts/data/provenance.schema.json)
scripts/           discover, verify, download_region, download_historical,
                   build_training_dataset, validate_dataset, generate_manifest, verify_datasets
tests/
```

## Rules

- Dataset IDs verified via `describe()` (RULE 7); never guessed. Update `config/datasets.yaml` +
  `docs/04-data/dataset-registry.md` together.
- Preserve channel/depth ordering (Golden 17–18); preserve provenance (Golden 16).
- One-day regional test before mass downloads (Golden 10).
- Never commit large datasets (RULE 12).
- GLORYS = target; ARGO = independent validation only (RULE 8–9).

## Environment

`data-engineering/pyproject.toml` — Copernicus/xarray/provenance tooling.

> **Pre-build stage:** structure is in place. First coding task = Copernicus one-day regional proof.