---
name: "rblx-animates"
description: "Make original Roblox-style 3D story reels the RBLX ANIMATES way (In this town/world first, Blox City, dripdyl-style Big Game) and run the growth loop: check reach and stayed-to-watch, compare with dripdyl, fix gaps, update the skill."
---

# RBLX ANIMATES: Roblox story video studio

This skill reproduces the production line behind the Instagram channel @rblxanimates: original, blocky Roblox-style 3D story
reels, 9:16 (In-this-town Shorts 80-120 s; Blox City storylines 90-120 s; plus ~20-minute compilations of uploaded videos),
narrated by one fast, upbeat voice, with meme sound effects, burned-in captions, a like/share/follow end card on Blox City episodes only, and a growth loop that measures the channel, compares it side by side
with Shorts that are winning right now (benchmark: @DripDyl) and updates this skill from what works. The quality bar is the two finished episodes in `examples/`:
EP2 "The Poor Boy Who Bought the School" and EP3 "I Told ONE Secret. By Lunch, Everyone Knew."

The work is long (about 5 hours, 2.5 of them unattended rendering) and the person cares about each stage, so the line has
**approval gates**. Treat them as part of the craft, not bureaucracy: every gate exists because skipping it once cost hours.

| # | Stage | Gate (stop and wait for the person) |
|---|---|---|
| 0 | Setup check | - |
| 1 | Viral research (when asked, when topics run dry, or when the growth loop finds a weak stage) | - |
| 2 | Topic + script | **Script + title approved** (white card) |
| 3 | Music question | **Music answer** (their track or the default) |
| 4 | Voice take | **Voice OK** (they listen) |
| 5 | Meme SFX + mix | - (they hear it with the voice gate or the final) |
| 6 | Shots + low-res QA | - |
| 7 | Look-dev stills | **Look OK** |
| 8 | Final render + finish | - |
| 9 | Delivery + wrap-up | **Never post** without an explicit yes for that exact file |

If the person says "just make it, we'll review after", gates 4 and 7 may be skipped for that episode; write that down in
the episode's `story.json` (`"gates": "waived by the user <date>: '<their words>'"`).

---

## 0. Setup check (once per machine, 2 minutes)

The kit is the `kit/` folder of this repository, installed to `~/RobloxStories` by `scripts/install.sh`. Episode work lives in
`~/RobloxStories_tmp/<slug>` with a symlink `~/RobloxStories/videos/<slug>` pointing at it (Blender tools find episodes
through `videos/`). Check, in this order, and fix before writing anything:

1. `~/RobloxStories/rbx/shotlib.py` exists (else run `scripts/install.sh` from this repo).
2. Blender 5.3+: `/Applications/Blender.app/Contents/MacOS/Blender --version` (macOS) or `$BLENDER`.
3. `ffmpeg -version`, and `~/RobloxStories/.venv/bin/python -c "import numpy, PIL"`.
4. ElevenLabs: `~/RobloxStories/.env` has `ELEVENLABS_API_KEY=` (paid tier; library voices fail on free keys).
   `cd ~/RobloxStories/tools/ep_audio && python3 el.py` prints tier and credits left. **Never print or paste the key.**
5. Optional ears: a browser with Gemini (gemini.google.com) for listening reports (see section 5).

Running from a cloud agent linked to the person's computer: run Blender and long jobs **on the computer, detached**
(`subprocess.Popen(..., start_new_session=True)` or `nohup` there). Sandboxed shells usually kill background jobs when the
call ends; a 2-hour render must not depend on your shell staying open. Poll logs instead of waiting inside one call.

---

## 1. The formats - never mix them

Read the reference for the format you are making before writing a single line.

**Blox City** (`references/BLOX_CITY.md`): storyline episodes, each one custom. A first-person kid narrator, a clear wrong
(bullying, betrayal, a secret sold), an escalation, a reversal and a warm callback ending. Blox City branding is allowed
("Blox City High", "Blox Tea"). Ideas: `references/EPISODE_CATALOGUE.md` (Day 01-30 with punchy titles; 01 and 02 are made).

**In this town / In this world** (`references/INTOWN_FORMAT.md`, `FORMATS.json`): premise in the first sentence
("In this town, every lie shows on your wrist"), short dense sentences, time-marked escalation, twist ending. Its own bed and
rules. Never put Blox City names or branding into it.

**Current priority (owner, 2026-11-17): new viral "In this town / In this world" videos built to the section 2 and
section 3 rules. Do not remake or re-render old episodes.**

**Big Game (dripdyl style)** (section 2 rules, `RESEARCH_2026-11-17_dripdyl_gemini.md`): the owner's benchmark format. Cold open "I [tiny action] and [huge
overreaction]" ("I stepped off a couch and 50 firefighters blasted me with fire hoses."), then "Welcome to the world's
biggest game of [playground game]", "The rules were simple." (3 strikes, last one standing wins $1,000,000), a roster of
absurd rivals (one hasn't moved since 2019, a grandma, a 5x champion), traps and eliminations each with a deadpan tag
("He went down." / "Worth it."), the narrator wins by **noticing a small detail**, a host fake-out, and a 3-8-word home
callback gag ("I've been up here for 3 days."). dripdyl runs 130-165 s at 3.7-4.2 words/s; our Shorts are 80-120 s. Original games and gags only.

All formats share the narrator, the ending rule (`references/ENDING_RULE.md`), the look and the kit.

---

## 2. Viral research (when asked "what's trending", when the growth loop finds a weak stage, or before a new batch)

Goal: learn the mechanism of videos that are winning **right now**, as rules you can apply. Copy the mechanism, never the
script, title or characters. The proven method (2026-11-17, 16 videos, `RESEARCH_2026-11-17_dripdyl_gemini.md`):

1. **Find candidates.** The person's links first. Then the benchmark roster (`references/COMPETITORS.md`): @DripDyl
   (benchmark the owner wants to match), @butterbloxe, @GreenBroRants, @Gneef, @RyoRants, @Xenost-j3i, @itsRedBear, @PurpleHat. Then
   YouTube search by upload date and by views ("roblox story", "in this world", "in this town", "roblox animation story")
   and the Shorts shelf. Prefer **outliers**: a Short with views >= 10x the channel's subscribers, or >= 5x its median.
   Ask Gemini (same task chat, step 3) for 10 more from the last 30 days with exact `/watch?v=` links; it finds them, you
   measure them. On 2026-11-17 all 10 of its links were real but only 1 was a winner (8.5M); the rest had 6k-370k views,
   so filter by measured views and outlier score before learning from anything.
2. **Measure with yt-dlp (numbers only come from here):** `yt-dlp --skip-download -J https://www.youtube.com/watch?v=ID`
   for views, likes, comments, duration, upload date, channel subscribers; `--write-auto-subs --sub-langs "en.*" --sub-format
   json3` for the words. From the captions compute words per second, the first sentence, when the crisis starts, the ending
   line. Use `/watch?v=ID` links, never `/shorts/` (it auto-advances). No media is downloaded.
3. **Watch with Gemini, Task mode, one chat.** Signed-in pro account at `https://gemini.google.com/u/1/app` (the person's
   default for research; check the avatar says the pro account and the picker says **Hydrogen**). Click **Task** (not Chat:
   Chat mode often answers "I can't watch YouTube" and refuses several videos at once). Keep the whole research run in **one
   task chat**; follow-ups go into that chat, never new chats. Write "Watch each of these Shorts one by one with the YouTube
   tool" and give all links as `/watch?v=` URLs. Ask per video for: what is on screen in the first 3 s and the first sentence;
   structure with timestamps; narrator voice (gender, age, accent, pitch, energy, pauses, punchline delivery, side-character
   voices); shot length, camera, why the motion looks clean; faces and overlays; caption style/position; music moods and SFX;
   the ending; why it went viral. End the same task with a voice-direction brief and an animation checklist. Read the answer
   with JS (`[...document.querySelectorAll('model-response')].at(-1).innerText`), wait 30-60 s per video.
4. **Trust levels.** Gemini is good at describing visuals, structure and delivery. It is wrong on numbers (it said 165 words
   where the transcript had 276, and 175-190 wpm where dripdyl measures 220-250) and cannot name music. Numbers: yt-dlp.
   Music: Content-ID card, on-screen credit or the person's Shazam. Mark everything else "Gemini, unverified".
5. **Record** per video in a dated `RESEARCH_<date>_*.md` (Project + repo `references/`): ID, channel, subs, views, likes,
   comments, runtime, date, outlier score, words/s, first sentence, beat map with times, ending, voice notes, animation notes,
   lesson. Then turn findings into rules (section 11 step 3) - a finding is not a rule until it is observed in 3+ channels.

### What the winners do (observed in 16 Shorts + 10 measured finds, 2026-11-17; re-check monthly)

- **Sentence 1 is the whole premise**, and frame 1 **shows it working** (the boy visibly shrinks; numbers float over heads;
  50 firefighters blast him). No title card, no greeting.
- **Rule + cost/condition in sentence 2** ("...but if they get the ick, it's gone"; "the only way to grow back is a truth
  that's hard to say"), then **3-4 absurd world examples with numbers and authority figures** (mayor the size of a pencil,
  grandma 500 pull-ups), then **"And me?"**: the narrator's handicap or the opposite of everyone.
- **"Until one night..." / "On Friday..."** brings a family or crush stake (sister in a fire, mom's last word).
- **The weakness is the only solution / the villain trips his own rule** (the 4-inch kid is the only one light enough; the
  narrator yells "RON! YOUR MOM IS HERE!"; the liar mayor is forced to answer yes/no live).
- **Numbered escalation** ("Night 1... Night 5", "Strike one... Strike three", an on-screen clock) gives the rhythm.
- **The rule solves the crisis in reverse** (lie on purpose to shrink into the vent; the useless toast power floats the bus).
- **Visible counters/progress bars** (BRAD'S CRUSHES: 212 -> 0, word counts, 0 -> 8,000,000,000) act as a clock.
- **Pace 3.8-4.9 words per second** (dripdyl 3.7-4.2, In-this-world hits 4.1-4.9). Near-zero dead air.
- **Cuts every 0.5-2.5 s**, camera never still, 2D face swaps on the beat, anime overlays (sweat drops, "!", hearts, comic
  starbursts), 1-3-word yellow/white captions with a heavy black stroke.
- **Music changes mood with the story** (playful -> tense -> warm/triumphant) and drops to silence for a wait; SFX on
  nearly every cut.
- **Endings:** a callback gag (dripdyl: "I've been up here for 3 days"), an emotional truth line, a rule-reversal twist, or a
  cliffhanger question that sets up Part 2. Most have no like/share CTA; one used an open comment prompt.
- **Runtimes split in two:** In-this-world rule stories 37-57 s, and storyline/game stories 135-180 s. Titles: 2-6 words +
  emoji, or the full premise.

---

## 3. Topic and script (gate: script + title)

If the person did not name a topic, propose 3 one-line premises tied to the research or the catalogue and let them pick.
Then write the script. The model for structure and density is `examples/EP3_friend_secret/SCRIPT_AND_PLAN.md`
(and EP2's). What makes these work:

- **Length by format and tier (owner 2026-11-18; numbers in `FORMATS.json`):** every In-this-town video is a **Short**
  of 80-120 s (310-450 words, as many a week as possible); Blox City 90-120 s (300-370 words). **Long videos** are ~20-minute
  compilations of videos already on the channel (2 a week, no new animation; YouTube long-form, whose watch hours count
  toward YPP separately from Shorts views). Kit v5.1 delivers ~3.8-4.2 words/s for In-this-town (TEMPO 1.12, 0.24 s meme pauses). Write `story.json` with
  `"format"` (`in_this_town` / `blox_city`), `"tier"` (`short`; `long` = compilation) and `"hook_word"` (the twist word that must land
  by 2.5 s); the kit reads them. Count words with a script, don't guess; if over the tier, cut pauses first, then a line.
- **Hook = the whole promise in one breath:** "I told my best friend one secret. By lunch, the whole school knew. And he
  got paid for it." The viewer decides in two seconds.
- **One line = one beat**, each beat a picture the camera can show. Concrete, visual details (a duck night-light, a shoe
  with a hole a pencil fits through) carry the story and become the props and callbacks.
- **The narrator reads everything**, quoted character lines included. No character voices (owner, re-confirmed 2026-11-18).
- **Meme SFX marks** `[RECORD SCRATCH]`, `[BRUH]`, `[FAHHH]`... sit after a full stop, in a word gap, never on a word.
  Plan 15-20 per episode, but at most 8 get a pause (0.24 s); the others play in word gaps with `"no_pause": true` in
  `meme_cues.json`. They are never spoken.
- **Reversal + callback:** the wronged kid wins by character, not revenge, and the last story line returns to the opening
  object ("The hole still fits a pencil." / "half my class ordered duck night-lights").
- **What to make: `references/VIRAL_PLAYBOOK.md`.** Premises from the 7 families scored 1-5 on mute test, 3x
  escalation, buildable with the kit, reverse-rule climax and shareability; propose only premises at >= 20/25 (show the
  score on the white card), with a personal stake + clock early and a visible counter when the rule has a number. Write
  with its beat template (template B, 80-120 s - owner 2026-11-18; the 45-60 s template A and 35-45 s "lite" format are
  not used for now), its first-sentence formulas and its ending formulas. Check COMPETITORS.md so a
  premise is not a recent hit (copy mechanisms, never premises, titles or characters).
- **First 3 seconds decide "stayed to watch" (check before approval, every format):** frame 0 is motion or the weirdest
  picture of the video (open on the climax image or the rule happening), never a static phone screen, a text wall or a
  character standing; sentence 1 is a world rule or an absurd consequence ("I did X and Y happened"), never backstory -
  the twist word lands by 2.5 s; a sharp SFX inside 0.5 s; voice starts at full energy with no silence; only one thing to
  read (1-2-word captions, no UI paragraph); 2-3 cuts or one big camera move before 3 s; the stakes read on mute.
  Our EP3/EP4 openings failed this (backstory sentence, twist word at ~4 s, static phone UI for 2 s; Gemini comparison
  2026-11-17). Write the 0-3 s plan (frame, words, SFX, cuts) on the white card next to the title.
- **Viral rules (In this world / Big Game):** apply "What the winners do" in section 2: premise in sentence 1 shown in
  frame 1, rule + cost in sentence 2, 3-4 absurd world examples, "And me?", "Until one night", the rule used in reverse,
  an on-screen counter where the premise has a number, deadpan one-line tags after absurd beats. Build the story around
  one visual rule or twist; earnest moral arcs alone read as predictable (Gemini scored our premise 5.5 vs 9.5).
- **Pace and dead air:** measured 2026-11-17: EP3 3.3 and EP4 3.45 words/s overall with 17-18 meme pauses (~8 s of
  silence); dripdyl 3.7-4.2, In-this-world hits 4.1-4.9 with almost no dead air. Keep at most 6-8 meme pauses, cut every
  other silence over 0.15 s except a deliberate 0.25 s beat before a punchline. The owner wants faster takes like the
  viral channels (2026-11-18): kit v5.1 uses TEMPO 1.12 for In-this-town; still play the sample. Measure, never assume.
- **Title (2026-11-17 gap):** 2-6 words, Title Case, at most 1 emoji, no "PART 2", no hashtags in the title (they go in
  the description). Ours ran to 98 characters in caps and got cut off in the feed.
- **Ending depends on the format (owner 2026-11-18, `references/ENDING_RULE.md` v2):**
  - **In this town / In this world: no like/share/follow line and no "Comment X or Y".** End on the last story line - a
    3-8-word callback gag, a truth line, a rule-reversal twist or a cliffhanger (VIRAL_PLAYBOOK ending formulas) - and cut.
    Comments come from the story (mystery, loophole, easter egg). The kit draws no end card without the like line.
  - **Blox City storylines keep it:** "Like, share and follow for more." then a one-word, two-option question: "Would you
    give Max a second chance? Comment TRUST or BLOCK." (one-tap answers get comments; themed phrases got zero).
- **TTS spelling:** the voice model mangles "Blox". Write "Blocks City" / "Blocks Tea" in `tts_script.txt` only; captions and
  the script keep "Blox".

Deliver a script document with: 2-3 punchy title options, cast, word count and runtime estimate, the script, the meme SFX
cue sheet (after which words, which sound, where it comes from), music options, and a beat map (time, beat, shots, kit notes).
Present title, script and music question for approval in a clean white card. **Stop until they approve.**

---

## 4. Music (ask before producing)

Ask: **"Do you have background music for this one?"**
- **Yes:** take their file (or track name). Use it as the bed for the whole video unless they give switch points.
- **No:** use the default bed. The channel's default is "Numbers" by TEMPOREX (the sound of viral "In this town" videos),
  but this repository cannot ship it. If the person has their own licensed copy at `~/RobloxStories/assets/music/default_bed.wav`,
  use it. Otherwise `tools/ep_audio/bed.py` composes an original bed with `tools/score.py` (numpy only, no samples), so
  the video never ships silent.

Make **one** final video with the bed mixed in (`out/final.mp4`). Write `MUSIC_LICENSE.txt` in the episode folder: what
the bed is and who holds the rights. Business accounts can get commercial songs muted; CC BY-NC music is never allowed;
Kevin MacLeod tracks were rejected by the channel owner (not the sound viral creators use).

---

## 5. Voice (gate: voice OK)

Narrator: ElevenLabs voice **Alex** `yl2ZDV1MzN4HbQJbMihG`, model `eleven_v3`, stability 0.0, similarity 0.75, style 0.25,
speaker boost (kit preset `alex_ep1`, `references/VOICE_SPEC.md`). Never change the voice because of measurements; only after
playing a clip to the person and getting a yes. Never clone a voice from someone else's video.

**Delivery direction (dripdyl-style, from the Gemini study; tags for eleven_v3, test at the voice gate):** a sharp friend
telling an unbelievable story - expressive in the setup, flat and matter-of-fact on absurd lines. Lift key nouns and numbers
("FIFTY firefighters"); setups rise, payoffs drop flat; a short breath (comma) before a number or twist; a full stop and a
beat before a deadpan punchline, then move on fast; deadpan = lower and flatter, "like a boring weather report", no
laugh. Rules and stakes slightly slower, action fast. For emotional storylines (butterbloxe), same clarity, ~15% warmer.
Gemini's verdict on our EP3/EP4 (2026-11-17): Alex reads dramatic and calm lines "at the same flat energy", and quoted
lines sound like the narrator. So tag every line with its emotion in `tts_script.txt` (`[excited]`, `[deadpan]`,
`[whispers]`, `[shouting]`, `[sad]`) and make the first line the most energetic of the video. Do not change the voice or
its settings for this; no side-character voices (owner 2026-11-18).
Narration (kit v5, `references/DRIPDYL_STYLE_GUIDE.md` section 8): `tts.py` now sends **one request per line** of
`tts_script.txt` with that line's tags (cached, so re-running only pays for changed lines; `RBX_TTS_MODE=single` = old
way); `post.py` starts the voice on frame 0, shrinks gaps to 0.08 s and makes meme pauses 0.24 s (warns above 8; mark
extra cues `"no_pause": true`). Targets: 3.8-4.2 words/s, first word <= 0.05 s. `TEMPO` is 1.12 for In-this-town (owner
2026-11-18: faster takes keep viewers curious to the end) and 1.08 for Blox City, from `story.json` "format";
`audio/post_cfg.json` {"tempo": x} overrides. The person still hears the sample before production.

```bash
E=~/RobloxStories_tmp/<slug>; mkdir -p $E/audio $E/sfx $E/out $E/frames $E/frames_lo
ln -s $E ~/RobloxStories/videos/<slug>
# script.txt (captions, "Blox") + tts_script.txt ("Blocks") + audio/meme_cues.json ([{"line","after_word","sfx"[,"nth"]}])
cd ~/RobloxStories/tools/ep_audio && export RBX_HOME=~/RobloxStories EP=$E
python3 tts.py && python3 words.py && python3 post.py      # raw.mp3 -> words.json, pauses.json, voice.wav (-14 LUFS)
```
`words.py` must print `mismatch []`. `post.py` prints duration, first word and words/s; the runtime must fit the tier
(`story.json`) or fix the script. Send the voice take
(as mp3) to the person and wait. About 1,800 characters of credits per episode.

---

## 6. Meme SFX and mix

All sounds are **our own**: the kit pack (`kit/sfx`, synthesized/generated), ElevenLabs sound generations and short Alex
takes ("[deadpan] Bruh."). Never use ripped meme clips: they get reels muted or claimed.

1. `audio/sfx_jobs.json`: `{"quack": {"sfx": "One single squeaky rubber duck toy quack", "dur": 0.8},
   "bruh": {"tts": "[deadpan] Bruh."}, "ohhh": {"copy": "<earlier episode>/sfx/ohhh.mp3"}}` then `python3 sfxgen.py`
   (existing files are skipped, so it never double-spends).
2. `audio/mix_cfg.json`: which file(s) play for each cue label, per-label gain, extras, and the bed (`examples/EP3_friend_secret/audio/mix_cfg.json`).
   `python3 bed.py` picks or composes the bed (section 4), then `python3 mix.py` then `python3 qa_audio.py` (must print PASS).
3. Levels by measurement: -14 LUFS, true peak <= -1.5 dB, meme hits inside word gaps, tails over speech <= -10 dB under the
   voice, bed clearly under the voice with an 8 dB dip under each hit. The mixer peak-normalises every sound, so dense sounds
   (a phone buzz) come out louder than sparse ones: lower their gain and fade their tails.
4. You cannot hear. Say which you used: measurements, or a Gemini listening report (the person uploads the mp3 at
   gemini.google.com; ask about voice clarity over the bed and whether any effect is too loud). The person's ear decides.

---

## 7. Animation (shots, low-res QA)

Read `references/CLEAN_ANIMATION.md` (the shot grammar and the EP2 post-mortem) and copy patterns from
`kit/templates/EP2_poor_boy_school_shots.py` and `examples/EP3_friend_secret/shots*.py`. Write `<ep>/shots.py`:

```python
from shotkit import *                     # Video, @S(id, word_a, word_b, desc) keyed to words.json indices
from rbx.shotlib import *                 # frame_on, hold, kneel_down, belly_laugh, crowd_laugh, game_screen, appear, car_door, seat_and_type, ...
from rbx import props3 as P3, cast, motion as mo, acting, qa, look
V = Video(__file__); install_snaps()
```
Helpers go **above** the `@S` decorator line, or the decorator swallows them. `V.shot(i, t0, t1, desc)(fn)` takes a zero-arg fn.

The grammar that makes it look clean (each rule fixed a mistake the channel owner caught in a posted video):
- **Cut each beat into simple shots** like the reference reels: MCU to the lens, OTS/POV, a straight-on readable insert, the
  aftermath. Hide big transitions in the cut (a car exit is three cuts: door opens, feet land, stands - never a float).
- **Frame by measurement:** `frame_on(chars, t0, t1, shot="mcu"|"med"|"cowboy"|"full")` for every character shot. A cut-off
  main character is a failure; a background kid's head at the edge can be fine.
- **Contact by construction:** `hold(ch, prop, ...)` puts the fists on the prop and the prop under the fists every frame;
  `P3` props carry grips (+X is the holder's left). Sit before the shot, never during it. Hands touch sleeves and props they
  interact with (`qa.touch`).
- **Acting:** `belly_laugh`/`crowd_laugh(target=...)` keep heads on the target (laughing kids "dancing" or looking away
  was a real complaint); `kneel_down` instead of a pose snap; heads down means head down, not turned away.
- **Readable props and screens:** phone/app/game screens are real UI images straight-on and big, never a number on a slab.
- **Camera and motion follow `references/DRIPDYL_STYLE_GUIDE.md`** (per-beat camera recipes with real `cams.py`
  calls, framing, focus, blur, motion density, pre-render pass/fail checklist; Gemini-written, checked against the code).
  EP4 root causes: 31 of 34 cameras were `frame_on` straight-on (pitch 4, 35 mm, 6 % push, f/2.8 focused between
  characters), 25 of 69 shots idle-only and 1 `strike()` in 96 s, shutter 0.5 on every shot including frame 0.
  **Kit v5 (2026-11-17) makes the fixes the defaults:** `frame_on` alternates +/-22 deg yaw, pitch -4, 45 mm, 15 % push
  from frame 1, f/2.8 solo / 5.6 two-shot, focus on `chars[0]`'s head; motion blur is off unless a shot calls
  `look.motion_blur(0.35-0.5)` (whips, crash zooms, throws, runs); `mo.strike(ch, t, pose, **mo.SNAP)` for comedy hits.
  You still choose: pass only the active character(s) to `frame_on`; use the beat recipes (crash_zoom, whip_pan, dutch,
  impact_shake, run_follow, hero_low, ots) for at least a third of the shots and always for the hook; key a strike, turn
  or gesture every 0.5-0.7 s; idle-only shots at most 15 % and never two in a row.
- **Smooth like the winners (apply and judge on the contact sheet):** no linear keys - ease in-out for moves, overshoot
  ease-out for pops and reactions, ease-in for falls; 2-3 frames of anticipation before jumps, throws, kneels and pick-ups;
  snap into an impact or shock pose in 3-6 frames and hold 8-12 frames with tiny drift; 5-10 deg torso/shoulder counter-
  rotation and head tilt on every pose (Gemini: our upper bodies stay "squared off"); 3/4 low or high angles for reactions
  instead of flat eye-level mediums; the camera always alive (5-8 % eased push-in on every static shot, whip pans or
  match-cut zooms between places); face swaps stepped, 1-2 frames **before** the sound, shock/anger/laugh mouths 20-30 %
  bigger, each big face swap with a head tilt or shoulder pop; motion blur only on fast flights, projectiles and whips,
  never on holds or frame 0; cuts every 0.5-2.5 s (ours already average ~1.4 s: 69 shots in 96 s). Overlays that carry
  the premise: floating counters, comic starbursts ("STRIKE THREE!"), phone pop-ups, sweat drops, "!" and hearts. Keep
  in-world UI in the top 60 % so captions never collide with it. 60 fps is a test (render cost doubles), not a default.
  Indoor and night scenes: test +10-15 % exposure at look-dev so characters pop on a phone (Gemini); the person decides.
- **Prop contact:** Gemini saw props hovering in front of flat hands (EP4 books, keyboard, paycheck; EP3 handshake, phone,
  money bag). Use `hold()` for every held prop and treat any NOTOUCH/PROPFLOAT flag as a blocker, then check those exact
  beats on the 2 fps contact sheet.
- **SFX on the picture:** a whoosh or pop on every cut and face swap and a hit on every impact, mixed under the voice;
  the bed should rise, drop out or change with the story's turns (Gemini: our bed "stays at one flat energy").
- **Look:** `look.STYLE="clean"`, `cast.CLEAN=True` (crisp, matte, neutral, not blue), night like reference
  `references/REF_IG_Dfe8B5Hs3G6.md`, day like `references/REF_IG_Dfs43n3oWqx.md`. Never judge the look from low-res frames.

**Characters:** the kit's blocky cast lives in `kit/rbx/cast.py`, `chars.py`, `acting.py` and the face atlases in
`kit/assets/faces` (Harry, Tyler, Luna, mom, dad, grandma, grandpa, mayor, kids...). Recolor and restyle per episode (see
`leo()`, `maxx()`, `chase()` in the EP3 shots). `kit/docs/CAST.md` lists them.

**Low-res pass + QA:** `Blender -b --factory-startup -P ~/RobloxStories/tools/ep_lo.py -- <slug> all` (detached), then read
`render_lo.log`. Flags: FLOAT, CLIP, HALF, CUTOFF, TINY, NOTOUCH, PROPFLOAT, EYELINE, AWAY, BLOCKED. Fix every one or write
down why it is acceptable (e.g. AWAY on a POV phone shot where the holder's head is hidden on purpose). Then make a 2 fps
contact sheet and **look at it** - flags cannot see "uncanny". EP3 went from 280 flags to 31 accepted ones.
Then run the viral gate: `python3 ~/RobloxStories/tools/ep_viral_check.py <ep>` (static, no render: idle-only shots,
actions per second, recipe cameras, hook move, frame-0 blur, first word, words/s, silences, meme pauses, hook word time from
`story.json` "hook_word", tagged TTS lines, outro). 0 FAIL before look-dev; EP4 fails 8 of its checks.

**Going faster with a team (optional):** for 60+ shots, split the work: a Manager/QA agent owns `shots.py` (shared helpers)
and the kit, Blender A owns `shots_a.py`, Blender B owns `shots_b.py` (`shots.py` execs both). They coordinate through an
append-only `BOARD.md` and inbox files. Copy the protocol from `examples/EP3_friend_secret/BRIEF.md`, `BOARD.md` and
`references/TEAM_AGENTS.md`. Give every agent the brief, the ownership rules and the "no final render" limit.

---

## 8. Look-dev (gate: look OK)

Render 6 full-quality 1080x1920 stills of the key looks (night interior, crowd, a readable prop close-up, a dark scene, the
emotional beat, a day exterior), put them side by side (`examples/EP3_friend_secret/lookdev/lookdev_strip.jpg`), compare with
the reference notes, and send them. Say what you measured (brightness, blue cast) and what only their eye can judge. Stop.

---

## 9. Final render and finish

```bash
cd ~/RobloxStories && zsh tools/ep_final.sh <slug> 32          # one Blender run per shot, lock + disk guard, ~1.4 min per second of video
python3 tools/ep_eta.py videos/<slug>                          # ETA from screen time
zsh tools/ep_finish.sh ~/RobloxStories_tmp/<slug>              # captions + end card + audio -> out/final.mp4
```
Test the overlay before the full finish: `tools/ep_captions.py <ep> test t:0 t:30 t:<Like time>`. The end card (Blox City only) is automatic when the script has the like ... follow line; In-this-town videos have none:
heart on "Like", share on "share", a cursor clicks + FOLLOW on "follow", a comment bubble on "Comment" and the two answer
buttons, all centred, with captions moved down to y 0.68.

Before delivering, make a 1 fps contact sheet of the final and look at every tile: readable screens, nobody floating or cut
off, captions not covering important text. Report anything you saw. Give progress updates with ticks and an honest ETA
while rendering (people ask "is it stuck?": answer with frame counts and the last frame time).

---

## 10. Delivery and wrap-up

- Package it (`references/VIRAL_PLAYBOOK.md` section 5): YouTube title 2-6 words, Title Case, <= 1 emoji, no "PART 2",
  no hashtags; description = one teaser line + #roblox #robloxstory #shorts; Instagram caption = a hook line + 4-5
  hashtags; cover = the brightest frame with a clear face or giant prop; made-for-kids answered truthfully.
- Deliver `out/final.mp4` (and the voice/mix files if asked). **Never post** to Instagram or YouTube without an explicit yes
  for that exact file. Record what was posted in `<ep>/POSTED.md` when they say they posted.
- Cloud backup: before saying a file is in Google Drive, check the Drive app is running and the file is **in the cloud**
  (search it with a Drive connector); a copy in the local Drive folder is not a backup until it uploads.
- Free disk space only after the backup is confirmed and with the person's OK: `frames/` and `frames_lo/` are ~7 GB per
  episode. Never delete their files without asking; deletes are permanent.
- After every fix, append a dated lesson to `~/RobloxStories/docs/LESSONS.md`
  (`date | problem | root cause | rule | check`). Every agent reads LESSONS first. This is how the kit keeps getting better.

---

## 11. Growth loop: measure -> find what wins -> learn -> update this skill -> ship

Run it when the person asks how the channel is doing, to check reach, what others do better, to grow or monetize, "run the
growth loop", every Monday, and 48 h after each post. Full instructions: `references/GROWTH_LOOP.md` (Project instructions).
The goal is a monetized channel, so every step ends in a decision that moves a monetization number.

1. **Measure our reach (never invent a number).** Windsor.ai connector (`get_connectors` -> Instagram `17841479901972435`,
   YouTube `91882`; `get_fields` before `get_data`), YouTube Studio / Instagram Insights screenshots the person gives, and
   `yt-dlp -J` on our own Shorts. Per video: views 48 h and 7 d, reach, average watch time and % watched, 3-s skip or
   swiped-away, likes, comments, shares/sends, saves, follows. Append to `CHANNEL_LOG.md`. Re-verify the YPP and Instagram
   thresholds on the official help pages each cycle and report "X / target (%)" and the 90-day pace.
   **"Stayed to watch"** (Shorts feed: viewed vs swiped away) is the number that gets a Short recommended; Shorts have no
   thumbnail click-through in the feed. Windsor does not expose it: ask for the YouTube Studio Shorts screenshot, and use
   `engaged_views / views` as a proxy (2026-11-17: 54-72 %) plus Instagram `media_reel_skip_rate` (18-39 %).
2. **Is it good?** Compare each funnel stage with our median and the peers. Baseline 2026-11-17: IG skip 18-39 %, 33-42 %
   watched, ~0 shares and 0-1 comments per video, IG reach 1.1-1.4k, YT 28-1,426 views; peers in this niche reach 2-25M with
   tens of thousands of likes. Name the **one weakest stage** (stop, hold, share, talk, convert, volume). If any stage is
   below the peer level, go to steps 3-4 aimed at that stage (weak stop -> study first 3 s; weak hold -> beat maps and pace;
   no shares -> endings and emotional payoffs).
3. **Compare ourselves with the benchmark, side by side.** In the same Gemini task chat, give our two latest public
   Shorts and two benchmark Shorts as `/watch?v=` links and ask for: score /10 for each on first 3 s, premise, voice,
   pace/dead air, animation smoothness, faces, camera, overlays/captions, music/SFX, ending, title, look; the biggest gap
   with a timestamp from OUR video; the exact fix; the top 5 gaps ranked by views lost; and why viewers swipe in our
   first 3 s. If the answer is only a summary, ask it to "write the full result here in the chat". Check every claim you
   can by measurement (words/s and silences from `words.json`, cuts with ffmpeg scene detection, outro length, a 0-3 s
   frame strip you look at) and mark the rest "Gemini". 2026-11-17 result: `RESEARCH_2026-11-17_gap_vs_dripdyl.md`.
   To let Gemini judge our production code, give it the public raw GitHub URLs of the repo files
   (`https://raw.githubusercontent.com/Harishisonline/rblx-animates-skill/main/...`). Its Connected Folders did not reach
   the web chat, github.com pages made it ask for a sign-in, and on a later turn raw URLs were blocked too: then paste the
   key code excerpts into the chat.
   To let Gemini judge our production code, give it the public raw GitHub URLs of the repo files
   (`https://raw.githubusercontent.com/Harishisonline/rblx-animates-skill/main/...`); its Connected Folders did not reach
   the web chat, and github.com pages made it ask for a sign-in.
4. **Find and learn from videos that already win it:** section 2 (outliers, yt-dlp numbers, Gemini Task chat). Write each
   finding as `rule | evidence (IDs + numbers) | level | test | decision rule`. Levels: proven (our own test won) > observed
   (3+ independent channels) > hypothesis. Only proven and observed rules become skill defaults; hypotheses become
   one-variable experiments in `EXPERIMENTS.md` (3 posts per arm, judged at 7 days, ~20 %+ gain on the primary metric with
   no loss on the guardrail; one viral post is noise).
5. **Update this skill with change control.** Show a white card per change: what changes | why (evidence + level) | how we
   test it | how we roll back. The person's decisions (runtime, ending, Alex voice, music, gates) never change on data alone.
   After a yes: edit the single source of truth (numbers in `FORMATS.json`, endings in `ENDING_RULE.md`, formats in their
   files, research in a dated file), propose the `SKILL.md` edit with the skill-update card, append to `LESSONS.md`, bump
   the kit version and `HANDOFF.md`.
6. **Ship** (`references/VIRAL_PLAYBOOK.md` sections 5-6; cadence decided 2026-11-18: as many 80-120 s Shorts as possible
   plus 2 compilations of ~20 minutes a week, built from finished `out/final.mp4` files only).
   Weekly batch of 5-7 premises scored on premise family, stake + clock in sentence 1, visual hook in frame 1,
   difference from our last 10 videos, cost; at least one follow-up to our best performer and one live experiment. Each goes
   through the normal gates. Package: 3 titles, a first frame that stops a scroll on mute, the same file to Shorts and Reels,
   the audience question answered truthfully. Log posts and schedule the 48 h check.

**Never:** invent or round up numbers; buy views or engagement; copy another creator's video, script, character or title;
use ripped music; mislabel made-for-kids; post without an explicit yes for that exact file; promise virality or a date.
Uniqueness matters for monetization: YouTube does not monetize near-identical template videos, so every video needs its
own story, visual hook, sets and cast.

---

## Reference map

| File | Read when |
|---|---|
| `references/BLOX_CITY.md`, `EPISODE_CATALOGUE.md` | Blox City topic/script |
| `references/INTOWN_FORMAT.md`, `FORMATS.json`, `STORY.md` | In-this-town scripts |
| `references/ENDING_RULE.md` | every script and finish |
| `references/MUSIC_PLAYBOOK.md`, `MUSIC_RESEARCH.md` | music question, research |
| `references/VOICE_SPEC.md`, `AUDIO.md`, `GEMINI_AUDIO_NOTES.md` | voice, mix, listening checks |
| `references/CLEAN_ANIMATION.md`, `ACTING.md`, `LOOK.md`, `REF_IG_*.md` | shots, acting, look |
| `references/DAILY_PIPELINE.md`, `TEAM_AGENTS.md` | the day plan, parallel agents |
| `references/LESSONS.md` | before any work: every mistake already paid for |
| `references/GROWTH_LOOP.md`, `CHANNEL_LOG.md`, `COMPETITORS.md`, `EXPERIMENTS.md` | growth loop, "check my reach", monetization |
| `RESEARCH_2026-11-17_dripdyl_gemini.md`, `RESEARCH_2026-11-17_gap_vs_dripdyl.md`, `RESEARCH_2026-11-17_viral_roblox_shorts.md` | viral research, gaps, Big Game format |
| `references/VIRAL_PLAYBOOK.md` | premises, scoring, script templates, endings, packaging, posting plan |
| `references/DRIPDYL_STYLE_GUIDE.md` | every shots.py, tts_script.txt and audio config (camera, motion, narration) |
| `examples/EP2_*`, `examples/EP3_*` | scripts, cue files, shots, QA report of finished episodes |
| `kit/SKILL.md` (installed as `~/RobloxStories/SKILL.md`) | the kit's API in depth |