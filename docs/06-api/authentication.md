# Authentication

> Application authentication and credential boundaries.

## MVP

- The MVP scientific dashboard has **no user-facing login**.
- The only credentials are server-side Copernicus Marine credentials:
  `COPERNICUSMARINE_SERVICE_USERNAME` / `COPERNICUSMARINE_SERVICE_PASSWORD`
  (provided via server environment / secret manager; never in frontend code or Git).

## Boundaries (LOCKED)

- RULE 1: frontend never directly accesses Copernicus credentials.
- RULE 2: frontend never calls Copernicus directly.
- Only the backend integration layer (Copernicus client) uses the credentials.

## Future (post-MVP, UNRESOLVED)

- If multi-user auth/authorization is added, it must follow `security-architecture.md` and be
  reviewed by the security owner. No auth decisions are locked today.