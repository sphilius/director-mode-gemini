# Audio Director — ChoreQuest Cookbook

A step-by-step playbook for generating the rest of ChoreQuest's voice lines with
the Audio Director. Copy-paste the command recipes; fill the master-doc template.

All commands run **from the repo root** (`C:\Users\sphil\Projects\director-mode\director-mode-gemini`)
so `backend` is importable. Nothing spends credits until you add `--execute`.

---

## The loop (how a session goes)

```
1. WRITE   → add/patch a character block in your master doc
2. PARSE   → confirm it read every line + category correctly
3. ESTIMATE→ see EL credits + Gemini $ + the hybrid split BEFORE spending
4. DRY-RUN → see the exact filenames + which engine each line routes to
5. EXECUTE → generate for real (asks "yes" first); files auto-named
6. LISTEN  → keep the good takes, delete the bad
7. MARK    → tell the tool which you kept, so it learns your taste
8. BASELINE→ check the learned tuning fingerprint; fold it back into config
```

Steps 2–4 are free and instant. Do them liberally.

---

## Step 1 — the master doc

Create `backend/audio_director/chorequest_master.md`. One `##` block per voice.
Format (the parser is forgiving about spacing):

```markdown
## <CharacterName>
**Voice Design Prompt:** <description you'd paste into ElevenLabs Voice Design>
**Preview Text:** <one line the character says, used to design the voice>
**Personality:** <tone notes — for your reference>

Config:
- stability: 40         # 0-100 or 0-1 both accepted
- similarity: 75
- style: 60
- speed: 1.0
- gemini_voice: Kore    # prebuilt Gemini voice for this character's bulk lines

### Lines
- [category] The line text.
- [category] [excited] A line with a v3 emotion tag (tag stays inline, routes to ElevenLabs).
- [category] [engine=gemini] A line you want forced to Gemini regardless.
```

### ChoreQuest category checklist

Aim for coverage across the states the app actually fires. Suggested set (rename
to match your code events):

| Category | When it plays | Route (default) |
|---|---|---|
| `greeting` | app open / daily first-launch | ElevenLabs (hero) |
| `streak-at-risk` | streak about to break | Gemini (tag it for EL if emotional) |
| `streak-saved` | streak preserved | Gemini |
| `task-complete` | a chore checked off | Gemini |
| `all-clear` | all tasks done for the day | Gemini |
| `level-up` | level/XP threshold | ElevenLabs (hero) |
| `reward` | reward/loot granted | Gemini |
| `repelled` | invalid action / "not yet" | Gemini |
| `idle` | idle nudge | Gemini |
| `encourage` | behind pace, gentle push | Gemini (tag for EL if it should land) |
| `victory` | big milestone | ElevenLabs (hero) |

> Rule of thumb: **hero moments and anything emotional → ElevenLabs; everyday
> chatter → Gemini.** The router does this automatically; override per line with
> `[engine=elevenlabs]` / `[engine=gemini]`.

---

## Step 2–4 — free recipes (no spend)

```bash
# Did it parse everything?
python -m backend.audio_director.cli parse backend/audio_director/chorequest_master.md

# What will it cost? (EL credits + Gemini $ + the hybrid split)
python -m backend.audio_director.cli estimate backend/audio_director/chorequest_master.md --plan creator

# Exact filenames + per-line engine, still $0
python -m backend.audio_director.cli generate backend/audio_director/chorequest_master.md
```

Tune routing without touching the doc:

```bash
# push everything to Gemini (cheapest — good for a rough pass / scratch track)
python -m backend.audio_director.cli generate backend/audio_director/chorequest_master.md --engine gemini

# everything to ElevenLabs (final hero pass)
python -m backend.audio_director.cli generate backend/audio_director/chorequest_master.md --engine elevenlabs

# redefine what counts as "hero"
python -m backend.audio_director.cli estimate backend/audio_director/chorequest_master.md \
  --hero-categories greeting,level-up,victory
```

---

## Step 5 — generate for real

Set keys in `.env` first (git-ignored):

```
ELEVENLABS_API_KEY=...
GEMINI_API_KEY=...
```

```bash
# one character at a time is the safe way to start
python -m backend.audio_director.cli generate backend/audio_director/chorequest_master.md \
  --character Iris --execute
```

It prints the estimate, then asks you to type `yes` (Phase-1 human gate). Files land in:

```
backend/audio_director/out/iris/chorequest_iris_greeting_01_t01_v3.mp3      (+ .json sidecar)
backend/audio_director/out/iris/chorequest_iris_idle_01_t01_gem.wav
```

Regenerate a line you didn't like — it auto-bumps the take (`_t02_`), never overwrites:

```bash
# (re-run the same command; existing files are detected and the take increments)
```

Skip the prompt for batch runs you've already reviewed the estimate for:

```bash
python -m backend.audio_director.cli generate <master.md> --character Grix --execute --yes
```

---

## Step 6–8 — keep, mark, learn

Listen to the takes, delete the bad `.mp3`/`.wav` (and their `.json`). Then tell
the tool what you kept so it learns your tuning:

```bash
python -m backend.audio_director.cli mark Iris chorequest_iris_greeting_01_t02_v3.mp3 --keep
python -m backend.audio_director.cli mark Iris chorequest_iris_greeting_01_t01_v3.mp3 --reject

# see the learned fingerprint (mean of your kept takes)
python -m backend.audio_director.cli baseline Iris
python -m backend.audio_director.cli baseline global
```

Once `baseline Iris` has a few samples, copy those numbers back into Iris's
`Config:` block. Over time your first take gets closer to keepable → fewer regens
→ lower cost (the regen multiplier is what dominates ElevenLabs spend).

---

## Two-stage voice workflow (matches how you work by hand)

1. **Design the voice** (ElevenLabs v2/v2.5): on the first `--execute` for a
   character with no `voice_id`, the tool generates design previews and creates a
   persistent voice (v1 auto-picks the first preview — swap in your chosen
   `generated_voice_id` later for full control).
2. **Generate lines** (ElevenLabs v3 + inline emotion tags): every line after that
   uses the locked voice. Put emotion tags inline: `[whispers]`, `[excited]`,
   `[nervous]` — they stay in the text and route the line to ElevenLabs.

---

## Cost cheat-sheet (Creator plan, ~$22/mo, verified 2026-07-19)

- ElevenLabs kept line ≈ **$0.04** (80 chars × 2.5 regen). Gemini kept line ≈ **$0.003**.
- A ~200-line ChoreQuest set ≈ **$11 of EL credit value** (fits one Creator month) or **~$0.63 all-Gemini**.
- Hybrid (hero on EL, bulk on Gemini) is usually the right call: hero quality where it's heard, pennies everywhere else.

---

## Troubleshooting

- **`ModuleNotFoundError: backend`** → run from the repo root, not inside `backend/`.
- **Weird glyphs in output** → cosmetic Windows console encoding; ignore, or `chcp 65001`.
- **ElevenLabs 401/404 on --execute** → check `ELEVENLABS_API_KEY` and confirm the
  v1 endpoint paths in `elevenlabs_client.py` against current docs.
- **Gemini audio empty** → confirm the TTS model id in `gemini_client.py`
  (`GEMINI_TTS_MODEL`) and that your key has TTS access.
- **Nothing spent when you expected it to** → you forgot `--execute` (that's the safety default).
