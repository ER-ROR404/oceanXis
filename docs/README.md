# Documentation

> **Authoritative engineering documentation for OceanEmbed (SIH26066).**

`SYSTEM_MEMORY_DUMP.md` (repo root, mirrored in `doc/`) preserves history. This `docs/` tree is the
**current authoritative implementation truth**. When a decision changes: write/update an ADR and
update the relevant doc — do not silently rewrite history.

## Reading order

For a new contributor or agent, follow this order:

1. `../AGENTS.md` — operating rules.
2. `../SYSTEM_MEMORY_DUMP.md` — full historical context.
3. `01-product/product-requirements.md` — what is being built and why.
4. `02-architecture/system-context.md` + `container-architecture.md` — how it is structured.
5. `03-domain/*` — scientific domain facts.
6. `04-data/*` — where data comes from and how it is made model-ready.
7. `05-ml/*` — model, training, and evaluation policy.
8. `06-api/*` — external interfaces (see also `../contracts/`).
9. `07-operations/*` — how it runs.

## Directory map

| Section | Contents |
|---------|----------|
| `01-product/` | Problem statement, product requirements, user workflows, acceptance criteria, scope/non-goals |
| `02-architecture/` | System/container/deployment architecture, data flow, ML serving, security, observability, **ADRs** |
| `03-domain/` | Ocean domain, canonical variables, depths, regions, units, scientific assumptions |
| `04-data/` | Data sources, dataset registry, data contract, preprocessing, regridding, QC, missing-data, temporal alignment, provenance |
| `05-ml/` | ML system, model architecture, feature spec, training/evaluation policy, experiments, checkpoints, model card |
| `06-api/` | API overview, authentication, error contract, OpenAPI policy |
| `07-operations/` | Local development, deployment, training ops, daily ingestion, monitoring, backup, incident response |
| `08-decisions/` | Consolidated decision log |

## Relationship to contracts

- `docs/` explain **what and why**. `../contracts/` define **the exact interface shapes**.
- The contracts are the single source of truth for interface structure; docs summarize them.
- `config/` holds the canonical runtime values (regions, depths, variables, datasets, model, training).