#!/usr/bin/env python3
"""Acquire ARGO float profiles for a region's validation period (RULE 9).

Turns a region's tensor store + the Argo GDAC global index into the
harmonized profiles.json store that ml/scripts/evaluate_argo.py consumes.
Profile dates are restricted to the temporal validation window computed from
the tensor store itself (mirrors the training split) — the training period is
never included, honoring the evaluation-policy gate.

Zero-network mode: pass a local index copy via --index-file and an already
populated GDAC cache via --gdac-cache. With --download the index and any
missing profile NetCDFs are fetched from the GDAC root.

Example (offline, after pre-downloading):
    python data-engineering/scripts/acquire_argo.py \
        --region-id bay_of_bengal \
        --regions-yaml config/regions.yaml \
        --tensor-store data/tensors/bay_of_bengal \
        --index-file /tmp/ar_index_global_prof.txt \
        --gdac-cache /tmp/argo_gdac \
        --out data/argo/profiles.json

Exit codes: 0 = OK, 1 = error, 2 = no ARGO profiles in the validation window.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from oceanembed_data.argo_acquire import (  # noqa: E402
    compute_validation_window,
    load_gdac_files,
    load_time_index,
    parse_index,
    select_rows,
    write_profiles_json,
)
from oceanembed_data.regions import RegionRegistry  # noqa: E402

DEFAULT_GDAC_ROOT = "https://data-argo.ifremer.fr/argo"
INDEX_NAME = "ar_index_global_prof.txt"


def fetch(url: str, dest: Path, timeout: int = 60) -> None:
    """Download url to dest; no-op if dest already exists."""
    if dest.exists():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(url, timeout=timeout) as resp, open(dest, "wb") as out:
        while True:
            chunk = resp.read(65536)
            if not chunk:
                break
            out.write(chunk)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region-id", required=True)
    parser.add_argument("--regions-yaml", required=True, type=Path)
    parser.add_argument("--tensor-store", required=True, type=Path)
    parser.add_argument("--gdac-cache", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--index-file", type=Path, default=None)
    parser.add_argument("--gdac-root", default=DEFAULT_GDAC_ROOT)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--temporal-window", type=int, default=7)
    parser.add_argument("--val-fraction", type=float, default=0.2)
    args = parser.parse_args(argv)

    try:
        registry = RegionRegistry.from_yaml(args.regions_yaml)
        bounds = registry.get(args.region_id)
    except FileNotFoundError as exc:
        print(f"[argo-acquire] ERROR: {exc}", file=sys.stderr)
        return 1
    except KeyError as exc:
        print(f"[argo-acquire] ERROR: {exc}", file=sys.stderr)
        return 1

    try:
        time_values = load_time_index(args.tensor_store)
    except Exception as exc:
        print(
            f"[argo-acquire] ERROR: cannot read time axis from "
            f"{args.tensor_store}/X.zarr: {exc}",
            file=sys.stderr,
        )
        return 1

    val_start, val_end = compute_validation_window(
        time_values,
        temporal_window=args.temporal_window,
        val_fraction=args.val_fraction,
    )

    # --- index ---------------------------------------------------------
    if args.index_file is None:
        if not args.download:
            print(
                "[argo-acquire] ERROR: --index-file required unless --download",
                file=sys.stderr,
            )
            return 1
        args.index_file = args.gdac_cache / INDEX_NAME
        fetch(f"{args.gdac_root.rstrip('/')}/{INDEX_NAME}", args.index_file)
    text = args.index_file.read_text(encoding="utf-8", errors="replace")
    rows = parse_index(text)
    selected = select_rows(
        rows,
        lon_min=bounds.lon_min,
        lon_max=bounds.lon_max,
        lat_min=bounds.lat_min,
        lat_max=bounds.lat_max,
        min_date=val_start,
        max_date=val_end,
    )
    print(
        f"[argo-acquire] index: {len(rows)} rows -> {len(selected)} in "
        f"{bounds} within {val_start}..{val_end}"
    )
    if not selected:
        print(
            "[argo-acquire] ERROR: zero ARGO profiles in the validation window",
            file=sys.stderr,
        )
        return 2

    # --- profile files ---------------------------------------------------
    if args.download:
        for row in selected:
            url = f"{args.gdac_root.rstrip('/')}/{row.file}"
            fetch(url, args.gdac_cache / row.file)
            print(f"[argo-acquire] fetched {row.file}")

    entries = load_gdac_files(args.gdac_cache, selected)
    if not entries:
        print(
            "[argo-acquire] ERROR: no usable ARGO profiles after parsing "
            "(all missing or QC-rejected)",
            file=sys.stderr,
        )
        return 2

    provenance = {
        "instrument": "argo_gdac",
        "region_id": bounds.id,
        "bounds": bounds.as_copernicus_bbox(),
        "validation_window": {"start": val_start.isoformat(), "end": val_end.isoformat()},
        "temporal_window": args.temporal_window,
        "val_fraction": args.val_fraction,
        "index_source": str(args.index_file),
        "gdac_root": args.gdac_root,
        "n_index_rows": len(rows),
        "n_selected": len(selected),
        "n_profiles": len(entries),
        "generated_at": datetime.now(UTC).isoformat(),
    }
    write_profiles_json(entries, args.out, provenance)
    print(
        f"[argo-acquire] wrote {len(entries)} profiles to {args.out}\n"
        "next: python ml/scripts/evaluate_argo.py "
        f"--config <cfg> --checkpoint <artifacts>/best.pt "
        f"--data-dir {args.tensor_store} --argo-profiles {args.out} "
        "--artifacts-dir <artifacts>"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
