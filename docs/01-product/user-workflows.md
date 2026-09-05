# User Workflows

> Updated per ADR-011: 3-Mode product vision (Map + Profile + Validation).
> See `product-vision.md` for the full No.1 strategy.

Primary user mode is **region-first**, exploration-driven, scientific.

## Mode 1 — Spatial Map Mode (🌊)

See `product-vision.md` for full specification.

1. User opens OceanEmbed.
2. User selects region: Bay of Bengal or Arabian Sea.
3. User selects a date.
4. System retrieves or loads processed daily data for that region/date.
5. System displays a map of the region.
6. User selects a depth (one of the 15 standard depths).
7. Map displays **predicted temperature at that depth**.
8. User changes depth with a slider/dropdown → map refreshes.
9. **UPGRADED:** User can switch view between Temperature / Confidence / Prediction Error.

## Mode 2 — Vertical Profile Mode (📈)

See `product-vision.md` for full specification.

1. From the map, user clicks a 0.25° grid cell.
2. System displays:
   - Coordinates (latitude/longitude)
   - Date
   - Observed surface temperature (input)
   - Predicted temperature profile at the 15 standard depths
   - **Where ARGO exists: side-by-side comparison table**
   - **Per-profile RMSE / bias / correlation**
   - Uncertainty interval per depth
3. Present as a depth vs temperature table and/or chart.

## Mode 3 — Scientific Validation Mode (🔬) — Judge-Facing

See `product-vision.md` for full specification.

1. Judge selects Date → Region → Depth.
2. System displays:
   - Overall RMSE / Bias / Correlation summary
   - ARGO coverage indicator
   - Spatial Prediction Error Map (green/yellow/red)
3. This answers: "How do you know your model is actually correct?"

## Judge/demo sequence (9 steps, per ADR-011)

1. Open OceanEmbed.
2. Select Bay of Bengal.
3. Select date.
4. Show 7 surface input channels (real data exists).
5. AI reconstruction → 0.25° depth map (Mode 1).
6. Click a grid cell → 15-depth profile (Mode 2).
7. Prediction vs ARGO comparison (independent validation).
8. RMSE / Bias / Correlation.
9. Confidence / uncertainty map + Scientific Validation Mode (Mode 3).

## Explicitly NOT in the user workflow

- Users do NOT upload satellite images, ARGO files, NetCDF files, or model files.
- Users do NOT provide Copernicus credentials — the backend handles access.