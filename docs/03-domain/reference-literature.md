# Reference Literature & External Resources

> **Purpose:** All external URLs, PDF paths, paper citations, and analysis sources used in
> OceanEmbed development. If OpenCode restarts or internet is lost, this file preserves
> every reference needed to continue.
>
> **Last updated:** 2026-09-04

---

## Official Sources

| Source | URL / Path | Purpose |
|--------|-----------|---------|
| SIH 2026 Official Portal | `https://sih.gov.in` | Authoritative problem statement text, theme, deadline |
| CodeHunters SIH 2026 PS Analysis | `https://www.codehuntersacademy.com/sih-2026-ps#SIH26066` | SWOT, evaluator questions, competitive landscape, scoring |
| CodeHunters Hackathon Playbook | `https://topmate.io/dasandcode` | Supplementary strategy (not authoritative over technical docs) |

---

## Reference Papers (PDFs)

### Paper 1 — Su et al. 2022 (ConvLSTM DORS) — CORE ARCHITECTURE REFERENCE

| Field | Value |
|-------|-------|
| **Citation** | Su, H., Jiang, J., Wang, A., Zhuang, W., Yan, X.-H. (2022). Subsurface Temperature Reconstruction for the Global Ocean from 1993 to 2020 Using Satellite Observations and Deep Learning. *Remote Sensing*, 14(13), 3198. |
| **DOI** | `https://doi.org/10.3390/rs14133198` |
| **PDF path (local)** | `remotesensing-14-03198-v2.pdf` (user-provided; model cannot read PDF directly) |
| **MDPI page** | `https://www.mdpi.com/2072-4292/14/13/3198` |
| **Affiliation** | Fuzhou University, Xiamen University, University of Delaware Center for Remote Sensing (Prof. Xiao-Hai Yan) |
| **Key contribution** | Deep Ocean Remote Sensing (DORS) product: 0–2000 m, 23 vertical layers, global, 1993–2020 |
| **Architecture** | ConvLSTM neural network: 1 input layer + 11 hidden ConvLSTM2D layers (BatchNorm, Dropout) + 1 ConvLSTM3D output layer |
| **Activation** | ELU |
| **Optimizer** | RMSprop, lr=0.001 |
| **Loss** | MSE |
| **Epochs** | Up to 4000 |
| **Inputs** | SST, SSH, Surface wind U/V (USSW, VSSW) + coordinate grids |
| **Training label** | Argo gridded data |
| **Benchmark** | Outperformed LightGBM across all depths; R²~0.99, RMSE~0.34°C vs Argo gridded |
| **Error characteristic** | Peaks at 100–200 m (thermocline); deeper layers >500 m more stable |
| **Relevance to OceanEmbed** | Primary architecture reference for CNN+ConvLSTM hybrid (ADR-010) |

### Paper 2 — Loo et al. 2026 (Adaptive Spatiotemporal Clustering) — DIFFERENTIATOR REFERENCE

| Field | Value |
|-------|-------|
| **Citation** | Loo, M.S., Li, W., Jiang, X., Cheng, H., Zhang, Z., Guan, J., Zhang, Y. (Apr 2026). An Adaptive Spatiotemporal Clustering Framework for 3D Ocean Subsurface Temperature Reconstruction. *arXiv:2605.00860v1* [physics.ao-ph]. |
| **arXiv** | `https://arxiv.org/abs/2605.00860` |
| **HTML (experimental)** | `https://arxiv.org/html/2605.00860v1` |
| **PDF path (local)** | `2605.00860v1.pdf` (user-provided; model cannot read PDF directly) |
| **Affiliation** | Tongji University, Shanghai, China |
| **Key contribution** | Two-stage framework: (1) Spatiotemporal clustering → (2) 3D reconstruction on coherent sub-blocks |
| **Vertical Clustering** | Hierarchical Agglomerative Clustering on time/space-averaged vertical profile T(z); Euclidean distance; identifies contiguous thermodynamically consistent depth intervals |
| **Temporal Clustering** | Climatological multi-year average → typical annual cycle → PCA extracts dominant mode p1 → dynamic programming change-point detection (ruptures) for seasonal breakpoints |
| **Backbones tested** | DP-CNN, Attention U-Net, ViT, FFNN, LSTM, OCNN (architecture-agnostic) |
| **Best performers** | DP-CNN and Attention U-Net |
| **Study areas** | Central Equatorial Indian Ocean (85°E–90°E, 5°N–10°N) and South China Sea (110°E–115°E, 10°N–15°N) |
| **Data** | 1993–2022, 0.25° grid, 73 vertical layers, Copernicus (CMEMS) |
| **Inputs** | SST, SSS, SSH, SSW (surface wind) |
| **Key result** | Spatiotemporal clustering reduced RMSE by 12.4%–27.2% across all backbones |
| **Error concentration** | 100–200 m thermocline layer (layers 15–25) |
| **Ablation** | Joint clustering >> vertical-only > temporal-only >> no clustering |
| **Training** | Adam, lr=1e-2, decay 0.01, batch 32, 300 epochs, early stopping patience 10, RTX 3090 |
| **Split** | 8:1:1 (train:val:test) globally |
| **Relevance to OceanEmbed** | Provides architecture-agnostic spatiotemporal clustering enhancement; directly applicable to Bay of Bengal / Arabian Sea (Indian Ocean tested); potential No.1 differentiator if combined with ConvLSTM |

### Paper 3 — Copernicus 0.25° Resolution Guide — TECHNICAL SPEC

| Field | Value |
|-------|-------|
| **PDF path (local)** | `Copernicus_0.25_Degree_Resolution_Guide.pdf` (user-provided; model cannot read PDF directly) |
| **Key facts captured** | 0.25° ≈ 27.8 km latitude spacing; 0.25° × cos(lat) for longitude (e.g., 26.9 km at 15°N) |
| **Resolution ≠ Accuracy** | Resolution is grid spacing; accuracy is fidelity to true ocean state |
| **Bounding box convention** | West=min_lon, East=max_lon, South=min_lat, North=max_lat |
| **Dimensions** | Spatial (where), Temporal (when), Depth (how deep) — orthogonal |
| **Unit conversions** | K→°C: °C = K − 273.15; current magnitude = √(uo² + vo²) |

---

## University of Delaware / Xiao-Hai Yan Lab

| Field | Value |
|-------|-------|
| **Repository** | `https://udspace.udel.edu/items/4e74ecf7-eb91-4428-b065-5396be5be90b` |
| **Institution** | Center for Remote Sensing, College of Earth, Ocean and Environment, University of Delaware |
| **PI** | Prof. Xiao-Hai Yan |
| **Relevance** | Leading research center for satellite remote sensing inversion of subsurface ocean thermal structures (DORS techniques); co-authored Su et al. 2022 |

---

## Evaluator Questions (from CodeHunters Analysis)

These are the questions an official SIH evaluator is likely to ask. Prepare answers for each:

1. **"Where exactly is your input or training data coming from, real Space Technology-domain data or a synthetic/demo dataset assembled for the hackathon?"**
   → Answer: Real Copernicus Marine Service data (CMEMS). All 7 surface inputs + GLORYS reanalysis target verified via `copernicusmarine.describe()`. Dataset IDs locked in `config/datasets.yaml`. Training period: 2018–2023 (train), 2024 (val), 2025 (test). Independent validation via ARGO GDAC profiles.

2. **"Walk me through why this level of tech is the right call here and not overkill for this specific problem."**
   → Answer: The surface-to-subsurface mapping is nonlinear, spatially/temporally variable, depth-dependent, and partially ill-posed (SYSTEM_MEMORY_DUMP §3). Simple interpolation or climatology cannot capture mesoscale eddy dynamics, thermocline variability, or seasonal evolution. ConvLSTM preserves spatial grid structure while modeling temporal sequences (Su et al. 2022). Physics-aware loss ensures scientific constraints. The problem statement explicitly permits CNN/ViT/GNN/attention/hybrid architectures.

3. **"What happens when connectivity drops, hardware fails, or input data is missing, does the system degrade gracefully or just break?"**
   → Answer: Copernicus unavailable → return cached latest data. Variable unavailable → mark channel unavailable (never zero-fill). Model inference fails → clear system error (never fake values). Fallback demo dataset exists so the demo never dies with live ingestion. Land/sea mask handles missing ocean cells.

4. **"How would this hold up with real production-scale data instead of your demo dataset?"**
   → Answer: The pipeline is designed for regional daily inference. Copernicus has no fixed Toolbox download quota. The architecture scales to full North Indian Ocean (5–30°N, 45–105°E) — the 0.25° grid is the required standardized resolution. Chunked historical downloads proven via `subset_split_on`. Colab GPU training scales to multi-year datasets.

5. **"Who exactly benefits from this, and how would you measure it is actually working after deployment, not just at demo time?"**
   → Answer: Beneficiaries: INCOIS/MoES operational oceanography, marine heatwave monitoring, fisheries, data assimilation, climate research. Measurement: depth-wise RMSE/bias/correlation against independent ARGO; spatial error maps; uncertainty calibration. The system is positioned as complementary to GODAS (not a replacement).

---

## Competition Timeline

| Field | Value |
|-------|-------|
| **Deadline** | 20 September 2026 |
| **Ideas submitted** | 0 / 500 (as of last check) |
| **Total SIH 2026 PS** | 226 across 30 organizations, 18 themes |
| **Directly competing PS** | 5 (ocean/spatial/observation cluster) |
| **Theme** | Disaster Management (official portal) |

---

## Local PDF Paths (for when model can read PDFs in future)

| Filename | Paper | Path hint |
|----------|-------|-----------|
| `remotesensing-14-03198-v2.pdf` | Su et al. 2022 (ConvLSTM DORS) | User-provided; check project root or download from DOI |
| `2605.00860v1.pdf` | Loo et al. 2026 (Spatiotemporal Clustering) | User-provided; download from `https://arxiv.org/pdf/2605.00860` |
| `Copernicus_0.25_Degree_Resolution_Guide.pdf` | Copernicus Resolution Guide | User-provided; source unknown — ask user for origin |
