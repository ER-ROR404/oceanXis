# Evaluation Policy

> RMSE, bias, correlation, depth-wise, spatial, and ARGO evaluation.
> Source: SYSTEM_MEMORY_DUMP.md §27–§34, §91, §128.

## Required metrics (LOCKED)

| Metric | Formula |
|--------|---------|
| RMSE | sqrt(mean((pred − target)²)) |
| Bias | mean(pred − target) |
| Correlation | Pearson correlation |

All computed per depth (15 rows) and optionally aggregated. Spatial/averaged RMSE is supplementary.

## Depth-wise evaluation (LOCKED)

Produce:

```text
depth | RMSE | bias | correlation
```

Expected behavior (to be measured, not assumed): stronger skill near surface, decreasing with depth.

## Model comparison (scientific credibility, required)

At minimum:

| Model | Purpose |
|-------|---------|
| Baseline A: climatology (mean depth profile) | Naïve reference |
| Baseline B: simple CNN | Simple learned baseline |
| Model C: OceanEmbed encoder–decoder | Candidate system |

Claiming improvement without this comparison is rejected (§30).

## Spatial evaluation (optional, valuable)

Regional RMSE / bias / correlation by region / depth; spatial error maps. Help locate
where model performs well or poorly (§29).

## ARGO validation (LOCKED as independent)

Predictions vs ARGO profiles by date/location, interpolated to the 15 standard depths. Never
fabricated — if no ARGO match exists for a cell, report none (Golden Rules 4, 21; §32, §95).

## Generalization tests

- Unseen dates (temporal holdout — primary).
- Spatial holdout (optional; train on BoB, test on AS — §90).
- Independent ARGO profiles (primary external-observation check — §128).