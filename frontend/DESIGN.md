# DESIGN.md — OceanEmbed Subsurface Ocean Explorer

> Single source of truth for the frontend design system.
> Mirrors `docs/superpowers/specs/2026-09-06-oceanembed-dashboard-design.md` §7.
> Every component must reference these tokens; do not invent ad-hoc colors/
> spacing/radius/motion in components.

---

## 1. Design Read (taste-skill brief inference)

**Reading this as:** a trust-first scientific ocean-data exploration tool for
climatologists, oceanographers, and INCOIS-style analysts; calm, precise,
technical language; data-dictated layout; restrained motion that
communicates state.

**This is a data tool, not a marketing page.** Taste-skill landing-page
blocks (heroes, marquees, scroll hijack, bento) do not apply. Its discipline
does: no AI-slop gradients, one design system per project, color/type/shape
locks, WCAG AA contrast, `prefers-reduced-motion` support, motivated motion.

**Dials:** `DESIGN_VARIANCE: 4` · `MOTION_INTENSITY: 4` · `VISUAL_DENSITY: 5`.

---

## 2. Typography

| Role | Font | Weight | Size / Line-height | Notes |
|------|------|--------|--------------------|-------|
| Display / headings | `Inter` (system-adjacent, Latin + °C glyphs) | 600 | H1 `text-2xl`, H2 `text-xl`, H3 `text-lg` | Data tool: no oversized display type. Tight `tracking-tight`. |
| Body / UI | `Inter` | 400 / 500 | `text-sm` / `text-base`, `leading-relaxed` | Muted for secondary, high-contrast for primary. |
| **Numeric readouts** | `ui-monospace` / `SFMono-Regular` stack | 500 | `text-sm tabular-nums` | **All numbers (temp, coords, depth, RMSE, sigma) are mono + `tabular-nums`.** |
| Labels / eyebrows | `Inter` | 500 | `text-xs uppercase tracking-wider` | Used sparingly (≤1 per 3 sections); badges/banner labels. |

- Font stack: `Inter, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`
  (Inter via `@fontsource` or bundled; no runtime Google Fonts fetch, offline
  demo must render).
- Mono stack: `ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas,
  monospace`.
- No serif anywhere (data tool).

---

## 3. Color

One palette. One accent. Two themes (light + dark) via Tailwind `dark:`
variant. **No pure black / pure white** (use `zinc-950` / `zinc-50`).

### Accent (single, locked)
- **Teal** — scientific, calm, used for ALL interactive intent + focus rings.
  - Light: `teal-700` (#0f766e) for text/interactive; `teal-600` fill.
  - Dark: `teal-400` (#2dd4bf) for text/interactive; `teal-500` fill.

### Neutrals
- Light theme: background `zinc-50`, surface `white`, border `zinc-200`,
  text-primary `zinc-900`, text-muted `zinc-500`, text-secondary `zinc-700`.
- Dark theme: background `zinc-950`, surface `zinc-900`, border `zinc-800`,
  text-primary `zinc-50`, text-muted `zinc-400`, text-secondary `zinc-300`.
- **Never mix zinc neutrals with slate/stone.** One neutral family only (zinc).

### Semantic (status)
| Token | Light | Dark | Used for |
|-------|-------|------|----------|
| Success | `emerald-600` | `emerald-400` | status `model_prediction` |
| Info | `sky-600` | `sky-400` | status `cached_data` |
| Warning | `amber-600` | `amber-400` | status `fallback_demo` |
| Error | `red-600` | `red-400` | status `unavailable`, inline errors |

### Map palettes (function-specific, separate from UI tokens)
- **Temperature layer:** hand-rolled viridis-style continuous scale
  (dark purple → blue → teal → green → yellow), null → **transparent**.
- **Uncertainty layer:** hand-rolled yellow → orange → red continuous scale
  (low sigma = yellow, high sigma = red), null → transparent.
- These are data-viz palettes, not UI accent; they coexist with teal accent
  (temp palette already contains teal/green; do not color UI chrome with
  viridis colors).

---

## 4. Spacing & layout

- **4px grid** (Tailwind default scale as-is: `1,2,3,4,5,6,8,10,12,16,...`).
- App shell: `max-w-[1400px] mx-auto px-4 md:px-6 py-4`, `min-h-[100dvh]`
  (NEVER `h-screen`).
- Map panel + profile/validation panels: `gap-4` gutter; panels are surfaces
  with `border` + 1px, not always cards (cards only where elevation earns it).
- Section spacing: `space-y-4` / `space-y-6`; py-16 max for app sections (data
  tool — no art-gallery whitespace, no cockpit cram).

---

## 5. Border & radius

- **One radius scale (locked):**
  - Interactive controls (buttons, selects, inputs): `rounded-md` (0.375rem).
  - Panels/cards/map container: `rounded-lg` (0.5rem).
  - Badges/pills: `rounded-full`.
- Borders: 1px `border-zinc-200` (light) / `border-zinc-800` (dark).
- **Focus ring (mandatory, WCAG visible):** 2px `ring-2 ring-teal-600/40
  ring-offset-2` (light) / `ring-teal-400/40` (dark), on every keyboard
  focusable element.

---

## 6. Elevation & shadows

- Shadows tinted to theme base; **no pure-black drop shadows.**
  - Light: `shadow-sm` with `shadow-zinc-900/5` for elevated panels.
  - Dark: `shadow-md` with `shadow-black/40`.
- Most panels use `border` instead of shadow (data tool); shadow only for
  overlays/tooltips/popovers.

---

## 7. Component states

- **Button (shadcn `button`):**
  - Default: teal accent fill (primary) OR `ghost`/`outline` variant.
  - Hover: `brightness-110` or bg-shift; Active: `scale-[0.98]` (tactile).
  - Disabled: `opacity-50 pointer-events-none`.
  - **Contrast gate:** button text must pass WCAG AA (4.5:1) vs its fill;
    never white-on-white or transparent-on-page.
- **Select / Input (shadcn):** label ABOVE input (never placeholder-as-label);
  focus ring per §5; error text below input in `text-red-*`.
- **Status banner:** full-width, tinted bg + border in semantic color (§3),
  icon + short label + detail text; slides in (motion §8).
- **Loading:** skeletons matching final layout shape (shadcn `skeleton`) —
  NO circular spinners as primary feedback.
- **Empty states:** composed, honest (e.g. "No data for Arabian Sea within
  demo scope" with action), not a bare "No data".
- **Error states:** inline, contextual, clear recovery action.

---

## 8. Motion (GSAP — motivated only)

**Principle:** every animation must communicate state transition, hierarchy,
or feedback. If you cannot justify it in one sentence, drop it.

- Library: `gsap` + `@gsap/react` `useGSAP` hook (auto-cleanup via
  `ctx.revert()`), scoped refs only (no global selectors).
- Allowed transitions (MOTION_INTENSITY 4):
  1. **Layer crossfade:** temperature ↔ uncertainty map layers — 400ms
     opacity fade, no movement.
  2. **Profile draw-in:** depth-vs-°C line + ±band — 500ms opacity + slight
     `y` on first render of a new cell/depth.
  3. **Validation rows stagger:** 300ms opacity stagger (max 100ms/row).
  4. **Status banner slide:** 250ms `y: -8 → 0` + opacity.
- Timing: `ease: "power2.out"`, durations 250–500ms. No spring overshoot in a
  data tool.
- **`prefers-reduced-motion: reduce`** → collapse to `opacity: 1` instantly
  (no transform, no stagger). Non-negotiable.
- **Never** mix GSAP with Framer Motion/react-spring in the same tree.
- **Never** `window.addEventListener("scroll")` — nothing scroll-scrubbed in
  this app by design.

---

## 9. Dark / Light theme policy

- Both themes designed + tested; **default follows `prefers-color-scheme`**,
  manual toggle in header.
- Tailwind `dark:` variant is the single mechanism (no separate theme lib).
- Do not ship a page only verified in one mode.

---

## 10. z-index scale (documented, no arbitrary z-50 spam)

| Layer | Value |
|-------|-------|
| Base content | `0` |
| Sticky header / controls | `10` |
| Map overlays, tooltips, popovers | `20` |
| Status banner (top, non-blocking) | `30` |
| Modal / dialog | `50` |

---

## 11. Copy & honesty (scientific integrity)

- No em-dashes in UI copy. Use commas/parentheses/periods.
- Static honest footer: *"Modeled reconstruction; trained on data through
  2023-12-31."*
- Status labels: `model_prediction` → "Live model", `cached_data` → "Served
  from cache", `fallback_demo` → "Demo data", `unavailable` → "Unavailable".
- No cyclone/tsunami/forecast claims. "Explain this location" shows real API
  numbers only (predicted °C, ±sigma, depth-wise ARGO RMSE), never invented.