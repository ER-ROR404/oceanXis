# Ocean Domain

> North Indian Ocean scientific domain and OceanEmbed terminology.
> Source: SYSTEM_MEMORY_DUMP.md §2, §3, §54.

## Problem framing

Subsurface ocean temperature drives circulation, upper-ocean heat content, stratification, climate
variability, air–sea interaction, marine ecosystems, heatwave monitoring, fisheries, and data
assimilation. Direct observations (ARGO, moorings, gliders, ships) are sparse; satellite surface
coverage is broad and frequent.

OceanEmbed treats this as a **learned inverse problem**:

```text
"surface variables → subsurface temperature"
```

The mapping is nonlinear, spatially and temporally variable, depth-dependent, physically
constrained, and partially ill-posed — therefore a learned latent representation (not trivial
interpolation).

## Terminology

| Term | Meaning |
|------|---------|
| Surface state | The 7 harmonized daily surface channels on the 0.25° grid |
| Ocean embedding | The latent spatial representation produced by the surface encoder |
| Reconstruction | Decoding the embedding into 15-depth temperature fields |
| GLORYS | Dense reanalysis used as training/reference target |
| ARGO | Independent in-situ vertical profiles used for validation |
| Product | A gridded geophysical dataset (e.g., SST L4); inputs are *multi-source surface ocean observations/products* — not "satellite images" |

## Physical context (North Indian Ocean)

- Domain: 5°N–30°N, 45°E–105°E (Arabian Sea, Bay of Bengal, equatorial band influence).
- Bay of Bengal: strong freshwater influence, stratification, monsoon forcing.
- Arabian Sea: upwelling zones (Somalia/Arabian), strong SST variability, thermocline shallowing.
- Daily 0.25° resolution captures mesoscale structure and thermocline displacement signals.

## Positioning

OceanEmbed provides a **complementary learned reconstruction pathway** for dense subsurface
temperature intelligence. It is not a replacement for GODAS, INCOIS numerical modelling, or data
assimilation systems (see `docs/01-product/scope-and-non-goals.md`).