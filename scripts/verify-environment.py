#!/usr/bin/env python3
"""Verify the OceanEmbed environment: Python version, tooling, and module availability.

Read-only developer tooling. Does not install anything, does not touch the network.
Referenced by `make verify-env` and CI.
"""

from __future__ import annotations

import importlib.util
import platform
import shutil
import sys
from pathlib import Path

REQUIRED_PYTHON = (3, 11)
REQUIRED_TOOLS = {"uv": "dependency manager", "ruff": "linter/formatter", "pytest": "test runner"}
# On-demand checks: report presence but never fail the gate on optional ML/backend modules.
OPTIONAL_MODULES = {
    "fastapi": "backend",
    "pydantic": "backend",
    "sqlalchemy": "backend",
    "copernicusmarine": "backend+data-engineering",
    "xarray": "backend+data-engineering+ml",
    "numpy": "backend+data-engineering+ml",
    "torch": "ml",
    "yaml": "config readers",
    "jsonschema": "contract verification",
}


def check_python() -> bool:
    major, minor = sys.version_info[:2]
    ok = (major, minor) >= REQUIRED_PYTHON
    print(f"[python] {platform.python_version()} (require >=3.11) -> {'OK' if ok else 'FAIL'}")
    return ok


def check_tools() -> bool:
    ok = True
    for tool, purpose in REQUIRED_TOOLS.items():
        found = shutil.which(tool) is not None
        if not found:
            ok = False
        print(f"[tool]    {tool:12} ({purpose}) -> {'found' if found else 'MISSING'}")
    return ok


def check_modules() -> bool:
    ok = True
    for mod, owner in OPTIONAL_MODULES.items():
        present = importlib.util.find_spec(mod) is not None
        if not present:
            ok = False
        print(f"[module]  {mod:20} ({owner}) -> {'present' if present else 'missing'}")
    return ok


def main() -> int:
    # Ensure the repo root is importable (scripts run from repo root via Makefile).
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    checks = [check_python(), check_tools(), check_modules()]
    overall = all(checks)
    print(f"\nEnvironment verification: {'PASS' if overall else 'FAIL'}")
    print("NOTE: optional modules only warn; install per-module via backend/ml/data-engineering pyprojects.")
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())