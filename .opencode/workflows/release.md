# Release Workflow

Release and validation workflow for the whole system.

## Preconditions

- All module tests pass, coverage ≥80% (backend/ML), lint clean.
- Contracts verified (`scripts/verify-contracts.py`), docs in sync.
- No secrets/datasets/checkpoints staged (RULE 12–14).
- ADR updated if any architectural decision changed.

## Steps

1. Bump version in `CHANGELOG.md` + relevant `pyproject.toml` (or package.json).
2. Run the repository-wide gate: `make test-all` (lint + test + contract verification).
3. Build images: `scripts/build-images.sh` (docker-build workflow).
4. Deploy to staging: `scripts/deploy-staging.sh`; run smoke tests against staging.
5. Validate data ingestion freshness + model endpoint (no realtime claims unless verified).
6. Approve and deploy to production: `scripts/deploy-production.sh`.
7. Record release in `CHANGELOG.md`; update `docs/08-decisions/decision-log.md` if needed.

## Rollback

- Backend/frontend: redeploy previous image.
- Model: registry promotion includes rollback-to-previous-approved-version path (ADR + model-registry).

Every release is reproducible from the repository + artifact store alone.