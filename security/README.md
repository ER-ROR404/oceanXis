# security/

**OceanEmbed security architecture and policies.**

```text
secret-policy.md          what is a secret + where it may live
credential-policy.md      Copernicus / cloud / DB credential handling (backend-only, server-side)
dependency-policy.md      pinning + vulnerability remediation
security-baseline.md      minimum security controls for deployment
```

Architecture: `docs/02-architecture/security-architecture.md`.

## Enforcement

- No secrets in Git (RULE 14) — enforced by `.gitignore`, `gitleaks` (security scan), and review.
- Frontend never sees Copernicus credentials (RULE 1).
- Every endpoint rate-limited, input-validated, error messages non-leaky (see SECURITY.md).

> **Pre-build stage:** policy docs will be filled during coding; scaffolding present.