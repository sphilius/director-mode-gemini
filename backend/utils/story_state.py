"""Story state management for Director Mode.

Maintains the evolving narrative state including scenes, characters,
mood, and timeline as the user directs the story through Gemini.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Mood(str, Enum):
    TENSE = "tense"
    CALM = "calm"
    JOYFUL = "joyful"
    MYSTERIOUS = "mysterious"
    DRAMATIC = "dramatic"
    MELANCHOLIC = "melancholic"
    SUSPENSEFUL = "suspenseful"
    ROMANTIC = "romantic"


@dataclass
class Character:
    name: str
    description: str
    motivation: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "motivation": self.motivation,
        }


@dataclass
class Scene:
    title: str
    description: str
    mood: Mood = Mood.CALM
    characters: list[Character] = field(default_factory=list)
    director_notes: str = ""
    timestamp: float = field(default_factory=time.time)
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "mood": self.mood.value,
            "characters": [c.to_dict() for c in self.characters],
            "directorNotes": self.director_notes,
            "timestamp": self.timestamp,
        }


class StoryState:
    """Manages the full narrative state across a directing session."""

    def __init__(self) -> None:
        self.session_id: str = str(uuid.uuid4())
        self.title: str = "Untitled Story"
        self.genre: str = ""
        self.scenes: list[Scene] = []
        self.characters: list[Character] = []
        self.current_scene_index: int = -1
        self.created_at: float = time.time()

    @property
    def current_scene(self) -> Optional[Scene]:
        if 0 <= self.current_scene_index < len(self.scenes):
            return self.scenes[self.current_scene_index]
        return None

    def add_scene(self, scene: Scene) -> Scene:
        self.scenes.append(scene)
        self.current_scene_index = len(self.scenes) - 1
        return scene

    def add_character(self, character: Character) -> Character:
        self.characters.append(character)
        return character

    def get_timeline(self) -> list[dict]:
        return [scene.to_dict() for scene in self.scenes]

    def get_context_summary(self) -> str:
        """Build a summary of the current story state for the LLM context."""
        parts = [f"Story: {self.title}"]
        if self.genre:
            parts.append(f"Genre: {self.genre}")
        if self.characters:
            names = ", ".join(c.name for c in self.characters)
            parts.append(f"Characters: {names}")
        if self.current_scene:
            parts.append(f"Current scene: {self.current_scene.title}")
            parts.append(f"Mood: {self.current_scene.mood.value}")
        parts.append(f"Total scenes: {len(self.scenes)}")
        return "\n".join(parts)

    def to_dict(self) -> dict:
        return {
            "sessionId": self.session_id,
            "title": self.title,
            "genre": self.genre,
            "scenes": [s.to_dict() for s in self.scenes],
            "characters": [c.to_dict() for c in self.characters],
            "currentSceneIndex": self.current_scene_index,
            "createdAt": self.created_at,
        }
