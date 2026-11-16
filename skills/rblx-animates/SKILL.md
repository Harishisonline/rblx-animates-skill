---
name: rblx-animates
description: Make original Roblox-style 3D story reels (9:16, 90-120 s) exactly the RBLX ANIMATES way, end to end - trend research, Blox City or "In this town / In this world" scripts, Alex narration, meme sound effects, music, Blender animation with the kit's characters, captions, the like/share/follow end card and the final render. Use this whenever someone wants a Roblox story video, a Blox City episode, an "In this town" reel, a Roblox animation for Instagram, TikTok or Shorts, or wants to research, script, voice, animate, render, check or fix one with the RobloxStories kit - even if they never name the skill.
---

# RBLX ANIMATES: Roblox story video studio

This skill reproduces the production line behind the Instagram channel @rblxanimates: original, blocky Roblox-style 3D story
reels, 9:16, 90-120 seconds, narrated by one upbeat voice, with meme sound effects, burned-in captions and an end card that
asks viewers to like, share, follow and comment. The quality bar is the two finished episodes in `examples/`:
EP2 "The Poor Boy Who Bought the School" and EP3 "I Told ONE Secret. By Lunch, Everyone Knew."

The work is long (about 5 hours, 2.5 of them unattended rendering) and the person cares about each stage, so the line has
**approval gates**. Treat them as part of the craft, not bureaucracy: every gate exists because skipping it once cost hours.

| # | Stage | Gate (stop and wait for the person) |
|---|---|---|
| 0 | Setup check | - |
| 1 | Research (when asked, or when topics run dry) | - |
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

## 1. The two formats - never mix them

Read the reference for the format you are making before writing a single line.

**Blox City** (`references/BLOX_CITY.md`): storyline episodes, each one custom. A first-person kid narrator, a clear wrong
(bullying, betrayal, a secret sold), an escalation, a reversal and a warm callback ending. Blox City branding is allowed
("Blox City High", "Blox Tea"). Ideas: `references/EPISODE_CATALOGUE.md` (Day 01-30 with punchy titles; 01 and 02 are made).

**In this town / In this world** (`references/INTOWN_FORMAT.md`, `FORMATS.json`): premise in the first sentence
("In this town, every lie shows on your wrist"), short dense sentences, time-marked escalation, twist ending. Its own bed and
rules. Never put Blox City names or branding into it.

Both formats share the narrator, the ending rule (`references/ENDING_RULE.md`), the look and the kit.

---

## 2. Research (when asked "what's trending", or before a new batch of topics)

Goal: rules you can apply, not a mood board. For each reference reel or Short record hook (first 3 s), structure with
timings, narration style, music, camera, look, facial acting and runtime. Method that works (details and past findings in
`references/MUSIC_PLAYBOOK.md`, `references/REF_IG_*.md`, `references/GEMINI_AUDIO_NOTES.md`):

- YouTube search sorted by views + the Shorts shelf for the niche ("roblox story", "poor boy roblox", "in this town").
- The music track comes from YouTube's own **Content-ID music card** in the page data, an on-screen credit, or the person's
  Shazam - nothing else. Gemini returned "unknown" on two control tracks, so it cannot identify music.
- Gemini in the browser can watch YouTube links and describe pacing, voice and mix. It cannot open Instagram links, and
  local file upload is blocked for automation, so the person uploads files or clicks consent dialogs for you.
- Never invent a view count, track name or BPM. Mark anything unverified as unverified. Append findings to the reference
  files with video ID, views, date and evidence, so the next session builds on them.

---

## 3. Topic and script (gate: script + title)

If the person did not name a topic, propose 3 one-line premises tied to the research or the catalogue and let them pick.
Then write the script. The model for structure and density is `examples/EP3_friend_secret/SCRIPT_AND_PLAN.md`
(and EP2's). What makes these work:

- **Length:** 300-370 spoken words. Alex runs about 197 words per minute, plus about 0.45 s per meme pause, which lands at
  90-120 s. Count words with a script, don't guess; if over 120 s, shorten pauses first, then cut a line.
- **Hook = the whole promise in one breath:** "I told my best friend one secret. By lunch, the whole school knew. And he
  got paid for it." The viewer decides in two seconds.
- **One line = one beat**, each beat a picture the camera can show. Concrete, visual details (a duck night-light, a shoe
  with a hole a pencil fits through) carry the story and become the props and callbacks.
- **The narrator reads everything**, quoted character lines included. No character voices.
- **Meme SFX marks** `[RECORD SCRATCH]`, `[BRUH]`, `[FAHHH]`... sit after a full stop, in a word gap, never on a word.
  Plan 15-20 per episode. They are never spoken.
- **Reversal + callback:** the wronged kid wins by character, not revenge, and the last story line returns to the opening
  object ("The hole still fits a pencil." / "half my class ordered duck night-lights").
- **Ending (every video, both formats):** "Like, share and follow for more." then a one-word, two-option comment question:
  "Would you give Max a second chance? Comment TRUST or BLOCK." One-tap answers get comments; themed phrases got zero.
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

```bash
E=~/RobloxStories_tmp/<slug>; mkdir -p $E/audio $E/sfx $E/out $E/frames $E/frames_lo
ln -s $E ~/RobloxStories/videos/<slug>
# script.txt (captions, "Blox") + tts_script.txt ("Blocks") + audio/meme_cues.json ([{"line","after_word","sfx"[,"nth"]}])
cd ~/RobloxStories/tools/ep_audio && export RBX_HOME=~/RobloxStories EP=$E
python3 tts.py && python3 words.py && python3 post.py      # raw.mp3 -> words.json, pauses.json, voice.wav (-14 LUFS)
```
`words.py` must print `mismatch []`. `post.py` prints duration and wpm; 90-120 s or fix the script. Send the voice take
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
- **Look:** `look.STYLE="clean"`, `cast.CLEAN=True` (crisp, matte, neutral, not blue), night like reference
  `references/REF_IG_Dfe8B5Hs3G6.md`, day like `references/REF_IG_Dfs43n3oWqx.md`. Never judge the look from low-res frames.

**Characters:** the kit's blocky cast lives in `kit/rbx/cast.py`, `chars.py`, `acting.py` and the face atlases in
`kit/assets/faces` (Harry, Tyler, Luna, mom, dad, grandma, grandpa, mayor, kids...). Recolor and restyle per episode (see
`leo()`, `maxx()`, `chase()` in the EP3 shots). `kit/docs/CAST.md` lists them.

**Low-res pass + QA:** `Blender -b --factory-startup -P ~/RobloxStories/tools/ep_lo.py -- <slug> all` (detached), then read
`render_lo.log`. Flags: FLOAT, CLIP, HALF, CUTOFF, TINY, NOTOUCH, PROPFLOAT, EYELINE, AWAY, BLOCKED. Fix every one or write
down why it is acceptable (e.g. AWAY on a POV phone shot where the holder's head is hidden on purpose). Then make a 2 fps
contact sheet and **look at it** - flags cannot see "uncanny". EP3 went from 280 flags to 31 accepted ones.

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
Test the overlay before the full finish: `tools/ep_captions.py <ep> test t:0 t:30 t:<Like time>`. The end card is automatic:
heart on "Like", share on "share", a cursor clicks + FOLLOW on "follow", a comment bubble on "Comment" and the two answer
buttons, all centred, with captions moved down to y 0.68.

Before delivering, make a 1 fps contact sheet of the final and look at every tile: readable screens, nobody floating or cut
off, captions not covering important text. Report anything you saw. Give progress updates with ticks and an honest ETA
while rendering (people ask "is it stuck?": answer with frame counts and the last frame time).

---

## 10. Delivery and wrap-up

- Deliver `out/final.mp4` (and the voice/mix files if asked). **Never post** to Instagram or YouTube without an explicit yes
  for that exact file. Record what was posted in `<ep>/POSTED.md` when they say they posted.
- Cloud backup: before saying a file is in Google Drive, check the Drive app is running and the file is **in the cloud**
  (search it with a Drive connector); a copy in the local Drive folder is not a backup until it uploads.
- Free disk space only after the backup is confirmed and with the person's OK: `frames/` and `frames_lo/` are ~7 GB per
  episode. Never delete their files without asking; deletes are permanent.
- After every fix, append a dated lesson to `~/RobloxStories/docs/LESSONS.md`
  (`date | problem | root cause | rule | check`). Every agent reads LESSONS first. This is how the kit keeps getting better.

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
| `examples/EP2_*`, `examples/EP3_*` | scripts, cue files, shots, QA report of finished episodes |
| `kit/SKILL.md` (installed as `~/RobloxStories/SKILL.md`) | the kit's API in depth |
