"""OceanEmbed ML inference service (serving).

Exposes the trained model to the backend over HTTP (RULE 3 boundary: the
backend never imports torch; this package is the ML side of that boundary).

The trained model is called as ``model(x)`` with NO coordinates — see
``service.py`` docstring for the verified call-site contract.
"""

from oceanembed.serving.service import InferenceService, LoadedModel

__all__ = ["InferenceService", "LoadedModel"]
