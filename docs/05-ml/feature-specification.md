# Feature Specification

> The seven canonical surface input channels and optional derived features.
> Source: SYSTEM_MEMORY_DUMP.md §13, §101, §115; LOCKED by problem statement.

## Canonical input channels (LOCKED — 7)

```text
0 = SST        (°C)
1 = SSS        (PSU, source convention)
2 = SSH / SLA  (m)
3 = current U  (m/s)
4 = current V  (m/s)
5 = wind U     (m/s)
6 = wind V     (m/s)
```

Channel order is canonical (RULE 20, Golden Rule 17). Do not reorder without updating contracts.

## Derived features (OPTIONAL — not MVP)

| Feature | Rationale | Status |
|---------|-----------|--------|
| SST gradient magnitude | Coastal/mesoscale boundary signals | OPTIONAL |
| SSH gradient | Geostrophic current proxy | OPTIONAL |
| Wind magnitude (U²+V²)⁰·⁵ | Ekman transport intensity | OPTIONAL |
| Current magnitude | Flow intensity | OPTIONAL |
| Climatological anomalies | Departure from mean signal | OPTIONAL |

For the first MVP: use the **7 required channels directly** with no derived features (§101).

## Augmentation policy (LOCKED)

- No image-style augmentation (flips, random rotations, color augmentation) — ocean data has
  geographic/physical meaning (Golden Rule 8, §35).
- Allowed controlled augmentations (optional, MVP secondary): input noise, random spatial crops
  within valid region, channel masking/dropout — all preserving physical plausibility.