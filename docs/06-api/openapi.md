# OpenAPI Policy

> How the OpenAPI specification is generated and maintained.

## Policy

- `contracts/api/openapi.yaml` is the **authoritative** API contract.
- FastAPI auto-generates an OpenAPI schema from the application; this generated schema must be
  validated/kept in sync with the authoritative contract (RULE 6).
- Response schemas reference the JSON schemas under `contracts/api/` (ocean-map, ocean-profile,
  prediction, health, error).

## Maintenance

- Every interface change updates `contracts/api/openapi.yaml` AND the corresponding
  `contracts/api/*.schema.json` AND the backend Pydantic schemas together.
- `scripts/verify-contracts.py` (run in CI) checks the generated API schema against the contract.
- Human review required for `contracts/` changes (CODEOWNERS).