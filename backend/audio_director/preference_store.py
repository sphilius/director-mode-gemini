"""Preference / baseline learner (v1: log + simple baseline).

Every generation and every keep/reject decision is appended to a JSONL event
log. `baseline_for()` returns the mean of the config settings from your ACCEPTED
takes for a character — a cold-startable "vocal tuning fingerprint" that pre-seeds
future generations toward what you actually keep, shrinking the regen multiplier
that dominates ElevenLabs cost.

This is the Regularizer that prevents "no data to learn from later." The full
recommender is deferred (Heuristic) — this just captures clean data and gives a
usable mean today.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).resolve().parent / "data"
EVENT_LOG = DATA_DIR / "preferences.jsonl"

_CONFIG_FIELDS = ("stability", "similarity", "style", "speed", "guidance", "loudness")


def _append(event: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    event = {"ts": time.time(), **event}
    with EVENT_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event) + "\n")


def record_generation(character: str, category: str, filename: str, engine: str,
                      model: str, config: dict, credits: float = 0.0) -> None:
    _append({
        "type": "generation",
        "character": character,
        "category": category,
        "filename": filename,
        "engine": engine,
        "model": model,
        "config": config,
        "credits": credits,
    })


def record_decision(character: str, filename: str, accepted: bool,
                    config: Optional[dict] = None) -> None:
    _append({
        "type": "decision",
        "character": character,
        "filename": filename,
        "accepted": bool(accepted),
        "config": config or {},
    })


def config_for_filename(filename: str) -> dict:
    """Look up the config used to generate a file (most recent generation event)."""
    for e in reversed(_read_events()):
        if e.get("type") == "generation" and e.get("filename") == filename:
            return e.get("config", {})
    return {}


def _read_events() -> list[dict]:
    if not EVENT_LOG.exists():
        return []
    events = []
    for line in EVENT_LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


def baseline_for(character: str) -> dict:
    """Mean config across ACCEPTED takes for this character. Empty if no data yet."""
    accepted = [
        e for e in _read_events()
        if e.get("type") == "decision" and e.get("accepted")
        and e.get("character") == character and e.get("config")
    ]
    if not accepted:
        return {}
    baseline: dict = {}
    for field in _CONFIG_FIELDS:
        vals = [e["config"][field] for e in accepted if isinstance(e["config"].get(field), (int, float))]
        if vals:
            baseline[field] = round(sum(vals) / len(vals), 3)
    baseline["_samples"] = len(accepted)
    return baseline


def global_baseline() -> dict:
    """Cross-character tendencies from all accepted takes."""
    accepted = [
        e for e in _read_events()
        if e.get("type") == "decision" and e.get("accepted") and e.get("config")
    ]
    if not accepted:
        return {}
    out: dict = {}
    for field in _CONFIG_FIELDS:
        vals = [e["config"][field] for e in accepted if isinstance(e["config"].get(field), (int, float))]
        if vals:
            out[field] = round(sum(vals) / len(vals), 3)
    out["_samples"] = len(accepted)
    return out
