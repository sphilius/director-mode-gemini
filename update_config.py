import os
import subprocess

# 1. Get external IP to keep VITE_WS_URL correct
try:
    external_ip = subprocess.check_output(
        ['curl', '-s', '-H', 'Metadata-Flavor: Google',
         'http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip']
    ).decode('utf-8').strip()
except Exception:
    external_ip = "localhost"

# 2. Define the new configuration
env_content = f"""PORT=8000
VITE_WS_URL=ws://{external_ip}:8000/ws/direct/default
CORS_ORIGINS=http://{external_ip}:5173
VERTEX_AI_PROJECT=gemini-live-agent-488820
VERTEX_AI_LOCATION=us-central1

# --- User Requested Models ---
GEMINI_MODEL=gemini-2.5-pro
GEMINI_LIVE_MODEL=gemini-live-2.5-flash-native-audio
VERTEX_AI_IMAGE_MODEL=imagen-3.0-generate-002
VERTEX_AI_VIDEO_MODEL=veo-3.0-generate
VERTEX_AI_MUSIC_MODEL=lyria-002
"""

with open(".env", "w") as f:
    f.write(env_content)
print("✅ Updated .env with new model versions.")

# 3. Define corrected director_agent.py content
agent_code = r'''"""Director Agent — the core AI agent that powers Director Mode."""
from __future__ import annotations

import base64
import json
import os
from typing import AsyncIterator, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types

from backend.utils.story_state import Character, Mood, Scene, StoryState

# Force load environment variables
load_dotenv()

SYSTEM_INSTRUCTION = """\
You are **Director**, an AI creative partner that helps users direct \
interactive stories in real time. You respond to natural-language \
directing commands.

Rules:
1. Always stay in character as a film/theatre director's assistant.
2. When the user gives a directing cue, narrate what happens on the \
   "stage" in 2-4 evocative sentences.
3. NEVER output raw JSON in your narrative response. When scene details \
   (like title, description, or mood) change, ALWAYS use the `update_scene` tool.
4. Keep continuity — reference earlier scenes and characters naturally.
5. If the user says "cut", end the current scene gracefully and \
   summarise it in one line.
"""

SCENE_FUNCTION = types.FunctionDeclaration(
    name="update_scene",
    description="Update the current scene's metadata based on the director's cue.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "title": types.Schema(type=types.Type.STRING, description="Short scene title"),
            "description": types.Schema(type=types.Type.STRING, description="Vivid scene description"),
            "mood": types.Schema(type=types.Type.STRING, description="Scene mood", enum=[m.value for m in Mood]),
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
    """Wraps the Gemini generative model with Director Mode behaviour."""

    def __init__(self, story_state: Optional[StoryState] = None) -> None:
        self.client = genai.Client(
            vertexai=True,
            project=os.environ.get("VERTEX_AI_PROJECT"),
            location=os.environ.get("VERTEX_AI_LOCATION", "us-central1")
        )
        self.model_id = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
        # Load image model from env
        self.image_model_id = os.environ.get("VERTEX_AI_IMAGE_MODEL", "imagen-3.0-generate-001")
        self.story = story_state or StoryState()
        self.history: list[types.Content] = []

    async def direct(self, user_input: str) -> dict:
        self.history.append(types.Content(role="user", parts=[types.Part(text=user_input)]))
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            tools=[TOOLS],
            temperature=0.4,
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
                    if part.text: narration += part.text
                    if part.function_call:
                        result = await self._handle_function_call(
                            part.function_call.name, dict(part.function_call.args)
                        )
                        state_updates.append(result)
        self.history.append(types.Content(role="model", parts=[types.Part(text=narration or "...")]))
        return {"narration": narration, "stateUpdates": state_updates, "story": self.story.to_dict()}

    async def direct_stream(self, user_input: str) -> AsyncIterator[str]:
        self.history.append(types.Content(role="user", parts=[types.Part(text=user_input)]))
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            tools=[TOOLS],
            temperature=0.4,
            max_output_tokens=1024,
        )
        full_text = ""
        stream = await self.client.aio.models.generate_content_stream(
            model=self.model_id,
            contents=self.history,
            config=config,
        )
        async for chunk in stream:
            if not chunk.candidates: continue
            for part in chunk.candidates[0].content.parts:
                if part.text:
                    full_text += part.text
                    yield json.dumps({"type": "token", "data": part.text}) + "\n"
                if part.function_call:
                    result = await self._handle_function_call(
                        part.function_call.name, dict(part.function_call.args)
                    )
                    event_type = result.get("action", "state_update")
                    yield json.dumps({"type": event_type, "data": result}) + "\n"
        self.history.append(types.Content(role="model", parts=[types.Part(text=full_text or "...")]))
        yield json.dumps({"type": "done", "data": self.story.to_dict()}) + "\n"

    async def _handle_function_call(self, name: str, args: dict) -> dict:
        if name == "update_scene":
            if self.story.current_scene:
                scene = self.story.current_scene
                scene.title = args.get("title", scene.title)
                scene.description = args.get("description", scene.description)
                scene.mood = Mood(args.get("mood", scene.mood.value))
                scene.director_notes = args.get("directorNotes", scene.director_notes)
            else:
                scene = Scene(
                    title=args.get("title", "Untitled"),
                    description=args.get("description", ""),
                    mood=Mood(args.get("mood", "calm")),
                    director_notes=args.get("directorNotes", ""),
                )
                self.story.add_scene(scene)
            
            try:
                print(f"Generating image for: {scene.title} using {self.image_model_id}...")
                image_response = await self.client.aio.models.generate_images(
                    model=self.image_model_id,
                    prompt=f"{scene.description}. {scene.mood.value} mood. Cinematic lighting, high quality, storyboard style.",
                    config=types.GenerateImagesConfig(number_of_images=1)
                )
                if image_response.images:
                    image_bytes = image_response.images[0].image_bytes
                    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
                    scene_data = scene.to_dict()
                    scene_data["imageUrl"] = f"data:image/png;base64,{image_b64}"
                    return {"action": "scene_updated", "scene": scene_data}
            except Exception as e:
                print(f"Image generation failed: {e}")
                return {"action": "scene_updated", "scene": scene.to_dict()}
            
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
'''

with open("backend/agents/director_agent.py", "w") as f:
    f.write(agent_code)
print("✅ Updated backend/agents/director_agent.py with dynamic model loading.")
