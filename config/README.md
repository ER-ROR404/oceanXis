# config/

> **Canonical runtime and domain configuration.** These files are the single source of truth for
> regions, depths, variables, datasets, and model/training defaults. Code reads these; contracts
> reference them; docs explain them.
>
> Hierarchy: `AGENTS.md` → `SYSTEM_MEMORY_DUMP.md` → `docs/` → `contracts/` → `config/` → code.

## Ownership & rules

- **Domain files** (`regions.yaml`, `depths.yaml`, `variables.yaml`) encode LOCKED facts from the
  problem statement. Do not change their canonical ordering/bounds without updating the related
  `docs/03-domain/*` and `contracts/ml/*` (RULE 20, Golden Rule 17/18).
- **Behavior files** (`datasets.yaml`, `preprocessing.yaml`, `model.yaml`, `training.yaml`) control
  runtime behavior without embedding constants in code (fail-fast, no hardcoded magic numbers).
- **`environments/`** (local/test/staging/production) hold per-environment configuration references.
  Real secrets live in the environment / secret manager, never in these files (RULE 14).

## Schema compatibility

- These YAML files MUST validate against `contracts/` schemas where one exists (e.g. regions/depths
  follow the canonical enums in `contracts/ml/*.schema.json`).
- `scripts/verify-contracts.py` validates configs against contracts in CI.

## Precedence

Environment variables (see `.env.example`) > `environments/<regime>.yaml` > domain/behavior YAML
defaults.
