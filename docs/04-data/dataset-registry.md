# Dataset Registry

> Verified dataset/product IDs, versions, variables, coverage, and provenance.
> Hard engineering gate (SYSTEM_MEMORY_DUMP.md §81). **Fill in only after `describe()`.**

## Verification matrix (hard gate)

Verification performed 2026-09-02 via `describe()` + `subset(dry_run=True)` (BoB & Arabian Sea, 2024-06-15).
See `docs/work-log/2026-09-02-copernicus-validation.md`.

| Variable | dataset_id | variable_name | source | spatial_resolution | temporal_resolution | coverage | units | latency | subset_supported | notes | verified_at |
|----------|-----------|---------------|--------|-------------------|---------------------|----------|-------|---------|------------------|-------|-------------|
| SST | `METOFFICE-GLO-SST-L4-REP-OBS-SST` | `analysed_sst` | orbit reprocessed (OSTIA METOFFICE) | 0.05° | daily | 1981→recent | °C | multi-year | ✔ | use for train/val | 2026-09-02 |
| SST (live) | `METOFFICE-GLO-SST-L4-NRT-OBS-SST-V2` | `analysed_sst` | orbit NRT | 0.05° | daily | recent | °C | ~1 day | ✔ | prod/live | 2026-09-02 |
| SSS | `cmems_obs-mob_glo_phy-sss_my_multi_P1D` | `sos` | multi-sat reprocessed | regional | daily | 2010s→2024 | 0.001 | multi-year | ✔ | train/val; switch to NRT for 2025 | 2026-09-02 |
| SSS (live) | `cmems_obs-mob_glo_phy-sss_nrt_multi_P1D` | `sos` | multi-sat NRT | regional | daily | 2024-01→2026-08 | 0.001 | ~1 day | ✔ | test/prod | 2026-09-02 |
| SSH/SLA | `cmems_obs-sl_glo_phy-ssh_my_allsat-l4-duacs-0.125deg_P1D` | `sla` | altimetry L4 allsat MY | 0.125° | daily | 1993-01→2026-01 | m | multi-year | ✔ | train/val | 2026-09-02 |
| SSH (live) | `cmems_obs-sl_glo_phy-ssh_nrt_allsat-l4-duacs-0.125deg_P1D` | `sla` | altimetry L4 allsat NRT | 0.125° | daily | recent | m | ~1 day | ✔ | prod/live | 2026-09-02 |
| Current U | `cmems_obs-mob_glo_phy-cur_my_0.25deg_P1D-m` | `uo` | multi-obs MY (geostrophic+Ekman+tide) | 0.25° | daily | 2018/2021/2024 verified | m/s | multi-year | ✔ | train/val | 2026-09-02 |
| Current V | `cmems_obs-mob_glo_phy-cur_my_0.25deg_P1D-m` | `vo` | same | 0.25° | daily | same | m/s | multi-year | ✔ | same product | 2026-09-02 |
| Current (live) | `cmems_mod_glo_phy-cur_anfc_0.083deg_P1D-m` | `uo`,`vo` | model analysis | 0.083° | daily | 2022-06→2026-09 | m/s | ~1 day | ✔ | prod/live | 2026-09-02 |
| Wind U | `cmems_obs-wind_glo_phy_my_l4_0.125deg_PT1H` | `eastward_wind` | scatterometer+model L4 MY | 0.125° | hourly (daily agg) | 2007-01→2026-04 | m/s | multi-year | ✔ | train/val/test | 2026-09-02 |
| Wind V | `cmems_obs-wind_glo_phy_my_l4_0.125deg_PT1H` | `northward_wind` | same | 0.125° | hourly (daily agg) | same | m/s | multi-year | ✔ | same product | 2026-09-02 |
| Wind (live) | `cmems_obs-wind_glo_phy_nrt_l4_0.125deg_PT1H` | `eastward_wind`,`northward_wind` | scatterometer+model L4 NRT | 0.125° | hourly | 2024-06→2026-09 | m/s | ~1 day | ✔ | prod/live | 2026-09-02 |
| GLORYS target | `cmems_mod_glo_phy_my_0.083deg_P1D-m` | `thetao` | GLORYS12 reanalysis | 0.083° | daily (50 levels) | 1993-01→2026-06 | °C | ~1–2 mo (reanalysis) | ✔ | training target @15 depths | 2026-09-02 |
| ARGO (val, fallback) | `cmems_obs-ins_glo_phy-temp-sal_my_cora-oa_P1M` | `TEMP`,`PSAL` | CORA in-situ OA | ~1° | monthly (gridded) | multi-year | °C | multi-year | ✔ | independent validation (gridded fallback) | 2026-09-02 |
| ARGO (raw profiles) | `cmems_obs-ins_glo_phy-temp-sal_my_cora_irr` / `...easycora_irr` | n/a | ARGO+in-situ profiles | — | profile | multi-year | °C | multi-year | ✗ no subset | prefer raw ARGO GDAC for true independence | 2026-09-02 |

## Manifest

Machine-readable entries live in `config/datasets.yaml` (runtime) and serialized manifests under
`data/manifests/`. Each entry records: `product_id`, `dataset_id`, `variable`, `source`, `resolution`,
`temporal_frequency`, `coverage_start/end`, `latency`, `units`, `notes`, `verified_at`
(SEE `contracts/data/dataset-metadata.schema.json`).

## Rules

- Never hard-code unverified dataset IDs (RULE 7).
- Update this registry + `config/datasets.yaml` together after every successful `describe()`.
- A training period is chosen only after the overlap across all inputs+target is verified (§126).