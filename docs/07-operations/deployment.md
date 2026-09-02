# Deployment

> Staging/production deployment procedures. **Deployment provider NOT LOCKED.**

## Staging (proposed)

1. Build images: `scripts/build-images.sh`.
2. Deploy staging: `scripts/deploy-staging.sh`.
3. Run smoke + integration tests against staging.
4. Validate health endpoint + one map/profile prediction flow.

## Production (target, not MVP)

- Apply Terraform (infrastructure/terraform), managed DB + object storage.
- Promote a **validated, registered** model from the model registry.
- Configure secrets via managed secret store.
- Enable monitoring/alerting (observability/).
- Deploy: `scripts/deploy-production.sh` (approval-gated).

## Guards

- No secrets in image layers or config (RULE 14).
- Applied migrations never edited (RULE 15).
- Model promoted through registry, not ad-hoc files (§55).
- Real-time/operational claims require latency verification (§129).

## Rollback

- Immutable, hashed model artifacts allow quick rollback via the registry.
- Immutable database migrations mean no destructive edits; new migrations for changes.