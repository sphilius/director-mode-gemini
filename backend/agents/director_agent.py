"""Director Agent — the core AI agent that powers Director Mode.

Uses the Gemini Multimodal Live API for real-time bidirectional streaming
of audio/text. The agent maintains conversation context and manipulates
the shared StoryState via function calling.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
from typing import Any, AsyncIterator, Optional

from google import genai
from google.genai import types

from backend.utils.story_state import Character, Mood, Scene, StoryState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System instruction — engineered for the creative storyteller challenge
# ---------------------------------------------------------------------------
DIRECTOR_SYSTEM_INSTRUCTION = """\
You are **Director**, an AI creative partner that helps users direct \
interactive stories in real time. You respond to natural-language \
directing commands — like "pan to the harbour", "add a mysterious stranger", \
or "make the mood tense" — and produce vivid, cinematic scene descriptions.

Rules:
1. Always stay in character as a film/theatre director's assistant.
2. When the user gives a directing cue, narrate what happens on the \
   "stage" in 2-4 evocative sentences.
3. Use the update_scene tool whenever a new scene begins or the mood, \
   setting, or tone changes significantly.
4. Use the introduce_character tool whenever a new character appears or \
   an existing character's role changes.
5. Keep continuity — reference earlier scenes and characters naturally.
6. If the user says "cut", end the current scene gracefully and \
   summarise it in one line.
7. When responding with audio, speak dramatically like a narrator — \
   varied pacing, evocative tone.
"""

# ---------------------------------------------------------------------------
# Tool declarations (function calling)
# ---------------------------------------------------------------------------
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

STORYBOARD_FUNCTION = types.FunctionDeclaration(
    name="generate_storyboard",
    description="Generate a storyboard breakdown for a requested scene.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "scene_title": types.Schema(type=types.Type.STRING, description="Title for the storyboard scene"),
            "shots": types.Schema(
                type=types.Type.ARRAY,
                items=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "shot_type": types.Schema(type=types.Type.STRING, description="e.g. wide, close-up, over-the-shoulder"),
                        "description": types.Schema(type=types.Type.STRING, description="What the shot shows"),
                    },
                ),
                description="List of shots in the storyboard",
            ),
        },
        required=["scene_title"],
    ),
)

TOOL_DECLARATIONS = types.Tool(
    function_declarations=[SCENE_FUNCTION, CHARACTER_FUNCTION, STORYBOARD_FUNCTION]
)


class DirectorAgent:
    """Wraps the Gemini Multimodal Live API with Director Mode behaviour.

    Supports two modes:
    - Live (bidi streaming): real-time audio/text via WebSocket
    - Standard (request/response): text-only via REST
    """

    def __init__(self, story_state: Optional[StoryState] = None) -> None:
        api_key = os.environ.get("GEMINI_API_KEY", "")
        project_id = os.environ.get("GCP_PROJECT_ID", "")
        region = os.environ.get("GCP_REGION", "us-central1")

        # Use Vertex AI if project is configured, otherwise use API key
        if project_id:
            self.client = genai.Client(
                vertexai=True, project=project_id, location=region
            )
        else:
            self.client = genai.Client(api_key=api_key)

        self.live_model_id = os.environ.get(
            "GEMINI_LIVE_MODEL", "gemini-2.5-flash-native-audio"
        )
        self.text_model_id = os.environ.get(
            "GEMINI_MODEL", "gemini-2.5-flash-preview-05-20"
        )
        self.story = story_state or StoryState()
        self.history: list[types.Content] = []

        # Live session state
        self._session: Any = None
        self._live_context: Any = None
        self._session_lock = asyncio.Lock()
        self._connected = False

    # ------------------------------------------------------------------
    # Live API — bidirectional streaming
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Establish a live session with the Gemini Multimodal Live API."""
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=types.Content(
                parts=[types.Part(text=DIRECTOR_SYSTEM_INSTRUCTION)]
            ),
            tools=[TOOL_DECLARATIONS],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Puck",
                    )
                ),
            ),
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
        )

        self._live_context = self.client.aio.live.connect(
            model=self.live_model_id,
            config=config,
        )
        self._session = await self._live_context.__aenter__()
        self._connected = True
        logger.info("Live session established with model %s", self.live_model_id)

    async def disconnect(self) -> None:
        """Close the live session."""
        if self._session and self._connected:
            try:
                await self._live_context.__aexit__(None, None, None)
            except Exception:
                logger.debug("Session already closed")
            self._session = None
            self._live_context = None
            self._connected = False
            logger.info("Live session closed")

    @property
    def is_connected(self) -> bool:
        return self._connected and self._session is not None

    async def send_audio(self, audio_bytes: bytes) -> None:
        """Forward a PCM audio chunk to the live session.

        Audio format: PCM 16-bit, 16kHz, mono.
        The Gemini API accepts 16kHz natively.
        """
        if not self.is_connected:
            raise RuntimeError("Not connected to live session")

        await self._session.send_realtime_input(
            audio=types.Blob(data=audio_bytes, mime_type="audio/pcm;rate=16000")
        )

    async def send_text(self, text: str) -> None:
        """Send a text directive to the live session."""
        if not self.is_connected:
            raise RuntimeError("Not connected to live session")

        await self._session.send_client_content(
            turns=types.Content(
                role="user", parts=[types.Part(text=text)]
            )
        )

    async def interrupt(self) -> None:
        """Signal to stop current generation.

        In the Live API, sending new audio input automatically triggers
        interruption via VAD. For explicit interruption from a button,
        we send audio_stream_end.
        """
        if not self.is_connected:
            return

        try:
            await self._session.send_realtime_input(audio_stream_end=True)
        except Exception as e:
            logger.warning("Interrupt failed: %s", e)

    async def receive_responses(self) -> AsyncIterator[dict]:
        """Receive and yield responses from the live session.

        Yields dicts with types:
        - {"type": "audio", "data": "<base64 pcm>"}
        - {"type": "text", "data": "..."}
        - {"type": "transcript_in", "data": "..."}
        - {"type": "transcript_out", "data": "..."}
        - {"type": "state_update", "data": {...}}
        - {"type": "turn_complete", "data": {...}}
        - {"type": "error", "data": "..."}
        """
        if not self.is_connected:
            return

        try:
            async for message in self._session.receive():
                # Handle tool calls (function calling)
                if message.tool_call:
                    for fc in message.tool_call.function_calls:
                        result = self._handle_function_call(
                            fc.name, dict(fc.args) if fc.args else {}
                        )
                        yield {"type": "state_update", "data": result}

                        # Send tool response back to the model
                        await self._session.send_tool_response(
                            function_responses=types.FunctionResponse(
                                name=fc.name,
                                response=result,
                                id=fc.id,
                            )
                        )

                # Handle server content (audio, text, transcriptions)
                if message.server_content:
                    sc = message.server_content

                    # Input transcription
                    if sc.input_transcription and sc.input_transcription.text:
                        yield {
                            "type": "transcript_in",
                            "data": sc.input_transcription.text,
                        }

                    # Output transcription
                    if sc.output_transcription and sc.output_transcription.text:
                        yield {
                            "type": "transcript_out",
                            "data": sc.output_transcription.text,
                        }

                    # Model turn — audio and text parts
                    if sc.model_turn and sc.model_turn.parts:
                        for part in sc.model_turn.parts:
                            if part.inline_data and part.inline_data.data:
                                yield {
                                    "type": "audio",
                                    "data": base64.b64encode(
                                        part.inline_data.data
                                    ).decode("ascii"),
                                }
                            if part.text:
                                yield {"type": "text", "data": part.text}

                    # Turn complete signal
                    if sc.turn_complete:
                        yield {
                            "type": "turn_complete",
                            "data": self.story.to_dict(),
                        }

        except Exception as e:
            logger.error("Error receiving from live session: %s", e)
            self._connected = False
            yield {"type": "error", "data": str(e)}

    # ------------------------------------------------------------------
    # Standard API — text request/response (fallback)
    # ------------------------------------------------------------------

    async def direct(self, user_input: str) -> dict:
        """Process a director command via the standard (non-live) API."""
        self.history.append(
            types.Content(role="user", parts=[types.Part(text=user_input)])
        )

        config = types.GenerateContentConfig(
            system_instruction=DIRECTOR_SYSTEM_INSTRUCTION,
            tools=[TOOL_DECLARATIONS],
            temperature=0.9,
            max_output_tokens=1024,
        )

        response = await self.client.aio.models.generate_content(
            model=self.text_model_id,
            contents=self.history,
            config=config,
        )

        narration = ""
        state_updates: list[dict] = []

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

        self.history.append(
            types.Content(role="model", parts=[types.Part(text=narration or "...")])
        )

        return {
            "narration": narration,
            "stateUpdates": state_updates,
            "story": self.story.to_dict(),
        }

    async def direct_stream(self, user_input: str) -> AsyncIterator[str]:
        """Stream a director response token-by-token (standard API)."""
        self.history.append(
            types.Content(role="user", parts=[types.Part(text=user_input)])
        )

        config = types.GenerateContentConfig(
            system_instruction=DIRECTOR_SYSTEM_INSTRUCTION,
            tools=[TOOL_DECLARATIONS],
            temperature=0.9,
            max_output_tokens=1024,
        )

        full_text = ""
        async for chunk in self.client.aio.models.generate_content_stream(
            model=self.text_model_id,
            contents=self.history,
            config=config,
        ):
            for part in chunk.candidates[0].content.parts:
                if part.text:
                    full_text += part.text
                    yield json.dumps({"type": "token", "data": part.text}) + "\n"
                if part.function_call:
                    result = self._handle_function_call(
                        part.function_call.name,
                        dict(part.function_call.args),
                    )
                    yield json.dumps({"type": "state_update", "data": result}) + "\n"

        self.history.append(
            types.Content(role="model", parts=[types.Part(text=full_text or "...")])
        )
        yield json.dumps({"type": "done", "data": self.story.to_dict()}) + "\n"

    # ------------------------------------------------------------------
    # Function call routing
    # ------------------------------------------------------------------

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

        if name == "generate_storyboard":
            storyboard = {
                "scene_title": args.get("scene_title", "Untitled"),
                "shots": args.get("shots", []),
            }
            return {"action": "storyboard_generated", "storyboard": storyboard}

        return {"action": "unknown", "name": name}

    def reset(self) -> None:
        self.story = StoryState()
        self.history.clear()
        self._connected = False
        self._session = None
        self._live_context = None
