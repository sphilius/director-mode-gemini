"""ElevenLabs REST client — spend-gated.

Two-stage workflow, matching how the user works by hand:
  1. Voice DESIGN  (eleven_multilingual_v2 / v2.5): generate preview samples from a
     description, pick one, create a persistent voice.
  2. LINE generation (eleven_v3 + inline emotion tags): synthesize each line.

SAFETY: nothing here spends credits unless `execute=True` AND ELEVENLABS_API_KEY is
set. Default is dry_run — it returns what it WOULD do. This is the hard guard behind
the human-approval ladder.

Endpoints follow ElevenLabs API v1. Confirm against current docs before a big run;
the base paths occasionally change.
"""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from typing import Optional

try:
    import httpx
except ImportError:  # keep import-safe for dry-run/parse-only usage
    httpx = None  # type: ignore

from backend.audio_director import pricing
from backend.audio_director.models import VoiceConfig

API_BASE = "https://api.elevenlabs.io/v1"
DEFAULT_OUTPUT_FORMAT = "mp3_44100_128"


@dataclass
class VoicePreview:
    generated_voice_id: str
    audio_bytes: Optional[bytes] = None


def _normalize_settings(cfg: VoiceConfig) -> dict:
    """0-100 style values -> 0-1 that ElevenLabs expects; speed passes through."""
    s = cfg.to_elevenlabs_settings()
    for k in ("stability", "similarity_boost", "style"):
        if k in s and s[k] is not None and s[k] > 1:
            s[k] = round(s[k] / 100.0, 3)
    return s


class ElevenLabsClient:
    def __init__(self, api_key: Optional[str] = None, execute: bool = False, timeout: float = 60.0):
        self.api_key = api_key or os.environ.get("ELEVENLABS_API_KEY")
        self.execute = execute
        self.timeout = timeout

    @property
    def live(self) -> bool:
        return bool(self.execute and self.api_key and httpx is not None)

    def _headers(self, accept: str = "application/json") -> dict:
        return {"xi-api-key": self.api_key or "", "Accept": accept, "Content-Type": "application/json"}

    # -- Stage 1: voice design ------------------------------------------------
    def design_voice(self, description: str, preview_text: str, n_samples: int = 3) -> list[VoicePreview]:
        """Generate preview samples for a described voice. No persistent voice yet."""
        if not self.live:
            return [VoicePreview(generated_voice_id=f"dryrun-{i+1}") for i in range(n_samples)]
        url = f"{API_BASE}/text-to-voice/create-previews"
        payload = {"voice_description": description, "text": preview_text}
        r = httpx.post(url, headers=self._headers(), json=payload, timeout=self.timeout)
        r.raise_for_status()
        previews = r.json().get("previews", [])
        out = []
        for p in previews[:n_samples]:
            audio = p.get("audio_base_64")
            out.append(VoicePreview(
                generated_voice_id=p.get("generated_voice_id", ""),
                audio_bytes=base64.b64decode(audio) if audio else None,
            ))
        return out

    def create_voice(self, name: str, description: str, generated_voice_id: str) -> Optional[str]:
        """Persist a chosen preview as a reusable voice; returns voice_id."""
        if not self.live:
            return f"dryrun-voice-{name}"
        url = f"{API_BASE}/text-to-voice"
        payload = {"voice_name": name, "voice_description": description,
                   "generated_voice_id": generated_voice_id}
        r = httpx.post(url, headers=self._headers(), json=payload, timeout=self.timeout)
        r.raise_for_status()
        return r.json().get("voice_id")

    # -- Stage 2: line generation --------------------------------------------
    def tts(self, voice_id: str, text: str, config: VoiceConfig,
            model_id: str = pricing.EL_DEFAULT_LINE_MODEL,
            output_format: str = DEFAULT_OUTPUT_FORMAT) -> Optional[bytes]:
        """Synthesize a line. Returns audio bytes, or None on dry-run."""
        if not self.live:
            return None
        url = f"{API_BASE}/text-to-speech/{voice_id}"
        params = {"output_format": output_format}
        payload = {"text": text, "model_id": model_id, "voice_settings": _normalize_settings(config)}
        r = httpx.post(url, headers=self._headers(accept="audio/mpeg"),
                       params=params, json=payload, timeout=self.timeout)
        r.raise_for_status()
        return r.content

    @staticmethod
    def credits_for(text: str, model_id: str = pricing.EL_DEFAULT_LINE_MODEL) -> float:
        return len(text) * pricing.EL_CREDITS_PER_CHAR.get(model_id, 1.0)
