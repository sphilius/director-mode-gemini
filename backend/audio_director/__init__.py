"""Audio Director — a sub-agent for producing named voice lines.

v1 slice (P/R/H-scoped):
  Prediction  : master-doc parse -> cost estimate -> ElevenLabs generation w/ auto-naming
  Regularizer : dry-run cost gate before any spend; keep/reject sidecar logging; spend ceiling
  Heuristic   : (deferred) Gemini routing, hybrid allocation, full preference recommender,
                autonomous budget approval, self-hosted TTS

Plugs into StoryForge Layer 2 (the TTS slot) but runs standalone via the CLI.
"""

from backend.audio_director.models import (
    CharacterVoice,
    LineSpec,
    VoiceConfig,
    CostEstimate,
    GenerationResult,
)

__all__ = [
    "CharacterVoice",
    "LineSpec",
    "VoiceConfig",
    "CostEstimate",
    "GenerationResult",
]

__version__ = "0.1.0"
