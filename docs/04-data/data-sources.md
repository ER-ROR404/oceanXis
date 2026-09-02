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

## Surface inputs (candidate products — UNRESOLVED until verified)

These were discussed as candidates (§51). **Dataset IDs are implementation details and change.**
Verify each with `describe()` before use; populate `config/datasets.yaml` + the verification matrix.

| Logical variable | Historical/REP candidate | NRT candidate | Status |
|------------------|--------------------------|---------------|--------|
| SST | `SST_GLO_SST_L4_REP_OBSERVATIONS_010_024` | `SST_GLO_SST_L4_NRT_OBSERVATIONS_010_001` | CANDIDATE — verify |
| SSS | `MULTIOBS_GLO_PHY_SSS_L3_MYNRT_015_014` | — | CANDIDATE — verify |
| SSH/SLA | `SEALEVEL_GLO_PHY_CLIMATE_L4_MY_008_057` | `SEALEVEL_GLO_PHY_L4_NRT_008_046` | CANDIDATE — verify |
| Current U/V | — | `MULTIOBS_GLO_PHY_MYNRT_015_003` (multi-source; may include model Ekman) | CANDIDATE — verify/disclose |
| Wind U/V | `WIND_GLO_PHY_L3_MY_012_005` | `WIND_GLO_PHY_L3_NRT_012_002` | CANDIDATE — verify |

## Training/reference target

**GLORYS** Global Ocean Reanalysis — `GLOBAL_MULTIYEAR_PHY_001_030` family (previously
`cmems_mod_glo_phy_my_0.083deg_P1D-m`; ~0.083°, daily, 50 vertical levels, 1993 onwards, temp/sal/
current/SSH). **Dataset ID must be verified via `describe()`** (UNRESOLVED).

## Independent validation

**ARGO** in-situ profiles — matched by date/location, interpolated to the 15 depths. Never a
frontend upload requirement; never fabricated (Golden Rules 4, 21).

## Historical vs NRT policy

- Training: stable repo/reprocessed products, coherent overlap verified (§126–§127).
- Demo/live: latest available daily data (not "real-time" unless verified).
- Do not casually mix REP and NRT products (§83–§84).

## Data format

- Intermediate: NetCDF + xarray + NumPy. Zarr only if volume demands (§43).