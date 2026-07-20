# Audio Director (v1)

A sub-agent that turns your streamlined master voice-prompt doc into named,
generated audio lines — with pre-spend cost visibility and preference logging.
Lives inside StoryForge (Director Mode); plugs into the Layer-2 TTS slot but runs
standalone from the CLI.

## What v1 does (P/R/H-scoped)

- **Prediction:** parse master doc → estimate cost → generate ElevenLabs lines with **deterministic auto-naming**.
- **Regularizer:** dry-run cost gate before any spend · keep/reject sidecar logging · explicit spend confirmation.
- **Heuristic (deferred):** Gemini routing, hybrid budget allocation, the full preference recommender, autonomous approval, self-hosted TTS.

## Install

```bash
# from repo root, with the project venv active
pip install -r backend/requirements.txt   # adds httpx
```

Set keys in `.env` (already git-ignored):

```
ELEVENLABS_API_KEY=...     # only needed for --execute
GEMINI_API_KEY=...         # already present; used later for Gemini routing
```

## Usage (run from repo root so `backend` imports)

```bash
# 1. Sanity-check parsing
python -m backend.audio_director.cli parse backend/audio_director/sample_master.md

# 2. See what it would cost BEFORE spending (ElevenLabs + Gemini)
python -m backend.audio_director.cli estimate backend/audio_director/sample_master.md --plan creator --regen 2.5

# 3. Dry-run generate (no credits, shows the filenames it would write)
python -m backend.audio_director.cli generate backend/audio_director/sample_master.md

# 4. Actually generate (spends credits; asks for confirmation first)
python -m backend.audio_director.cli generate backend/audio_director/sample_master.md --character Iris --execute

# 5. Inspect the learned tuning baseline once you've marked keeps
python -m backend.audio_director.cli baseline Iris
```

## Master doc format

One character per `##` header. Fields via `**Label:**`. A `Config:` block of
`key: value` lines (stability/similarity/style/speed/guidance/loudness; 0–100 or
0–1 both accepted). Lines under `### Lines` as `- [category] text`, where the
**first** `[bracket]` is the category and any later `[bracket]` tokens are v3
emotion tags kept inline. See `sample_master.md`.

## Output

```
backend/audio_director/out/<character>/chorequest_iris_streak-at-risk_t03_v3.mp3
                                        chorequest_iris_streak-at-risk_t03_v3.mp3.json   # metadata sidecar
backend/audio_director/data/preferences.jsonl                                            # keep/reject log (learning)
```

## Files

| File | Role |
|---|---|
| `pricing.py` | Verified EL + Gemini rates — single source of truth. Update here. |
| `models.py` | Dataclasses (CharacterVoice, LineSpec, VoiceConfig, CostEstimate…). |
| `master_parser.py` | Master markdown → structured characters. |
| `cost_estimator.py` | Per-line/character/total cost, both engines, dry-run report. |
| `naming.py` | Deterministic filenames + JSON sidecars + take numbering. |
| `preference_store.py` | JSONL keep/reject log + baseline fingerprint. |
| `elevenlabs_client.py` | REST wrapper (voice design + line TTS). Spend-gated. |
| `audio_director.py` | Orchestrator. |
| `cli.py` | Command-line entrypoint. |

## Not yet wired (next steps)

- Gemini TTS generator (cost path already estimated; generation deferred).
- Router that sends hero lines → ElevenLabs, bulk → Gemini.
- Preference recommender that pre-seeds config toward `argmax P(accept)`.
- Budget approval Phase 2/3 (assisted → autonomous within a ceiling).
