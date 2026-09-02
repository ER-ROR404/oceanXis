# CONTRIBUTING.md

> OceanEmbed — contribution standards for humans and AI agents.

## Repository governance

1. `AGENTS.md` defines mandatory agent operating rules. Read it before any work.
2. `SYSTEM_MEMORY_DUMP.md` preserves history; `docs/` and `contracts/` are the current authoritative truth.
3. Changes that alter an architectural decision require an ADR update or new ADR first.
4. Changes that alter any interface must update the relevant contract under `contracts/` and its schema consumers.

## Branching

- Long-lived branches: `main` (protected) and `develop` (integration) as needed.
- Feature branches: `feat/<short-description>`.
- Bug fixes: `fix/<short-description>`.
- Data/ML experiments: `experiment/<name>` — never merged directly to `main`.
- Do not force-push to shared branches.

## Commit convention

Use Conventional Commits:

```text
<type>: <description>
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`.

Examples:

```text
feat: add region registry
fix: align Bayesian grid longitude convention
test: add depth ordering unit tests
docs: record ADR-008 regional MVP scope
```

Keep commits small, atomic, and reviewable. Do NOT commit:

- secrets (`.env`, credentials, tokens)
- large datasets (also enforced by RULE 12)
- model checkpoints (also enforced by RULE 13)
- generated artifacts (`__pycache__`, `dist/`, `node_modules/`)

## Pull requests

Each PR must include:

1. A description of the change and why.
2. Reference to the relevant ADR / requirement / issue.
3. Contract or config changes, if any.
4. Test plan: commands run and results.
5. Links to any generated reports or artifacts.

For ML PRs, include the experiment registry entry and model-card/limitation notes where the change affects model behavior.

## Testing expectations

- TDD: test first (RED) → implement (GREEN) → refactor (IMPROVE).
- Minimum line coverage target: **80%** for backend and ML code.
- Every behavioral change needs a test in the appropriate `tests/` directory.
- Run the relevant module's tests before requesting review (see ROOT `Makefile`).
- CI must pass the repository-wide gate (`ci.yml`) before merge.

## Review

- Human review required for changes to `contracts/`, `docs/02-architecture/`, and `database/migrations/`.
- Security-sensitive changes (auth, credentials handling, API endpoints) require a security review.
- AI-agent review (code-reviewer) is expected for all code changes per `AGENTS.md`.

## Definition of done

1. Tests written first and passing.
2. Coverage ≥ 80% for backend/ML.
3. Lint and type checks pass.
4. Contracts updated if interfaces changed.
5. Docs updated if behavior changed.
6. No secrets, datasets, or checkpoints staged.
7. ADR created/updated if an architectural decision changed.