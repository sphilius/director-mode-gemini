"""Data models for the Audio Director.

Deliberately mirrors backend/utils/story_state.py conventions: dataclasses,
`from __future__ import annotations`, to_dict() for JSON, short uuid ids.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class VoiceConfig:
    """ElevenLabs-style tuning knobs parsed from the master doc.

    Standard EL voice_settings: stability, similarity_boost, style, speed,
    use_speaker_boost. `guidance` and `loudness` are carried through as-is
    (non-standard) so nothing the user wrote is lost.
    """
    stability: Optional[float] = None
    similarity: Optional[float] = None      # -> similarity_boost
    style: Optional[float] = None
    speed: Optional[float] = None
    guidance: Optional[float] = None         # passthrough (non-standard)
    loudness: Optional[float] = None         # passthrough (non-standard)
    use_speaker_boost: Optional[bool] = None

    def to_elevenlabs_settings(self) -> dict:
        """Map to the ElevenLabs voice_settings payload, dropping None/unknowns."""
        out: dict = {}
        if self.stability is not None:
            out["stability"] = self.stability
        if self.similarity is not None:
            out["similarity_boost"] = self.similarity
        if self.style is not None:
            out["style"] = self.style
        if self.speed is not None:
            out["speed"] = self.speed
        if self.use_speaker_boost is not None:
            out["use_speaker_boost"] = self.use_speaker_boost
        return out

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class LineSpec:
    """A single line to generate for a character, tagged by category."""
    category: str            # e.g. "greeting", "streak-at-risk", "level-up"
    text: str
    index: int = 0           # position within its category
    emotion_tags: list[str] = field(default_factory=list)  # v3 tags, e.g. ["[excited]"]

    @property
    def tagged_text(self) -> str:
        """Text with v3 emotion tags prepended (ElevenLabs v3 inline tags)."""
        if not self.emotion_tags:
            return self.text
        return " ".join(self.emotion_tags) + " " + self.text

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "text": self.text,
            "index": self.index,
            "emotionTags": self.emotion_tags,
        }


@dataclass
class CharacterVoice:
    """One voice/character parsed from the master doc (an H2 section)."""
    name: str
    voice_design_prompt: str = ""
    preview_text: str = ""
    personality: str = ""
    config: VoiceConfig = field(default_factory=VoiceConfig)
    lines: list[LineSpec] = field(default_factory=list)
    voice_id: Optional[str] = None           # set once the EL voice exists
    voice_version: str = "v3"                # naming tag
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    @property
    def slug(self) -> str:
        return _slugify(self.name)

    def categories(self) -> list[str]:
        seen: list[str] = []
        for ln in self.lines:
            if ln.category not in seen:
                seen.append(ln.category)
        return seen

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "voiceDesignPrompt": self.voice_design_prompt,
            "previewText": self.preview_text,
            "personality": self.personality,
            "config": self.config.to_dict(),
            "lines": [ln.to_dict() for ln in self.lines],
            "voiceId": self.voice_id,
            "voiceVersion": self.voice_version,
        }


@dataclass
class LineCost:
    line: LineSpec
    el_credits: float
    el_usd: float
    gemini_usd: float


@dataclass
class CostEstimate:
    """Pre-spend cost breakdown across ElevenLabs and Gemini."""
    character: str
    regen_multiplier: float
    el_plan: str
    el_line_credits: float = 0.0       # kept-line credits incl. regen
    el_design_credits: float = 0.0     # one-time voice-design credits
    el_usd: float = 0.0
    gemini_usd: float = 0.0
    per_line: list[LineCost] = field(default_factory=list)

    @property
    def el_total_credits(self) -> float:
        return self.el_line_credits + self.el_design_credits

    def to_dict(self) -> dict:
        return {
            "character": self.character,
            "regenMultiplier": self.regen_multiplier,
            "elPlan": self.el_plan,
            "elLineCredits": round(self.el_line_credits, 1),
            "elDesignCredits": round(self.el_design_credits, 1),
            "elTotalCredits": round(self.el_total_credits, 1),
            "elUsd": round(self.el_usd, 4),
            "geminiUsd": round(self.gemini_usd, 4),
            "lineCount": len(self.per_line),
        }


@dataclass
class GenerationResult:
    character: str
    category: str
    take: int
    filename: str
    path: str
    engine: str
    model: str
    credits_spent: float = 0.0
    dry_run: bool = True
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


def _slugify(text: str) -> str:
    out = []
    for ch in text.strip().lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in (" ", "-", "_"):
            out.append("-")
    slug = "".join(out)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "unnamed"
