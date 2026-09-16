# Demo Recording Checklist — OceanEmbed (SIH26066)

> Run this top-to-bottom once before the take. Anything unchecked → fix it, then start.
> **The two hard gates:** (1) the status banner is **teal** (`Live model` — or `Served from
> cache` when the backend's 60 s route cache answers; both mean the live inference service),
> never amber `Demo data` or red `Unavailable`; (2) the spoken numbers match
> `DEMO_FEATURE_AUDIT.md` §8 exactly.
> Commands below are the exact ones that produced the verified audit on 2026-09-16.

## A. Start the stack (order matters: ML → backend → frontend)

```bash
# 0) Pre-requisites (must exist, from the repo root)
ls data/checkpoints/hybrid_v1/best.pt          # checkpoint
ls data/tensors/bay_of_bengal/X.zarr           # tensor store (730 daily dates)

# 1) ML inference service  (:8080) — run from the repo root.
#    Use the repo-root .venv (it has torch + the editable `oceanembed` install);
#    `ml/.venv` does NOT exist in this checkout.
TENSOR_DIR=/home/joel/Projects/ERROR404/data/tensors \
REGION=bay_of_bengal \
CHECKPOINT_PATH=/home/joel/Projects/ERROR404/data/checkpoints/hybrid_v1/best.pt \
  nohup /home/joel/Projects/ERROR404/.venv/bin/python -m oceanembed.serving.server \
  > /tmp/opencode/ml-inference.log 2>&1 &

# 2) Backend API (:8000) — run from backend/
cd /home/joel/Projects/ERROR404/backend
OCEANEMBED_MODEL_SERVICE_URL=http://localhost:8080 \
OCEANEMBED_DEMO_CACHE_DIR=/home/joel/Projects/ERROR404/artifacts/demo_cache \
  nohup .venv/bin/uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 \
  > /tmp/opencode/backend.log 2>&1 &

# 3) Frontend (:5173) — run from frontend/
cd /home/joel/Projects/ERROR404/frontend
nohup npm run dev -- --host 127.0.0.1 > /tmp/opencode/frontend.log 2>&1 &
```

> The offline demo cache (31 weekly dates 2023-06-01 → 2023-12-28) is the *fallback*.
> For the main take the ML service must be **on** so the banner reads `Live model`.

## B. Service health (all four must pass)

- [ ] `curl -s http://127.0.0.1:8080/health` → contains `"model":"hybrid_v1"` and `"status":"ok"`
- [ ] `curl -s http://127.0.0.1:8000/api/v1/health` → `"model_loaded":{"status":"ok"}` and `"cache_accessible":{"status":"ok"}`
      (`"database":{"status":"degraded"}` is **expected** locally — no Postgres is used for any demoed feature)
- [ ] `curl -s "http://127.0.0.1:8000/api/v1/ocean/map?region=bay_of_bengal&date=2023-09-01&depth=75"` → `"status":"model_prediction"`
- [ ] `curl -s "http://127.0.0.1:8000/api/v1/ocean/profile?region=bay_of_bengal&date=2023-09-01&latitude=11.5&longitude=90"` → 15 depths `[0,5,10,20,30,50,75,100,125,150,200,300,500,700,1000]` and 15 temperatures
- [ ] Frontend responds: open `http://localhost:5173` and see the map paint

## C. Pre-flight on the running app (2 minutes)

- [ ] Browser: **1920×1080**, 100 % zoom, devtools **closed**, one tab only (`localhost:5173`)
- [ ] OS notifications / messaging apps silenced; no other windows on the recording display
- [ ] No terminal window visible on the recording screen (logs mention the DB path — irrelevant and noisy)
- [ ] `.env` / credentials file not visible anywhere (Copernicus credentials must never appear)
- [ ] Visit **Validation & Model** once, then back to **Ocean Explorer** (warms tiles + API cache)
- [ ] Banner is **teal**: `Live model · Served by the hybrid_v1 inference service.` (fresh inference) **or** `Served from cache · Same result from a recent request (60 s TTL).` — both verified. Amber `Demo data` or red `Unavailable` = not ready.
      *Tip:* if you want the first frame to read `Live model`, wait >60 s after your last pre-flight interaction, then reload the page immediately before recording.
- [ ] Header badge = `Research prototype · Historical reconstruction`; footer = `Modeled reconstruction; trained on data through 2023-12-31.`
- [ ] Region select = `bay_of_bengal`, date select = `2023-09-01`, depth rail active = `100`, and the rail lists `Surface 5 10 20 30 50 75 100 125 150 200 300 500 700 1000`
- [ ] Map stats line = `100 m · 3,841 valid ocean cells · 0.25° grid · 2023-09-01`
- [ ] Legend = `18.0 23.1 28.1 °C`
- [ ] Console: **0 errors** (check now, while devtools are allowed)
- [ ] Feature spot-check (each must behave as described — details in `DEMO_CLICK_PATH.md`):
  - [ ] hover mid-basin → read-out appears (`11.50°N, 90.00°E` / value / depth)
  - [ ] click that cell → popup `27.71 °C ±1.18` at 75 m + profile panel opens
  - [ ] profile chart: 15 markers, y-axis `0 250 500 750 1000`, thermocline visible
  - [ ] `Exact values` toggle → 15 rows, `0 m 29.2°C ±1.46` … `1000 m 6.5°C ±0.25`
  - [ ] `Uncertainty` at **75 m** → legend `1.0 2.7 4.4 ±1σ · °C` (not stretched to a huge max)
  - [ ] Validation page → `285 of 291 ARGO profiles matched (3,958 depth observations)`, `RMSE 1.35 °C`, `Bias 0.61 °C`, `Correlation 0.990`, RMSE bar chart rendered
- [ ] Rehearse the full click path **once with a stopwatch**; target 57–63 s
- [ ] Recording software: 1080p, 60 fps, full-screen browser window; mic level checked; script on a second device (never on the recording screen)

## D. During the take

- [ ] Follow `DEMO_CLICK_PATH.md` exactly: 6 clicks + 1 hover + 1 scroll — no extra clicks
- [ ] Move the mouse **slowly**; stop moving while speaking a number
- [ ] Pause ~0.5 s after every visual change (layer toggle, depth change, tab switch, popup)
- [ ] Never wait visibly for an API; every fetch is pre-warmed and resolves in well under a second
- [ ] Keep the selected cell consistent: the popup, the profile panel and the read-out must all show `11.50°N, 90.00°E`
- [ ] Do not touch: Region select, Date stepper, Reset view, zoom/pan (see the "do not click" table)
- [ ] Watch the banner: teal is good either way. If it turns **amber (`Demo data`)** or **red (`Unavailable`)**, the ML service died — stop the take. Do not narrate a banner change
- [ ] Watch for red/amber banners, "No profile here", or a blank map — any of those means stop and re-run §B

## E. After the take

- [ ] Audio: levels consistent, no clipping, no room noise, no notification sounds
- [ ] Readability: on a 1080p playback, the popup, the profile y-axis labels (`0…1000 m`) and the ARGO numbers are legible
- [ ] Every spoken claim cross-checked against `DEMO_FEATURE_AUDIT.md` §8 — no ad-libbed metric
- [ ] No forbidden wording anywhere in the audio: "real-time", "live data", "forecast", "95%", "accuracy 99%", "pure satellite", "Arabian Sea", "global", "replaces ARGO", "better than GODAS"
- [ ] Duration 57–63 s
- [ ] Screen shows **only** 2022–2023 dates (never a 2026 date); the footer honesty line appears at least once
- [ ] No secrets, tokens, API keys, `.env` contents, emails or terminal output visible in any frame
- [ ] No fake UI state: every value on screen is a real model/cache output for 2023-09-01
- [ ] File named and stored, e.g. `oceanembed-sih26066-demo-final.mp4`; keep the project tree clean (no stray screenshots/scripts committed)

## F. Known friction to handle (verified this session)

| Friction | Handling |
|---|---|
| The ARGO panel sits ~855 px down the Validation page | One deliberate scroll during the 53–58 s beat (see click path step 11). The panel then fills the viewport. |
| Returning to the Explorer remounts the Leaflet map | Warm both tabs pre-flight; if the basemap flashes, hold ~0.5 s before speaking. |
| "Live model" / "Served from cache" banner wording | Both describe the serving path (live inference service vs. its 60 s response cache) — never the data vintage. The take can legitimately show either mid-record (observed this session): do not react, do not edit, and never say "live data" or "real-time". |
| σ outlier cells at 0–30 m / 100 m / 125 m | Shoot the uncertainty beat at **75 m** (σ 1.0–4.4 °C). The σ values are the model's raw output — do not "fix" them. |
| Temperature-axis tick labels are non-round (e.g. `5.3 12.3 19.3 32.4`) | Cosmetic, pre-existing; do not zoom into the tick labels on camera. The depth axis (the SIH26066 output) reads cleanly `0 250 500 750 1000 m`. |
| Profile chart depth scale | Fixed and correct (15 markers at true proportional depths). Do not "help" the presenter by describing points as evenly spaced. |

## G. Hard disqualifiers (never do these)

- [ ] ❌ No invented dataset, date, metric or capability
- [ ] ❌ No Copernicus credential or `.env` content on screen
- [ ] ❌ No claim of real-time / forecast / operational capability
- [ ] ❌ No claim that only the Bay of Bengal is "supported" while showing another region as available — and no other region shown at all
- [ ] ❌ No editing a broken take's numbers in post; re-record instead
