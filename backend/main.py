"""Director Mode — FastAPI backend.

Exposes REST and WebSocket endpoints for the Director Mode frontend.
Supports two WebSocket modes:
- /ws/direct/{id}   — text-only streaming (standard Gemini API)
- /ws/live/{id}     — bidirectional audio+text (Gemini Live API)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

from backend.agents.director_agent import DirectorAgent
from backend.utils.story_state import StoryState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Session store (in-memory; swap for Redis in production)
# ---------------------------------------------------------------------------
sessions: dict[str, DirectorAgent] = {}


def get_or_create_agent(session_id: str) -> DirectorAgent:
    if session_id not in sessions:
        state = StoryState()
        state.session_id = session_id
        sessions[session_id] = DirectorAgent(story_state=state)
    return sessions[session_id]


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    # Disconnect all live sessions on shutdown
    for agent in sessions.values():
        if agent.is_connected:
            await agent.disconnect()
    sessions.clear()


app = FastAPI(
    title="Director Mode",
    description="AI-powered interactive story directing with Gemini",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class DirectRequest(BaseModel):
    session_id: str = "default"
    prompt: str


class DirectResponse(BaseModel):
    narration: str
    state_updates: list[dict]
    story: dict


class SessionInfo(BaseModel):
    session_id: str
    story: dict


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "ok", "service": "director-mode"}


@app.post("/api/direct", response_model=DirectResponse)
async def direct(req: DirectRequest):
    agent = get_or_create_agent(req.session_id)
    result = await agent.direct(req.prompt)
    return DirectResponse(
        narration=result["narration"],
        state_updates=result["stateUpdates"],
        story=result["story"],
    )


@app.get("/api/session/{session_id}", response_model=SessionInfo)
async def get_session(session_id: str):
    agent = get_or_create_agent(session_id)
    return SessionInfo(session_id=session_id, story=agent.story.to_dict())


@app.post("/api/session/{session_id}/reset")
async def reset_session(session_id: str):
    if session_id in sessions:
        agent = sessions[session_id]
        if agent.is_connected:
            await agent.disconnect()
        agent.reset()
    return {"status": "reset", "session_id": session_id}


# ---------------------------------------------------------------------------
# WebSocket — text-only streaming (standard Gemini API)
# ---------------------------------------------------------------------------
@app.websocket("/ws/direct/{session_id}")
async def ws_direct(websocket: WebSocket, session_id: str):
    await websocket.accept()
    agent = get_or_create_agent(session_id)

    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            prompt = payload.get("prompt", "")

            async for chunk in agent.direct_stream(prompt):
                await websocket.send_text(chunk)
    except WebSocketDisconnect:
        pass


# ---------------------------------------------------------------------------
# WebSocket — bidirectional Live API (audio + text)
# ---------------------------------------------------------------------------
@app.websocket("/ws/live/{session_id}")
async def ws_live(websocket: WebSocket, session_id: str):
    """Bidirectional WebSocket for the Gemini Multimodal Live API.

    Client → Server messages:
    - Binary frame: raw PCM audio bytes (16-bit, 16kHz, mono)
    - Text frame (JSON):
        {"type": "text", "data": "some directive"}
        {"type": "interrupt"}
        {"type": "disconnect"}

    Server → Client messages:
    - Binary frame: raw PCM audio bytes (16-bit, 24kHz, mono)
    - Text frame (JSON):
        {"type": "text", "data": "..."}
        {"type": "transcript_in", "data": "..."}
        {"type": "transcript_out", "data": "..."}
        {"type": "state_update", "data": {...}}
        {"type": "turn_complete", "data": {...story...}}
        {"type": "connected"}
        {"type": "error", "data": "..."}
    """
    await websocket.accept()
    agent = get_or_create_agent(session_id)

    # Establish live session
    try:
        await agent.connect()
        await websocket.send_text(json.dumps({"type": "connected"}))
    except Exception as e:
        logger.error("Failed to connect live session: %s", e)
        await websocket.send_text(
            json.dumps({"type": "error", "data": f"Connection failed: {e}"})
        )
        await websocket.close()
        return

    # Run input and output loops concurrently
    async def input_loop():
        """Read from WebSocket and forward to Gemini Live session."""
        try:
            while True:
                message = await websocket.receive()

                if message.get("type") == "websocket.disconnect":
                    break

                # Binary frame → audio
                if "bytes" in message and message["bytes"]:
                    await agent.send_audio(message["bytes"])

                # Text frame → JSON control message
                elif "text" in message and message["text"]:
                    payload = json.loads(message["text"])
                    msg_type = payload.get("type", "")

                    if msg_type == "text":
                        await agent.send_text(payload.get("data", ""))
                    elif msg_type == "interrupt":
                        await agent.interrupt()
                    elif msg_type == "disconnect":
                        break

        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.error("Input loop error: %s", e)

    async def output_loop():
        """Read from Gemini Live session and forward to WebSocket."""
        try:
            async for response in agent.receive_responses():
                if response["type"] == "audio":
                    # Decode base64 and send as binary frame
                    import base64
                    audio_bytes = base64.b64decode(response["data"])
                    await websocket.send_bytes(audio_bytes)
                else:
                    # Send JSON text frame
                    await websocket.send_text(json.dumps(response))
        except Exception as e:
            logger.error("Output loop error: %s", e)

    try:
        # Run both loops concurrently; when either finishes, cancel the other
        input_task = asyncio.create_task(input_loop())
        output_task = asyncio.create_task(output_loop())

        done, pending = await asyncio.wait(
            [input_task, output_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    finally:
        await agent.disconnect()
