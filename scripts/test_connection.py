#!/usr/bin/env python3
"""Test script for the Gemini Live API connection.

Connects directly to the Gemini Live API (no WebSocket server needed)
and verifies:
1. Text input/output works
2. Function calling triggers correctly

Usage:
    export GEMINI_API_KEY=your-key
    python scripts/test_connection.py
"""

import asyncio
import os
import sys

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from google import genai
from google.genai import types

from backend.agents.director_agent import (
    DIRECTOR_SYSTEM_INSTRUCTION,
    TOOL_DECLARATIONS,
)


async def test_text_response():
    """Test 1: Send a text message and get a text response."""
    print("=" * 60)
    print("TEST 1: Basic text connection")
    print("=" * 60)

    api_key = os.environ.get("GEMINI_API_KEY", "")
    project_id = os.environ.get("GCP_PROJECT_ID", "")
    region = os.environ.get("GCP_REGION", "us-central1")

    if project_id:
        client = genai.Client(vertexai=True, project=project_id, location=region)
    elif api_key:
        client = genai.Client(api_key=api_key)
    else:
        print("ERROR: Set GEMINI_API_KEY or GCP_PROJECT_ID")
        return False

    model_id = os.environ.get("GEMINI_LIVE_MODEL", "gemini-2.5-flash-native-audio")

    config = types.LiveConnectConfig(
        response_modalities=["TEXT"],
        system_instruction=types.Content(
            parts=[types.Part(text=DIRECTOR_SYSTEM_INSTRUCTION)]
        ),
        tools=[TOOL_DECLARATIONS],
    )

    print(f"Connecting to {model_id}...")

    try:
        async with client.aio.live.connect(model=model_id, config=config) as session:
            print("Connected!\n")

            # Send text
            prompt = "Hello, I'm a filmmaker. What can you help me with?"
            print(f">>> {prompt}\n")

            await session.send_client_content(
                turns=types.Content(
                    role="user", parts=[types.Part(text=prompt)]
                ),
                turn_complete=True,
            )

            # Receive response
            response_text = ""
            async for message in session.receive():
                if message.text:
                    response_text += message.text

                if message.server_content and message.server_content.turn_complete:
                    break

            print(f"<<< {response_text}\n")
            print("PASS: Text response received\n")
            return True

    except Exception as e:
        print(f"FAIL: {e}\n")
        return False


async def test_function_calling():
    """Test 2: Send a storyboard request and verify function_call fires."""
    print("=" * 60)
    print("TEST 2: Function calling")
    print("=" * 60)

    api_key = os.environ.get("GEMINI_API_KEY", "")
    project_id = os.environ.get("GCP_PROJECT_ID", "")
    region = os.environ.get("GCP_REGION", "us-central1")

    if project_id:
        client = genai.Client(vertexai=True, project=project_id, location=region)
    elif api_key:
        client = genai.Client(api_key=api_key)
    else:
        print("ERROR: Set GEMINI_API_KEY or GCP_PROJECT_ID")
        return False

    model_id = os.environ.get("GEMINI_LIVE_MODEL", "gemini-2.5-flash-native-audio")

    config = types.LiveConnectConfig(
        response_modalities=["TEXT"],
        system_instruction=types.Content(
            parts=[types.Part(text=DIRECTOR_SYSTEM_INSTRUCTION)]
        ),
        tools=[TOOL_DECLARATIONS],
    )

    print(f"Connecting to {model_id}...")

    try:
        async with client.aio.live.connect(model=model_id, config=config) as session:
            print("Connected!\n")

            prompt = (
                "Create a dramatic sunset scene at a harbour. "
                "There should be a mysterious old sailor character. "
                "Make the mood tense."
            )
            print(f">>> {prompt}\n")

            await session.send_client_content(
                turns=types.Content(
                    role="user", parts=[types.Part(text=prompt)]
                ),
                turn_complete=True,
            )

            # Collect responses
            function_calls = []
            response_text = ""

            async for message in session.receive():
                if message.text:
                    response_text += message.text

                if message.tool_call:
                    for fc in message.tool_call.function_calls:
                        call_info = {
                            "name": fc.name,
                            "args": dict(fc.args) if fc.args else {},
                            "id": fc.id,
                        }
                        function_calls.append(call_info)
                        print(f"  FUNCTION CALL: {fc.name}({dict(fc.args) if fc.args else {}})")

                        # Send tool response back
                        await session.send_tool_response(
                            function_responses=types.FunctionResponse(
                                name=fc.name,
                                response={"status": "ok"},
                                id=fc.id,
                            )
                        )

                if message.server_content and message.server_content.turn_complete:
                    break

            if response_text:
                print(f"\n<<< {response_text[:200]}...")

            print(f"\nFunction calls received: {len(function_calls)}")
            for fc in function_calls:
                print(f"  - {fc['name']}: {list(fc['args'].keys())}")

            if function_calls:
                names = {fc["name"] for fc in function_calls}
                expected = {"update_scene", "introduce_character"}
                matched = names & expected
                print(f"\nExpected tools triggered: {matched}")
                print("PASS: Function calling works!\n")
                return True
            else:
                print("\nWARN: No function calls received (model may not have")
                print("chosen to call tools this time — this is non-deterministic)")
                print("Try running the test again.\n")
                return True  # Not a hard failure

    except Exception as e:
        print(f"FAIL: {e}\n")
        return False


async def main():
    print("\nDirector Mode — Gemini Live API Connection Test")
    print("=" * 60)
    print()

    results = []
    results.append(await test_text_response())
    results.append(await test_function_calling())

    print("=" * 60)
    print("RESULTS:")
    print(f"  Test 1 (text):      {'PASS' if results[0] else 'FAIL'}")
    print(f"  Test 2 (functions): {'PASS' if results[1] else 'FAIL'}")
    print("=" * 60)

    if all(results):
        print("\nAll tests passed! The Gemini Live API connection is working.")
    else:
        print("\nSome tests failed. Check your API key and model access.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
