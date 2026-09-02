# Scientific Assumptions

> Physical and scientific assumptions used by preprocessing and modeling.
> Status markers: LOCKED / CONFIRMED / PROPOSED / UNRESOLVED.
> Every claim must be traceable to data or a documented assumption (Golden Rule 21).

## Assumptions

| # | Assumption | Type |
|---|-----------|------|
| A1 | The surface ocean state contains indirect, physically meaningful signatures of subsurface thermal structure | LOCKED (core problem premise) |
| A2 | The surface→subsurface mapping is nonlinear, spatially/temporally variable, depth-dependent, physically constrained, and partially ill-posed | CONFIRMED (scientific consensus in problem framing) |
| A3 | Learned latent representations are a reasonable strategy for this inversion (vs trivial interpolation) | PROPOSED |
| A4 | GLORYS is a suitable dense training/reference target; ARGO provides independent validation | LOCKED (problem statement) |
| A5 | Skill is expected to be stronger near the surface and weaker with depth | PROPOSED (to be measured, not assumed; §92) |
| A6 | Aggressive image-style augmentation is scientifically invalid for ocean grids (geography/physics) | LOCKED rule (Golden Rule 8) |
| A7 | Missing values are handled via validity masks; never blind zero-fill | LOCKED rule (§36) |
| A8 | Current products may be multi-source (incl. model-derived Ekman components) and must be disclosed; not "pure satellite" | CONFIRMED for candidate products — re-verify per dataset | 
| A9 | Interpolation of large missing ocean areas should not be performed blindly | LOCKED rule (§109) |
| A10 | Temporal cohesion of the training stack (no unverified NRT/reprocessed mixing) | LOCKED rule (§83–§84, §127) |
| A11 | No physical temperature bounds imposed unless documented and scientifically justified | CONFIRMED policy (§125) |
| A12 | 0.25° daily grids capture the mesoscale/thermocline signal relevant to the MVP | PROPOSED (baseline assumption) |

## Non-assumptions (explicitly rejected)

- Random spatial/temporal splits are valid (REJECTED — ADR-007).
- Temperature decreases monotonically with depth (REJECTED as a constraint; §24).
- "Satellite-only" labeling of multi-source current products (REJECTED — A8).
- Real-time/operational claims without latency verification (REJECTED — §129).