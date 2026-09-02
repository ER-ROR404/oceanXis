# System Context

> Describes external systems, users, and OceanEmbed's system boundary.
> Reference: SYSTEM_MEMORY_DUMP.md §150.

## Actors / external systems

| Element | Type | Relationship |
|---------|------|--------------|
| User (ocean scientist / judge / operator) | Human | Interacts through the React web UI |
| Copernicus Marine | External provider | Primary provider of multi-source surface ocean products (via Toolbox) |
| GLORYS (GLOBAL_MULTIYEAR_PHY_001_030 family) | External reference product | Dense training/reference **target** — never an inference input |
| ARGO | External observation programme | **Independent validation** observations |
| Prediction/object store | Internal boundary | Cached raw data, harmonized tensors, prediction rasters |
| Database | Internal boundary | Metadata + application state (dataset/ingestion/prediction/model registry) |

```text
                       USER
                         |
                         v
                +----------------+
                |   React Web UI |
                +----------------+
                         |
                         | HTTPS/JSON
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
```

## System boundary rules

- The **backend** is the only component that talks to Copernicus Marine.
- The **frontend** never holds Copernicus credentials and never calls Copernicus (RULE 1, 2).
- **GLORYS** subsurface temperature is a training target only; it must never appear among inference
  inputs (RULE 8, Golden Rule 9).
- **ARGO** remains independent validation data (RULE 9).
- OceanEmbed does not replace GODAS or INCOIS operational modelling (§6/§99 of memory dump).

## Core transformation

```text
DAILY SURFACE OCEAN STATE
    → multi-source data harmonization
    → surface ocean embedding
    → deep learning reconstruction
    → subsurface temperature profile (15 depths)
    → daily 3D temperature product
```