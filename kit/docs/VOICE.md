# Voice: choosing and recording the narrator

## Why v1 sounded "like 1.5x speed"
It was: the voice was recorded at ~190 wpm, then ffmpeg-sped x1.15 and x1.355 (total x1.56) to reach 258 wpm. Time-stretch
squeezes vowels and breaths. The reference narrators run 240-317 wpm but sound natural because they were performed/rendered
fast, not stretched afterwards.

## v2 rules
1. **Pick the voice first, with samples.** `python tools/eleven.py voices` then
   `python tools/eleven.py sample "<first 30 words of the script>" Voice1,Voice2,... --model eleven_turbo_v2_5 --speed 1.1`.
   Send the clips to the user (SendUserFile) and wait for approval. Never generate the full read before approval.
2. **Speed comes from the voice model**: `voice_settings.speed` (config `tts_speed`, default 1.05, max 1.15).
   `voice_run.py` now defaults to `--speed 1.0` and refuses > 1.12; `retempo.py` refuses factors > 1.12 (`--force` to override).
3. **Write for the ear.** 5-12 word sentences, contractions, no hard-to-say strings, onomatopoeia spelled phonetically
   ("Bzzz"), numbers as words. Mark emphasis with punctuation (dash, "!", short sentence). With v3-style models, audio
   tags like [whispers] or [excited] are allowed when the model supports them: test on a sample first.
4. **Delivery settings**: stability 0.35-0.45 (more expressive), style 0.4, similarity 0.8, speaker boost on.
5. **Targets after processing (v3.7)**: the format band from docs/FORMATS.json (In this world/town, horror, comedy:
   255-290 wpm, 62-75 words in the first 15 s; legacy calm format `natural`: 215-245 wpm, 60-72 words), no gaps > 0.45 s inside a sentence, 80-150 ms
   gaps after punchlines, slow 5-10% on the twist line.
6. Run `python tools/pacing.py <slug>` after the voice and after the shot list.

## Candidate narrator voices on a fresh ElevenLabs account (premade, free)
Chris (casual, down to earth, natural pace), Charlie (energetic/hyped), Will (relaxed optimist), Eric (smooth), Callum (husky
trickster, good for comedy/horror), Liam (young social-media creator, but sounded too synthetic at x1.5), Brian (deep, cinematic).
Which voice any viral channel uses could not be verified; the RoShot product's default is "Adam C". Always audition.

## Approval gate
The user approves (a) the voice sample, (b) the character/graphics look-dev pack, (c) the script, in that order, before any
full voice generation or render (credits and an hour of render time are at stake).
