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

- Copernicus `describe()` connection proof.
- Dataset verification matrix (dataset IDs must be verified, not guessed).
- All application/ML implementation code (backend, ml, data-engineering, frontend, database migrations).