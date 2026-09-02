# ML Serving Flow

> Runtime inference path from API request to model response.
> Reference: SYSTEM_MEMORY_DUMP.md §117, §145.

## Request path (per day/region)

```text
Frontend (region, date, depth[, grid cell])
    ↓
GET /api/ocean/map  |  GET /api/ocean/profile
    ↓
FastAPI: validate region/date
    ↓
Preprocessing service: load harmonized daily inputs
    ↓ regenerate/normalize → tensor [1, 7, H, W]   (float32)
    ↓
ML inference service
    ↓
model(predict): [1, 7, H, W] → [1, 15, H, W]        (float32)
    ↓ optional uncertainty head → [1, 15, H, W]
    ↓
postprocess: denormalize (°C), apply ocean mask,
             sanity checks (finite, no NaN, mask respected)
    ↓
response conforms to contracts/api/*.schema.json
    ↓
Frontend renders map / 15-depth profile / uncertainty / validation
```

## Serving contract

Input: `float32 [B, 7, H, W]` — canonical channel order (SST, SSS, SSH/SLA, current U, current V,
wind U, wind V).

Output: `float32 [B, 15, H, W]` — canonical depth order
`0, 5, 10, 20, 30, 50, 75, 100, 125, 150, 200, 300, 500, 700, 1000`.

Optional uncertainty: `float32 [B, 15, H, W]` (non-negative variance).

## Important serving rules

- Inference consumes the canonical model-input contract (RULE 5).
- GLORYS/ARGO subsurface data is never an inference input (RULE 8/9).
- Depth ordering preserved exactly (Golden Rule 18).
- No fabrication: if inference fails, return a clear error — never fake values (§122).
- Model version + preprocessing/normalization version returned with predictions (§79).

## Profile extraction

`profile(latitude, longitude)`:

1. Nearest valid grid cell on the 0.25° grid inside the region.
2. Extract the 15-depth column from the prediction tensor.
3. Optionally match a nearby independent ARGO profile (interpolated to the 15 depths) for display —
   marked clearly as independent observation.