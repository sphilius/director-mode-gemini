"""Cost estimation — pre-spend visibility across ElevenLabs and Gemini.

This is the Regularizer that prevents "surprise credit burn": every generation
run is preceded by a dry-run estimate the human sees before anything is spent.
Estimates BOTH engines even though v1 only generates on ElevenLabs, so the
hybrid decision is informed.
"""

from __future__ import annotations

from backend.audio_director import pricing
from backend.audio_director.models import CharacterVoice, CostEstimate, LineCost
from backend.audio_director.router import RoutingPolicy, decide_engine, ELEVENLABS

# Voice-design assumptions (one-time per character, ElevenLabs only).
DESIGN_SAMPLES = 3   # previews generated per design round
DESIGN_ROUNDS = 2    # refinement passes before the voice is locked


def estimate_character(
    cv: CharacterVoice,
    plan_key: str = pricing.DEFAULT_ELEVENLABS_PLAN,
    regen_multiplier: float = pricing.DEFAULT_REGEN_MULTIPLIER,
    line_model: str = pricing.EL_DEFAULT_LINE_MODEL,
    design_model: str = pricing.EL_DEFAULT_DESIGN_MODEL,
    gemini_model: str = pricing.DEFAULT_GEMINI_TTS_MODEL,
) -> CostEstimate:
    plan = pricing.ELEVENLABS_PLANS[plan_key]
    usd_per_credit = plan.usd_per_credit
    line_cpc = pricing.EL_CREDITS_PER_CHAR[line_model]
    design_cpc = pricing.EL_CREDITS_PER_CHAR[design_model]
    gm = pricing.GEMINI_TTS_MODELS[gemini_model]

    est = CostEstimate(character=cv.name, regen_multiplier=regen_multiplier, el_plan=plan.name)

    # Per-line costs (kept line = generated chars * regen multiplier).
    for ln in cv.lines:
        chars = len(ln.text)
        el_credits_kept = chars * line_cpc * regen_multiplier
        el_usd = el_credits_kept * usd_per_credit

        in_tok = pricing.gemini_input_tokens_for(ln.text) * regen_multiplier
        out_tok = pricing.gemini_output_tokens_for(ln.text) * regen_multiplier
        gem_usd = (in_tok / 1_000_000 * gm.usd_in_per_mtok) + (out_tok / 1_000_000 * gm.usd_out_per_mtok)

        est.el_line_credits += el_credits_kept
        est.el_usd += el_usd
        est.gemini_usd += gem_usd
        est.per_line.append(LineCost(line=ln, el_credits=el_credits_kept, el_usd=el_usd, gemini_usd=gem_usd))

    # One-time voice-design credits (ElevenLabs only).
    design_text = cv.preview_text or cv.voice_design_prompt or ""
    design_credits = len(design_text) * design_cpc * DESIGN_SAMPLES * DESIGN_ROUNDS
    est.el_design_credits = design_credits
    est.el_usd += design_credits * usd_per_credit

    return est


def estimate_all(characters: list[CharacterVoice], **kwargs) -> list[CostEstimate]:
    return [estimate_character(cv, **kwargs) for cv in characters]


def render_estimate(estimates: list[CostEstimate]) -> str:
    """Human-readable pre-spend report for the CLI dry-run gate."""
    plan = estimates[0].el_plan if estimates else "?"
    regen = estimates[0].regen_multiplier if estimates else 0
    lines = [
        f"COST ESTIMATE  (ElevenLabs plan: {plan}, regen x{regen}, "
        f"pricing verified {pricing.PRICING_LAST_VERIFIED})",
        "-" * 74,
        f"{'Character':<16}{'Lines':>6}{'EL credits':>14}{'EL $':>10}{'Gemini $':>12}",
        "-" * 74,
    ]
    tot_lines = tot_credits = tot_el = tot_gem = 0.0
    for e in estimates:
        n = len(e.per_line)
        lines.append(
            f"{e.character:<16}{n:>6}{e.el_total_credits:>14,.0f}"
            f"{e.el_usd:>10.2f}{e.gemini_usd:>12.4f}"
        )
        tot_lines += n
        tot_credits += e.el_total_credits
        tot_el += e.el_usd
        tot_gem += e.gemini_usd
    lines.append("-" * 74)
    lines.append(
        f"{'TOTAL':<16}{tot_lines:>6.0f}{tot_credits:>14,.0f}{tot_el:>10.2f}{tot_gem:>12.4f}"
    )
    # Plan-budget context.
    plan_obj = next((p for p in pricing.ELEVENLABS_PLANS.values() if p.name == plan), None)
    if plan_obj and plan_obj.monthly_credits:
        pct = tot_credits / plan_obj.monthly_credits * 100
        lines.append("")
        lines.append(
            f"ElevenLabs: {tot_credits:,.0f} credits = {pct:.0f}% of the {plan}"
            f" monthly bucket ({plan_obj.monthly_credits:,})."
        )
        lines.append(
            f"Gemini (paid API) would cost ~${tot_gem:.2f} total for the same lines "
            f"- about {(tot_el / tot_gem):.0f}x cheaper." if tot_gem else ""
        )
    return "\n".join(l for l in lines if l != "")


def routed_summary(
    characters: list[CharacterVoice],
    policy: RoutingPolicy,
    plan_key: str = pricing.DEFAULT_ELEVENLABS_PLAN,
    regen_multiplier: float = pricing.DEFAULT_REGEN_MULTIPLIER,
    line_model: str = pricing.EL_DEFAULT_LINE_MODEL,
    design_model: str = pricing.EL_DEFAULT_DESIGN_MODEL,
    gemini_model: str = pricing.DEFAULT_GEMINI_TTS_MODEL,
) -> str:
    """What the HYBRID routing actually costs — per engine and combined."""
    plan = pricing.ELEVENLABS_PLANS[plan_key]
    upc = plan.usd_per_credit
    lcpc = pricing.EL_CREDITS_PER_CHAR[line_model]
    dcpc = pricing.EL_CREDITS_PER_CHAR[design_model]
    gm = pricing.GEMINI_TTS_MODELS[gemini_model]

    el_lines = gem_lines = 0
    el_credits = el_usd = gem_usd = 0.0
    el_characters: set[str] = set()

    for cv in characters:
        for ln in cv.lines:
            if decide_engine(ln, policy) == ELEVENLABS:
                el_lines += 1
                c = len(ln.text) * lcpc * regen_multiplier
                el_credits += c
                el_usd += c * upc
                el_characters.add(cv.name)
            else:
                gem_lines += 1
                in_tok = pricing.gemini_input_tokens_for(ln.text) * regen_multiplier
                out_tok = pricing.gemini_output_tokens_for(ln.text) * regen_multiplier
                gem_usd += in_tok / 1_000_000 * gm.usd_in_per_mtok + out_tok / 1_000_000 * gm.usd_out_per_mtok

    # Voice-design credits only for characters that have at least one EL line.
    for cv in characters:
        if cv.name in el_characters:
            dtext = cv.preview_text or cv.voice_design_prompt or ""
            dc = len(dtext) * dcpc * DESIGN_SAMPLES * DESIGN_ROUNDS
            el_credits += dc
            el_usd += dc * upc

    combined = el_usd + gem_usd
    lines = [
        f"ROUTED (mode={policy.mode}) - what the hybrid split actually costs:",
        f"  ElevenLabs : {el_lines:>3} lines   {el_credits:>10,.0f} credits   ${el_usd:>7.2f}",
        f"  Gemini     : {gem_lines:>3} lines   {'':>10}          ${gem_usd:>7.4f}",
        f"  COMBINED   : {el_lines + gem_lines:>3} lines   {'':>10}          ${combined:>7.2f}",
    ]
    return "\n".join(lines)
