# References: what we measured and what we saw (2026-11-13)

Evidence behind the v2 rules. "Measured" = computed from downloaded reference clips on this machine (ffmpeg scene
detection + faster-whisper). "Read" = from web pages/transcripts (see `research/notes_*.md`, with their honesty
notes). Nothing here was copied: it is used to set numbers and habits, never plots, characters or footage.

## Measured (11 clips, ffmpeg scdet threshold 8, whisper small.en)
| Clip | Format | Length | Cuts/min | Avg shot | Cuts in first 15 s | Narration |
|---|---|---|---|---|---|---|
| harotalks "dog growled" 10M | 360x640 30fps | 88 s | 56 | 1.07 s | 18 | 273 wpm, 71 words in 15 s |
| harotalks "thing under bed" 5.5M | 360x640 | 87 s | 54 | 1.10 s | 14 | 277 wpm, 66 w/15 s |
| atlassdoc "everything is free" 1M | 360x640 | 131 s | 50 | 1.18 s | 11 | 317 wpm, 82 w/15 s |
| atlassdoc "no kids" 720K | 360x640 | 137 s | 32 | 1.83 s | 13 | 310 wpm, 72 w/15 s |
| "In This Town" compilation 2.4M | 1280x720 60fps | 240 s | 71 | 0.84 s | 18 | 241 wpm, 59 w/15 s |
| "In This World" compilation | 1280x720 30fps | 240 s | 30 | 1.95 s | 10 | n/a |
| gibbsontv Liar's Bar 13M | 1280x720 24fps | 66 s | 45 | 1.32 s | 4 | music only |
| gibbsontv Backrooms 10M | 960x720 30fps | 115 s | 27 | 2.21 s | 3 | music only |
| gibbsontv Spooder-Man 10M | 1280x536 24fps | 67 s | 13 | 4.2 s | 5 | music only |
| BonkieDoge Moon-Animator meme 54M | 360x640 30fps | 13 s | 9 | 4.5 s | 2 | none (one continuous shot) |
| saltnyako 6M | 960x720 20fps | 29 s | 0 | 29 s | 0 | none |

Take-aways
1. Narrated "In this world" shorts really are fast: 240-317 wpm and a cut every ~1.1 s. **Speed was not our problem.**
2. Our v1 felt "1.5x" because we **stacked time-stretching** on a voice recorded at ~190 wpm: ffmpeg atempo 1.15, then
   retempo x1.355 = x1.56 total, which squeezes the vowels and makes any voice sound sped-up. The references sound
   natural at the same wpm because the performance was *recorded/rendered fast* (or only lightly sped, pitch-corrected).
   Fix: let the voice model do the speed (voice_settings.speed <= 1.15), no ffmpeg stretch above 1.12, target 215-245 wpm (v2; SUPERSEDED in v3.7 by 255-290 wpm for hype formats, docs/FORMATS.json).
3. Our shots also moved too much: nearly every shot was a 40-60% push-in plus shake in ~1 s. Reference story shorts
   keep most moves gentle and vary shot TYPE (wide, medium, close-up, insert, over-the-shoulder, POV) cut to cut.
4. gibbsontv (cinematic) holds shots 1.3-4 s and relies on lighting, scale and one strong camera idea per shot.
5. The viral 54M meme is a **single continuous POV-style shot** with realistic lighting, DoF and a clear gag: craft in
   one shot beats many sloppy cuts.

## Seen (frame contact sheets of the references)
- **Lighting**: warm/cool contrast (amber lamps vs blue night), soft real shadows, a rim light on the character, real
  depth of field (backgrounds blurred), bloom on bright objects. harotalks interiors: dark room + one warm lamp.
- **Environments are dense**: bakery with shelves of bread, supermarket aisles, brick walls with texture, props
  everywhere. v1 re-used one school building in every town shot and left skies/floors empty.
- **Characters** are full Roblox avatars with hair/accessories/faces and clean clothing colours; animals are fuller
  models (furry-looking dog, crate, lamp), not single primitives.
- **Captions**: Poppins-style heavy sans, white with thick black outline, 2-4 words per line, the KEY word recoloured
  (red, purple, yellow, orange), centred in the lower third, above the app UI zone.
- **Camera**: macro inserts (bread dough filling the frame), low hero angles, POV with a held prop, Dutch angles for
  horror, whip/blur transitions; subjects always large in the 9:16 frame (face/torso fill 40-70% of height).
- **Scale**: small things are shown in extreme close-ups with a separate big copy, never enlarged in wide shots.

## Read (from research/notes_story.md and notes_visuals.md)
- Format is hot right now (Aug-Nov 2026): 4-14M hits from small channels too (Flookus 75K subs: 7.3M).
- Hit lengths 0:38-2:58; one-sentence rule in the first 1.2-3.4 s; 3-5 concrete examples; underdog narrator;
  escalation; twist; short punchline/callback ending (+ optional in-world CTA).
- AI as the setting works only when intimate and rule-based ("Machine Judge" 7.5M, "Robots Have Humans" 2.3M); a generic
  "AI attack" got 69K and 36 views.
- YouTube is de-prioritising re-uploaded content and can demonetise templated, mass-produced videos ("inauthentic
  content"): every video needs its own script, cast and sets, not a re-skin.
- Moon Animator easing: linear looks robotic; Sine/Quad natural; Back overshoot; anticipation + follow-through matter.

## Not verified (be honest in reports)
Which TTS voice any channel uses; audio loudness/music genre; exact fps/lens/camera data of those channels; retention %.
