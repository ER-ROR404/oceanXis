# Data Flow

> Reference: SYSTEM_MEMORY_DUMP.md §55, §59, §85, §117.

## Training data flow

```text
Copernicus products (+ GLORYS target)
    ↓ subset(request region/date/vars)
raw NetCDF per variable
    ↓ QC, invalid-value removal, land/sea mask
    ↓ temporal alignment (daily convention)
    ↓ spatial regridding → 0.25° × 0.25°
    ↓ unit conversion
    ↓ missing-data mask
    ↓ normalize (TRAIN-ONLY statistics)   [RULE 11]
tensor sample:
    X = [7, H, W]
    Y = [15, H, W]
    mask = [H, W]
    metadata = {date, region, lat grid, lon grid, provenance}
    ↓
PyTorch Dataset → DataLoader → training
```

## Daily inference flow

```text
backend checks cache for (region, date, variable, dataset_version)
    ↓ hit → use cached; miss → Copernicus subset request → cache
harmonized daily inputs [1, 7, H, W]
    ↓ normalize (stored training statistics)
    ↓ model inference → [1, 15, H, W]
    ↓ denormalize → °C
    ↓ apply ocean mask
    ↓ save prediction raster + metadata
    ↓ expose via API (map, profile, prediction)
```

## Daily ingestion pipeline (operational, proposed)

```text
scheduler → check latest available date → identify missing inputs
    → fetch required regional products → cache raw
    → QC → harmonization → model inference
    → prediction validation checks → save prediction → update dashboard
```

## Provenance at every hop

Each hop records: `source_provider`, `product_id`, `dataset_id`, `dataset_version`, `variable`,
`source_resolution`, `target_resolution`, time convention, interpolation method, unit conversion,
normalization/preprocessing version (see `docs/04-data/data-provenance.md`).

## Cache policy

- Cache key: `region + variable + date + dataset_version`.
- Never re-request cached data (§60).
- Large datasets and checkpoints never enter Git (RULE 12/13).