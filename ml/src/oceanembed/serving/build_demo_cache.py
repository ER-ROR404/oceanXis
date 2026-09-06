"""Offline demo cache builder (plan Step 2.3).

For each date in [start, end], runs InferenceService.predict and saves:
- ``<out>/<region>/<date>.npz`` — mu/log_var [15,H,W] float32 (NaN land)
- ``<out>/<region>/coordinates.json`` — lat/lon grid + canonical depths
- ``<out>/manifest.json`` — honest metadata (checkpoint epoch/val_loss,
  channel_status, masked_land_count, format_version)

The output feeds the backend's ``fallback_demo`` path when the model service
is down — the directory lives under ``artifacts/`` (gitignored). NaN land
round-trips; zero is never fabricated.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from oceanembed.losses.physics_constraints import CANONICAL_DEPTHS
from oceanembed.serving.service import InferenceService

FORMAT_VERSION = 1


def build_demo_cache(
    region_dir: str | Path,
    checkpoint_path: str | Path,
    cfg: dict,
    *,
    start: str,
    end: str,
    step_days: int = 7,
    out_dir: str | Path = "artifacts/demo_cache",
    region_id: str | None = None,
    trained_on: str = "2023-12-31",
) -> dict:
    """Build the demo cache for a region; returns the manifest dict.

    Dates inside the temporal-window boundary (first T-1 days) are skipped
    with a warning — ``predict`` legitimately refuses them, and crashing on
    known boundary dates would be a bug for a batch tool.
    """
    region_dir = Path(region_dir)
    if not (region_dir / "X.zarr").exists():
        raise FileNotFoundError(f"region tensor store not found: {region_dir} (no X.zarr)")

    service = InferenceService(region_dir=region_dir, cfg=cfg, checkpoint_path=checkpoint_path)
    service.load_model()

    available = service.available_dates()
    chosen = [d for d in available if start <= d <= end][::max(1, step_days)]

    region_id = (region_id or region_dir.name).lower()
    out = Path(out_dir) / region_id
    out.mkdir(parents=True, exist_ok=True)

    skipped: list[str] = []
    skipped_details: list[str] = []
    for date in chosen:
        try:
            mu, log_var, _ = service.predict(date)
        except ValueError as exc:
            skipped.append(date)
            skipped_details.append(f"{date}: {str(exc)[:100]}")
            continue
        np.savez(
            out / f"{date}.npz",
            mu=np.asarray(mu, dtype=np.float32),
            log_var=np.asarray(log_var, dtype=np.float32),
        )

    lats = np.asarray(service.lats)
    lons = np.asarray(service.lons)
    (out / "coordinates.json").write_text(
        json.dumps(
            {
                "region": region_id,
                "lat": [float(v) for v in lats],
                "lon": [float(v) for v in lons],
                "depths_m": list(CANONICAL_DEPTHS),
                "n_lat": int(lats.size),
                "n_lon": int(lons.size),
                "n_depths": int(service.dataset.n_depths),
            },
            indent=2,
        )
    )

    nested = (region_dir / "normalization_stats.json")
    channel_status = {}
    if nested.exists():
        stats = json.loads(nested.read_text())
        for key in sorted(stats):
            channel_status[key] = "available"
    if not channel_status:
        channel_status = {"unavailable": "normalization stats missing"}

    manifest = {
        "format_version": FORMAT_VERSION,
        "region": region_id,
        "model_version": "hybrid_v1",
        "checkpoint": str(Path(checkpoint_path).name),
        "epoch": service.ckpt.epoch,
        "val_loss": service.ckpt.val_loss,
        "trained_on": trained_on,
        "date_start": chosen[0] if chosen else None,
        "date_end": chosen[-1] if chosen else None,
        "n_dates": len(chosen) - len(skipped),
        "dates": [d for d in chosen if d not in skipped],
        "step_days": step_days,
        "n_lat": int(lats.size),
        "n_lon": int(lons.size),
        "grid": {"n_lat": int(lats.size), "n_lon": int(lons.size), "n_depths": int(service.dataset.n_depths)},
        "masked_land_count": int((service.mask != 1.0).sum()),
        "channel_status": channel_status,
        "skipped_dates": skipped_details,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    (Path(out_dir) / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def main() -> None:  # pragma: no cover - thin CLI
    parser = argparse.ArgumentParser(description="Build the offline demo cache")
    parser.add_argument("--region-dir", required=True, help="Region tensor store dir")
    parser.add_argument("--checkpoint", required=True, help="Trained checkpoint (best.pt)")
    parser.add_argument("--start", required=True, help="Inclusive start date YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="Inclusive end date YYYY-MM-DD")
    parser.add_argument("--step-days", type=int, default=7, help="Subsample stride in days")
    parser.add_argument("--out", default="artifacts/demo_cache", help="Cache root dir")
    parser.add_argument("--region", default=None, help="Region id (default: region dir name)")
    parser.add_argument("--trained-on", default="2023-12-31", help="Honesty metadata")
    parser.add_argument("--config", default="", help="Path to hybrid_v1.yaml (model block)")
    args = parser.parse_args()

    cfg: dict
    if args.config:
        import yaml

        with open(args.config) as f:
            cfg = dict(yaml.safe_load(f)["model"])
    else:
        from oceanembed.serving.server import DEFAULT_CFG

        cfg = dict(DEFAULT_CFG)

    manifest = build_demo_cache(
        region_dir=args.region_dir,
        checkpoint_path=args.checkpoint,
        cfg=cfg,
        start=args.start,
        end=args.end,
        step_days=args.step_days,
        out_dir=args.out,
        region_id=args.region,
        trained_on=args.trained_on,
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":  # pragma: no cover
    main()
