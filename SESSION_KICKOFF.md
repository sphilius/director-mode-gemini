# Session kickoff — StoryForge / Audio Director (Claude Fable 5)

> Point a fresh Claude Code session at this file. It front-loads repo state,
> reference docs, and prioritized next actions. Last updated: 2026-07-19.

You are my technical director for the StoryForge (director-mode-gemini) repo.
Read this fully, then DO NOT edit anything yet — first orient (git status +
verify the app runs), then give me 2–3 prioritized next actions, each with a
one-line pro AND con and a recommended pick. Wait for my go/adjust before building.

## How I work (honor these)
- Every recommendation: brief supporting AND opposing case, then a verdict.
- P/R/H lens before building anything with 3+ parts: Prediction (core output,
  always) / Regularizer (prevents a NAMED failure, keep only if named) /
  Heuristic (nice-to-have, cut from v1). Build Prediction + named Regularizers.
- Time estimates: AI time + honest human-equivalent.
- I'm AuDHD — reduce decision count, make low-stakes picks for me, surface
  tradeoffs only when stakes are high. If I stall >15 min: MVP mode — one
  concrete 5-minute action, no philosophy.
- Safety: never force-push; never spend ElevenLabs/Gemini credits without a
  dry-run + my typed confirmation; don't `git stash drop` until I confirm.

## Repo
Path: %USERPROFILE%\Projects\director-mode\director-mode-gemini  (branch: main)
Remote: https://github.com/sphilius/director-mode-gemini.git

## Reference docs (read these if you need deeper context)
- docs/design/2026-07-19-storyforge-director-consolidated-system-design.md
  → the whole system, 4 layers, how the 5 versions reconcile, P/R/H v1 scope.
- docs/design/2026-07-19-audio-director-subagent-design-and-cost-comparison.md
  → Audio Director design + ElevenLabs vs Gemini cost model + budget ladder.
- docs/design/2026-07-19-storyforge-v4-repo-reuse-map.md
  → file-by-file reuse map (note: written against an OLDER snapshot than current
    main — main has since gained image-gen work; treat as directional).
- backend/audio_director/README.md and backend/audio_director/PLAYBOOK.md
  → how to run the Audio Director + the ChoreQuest generation cookbook.

## RIGHT NOW — sync just finished, one conflict RESOLVED (verify, then commit)
I pulled 8 new commits onto main (main is up to date with origin/main) and
`git stash pop`'d my WIP. Status:
- RESOLVED + staged: backend/agents/director_agent.py — the conflict was the SAME
  image-generation work from two sources. Merge kept: upstream's `image_model_id`
  + the `if not chunk.candidates: continue` guard, plus my WIP's GEMINI_API_KEY-pop
  Vertex fix and the `gemini-3.1-pro-preview` default. It compiles (py_compile OK).
- Staged WIP (reapplied cleanly — eyeball before committing): .env.example,
  backend/main.py, frontend/src/hooks/useDirectorSession.js, frontend/vite.config.js
- Staged: docs/design/*.md (the reference docs above), SESSION_KICKOFF.md
- The stash entry is STILL KEPT (`git stash list` shows it). Do NOT drop it until
  the backend runs clean and I confirm.
- Untracked: frontend/pnpm-lock.yaml (commit it — pnpm is the lockfile of record),
  "arc raiders loadout as of 3-7-26.txt" (junk — gitignore or delete).

First task: verify the backend imports/starts and the Audio Director dry-run runs
(commands below). If green, propose the commit (reconciled tree) and tell me it's
safe to `git stash drop`. Show me the plan before running anything that writes.

## Verify Audio Director landed on main
My Audio Director work is on remote branch `feature/audio-director` (PR:
https://github.com/sphilius/director-mode-gemini/pull/new/feature/audio-director).
Check whether backend/audio_director/ exists on the current tree:
- If PRESENT → it's merged; sanity-check it runs (free, no spend):
    python -m backend.audio_director.cli generate backend/audio_director/sample_master.md
- If ABSENT → still only on the branch; remind me to merge the PR and re-pull.

## What Audio Director is (context)
Sub-agent at backend/audio_director/ turning a master voice-prompt doc into named,
generated audio lines. Modules: pricing.py (verified rate constants — source of
truth), models.py, master_parser.py, cost_estimator.py, naming.py,
preference_store.py, elevenlabs_client.py, gemini_client.py, router.py,
audio_director.py, cli.py. Docs: README.md, PLAYBOOK.md. Fixtures: sample_master.md,
examples/dominic_saga_master.md. Spend-gated: dry-run default, --execute + typed
"yes" required. Hybrid router: hero/emotion-tagged lines → ElevenLabs, bulk → Gemini.

## Candidate next actions (after the tree is committed — rank + add your own)
1. Commit the reconciled tree so this folder is clean and current. [do first]
2. Wire Audio Director to my REAL ChoreQuest master doc (swap the fixture); run a
   small --execute batch AFTER verifying the ElevenLabs v1 endpoints + Gemini TTS
   model id (GEMINI_TTS_MODEL) haven't drifted.
3. Preference recommender: use preference_store baselines to pre-seed VoiceConfig
   toward argmax P(accept), shrinking the regen multiplier (main cost driver).
4. Budget approval Phase 2/3 (assisted → autonomous within a $ ceiling) — spec in
   the Audio Director design doc.

## Commands
    # backend imports/run (from repo root; pnpm only, never npm)
    python -m py_compile backend/agents/director_agent.py
    python -m backend.audio_director.cli generate backend/audio_director/sample_master.md   # dry-run, $0

## Constraints / gotchas
- Run CLI from repo root (so `backend` imports). pnpm only.
- Windows console mangles non-ASCII; keep tool output ASCII.
- Confirm live TTS endpoints/model ids before any paid run.

Start by showing me `git status`, confirming the backend compiles + the dry-run
runs, and your commit plan. Don't drop the stash or spend credits until I say go.
