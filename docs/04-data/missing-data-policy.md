# Missing Data Policy

> Treatment of NaNs, clouds, retrieval gaps, and missing channels.
> Source: SYSTEM_MEMORY_DUMP.md §36, §122.

## Guarantees

- **Never** blindly replace missing values with zero (RULE/Golden Rule 7-equivalent policy).
- Missing values are represented by NaN in data and tracked by a **validity mask**.
- For the strict official spec, the model's logical inputs remain the 7 surface variables; an
  added validity-mask channel (if introduced) is documented and reflected in `config/variables.yaml`
  and the model-input contract (RULE/§36).

## Runtime behaviors (§122)

- Copernicus unavailable → serve cached latest data (marked as cached).
- A variable unavailable → mark that channel unavailable (report `channel_status`); never silently
  zero-fill.
- Model inference fails → clear system error; never display fabricated scientific values.
- ARGO comparison gaps → reported as missing; never fabricated (Golden Rules 4, 21).

## Risk scenarios (§93)

cloudy SST, salinity gaps, coastal contamination, masked-out land, extreme events, unusual
circulation, distribution shift, deep-depth uncertainty, regional bias, source inconsistency.