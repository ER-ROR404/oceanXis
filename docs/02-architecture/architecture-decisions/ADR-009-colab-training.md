# ADR-009: Google Colab as the GPU training host

- **Status:** Accepted (team decision)
- **Date:** 2026-09-02 (SIH26066 build)
- **Owner:** ml

## Context

OceanEmbed is a software-only submission: no hardware budget. Training the ML models
(SYSTEM_MEMORY_DUMP §9) benefits strongly from a GPU, but:

- The local development machine has no usable GPU (CPU only, Python 3.10 < the project's
  required 3.11 — local runs are CPU-based correctness/test runs only).
- The repository contains an `infrastructure/cloud-training/` skeleton, but **no cloud-training
  job infrastructure is provisioned** (no budget, and the SIH is time-boxed).
- The `ml/` codebase must therefore run **both** locally (CPU, fast iteration + tests) **and**
  on a free, ephemeral GPU host for real training runs.

**Google Colab** provides a free Tesla T4 (16 GB VRAM) with PyTorch/CUDA pre-installed, a Jupyter
notebook surface, and Google Drive integration for artifact storage — no provisioning, no budget.

## Decision

**Use Google Colab as the GPU training host.** GitHub is the sync layer between local work
(OpenCode-authored code) and Colab runs:

1. All code/config lives in the repo (`ml/src`, `ml/configs`, `ml/scripts`, `colab/`), authored
   locally and pushed to GitHub (main branch, normal PR convention).
2. A committed notebook `colab/oceanembed_training.ipynb` is the **single entry point** for
   training runs on Colab:
   - clones/pulls the repo (token supplied **at runtime** via Colab secrets / `getpass` — never
     committed, RULE 14),
   - mounts Drive for tensors + checkpoints,
   - installs `colab/requirements.txt` (mirrors `ml/pyproject.toml` + GPU torch),
   - runs `ml/scripts/train_colab_entry.py --config <experiment>.yaml` with config paths passed
     via environment/args (no hardcoded absolute paths, `OPENCODE_SDL_CONTRACT.md` Phase 4).
3. **Checkpoints, datasets, and large artifacts stay OUT of Git** (RULE 12/13):
   - checkpoints → Drive (`artifacts/...`),
   - tensors → Drive / object storage,
   - only small **manifests + metrics** (JSON/YAML) are pushed back to GitHub via a normal branch
     (Phase 5: `experiments/reports/`, `model-registry/registry.yaml`).
4. The existing `infrastructure/cloud-training/` skeleton is **retained, not deleted** — it remains
   a documented future option if the team later needs persistent GPU capacity (no code depends on
   it; `docs/07-operations/training-operations.md` will document both paths).

## Alternatives considered

- **Local CPU training** — guaranteed to work (test gate) but too slow for real runs/hyperparameter
  work; GPU not available.
- **Paid cloud training (AWS/GCP/custom job infra)** — not provisioned, no budget, time-boxed; the
  `infrastructure/cloud-training/` skeleton remains for later.
- **Kaggle/AWS Studio/etc.** — viable but Colab was chosen for zero provisioning + existing Google
  account + Drive integration.

## Consequences

- `colab/oceanembed_training.ipynb` + `colab/requirements.txt` (committed).
- `ml/scripts/train_colab_entry.py` — thin, Colab-safe entry (config via args/env only).
- Every `ml` module must import cleanly with **only** `colab/requirements.txt` installed
  (Colab-safety test gate, plan §14).
- Training is interruptible (Colab session timeouts/quotas): checkpoints every epoch, resumable
  configs, artifacts writable to Drive.
- Determinism: GPU runs pin seeds (RULE in `reproducibility.py`); documented caveat that
  non-deterministic kernels may cause small run-to-run variance (logs record it, not eliminated).
- The backend (RULE 3) never sees training code; it serves only an **approved checkpoint** from the
  model registry.
- `experiment_template.yaml` hardware field: `cpu | colab-gpu` (cloud-training job = future option).

## References

- AGENTS.md environment isolation; RULE 12/13/14 (no datasets/checkpoints/secrets in Git).
- OPENCODE_SDL_CONTRACT.md Phase 4 (Colab compatibility of all entry points).
- docs/07-operations/training-operations.md (to be updated with the Colab runbook).
- ADR-003 (PyTorch), ADR-010 (CNN + ConvLSTM hybrid; trained on Colab).