# Variables

> Canonical surface variables, semantics, and channel ordering.
> Source: SYSTEM_MEMORY_DUMP.md §3, §13, §115; LOCKED inputs.

## Canonical channel order (7 channels)

```text
0 = SST
1 = SSS
2 = SSH / SLA
3 = current U
4 = current V
5 = wind U
6 = wind V
```

Do NOT reorder channels without updating `config/variables.yaml`, the model config, and
`contracts/ml/model-input.schema.json` (RULE 20, Golden Rule 17).

## Per-variable semantics

### SST — Sea Surface Temperature
Surface thermal state, air–sea interaction, mixing, thermal/mesoscale gradients.
- Units: °C (internal convention).

### SSS — Sea Surface Salinity
Density, stratification, freshwater influence, upper-ocean structure. Together with SST determines
seawater density.
- Units: PSU (or source convention; document per dataset).

### SSH / SLA — Sea Surface Height / Sea Level Anomaly
Dynamic height, pressure structure, mesoscale eddies, thermocline displacement, large-scale
circulation.
- Units: meters.

### Current U / Current V
Horizontal transport, mesoscale circulation, advection, eddy structure.
- Units: m/s.
- **Caveat:** a candidate multi-source current product may include model-derived Ekman/current
  components. Such products are disclosed, never described as "pure satellite."

### Wind U / Wind V
Wind stress, Ekman transport, upwelling/downwelling, vertical mixing, air–sea coupling.
- Units: m/s.

## Derived features (OPTIONAL — not MVP)

Spatial gradients of SST/SSH, wind magnitude, current magnitude, climatological anomalies. For the
first MVP the 7 required channels are used directly (§101).