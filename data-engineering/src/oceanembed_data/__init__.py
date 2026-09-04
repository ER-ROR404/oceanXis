"""OceanEmbed data acquisition and harmonization.

Responsibility: acquire and transform trustworthy data — do NOT train models.

Workflow: Copernicus → discover/verify → subset → harmonize → validate → provenance

Key rules:
- Dataset IDs verified via describe() (RULE 7); never guessed.
- One-day regional test before mass downloads (Golden Rule 10).
- Preserve channel/depth ordering (Golden Rules 17–18).
- GLORYS = training target; ARGO = independent validation only (RULE 8–9).
"""

__version__ = "0.1.0"
