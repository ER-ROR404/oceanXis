# Units

> Canonical internal units per variable. One convention, enforced.
> Source: SYSTEM_MEMORY_DUMP.md §42.

## Canonical internal units

| Variable | Internal unit |
|----------|---------------|
| SST | °C |
| SSS | PSU (source practical-salinity convention; documented per dataset) |
| SSH / SLA | m |
| Current U | m/s |
| Current V | m/s |
| Wind U | m/s |
| Wind V | m/s |
| Temperature target | °C |

## Unit harmonization rules

- Convert at the preprocessing boundary; record conversion in provenance (§78).
- Choose one internal convention and keep it consistent across datasets.
- Watch for Kelvin vs Celsius, meters vs centimeters (§110).
- z-score normalization is applied per channel on top of these physical units; normalization
  statistics are TRAIN-ONLY (RULE 11). `X` in the model is float32 normalized; outputs are
  denormalized back to °C before display.