import os

# The corrected content for director_agent.py
NEW_CONTENT = """\"\"\"Director Agent — the core AI agent that powers Director Mode.

Uses Google's Gemini API to interpret director-style commands and
evolve an interactive story. The agent maintains conversation context
and manipulates the shared StoryState.
\"\"\"

from __future__ import annotations

import json
import os
from typing import AsyncIterator, Optional

from google import genai
from google.genai import types

from backend.utils.story_state import Character, Mood, Scene, StoryState

SYSTEM_INSTRUCTION = \"\"\"\\
You are **Director**, an AI creative partner that helps users direct \\
interactive stories in real time. You respond to natural-language \\
directing commands — like "pan to the harbour", "add a mysterious stranger", \\
or "make the mood tense" — and produce vivid, cinematic scene descriptions.

Rules:
1. Always stay in character as a film/theatre director's assistant.
2. When the user gives a directing cue, narrate what happens on the \\
   "stage" in 2-4 evocative sentences.
3. Return structured JSON when asked for scene or character metadata.
4. Keep continuity — reference earlier scenes and characters naturally.
5. If the user says "cut", end the current scene gracefully and \\
   summarise it in one line.
\"\"\"

SCENE_FUNCTION = types.FunctionDeclaration(
    name="update_scene",
    description="Update the current scene's metadata based on the director's cue.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "title": types.Schema(type=types.Type.STRING, description="Short scene title"),
            "description": types.Schema(type=types.Type.STRING, description="Vivid scene description"),
            "mood": types.Schema(
                type=types.Type.STRING,
                description="Scene mood",
                enum=[m.value for m in Mood],
            ),
            "directorNotes": types.Schema(type=types.Type.STRING, description="Internal notes for continuity"),
        },
        required=["title", "description", "mood"],
    ),
)

CHARACTER_FUNCTION = types.FunctionDeclaration(
    name="introduce_character",
    description="Introduce or update a character in the story.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "name": types.Schema(type=types.Type.STRING, description="Character name"),
            "description": types.Schema(type=types.Type.STRING, description="Brief character description"),
            "motivation": types.Schema(type=types.Type.STRING, description="Character motivation"),
        },
        required=["name", "description"],
    ),
)

TOOLS = types.Tool(function_declarations=[SCENE_FUNCTION, CHARACTER_FUNCTION])


class DirectorAgent:
    \"\"\"Wraps the Gemini generative model with Director Mode behaviour.\"\"\"

    def __init__(self, story_state: Optional[StoryState] = None) -> None:
        # FIX 1: Use Vertex AI credentials from environment
        self.client = genai.Client(
            vertexai=True,
            project=os.environ["VERTEX_AI_PROJECT"],
            location=os.environ["VERTEX_AI_LOCATION"]
        )
        self.model_id = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
        self.story = story_state or StoryState()
        self.history: list[types.Content] = []

    async def direct(self, user_input: str) -> dict:
        \"\"\"Process a director command and return the response + state updates.\"\"\"
        self.history.append(types.Content(role="user", parts=[types.Part(text=user_input)]))

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            tools=[TOOLS],
            temperature=0.9,
            max_output_tokens=1024,
        )

        response = await self.client.aio.models.generate_content(
            model=self.model_id,
            contents=self.history,
            config=config,
        )

        narration = ""
        state_updates: list[dict] = []

        if response.candidates:
            for candidate in response.candidates:
                for part in candidate.content.parts:
                    if part.text:
                        narration += part.text
                    if part.function_call:
                        result = self._handle_function_call(
                            part.function_call.name,
                            dict(part.function_call.args),
                        )
                        state_updates.append(result)

        # Append assistant turn to history
        self.history.append(types.Content(role="model", parts=[types.Part(text=narration or "...")]))

        return {
            "narration": narration,
            "stateUpdates": state_updates,
            "story": self.story.to_dict(),
        }

    async def direct_stream(self, user_input: str) -> AsyncIterator[str]:
        \"\"\"Stream a director response token-by-token.\"\"\"
        self.history.append(types.Content(role="user", parts=[types.Part(text=user_input)]))

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            tools=[TOOLS],
            temperature=0.9,
            max_output_tokens=1024,
        )

        full_text = ""
        
        # FIX 2: Await the stream creation
        stream = await self.client.aio.models.generate_content_stream(
            model=self.model_id,
            contents=self.history,
            config=config,
        )

        async for chunk in stream:
            if not chunk.candidates:
                continue
            for part in chunk.candidates[0].content.parts:
                if part.text:
                    full_text += part.text
                    yield json.dumps({"type": "token", "data": part.text}) + "\\n"
                if part.function_call:
                    result = self._handle_function_call(
                        part.function_call.name,
                        dict(part.function_call.args),
                    )
                    yield json.dumps({"type": "state_update", "data": result}) + "\\n"

        self.history.append(types.Content(role="model", parts=[types.Part(text=full_text or "...")]))
        yield json.dumps({"type": "done", "data": self.story.to_dict()}) + "\\n"

    def _handle_function_call(self, name: str, args: dict) -> dict:
        if name == "update_scene":
            scene = Scene(
                title=args.get("title", "Untitled"),
                description=args.get("description", ""),
                mood=Mood(args.get("mood", "calm")),
                director_notes=args.get("directorNotes", ""),
            )
            self.story.add_scene(scene)
            return {"action": "scene_updated", "scene": scene.to_dict()}

        if name == "introduce_character":
            character = Character(
                name=args.get("name", "Unknown"),
                description=args.get("description", ""),
                motivation=args.get("motivation", ""),
            )
            self.story.add_character(character)
            return {"action": "character_introduced", "character": character.to_dict()}

        return {"action": "unknown", "name": name}

    def reset(self) -> None:
        self.story = StoryState()
        self.history.clear()
"""

# Write the file
file_path = "backend/agents/director_agent.py"
with open(file_path, "w") as f:
    f.write(NEW_CONTENT)

print(f"✅ Successfully patched {file_path}")
