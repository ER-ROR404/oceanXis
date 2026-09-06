"""Regression lock: frontend/src/assets/validation/argo_validation_summary.json.

This asset drives the Phase 4 dashboard validation panel. The numbers are
copied VERBATIM from the repo-official work-log (docs/work-log/2026-09-06-argo-
validation.md) — recalculating them here would risk violating the "no invented
scores" rule (SYSTEM_MEMORY_DUMP §152.4-5 / AGENTS.md). These tests:

  1. lock the file to its committed contract schema, and
  2. assert the values EQUAL the work-log table (so a re-edit can't silently
     drift from the authoritative source).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft7Validator

# Paths relative to repo root.
ROOT = Path(__file__).resolve().parents[2]
SUMMARY = ROOT / "frontend/src/assets/validation/argo_validation_summary.json"
SCHEMA = ROOT / "contracts/validation/argo-summary.schema.json"
WORKLOG = ROOT / "docs/work-log/2026-09-06-argo-validation.md"

# Canonical depths (must appear exactly once, in order — RULE 20).
CANONICAL_DEPTHS = [0, 5, 10, 20, 30, 50, 75, 100, 125, 150, 200, 300, 500, 700, 1000]


@pytest.fixture(scope="module")
def summary() -> dict:
    return json.loads(SUMMARY.read_text())


@pytest.fixture(scope="module")
def schema() -> dict:
    return json.loads(SCHEMA.read_text())


class TestArgoSummarySchema:
    """The summary conforms to its committed contract schema."""

    def test_schema_is_valid_draft7(self, schema: dict) -> None:
        Draft7Validator.check_schema(schema)

    def test_summary_conforms_to_schema(self, summary: dict, schema: dict) -> None:
        errors = sorted(Draft7Validator(schema).iter_errors(summary), key=lambda e: list(e.path))
        assert not errors, f"summary violates schema: {errors}"

    def test_depth_keys_are_exactly_canonical(self, summary: dict) -> None:
        keys = [int(k) for k in summary["depth_wise"]]
        assert keys == CANONICAL_DEPTHS, "depth_wise keys must equal the canonical depth list"


class TestArgoSummaryRegression:
    """Values equal the committed work-log (authoritative source)."""

    def _parse_worklog_depth_table(self) -> dict[int, tuple[int, float, float, float]]:
        """Extract (n, rmse, bias, corr) per depth from the work-log markdown table."""
        in_table = False
        rows: dict[int, tuple[int, float, float, float]] = {}
        for line in WORKLOG.read_text().splitlines():
            if line.startswith("| Depth (m) |"):
                in_table = True
                continue
            if not in_table:
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 5 or not cells[0].isdigit():
                continue
            depth = int(cells[0])
            n = int(cells[1].replace(",", ""))
            rmse = float(cells[2])
            bias = float(cells[3].replace("−", "-").replace("+", ""))
            corr = float(cells[4])
            rows[depth] = (n, rmse, bias, corr)
        return rows

    def test_overall_matches_worklog(self, summary: dict) -> None:
        text = WORKLOG.read_text()
        assert "**Overall RMSE** | **1.3533 °C**" in text
        assert "**Overall bias** | **+0.6121 °C**" in text
        assert "**Overall correlation** | **0.99**" in text
        assert summary["overall"]["rmse_c"] == pytest.approx(1.3533, abs=1e-9)
        assert summary["overall"]["bias_c"] == pytest.approx(0.6121, abs=1e-9)
        assert summary["overall"]["correlation"] == pytest.approx(0.99, abs=1e-9)

    def test_profiles_match_worklog(self, summary: dict) -> None:
        text = WORKLOG.read_text()
        assert "285 / 6" in text
        assert summary["profiles"]["loaded"] == 291
        assert summary["profiles"]["matched"] == 285
        assert summary["profiles"]["unmatched"] == 6
        assert summary["profiles"]["unmatched_reasons"]["land"] == 6
        assert summary["profiles"]["depth_observations"] == 3958

    def test_validation_window_matches_worklog(self, summary: dict) -> None:
        text = WORKLOG.read_text()
        assert "2023-08-10 .. 2023-12-31" in text
        assert summary["validation_window"]["start"] == "2023-08-10"
        assert summary["validation_window"]["end"] == "2023-12-31"

    def test_depth_wise_matches_worklog(self, summary: dict) -> None:
        worklog_rows = self._parse_worklog_depth_table()
        assert worklog_rows, "no depth rows parsed from work-log"
        assert set(worklog_rows) == set(int(k) for k in summary["depth_wise"]), \
            "summary depths and work-log depths must match"
        for depth_str, cell in summary["depth_wise"].items():
            depth = int(depth_str)
            n, rmse, bias, corr = worklog_rows[depth]
            assert cell["n"] == n, f"depth {depth}: n mismatch"
            assert cell["rmse_c"] == pytest.approx(rmse, abs=1e-9), f"depth {depth}: rmse"
            assert cell["bias_c"] == pytest.approx(bias, abs=1e-9), f"depth {depth}: bias"
            assert cell["correlation"] == pytest.approx(corr, abs=1e-9), f"depth {depth}: corr"

    def test_model_version_and_source_worklog(self, summary: dict) -> None:
        assert summary["model_version"] == "hybrid_v1"
        assert summary["source_work_log"] == "docs/work-log/2026-09-06-argo-validation.md"

    def test_limitations_string_present(self, summary: dict) -> None:
        assert isinstance(summary["limitations"], str) and len(summary["limitations"]) > 20
        # Honest: acknowledges the thermocline warm bias and sparse depth-0.
        assert "thermocline" in summary["limitations"].lower()
        assert "warm bias" in summary["limitations"].lower()
