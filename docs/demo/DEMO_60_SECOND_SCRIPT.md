# 60-Second Demo Script — OceanEmbed (SIH26066)

> **Audience:** a non-oceanography SIH judge. **Target:** 60 s (±3 s).
> **Every value spoken here was verified on 2026-09-16 against the running stack** — see
> `DEMO_FEATURE_AUDIT.md` §8 (P0 data sheet). Do not ad-lib numbers.
> **Pacing:** each voiceover cell is sized for ~3 words/second. Under-fill rather than rush;
> the on-screen movement needs a beat of silence anyway.
> **Structure:** PROBLEM → SOLUTION → CORE INNOVATION → LIVE SOFTWARE → PROFILE →
> UNCERTAINTY → VALIDATION → IMPACT.

## Story arc

| Beat | Window | Purpose |
|---|---|---|
| Problem | 0–8 s | the ocean below the surface is barely observed |
| Solution | 8–15 s | OceanEmbed reconstructs it from surface data |
| Core innovation | 15–22 s | 7 surface variables → CNN + ConvLSTM → 15 depths |
| Live software | 22–38 s | the Explorer proves it exists and responds |
| Subsurface profile | 38–48 s | a real water column at a real cell |
| Uncertainty | 48–53 s | honest per-cell ±1σ |
| Validation | 53–58 s | independent ARGO numbers |
| Impact | 58–60 s | one closing sentence |

---

## Script table

### 0–8 s · PROBLEM

| Field | Detail |
|---|---|
| **Screen action** | Explorer is open on the Bay of Bengal map; do **not** touch the mouse yet — let the temperature field render. |
| **Feature** | Subsurface temperature map (F1) + honest header badge "Research prototype · Historical reconstruction". |
| **Voiceover** | "Satellites measure the ocean surface everywhere. Below the surface, temperature is sampled by only a few hundred drifting floats." |
| **On-screen text** | `Surface: observed from space` · `Subsurface: sparsely sampled` |
| **Judge takeaway** | There is a real, specific data gap: the ocean's interior is barely observed. |

### 8–15 s · SOLUTION

| Field | Detail |
|---|---|
| **Screen action** | Slow mouse move across the map (no clicks); the field is already visible. |
| **Feature** | Map + 0.25° grid + status banner (teal: `Live model` — or `Served from cache` if the 60 s route cache answered; both mean the live inference service) |
| **Voiceover** | "OceanEmbed reconstructs that missing water column for the Bay of Bengal — using surface observations, with a deep learning model." |
| **On-screen text** | `OceanEmbed — subsurface temperature reconstruction` · `Bay of Bengal · 0.25° daily` |
| **Judge takeaway** | The solution turns surface data into the subsurface field; scope is stated honestly. |

### 15–22 s · CORE INNOVATION

| Field | Detail |
|---|---|
| **Screen action** | Click **Validation & Model** (top nav). The page opens at the top — nothing to scroll: architecture cards, 7 input channels and the pipeline chips are all in frame. |
| **Feature** | Model card (F15): `Architecture = CNN + ConvLSTM`, `Temporal context = 7-day surface sequence`, `Output = 15-depth profile · 0–1000 m`, `Grid = 0.25° daily`, `Domain served = Bay of Bengal · 5–22°N, 80–100°E` + the 7 input channels. |
| **Voiceover** | "Seven surface variables go in — sea temperature, salinity, sea level, currents, winds. A CNN and a ConvLSTM output temperatures at fifteen depths, down to 1000 metres." |
| **On-screen text** | `7 surface variables → CNN + ConvLSTM → 15 depths (0–1000 m)` |
| **Judge takeaway** | The model is concretely defined: inputs, architecture, output, resolution. |

### 22–38 s · LIVE SOFTWARE WALKTHROUGH

| Field | Detail |
|---|---|
| **Screen action (22–27 s)** | Click **Ocean Explorer** to return. Map repaints the Bay of Bengal at 100 m (default). Banner stays teal. |
| **Feature** | Explorer + date + 0.25° grid + cell count |
| **Voiceover (22–27 s)** | "This is the OceanEmbed Explorer — Bay of Bengal, 1 September 2023, 100 metres deep. Every 0.25-degree cell here is a full water column." |
| **On-screen text** | `2022-01-01 → 2023-12-31 · 730 daily reconstructions · 3,841 ocean cells` |

| Field | Detail |
|---|---|
| **Screen action (27–31 s)** | Click **75** in the depth rail (right edge). The map recolours and the legend changes to `19.8 24.2 28.5 °C`. |
| **Feature** | Depth rail (F2) |
| **Voiceover (27–31 s)** | "We can move through the water column — here at 75 metres, the thermocline band." |
| **On-screen text** | `Depth 75 m` |
| **Judge takeaway (22–31 s)** | The reconstruction is genuinely 3-D: 15 depths, 2 years of daily dates, a whole region — and it is interactive. |

| Field | Detail |
|---|---|
| **Screen action (31–38 s)** | Move the pointer slowly to a mid-basin cell (~50% across, ~55% down the map) and stop: the read-out appears. Then click it: the popup opens — `11.50°N · 90.00°E`, `27.71 °C ±1.18`, `75 m · 2023-09-01`. |
| **Feature** | Hover read-out (F6) + cell click popup (F7) |
| **Voiceover (31–38 s)** | "Hover a cell for the value. Click it, and we get the temperature with its uncertainty: 27.7 degrees at 75 metres, plus or minus 1.2." |
| **On-screen text** | `11.50°N, 90.00°E · 27.71 °C ±1.18` |
| **Judge takeaway** | Real values, per grid cell, with uncertainty — not an illustration. |

### 38–48 s · SUBSURFACE PROFILE

| Field | Detail |
|---|---|
| **Screen action** | The profile panel has already slid in on the right (it opens on the cell click). Point at the curve: the 15 markers, the y-axis running 0 m (top) to 1000 m (bottom), the ±1σ band. Nothing to click. |
| **Feature** | Vertical profile chart (F8) + "Explain this location" text (F10) |
| **Voiceover** | "Every cell gives the whole column: 29 degrees at the surface, 26 at 100 metres, 6.5 down at 1000 metres. That steep drop is the thermocline — where most of the ocean's heat is stored." |
| **On-screen text** | `Profile · 11.50°N, 90.00°E · 0 → 1000 m` |
| **Judge takeaway** | The reconstruction produces a physically sensible subsurface structure, not a flat number. |

### 48–53 s · UNCERTAINTY

| Field | Detail |
|---|---|
| **Screen action** | Click **Uncertainty** in the top-left layer toggle. The map recolours; the legend reads `1.0 2.7 4.4 ±1σ · °C`. Do not change depth. |
| **Feature** | ±1σ uncertainty layer (F5) |
| **Voiceover** | "The model also estimates its own uncertainty — here at 75 metres it stays between about 1 and 4 degrees. That's ±1σ, not a confidence guarantee." |
| **On-screen text** | `±1σ model uncertainty (uncalibrated)` |
| **Judge takeaway** | The team ships uncertainty and describes it accurately — a maturity signal. |

### 53–58 s · VALIDATION

| Field | Detail |
|---|---|
| **Screen action** | Click **Validation & Model**, then scroll down about one screen so the **Independent ARGO validation** panel fills the viewport (metrics + RMSE-by-depth chart + depth table). This is the only scroll in the video — start it as the sentence begins. |
| **Feature** | ARGO validation panel (F13) + RMSE-by-depth chart (F14) |
| **Voiceover** | "Against independent ARGO floats the model never trained on: 285 profiles, 3,958 measurements — RMSE 1.35 degrees, correlation 0.99. And we show where it is weakest, in the thermocline band." |
| **On-screen text** | `ARGO validation · 285/291 profiles · 3,958 obs · RMSE 1.35 °C · bias 0.61 °C · r = 0.99` |
| **Judge takeaway** | Independent validation with published weaknesses — credible, not cherry-picked. |

### 58–60 s · IMPACT

| Field | Detail |
|---|---|
| **Screen action** | Hold the ARGO panel (or click **Ocean Explorer** for the closing map — only if the click can be done before the sentence starts). |
| **Feature** | — (closing line) |
| **Voiceover** | "OceanEmbed makes the subsurface ocean easier to explore where observations are limited." |
| **On-screen text** | `Reconstruction · not a forecast` |
| **Judge takeaway** | Clear value proposition built on what was just demonstrated. |

---

## Key phrases (memorize exactly)

- "Seven surface variables in — fifteen depths out."
- "Every 0.25-degree cell is a full water column."
- "RMSE **1.35** degrees, correlation **0.99**, against ARGO data the model never trained on."
- "It's ±1σ — a model estimate, not a 95% guarantee."
- "A historical reconstruction, not a forecast."

## Numbers you may say out loud (and nothing else)

```
2023-09-01 · Bay of Bengal · 0.25° · 3,841 ocean cells · 730 daily dates (2022-01-01 → 2023-12-31)
11.50°N, 90.00°E  ·  0 m 29.2 °C  ·  75 m 27.7 °C ±1.2  ·  100 m 25.6 °C  ·  1000 m 6.5 °C
σ at 75 m on the map: 1.0 – 4.4 °C (±1σ, uncalibrated)
ARGO: 285 of 291 profiles matched, 3,958 depth observations, RMSE 1.35 °C, bias 0.61 °C, r = 0.99
Model: hybrid_v1 · CNN + ConvLSTM · 7-day window · 15 depths · checkpoint best.pt epoch 83
```

## Hard traps (one slip costs credibility)

- ❌ "Real-time" / "live data" / "today" / "forecast" → this is a **historical reconstruction through 2023-12-31**. The teal banner describes the serving path, not the data vintage.
- ❌ "95% confidence" / "accuracy 99%" → it is **±1σ, uncalibrated**; 0.99 is a **correlation**, not accuracy.
- ❌ "Pure satellite" → inputs are multi-source satellite-derived **and** ocean-observation products.
- ❌ "Works globally" / "Arabian Sea" → **Bay of Bengal only** in the live demo.
- ❌ "We replace ARGO" / "better than GODAS" → ARGO is the independent reference; no comparison exists.
- ❌ Reading the depth-0 σ off the map, or showing the uncertainty layer at 0–30 m → sparse outlier cells (see audit §6.3).
- ❌ Inventing any number not in the list above.

## If the judge asks

- **"Is this real-time?"** → "No — it's a daily historical reconstruction; the data runs 2022 to the end of 2023. The 'Live model' banner means this result came from the live inference service rather than the offline cache."
- **"How accurate is it?"** → "Overall RMSE 1.35 °C against independent ARGO floats. At 500–1000 m it's about 0.2 °C; the hardest band is the thermocline at 75–150 m, around 1.2 to 2.8 °C, and we publish that."
- **"Is the uncertainty calibrated?"** → "No — it's the model's own ±1σ estimate. Calibration/coverage analysis is the next step, and the UI says so."
- **"Can you do other regions?"** → "The pipeline is region-agnostic, but today only the Bay of Bengal model is trained and served; the Arabian Sea shows no data rather than pretending."
- **"What's next?"** → "Train the same architecture for the Arabian Sea and validate per-region, and add calibration so ±1σ can be quoted as coverage."
