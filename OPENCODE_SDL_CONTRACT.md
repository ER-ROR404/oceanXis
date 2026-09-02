# OpenCode SDLC Compliance & Code Generation Contract

> This document defines the mandatory software development lifecycle (SDLC) process
> that the OpenCode agent must follow for every task in this repository.
> It supplements `AGENTS.md` with phase-specific enforcement rules.

---

## PHASE 1: REQUIREMENTS & FEASIBILITY AUDIT (Planning)

1. **Context Verification**: Before writing or modifying a line of code, the agent MUST parse `SYSTEM_MEMORY_DUMP.md`.
2. **Alignment Check**: The agent must verify that the target task matches the established input/output data structures and business logic.
3. **Intent Safeguard**: If details are missing, the agent must halt execution and prompt the user instead of guessing parameters.

---

## PHASE 2: SECURE DATA & INTERFACE ARCHITECTURE (Design)

1. **Zero Secret Commits**: Hardcoding passwords, API tokens, cryptographic keys, or DB connection strings is strictly prohibited.
2. **Dynamic Configuration**: All configuration settings must be loaded dynamically from environment variables (`.env`) via a validated config module.
3. **Schema Isolation**: Frontend and Backend layers must use rigid, explicitly typed schemas (e.g., Pydantic models or TypeScript interfaces) to enforce structural contracts.
4. **Data Security**: Large datasets (`data/`) and machine learning weights (`.pt`, `.h5`) must be completely isolated from Git version tracking using a strict `.gitignore`.

---

## PHASE 3: COMPREHENSIVE IMPLEMENTATION (Construction)

1. **Zero Code Truncation**: The agent is forbidden from generating code blocks containing `# TODO: implement this`, placeholders, or truncated logic.
2. **Production Standardization**: All code modules must feature robust try-except error handling, structured system logging (`logging`), clear type hints, and code comments explaining the "why" behind complex formulas.

---

## PHASE 4: STABILITY VERIFICATION (Testing & MLOps)

1. **Local Validation**: Every code generation run must include unit tests (e.g., using `pytest` or `Jest`) to verify component stability.
2. **Pipeline Safety**: Local code changes must maintain absolute compatibility with the Google Colab execution runner to ensure remote training runs do not crash due to missing functions or imports.
