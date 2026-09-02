# Depth Levels

> Canonical 15 output depths and ordering (LOCKED by problem statement).
> Source: SYSTEM_MEMORY_DUMP.md §15, §116; `config/depths.yaml`.

## Canonical depth order

```text
 0, 5, 10, 20, 30, 50, 75, 100, 125,
 150, 200, 300, 500, 700, 1000   (meters)
```

OUTPUT_CHANNELS = 15.

Do NOT reorder output channels (RULE 20, Golden Rule 18). The model output, evaluation tables, API
profiles, and frontend charts must all preserve this order.

## Purpose

Depth-wise skill assessment is a core deliverable:

```text
depth | RMSE | bias | correlation
```

## Expected behavior (to be measured, not assumed)

- Stronger skill near the surface (surface observations carry direct signal).
- Decreasing skill with depth (progressively weaker indirect information).
- Do NOT impose monotonic temperature assumptions in loss/regularization. Ocean temperature can
  change non-monotonically with depth (§24).

## Interpolation to standard depths

GLORYS (and ARGO when validating) provide their own vertical levels. Mapping to the 15 standard
depths uses documented interpolation (linear in depth for continuous temperature), recorded in
provenance (§40, §78).