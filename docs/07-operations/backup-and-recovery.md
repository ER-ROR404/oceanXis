# Backup and Recovery

> Backup and restoration procedures.

## Data plane

- Raw + harmonized data and prediction rasters live in object storage / filesystem (outside Git).
- Retain the dataset manifests and provenance records so datasets can be re-derived.
- Back up or re-derivable: manifests + provenance are small and Git-tracked; bulk data is
  re-downloadable from Copernicus (regional subsets) on demand.

## Database (metadata + application state)

- Metadata only (dataset registry, ingestion jobs, prediction metadata, model registry).
- Scheduled backups of the database; restore to a known-good snapshot.

## Models / checkpoints

- Immutable, hashed artifacts in object storage / artifact registry (not Git).
- Registry (`.yaml` + manifests) is Git-tracked; weights are restorable from the artifact store.

## Recovery order (incident)

1. Restore/manifest the dataset registry.
2. Restore database metadata.
3. Point registry at existing artifact-store weights (or re-download regional data).
4. Validate health + one map/profile flow before full service.

## RPO/RTO note

- MVP/local: no strict SLA — document a pragmatic target (e.g., ≤ 24h recovery) once deployment
  is decided. Status: UNRESOLVED (deployment provider not locked).