# Preprocessing Pipeline

> Raw-to-model preprocessing stages.
> Source: SYSTEM_MEMORY_DUMP.md §55.

## Stages

```text
1. Retrieve region subset (Copernicus Toolbox, cache-first)
2. Open source NetCDF (xarray)
3. Quality control + invalid-value removal       (docs/04-data/quality-control.md)
4. Temporal alignment → daily convention         (docs/04-data/temporal-alignment.md)
5. Spatial regridding → 0.25° × 0.25°            (docs/04-data/regridding.md)
6. Land/sea masking                              (docs/04-data/quality-control.md)
7. Missing-data mask                             (docs/04-data/missing-data-policy.md)
8. Unit harmonization                            (docs/03-domain/units.md)
9. Normalization (TRAIN-ONLY statistics)         (RULE 11)
10. Tensor construction [7,H,W] + [15,H,W] + mask + metadata
```

## Output bundle (per sample)

- `X [7,H,W]` — normalized surface inputs
- `Y [15,H,W]` — temperature at 15 depths (GLORYS-derived)
- `mask [H,W]` — valid ocean cells
- metadata: date, region, lat/lon grids, provenance, preprocessing version

## Config

Preprocessing behavior is controlled by `config/preprocessing.yaml` (grid, interpolation methods,
QC thresholds, normalization version) — not hard-coded in code.

## Provenance

Every stage records its transformation in the provenance record
(`contracts/data/provenance.schema.json`), including interpolation method and unit conversions.