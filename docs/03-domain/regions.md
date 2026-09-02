# Regions

> Official domain and application-level region definitions.
> Source: SYSTEM_MEMORY_DUMP.md §11–§12; `config/regions.yaml`.

## Official domain (LOCKED)

```text
North Indian Ocean
    longitude:  45°E to 105°E
    latitude:    5°N to  30°N
grid:        0.25° × 0.25°
temporal:    daily
```

## Application regions (MVP)

```text
bay_of_bengal:
    min_lon:  80°E
    max_lon: 100°E
    min_lat:   5°N
    max_lat:  22°N

arabian_sea:
    min_lon:  45°E
    max_lon:  75°E
    min_lat:   5°N
    max_lat:  25°N
```

Both regions use the SAME Copernicus access mechanism. The backend maps
`region="bay_of_bengal" | "arabian_sea"` → bounds (validated via `config/regions.yaml`).

## Conventions

- Latitude/longitude conventions are normalized in preprocessing (choose 0–360 or −180–180
  internally; never mix — §108). NetCDF latitude arrays may be ascending or descending; normalize.
- Longitude wraparound and coastal cells are handled in regridding/masking (§110).
- Grid cells are addressed at 0.25° centers inside the region bounds.