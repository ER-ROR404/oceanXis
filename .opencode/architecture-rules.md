# Architecture Rules (agents)

Non-negotiable boundaries. Mirrors `AGENTS.md` RULE 1–20 and `docs/02-architecture/`.

## Data / provider

- RULE 7 — Dataset IDs are verified via `copernicusmarine.describe()`, never guessed. Registry:
  `config/datasets.yaml` + `docs/04-data/dataset-registry.md`.
- RULE 8 — GLORYS subsurface variables are training/reference targets only; never inference inputs.
- RULE 9 — ARGO is independent validation data, matched by date/location, never fabricated.
- RULE 10 — Train/validation/test split is strictly temporal; no random split of ocean data.
- RULE 11 — Normalization statistics come from training data only; stored as model artifacts.

## Application

- RULE 1 — Frontend never accesses Copernicus credentials.
- RULE 2 — Frontend never calls Copernicus directly (always through the backend API).
- RULE 3 — Backend never contains model-training code.
- RULE 4 — ML training never depends on frontend code.
- RULE 5 — ML inference consumes the canonical model-input contract.
- RULE 6 — API responses conform to `contracts/api/`.
- RULE 15 — Applied database migrations are never edited; add a new migration.
- RULE 20 — No channel/depth reordering without updating contracts + `config/`.

## Engineering restraint

- RULE 16 — No new dependency when an existing one solves the problem.
- RULE 17 — No microservices without a documented architectural reason (ADR).
- RULE 18 — No Kubernetes merely for "enterprise".
- RULE 19 — No LLM/chatbot feature unless explicitly required.

## Layering

```text
frontend → backend API → services → integrations (copernicus/argo/storage)
data-engineering → object storage → ML dataset → training → checkpoint → evaluation → registry → inference
```

Violations of these rules block merge.