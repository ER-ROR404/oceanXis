# OceanEmbed — SIH26066

> **Satellite Embedding-Based Deep Learning Framework for Reconstruction of Subsurface Ocean Temperature from Surface Satellite Observations.**
> Ministry of Earth Sciences (MoES) · Indian National Centre for Ocean Information Services (INCOIS) · SIH 2026 · Software

## One-sentence source of truth

OceanEmbed is a software-only, surface-observation-driven deep-learning system that harmonizes seven daily surface ocean variables to a 0.25° grid, learns a latent representation of the North Indian Ocean surface state, reconstructs temperature at 15 standard subsurface depths, validates against GLORYS and independent ARGO observations, and exposes the result as an interactive Bay of Bengal / Arabian Sea scientific data product.

## What this repository contains

| Area | Description |
|------|-------------|
| `docs/` | Current authoritative engineering documentation (product, architecture, domain, data, ML, API, operations, decisions) |
| `contracts/` | Versioned interface contracts — API (OpenAPI + JSON schemas), data, ML |
| `config/` | Canonical domain/runtime configuration (regions, depths, variables, datasets, preprocessing, model, training) |
| `backend/` | FastAPI application backend (ingestion, preprocessing, inference, profile, prediction APIs) |
| `ml/` | Independent ML training/evaluation/inference package (PyTorch) |
| `data-engineering/` | Data acquisition and harmonization workflows (Copernicus Marine) |
| `database/` | Alembic migrations and seed data |
| `frontend/` | React + TypeScript + Vite interactive dashboard |
| `infrastructure/` | Docker/Terraform/Kubernetes skeletons (production target; NOT required for MVP) |
| `security/` | Security and credential governance |
| `observability/` | Metrics, dashboards, and alert definitions |
| `.opencode/` | AI-agent control plane (rules + workflows) |

## System at a glance

```text
7 surface channels (SST, SSS, SSH/SLA, current U/V, wind U/V)
        ↓
harmonization → daily 0.25° tensor [7,H,W]
        ↓
Surface Encoder → Ocean Embedding → Depth Decoder
        ↓
temperature [15,H,W] (0..1000 m, 15 standard depths)
        ↓
validation vs GLORYS (target) and ARGO (independent)
```

## Non-goals (MVP)

No hardware, no cyclone/tsunami forecasting, no GODAS replacement, no chatbot features, no Kubernetes for the MVP. OceanEmbed is a *complementary* learned reconstruction pathway, not a replacement for numerical ocean modelling.

## Key constraints

- Copernicus credentials remain **backend-only** (server-side), never in frontend code or Git.
- Dataset IDs must be **verified** via `copernicusmarine.describe()` before use — never guessed.
- Data is **temporally split** (no random train/test split); normalization uses training data only.
- No fabrication of data, dataset IDs, validation scores, or ARGO comparisons.

## Quick start (once implemented)

See `docs/07-operations/local-development.md`. The first milestone is the **Copernicus connection proof**: `describe()` → one verified SST dataset → one-day regional download → NetCDF inspection.

## Governance

- Repository rules for AI agents: `AGENTS.md`
- Historical decisions and constraints: `SYSTEM_MEMORY_DUMP.md`
- Contribution standards: `CONTRIBUTING.md`
- Security: `SECURITY.md`