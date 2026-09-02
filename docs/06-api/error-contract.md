# Error Contract

> Standardized API errors and client behavior.
> Schema: `contracts/api/error.schema.json`.

## Envelope

Errors follow a consistent structure:

```json
{
  "error": {
    "code": "INVALID_REGION",
    "message": "Unknown region: 'atlantis'. Valid regions: bay_of_bengal, arabian_sea.",
    "details": {}
  }
}
```

## Codes

| Code | Meaning |
|------|---------|
| `INVALID_REGION` | Unknown/unsupported region |
| `INVALID_DATE` | Date malformed or outside available coverage |
| `INVALID_DEPTH` | Depth not among the 15 canonical depths |
| `INVALID_COORDINATE` | Grid cell outside region / bad lat/lon |
| `DATA_NOT_AVAILABLE` | Requested data missing (no cache fallback) |
| `CHANNEL_UNAVAILABLE` | One or more surface channels unavailable (not zero-filled) |
| `MODEL_NOT_LOADED` | Inference model unavailable |
| `INFERENCE_FAILED` | Model produced invalid/failed output |
| `UNKNOWN_ERROR` | Unclassified failure |

## Rules

- Errors never leak credentials or internal dataset details (§64, §77).
- Client behavior: surface the `message`; act on stable `code`; treat `details` as advisory.
- Backend never displays fabricated scientific values on error (§122).