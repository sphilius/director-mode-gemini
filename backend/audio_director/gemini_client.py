"""Gemini TTS client — spend-gated, for bulk / ambient lines.

Uses the Google AI Studio API (GEMINI_API_KEY) by default so personal/household
use lands on the free tier. Output is 24 kHz mono PCM, wrapped to WAV here.

SAFETY: nothing runs unless `execute=True` AND GEMINI_API_KEY is set. Default is
dry-run. Confirm the TTS model id + SDK surface against current docs before a big
run — Gemini's TTS API moves faster than ElevenLabs'.
"""

from __future__ import annotations

import io
import os
import wave
from typing import Optional

from backend.audio_director import pricing

try:
    from google import genai
    from google.genai import types
except ImportError:  # keep import-safe for dry-run/parse-only usage
    genai = None  # type: ignore
    types = None  # type: ignore

# AI Studio model string (distinct from the pricing key in pricing.py).
DEFAULT_TTS_MODEL_ID = os.environ.get("GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts")
DEFAULT_GEMINI_VOICE = "Kore"          # a neutral prebuilt voice
GEMINI_SAMPLE_RATE = 24000             # Gemini TTS PCM output rate
GEMINI_SAMPLE_WIDTH = 2                 # 16-bit
GEMINI_CHANNELS = 1


def pcm_to_wav(pcm: bytes, rate: int = GEMINI_SAMPLE_RATE) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(GEMINI_CHANNELS)
        wf.setsampwidth(GEMINI_SAMPLE_WIDTH)
        wf.setframerate(rate)
        wf.writeframes(pcm)
    return buf.getvalue()


class GeminiTTSClient:
    def __init__(self, api_key: Optional[str] = None, execute: bool = False,
                 model_id: str = DEFAULT_TTS_MODEL_ID):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.execute = execute
        self.model_id = model_id
        self._client = None

    @property
    def live(self) -> bool:
        return bool(self.execute and self.api_key and genai is not None)

    def _get_client(self):
        if self._client is None:
            # AI Studio (Developer API) — NOT Vertex — so the free tier applies.
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def tts(self, text: str, voice_name: str = DEFAULT_GEMINI_VOICE) -> Optional[bytes]:
        """Synthesize a line. Returns WAV bytes, or None on dry-run."""
        if not self.live:
            return None
        client = self._get_client()
        resp = client.models.generate_content(
            model=self.model_id,
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                    )
                ),
            ),
        )
        pcm = resp.candidates[0].content.parts[0].inline_data.data
        return pcm_to_wav(pcm)

    @staticmethod
    def usd_for(text: str, model_key: str = pricing.DEFAULT_GEMINI_TTS_MODEL) -> float:
        gm = pricing.GEMINI_TTS_MODELS[model_key]
        in_tok = pricing.gemini_input_tokens_for(text)
        out_tok = pricing.gemini_output_tokens_for(text)
        return (in_tok / 1_000_000 * gm.usd_in_per_mtok) + (out_tok / 1_000_000 * gm.usd_out_per_mtok)
