#!/usr/bin/env python3
"""Phase 3.0 — Data Contract Verification (v2)

Uses copernicusmarine.describe() Pydantic model structure:
  Catalogue -> products -> datasets -> versions -> parts -> services -> variables

Run: python scripts/verify_data_contract.py
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import copernicusmarine as cm
import numpy as np


# ── Canonical domain (LOCKED in spec v2.1 §2) ──────────────────────────

LAT_MIN = 5.0    # °N (inclusive)
LAT_MAX = 30.0   # °N (inclusive)
LON_MIN = 45.0   # °E (inclusive)
LON_MAX = 105.0  # °E (inclusive)
RESOLUTION = 0.25  # °


# ── Dataset definitions ──────────────────────────────────────────────────

DATASETS = {
    "SST": {
        "dataset_id": "METOFFICE-GLO-SST-L4-REP-OBS-SST",
        "variable": "analysed_sst",
        "expected_units": "kelvin",
        "native_resolution": "0.05°",
        "role": "input",
    },
    "SSS": {
        "dataset_id": "cmems_obs-mob_glo_phy-sss_my_multi_P1D",
        "variable": "sos",
        "expected_units": ".001",  # CF convention: PSU * 0.001
        "native_resolution": "0.125°",  # verified from API (not 0.25°)
        "role": "input",
    },
    "SSH": {
        "dataset_id": "cmems_obs-sl_glo_phy-ssh_my_allsat-l4-duacs-0.125deg_P1D",
        "variable": "sla",
        "expected_units": "m",
        "native_resolution": "0.125°",
        "role": "input",
    },
    "Current_U": {
        "dataset_id": "cmems_obs-mob_glo_phy-cur_my_0.25deg_P1D-m",
        "variable": "uo",
        "expected_units": "m/s",  # CF convention: m s-1 = m/s
        "native_resolution": "0.25°",
        "role": "input",
    },
    "Current_V": {
        "dataset_id": "cmems_obs-mob_glo_phy-cur_my_0.25deg_P1D-m",
        "variable": "vo",
        "expected_units": "m/s",
        "native_resolution": "0.25°",
        "role": "input",
    },
    "Wind_U": {
        "dataset_id": "cmems_obs-wind_glo_phy_my_l4_0.125deg_PT1H",
        "variable": "eastward_wind",
        "expected_units": "m s-1",
        "native_resolution": "0.125°",
        "role": "input",
    },
    "Wind_V": {
        "dataset_id": "cmems_obs-wind_glo_phy_my_l4_0.125deg_PT1H",
        "variable": "northward_wind",
        "expected_units": "m s-1",
        "native_resolution": "0.125°",
        "role": "input",
    },
    "GLORYS_T": {
        "dataset_id": "cmems_mod_glo_phy_my_0.083deg_P1D-m",
        "variable": "thetao",
        "expected_units": "degrees_C",  # CF convention
        "native_resolution": "0.083°",
        "role": "training_target",
    },
}


@dataclass
class VerifiedVar:
    name: str
    dataset_id: str
    variable: str
    accessible: bool = False
    variable_found: bool = False
    actual_units: str = ""
    units_match: bool = False
    standard_name: str = ""
    lat_min: float = 0.0
    lat_max: float = 0.0
    lon_min: float = 0.0
    lon_max: float = 0.0
    time_min: str = ""
    time_max: str = ""
    time_min_year: int = 0
    time_max_year: int = 0
    depth_min: float | None = None
    depth_max: float | None = None
    has_depth: bool = False
    native_step_lat: float = 0.0
    native_step_lon: float = 0.0
    error: str = ""


def ms_to_date(ms: float) -> str:
    """Convert milliseconds since 1970-01-01 to ISO date string."""
    try:
        dt = datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d")
    except (ValueError, OSError):
        return f"{ms}ms"


def verify_one(name: str, config: dict) -> VerifiedVar:
    """Verify a single dataset using describe()."""
    v = VerifiedVar(
        name=name,
        dataset_id=config["dataset_id"],
        variable=config["variable"],
    )
    
    try:
        catalogue = cm.describe(dataset_id=config["dataset_id"])
        v.accessible = True
        
        # Navigate: catalogue -> products -> datasets -> versions -> parts -> services -> variables
        for product in catalogue.products:
            for dataset in product.datasets:
                # Get latest version
                if not dataset.versions:
                    continue
                version = dataset.versions[-1]
                
                for part in version.parts:
                    for service in part.services:
                        # Prefer arco-geo-series (has coordinates)
                        if service.service_name not in ("arco-geo-series", "arco-time-series"):
                            continue
                        
                        for var in service.variables:
                            if var.short_name == config["variable"]:
                                v.variable_found = True
                                v.actual_units = var.units
                                v.units_match = (var.units == config["expected_units"])
                                v.standard_name = var.standard_name or ""
                                
                                # Extract bbox
                                if var.bbox and len(var.bbox) == 4:
                                    v.lon_min, v.lat_min, v.lon_max, v.lat_max = var.bbox
                                
                                # Extract coordinates
                                for coord in var.coordinates:
                                    cid = coord.coordinate_id
                                    if cid == "latitude":
                                        v.lat_min = coord.minimum_value
                                        v.lat_max = coord.maximum_value
                                        v.native_step_lat = coord.step
                                    elif cid == "longitude":
                                        v.lon_min = coord.minimum_value
                                        v.lon_max = coord.maximum_value
                                        v.native_step_lon = coord.step
                                    elif cid == "time":
                                        v.time_min = ms_to_date(coord.minimum_value)
                                        v.time_max = ms_to_date(coord.maximum_value)
                                        try:
                                            v.time_min_year = int(v.time_min[:4])
                                            v.time_max_year = int(v.time_max[:4])
                                        except (ValueError, IndexError):
                                            pass
                                    elif cid == "depth":
                                        v.has_depth = True
                                        v.depth_min = coord.minimum_value
                                        v.depth_max = coord.maximum_value
                                
                                # Only need first matching variable from first matching service
                                return v
                
                # If no arco service found, try any service
                for service in part.services:
                    for var in service.variables:
                        if var.short_name == config["variable"]:
                            v.variable_found = True
                            v.actual_units = var.units
                            v.units_match = (var.units == config["expected_units"])
                            v.standard_name = var.standard_name or ""
                            if var.bbox and len(var.bbox) == 4:
                                v.lon_min, v.lat_min, v.lon_max, v.lat_max = var.bbox
                            return v
    
    except Exception as e:
        v.error = str(e)[:200]
    
    return v


def compute_grid():
    """Compute canonical 0.25° grid."""
    lats = np.arange(LAT_MIN, LAT_MAX + RESOLUTION / 2, RESOLUTION)
    lons = np.arange(LON_MIN, LON_MAX + RESOLUTION / 2, RESOLUTION)
    # Ensure endpoints are exact
    lats = lats[(lats >= LAT_MIN - 1e-9) & (lats <= LAT_MAX + 1e-9)]
    lons = lons[(lons >= LON_MIN - 1e-9) & (lons <= LON_MAX + 1e-9)]
    return lats, lons


def check_domain(v: VerifiedVar) -> dict:
    """Check if dataset covers our canonical domain."""
    return {
        "lat_covers_min": v.lat_min <= LAT_MIN + 0.01,
        "lat_covers_max": v.lat_max >= LAT_MAX - 0.01,
        "lon_covers_min": v.lon_min <= LON_MIN + 0.01,
        "lon_covers_max": v.lon_max >= LON_MAX - 0.01,
    }


def main():
    print("=" * 80)
    print("PHASE 3.0 — DATA CONTRACT VERIFICATION (v2)")
    print("=" * 80)
    
    # 1. Grid
    lats, lons = compute_grid()
    H, W = len(lats), len(lons)
    print(f"\n1. CANONICAL GRID")
    print(f"   Latitude:  {LAT_MIN}°N to {LAT_MAX}°N, step {RESOLUTION}° → H={H}")
    print(f"   Longitude: {LON_MIN}°E to {LON_MAX}°E, step {RESOLUTION}° → W={W}")
    print(f"   First lat: {lats[0]:.2f}°  Last lat: {lats[-1]:.2f}°")
    print(f"   First lon: {lons[0]:.2f}°  Last lon: {lons[-1]:.2f}°")
    print(f"   Total grid cells: {H}×{W} = {H*W}")
    
    # 2. Verify each dataset
    print(f"\n2. DATASET SCHEMA VERIFICATION")
    results = {}
    for name, config in DATASETS.items():
        print(f"\n   [{name}] {config['dataset_id']}")
        v = verify_one(name, config)
        results[name] = v
        
        if v.error:
            print(f"   ❌ ERROR: {v.error}")
            continue
        
        print(f"   Accessible: ✅")
        print(f"   Variable found: {'✅' if v.variable_found else '❌'}")
        print(f"   Short name: {v.variable}")
        print(f"   Standard name: {v.standard_name}")
        units_expected = config["expected_units"]
        units_status = "✅" if v.units_match else f"⚠️  expected {units_expected}"
        print(f"   Units: {v.actual_units} {units_status}")
        print(f"   Lat range: {v.lat_min:.4f} to {v.lat_max:.4f} (step {v.native_step_lat:.4f}°)")
        print(f"   Lon range: {v.lon_min:.4f} to {v.lon_max:.4f} (step {v.native_step_lon:.4f}°)")
        print(f"   Time range: {v.time_min} to {v.time_max} ({v.time_min_year}-{v.time_max_year})")
        if v.has_depth:
            print(f"   Depth range: {v.depth_min} to {v.depth_max} m")
        
        dc = check_domain(v)
        covers = all(dc.values())
        print(f"   Domain coverage: {'✅ FULL' if covers else '⚠️  PARTIAL'}")
        if not covers:
            for k, val in dc.items():
                if not val:
                    print(f"     {k}: ❌")
    
    # 3. Coverage matrix
    print(f"\n3. TEMPORAL COVERAGE MATRIX (2018-2025)")
    header = f"   {'Variable':<12}" + "".join(f"{y:>6}" for y in range(2018, 2026))
    print(header)
    print("   " + "-" * (12 + 6 * 8))
    
    for name, v in results.items():
        row = f"   {name:<12}"
        for year in range(2018, 2026):
            if v.time_min_year <= year <= v.time_max_year:
                row += "    ✅"
            else:
                row += "    ❌"
        print(row)
    
    # 4. Summary
    print(f"\n4. VERIFICATION SUMMARY")
    all_ok = True
    for name, v in results.items():
        issues = []
        if not v.accessible:
            issues.append("NOT ACCESSIBLE")
        if not v.variable_found:
            issues.append("variable not found")
        if not v.units_match:
            issues.append(f"units mismatch ({v.actual_units} vs {DATASETS[name]['expected_units']})")
        dc = check_domain(v) if v.accessible else {}
        if not all(dc.values()):
            missing = [k for k, val in dc.items() if not val]
            issues.append(f"domain gap: {missing}")
        if v.time_min_year > 2018:
            issues.append(f"data starts {v.time_min_year}, need 2018")
        
        if issues:
            print(f"   ❌ {name}: {', '.join(issues)}")
            all_ok = False
        else:
            print(f"   ✅ {name}: all checks passed")
    
    # 5. Grid contract
    print(f"\n5. GRID CONTRACT (frozen)")
    print(f"   Input:  [B, T=7, C=7, H={H}, W={W}]")
    print(f"   Output: [B, C=15, H={H}, W={W}]")
    print(f"   Spatial: {H*W} cells ({H*W * 0.25 * 0.25:.0f} km² per cell)")
    
    # 6. Unit conversion notes
    print(f"\n6. UNIT CONVERSION NOTES")
    conversions = {
        "SST": f"kelvin -> °C: T_C = T_K - 273.15",
        "SSS": f"{results['SSS'].actual_units} -> PSU: multiply by 1000",
        "GLORYS_T": f"Already in {results['GLORYS_T'].actual_units} (no conversion)",
    }
    for name, note in conversions.items():
        print(f"   {name}: {note}")
    
    # Save
    output = {
        "grid": {
            "lat_min": LAT_MIN, "lat_max": LAT_MAX,
            "lon_min": LON_MIN, "lon_max": LON_MAX,
            "resolution": RESOLUTION,
            "H": int(H), "W": int(W),
            "lats": lats.tolist(), "lons": lons.tolist(),
        },
        "datasets": {},
        "all_ok": all_ok,
    }
    for name, v in results.items():
        output["datasets"][name] = {
            "dataset_id": v.dataset_id,
            "variable": v.variable,
            "accessible": v.accessible,
            "variable_found": v.variable_found,
            "actual_units": v.actual_units,
            "units_match": v.units_match,
            "standard_name": v.standard_name,
            "lat_range": [v.lat_min, v.lat_max],
            "lon_range": [v.lon_min, v.lon_max],
            "time_range": [v.time_min, v.time_max],
            "time_years": [v.time_min_year, v.time_max_year],
            "has_depth": v.has_depth,
            "depth_range": [v.depth_min, v.depth_max] if v.has_depth else None,
            "native_step": [v.native_step_lat, v.native_step_lon],
        }
    
    out_path = Path("data/contracts/data_contract_verification.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\n   Saved: {out_path}")
    
    if all_ok:
        print(f"\n{'='*80}")
        print(f"✅ DATA CONTRACT VERIFICATION PASSED")
        print(f"{'='*80}")
        return 0
    else:
        print(f"\n{'='*80}")
        print(f"❌ DATA CONTRACT VERIFICATION FAILED")
        print(f"{'='*80}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
