"""Shared fixtures for data-engineering tests."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure data-engineering/src is on the path for imports
_project_root = Path(__file__).resolve().parent.parent.parent
_src_path = str(_project_root / "data-engineering" / "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)
