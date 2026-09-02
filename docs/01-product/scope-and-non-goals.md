# Scope and Non-Goals

## In scope (36-hour MVP)

- **Data ingestion**: Copernicus Marine products (historical + latest available), satellite-derived /
  gridded surface ocean products.
- **Data harmonization**: temporal alignment, spatial regridding to 0.25°, unit/coordinate
  normalization, missing-data handling, QC, land/sea masking, channel construction.
- **Machine learning**: surface encoder → latent **OceanEmbed** representation → depth-conditioned
  reconstruction → temperature prediction; optional uncertainty head.
- **Validation**: GLORYS as training/reference target; ARGO as independent validation; RMSE,
  correlation, bias; depth-wise skill.
- **Application**: Bay of Bengal / Arabian Sea map exploration, depth selection, grid-cell
  selection, vertical temperature profile, uncertainty display, optional ARGO comparison.

## Out of scope (MVP)

- Hardware, sensors, or any physical deployment.
- Raw orbital/Level-0 satellite image processing.
- Global-ocean production or full-domain training if data volume becomes excessive.
- Cyclone prediction, tsunami prediction, weather forecasting.
- Replacing INCOIS operational models or GODAS.
- Full numerical ocean modelling; real-time physical ocean forecasting.
- Chatbot / LLM features (RULE 19 — do not add unless explicitly required).
- Mobile app.
- Multi-cloud, Kubernetes, or microservice infrastructure for the MVP.

## Product positioning (critical)

OceanEmbed is a **complementary surface-observation-driven learned reconstruction pathway**, not a
replacement for GODAS or numerical ocean modelling:

```text
GODAS:      physical ocean model + data assimilation + multiple observations
OceanEmbed: surface state + learned latent representation + deep learning → subsurface temperature
```

## Terminology discipline

- Inputs are **multi-source surface ocean observations/products** — not "satellite images."
- The surface current product may be multi-source and may include model-derived components; it is
  never described as "pure satellite" without an explicitly documented derivation.
- Wording for freshness: **"latest available daily ocean observations"** unless true real-time
  availability is independently verified.