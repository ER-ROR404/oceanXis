# User Workflows

Primary user mode is **region-first**, exploration-driven, scientific.

## Workflow 1 — Regional subsurface temperature map

1. User opens OceanEmbed.
2. User selects region: Bay of Bengal or Arabian Sea.
3. User selects a date.
4. System retrieves or loads processed daily data for that region/date.
5. System displays a map of the region (surface state / data status).
6. User selects a depth (one of the 15 standard depths).
7. Map displays **predicted temperature at that depth**.
8. User changes depth with a slider/dropdown → map refreshes.

Example:
```
Region:    Bay of Bengal
Date:      YYYY-MM-DD
Depth:     100 m
Result:    predicted temperature map
```

## Workflow 2 — Grid-cell drill-down (vertical profile)

1. From the map, user clicks a 0.25° grid cell.
2. System displays:
   - Coordinates (latitude/longitude)
   - Date
   - Predicted temperature profile at the 15 standard depths
   - Surface input values at the cell
   - Uncertainty (where implemented)
   - Optional independent ARGO observation if available (never fabricated)
3. Present as a depth vs temperature table and/or chart.

Conceptual output:
```
Depth       Temperature       Uncertainty
-------------------------------------------
0 m         xx.x °C           ±x.x
5 m         xx.x °C           ±x.x
...
1000 m      xx.x °C           ±x.x
```

## Workflow 3 — Validation / comparison view (proposed)

1. User inspects model metadata and evaluation summary.
2. Depth-wise RMSE / bias / correlation displayed (from the latest evaluation report).
3. Prediction vs GLORYS profile where available; prediction vs ARGO profile where independent
   observations exist.

## Judge/demo sequence (recommended)

1. Open OceanEmbed.
2. Select Bay of Bengal.
3. Select date.
4. Display surface/data status.
5. Select depth = 100 m → predicted temperature map.
6. Click a grid cell → full 15-depth profile.
7. Show uncertainty (if implemented).
8. Show ARGO validation where available.
9. Show RMSE/correlation summary.
10. Explain surface observations → embedding → reconstruction.
11. Explain operational relevance (subsurface ocean intelligence layer).

## Explicitly NOT in the user workflow

- Users do NOT upload satellite images, ARGO files, NetCDF files, or model files.
- Users do NOT provide Copernicus credentials — the backend handles access.