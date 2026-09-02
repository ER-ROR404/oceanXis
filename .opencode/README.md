# .opencode/

> **AI-agent control plane.** How LLM coding agents should operate inside this repository.
>
> Read order for agents before ANY code change:
> `AGENTS.md` → `SYSTEM_MEMORY_DUMP.md` → `docs/` → `contracts/` → `config/` → implementation.

## What lives here

| File | Purpose |
|------|---------|
| `project-context.md` | One-page architectural context (don't parse the whole memory dump first). |
| `coding-rules.md` | Coding conventions and prohibited implementation shortcuts. |
| `architecture-rules.md` | Boundaries an agent must not violate. |
| `testing-rules.md` | Test requirements per module/change type. |
| `workflows/feature.md` | Repeatable feature-development workflow. |
| `workflows/bugfix.md` | Repeatable bug-fix workflow. |
| `workflows/data-pipeline.md` | Safe workflow for data ingestion/preprocessing changes. |
| `workflows/model-training.md` | Safe workflow for model/training changes. |
| `workflows/release.md` | Release and validation workflow. |

## Operating contract for agents

1. Follow the hierarchy: agent rules → memory dump → docs → contracts → config → code.
2. Never invent scientific/data facts, dataset IDs, or validation scores (RULE 7, Golden Rules 1–4).
3. Smallest possible change; tests first (TDD; 80%+ line coverage backend/ML).
4. Update contracts + docs when behavior/interfaces change (RULE 6, RULE 20).
5. Run the relevant module tests + `make lint` before reporting completion.

These files are **SHARED** artifacts, kept in sync with `AGENTS.md` and `docs/`.