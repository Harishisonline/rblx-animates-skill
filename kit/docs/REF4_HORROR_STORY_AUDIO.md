# REF 4 horror bible: story, narration, original sound (2026-11-13)

Source: REF 4 https://www.youtube.com/shorts/zzu-VJTRlM8 (crows / "the sliver"), cross-checked with REF 5 (same creator style).
Visual target stays REF 1 (cinematic look, see LOOK.md / REFERENCES.md). Notes + timed transcripts:
`~/RobloxStories/research/refs/ref4/` (cutlist_notes.md, transcript_timed.txt).
CAVEAT: the video file could not be downloaded (YouTube 403), so the audio findings come from caption timing and the
auto-caption `[music]` tags (only 2 in 92 s), not from an earshot reading. Before relying on exact dB values, drop the mp4 in
`~/RobloxStories_tmp/refs/ref45/` and run `earshot` (loudness curve, music/voice/sfx split) to confirm. Levels below are our
targets, derived from AUDIO.md norms, not measured from the ref.

## 1. What makes REF 4 different
- Story is a classic folk-horror fable in "In this world" form: a rule, a pet/ally, an object clue, a named monster, a twist
  that reinterprets the rule (the omen was protection). Dread comes from the rule being COUNTABLE (1 crow -> 20 -> a tree full).
- No viral meme/phonk/"spooky piano" bed under the whole thing. Narration carries it; music only surfaces at two moments
  (the warm gift montage ~15 s and the monster naming ~61 s). The rest is room tone, small foley and silence.
- Every sentence is one picture; nothing is described that is not shown.

## 2. Beat template, 80-90 s horror (~230-250 wpm, 330-370 words)
| t (s) | Beat | Rule | Sound |
|---|---|---|---|
| 0-3.5 | HOOK = rule | "In this world, <omen> means <someone is taken>." 10-14 words | cold open: room tone + 1 diegetic omen sound (caw, tap). No music |
| 3.5-10 | Make it countable | 1 sign = watching, many = tonight. Gives the viewer a meter | omen sound repeats, closer/denser each time |
| 10-17 | PLANT the ally + object | narrator's small kindness (feeds/pets) + an object exchange | only warm moment: soft 2-note motif (music box/celesta) -12 dB under voice |
| 17-26 | TURN 1 | ally behaves wrong (stares) + count jumps + the WRONG object (fingernail) | motif stops mid-phrase; drone fades in at -30 dB; one dry sting on the object |
| 26-30 | Adult fails | dad/teacher tries a normal fix; it doesn't work | loud diegetic action (clang) then hard silence 0.6 s |
| 30-45 | ESCALATE x2 | home -> school -> home; omen follows | drone +3 dB per escalation; pulses slow (60 bpm heartbeat-like low thump, not a beat) |
| 45-51 | MIDPOINT REVERSAL | the omen is not looking at you, it's looking at THE DOOR | everything drops to room tone; the single important sound (tapping) |
| 51-61 | MONSTER REVEAL by parts | sound -> fingers -> arm -> full height; callback detail (missing nail) | sub-bass swell 3-4 s, no hit until full height, then a low thud + air |
| 61-64 | NAME + one rule | "It was the <name>. It <verb>s kids <how>." | the motif returns detuned/slow, 1 phrase (the ref's 2nd [music] tag) |
| 64-74 | CLIMAX choice | narrator acts on the planted ally/object | rising cluster/riser 6-8 s, foley drag/peck; cut to black = everything cut, 0.5 s silence |
| 74-83 | TWIST reframe | "They never X to take me. They X so it couldn't." | open fifth pad, quiet, wind |
| 83-88 | CALLBACK reward | planted object returns transformed (the other nine nails) | motif back in original warm key, one phrase |
| 88-90 | CTA sting | monster now targets "anyone who doesn't like" | drone + one omen sound, cut on the last word |

Timing rules: rule finished by 3.5 s; ally+object planted before 17 s; monster not shown before 50 % of runtime; name said
exactly once; twist in the last 18 %; the last image echoes the first.

## 3. Narration writing rules
1. First person, past tense, plain kid vocabulary; sentences 5-12 words; one image per sentence.
2. Rules are stated as fact, never as "legend says". Make the rule measurable (numbers, distance, count, nights).
3. Use the "Then one morning, ... It just stared at me." pattern: a normal routine, then one detail is wrong.
4. Describe the monster by PARTS and TEXTURE (long, gray, flat as paper, tipped sideways), never by adjectives like scary/creepy.
5. Adults are kind but useless, never stupid. Their fix is concrete (clang pots, lock doors, move the desk).
6. Short fragments for shocks: "A long gray fingernail." "Fog. Still here." "Nothing."
7. Callbacks: every planted object pays off twice (clue on the monster, reward at the end).
8. Twist is a mirror sentence of the rule ("They never gathered to take me. They gathered so it couldn't.").
9. CTA stays in-world and ends on the rule ("...the door of everyone who doesn't leave a like.").
10. Voice delivery (ElevenLabs): calm, low, close-mic, slightly faster on lists, slower (+15 % gaps) on reveal sentences;
    stability ~0.55, style low. Never "spooky voice". Leave 300-600 ms after shock fragments (use retempo.py / tighten.py
    to protect those gaps rather than closing all silence).

## 4. Original-sound recipe (replaces the repetitive viral track)
Layers, all original or CC0/real-library; mix targets relative to voice peaking around -16 LUFS short-term:
| Layer | What | Make it with | Level vs voice |
|---|---|---|---|
| A. Room tone | location bed (bedroom hum, fridge, distant traffic, wind on glass), never true silence | real-sfx ambience role / Kenney rpg-audio; else forge a filtered brown-noise bed (lowpass 400 Hz, slow 0.1 Hz amplitude drift) | -32 to -28 dB |
| B. Diegetic omen | the story's signature sound (caw, tap, scratch, breath on glass) | real recordings; `earshot rank "<desc>" folder --top 5`; vary pitch +-2 st each repeat, get closer (less reverb, more level) | -14 to -8 dB, foreground |
| C. Drone | 2 detuned sines/saws at 40-55 Hz + a filtered noise air band, a minor-second cluster on top at 220-233 Hz | `tools/synth_sfx.py` / earshot forge (generative, seed per video); automate lowpass 300 -> 2 kHz across the escalations | starts -30, ends -18 |
| D. Motif | 2-4 note theme on music box/celesta/plucked string, kid-like | synthesize (FM bell: ratio 3.5, fast decay) or ElevenLabs music with prompt "solo music box, 4 notes, no drums"; reuse detuned (-50 cents, half speed) at the name drop | -12 dB, only at plant / name / callback |
| E. Reveal swell | sub swell 30-50 Hz 3-4 s + reversed reverb tail of the omen sound into the reveal | synth + reverse of layer B | peaks -10, then cut |
| F. Impacts | 1 low thud per act (object insert, full-height reveal, bed drop), NOT on every cut | real-sfx hit role, lowpassed, + 1.5 s dark reverb | -8 dB |
| G. Foley | footsteps, blanket drag, lock click, pecks; dry and close | Kenney rpg-audio foley, real-sfx `from_cues.py` | -14 dB |
| H. Silence | true drop to room tone only, 0.4-0.8 s, 2-3 times per video (after clang, before tapping, after black-out) | mute B-G, keep A | — |

Design steps:
1. Lock the voice first; mark the beats in `audio/cues.json` (hook, plant, turn, reversal, reveal start/peak, name, climax, black, twist, callback).
2. Build A for each location, crossfade 0.5 s on location changes.
3. Place B on picture; real recordings only (run `earshot realness` on candidates; reject anything that reads synthetic).
4. Generate C with a fixed seed; automate filter/level per beat table; side-chain duck C by 4-6 dB under the voice.
5. Compose D once per video (original melody), place 3 times max.
6. Place E/F only on the 3-4 marked peaks; everything else is foley.
7. Carve H: hard-cut all non-ambience layers at the silence marks.
8. Master: -14 LUFS integrated, TP <= -1 dBTP; check with `tools/audio_qa.py <slug>`; check that loudness RISES across the
   video (escalation) by reading the short-term LUFS curve: first 15 s should be ~4-6 LU quieter than 60-75 s.

## 5. Mistakes to avoid
- The viral Roblox horror bed (same phonk/"creepy piano"/meme track looping from 0 s). It flattens dread, signals "template", and
  risks Content ID. Never use a trending track in horror.
- Music wall-to-wall. If music plays more than ~35 % of runtime it is too much.
- Stingers on every cut / jump-scare screams. One impact per act.
- Silence that is digital zero (sounds like a glitch). Silence = room tone.
- Monster shown in the first half, or explained twice, or given a backstory dump.
- Abstract adjectives ("terrifying", "creepy") instead of parts and textures.
- Twist that introduces a new rule instead of reframing the first.
- Grade: crushed pure black or teal-orange action grade. Use REF 1 look with a cold night grade (see below).

## 6. Camera, light and grade for dread (apply on REF 1 cinematic base)
- Night interiors: one motivated source (window moonlight 6500-8000 K, low; or phone/hall light warm 2700 K through the door gap),
  everything else falls off to blue-grey shadows with lifted blacks (floor ~0.03-0.05, not 0). Volumetric haze low density
  so the window beam reads.
- Shots 1.6-2.4 s normally; reveal shots hold 2.5-3.5 s with a very slow push-in (2-4 % per second). Climax shots 0.8-1.2 s.
- Reveal grammar: low floor camera at the door gap (lens 24 mm, 15 cm off floor), tilt up as the monster rises; edge-on
  silhouette shots (monster turns sideways = vanishes).
- POV-from-bed shots for night beats; over-the-shoulder at the window for omen counting; inserts (ECU) of every story object.
- Grade: desaturate 15-25 %, shadows toward teal-blue, highlights neutral-warm only on safe things (ally, motif moments), slight
  green-grey in monster scenes, film grain 2-3 %, soft vignette 15 %.

## 7. Gap list for the kit (code is owned by a later phase)
1. No generative score tool: need `tools/score.py` (drone/motif/swell generators from a beat list, seeded, stems out).
2. `finish.py` mixes one music file at a fixed dB; needs per-beat automation (level + lowpass) and side-chain ducking.
3. No ambience/room-tone library: real-sfx index has 29 ambiences; need a CC0 room-tone/wind/night pack (user approval to download).
4. cues.json has no beat types (plant/turn/reveal/silence); add them so mixing and grade can key off beats.
5. No silence-protection in tighten.py/retempo.py (they shorten gaps the horror needs).
6. `look.py` has no `night_dread` preset (moon key + lifted blue blacks + haze + grain); `cams.py` lacks floor-gap tilt-up and
   reveal-by-parts recipes.
7. `audio_qa.py` should report the short-term loudness slope (escalation check) and % of runtime with music.
8. No creature cast (see REF5_ENTITIES.md).
9. Reference audio not measured yet: get the mp4 manually and run earshot to replace the inferred values here.
