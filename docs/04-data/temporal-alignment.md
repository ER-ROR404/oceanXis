# Temporal Alignment

> Daily timestamp alignment and latency handling.
> Source: SYSTEM_MEMORY_DUMP.md §41, §106.

## Policy

- Align all variables to a **common daily time convention** (LOCKED: daily temporal resolution).
- Never merge datasets based solely on filename date.
- Normalize producer timestamps explicitly:
  - Toolbox `subset` uses Analysis-Ready Cloud Optimized conventions (timestamps aligned to interval
    **start**).
  - Raw `get` files may use producer conventions such as interval **center**.
- If a variable's true match falls on an adjacent day, use the actual matching available date and
  record it; do not silently shift data by one day to make arrays fit (§106).

## Latency

- Do not claim "real-time" without verification (§50, §129).
- Preferred wording: "latest available daily ocean observations."
- Copernicus docs indicate ~1–4 h typical delay for subset availability after files; dataset-
  specific values are checked at verification time.

## Alignment invariants

- All channels correspond to the same daily time unit.
- Temporal transformations are documented in provenance.