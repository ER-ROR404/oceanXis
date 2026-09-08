# Phase 5 Frontend Build Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the OceanEmbed Subsurface Ocean Explorer frontend (React + TS + Vite + Tailwind v4 + shadcn/ui + Leaflet + Recharts + GSAP) adhering strictly to `frontend/DESIGN.md`, contracts, and the approved design spec.

**Architecture:** Client-side React SPA communicating with FastAPI backend `/api/v1`. Strict separation of concerns: Map panel, Profile panel, ARGO validation panel, status banners, and deterministic "Explain this location" generator.

**Tech Stack:** React 18, TypeScript, Vite, Tailwind CSS v4, shadcn/ui primitives, Leaflet (map), Recharts (profile + ±95% band), GSAP (`@gsap/react` `useGSAP` for motivated transitions), Vitest + React Testing Library.

**Spec:** `docs/superpowers/specs/2026-09-06-oceanembed-dashboard-design.md` and `frontend/DESIGN.md`.

## Global Constraints

- Never access Copernicus credentials or call Copernicus directly (RULE 1, 2).
- All numbers rendered in UI must use monospace font + `tabular-nums`.
- GSAP animations restricted to **motivated state transitions** only (layer crossfade, profile draw-in, validation stagger, status slide); must respect `prefers-reduced-motion`.
- Zero em-dashes (`—`) in UI copy.
- Static honest footer present on all screens: *"Modeled reconstruction; trained on data through 2023-12-31."*
- Minimum line coverage target: 80%.

---

## Task Breakdown

### Task 1: Frontend Scaffold & Dependency Setup

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Test: `frontend/src/__tests__/app.test.tsx`

- [ ] **Step 1: Write package.json and config files**
- [ ] **Step 2: Install dependencies (react, react-dom, leaflet, recharts, gsap, @gsap/react, tailwindcss, @tailwindcss/vite, lucide-react)**
- [ ] **Step 3: Write initial test for App mounting**
- [ ] **Step 4: Run test to verify it passes**
- [ ] **Step 5: Commit**

---

### Task 2: Contract Update — Exposing Sigma (`sigma`) in Map & Profile APIs

**Files:**
- Modify: `contracts/api/ocean-map.schema.json`
- Modify: `contracts/api/ocean-profile.schema.json`
- Modify: `backend/app/api/v1/envelope.py`
- Modify: `backend/app/services/cache.py`
- Modify: `backend/app/services/inference_client.py`
- Test: `backend/tests/api/test_map.py`
- Test: `backend/tests/api/test_profile.py`

- [ ] **Step 1: Add `sigma` field to ocean-map and ocean-profile JSON schemas**
- [ ] **Step 2: Update backend envelope builders (`build_map_payload`, `build_profile_payload`) to compute and pass `sigma` (`sqrt(exp(log_var))`)**
- [ ] **Step 3: Update `DemoCache` and `InferenceClient` to parse and validate `sigma`**
- [ ] **Step 4: Run backend test suite and verify 130+ tests pass**
- [ ] **Step 5: Commit**

---

### Task 3: Typed API Client & Contract Validation

**Files:**
- Create: `frontend/src/types/contracts.ts`
- Create: `frontend/src/api/client.ts`
- Test: `frontend/src/api/client.test.ts`

- [ ] **Step 1: Write failing tests for typed client decoding (map, profile, history, error envelope status mapping)**
- [ ] **Step 2: Implement `client.ts` and `contracts.ts` mirroring backend contracts**
- [ ] **Step 3: Run vitest to verify tests pass**
- [ ] **Step 4: Commit**

---

### Task 4: Layout Shell, Status Banners & Honest Footer

**Files:**
- Create: `frontend/src/components/layout/Header.tsx`
- Create: `frontend/src/components/layout/StatusBanner.tsx`
- Create: `frontend/src/components/layout/Footer.tsx`
- Test: `frontend/src/__tests__/layout.test.tsx`

- [ ] **Step 1: Write tests for Header, StatusBanner (model_prediction, cached_data, fallback_demo, unavailable), and Footer**
- [ ] **Step 2: Implement layout components adhering to `frontend/DESIGN.md`**
- [ ] **Step 3: Run vitest to verify tests pass**
- [ ] **Step 4: Commit**

---

### Task 5: Map Panel (Leaflet + viridis + uncertainty layer + controls)

**Files:**
- Create: `frontend/src/components/map/OceanMap.tsx`
- Create: `frontend/src/components/controls/RegionDateDepthSelector.tsx`
- Test: `frontend/src/__tests__/map.test.tsx`

- [ ] **Step 1: Write tests for map rendering, cell click callback, layer toggle (temperature / uncertainty)**
- [ ] **Step 2: Implement Leaflet map integration with hand-rolled viridis/inferno color scales and GSAP crossfade**
- [ ] **Step 3: Run vitest to verify tests pass**
- [ ] **Step 4: Commit**

---

### Task 6: Profile Panel & "Explain This Location"

**Files:**
- Create: `frontend/src/components/profile/ProfileChart.tsx`
- Create: `frontend/src/components/profile/ExplainLocation.tsx`
- Test: `frontend/src/__tests__/profile.test.tsx`

- [ ] **Step 2: Implement Recharts depth-vs-°C chart with reversed y-axis, ±95% uncertainty band, and null-gap handling**
- [ ] **Step 3: Implement deterministic "Explain this location" card**
- [ ] **Step 4: Run vitest to verify tests pass**
- [ ] **Step 5: Commit**

---

### Task 7: ARGO Validation Panel & E2E Integration

**Files:**
- Create: `frontend/src/components/validation/ArgoValidationPanel.tsx`
- Create: `frontend/src/App.tsx` (wire up all tabs/modes)
- Test: `frontend/src/__tests__/e2e-explorer.test.tsx`

- [x] **Step 1: Write tests for ARGO summary table rendering and region 404 honest state**
- [x] **Step 2: Implement ArgoValidationPanel from `argo_validation_summary.json` asset**
- [x] **Step 3: Wire up App.tsx with full map → click → profile → ARGO workflow**
- [x] **Step 4: Run full vitest suite and build (`npm run build`)**
- [x] **Step 5: Commit** (077db1e)
