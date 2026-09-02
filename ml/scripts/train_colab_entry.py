#!/usr/bin/env python3
"""Colab-safe training entry point (Phase 0 scaffold, ADR-009).

Single thin entry usable on Google Colab (GPU) AND locally (CPU). Paths come
from CLI args / environment only — no hardcoded absolute paths, no local-only
imports (OPENCODE_SDL_CONTRACT.md Phase 4).

Phase status:
- `--check` works TODAY: validates python/torch/config/artifacts so the Colab
  notebook (colab/oceanembed_training.ipynb) has a meaningful preflight gate.
- The actual training call is wired in Phase 3 (Stage 1 CNN) / Phase 4
  (Stage 2 CNN+ConvLSTM, ADR-010) once `oceanembed.training` exists.

Usage:
    python ml/scripts/train_colab_entry.py --config ml/configs/cnn_v1.yaml \
        --artifacts-dir <writable-dir> [--check] [--gpu]
"""

from __future__ import annotations

import argparse
import os
import pathlib
import sys


def _load_yaml(path: pathlib.Path) -> dict:
    """Load a YAML config, degrading gracefully if pyyaml is unavailable."""
    try:
        import yaml  # pyyaml (declared in ml/pyproject.toml / colab/requirements.txt)
    except ImportError as exc:  # pragma: no cover - defensive for bare environments
        raise SystemExit(
            "pyyaml is not installed (found via `import yaml`). Install ml deps first:\n"
            "  pip install -r colab/requirements.txt   (Colab, ADR-009)\n"
            "  pip install -e './ml[dev]'              (local)"
        ) from exc
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise SystemExit(f"{path}: config must be a YAML mapping, got {type(data).__name__}")
    return data


def run_preflight(config: pathlib.Path, artifacts_dir: pathlib.Path, require_gpu: bool) -> None:
    """Validate the environment + config so a Colab run fails fast, not mid-epoch."""
    checks: list[tuple[str, bool, str]] = []

    ok_py = sys.version_info >= (3, 11)
    checks.append(("python >= 3.11", ok_py, f"found {sys.version.split()[0]}"))

    try:
        import torch  # noqa: F401
        torch_ok, torch_msg = True, torch.__version__
    except ImportError:
        torch_ok, torch_msg = False, "not importable (install colab/requirements.txt)"
    checks.append(("torch importable", torch_ok, torch_msg))

    if ok_py and torch_ok:
        import torch
        cuda_ok = torch.cuda.is_available()
        if require_gpu and not cuda_ok:
            checks.append(("CUDA available", False, "required (--gpu) but torch.cuda.is_available() is False"))
        else:
            checks.append(("CUDA available", cuda_ok, str(torch.cuda.get_device_name(0)) if cuda_ok else "CPU mode"))
    else:
        checks.append(("CUDA available", False, "skipped (torch/python gate failed)"))

    # Config must exist and declare the locked model/architecture keys (Phase 0 gate).
    try:
        cfg = _load_yaml(config)
        has_model = isinstance(cfg.get("model"), dict) and "architecture" in cfg["model"]
        checks.append(("config loads + declares model.architecture", has_model, str(config)))
        if has_model:
            checks.append(("architecture", True, cfg["model"]["architecture"]))
    except SystemExit as exc:
        checks.append(("config loads", False, str(exc)))

    # Artifacts dir must be writable (Drive on Colab; RULE 13 keeps checkpoints out of Git).
    try:
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        probe = artifacts_dir / ".oceanembed_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        checks.append(("artifacts dir writable", True, str(artifacts_dir)))
    except OSError as exc:
        checks.append(("artifacts dir writable", False, f"{artifacts_dir}: {exc}"))

    print("oceanembed train entry — preflight")
    print("===================================")
    failed = False
    for name, ok, detail in checks:
        mark = "PASS" if ok else "FAIL"
        if not ok:
            failed = True
        print(f"[{mark}] {name:28s} {detail}")
    print("===================================")
    if failed:
        raise SystemExit(3)  # distinct code: env/config gate failed
    print("Preflight OK. Real training is wired in Phase 3 (CNN) / Phase 4 (CNN+ConvLSTM).")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=pathlib.Path, help="path to ml/configs/<experiment>.yaml")
    parser.add_argument("--artifacts-dir", required=True, type=pathlib.Path, help="writable dir for checkpoints/stats (Drive on Colab)")
    parser.add_argument("--check", action="store_true", help="preflight only (env/config/artifacts), no training")
    parser.add_argument("--gpu", action="store_true", help="assert CUDA is available (use on Colab)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.config.exists():
        print(f"config not found: {args.config}")
        return 2
    try:
        run_preflight(args.config, args.artifacts_dir, require_gpu=args.gpu)
    except SystemExit as exc:
        return int(exc.code or 1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())