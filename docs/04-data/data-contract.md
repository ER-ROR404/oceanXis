# Data Contract

> Formal structure of harmonized ocean data feeding the ML pipeline.
> Source: SYSTEM_MEMORY_DUMP.md §112; JSON schemas in `contracts/data/`.

## Sample contract

One training/inference sample:

```text
X:  float32 array, shape [7, H, W]        — normalized surface inputs (channel order fixed)
Y:  float32 array, shape [15, H, W]       — temperature target at 15 depths (order fixed)
mask: [H, W]                               — valid-ocean-cell boolean
metadata: {date, region, latitude_grid, longitude_grid, provenance...}
```

## Tensor invariants

- dtype float32 for model tensors.
- H/W identical across X and Y (same 0.25° grid).
- NaN handling via the validity `mask`; NaNs in tensor cells outside the mask are expected and
  masked in loss/metrics.
- Channel order: SST, SSS, SSH/SLA, current U, current V, wind U, wind V (LOCKED).
- Depth order: 0, 5, 10, 20, 30, 50, 75, 100, 125, 150, 200, 300, 500, 700, 1000 (LOCKED).

## Files

- `contracts/data/surface-input.schema.json` — the seven-channel input.
- `contracts/data/training-sample.schema.json` — X/Y/mask/metadata bundle.
- `contracts/data/dataset-metadata.schema.json` — registry entries.
- `contracts/data/provenance.schema.json` — lineage records.

## Verification

`scripts/verify-contracts.py` validates configs/manifests/samples against these schemas in CI.
Fixtures: small synthetic `tests/fixtures/` allow contract tests without Copernicus access.