# Coding Rules (agents)

Conventions an agent must follow when writing code in this repository.

## Style

- Python: black-style formatting, ruff (see root `pyproject.toml`), type hints everywhere.
- TypeScript: strict `tsconfig.json`, ESLint enforced.
- Small functions (<50 lines), focused files (<800 lines). Many small files, not few large ones.
- No dead code, no debugging leftovers, no commented-out blocks.

## Immutability

- Prefer returning new objects over mutating inputs (especially numpy/xarray tensors).
- Never mutate normalization statistics, contracts, or migration files in place.

## Boundaries (highlights — full list in architecture-rules.md)

- Backend services talk to Copernicus ONLY via `backend/app/integrations/copernicus/`.
- ML inference consumes `contracts/ml/model-input.schema.json` (RULE 5).
- API responses conform to `contracts/api/*` (RULE 6).

## Prohibited shortcuts

- Do NOT hardcode dataset IDs (RULE 7) — verify via `describe()` first, populate `config/datasets.yaml`.
- Do NOT put secrets/logs of secrets in code (RULE 14).
- Do NOT reorder channels/depths (RULE 20).
- Do NOT add LLM features, microservices, or Kubernetes without an ADR (RULE 17–19).
- Do NOT add a dependency when an existing one suffices (RULE 16).

## Error handling

- Fail fast with clear messages at system boundaries; validate all inputs (schema-based).
- Never silently swallow errors. Log structured context server-side; user-friendly messages in UI.

## Verification before completion

- Run the module tests + `make lint`. Evidence before claiming success (see `Makefile`).