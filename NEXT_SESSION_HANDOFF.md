# NEXT_SESSION_HANDOFF.md

> **READ ME FIRST when a new coding session starts (2026-09-03 onward).**
> This is the continuity handoff so development resumes without confusion.
> Full evidence detail: `docs/work-log/2026-09-02-copernicus-validation.md`.

## Current Status (2026-09-04)
**Phase 2 COMPLETE** — data harmonization pipeline built, tested, committed.
**Phase 3 READY** — ML architecture spec v2.0 written and committed, awaiting line-by-line evaluator review.

### What exists today (committed):
- `data-engineering/src/oceanembed_data/` — catalog, regions, copernicus, harmonization (32+23+19+13 tests = 55 total)
- `scripts/build_training_dataset.py` — Zarr tensor assembly + normalization
- `scripts/download_historical.py` — chunked bounded-period downloads
- `data/tensors/bay_of_bengal/` — 1-day proof tensors (X: 1x7x69x81, Y: 1x15x69x81, 94.7% valid)
- `docs/superpowers/specs/2026-09-04-ml-architecture-design.md` — FULL ML architecture spec (evaluator-reviewed, 836 lines)

## What we PROVED today (Copernicus API validation — PHASE COMPLETE)
All **7 surface inputs + GLORYS target** verified live via `copernicusmarine` `describe()` +
`subset(dry_run=True)` (no big downloads) for **Bay of Bengal & Arabian Sea**.

| Channel | ✅ Selected dataset_id | variable |
|---------|------------------------|----------|
| SST | `METOFFICE-GLO-SST-L4-REP-OBS-SST` | `analysed_sst` |
| SSS (train/val) | `cmems_obs-mob_glo_phy-sss_my_multi_P1D`; test(2025)+prod → `...sss_nrt_multi_P1D` | `sos` |
| SSH/SLA | `cmems_obs-sl_glo_phy-ssh_my_allsat-l4-duacs-0.125deg_P1D` (NRT: `...ssh_nrt_...`) | `sla` |
| Current U/V | `cmems_obs-mob_glo_phy-cur_my_0.25deg_P1D-m` (NRT/analysis: `cmems_mod_glo_phy-cur_anfc_0.083deg_P1D-m`) | `uo`,`vo` |
| Wind U/V | `cmems_obs-wind_glo_phy_my_l4_0.125deg_PT1H` (NRT: `cmems_obs-wind_glo_phy_nrt_l4_0.125deg_PT1H`) | `eastward_wind`,`northward_wind` |
| GLORYS target | `cmems_mod_glo_phy_my_0.083deg_P1D-m` | `thetao` (0.49–5728 m; 15 canonical depths) |
| ARGO (validation) | raw ARGO GDAC profiles (preferred) / CORA-OA `cmems_obs-ins_glo_phy-temp-sal_my_cora-oa_P1M` (fallback) | `TEMP` |

## Decisions reached
- **Split (temporal, RULE 10):** train **2018–2023** / validation **2024** / test **2025**. **All channels
  verified GREEN across the entire split** (full matrix in work-log §5). Same day & location for all inputs.
- **Currents:** use MY observation currents for training (NOT the analysis product, which only spans 2022→).
- **Wind:** use MY L4 0.125° (2007→2026). (The 0.25° version ends 2009 — wrong one. The NRT L4 starts 2024-06.)
- **SSS test-year:** switch MY→NRT for 2025.
- **GLORYS = target ONLY** (never an input — avoid target leakage, RULE 8/RULE 9).

## OPEN items / decisions still needed from user
1. **Spec review:** User is reviewing `docs/superpowers/specs/2026-09-04-ml-architecture-design.md` line-by-line. Wait for approval before writing implementation code.
2. **Historical data download:** 2018-2023 training data not yet downloaded. Can run in parallel with Phase 3 architecture coding.
3. **ARGO data:** Not downloaded (correct — independent validation, Phase 6).

## Environment — how to resume
- Python 3.11 venv: `/home/joel/Projects/ERROR404/.venv` (`source .venv/bin/activate`)
- `copernicusmarine==2.4.1` installed; OAuth login already done (credentials in `.env`, tokens at
  `~/.copernicusmarine/.copernicusmarine-credentials`). Never commit `.env`.
- Python 3.11 binary: `/home/joel/.local/bin/python3.11`
- Auth command if needed: `copernicusmarine login --username samsan4627@gmail.com --password "<pw>" --force-overwrite`

## Docs updated today (canonical truth)
- `docs/work-log/2026-09-02-copernicus-validation.md` — full evidence + full split matrix
- `docs/04-data/data-sources.md` — verified IDs replacing old candidates
- `docs/04-data/dataset-registry.md` — verification matrix filled in
- `config/datasets.yaml` — verified dataset IDs, `verified: true`, `verified_at` set

## Old invalid IDs — DO NOT use
`SEALEVEL_GLO_PHY_L4_MY_008_047`, `SEALEVEL_GLO_PHY_CLIMATE_L4_MY_008_057`, `WIND_GLO_PHY_L3_MY_012_005`,
`WIND_GLO_PHY_L3_NRT_012_002`, `MULTIOBS_GLO_PHY_SSS_L3_MYNRT_015_014`, `MULTIOBS_GLO_PHY_MYNRT_015_003`,
`SST_GLO_SST_L4_REP_..._010_024`, `SST_GLO_SST_L4_NRT_..._010_001`.