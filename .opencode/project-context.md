# Project Context (one page)

OceanEmbed reconstructs **subsurface ocean temperature** (15 standard depths) from **7 surface
satellite channels** over the **North Indian Ocean** (0.25° grid, daily). Source: SIH26066.

- Quick context: `SYSTEM_MEMORY_DUMP.md` (history/decisions) + `docs/` (current truth).
- Product: `docs/01-product/` · Architecture: `docs/02-architecture/` · Domain: `docs/03-domain/`
- Data: `docs/04-data/` · ML: `docs/05-ml/` · API: `docs/06-api/` · Ops: `docs/07-operations/`

## Canonical facts (LOCKED)

- Inputs (7, ordered): SST, SSS, SSH/SLA, current U, current V, wind U, wind V.
- Outputs (15, ordered): temperature at 0,5,10,20,30,50,75,100,125,150,200,300,500,700,1000 m.
- Grid 0.25°; temporal daily; domain 5–30°N, 45–105°E.
- MVP regions: Bay of Bengal, Arabian Sea.

## System structure

```text
imports:       contracts/ (interfaces)  config/ (canonical config)
governs:       docs/ + AGENTS.md + SYSTEM_MEMORY_DUMP.md
implementers:  backend/ (FastAPI API)  ml/ (PyTorch training/inference)
               data-engineering/ (Copernicus ingestion/harmonization)
               frontend/ (React UI)  database/ (Alembic migrations)
deploy:        infrastructure/ (Docker/Terraform/K8s)  observability/
```

## Key rules to not re-learn from scratch

- Frontend never touches Copernicus/credentials (RULE 1–2); backend never trains (RULE 3).
- GLORYS = training target, never inference input (RULE 8); ARGO = independent validation only (RULE 9).
- Temporal (not random) train/val/test split (RULE 10); normalization from training data only (RULE 11).
- No datasets/checkpoints/secrets in Git (RULE 12–14).

## Status

Documentation + skeleton phase complete. Coding phase: start with the Copernicus 1-day regional
proof (verify datasets → subset one day → harmonize → baseline model), per `docs/07-operations/`
and ADR-008.