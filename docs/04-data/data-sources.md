# Data Sources

> Documents Copernicus, GLORYS, ARGO, and other approved sources.
> Source: SYSTEM_MEMORY_DUMP.md §44–§54.

## Primary provider

**Copernicus Marine** via the `copernicusmarine` Python Toolbox:

- `login` (server-side credentials)
- `describe` — catalogue discovery/verification (RULE 7)
- `subset` — regional/date/variable/depth extraction (NetCDF default; Zarr/CSV per dataset)
- `get` — full producer files
- Credentials: backend-only env vars (see `SECURITY.md`)

## Surface inputs (VERIFIED 2026-09-02 — see docs/work-log/2026-09-02-copernicus-validation.md)

Verified via `describe()` + `subset(dry_run=True)` for Bay of Bengal and Arabian Sea at 2024-06-15.

| Logical variable | Historical/train dataset_id | NRT/live dataset_id | Verified variable |
|------------------|------------------------------|---------------------|-------------------|
| SST | `METOFFICE-GLO-SST-L4-REP-OBS-SST` (1981→) | `METOFFICE-GLO-SST-L4-NRT-OBS-SST-V2` | `analysed_sst` |
| SSS | `cmems_obs-mob_glo_phy-sss_my_multi_P1D` (→2024) | `cmems_obs-mob_glo_phy-sss_nrt_multi_P1D` (2024→) | `sos` |
| SSH/SLA | `cmems_obs-sl_glo_phy-ssh_my_allsat-l4-duacs-0.125deg_P1D` (1993→) | `cmems_obs-sl_glo_phy-ssh_nrt_allsat-l4-duacs-0.125deg_P1D` | `sla` |
| Current U/V | `cmems_obs-mob_glo_phy-cur_my_0.25deg_P1D-m` (MY obs) | `cmems_mod_glo_phy-cur_anfc_0.083deg_P1D-m` (analysis, 2022→) | `uo`, `vo` |
| Wind U/V | `cmems_obs-wind_glo_phy_my_l4_0.125deg_PT1H` (2007→) | `cmems_obs-wind_glo_phy_nrt_l4_0.125deg_PT1H` (2024-06→) | `eastward_wind`, `northward_wind` |

> Old candidate IDs (`010_024`, `015_014`, `008_057`, `015_003`, `012_005/012_002`) are **invalid/out-of-date**
> and must NOT be used. The verified IDs above supersede them.

## Training/reference target

**GLORYS** Global Ocean Reanalysis — daily physics `cmems_mod_glo_phy_my_0.083deg_P1D-m`
(product `GLOBAL_MULTIYEAR_PHY_001_030`; ~0.083°, daily, 50 vertical levels, 1993-01→2026-06).
Target variable: `thetao` (temperature, 0.49–5728 m, covers the 15 canonical depths).
**VERIFIED — dataset_id confirmed via `describe()`.**

## Independent validation

**ARGO** in-situ profiles — matched by date/location, interpolated to the 15 depths. Never a
frontend upload requirement; never fabricated (Golden Rules 4, 21).

## Historical vs NRT policy

- Training: stable repo/reprocessed products, coherent overlap verified (§126–§127).
- Demo/live: latest available daily data (not "real-time" unless verified).
- Do not casually mix REP and NRT products (§83–§84).
- **GLORYS is a reanalysis and is NOT near-real-time** (verified: coverage lags ~1–2 months).
  Frame any "nowcast" output with explicit reported latency, or use an NRT temperature analysis
  product for live output (requires an ADR as it changes the target contract).

## Data format

- Intermediate: NetCDF + xarray + NumPy. Zarr only if volume demands (§43).