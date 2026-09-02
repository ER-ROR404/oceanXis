# Testing Rules (agents)

- TDD: write the failing test first (RED) → minimal implementation (GREEN) → refactor (IMPROVE).
- Minimum line coverage: **80%** for backend and ML code.
- Every behavioral change needs a test in the appropriate `tests/` directory.
- Tests must not require live Copernicus/network calls — use synthetic fixtures under
  `tests/fixtures/` (small, non-sensitive, CI-safe).

## Where tests live

| Module | Location | Run with |
|--------|----------|----------|
| Backend | `backend/tests/{unit,integration,api}/` | `pytest backend/tests` |
| ML | `ml/tests/` | `pytest ml/tests` |
| Data-engineering | `data-engineering/tests/` | `pytest data-engineering/tests` |
| Frontend | `frontend/` (per-component) | `npm test` (frontend) |
| Repository gate | root CI | `make test-all` |

## Required per change type

- **API change** → contract validation + `api/` endpoint tests (response conforms to schema).
- **Data pipeline change** → harmonization/provenance tests + contract tests.
- **Model/architecture change** → shape/contract tests + metrics tests; never only accuracy claims.
- **Bug fix** → regression test reproducing the bug first.
- **Config change** → config-vs-contract validation test (`scripts/verify-contracts.py`).

## Coverage

- Run `pytest --cov=backend --cov=ml` and `make lint` before reporting completion.
- CI enforces the 80% gate (see `.github/workflows/*.yml`).

## Leakage checks (ML tests)

Every training/eval test must prove:
- test/val dates are strictly later than train (RULE 10);
- normalization stats came from train only (RULE 11);
- no target/GLORYS-subsurface channel appears in the input tensor (RULE 8).