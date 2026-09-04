# OceanEmbed — ML Architecture Specification v2.1

**Status:** Implementation-Ready
**Competition:** SIH26066 — OceanEmbed
**Objective:** Build a scientifically credible, reproducible, uncertainty-aware system for reconstructing subsurface ocean temperature from surface observations.

This revision is based directly on the v2.0 specification and 14 evaluator corrections.

---

## 0. Implementation Gate

**No production implementation begins until these contracts pass the data/model verification checks below.**

The architecture is intentionally **not made more complicated**. The core remains:

> **7 surface variables -> 7-day temporal sequence -> CNN spatial encoder -> ConvLSTM -> depth decoder -> 15-depth temperature + uncertainty -> independent ARGO evaluation**

Clustering, advanced epistemic uncertainty, Transformer/GNN components and GODAS comparison remain **optional/deferred**.

---

## 1. Problem Definition

## 1.1 Input

OceanEmbed receives seven surface-ocean variables:

1. SST
2. SSS
3. SSH/SLA
4. Surface Current U
5. Surface Current V
6. Surface Wind U
7. Surface Wind V

The inputs are harmonized to:

> **0.25° x 0.25° daily spatial resolution**

and organized into a temporal window.

### Canonical tensor

```
X ∈ R[B, T, 7, H, W]
```

where:

- `B` = batch
- `T = 7` = temporal window
- `7` = input channels
- `H` = latitude grid dimension
- `W` = longitude grid dimension

---

## 2. Spatial Contract

## 2.1 Problem domain

The target SIH domain is:

```
Latitude:   5°N -> 30°N
Longitude:  45°E -> 105°E
Resolution: 0.25° x 0.25°
```

### Important correction from v2.0

The previous specification used:

```
H = 69
W = 81
```

for an example regional grid.

That **must not be hardcoded as the full problem-domain shape**.

The implementation will derive `H` and `W` from the canonical coordinate definition.

```python
lat = canonical_latitudes()
lon = canonical_longitudes()

H = len(lat)
W = len(lon)
```

This prevents an accidental mismatch between:

- full North Indian Ocean
- Bay of Bengal
- Arabian Sea
- demonstration subregions.

---

## 3. Data Contract

Before training, a machine-readable dataset manifest must verify every product.

| Channel   | Required information                                         |
| --------- | ------------------------------------------------------------ |
| SST       | Dataset ID, variable name, units, native resolution, cadence |
| SSS       | Dataset ID, variable name, units, native resolution, cadence |
| SSH/SLA   | Dataset ID, variable name, units, native resolution, cadence |
| Current U | Dataset ID, variable name, units, native resolution, cadence |
| Current V | Dataset ID, variable name, units, native resolution, cadence |
| Wind U    | Dataset ID, variable name, units, native resolution, cadence |
| Wind V    | Dataset ID, variable name, units, native resolution, cadence |

### Rule

**Dataset IDs in the specification are candidates until verified by the current Copernicus catalogue/API.**

The pipeline must fail loudly if:

- dataset unavailable
- variable missing
- unexpected units
- unexpected dimensions
- unexpected coordinate system
- unexpected temporal cadence
- incompatible resolution.

No silent substitution.

---

## 4. Data Harmonization Contract

The raw products may have different:

- spatial resolutions
- temporal frequencies
- coordinate conventions
- units
- masks
- missing-value conventions.

Therefore:

```
Raw products
      |
Quality control
      |
Variable extraction
      |
Temporal alignment
      |
Spatial regridding
      |
Common 0.25° grid
      |
Ocean validity mask
      |
Missing-data mask
      |
Unit normalization
      |
Training-statistic normalization
      |
7-channel tensor
```

### Regridding

The exact method is **variable-dependent and must be recorded in the dataset manifest**.

We will not claim:

> "bilinear for everything."

Continuous variables may use an appropriate interpolation method; masks/categories use nearest-neighbour semantics.

### Missing data

**Never replace invalid ocean observations with zero without a mask.**

The system maintains:

```
X
valid_mask
```

so the model/evaluation pipeline knows which values are genuinely observed.

---

## 5. Temporal Contract

## Primary model window

```
T = 7 days
```

For prediction day `t`:

```
[t-6, t-5, t-4, t-3, t-2, t-1, t]
```

is supplied to the model.

Target:

```
Y(t)
```

is the subsurface temperature field for day `t`.

### Why 7 days?

It is an **engineering/scientific hypothesis**, not a proven optimum.

We will compare:

```
T = 1     CNN baseline
T = 3     temporal experiment
T = 7     primary model
```

if compute permits.

We select the window based on validation performance and computational practicality.

---

## 6. Target Contract

The output contains temperature at exactly:

```
0
5
10
20
30
50
75
100
125
150
200
300
500
700
1000 m
```

### Output tensor

```
μ ∈ R[B, 15, H, W]
```

where:

```
μ[:, 0, :, :] = 0 m
μ[:, 1, :, :] = 5 m
...
μ[:, 14, :, :] = 1000 m
```

Units after inverse normalization:

> **°C**

---

## 7. Core Model Contract

## OceanEmbedNet

```
Input
[B, 7, 7, H, W]
       |
Coordinate/seasonal context
       |
CNN spatial encoder
       |
[B, 7, F, H', W']
       |
ConvLSTM
       |
[B, F', H', W']
       |
Spatial decoder
       |
[B, 15, H, W]
```

### Important correction

Instead of treating day-of-year as an ordinary spatial coordinate channel, use seasonal encoding:

```
sin(2π * day_of_year / 365.25)
cos(2π * day_of_year / 365.25)
```

Latitude and longitude remain spatial coordinate fields.

Thus:

```
7 observation channels
+
2 seasonal channels
+
2 spatial coordinate channels
```

when coordinate context is enabled.

The model implementation should make this configurable.

---

## 8. CNN Encoder

Primary architecture:

```
Input: C_in
      |
Conv 3×3
      |
32 features
      |
downsample
      |
64 features
      |
downsample
      |
128 features
      |
downsample
```

The exact normalization/activation choice is configurable.

### Requirement

The encoder must preserve enough spatial information for reconstruction.

If we call it **U-Net**, it must actually have skip connections.

Otherwise call it:

> **Multi-scale CNN encoder-decoder**

This removes the ambiguity present in v2.0.

---

## 9. ConvLSTM

The temporal component receives:

```
[B, 7, 128, H', W']
```

and learns temporal evolution while preserving spatial structure.

Primary configuration:

```
ConvLSTM2D
input channels: 128
hidden channels: configurable
layers: configurable
kernel: 3×3
```

### Important

The specification does **not** assume that three ConvLSTM layers are automatically optimal.

We will benchmark a lightweight configuration first.

The goal is:

> sufficient temporal representation within hackathon compute constraints.

---

## 10. Decoder

The temporal representation is decoded back to the original grid:

```
latent spatial representation
        |
upsampling
        |
feature refinement
        |
H x W
        |
15 temperature channels
```

### Depth representation

We will initially use **15 output channels**.

This is simpler and directly matches the required output contract.

Per-depth specialization can be implemented as separate lightweight heads **only if the baseline demonstrates a benefit**.

---

## 11. Uncertainty Contract

This section is significantly revised.

## Primary uncertainty: Aleatoric

The network outputs:

```
μ
log_variance
```

with:

```
μ       ∈ R[B,15,H,W]
log_var ∈ R[B,15,H,W]
```

The uncertainty represents the model's estimated observation/process noise at each location and depth.

Gaussian NLL trains both:

- accurate mean prediction
- meaningful variance estimation.

### Numerical safety

Variance must be constrained:

```
σ² = softplus(raw_variance) + ε
```

rather than allowing arbitrary negative/unstable variance.

---

## 12. Epistemic Uncertainty

### Status: OPTIONAL

MC Dropout will **not** be part of the first implementation.

If time and validation justify it:

```
Run model N times
       |
μ₁, μ₂, ... μN
       |
variance across μ predictions
       |
epistemic uncertainty
```

Then distinguish:

```
Aleatoric = predicted observation/process uncertainty

Epistemic = model/data uncertainty estimated through stochastic inference
```

We will **not** calculate epistemic uncertainty by subtracting aleatoric variance from an incorrectly defined sampled variance.

That issue in v2.0 is fixed here.

---

## 13. Uncertainty Calibration

The model must be evaluated for calibration.

For Gaussian predictions:

```
μ ± 1σ
μ ± 2σ
```

are compared with independent observations.

But we will report **empirical coverage**, not assume:

> "1σ = 68%"

unless the distribution is sufficiently calibrated.

### Required outputs

```
Coverage @ 1σ
Coverage @ 2σ
Reliability/calibration plot
```

Calibration is a result, not a guaranteed property.

---

## 14. Loss Function

Primary loss:

```
L_NLL
```

Then controlled experiments:

### Experiment A

```
L = NLL
```

### Experiment B

```
L = NLL + λsmooth Lsmooth
```

### Experiment C

```
L = NLL + λsmooth Lsmooth
    + λsurface Lsurface
```

### Optional

Deep stabilization term only if scientifically justified by results.

### Crucial rule

The coefficients are **hyperparameters to be selected using validation experiments**.

We do not freeze:

```
λ1 = 0.1
λ2 = 1.0
λ3 = 0.01
```

as scientifically established constants.

---

## 15. Physics Constraints

We will use **soft constraints**, not claim that the model is a complete physical ocean model.

Candidate constraints:

### Vertical smoothness

Penalize unrealistic adjacent-depth discontinuities.

### Surface consistency

Test whether predicted near-surface temperature remains consistent with the chosen target definition and observed SST.

### Deep stability

Use cautiously because "deep = stable" is not a universal rule.

Every constraint must survive an ablation:

```
Without constraint
vs
With constraint
```

If it doesn't improve the scientific metrics or produce a useful physical improvement, remove it.

---

## 16. Training Data Protocol

The v2.0 dates are **provisional until coverage verification**.

Candidate protocol:

```
Training:    2018-2023
Validation:  2024
External evaluation: 2025 ARGO
```

Before freezing, generate a coverage matrix:

```
                 2018 ... 2023 | 2024 | 2025
SST                  ✓             ✓      ✓
SSS                  ✓             ✓      ✓
SSH                  ✓             ✓      ✓
Current U/V          ✓             ✓      ✓
Wind U/V             ✓             ✓      ✓
GLORYS               ✓             ✓      ✓
ARGO                  -             -      ✓
```

If a required variable has insufficient coverage, the dates must change.

---

## 17. Leakage Prevention

This is **non-negotiable**.

### Training statistics

Computed only from training data:

```
mean
std
```

### Test information

Never used for:

- model selection
- hyperparameter tuning
- normalization
- architecture selection
- threshold selection.

### Temporal windows

Ensure a validation/test sample's input history does not accidentally cross an inappropriate data boundary.

### ARGO

ARGO evaluation data remains excluded from training and model-selection logic according to the defined evaluation protocol.

---

## 18. Baselines

We retain three essential baselines.

### Baseline 1 — Climatology

Monthly mean temperature.

### Baseline 2 — Persistence

Previous available profile.

### Baseline 3 — CNN-only

Same spatial encoder/decoder but without temporal modeling.

Then:

```
CNN
  |
CNN + ConvLSTM
```

tests whether temporal information actually improves the reconstruction.

---

## 19. Primary Scientific Evaluation

The primary metrics are:

### RMSE

```
RMSE = sqrt(mean((prediction - observation)²))
```

### Bias

```
Bias = mean(prediction - observation)
```

### Pearson correlation

Measures agreement in variability.

### R²

Secondary explanatory metric.

All are reported:

- overall
- depth-wise
- spatially where appropriate.

---

## 20. ARGO Matching Protocol

Before implementation, freeze:

1. spatial matching radius
2. temporal matching window
3. accepted ARGO quality flags
4. vertical interpolation method
5. treatment of missing deep observations
6. minimum profile depth
7. minimum number of matched observations for reporting statistics.

For example, the system should **not fabricate a 1000 m ARGO observation** when a float only measured to 600 m.

---

## 21. Evaluation Hierarchy

The final scientific evaluation becomes:

```
             TRAIN
        GLORYS 2018-23
              |
            MODEL
              |
       ┌──────┴──────┐
       ↓             ↓
   Validation     External test
     GLORYS          ARGO
     2024            2025
```

### Primary claim

**ARGO performance is the main external evidence.**

GLORYS performance demonstrates reconstruction against the training/reference field but should not be presented as equivalent to direct observational validation.

---

## 22. Competition / Research Claims

Replace absolute statements such as:

> "No existing system does X."

with:

> **"OceanEmbed's targeted differentiation is the combination of..."**

1. North Indian Ocean regional focus
2. seven surface channels
3. standardized 0.25° reconstruction
4. 15-depth output
5. uncertainty estimation
6. independent ARGO evaluation
7. operational pre-computation/serving.

This is much safer scientifically.

---

## 23. Clustering

### Status: DEFERRED

No clustering in the first production model.

Experiment only after:

```
CNN baseline
      |
CNN + ConvLSTM
      |
evaluation
```

If clustering is tested:

> It must demonstrate a predefined, statistically meaningful improvement over the primary baseline.

I would **not permanently freeze ">5% RMSE improvement"** until we define whether that means relative overall RMSE, depth-weighted RMSE, or statistically significant improvement.

---

## 24. Product Contract

## Mode A — Spatial Map

User selects:

```
Region
Date
Depth
```

System returns:

```
0.25° x 0.25°
subsurface temperature field
```

with optional:

```
uncertainty layer
```

---

## Mode B — Vertical Profile

User clicks:

```
latitude
longitude
```

System returns:

```
15 depth levels
temperature
uncertainty
```

and ARGO comparison when available.

---

## Judge Validation View

Show:

```
OceanEmbed
vs
ARGO
```

plus:

```
RMSE
Bias
Correlation
Coverage
```

This should be one of the most important demo screens.

---

## 25. Inference Contract

Input:

```
7 days x 7 variables
```

Output:

```
15 depths x H x W
```

Inference performs:

```
Load model
      |
Load preprocessing version
      |
Load normalization statistics
      |
Validate input schema
      |
Model inference
      |
Uncertainty
      |
Inverse normalization
      |
Physical/unit checks
      |
Store result
```

Every prediction stores:

```
model_version
dataset_version
preprocessing_version
normalization_version
timestamp
region
grid_definition
depth_definition
```

---

## 26. Operational Strategy

For the hackathon:

> **Pre-computed results are the primary demo path.**

Live ingestion is a secondary capability.

```
COPERNICUS
    |
daily ingestion
    |
inference
    |
cache
    |
frontend
```

If Copernicus is unavailable during the presentation:

```
cached verified result
        |
        DEMO CONTINUES
```

This is much safer than making the entire demo dependent on an external API.

---

## 27. Success Criteria

We now divide them into two categories.

## Engineering acceptance

Must work:

- [ ] data ingestion
- [ ] harmonization
- [ ] tensor generation
- [ ] CNN forward pass
- [ ] ConvLSTM forward pass
- [ ] training checkpoint
- [ ] inference
- [ ] API
- [ ] spatial map
- [ ] profile
- [ ] ARGO matching
- [ ] evaluation pipeline

## Scientific targets

These are **targets, not guaranteed results**:

- outperform climatology
- outperform persistence
- demonstrate value over CNN-only
- achieve useful ARGO agreement
- produce calibrated uncertainty
- demonstrate depth-wise performance transparently.

We will not manufacture numerical success claims before experiments.

---

## 28. Final MVP Scope

## MUST BUILD

```
✓ 7-variable ingestion
✓ data harmonization
✓ 0.25° grid
✓ 7-day input sequence
✓ CNN baseline
✓ CNN + ConvLSTM
✓ 15-depth output
✓ Gaussian uncertainty
✓ ARGO evaluation
✓ depth-wise metrics
✓ spatial map
✓ vertical profile
```

## SHOULD BUILD

```
✓ uncertainty map
✓ validation view
✓ automated inference
✓ model comparison
✓ reproducibility metadata
```

## DEFER

```
○ clustering
○ Transformer
○ GNN
○ advanced epistemic uncertainty
○ GODAS comparison
○ complex cloud/Kubernetes deployment
```

---

## 29. The Final Architecture

This is the architecture I would now take forward:

```
                 SURFACE OBSERVATIONS
                         |
             ┌───────────┴───────────┐
             │ 7 Copernicus-derived  │
             │ surface variables     │
             └───────────┬───────────┘
                         ↓
                 QUALITY CONTROL
                         ↓
              TEMPORAL ALIGNMENT
                         ↓
               SPATIAL REGRIDDING
                         ↓
                 0.25° x 0.25°
                         ↓
                 7-DAY SEQUENCE
                         ↓
              ┌──────────────────┐
              │ CNN SPATIAL      │
              │ ENCODER          │
              └────────┬─────────┘
                       ↓
              ┌──────────────────┐
              │ ConvLSTM         │
              │ TEMPORAL MODEL   │
              └────────┬─────────┘
                       ↓
              ┌──────────────────┐
              │ DEPTH DECODER    │
              └────────┬─────────┘
                       ↓
              ┌────────┴─────────┐
              ↓                  ↓
        TEMPERATURE μ       UNCERTAINTY σ
          15 depths            15 depths
              │                  │
              └────────┬─────────┘
                       ↓
             INDEPENDENT ARGO
                EVALUATION
                       ↓
          ┌────────────┼────────────┐
          ↓            ↓            ↓
       MAP VIEW    PROFILE VIEW  VALIDATION
```

---

## Appendix A: Verified Dataset IDs

All verified via copernicusmarine.describe() on 2026-09-02:

| Variable | Dataset ID | Variable Name | Units | Native Resolution | Cadence | Regrid Method |
|----------|-----------|---------------|-------|-------------------|---------|---------------|
| SST | METOFFICE-GLO-SST-L4-REP-OBS-SST | analysed_sst | K (convert to C) | 0.05° | Daily | Bilinear |
| SSS | cmems_obs-mob_glo_phy-sss_my_multi_P1D | sos | PSU | 0.25° | Daily | None |
| SSH/SLA | cmems_obs-sl_glo_phy-ssh_my_allsat-l4-duacs-0.125deg_P1D | sla | m | 0.125° | Daily | Bilinear |
| Current U | cmems_obs-mob_glo_phy-cur_my_0.25deg_P1D-m | uo | m/s | 0.25° | Daily | None |
| Current V | cmems_obs-mob_glo_phy-cur_my_0.25deg_P1D-m | vo | m/s | 0.25° | Daily | None |
| Wind U | cmems_obs-wind_glo_phy_my_l4_0.125deg_PT1H | eastward_wind | m/s | 0.125° | Hourly->Daily | Bilinear |
| Wind V | cmems_obs-wind_glo_phy_my_l4_0.125deg_PT1H | northward_wind | m/s | 0.125° | Hourly->Daily | Bilinear |
| GLORYS T | cmems_mod_glo_phy_my_0.083deg_P1D-m | thetao | K (convert to C) | 0.083° | Daily | Bilinear + depth interpolation |

## Appendix B: Canonical Depths (LOCKED)

```
[0, 5, 10, 20, 30, 50, 75, 100, 125, 150, 200, 300, 500, 700, 1000]
```

## Appendix C: Reference Papers

| Paper | Citation | Key Insight |
|-------|----------|-------------|
| Su et al. 2022 | Remote Sensing, 14(13), 3198. DOI:10.3390/rs14133198 | ConvLSTM for subsurface reconstruction; trained on Argo; R2=0.99, RMSE=0.34 C |
| Loo et al. 2026 | arXiv:2605.00860v1 [physics.ao-ph] | Spatiotemporal clustering reduces RMSE 12-27%; Attention U-Net best performer |

## Appendix D: Loss Function Details

### NLL Loss

```
L_NLL = 0.5 * mean(log(σ²) + (T_obs - μ)² / σ²)
```

where σ² = softplus(raw_log_var) + ε, ε = 1e-6

### Vertical Smoothness

```
L_smooth = mean((μ_d - μ_{d+1})² / Δz_d)  for d = 0..13
```

### Surface Consistency

```
L_surface = mean((μ_0 - T_GLORYS_surface)²)
```

Note: μ_0 is supervised against GLORYS surface temperature, NOT satellite SST directly. This ensures consistency with the training target definition.

### Deep Stabization (optional, experiment D only)

```
L_deep = mean((μ_d - μ_{d-1})² / Δz_d)  for d where depth > 300m
```

## Appendix E: Ablation Study Protocol

### Experiment A — Climatology baseline

```
Monthly mean GLORYS temperature per depth
No model needed
```

### Experiment B — Persistence baseline

```
Yesterday's GLORYS profile = today's prediction
No model needed
```

### Experiment C — CNN only (T=1)

```
Spatial features only, no temporal modeling
L = NLL
```

### Experiment D — CNN + ConvLSTM (T=7)

```
Full spatiotemporal model
L = NLL
```

### Experiment E — CNN + ConvLSTM + physics constraints

```
Full model with vertical smoothness
L = NLL + λsmooth * L_smooth
```

### Experiment F — CNN + ConvLSTM + uncertainty + physics

```
Full model with calibrated uncertainty
L = NLL + λsmooth * L_smooth + λsurface * L_surface
```

Selection criteria: best validation RMSE + calibrated uncertainty.

### Experiment G — Temporal window comparison (if compute permits)

```
T=1 vs T=3 vs T=7
Same architecture, different input windows
Select by validation performance
```

## Appendix F: ARGO Matching Protocol (to be frozen before implementation)

### Pre-implementation requirements

1. Download ARGO GDAC profiles for North Indian Ocean (5-30N, 45-105E)
2. Filter by quality flags (QC = 1 or 2)
3. Select profiles with temperature measurements

### Matching rules (candidates, to be verified)

1. **Spatial matching:** ARGO profile within radius R of a 0.25° grid cell center. Candidate R = 0.125° (half grid cell).
2. **Temporal matching:** ARGO profile within ±0.5 days of model prediction date.
3. **Vertical interpolation:** Linear interpolation from ARGO native depths to 15 standard depths.
4. **Minimum depth:** Profile must reach at least 200m to be included in thermocline evaluation.
5. **Missing deep observations:** If ARGO profile does not reach 1000m, evaluate only shallower depths for that profile. Do NOT fabricate deep observations.
6. **Minimum matched depths:** Profile must have ≥5 of 15 standard depths to be included.
7. **Minimum profiles for statistics:** At least 30 matched profiles required for depth-wise RMSE reporting.

These values are candidates and must be verified against actual ARGO data availability before freezing.
