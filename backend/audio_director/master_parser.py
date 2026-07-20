"""Parse the streamlined master voice-prompt document.

Format (markdown). Each character is an H2 (`## Name`). Under it:

    ## Iris
    **Voice Design Prompt:** A warm, slightly raspy alto in her 30s...
    **Preview Text:** Hey there — ready to knock out today's quests?
    **Personality:** Encouraging, a little sardonic, never saccharine.

    Config:
    - stability: 40
    - similarity: 75
    - style: 60
    - speed: 1.0
    - guidance: 30
    - loudness: 0

    ### Lines
    - [greeting] Morning! Let's make today count.
    - [greeting] [excited] You showed up — that's half the battle.
    - [streak-at-risk] Careful — your streak is about to slip.
    - [level-up] Level up. You earned it.

Line rule: the FIRST [bracket] on a line is its category. Any further
[bracket] tokens are ElevenLabs v3 emotion tags — kept inline in the text
(v3 reads them in place) and also recorded as metadata.
"""

from __future__ import annotations

import re
from pathlib import Path

from backend.audio_director.models import CharacterVoice, LineSpec, VoiceConfig

_LABELS = {
    "voice design prompt": "voice_design_prompt",
    "voice design": "voice_design_prompt",
    "design prompt": "voice_design_prompt",
    "preview text": "preview_text",
    "preview": "preview_text",
    "personality": "personality",
}

_CONFIG_KEYS = {
    "stability": "stability",
    "similarity": "similarity",
    "similarity_boost": "similarity",
    "style": "style",
    "speed": "speed",
    "guidance": "guidance",
    "loudness": "loudness",
    "use_speaker_boost": "use_speaker_boost",
    "speaker_boost": "use_speaker_boost",
}

_H2 = re.compile(r"^\s*##\s+(?!#)(.+?)\s*$")
_H3 = re.compile(r"^\s*###\s+(.+?)\s*$")
_BOLD_LABEL = re.compile(r"^\s*\*\*(.+?):\*\*\s*(.*)$")
_KV = re.compile(r"^\s*[-*]?\s*([A-Za-z_ ]+?)\s*[:=]\s*(.+?)\s*$")
_BRACKET = re.compile(r"\[([^\]]+)\]")


def parse_master_file(path: str | Path) -> list[CharacterVoice]:
    text = Path(path).read_text(encoding="utf-8")
    return parse_master_text(text)


def parse_master_text(text: str) -> list[CharacterVoice]:
    characters: list[CharacterVoice] = []
    current: CharacterVoice | None = None
    section = ""  # "", "lines", "config"

    for raw in text.splitlines():
        line = raw.rstrip()

        h2 = _H2.match(line)
        if h2:
            current = CharacterVoice(name=h2.group(1).strip())
            characters.append(current)
            section = ""
            continue

        if current is None:
            continue  # skip any preamble before the first character

        h3 = _H3.match(line)
        if h3:
            heading = h3.group(1).strip().lower()
            section = "lines" if "line" in heading else ("config" if "config" in heading else "")
            continue

        if not line.strip():
            continue

        # Bold "**Label:** value" fields
        bold = _BOLD_LABEL.match(line)
        if bold:
            key = bold.group(1).strip().lower()
            val = bold.group(2).strip()
            if key in _LABELS:
                setattr(current, _LABELS[key], val)
                section = ""
                continue
            if key == "config":
                section = "config"
                continue

        # A bare "Config:" line switches mode
        if line.strip().lower().rstrip(":") == "config":
            section = "config"
            continue

        # Lines section
        if section == "lines" and re.match(r"^\s*[-*]\s+", line):
            spec = _parse_line_item(line, len(current.lines))
            if spec:
                current.lines.append(spec)
            continue

        # Config key/value (either explicit config section, or a loose k:v that matches a known key)
        kv = _KV.match(line)
        if kv:
            key = kv.group(1).strip().lower().replace(" ", "_")
            if key in _CONFIG_KEYS:
                _apply_config(current.config, _CONFIG_KEYS[key], kv.group(2).strip())
                continue

    return characters


def _parse_line_item(line: str, index: int) -> LineSpec | None:
    body = re.sub(r"^\s*[-*]\s+", "", line).strip()
    brackets = _BRACKET.findall(body)
    if not brackets:
        # No category — skip but don't crash; caller may treat as uncategorised
        return LineSpec(category="uncategorized", text=body, index=index)
    category = brackets[0].strip()
    emotion_tags = [f"[{b.strip()}]" for b in brackets[1:]]
    # Text = everything after the first bracket token, verbatim (emotion tags stay inline)
    first_close = body.index("]") + 1
    text = body[first_close:].strip()
    return LineSpec(category=category, text=text, index=index, emotion_tags=emotion_tags)


def _apply_config(cfg: VoiceConfig, field_name: str, raw: str) -> None:
    if field_name == "use_speaker_boost":
        cfg.use_speaker_boost = raw.strip().lower() in ("true", "yes", "on", "1")
        return
    try:
        cfg.__setattr__(field_name, float(raw))
    except ValueError:
        pass  # ignore unparseable values rather than crash


def summarize(characters: list[CharacterVoice]) -> str:
    rows = []
    for cv in characters:
        cats = ", ".join(f"{c} x{sum(1 for l in cv.lines if l.category == c)}" for c in cv.categories())
        rows.append(f"  {cv.name:<16} {len(cv.lines):>3} lines  [{cats}]")
    return f"Parsed {len(characters)} character(s):\n" + "\n".join(rows)
