---
name: roblox-story-kit
description: Make an original Roblox-style 3D animated story video (9:16 short, 60-120s, "In this world, X makes you Y" format, first-person narrator) end to end on this computer in Blender, with ElevenLabs voice, polished lighting/camera/props, sound effects, captions and music. v2 adds approval gates (voice sample, look-dev pack, script), natural-pace narration, camera recipes, a lighting/grade system and a pacing checker. Use when the user says "roblox story", "roblox animation video", "make a story video about X", "make a roblox short about X", asks for story ideas for this format, or sends popular Roblox animation videos to learn from. Also for first-time setup or updating of the kit ("set up the roblox kit", "update the roblox kit").
---

# Roblox story kit v4.1

A studio for high-retention Roblox-style story shorts: procedural blocky characters with expressive faces, sets, camera
recipes, lighting + grade, captions, sound and music, all built and rendered locally in Blender from Python.
One video = one folder `videos/<slug>/`. The original v1 skill is backed up at
`~/RobloxStories/_backups/roblox-story-kit-v1-original/`. What changed and why: `docs/REFERENCES.md`, `CHANGELOG.md`.

## 0. Find the workspace (every time)

The kit's code lives next to this file; videos are made in a separate **workspace** (default `~/RobloxStories`).
`~/.roblox-story-kit.json` holds `{"workspace": ..., "python": ...}`.

- Missing pointer, or user asks to set up: run `python3.13 -I "<this skill's folder>/setup.py"` (Python 3.10-3.13; **not 3.14**).
  It copies the engine, makes `.venv`, installs numpy, Pillow, faster-whisper, yt-dlp, finds Blender and ffmpeg,
  downloads music, renders a test frame, prints `READY` or what is missing. `--update` refreshes engine code after the
  kit changed (never touches videos). Re-running is safe.
- Missing ffmpeg/Blender: tell the user the fix line setup printed and ask before installing (brew on Mac). Blender 5.x.
- Run every command **from the workspace** with the kit's python (`PY` = the `python` in the pointer file).
- Optional assets: `$PY tools/assets.py starter` (CC0 HDRIs + OFL fonts). Captions v2 uses Poppins from there.

**v3.2: read `docs/AGENT_PLAYBOOK.md` FIRST** (mandatory rules from the REF1 quality loop: gates, shot/acting/lighting/
transition/audio/caption rules, blender lock, preview-and-LOOK loop, failure-class fixes, open weak spots). Delivery requires
`$PY tools/qa_gate.py <slug>` to print `QA GATE PASS`, and `python3 tools/grade_check.py <final.mp4>` all PASS
(2026-11-14: default look = look.ref_matte, neutral matte grade from docs/research/REF_IG_Dfe8B5Hs3G6.md; NOT blue; UNRENDERED until a look-dev pack passes).

## Clean LOOK v4.0 (2026-11-15) - the user's look = crisp, NOT matte (docs/CLEAN_ANIMATION.md sections 8-9)
- Defaults now: `look.STYLE = "clean"` (no lift, haze or desat; AgX Medium High Contrast; light vignette) and `cast.CLEAN = True`
  (no grain or weave bumps on characters). References: IG Dfe8B5Hs3G6 (night), Dfs43n3oWqx (day: blue sky, sunlit, green).
  This SUPERSEDES the ref_matte "milky/desaturated" targets and the grade_check matte profile below for this channel.
- Look-dev = 5-6 full-quality stills (`tools/render.py <slug> still:T <shot> 24`) next to the reference. render_lo
  (34 %, 6 samples) is ONLY for motion and contact checks, never for the look.
- Finals: 1080x1920, `final <ids> 32` samples, full-res raytracing.
- Contact by construction: IK the fists first, measure, then build the prop under them (`fit_desk_to_hands`). Sit before
  the shot starts. Vehicles: characters start outside next to an open door (`car_door`, `appear`).

## v4.1 (2026-11-15, after the user reviewed the POSTED EP2) - NON-NEGOTIABLE for every shot (CLEAN_ANIMATION.md 10-14)
- **Framing:** every character shot uses `frame_on(chars, t0, t1, "mcu|med|cowboy|full")`. QA CUTOFF/HALF/TINY must be clean for the
  speaking or acting character. Guessed still_cam positions cut Harry, Ryan and his dad in half in EP2.
- **Objects:** use `rbx/props3` props only (pizza_box, book_stack, keyboard, laptop, tray: readable details + GRIPS). Hold with
  `hold(ch, prop, t0, t1)`, type with `seat_and_type` + a visible keyboard, drop with `drop()`. QA NOTOUCH/CLIP/PROPFLOAT clean.
  Every interaction beat gets an INSERT of hands on the object; screens show a picture (`game_screen`), not just numbers.
- **Body:** reactions use presets: `belly_laugh` / `crowd_laugh` (eyes on the target, no dancing), `kneel_down` / `KNEEL_POSE`,
  `mo.sit`, `mo.turn`. Otherwise start the shot already in the pose (hide transitions in the cut).
- **Vehicles:** a 3-cut exit: car arrives with no character -> shoe-steps-down insert -> hero beside the open door. Never `appear()` in
  the same continuous shot as the arrival.
- After any kit change run `~/RobloxStories_tmp/shotlib_test` (6 shots) and LOOK at out/test_strip.jpg.

## Daily pipeline v4.0 (2026-11-15) - READ docs/DAILY_PIPELINE.md: EP2 is the approved quality bar, reproduce it daily
- New videos: `from rbx.shotlib import *` + `install_snaps()` (every EP2 helper: cameras, contact, physics, car door, desk).
  Worked example: `templates/EP2_poor_boy_school_shots.py`.
- Run order: `tools/ep_audio/` (EP=<dir>: tts, words, post, sfxgen, mix) -> `Blender ... -P tools/ep_lo.py -- <slug> all` (fix all QA flags,
  look at sheets) -> look-dev strip -> `tools/ep_final.sh <slug> 32` (detached on the Mac) -> `tools/ep_finish.sh <ep dir>` -> final sheet.
- ETA = `tools/ep_eta.py <ep dir>`: about 1.4 min of render per second of video. Never estimate from shot count.

## Clean animation v3.9 (2026-11-15) - READ docs/CLEAN_ANIMATION.md BEFORE WRITING ANY SHOT
Learned from the user's frame QA of EP2 and craftee_films reels studied frame by frame. Summary:
- **Design the beat as a cut sequence of simple shots** (craftee method): establishing wide, single MCU reactions facing the
  lens, OTS/dirty singles, prop inserts (ECU, shallow DOF), aftermath instead of complex physics. One idea per shot,
  1-2.5 s each. Never stage a multi-character physical action (slap, bump, poke) in one wide.
- **Contact**: feet on the ground; seated = `mo.sit(seat_h=1.5)` on a real chair, desk top 2.6-2.9, hands on the keyboard via
  `mo.reach` + `mo.contact(wobble)`; props gripped and aimed (`aim_prop`/`attach`), never through a body; falling objects use
  `drop()` (gravity 32, tumble, land flat, bounce, slide).
- **Eyelines**: everyone looks at what they react to (`mo.look_at`/`eyeline`/`stage`). For "laugh at Harry", film from Harry's
  POV/OTS so the bullies point and laugh toward the lens.
- **Cameras** aim from the face direction (`face_yaw`), need clearance (`safe_pos` + `_clear`), stay inside rooms.
- **Text** fits its board (`signs.fit_text`) and gets a straight-on insert.
- **QA gate**: `rbx/qa.py` (declare `qa.sit/air/prop/touch/look` in the shot); `render_lo.py` logs FLOAT, CLIP, NOTOUCH,
  EYELINE, BLOCKED and AWAY. Clean log + a LOOKED-at 2 fps contact sheet before the user sees anything.

## Music v3.8 (2026-11-15) - READ docs/MUSIC_PLAYBOOK.md BEFORE PICKING ANY MUSIC
- Pick music from what VIRAL ROBLOX STORIES actually use (MUSIC_PLAYBOOK.md, evidence-backed), never "a free library track that fits".
  In this town / In this world bed = "Numbers" by TEMPOREX (YouTube Content-ID card + on-screen credit, Gneef 4.9M / GreenBroRants 9.1M);
  scene-break cue = "Relaxed Scene" (James Clarke); sad storylines = pop/emotional songs (e.g. Tom Odell "Another Love" on Bloopo 6.2M).
- Never spend ElevenLabs credits on music (user rule). Never invent a track name: names only from a platform music card, an on-screen credit or the user's Shazam.
- Commercial song as the bed: finish TWO files: out/final_nomusic.mp4 (posted; the user adds the song in Instagram's music picker)
  and out/final_preview.mp4 (song mixed in, review only, never posted). Baked-in music must be commercial-OK (CC BY + credit, CC0, owned, licensed); write MUSIC_LICENSE.txt.
- Every video ends with "Like, share and follow for more." + the comment question, icons popping on the words (docs/ENDING_RULE.md).

## Format playbooks (v3.7, 2026-11-14) - decide this BEFORE writing a word
One data file holds every per-format default: `docs/FORMATS.json`. Print it: `$PY tools/format_preset.py <format>` (`--json`).
Put `"format": "<name>"` in `videos/<slug>/story.json`; `hype_lint.py`, `pacing.py`, `grade_check.py --format` and `qa_gate.py`
read their bands from it. Evidence tags: **[M]** measured on reference videos, **[I]** inferred/convention, **[U]** UNVERIFIED.

| | In this world / In this town (default) | Horror | Comedy | Emotional twist | Chase / action |
|---|---|---|---|---|---|
| Look (`V.look`) | `ref_matte`; day ext `ref_day`, night `ref_night`, lamp rooms `ref_practical` [U unrendered] | `ref_night` + `ref_practical` [U] | `ref_day` [U] | `ref_day`, ONE night beat for the sad turn [U] | `ref_day` / `ref_night` [U] |
| Grade gate | `grade_check --profile matte` (B-R -15..+8, S 0.30, p2 17, p50 49, p98 124) [M Dfe8B5] | matte [M] | `--profile day` (p50 ~100, p2 ~38, p98 ~202) [M Dfs43] | day [M] | day [M] |
| Music | `assets/music/inthisworld_bed.wav` at **1.0x** (user rule) [track BPM/licence U] | drone / music box / sub booms, near-silence before scares [I] | pizzicato/ukulele/chiptune 100-125 BPM, stops dead on the punchline [I] | piano + strings 60-80 BPM [I] | phonk/hybrid 130-160 BPM [I] |
| Delivered pace | **255-290 wpm** [M refs 262-293] | 255-290 [M] | 255-290 [M] | 245-290 [I] | 260-295 [I] |
| Spoken SFX | quiet, clipped, on cuts ("click.") >= 0.6/10 s | QUIET only ("creak...") [refs used 0; user wants some] | SHOUTED running gag ~1/10 s, triplet at the peak [M] | few, soft | shouted impact words |
| Mix | bed 6-8 LU under voice, duck 3-5 dB [M research]; voice-clarity = option | bed 8-10 LU, duck 4-6 | bed ~8 LU, duck 3 | bed 8-10, duck 2-3 | bed ~6, duck 5-6 |
| SFX density | medium: whoosh on cuts, 1 hit per reveal | low, loud hits | high | low | high |
| Faces | worried, worried_dart, pop_shock, sad_tear, smug_up, blank, content | + terror, scream | content, smug_up, grin, blank | sad_tear, content, relief | pop_shock, furious, determined |

Rules for EVERY format (sources: `docs/research/NARRATION_HYPE.md`, `MUSIC_RESEARCH.md`, `REF_IG_Dfe8B5Hs3G6.md`,
`REF_IG_Dfs43n3oWqx.md`, `GEMINI_AUDIO_NOTES.md`):
- **Length up to 120 s** (60-120 for story formats, 45-90 for comedy/chase). The old "80-90 s" and "215-245 wpm" are SUPERSEDED
  (215-245 lives on only as format `natural`, a calm read on request). EP1 at ~185 wpm read as "just delivering a story".
- **Hook**: the rule is spoken in sentence 1, inside 3 s [M 9/9 refs]. **Spark rule**: a spark ("!", "?", spoken SFX, CAPS word,
  "Wait...") at least every 6 s, never a flat stretch > 10 s; >= 1 "!" per 10 s; one whisper beat only [I].
- **CTA** = the last 2 sentences end on a ONE-WORD, TWO-OPTION question ("EXPOSE or PROTECT?"); horror may use a threat-CTA [M].
- **Voice**: In this town/world = voice_preset `intown_v1` (DEFAULT): Alex on eleven_multilingual_v2, stability 0.55, style 0.0,
  speed 1.15, no tags, plain punctuation, paragraph takes; post = gap cap 0.30 s, atempo to 257 wpm, gentle 1.5:1 comp, loudnorm -14,
  no presence boost (`docs/VOICE_SPEC.md` INTOWN recipe). Calm deadpan storyteller, NO hype: the hook/spark/CTA/'!' bullets above
  do NOT apply to this format (`tools/intown_lint.py`). `hype_v3` (Alex v3, per-beat tags) stays selectable for other formats.
- **Cutting**: ~30 cuts/min, average shot ~2 s [M both IG refs]; holds 4-6 s only on dread beats.
- **Captions**: 1-3 words, white heavy ALL CAPS, y 0.65, ONE key word #FFD21E (threat #E0141E); spoken-SFX words get their own pop.
- **Grade**: neutral, never blue: no `cine_*` preset as the master look (EP1 B-R +35, S 0.60). `grade_check` all PASS before delivery.
- **Hands**: any "keeps sleeve down / tugs / holds X" beat = fingertips ON the object at the START frame, gap < 0.05 studs
  (`town.CUFF_TOL`, `town.hand_on_prop`, `town.insert_sleeve_pull`). Or don't mention the hand.
- **Faces** (UNRENDERED): hard decal swaps on beats, `ch.ladder()` on surprises (6-8 f/step), `ch.dart()` in fear holds, blinks every
  2.5-4 s, `sad_tear` 1.5-2 s on a push-in; NEVER lip-sync the narrator-POV character during VO (`docs/ACTING.md` v3.7).
- **Mix**: `mix.py/finish.py --voice-clarity` (mix D: voice HPF 80 + 3 kHz +2.5 dB, bed bass shelf -6 dB, bed ~6.6 dB under,
  3.7 dB duck) is an OPTION, **not the default**, until the user approves the A/B (`A_base_m` vs `D_fix_m`). Master -14 LUFS, TP <= -1.5.
- **Status (be honest in reports)**: measured = ref pace/cut rate/grade stats, EP1 band loudness; inferred = per-genre BPM, beds,
  energy curve, spark density; UNVERIFIED = every music track/BPM/licence of the refs, Gemini's audio numbers (low confidence,
  templated), the ref_* look presets and the new face cells (nothing rendered), mix D by ear.

**Read first, in the workspace, before writing anything:** `PLAYBOOK.md` (beats/numbers), `docs/REFERENCES.md` (what the
references actually do, measured), `docs/VOICE.md`, `docs/CAMERA.md`, `docs/LOOK.md`, `docs/PROPS_AND_SCALE.md`,
`docs/STORY.md`. Worked examples: `videos/laugh_float/shots.py`, `videos/sneeze_teleport/shots.py` (v1 style) and
`videos/ai_lookdev/shots.py` (v2 look: lighting, cams, props2, survivor/robot/drone).

Stories must be original: own characters, sets, sounds; no real Roblox UI/logos/avatars/game audio; no copied plots; every
video gets its own script and cast (platforms demonetise templated mass production).


**In-this-town narration (measured 2026-11-14, supersedes 'hype'):** read engine/docs/research/INTOWN_FORMAT.md before scripting.
Calm first-person AI storyteller, 225-290 wpm, gaps 0.1-0.4 s, 0 spoken SFX, 0 '!', no question CTA, ends on twist/callback.
In-this-town videos must NOT use 'Blox Town'/'Blox City' branding; 'Blox City' is reserved for later storyline videos.

## Quality bar (user-approved baseline)
The user rated `videos/ai_world` (Option B) as good and expects **that level or better** in every video. Before building, open
`videos/ai_world/shots.py`, `rbx/aiworld.py` and `videos/ai_world/REPORT.md`: lit multi-location sets with 6-10 props each, wet/reflective
ground, rim + fill light on faces, varied camera recipes, animated props (drones, pulsing core), per-shot exposure, coloured key-word
captions, natural-pace voice, -14 LUFS. Do not regress below it; fix its known weak shots in new work: dark door slab, busy top-down shot,
hero too small next to big props, helmet-like hair, a billboard repeated in many shots, no squash/stretch or walk polish yet.
Every new video needs its own sets and cast (not a re-skin), but may reuse the engine.

## Storage (Google Drive)
The user is short on disk. Long-lived data lives on **Google Drive** (`~/Library/CloudStorage/GoogleDrive-*/My Drive/RobloxStories/`):
`videos/ sfxlib/ research/ assets/ music/ _backups/` are symlinks from the workspace into Drive (`tools/storage.py status|to-drive`).
Local on purpose: code (`rbx/ tools/ docs/ sfx/`), `.venv`, `config.json`, `.env` (API key: never uploaded), earshot (`~/earshot`).
Render scratch (`frames/ blend/ caps/`) is symlinked into the LOCAL `tmp_dir` (`~/RobloxStories_tmp`) so thousands of PNGs never sync
to Drive, and `finish.py` deletes them afterwards (`auto_clean_frames`). Consequences: a fix to one shot after finishing means a full
re-render; for A/B/C variants from the same frames run every `finish.py` with `KEEP_FRAMES=1` and then `tools/clean.py <slug>`.
Keep >= 8 GB free on the Mac while rendering (a 75 s video writes ~4.5 GB of frames).

**Storage reality check (2026-11-14, mandatory before saying "it is on Drive"):** the `videos/` symlink points at `~/Library/CloudStorage/GoogleDrive-*/My Drive/...`.
If the Google Drive app is NOT running (`pgrep -fl "Google Drive"` empty, no Drive mount in `mount`), that path is just a plain LOCAL folder and nothing syncs: EP1 sat there for a day and was not in Drive.
Before claiming a file is stored, run `pgrep -fl "Google Drive"` and verify via the Drive connector search (title contains the slug, check modifiedTime).
The Drive connector's create_file refuses uploads over 10 MB, so finished videos (25-105 MB) need the Drive app (open Google Drive.app, then check sync) or a manual upload by the user.
Never delete a local copy as "freed space" until the Drive copy is verified.

## The pipeline (v2) with approval gates

Gates cost the user a minute and save credits and an hour of render. Do not skip them unless the user said autopilot.

1. **Premise + script** (`videos/<slug>/script.txt`, `#` lines are notes). Follow `docs/STORY.md`: rule in the first
   sentence (7-12 words), 3-5 concrete examples (each a shot), underdog narrator with a planted flaw, escalation, twist,
   punchline callback. Words = length x format pace (~270 wpm: 90 s ~ 400 words, 120 s ~ 540). Run
   `$PY tools/hype_lint.py <slug>` (no FAIL; for in_this_world it delegates to `tools/intown_lint.py`) and `$PY tools/story.py check <slug>`. Optional `emphasis.txt` (one key word per line) for caption colours.
2. **GATE A: voice sample.** `$PY tools/eleven.py voices`, then
   `$PY tools/eleven.py sample "<first 30 words>" Voice1,Voice2,...` with the current recipe in `docs/VOICE_SPEC.md` (In this town: intown_v1 = Alex, eleven_multilingual_v2 --stability .55 --style 0 --speed 1.15).
   Send the clips with SendUserFile; wait for approval; put the chosen id in `config.json` (`voice_id`).
3. **GATE B: look-dev pack** (graphics + characters). Build `videos/<slug>_lookdev/shots.py` like `videos/ai_lookdev`
   (hero, villain/robot, key prop, wide set, insert, hideout/interior, crowd, face-off), render stills
   (`$PY tools/blend.py <slug>_lookdev still:<t> <shot>`), tile them into one contact sheet and show the user. Wait.
4. **GATE C: script** shown to the user (unless autopilot).
5. **Voice** (costs ~1 credit/char; turbo/flash models cost half). `$PY tools/eleven.py tts <slug>` (reads script.txt, uses
   `tts_speed` natural speed) **or** the ElevenLabs connector (`creative_generate_speech`, same voice/model) then save to
   `videos/<slug>/audio/raw.mp3`. Never paste keys in chat; the key lives in `.env`.
6. **Voice processing** (v2: no stacked stretching):
   ```
   $PY tools/voice_run.py --video <slug> --voice videos/<slug>/audio/raw.mp3     # speed 1.0, cuts silences, timestamps
   $PY tools/tighten.py <slug> --max-gap 0.45
   $PY tools/pacing.py <slug> [--format NAME]                                    # wpm 255-290 (format band), words/15s 62-75
   ```
   If wpm is low: tighten the script / regenerate flat takes; post atempo 1.08-1.15 per VOICE_SPEC. `retempo.py` refuses > 1.12.
7. **Sound effects**: pack in `sfx/` (aww boing bonk boom buzz buzzer cashier chat cheer click clink coin confetti crickets
   crowd ding door footsteps gasp glitch hammer jet kids_laugh meow paper pigeon place poof pop rimshot rise rocket rope
   sparkle splat stomp teleport thud whoosh wind window zombie alarm). New sounds: connector `creative_generate_in_flow`
   (node_type `sfx`) or `$PY tools/eleven.py sfx <name> "<prompt>"` then `tools/sfxprep.py`, add `lead`/`gain` to
   `sfx/pack.json`; or synthesise with numpy (the `buzz` is synthesised).
8. **Shots** (`videos/<slug>/shots.py`):
   ```python
   from shotkit import *
   from rbx import story
   from rbx.story import *
   V = Video(__file__); story.bind(V); V.look = "ref_matte"  # format look (FORMATS.json); never a cine_* master
   @S(1, 0, 8, "HOOK: ...")                                # shot = script word indices 0..8; last shot uses None
   def s01(t0, t1):
       P.ai_city(); look.rig("neon", focus=(0, -28, 4))
       h = P.survivor(t0, t1); h.pose(t0, loc=(0, -28, 0))
       cams.hero_low(t0, t1, (0, -28, 4.2))                # one recipe per shot, never the same twice in a row
   ```
   Timing is by script word index, so regenerating the voice never breaks the edit. Rules: average shot 1.4-2.2 s (hold
   key beats 2.5-3.5 s); every noun on screen; reaction close-up after every surprise; alternate wide/medium/close/insert
   (`cams.pick(prev, beat)`); SFX on every hit/whoosh/poof/reveal; camera moves small and eased (see `docs/CAMERA.md`);
   props obey the scale policy (`docs/PROPS_AND_SCALE.md`); each location gets its own set and 6-10 props; lighting via
   `look.rig` in every shot; captions zone (bottom 20%) kept clear.
9. **Preview + fix**: `$PY tools/pacing.py <slug>` then
   ```
   $PY tools/blend.py <slug> preview all
   $PY tools/contact.py <slug> all 12 full        # -> videos/<slug>/full.jpg, LOOK at every tile
   $PY tools/blend.py <slug> still:12.3 14        # one frame of shot 14 at t=12.3 s (half res)
   ```
   Fix until every frame passes the checklists in `docs/LOOK.md` (faces visible, not black, no green skin, nothing inside
   the lens) and `docs/CAMERA.md`. Re-preview only changed shots (`preview 3,7,12`).
10. **Render**: `$PY tools/blend.py <slug> cues`, then `final` in the background (~0.5 frame/s on an Apple-silicon Mac;
    ~1 h for 70 s). Never two finals at once. Disk: ~5 GB of frames.
10b. **Sound design (docs/AUDIO.md recipe, mandatory)**: In this world/town = the AI-world bed at 1.0x (format rule above), no
    generated score. Other formats: NO house/viral track; Mark beats + holds + locations in
    `audio/cues.json` (`{"t":18.2,"beat":"dread"}`, `{"t":41.0,"beat":"hold","dur":0.6}`, `{"t":0,"amb":"room"}`), set
    `"mood"` in story.json (horror mystery comedy emotional adventure). finish.py then writes a NEW original score
    (`tools/score.py`, new key/motif per run) + a CC0 room-tone bed (`tools/ambience.py`), ducks the score under the voice.
11. **Finish**: `$PY tools/finish.py <slug> [--mood horror]` mixes voice + room tone + SFX + original score and burns captions v2 (grouped words, key word coloured,
    Pillow overlay: works without libass). `--audio-only` stops after the mastered mix (no frames needed). `--captions ass` = old one-word style (needs libass). Outputs `out/final.mp4`,
    `final_nocaptions.mp4`, `final_phone.mp4` (720p ~25 MB).
11b. **Audio QA with earshot (mandatory, `docs/AUDIO.md`)**: `$PY tools/audio_qa.py <slug>` (loudness, true peak, sync of SFX to cues/cuts,
    scorecard). Fix level/sync problems before reporting. If a real SFX library is configured for `real-sfx`, let it place real recorded
    sounds instead of the synthesized pack (see docs/AUDIO.md). Skills installed: `earshot`, `real-sfx` in ~/.claude/skills.
11c. **QA GATE (mandatory, blocks delivery)**: `$PY tools/qa_gate.py <slug>` runs pacing, audio_qa --quick (LUFS/peak/
    silence), transition SFX peaks (>= +10 dB on each cut), flash/whip/push frame lengths measured from the frames, caption
    timing + caption-vs-insert doubles, frame count vs audio length; add `--stress` after any rig/pose/cast/world/lighting
    change (fails on missing stress cells). Exit 0 = PASS. Fix every FAIL (see `docs/AGENT_PLAYBOOK.md` sec. 10) and re-run;
    never deliver on FAIL. Writes `out/qa_gate.json`. It does not judge acting/finish: LOOK at the contact sheet too.
12. **QA the real encode**: `ffmpeg -i videos/<slug>/out/final.mp4 -vf "fps=1/1.8,scale=216:384,tile=10x4" -frames:v 1 videos/<slug>/qa.jpg`,
    fix bad shots (`final <ids>`, re-run finish).
13. **Report**: file locations, credits spent, what was not checked. You cannot hear the mix: say so, ask the user to listen.
    Offer `$PY tools/clean.py <slug>` to free the frames.

## Toolkit map
- `rbx/core.py` primitives, materials, `Cam` (push, orbit, crash, whip, track, handheld, key), `sfx`, render setup.
- `rbx/look.py` **v3.6**: `rig(preset)`, `fog`, `hdri`, `grade` (auto); default `ref_matte`, plus `ref_day ref_night ref_practical`,
  `look.ref(warmth=, desat=, lift=, roll=, exposure=)` tuner (UNRENDERED); legacy day dusk night interior neon horror story_warm.
- `rbx/cams.py` **v2**: eye_med, close_up, hero_low, ots, two_shot, establish, pull_reveal, orbit_slow, top_down, track_side,
  pov, insert, dutch_push, crash_zoom, dolly_zoom, whip, `pick`.
- **v3 cinematic (REF1) - read `engine/docs/CAMERA_AND_FX.md` first.** `cams.py`: mcu, push_in, ground_low (18mm up-tilt),
  aerial_glide, aerial_dive, fly_in_window, truck (past FG), rack, run_follow, dutch, ecu, prop_macro, whip_pan, overhead,
  micro/shake (36mm-sensor lenses, every shot moves). `look.py`: `cinematic(preset)` with cine_day / cine_room / cine_night /
  night_dread / sepia (AgX, AO, haze, vignette), `motion_blur(shutter)`. `fx.py`: flash, ghost, whip_out/whip_in,
  push_through, match_save/match_frame, dust, siren, practical, sign. `tools/pacing.py` v3 (REF1 cutting, exit 1 on FAIL),
  `tools/captions2.py` v3 (2-3 words, yellow key word, timers.json countdown).
- `rbx/props2.py` **v2**: mosquito (+macro), swarm_cloud, pigeon, helmet, steel_locker, wood_crate, robot, drone,
  server_rack, terminal, neon_sign, lit_building_mat, ai_city, survivor, wrist_band, floating_number, searchlight, world_pos.
- **WORLD v3 (read `docs/WORLD.md` first; reuse, don't reinvent)**: `rbx/town.py` Blox Town v3 locations (main_street, pharmacy_corner,
  night_street, school_exterior, school_hallway, classroom, kitchen, bedroom, front_hall, insert_table wrist/phone/map) + modular
  pieces (facade, street, lamps, benches, bikes, cars, police_car, lockers, desks, counters...); `rbx/pbr.py` CC0 PBR material library
  (`pbr.get('brick', tint=...)`); `rbx/signs.py` readable text props (sign, closed_sign, poster, note, chalk, screen, street_screen,
  phone UI, laptop feed, wrist_counter, typed, brand_sign); `rbx/crowd.py` instanced extras (1-2k cheap, police/students, number
  badges); `rbx/townmap.py` flat map + animated route. Validate with `tools/world_stills.py`; textures via `tools/fetch_pbr.py`.
- `rbx/robloxworld.py` **v2.4** Blox Town world for @rblxanimates (`RW.blox_town()`, `RW.kitchen()`, `RW.living_room()`,
  place constants PLAZA/HALL/SKATE/BAKERY/HOUSE/GRILL/PARK/HILL). `tools/eleven_lines.py` = line-level voice fixes.
- `rbx/cast.py` **v2.2** PERMANENT @rblxanimates cast (host Harry, mayor, bestie Tyler, crush Luna, mom, dad, grandpa, grandma) + hop/walk2/react
  squash-stretch helpers; bible in `docs/CAST.md`. Reuse these in every channel video; never redesign without the user's OK.
- `rbx/chars.py` R6 characters (`Char`, `kid(i)`...), hair buzz/bun/tophat/pilot/bald/messy, extras glasses/beard/collar/backpack.
- `rbx/acting.py` faces (`face(t,"shock")`, eyes=/mouth=), blink, talk, `act(t, gesture)`, look, nod, jump, run, panic, breathe;
  v3.7 `ladder(t, "surprise_laugh")`, `dart(t0, t1)`, `blink_schedule`, new cells/EXPRs (blank pop_shock sad_tear worried_dart
  smug_up content) with 4x4 fallback (UNRENDERED; `tools/face_dryrun.py`).
- `rbx/motion.py` **v3 acting library** (also via `acting.*`): `strike` (anticipation→hit→overshoot→settle, head leads 2 f), `idle`, `walk`/`run` (12 f cycle)/`skid_stop`/`run_away`, `turn`/`dread_turn`/`look_at`, `shock`/`recoil`/`gasp`/`point`/`grab`/`read`/`laugh`/`cry`/`stomp`/`shrug`/`nod`/`shake`/`sit`/`stand`/`stumble`/`fall`/`embrace`, `talk_cadence`, `emote`, `blocking`/`eyeline`. Read `docs/ACTING.md` before animating.
  Gestures: idle shock hands_head hands_face cheer point point_l shrug recoil lean slump think cross phone reach push hold
  wave fists facepalm brace.
- `rbx/story.py` cast + helpers (`laugh, drift, fly, look_at, facing, crowd_src/crowd, confetti, town_scene, class_scene`...).
- `rbx/world.py`, `world2.py`, `sets.py`, `locs.py` v1 sets (town, classroom, cockpit, club, bedroom...).
- Audio **v3** (recipe: `docs/AUDIO.md`, why: `docs/REF4_HORROR_STORY_AUDIO.md`): `tools/score.py` (generative original score
  from the beat map: drone, sub, pad, cluster, bowed metal, air, pulse, motif, riser, hit, holds; seeded, stems + score.json),
  `tools/ambience.py` (room / street / school_hallway / wind / night_crickets / kitchen_hum: CC0 Openverse recordings in
  sfxlib/openverse/amb_*, procedural fallback), `tools/mix.py` (side-chain duck, holds cut music+sfx, `through` cues,
  per-beat gain for plain music files), `tools/holds.py` (tighten.py/retempo.py keep protected pauses),
  `tools/audio_qa.py` (earshot + music share, escalation slope, digital silence, holds). Skills `earshot` + `real-sfx`.
- **v3.2 QA**: `docs/AGENT_PLAYBOOK.md` (mandatory agent rules + open weak spots), `tools/qa_gate.py <slug> [--stress]
  [--no-audio]` (single PASS/FAIL delivery gate, exit code), `tools/stress_suite.py` (cast x pose x location regression sheet,
  takes the blender lock), `docs/LESSONS.md` (lesson log).
- v3.7: `tools/format_preset.py` (per-format defaults from `docs/FORMATS.json`), `tools/hype_lint.py` (script hype gate),
  `tools/grade_check.py` (colour gate, `--profile matte|day`), `tools/face_dryrun.py` (face system test, no Blender).
- Tools: `blend.py, contact.py, finish.py, captions2.py, pacing.py, eleven.py (voices/sample/tts/sfx), voice_run.py,
  tighten.py, retempo.py, assets.py, clean.py, analyze_inspo.py (reference analysis)`.

## Trigger notes
- "is it ready / deliver / finish the video" -> run `qa_gate.py <slug>` first; report its verdict verbatim.
- "fix the quality / match reference 1 / run the quality loop" -> `docs/AGENT_PLAYBOOK.md` + `REF1_CINEMATIC.md`, test on
  `videos/test_seq` (placeholder voice, no ElevenLabs credits), LOOK at every render.
- MUSIC for the "In this world / In this town" format (user rule 2026-11-14): the bed is `assets/music/inthisworld_bed.wav`
  (the approved AI-world track) at 1.0x speed, never finish.py --music (1.5x) and no generated score unless the user asks.
  Episode audio scripts take `--bed FILE` (default = that file). EP1 sat the bed ~3.4 LU under the voice and the user heard the
  voice as dulled; research target is 6-8 LU (mix D, `--voice-clarity`, pending the user's A/B verdict). See docs/AUDIO.md.
- Sync after editing the master: `python3.13 -I setup.py ~/RobloxStories --update --no-pip --no-music --no-test`
  (pass the workspace path explicitly; `.` run from the kit folder turns the kit folder into the workspace and rewrites the pointer).

## Traps already hit
- Python 3.14 is outside the supported range: run setup with 3.13.
- Homebrew ffmpeg may lack libass: use captions v2 (default).
- Sky/solid-colour worlds look flat: always `look.rig` + `V.look`.
- Windows from a noise texture grain: use `P.lit_building_mat`.
- Camera inside props / under the floor / blank tiles: check the contact sheet; `cams.insert` clamps z>=0.6.
- Visibility keys less than one frame apart collapse (use `W2.vanish`). No custom attributes on bpy objects.
- Prop scale: mosquitoes <= hand size in wide shots (v1 had them 3x a head).
- Never stack time-stretch on the voice (see `docs/VOICE.md`).
- Roblox head is ~1.24 wide; two characters 3 units apart need ~5.5 units of frame width (width = distance*13.5/lens).
- Long Python in a shell heredoc can fail on Windows: write patch scripts to a file.

## Learning rule (mandatory, added 2026-11-14)
Before starting ANY job read engine/docs/LESSONS.md. After EVERY fix, failed attempt, or user correction, append one lesson
(problem | root cause | preventing rule | proving check) to LESSONS.md, and if it is a repeatable check, add it to engine/tools/qa_gate.py.
A fix without a lesson entry is not finished. Sync master -> ~/RobloxStories after editing.

## Narrator voice (user decision 2026-11-14)
Use Alex (yl2ZDV1MzN4HbQJbMihG) now; Adrian (BT6eaRWNcJkXzGwuFtu0) as backup. Full recipe: engine/docs/VOICE_SPEC.md.
In this town / In this world: follow the reference reels' narration EXACTLY (calm deadpan first-person AI storyteller, no hype;
user decision 2026-11-14) -> voice_preset intown_v1. Open item: Alex measures ~157 Hz vs the reels' 181-203 Hz.


## Posting and analytics (Windsor.ai connector, checked 2026-11-14)
- Instagram @rblxanimates (account 17841479901972435): the connector CAN publish (create_video_post = Reel, create_image_post, create_carousel_post, create_story) and comment (create_comment, reply_to_comment, hide/delete). It needs a PUBLIC video URL (MP4/MOV, 9:16, <= 15 min); local files cannot be sent. Never post without the user's explicit yes on the exact video version, caption and cover.
- YouTube (channel 91882, "Roblox animated"): read-only analytics. No upload action. The user uploads by hand.
- Windsor trial = last 30 days only; asking for older data errors. YouTube per-video/daily rows came back empty while the channel was tiny.
- ALWAYS ask/record which version was posted. EP1: the user posted v1 (c854f388..., before the cuff-sleeve fix and the AI-world music). v2 is NOT posted. Do not offer a re-post of a version that is already live unless asked.
- Baseline (13 Nov): IG 4 followers; number-world reel 2,187 views / 1,402 reach / 37 likes / 3 saves / 0 comments / avg watch 41.8 s / 23.5 % skip at 3 s; Blox Town intro 121 views, 38.9 % skip. Lesson: hook holds, comment CTA did not work; end every episode on a one-word, one-tap question.
