# Feature Workflow

Repeatable feature-development workflow for agents (backend, ML, data, frontend).

## Steps

1. **Read context**: `AGENTS.md`, `.opencode/project-context.md`, relevant `docs/`, the affected
   `contracts/`, and existing `config/` + implementation.
2. **Confirm scope**: is the requirement LOCKED/CONFIRMED/PROPOSED? Mark UNRESOLVED if ambiguous.
   If an architectural decision is implied → create/update an ADR first.
3. **Write the test first (RED)**: per `.opencode/testing-rules.md`.
4. **Implement (GREEN)**: smallest change; respect architecture boundaries.
5. **Refactor (IMPROVE)**: keep functions/files within size limits; check immutability.
6. **Update contracts/docs** if interfaces or behavior changed (RULE 6, RULE 20).
7. **Verify**: module tests + coverage ≥80% + `make lint` (+ `make test-all` for cross-cutting).
8. **Review**: run a code-review pass (see `receiving-code-review` guidance) before commit.

## Gate

Do not merge without: passing tests, coverage gate, lint, contract verification, docs/contract
sync, and (for ML) an evaluation result + model-card note where behavior changes.