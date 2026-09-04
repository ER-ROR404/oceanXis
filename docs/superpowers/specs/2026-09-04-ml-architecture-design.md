# OceanEmbed — ML Architecture Specification v2.0

> **Date:** 2026-09-04
> **Status:** DEPRECATED — replaced by v2.1 (`2026-09-04-ml-architecture-design-v2.1.md`)
> **Purpose:** Complete ML architecture spec for the OceanEmbed subsurface temperature reconstruction system.
> **Competition:** SIH26066 — Ministry of Earth Sciences / INCOIS — Disaster Management theme
> **Goal:** Win against 500+ teams with scientific credibility, not model complexity.

---

## Frozen Before Coding — The 5 Things

Before any implementation code is written, these five items are frozen:

| # | Question | Frozen Answer |
|---|----------|--------------|
| 1 | **Exactly what are the 7 inputs?** | SST, SSS, SSH/SLA, Current U, Current V, Wind U, Wind V (LOCKED in config/variables.yaml) |
| 2 | **Exactly where does each input come from?** | 5 different Copernicus Marine products (verified via copernicusmarine.describe() on 2026-09-02 — see config/datasets.yaml) |
| 3 | **Exactly what does the model output?** | Temperature (°C) at 15 standard depths (0–1000 m) at 0.25° daily resolution, plus uncertainty (+/- sigma) |
| 4 | **Exactly how do we prove the output is correct?** | Independent ARGO profile comparison — depth-wise RMSE, bias, correlation. ARGO data is never used in training. |
| 5 | **Exactly what makes OceanEmbed different?** | Not "we built a sophisticated AI." — "We built a scientifically validated system that reconstructs previously unobserved subsurface ocean temperature from surface observations, quantifies where it can be trusted, and delivers the result on the required spatial/depth grid." |

---

## Section 2: Competition and Scientific Landscape

### 2.1 What exists today

| Method | Description | Limitation |
|--------|-------------|-----------|
| **Climatology** | Monthly mean temperature from historical observations | Cannot capture daily variability, mesoscale features, or interannual events |
| **Persistence** | Yesterday's profile = today's | Fails during rapid changes (storm events, upwelling onset) |
| **GODAS** (INCOIS operational) | Physics-based ocean data assimilation system | Computationally expensive; requires full ocean model; not publicly accessible at daily 0.25° for arbitrary regions |
| **EN4 / IAP** | Gridded observational products from sparse profiles | Spatial gaps where ARGO coverage is poor; smoothed features |
| **DORS (Su et al. 2022)** | ConvLSTM, trained on Argo gridded, global 1° | Trained on sparse Argo (spatial gaps); 1° resolution too coarse for regional features |
| **Loo et al. 2026** | Spatiotemporal clustering + various backbones, 0.25° | Indian Ocean tested but no uncertainty quantification; no independent ARGO validation shown |

### 2.2 The research gap we fill

No existing system simultaneously provides:
1. **High-resolution (0.25°) regional reconstruction** from 7 surface channels
2. **Quantified uncertainty** at every depth and grid cell
3. **Independent ARGO validation** (not just training-target comparison)
4. **Physics-aware constraints** that prevent physically implausible outputs
5. **Daily operational capability** with pre-computed results and instant serving

### 2.3 Our differentiation

| Dimension | 500+ teams (typical) | OceanEmbed |
|-----------|----------------------|------------|
| Training data | Toy / synthetic / single-source | GLORYS reanalysis (2018-2023, dense, verified) |
| Independent validation | None or training data comparison | ARGO profiles (gold standard, never in training) |
| Uncertainty | None | Gaussian heteroscedastic — every prediction has a confidence interval |
| Physics constraints | None | Vertical smoothness, surface consistency, thermocline behavior |
| Input richness | 2-4 variables from one dataset | 7 variables from 5 Copernicus products, harmonized |
| Operational design | One-shot demo | Daily automated pipeline, pre-computed, instant serve |
| Evaluator credibility | "Trust us" | "Here is ARGO validation, uncertainty maps, depth-wise metrics" |

---

## Section 3: End-to-End Architecture

### 3.1 System overview

```
Multiple Copernicus products (5 datasets, different resolutions/timings)
          |
Quality control + temporal alignment + spatial regridding
          |
Common 0.25° daily 7-channel tensor  <-- THIS IS PART OF OUR CONTRIBUTION
          |
7-day temporal window of surface observations
          |
    +-----------------------------------+
    |   OceanEmbed Reconstruction      |
    |        Network                   |
    |  CNN spatial + ConvLSTM          |
    |  temporal + depth decoder        |
    +-----------------------------------+
          |
Temperature at 15 depths + uncertainty (mu, sigma)
          |
Independent ARGO validation
          |
Product: spatial maps + vertical profiles + confidence layers
```

### 3.2 The data harmonization contribution

The 7 input variables come from **5 different Copernicus Marine products** with different native resolutions, temporal characteristics, and file formats. Our engineering contribution is the **harmonization layer** that produces a consistent multi-channel tensor:

```
METOFFICE-GLO-SST-L4-REP-OBS-SST    (SST, 0.05°, daily)  ---+
cmems_obs-mob_glo_phy-sss_my        (SSS, 0.25°, daily)  ---+
cmems_obs-sl_glo_phy-ssh_my         (SSH, 0.125°, daily) ---+  Harmonize
cmems_obs-mob_glo_phy-cur_my        (U/V current, 0.25°) ---+  -> 0.25°
cmems_obs-wind_glo_phy_my_l4        (U/V wind, 0.125°)   ---+  daily
                                                                  |
                                                      7-channel tensor
                                                      (B, 7, H, W)
```

This is not trivial — different products have different:
- Spatial resolutions (0.05°, 0.083°, 0.125°, 0.25°)
- Temporal cadences (some hourly, some daily)
- Variable conventions (Kelvin vs Celsius, different naming)
- Land/sea masking
- Quality flags

The harmonization pipeline (Phase 2, already implemented and tested) handles all of this. The model only ever sees the clean 0.25° daily tensor.

### 3.3 Training target vs validation source

| | GLORYS Reanalysis | ARGO Profiles |
|---|---|---|
| **Role** | Training target (dense labels) | Independent validation (never in training) |
| **Why** | Spatially complete at 0.25°; covers 2018-2023; physically consistent | Direct in-situ measurements; gold standard for ocean accuracy |
| **Coverage** | Every grid cell, every day | Sparse, irregular float locations |
| **Used in training** | YES — model learns surface-to-GLORYS mapping | NO — ARGO is held out entirely |
| **Used in evaluation** | Upper-bound reference | True out-of-sample accuracy proof |

**Why this is scientifically defensible:** GLORYS is a reanalysis that assimilates observations (including ARGO). Training on GLORYS lets the model learn dense spatial patterns. Validating on ARGO (which is independent of our model) proves the model generalizes to real observations. This is the same approach used by operational oceanography centers worldwide.

---

## Section 4: Data Harmonization and Ocean Representation

### 4.1 What this section does

This section describes how raw Copernicus data becomes a clean 7-channel input tensor. This is **engineering contribution**, not a research innovation.

### 4.2 Harmonization pipeline (implemented, tested, committed)

The pipeline is already built and tested (Phase 2, commit 91a8a68):

```
Raw NetCDF from Copernicus
    |
1. Regrid to 0.25° (bilinear interpolation for SSH/wind; nearest for currents)
    |
2. Select GLORYS subsurface levels -> 15 canonical depths (linear interpolation in depth)
    |
3. Extract surface variables only (7 channels)
    |
4. Apply land/sea validity mask
    |
5. Stack into (T, C, H, W) tensor
    |
6. Z-score normalization (training statistics only — Rule 11)
    |
7. Save as Zarr with provenance metadata
```

**Verified output:** 1-day proof data produces X shape (1, 7, 69, 81), Y shape (1, 15, 69, 81), 94.7% valid ocean cells. Latitude, longitude, and time all perfectly aligned across X, Y, and Mask.

### 4.3 Optional: Ocean Regime Representation (deferred)

**Status: NOT in Phase 3. Implement only if experiments prove it helps.**

Inspired by Loo et al. 2026's spatiotemporal clustering (12-27% RMSE reduction), we may add an optional "ocean regime" module that groups grid cells by vertical profile similarity. However:

- The baseline CNN + ConvLSTM architecture must be built and tested FIRST
- Clustering adds implementation, training, debugging, and explanation complexity
- It must demonstrate measurable RMSE improvement in ablation studies before inclusion
- If included, it would be a **module within the network**, not a separate preprocessing step

**Decision rule:** Build baseline -> measure performance -> if clustering improves RMSE by >5%, include it. Otherwise, ship the simpler architecture.

---

## Section 5: OceanEmbed Reconstruction Network

### 5.1 The core task

```
Input:  7 surface variables x 7 days x H x W  (where H=69, W=81 for North Indian Ocean)
Output: Temperature at 15 depths x H x W
```

This is a spatiotemporal regression problem: map a sequence of surface observations to a 3D subsurface temperature field.

### 5.2 Network architecture — CNN + ConvLSTM

```
INPUT: (B, T=7, C=7, H, W) — 7 days of 7-channel surface observations

    | Add coordinate channels (lat, lon, day-of-year)
    -> (B, T=7, C=10, H, W)

    | Per-timestep CNN spatial encoder
    -> (B, T=7, F=32, H, W) — spatial feature maps per day

    | ConvLSTM temporal encoder (3 layers)
    -> (B, F=64, H, W) — fused spatiotemporal features

    | Reconstruction decoder
    -> (B, 15, H, W) — temperature at 15 depths

    | Uncertainty head (log variance)
    -> (B, 15, H, W) — log sigma-squared at 15 depths
```

### 5.3 Detailed layer specification

**CNN Spatial Encoder (per timestep):**

```
Input: (B, 10, H, W)  [7 channels + 3 coordinate channels]

ConvBlock(10 -> 32)    -> (B, 32, H, W)     # 3x3 conv + BN + ELU
MaxPool2D(2)           -> (B, 32, H/2, W/2)
ConvBlock(32 -> 64)    -> (B, 64, H/2, W/2)
MaxPool2D(2)           -> (B, 64, H/4, W/4)
ConvBlock(64 -> 128)   -> (B, 128, H/4, W/4)
MaxPool2D(2)           -> (B, 128, H/8, W/8)

Output: (B, 128, H/8, W/8) — compressed spatial representation
```

**ConvLSTM Temporal Encoder:**

```
Input: (B, T=7, 128, H/8, W/8) — sequence of spatial features

ConvLSTM2D(input=128, hidden=64, kernel=3, num_layers=3, batch_norm=True)
  -> (B, 64, H/8, W/8) — temporal feature (last hidden state)

Upsample(2) -> (B, 64, H/4, W/4)
Upsample(2) -> (B, 64, H/2, W/2)
Upsample(2) -> (B, 64, H, W) — back to original spatial resolution
```

**Reconstruction Decoder:**

```
Input: (B, 64, H, W)

ConvBlock(64 -> 32)   -> (B, 32, H, W)

# 15 parallel depth heads, each:
Conv1x1(32 -> 16) -> ELU -> Conv1x1(16 -> 1) -> (B, 1, H, W) per depth

Stack 15 heads -> (B, 15, H, W) — temperature at all depths
```

**Uncertainty Head (parallel to reconstruction):**

```
Input: (B, 32, H, W) — same features as reconstruction

Conv1x1(32 -> 16) -> ELU -> Conv1x1(16 -> 15) -> (B, 15, H, W) — log sigma-squared
```

### 5.4 Why this architecture

| Design choice | Reason |
|---------------|--------|
| U-Net style CNN encoder | Captures multi-scale spatial features (eddy-scale to basin-scale); skip connections preserve resolution |
| ConvLSTM temporal | Su et al. 2022 proven; models temporal evolution of surface-to-subsurface mapping; T4-friendly |
| Per-depth heads | Each depth has different characteristics (surface = noisy, thermocline = variable, deep = stable); separate heads specialize |
| Coordinate channels | Latitude/longitude/day-of-year provide spatial and seasonal context without explicit feature engineering |
| Uncertainty head | Produces confidence intervals — our key differentiator |

### 5.5 Model size and compute

| Metric | Value |
|--------|-------|
| Parameters | ~2-5M |
| Model file size | ~20 MB |
| Training time (T4) | ~7 hours (200 epochs, AMP, gradient checkpointing) |
| Inference time per day | <5 seconds for full North Indian Ocean grid |
| GPU memory | <8 GB (with AMP + gradient checkpointing) |

### 5.6 Implementation

File: `ml/src/oceanembed_ml/models/reconstruction_net.py`

```python
class OceanEmbedNet(nn.Module):
    """CNN + ConvLSTM spatiotemporal reconstruction network."""

    def __init__(
        self,
        in_channels: int = 7,
        coord_channels: int = 3,
        n_depths: int = 15,
        temporal_window: int = 7,
        base_channels: int = 32,
    ):
        super().__init__()
        self.spatial_encoder = UNetEncoder(in_channels + coord_channels, base_channels)
        self.temporal_modeler = ConvLSTMTemporal(base_channels * 4, base_channels * 2, temporal_window)
        self.decoder = ReconstructionDecoder(base_channels * 2, base_channels, n_depths)
        self.uncertainty_head = UncertaintyHead(base_channels * 2, n_depths)

    def forward(self, x: torch.Tensor, coords: torch.Tensor):
        """
        Args:
            x: (B, T, 7, H, W) — 7-day window of surface observations
            coords: (B, 3, H, W) — lat, lon, day-of-year
        Returns:
            mu: (B, 15, H, W) — predicted temperature
            log_var: (B, 15, H, W) — log variance (for uncertainty)
        """
        B, T, C, H, W = x.shape

        # Spatial features per timestep
        spatial_feats = []
        for t in range(T):
            inp = torch.cat([x[:, t], coords], dim=1)
            feat = self.spatial_encoder(inp)
            spatial_feats.append(feat)

        spatial_seq = torch.stack(spatial_feats, dim=1)

        # Temporal modeling
        temporal_feat = self.temporal_modeler(spatial_seq)

        # Reconstruction
        mu = self.decoder(temporal_feat)
        log_var = self.uncertainty_head(temporal_feat)

        return mu, log_var
```

---

## Section 6: Uncertainty and Confidence

### 6.1 What uncertainty means scientifically

Every model prediction has two sources of error:

| Source | What it is | How we measure it |
|--------|-----------|-------------------|
| **Aleatoric (irreducible)** | Inherent ocean variability that no model can predict (weather noise, sub-grid processes, measurement error in inputs) | Learned by the Gaussian head — the model's predicted sigma represents how noisy the problem is at each location/depth |
| **Epistemic (reducible)** | Uncertainty due to limited training data or model capacity | Estimated via MC Dropout — run the model N times with dropout active, compute variance of predictions |

### 6.2 How uncertainty is computed

**During training (Gaussian heteroscedastic NLL loss):**

The model outputs mu (predicted temperature) and log sigma-squared (log variance) at every depth and grid cell. The Negative Log-Likelihood loss trains the model to:

- Predict mu close to the true value (minimize (T_true - mu)^2)
- Increase sigma where the problem is genuinely hard (large ocean variability, complex dynamics)
- Decrease sigma where the problem is easy (stable deep ocean, well-constrained surface)

**At inference (MC Dropout for epistemic uncertainty):**

```python
def predict_with_uncertainty(model, x, coords, n_samples=20):
    """Monte Carlo Dropout uncertainty estimation."""
    model.train()  # keep dropout active
    predictions = []
    for _ in range(n_samples):
        mu, log_var = model(x, coords)
        # Sample from predicted distribution
        pred = mu + torch.randn_like(mu) * torch.exp(0.5 * log_var)
        predictions.append(pred)

    predictions = torch.stack(predictions)  # (N, B, 15, H, W)
    mean_pred = predictions.mean(dim=0)
    total_uncertainty = predictions.std(dim=0)
    aleatoric = torch.exp(0.5 * log_var.mean(dim=0))
    epistemic = total_uncertainty**2 - aleatoric**2  # decomposition

    return mean_pred, total_uncertainty, aleatoric, epistemic
```

### 6.3 What the user sees

**Vertical Profile (Mode B):**
- Blue line: model prediction (mu)
- Shaded region: mu +/- sigma (68% confidence) and mu +/- 2*sigma (95% confidence)
- Red dots: ARGO observations (when available)

**Spatial Map (Mode A):**
- Temperature map: color-coded mu at selected depth
- Confidence map: color-coded sigma at selected depth (green = confident, red = uncertain)
- Toggle between views

### 6.4 Uncertainty calibration

After training, we verify that predicted uncertainty matches actual error:

```python
def calibration_check(predictions, uncertainties, observations):
    """Check if predicted sigma matches actual error distribution."""
    errors = np.abs(predictions - observations)
    within_1sigma = np.mean(errors < uncertainties)  # should be ~68%
    within_2sigma = np.mean(errors < 2 * uncertainties)  # should be ~95%
    return within_1sigma, within_2sigma
```

If calibration is off, a post-training calibration layer adjusts sigma values.

---

## Section 7: Training Strategy

### 7.1 Training data

| Component | Source | Period | Shape |
|-----------|--------|--------|-------|
| **Input (X)** | 7 surface variables from Copernicus | 2018-2023 (daily) | (N_days, 7, H, W) |
| **Target (Y)** | GLORYS subsurface temperature | 2018-2023 (daily) | (N_days, 15, H, W) |
| **Validation** | ARGO profiles | 2024-2025 | Sparse, irregular |

### 7.2 Temporal split (LOCKED — Rule 10)

```
Training:   2018-01-01 to 2023-12-31  (6 years, ~2190 days)
Validation: 2024-01-01 to 2024-12-31  (1 year, 366 days)
Testing:    2025-01-01 to 2025-12-31  (1 year, 365 days — ARGO validation period)
```

**NO random shuffling.** Temporal ordering is preserved. The model must never see future data during training.

### 7.3 Sample construction

```
For each day t in training period:
  Input: 7-day window of surface observations [t-6, t-5, ..., t]
  Target: subsurface temperature on day t (GLORYS)

Sliding window (stride=1):
  ~2190 training samples (one per day)
  ~366 validation samples
  ~365 test samples
```

### 7.4 Normalization (Rule 11)

```
For each channel c:
  mean_c = mean(X_train[:, c])     # computed from training data ONLY
  std_c  = std(X_train[:, c])      # computed from training data ONLY

  X_normalized = (X - mean_c) / std_c

Same for Y (target temperatures):
  Y_mean, Y_std computed from training GLORYS only
  Y_normalized = (Y - Y_mean) / Y_std

At inference: denormalize using stored training statistics
```

**Critical:** Normalization statistics are computed ONLY from training data. Using validation/test statistics would be data leakage.

### 7.5 Loss function

```
L_total = L_nll + lambda_1 * L_smooth + lambda_2 * L_surface + lambda_3 * L_deep

Where:
  L_nll      = -log p(T_obs | mu, sigma^2)       # Gaussian NLL (primary loss)
  L_smooth   = sum_d |mu_d - mu_{d+1}|^2 / delta_z_d  # vertical smoothness
  L_surface  = ||mu_0 - SST_obs||^2               # surface consistency
  L_deep     = sum_{d>300m} ||mu_d - mu_{d-1}||^2 / delta_z_d  # deep stabilization

lambda_1 = 0.1, lambda_2 = 1.0, lambda_3 = 0.01
```

### 7.6 Training hyperparameters

```python
optimizer = Adam(lr=1e-4, weight_decay=1e-5)
scheduler = CosineAnnealingLR(optimizer, T_max=100, eta_min=1e-6)
batch_size = 8
max_epochs = 200
early_stopping_patience = 20
use_amp = True              # float16 on T4 -> 2x speedup
use_gradient_checkpointing = True  # trade compute for memory
```

### 7.7 Baselines for comparison

| Baseline | Description | Implementation |
|----------|-------------|----------------|
| **Climatology** | Monthly mean temperature from training GLORYS | Precompute monthly means per depth |
| **Persistence** | Yesterday's GLORYS profile = today's prediction | Shift target by 1 day |
| **CNN-only** | Spatial features only, no temporal modeling | Remove ConvLSTM from architecture |

These baselines are essential for the evaluation section — they prove our model adds value beyond simple methods.

### 7.8 Colab T4 GPU constraints

| Constraint | Mitigation |
|-----------|-----------|
| 15 GB GPU memory | AMP (float16), gradient checkpointing, spatial sub-sampling (random 32x32 crops during training) |
| ~8h daily limit | 200 epochs x ~250 batches x 0.5s = ~7h total |
| No persistent storage | Save checkpoints to Google Drive; download final model |

---

## Section 8: Inference and Product Pipeline

### 8.1 Two user-facing modes

**Mode A — Spatial Map**

```
Region (North Indian Ocean)
  |
Date (user selects)
  |
Depth (user selects: 0, 5, 10, ..., 1000 m)
  |
0.25° x 0.25° temperature map for that depth on that date
  |
Toggle: Temperature | Confidence (uncertainty) | Both
```

**Mode B — Vertical Profile**

```
User clicks a grid cell on the map
  |
15-depth temperature profile at that location and date
  |
Blue line: model prediction (mu)
Shaded: uncertainty (mu +/- sigma)
Red dots: ARGO comparison (when available)
```

### 8.2 Daily automated pipeline

```
EVERY 24 HOURS (automated):

1. FETCH
   -> Latest available Copernicus data for 7 surface variables
   -> Date: yesterday (Copernicus has ~24h lag)

2. HARMONIZE
   -> Apply harmonization pipeline (Section 4.2)
   -> Output: (1, 7, H, W) tensor

3. PREPARE INPUT
   -> Stack 7-day temporal window [t-6, ..., t]
   -> Add coordinate channels
   -> Normalize with training statistics

4. INFERENCE
   -> Load pre-trained model
   -> Forward pass -> mu, log sigma-squared at 15 depths
   -> MC Dropout -> epistemic uncertainty
   -> Denormalize to °C

5. STORE
   -> Save to database/cache:
     - timestamp
     - grid coordinates
     - temperature profiles (15 depths x H x W)
     - uncertainty maps (aleatoric + epistemic)
     - model version

6. VALIDATE (when ARGO data available)
   -> Match ARGO profiles to model grid
   -> Compute depth-wise RMSE, bias, correlation
   -> Store validation metrics
```

### 8.3 Serving pre-computed results

When user/evaluator queries:

```
GET /api/v1/temperature?lat=15.0&lon=85.0&date=2025-09-03

Response:
{
  "lat": 15.0, "lon": 85.0, "date": "2025-09-03",
  "depths_m": [0, 5, 10, 20, 30, 50, 75, 100, 125, 150, 200, 300, 500, 700, 1000],
  "temperature_c": [28.1, 27.9, 27.5, 26.2, 24.8, 22.1, 18.5, 15.2, 12.8, 10.5, 8.2, 6.1, 4.5, 3.8, 3.2],
  "uncertainty_c": [0.3, 0.4, 0.5, 0.8, 1.2, 1.5, 1.8, 2.0, 1.9, 1.7, 1.3, 0.9, 0.6, 0.4, 0.3],
  "argo_comparison": {
    "available": true,
    "argo_temperature_c": [28.0, 27.8, 27.3, 26.0, 24.5, 21.8, 18.2, 15.0, 12.5, 10.2, 8.0, 6.0, 4.4, 3.7, 3.1],
    "rmse_by_depth": [0.1, 0.1, 0.2, 0.2, 0.3, 0.3, 0.3, 0.2, 0.3, 0.3, 0.2, 0.1, 0.1, 0.1, 0.1]
  }
}
```

---

## Section 9: Scientific Evaluation

**This is one of the strongest sections.** It proves our system works, not just that it runs.

### 9.1 Evaluation protocol

```
Training period (2018-2023):
  -> Model predictions vs GLORYS (upper bound on performance)
  -> Shows: "our model can learn the training data"

Validation period (2024):
  -> Model predictions vs GLORYS (out-of-sample from training perspective)
  -> Shows: "our model generalizes to unseen years"

Testing period (2025):
  -> Model predictions vs ARGO (independent, never used in training)
  -> Shows: "our model matches real ocean observations"
  -> This is the PRIMARY evaluation result
```

### 9.2 Metrics (depth-wise)

For each depth d in {0, 5, 10, 20, 30, 50, 75, 100, 125, 150, 200, 300, 500, 700, 1000}:

```
RMSE_d  = sqrt(mean((mu_d - T_obs_d)^2))
Bias_d  = mean(mu_d - T_obs_d)
Corr_d  = Pearson correlation(mu_d, T_obs_d)
R2_d    = 1 - SS_res / SS_tot
```

### 9.3 Model comparison table

**This table is the "money slide" for evaluators:**

| Model | RMSE (0-200m) | RMSE (200-1000m) | Overall RMSE | R2 | ARGO Corr |
|-------|--------------|-----------------|-------------|-----|----------|
| Climatology | -- | -- | -- | -- | -- |
| Persistence | -- | -- | -- | -- | -- |
| CNN-only | -- | -- | -- | -- | -- |
| **CNN + ConvLSTM (OceanEmbed)** | **--** | **--** | **--** | **--** | **--** |

**Evaluated against ARGO (independent) — not against training data.**

### 9.4 Depth-wise analysis

```
Depth (m)  | RMSE  | Bias  | Corr  | R2    | Notes
-----------|-------|-------|-------|-------|------------------
0          | --    | --    | --    | --    | Surface: most variable
5          | --    | --    | --    | --    |
10         | --    | --    | --    | --    |
20         | --    | --    | --    | --    | Mixed layer
30         | --    | --    | --    | --    |
50         | --    | --    | --    | --    | Thermocline onset
75         | --    | --    | --    | --    |
100        | --    | --    | --    | --    | Thermocline: hardest
125        | --    | --    | --    | --    |
150        | --    | --    | --    | --    |
200        | --    | --    | --    | --    | Thermocline base
300        | --    | --    | --    | --    |
500        | --    | --    | --    | --    | Deep: most stable
700        | --    | --    | --    | --    |
1000       | --    | --    | --    | --    | Deepest: least variable
```

### 9.5 Spatial error analysis

- Error map: RMSE at each grid cell (0.25° resolution) for selected depth
- Identifies where model performs well vs poorly
- Reveals if errors correlate with specific oceanographic features (eddies, upwelling zones)

### 9.6 Uncertainty calibration

```
Within 1 sigma:  should be ~68% of ARGO observations
Within 2 sigma:  should be ~95% of ARGO observations
```

If calibration is off, the uncertainty estimates are misleading. This check is mandatory.

### 9.7 Comparison to GODAS

If GODAS data is accessible for our domain:
- Compare our model's RMSE against GODAS RMSE (both validated against ARGO)
- GODAS is the operational baseline from INCOIS — beating it is a strong result
- If GODAS is not accessible, state this as a limitation and compare to climatology instead

### 9.8 What evaluators will ask

| Question | Answer |
|----------|--------|
| "Is your model more accurate than existing methods?" | See comparison table (Section 9.3) — we show RMSE vs climatology, persistence, CNN-only, and GODAS (if available) |
| "How do you know it works on real data?" | Independent ARGO validation — ARGO is never used in training |
| "When should I trust the prediction?" | Uncertainty map — sigma quantifies confidence at every grid cell and depth |
| "What are the limitations?" | Thermocline (50-200m) has highest error; deep ocean (500-1000m) is most accurate; errors increase in dynamically complex regions |

---

## Section 10: Implementation Plan

### Phase 3: ML Model Architecture (CURRENT)

| Step | File | Description |
|------|------|-------------|
| 3.1 | ml/src/oceanembed_ml/models/reconstruction_net.py | CNN encoder + ConvLSTM + decoder + uncertainty head |
| 3.2 | ml/src/oceanembed_ml/losses/nll_loss.py | Gaussian NLL loss |
| 3.3 | ml/src/oceanembed_ml/losses/physics_loss.py | Vertical smoothness + surface consistency + deep stabilization |
| 3.4 | ml/src/oceanembed_ml/models/uncertainty.py | MC Dropout inference + calibration |
| 3.5 | ml/tests/test_model.py | Unit tests for model forward pass, loss, shapes |

### Phase 4: Training Pipeline

| Step | File | Description |
|------|------|-------------|
| 4.1 | ml/src/oceanembed_ml/data/loader.py | Zarr tensor loader with temporal windowing |
| 4.2 | ml/src/oceanembed_ml/training/trainer.py | Training loop with AMP, gradient checkpointing, early stopping |
| 4.3 | ml/src/oceanembed_ml/training/baselines.py | Climatology, persistence, CNN-only baselines |
| 4.4 | colab/oceanembed_training.ipynb | Updated Colab notebook with full training pipeline |
| 4.5 | ml/scripts/train_colab_entry.py | Training entry point |

### Phase 5: Evaluation Pipeline

| Step | File | Description |
|------|------|-------------|
| 5.1 | ml/src/oceanembed_ml/evaluation/depth_metrics.py | Depth-wise RMSE, bias, correlation, R2 |
| 5.2 | ml/src/oceanembed_ml/evaluation/argo_match.py | Match ARGO profiles to model grid |
| 5.3 | ml/src/oceanembed_ml/evaluation/calibration.py | Uncertainty calibration check |
| 5.4 | ml/src/oceanembed_ml/evaluation/comparison.py | Model comparison table generation |
| 5.5 | ml/scripts/evaluate.py | Full evaluation pipeline |

### Phase 6: ARGO Validation

| Step | File | Description |
|------|------|-------------|
| 6.1 | data-engineering/scripts/download_argo.py | Download ARGO GDAC profiles for North Indian Ocean |
| 6.2 | ml/src/oceanembed_ml/evaluation/argo_validation.py | Independent validation against ARGO |

### Phase 7: Inference and Serving API

| Step | File | Description |
|------|------|-------------|
| 7.1 | backend/src/oceanembed_api/inference.py | Daily automated inference pipeline |
| 7.2 | backend/src/oceanembed_api/routes/temperature.py | API endpoints for pre-computed results |
| 7.3 | backend/src/oceanembed_api/routes/profiles.py | Vertical profile endpoint |

### Phase 8: Frontend (FLEXIBLE)

| Step | File | Description |
|------|------|-------------|
| 8.1 | frontend/src/components/SpatialMap.tsx | Mode A: spatial temperature map |
| 8.2 | frontend/src/components/VerticalProfile.tsx | Mode B: depth profile with uncertainty |
| 8.3 | frontend/src/components/UncertaintyLayer.tsx | Confidence visualization |

---

## Section 11: Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|-----------|
| T4 GPU too slow for training | Delays Phase 4 | Medium | Start with small sub-region; optimize hyperparameters; use gradient accumulation |
| GLORYS reanalysis bias | Model learns biases, not real ocean | Low | ARGO validation catches this; compare GLORYS vs ARGO directly |
| Temporal data leakage | Overly optimistic results | Low | Strict temporal split (Section 7.2); no random shuffle; time-series CV |
| Uncertainty miscalibration | Confidence intervals misleading | Medium | Calibration layer post-training; reliability diagrams; mandatory calibration check |
| Memory overflow on T4 | Training crashes | Medium | Spatial sub-sampling (32x32 crops); gradient checkpointing; reduce batch size |
| ARGO data quality issues | Validation unreliable | Low | Use quality-controlled ARGO GDAC; filter by quality flags; check for outliers |
| Copernicus API downtime | Cannot run daily pipeline | Low | Cache latest data locally; retry logic; fallback to previous day's data |
| Model overfits to GLORYS | Poor ARGO validation | Medium | Regularization (weight decay, dropout); early stopping; monitor ARGO metrics during training |

---

## Section 12: Measurable Success Criteria

### 12.1 Model performance (quantitative)

| Criterion | Target | Measurement |
|-----------|--------|-------------|
| Overall RMSE vs ARGO (test set) | < 0.6 °C | ml/scripts/evaluate.py |
| RMSE at 0-200m vs ARGO | < 0.8 °C | Depth-wise evaluation |
| RMSE at 200-1000m vs ARGO | < 0.4 °C | Depth-wise evaluation |
| R2 vs ARGO (overall) | > 0.90 | Depth-wise evaluation |
| Correlation vs ARGO (all depths) | > 0.95 | Depth-wise evaluation |
| Beat climatology | RMSE < 50% of climatology RMSE | Baseline comparison |
| Beat persistence | RMSE < 70% of persistence RMSE | Baseline comparison |
| Beat CNN-only | RMSE < 90% of CNN-only RMSE | Ablation study |

### 12.2 Uncertainty calibration (quantitative)

| Criterion | Target | Measurement |
|-----------|--------|-------------|
| Within 1 sigma coverage | 60-75% of ARGO observations | Calibration check |
| Within 2 sigma coverage | 90-99% of ARGO observations | Calibration check |

### 12.3 Engineering (qualitative)

| Criterion | Target |
|-----------|--------|
| Training completes on Colab T4 | < 8 hours, checkpoint saved to Drive |
| Daily inference pipeline | Automated, no human intervention |
| API response time | < 1 second for pre-computed results |
| Model file size | < 50 MB |
| Test coverage | >= 80% for ml/ module |

### 12.4 Evaluator-facing deliverables

| Criterion | Target |
|-----------|--------|
| Spatial map (Mode A) | Working, shows temperature at any depth/date |
| Vertical profile (Mode B) | Working, shows 15-depth profile with uncertainty |
| ARGO comparison | Working, shows red dots on profile when available |
| Uncertainty map | Working, shows confidence at each grid cell |
| Comparison table | Shows our model vs baselines vs GODAS |

### 12.5 What we do NOT claim

- We do NOT claim to replace GODAS
- We do NOT claim real-time capability (data has 24h lag)
- We do NOT claim global coverage (North Indian Ocean only)
- We do NOT claim the model works for all ocean variables (temperature only)
- We do NOT hide limitations — we report depth-wise errors honestly

---

## Appendix A: Verified Dataset IDs

All verified via copernicusmarine.describe() on 2026-09-02:

| Variable | Dataset ID | Resolution | Cadence |
|----------|-----------|-----------|---------|
| SST | METOFFICE-GLO-SST-L4-REP-OBS-SST | 0.05° | Daily |
| SSS | cmems_obs-mob_glo_phy-sss_my_multi_P1D | 0.25° | Daily |
| SSH/SLA | cmems_obs-sl_glo_phy-ssh_my_allsat-l4-duacs-0.125deg_P1D | 0.125° | Daily |
| Current U/V | cmems_obs-mob_glo_phy-cur_my_0.25deg_P1D-m | 0.25° | Daily |
| Wind U/V | cmems_obs-wind_glo_phy_my_l4_0.125deg_PT1H | 0.125° | Hourly to daily |
| GLORYS T | cmems_mod_glo_phy_my_0.083deg_P1D-m | 0.083° | Daily |

## Appendix B: Canonical Depths (LOCKED)

```
0, 5, 10, 20, 30, 50, 75, 100, 125, 150, 200, 300, 500, 700, 1000 meters
```

## Appendix C: Reference Papers

| Paper | Citation | Key Insight |
|-------|----------|-------------|
| Su et al. 2022 | Remote Sensing, 14(13), 3198. DOI:10.3390/rs14133198 | ConvLSTM for subsurface reconstruction; trained on Argo; R2=0.99, RMSE=0.34 C |
| Loo et al. 2026 | arXiv:2605.00860v1 [physics.ao-ph] | Spatiotemporal clustering reduces RMSE 12-27%; Attention U-Net best performer |
