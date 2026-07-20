# Audio Director Sub-Agent — Design + ElevenLabs vs Google AI Studio Cost Comparison

**Prepared for:** Sasha Philius
**Date:** 2026-07-19 (temporal anchor confirmed from system clock)
**Scope:** (1) Cost comparison of ElevenLabs vs Google AI Studio for personal and commercial voice generation; (2) full design of an "Audio Director" sub-agent that generates + names lines, learns your vocal-tuning preferences, pre-computes budgets, and runs a human→automated approval ladder. Baseline: **ElevenLabs Creator (~$22/mo)**, ChoreQuest voice work.

> **Time to produce:** AI ~30 min. Human equivalent ~4–5 hrs (pricing research, building the cost model, designing the agent + data model). Ratio ≈ 9×.

---

## Part 1 — Cost comparison (the number you actually asked for)

### 1.1 Stated assumptions (so you can challenge the math)

| Assumption | Value | Note |
|---|---|---|
| Avg VO line length | **80 characters** (~13 words, ~5 sec audio) | Game lines (greeting, streak-at-risk, level-up) run short. Adjust up if yours are longer. |
| ChoreQuest voice set | **10 characters × 20 lines = 200 final lines** | Categories: greeting, repelled, streak-at-risk, task-complete, level-up, idle, etc. |
| Regeneration multiplier | **2.5×** on line takes | You generate a few takes and keep one. Every generated take burns credits/tokens. |
| Voice-design cost (one-time/char) | ~150-char preview × 3 samples × 2 refine rounds | ElevenLabs Voice Design in v2/v2.5. Negligible on Gemini. |
| ElevenLabs model for lines | **v3 (1 credit/char)** | Your workflow: v2 for voice *design*, v3 + emotion tags for *lines*. |
| Gemini model | **2.5 Flash TTS** ($0.50 in / $10 out per 1M tok) and **3.5 Flash TTS** ($6 out) | Output = 25 tokens/sec of audio → ~125 out-tok/line. |

### 1.2 Per-line and per-set cost

| Metric | ElevenLabs (Creator, v3) | Gemini 2.5 Flash TTS (paid API) | Gemini AI Studio (free tier) |
|---|---|---|---|
| Cost per *generated* take | 80 credits ≈ **$0.0176** | ~$0.00126 | $0 (rate-limited) |
| Cost per *kept* line (2.5× regen) | ~200 credits ≈ **$0.044** | ~**$0.0032** | $0 |
| Voice design (10 chars, one-time) | ~9,000 credits ≈ **$2.00** | ~negligible | $0 |
| **Whole 200-line set** | **~$11 of credit value** (fits in one $22 Creator month, ~half your monthly credits) | **~$0.63 total** | **$0** (slower, rate-limited) |

*ElevenLabs credit value: Creator = 100,000 credits / $22 → $0.00022/credit. The full ChoreQuest set (~50,000 credits incl. design + regen) consumes ~half a month's Creator allotment — so in practice the marginal cash cost is "you were paying $22/mo anyway."*

### 1.3 The two scenarios

**Scenario 1 — Personal / household use (your actual case today)**

| Option | Real cost for ChoreQuest | What you get / give up |
|---|---|---|
| **ElevenLabs Creator** | **~$22/mo** (set fits in one month) | Best expressive quality, v3 emotion tags, Voice Design UX, PVC. This is why you're using it. |
| **Gemini AI Studio (free)** | **~$0** | Free + fast enough for bulk, but rate-limited, lower character/emotional fidelity, and free-tier data terms (inputs may be used to improve products) — fine for household, not for shipping. |
| **Gemini paid API** | **~$0.63 total** | Near-free, commercial-clean terms, but expressive quality trails ElevenLabs v3 today. |

> **Verdict (personal):** You're not overpaying. At household scale the ElevenLabs $22/mo is buying *quality and iteration speed*, and one month covers the whole ChoreQuest set. Gemini free tier is the right tool for throwaway/placeholder lines, not hero VO.

**Scenario 2 — Commercial / monetized**

| Option | Cost @ 200 lines | Cost @ 2,000 lines | Cost @ 20,000 lines | Commercial rights |
|---|---|---|---|---|
| **ElevenLabs** | ~$11 (Creator) | ~$88 → needs Pro (~$99/500k credits) | ~$800+ (Pro + overage/Scale) | **Included on any paid plan** (Starter+). Free tier does NOT grant broad commercial rights. |
| **Gemini paid API** | ~$0.63 | ~$6.30 | ~$63 | Allowed under paid API terms |
| **Hybrid (recommended)** | ~$8 EL hero + ~$0.2 Gemini bulk | ~$40 + ~$4 | ~$300 + ~$40 | Mixed; track per-asset |

> **Verdict (commercial):** The cost gap compounds hard with volume — Gemini is ~14× cheaper per line and the delta grows. But for a *monetized* product, expressive quality on hero/character lines is a feature customers hear. **Don't pick one — split by line importance.** That split is exactly what the Audio Director automates.

### 1.4 A third path worth a look (you asked if there's a better approach)

- **Self-hosted open-source TTS** (Kokoro-class / Coqui-lineage models on your own GPU): ~$0 marginal cost per line after setup, full commercial freedom, no rate limits. Quality is improving fast but still below ElevenLabs v3 for emotional range, and it's real setup/maintenance work. **Best fit:** high-volume bulk/ambient lines in a commercialized product, once volume makes the per-line savings worth a weekend of setup.
- **Google Cloud TTS (Chirp/standard voices):** a middle tier — cheaper and more controllable than Studio free tier, less expressive than ElevenLabs. Useful as a Gemini alternative if you want SSML-level control.

*(Pricing for ElevenLabs and Gemini is verified against live 2026 sources — see Sources. The open-source/Cloud-TTS figures are directional; confirm before committing.)*

---

## Part 2 — Audio Director sub-agent design

### 2.1 What it is
A specialized sub-agent that owns the *entire* voice-line production pipeline you currently do by hand in the ElevenLabs GUI — parsing your master prompt doc, pre-computing cost, routing each line to the cheapest engine that meets a quality bar, generating + **auto-naming** files, and learning your tuning preferences so the first take is closer to keepable over time. It plugs into the StoryForge Director Mode "TTS slot" (Layer 2) but runs standalone for any project.

### 2.2 Architecture (7 components)

```
                 ┌──────────────────────────────────────────┐
   master doc →  │ 1. MASTER-PROMPT PARSER                  │
                 │   H2 header = voice name → {design prompt,│
                 │   preview text, personality, config:     │
                 │   guidance/loudness/stability/similarity/ │
                 │   style/speed}                            │
                 └───────────────┬──────────────────────────┘
                                 ▼
   past audio →  ┌──────────────────────────────────────────┐
   + your picks  │ 2. PREFERENCE / BASELINE LEARNER         │
                 │   builds per-character + global "vocal    │
                 │   tuning fingerprint" from your accept/   │
                 │   reject history → pre-seeds config       │
                 └───────────────┬──────────────────────────┘
                                 ▼
                 ┌──────────────────────────────────────────┐
                 │ 3. COST ESTIMATOR                        │
                 │   counts chars (EL credits) + tokens      │
                 │   (Gemini) per line/category/character →  │
                 │   $ per engine + hybrid, BEFORE spending  │
                 └───────────────┬──────────────────────────┘
                                 ▼
                 ┌──────────────────────────────────────────┐
                 │ 4. ROUTER / BUDGET ALLOCATOR             │
                 │   per line: hero→ElevenLabs, bulk→Gemini; │
                 │   proposes EL / Gemini / hybrid budget    │
                 └───────────────┬──────────────────────────┘
                                 ▼
                 ┌───────────────────────────┐   approve?
                 │ 5. REVIEW LADDER          │◄── human (first N)
                 │   human→assisted→auto     │──► then director agent
                 └───────────────┬───────────┘
                                 ▼
                 ┌──────────────────────────────────────────┐
                 │ 6. GENERATOR                             │
                 │   EL: v2/v2.5 Voice Design → pick →       │
                 │   v3 + emotion tags for lines            │
                 │   Gemini: TTS API for bulk               │
                 └───────────────┬──────────────────────────┘
                                 ▼
                 ┌──────────────────────────────────────────┐
                 │ 7. NAMING ENGINE (the fix you wanted)    │
                 │   writes {project}_{character}_{category}_│
                 │   {take}_{version}.mp3 at generation time │
                 └──────────────────────────────────────────┘
```

### 2.3 The naming fix (specifically what annoyed you)
ElevenLabs' GUI auto-names files and forces manual renaming. **The real fix is to generate via the API, not the GUI** — then the sub-agent controls the filename at write time. Convention:

```
{project}_{character}_{category}_{take}_{voiceVersion}.mp3
e.g.  chorequest_iris_streak-at-risk_t03_v3.mp3
```

Metadata sidecar (`.json`) per file records: engine, model, all config params, the exact line text, emotion tags used, credits/tokens spent, and your keep/reject flag. That sidecar is also the training data for component 2.

### 2.4 Preference learning (how it gets better at your taste)
A lightweight recommender, not a heavy ML pipeline:

- **Event log:** every generation writes `{character, config params, engine, emotion tags, accepted?}`.
- **Cold start:** seed from the config block in your master doc (your stated stability/similarity/style/speed defaults).
- **Per-character fingerprint:** the config settings your *kept* takes cluster around (e.g., "Iris keeps at stability 35–45, style 60").
- **Global baseline:** your cross-character tendencies (e.g., "you reject high-stability robotic takes; you favor style ≥ 50").
- **Use:** at generation time, pre-seed config toward `argmax P(you accept)` for that character/category. Over time, fewer regens to get a keeper → directly lowers the 2.5× multiplier that dominates ElevenLabs cost.

This satisfies both of your stated goals: (a) generate samples for you to direct even if the first batch is bad, and (b) analyze existing samples to establish your baseline vocal-tuning fingerprint.

### 2.5 The budget review ladder (human → automated, configurable)

| Phase | Who approves budget | Trigger to advance | Your control |
|---|---|---|---|
| **1 — Calibration** | **You approve every budget**, first **N** runs | `N` slider = **10–100** (your granularity setting) | Every proposal; your edits train the allocator |
| **2 — Assisted** | Director agent proposes + auto-approves **within a $ ceiling you set**; shows only final cost + one-tap override | After N clean runs | Ceiling + one-tap override on every run |
| **3 — Autonomous (opt-in)** | Agent runs within budget, logs, notifies | Explicit opt-in only | Hard $ ceiling, kill switch, toggle off anytime |

Guardrails (aligned with your operating rules): the human stays the decision-maker, the ceiling is never auto-raised, there's always a kill switch, and the whole ladder is a toggle you can drop back to Phase 1 at will. No mid-run auto-spend above ceiling, ever.

### 2.6 Your workflow, encoded
The sub-agent bakes in exactly what you described:
1. Parse the streamlined master doc (H2 = voice name; sections = design prompt / preview / personality / config).
2. **Voice design in v2/v2.5** → generate 3 samples → you pick or it refines the design prompt.
3. Once the voice is locked, **generate lines in v3 with emotion/empathy tags**, by category (greeting, repelled, streak-at-risk…).
4. Auto-name + auto-download each keeper. No manual renaming.
5. Log the pick → feed the preference learner.

### 2.7 P/R/H-scoped v1 (build this slice first)

**Prediction (build):** master-doc parser → cost estimator → ElevenLabs API generation with the naming engine. *(This alone kills the manual-rename pain and gives you pre-spend cost visibility.)*

**Regularizer (named-failure guards, build):**
- Dry-run cost gate before any spend → *prevents:* "surprise credit burn."
- Keep/reject sidecar logging → *prevents:* "no data to learn from later."
- Ceiling + confirm on every run in Phase 1 → *prevents:* "runaway autonomous spend."

**Heuristic (defer):** Gemini routing, hybrid allocation, the full preference recommender, autonomous Phase 3, self-hosted TTS. Add each when a real gap names it. *(v1 can be ElevenLabs-only with manual engine choice; routing earns its way in once you have volume.)*

### 2.8 Where it lives (surface routing)
- **Build:** Claude Code (multi-file Python sub-agent + API wrappers). Not Mesa work — fully clear to execute.
- **Run:** as a StoryForge Layer-2 component, or standalone CLI/skill for any project.
- **Secrets:** ElevenLabs + Gemini API keys via a keychain/`.env`, never hardcoded (your deliverable convention). The `api-keychain` skill fits here.

---

## Part 3 — Recommendation

1. **Personal use:** stay on ElevenLabs Creator for hero/character lines; use Gemini free tier for placeholders. You're not overpaying — one month covers ChoreQuest.
2. **Commercial:** go **hybrid** — ElevenLabs v3 for character-defining lines, Gemini paid API for bulk/ambient. The Audio Director makes the split automatic and pre-priced.
3. **Build the v1 slice** (parser + cost estimator + EL API generation + naming engine) first. It removes your two biggest pains — manual renaming and blind spend — in the smallest shippable unit.
4. **Then** layer in preference learning and Gemini routing, each justified by a named gap.

---

*Sources:*
- *ElevenLabs pricing 2026: [elevenlabs.io/pricing](https://elevenlabs.io/pricing), [BIGVU](https://bigvu.tv/blog/elevenlabs-pricing-2026-plans-credits-commercial-rights-api-costs/), [Flexprice](https://flexprice.io/blog/elevenlabs-pricing-breakdown)*
- *Gemini / Google AI TTS pricing 2026: [ai.google.dev/gemini-api/docs/pricing](https://ai.google.dev/gemini-api/docs/pricing), [Google Cloud TTS pricing](https://cloud.google.com/text-to-speech/pricing), [TokenCost TTS comparison](https://tokencost.app/blog/tts-api-pricing-2026)*
- *Your workflow + master-doc structure, per your description (2026-07-19).*
