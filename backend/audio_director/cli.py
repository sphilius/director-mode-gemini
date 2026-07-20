"""Audio Director CLI.

Run from the repo root (so `backend` is importable):

    python -m backend.audio_director.cli parse    <master.md>
    python -m backend.audio_director.cli estimate <master.md> [--plan creator] [--regen 2.5]
    python -m backend.audio_director.cli generate <master.md> [--character Iris] [--execute]
    python -m backend.audio_director.cli baseline  <character>

Generation is DRY-RUN by default (no credits spent). `--execute` spends, and the
CLI requires an explicit "yes" first (Phase-1 human approval). `.env` is loaded
if python-dotenv is present.
"""

from __future__ import annotations

import argparse
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from backend.audio_director import preference_store
from backend.audio_director.audio_director import AudioDirector


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("master", help="Path to the master voice-prompt markdown file")
    p.add_argument("--project", default="chorequest", help="Project prefix for filenames")
    p.add_argument("--plan", default="creator", choices=["free", "starter", "creator", "pro"])
    p.add_argument("--regen", type=float, default=2.5, help="Regeneration multiplier")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="audio-director", description="Audio Director v1")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_parse = sub.add_parser("parse", help="Parse the master doc and show a summary")
    _add_common(p_parse)

    p_est = sub.add_parser("estimate", help="Show a pre-spend cost estimate")
    _add_common(p_est)

    p_gen = sub.add_parser("generate", help="Generate lines (dry-run unless --execute)")
    _add_common(p_gen)
    p_gen.add_argument("--character", default=None, help="Only this character")
    p_gen.add_argument("--out", default="backend/audio_director/out", help="Output directory")
    p_gen.add_argument("--execute", action="store_true", help="Actually spend credits + write files")
    p_gen.add_argument("--yes", action="store_true", help="Skip the confirmation prompt")

    p_base = sub.add_parser("baseline", help="Show learned vocal-tuning baseline")
    p_base.add_argument("character", help="Character name (or 'global')")

    args = parser.parse_args(argv)

    if args.cmd == "baseline":
        data = (preference_store.global_baseline() if args.character.lower() == "global"
                else preference_store.baseline_for(args.character))
        if not data:
            print(f"No accepted-take data yet for '{args.character}'. Generate + mark keeps first.")
        else:
            print(f"Baseline for {args.character}:")
            for k, v in data.items():
                print(f"  {k}: {v}")
        return 0

    director = AudioDirector(
        project=args.project, plan=args.plan, regen_multiplier=args.regen,
        out_dir=getattr(args, "out", "backend/audio_director/out"),
        execute=getattr(args, "execute", False),
    )

    if args.cmd == "parse":
        print(director.run(args.master).get("summary"))
        return 0

    if args.cmd == "estimate":
        rep = director.run(args.master)
        print(rep["summary"]); print(); print(rep["estimate"])
        return 0

    if args.cmd == "generate":
        characters = director.parse(args.master)
        if args.character:
            characters = [c for c in characters if c.name.lower() == args.character.lower()]
            if not characters:
                print(f"No character named '{args.character}'."); return 1
        print(director.estimate_report(characters))
        print()
        if args.execute and not args.yes:
            # Phase-1 human approval gate.
            reply = input("This will SPEND ElevenLabs credits. Type 'yes' to proceed: ").strip().lower()
            if reply != "yes":
                print("Aborted. No credits spent."); return 0
        report = director.run(args.master, do_generate=True, only_character=args.character)
        mode = "GENERATED" if args.execute else "DRY-RUN (no spend)"
        print(f"\n{mode}: {len(report['generated'])} line(s)")
        for g in report["generated"]:
            flag = "  ERROR: " + g["error"] if g.get("error") else ""
            print(f"  {g['filename']}{flag}")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
