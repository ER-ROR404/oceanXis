# frontend/

**OceanEmbed user interface (React + TypeScript + Vite).**

Interactive ocean dashboard: select region/date/depth → temperature map; select a grid cell →
15-depth temperature profile (with optional uncertainty), plus ARGO validation.

## Hard rules

- **Never** accesses Copernicus credentials (RULE 1).
- **Never** calls Copernicus directly — all data via the backend API (RULE 2).
- Consumes `contracts/api/*` typed clients (`src/types`, `src/api`).

## Layout

```text
src/
  main.tsx / App.tsx        bootstrap + composition
  routes/                   dashboard, about, index
  components/               layout, map, profile, controls, validation
  api/                      typed HTTP client (client, ocean, profiles, metadata)
  hooks/                    useOceanMap, useOceanProfile, useMetadata
  types/                    ocean, profile, prediction, api
  state/                    minimal global state
  styles/                   globals.css
```

## Environment

`frontend/package.json` (dev deps via npm). See `docs/07-operations/local-development.md`.

> **Pre-build stage:** structure is in place; implementation lands in the coding phase
> **after the data pipeline + model are proven** (Golden Rule 11: no frontend before pipeline).