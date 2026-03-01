"""Director Mode — FastAPI backend.

Exposes REST and WebSocket endpoints for the Director Mode frontend.
Maintains per-session DirectorAgent instances so each user gets an
independent story context.
"""

from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.agents.director_agent import DirectorAgent
from backend.utils.story_state import StoryState

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
    sessions.clear()


app = FastAPI(
    title="Director Mode",
    description="AI-powered interactive story directing with Gemini",
    version="0.1.0",
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
        sessions[session_id].reset()
    return {"status": "reset", "session_id": session_id}


# ---------------------------------------------------------------------------
# WebSocket for streaming
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
