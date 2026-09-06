"""Domain primitives read from canonical config (config/regions.yaml, config/depths.yaml).

Never hardcode region bounds or depths here (RULE 20); the YAML files are the
source of truth.
"""

from app.domain.depths import CANONICAL_DEPTHS, CANONICAL_DEPTHS_SET
from app.domain.regions import REGION_IDS, REGIONS, Region, get_region

__all__ = [
    "CANONICAL_DEPTHS",
    "CANONICAL_DEPTHS_SET",
    "REGIONS",
    "REGION_IDS",
    "Region",
    "get_region",
]
