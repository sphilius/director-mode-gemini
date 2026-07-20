"""Audio Director orchestrator — ties the v1 slice together.

Flow:  parse master doc  ->  estimate cost (always)  ->  [human gate]  ->
       ensure voice  ->  generate + auto-name each line  ->  log for learning.

The human gate is enforced by the caller (CLI): generation only spends when
`execute=True`, and the CLI additionally requires an explicit confirmation.
"""

from __future__ import annotations

from pathlib import Path

from backend.audio_director import naming, preference_store, pricing
from backend.audio_director.cost_estimator import estimate_all, render_estimate, routed_summary
from backend.audio_director.elevenlabs_client import ElevenLabsClient
from backend.audio_director.gemini_client import GeminiTTSClient, DEFAULT_GEMINI_VOICE
from backend.audio_director.master_parser import parse_master_file, summarize
from backend.audio_director.models import CharacterVoice, GenerationResult
from backend.audio_director.router import RoutingPolicy, decide_engine, route_reason, ELEVENLABS


class AudioDirector:
    def __init__(
        self,
        project: str = "chorequest",
        out_dir: str | Path = "backend/audio_director/out",
        plan: str = pricing.DEFAULT_ELEVENLABS_PLAN,
        regen_multiplier: float = pricing.DEFAULT_REGEN_MULTIPLIER,
        execute: bool = False,
        line_model: str = pricing.EL_DEFAULT_LINE_MODEL,
        policy: RoutingPolicy | None = None,
    ) -> None:
        self.project = project
        self.out_dir = Path(out_dir)
        self.plan = plan
        self.regen_multiplier = regen_multiplier
        self.execute = execute
        self.line_model = line_model
        self.policy = policy or RoutingPolicy()
        self.client = ElevenLabsClient(execute=execute)
        self.gemini = GeminiTTSClient(execute=execute)

    # -- read-only stages -----------------------------------------------------
    def parse(self, master_path: str | Path) -> list[CharacterVoice]:
        return parse_master_file(master_path)

    def estimate_report(self, characters: list[CharacterVoice]) -> str:
        estimates = estimate_all(
            characters, plan_key=self.plan,
            regen_multiplier=self.regen_multiplier, line_model=self.line_model,
        )
        routed = routed_summary(
            characters, self.policy, plan_key=self.plan,
            regen_multiplier=self.regen_multiplier, line_model=self.line_model,
        )
        return render_estimate(estimates) + "\n\n" + routed

    # -- generation -----------------------------------------------------------
    def ensure_voice(self, cv: CharacterVoice) -> str:
        if cv.voice_id:
            return cv.voice_id
        previews = self.client.design_voice(cv.voice_design_prompt, cv.preview_text or cv.name)
        chosen = previews[0].generated_voice_id if previews else "dryrun-1"
        voice_id = self.client.create_voice(cv.name, cv.voice_design_prompt, chosen) or "dryrun-voice"
        cv.voice_id = voice_id
        return voice_id

    def generate_character(self, cv: CharacterVoice) -> list[GenerationResult]:
        char_dir = self.out_dir / cv.slug
        results: list[GenerationResult] = []
        cat_counts: dict[str, int] = {}
        el_voice_id: str | None = None   # ensured lazily, only if an EL line appears

        for ln in cv.lines:
            cat_counts[ln.category] = cat_counts.get(ln.category, 0) + 1
            line_no = cat_counts[ln.category]
            engine = decide_engine(ln, self.policy)

            if engine == ELEVENLABS:
                version, ext, model = cv.voice_version, "mp3", self.line_model
                credits = ElevenLabsClient.credits_for(ln.text, self.line_model)
            else:
                version, ext, model = "gem", "wav", self.gemini.model_id
                credits = 0.0

            take = naming.next_take(char_dir, self.project, cv.name, ln.category, line_no, version)
            filename = naming.build_filename(
                self.project, cv.name, ln.category, line_no, take, version, ext=ext,
            )
            result = GenerationResult(
                character=cv.name, category=ln.category, take=take,
                filename=filename, path=str(char_dir / filename),
                engine=engine, model=model,
                credits_spent=credits if (self.execute and engine == ELEVENLABS) else 0.0,
                dry_run=not self.execute,
            )

            try:
                if self.execute:
                    if engine == ELEVENLABS:
                        if el_voice_id is None:
                            el_voice_id = self.ensure_voice(cv)
                        audio = self.client.tts(el_voice_id, ln.text, cv.config, model_id=self.line_model)
                        voice_ref, cfg = el_voice_id, cv.config.to_dict()
                    else:
                        gvoice = cv.gemini_voice or DEFAULT_GEMINI_VOICE
                        audio = self.gemini.tts(ln.text, gvoice)
                        voice_ref, cfg = gvoice, {}
                    if audio:
                        path = naming.write_audio(char_dir, filename, audio)
                        naming.write_sidecar(path, {
                            "project": self.project, "character": cv.name,
                            "category": ln.category, "lineNo": line_no, "take": take,
                            "text": ln.text, "emotionTags": ln.emotion_tags,
                            "engine": engine, "model": model, "voiceRef": voice_ref,
                            "config": cfg, "credits": credits,
                            "routeReason": route_reason(ln, self.policy),
                        })
                    preference_store.record_generation(
                        cv.name, ln.category, filename, engine, model, cfg, credits,
                    )
            except Exception as exc:  # never let one line kill the run
                result.error = str(exc)
            results.append(result)
        return results

    def run(self, master_path: str | Path, do_generate: bool = False,
            only_character: str | None = None) -> dict:
        characters = self.parse(master_path)
        if only_character:
            characters = [c for c in characters if c.name.lower() == only_character.lower()]
        report = {
            "summary": summarize(characters),
            "estimate": self.estimate_report(characters),
            "generated": [],
        }
        if do_generate:
            for cv in characters:
                report["generated"].extend(r.to_dict() for r in self.generate_character(cv))
        return report
