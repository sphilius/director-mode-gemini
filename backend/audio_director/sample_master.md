# ChoreQuest — Master Voice Prompts (sample / fixture)

This is the format the parser expects. One character per `##` header.
The first `[bracket]` on a line is its category; any later `[bracket]` tokens
are ElevenLabs v3 emotion tags, kept inline in the text.

## Iris
**Voice Design Prompt:** A warm, slightly raspy alto in her mid-30s. Grounded, dry wit, coaches without condescending. Natural North American accent.
**Preview Text:** Hey there — ready to knock out today's quests? I've got a good feeling about this one.
**Personality:** Encouraging but never saccharine; a little sardonic; celebrates real effort, gently calls out avoidance.

Config:
- stability: 42
- similarity: 78
- style: 55
- speed: 1.0
- guidance: 30
- loudness: 0

### Lines
- [greeting] Morning. Let's make today count.
- [greeting] [excited] You showed up — that's already half the battle.
- [streak-at-risk] Careful — your streak's about to slip. One quick win keeps it alive.
- [streak-at-risk] [concerned] Hey, don't let all that progress evaporate now.
- [task-complete] Nice. That's one down.
- [level-up] [excited] Level up! You earned every bit of that.
- [idle] Still here when you're ready. No rush.

## Grix
**Voice Design Prompt:** A gravelly, mischievous goblin-merchant baritone. Theatrical, fast-talking, fond of the player but always working an angle.
**Preview Text:** Ahh, back again! Grix has JUST the thing for a quester of your... particular talents.
**Personality:** Comic relief; greedy but loyal; needles the player affectionately.

Config:
- stability: 30
- similarity: 70
- style: 80
- speed: 1.05

### Lines
- [greeting] Ahh, back again! Grix knew you couldn't stay away.
- [repelled] [annoyed] Oi! That's not for browsers. Coin first, hands later.
- [streak-at-risk] Tsk tsk. A broken streak is BAD for business — yours and mine.
- [task-complete] [pleased] Heh. Efficient. I respect that.
