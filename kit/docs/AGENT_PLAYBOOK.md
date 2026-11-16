# AGENT PLAYBOOK (v3.2): mandatory rules for every agent that makes a video

Written from the 5-round test_seq quality loop (2026-11-14). The target is REFERENCE 1 (`REF1_CINEMATIC.md`). Every rule
below came from a defect a reviewer actually saw. Do not skip any rule unless the user says "autopilot" for that gate.

## 0. Pick the FORMAT first (v3.7)
`python tools/format_preset.py <format>` (in_this_world / in_this_town, horror, comedy, emotional_twist, chase_action) prints
the look, bed, wpm band, duck, SFX density, captions and expression set from `docs/FORMATS.json`. Put `"format": "<name>"` in
`videos/<slug>/story.json`; hype_lint.py, pacing.py, grade_check.py (--format) and qa_gate.py then use that format's bands.
Checklist: [ ] hype_lint no FAIL before TTS [ ] pacing wpm in band after TTS (255-290 for hype formats) [ ] V.look = format
look (never cine_* as master) [ ] grade_check --format all PASS [ ] faces: ladder on surprises, dart on fear holds, no
narrator lip-sync [ ] sleeve/hand contact < 0.05 at the START frame [ ] mix: voice-clarity only if the user approved D.

## 1. Approval gates (never skip)
1. **Voice comes from the user.** Gate A in SKILL.md: send voice samples, wait for a pick. A macOS `say` placeholder is for
   timing tests only and must never ship. Do not spend ElevenLabs credits on test or integration runs.
2. **Cast v3 is approved and permanent**: Harry, Tyler, Luna, Mayor Bigsby, Mom Rosa, Dad Rick, Grandpa Otto, Grandma Pearl.
   Names, roles and designs never change. You may change rigs, poses, lighting, finish and bugs (`CAST.md`).
3. **Script passes `tools/story.py check`** and the user sees it (Gate C) before any voice is generated.
4. **Look-dev pack** (Gate B) for any new location or prop family.

## 2. Shot script (REF1 numbers, `REF1_CINEMATIC.md` sec. 3)
- Shot length mean 48 f (1.6 s), sd 15, clamp 19-99 f; hook shot 60-78 f. `tools/pacing.py` must show no FAIL rows.
- Per 10 shots: 3 inserts, 3 faces, 1-2 aerial/wide, 1-2 low MS, 0-1 top-down. Never the same type back-to-back > 15 %.
- Cut on VO phrase boundaries; every concrete noun gets its own picture; cuts by word index (`V.w(i)`), never by seconds.
- MCUs: faces 35-55 % of frame height, framed on the rule of thirds (never dead centre), crop at mid-chest, 40-50 mm,
  slow push 6-10 %/s, shallow DoF (f/1.8-2.8). Nothing big in the bottom 20 % near-lens zone (that is the caption zone).
- Inserts: 70-100 mm, rack 12-18 f, the object fills the frame; the insert must show the action the description names.

## 3. Acting (`ACTING.md`)
- Shoulder abduction <= 10 deg in rest/talk poses (no "wing arms"); elbows tucked; gestures asymmetric.
- Hands never in the near-lens zone (bottom 20 % of an MCU) and never as a floating block; one hand in a pocket is fine.
- Every MCU has contrapposto: hip offset, head tilt 5-10 deg, a slow sway layer. No square, frontal, symmetric stance.
- Key a brow change (raise/knit) and a mouth shape on every stressed word; blinks 3-4 f, never on a stressed word.
- Eyes open on every key beat (closed eyes read as asleep); soft brow for care beats; at most one blink in the beat.
- Contact actions (button a cuff, hand over an object) need real contact: IK the fingertips onto the target (< town.CUFF_TOL = 0.05 studs since 2026-11-14; guard with `town.hand_on_prop(hand, prop, t0, t1)`
  and LOOK at the START-frame still of every 'keeps sleeve down / tugs sleeve / holds X' beat),
  present the target to camera, no stand-in stick/rod props. If the action cannot be read in the still, reframe.
- Pose presets need joint limits and a self-collision check (crossed forearms through each other read as a broken rig).

## 4. Lighting (`WORLD.md`, `CAMERA_AND_FX.md`, `research/REF_IG_Dfe8B5Hs3G6.md`)
- **Default look = `look.ref_matte`** (shotkit default since 2026-11-14); nights `ref_night`, lamp/doorway-lit rooms
  `ref_practical`, exteriors by day `ref_day`; tune with `look.ref(warmth=, desat=, lift=, roll=, exposure=)`.
  Old presets (cine_*, day, night, story_warm...) stay selectable but their sky-blue fill/rim + blue-lifted shadows made
  EP1 'blueish': do not use them for In-this-world episodes without the user asking. ref_* are UNRENDERED until a
  test render is approved: the first render with them MUST be a 4-still look-dev pack checked with grade_check.
- **MANDATORY before any delivery: `python3 tools/grade_check.py <mp4 or stills dir>`** -> every row PASS
  (no cool-cast day frame B-R > +15, sat 0.30 +- 0.06, p2 17 +- 5, median 49 +- 12, p98 124 +- 40). Paste the output in the report.
- `look.rig` in every shot; key + fill + rim on every face; luma per grade_check (median ~49, p2 ~17, p98 ~124; the old YAVG ~91 target is retired), no clipped whites except flash.
- Night interiors: a warm motivated key on the cast (lamp/practical), verify with a stress tile, no blue crush.
- Skin uses `town.skin_mat` (SSS + falloff + AO), never flat plastic; inserts get their own exposure and rim.

## 5. Transitions (frame budgets, measured by `qa_gate.py`)
- 95 % hard cuts.
- White flash: hard cut into 1-3 full-white frames, full contrast again within 8 frames total (`fx.flash_cut`).
- Whip: 2-20 blurred frames, shutter 0.5-1.0; the whip must LAND on a recognisable object (fridge, art wall, a face),
  never a bare wall. The landing frame must be sharp.
- Push-through / wipe: the occluder is a readable object (locker edge with vents/handle), 3-6 frames, not a colour smear.

## 6. Audio (`AUDIO.md`)
- Master -14 LUFS (-15..-13), true peak <= -1 dBTP, digital silence <= 2 %, voice clearly on top.
- Every transition cut has its own SFX peak within 2 frames of the cut and >= +10 dB over the bed (not the voice onset).
- Mood timbres: mystery/horror = pads, drones, low strings; no lo-fi beat, chat pops or celesta. Escalation +3..+9 LU.
- Run `tools/audio_qa.py <slug>` (full, with earshot) once per delivery; say you cannot hear the mix.

## 7. Captions (`captions2.py`)
- Defaults = REF_IG spec: 1-3 words, heavy sans ALL CAPS, size 64 @1080 w (~2.4 % cap height), centre y 0.65, thin dark
  outline, hard cut between groups (pop off), ONE key word in #FFD21E (red #E0141E only for danger words, by hand).
- 2-3 words, white, key word #FFD21E, snapped to the voice onset (<= 1 frame off), not in a white flash frame.
- On an INSERT that shows text or digits, do not caption the same word/number (blank that group): no doubles like "001".
- Caption at 62-72 % height (or `top` per shot in `captions.json` when the subject sits low).

## 8. Blender lock and renders
- Only ONE Blender run at a time across all agents:
  `until mkdir ~/RobloxStories_tmp/blender.lock 2>/dev/null; do sleep 5; done` before, `rmdir ~/RobloxStories_tmp/blender.lock`
  right after the command exits, even on failure. A lock older than 90 min with no blender process may be removed.
- Never leave Blender/ffmpeg running. Never delete another video's frames. Keep frames with `.keep_frames` while iterating.

## 9. Preview-and-LOOK loop (the only way to claim a fix)
1. Low-res previews (540x960, 8-16 samples) of the changed shots only.
2. Read EVERY image you render. Describe what you see before saying it is fixed.
3. Never claim a fix you did not see in a render or measure with a tool.
4. Before delivery: full render, `finish.py`, then **`tools/grade_check.py videos/<slug>/out/<final>.mp4` all PASS** and
   **`tools/qa_gate.py <slug>` must print `QA GATE PASS`** (exit 0). `tools/pacing.py` row 'cuts/min vs REF_IG' ok (26-40/min).
   Run `--stress` after any change to `rbx/` rig, pose, cast, world or lighting code, and LOOK at the stress sheet.
5. Log each change in `CHANGELOG.md`; edit only files you own in multi-agent runs, report the rest.

## 10. What to do for each failure class
| Failure | Fix |
|---|---|
| Contact action unreadable (D2) | IK fingertips to the target, present it to camera, remove stand-in props, reframe on the hands |
| Wing arms / block hands (D3, R4-2) | clamp abduction <= 10 deg, hands at the waist midline or a pocket, out of the near-lens zone |
| Frontal MCU (R2-2, R2-5) | hip offset + head tilt + sway; thirds framing; mid-chest crop; push + shallow DoF |
| Flat face (R2-1b), closed eyes (R5-1) | brow + mouth keys per stressed word; eyes open on key beats; short blinks off-stress |
| Caption doubles an insert (R2-1) | blank that caption group on the insert |
| Plastic hand / prop (D4) | skin_mat, separate fingers, bevelled watch with specular bezel, rim light |
| Floating accessory (R2-3) | conform to the hair cap (shrinkwrap / snap to surface) |
| Flash too long (R5-2) | flash_cut, decay <= 6 f |
| Whip on a bare wall (R5-1) | aim the end angle at a dressed object; check the landing frame is sharp |
| Smear wipe (R5-3, R4-1) | occluder with an edge and texture; add contrast to the next insert |
| Weak transition SFX (R3-2, R5-1) | whoosh/hit peak on the cut, >= +10 dB over bed |
| Night crush (R3-2 world) | warm motivated key; stress tile |
| Unverified regressions (R1-3) | `qa_gate.py <slug> --stress` (fails on missing cells / errors) |

## 11. Known weak spots still open (end of loop 2026-11-14; fix before claiming REF1 quality)
- D2 s04: Mom buttoning Harry's cuff does not read (stick prop, no contact, Harry eyes shut, near arm off-frame).
- D3/R4-2: wing arms and block hands in s02, s05, s07; Tyler's s07 talk pose knots the forearms.
- R2-2/R2-5: s05/s07 MCUs frontal, centred, weak DoF, arm blocks fill the lower frame.
- R2-1b: Tyler's face does not change on stressed words.
- R2-1: s08 caption '001' doubles the watch readout (qa_gate fails it).
- D4: insert hand still reads as a slab in places; watch face a flat disc, cuff ring reads broken.
- R2-3: Mom's headband floats above the hair (in `rbx/cast.py`).
- R5-1/R5-3/R4-1: whip lands on a bare wall; locker wipe is a blue smear (qa_gate: push span 1 f).
- R3-2 audio: bed reads lo-fi; transition SFX peaks only +5..+10 dB over the bed (qa_gate fails all three).
- R1-3: no full stress-suite run since round 4.
