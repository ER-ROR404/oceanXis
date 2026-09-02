# Incident Response

> Response procedures for service/data/model failures.

## Severity

| Sev | Definition | Example |
|-----|-----------|---------|
| SEV1 | Demo/application unusable; fabricated data risk | inference crash, data pipeline silent corruption |
| SEV2 | Feature degraded but demo operable | a channel unavailable, cached fallback serving stale data |
| SEV3 | Minor / cosmetic | dashboard metric lag |

## Response

1. **Detect** — health checks, monitoring/alerts, manual check.
2. **Assess** — identify affected component (data / model / backend / infra) and severity.
3. **Contain**:
   - data failure → serve cached data, mark cached, never zero-fill (§122).
   - inference failure → clear error; never display fabricated values.
   - infra failure → restart/roll back service.
4. **Recover** — restore from backup/manifests (`backup-and-recovery.md`), point registry at known
   weights, re-download regional data if needed.
5. **Analyze** — document root cause; update docs/ADR if behavior/architecture must change.

## Key rules

- Never compromise scientific honesty during an incident (Golden Rules 4, 21).
- Health checks never trigger expensive external calls (§123).
- Logs exclude credentials (§121).

## Post-incident

- Add/update a regression test.
- Update `CHANGELOG.md`.
- If architecture or interface behavior changed, update the relevant contract + ADR.