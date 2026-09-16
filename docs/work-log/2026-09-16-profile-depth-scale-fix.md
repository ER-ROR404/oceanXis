# Work Log — 2026-09-16: Subsurface profile chart was plotting temperature on the depth axis

> **Symptom:** the profile chart's 15 model levels were crushed into a thin horizontal
> strip near the top of the plot even though the Y axis read 0–1000 m.
> **Cause:** a chart-library axis-mapping bug, not a data bug. In recharts' default
> *horizontal* layout every series plots its own `dataKey` on the value (Y) axis, so
> `<Line dataKey="temp">` put **temperature on the depth axis** and the X axis
> (`dataKey="temp"`) put temperature on the horizontal axis — temperature on both axes.
> **Fix:** render the chart as a recharts `layout="vertical"` chart (temperature = value
> axis, depth = the axis each row is positioned by). No prediction value, depth value,
> or σ value was changed or interpolated.

## 1. Reproduction (before)

Measured from the rendered SVG (jsdom, 600×400 container): the 15 markers sat at
`cy ≈ 10.2 … 18.4` in a plot area spanning `cy 8 … 362` — a total span of **7.9 px**
instead of the full depth range, with the surface point at the *bottom*.

Cause confirmed in the installed library (`recharts@2.12.7`):

- `cartesian/Line.js` + `cartesian/Area.js` `getComposedData`: horizontal layout →
  `y: yAxis.scale(value)` where `value = getValueByDataKey(entry, item.dataKey)`, and
  `x: getCateCoordinateOfLine(xAxis …)` uses the chart-level `XAxis dataKey`.
- Therefore `<YAxis dataKey="depth">` only supplied *ticks*, never the marker positions:
  `yAxis.scale(29.92 °C)` on a 0–1000 m scale = a few pixels below the top.

## 2. Fix

`frontend/src/components/profile/ProfileChart.tsx` (only file with rendering logic changed):

| Axis | Before | After |
|------|--------|-------|
| chart layout | default horizontal | `layout="vertical"` |
| X axis | `dataKey="temp"` (category axis) | `dataKey="temp"`, `type="number"` — the **value** axis (temperature, real °C) |
| Y axis | `dataKey="depth"` + `reversed`, domain `[dataMin, dataMax]` | `dataKey="depth"`, `type="number"`, domain `[0, 1000]`, no `reversed` (vertical layout's Y range already runs top→bottom) |
| `<Line>` | `dataKey="temp"` (plotted temp on Y) | `dataKey="temp"` now plotted on the X value axis, positioned at each row's real depth |
| `<Area dataKey="band">` | `[lo, hi]` range on the depth (Y) axis → a nonsense 0.7 m-tall sliver near the surface | `[lo, hi]` range on the X value axis → a **horizontal** ±1σ band at the level's true depth |

Recharts supports this directly: with `layout="vertical"` the Y coordinate is taken from
the Y axis `dataKey` (`util/ChartUtils.js#getCateCoordinateOfLine` → `axis.scale(value)`),
`monotone` becomes `curveMonotoneY` (monotone in depth, which is strictly ordered), and
range `Area`s are drawn horizontally (`shape/Curve.js`). The Y domain is fixed at
`[0, 1000]` so the axis always covers the full model column and the `padding` keeps the
0 m / 1000 m markers from being clipped at the plot edge.

## 3. Depth-array contract guard

`frontend/src/api/client.ts`: the profile guard now **verifies** the response's `depths`
against the canonical 15 levels in canonical order (metres) instead of silently
substituting the constant. An index array (`0..14`) or a reordered wire array would pair
the wrong temperature with each depth, so it is rejected as `ContractError`.

## 4. Verification

### Unit / build (from `frontend/`)

- `npx vitest run` → **159 passed** (was 156); `npx tsc --noEmit` clean; `npm run build` clean.
- New regression tests in `src/__tests__/profile.test.tsx`:
  - all 15 levels rendered as markers;
  - every marker sits at `depth/1000` of the 0–1000 m span (an index axis would put
    1000 m at 14/15);
  - the axis is inverted (0 m above 1000 m, surface marker in the upper half);
  - temperature is the horizontal coordinate (warmest level right of the coldest).
  - **RED evidence:** removing `layout="vertical"` fails these tests with
    `expected 7.909… to be greater than 100` (the old 7.9 px span).
- New contract tests in `src/api/client.test.ts`: rejects index depths, rejects reordered
  depths, keeps the response depth array.

### Real browser + live model service (5.50°N, 93.25°E, 2023-09-01)

Backend `/api/v1/ocean/profile` → `status: model_prediction`, `depths` =
`[0,5,10,20,30,50,75,100,125,150,200,300,500,700,1000]`,
`temperatures` = `[29.92, 29.75, 29.96, 30.03, 29.74, 28.77, 26.34, 22.08, 17.57, 14.54,
12.36, 11.06, 9.67, 8.36, 6.53]` °C (all 15 real prediction values, unchanged).

Rendered chart (Playwright, chromium, 1500×900 viewport):

- marker `cy`: `16.0, 17.0, 17.9, 19.9, 21.8, 25.7, 30.6, 35.4, 40.3, 45.1, 54.8, 74.2, 113.0, 151.8, 210.0`
  (0 m → 1000 m spans the whole 256 px chart; **max depth-proportion error 0.0000**);
- Y ticks at `0, 250, 500, 750, 1000` m in true proportion, 0 m at the top;
- the ±1σ band shares each marker's depth coordinate exactly (same y values);
- hover at 200 m → `200 m | ±1σ range: 11.8 – 12.9 | temperature: 12.4`, i.e. the API's
  12.359 °C ± 0.514 °C at 200 m;
- no console errors, no page errors.

## 5. What did not change

- Model predictions, σ values, depth levels, canonical order — untouched (no
  interpolation, no smoothing of values; the connecting curve is still labelled
  "Visual interpolation between the 15 model levels").
- ±1σ (uncalibrated) uncertainty framing, the honesty captions and the "Exact values"
  (`DepthColumn`) view.
- No new dependency, no new UI surface.
