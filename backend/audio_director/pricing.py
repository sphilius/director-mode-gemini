"""Pricing constants — the single source of truth for cost math.

VERIFIED: 2026-07-19 against live public pricing. Re-check before trusting at scale;
model names and rates move. Update the numbers here and every estimate follows.

Sources:
  - ElevenLabs: https://elevenlabs.io/pricing
  - Gemini TTS: https://ai.google.dev/gemini-api/docs/pricing
"""

from __future__ import annotations

from dataclasses import dataclass

PRICING_LAST_VERIFIED = "2026-07-19"


# --------------------------------------------------------------------------
# ElevenLabs
# --------------------------------------------------------------------------
# Credits are the billing unit. Text-to-Speech = 1 credit per character on the
# v2/v3 multilingual models; the Flash/Turbo models are discounted (~0.5/char).
# A plan buys a monthly credit bucket; effective $/credit = plan_price / credits.

@dataclass(frozen=True)
class ElevenLabsPlan:
    name: str
    monthly_usd: float
    monthly_credits: int
    commercial_rights: bool  # paid plans grant commercial use; free does not

    @property
    def usd_per_credit(self) -> float:
        return self.monthly_usd / self.monthly_credits if self.monthly_credits else 0.0


# The user's baseline plan is Creator (~$22/mo).
ELEVENLABS_PLANS: dict[str, ElevenLabsPlan] = {
    "free":    ElevenLabsPlan("Free",    0.0,   10_000,  commercial_rights=False),
    "starter": ElevenLabsPlan("Starter", 5.0,   30_000,  commercial_rights=True),
    "creator": ElevenLabsPlan("Creator", 22.0,  100_000, commercial_rights=True),
    "pro":     ElevenLabsPlan("Pro",     99.0,  500_000, commercial_rights=True),
}

DEFAULT_ELEVENLABS_PLAN = "creator"

# Credits per character by model family.
EL_CREDITS_PER_CHAR = {
    "eleven_v3":               1.0,   # expressive, emotion tags — used for LINES
    "eleven_multilingual_v2":  1.0,   # used for VOICE DESIGN previews
    "eleven_turbo_v2_5":       0.5,   # discounted, bulk
    "eleven_flash_v2_5":       0.5,   # discounted, bulk
}
EL_DEFAULT_LINE_MODEL = "eleven_v3"
EL_DEFAULT_DESIGN_MODEL = "eleven_multilingual_v2"


# --------------------------------------------------------------------------
# Google Gemini TTS  (per 1,000,000 tokens)
# --------------------------------------------------------------------------
# Output audio bills at ~25 tokens per second of speech. Input is the text.

@dataclass(frozen=True)
class GeminiTTSModel:
    name: str
    usd_in_per_mtok: float
    usd_out_per_mtok: float


GEMINI_TTS_MODELS: dict[str, GeminiTTSModel] = {
    "gemini-2.5-flash-tts": GeminiTTSModel("gemini-2.5-flash-tts", 0.50, 10.0),
    "gemini-3.5-flash-tts": GeminiTTSModel("gemini-3.5-flash-tts", 1.00, 6.0),
}
DEFAULT_GEMINI_TTS_MODEL = "gemini-2.5-flash-tts"

GEMINI_OUTPUT_TOKENS_PER_SECOND = 25.0  # audio output token rate


# --------------------------------------------------------------------------
# Speech-rate heuristics (shared) — used to estimate audio length from text.
# --------------------------------------------------------------------------
CHARS_PER_SECOND_SPEECH = 15.0   # ~2.5 words/sec * ~6 chars/word
CHARS_PER_INPUT_TOKEN = 4.0      # rough text tokenization
DEFAULT_REGEN_MULTIPLIER = 2.5   # takes generated per kept line (you try a few)


def audio_seconds_for(text: str) -> float:
    return max(len(text), 1) / CHARS_PER_SECOND_SPEECH


def gemini_output_tokens_for(text: str) -> float:
    return audio_seconds_for(text) * GEMINI_OUTPUT_TOKENS_PER_SECOND


def gemini_input_tokens_for(text: str) -> float:
    return max(len(text), 1) / CHARS_PER_INPUT_TOKEN
