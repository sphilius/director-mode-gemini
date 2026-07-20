# StoryForge — V4 Repo Reuse Map (director-mode-gemini)

**Prepared for:** Sasha Philius · **Date:** 2026-07-19
**Companion to:** the StoryForge Consolidated System Design.
**What this is:** a file-by-file inventory of the Director Mode / StoryForge repo (the code behind V4's "Repository Structure Overview" and the `director-mode-gemini.zip`), with a reuse verdict per file keyed to the 4-layer StoryForge architecture.

> **Time to produce:** AI ~15 min. Human equivalent ~2 hrs.

## Provenance & confidence

- **Source of truth:** the *Director Mode Rebuild Plan* (V3, Mar 17) assessed the repo at commit `506d917` — "25 files across backend, frontend, infra, and docs" — and names almost every module explicitly. This map is reconstructed from those named references + the confirmed repo identity (`director-mode-gemini.zip`, 29,736 bytes).
- **Confidence:** High on files V3 names directly (marked ✔). Medium on inferred structure (marked ~). I could **not** extract byte-exact contents this session (the 600KB AI Studio export is a newline-free blob the tools read as binary; the zip needs the disk-down sandbox to unzip).
- **To make it byte-exact:** either (a) re-run once the sandbox has disk, and I'll unzip + diff, or (b) drop `director-mode-gemini.zip` into a connected Cowork folder, or (c) I open the AI Studio prompt via Claude-in-Chrome and read the verbatim dump.

## Reconstructed repo tree + reuse verdicts

Legend — **Reuse:** keep as-is · **Refactor:** keep + modify · **Replace:** gut and rewrite · **New:** planned, not yet built · **Cut:** debug artifact to delete.

### backend/
| File | V3 evidence | State at 506d917 | StoryForge layer | Verdict |
|---|---|---|---|---|
| `main.py` | ✔ FastAPI, WebSocket, `/health`, function calling | Works | L2 | **Refactor** — add `/ws/live/{session_id}` route |
| `director_agent.py` | ✔ `DirectorAgent` wraps google-genai, `direct_stream()`, `update_scene`/`introduce_character` | Works (text only) | L2 | **Refactor** — add `direct_live()`, wrap in ADK, register new tools |
| `models/story_state.py` (~) | ✔ StoryState: scenes, characters, moods, timeline, context-summary builder | Works | **L1 (spine)** | **Reuse** — extend Character with `visual_traits`, `reference_image`, `style_tags` |
| `live/live_session.py` | ✔ Named as NEW in Session 1 (`GeminiLiveSession`, PCM 24kHz, interruption) | Missing | L2 | **New** |
| `live/audio_router.py` | ✔ Named as NEW in Session 1 (browser↔Gemini bridge) | Missing | L2 | **New** |
| `utils/session_store.py` | ✔ Named as NEW in Session 5 (JSON persist to `/tmp/sessions/`) | Missing | L2 (regularizer) | **New** |
| `requirements.txt` | ✔ has google-genai; add google-adk | Works | infra | **Refactor** |
| `fix_agent.py`, `fix_agent_v2.py`, `fix_final.py`, `update_config.py` | ✔ V3 Session 7B: "remove debug artifacts" | Cruft | — | **Cut** |

### frontend/
| File | V3 evidence | State | Layer | Verdict |
|---|---|---|---|---|
| `src/components/DirectorCanvas.jsx` | ✔ currently a scrolling text div | Works (wrong) | L2 | **Replace** — tldraw Editor instance |
| `src/components/VoiceControls.jsx` | ✔ Web Speech API fallback | Works (wrong) | L2 | **Replace** — AudioWorklet PCM capture |
| `src/components/AudioPlayback.jsx` | ✔ NEW in Session 3 | Missing | L2 | **New** |
| `src/components/StoryTimeline.jsx` (~) | ✔ StoryTimeline with image display | Works | L2 | **Refactor** — feed canvas nodes instead |
| `src/components/StatusBar.jsx` (~) | ✔ StatusBar | Works | L2 | **Reuse** |
| `src/hooks/useDirectorSession.js` (~) | ✔ referenced (wire scene/character events) | Works | L2 | **Refactor** — emit canvas node events |
| `src/shapes/{SceneNode,CharacterNode,NoteNode}.jsx` (~) | ✔ named as custom tldraw shapes (Session 2) | Missing | L2 | **New** |
| `src/utils/layoutEngine.js` | ✔ NEW in Session 2 (auto `[x,y]`) | Missing | L2 | **New** |
| `package.json` | ✔ pnpm migration, add tldraw | Works | infra | **Refactor** |

### infra/
| File | V3 evidence | State | Verdict |
|---|---|---|---|
| `Dockerfile` | ✔ multi-stage Node + Python | Works | **Reuse** |
| `deploy.sh` | ✔ Cloud Run deploy, but "wrong env vars" | Broken | **Refactor** — fix `VERTEX_AI_*`, `DIRECTOR_MODE` |
| `main.tf` (~) | ✔ NEW in Session 7B (Terraform) | Missing | **New** |

### docs/
| File | V3 evidence | State | Verdict |
|---|---|---|---|
| `architecture.svg` | ✔ "placeholder" | Stub | **Replace** — real pipeline diagram |
| `README.md` (~) | ✔ Session 7B polish | Partial | **Refactor** |
| `DEMO_SCRIPT.md` (~) | ✔ NEW in Session 7B | Missing | **New** |
| `.env` | ✔ 5 vars (project, location, model, image model, WS URL) | — | **Refactor** — align to verified 2026 model strings |

## What's reusable vs. what's really a rewrite

- **The keeper is Layer 1.** `StoryState` (the deterministic spine) is the single most reusable asset — it survives untouched into the unified StoryForge and just gains character-consistency fields. Protect it.
- **The backend agent is a refactor, not a rewrite.** `director_agent.py` + `main.py` keep their shape; you're *adding* a live path and ADK wrapper alongside the working text path, not replacing them.
- **The frontend is mostly a rewrite.** DirectorCanvas and VoiceControls both get gutted (text-div→tldraw, Web Speech→AudioWorklet). That's the bulk of new build effort and matches the P/R/H v1 slice in the main design doc.
- **~40% of the target files don't exist yet** (all the `live/`, canvas shapes, layout/audio/session modules). The repo at 506d917 is a working *text* prototype; the unified system is that prototype + the missing real-time/spatial layer.

## Recommended next step

When you're ready to build, the cleanest path is to **let me unzip `director-mode-gemini.zip` and produce a byte-exact diff against this reconstructed map** — that turns every `~` into a `✔` and catches any file V3 didn't mention. Needs either the sandbox disk cleared or the zip in a connected folder.

---

*Sources: Director_Mode_Rebuild_Plan.docx (V3) file inventory at commit 506d917; StoryForge Repository Structure Overview metadata (V4); director-mode-gemini.zip (V5) identity confirmation. Byte-exact contents not extracted this session — see Provenance.*
