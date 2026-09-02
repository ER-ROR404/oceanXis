# SECURITY.md

> OceanEmbed security expectations, secret handling, and vulnerability management.

## Security model (summary)

- Copernicus Marine is the primary external data provider. Credentials
  (`COPERNICUSMARINE_SERVICE_USERNAME` / `COPERNICUSMARINE_SERVICE_PASSWORD`)
  are **backend-only** and must never reach the frontend, Git history, logs,
  API responses, Docker image layers, or public configuration.
- The backend is the single trusted boundary that talks to Copernicus.
  The frontend never calls Copernicus directly.
- Secrets are supplied at runtime through environment variables / secret manager,
  never hard-coded.
- Applied database migrations are immutable (never edited).

## Secret handling rules

1. Never commit `.env` or any file containing real credentials.
2. Only `.env.example` with placeholders is committed.
3. Never log passwords, tokens, or dataset credentials.
4. Rotate exposed secrets immediately; report and review the codebase for similar issues.
5. Use server-side secret management for non-local environments.

## Reporting vulnerabilities

- Do **not** open a public issue for security vulnerabilities.
- Report privately to the repository maintainers before disclosure.
- Include: affected component, severity assessment, reproduction steps, and proposed fix.

## Vulnerability management

- Dependency updates are proposed via Dependabot (`.github/dependabot.yml`).
- CI runs dependency/secret scanning (`security.yml`).
- Critical or high findings block merge until remediated or explicitly waived with justification.

## Minimum controls before deployment

See `security/security-baseline.md`. At minimum:

- No secrets in code or build artifacts (verified with secret scanning).
- All external API calls go through the backend.
- Input validation at every system boundary.
- Health/readiness endpoints that do not trigger expensive external calls.
- Structured logging that excludes sensitive fields.

## Security contact

Maintain the contact in `.github/CODEOWNERS` as the security owner for this repository.