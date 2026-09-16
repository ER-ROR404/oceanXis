# Demo Feature Audit — OceanEmbed (SIH26066)

> **Audited 2026-09-16 against the running stack** (ML inference `:8080`, backend `:8000`,
> frontend `:5173`) **and the repository source**. Every entry below was either observed in
> the browser or read in the deployed code path. Nothing was invented, and nothing that
> failed inspection is listed as working.
>
> Evidence tags: `LIVE-API` = HTTP response observed, `LIVE-UI` = Playwright observation on
> `localhost:5173`, `CODE` = deployed source file, `ASSET` = committed data file.
>
> **Product statement that survives the audit:** OceanEmbed reconstructs historical
> (2022-01-01 → 2023-12-31) subsurface temperature at 15 depths for the **Bay of Bengal**,
> from 7 surface channels, with a per-cell ±1σ model uncertainty — validated against
> independent ARGO floats. It is a **reconstruction, not a forecast and not real-time**.

---

## 1. Verified system state

| Service | Where | Status | Evidence |
|---|---|---|---|
| ML inference | `ml/src/oceanembed/serving/server.py` (`:8080`) | healthy, model loaded | `LIVE-API` `GET /health` → `model: hybrid_v1`, `status: ok` |
| Backend API | `backend/app/main.py` (`:8000`) | `model_loaded: ok`, `cache_accessible: ok`, `database: degraded` | `LIVE-API` `GET /api/v1/health` — DB degraded is the expected local-demo state (no Postgres); it does not affect any demoed feature |
| Frontend | `frontend/` (Vite `:5173`) | running, no console errors | `LIVE-UI` full walkthrough: 0 console errors, 0 page errors |
| Checkpoint | `data/checkpoints/hybrid_v1/best.pt` | epoch 83, val_loss 0.3714623343872113 | `LIVE-API` `/availability` checkpoint block; shown in the UI provenance panel |
| Tensor store | `data/tensors/bay_of_bengal/` | 730 daily dates 2022-01-01 → 2023-12-31 | `CODE` `InferenceService.available_dates()`; `LIVE-API` availability dates |

**Model served — `hybrid_v1`:**

```
OceanEmbedNet  =  multi-scale CNN encoder (Conv2d 7→32→64→128)
               →  ConvLSTM temporal encoder (hidden 128, 1 layer)
               →  depth decoder with mu_head + log_var_head
               →  [B, 15, H, W] temperature + raw log-variance
```
`CODE` `ml/src/oceanembed/models/reconstruction_net.py`, `ml/src/oceanembed/serving/service.py`.

- In → out: **7 channels → 15 depths** (`CODE` `ml/configs/hybrid_v1.yaml`: `in_channels: 7`,
  `out_channels: 15`; both marked LOCKED).
- Deployed temporal window: **T = 7 days** (`CODE` `service.py` `TEMPORAL_WINDOW = 7`;
  `ml/configs/hybrid_v1.yaml` `data.temporal_window: 7`). The inference call builds a
  `[1, 7, 7, H, W]` window and calls `model(x)`.
- **Honesty note (do not oversell):** the architecture contains optional seasonal/spatial
  coordinate encoders (`use_seasonal`/`use_spatial: true` in config), but the trained
  call sites never feed coordinates — `CODE` `service.py` module docstring and
  `trainer.py`/`evaluation/argo.py` call sites. The UI correctly says only
  **"CNN + ConvLSTM"**. Do not claim day-of-year or coordinate conditioning.
- Uncertainty: `sigma = sqrt(exp(log_var))`, public wire field only (raw `log_var` never
  leaves the ML service) — `CODE` `backend/app/api/v1/envelope.py`, `ASSET`/`CODE` schema
  `contracts/api/ocean-profile.schema.json`.

## 2. Verified data surface (what the demo may show)

| Fact | Value | Evidence |
|---|---|---|
| Region actually served | **Bay of Bengal only** | `LIVE-API` `/availability`: `bay_of_bengal: available`; `arabian_sea` & `north_indian_ocean`: `no_data`; `LIVE-API` `/ocean/metadata` `regions: ["bay_of_bengal"]` |
| Served dates | **730 daily, 2022-01-01 → 2023-12-31** | `LIVE-API` availability (`date_start`/`date_end`) |
| Date the UI opens on | **2023-09-01** | `LIVE-UI` date select value; `CODE` `useOceanExplorer` picks the first available date ≥ 2023-09-01 |
| Grid | **0.25°, daily, 69 lat × 81 lon**, lat 5.0→22.0, lon 80.0→100.0 | `LIVE-API` map payload; UI subtitle "Bay of Bengal · 0.25° reconstruction grid" |
| Valid ocean cells | **3,841 of 5,589** (land/masked = transparent, never 0.0) | `LIVE-API` map payload cell count; UI stats line "3,841 valid ocean cells" |
| 2023-09-01 @ 100 m temperature range | **18.0 – 28.1 °C** (legend min/mid/max `18.0 23.1 28.1 °C`) | `LIVE-UI` legend; `LIVE-API` payload |
| 2023-09-01 @ 75 m ±1σ range | **1.0 – 4.4 °C** (legend `1.0 2.7 4.4 ±1σ · °C`) | `LIVE-UI` legend |
| Offline fallback | pre-built demo cache, **31 weekly dates 2023-06-01 → 2023-12-28**, banner becomes `Demo data` | `ASSET` `artifacts/demo_cache/manifest.json` (`n_dates: 31`, `step_days: 7`); `CODE` `StatusBanner` copy |
| Training target | **GLORYS12v1 reanalysis** | `LIVE-API` map/profile metadata `data_source` |
| Training cutoff | **2023-12-31** | `LIVE-API` `/ocean/metadata` `data_freshness`; footer copy |
| Independent validation | **ARGO**, window 2023-08-10 → 2023-12-31, never used for training | `ASSET` `frontend/src/assets/validation/argo_validation_summary.json`; `CODE` no ARGO reference in the training/data pipeline |

## 3. Feature → Problem map (verified features only)

Legend: **P0** = must show in the 60 s video · **P1** = show if time / use as fallback ·
**P2** = do not show.

### F1 — Subsurface temperature map (Temperature layer) — **P0**

- **What the user sees:** a dark basemap of the Bay of Bengal with a teal temperature field painted per 0.25° ocean cell; land stays transparent so the coastline shows through.
- **Purpose:** make the reconstruction spatial — one whole region, one depth, one date.
- **PROBLEM CONNECTION:** SIH26066 asks for subsurface temperature over a region, not a single point; satellites give the surface only.
- **DEMO ACTION:** land on the Explorer (defaults already correct) and let the map render.
- **WHAT PRESENTER SHOULD SAY:** "This is the Bay of Bengal — every one of these 0.25° cells is a full temperature profile, and this map is the 100 metre slice."
- **JUDGE TAKEAWAY:** A complete regional subsurface field is reconstructed, not a hand-picked point.
- **Evidence:** `LIVE-UI` (map rendered, 3,841 cells); `CODE` `map/OceanMap.tsx` + `CellCanvasLayer.tsx`.

### F2 — Depth rail: 15 model levels, 0–1000 m — **P0**

- **What the user sees:** a vertical rail of buttons labelled `Surface 5 10 20 30 50 75 100 125 150 200 300 500 700 1000`; the active slice is highlighted.
- **Purpose:** inspect the reconstruction at any standard depth.
- **PROBLEM CONNECTION:** the deliverable is a *subsurface* product across 15 standard depths — this is the depth axis of the problem statement.
- **DEMO ACTION:** click `500 m` (dramatic colour change), then `75 m` during the uncertainty beat.
- **WHAT PRESENTER SHOULD SAY:** "We can move through the water column — this is 500 metres, deep water."
- **JUDGE TAKEAWAY:** OceanEmbed genuinely reconstructs depth, level by level, not just a surface field.
- **Evidence:** `LIVE-UI` rail labels + map recolour + stats line change; `LIVE-API` per-depth payloads (100 m T 18.0–28.1 °C vs 500 m T 7.3–10.5 °C); `CODE` `controls/DepthRail.tsx`.

### F3 — Region selector — **P1** (present, do not click)

- **What the user sees:** a `Region` select with Bay of Bengal / Arabian Sea / North Indian Ocean (only Bay of Bengal is served).
- **Purpose:** scope the product to a region.
- **PROBLEM CONNECTION:** the PoC region of SIH26066 is the Bay of Bengal (Arabian Sea planned).
- **DEMO ACTION:** **do nothing** — the default is `bay_of_bengal`. Do not select the other two (they render an honest "No data available" state).
- **WHAT PRESENTER SHOULD SAY:** *(if asked)* "We ship the Bay of Bengal model today; the other regions are declared but not trained yet."
- **JUDGE TAKEAWAY:** The scope claim matches what actually runs.
- **Evidence:** `LIVE-API` availability (`no_data` for the other regions); `LIVE-UI` select; `CODE` `controlPanel.tsx`.

### F4 — Date stepper (730 available dates) — **P1**

- **What the user sees:** `◀ 2023-09-01 ▶` with a dropdown listing the real availability list; the footer chip reads "Bay of Bengal · 2022-01-01 → 2023-12-31".
- **Purpose:** pick the reconstruction day.
- **PROBLEM CONNECTION:** the problem is about reconstructing *daily* subsurface state; this shows the temporal coverage is real.
- **DEMO ACTION:** leave it on **2023-09-01** (the default). Optionally one click of `◀` to prove it responds.
- **WHAT PRESENTER SHOULD SAY:** "Two years of daily reconstructions are served — this is 1 September 2023."
- **JUDGE TAKEAWAY:** Coverage is daily and continuous, not a single showcase date.
- **Evidence:** `LIVE-UI` select value + availability chip; `LIVE-API` 730 dates; `CODE` `controls/DateBar.tsx`.

### F5 — ±1σ uncertainty layer — **P0** (differentiator, and the honesty test)

- **What the user sees:** the same map recoloured on a dedicated uncertainty scale, legend reading e.g. `1.0 2.7 4.4 ±1σ · °C`.
- **Purpose:** expose the model's own confidence per cell rather than a bare number.
- **PROBLEM CONNECTION:** any operational subsurface product needs an uncertainty estimate; SIH26066 expects a trustworthy product, not a single point guess.
- **DEMO ACTION:** click `75 m`, then the `Uncertainty` button; say the line, then return to `Temperature`.
- **WHAT PRESENTER SHOULD SAY:** "Alongside every reconstruction the model estimates its own uncertainty — this is ±1σ, an uncalibrated model estimate, not a 95% confidence claim."
- **JUDGE TAKEAWAY:** The team understands and discloses uncertainty honestly.
- **Evidence:** `LIVE-UI` layer toggle + legend (`LIVE-API` σ per depth); `CODE` `MapColorbar.tsx`, `utils/explain.ts` (`Z = 1`), Validation page disclosure panel.
- **Caveat (see §6.3):** use **75 m** (σ 1.0–4.4 °C) for this shot. σ has sparse extreme outliers at 0–30 m and 100/125 m.

### F6 — Hover read-out (cell inspection) — **P0**

- **What the user sees:** a floating read-out `11.50°N, 90.00°E / 27.71 °C / 75 m` following the pointer (values for the demo cell/depth).
- **Purpose:** read the field without committing to a selection.
- **PROBLEM CONNECTION:** the reconstruction must be queryable at any location the judge asks about.
- **DEMO ACTION:** hover one mid-basin cell (slow move, then stop for ~1 s).
- **WHAT PRESENTER SHOULD SAY:** "Any cell, instantly — location, reconstructed temperature, and the depth I'm on."
- **JUDGE TAKEAWAY:** This is an interactive data product, not a static image.
- **Evidence:** `LIVE-UI` tooltip text captured (`11.50°N, 90.00°E`, `27.71 °C`, `75 m`); `CODE` `OceanMap.tsx` `onHover`.

### F7 — Click a grid cell → value popup + selection outline — **P0**

- **What the user sees:** a popup anchored on the cell — `11.50°N · 90.00°E`, `27.71 °C ±1.18`, `75 m · 2023-09-01` — plus a teal outline marking the selected cell.
- **Purpose:** commit to one coordinate and show temperature *with* its uncertainty.
- **PROBLEM CONNECTION:** proves the reconstruction is delivered per grid cell, with uncertainty, for a real date.
- **DEMO ACTION:** click the mid-basin cell (map centre, slightly below middle).
- **WHAT PRESENTER SHOULD SAY:** "One click: 27.7 degrees at 75 metres, ±1.2 — a real value from the model, on 1 September 2023."
- **JUDGE TAKEAWAY:** Reconstruction + uncertainty are delivered together at grid-cell level.
- **Evidence:** `LIVE-UI` popup text (exact strings above); `CODE` `OceanMap.tsx` `openValuePopup` + selection marker.

### F8 — Vertical profile chart at the selected cell (temperature vs true depth) — **P0**

- **What the user sees:** a chart with temperature (18–28 °C) across the X axis and depth **0 m at the top, 1000 m at the bottom on a true proportional scale**, with the 15 model levels marked, an amber-free ±1σ band around the curve, and a dashed 200 m reference line.
- **Purpose:** show the water column that a single map pixel represents.
- **PROBLEM CONNECTION:** this *is* the requested output — subsurface temperature structure, not a surface value.
- **DEMO ACTION:** nothing extra — the profile panel opens automatically on cell click; point at the thermocline.
- **WHAT PRESENTER SHOULD SAY:** "That same cell gives us the whole water column — about 29 degrees at the surface, 26 at 100 metres, and 6.5 at 1000 metres. That sharp fall is the thermocline."
- **Demo values (11.50°N, 90.00°E, 2023-09-01):** `29.2 °C @ 0 m · 27.7 @ 75 m · 25.6 @ 100 m · 14.7 @ 200 m · 6.5 @ 1000 m`; max σ 1.75 °C.
- **JUDGE TAKEAWAY:** The model reconstructs a physically sensible profile, not a flat guess.
- **Evidence:** `LIVE-UI` 15 markers with max depth-proportion error 0.0000, y-axis 0→1000 m, tooltip `200 m … temperature 12.4`; `LIVE-API` profile payload; `CODE` `profile/ProfileChart.tsx`; regression tests `frontend/src/__tests__/profile.test.tsx`.

### F9 — "Exact values" depth column (15 values + σ) — **P1**

- **What the user sees:** on toggle, a table of the 15 levels: `0 m 29.2°C ±1.46  level 1/15` … `1000 m 6.5°C ±0.25  level 15/15`.
- **Purpose:** make the reconstruction auditable value-by-value (no chart-reading).
- **PROBLEM CONNECTION:** a scientific deliverable must be inspectable numerically, not just visually.
- **DEMO ACTION:** click `Exact values` after the profile beat (only if ~4 s remain, otherwise skip).
- **WHAT PRESENTER SHOULD SAY:** "And every level can be read exactly — value and uncertainty."
- **JUDGE TAKEAWAY:** The output is real numbers, verifiable on screen.
- **Evidence:** `LIVE-UI` 15 rows with those exact strings; `CODE` `depth/DepthColumn.tsx`.

### F10 — "Explain this location" (deterministic, no LLM) — **P1**

- **What the user sees:** plain-language sentences for the selected cell: *"Surface temperature is reconstructed as 29.2 deg C. A sharp thermocline is estimated near 150 m, where temperature falls about 4.1 deg C. Model uncertainty estimate is ±1.5 deg C near the surface (1 sigma). Reconstruction from a statistical model, not an observation."*
- **Purpose:** translate the chart into a statement a non-oceanographer can repeat.
- **PROBLEM CONNECTION:** the product must communicate subsurface structure to non-experts (fisheries/operations), not only to scientists.
- **DEMO ACTION:** pause on the panel so the text is readable (it is part of the profile beat, no click needed).
- **WHAT PRESENTER SHOULD SAY:** "It even explains the location in words — and it says what it is: a model reconstruction, not an observation."
- **JUDGE TAKEAWAY:** Interpretation is evidence-traceable and explicitly non-LLM, non-observational.
- **Evidence:** `LIVE-UI` exact sentences; `CODE` `profile/ExplainLocation.tsx` + `utils/explain.ts` (deterministic rules, `Z = 1`).

### F11 — Map colour legend with the real value range — **P1**

- **What the user sees:** a horizontal colour scale above the map with `min mid max` taken from the loaded field and the unit (`°C` or `±1σ · °C`).
- **Purpose:** make the colours quantitative.
- **PROBLEM CONNECTION:** a temperature product without a scale is decoration.
- **DEMO ACTION:** incidental — visible in every map shot.
- **WHAT PRESENTER SHOULD SAY:** *(no separate sentence; the numbers do the work)*
- **JUDGE TAKEAWAY:** Colours map to real degrees, computed from ocean cells only.
- **Evidence:** `LIVE-UI` legend `18.0 23.1 28.1 °C` at 100 m and `1.0 2.7 4.4 ±1σ · °C` at 75 m; `CODE` `map/MapColorbar.tsx` (`data-testid="map-legend"`), `colorScales.ts`.

### F12 — Honest status banner + footer — **P0** (credibility shot)

- **What the user sees:** a teal banner reading **`Live model · Served by the hybrid_v1 inference service.`** — or, when the backend's 60-second route cache answers, **`Served from cache · Same result from a recent request (60 s TTL).`** (both observed this session). The footer reads **"Modeled reconstruction; trained on data through 2023-12-31."** and the header carries the badge **"Research prototype · Historical reconstruction"**.
- **Purpose:** disclose the serving path and the data vintage on screen.
- **PROBLEM CONNECTION:** a subsurface product used for decisions must not be mistaken for a real-time forecast.
- **DEMO ACTION:** incidental (banner and footer are always on screen).
- **WHAT PRESENTER SHOULD SAY:** "Built as an honest research prototype: historical reconstruction, with the data vintage stated on screen."
- **JUDGE TAKEAWAY:** The wording is deliberate and matches the implementation.
- **Evidence:** `LIVE-UI` banner/footer/badge strings; `CODE` `layout/StatusBanner.tsx`, `layout/Footer.tsx`, `layout/Header.tsx`.
- **Terminology trap:** "Live model" / "Served from cache" describe **which serving path answered** (live inference service vs. its 60 s response cache) — neither is a data-freshness claim. Amber **`Demo data`** would mean the model service is offline; red **`Unavailable`** means neither path could serve. The dates on screen are always 2022–2023. Never say "live data" / "real-time".

### F13 — Independent ARGO validation panel (numbers + depth table) — **P0**

- **What the user sees:** `Independent ARGO validation · hybrid_v1`, *"Aggregate, depth-wise validation against independent ARGO floats, 2023-08-10 to 2023-12-31. 285 of 291 ARGO profiles matched (3,958 depth observations)."*, three metric cards **RMSE 1.35 °C · Bias 0.61 °C · Correlation 0.990**, a 15-row depth-wise table, and an amber limitation note.
- **Purpose:** prove skill against independent real-world measurements.
- **PROBLEM CONNECTION:** SIH26066 requires validation of the reconstruction, not just a demo.
- **DEMO ACTION:** scroll the Validation page to the ARGO panel (see `DEMO_CLICK_PATH.md` §4).
- **WHAT PRESENTER SHOULD SAY:** "We validate against independent ARGO floats the model never trained on — 285 profiles, 3,958 measurements: RMSE 1.35 degrees, bias 0.61, correlation 0.99."
- **JUDGE TAKEAWAY:** Credible, independently validated skill.
- **Evidence:** `LIVE-UI` panel text (exact strings above); `ASSET` `argo_validation_summary.json`; implementation `ml/src/oceanembed/evaluation/argo.py`, `ml/scripts/evaluate_argo.py`; reproduction `docs/work-log/2026-09-13-argo-validation-mask-fix.md`.

### F14 — RMSE-by-depth chart (with the thermocline weakness highlighted) — **P0**

- **What the user sees:** a bar chart of RMSE at the 15 depths, with the 75–150 m bars in amber and the caption *"Amber bars mark the 75–150 m thermocline band with the highest error."*
- **Purpose:** show *where* the model is strong and weak instead of a single flattering number.
- **PROBLEM CONNECTION:** honest, depth-resolved evaluation is part of a defensible subsurface product.
- **DEMO ACTION:** it is directly below the metric cards — point at it while finishing the validation sentence.
- **WHAT PRESENTER SHOULD SAY:** "And we show where it is weakest — the thermocline band at 75 to 150 metres."
- **JUDGE TAKEAWAY:** The evaluation is not cherry-picked.
- **Evidence:** `LIVE-UI` bars rendered, caption text, 15 depth rows; `ASSET` depth-wise RMSE (75 m 2.81 °C, 100 m 2.65 °C vs 500 m 0.19 °C); `CODE` `validation/RmseDepthChart.tsx`.

### F15 — Model card: architecture, inputs, provenance, pipeline — **P0** (innovation beat)

- **What the user sees:** cards `Architecture = CNN + ConvLSTM`, `Temporal context = 7-day surface sequence`, `Output = 15-depth profile · 0–1000 m`, `Grid = 0.25° daily`, `Domain served = Bay of Bengal · 5–22°N, 80–100°E`; the 7 input channels with honest wording (*"Multi-source satellite-derived and ocean observation products, harmonized onto a single 0.25° reconstruction grid"*); a collapsible "How does OceanEmbed work?" chip chain `7 surface variables → Data harmonization → 7-day temporal context → CNN → ConvLSTM → 15-depth reconstruction → Temperature + uncertainty`; and provenance `best.pt · epoch 83 · val_loss 0.3714623343872113` from the live `/availability` report.
- **Purpose:** state exactly what the model is, what it eats, what it emits, and which checkpoint produced the screen.
- **PROBLEM CONNECTION:** the problem statement is a deep-learning reconstruction task; the judge must see the architecture and inputs.
- **DEMO ACTION:** open the Validation & Model tab (top of the page — no scrolling needed for this part).
- **WHAT PRESENTER SHOULD SAY:** "Seven surface variables go in — sea surface temperature, salinity, sea level, currents, winds — a CNN and a ConvLSTM read seven days of that, and out come temperatures at 15 depths from 0 to 1000 metres."
- **JUDGE TAKEAWAY:** Clear, verifiable model definition tied to the checkpoint provenance.
- **Evidence:** `LIVE-UI` all strings above; `CODE` `pages/ValidationPage.tsx`, `science/InputProvenancePanel.tsx`, `science/ModelFlowExplainer.tsx`; `LIVE-API` `/availability` checkpoint.

### F16 — Location picker + region reset view — **P2**

- **What the user sees:** a `Latitude`/`Longitude` form (disabled until a field loads) and a `Reset view` button, both in the top-left control panel.
- **Purpose:** keyboard access to any cell, snapping to the real grid; reset the map extent.
- **PROBLEM CONNECTION:** accessibility of arbitrary coordinates — real, but not needed to make the point in 60 s.
- **DEMO ACTION:** **do not use on camera** (typing costs seconds); keep as the deterministic fallback for the cell click.
- **WHAT PRESENTER SHOULD SAY:** *(only if asked:* "I can also type exact coordinates — it snaps to the served grid."*)*
- **JUDGE TAKEAWAY:** Any coordinate is reachable; the tool is not limited to one showcase cell.
- **Evidence:** `LIVE-UI` form present and enabled after load; `CODE` `controls/LocationPicker.tsx`, `ControlPanel.tsx`.
- **Note:** it selects a cell (opens the profile panel) but does **not** open the map popup — the popup is produced by a map click only.

## 4. Backend API surface (verified)

All under `/api/v1`, contract-guarded on the frontend (`frontend/src/api/client.ts`).

| Endpoint | Verified behaviour |
|---|---|
| `GET /availability` | Per-region capability report: Bay of Bengal `available` with 730 dates + grid `69×81×15` + checkpoint; other regions `no_data` with empty dates |
| `GET /ocean/map` | `channel: temperature`, one canonical depth; `values`/`sigma` 2D `[lat][lon]`, `null` on land; status `model_prediction` on the live path |
| `GET /ocean/profile` | 15 canonical depths `[0,5,10,20,30,50,75,100,125,150,200,300,500,700,1000]`, 15 temperatures, 15 σ (null-mask mirrors temperatures) |
| `GET /ocean/history` | Region date list (the same availability list) |
| `GET /ocean/metadata` | `regions: ["bay_of_bengal"]`, `model_version`, `data_freshness: 2023-12-31` |
| `GET /model/version` | `{"model_version":"hybrid_v1","trained_on":"2023-12-31","data_version":"bay_of_bengal-2022-2023-v1"}` |
| `GET /health` | `api: ok`, `model_loaded: ok`, `cache_accessible: ok`, `database: degraded` (expected) |

**Verified error handling (they return contracts, not stack traces):**

- Unknown/unserved region or out-of-range date → **404 `DATA_NOT_AVAILABLE`** (`"No data available for the requested region/date."`).
- Invalid depth → **400 `INVALID_DEPTH`** with the valid list in the message.
- Coordinates outside the region grid → **400 `INVALID_COORDINATE`** with `latitude_bounds`/`longitude_bounds`.

**Cache / fallback behaviour (verified, do not hide):**

- Route TTL cache (60 s) → status `cached_data`, banner *"Served from cache — Same result from a recent request (60 s TTL)."*
- Model service down → `fallback_demo` from the pre-built demo cache (31 weekly dates), banner *"Demo data — Model service offline; pre-built cache, not the live model."*
- Neither available → `unavailable` (503) rendered honestly, never fabricated.

## 5. Model explanation for the presenter (PHASE 5)

```
INPUT   7 surface channels (locked order): SST · SSS · SSH/SLA · current U · current V · wind U · wind V
        (multi-source satellite-derived + ocean-observation products, harmonized to one 0.25° grid)
MODEL   CNN encoder (7 → 32 → 64 → 128 channels) → ConvLSTM (hidden 128, 1 layer) → depth decoder
        with separate mean and log-variance heads
OUTPUT  temperature (°C) + ±1σ model uncertainty at 15 standard depths: 0, 5, 10, 20, 30, 50, 75,
        100, 125, 150, 200, 300, 500, 700, 1000 m — on a 0.25° daily grid
TEMPORAL 7-day surface sequence (deployed `TEMPORAL_WINDOW = 7`; 7-day context, not a 36-hour window)
TRAINED  GLORYS12v1 reanalysis as the target, temporal split (last 20% of samples = validation),
         data through 2023-12-31, checkpoint best.pt epoch 83
```

One-sentence version: **"Seven surface measurements, seven days of context, one CNN + ConvLSTM — and out come temperatures at fifteen depths from the surface to 1000 metres, with an uncertainty estimate."**

## 6. Honest-limits inventory (say these, or be ready to)

### 6.1 Validation

- Window: **2023-08-10 → 2023-12-31**, ARGO only; 291 profiles loaded, **285 matched**, 6 unmatched (all land cells — reported, never dropped), **3,958 depth observations**.
- Overall: **RMSE 1.3533 °C · bias +0.6121 °C · correlation 0.99**.
- Depth-resolved: **0–30 m RMSE 0.41–0.95 °C**; **50 m 1.80**; **75 m 2.81 (bias +2.17)**; **100 m 2.65 (bias +2.16)**; **125 m 1.86**; **150 m 1.25**; **200 m 0.64**; **300–1000 m 0.16–0.26 °C**.
- Per-depth **correlation is not uniformly high** (0 m 0.58, 5 m 0.29, 30 m 0.13, 75 m 0.71, 100 m 0.73, 300 m 0.62, 1000 m 0.10). The overall 0.99 is driven by matching large deep variance. **Never present the overall 0.99 as a per-cell accuracy.**
- The committed asset itself states both the strength and the thermocline weakness (`limitations` string, rendered in the UI).

### 6.2 Scope and vintage

- **Only the Bay of Bengal is served** (5–22°N, 80–100°E). Arabian Sea / North Indian Ocean are declared but have no data.
- Data covers **2022-01-01 → 2023-12-31**; the demo date is **2023-09-01**. This is **retrospective reconstruction**, not nowcasting or forecasting.
- Inputs combine satellite-derived and model-analysis products — never say "7 pure satellite measurements".

### 6.3 Uncertainty display caveat (verified this session)

σ = `sqrt(exp(log_var))` is the model's own output, and a handful of cells carry extreme values at shallow depths. Verified σ maxima on 2023-09-01 (of 3,841 ocean cells):

| Depth | σ min–max (°C) | cells with σ > 10 °C | demo-safe? |
|---|---|---|---|
| 0 m | 1.18 – **160.41** | 13 | ❌ |
| 5 m | 1.44 – 65.86 | 13 | ❌ |
| 10 m | 1.04 – 31.67 | 13 | ❌ |
| 20 m | 0.80 – 26.92 | 13 | ❌ |
| 30 m | 0.67 – 41.09 | 13 | ❌ |
| **50 m** | 0.57 – 2.10 | 0 | ✅ |
| **75 m** | 1.05 – 4.41 | 0 | ✅ (scripted) |
| 100 m | 1.57 – 15.80 | 7 | ⚠️ avoid for σ |
| 125 m | 1.55 – 17.90 | 9 | ⚠️ avoid for σ |
| 150 m / 200 m / 300 m+ | 1.09–9.41 / 0.49–3.32 / 0.20–2.89 | 0 | ✅ |

Because the legend scales to the field's true min/max, a few 100 °C-class σ cells at 0–30 m would flatten the whole σ map. **Shoot the uncertainty layer at 75 m** (σ 1.0–4.4 °C). This is a *display-planning* fact, not a fabrication: the σ values are the model's raw output and no value is altered.

### 6.4 Presentation traps (verified wording)

- Banner says **"Live model"** → it means the live inference service served it (2023 data). Never say "real-time" / "today's ocean".
- Uncertainty is **±1σ, uncalibrated** — never "95% confidence". The UI itself says this.
- ARGO is **validation only** — never training data.
- GLORYS is the **training target**, not truth; ARGO is the independent check.
- Correlation 0.99 is **overall**, dominated by deep variance — not per-cell accuracy.

## 7. What NOT to show in the 60-second video

| Excluded | Why |
|---|---|
| Arabian Sea / North Indian Ocean selection | `no_data` — would show an empty state and contradict the served-scope claim |
| `/api/v1` docs, OpenAPI, terminal windows, logs, DB row counts | Backend/DB is `degraded` locally and irrelevant to SIH26066 |
| `git` state, code editors, test output | Judges score the product, not the repo |
| Location picker typing, Reset view, region dropdown fiddling | Costs seconds, adds no new understanding (P2) |
| 0–30 m or 100–125 m **uncertainty** shots | σ outlier cells flatten the σ map (§6.3) |
| Scrolling around the Validation page looking for numbers | Pre-scripted single scroll only (see click path) |
| Any 2026 date, "real-time", "forecast", "95%", "replaces ARGO", "better than GODAS", "global" | Not supported by the repository |
| The 36-hour MVP framing as shipped capability | The deployed product is a daily historical reconstruction; do not imply an operational forecast service |
| Long loading states | Pre-flight warms the caches so the map paints immediately |

## 8. P0 data sheet (values you may use verbatim)

```
Product .......... OceanEmbed hybrid_v1 — subsurface temperature reconstruction, Bay of Bengal
Region served .... Bay of Bengal · 5–22°N, 80–100°E (only served region)
Grid ............. 0.25° · 69 lat × 81 lon · 3,841 valid ocean cells of 5,589
Dates served ..... 2022-01-01 → 2023-12-31 (730 daily) · demo date 2023-09-01
Model ............ OceanEmbedNet: multi-scale CNN (7→32→64→128) → ConvLSTM (128, 1 layer) → depth decoder
                   with mean + log-variance heads; checkpoint best.pt, epoch 83, val_loss 0.3714623343872113
Inputs ........... 7 surface channels: SST, SSS, SSH/SLA, current U, current V, wind U, wind V
Temporal window .. 7 days (deployed TEMPORAL_WINDOW = 7)
Outputs .......... temperature + ±1σ model uncertainty at 15 depths: 0,5,10,20,30,50,75,100,125,
                   150,200,300,500,700,1000 m
Training target .. GLORYS12v1 reanalysis · temporal split (last 20% = validation) · data through 2023-12-31
Demo cell ........ 11.50°N · 90.00°E on 2023-09-01
                   0 m 29.2 °C · 75 m 27.7 °C · 100 m 25.6 °C · 200 m 14.7 °C · 1000 m 6.5 °C · max σ 1.75 °C
Map ranges ....... 100 m (default): T 18.0–28.1 °C   75 m: T 19.8–28.5 °C, σ 1.0–4.4 ±1σ °C
ARGO validation .. window 2023-08-10 → 2023-12-31 · 291 profiles loaded / 285 matched (6 land) /
                   3,958 depth observations
                   RMSE 1.3533 °C · bias +0.6121 °C · correlation 0.99
                   depth-wise: 50 m 1.80 · 75 m 2.81 · 100 m 2.65 · 150 m 1.25 · 500 m 0.19 · 1000 m 0.16 °C
Data sources ..... training target GLORYS12v1 (Copernicus); validation ARGO (independent); never mixed
Offline mode ..... 31 weekly dates 2023-06-01 … 2023-12-28, banner "Demo data"
```

## 9. NOT DEMO-READY items

| Item | Status | What would be needed |
|---|---|---|
| Arabian Sea / North Indian Ocean exploration | **NOT DEMO-READY** | a trained model + tensor store for those regions (none exists; `/availability` reports `no_data`) |
| Any 2024–2026 date | **NOT DEMO-READY** | data beyond 2023-12-31 is not in the tensor store; requests return 404 `DATA_NOT_AVAILABLE` |
| Calibrated confidence intervals | **NOT DEMO-READY** | no calibration/coverage analysis exists in the repo; UI ships ±1σ and says so |
| Forecast / nowcast claim | **NOT DEMO-READY** | the model reconstructs past dates only; no forecast pipeline exists |
| Cell-exact ARGO comparison in the UI | **NOT DEMO-READY** | the UI validates in aggregate by design (`ArgoValidationPanel` copy: "aggregate validation, not cell-exact") |

Everything the 60-second script relies on is demo-ready: the Explorer, the depth rail, the
profile chart, the uncertainty layer at 75 m, the Validation & Model page and its ARGO panel.
