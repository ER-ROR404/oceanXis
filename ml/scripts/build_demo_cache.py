#!/usr/bin/env python
"""CLI entry point for the demo cache builder (plan Step 2.3).

Usage (from repo root, in the ML env):
    python ml/scripts/build_demo_cache.py \
        --region-dir data/tensors/bay_of_bengal \
        --checkpoint data/checkpoints/hybrid_v1/best.pt \
        --start 2023-06-01 --end 2023-12-31 --step-days 7 \
        --out artifacts/demo_cache
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from oceanembed.serving.build_demo_cache import main  # noqa: E402

if __name__ == "__main__":
    main()
