# Security Architecture

> Reference: SYSTEM_MEMORY_DUMP.md §45, §62, §77; SECURITY.md.

## Trust boundaries

```text
  untrusted                                          trusted
 ┌──────────────┐      ┌──────────────────────────────────────────────┐
 │    Browser   │ ───► │  FastAPI backend                             │
 │ React UI     │      │  • validates all input                       │
 └──────────────┘      │  • sole owner of Copernicus credentials      │
                       │  • only component that calls Copernicus      │
                       └───────────────┬──────────────────────────────┘
                                       │ HTTPS
                                       ▼
                            Copernicus Marine Toolbox
```

- The backend is the **single trusted boundary** that talks to Copernicus Marine.
- The frontend must never directly access Copernicus credentials (RULE 1) or call Copernicus
  directly (RULE 2).

## Secret boundaries

| Secret | Where it may live | Where it must never live |
|--------|-------------------|--------------------------|
| `COPERNICUSMARINE_SERVICE_USERNAME` / `PASSWORD` | Server-side env vars / secret manager / local `.env` (git-ignored) | Frontend JS, Git history, logs, API responses, Docker image layers, public config |

## Application security measures

1. **Input validation** — every API boundary validates region, date, depth, and grid cell.
2. **Error handling** — standardized errors (see `contracts/api/error.schema.json`) that never leak
   credentials or internal dataset details.
3. **Health checks** — never trigger expensive external calls.
4. **Structured logging** — excludes passwords, tokens, and credentials (§121).
5. **API responses** — conform to `contracts/`; never expose raw provider secrets (§64).

## Data-plane security (config/datasets)

- Dataset IDs are verified via `copernicusmarine.describe()` (RULE 7); no hard-coded unverified IDs.
- Provenance recorded per dataset; no silent substitution of dataset versions.

## Supply-chain

- Dependency pinning per module (`pyproject.toml`, lock files).
- CI scanning: `security.yml` (dependency audit + gitleaks + npm audit).
- Applied database migrations are immutable (RULE 15).

## MVP threat note

For the 36-hour MVP there is no user-facing authentication — the product is a scientific dashboard.
If multi-user auth is added later, it must follow the boundaries in this document and be reviewed by
the security owner (`security-reviewer` agent / `@oceanembed/security`).