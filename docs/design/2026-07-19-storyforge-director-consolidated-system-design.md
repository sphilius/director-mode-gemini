# StoryForge / Director Mode — Consolidated System Design

**Prepared for:** Sasha Philius
**Date:** 2026-07-19 (temporal anchor confirmed from system clock)
**Purpose:** Merge the 5 versions of the Story Forge / Director Mode AI system (Gemini Live Agent Challenge, Feb–Jun 2026) into one cohesive architecture, with overlaps reconciled and a P/R/H-scoped v1 build path.

> **Time to produce:** AI ~35 min. Human equivalent ~5–6 hrs (reading 5 sprawling docs, reconciling naming, drafting architecture). Ratio ≈ 9×, because the bottleneck here is synthesis, not typing.

---

## 0. TL;DR

You built the same idea five times under four names. The through-line is stable: **a voice-driven, canvas-based AI "director" that generates an interleaved stream of narrative text + images + spoken audio in real time, grounded by a deterministic story-state engine.** What drifted between versions was *scope* (hackathon demo → post-hackathon rebuild → IDE → reusable method) and *substrate* (React/web canvas vs Godot/native).

This doc collapses that into one layered system I'll call **StoryForge** (your original name; the "OmniForge" doc from today is an alias for the same thing). The architecture is deliberately layered so you can ship the **Director Mode core** first and bolt on the IDE and method layers later without a rewrite.

---

## 1. The five versions (what each one actually was)

| # | Doc / artifact | Date | What it really is | What it contributed |
|---|---|---|---|---|
| **V1** | *Spatial Stream Engine — Hackathon Synthesis & Technical Strategy* | Feb 26 | Strategy memo weighing 3 tracks (Rap Coach / Horror Story Director / PCoS) | The **agent architecture** (6-agent ADK pipeline) and the "interleaved multimodal output" thesis |
| **V2** | *FINAL_HACKATHON_REPORT.md* + `run_hackathon.py` | Mar 3 | Narrative-IP / story-factor extraction from your chat history | The **story-content layer** — your Dominic Saga lore (Cedric, Dominic, Canus, Naszsir, the Source, the Veil, Nephilim, Third Order) as canonical grounding data |
| **V3** | *Director_Mode_Rebuild_Plan.docx* | Mar 17 | Detailed session-by-session rebuild spec against commit `506d917` | The **authoritative build spec** — actual repo state, the 70-point capability gap, 8 build sessions + 3 IDE-vision sessions |
| **V4** | *StoryForge Repository Structure Overview* (AI Studio prompt, ~600KB) | May 21 | Repo snapshot at the IDE stage | The **StoryForge IDE evolution** — story+code dual output, intent classifier, CLD diagrams |
| **V5** | `director-mode-gemini.zip` + *forge_playbook.md* | Jun 6–16 | Code bundle + a reusable method playbook | The **generalization** — Director Mode's method abstracted into a game-design/consulting pipeline with the P/R/H complexity auditor |

*(Note: I read V1, V2, V3, V5 and the competing "OmniForge" draft in full. For V4 I worked from V3's IDE-vision sessions and the file's title/structure rather than parsing the full 600KB AI Studio export, to conserve token budget. Say the word and I'll deep-parse it.)*

### The naming sprawl, resolved

You have four names for one thing. Pick one and alias the rest:

- **Spatial Stream Engine** → the *rendering concept* (interleaved stream on a canvas). Keep as a component name.
- **Director Mode** → the *core product* (voice → director agent → canvas). **This is the ship-first layer.**
- **StoryForge** → the *full IDE* (Director Mode + code generation + story-grid intelligence). The umbrella name.
- **OmniForge** → today's alias; same system. Fold it in.

**Recommendation:** **StoryForge** is the umbrella; **Director Mode** is its flagship mode. Everything else is a component or a later layer.

---

## 2. Unified architecture (one system, four layers)

The key insight that reconciles every version: these aren't competing designs, they're **stacked layers of the same system**. Lower layers ship first and stand alone; higher layers are optional and additive.

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 4 — METHOD / PRODUCTIZATION   (V5: forge_playbook)    │
│  Reusable pipelines (game-design, case-architect), P/R/H     │
│  auditor, skill-ification. Sells the engine, not the story.  │
├─────────────────────────────────────────────────────────────┤
│  LAYER 3 — STORYFORGE IDE           (V4: repo overview)      │
│  Intent classifier (story/code/system/hybrid), CodeAgent,    │
│  Story-Grid 5-Commandments analysis, CLD diagrams,           │
│  emotional CLD state machine. VS Code webview.               │
├─────────────────────────────────────────────────────────────┤
│  LAYER 2 — DIRECTOR MODE CORE       (V1 + V3: SHIP FIRST)    │
│  Voice loop (Gemini Live) → Director agent (ADK) → spatial   │
│  canvas (tldraw) → interleaved text + image + audio.         │
│  Character-consistency engine. Session persistence.          │
├─────────────────────────────────────────────────────────────┤
│  LAYER 1 — STORY-STATE + CONTENT    (V2: canonical data)     │
│  Deterministic StoryState (scenes, characters, moods,        │
│  timeline). Dominic Saga lore as grounding corpus.           │
│  Zero-hallucination structured outputs + Search grounding.   │
└─────────────────────────────────────────────────────────────┘
                          ▲
                  ┌───────┴────────┐
                  │  AUDIO DIRECTOR │  ← separate sub-agent (own doc)
                  │  sub-agent      │     plugs into Layer 2's TTS slot
                  └────────────────┘
```

### Layer 1 — Story-State + Content (the deterministic spine)
The non-negotiable foundation from V2/V3. A `StoryState` model (scenes, characters, moods, timeline, context-summary builder) that is **fully deterministic** — the LLM proposes, the state disposes. Your Dominic Saga lore lives here as a canonical corpus so the director can't contradict established canon. Grounding is enforced via structured outputs + Google Search grounding (V3 Session 6).

**Why it's Layer 1:** every other layer reads/writes this. It's the "deterministic core" your own operating principles demand (CLAUDE.md: deterministic core, optional AI).

### Layer 2 — Director Mode Core (ship this first)
The flagship. Reconciles V1's agent architecture with V3's build reality:

- **Voice loop:** browser mic → AudioWorklet (24 kHz PCM) → WebSocket → **Gemini Live API** → streamed audio back, with barge-in/interruption (V3 Sessions 1 & 3). Text fallback mode for local dev.
- **Director agent:** an **ADK-wrapped** `DirectorAgent` (V3 Session 6) exposing tools: `update_scene`, `introduce_character`, `generate_storyboard`, `generate_reference`. V1's 6-agent pipeline (NarrativeWeaver, VisualMomentDetector, ImageSynthesizer, TTSGenerator, ChoiceArchitect) becomes the *internal decomposition* of this one ADK agent rather than 6 separate services — simpler, and it's how V3 actually built it.
- **Spatial canvas:** **tldraw** infinite canvas with custom `SceneNode` / `CharacterNode` / `NoteNode` shapes, an auto-layout engine, and relational arrows (V3 Session 2). This is the "Spatial Stream Engine" made concrete.
- **Interleaved output:** text tokens + image-generation events + audio chunks stream together; the canvas renders each type as it arrives (V1's core judging thesis, V3 Session 7A).
- **Character-consistency engine:** visual-trait injection into image prompts + the "Anchor Technique" (context summary prepended every turn, behavioral instruction last) so a character looks the same in Scene 1 and Scene 3 (V3 Session 5).

### Layer 3 — StoryForge IDE (later)
V4's evolution: port the Director Mode canvas into a **VS Code extension webview**, add an **intent classifier** (story / code / system / hybrid), a **CodeAgent** for workspace-aware code generation, **Story-Grid 5-Commandments** structural analysis (Inciting Incident → Progressive Complication → Crisis → Climax → Resolution), and the **emotional CLD state machine** (Curiosity/Fear/Frustration pools modulating the system prompt). Dual output: story in the canvas panel, code in the editor.

### Layer 4 — Method / Productization (much later, the consulting-pivot lever)
V5's `forge_playbook`: abstract the whole thing into reusable, sell-able pipelines (`game-design-pipeline`, `case-architect`) governed by the **P/R/H complexity auditor**. This is where StoryForge stops being one app and becomes a method you can license or teach.

---

## 3. Conflicts between versions — and the rulings

| Conflict | Sources | Ruling | Why |
|---|---|---|---|
| **Web/React canvas vs Godot/C# native** | V1–V4 (React/tldraw) vs today's OmniForge doc (Godot + Node bridge) | **tldraw/React for Director Mode core; Godot only if you later ship a packaged game client.** | You have working React/tldraw code (V3). Godot buys nothing for a voice+canvas director and reintroduces the C#↔LLM bridge problem the OmniForge doc invented a Node server to solve. Don't add a substrate to solve a problem you don't have. |
| **6 separate ADK agents vs 1 ADK agent with tools** | V1 (6-agent pipeline) vs V3 (single `DirectorAgent`) | **One ADK agent, tools as internal decomposition.** | V3 is what actually built and ran. 6 microservices is Heuristic complexity (no named failure it prevents). Collapse to one; split later only if a real bottleneck names itself. |
| **Gemini Live native audio vs Cloud TTS vs ElevenLabs** | V1 (Cloud TTS / Live native) vs your current ElevenLabs workflow | **Route by line importance via the Audio Director sub-agent** (see companion doc). Hero/character lines → ElevenLabs; bulk/ambient → Gemini. | Quality vs cost is a real tradeoff, not a pick-one. The Audio Director is exactly the abstraction that lets both coexist. |
| **Horror Story Director vs PCoS (productivity)** | V1 dual-track | **Creative Storyteller track only.** Borrow PCoS's deterministic orchestration pattern, drop its product framing. | 40% multimodal-innovation weighting rewards the narrative track; your rarest edge (narrative craft) has less hackathon competition. PCoS survives as an *architectural pattern*, not a second product. |
| **Model strings** | V3 pins `gemini-2.0-flash`, `imagen-3.0` | **Re-verify against the live Vertex console before each build session.** Today's pricing data already shows Gemini 3.1/3.5-era TTS models. | Model deprecation is a named failure (V3 risk log). Don't hardcode from a March doc in July. |
| **npm vs pnpm, disk space** | V3 risk log | **pnpm exclusively; resolve disk space before Session 0.** | Already cost you hours once (V3). Also note: this workspace's Linux sandbox is currently out of disk — same failure class, worth clearing. |

---

## 4. The P/R/H-scoped v1 (what to actually build first)

Applying your own complexity auditor (forge_playbook Part C) to Director Mode Core so you ship instead of sprawl:

**Prediction (the core output — always build):**
- Voice in → director agent → **text narrative streaming to canvas**
- `update_scene` / `introduce_character` tools mutating `StoryState`
- **One** image per scene on the canvas (Imagen)
- Spoken audio back (start with Gemini Live native voice — zero extra integration)

**Regularizer (prevents a named failure — build only these):**
- Text fallback mode → *prevents:* "Live API blocked in sandbox kills all local dev" (V3's documented WebSocket-in-sandbox failure)
- Session persistence to JSON → *prevents:* "backend restart wipes the story mid-demo"
- Character visual-trait injection → *prevents:* "same character looks different every scene" (the consistency failure)
- Image-gen retry with backoff → *prevents:* "Imagen rate-limit crashes the session live"

**Heuristic (no named failure — CUT from v1, add back only when a failure proves it):**
- Multi-panel storyboards (single image first)
- Veo animatics / video
- Story-Grid analysis layer
- The VS Code IDE port
- Multi-agent split
- Relational arrows on canvas
- Affective dialogue tone-matching

**v1 = Prediction + the 4 named Regularizers. Everything in the Heuristic list waits for a real failure to justify it.** That's roughly V3 Sessions 0–5 minus the storyboard multi-panel work — a genuinely shippable slice.

---

## 5. Reconciled build sequence

Ordered by dependency (from V3, pruned to the v1 scope above):

1. **Session 0 — Environment reset.** pnpm migration, tldraw deps, `.env`, backend `/health`, frontend builds. *(Clear disk first.)*
2. **Session 1 — Gemini Live backend** with text-fallback mode.
3. **Session 2 — tldraw canvas** with SceneNode/CharacterNode + auto-layout (skip arrows).
4. **Session 3 — Browser audio pipeline** (mic PCM out, speaker in, interruption).
5. **Session 4′ — Single-image generation** per scene on canvas (defer multi-panel storyboards).
6. **Session 5 — Character-consistency engine** + session persistence.
7. **Ship / demo the slice. Reassess.** Then pull Heuristic items back one at a time, each justified by a named gap.

Channel assignment (from V3, unchanged): Antigravity = new feature code · Claude Code = debugging/file surgery · Gemini CLI = Live API/WebSocket testing · Claude Desktop = planning/handoffs · GCP Console = billing/APIs/deploy.

---

## 6. Open decisions for you

1. **Umbrella name:** confirm **StoryForge** (flagship = Director Mode), or keep OmniForge?
2. **Audio backend default:** ship v1 on Gemini Live native voice (fastest), then layer in the Audio Director sub-agent for ElevenLabs hero lines? (Recommended — see companion doc.)
3. **V4 deep-parse:** want me to fully unpack the 600KB StoryForge repo export and produce a file-by-file inventory + reuse map? (Design-level was your call; this is the upgrade.)
4. **IP boundary:** the Dominic Saga lore (Layer 1 content) is your creative IP. Keep it out of any productized/sellable Layer 4 method that others would run.

---

*Sources: your Google Drive — Spatial Stream Engine synthesis (V1), FINAL_HACKATHON_REPORT.md (V2), Director_Mode_Rebuild_Plan.docx (V3), StoryForge Repository Structure Overview (V4), forge_playbook.md + director-mode-gemini.zip (V5), and the OmniForge: Consolidated System Design draft (2026-07-19).*
