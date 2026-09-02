# Model Card

> Documentation of model purpose, limitations, data, metrics, risks, and intended use.
> Status: template/format. **Must be filled from real data and real evaluation — no fabricated
> values (Golden Rules 3, 4, 21).**

## Template

### Overview
- Model name / version (`model_version`).
- Task: surface → subsurface temperature reconstruction (15 depths).
- Problem: SIH26066 (OceanEmbed).

### Intended use
- Regional (Bay of Bengal / Arabian Sea) daily 0.25° subsurface temperature estimates.
- Complementary learned reconstruction pathway; **not** a replacement for GODAS/numerical models.

### Data
- Inputs: 7 surface channels (SST, SSS, SSH/SLA, current U/V, wind U/V).
- Target: GLORYS temperature at 15 depths (training/reference target).
- Validation: independent ARGO profiles.
- Dataset IDs/versions: see dataset registry (verified via `describe()`).

### Training / evaluation
- Temporal split (train/val/test periods).
- Metrics: per-depth RMSE, bias, correlation; baseline comparison.
- Uncertainty (if applicable): calibration method + validation.

### Risks & limitations
- Skill expected to degrade with depth (measure, don't assume).
- Missing/cloudy data handled via masks — gaps are reported, not fabricated.
- Multi-source current product includes model-derived components (disclosed, not "pure satellite").
- No real-time/operational claim without latency verification.

### Responsible-use notes / stewardship
- Provenance preserved; datasets verified; leaked-input audit performed.
- Maintained by `@oceanembed/ml`; reviewed per CONTRIBUTING.md.