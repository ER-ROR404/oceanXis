#!/usr/bin/env python3
"""ARGO independent validation entry point (evaluation-policy LOCKED, RULE 9).

Scores a trained checkpoint against ARGO float profiles: predictions for each
profile's (date, lat, lon) on the region grid are compared against the float's
measured temperature interpolated to the 15 canonical depths. Writes an
argo_report.json (metrics + traceable per-profile records). Never fabricates:
off-domain/land/unmatched profiles are reported with n_matched / n_unmatched
and per-profile reasons.

Usage:
    python ml/scripts/evaluate_argo.py \
        --config ml/configs/hybrid_v1.yaml \
        --checkpoint <artifacts>/best.pt \
        --data-dir <region-dir> \
        --argo-profiles <profiles>.json \
        --artifacts-dir <artifacts> [--gpu]
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys


def _load_yaml(path: pathlib.Path) -> dict:
    try:
        import yaml  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - defensive
        raise SystemExit("pyyaml required: pip install -r colab/requirements.txt") from exc
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise SystemExit(f"{path}: config must be a YAML mapping")
    return data


def load_profiles(profile_path: pathlib.Path) -> list:
    """Load ARGO profiles from the harmonized JSON store.

    Format (produced by the data-engineering ARGO flow from raw GDAC):
    [{"source_id": "6902914_0123", "date": "2024-01-08T13:00:00",
      "lat": 8.5, "lon": 88.2,
      "depths_m": [0.0, 5.1, ...], "temps_c": [28.3, 28.2, ...]}, ...]
    """
    from oceanembed.evaluation.argo import ArgoProfile  # noqa: PLC0415

    with profile_path.open("r", encoding="utf-8") as fh:
        raw = json.load(fh)
    profiles: list[ArgoProfile] = []
    for entry in raw:
        profiles.append(
            ArgoProfile(
                source_id=str(entry["source_id"]),
                date=np_datetime(entry["date"]),
                lat=float(entry["lat"]),
                lon=float(entry["lon"]),
                depths_m=entry["depths_m"],
                temps_c=entry["temps_c"],
            )
        )
    return profiles


def np_datetime(value) -> object:
    import numpy as np  # noqa: PLC0415

    return np.datetime64(value)


def run_argo_validation(
    config_path: pathlib.Path,
    checkpoint_path: pathlib.Path,
    data_dir: pathlib.Path,
    argo_profiles_path: pathlib.Path,
    artifacts_dir: pathlib.Path,
    device: str | None = None,
) -> dict:
    """Run ARGO validation end-to-end; returns the report (also written out).

    Raises:
        FileNotFoundError: If the checkpoint, region store, or profile file is
            missing (fail fast instead of producing an empty report).
    """
    import torch  # noqa: PLC0415

    cfg = _load_yaml(config_path)
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"checkpoint not found: {checkpoint_path}")
    if not (data_dir / "X.zarr").exists() or not (data_dir / "mask.zarr").exists():
        raise FileNotFoundError(f"tensor store incomplete in {data_dir}")
    if not argo_profiles_path.exists():
        raise FileNotFoundError(f"argo profiles not found: {argo_profiles_path}")

    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    from oceanembed.data.dataset import OceanEmbedDataset  # noqa: PLC0415
    from oceanembed.evaluation.argo import ArgoValidator  # noqa: PLC0415
    from oceanembed.models.reconstruction_net import OceanEmbedNet  # noqa: PLC0415

    data_cfg = cfg.get("data", {})
    model_cfg = cfg.get("model", {})

    dataset = OceanEmbedDataset(
        region_dir=data_dir,
        temporal_window=int(data_cfg.get("temporal_window", 7)),
        normalize=True,
    )

    model = OceanEmbedNet(
        in_channels=int(model_cfg.get("in_channels", 7)),
        out_channels=int(model_cfg.get("out_channels", 15)),
        convlstm_hidden=int(model_cfg.get("convlstm_hidden", 128)),
        convlstm_layers=int(model_cfg.get("convlstm_layers", 1)),
    )

    ckpt = torch.load(checkpoint_path, map_location="cpu")
    state = ckpt.get("best_model_state") or ckpt.get("model_state_dict")
    if state is None:
        raise ValueError(f"{checkpoint_path}: no best_model_state/model_state_dict found")
    model.load_state_dict(state)

    profiles = load_profiles(argo_profiles_path)
    report, records = ArgoValidator(dataset, model, device=device).validate(profiles)

    payload = {
        "validation": "argo",
        "checkpoint": str(checkpoint_path),
        "config": str(config_path),
        "data_dir": str(data_dir),
        "argo_profiles": str(argo_profiles_path),
        "n_profiles": int(report["n_profiles"]),
        "n_matched": int(report["n_matched"]),
        "n_unmatched": int(report["n_unmatched"]),
        "metrics": {k: round(v, 4) if isinstance(v, float) and v == v else v for k, v in report.items()},
        "profiles": records,
    }

    artifacts_dir.mkdir(parents=True, exist_ok=True)
    out_path = artifacts_dir / "argo_report.json"
    out_path.write_text(json.dumps(payload, indent=2))
    _print_summary(payload)
    return payload


def _print_summary(payload: dict) -> None:
    m = payload["metrics"]
    print(f"[argo] profiles: {payload['n_matched']}/{payload['n_profiles']} matched "
          f"({payload['n_unmatched']} unmatched)")
    print(f"[argo] overall RMSE={m.get('rmse')}  bias={m.get('bias')}  corr={m.get('corr')}")
    print("[argo] report written to artifacts/argo_report.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ARGO independent validation")
    parser.add_argument("--config", required=True, type=pathlib.Path)
    parser.add_argument("--checkpoint", required=True, type=pathlib.Path)
    parser.add_argument("--data-dir", required=True, type=pathlib.Path)
    parser.add_argument("--argo-profiles", required=True, type=pathlib.Path)
    parser.add_argument("--artifacts-dir", required=True, type=pathlib.Path)
    parser.add_argument("--gpu", action="store_true")
    args = parser.parse_args(argv)

    try:
        run_argo_validation(
            config_path=args.config,
            checkpoint_path=args.checkpoint,
            data_dir=args.data_dir,
            argo_profiles_path=args.argo_profiles,
            artifacts_dir=args.artifacts_dir,
            device="cuda" if args.gpu else None,
        )
    except Exception as exc:  # pragma: no cover - CLI boundary
        print(f"[argo] ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
