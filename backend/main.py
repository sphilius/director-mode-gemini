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

# Allowed browser origins, from the CORS_ORIGINS env var (comma-separated).
#
# The default covers the usual local dev ports, so `uvicorn backend.main:app`
# still works out of the box with no env set. Set CORS_ORIGINS in deployment.
#
# SECURITY: "*" is filtered out rather than honoured. A wildcard origin lets any
# website call this API from a visitor's browser, and it is what makes the
# WebSocket check below meaningless. The .strip() tolerates "a.com, b.com"
# (a space after the comma would otherwise never match) and stops " *" from
# slipping past the wildcard filter.
#
# NOTE: setting CORS_ORIGINS to only "*" yields an EMPTY list and refuses all
# cross-origin requests. That is deliberate — list real origins.
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip() and origin.strip() != "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    # No cookie or session auth exists here — nothing sets or reads cookies, and
    # session ids travel in the URL path. So credentials are never needed.
    allow_credentials=False,
    # Only the methods this API serves: every HTTP route is @app.get or
    # @app.post. OPTIONS is required for the browser's CORS preflight.
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
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
    print(f"\\n--- WEBSOCKET HANDSHAKE INITIATED FOR SESSION: {session_id} ---\\n")

    # SECURITY: CORSMiddleware does NOT protect this endpoint. Starlette applies
    # it only to HTTP scopes, and browsers send no CORS preflight for a WebSocket
    # handshake — so without this check ANY website could open a socket here in a
    # visitor's browser and drive the agent on their behalf. That attack is called
    # cross-site WebSocket hijacking (CSWSH).
    #
    # Browsers ALWAYS send Origin on a WS handshake, so a mismatch is a real
    # cross-site attempt -> refuse. A MISSING Origin means a non-browser client
    # (curl, a script, tests), which cannot be a cross-site attack, so it is
    # allowed rather than breaking local tooling.
    origin = websocket.headers.get("origin")
    if origin is not None and origin not in ALLOWED_ORIGINS:
        print(f"\\n--- WEBSOCKET REJECTED, DISALLOWED ORIGIN: {origin} ---\\n")
        # Close BEFORE accept() so the handshake is refused outright and no agent
        # or session is created. 1008 = policy violation.
        await websocket.close(code=1008)
        return

    try:
        await websocket.accept()
        print(f"\\n--- WEBSOCKET ACCEPTED FOR SESSION: {session_id} ---\\n")
    except Exception as e:
        print(f"\\n--- WEBSOCKET FAILED TO ACCEPT: {str(e)} ---\\n")
        return
    agent = get_or_create_agent(session_id)

    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            prompt = payload.get("prompt", "")

            try:
                async for chunk in agent.direct_stream(prompt):
                    await websocket.send_text(chunk)
            except Exception as e:
                import traceback
                print(f"\\n--- WEBSOCKET STREAM ERROR ---\\n")
                traceback.print_exc()
                await websocket.send_text(json.dumps({"type": "error", "data": f"Backend Error: {str(e)}"}))
    except WebSocketDisconnect:
        pass
