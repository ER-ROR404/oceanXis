# Session Resume — OceanEmbed Phase 5 Frontend (2026-09-08)

> Live handoff point. Start a new session by reading this file, then the
> stack-start commands in §6. All work is committed; nothing pending except
> the branch integration decision in §2 and optional polish in §9.

## 1. Objective and status

Complete the OceanEmbed (SIH26066, "Subsurface Ocean Explorer") Phase 5
frontend to a polished, bug-free state and verify the full stack.

**Status: implementation COMPLETE and verified.**

- Frontend: 85 tests / 8 files green, coverage **97.92 stmts / 88.14 branch /
  93.33 funcs / 97.92 lines**, `npm run build` clean.
- Backend: 135 tests green, `app` coverage **95% lines**.
- Stack e2e: **10/10 checks** in real Chromium (browser -> Vite :5173 ->
  `/api` proxy -> FastAPI :8000 -> demo cache), zero page/console errors.

## 2. Git state and open decision

Branch `feat/phase5-frontend-completion`, base `main` (fork point `cb8a7ad`,
Task 5). Five branch commits, all pushed nowhere yet:

```
20c009c feat(frontend): Task 6 - depth profile with 95% uncertainty band and deterministic explainer
077db1e feat(frontend): Task 7 - wired Ocean Explorer app with end-to-end tests
3a7ec39 fix(backend): correct editable package layout
1fff68f fix(backend): history falls back to demo cache when model service is down
d532bc2 chore: mark Task 7 done in plan; add playwright devDep for stack e2e
```

**OPEN DECISION (awaiting user):** merge to `main` locally (1), push + PR (2),
or keep branch as-is (3). Use `skill: finishing-a-development-branch`.

Working tree is clean except `frontend/scripts/stack-e2e.mjs` +
`docs/superpowers/plans/2026-09-08-session-resume.md` (this handoff) which
should be committed when the session ends. Repo is ahead of origin:
`git push` for all branch commits + main at the end (user asked for push).

## 3. Where we are in the task list

- Done: Task 6, Task 7a/7b/7c, coverage gates, Task 7 commit, backend env
  unblock + 2 backend fixes, stack e2e, polish audit (em-dash 0, mono in use).
- Pending: branch integration decision (§2); optional polish (§9).

## 4. Honest constraints (do not "fix" these — they are the product)

- **No realtime data.** Reconstruction model trained through 2023-12-31.
  Only demo dates servable: 31 weekly dates 2023-06-01..2023-12-28
  (`artifacts/demo_cache/manifest.json`: hybrid_v1, epoch 83, val_loss 0.3714,
  grid 69x81, Bay of Bengal).
- **Demo scope = Bay of Bengal only.** `arabian_sea` / `north_indian_ocean`
  return honest "Unavailable — No demo data ... covers Bay of Bengal from
  ..." + "Return to Bay of Bengal" action.
- Frontend must never touch Copernicus (backend-only). ARGO = independent
  validation (panel shows RMSE 1.3533, bias 0.6121, corr 0.99 — committed
  asset). GLORYS subsurface never an inference input.
- Design: numbers mono (`font-mono-data`), zero em-dashes in src, honest
  footer "Modeled reconstruction; trained on data through 2023-12-31." on
  every screen. GSAP/leaflet animations reduced-motion gated.

## 5. Architecture facts (verified this session)

- API mounted at `/api/v1` (`backend/app/main.py:126`, `create_app()` factory —
  uvicorn MUST run with `--factory`).
- Routes: `/api/v1/health`, `/ocean/history`, `/ocean/metadata`,
  `/ocean/map?region&date&depth`, `/ocean/profile?region&date&latitude&longitude`,
  `/model/version`. Map/profile statuses: `model_prediction | cached_data |
  fallback_demo | unavailable`. Envelope + routes conform to
  `contracts/api/*.schema.json` (RULE 6).
- `/ocean/history` now falls back to `DemoCache.available_dates(region)`
  (same manifest as fallback_demo) when the model service is down — fixes
  the demo being stranded with zero dates (commit 1fff68f).
- Demo cache reader: `backend/app/services/cache.py` `DemoCache` (get_map /
  get_profile / available_dates; land = null, sigma mirrors values).
- Frontend: `src/hooks/useOceanExplorer.ts` owns all state incl. a monotonic
  `requestSeq` ref that guards stale history/map/profile responses race-free;
  `setRegion` resets date/dates/envelopes in one transactional commit.
  `src/App.tsx` wires Header, StatusBanner (optional `detail` prop), Region/
  Date/Depth selector, OceanMap (cell click -> nearest grid cell),
  profile section, ArgoValidationPanel, Footer, and skeleton/empty/error
  states (testids: map-skeleton, map-error-state, empty-region-state,
  selected-cell, field-caption, profile-skeleton).
- Vite proxy `/api` -> `http://localhost:8000`; ApiClient base
  `import.meta.env.VITE_API_BASE_URL ?? '/api/v1'` (tsconfig has
  `"types": ["vite/client"]`).
- Backend packaging: `backend/pyproject.toml` `[tool.setuptools.packages.find]`
  must keep `where = ["."]` + `include = ["app*", "scripts*"]` (the
  `where=["app"]` misconfiguration shipped zero packages — fixed 3a7ec39).

## 6. Starting the stack (resume commands)

Backend (from `backend/`):

```bash
uv run uvicorn "app.main:create_app" --factory --port 8000 --log-level warning
# detached: setsid nohup uv run uvicorn "app.main:create_app" --factory --port 8000 ... > /tmp/opencode/backend.log 2>&1 < /dev/null &
```

Frontend (from `frontend/`):

```bash
npm run dev   # http://localhost:5173, proxies /api to :8000
```

`GetContext` note: `uv run` from `backend/` uses/creates `backend/.venv`
(project env); the root `.venv` also has editable installs of all three
packages. Both work.

## 7. Test commands and results

```bash
# frontend (from frontend/)
npx vitest run                 # 85 tests / 8 files
npm run test:coverage          # 97.92/88.14/93.33/97.92
npm run build                  # tsc + vite, clean (chunk-size warning only)

# backend (from repo root or backend/)
uv run pytest backend/tests    # 135 passed

# stack e2e (from frontend/, backend :8000 + vite :5173 running)
node scripts/stack-e2e.mjs     # 10/10 checks; needs playwright@1.58.0 (=chromium-1208, cached)
```

Backend tests need `uv pip install -e backend -e data-engineering` once if
starting from a fresh `.venv` (and the package-layout fix in §5).

## 8. Session trap notes (avoid re-discovering)

- `edit` tool often throws `err.stdout.split is not a function` AFTER the edit
  applied — verify with grep/read, don't retry blindly.
- `pkill -f "uvicorn app.main"` matches the invoking shell's own cmdline and
  kills the session. Kill by port: `fuser -k 8000/tcp`.
- jsdom canvas: stubbed in `frontend/src/test/setup.ts` via
  `Object.defineProperty` on `getContext` AND `toDataURL` (jsdom's
  `toDataURL` returns `null` without the `canvas` package).
- Honest duplicate messages render in both StatusBanner AND panels — tests
  use `getByTestId('status-banner')` / `getByTestId('empty-region-state')`
  / `within()`, never bare `getByText` for those strings.
- `@vitest/coverage-v8` must be 2.1.9 (v5 requires vitest 5). Coverage config
  `include`/`exclude` replaces vitest defaults — keep `dist/` and test files
  excluded.
- Playwright: pin `1.58.0` (chromium revision 1208, matches local cache; never
  run `npx playwright install`).
- Region select options are lowercase labels: "bay of bengal", "arabian sea".
- ESM node scripts must live under `frontend/` (or set import path) so
  `import 'playwright'` resolves.

## 9. Remaining polish (all optional, all gated green)

- Chunk-size warning (>500 kB: leaflet + recharts + GSAP): lazy-load map/chart
  via `React.lazy` if desired. No functional gap.
- Backend deprecation warnings (jsonschema RefResolver, starlette anyio
  alias) — cosmetic, not blocking.
- Backend `.coverage`/pytest-cov report artifacts exist locally; not committed.

## 10. User context

- User asked to "complete the software with 0 bug, quickly", then to start the
  software for testing (it is running: :5173 + :8000), then to save this
  history for later resume without context loss.
- Branch finishing decision still open (§2) — present the 3-option menu
  (`finishing-a-development-branch` skill) and wait.
- This doc commits as part of Task-7-era work; delete stray `uv.lock` files
  (untracked artifacts) before `git status` cleanliness claims.