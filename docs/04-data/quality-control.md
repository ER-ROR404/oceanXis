# Quality Control

> Source QC, invalid-value handling, and ocean masking.
> Source: SYSTEM_MEMORY_DUMP.md §36, §37, §109, §111.

## QC stages

1. Use source-provided quality flags where available.
2. Remove invalid values (fill values, NaNs, physically impossible defaults).
3. Apply the **land/sea mask** consistently to all channels and the target.
4. Interpolate only where scientifically justified — never blindly across large gaps.

## Land/sea mask

- Single common ocean mask after regridding.
- Land excluded; coastal invalid cells handled consistently.
- Loss/metrics computed only over valid ocean cells (mask-respecting metric APIs).

## File-level validation (every downloaded file)

Check and report:

```text
variable, shape, units, min, max, missing_percent
expected variables, expected dimensions, coordinate names
time length, lat/lon range, NaN percentage, fill values
```

A validation report is produced per file; failures block promotion into the tensor pipeline.

## NaNs / fill values

- NaNs remain NaNs in masked-out cells (not zero-filled).
- Validity is tracked by the companion `mask` tensor (§36).