"""RULE 3 boundary checks (static, ML suite side).

The enforcement that backend imports never load torch lives in the backend
test suite (backend env has no torch — any accidental import fails loudly).
Here we assert the structural side: backend/ contains no ML-serving code.
"""

from __future__ import annotations

from pathlib import Path

# backend/ dir: <repo>/backend
BACKEND_DIR = Path(__file__).resolve().parents[3] / "backend"


def test_backend_has_no_serving_import_leak() -> None:
    assert not (BACKEND_DIR / "app" / "serving").exists(), (
        "backend/ must not contain ML serving code (RULE 3)"
    )


def test_backend_has_no_torch_in_source() -> None:
    """backend/ source must not reference torch anywhere."""
    import re

    hits = []
    for py in BACKEND_DIR.rglob("app/**/*.py"):
        if py.is_file():
            text = py.read_text(errors="ignore")
            if re.search(r"^\s*(import|from)\s+torch", text, re.MULTILINE):
                hits.append(str(py))
    assert not hits, f"backend/ source imports torch: {hits}"
