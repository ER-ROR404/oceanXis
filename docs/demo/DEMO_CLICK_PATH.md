# Exact Demo Click Path — OceanEmbed (SIH26066)

> **Verified interactively on 2026-09-16** against the running stack (ML `:8080`, backend
> `:8000`, frontend `:5173`) with a **1920×1080 viewport at 100 % zoom**. Every "expected
> result" string below was read off the screen.
>
> Pixel coordinates are for 1920×1080. For any other window size, use the **labelled
> control** instead of the pixel — the labels (`Ocean Explorer`, `Validation & Model`,
> `75`, `Uncertainty`, `Temperature`) are stable; pixel positions are not.
>
> **Golden rule:** if an expected result does not match, stop and re-run the pre-flight.
> Never improvise a number on camera.

## 0. Pre-flight (not recorded, ~30 s)

1. All three services up (see `DEMO_RECORDING_CHECKLIST.md` §A for the commands).
2. Open `http://localhost:5173` in a clean Chromium window, 1920×1080, 100 % zoom, devtools **closed**.
3. Wait for the map to paint. **Must read:** a **teal** banner — `Live model · Served by the hybrid_v1 inference service.` or (after a recent identical request) `Served from cache · Same result from a recent request (60 s TTL).` — plus the header badge `Research prototype · Historical reconstruction`. Amber `Demo data` = the ML service is down; stop.
4. **Warm both tabs once** (click *Validation & Model*, then *Ocean Explorer*) so the basemap
   tiles and API responses are cached; a tab visit remounts the Leaflet map and can flash for a
   moment on the first load.
5. Confirm the state that the script assumes:
   - region select = `bay_of_bengal` (default — do not touch),
   - date select = `2023-09-01` (default — do not touch),
   - depth rail active = `100` (default — the script's first depth action is the 75 m click),
   - map stats line = `100 m · 3,841 valid ocean cells · 0.25° grid · 2023-09-01`,
   - legend = `18.0 23.1 28.1 °C`.

## 1. The path (≈60 s)

| # | Time | Action (exact) | Expected result on screen | Script beat |
|---|---|---|---|---|
| 1 | 0 s | **Do nothing.** The Explorer is already open on the Bay of Bengal. | Temperature field at 100 m, teal legend `18.0 23.1 28.1 °C`, teal banner (`Live model …` or `Served from cache …`), footer `Modeled reconstruction; trained on data through 2023-12-31.` | 0–8 s problem |
| 2 | 8 s | Move the mouse **slowly** across the map, then stop (no click). | No state change — the field and 0.25° grid are the point. | 8–15 s solution |
| 3 | 15 s | Click **Validation & Model** (top nav, ≈ `(895, 27)`). | Validation page opens at the **top**: `OceanEmbed Hybrid v1`, architecture cards (`CNN + ConvLSTM`, `7-day surface sequence`, `15-depth profile · 0–1000 m`, `0.25° daily`, `Bay of Bengal · 5–22°N, 80–100°E`), the 7 input channels, and the "How does OceanEmbed work?" chips. **No scrolling needed.** | 15–22 s innovation |
| 4 | 22 s | Click **Ocean Explorer** (top nav, left of the other tab, ≈ `(757, 27)`). | Map repaints (Bay of Bengal, 100 m). If the basemap flashes, hold ~0.5 s before speaking. | 22–27 s walkthrough |
| 5 | 27 s | Click **75** in the depth rail (right edge, ≈ `(1871, 533)`). | Map recolours; legend changes to `19.8 24.2 28.5 °C`; stats line reads `75 m · 3,841 valid ocean cells · 0.25° grid · 2023-09-01`. | 27–31 s |
| 6 | 31 s | Move the pointer slowly to the map cell at ≈ `(960, 602)` (map centre, slightly below middle) and stop. | Floating read-out appears: `11.50°N, 90.00°E` / `27.71 °C` / `75 m`. | 31–38 s hover |
| 7 | 35 s | Click the same cell. | Popup: `11.50°N · 90.00°E`, `27.71 °C ±1.18`, `75 m · 2023-09-01`; the cell gets a teal outline; the **profile panel opens on the right** with the 15-level curve (x-axis temperature, y-axis 0 m top → 1000 m bottom). | 31–38 s click |
| 8 | 38 s | **Do nothing** — point at the curve (thermocline knee between 75 m and 200 m; dashed line at 200 m). | Profile shows `29.2 → 25.6 (100 m) → 14.7 (200 m) → 6.5 °C (1000 m)`; caption "Model uncertainty estimate (±1σ)…"; "Explain this location" text below. | 38–48 s profile |
| 9 | 48 s | Click **Uncertainty** (top-left layer toggle, ≈ `(160, 169)`). | Map recolours on the σ scale; legend reads `1.0 2.7 4.4 ±1σ · °C`. Depth stays 75 m. | 48–53 s uncertainty |
| 10 | 50 s | Click **Temperature** (≈ `(72, 169)`) only if the script needs the map back before the tab switch (optional). | Map returns to the temperature field. | — |
| 11 | 53 s | Click **Validation & Model** (≈ `(895, 27)`), then **scroll down ~one screen** (mouse wheel ≈ 5 notches, or two `Page Down`) so **Independent ARGO validation** is at the top of the viewport. | Panel fills the viewport: `285 of 291 ARGO profiles matched (3,958 depth observations)`, cards `RMSE 1.35 °C · Bias 0.61 °C · Correlation 0.990`, the RMSE-by-depth bar chart with amber 75–150 m bars, and the 15-row depth table. | 53–58 s validation |
| 12 | 58 s | Hold the shot (optionally click **Ocean Explorer** if it can be done before the sentence starts). | — | 58–60 s impact |

**Total actions: 6 clicks + 1 scroll + 1 hover.** Everything else is narration.

### Why this cell

`11.50°N, 90.00°E` is open ocean in the middle of the Bay of Bengal, so:

- the popup is clean — `27.71 °C ±1.18` at 75 m (no coastal σ outlier),
- the profile is a textbook stratified column: `29.2 → 27.7 (75 m) → 25.6 (100 m) → 14.7 (200 m) → 6.5 °C (1000 m)`, max σ 1.75 °C,
- neighbouring cells agree within ~0.5 °C, so a pixel-perfect click is not required — but the
  spoken coordinate must be read from the panel if the popup shows anything other than
  `11.50°N · 90.00°E`.

### If the map click misses (fallback, still deterministic)

Use the **Location** form in the top-left panel instead of clicking the map:

1. Click the `Latitude` field (≈ `(128, 300)`), type `11.5`.
2. Tab/click the `Longitude` field (≈ `(128, 345)`), type `90`.
3. Click **Inspect**.

Result: the same cell is snapped to the real grid and the profile panel opens with
`11.50°N, 90.00°E | 2023-09-01`. Note: this path does **not** open the map popup, so the
line "27.7 degrees at 75 metres, plus or minus 1.2" must then be read from the profile
panel / "Exact values" table instead.

## 2. What NOT to click during the recording

| Don't touch | Why |
|---|---|
| **Region** select → Arabian Sea / North Indian Ocean | `no_data` — an empty state on camera contradicts the scope claim. Default `Bay of Bengal` is correct. |
| **Date** stepper / date dropdown | 2023-09-01 is already selected and is a good, verified date; changing it adds dead air and a second API round-trip. |
| **Reset view** | The map already auto-fits the reconstruction domain; a reset mid-shot makes the field jump for no reason. |
| **Temperature layer at 0–30 m, or the uncertainty layer at 0–30 m / 100 m / 125 m** | σ has sparse extreme cells there (up to 160 °C at 0 m); the σ legend would stretch to that maximum and flatten the map. 50 m and 75 m are clean. |
| Coastline-hugging cells | Same σ-outlier and land-edge issue; stay mid-basin. |
| The map zoom/pan controls | Extra motion that delays the popup; the scripted cell is already in frame. |
| Anything with a date other than 2023-09-01 | All spoken numbers in the script belong to 2023-09-01 at 11.50°N, 90.00°E. |

## 3. Recovery cheatsheet

| Symptom | Fix (say nothing; just fix) |
|---|---|
| Banner reads `Served from cache` (teal) | Expected if the same request happened within the last 60 s (observed this session). Same result, same live service — keep going, do not re-narrate, and do not call it "live data". |
| Banner reads `Demo data` (amber) | The ML service is down. Stop; restart the stack and re-record (the numbers would be the offline cache's, not the live model's). |
| Popup shows a different coordinate | Read the real coordinate from the popup/panel and say that instead; never say a coordinate that is not on screen. |
| Profile panel shows "No profile here" | The cell is land/masked — the map click landed on a coastal gap. Click the fallback cell (`11.5`, `90`) via the Location form. |
| Map is blank/dark for >2 s after the tab switch | Wait, don't click. The tiles are reloading; the field paints on top of the basemap. |
| ARGO numbers are off-screen after scrolling | Scroll a little further down; the panel is ~1,060 px tall and fills a 1080 px viewport almost exactly. |
| Any 4xx toast / red banner appears | Stop the take. A red state (e.g. `unavailable`) is honest but must not be in the video. |
