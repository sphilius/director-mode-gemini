# Dominic Saga — Master Voice Prompts (creative-IP test)

Narrative/character VO rather than game-UI barks. Demonstrates the Audio Director
on dark-fantasy IP: expressive lines skew toward ElevenLabs; only flat ambient
lines fall through to Gemini. Categories here map to dramatic beats, not app events.

## Cedric
**Voice Design Prompt:** A weary man in his late 20s, warm baritone worn thin by grief. Resolve under exhaustion; the sound of someone who has carried too much for too long and keeps walking anyway. Grounded, no theatrics.
**Preview Text:** I used to think saving people was the simple part. I was a fool, and fools get everyone killed.
**Personality:** The reluctant savior. Idealism calcified into duty. Speaks plainly; the weight is in what he won't say.

Config:
- stability: 55
- similarity: 80
- style: 45
- speed: 0.97
- gemini_voice: Charon

### Lines
- [monologue] I used to think saving people was the simple part.
- [lament] [heavy] She trusted me. That's the part I can't set down.
- [resolve] [firm] If the price is my name, my peace, my soul — then it's paid. Move.
- [ambient] [engine=gemini] Rain again. Of course it's rain.

## Dominic
**Voice Design Prompt:** A charismatic reformer-king in his 40s, rich commanding baritone that knows how to fill a room. Persuasive, magnetic, utterly certain — with hairline fractures of guilt that surface only when he thinks no one is listening.
**Preview Text:** They will call it a massacre. History will call it necessary. I will call it Tuesday, and I will sleep.
**Personality:** The tragic usurper. Ends justify means, all the way down — until they don't. Late-stage atonement he can't yet admit he wants.

Config:
- stability: 40
- similarity: 78
- style: 70
- speed: 1.0
- gemini_voice: Orus

### Lines
- [decree] [commanding] The old order fed on your children and called it peace. I am done being polite to it.
- [threat] [cold] Kneel, or be a lesson. I have no shortage of lessons left to teach.
- [confession] [quiet] I told myself every death bought a hundred lives. I never once did the arithmetic.
- [rally] [rising] We do not get to be clean. We get to be the last ones standing. Choose.

## Canus
**Voice Design Prompt:** A vast, serene, paternal presence — a creator-deity voice, unhurried and gentle in a way that becomes menacing precisely because it never rises. Cathedral reverb baked into the timbre. Speaks as one soothing a frightened child while withholding the truth that would free them.
**Preview Text:** Do not weep for the wall. The wall is love. The wall is the only reason you have a throat with which to weep.
**Personality:** The authoritarian creator. Savior complex made cosmic. Maintains reality through a foundational lie he believes is mercy.

Config:
- stability: 70
- similarity: 85
- style: 35
- speed: 0.9
- gemini_voice: Kore

### Lines
- [pronouncement] [serene] Do not weep for the wall. The wall is love.
- [rebuke] [gentle] You mistake the cage for cruelty, child. I built it around the fire, not around you.
- [lie] [tender] There was never a shattering. There was only ever Me, and the peace I have given you.

## Naszsir
**Voice Design Prompt:** A silken, amused antagonist — androgynous, precise, delighting in every syllable. Cruelty worn as courtesy. The voice of someone who has already read the last page and finds your struggle charming. Light, unhurried, never raises the volume because it never needs to.
**Preview Text:** Oh, don't stop on my account. You were doing such marvelous work convincing yourself you had a choice.
**Personality:** The elegant nihilist. Stokes wars, weaponizes prophecy, savours the moral collapse of better people.

Config:
- stability: 45
- similarity: 82
- style: 85
- speed: 1.03
- gemini_voice: Puck

### Lines
- [taunt] [amused] Oh, don't stop on my account. You were doing such marvelous work.
- [prophecy] [silken] I told them a truth shaped like a hope. They did the rest to themselves.
- [menace] [soft] I will not raise a hand against you, hero. I will simply wait. I'm very good at waiting.
- [aside] [engine=gemini] Mm. Predictable. But then, that is the point.
