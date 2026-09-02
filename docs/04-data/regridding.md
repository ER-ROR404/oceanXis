# Regridding

> Spatial harmonization onto the 0.25° × 0.25° grid.
> Source: SYSTEM_MEMORY_DUMP.md §40, §107, §110.

## Policy

- Source products differ in native resolution (~0.05° SST, ~0.083° GLORYS, 0.25° products, etc.).
- Target grid is always the official **0.25° × 0.25°** grid for the selected region (LOCKED).
- Method per variable is documented in `config/preprocessing.yaml` and provenance:
  - continuous gridded fields (SST, SSH, temperature target): interpolate to 0.25° centers
    (bilinear on lat/lon) —
  - categorical/mask fields: nearest-neighbor.
  - Interpolation of **large missing ocean areas** is not performed blindly (A9 / §109).

## Alignment invariants

- All input channels share identical latitude/longitude grids (same H/W).
- Target shares the same H/W as the inputs.
- Latitude orientation normalized (ascending vs descending arrays §110).

## Edge cases

- Longitude wraparound (domain crossing convention boundary).
- Coastline/coastal invalid cells.
- Sparse salinity swaths and missing satellite swaths.
- Duplicated time coordinates, masked arrays, NaN vs fill values.

Each is resolved explicitly in preprocessing; do not rely on silent array alignment (§107).
Document the longitude convention once (choose 0–360 or –180–180 internally; never mix (§108)).