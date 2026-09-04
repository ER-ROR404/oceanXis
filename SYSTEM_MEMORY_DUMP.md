# SYSTEM_MEMORY_DUMP.md

> STATUS: SOURCE OF TRUTH FOR OCEANEMBED / SIH26066
>
> PURPOSE: Transfer the complete project context from the ChatGPT mentoring environment into a local OpenCode terminal IDE without losing architectural decisions, domain assumptions, data rules, constraints, unresolved items, or implementation direction.
>
> IMPORTANT: This document distinguishes between:
> - LOCKED REQUIREMENT = explicitly required by the problem statement or established decision.
> - CONFIRMED = verified from an authoritative/current source.
> - PROPOSED = recommended engineering design, not an official SIH requirement.
> - UNRESOLVED = must be verified before implementation.
>
> Do NOT silently convert PROPOSED or UNRESOLVED items into facts.

---

# 0. PROJECT IDENTITY

## Project

OceanEmbed

## SIH Problem Statement

SIH26066

## Official Problem Title

OceanEmbed - Satellite Embedding-Based Deep Learning Framework for Reconstruction of Subsurface Ocean Temperature from Surface Satellite Observations.

## Organization

Ministry of Earth Sciences (MoES)

## Department

Indian National Centre for Ocean Information Services (INCOIS)

## Category

Software

## Current source-of-truth interpretation

The official SIH problem statement must be treated as the authority for exact wording, scope, theme/category, required inputs, outputs, and evaluation expectations.

Some third-party SIH mirrors classify the problem differently. Do NOT use third-party classification to override the official SIH portal.

## Hardware constraint

The team explicitly does NOT want hardware.

This project is software-only.

---

# 1. EXECUTIVE SYSTEM DEFINITION

OceanEmbed is an AI-powered oceanographic reconstruction system.

The system receives daily surface ocean observations and learns the hidden relationship between those surface observations and the three-dimensional subsurface temperature structure.

The core transformation is:

    DAILY SURFACE OCEAN STATE
            |
            v
    MULTI-SOURCE DATA HARMONIZATION
            |
            v
    SURFACE OCEAN EMBEDDING
            |
            v
    DEEP LEARNING RECONSTRUCTION
            |
            v
    SUBSURFACE TEMPERATURE PROFILE
            |
            v
    DAILY 3D TEMPERATURE PRODUCT

The system must reconstruct temperature at:

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
    1000 meters

The official problem specifies:

    Spatial resolution: 0.25° x 0.25°
    Temporal resolution: Daily
    Geographic domain:
        5°N to 30°N
        45°E to 105°E

The official problem explicitly expects a Proof-of-Concept over:

    Bay of Bengal
    and/or
    Arabian Sea

The practical 36-hour implementation should therefore NOT attempt a full production-grade North Indian Ocean system.

---

# 2. CORE BUSINESS / SCIENTIFIC PROBLEM

## Existing problem

Subsurface ocean temperature is essential for:

- ocean circulation understanding
- upper-ocean heat content
- stratification
- climate variability
- air-sea interaction
- marine ecosystems
- marine heatwave monitoring
- fisheries
- data assimilation
- oceanographic analysis

Direct subsurface observations are sparse.

ARGO floats, moorings, gliders, ships and other in-situ systems provide vertical information, but they do not provide a continuously dense basin-scale field.

Satellite observations provide broad and frequent surface coverage.

The scientific challenge is:

    Can the hidden subsurface thermal structure be inferred from
    the information encoded in the surface ocean state?

OceanEmbed addresses this as a learned inverse problem.

---

# 3. SCIENTIFIC CORE

Surface variables contain indirect signatures of subsurface processes.

## SST

Sea Surface Temperature.

Provides information about:

- surface thermal state
- air-sea interaction
- mixing
- thermal gradients
- mesoscale structure

## SSS

Sea Surface Salinity.

Provides information about:

- density
- stratification
- freshwater influence
- upper-ocean structure

Temperature + salinity jointly affect seawater density.

## SSH / SLA

Sea Surface Height / Sea Level Anomaly.

Provides information related to:

- dynamic height
- pressure structure
- mesoscale eddies
- thermocline displacement
- large-scale ocean circulation

## Surface current U/V

Provides information about:

- horizontal transport
- mesoscale circulation
- advection
- eddy structure

## Surface wind U/V

Provides information about:

- wind stress
- Ekman transport
- upwelling
- downwelling
- vertical mixing
- air-sea coupling

## Critical scientific interpretation

The relationship between surface state and subsurface temperature is:

- nonlinear
- spatially variable
- temporally variable
- depth dependent
- physically constrained
- partially ill-posed

Therefore:

    "surface variables -> subsurface temperature"

is not a trivial interpolation problem.

The model must learn latent ocean dynamics.

---

# 4. SYSTEM BOUNDARIES

## IN SCOPE

### Data ingestion

- Copernicus Marine
- satellite-derived / gridded surface ocean products
- historical data
- near-real-time/current data where available

### Data harmonization

- temporal alignment
- spatial regridding
- unit normalization
- coordinate normalization
- missing-data handling
- quality control
- land/sea masking
- channel construction

### Machine learning

- surface encoder
- latent OceanEmbed representation
- depth-conditioned reconstruction
- temperature prediction
- uncertainty estimation as a differentiating capability

### Validation

- GLORYS as training/reference target
- ARGO as independent validation
- RMSE
- correlation
- bias
- depth-wise skill

### Application

- Bay of Bengal
- Arabian Sea
- map-based exploration
- depth selection
- grid-cell selection
- vertical temperature profile
- uncertainty display
- optional ARGO comparison

---

# 5. OUT OF SCOPE FOR THE 36-HOUR MVP

Do NOT attempt:

- hardware
- physical ocean sensor deployment
- building satellites
- raw satellite image processing from orbital imagery
- global ocean production
- entire 45–105°E / 5–30°N production training if data volume becomes excessive
- cyclone prediction
- tsunami prediction
- generic weather forecasting
- replacing INCOIS operational ocean models
- replacing GODAS
- full numerical ocean modelling
- real-time physical ocean forecasting
- chatbot as the main product
- unnecessary LLM features
- mobile app unless required later
- multi-cloud production infrastructure
- complicated Kubernetes infrastructure
- microservices for the hackathon MVP

---

# 6. CRITICAL PRODUCT POSITIONING

OceanEmbed should NOT be presented as:

    "We replace GODAS."

Instead:

    "OceanEmbed provides a complementary surface-observation-driven
     learned reconstruction pathway for dense subsurface temperature
     intelligence."

Existing operational systems can use:

    satellite observations
    +
    in-situ observations
    +
    physical ocean models
    +
    data assimilation

OceanEmbed demonstrates:

    surface observations
    +
    learned representation
    +
    deep learning
    =
    subsurface temperature reconstruction

This distinction is essential for technical credibility.

---

# 7. USER WORKFLOW

The user should NOT need to upload:

- satellite images
- ARGO files
- NetCDF files
- ocean model files

The system handles data ingestion internally.

---

# 8. PRIMARY USER MODE

## Region-first workflow

1. User opens OceanEmbed.
2. User selects:
   - Bay of Bengal
   - Arabian Sea
3. User selects date.
4. System retrieves or loads processed daily data.
5. System displays a map.
6. User selects a depth.
7. Map displays predicted temperature at that depth.
8. User clicks a 0.25° grid cell.
9. System displays the vertical temperature profile for that grid cell.

Example:

    Region:
        Bay of Bengal

    Date:
        YYYY-MM-DD

    Selected grid cell:
        15.25°N, 87.50°E

    Depth:
        100 m

    Result:
        predicted temperature

---

# 9. GRID-CELL DRILL-DOWN WORKFLOW

When a user clicks a grid cell:

Display:

    Coordinates
    Date
    Predicted temperature profile
    15 standard depths
    Surface input values
    Uncertainty
    Optional independent ARGO observation if available

Example conceptual output:

    Depth       Temperature       Uncertainty
    -------------------------------------------
    0 m         xx.x °C           ±x.x
    5 m         xx.x °C           ±x.x
    10 m        xx.x °C           ±x.x
    ...
    1000 m      xx.x °C           ±x.x

The profile is one of the strongest demo components because it directly demonstrates the core scientific problem.

---

# 10. MAP WORKFLOW

Default map:

    Selected region
        +
    selected date
        +
    selected depth

The user can change the depth using a slider/dropdown.

The map then displays:

    predicted subsurface temperature at selected depth

The map should not attempt to render a complicated 3D ocean model unless time permits.

---

# 11. REGION DEFINITIONS

These are application-level working bounding boxes.

## Bay of Bengal

    minimum longitude = 80°E
    maximum longitude = 100°E
    minimum latitude  = 5°N
    maximum latitude  = 22°N

## Arabian Sea

    minimum longitude = 45°E
    maximum longitude = 75°E
    minimum latitude  = 5°N
    maximum latitude  = 25°N

These are NOT separate APIs.

Both use the same Copernicus Marine access mechanism.

The backend maps:

    region="bay_of_bengal"

or:

    region="arabian_sea"

to the corresponding geographic bounds.

---

# 12. OFFICIAL PROBLEM DOMAIN

North Indian Ocean:

    Longitude:
        45°E to 105°E

    Latitude:
        5°N to 30°N

Required standardized grid:

    0.25° x 0.25°

Required temporal resolution:

    daily

MVP regions:

    Bay of Bengal
    Arabian Sea

---

# 13. REQUIRED INPUT VARIABLES

The official problem statement requires:

1. SST
2. SSS
3. SSH / SLA
4. Surface ocean currents U/V
5. Surface winds U/V

Therefore the model has:

    7 logical surface channels

assuming:

    SST       = 1
    SSS       = 1
    SSH/SLA   = 1
    current U = 1
    current V = 1
    wind U    = 1
    wind V    = 1

Total:

    INPUT_CHANNELS = 7

---

# 14. INPUT MATRIX

The conceptual ML tensor is:

    X[time, channel, latitude, longitude]

For one day:

    X_day = [7, H, W]

For a batch:

    X = [B, 7, H, W]

where:

    B = batch size
    H = number of latitude grid cells
    W = number of longitude grid cells

The exact H/W depends on the selected region.

---

# 15. TARGET MATRIX

The target contains 15 depth levels.

    Y[time, depth, latitude, longitude]

For one day:

    Y_day = [15, H, W]

For a batch:

    Y = [B, 15, H, W]

Depth channels:

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
    1000

Therefore:

    OUTPUT_CHANNELS = 15

---

# 16. IMPORTANT ML ARCHITECTURE STATUS

There is NO officially mandated neural network architecture.

The problem statement explicitly allows architectures such as:

- CNN
- Vision Transformer
- Autoencoder
- GNN
- attention-based hybrid architecture

Therefore the exact neural architecture is an engineering decision.

The project discussion established the following preferred conceptual architecture:

    7-channel surface state
            |
            v
    Surface Encoder
            |
            v
    Ocean Embedding / Latent Representation
            |
            v
    Depth-conditioned Decoder
            |
            v
    15 depth temperatures

A future uncertainty head is recommended.

Do NOT falsely document a specific layer count as an already-established project requirement.

---

# 17. RECOMMENDED MVP NEURAL NETWORK

The safest 36-hour architecture is a CNN-based encoder-decoder.

Recommended conceptual implementation:

    Input
      [B, 7, H, W]

      ↓

    Conv2D(7 -> 32, kernel=3, padding=1)
      BatchNorm
      ReLU

      ↓

    Conv2D(32 -> 64, kernel=3, padding=1)
      BatchNorm
      ReLU

      ↓

    Conv2D(64 -> 128, kernel=3, padding=1)
      BatchNorm
      ReLU

      ↓

    Conv2D(128 -> 128, kernel=3, padding=1)
      ReLU

      ↓

    Ocean Embedding
      [B, 128, H, W]

      ↓

    Decoder

      Conv2D(128 -> 128)
      ReLU

      Conv2D(128 -> 64)
      ReLU

      Conv2D(64 -> 32)
      ReLU

      Conv2D(32 -> 15)

      ↓

    Temperature output
      [B, 15, H, W]

This is a RECOMMENDED BASELINE, not an official requirement.

---

# 18. RECOMMENDED U-NET-LIKE VARIANT

If spatial context is important and implementation time permits:

    Encoder
        7 -> 32 -> 64 -> 128

    Bottleneck
        128

    Decoder
        128 -> 64 -> 32 -> 15

Skip connections may be used.

Advantages:

- preserves spatial detail
- simple to train
- easy to explain to judges
- faster to implement than a full ViT
- suitable for dense grid prediction

---

# 19. OPTIONAL ADVANCED ARCHITECTURE

After the CNN baseline works:

    Surface Encoder
        ↓
    Latent Ocean Embedding
        ↓
    Attention / Transformer block
        ↓
    Depth-conditioned decoder
        ↓
    Temperature + uncertainty

This should only be implemented if the baseline pipeline is already functional.

Do NOT spend the first half of the hackathon implementing a Transformer before proving data ingestion and training.

---

# 20. DEPTH-CONDITIONED DECODER

A stronger research-oriented design is:

    surface embedding
          +
    depth embedding
          ↓
    depth-specific decoder
          ↓
    temperature at requested depth

This can allow one model to explicitly condition predictions on depth.

However, for the MVP, directly producing all 15 depth channels is simpler and should be preferred unless the team has enough time.

---

# 21. UNCERTAINTY

Uncertainty is NOT explicitly mandated by the problem statement.

It is a recommended differentiator.

Possible implementation:

    shared decoder
        |
        +---- temperature head
        |
        +---- uncertainty / log-variance head

Outputs:

    temperature
    predicted variance

This supports:

    "prediction + confidence"

rather than presenting the model as perfectly certain.

The uncertainty output should be calibrated and validated before being described as statistically rigorous.

---

# 22. LOSS FUNCTIONS

The official problem requires standard skill metrics but does not prescribe a training loss.

Recommended primary loss:

    Masked Mean Squared Error

    L_MSE =
        mean(
            mask * (prediction - target)^2
        )

Why:

- temperature is continuous
- MSE strongly penalizes large errors
- straightforward
- stable
- easy to explain

Recommended alternative:

    Huber Loss

Useful if GLORYS/observations contain outliers or artifacts.

---

# 23. DEPTH-WEIGHTED LOSS

A research-oriented option:

    L_total =
        Σ_d w_d * L_d

where:

    d = depth

Possible reasoning:

- shallower layers may have stronger surface signal
- deeper layers are harder
- evaluation should expose depth degradation

Do NOT invent arbitrary weights without validation.

Start with equal depth weighting.

Then experiment.

---

# 24. OPTIONAL PHYSICS-AWARE LOSS

A potential innovation:

    L_total =
        L_temperature
        +
        λ1 * L_vertical_smoothness
        +
        λ2 * L_physical_constraint

Potential vertical smoothness term:

    |T(d+1) - T(d)|

The purpose is to discourage physically implausible oscillations in vertical profiles.

However:

- do not over-constrain real thermocline structure
- do not impose simplistic monotonic temperature assumptions
- ocean temperature can change non-monotonically with depth

This is an experimental feature, not an MVP requirement.

---

# 25. UNCERTAINTY LOSS

If a Gaussian heteroscedastic head is implemented:

    predicted:
        μ
        log(σ²)

Use Gaussian negative log-likelihood:

    L_NLL =
        0.5 * [
            log(σ²)
            +
            (y - μ)² / σ²
        ]

Only implement this after deterministic prediction works.

---

# 26. FINAL RECOMMENDED LOSS FOR MVP

Start:

    L = MaskedMSE

Then compare:

    MaskedMSE
    vs
    Huber

Advanced:

    depth-weighted loss
    +
    uncertainty NLL
    +
    optional physically motivated regularization

---

# 27. REQUIRED EVALUATION METRICS

The official problem explicitly mentions:

- correlation
- RMSE
- bias

Therefore all three must be implemented.

## RMSE

    RMSE = sqrt(mean((prediction-target)^2))

## Bias

    Bias = mean(prediction-target)

## Correlation

Use Pearson correlation unless another correlation measure is explicitly justified.

---

# 28. DEPTH-WISE METRICS

Metrics must be computed separately for each depth.

Example:

    0 m
    5 m
    10 m
    ...
    1000 m

Produce a table:

    depth | RMSE | Bias | Correlation

This is much more informative than a single global metric.

---

# 29. SPATIAL METRICS

Where practical, calculate:

- regional RMSE
- regional bias
- correlation
- spatial error map

This helps show where the model performs well/poorly.

---

# 30. MODEL COMPARISON

At minimum compare:

### Baseline 1

Climatological / mean-depth profile baseline.

### Baseline 2

Simple CNN.

### Candidate model

OceanEmbed encoder-decoder.

This prevents the project from claiming improvement without a baseline.

---

# 31. TRAINING TARGET

The recommended target source is:

    GLORYS Global Ocean Reanalysis

Use GLORYS temperature as the primary dense training target.

The official problem statement recommends GLORYS.

Do NOT feed subsurface GLORYS temperature into the model as an input.

It is the training/reference target.

Conceptually:

    Surface observations
        ↓
        MODEL
        ↓
    predicted subsurface T

while:

    GLORYS subsurface T
        ↓
    training target

---

# 32. ARGO ROLE

ARGO is primarily for independent validation.

Do NOT treat ARGO as a required frontend input.

ARGO is sparse by design and should be used to test whether the model generalizes beyond the gridded reanalysis target.

Validation flow:

    OceanEmbed prediction
            |
            +---- compare against ARGO profile
            |
            +---- depth interpolation if needed
            |
            +---- RMSE / bias / correlation

This is more credible than validating only against GLORYS.

---

# 33. DATA LEAKAGE POLICY

This is critical.

Do NOT randomly split daily ocean grids into train/validation/test.

Random splitting can cause temporal leakage.

Recommended:

    TRAIN:
        earlier time period

    VALIDATION:
        later time period

    TEST:
        latest held-out period

Example conceptual split:

    2020-2022 -> training
    2023      -> validation
    2024      -> test

Exact years must be selected only after current dataset coverage is verified.

Do NOT hard-code these years as final requirements.

---

# 34. SPATIAL GENERALIZATION TEST

If sufficient data exists, perform an optional regional holdout.

Example:

    train:
        most of Bay of Bengal

    test:
        withheld spatial region

This tests spatial generalization.

For the 36-hour MVP, temporal holdout is more important.

---

# 35. DATA AUGMENTATION

Ocean data must NOT be augmented like ordinary photographs.

DO NOT use:

- arbitrary horizontal flips
- vertical flips
- random rotations
- arbitrary image color augmentation
- arbitrary geometric transformations

These can violate geographic and physical meaning.

Possible safe augmentations:

- small input noise
- random spatial crops within the same valid region
- masking/dropout of selected surface channels
- controlled missing-data simulation

But every augmentation must preserve physical plausibility.

Recommended MVP:

    NO aggressive augmentation.

Start with:

    original harmonized daily data

Optionally use:

    controlled missing-value/channel masking

to improve robustness.

---

# 36. MISSING DATA POLICY

Ocean datasets may contain:

- land
- clouds
- retrieval gaps
- quality-control failures
- missing observations
- invalid values

Do NOT blindly replace all missing values with zero.

Use:

    land/sea mask
    valid-data mask

Potential tensor design:

    input channels
    +
    validity mask

If adding masks, document the expanded channel count.

For the strict official input specification, the logical ocean variables remain the seven required surface variables.

---

# 37. LAND/SEA MASK

Apply a common ocean mask after regridding.

The mask should ensure:

- land is excluded
- coastal invalid cells are handled consistently
- loss is calculated only over valid ocean cells

---

# 38. NORMALIZATION

Each input channel should be normalized separately.

Preferred:

    z-score normalization

    x_norm = (x - mean) / std

Compute normalization statistics from TRAINING DATA ONLY.

Never calculate normalization statistics using the full dataset before splitting.

This prevents subtle leakage.

Save:

    mean
    std

as model artifacts.

---

# 39. TARGET NORMALIZATION

Temperature target may also be normalized.

If normalized:

    T_norm = (T - μ_T) / σ_T

Store target normalization parameters.

During inference:

    predicted_temperature =
        predicted_normalized_temperature * σ_T
        + μ_T

Do not forget inverse transformation before displaying °C.

---

# 40. REGRIDDING

The official problem requires:

    0.25° x 0.25°

Source products may have different resolutions.

Therefore:

    raw source
        ↓
    spatial harmonization
        ↓
    0.25° grid

Possible interpolation methods:

- bilinear for continuous gridded variables
- nearest-neighbor for categorical masks
- physically appropriate method for each product

Document the method per variable.

Do not assume all products use the same source grid.

---

# 41. TEMPORAL HARMONIZATION

Official target frequency:

    daily

All input variables must be aligned to a common daily time convention.

Potential issue:

different products can use:

- UTC timestamps
- center-of-interval timestamps
- start-of-day timestamps
- different latency

Copernicus documentation currently notes that Toolbox `subset` uses Analysis-Ready Cloud Optimized data conventions with timestamps aligned to the start of the interval, while original files retrieved using `get` may use producer timestamps such as center-of-interval timestamps.

Therefore the preprocessing pipeline must explicitly normalize timestamps.

Never merge datasets based solely on filename date.

---

# 42. UNIT HARMONIZATION

Every channel must have explicit units.

Store metadata:

    variable
    unit
    source
    source dataset ID
    preprocessing
    normalization

Examples:

    SST -> °C or K, but choose one internal convention
    SSS -> PSU / practical salinity convention of source
    SSH -> meters
    currents -> m/s
    wind -> m/s
    temperature target -> °C or K

Use one internal convention consistently.

---

# 43. SOURCE DATA FORMAT

Preferred intermediate format:

    NetCDF

For larger ML pipelines:

    Zarr

can be considered.

Initial implementation:

    NetCDF
    +
    xarray
    +
    NumPy

Do not prematurely introduce a complicated storage system.

---

# 44. COPERNICUS MARINE DATA ACCESS

Primary data provider:

    Copernicus Marine

Current official Toolbox capabilities include:

- login
- describe
- subset
- get
- remote dataset/dataframe access

The Python library is:

    copernicusmarine

Install:

    python -m pip install copernicusmarine

Authenticate:

    copernicusmarine login

Copernicus states that the Toolbox has no fixed volume or bandwidth quota.

However, actual retrieval speed remains dependent on:

- network
- server response
- request size
- number of variables
- local disk
- local processing

Do NOT promise a fixed "X seconds" retrieval time.

---

# 45. COPERNICUS AUTHENTICATION

Login is required for authenticated Toolbox access.

The login command creates a configuration file so credentials do not need to be manually supplied on every request.

For production/headless systems, environment variables are supported:

    COPERNICUSMARINE_SERVICE_USERNAME
    COPERNICUSMARINE_SERVICE_PASSWORD

Credentials MUST:

- remain server-side
- never enter frontend JavaScript
- never be committed to Git
- never be placed in public configuration
- never be exposed through API responses

---

# 46. COPERNICUS API TERMINOLOGY

IMPORTANT:

The Copernicus Marine Toolbox Python interface is NOT a conventional REST API.

Use:

    Python package:
        copernicusmarine

The architecture is:

    Frontend
        ↓
    FastAPI backend
        ↓
    copernicusmarine Python library
        ↓
    Copernicus Marine

Do NOT design the frontend around direct Copernicus authentication.

---

# 47. DATASET DISCOVERY RULE

Never blindly hard-code old dataset IDs.

Use:

    copernicusmarine.describe()

Example:

    import copernicusmarine

    results = copernicusmarine.describe(
        contains=["thetao"]
    )

Use catalogue metadata to verify:

- product ID
- dataset ID
- variable names
- units
- spatial coverage
- temporal coverage
- resolution
- depth
- data availability
- subset support
- latency
- dataset version

Dataset IDs are implementation details and can change.

---

# 48. COPERNICUS SUBSET

Use `subset()` for targeted extraction.

Conceptual:

    copernicusmarine.subset(
        dataset_id="VERIFIED_DATASET_ID",
        variables=["VERIFIED_VARIABLE"],
        minimum_longitude=80,
        maximum_longitude=100,
        minimum_latitude=5,
        maximum_latitude=22,
        start_datetime="YYYY-MM-DD",
        end_datetime="YYYY-MM-DD",
        output_filename="bay_of_bengal.nc"
    )

The exact current signature and dataset-specific capabilities must be verified using the current Toolbox documentation.

---

# 49. HISTORICAL VS DAILY INGESTION

The same Copernicus Marine Toolbox mechanism can support:

## Historical training data

Example:

    multi-year data

Use chunked downloads.

## Daily / latest inference

Example:

    latest available daily data

The backend should periodically check for new available data.

Therefore:

    Copernicus access layer
        =
    historical + operational ingestion mechanism

But the underlying dataset choices may differ.

Historical reprocessed products and near-real-time products should not automatically be mixed.

---

# 50. DATA LATENCY

Do NOT claim:

    "real-time"

unless verified for the exact dataset.

Copernicus documentation states that data is generally available through the Subset service after the underlying Files service, with a typical delay of approximately 1–4 hours in the current documentation.

Dataset-specific latency must still be checked.

Preferred product wording:

    "latest available daily ocean observations"

unless true real-time availability is independently verified.

---

# 51. CANDIDATE COPERNICUS PRODUCTS DISCUSSED

These were previously identified as candidate products.

They are NOT all permanently locked.

They must be re-verified using the current catalogue before implementation.

## SST

Historical reprocessed candidate:

    SST_GLO_SST_L4_REP_OBSERVATIONS_010_024

Candidate characteristics discussed:

    daily
    ~0.05°
    historical

NRT candidate:

    SST_GLO_SST_L4_NRT_OBSERVATIONS_010_001

---

## SSS

Candidate:

    MULTIOBS_GLO_PHY_SSS_L3_MYNRT_015_014

Discussed characteristics:

    daily
    0.25°
    2010 onward / current coverage at time of verification

Must re-check current availability.

---

## SSH / SLA

Historical candidate:

    SEALEVEL_GLO_PHY_CLIMATE_L4_MY_008_057

Discussed characteristics:

    daily
    0.25°

NRT candidate:

    SEALEVEL_GLO_PHY_L4_NRT_008_046

Exact current resolution/version must be verified.

---

## SURFACE CURRENTS

Candidate:

    MULTIOBS_GLO_PHY_MYNRT_015_003

This product was identified as a combined current product.

IMPORTANT:

It is NOT necessarily "pure satellite-only current."

It combines satellite-derived geostrophic current information with modelled Ekman/current information.

This must be disclosed.

Alternative strategy:

    derive geostrophic information from SSH

if a scientifically appropriate implementation is chosen.

---

## SURFACE WINDS

Candidate:

    WIND_GLO_PHY_L3_NRT_012_002

Historical candidate:

    WIND_GLO_PHY_L3_MY_012_005

Expected variables:

    eastward wind
    northward wind

Exact variable names must be verified.

---

# 52. GLORYS

Candidate training/reference dataset:

    GLOBAL_MULTIYEAR_PHY_001_030

Previously identified dataset:

    cmems_mod_glo_phy_my_0.083deg_P1D-m

Previously discussed characteristics:

    ~0.083°
    daily
    50 vertical levels
    1993 onward
    temperature
    salinity
    currents
    SSH etc.

IMPORTANT:

The exact current dataset ID must be verified through `describe()` before production use.

---

# 53. ARGO

ARGO is the independent validation source.

Do not require the user to upload ARGO.

Backend validation can:

    locate ARGO observations
    match date
    match spatial position
    interpolate model profile
    compare depth-by-depth

The official problem statement explicitly recommends independent ARGO validation.

---

# 54. DATA SOURCE RULE

Do NOT call all inputs:

    "satellite images"

Many inputs are gridded geophysical products.

Preferred terminology:

    "multi-source surface ocean observations/products"

This is more scientifically accurate.

---

# 55. TRAINING DATA TENSOR PIPELINE

Raw:

    Copernicus products
        +
    other approved observations

↓

Crop:

    selected region

↓

Quality control

↓

Temporal alignment

↓

Spatial regridding

↓

Land/sea masking

↓

Missing-data mask

↓

Unit conversion

↓

Normalization

↓

Tensor construction

↓

Training sample:

    X = [7, H, W]

Target:

    Y = [15, H, W]

---

# 56. HISTORICAL DATA DOWNLOAD POLICY

DO NOT download:

    entire global ocean
    entire multi-decade archive

before proving the pipeline.

Start:

    one region
    1–7 days
    one variable

Then:

    one region
    1–7 days
    all variables

Then:

    training period
    chunked downloads

---

# 57. CHUNKING

Historical requests should be split by manageable units:

- variable
- day
- month
- year

depending on data size.

Copernicus currently supports `subset_split_on`, including splitting by:

- variable
- hour
- day
- month
- year

This should be used where helpful.

---

# 58. RECOMMENDED STORAGE LAYOUT

Conceptual:

    ocean-data/
    ├── bay_of_bengal/
    │   ├── 2020/
    │   │   ├── 01/
    │   │   │   ├── sst.nc
    │   │   │   ├── sss.nc
    │   │   │   ├── ssh.nc
    │   │   │   ├── current_u.nc
    │   │   │   ├── current_v.nc
    │   │   │   ├── wind_u.nc
    │   │   │   └── wind_v.nc
    │   │   └── ...
    │   └── ...
    │
    └── arabian_sea/
        ├── 2020/
        └── ...

The exact storage structure can be optimized after data volume is known.

---

# 59. DAILY INGESTION PIPELINE

Production-like workflow:

    scheduler
        ↓
    check latest available date
        ↓
    identify missing inputs
        ↓
    fetch required regional products
        ↓
    cache raw data
        ↓
    QC
        ↓
    harmonization
        ↓
    model inference
        ↓
    prediction validation checks
        ↓
    save prediction
        ↓
    update dashboard

---

# 60. CACHE POLICY

Do not repeatedly request the same data.

Before requesting Copernicus:

    check local/object cache

If:

    region + variable + date + dataset_version

already exists:

    use cached copy

Otherwise:

    request from Copernicus

This reduces latency and API dependency.

---

# 61. BACKEND ARCHITECTURE

Recommended:

    FastAPI

Architecture:

    Frontend
        |
        | HTTPS / JSON
        v
    FastAPI
        |
        +-- validation
        +-- region mapping
        +-- authentication
        +-- caching
        +-- Copernicus service
        +-- preprocessing
        +-- ML inference
        +-- prediction store
        |
        v
    OceanEmbed model

---

# 62. FRONTEND/BACKEND BOUNDARY

Frontend should know:

    region
    date
    depth
    grid cell

Frontend should NOT know:

    Copernicus username
    Copernicus password
    dataset credentials
    internal dataset IDs
    raw ingestion credentials

Backend controls:

    geographic constraints
    allowed dates
    dataset selection
    caching
    model version

---

# 63. APPLICATION API

Conceptual endpoint:

    GET /api/ocean/history

Parameters:

    region
    start_date
    end_date

Example:

    /api/ocean/history?region=bay_of_bengal&start_date=2020-01-01&end_date=2020-01-07

Other conceptual endpoints:

    GET /api/ocean/map

    GET /api/ocean/profile

    GET /api/ocean/metadata

    GET /api/ocean/health

    GET /api/model/version

Exact endpoint names are not locked.

---

# 64. RECOMMENDED API RESPONSE FOR PROFILE

Conceptual:

    {
      "region": "bay_of_bengal",
      "date": "YYYY-MM-DD",
      "latitude": 15.25,
      "longitude": 87.50,
      "profile": [
        {
          "depth_m": 0,
          "temperature_c":  ...
        },
        ...
      ],
      "uncertainty": [
        ...
      ],
      "model_version": "..."
    }

Do not expose internal credentials or raw provider secrets.

---

# 65. DATABASE / PREDICTION STORAGE

A simple MVP can use:

    PostgreSQL

or:

    SQLite

depending on deployment.

For spatial products, object storage/files may be preferable to putting every raster cell into relational rows.

Recommended conceptual separation:

    metadata DB
        +
    NetCDF/Zarr/object storage
        +
    prediction API

Do not over-engineer this during the 36-hour event.

---

# 66. FRONTEND TECHNOLOGY

No frontend framework was formally locked during the conversation.

Recommended enterprise/MVP stack:

    TypeScript
    React
    Vite

Optional:

    Next.js

But do NOT introduce Next.js unless SSR/routing requirements justify it.

For a hackathon dashboard, React + Vite is simpler.

---

# 67. MAP VISUALIZATION

Preferred:

    MapLibre GL JS

or:

    Leaflet

If advanced WebGL rendering is needed:

    deck.gl

The MVP only needs:

- map
- grid visualization
- depth selector
- click-to-profile
- legend

Do not build a complex 3D globe unless it directly improves the demo.

---

# 68. CHARTING

Use a lightweight chart library or custom SVG/canvas.

Required chart:

    depth vs temperature

Optional:

    depth vs uncertainty
    prediction vs ARGO
    error profile

---

# 69. BACKEND LANGUAGE

Preferred:

    Python 3.x

Reason:

- Copernicus Python Toolbox
- xarray
- NumPy
- PyTorch
- scientific ecosystem
- FastAPI

Keep one primary language across backend and ML.

---

# 70. ML FRAMEWORK

Recommended:

    PyTorch

Supporting libraries:

    NumPy
    xarray
    pandas
    scipy
    scikit-learn
    NetCDF4 / h5netcdf as required
    Zarr as required

Do not install unnecessary libraries.

---

# 71. PYTHON DATA STACK

Recommended:

    xarray
    numpy
    pandas
    scipy

Why xarray:

- labeled dimensions
- latitude/longitude/depth/time
- NetCDF support
- oceanographic workflows
- easier alignment than raw NumPy

---

# 72. BACKEND DEPENDENCIES

Recommended:

    fastapi
    uvicorn
    pydantic
    copernicusmarine
    xarray
    numpy
    scipy
    torch

Optional:

    sqlalchemy
    psycopg
    redis

Only add Redis/PostgreSQL if actual caching/database requirements justify them.

---

# 73. FRONTEND DEPENDENCIES

Recommended:

    react
    typescript
    vite

Map:

    maplibre-gl

Chart:

    recharts

or another lightweight chart library.

State:

    React state first

Do not add Redux unless application complexity requires it.

---

# 74. DEPENDENCY CONSTRAINT

Pin or lock dependency versions for reproducibility after the first successful environment.

Use:

    requirements.txt

and/or:

    pyproject.toml

For frontend:

    package-lock.json
    or pnpm-lock.yaml
    or yarn.lock

Do not allow "latest" production dependencies without lock files.

---

# 75. REPOSITORY STRUCTURE

Recommended:

    oceanembed/
    │
    ├── README.md
    ├── SYSTEM_MEMORY_DUMP.md
    ├── .env.example
    ├── .gitignore
    │
    ├── backend/
    │   ├── app/
    │   │   ├── main.py
    │   │   ├── api/
    │   │   ├── services/
    │   │   ├── models/
    │   │   ├── schemas/
    │   │   └── config/
    │   └── tests/
    │
    ├── ml/
    │   ├── models/
    │   ├── datasets/
    │   ├── training/
    │   ├── evaluation/
    │   ├── preprocessing/
    │   └── inference/
    │
    ├── data/
    │   ├── raw/
    │   ├── processed/
    │   └── manifests/
    │
    ├── frontend/
    │   ├── src/
    │   └── public/
    │
    ├── scripts/
    │   ├── discover_datasets.py
    │   ├── test_copernicus.py
    │   ├── download_region.py
    │   └── preprocess.py
    │
    └── docs/

Exact structure can evolve.

---

# 76. CONFIGURATION

Do not hard-code:

- credentials
- model paths
- dataset versions
- storage locations
- production URLs

Use:

    .env

and configuration classes.

Example:

    COPERNICUSMARINE_SERVICE_USERNAME
    COPERNICUSMARINE_SERVICE_PASSWORD
    MODEL_PATH
    DATA_ROOT
    DATABASE_URL

---

# 77. SECURITY

Never commit:

    .env

Never expose:

    Copernicus credentials

Never put secrets in:

    frontend code
    Docker image layers
    Git history
    logs
    API responses

Use:

    .env.example

with placeholders.

---

# 78. DATA PROVENANCE

Every processed dataset should preserve metadata:

    source_provider
    product_id
    dataset_id
    dataset_version
    variable
    source_resolution
    target_resolution
    source_time
    target_time
    interpolation_method
    unit_conversion
    normalization_version
    preprocessing_version

This is important for scientific reproducibility and judge credibility.

---

# 79. MODEL VERSIONING

Every prediction should be traceable to:

    model_version

and ideally:

    training_dataset_version
    preprocessing_version
    normalization_version

Example:

    model_version = oceanembed-cnn-v1

---

# 80. DATASET MANIFEST

Maintain a machine-readable manifest:

    data/manifests/datasets.json

Each entry should contain:

    product_id
    dataset_id
    variable
    source
    resolution
    temporal_frequency
    coverage_start
    coverage_end
    latency
    units
    notes
    verified_at

This prevents undocumented dataset changes.

---

# 81. DATASET VERIFICATION MATRIX

Before full training, produce a table containing:

    variable
    dataset_id
    variable_name
    source
    spatial_resolution
    temporal_resolution
    coverage
    units
    latency
    subset_supported
    notes

Required rows:

    SST
    SSS
    SSH/SLA
    current U
    current V
    wind U
    wind V
    GLORYS temperature
    ARGO validation

This is a hard engineering gate.

---

# 82. CURRENT U/V CAUTION

The surface current requirement deserves special attention.

The candidate Copernicus current product discussed previously is a multi-source product and may contain model-derived Ekman components.

Therefore do NOT tell judges:

    "All seven channels are pure satellite observations."

Safer:

    "We harmonize multi-source surface ocean observations/products
     specified by the problem statement."

If a pure satellite-current implementation is required, derive/construct the current component through an explicitly documented methodology.

---

# 83. HISTORICAL DATA POLICY

Historical training should prefer stable/reprocessed products.

Do not casually mix:

    historical reprocessed SST

with:

    current NRT SSS

with:

    unrelated historical current generation

unless overlap and consistency have been verified.

The training period must use a coherent set of products.

---

# 84. NRT DATA POLICY

For live demo:

    use latest available data

For training:

    use stable historical/reprocessed products

This separation avoids dataset-generation mismatch.

---

# 85. MODEL TRAINING PIPELINE

Conceptual:

    raw source data
        ↓
    dataset harmonization
        ↓
    daily 0.25° tensors
        ↓
    train/val/test temporal split
        ↓
    normalization
        ↓
    PyTorch Dataset
        ↓
    DataLoader
        ↓
    CNN encoder-decoder
        ↓
    loss
        ↓
    validation
        ↓
    checkpoint
        ↓
    test
        ↓
    evaluation report
        ↓
    inference artifact

---

# 86. TRAINING SAMPLE

One sample:

    date = one day

Input:

    [7, H, W]

Target:

    [15, H, W]

Batch:

    [B, 7, H, W]

Target batch:

    [B, 15, H, W]

---

# 87. TRAINING LOOP

Recommended:

    optimizer = Adam

Learning rate:

    must be tuned experimentally

Do NOT document a specific learning rate as a locked project requirement unless actually tested.

Potential starting point:

    1e-3

but this is a tunable engineering choice.

Potential scheduler:

    ReduceLROnPlateau
    or cosine decay

Again:

    optional.

---

# 88. EARLY STOPPING

Recommended:

    monitor validation loss

Stop if:

    no meaningful validation improvement
    for configured patience

Save:

    best validation checkpoint

Do not choose final model based on test set.

---

# 89. TEST SET POLICY

The test set must remain untouched during:

- hyperparameter selection
- architecture selection
- model tuning

Only use test data for final evaluation.

---

# 90. CROSS-REGION GENERALIZATION

Potential experiment:

    train on Bay of Bengal
    test on Arabian Sea

or:

    train on combined regions
    hold out a spatial region

This could become a strong research result.

However, it is not required for the first MVP.

---

# 91. BASELINE MODELS

Required for scientific credibility.

## Baseline A

Climatology.

Predict:

    average temperature profile

## Baseline B

Simple CNN.

## Model C

OceanEmbed proposed architecture.

Compare:

    RMSE
    Bias
    Correlation

by depth.

---

# 92. EXPECTED DEPTH BEHAVIOR

Do not assume equal performance at all depths.

Likely:

    stronger skill near surface
    decreasing skill with depth

This is scientifically plausible because the surface observations contain progressively weaker indirect information about deeper structure.

The actual results must be measured, not assumed.

---

# 93. MODEL FAILURE MODES

The system must explicitly consider:

- missing surface observations
- cloudy SST
- salinity gaps
- coastal contamination
- land masking
- extreme ocean events
- unusual circulation regimes
- distribution shift
- deep-depth uncertainty
- regional bias
- source-product inconsistency

---

# 94. UNCERTAINTY DISPLAY

If uncertainty is implemented, display:

    temperature
    +
    confidence/uncertainty

Do not display an arbitrary "confidence percentage" unless it is statistically calibrated.

Prefer:

    predicted uncertainty
    or
    uncertainty interval

---

# 95. SCIENTIFIC VALIDATION VIEW

A strong demo should include:

    predicted profile
    vs
    GLORYS profile

and, where available:

    predicted profile
    vs
    ARGO profile

The ARGO comparison is especially useful because it is an independent observation.

---

# 96. JUDGE DEMONSTRATION

The ideal demo sequence:

    1. Open OceanEmbed
    2. Select Bay of Bengal
    3. Select date
    4. Display surface/data status
    5. Select depth = 100 m
    6. Display predicted temperature map
    7. Click grid cell
    8. Show full 15-depth profile
    9. Show uncertainty
    10. Show ARGO validation where available
    11. Show RMSE/correlation summary
    12. Explain how surface observations become an embedding
    13. Explain why the result matters operationally

This is more powerful than a generic dashboard.

---

# 97. DISASTER / OPERATIONAL POSITIONING

OceanEmbed itself is NOT a cyclone predictor.

It should not claim:

    "predicts cyclones"

unless a separate cyclone model is actually built and validated.

Potential downstream relevance:

- marine heatwave intelligence
- upper-ocean thermal structure
- ocean heat content analysis
- cyclone-ocean interaction research
- fisheries/environmental analysis
- operational ocean-state understanding

The product should be positioned as a subsurface ocean intelligence layer.

---

# 98. INCOIS CONTEXT

INCOIS operational ocean workflows involve:

- satellite observation acquisition
- satellite processing
- quality control
- data assimilation
- numerical ocean modelling
- ocean analysis
- forecasting/nowcasting
- data dissemination

OceanEmbed should therefore be presented as a complementary AI reconstruction layer.

It is not a replacement for operational numerical ocean modelling.

---

# 99. GODAS CONTEXT

INCOIS-GODAS is an ocean analysis/reanalysis system involving physical ocean modelling and assimilation of observations.

OceanEmbed should not attempt to duplicate all of GODAS.

Difference:

    GODAS:
        physical ocean model
        +
        data assimilation
        +
        multiple observations

    OceanEmbed:
        surface state
        +
        learned latent representation
        +
        deep learning
        →
        subsurface temperature

This distinction is a major presentation point.

---

# 100. INNOVATION STRATEGY

The research landscape already contains:

- CNN approaches
- ConvLSTM approaches
- ViT approaches
- hybrid transformer approaches
- machine learning retrieval
- super-resolution methods
- physically guided approaches
- uncertainty-aware approaches

Therefore:

    "We use AI"

is NOT an innovation.

Also:

    "We use a Transformer"

is NOT sufficient innovation.

Strong differentiators:

1. North Indian Ocean focus
2. daily 0.25° harmonization
3. multi-source surface feature fusion
4. explicit latent OceanEmbed representation
5. independent ARGO validation
6. depth-wise skill reporting
7. uncertainty
8. operational ingestion architecture
9. reproducible data provenance
10. regional cross-validation
11. scientific visualization

---

# 101. FEATURE ENGINEERING

Do not invent dozens of derived features.

Primary features are the seven official surface variables.

Potential derived features:

- spatial gradients of SST
- spatial gradients of SSH
- wind magnitude
- current magnitude
- anomalies relative to climatology

These are OPTIONAL.

For the first MVP, use the seven required channels directly.

---

# 102. CLIMATOLOGY

A climatological prior can be useful.

Possible:

    temperature climatology by depth
    +
    model residual

Instead of:

    direct temperature prediction

This is an advanced option.

For the MVP:

    direct prediction

is simpler.

---

# 103. RESIDUAL LEARNING

Optional architecture:

    climatological temperature profile
            +
    predicted residual
            =
    reconstructed temperature

This can improve stability and interpretability.

But it must be evaluated experimentally.

---

# 104. MODEL INPUT SHOULD REMAIN SURFACE-ONLY

This is a core problem requirement.

Do NOT accidentally give the model:

- GLORYS subsurface temperature
- ARGO temperature
- subsurface salinity
- subsurface currents

as inference inputs.

Those are targets/reference/validation data.

The model's inference inputs are surface observations.

---

# 105. DATA LEAKAGE CHECKLIST

Before training:

- target is not included in input
- future observations are not included in past samples
- normalization uses training data only
- validation/test dates are later than training
- ARGO validation is independent
- no test-derived hyperparameters
- no target-derived features
- no accidental GLORYS subsurface channels

---

# 106. TIME ALIGNMENT

When combining:

    SST
    SSS
    SSH
    currents
    wind

ensure they correspond to the same daily temporal unit.

If one product is delayed:

    use the actual matching available date

Do not silently shift data by one day to make arrays fit.

Every temporal transformation must be documented.

---

# 107. SPATIAL ALIGNMENT

All input channels must end with:

    same H
    same W
    same latitude grid
    same longitude grid

Target must use:

    same H
    same W

The model cannot directly consume mismatched source grids.

---

# 108. COORDINATE CONVENTION

Standardize longitude convention.

Recommended:

    0–360° or -180–180°

Pick one internally.

Do not mix conventions.

The North Indian Ocean domain should be represented consistently.

---

# 109. QUALITY CONTROL

Use source-provided quality flags where available.

Do not treat every retrieved value as equally trustworthy.

Potential preprocessing:

    source QC
    ↓
    invalid-value removal
    ↓
    land mask
    ↓
    interpolation where scientifically justified

Do not blindly interpolate large missing ocean areas.

---

# 110. REGRIDDING EDGE CASES

Watch for:

- longitude wraparound
- coastline cells
- sparse salinity observations
- missing satellite swaths
- different latitude orientation
- ascending vs descending latitude arrays
- duplicated time coordinates
- masked arrays
- NaN vs fill values
- Kelvin vs Celsius
- meters vs centimeters

These are common sources of silent model corruption.

---

# 111. FILE VALIDATION

Every downloaded file should be checked for:

- expected variables
- expected dimensions
- coordinate names
- units
- time length
- latitude range
- longitude range
- NaN percentage
- fill values
- min/max statistics

Example validation report:

    variable
    shape
    units
    min
    max
    missing_percent

---

# 112. DATA CONTRACT

Every model sample should satisfy:

    X:
        dtype = float32
        shape = [7, H, W]

    Y:
        dtype = float32
        shape = [15, H, W]

    mask:
        valid ocean cells

    metadata:
        date
        region
        latitude grid
        longitude grid

---

# 113. MODEL CONTRACT

Input:

    float32 tensor
    [B, 7, H, W]

Output:

    float32 tensor
    [B, 15, H, W]

Optional uncertainty:

    [B, 15, H, W]

The inference service must preserve:

    depth ordering

exactly:

    [0, 5, 10, 20, 30, 50, 75, 100,
     125, 150, 200, 300, 500, 700, 1000]

---

# 114. MODEL CHECKPOINT

Store:

    model weights
    architecture configuration
    normalization statistics
    depth list
    channel order
    preprocessing version
    dataset version

A checkpoint without channel ordering metadata is unsafe.

---

# 115. CHANNEL ORDER

Canonical channel order:

    0 = SST
    1 = SSS
    2 = SSH/SLA
    3 = current U
    4 = current V
    5 = wind U
    6 = wind V

Do NOT reorder channels without updating the model configuration.

---

# 116. DEPTH ORDER

Canonical depth order:

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
    1000

Do NOT reorder output channels.

---

# 117. DAILY INFERENCE

For one daily prediction:

    retrieve 7 channels
        ↓
    align
        ↓
    regrid
        ↓
    normalize
        ↓
    tensor [1,7,H,W]
        ↓
    model
        ↓
    output [1,15,H,W]
        ↓
    denormalize
        ↓
    apply ocean mask
        ↓
    save
        ↓
    expose through API

---

# 118. PERFORMANCE EXPECTATION

The goal is not:

    massive cloud-scale infrastructure

The goal is:

    reliable regional daily inference

A small regional subset should be practical to retrieve in minutes under normal conditions, but never promise a deterministic retrieval time.

Copernicus has no fixed Toolbox download quota, but actual speed depends on request and infrastructure.

---

# 119. 36-HOUR MVP PLAN

## HOUR 0–2

Infrastructure:

- repository
- Python environment
- frontend skeleton
- FastAPI skeleton
- Copernicus account
- login
- `describe()`

SUCCESS CRITERION:

    current dataset metadata successfully retrieved

---

## HOUR 2–5

Data proof:

- one variable
- Bay of Bengal
- 1 day
- open NetCDF
- inspect dimensions
- verify values

Then:

- Arabian Sea
- same test

SUCCESS CRITERION:

    reliable regional data retrieval

---

## HOUR 5–10

Multi-variable ingestion:

- SST
- SSS
- SSH/SLA
- current U
- current V
- wind U
- wind V

SUCCESS CRITERION:

    one harmonized daily tensor

    [7,H,W]

---

## HOUR 10–15

Target:

- GLORYS
- extract temperature
- map to 15 depths

SUCCESS CRITERION:

    target tensor

    [15,H,W]

---

## HOUR 15–22

Model:

- baseline
- CNN
- training
- validation

SUCCESS CRITERION:

    nontrivial predictions

---

## HOUR 22–27

Evaluation:

- RMSE
- bias
- correlation
- depth-wise charts
- prediction maps

---

## HOUR 27–32

Application:

- map
- depth slider
- grid-cell click
- vertical profile

---

## HOUR 32–36

Polish:

- ARGO comparison if available
- uncertainty if model supports it
- architecture diagram
- data-flow diagram
- metrics
- final demo
- fallback static sample

---

# 120. MVP FALLBACK STRATEGY

If live ingestion becomes unreliable:

DO NOT allow the entire demo to fail.

Prepare:

    cached verified data
    cached predictions
    cached validation profiles

The live ingestion pipeline can still be demonstrated separately.

The user-facing demo must remain functional.

---

# 121. OBSERVABILITY

Log:

    ingestion start
    ingestion end
    dataset ID
    date
    region
    bytes/files
    preprocessing time
    inference time
    model version
    errors

Do NOT log:

    passwords
    credentials

---

# 122. ERROR HANDLING

If Copernicus is unavailable:

    return cached latest data

If a variable is unavailable:

    mark channel unavailable

Do NOT silently fill everything with zeros.

If model inference fails:

    return a clear system error

Do not display fake scientific values.

---

# 123. HEALTH CHECKS

Backend:

    GET /health

Should verify:

    API process alive
    model loaded
    data cache accessible

Optional:

    Copernicus connectivity

Do not make health checks trigger expensive data downloads.

---

# 124. TESTING

Minimum tests:

### Unit

- region mapping
- coordinate conversion
- normalization
- depth ordering
- channel ordering
- mask handling

### Data tests

- file opens
- expected variables
- expected dimensions
- no unexpected coordinate reversal

### API tests

- valid region
- invalid region
- invalid date
- profile response

### ML tests

- model accepts [B,7,H,W]
- model outputs [B,15,H,W]
- no NaNs
- normalization/denormalization round trip

---

# 125. SCIENTIFIC SANITY CHECKS

Before displaying a prediction:

- temperature is finite
- no impossible NaNs
- no extreme numerical explosion
- profile is inspectable
- uncertainty is non-negative
- mask is respected

Do NOT impose arbitrary physical temperature bounds unless scientifically justified and documented.

---

# 126. DATASET COVERAGE CHECK

Before selecting training years:

verify actual overlap among:

    SST
    SSS
    SSH
    current
    wind
    GLORYS

The usable training period is the intersection:

    common_time_range(all_required_inputs, target)

Do not choose years first and discover missing variables later.

---

# 127. PRODUCT CONSISTENCY

A training sample should ideally come from:

    coherent product generations
    overlapping date ranges
    documented preprocessing

Avoid:

    arbitrary mixing of NRT and reprocessed datasets

unless the model explicitly supports domain adaptation.

---

# 128. MODEL GENERALIZATION

The model should be evaluated on:

1. unseen dates
2. ideally unseen spatial locations
3. independent ARGO profiles

A high training score alone is not evidence of a successful OceanEmbed system.

---

# 129. SCIENTIFIC CLAIM POLICY

Do not claim:

    "accurate"

without metrics.

Do not claim:

    "real-time"

without latency verification.

Do not claim:

    "satellite-only"

if a candidate current product contains model-derived components.

Do not claim:

    "operational"

unless deployed and monitored.

Use:

    "prototype"
    "PoC"
    "learned reconstruction"
    "latest available daily product"

when appropriate.

---

# 130. PRESENTATION STORY

Recommended narrative:

## Problem

Subsurface temperature is critical but sparsely observed.

## Gap

Surface satellites provide broad coverage, but subsurface structure is not directly observed.

## Insight

Surface variables contain physical signatures of subsurface dynamics.

## Solution

OceanEmbed learns a compact latent representation of the surface ocean state.

## Reconstruction

The embedding is decoded into temperature at 15 standard depths.

## Validation

Compare against GLORYS and independently against ARGO.

## Product

A daily 0.25° subsurface temperature intelligence layer for the North Indian Ocean.

## Demo

Bay of Bengal / Arabian Sea → date → depth → grid cell → vertical profile.

---

# 131. JUDGE QUESTIONS TO EXPECT

## "Why not just use GLORYS?"

Answer:

    GLORYS is a model/reanalysis product used here as a training/reference
    target. OceanEmbed demonstrates an alternative learned reconstruction
    pathway driven by surface observations.

## "Why is this useful?"

Answer:

    It aims to provide dense subsurface temperature estimates from
    broadly available surface observations where direct vertical
    observations are sparse.

## "Why ARGO?"

Answer:

    ARGO provides independent in-situ vertical observations for validation.

## "Why seven variables?"

Answer:

    They are explicitly specified by the problem statement and represent
    complementary physical signatures of the subsurface state.

## "Why 15 depths?"

Answer:

    They are the standard depths specified by the problem statement.

## "Why 0.25°?"

Answer:

    It is the required standardized spatial resolution.

## "Why deep learning?"

Answer:

    The surface-to-subsurface mapping is nonlinear and spatially/
    temporally dependent, making learned representation useful.

---

# 132. COMMON JUDGE REJECTION RISKS

1. No real data.
2. Only a UI.
3. Fake AI.
4. No validation.
5. No baseline.
6. No independent observations.
7. Claiming Transformer innovation without scientific differentiation.
8. Claiming satellite-only while using model-derived current data.
9. No explanation of preprocessing.
10. No evidence of depth-wise performance.
11. No handling of missing data.
12. No reproducibility.
13. Generic dashboard instead of scientific product.
14. Overbuilding frontend and underbuilding ML.
15. Claiming operational capability without latency/data validation.

---

# 133. MOST IMPORTANT EXECUTION PRINCIPLE

Build the smallest system capable of proving:

    REAL DATA
        ↓
    REAL PREPROCESSING
        ↓
    REAL MODEL
        ↓
    REAL SUBSURFACE OUTPUT
        ↓
    REAL VALIDATION
        ↓
    REAL USER INTERACTION

Do not optimize for feature count.

Optimize for proof.

---

# 134. HISTORICAL DECISIONS FROM THE CHAT

## Decision 1

Copernicus Marine is the primary data provider.

Reason:

- programmatic Toolbox
- regional subsetting
- historical data
- near-real-time data
- scientific ocean products
- Python integration

---

## Decision 2

Use the Python `copernicusmarine` package rather than direct frontend access.

Reason:

- backend security
- Python ML ecosystem
- direct integration with xarray/PyTorch

---

## Decision 3

Copernicus credentials remain backend-only.

---

## Decision 4

Use `describe()` before hard-coding dataset IDs.

This was explicitly strengthened after verifying current Copernicus documentation.

---

## Decision 5

Do small downloads before historical bulk download.

---

## Decision 6

Do not download the entire global archive.

---

## Decision 7

Use regional MVP:

    Bay of Bengal
    Arabian Sea

---

## Decision 8

Use 0.25° x 0.25° standardized grid.

This is an official problem requirement.

---

## Decision 9

Use daily temporal resolution.

Official requirement.

---

## Decision 10

Use seven logical surface channels.

Official requirement.

---

## Decision 11

Use 15 standard depth outputs.

Official requirement.

---

## Decision 12

Use GLORYS as training/reference target.

---

## Decision 13

Use ARGO as independent validation.

---

## Decision 14

Do not make ARGO a user input.

---

## Decision 15

Do not make the user upload satellite files.

---

## Decision 16

User interaction should be region-first and grid-cell/profile-driven.

---

## Decision 17

Primary product is a scientific ocean data product, not a chatbot.

---

## Decision 18

Do not replace GODAS.

Position OceanEmbed as complementary.

---

## Decision 19

Do not add cyclone/tsunami prediction to the 36-hour MVP.

---

## Decision 20

Start with a CNN baseline before implementing a Transformer/ViT.

---

## Decision 21

Architecture should prioritize simplicity and demonstrability.

---

## Decision 22

Uncertainty is a recommended differentiator but not a hard requirement.

---

## Decision 23

Depth-wise evaluation is important.

---

## Decision 24

Random train/test splitting should be avoided.

Use temporal holdout.

---

## Decision 25

Do not use image-style augmentation blindly.

Ocean data is geographically and physically meaningful.

---

## Decision 26

Normalize channels separately.

Training data only determines normalization statistics.

---

## Decision 27

Use NetCDF initially.

Consider Zarr only if needed.

---

## Decision 28

Use FastAPI for backend.

---

## Decision 29

Keep frontend and Copernicus credentials completely separated.

---

## Decision 30

Cache data and predictions.

---

## Decision 31

Do not promise deterministic "minutes" download latency.

Regional subsets should be practical, but real timing depends on infrastructure.

---

# 135. PREVIOUSLY VERIFIED COPERNICUS FACTS

Current official Copernicus documentation confirms:

- Toolbox supports login.
- Toolbox supports metadata discovery through `describe`.
- Toolbox supports `subset`.
- Toolbox supports `get`.
- Python API exists.
- Subset can select variables, geography, time and depth.
- Subset defaults to NetCDF and can support Zarr/CSV depending on data type.
- Toolbox has no fixed volume/bandwidth quota.
- Credentials can be stored/configured.
- Environment variables are supported for automated pipelines.
- `subset_split_on` supports splitting outputs by variable/time units.
- Most datasets support subsetting, but not necessarily every dataset.
- `get` provides full producer files.
- `subset` uses analysis-ready cloud-optimized data conventions.
- Actual data availability/latency is dataset-specific.

---

# 136. OFFICIAL COPERNICUS TOOLBOX PRINCIPLE

The current recommended flow is:

    1. Login
    2. Describe
    3. Verify dataset
    4. Subset
    5. Validate downloaded data
    6. Harmonize
    7. Cache
    8. Train/infer

Never skip:

    Describe
    →
    Verify

when dataset IDs or versions are uncertain.

---

# 137. IMMEDIATE NEXT CODING TASK

The first OpenCode task is NOT:

    "build the entire app"

It is:

    BUILD COPERNICUS CONNECTION PROOF

Requirements:

1. Install `copernicusmarine`.
2. Authenticate.
3. Run `describe()`.
4. Find current datasets for:
   - SST
   - SSS
   - SSH/SLA
   - current U
   - current V
   - wind U
   - wind V
5. Export a dataset verification report.
6. Select one verified SST dataset.
7. Download one day.
8. Bay of Bengal.
9. Open the resulting NetCDF.
10. Print:
    - dimensions
    - variables
    - coordinates
    - units
    - min
    - max
    - NaN percentage.
11. Repeat for Arabian Sea.

SUCCESS CONDITION:

    One verified real regional dataset
    can be retrieved programmatically
    and opened successfully.

---

# 138. SECOND CODING TASK

Build:

    dataset_registry.py

Containing verified metadata:

    DatasetSpec(
        logical_name="sst",
        product_id=...,
        dataset_id=...,
        variable=...,
        units=...,
        resolution=...,
        temporal_frequency=...,
        coverage_start=...,
        coverage_end=...,
        notes=...
    )

Do not manually scatter dataset IDs across the application.

---

# 139. THIRD CODING TASK

Build:

    region_registry.py

Example:

    REGIONS = {
        "bay_of_bengal": {
            "min_lon": 80,
            "max_lon": 100,
            "min_lat": 5,
            "max_lat": 22,
        },
        "arabian_sea": {
            "min_lon": 45,
            "max_lon": 75,
            "min_lat": 5,
            "max_lat": 25,
        },
    }

---

# 140. FOURTH CODING TASK

Build:

    ingestion_service.py

Responsibilities:

- validate region
- validate date
- resolve dataset
- check cache
- request subset
- save raw file
- record provenance
- return local path

---

# 141. FIFTH CODING TASK

Build:

    harmonization_service.py

Responsibilities:

- open source NetCDF
- normalize coordinates
- normalize timestamps
- normalize units
- regrid to 0.25°
- apply QC
- apply land/sea mask
- calculate missing mask
- return harmonized array

---

# 142. SIXTH CODING TASK

Build:

    training_dataset.py

Contract:

    __getitem__()

returns:

    {
        "inputs": [7,H,W],
        "target": [15,H,W],
        "mask": [H,W],
        "metadata": ...
    }

---

# 143. SEVENTH CODING TASK

Build:

    oceanembed_model.py

Start with:

    CNN encoder
    +
    decoder
    =
    15-channel temperature prediction

Do NOT start with ViT.

---

# 144. EIGHTH CODING TASK

Build:

    evaluate.py

Outputs:

    depth
    RMSE
    bias
    correlation

Also produce:

    prediction map
    error map
    profile comparison

---

# 145. NINTH CODING TASK

Build:

    inference_service.py

Input:

    region
    date

Output:

    [15,H,W]

Then:

    profile(latitude, longitude)

Output:

    15-depth temperature profile

---

# 146. TENTH CODING TASK

Build frontend.

Minimum UI:

    Region selector
    Date selector
    Depth selector
    Temperature map
    Grid-cell click
    Profile chart
    Model metadata
    Validation indicator

---

# 147. DEFINITION OF DONE

The MVP is considered successful when:

[ ] Copernicus authentication works.

[ ] Current datasets are discovered programmatically.

[ ] Dataset metadata is recorded.

[ ] Bay of Bengal data can be retrieved.

[ ] Arabian Sea data can be retrieved.

[ ] Seven surface inputs are harmonized.

[ ] Data is standardized to daily / 0.25°.

[ ] GLORYS target is available.

[ ] 15-depth target is constructed.

[ ] CNN baseline trains.

[ ] Test set is temporally held out.

[ ] RMSE is calculated.

[ ] Bias is calculated.

[ ] Correlation is calculated.

[ ] Depth-wise metrics are displayed.

[ ] Model inference works.

[ ] Map works.

[ ] Grid-cell click works.

[ ] Vertical profile works.

[ ] ARGO validation is demonstrated where data permits.

[ ] Copernicus credentials are server-side.

[ ] Raw data is cached.

[ ] Model version is recorded.

[ ] A fallback demo dataset exists.

[ ] Final presentation explains scientific validity.

---

# 148. THINGS THAT ARE NOT YET LOCKED

The following must NOT be treated as final decisions:

- exact CNN layer count
- exact hidden dimensions
- exact optimizer learning rate
- exact batch size
- exact training years
- exact train/validation/test dates
- exact dataset versions
- exact current product
- exact frontend map library
- exact database
- exact deployment provider
- exact uncertainty method
- exact physics loss
- exact feature augmentation
- exact Transformer architecture

These are engineering decisions to be validated.

---

# 149. THINGS THAT ARE LOCKED BY THE PROBLEM

The following are hard requirements:

    Surface inputs:
        SST
        SSS
        SSH/SLA
        current U/V
        wind U/V

    Temporal:
        daily

    Spatial:
        0.25° x 0.25°

    Domain:
        North Indian Ocean
        5°N–30°N
        45°E–105°E

    Output:
        subsurface temperature

    Standard depths:
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

    Evaluation:
        independent observations
        correlation
        RMSE
        bias

    Expected PoC:
        Bay of Bengal / Arabian Sea

---

# 150. FINAL ARCHITECTURE

The complete intended architecture is:

                       USER
                         |
                         v
                +----------------+
                |   React Web UI |
                +----------------+
                         |
                         | HTTPS
                         v
                +----------------+
                |    FastAPI     |
                |    Backend     |
                +----------------+
                    |          |
                    |          |
                    v          v
             +----------+   +----------+
             |  Cache / |   |  Model   |
             | Storage  |   | Service  |
             +----------+   +----------+
                    |
                    v
          +----------------------+
          | Copernicus Marine    |
          | Python Toolbox       |
          +----------------------+
                    |
                    v
          +----------------------+
          | Multi-source Ocean   |
          | Surface Products     |
          +----------------------+
                    |
                    v
          +----------------------+
          | QC / Harmonization   |
          | Daily / 0.25°         |
          +----------------------+
                    |
                    v
             [B, 7, H, W]
                    |
                    v
          +----------------------+
          | Surface Encoder      |
          +----------------------+
                    |
                    v
          +----------------------+
          | Ocean Embedding      |
          +----------------------+
                    |
                    v
          +----------------------+
          | Depth Decoder         |
          +----------------------+
                    |
                    v
             [B, 15, H, W]
                    |
                    v
          +----------------------+
          | Temperature Product  |
          +----------------------+
                    |
          +---------+----------+
          |                    |
          v                    v
     Visualization        Validation
                               |
                         +-----+-----+
                         |           |
                       GLORYS      ARGO
                         |           |
                         +-----+-----+
                               |
                               v
                       RMSE / Bias /
                       Correlation

---

# 151. FINAL PRODUCT DEFINITION

OceanEmbed is a:

    Daily
    0.25° x 0.25°
    surface-observation-driven
    deep-learning
    subsurface-temperature reconstruction
    system

for the North Indian Ocean.

The MVP focuses on:

    Bay of Bengal
    Arabian Sea

The user experience is:

    Region
      →
    Date
      →
    Depth
      →
    Temperature Map
      →
    Grid Cell
      →
    15-Depth Profile
      →
    Uncertainty / Validation

The ML experience is:

    7 surface channels
      →
    harmonization
      →
    encoder
      →
    Ocean embedding
      →
    decoder
      →
    15-depth temperature field

The scientific validation experience is:

    prediction
      vs
    GLORYS
      +
    independent ARGO

---

# 152. GOLDEN RULES FOR OPENCODE

1. Do not invent data.
2. Do not invent dataset IDs.
3. Do not invent validation scores.
4. Do not fake ARGO validation.
5. Do not call model-derived current products "pure satellite."
6. Do not expose Copernicus credentials.
7. Do not randomly split temporal ocean data.
8. Do not use image-style augmentation blindly.
9. Do not feed subsurface target information into inference inputs.
10. Do not build the frontend before proving the data pipeline.
11. Do not download years of data before a one-day test succeeds.
12. Do not optimize architecture before establishing a baseline.
13. Do not claim operational/real-time capability without verifying latency.
14. Do not replace GODAS in the product narrative.
15. Do not add unnecessary LLM features.
16. Preserve dataset provenance.
17. Preserve channel ordering.
18. Preserve depth ordering.
19. Normalize using training statistics only.
20. Keep the 36-hour MVP regional and demonstrable.
21. Every scientific claim must be traceable to data or a documented assumption.
22. If a requirement is ambiguous, mark it UNRESOLVED instead of guessing.

---

# 153. AUTHORITATIVE SOURCE HIERARCHY

Priority order:

    1. Official SIH problem statement / official SIH portal
    2. Official Copernicus Marine documentation/catalogue
    3. Official INCOIS documentation
    4. Official dataset documentation
    5. Peer-reviewed research
    6. Uploaded project memory
    7. Secondary/community SIH mirrors
    8. Model inference / engineering proposal

When sources disagree:

    use the higher-priority source

Never silently overwrite an official requirement with a community interpretation.

---

# 154. SOURCE MATERIAL USED TO CREATE THIS MEMORY

Primary project sources available in the previous working environment included:

- SIH 2026 problem-statement material
- Ocean Data API transfer memory
- Copernicus Marine official documentation
- INCOIS public operational/data documentation
- research literature on satellite-to-subsurface temperature reconstruction
- CodeHunters hackathon mentoring context

The uploaded Ocean Data API transfer memory explicitly records:

- Copernicus Marine as primary provider
- Bay of Bengal and Arabian Sea bounds
- backend-only authentication
- `copernicusmarine`
- `describe()`
- `subset()`
- FastAPI architecture
- NetCDF
- harmonization
- chunked historical downloads
- automated daily ingestion

The SIH26066 problem statement records:

- daily observations
- 0.25° grid
- North Indian Ocean domain
- seven surface input variables
- 15 output depths
- CNN/ViT/Autoencoder/GNN/attention options
- GLORYS target
- independent ARGO validation
- RMSE/correlation/bias
- Bay of Bengal/Arabian Sea PoC

---

# 155. RESOURCE REFERENCE

The project's official CodeHunters resource mapping identifies the Ultimate Hackathon Playbook as the primary external learning resource for:

- problem statements
- architecture
- MVP
- AI usage
- strategy
- judge psychology
- presentation

Official resource URL recorded in Resources.md:

    https://topmate.io/dasandcode

This resource is supplementary and does NOT override the technical source-of-truth above.

---

# 156. FINAL STATUS

PROJECT STATUS:

    Architecture:
        STRONG

    Domain understanding:
        ESTABLISHED

    Data provider:
        SELECTED
        Copernicus Marine

    API mechanism:
        SELECTED
        Python Toolbox

    Authentication:
        ESTABLISHED
        backend/server-side

    Regions:
        SELECTED FOR MVP
        Bay of Bengal
        Arabian Sea

    Surface inputs:
        LOCKED
        7 channels

    Target:
        LOCKED
        15 depth temperatures

    Grid:
        LOCKED
        0.25° x 0.25°

    Frequency:
        LOCKED
        daily

    Training target:
        SELECTED
        GLORYS

    Independent validation:
        SELECTED
        ARGO

    Model:
        BASELINE RECOMMENDED
        CNN encoder-decoder

    Advanced model:
        OPTIONAL
        attention / ViT / depth conditioning

    Uncertainty:
        OPTIONAL DIFFERENTIATOR

    Frontend:
        RECOMMENDED
        React + TypeScript + Vite

    Backend:
        RECOMMENDED
        FastAPI + Python

    ML:
        RECOMMENDED
        PyTorch + xarray + NumPy

    Database:
        NOT LOCKED

    Deployment:
        NOT LOCKED

    Exact Copernicus dataset IDs:
        MUST BE VERIFIED BEFORE DOWNLOAD

    Exact training period:
        MUST BE VERIFIED AFTER DATA COVERAGE MATRIX

    Exact neural hyperparameters:
        MUST BE EXPERIMENTALLY SELECTED

---

# 157. IMMEDIATE NEXT STEP

DO THIS FIRST IN OPENCODE:

    1. Create Python environment.
    2. Install copernicusmarine.
    3. Authenticate.
    4. Run describe().
    5. Generate the dataset verification matrix.
    6. Select one verified SST dataset.
    7. Download one day for Bay of Bengal.
    8. Validate NetCDF.
    9. Download the same test for Arabian Sea.
    10. Commit the verified dataset registry.

ONLY AFTER THIS SUCCEEDS:

    verify all seven surface channels
        ↓
    build harmonization
        ↓
    build GLORYS target
        ↓
    train CNN baseline
        ↓
    evaluate
        ↓
    build application

---

# 158. ONE-SENTENCE SOURCE OF TRUTH

OceanEmbed is a software-only, surface-observation-driven deep-learning system that harmonizes seven daily surface ocean variables to a 0.25° grid, learns a latent representation of the North Indian Ocean surface state, reconstructs temperature at 15 standard subsurface depths, validates against GLORYS and independent ARGO observations, and exposes the result as an interactive Bay of Bengal / Arabian Sea scientific data product.

# 159. ML ARCHITECTURE DECISION (2026-09-04, evaluator-reviewed)

Primary architecture: CNN spatial encoder + ConvLSTM temporal encoder + reconstruction decoder.

Based on Su et al. 2022 (ConvLSTM, proven R2=0.99) and adapted for our 7-channel, 0.25° setup.

Spatiotemporal clustering (Loo et al. 2026) is DEFERRED — must prove >5% RMSE gain in ablation study before inclusion.

Full spec: docs/superpowers/specs/2026-09-04-ml-architecture-design.md

# 160. FROZEN BEFORE CODING (2026-09-04)

1. Inputs: SST, SSS, SSH/SLA, Current U/V, Wind U/V (7 channels, LOCKED)
2. Sources: 5 Copernicus Marine products (verified 2026-09-02)
3. Outputs: Temperature at 15 depths + uncertainty (mu, sigma)
4. Validation: Independent ARGO profiles (never in training)
5. Differentiation: Scientific credibility + uncertainty + ARGO validation (not model complexity)

# END OF SYSTEM_MEMORY_DUMP.md
