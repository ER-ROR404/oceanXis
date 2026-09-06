# OceanEmbed Dashboard — Design Spec (Subsurface Ocean Explorer)

> **Status:** APPROVED (2026-09-06) — brainstormed and confirmed with the product owner.
> **Audience:** implementation (Phase 5 of `plans/backend-frontend-demo-build.md`).
> **Relationship:** this spec REFINES (does not replace) the ADR-011 LOCKED
> 3-mode product vision in `docs/01-product/product-vision.md` and
> `docs/01-product/user-workflows.md`. It adds audience-tiering, an honest
> trust snapshot, and a deterministic "Explain this location," and it records
> one concrete contract-and-data gap (uncertainty surfacing).

---

## 1. Purpose

Build the **Subsurface Ocean Explorer** — the primary user-facing deliverable of
OceanEmbed and the centerpiece of the SIH 2026 demo. It is a *scientific data
product*, not a generic AI dashboard. Every screen answers one of five
questions the target users actually ask:

1. **Where?** — the map.
2. **How deep?** — the depth selector.
3. **What is happening below the surface?** — the vertical profile.
4. **Can I trust it?** — calibrated uncertainty + status.
5. **How do you know?** — aggregate ARGO validation.

---

## 2. Audience & gap analysis (grounded in research)

Three primary user groups. The design is **scientist-first**; operators and
decision managers get a lightweight honest layer, not a separate product.

| Audience | Currently uses | Gap OceanEmbed fills | OceanEmbed surface |
|----------|----------------|----------------------|--------------------|
| **Ocean scientist / researcher** | Argovis, INCOIS Live Access Server, Marine Argo Atlas, last-mile Python | No gap-free reconstructed subsurface field (0–1000 m, 15 depths) to interrogate anywhere, with calibrated uncertainty and honest validation | Full 3-mode explorer: map → profile → validation → explain |
| **INCOIS / operational analyst** | Ocean State Forecast (OSF), SAMUDRA (surface waves/currents/winds; 5-day forecast; PFZ) | OSF is **surface + wave/current + forecast**; no deep 0–1000 m thermal reconstruction with confidence | Region/date/depth snapshot + uncertainty + honest trust strip |
| **Disaster / decision manager** | OSF bulletins, warnings | Sparse interpretation of deep, uncertain thermal state; needs one-glance confidence | Honest high-level strip; no disaster claims |

**Terminology adopted verbatim from the domain (users already understand these):**
region, date, depth (m), temperature (°C), latitude / longitude, profile,
uncertainty / confidence, mixed layer, thermocline, ARGO, RMSE, bias,
correlation, validation. **No invented jargon.**

**Differentiation (from research):** several competing tools (FloatChart,
Atlas-argo) lean on an LLM chat assistant. OceanEmbed deliberately uses a
**deterministic** "Explain this location" — no chatbot (this is also a LOCKED
"what not to build" in product-vision.md). Reused the well-tested **Argovis
pattern** (Leaflet map → click a cell → coordinates + profile) because it is
already what ocean scientists expect.

### Honest-framing constraints (RULEs 4, 21, and product-vision "what not to build")

- We do **NOT** claim cyclone / tsunami / operational nowcast/forecast. The UI
  says: *"subsurface ocean thermal intelligence that can support downstream
  ocean and disaster-management analysis."*
- The data is **not realtime**: trained on data through `2023-12-31`; demo
  cache is 2023 dates. Every page carries a static honest footer: *"Modeled
  reconstruction; trained on data through 2023-12-31."*
- We do **NOT** render a fake spatial error map or cell-exact ARGO overlay from
  data we do not have. Validation is **aggregate depth-wise** ARGO only
  (from `frontend/src/assets/validation/argo_validation_summary.json`, Phase 4).

---

## 3. The five questions → surface mapping

| Question | Surface | Data source |
|----------|---------|-------------|
| Where? | Interactive Leaflet map of the region | `/ocean/map` (coordinates grid, `values[][]`, null land) |
| How deep? | Depth selector (15 canonical depths) | `/ocean/map` depth param |
| Below the surface? | Vertical profile chart (depth vs °C, y reversed, 0 m top) | `/ocean/profile` |
| Can I trust it? | Uncertainty layer on map + ±95% band on profile + status banner | **NEW:** `sigma`/`log_var` in map+profile payloads |
| How do you know? | ARGO validation panel (depth-wise RMSE/bias/corr, limitations, coverage) | `argo_validation_summary.json` |

---

## 4. Layout & controls

```
OCEANEMBED · Subsurface Ocean Explorer        [● ready · modeled data]
Region [bay_of_bengal▼]  Date [03 Sep▼]  Depth [100 m▼]  Layer [Temperature▼|Uncertainty]
[ ----------------------------------------------------------------------- ]
[   Interactive map (Leaflet) — 0.25° reconstructed field                  ]
[   Temperature layer: viridis-style; null land transparent                ]
[   Uncertainty layer: sigma field                                         ]
[   ● selected cell → click → opens profile                                ]
[ ----------------------------------------------------------------------- ]
Selected cell: 15.25°N, 87.50°E
[ Temperature profile + ±95% band ]  [ Explain this location ]  [ ARGO validation ]
[ Honest trust strip: region condition + confidence + "illustrative, not operational forecasting" ]
```

- **Status banner** driven by `PredictionEnvelope.status` from
  `prediction.schema.json`:
  - `model_prediction` — green "live model"
  - `cached_data` — blue "served from cache"
  - `fallback_demo` — amber "demo data"
  - `unavailable` — red error, `error.code` message
  - Tooltip surfaces `channel_status`.
- **Footer (static):** *"Modeled reconstruction; trained on data through
  2023-12-31."*

---

## 5. Modes (scientist-first core + trust strip)

### Mode 1 — Spatial exploration
Region → Date → Depth; layer toggle **Temperature / Uncertainty**.
The map redraws on changing depth; clicking a cell transitions to mode 2.

### Mode 2 — Profile investigation
Click a grid cell → header with coordinates + date + status; depth-vs-°C
chart with the ±95% uncertainty band (95% ≈ 1.96·sigma). Null depths render
as **gaps, never a 0-line** (correctness invariant). Where validation exists
for that depth, an ARGO marker/metric is shown (aggregate, not cell-exact).

### Mode 3 — Validation / trust
ARGO panel importing `argo_validation_summary.json` (Phase 4): overall card
(RMSE/bias/corr), per-depth table, ARGO coverage count (285/291 matched),
and the **limitations callout** (thermocline warm bias up to +2.2 °C at
75–150 m; depth-0 n=25).

### "Explain this location" (deterministic, no LLM)
For the selected cell + depth, generate a scientific summary **entirely from
actual outputs**, e.g. (values illustrative, shown only to convey shape):

> 15.25°N, 87.50°E — 100 m. Predicted temperature 21.8 °C, estimated
> uncertainty ±1.2 °C. ARGO validation available at this depth; local depth-wise
> RMSE ≈ 2.6 °C (from the committed aggregate summary).

Every number rendered is a real API or committed-summary value, never
model-derived prose invented by an LLM.

### Honest trust snapshot (operators + decision managers)
For the selected region/date/depth: the field's overall temperature, a
mean-confidence readout for the current view, and the static line:
*"Illustrative reconstruction for [date]; not operational forecasting."*
No cyclone/tsunami/alert language anywhere.

---

## 6. Data & contract requirements

### Currently available (build on these)
- `/ocean/map` → temperature grid; `null` land cells.
- `/ocean/profile` → 15 depths; `null` where unavailable.
- `argo_validation_summary.json` → aggregate depth-wise metrics.
- `PredictionEnvelope` status taxonomy → honest UI states.

### **NEW contract-and-backend work required (the one real gap)**
Expose **uncertainty** in the public API so the uncertainty layer and profile
±band can be rendered from real data (never fabricated):
1. ml `/predict` already returns `mu` + `log_var`. Define the public field as
   **`sigma`** (the standard deviation, `sqrt(exp(log_var))`), which is the
   display-ready form. `log_var` stays internal to ml; `sigma` is the contract
   field exposed to the API.
2. Contract update(s) to add **`sigma`** to:
   - `contracts/api/ocean-map.schema.json` (sigma grid at each depth), and
   - `contracts/api/ocean-profile.schema.json` (sigma at each depth).
3. Backend `build_map_payload` / `build_profile_payload` + `envelope.py` to
   pass sigma through (derived from `log_var` via `sqrt(exp(log_var))`);
   `InferenceClient` to validate it.
4. Its own tests (schema conformance + null handling + regression).

> Out of scope (honest): cell-located ARGO overlay, spatial prediction-error
> map (no committed per-cell error field), LLM/chatbot, realtime frame. These
> are explicitly documented as deferred / not built.

---

## 7. Architecture & tech (respects existing Phase 5 plan)

**Design stance (taste-skill read):** *"A trust-first scientific ocean-data
exploration tool for climatologists and INCOIS-style analysts, with a calm,
precise, technical language."* Dial values: `DESIGN_VARIANCE 4` (offset,
data-dictated layout), `MOTION_INTENSITY 4` (motivated state transitions only),
`VISUAL_DENSITY 5` (data tool; numbers in mono). This is a **data tool, not a
marketing page** — taste-skill's landing-page blocks do not apply; its
discipline (no AI-slop, one design system, color/type lock, contrast,
reduced-motion, motivated GSAP) does.

- **Stack:** React + TypeScript + Vite (greenfield `frontend/`).
  - **Styling:** Tailwind CSS v4 (`@tailwindcss/vite` plugin — NOT the
    `tailwindcss` postcss plugin). One design system per project: shadcn/ui
    (code-owned components via `npx shadcn@latest`) — the correct choice for a
    React + Tailwind data tool. No other UI framework mixed in.
  - **MCPs:** `magic` (`@magicuidesign/mcp`) + `shadcn`
    (`@magnusrodseth/shadcn-mcp-server`) enabled for component source
    (added to `~/.config/opencode/opencode.json`; requires opencode restart
    to take effect). `GITHUB_TOKEN` is optional (public access works; token
    raises GitHub rate limits).
  - **Animation:** GSAP (`gsap` + `@gsap/react` `useGSAP` hook) for
    **motivated** transitions only: layer crossfade on map, profile draw-in,
    staggered reveal of validation rows, status-banner slide. Every animation
    must answer "what does this communicate?" (state transition / hierarchy /
    feedback). No decorative marquees, no scroll hijack, no infinite loops.
    `prefers-reduced-motion` collapses to opacity-only or none.
  - **Runtime deps (minimal, RULE 16):** `react`, `react-dom`, `leaflet`,
    `recharts`, `gsap`, `@gsap/react`, `tailwindcss`, `@tailwindcss/vite`,
    `class-variance-authority`, `clsx`, `tailwind-merge`, `lucide-react`
    (icons; ONE family).
- **Typed client** (`src/api/client.ts` + `src/types/contracts.ts`): TS types
  mirroring the contract schemas; typed `getHealth`, `getHistory`, `getMap`,
  `getProfile`, `getMetadata`, `getModelVersion`; centralized `error.schema.json`
  envelope decode → typed `ApiError`; `PredictionEnvelope` discriminated on
  `status` → distinct banners.
- **Map panel:** Leaflet over the region bounds; raster overlay from
  `values[][]` with null→transparent; hand-rolled continuous viridis-style
  color scale (no new dep); click cell → lat/lon → profile; depth selector;
  date slider bound to `/ocean/history`; region dropdown (`arabian_sea`/
  `north_indian_ocean` → honest "no data in demo scope" 404 banner). Layer
  toggle Temperature / Uncertainty crossfades via GSAP.
- **Profile panel:** Recharts depth-vs-°C, y reversed; ±95% band from sigma;
  null→gap only; line draw-in via GSAP.
- **ARGO panel:** imports the committed JSON; renders table + overall +
  limitations with a restrained stagger reveal.
- **Layout:** app header (name + model version + health dot), status banner,
  router (Map / Validation), honest footer. shadcn/ui primitives (Button,
  Card, Select, Badge, Table) skin the whole app; tokens in
  `frontend/DESIGN.md` (single source of truth for color, type, spacing,
  radius, elevation, motion).

---

## 8. Testing (TDD, ≥80%)

- Unit: typed client decode paths (live/cached/fallback/unavailable → typed
  results; error envelope → ApiError), color scale, sigma-band derivation,
  null handling.
- Integration/component: map renders field + skips null pixels; profile
  renders ±band + null gaps; ARGO table renders rows; status banner variants;
  honest states (404 arabian_sea, unavailable).
- Animation: GSAP `useGSAP` contexts use scoped refs + `ctx.revert()`
  cleanups; `prefers-reduced-motion` collapse tested (no orphaned
  ScrollTriggers/tweens; jsdom stubs where needed).
- Real-stack E2E: `GET /ocean/map` + `/ocean/profile` (with sigma) through the
  actual app; verify uncertainty present and honest.
- Every 200 response validated against its contract schema (RULE 6).

---

## 9. Acceptance criteria

- `npm run build` + `tsc --noEmit` + vitest green; coverage ≥ 80%.
- Manual walkthrough: map renders BoB temp at depth 100 for a demo date; click
  → 15-depth profile with ±band; uncertainty layer toggle works; ARGO panel
  numeric; "Explain this location" shows real numbers + ±; status banner shows
  `model_prediction`; `arabian_sea` shows honest no-data state; honest footer
  present; no forecast/cyclone claims.
- Uncertainty (`sigma`) present and contract-validated in both map and profile
  responses.
- **Design-system conformance** (taste-skill pre-flight, adapted to a data
  tool): one accent color used identically across the app; one radius scale;
  all numeric readouts in mono; WCAG AA contrast on all interactive controls;
  `min-h-[100dvh]` (never `h-screen`); no decorative/looping motion; no
  em-dashes in UI copy; two themes (light + dark) designed and tested; empty/
  loading/error states present; cards used only where elevation earns them.

---

## 10. Open items / decisions already made

- Uncertainty surfacing is **required** (a small contract + backend + ml
  change) — accepted and flagged, not hidden.
- Cell-located ARGO and spatial error maps: **deferred / not built** (honest).
- "Explain this location" is **deterministic** (no LLM) — this is the chosen
  differentiator.
- **Design system:** documented in `frontend/DESIGN.md` (read first, enforced
  during build) — tokens for type/color/spacing/radius/elevation/motion,
  plus taste-skill discipline adapted to a data tool.
- **MCP servers** `magic` + `shadcn` enabled in `~/.config/opencode/
  opencode.json` (requires opencode restart to take effect in-session).
  Component source fetched via these MCPs during Phase 5; component code is
  owned (checked in), not a runtime dependency.
