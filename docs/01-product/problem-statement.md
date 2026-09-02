# Problem Statement (SIH26066)

> **Source:** Official SIH 2026 portal. This is a normalized record — where wording differs from the
> official portal, the official portal wins (see `SYSTEM_MEMORY_DUMP.md` §153).
> Status markers: `LOCKED REQUIREMENT` / `CONFIRMED` / `PROPOSED` / `UNRESOLVED`.

## Identity

| Field | Value | Status |
|-------|-------|--------|
| Problem ID | SIH26066 | LOCKED |
| Title | OceanEmbed — Satellite Embedding-Based Deep Learning Framework for Reconstruction of Subsurface Ocean Temperature from Surface Satellite Observations | LOCKED |
| Organization | Ministry of Earth Sciences (MoES) | LOCKED |
| Department | Indian National Centre for Ocean Information Services (INCOIS) | LOCKED |
| Category | Software | LOCKED |

## Problem summary (normalized)

Subsurface ocean temperature is essential for ocean circulation understanding, upper-ocean heat
content, stratification, climate variability, marine heatwave monitoring, ecosystem analysis, and
operational oceanography — but direct subsurface observations (ARGO floats, moorings, gliders,
ships) are spatially sparse. Satellite observations provide broad and frequent surface coverage.

The challenge is a **learned inverse problem**:

```text
Can the hidden subsurface thermal structure be inferred from the information
encoded in the surface ocean state?
```

## Required inputs (surface)

| # | Variable | Status |
|---|----------|--------|
| 1 | Sea Surface Temperature (SST) | LOCKED |
| 2 | Sea Surface Salinity (SSS) | LOCKED |
| 3 | Sea Surface Height / Sea Level Anomaly (SSH / SLA) | LOCKED |
| 4 | Surface ocean current U | LOCKED |
| 5 | Surface ocean current V | LOCKED |
| 6 | Surface wind U | LOCKED |
| 7 | Surface wind V | LOCKED |

Logical channel count: **7**. Canonical order: SCC, SSS, SSH/SLA, current U, current V, wind U, wind V.

## Required outputs

Temperature reconstructed at **15 standard depths**:

```text
0, 5, 10, 20, 30, 50, 75, 100, 125, 150, 200, 300, 500, 700, 1000 m
```

Output channel count: **15**. Ordering is canonical and contracts-enforced.

## Spatial / temporal / domain

| Aspect | Requirement | Status |
|--------|-------------|--------|
| Spatial resolution | 0.25° × 0.25° | LOCKED |
| Temporal resolution | daily | LOCKED |
| Official domain | North Indian Ocean: 5°N–30°N, 45°E–105°E | LOCKED |
| Expected PoC | Bay of Bengal and/or Arabian Sea | LOCKED |

## Permitted model families

The problem statement explicitly allows architectures such as CNN, Vision Transformer, Autoencoder,
GNN, and attention-based hybrid architectures. **The exact architecture is an engineering decision**
(`PROPOSED` CNN encoder–decoder baseline — see `docs/05-ml/`).

## Training / validation expectation

| Item | Status |
|------|--------|
| GLORYS as dense training/reference target | LOCKED (recommended by problem statement) |
| Independent validation against observations | LOCKED |
| ARGO as independent validation source | LOCKED (per problem statement) |
| Metrics: correlation, RMSE, bias | LOCKED |

## Hardware constraint

The team has explicitly decided: **software-only**. No hardware deliverable.
Status: CONFIRMED (team decision).