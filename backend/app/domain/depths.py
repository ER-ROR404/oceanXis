"""Canonical output depths from config/depths.yaml (LOCKED ordering, RULE 20)."""

from __future__ import annotations

from pathlib import Path

import yaml

_DEPTHS_PATH = Path(__file__).resolve().parents[3] / "config" / "depths.yaml"

with open(_DEPTHS_PATH) as _f:
    _DEPTHS_CFG = yaml.safe_load(_f)

CANONICAL_DEPTHS: tuple[int, ...] = tuple(int(d) for d in _DEPTHS_CFG["output_depths_m"])

if len(CANONICAL_DEPTHS) != _DEPTHS_CFG["output_channels"]:
    raise RuntimeError(
        f"config/depths.yaml inconsistency: {len(CANONICAL_DEPTHS)} depths != "
        f"{_DEPTHS_CFG['output_channels']} channels"
    )

CANONICAL_DEPTHS_SET = frozenset(CANONICAL_DEPTHS)
