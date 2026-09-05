#!/usr/bin/env python3
"""Colab-safe training entry point (ADR-009).

Single thin entry usable on Google Colab (GPU) AND locally (CPU). Paths come
from CLI args / environment only — no hardcoded absolute paths, no local-only
imports (OPENCODE_SDL_CONTRACT.md Phase 4).

Modes:
- `--check` (default when flag present): preflight only — validates
  python/torch/config/artifacts so the Colab notebook has a meaningful gate.
- without `--check`: REAL training. Requires `--data-dir` pointing at the
  harmonized tensors (region dir containing X.zarr / Y.zarr / mask.zarr).

Usage:
    python ml/scripts/train_colab_entry.py --config ml/configs/hybrid_v1.yaml \
        --data-dir data/tensors/bay_of_bengal \
        --artifacts-dir <writable-dir> [--gpu]
"""

from __future__ import annotations

import argparse
import json
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
            # CPU mode is a valid target unless --gpu is asserted (ADR-009: Colab is GPU, local is CPU)
            checks.append(("CUDA available", True, str(torch.cuda.get_device_name(0)) if cuda_ok else "CPU mode (OK, --gpu not asserted)"))
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


def run_training(
    config: pathlib.Path,
    data_dir: pathlib.Path,
    artifacts_dir: pathlib.Path,
    device: str | None = None,
) -> tuple[dict[str, list[float]], dict[str, float], str]:
    """Run the real OceanEmbedNet training loop.

    Args:
        config: Experiment YAML config (model/data/training keys).
        data_dir: Region dir containing X.zarr, Y.zarr, mask.zarr (+ normalization_stats.json).
        artifacts_dir: Writable output dir for checkpoints + run manifest.
        device: Optional forced device ('cuda' / 'cpu'); auto-detected if None.

    Returns:
        (history, metrics, status) tuple for tests and the run manifest.

    Raises:
        FileNotFoundError: If config or data_dir tensor store is missing.
    """
    cfg = _load_yaml(config)

    import torch

    # Resolve device: CLI > CUDA availability > CPU
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    # ── Import oceanembed (installed via ml[dev], or sys.path on Colab) ──
    try:
        from oceanembed.data.dataset import create_dataloaders
        from oceanembed.models.reconstruction_net import OceanEmbedNet
        from oceanembed.training.trainer import Trainer
    except ImportError as exc:
        raise SystemExit(
            "oceanembed package not importable. Install it first:\n"
            "  pip install -e './ml[dev]'        (local)\n"
            "  sys.path.insert(0, '/content/oceanembed/ml/src')  (Colab)\n"
        ) from exc

    data_dir = pathlib.Path(data_dir)
    for store in ("X.zarr", "Y.zarr", "mask.zarr"):
        if not (data_dir / store).exists():
            raise FileNotFoundError(f"Missing tensor store '{store}' in {data_dir}")

    artifacts_dir = pathlib.Path(artifacts_dir)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    model_cfg = cfg.get("model", {})
    data_cfg = cfg.get("data", {})
    training_cfg = cfg.get("training", {})

    # Seed for reproducibility (deterministic training policy)
    seed = int(training_cfg.get("seed", 42))
    import random
    import numpy as np
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    # ── Build dataloaders ──
    temporal_window = int(data_cfg.get("temporal_window", 7))
    batch_size = int(data_cfg.get("batch_size", 8))
    val_fraction = float(data_cfg.get("val_fraction", 0.2))

    train_loader, val_loader = create_dataloaders(
        region_dir=data_dir,
        temporal_window=temporal_window,
        batch_size=batch_size,
        normalize=True,
        val_fraction=val_fraction,
        num_workers=0,
    )

    # ── Build model ──
    model = OceanEmbedNet(
        in_channels=int(model_cfg.get("in_channels", 7)),
        out_channels=int(model_cfg.get("out_channels", 15)),
        convlstm_hidden=int(model_cfg.get("convlstm_hidden", 128)),
        convlstm_layers=int(model_cfg.get("convlstm_layers", 1)),
    )
    model.to(device)

    # ── Trainer ──
    epochs = int(training_cfg.get("epochs", 100))
    lr = float(training_cfg.get("lr", 1e-3))
    patience = int(training_cfg.get("early_stopping_patience", 15))

    trainer = Trainer(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        lr=lr,
        checkpoint_dir=artifacts_dir,
        early_stopping_patience=patience,
    )

    print(f"[train] device={device} epochs={epochs} lr={lr} T={temporal_window} "
          f"batch={batch_size} train_batches={len(train_loader)} val_batches={len(val_loader)}")
    history = trainer.train(epochs=epochs)

    # Final validation metrics for the manifest
    val_loss, metrics = trainer.validate()
    status = "complete"

    # ── Write run manifest (metrics + provenance, NOT checkpoints — RULE 13) ──
    manifest = {
        "experiment": cfg.get("experiment", {}).get("name", "unknown"),
        "model": {
            "architecture": model_cfg.get("architecture", "oceanembed_net"),
            "in_channels": model_cfg.get("in_channels", 7),
            "out_channels": model_cfg.get("out_channels", 15),
        },
        "data": {
            "region": data_dir.name,
            "temporal_window": temporal_window,
            "n_train_samples": len(train_loader.dataset),
            "n_val_samples": len(val_loader.dataset),
        },
        "training": {"epochs_run": len(history["train_loss"]), "lr": lr, "device": device},
        "metrics": {"val_nll": val_loss, **metrics},
        "best_val_loss": trainer.early_stopping.best_loss,
        "status": status,
    }
    manifest_path = artifacts_dir / "run_manifest.json"
    with open(manifest_path, "w") as fh:
        json.dump(manifest, fh, indent=2)
    print(f"[train] run manifest written: {manifest_path}")
    print(f"[train] status={status} best_val_loss={trainer.early_stopping.best_loss:.6f}")

    return history, metrics, status


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=pathlib.Path, help="path to ml/configs/<experiment>.yaml")
    parser.add_argument("--artifacts-dir", required=True, type=pathlib.Path, help="writable dir for checkpoints/stats (Drive on Colab)")
    parser.add_argument("--data-dir", type=pathlib.Path, default=None, help="region dir with X.zarr/Y.zarr/mask.zarr (required for real training)")
    parser.add_argument("--check", action="store_true", help="preflight only (env/config/artifacts), no training")
    parser.add_argument("--gpu", action="store_true", help="assert CUDA is available (use on Colab)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.config.exists():
        print(f"config not found: {args.config}")
        return 2
    try:
        if args.check:
            run_preflight(args.config, args.artifacts_dir, require_gpu=args.gpu)
            return 0
        if args.data_dir is None:
            print("error: --data-dir is required for real training (use --check for preflight only)")
            return 2
        # Real training path
        device = "cuda" if args.gpu else None  # --gpu asserts CUDA; otherwise auto
        run_training(
            config=args.config,
            data_dir=args.data_dir,
            artifacts_dir=args.artifacts_dir,
            device=device,
        )
        return 0
    except SystemExit as exc:
        return int(exc.code or 1)
    except FileNotFoundError as exc:
        print(f"error: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())