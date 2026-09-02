# AGENTS.md

> **This file is the entry point for any AI coding agent working in this repository.**
> Read this file first, then follow the hierarchy below.

## Document hierarchy

```text
AGENTS.md
    ↓
SYSTEM_MEMORY_DUMP.md
    ↓
docs/
    ↓
contracts/
    ↓
implementation
```

1. `AGENTS.md` — operating rules for agents working in this repo.
2. `SYSTEM_MEMORY_DUMP.md` — historical project memory, decisions, constraints, and source-of-truth context (SIH26066 / OceanEmbed).
3. `docs/` — current authoritative engineering documentation.
4. `contracts/` — versioned interface contracts (API, data, ML).
5. `config/` — canonical runtime/domain configuration.
6. Implementation code under `backend/`, `ml/`, `data-engineering/`, `frontend/`.

> **Principle:** `SYSTEM_MEMORY_DUMP.md` preserves history. `docs/` and `contracts/` are the current authoritative implementation truth. If a decision changes, do not rewrite history silently — create/update an ADR and update the current contract/documentation.

## BEFORE MODIFYING CODE

Agents MUST perform these steps before any code change:

1. Read `AGENTS.md`.
2. Read relevant domain documentation under `docs/`.
3. Read the relevant contract under `contracts/`.
4. Inspect the existing implementation.
5. Identify existing tests.
6. Make the smallest change.
7. Run the relevant tests.
8. Update documentation if behavior changed.
9. Never silently change an architectural decision.
10. Never invent missing scientific/data information.

## RULES

### Architecture boundaries

```text
RULE 1   Frontend must never directly access Copernicus credentials.
RULE 2   Frontend must never call Copernicus directly.
RULE 3   Backend must never contain model-training code.
RULE 4   ML training must never depend on frontend code.
RULE 5   ML inference must consume the canonical model-input contract.
RULE 6   API responses must conform to contracts/.
RULE 7   Dataset IDs must be verified rather than guessed.
RULE 8   GLORYS subsurface variables must never become inference inputs.
RULE 9   ARGO must remain independent validation data.
RULE 10  Train/validation/test splitting must respect temporal ordering.
RULE 11  Normalization statistics must be calculated from training data only.
RULE 12  Large datasets must never be committed to Git.
RULE 13  Large model checkpoints must never be committed to Git.
RULE 14  Secrets must never be committed to Git.
RULE 15  Applied database migrations must never be edited.
RULE 16  Do not introduce a new dependency when an existing dependency solves the problem.
RULE 17  Do not introduce microservices without a documented architectural reason.
RULE 18  Do not introduce Kubernetes merely because the project is "enterprise".
RULE 19  Do not add an LLM/chatbot feature unless explicitly required.
RULE 20  Do not change canonical variable/depth/channel ordering without updating contracts.
```

### Scientific/source-of-truth rules (from SYSTEM_MEMORY_DUMP.md §152)

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

### Requirement classification

Use these status markers in all documentation:

- `LOCKED REQUIREMENT` — explicitly required by the problem statement or an established decision.
- `CONFIRMED` — verified from an authoritative/current source.
- `PROPOSED` — recommended engineering design, not an official SIH requirement.
- `UNRESOLVED` — must be verified before implementation.

Do NOT silently convert `PROPOSED` or `UNRESOLVED` items into facts.

## Environment isolation

Three logical Python environments; do NOT make ML training a dependency of the backend:

- **Backend environment** — FastAPI, Pydantic, SQLAlchemy, Copernicus client, xarray, inference runtime.
- **ML environment** — PyTorch, CUDA-compatible dependencies, xarray, scientific stack, training utilities.
- **Data-engineering environment** — ingestion, harmonization, provenance tooling.

Dependencies are declared per-module (`backend/pyproject.toml`, `ml/pyproject.toml`, `data-engineering/pyproject.toml`, `frontend/package.json`). The root `pyproject.toml` holds shared linting/formatting/testing tooling only.

## Testing expectations

- TDD: write the test first (RED), implement (GREEN), refactor (IMPROVE).
- Minimum line coverage target: 80% for backend and ML code.
- Every behavioral change needs a test in the appropriate `tests/` directory.
- Run the relevant modules' tests before reporting work complete.

## Canonical facts (LOCKED by problem statement)

- Inputs: 7 surface channels — SST, SSS, SSH/SLA, current U, current V, wind U, wind V.
- Outputs: temperature at 15 standard depths — 0, 5, 10, 20, 30, 50, 75, 100, 125, 150, 200, 300, 500, 700, 1000 m.
- Grid: 0.25° x 0.25°; Temporal: daily.
- Domain: North Indian Ocean — 5°N to 30°N, 45°E to 105°E.
- PoC regions: Bay of Bengal, Arabian Sea.
- Evaluation: RMSE, bias, correlation, depth-wise; GLORYS as training target; ARGO as independent validation.