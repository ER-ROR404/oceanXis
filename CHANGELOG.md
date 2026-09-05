# CHANGELOG.md

All notable changes to OceanEmbed will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
uses Semantic Versioning. Releases are created through the `release.yml` workflow.

## [Unreleased]

### Added

- Repository knowledge and governance layer (non-code):
  - `AGENTS.md` — AI-agent operating rules, boundaries, and golden rules.
  - `SYSTEM_MEMORY_DUMP.md` — complete historical project memory for SIH26066.
  - `CONTRIBUTING.md`, `SECURITY.md`, `README.md`.
  - `docs/` — product, architecture (+ ADR-001..008), domain, data, ML, API, operations, decisions.
  - `contracts/` — API (OpenAPI + JSON schemas), data, and ML contracts.
  - `config/` — canonical regions, depths, variables, datasets, preprocessing, model, training configuration.
  - `.opencode/` — AI-agent control plane (project context, rules, workflows).
  - Repository skeleton for `backend/`, `ml/`, `data-engineering/`, `database/`, `frontend/`,
    `infrastructure/`, `model-registry/`, `experiments/`, `security/`, `observability/`.
  - CI workflow definitions (`.github/workflows/`) and `docker-compose*` skeletons.

### Not yet implemented

- All application/ML implementation code (backend, ml, data-engineering, frontend, database migrations).

## 2026-09-02 — Copernicus Marine data validation (Phase 1 pre-work)

### Added

- Live-verified ALL 7 surface input channels + GLORYS temperature target for Bay of Bengal & Arabian Sea
  via `copernicusmarine` `describe()` + `subset(dry_run=True)`. No big datasets downloaded.
- Confirmed train/validation/test split feasibility: **train 2018–2023 / validation 2024 / test 2025** —
  full 7-input + GLORYS matrix GREEN across all windows.
- Confirmed near-real-time production readiness for all 5 NRT surface inputs (data at 7-days-ago);
  flagged GLORYS as reanalysis-only (NOT NRT, ~1–2 mo latency).
- Identified ARGO validation path (raw GDAC profiles preferred; CORA-OA gridded fallback, subset-supported).
- `config/datasets.yaml`: replaced INVALID old candidate IDs with verified IDs and set `verified: true`.
- Docs updated: `docs/work-log/2026-09-02-copernicus-validation.md`, `docs/04-data/data-sources.md`,
  `docs/04-data/dataset-registry.md`, and added `NEXT_SESSION_HANDOFF.md` (session continuity).
- Deprecated invalid dataset IDs that were present from the original skeleton (see handoff).

### Verdict

- **Auth + API health:** PASS. **All 7 inputs + target:** VERIFIED (16/16 GREEN at 2024-06-15).
- **Split 2018–23/2024/2025:** AVAILABLE (all channels). **Production NRT inputs:** AVAILABLE.
- **GLORYS as live target:** CAVEAT (reanalysis latency) — open ADR decision (see handoff §Open items).