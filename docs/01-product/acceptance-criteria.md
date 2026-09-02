# Acceptance Criteria

Objective conditions for declaring features complete. IDs reference `docs/01-product/product-requirements.md`.

> **MVP milestone — Copernicus Connection Proof** (highest priority, stage-gate):
> 1. `copernicusmarine` installed and authenticated (backend, server-side).
> 2. `describe()` discovers current datasets for SST, SSS, SSH/SLA, current U/V, wind U/V.
> 3. Dataset verification report exported.
> 4. One verified SST dataset → one day → Bay of Bengal → NetCDF opens with expected
>    dimensions/variables/units/min/max/NaN%. Same repeated for Arabian Sea.

## Definition of done (converted from SYSTEM_MEMORY_DUMP.md §147)

### Data pipeline
- [ ] D1 — Copernicus authentication works.
- [ ] D2 — Current datasets are discovered programmatically (`describe()`).
- [ ] D3 — Dataset metadata is recorded (manifest/registry).
- [ ] D4 — Bay of Bengal regional data retrievable.
- [ ] D5 — Arabian Sea regional data retrievable.
- [ ] D6 — Seven surface inputs harmonized to a common grid.
- [ ] D7 — Data standardized to daily / 0.25°.
- [ ] D8 — GLORYS target available (dense training/reference target).
- [ ] D9 — 15-depth target tensor constructed.
- [ ] D14 — Raw data cached; provenance recorded.

### ML
- [ ] M1 — CNN baseline architecture implemented (inputs `[B,7,H,W]`, outputs `[B,15,H,W]`).
- [ ] M2 — Train/validation/test split respects temporal ordering (RULE 10).
- [ ] M3 — Normalization statistics computed from training data only (RULE 11).
- [ ] M4 — RMSE computed.
- [ ] M5 — Bias computed.
- [ ] M6 — Correlation (Pearson) computed.
- [ ] M7 — Depth-wise metrics displayed.
- [ ] M8 — Baselines (climatology + simple CNN) available for comparison.
- [ ] M9 — Model version recorded with checkpoint manifest.

### Application
- [ ] A1 — Model inference works via backend service.
- [ ] A2 — Map works (region + date + depth → temperature map).
- [ ] A3 — Grid-cell click works.
- [ ] A4 — Vertical profile works (15 depths).
- [ ] A5 — ARGO validation demonstrated where data permits (never fabricated).
- [ ] A6 — Copernicus credentials server-side only.
- [ ] A7 — Fallback demo dataset exists.
- [ ] A8 — Final presentation explains scientific validity (baseline comparison, leakage controls, provenance).

## Quality gates
- Backend/ML line coverage ≥ 80%.
- Contracts updated whenever interfaces change; `scripts/verify-contracts.py` passes in CI.
- No secrets, datasets, or checkpoints staged (gitleaks CI + CODEOWNERS review).
- Applied migrations never edited (RULE 15).