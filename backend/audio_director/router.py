"""Engine router — decides ElevenLabs vs Gemini per line.

The hybrid principle: expressive/character-defining lines go to ElevenLabs (v3
emotion tags, best quality); bulk/ambient/utility lines go to Gemini (near-free,
fast). A per-line override always wins, so you keep manual control.

Override syntax in the master doc line (as a bracket token after the category):
    - [greeting] [engine=gemini] Welcome back.
    - [boss-intro] [engine=elevenlabs] [menacing] You should not have come.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.audio_director.models import LineSpec

ELEVENLABS = "elevenlabs"
GEMINI = "gemini"

# Categories that are "hero" by default — routed to ElevenLabs in hybrid mode.
DEFAULT_HERO_CATEGORIES = frozenset({
    "greeting", "level-up", "boss", "boss-intro", "story", "hero",
    "victory", "defeat", "reveal", "cutscene",
})


@dataclass
class RoutingPolicy:
    mode: str = "hybrid"                     # "hybrid" | "elevenlabs" | "gemini"
    hero_categories: frozenset = DEFAULT_HERO_CATEGORIES
    emotional_to_elevenlabs: bool = True     # any line with v3 emotion tags -> EL
    overrides_win: bool = True

    def with_hero(self, categories: list[str]) -> "RoutingPolicy":
        return RoutingPolicy(
            mode=self.mode,
            hero_categories=frozenset(c.strip().lower() for c in categories),
            emotional_to_elevenlabs=self.emotional_to_elevenlabs,
            overrides_win=self.overrides_win,
        )


def decide_engine(line: LineSpec, policy: RoutingPolicy) -> str:
    # 1. explicit per-line override
    if policy.overrides_win and line.engine_override in (ELEVENLABS, GEMINI):
        return line.engine_override
    # 2. forced single-engine modes
    if policy.mode == ELEVENLABS:
        return ELEVENLABS
    if policy.mode == GEMINI:
        return GEMINI
    # 3. hybrid heuristic
    if line.category.lower() in policy.hero_categories:
        return ELEVENLABS
    if policy.emotional_to_elevenlabs and line.emotion_tags:
        return ELEVENLABS
    return GEMINI


def route_reason(line: LineSpec, policy: RoutingPolicy) -> str:
    if policy.overrides_win and line.engine_override in (ELEVENLABS, GEMINI):
        return "override"
    if policy.mode in (ELEVENLABS, GEMINI):
        return f"mode={policy.mode}"
    if line.category.lower() in policy.hero_categories:
        return "hero-category"
    if policy.emotional_to_elevenlabs and line.emotion_tags:
        return "emotion-tags"
    return "bulk-default"
