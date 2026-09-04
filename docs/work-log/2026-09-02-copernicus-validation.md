# Work Log — 2026-09-02: Copernicus Marine API Validation (Phase 1 pre-work)

> **Purpose:** Continuity record for later development. Captures today's live-verified results,
> the data-source decisions, the train/val/test split feasibility, ARGO status, and production
> (NRT) readiness. Supersedes the *candidate-only* IDs listed in `SYSTEM_MEMORY_DUMP.md` §51 and
> `docs/04-data/data-sources.md` (which were marked UNRESOLVED).

## 1. Environment & auth

- Python 3.11 venv created at `/home/joel/Projects/ERROR404/.venv` (`/home/joel/.local/bin/python3.11`).
- Installed `copernicusmarine==2.4.1` (`pip install copernicusmarine`; note `copernicus-marine` is a false trail).
- OAuth login: **SUCCESS** (`copernicusmarine login --username samsan4627@gmail.com --password "…" --force-overwrite`).
  Tokens stored at `/home/joel/.copernicusmarine/.copernicusmarine-credentials`. Credentials in `/home/joel/Projects/ERROR404/.env` (never commit).
- `cm.describe()` returns full catalogue (~307 products).
- Validation method used throughout: `cm.subset(..., dry_run=True)` — validates request **without downloading**
  (honors "do NOT download big datasets"). Auth also validated by successful describe.

## 2. Historical test date + target regions

- One shared historical test date: **2024-06-15** (both seas).
- **Bay of Bengal:** lon 80–100°E, lat 5–22°N.
- **Arabian Sea:** lon 45–75°E, lat 5–25°N. (From `config/regions.yaml`.)
- Core validation grid: our canonical 0.25° domain; inputs are daily; GLORYS target at 0.083°.

## 3. VERIFIED dataset IDs (replaces `config/datasets.yaml` candidates)

All 7 surface inputs + GLORYS target verified GREEN for **both** regions at 2024-06-15.

| # | Channel | dataset_id | variable(s) | units | Coverage (verified live) |
|---|---------|-----------|-------------|-------|--------------------------|
| 0 | SST | `METOFFICE-GLO-SST-L4-REP-OBS-SST` | `analysed_sst` | °C | 1981 → recent (multi-year) |
| 1 | SSS | `cmems_obs-mob_glo_phy-sss_my_multi_P1D` (MY) / `cmems_obs-mob_glo_phy-sss_nrt_multi_P1D` (NRT, for 2025+) | `sos` | 0.001 | MY 2010s→2024; NRT 2024-01→2026-08 |
| 2 | SSH/SLA | `cmems_obs-sl_glo_phy-ssh_my_allsat-l4-duacs-0.125deg_P1D` | `sla` | m | 1993-01 → 2026-01 |
| 3 | Current U | `cmems_obs-mob_glo_phy-cur_my_0.25deg_P1D-m` (MY obs) — preferred | `uo` | m/s | 2018/2021/2024 ✔ |
| 4 | Current V | same product | `vo` | m/s | same |
| 5 | Wind U | `cmems_obs-wind_glo_phy_my_l4_0.125deg_PT1H` | `eastward_wind` | m/s | 2007-01 → 2026-04 |
| 6 | Wind V | same product | `northward_wind` | m/s | same |
| — | GLORYS target | `cmems_mod_glo_phy_my_0.083deg_P1D-m` | `thetao` | °C | 1993-01 → 2026-06; 0–5728 m |

### Corrections vs memory dump / old contracts
- **SSH:** `SEALEVEL_GLO_PHY_L4_MY_008_047` and `SEALEVEL_GLO_PHY_CLIMATE_L4_MY_008_057` **do not exist**.
  Correct verified ID is `cmems_obs-sl_glo_phy-ssh_my_allsat-l4-duacs-0.125deg_P1D` (var `sla`).
- **SSS** variable is **`sos`** (NOT `so`); units `0.001`.
- **Wind:** old `WIND_GLO_PHY_L3_MY_012_005` / `_NRT_012_002` **no longer exist**. Use the gridded L4:
  - MY: `cmems_obs-wind_glo_phy_my_l4_0.125deg_PT1H` (2007–2026)
  - NRT: `cmems_obs-wind_glo_phy_nrt_l4_0.125deg_PT1H` (2024-06–2026-09)
- **GLORYS daily physics** = `cmems_mod_glo_phy_my_0.083deg_P1D-m` (product `GLOBAL_MULTIYEAR_PHY_001_030`).
  Contains `thetao, so, uo, vo, zos, bottomT, mlotst, siconc, sithick`, 11 vars, depth 0.49–5728 m.

## 4. Currents & wind — long-history alternatives found (key decisions)

**Problem:** the analysis/forecast products only cover recent years, which cannot support a long
training window. Alternatives resolved:

- **Currents (historical/training): use MY observation currents** `cmems_obs-mob_glo_phy-cur_my_0.25deg_P1D-m`.
  Vars `uo`,`vo` (total) + `ugos/ve` (geostrophic+Ekman/tidal) decompositions. Verified GREEN for 2018, 2021, 2024.
  (Overrides the analysis product `cmems_mod_glo_phy-cur_anfc_0.083deg_P1D-m`, which only spans 2022-06→2026-09 and is the NRT/analysis choice.)
- **Wind (historical/training): use MY L4 gridded** `cmems_obs-wind_glo_phy_my_l4_0.125deg_PT1H`
  (2007–2026). Verified GREEN for 2018/2021/2023/2024/2025. This is the single consistent long-history wind source.
  - Ignore: MY L4 0.25° (only 1994–2009), MY L3 ASCAT (ends 2021), NRT L4 (starts 2024-06).
- GLORYS itself ships `uo/vo/zos` from 1993, but per contract GLORYS must stay the **target only** (avoid target leakage in inputs).

## 5. Train / validation / test split — AVAILABILITY CONFIRMED

Proposed split (temporal, no random shuffle per RULE 10):
- **Train:** 2018-01-01 → 2023-12-31
- **Validation:** 2024-01-01 → 2024-12-31
- **Test:** 2025-01-01 → 2025-12-31

Full 7-input + GLORYS matrix sampled across windows (BoB shown; AS same):

| Window | SST | SSS | SSH | CurrU | CurrV | WindU | WindV | GLORYS |
|--------|-----|-----|-----|-------|-------|-------|-------|--------|
| TRAIN 2018 | 🟢 | 🟢 | 🟢 | 🟢 | 🟢 | 🟢 | 🟢 | 🟢 |
| TRAIN 2021 | 🟢 | 🟢 | 🟢 | 🟢 | 🟢 | 🟢 | 🟢 | 🟢 |
| TRAIN 2023 | 🟢 | 🟢 | 🟢 | 🟢 | 🟢 | 🟢 | 🟢 | 🟢 |
| VAL 2024 | 🟢 | 🟢 | 🟢 | 🟢 | 🟢 | 🟢 | 🟢 | 🟢 |
| TEST 2025 | 🟢 | 🟢(via NRT) | 🟢 | 🟢 | 🟢 | 🟢 | 🟢 | 🟢 |

- **All channels available across the entire split.**
- **SSS nuance:** MY SSS `...sss_my_multi_P1D` covers through 2024; for 2025 (test) switch to NRT SSS
  `cmems_obs-mob_glo_phy-sss_nrt_multi_P1D` (covers 2024-01→2026-08). Clean 2024 overlap verified (both GREEN in Dec-2024).
- No inter-channel timeout: same-day same-location data confirmed present for every channel in every window.

## 6. ARGO independent validation — status

ARGO must remain **independent validation** (RULE 9). Verified options in Copernicus:

| Product | dataset_id | subset? | Notes |
|---------|-----------|---------|-------|
| CORA-OA gridded (in-situ reprocessed) | `cmems_obs-ins_glo_phy-temp-sal_my_cora-oa_P1M` | 🟢 GREEN for 2021/2024/2025 | Monthly, `TEMP`/`PSAL` + errors, gridded. ARGO+other in-situ. |
| CORA (raw profiles) | `cmems_obs-ins_glo_phy-temp-sal_my_cora_irr` | 🔴 no subset service | original-files only |
| EasyCORA (raw profiles) | `cmems_obs-ins_glo_phy-temp-sal_my_easycora_irr` | 🔴 no subset service | original-files only |

**Recommendation:** for the MVP validation, use **raw ARGO float profiles** matched by date/location and
interpolated to the 15 depths (true independence). Cora-oa is only acceptable as a fallback (it grids ARGO
+ other platforms, so not purely independent single-float validation). Raw ARGO GDAC is the canonical source;
needs float-profile download flow separate from gridded `subset()`.

## 7. Production-grade near-real-time readiness — CONFIRMED

All 5 NRT surface channels return data at **7 days ago** (tested 2026-08-26, BoB):

| Channel | dataset_id | Status @7d ago |
|---------|-----------|:---:|
| SST NRT `METOFFICE-GLO-SST-L4-NRT-OBS-SST-V2` | `analysed_sst` | 🟢 |
| SSS NRT | `cmems_obs-mob_glo_phy-sss_nrt_multi_P1D` (`sos`) | 🟢 |
| SSH NRT | `cmems_obs-sl_glo_phy-ssh_nrt_allsat-l4-duacs-0.125deg_P1D` (`sla`) | 🟢 |
| Current analysis | `cmems_mod_glo_phy-cur_anfc_0.083deg_P1D-m` (`uo`) | 🟢 |
| Wind NRT L4 | `cmems_obs-wind_glo_phy_nrt_l4_0.125deg_PT1H` (`eastward_wind`) | 🟢 |

**Caveat — GLORYS is NOT near-real-time.** `cmems_mod_glo_phy_my_0.083deg_P1D-m` is a **reanalysis**
(target), with ~1-month production latency (verified: coverage ends 2026-06-23 as of system date 2026-09-02,
i.e. ~2 months behind). Therefore:
- A **production "nowcast"** of subsurface temperature must be framed as "latest GLORYS-consistent estimate"
  with explicit reported latency in the product narrative (per RULE 13 — do not claim real-time without proof),
  OR use an NRT ocean temperature analysis product for live output (NOTE: that changes the target contract and
  needs an ADR).

## 8. Verification matrix — dataset-registry tab

See `docs/04-data/dataset-registry.md` (updated in parallel) and `config/datasets.yaml` for machine-readable
entries. All IDs above are **verified**; set `verified: true`, `selected: true` on the chosen ones in config.

## 9. Next steps (handoff)

1. Update `config/datasets.yaml` with verified IDs/vars/coverage; flip `verified`/`selected`.
2. Update `docs/04-data/data-sources.md` and `dataset-registry.md` (done in parallel — read latest).
3. Run ONE real one-day mini-download (SST, BoB ≈ small file) to prove xarray round-trip + NaN/units QC —
   satisfies Phase 1 one-day proof (implementation-plan exit gate). Do NOT pull years of data yet.
4. Decide/ADR the GLORYS-not-NRT production framing.
5. Stand up ARGO raw float validation harness (or adopt cora-oa fallback) for matched date/location profiles.
6. Proceed with Phase 1 data-engineering using the split above (train 2018-23 / val 2024 / test 2025).