"""Deterministic naming engine + metadata sidecars.

The whole point: control the filename at write time (via API generation) instead
of accepting ElevenLabs' auto-generated GUI names and renaming by hand.

Convention:
    {project}_{character}_{category}_{lineNo:02d}_t{take:02d}_{voiceVersion}.{ext}
    e.g.  chorequest_iris_streak-at-risk_02_t01_v3.mp3

  - lineNo : which line within the category (distinguishes different lines)
  - take   : which regeneration of that line (distinguishes retries; starts at 01)

Every audio file gets a `.json` sidecar recording exactly how it was made — which
doubles as the training data for the preference learner.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from backend.audio_director.models import _slugify


def build_filename(
    project: str,
    character: str,
    category: str,
    line_no: int,
    take: int = 1,
    voice_version: str = "v3",
    ext: str = "mp3",
) -> str:
    parts = [
        _slugify(project),
        _slugify(character),
        _slugify(category),
        f"{line_no:02d}",
        f"t{take:02d}",
        _slugify(voice_version),
    ]
    return "_".join(parts) + f".{ext}"


def next_take(directory: Path, project: str, character: str, category: str,
              line_no: int, voice_version: str) -> int:
    """Next unused take number for one specific line (character+category+lineNo+version)."""
    directory = Path(directory)
    if not directory.exists():
        return 1
    prefix = "_".join([_slugify(project), _slugify(character), _slugify(category), f"{line_no:02d}"])
    version = _slugify(voice_version)
    highest = 0
    pat = re.compile(rf"^{re.escape(prefix)}_t(\d+)_{re.escape(version)}\.\w+$")
    for f in directory.iterdir():
        m = pat.match(f.name)
        if m:
            highest = max(highest, int(m.group(1)))
    return highest + 1


def write_audio(directory: Path, filename: str, audio_bytes: bytes) -> Path:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / filename
    path.write_bytes(audio_bytes)
    return path


def write_sidecar(audio_path: Path, metadata: dict) -> Path:
    """Write `<audio>.json` next to the audio file with full generation metadata."""
    audio_path = Path(audio_path)
    sidecar = audio_path.with_suffix(audio_path.suffix + ".json")
    sidecar.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return sidecar
