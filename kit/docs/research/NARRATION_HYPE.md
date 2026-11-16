# NARRATION_HYPE — constant-hype narration for Roblox story shorts (2026-11-14)

User problem: our narrator "feels like it is just delivering a story". Viral creators keep the energy UP the whole way and
the narrator SAYS the sound effects ("woosh", "splash", "BOOM"). mosquito_town already does this ("Bzzzz! Poof!") and the
user liked it. This doc makes that the house style for every script + voice. Gate: `python tools/hype_lint.py <slug>`.

## 0. Measured references (2026-11-14, YouTube watch pages in the built-in browser, "Show transcript" panel = YouTube
auto-captions, duration from the player; wpm = transcript words / duration, [music] markers removed). Paraphrased, no quotes kept.
| # | URL | Channel | Views (seen) | Len | Words | wpm | Spoken SFX / interjections in transcript | Notes |
|---|---|---|---|---|---|---|---|---|
| 1 | https://www.youtube.com/watch?v=E9TTaFj-YXU (ref 5) | Haro Talks (165k subs) | 123k likes; views not read | 100.9 s | 446 | 265 | none; ASR tag [snorts] once | horror "In this world, if a cat...": rule in sentence 1 (0-3 s), 41 sentences (~11 w avg), threat-CTA "...everyone who doesn't leave a like" |
| 2 | https://www.youtube.com/watch?v=zzu-VJTRlM8 (ref 4) | Haro Talks | 1.4M in 2 days | 93.5 s | 408 | 262 | none | same template: rule + omen line in 0-8 s, 43 sentences (~9.5 w), same threat-CTA |
| 3 | https://www.youtube.com/watch?v=npdxivww0Xk | legendRBX | not read | 155.2 s | ~758 | ~293 | "what", "slam" | 2nd person ("you") throughout, 70 sentences (~11 w), fastest measured |
| 4 | https://www.youtube.com/watch?v=lrueeOM4VKg | RealDanty | 7,769,209 | 49.9 s | 233 | 280 | none | highest views; LONG run-on sentences (13 sentences, ~18 w avg), comedy-absurd, ends on a moral |
| 5 | https://www.youtube.com/watch?v=7SPMY6zHgsE | DinoPlays | not read | 63.4 s | 282 | 267 | "Poof" x6 (2 mis-transcribed "Poop"), "what" | comedy wish story: spoken SFX as a RUNNING GAG after each wish (~1 per 10 s), 3 questions, 55 sentences (~5 w) |
| 6 | https://www.youtube.com/watch?v=CV2b2H-OJzc | Told Wrong Tales | 24k / 1 day | 62.0 s | 233 | 225 | "No, no, no, no" | horror; cliffhanger ending |
| 7 | https://www.youtube.com/watch?v=qqniGB2Cb6I | Roblox Narratives | 54,730 | 117.9 s | 422 | 215 | "what" | comedy romance, calm delivery |
| 8 | https://www.youtube.com/watch?v=IYDIHuSlR7s | Except You | 9.1k / 1 day | 47.0 s | 134 | 171 | "pop" | slowest, lowest views |
| 9 | https://www.youtube.com/watch?v=QR-VrdQNMsg | Craftee films | not read | 51.3 s | 202 | 236 | none | not Roblox (3D rescue story), third-person news-like narration; craftee_films shorts list is mostly non-Roblox |
Caption style seen (screenshot, ref 5 at 0:01): 2-3 words per caption, white bold lower-case with the KEY word in a coloured
(magenta) caps line under it, centred in the lower third.

Findings (MEASURED):
- Pace is the hype. All 4 high-view videos run 262-293 wpm; the 3 small channels run 171-225. Our EP1 measured ~201 (text
  estimate) = the "just delivering a story" range. Target 260-290 delivered.
- The rule/hook is in the first sentence, inside ~3 s, in every "In this world/town" video (9/9).
- Spoken SFX in the transcripts are RARE outside comedy: 0 in the horror refs, but comedy (DinoPlays) uses ONE repeated SFX word
  as a running gag (~1 per 10 s). mosquito_town's "Bzzzz! Poof!" pattern matches this.
- Sentences: 5-11 words average; the 7.7M video breaks this with run-ons, so length is not a hard rule, speed is.
- CTA: both Haro Talks refs end on a threat-CTA ("the monster visits everyone who doesn't leave a like"); several others end on a
  twist/moral with no CTA.

What we could NOT see (honest list):
- Exclamation marks / CAPS: YouTube ASR captions carry no "!" and no SFX words that are not clear speech, so "!" density and
  shouted-vs-whispered contrast were NOT measured; energy curve per beat below is INFERRED, not measured.
- No audio was downloaded, so voice processing (EQ/comp/saturation) comes only from the earlier earshot measurement of refs 4/5
  (VOICE_SPEC.md); loudness/onsets for refs 6-9 are unmeasured. Pause lengths unmeasured.
- View counts for #1, #3, #5, #9 were not readable from the page (animated counter).
- Instagram and TikTok: not visited by this agent (the shared browser pane was in use by another agent on Instagram; tab
  contention), so no Reels/TikTok data. A scripted caption-track fetch was refused by the auto-mode permission check, so all
  transcripts came from the on-page transcript panel.
- WebSearch (standard) found only gig/marketing pages for the genre; YouTube search in the browser was what worked.

## 1. Targets (re-checked against section 0)
| Metric | Target | Basis |
|---|---|---|
| Delivered pace | 260-290 wpm (hype_lint text estimate PASS 235-290) | MEASURED: high-view 262-293, low-view 171-225 |
| Sentence length | median 5-11 words, max 14 (one deliberate run-on allowed) | MEASURED averages; max is our choice |
| Spark density | a spark (! / ? / spoken SFX / CAPS / "Wait") every <= 6 s, never > 10 s | INFERRED (user feedback + mosquito_town) |
| Exclamations in OUR text | >= 1.0 per 10 s | INFERRED: v3 needs "!" to perform energy; refs not measurable |
| Spoken SFX | comedy >= 1 per 10 s as a running gag; horror >= 0.6 per 10 s, quieter ("click.", "creak...") | MEASURED comedy ~1/10 s; horror refs 0 (user wants them anyway) |
| Pauses | <= 0.14-0.4 s; one 0.5-0.8 s stop-down before the twist (ref 5 has 0.3 s stop at 41.6 s, earshot) | partly measured |
| Hook | rule in sentence 1, within 3 s | MEASURED 9/9 |
| Direct address | >= 2 "you" lines or questions | MEASURED (#3 all 2nd person, #5 3 questions) |
| CTA | last 2 sentences: one-word two-option comment OR threat-CTA ("...visits everyone who doesn't leave a like") | MEASURED (refs 1-2) + LESSONS |

## 2. Energy curve template (0-10 intensity; narrator never drops below 5 except the one whisper beat)
"In this world" comedy (60-90 s): hook 9 -> rule + 3 examples 7-8 (each example ends on a gag + SFX) -> "But..." pivot 6 ->
escalation 8 -> 9 -> "Then I noticed something." 5 (whisper/low) -> payoff 10 (shout + SFX triplet) -> button 7 -> CTA 8.
Mystery / horror ("In this town", number_lies): hook 8 (urgent) -> rule 7 -> plant 6 (low, tense, still fast) -> rising 7-8
(digits ticking = SFX words "click... click") -> reveal 9 -> whisper beat 4 (ONE line) -> twist 10 -> cliffhanger 8 -> CTA 8.
Rule: every beat ENDS higher than it started; reset energy at each new take (section 4).

## 3. Spoken-SFX vocabulary (40) and placement
woosh, swoosh, zoom, vroom, BOOM, BAM, bang, kaboom, POW, wham, smack, slap, thud, bonk, CRASH, SPLASH, splat, plop, drip,
gulp, gasp, DING, beep, buzz/Bzzzz, zap, crack, snap, click, knock, creak, SLAM, POOF, pop, fizz, hiss, ka-CHING, honk,
SKRRT, crunch, boing. Also interjections: Wait, what?! / Nope. / Oof. / Ow! / Bro. / Yoink!
Placement rules:
1. SFX word goes AFTER the action clause it illustrates, as its own 1-word sentence: "My bag hit the pavement. THUD!"
   Exception: lead-in SFX for surprise ("BOOM! The screen flickered.").
2. One per 6-10 s on average; cluster up to 3 at peaks ("Bzzzz! Poof! Gone.").
3. Put it ON A CUT: the SFX word starts the new shot (cue sheet below), never mid-shot.
4. Real sound effect lands 0-40 ms BEFORE the spoken word onset (the ear hears the hit, the voice "names" it), at -6 to -10 dB
   under the voice so the word stays legible. Never let the real SFX mask the spoken one.
5. Caption: the SFX word is its own caption pop, ALL CAPS, 1.3x size, colour accent (yellow/orange), 2-frame scale overshoot,
   letters stretched for long sounds (BZZZZ, WOOOSH); max 6 letters plus repeats.
6. Horror: keep SFX words quiet/clipped ("click.", "creak...") rather than shouted; comedy shouts them.

## 4. ElevenLabs delivery recipe — Alex yl2ZDV1MzN4HbQJbMihG, eleven_v3
Settings: stability 0.0-0.3 (v3 "Creative"; 0.0 = most expressive, use 0.3 if a take wobbles), similarity 0.75, style 0.35-0.45
(up from 0.25 in VOICE_SPEC), speaker boost on, speed 1.0 at generation (speed up in post with atempo 1.08-1.15 until words.json measures 260-290 wpm).
Text tricks: CAPS on 1 emphasis word per sentence max; "!" not "!!!"; "..." only where a 0.3 s pause is wanted (v3 has no
<break>); "?!" for disbelief; SFX words as their own sentences; stretched spelling for length (Bzzzz, Woooosh).
Tags (lowercase, before the line): [excited] hook/payoff, [shouting] max 2 per video, [whispers] one beat only,
[gasps] before reveals, [laughs] on comedic gags, [fast-paced] on lists/escalation, [sarcastic]/[mischievously] on button lines.
Don't stack conflicting tags ([whispers][excited]). v3 may also render SFX tags ([explosion], [clapping]) as sound; we do NOT
use those — spoken words + our own SFX layer are controllable.
Takes: split by beat, 2-4 sentences (60-250 chars) per take, each starting with its energy tag, so v3 resets energy instead of
decaying over a long read. Generate each take once; regenerate only the takes that lint/listen flat. Join with 0.10-0.14 s gaps,
then the VOICE_SPEC post chain (silenceremove, atempo, HPF 80, +3 dB 4 kHz, comp 3:1 at -20 dB) plus for hype: faster attack
(5 ms) and a gentle saturation (ffmpeg `asoftclip=type=tanh` at low drive) so shouts stay dense; no reverb except a short
plate (<0.6 s) on the whisper line only; loudnorm I=-14 TP=-1.5.
"Blox Town": STT/TTS reads it "Blockstown". Options in order: (a) respell in the TTS text only: "Blocks Town" (two words,
caption keeps "Blox Town"); (b) pronunciation dictionary alias rule Blox -> Blocks via /v1/pronunciation-dictionaries
(alias rules are the v3-safe kind; phoneme rules only work on flash_v2 per the docs). Keep words.json on SCRIPT tokens
(LESSONS) so captions stay "Blox Town".
Credits: no test lines were generated for this doc (0 characters used).

## 5. Aligning spoken SFX with real SFX and caption pops (cue sheets)
In `ep1_cues.py`-style sheets entries are (shot, word_index, offset_s, name, vol, extra). For a spoken SFX word at index w:
`(shot, w, -0.03, "<sfx>", 0.8, {"spoken": True})` — real sound 30 ms before the word onset from words.json. Cut the new shot
on the same word (`@S(id, w, ...)` starts at w). captions2.py: give the word style "sfx" (caps, accent colour, pop) when
`hype_lint.is_sfx(word)` is true. make_audio_preview.py: duck the real SFX 4 dB under the voice for 0.25 s when "spoken" is set.
Map words to library names in sfx/: woosh->whoosh, boom->boom, buzz/bzzzz->buzz, beep->beep, bonk->bonk, click->click, ding->chat.

## 6. Rewrite checklist + examples
Checklist: [ ] hook spark in 3 s [ ] every sentence <= 14 words [ ] a spark every <= 6 s [ ] >= 1 spoken SFX / 10 s, on cuts
[ ] >= 1.5 "!" / 10 s [ ] one "Wait... what?" style turn before the twist [ ] one whisper beat only [ ] CTA one-word choice
[ ] hype_lint PASS/FIX only, no FAIL.

EP1 number_lies opening ~30 s — BEFORE (measured flat 31 s, 0 "!", 1 SFX):
"Look at your wrist. That number isn't your age… it's how many people have lied about you. In Blox Town, over forty, shops
flip their signs to CLOSED. Over ninety, police stop asking. I'm Harry..."
AFTER (written for this doc):
[excited] Look at your wrist! That number? NOT your age. It's how many people lied about you!
[fast-paced] In Blox Town, hit forty... SLAM! Shops flip to CLOSED. Hit ninety? Police stop asking. Woop woop.
I'm Harry! I deliver groceries. Zoom! And my left sleeve? Always down.
Every morning, Mom buttons my cuff. Click! "Covered, Harry. ALWAYS covered."
[gasps] This morning my wrist read zero-zero-zero. Then Tyler leaned on his locker. Bonk. "Honestly? I never knew you."
Click! Zero-zero-one. Wait... WHAT?!
Mosquito beat — BEFORE: "Mayor Gus hid inside a fridge. For three days." AFTER: "[laughs] Mayor Gus hid in a fridge. Slam! For
THREE days!" and add a CTA: "Would YOU sleep outside? Comment BITE or HIDE, and follow for part two!"

## 7. Hype lint spec + measured results (tools/hype_lint.py, defaults 4.5 w/s, max 14 words; retuned to section 0)
Rows: wpm estimate, longest flat stretch, long sentences, hook spark in 3 s, spoken SFX/10 s, exclamations/10 s, questions +
'you', CTA (thresholds in the tool docstring). Exit 1 on any FAIL.
| Script | wpm est | flat | long sent | hook | SFX | "!" | q/you | CTA | verdict |
|---|---|---|---|---|---|---|---|---|---|
| number_lies | 228 FIX (334 w, ~88 s) | 27.8 s FAIL | 0 PASS | PASS | 1 (0.11/10 s) FAIL | 0 FAIL | 2/10 PASS | PASS | FAIL |
| mosquito_town | 227 FIX (307 w, ~81 s) | 9.5 s FIX | 0 PASS | PASS | 14 (1.73/10 s) PASS | 28 (3.5/10 s) PASS | 0/4 PASS | FAIL | FAIL |
The wpm row is a text estimate (word count + punctuation pauses at 4.5 w/s); the real check is pacing.py on words.json after TTS
(raise its 215-245 band to 255-290 for hype formats: measured refs).

## 8. Root cause + tested fix (2026-11-14, voice_tests/NOTES.md, VOICE_SPEC.md "HYPE recipe")
EP1 flat = slow (185 wpm, no post speed-up) + narrow pitch (13.9 st) + flat loudness curve + one 108 s v3 take + script with no
sparks. Test: hype rewrite of the first ~25 s (voice_tests/hype_open.txt, lint FIX only on text wpm) voiced 3 ways (1,661 chars).
Winner B = per-line takes, stability 0.0, style 0.45, then atempo ~1.41: 264 wpm, f0 range 20.0 st (EP1 13.9).
Gemini (URL-only, one model's opinion): confirms techniques (whisper before reveals, spoken SFX pspsps/Poof, energy reset per scene,
0.1-0.3 s gaps, dry compressed voice) but its pace numbers (178-190 wpm) contradict our transcript count (262-293): ignore them.
