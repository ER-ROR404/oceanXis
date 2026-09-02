# contracts/

> **Versioned interface contracts.** These are the authoritative source of truth for every
> interface in OceanEmbed: API, data, and ML model contracts.
>
> Hierarchy: `AGENTS.md` → `SYSTEM_MEMORY_DUMP.md` → `docs/` → `contracts/` → implementation.
> If any interface changes, the relevant contract here **and** its schema consumers must change
> together (see `docs/06-api/openapi.md`). Human review required for contract changes (CODEOWNERS).

## Structure

```text
contracts/
├── api/          — HTTP API contract
│   ├── openapi.yaml                  # authoritative OpenAPI spec
│   ├── ocean-map.schema.json        # /ocean/map response
│   ├── ocean-profile.schema.json    # /ocean/profile response
│   ├── prediction.schema.json       # prediction payload envelope
│   ├── health.schema.json           # health check response
│   └── error.schema.json            # standardized error envelope
├── data/         — dataset / sample / provenance contracts
│   ├── surface-input.schema.json    # 7-channel surface X
│   ├── training-sample.schema.json  # X/Y/mask/metadata bundle
│   ├── dataset-metadata.schema.json # registry entries
│   └── provenance.schema.json       # lineage records
└── ml/          — model I/O and artifact contracts
    ├── model-input.schema.json      # canonical model input
    ├── model-output.schema.json     # [B,15,H,W] temperature output
    ├── checkpoint-manifest.schema.json
    └── evaluation-result.schema.json
```

## Versioning

- Contracts are versioned. Breaking changes bump a **major** contract version and are recorded in
  `docs/08-decisions/decision-log.md` (ADR required for architectural changes).
- `CHANGELOG.md` tracks contract version changes.

## Validation

- `scripts/verify-contracts.py` (CI) validates configs, manifests, and API responses against these
  schemas. Behavior change without a contract update = CI failure.

## Golden rules enforced here

- RULE 6 — API responses conform to contracts.
- RULE 20 — channel/depth ordering changes require contract updates.
- RULE 5 — ML inference consumes the canonical model-input contract.
- Golden Rule 17/18 — channel and depth ordering preserved.