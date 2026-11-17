# Changelog

## 2026-11-18 v5.1 - owner decisions: no CTA in In-this-town, faster takes, long/short tiers
- `tools/ep_endcard.ending()` returns None when the script has no "like ... follow" line -> no end card;
  `ep_captions.py` handles it (captions stay at y 0.65). Blox City scripts keep the end card (ENDING_RULE.md v2).
- `tools/ep_audio/post.py`: TEMPO default 1.12 when story.json "format" is in_this_town/in_this_world (Blox City 1.08).
  Tested on EP4's raw voice as in_this_town: 88.9 s, 3.70 words/s, first word 0.02 s (before per-line tags).
- `tools/ep_viral_check.py`: In-this-town FAILS on any like/share/follow outro; runtime check by story.json "tier"
  (long 80-120 s, short 35-60 s).
- `docs/FORMATS.json` in_this_world: length 80-120 s, tiers long/short, cadence 2 long + many short, cta none, tts/tempo/
  tone updated (old 2026-11-14 calm/no-tag reading superseded). `docs/ENDING_RULE.md` v2.
Backups: *.bak_v51.

## 2026-11-17 v5.0 - DRIPDYL guide defaults (camera, blur, voice edit, per-line TTS, viral gate)
Source: docs/DRIPDYL_STYLE_GUIDE.md (Gemini read the repo; Claude checked every claim against this code).
**Tested without rendering:** frame_on built in headless Blender (lens 45, f/2.8 solo / 5.6 two-shot, side alternates,
camera moves from frame 1); post.py v5 run on EP4's raw voice (92.2 s vs 95.6 s, first word 0.02 s); ep_viral_check on
EP4 reproduces its measured flaws (8 FAIL). tts.py v5 not yet called (costs credits; runs at the next voice gate).
- `rbx/shotlib.frame_on`: yaw default +/-22 (alternates each call; was 0 straight-on), pitch -4 (was 4), lens 45 (was 35),
  push 0.15 starting on frame 1 (CUBIC ease-out; was 0.06 ease-in-out), fstop None -> 2.8 solo / 5.6 two-shot, focus on
  chars[0]'s head (was the bounding-box centre), camera never below floor+0.8. Module constants FRAME_YAW/PITCH/LENS/PUSH.
- `tools/shotkit.build`: setup_render(blur=False). Motion blur only where a recipe or shot calls look.motion_blur(>0)
  (whip_pan, run_follow, aerials already do).
- `rbx/motion`: NORMAL and SNAP timing presets for strike(ch, t, pose, **mo.SNAP).
- `tools/ep_audio/tts.py`: one eleven_v3 request per tts_script.txt line with its own tags (cached per line; untagged
  lines get RBX_TTS_DEFAULT_TAG=[excited]); tags stripped from the alignment; writes raw.wav + raw.mp3. RBX_TTS_MODE=single
  = old behaviour. Voice/settings unchanged.
- `tools/ep_audio/words.py`: works without the global tag prefix.
- `tools/ep_audio/post.py`: pause 0.24 (was 0.45), gap 0.08 (was 0.14), detect 0.16 (was 0.22), lead 0 (was 0.10 s),
  leading silence trimmed, warns above 8 meme pauses ("no_pause": true in meme_cues.json), TEMPO unchanged (1.08, voice
  gate). audio/post_cfg.json or RBX_* env override; {"pause":0.45,"gap":0.14,"detect":0.22,"lead":0.10} = v4.
- NEW `tools/ep_viral_check.py <ep>`: static pre-render gate (idle-only shots, actions/s, recipe cameras, hook move,
  frame-0 blur, first word, wps, silences, meme pauses, hook word time from story.json "hook_word", tagged TTS lines, outro).
Backups: *.bak_v5.

## 2026-11-14 v3.7 - integration: format playbooks, hype pace 255-290 wpm, natural faces (data), voice-clarity option
**Nothing in this release was rendered or listened to.** Faces, ref_* looks and mix D are data/code only (UNRENDERED / not heard).
- NEW `docs/FORMATS.json` (single source of per-format defaults: look, grade profile, bed, wpm bands, words in first 15 s,
  spark/SFX/exclamation density, CTA, cut rate, mix/duck, SFX density, captions, expression set) for in_this_world (alias
  in_this_town, default), horror, comedy, emotional_twist, chase_action, natural (legacy 215-245 calm read). Tagged
  measured / inferred / UNVERIFIED.
- NEW `tools/format_preset.py <format> [--json] [--video]` prints it; shared loader for the tools below.
- `tools/pacing.py --format NAME` (else story.json "format", else default): wpm band 255-290 for the hype formats (was
  215-245), words in first 15 s 62-75, length up to 120 s (was 80-90 / 40-55 shots), cut-rate band per format. FIX/FAIL
  semantics unchanged (wpm/length/15 s = FIX; shot count far outside the cut-rate band = FAIL).
- `tools/hype_lint.py --format`: wpm-estimate / flat / SFX / "!" bands from FORMATS.json (text band 235-290 shares pacing's 290
  ceiling; pacing is the delivered check). `tools/story.py` budget now 255-290 wpm, 60-120 s (was 215-245, 80-90 s).
- `tools/grade_check.py --profile matte|day / --format`: targets from FORMATS.json grade_profiles (day = REF_IG_Dfs43n3oWqx
  exteriors). `tools/qa_gate.py --format` passes through to pacing.
- `rbx/acting.py`: eye cells half_up closed_happy dots ring worried_l worried_r tear1, mouth cells dash o_small cat_w wavy_side
  frown_wobble grin_top grin_full scream_tongue (5x5 atlas via assets/faces/<style>_<layer>.json {"grid":5}; 4x4 atlases
  FALL BACK to the nearest old cell, so existing renders cannot go blank); EXPR blank pop_shock sad_tear worried_dart smug_up
  content laugh_smug toothy angry_shout; `ladder()`, `dart()`, pure `ladder_plan/dart_plan/blink_schedule`; `blink()` default
  2.5-4.0 s (was 1.8-3.6) and skips ladder/dart windows. `rbx/cast.py`: aliases tear/erased/dart, `cast.ladder/dart`,
  `cast.FACE_SET`. Atlas PNGs NOT regenerated (would be a render-like step): new cells show their fallbacks until then.
- NEW `tools/face_dryrun.py` (stubbed bpy; 20 checks). Cheat sheet: docs/ACTING.md "v3.7".
- `tools/mix.py --voice-clarity [--clarity-scoop]` / `finish.py --voice-clarity` / config.json "voice_clarity": MUSIC_RESEARCH
  mix D as an OPTION (default OFF until the user approves the A/B A_base_m vs D_fix_m). docs/AUDIO.md section added.
- Docs de-conflicted: SKILL.md "Format playbooks" + evidence status; STORY_ENGINE.md, VOICE_SPEC.md (current-rules banner),
  VOICE.md, PLAYBOOK.md, REFERENCES.md, LOOK.md, AGENT_PLAYBOOK.md sec. 0 checklist.

## 2026-11-14 v3.6 - REF_IG_Dfe8B5Hs3G6 look (neutral matte grade), grade_check, contact tolerance 0.05
**UNRENDERED / visually untested: no test render was allowed. Every new preset value is derived from measurements of the
reference reel and must be confirmed by a 4-still look-dev render + tools/grade_check.py before an episode uses it.**
- `rbx/look.py`: NEW presets ref_matte (default), ref_day, ref_night, ref_practical (neutral fill/rim, shadows (1,1,1), warm
  practical key, desat, lift/roll matte toe + highlight roll-off, vignette, per-preset exposure, AgX Base Contrast);
  `look.ref(base, warmth, sat, desat, lift, roll, exposure, vignette)` tuner; `REF_TARGETS`; `DEFAULT_PRESET`; cinematic()
  default preset ref_matte and applies preset exposure; _grade_extra handles lift/roll. Old presets unchanged + selectable.
- `rbx/cast.py`: LOOK_RIG entries for ref_*; LOOK_COOL neutral fill/rim colours for the character rig (old #cfe2ff sky blue
  was the face-level source of EP1's blue cast).
- `tools/shotkit.py`: V.look default "day" -> look.DEFAULT_PRESET (ref_matte).
- NEW `tools/grade_check.py <mp4|stills dir|still>`: ffmpeg-only B-R / saturation / p2 / p50 / p98 vs the ref spec, PASS/FIX
  rows + coolest / most saturated frames. EP1 (v2): cool-cast frames 34/92, sat 0.60, p2 6, p50 83, p98 212 -> 6 FIX.
- `rbx/town.py`: CUFF_TOL = 0.05 studs (insert_cuff_button pinch + insert_sleeve_pull grip were 0.2); NEW
  `hand_on_prop(hand, prop, t0, t1, step, tol)` bbox-gap guard incl. start frame -> STRESS_FAIL hand_on_prop. NOTE: the
  previous builds measured 0.112 / 0.130 and will now FAIL until the hand geometry is brought onto the cuff.
- `tools/qa_gate.py`: build-guard text covers grip / hand_on_prop.
- `tools/captions2.py`: defaults size 84 -> 64, y 0.67 -> 0.65 (POS mid 0.65, low 0.70), pop off (hard cut).
- `tools/pacing.py`: row 'cuts/min vs REF_IG (~30)' (26-40 ok, else FIX). EP1 = 35/min ok.
- docs: research/REF_IG_Dfe8B5Hs3G6.md (full 1 s coverage shot table), AGENT_PLAYBOOK sec 3/4/7/9 (ref look + grade_check
  mandatory pre-delivery), LESSONS.

## 2026-11-14 v3.5 - worst-defect fixes after the 5-round loop
- NEW `rbx/town.py insert_cuff_button(t0, t1, t_pinch, role, helper, t_click)`: close insert on two hands at a cuff
  (presenter's wrist across frame, placket + 2-hole button to the lens, helper's skin/sleeve hand enters lower right,
  thumb + index pinch the button, buttoning twist, button seats on the click). Measured pinch->button max 0.112 studs.
  test_seq s04 now uses it (was the unreadable full-body two-shot).
- NEW `rbx/cams.py hands_guard(cam, chars, t0, t1, zone=0.2)`: STRESS_FAIL hand_near_lens when a fist projects into the
  bottom 20 % / side edges. NEW `rbx/motion.py hide_wrist()`: one-armed sad wrist beat (no wing arms).
- test_seq s02/s05/s07 reframed: MCUs cropped at mid-chest, camera at/above eye level, body 3/4, lens-side arm back;
  s02 35 mm from chest height with hide_wrist; locker wipe motion blur 1.0 -> 0.6.
- `tools/captions2.py`: captions.json "hide" rules (per shot / per word). test_seq hides '001' in s08.
- `rbx/cast.py` Mom headband conformed to the hair cap (semi-ellipse at y -0.12, was floating ~0.25 above).
- `tools/qa_gate.py`: 'build guards' check (STRESS_FAIL lines from out/render_stdout*.log), 'captions vs insert' honours
  hide rules. LESSONS.md: 4 new rules.

## 2026-11-14 v3.2 - quality loop summary, AGENT_PLAYBOOK, qa_gate
- Loop: 5 review rounds on test_seq (8-shot 12.6 s Episode 1 excerpt, placeholder voice) against REF1. Fixed and measured
  over the rounds: flash_cut (2-3 white + 3 decay = 6 f, frames 131-136), whip landing re-aimed (blur span 10 f), skin_mat v3
  + block_hand v5, night interior cast light, caption snap to cuts/voice (max 0.45 f off), score melodic share 96.8 -> 84 %,
  end guard, audio -14.0 LUFS / -1.4 dBTP, last frame on the audio end (378 f = 12.600 s). passed=false at the end.
- NEW `engine/docs/AGENT_PLAYBOOK.md`: mandatory rules (gates, REF1 shot numbers, acting, lighting, transition frame budgets,
  audio mix, captions, blender lock, preview-and-LOOK loop, fix per failure class, open weak spots).
- NEW `engine/tools/qa_gate.py <slug> [--stress] [--no-audio]`: one PASS/FAIL delivery gate with exit code (0/1/2) and
  out/qa_gate.json. test_seq result (measured): FAIL, 5 checks - transition SFX only +9.6/+5.5/+7.8 dB over bed (rule +10),
  locker push blur span 1 f (rule 2-20), s08 caption '001' doubles the insert readout. Passing: loudness, silence, flash 6 f,
  whip 10 f with sharp landing, caption timing, length 378/378 f. Pacing warns (FIX: length 12.7 s, 42 words in 15 s: excerpt).
- SKILL.md: v3.2 read-first pointer, pipeline step 11c QA GATE (blocks delivery), toolkit map, trigger notes, sync trap.
- Still open (not fixed in this loop, see AGENT_PLAYBOOK sec. 11): D2 cuff action, D3/R4-2 wing arms, R2-2/R2-5 MCU
  framing/contrapposto, R2-1b brow/mouth keys, R2-1 '001' caption, D4 hand/watch finish, R2-3 headband, R5-1 whip landing
  object, R5-3 locker wipe, R3-2 score timbre + SFX level, R1-3 full stress run. Cast designs untouched.
- Trap: `setup.py --update .` run from the kit folder made the kit folder the workspace (pointer rewritten); restored by
  re-running with `~/RobloxStories`.

## 2026-11-14 world round 5 (D4/R4-1, R3-2; R2-3 reported)
- D4/R4-1 `rbx/town.py skin_mat` v3: SSS 0.35, grazing falloff (LayerWeight 0.55 -> MapRange) to a deep red-brown
  terminator, AO crease darkening (0.45 floor) so finger gaps/wrist read as geometry. Measured: s08 skin was 245/220/205
  (clipped); now 235/205/186 with visible centre-to-edge gradient (still_08_11.50/11.90, still_01_2.00).
- Root cause of the clipped "plastic slab": the shot's cine_room look rig (key 3200 W + fill, character scale) lands flat on
  the camera-facing arm on top of the insert's own lights. Wrist insert now sets look.exposure(-0.6) and gives the backdrop
  lights +0.6 stop back; rims raised (330/240/300 W), front bounce 140 -> 45 W, key moved to the side.
- `block_hand` v5: palm overlaps the forearm 0.3 (no groove = no "stack of blocks"), 4 separate fingers of different
  lengths with knuckle bumps + curled tips and real gaps, two-segment thumb.
- Latent: phone + laptop insert hands used the flat `tw_skin_*` plastic material; now `skin_mat` too (not re-rendered).
- R3-2 re-verified: front_hall(night=True) stress tiles (cine, 18/45/85, rot 4 = Mom 85close): no blue cast (mean RGB
  137/116/110), face luma ~100. No change needed (r4 `_interior_cast_light`).
- R2-3 Mom headband NOT fixed: it is built in `rbx/cast.py` (cast owner); still floats as a ring in the front_hall 85close tile.

## 2026-11-14 fx/captions/audio round 4 (R3-1, R3-2, R3-3, R3-4)
- R3-1/R3-3 `rbx/fx.py`: new `flash_cut()`; split flash = hard cut into 2 white frames (255, measured luma 254.9) + 4-frame
  decay, all on shot B; A-side no-op. Root cause of the grey: partial mix 0.55 at +1.2 EV under AgX never reaches white.
  Cue on the exact cut frame (`cut_time`). test_seq frames 131-132 white, 133-136 decay, 137 clean (full-res render).
- `tools/captions2.py snap_to_cuts`: 'EVERY MORNING' 130 -> 132 (after the white), 'THAT NUMBER' 30 -> 34 (on the cut).
- audio_qa: flash cut +16 ms +21.6 dB -> ok; 3/3 transitions.
- R3-2 `tools/score.py`: motif gated by rests + rest budget: melodic 96.8 % -> 84.0 % (same seed). Score tags: ambient pad/singing bowl.
- R3-4 score end hit + `tools/mix.py end_guard` (-2.4 dB here): earshot closing level +2.9 -> +0.8 LU, critique 23/23.
- `tools/finish.py`: `.keep_frames` marker (auto_clean deleted test_seq frames once this round; restored from final_nocaptions.mp4).

## 2026-11-14 world round 2 (D4, D8) - rbx/town.py insert_table / _bokeh_backdrop
- D4 ROOT CAUSE: the wrist 'cuff' cam sat 0.9 below the arm pitched up, so the lower 40 % of frame was the arm's unlit
  underside (blurred, near-black) and the top looked past the 30-high backdrop wall into the world. Cams now sit level/above
  the arm (cuff: device centred during the rack; ecu: 28 mm, target pulled toward the fist so the knuckles anchor the wrist).
- Backdrop wall 60x70 (no sky over it for any up-angled insert), upper wash light `_bgL3`; bokeh spheres seg 10 -> 40
  (defocused 10-gons read as octagons). Wrist: warm under-bounce `it_bounce` + low back rim `it_rimL`; strap lighter
  (#5d7088) with edge lips, wraps the block wrist as one band.
- Measured (test_seq s01 stills t=0.2/0.63/1.6, cine_room look): lower-40 % mean luma 0.30-0.34 (was near-black);
  world_stills cuff p2 0.051 -> 0.102. s08 preview (001) checked: lit wood floor, round bokeh, knuckles in frame.
- D8: night kitchen still (research/world_stills/kitchen_v3b_nightTrue_wide.png) re-checked: no pink cast, ceiling lit.

## 2026-11-14 fx/audio round 1 (D6, D7)
- D6 `rbx/fx.py push_through()`: root cause = the LINEAR setter read `action.fcurves` (absent on Blender 5 layered
  actions) inside try/except, so keys stayed BEZIER and the card lingered. Now uses `core.fcurves()`, QUAD ease-in to full
  cover on the last frame of A only, "out" keyed one frame early with ease-out. 540x960 render of s07 end/s08 start:
  frames >= 50 % dark (luma < 40): 2 (318: 0.66, 319: 1.0); was 5.
- Latent, same bug: `fx.flash()` exposure interpolation setter also used `action.fcurves` -> `fcurves()`.
- D7 `tools/mix.py`: peak-aligned sounds get a trimmed (<= 0.17 s), reshaped pre-roll with a hard 4 ms attack (`shape_pre`):
  every whip/whoosh/riser cue in every story now has an onset at motion start and its peak on the cut. Measured
  (sfx bus minus no-sfx mix): whoosh onset 7.25 s at +5 dB over bed, peak 7.38-7.42 (cut 7.433). earshot: whip cut onset -11 ms.
- D7 `tools/score.py`: darker sparse mystery (bowed motif, low root, slow, bowed metal always, lowclock pulse). See docs/AUDIO.md.


## 2026-11-14 acting round 1 (rbx/motion.py, docs/ACTING.md) - D2, D3
- ROOT CAUSE (D2, D3): R6 targets out of reach. Shoulders are 1.5 off centre, arm 1.55 long; midline / chin / belly
  targets were unreachable and `solve_arm` straightened the arm toward them, so fists floated (Mom's hands at her chin,
  tug_sleeve hands apart, winged elbows). New `reachable(arm, p)` envelope used by every IK call (slide toward own side
  keeping height/depth, keep fists out of the torso).
- D2 `present_cuff`: IK forearm forward at belly height (optional `toward=` torso turn) instead of FK (50, 22) that put
  the arm out to the side at chest height. New `cuff_point(ch, arm)` empty on the sleeve cuff (forearm, 0.42 above fist).
  `button_cuff` rewritten as a world-space solve of both characters (`_place_for_contact`): Mom faces the cuff cheated
  0.6 to camera, is placed so the cuff is at her right-hand working point, right fist ON the cuff; left hand cradles the
  forearm only when reachable, else hangs relaxed. Measured test_seq s04: R fist to Harry cuff 0.15-0.18 studs from
  t=5.3 s (was 0.55-0.58 to the fist, hands at chin height). RBX_DEBUG=1 prints the distance.
- D3 `tug_sleeve`: fists meet face to face at x=0, hip-local z 0.85 (reach-envelope optimum), tug moves both fists
  down together. POSES: stand/relaxed arms hang with out ~0 and no twist, key_pose_dict cancels hip roll on FK arms
  (gravity hang); confident = thumb in front pocket (was hand on hip = wing elbow, Tyler s07); hands_hips elbows tucked
  back. Verified in 540x960 renders of s02, s05, s07.
- NOTE setup sync: `setup.py --update ... .` run from the kit dir treats "." as the WORKSPACE (copied engine into the
  kit root and repointed ~/.roblox-story-kit.json to the kit). Pointer restored; use `setup.py ~/RobloxStories --update`.

## 2026-11-14 test_seq shots.py (round 1, shot direction)
- D1: s03->s04 flash shortened to REF1 length: s03 `fx.flash(t1-1/30, fin=3, hold=0, fout=0)`, s04 `fx.flash(t0, fin=0, hold=0, fout=4)`. Measured (540x960 render, luma): 7 lifted frames (131-137), 5 strong; was ~17. Screen text readable up to the cut frame.
- D5: s05->s06 whip uses `WH_K = dict(fx.WHIP, deg=-40)` for both halves; +75/-75 ended on a bare grey wall, -40 ends on the dressed fridge/art wall (frames 217-223 checked) and s06 lands on lockers.

## v3 integration test fixes (2026-11-14, videos/test_seq)
First run of cast v3 + cams/look/fx v3 + acting + town v3 + audio v3 together. Minimal fixes:
- `rbx/town.py insert_table(kind="wrist")`: sleeve/cuff/skin were hard-coded cyan hoodie + pale skin, which matches no cast
  member; now `skin=, sleeve=, cuff=` params defaulting to Harry (#e9b98f skin, cream sleeve, maroon cuff).
- `rbx/fx.py flash()`: a flash split across a cut (A: fout=0, B: fin=0) fired the sound twice (0.47 s apart), and the sound
  name "flash" does not exist in `sfx/` (silently dropped). Now only the fin>0 side fires, falling back to "sparkle"
  when `sfx/flash.wav` is missing.
- `tools/pacing.py classify()`: keywords were matched anywhere in the description in TYPES order, so "AERIAL: ... street
  screen" counted as an insert ("SCREEN") and "ECU: wrist" as a face. The type-tag prefix before ":" now wins.
- `tools/render.py cues` rewrote audio/cues.json from sfx() calls only, wiping the hand-written beat/amb/hold cues that
  AUDIO.md says to put there; it now keeps entries without an sfx "name" (full runs only). `tools/ambience.py` also
  reads `amb` entries from audio/beats.json (it ignored them: test_seq got room tone only instead of street/kitchen/hallway).

## v2.4 (2026-11-13) Blox Town world + intro video
- `rbx/robloxworld.py`: reusable classic-Roblox-style map 'Blox Town' (procedural studded materials, sky/clouds/hills, spawn
  plaza with fountain + neon RBLX ANIMATES arch (flicker-on), lamp posts with RBLX ANIMATES banners, town hall, Blox Bakery,
  skatepark, family house + garage + backyard grill, park, shops, trees/bushes/flowers/fences/benches/mailboxes/crates,
  giant 3D RBLX ANIMATES hill letters) + interiors kitchen() / living_room(gamer=).
- `tools/eleven_lines.py`: regenerate single lines with previous_text/next_text for splicing.

## v2.3 (2026-11-13) cast revisions (user review)
- Renames: host Nova -> HARRY, best friend Dash -> TYLER (Char names, labels, docs).
- Luna hair v3: side part + tapered fringe, waist-length crimson NURBS locks (`cast._strand`) over both shoulders + back layer,
  neck-parented sway rig; low rim light for legs; stronger shy blush.
- Harry v2: varsity jacket, chain, star patch, chestnut tapered-lock hair, rounded (subsurf) head, atlas `harry`.
- Dad v2: orange puffer vest over lavender hoodie, salt-and-pepper slicked hair, Mom's skin tone, atlas `dad` (brows, stubble).
- Tyler v2: navy zip jacket, spiky brown hair with flat fringe, dot-eye atlas `tyler`, skateboard.
- New look preset `story_warm`; new expressions exasperated, grumpy, deadpan, shocked.

## v2.2.1 (2026-11-13) Luna redesign (user request)
- Luna (`cast.crush`) redesigned: custom anime face atlas `assets/faces/luna_{eyes,mouth}.png` from new `tools/make_luna_face.py`
  (red slit-pupil eyes, winged lashes, blush strokes, pout with fangs; all 16 eye + 16 mouth cells), wider head, long dark-red
  side-parted hair, denim jacket + vest + tie + skirt + boots. New generic expressions in `acting.EXPR`: pout, beam, surprised, shy.
  Other 7 characters unchanged.

## v2.2 (2026-11-13) permanent cast for @rblxanimates
- `rbx/cast.py`: 8 locked, reusable characters (host Nova, Mayor Bigsby, Dash, Luna, Mom Rosa, Dad Rick, Grandpa Otto,
  Grandma Pearl), each a rigged Char with signature colour, silhouette add-ons (no helmet hair), hand props, rim light, idle.
- Motion polish helpers: `cast.hop` (anticipation, stretch, squash, overshoot), `cast.walk2` (hip bob after heel strike, torso
  counter-twist), `cast.react`, `cast.squash`.
- `docs/CAST.md` bible; look-dev `videos/rblx_cast/shots.py` (cast sheet + portraits).

## v2 (2026-11-13)
Why: the first video (mosquito_town) felt like 1.5x speed, the voice was disliked, props (steel box, pigeon) and
mosquitoes (too big) looked unpolished. Research + measurement of reference channels (docs/REFERENCES.md) drove these changes.
- Voice: ElevenLabs native speed + expressive settings; no stacked time-stretch (voice_run default 1.0, retempo capped at 1.12);
  `eleven.py voices|sample` for auditions; approval gate before the full read.
- Look: `rbx/look.py` (lighting presets with key/fill/rim, fog, HDRI, bloom + saturation/contrast + split-tone grade applied to
  every shot, per-video `V.look`).
- Camera: `rbx/cams.py` recipes (eye_med, close_up, hero_low, ots, two_shot, establish, insert, dutch_push, crash_zoom, dolly_zoom,
  pov, orbit, top_down, ...) with calmer moves and `cams.pick` variety.
- Props: `rbx/props2.py` polished mosquito (hand-size + macro), pigeon, steel locker, crate, robot, drone, server rack,
  terminal, neon sign, lit-window city, survivor hero, wrist band, floating numbers; scale policy.
- Captions v2: grouped words, key word recoloured, Pillow overlay (no libass needed); `finish.py --captions v2|ass`.
- Pacing checker `tools/pacing.py`; asset fetcher `tools/assets.py` (CC0 HDRIs, OFL fonts); synthesised `buzz` SFX.
- Docs: REFERENCES, LOOK, CAMERA, VOICE, PROPS_AND_SCALE, STORY, ASSETS; research notes in research/.
- Workflow: approval gates (voice sample, look-dev pack, script). Setup must use Python 3.10-3.13.
Original v1 skill: ~/RobloxStories/_backups/roblox-story-kit-v1-original/
Known gaps: characters are still the R6 block rig (no R15 limbs/finger detail); no imported models yet (Quaternius/Kenney are
manual downloads, see docs/ASSETS.md); interior sets other than the hideout are minimal; renders ~0.5 frame/s on Apple silicon.

## v2.1 (2026-11-13) - ai_world production polish
- New `rbx/aiworld.py` (imported in shotkit as `A`): `street()` (wet asphalt, lighter sidewalks + curbs, puddles, lane strips,
  street lamps with real spots, vending machines, holo-billboard, barricades, wrecked car, bins, sign, security camera,
  overhead cables, sky-fill + bounce lights: no more black lower third), `hideout()` (shelves, bunk, map wall with strings,
  racks, desk+screens, desk lamp, crates, cables, string lights, hanging lamp, blast door, dust), `core_hall()` (rack rows,
  floor/ceiling strips, wall cameras, vault door + scanner), `core_room()` (giant pulsing eye, rotating rings, pedestal,
  floor cables, consoles with ERROR screens, catwalk rail), `_room()`, `shelf, desk_lamp, screen, bunk, map_wall, blast_door`.
- Cast: `enforcer()` (tall 'Unit Seven', armour, red visor/trim, chest number, two rim lights), `robot2()` (trim + rim),
  `helper_bot()`, `drone2()` (nav lights, under-glow, antenna, optional searchlight + visible cone), `citizen(i)` (varied
  hair/outfit/skin/scarf/vest/beanie/glasses/backpack/wrist tag + optional floating number), `face_light()`.
- Animation/FX: `pulse()` and `flicker()` on emission, `spin()`, `cable()/sag()`, `sparks()`, `dust()`, `rain()`, `searchcone()`.
- `wrist_macro()`: standalone big forearm + tag with the number facing the camera (fixes the dark-slab wrist insert).
- `cams.py`: `crane`, `handheld_follow`, `macro`. `look.py`: brighter neon preset, `look.exposure(v)` per shot (shotkit applies).
- `chars._x_backpack` default label is now blank (was "EDDIE"; showed on every backpack). Survivor backpack blank.
- `tools/synth_sfx.py`: numpy SFX drone, scan, powerdown, beep (added to sfx/ and pack.json).
- Known: `look.grade` colour-balance step fails on Blender 5.3 ("float has no len"), so split-tone is skipped (bloom +
  saturation/contrast still apply). Not fixed yet.

## v2.2 (2026-11-13)
- Installed skills earshot (ears for agents, ~/earshot) and real-sfx (real recorded SFX placement). Added docs/AUDIO.md and tools/audio_qa.py; SKILL.md step 11b makes audio QA part of every video.
- finish.py masters the mix to -14 LUFS / -1.5 dBTP (loudnorm) after the mix; earshot found v1 at -19.5 LUFS. Env NO_LOUDNORM=1 skips.
- tools/sfx_library.py: fetches Kenney CC0 audio packs; registered with real-sfx (470 sounds indexed). Thin on whooshes/risers/ambience.

## v2.3 (2026-11-13)
- Storage on Google Drive: tools/storage.py (to-drive/status), render scratch in local tmp_dir via symlinks (kit.link_local_tmp), auto_clean_frames after finish.py, KEEP_FRAMES=1 to keep, clean.py handles symlinks.

## v3.0.1 (2026-11-14) - test_seq integration-test fixes
- captions2.groups_of: clause/sentence breaks now also detected when the word ends in a closing quote or ellipsis
  (`Harry."`, `you."`, `age…`). Before, groups ran across sentences ("HARRY THEN", "YOU A DIGIT").
- finish.py phone copy: video bitrate capped at 6 Mbps. The 25 MB budget formula gave a 12.6 s clip 15.8 Mbps, so the
  720p "phone" copy (24.5 MB) was ~2x larger than the 1080p master.

## 2026-11-14 test_seq round 2
- town.py: evening_kitchen grade no longer split-tones magenta (shadows 0.99/0.99/1.01, lights 1.05/1.0/0.93); night kitchen ceiling #d9cbb6 + warm up-bounce light kt_ceilB (fixes dark ceiling / pink top third). Not yet verified in a night render (test_seq uses the day kitchen).

## 2026-11-14 test_seq round 3 (world)
- [D4] town.insert_table wrist: rebuilt device as ONE strap ring + ONE round bezel (cyl) + inset screen; the old black band +
  tilted rectangular bezel + level counter pad read as 2-3 overlapping black plates. signs.wrist_counter(face=False) skips its
  own pad/glow plane. Device front set inside the sleeve's inner face (digits no longer glow through the closed sleeve in cam
  'cuff'). Matte screen (no key-light hotspot). Verified world_stills insert_wrist ecu/cuff.
- [D4] _bokeh_backdrop: lit tabletop, solid counter to the tabletop, low wash light + low bokeh; insert world ambient warm
  (cool for phone) instead of navy 0.5. Wrist ECU lower-half mean luma 13-35 -> 85-129; phone insert also checked.
- block_arm: cuff rib grooves are a darker cuff shade instead of pure black slats (read as spikes at ECU).
- [D8] Night kitchen verified in a render (kitchen@night=True wide): no pink cast, ceiling warm; ceiling-wall junction dark band
  fixed with full-depth kt_ceilB (28x24) + kt_wallW back-wall wash.

## R2 acting (2026-11-14)
- motion.POSES["confident"]: dropped the IK "thumb in pocket" hand (fist floated in front of the belly in the s07 MCU); left arm now a loose FK hang (-6,1,8), elbow 12. Verified test_seq still_07.
- Verified (no code change) s04 button_cuff contact: Mom R fist -> Harry cuff 0.169 studs at contact (RBX_DEBUG), still_04_5.60/5.90 show the fist on the presented cuff.
- Open: tug_sleeve (s02) still reads as raised/winged arms; R6 geometry (shoulders 1.5 off midline, arm 1.55) makes fists meeting at the midline only possible with near-straight arms. Needs a design choice (one-handed tug or allowing arm/torso overlap).

- 2026-11-14 test_seq R2 (shots owner): final render completed shot-by-shot in foreground under lock (render.py takes ONE selection arg; "final 2 3 24" silently renders only shot 2 - pass one id per call). Flash s03->s04 measured 7 milky frames (f131-137); s05 whip ends on dressed fridge/art wall. Outputs: out/test_seq_r1.mp4, _phone, r1_contact16.jpg, r1_transitions.jpg.

## 2026-11-14 test_seq round 2 (fx/audio)
- [D6] push_through s07->s08 measured on a fresh full render (12 spp): 1 fully black frame (0319, mean luma 4), 1 more
  >= 50 % dark (0318, 60 % px < 20); first frame of s08 (0320) already opening. Budget (<= 2) met, no code change.
- [D7]/[R1-2] score.py mystery: the HOOK now states the bowed motif (motif_on += hook, motif_max 3 -> 4) and the first
  rest starts no earlier than 3.5 s (all moods). Root cause: a drone-only hook plus a rest at ~2.4 s was not heard as music
  under the VO (earshot AST Music < 0.3): critical "music presence 33 %, no music at 0:00-0:05" on 2 of 4 seeds; 0 of 6
  seeds fail now (music level/ducking were tested and are not the cause: -13/-9/-5 dB all gave 33 %).
- test_seq_r1.mp4 finished + audio_qa: -14.1 LUFS, -2.4 dBTP, launch-grade 21/23, 0 critical/major; whoosh onset +7 ms on
  the 7.42 s whip cut; 377 frames @30 = audio 12.565 s; 1080x1920; phone copy 8.6 MB.
- Known, not fixed: horror mood fails the same music-presence check (0-33 % on seeds 1-3; adding hook motif/pad did not
  help and pushed melodic share to 86-90 % vs the 45 % horror target). Mix nearly mono (side -21.5 dB) and sub share
  -17.8 dB (minor). NOTE: the sync command `setup.py --update ... .` run from the kit dir makes the KIT DIR the workspace
  and rewrites ~/.roblox-story-kit.json; use `setup.py ~/RobloxStories --update --no-pip --no-music --no-test`.

## 2026-11-14 test_seq ROUND 2 (render agent)
- shots.py: no API changes needed (all 8 shots built in `cues` mode with the synced kit). Old frames/blends deleted; full
  re-render 1080x1920 @24 spp, one shot per render.py call under the blender lock (~16.5 min total). 381 frames rendered,
  finish trims to the 12.56 s mix = 377 frames. EEVEE warns "Shadow buffer full (2049-2056/2048)" on s06/s07 (hallway) -
  possible missing shadows there; not investigated (world owner).
- Measured: flash s03->s04 frames 132-137 (peak luma 224 at 133-134), 6 milky frames; whip s05->s06 f218-228 (s05 end f223
  lands on the fridge/art wall); push-through s07->s08: 1 black frame (319, luma 4), 318 half dark, 320 opening.
- audio_qa: launch-grade 22/23, 0 critical/major, -14.1 LUFS, -2.7 dBTP. pacing: FIX narration 203 wpm (placeholder say voice).
- Seen, not fixed: s02 tug_sleeve still reads as raised/winged arms (frame 51).
- Outputs: out/test_seq_r2.mp4 (14.2 MB, 1080x1920), out/test_seq_r2_phone.mp4 (8.7 MB, 720x1280), r2_contact16.jpg, r2_transitions.jpg.

## 2026-11-14 R2 judge
- NEW tools/stress_suite.py: re-runnable regression stills (8 cast x 12 rotating poses x 10 location jobs incl. kitchen day/night, hallway, classroom, main street day/night, bedroom, front hall, cine+flat, 18/45/85 mm, 1000-extra crowd aerial). Takes/release blender.lock per Blender run. Output ~/RobloxStories/research/stress/<stamp>/ + sheet.jpg. Run: python tools/stress_suite.py all 6

## 2026-11-14 R3 shots (test_seq direction)
- test_seq/shots.py: V.end = voice.wav length rounded UP to a frame (was last word end + 0.25 = 381 f vs 12.565 s mix; finish cut 4 frames). [R2-3]
- test_seq/shots.py: new mcu_live() for s05/s07: 12 %/s push, 7-8 deg arc, eyes at 36 % from top (aim drops below face), micro drift 0.5 deg. [R2-5]
- test_seq/captions.json: inserts s01 + s08 captions at "top" (0.20) so they clear the wrist device; emphasis.txt: "001" no longer yellow (duplicated the prop), "clicked" instead. [R2-1]
- stress_suite run 20261114_0329 (10 jobs, all rc=0), sheet at research/stress/20261114_0329/sheet.jpg. [R1-3]

## 2026-11-14 test_seq round 3 (world, R3)
- [D4] wrist insert v4: `block_hand` (back of hand + 4 knuckle bumps + curled fingers + thumb) replaces the fist box + 3
  crease slats (the "diagonal stripe bands"); `skin_mat` mottled SSS skin + micro-normal (no flat slab); dark continuous strap
  ring with keeper ridges and a smaller bezel so the band visibly wraps the arm (was light-grey lugs only); sleeve slides to
  0.75 past the band (cuff in the ECU) and starts 0.85 past the bezel (no digit glint through the sleeve mouth); cuff ribs
  are fine inset knit lines; `insert_table(role=)` + `ARM_STYLE` give each of the 8 cast their own skin/sleeve/cuff
  (Harry: cream sleeve, maroon rib). ECU re-framed to fist + watch + cuff; top rim light. Verified world_stills
  insert_wrist r3w2 ecu/cuff.
- [R2-4]/[R2-3 hallway] `shadow_budget()` in `_L` (all locations): shadow pool 1024, soft washes res-capped. 1080x1920
  24 spp + motion blur s06 frames: 0 'Shadow buffer full' (the old 2049-2056/2048 no longer reproduces on current code even
  with the old 512/0.001 settings, so the budget is headroom, measured on 3 frames). ceiling_panel emitter halved, hallway
  ambient 0.3->0.2; under-feet floor luma 187 vs open floor 212 (contact shadow present but soft; not stronger than before).
- [R2-2] `night_cast_keys`: warm shop-window spill row + cast-mark key/fill on night main street / night_street. Stress
  main_street_night_cine_85close: face fully readable (was near-black).
- [D8] night kitchen: warm ambient + kt_frontF / kt_floorW fills. Stress kitchen_night_flat 18low/45med: dark costumes keep
  detail, no pink cast, ceiling warm, foreground floor warm.
- NOT mine (cast.py owner): Luna/Mom headband floating above hair cap + spikes clipping, Harry hair-top seam crease.

## 2026-11-14 R3 acting/characters (motion.py, acting.py, cast.py, ACTING.md)
- [D2] s04 cuff: root cause = the cuff was presented FORWARD, so from the 3/4 camera it projected over Harry's own jacket and
  Mom's (correctly placed, 0.15-0.2 studs) fist read as a hand on his chest. `present_cuff(toward=, cam=)` now raises the
  forearm toward the partner with the fist pushed out past the torso edge (|x|>=1.6) into the gap between the bodies;
  `button_cuff(present=True)` re-presents the wrist toward the buttoner before solving her placement (joint world solve) and
  measures contact over the whole span (`ch._contact`, prints STRESS_FAIL if > 0.25). Measured test_seq: 0.165 (f160),
  0.173 (f180), span max 0.206 / mean 0.182; still s04_f0160 shows the wrist in the gap with Mom's fist on it.
- [D3] wings: REST arms out +4 -> -2; POSES stand/relaxed/confident/sad_slump/point FK hangs angled in (out -2..-3) and asymmetric
  (one forearm forward, elbow 24-26); `clamp_hang()` clamps hanging FK arms (|fwd|<45) to out -6..+3 in key_pose_dict and
  talk beats; legacy acting.G idle/lean/slump outs fixed; locomote arm_out 6 -> -1. Fists now x 1.30-1.44 (were 1.58-1.63).
- [D3] tug_sleeve rebuilt: elbows tucked (pole down/in), fists face to face at the midline at the only height R6 allows
  (hip-local z 1.0, y -1.0, |x| 0.51); measured fist centres 1.06-1.10 apart (blocks 1.0 wide = touching), s02 f51/f62.
- [D3] lean_on (s06 'arm thrown up behind the head', 'hand crossing the chest'): flat hand clamped to a shoulder band
  (hip-local z 1.0-1.85) - shots.py passes a locker point at z 5.4 above the head; pocket fist on its own hip (x 1.3).
- [R2-1]/[R2-2] talk_cadence v3.2: face arcs (opening look, eyes+mouth swap ON each stressed word - longest word if none
  flagged, settle look, eye dart in the longest gap), per-phrase alternating head tilt + torso weight shift, low MCU-safe
  gesture arc for hands=False (one forearm to the belly, arms alternate, never symmetric). Seen in s05 f200/212 and
  s07 f280/290/305 (3 different eye sets per line, forearm beat, head tilt).
- acting.face/blink: blinks keyed at build time reopened to the OLD eye cell and silently undid later expression swaps; the
  reopen key is now re-keyed whenever eyes change (latent bug for every cast member in every story).
- [R2-1 walk] cast.walk2: arm swing clamped to +-30, out -1, elbows keyed per step (18 fwd / 6 back), ends in the hang pose.
  Re-ran stress_suite front_hall (research/stress/20261114_0343): the swing is now within 30 deg but still reads big
  because walk2 turns the walker along its path (side-on to that camera) - stress_suite issue, not changed (not my file).
- [R2-3] Luna: NOT drift. test_seq has no Luna; the 'dark hair with red band' character at f160/f200 is Mom (Rosa: espresso
  bob + coral headband). cast.crush is the single v3 design (long dark-crimson hair, black tie) used everywhere.

## 2026-11-14 ROUND 3 (fx/captions/audio/pacing)
- [D7] Transitions: mix.py TRANS designs whip/flash/push sounds from real CC0 recordings (air swell peaking on the cut,
  hit attack on the cut, 50 ms suck-in, auto-pan with the move); fx.whip_out/flash/push_through and cams.whip_pan/
  crash_zoom/fly-through tag their cues (cut/kind/pan). push_through had no sound; whip_pan cued at the whip start;
  flash used the "sparkle" glock. Measured test_seq: attack within 1 frame of the whip (-4 ms, +13.7 dB/20 ms) and push
  (-28 ms, +17.8 dB); earshot timeline whip "+1 ms OK", push "-29 ms OK". Flash: voice word onset 60 ms before the cut
  masks it (+1.3 dB in the frame) - cut/line placement, reported to shots owner.
- [D7] Mystery score: dark string pad, cello pizz ostinato, bowed motif oct 1, modal paths (no i-VI-III-v). earshot
  "inspirational corporate" z 1.4 -> 0.4-0.65; critique launch-grade 21/23, 0 critical/major, music presence 67 %.
  Rests: none before 5 s / in the last 3 s, pre-hit rest 0.5 s, hook escalation floor -1 dB, end fade 1.5 -> 0.35 s.
  finish default score level -20 -> -19 LUFS.
- [R2-1] Stereo: stereo SFX bus + pan, widened beds, voice early-reflection side. Side/mid -21.8 -> -10.9 dB.
- [R2-2 dyn] Ducking gate rewritten (opens in phrase gaps; applied duck -4.9 dB logged in audio/mix_report.json), music
  dips before cuts, BEAT_RIDE_DB fader ride: LRA 1.5 -> 4.4 LU (ending under the body in the ride; critique still says
  the last 1.25 s is +2.7 LU over the body, minor).
- [R2-2 tail] Not reproducible on test_seq_r2 (last frames luma 96, caption on): guarded anyway - finish holds the last
  frame when frames end before the mix, cuts > 6 trailing black frames (tested on synthetic projects), last caption
  holds to the end of the sound.
- [R2-4] captions2: frame-nearest switching, snap to heard voice onsets, out/caption_report.json (test_seq: onset
  <= 0.45 f, all words visible while spoken, 5 starts snapped, "Every" was 100 ms late in words.json). pacing.py: wpm
  over the spoken span, "info" with a placeholder voice (203 wpm, needs the real take).
- Bugs: mix.py took audio/music.json as the music file; ambience now seeded from --score-seed (reproducible beds).
- audio_qa.py: "Mix checks" section (stereo, LRA, duck, dips, per-transition attack within 1 frame).
- Output: videos/test_seq/out/fx_r3_audio.mp4 = r2 picture + round-3 mix (frames/ were removed by another agent's
  re-render while this round ran, so no new full mux).

## 2026-11-14 ROUND 3 (render agent)
- test_seq re-rendered completely with the current kit: shots.py needed NO API changes (all 8 shots built in preview and final).
  1080x1920, 24 samples, serial under blender.lock; finish --mood mystery (KEEP_FRAMES=1), pacing, audio_qa.
  Output out/test_seq_r3.mp4 (12.60 s, 15.3 MB), test_seq_r3_phone.mp4 (6.6 MB), r3_contact16.jpg, r3_transitions.jpg.
- Open findings: flash cut 4.407 s has no clear audio accent on the cut (audio_qa CHECK, 2/3 transitions accented);
  the caption "EVERY MORNING" appears about 4 frames before the s03->s04 flash cut (it sits on the aerial);
  pacing FIX: 42 words in the first 15 s (placeholder voice, 203 wpm); Mom's s05 'Covered, Harry' face reads as a
  squint/grimace rather than a smile; last frame of the strip after the push-through is black (end of video).

## 2026-11-14 ROUND 4 (world agent)
- [R3-3/R3-2 cuff] block_arm: knit-rib cuff = solid `knit_mat` (flat colour + sheen, no tiled fabric texture) + 9 raised
  same-material ribs per face. The old tile-0.5 fabric + dark inset slats read as diagonal red stripes. Seen fixed in
  test_seq s01 t0.63 and s08 stills.
- [D4] skin_mat v2: a facing falloff toward a deeper, redder tone (a fake SSS terminator) on top of the mottling and the micro bump.
  Wrist insert sleeve rest position bx+0.75 -> bx+0.40, so the cuff and sleeve are in the s08 ECU frame (seen).
- [R3-2 watch] wrist_counter(pulse=1.45): each new value pops (1.45 -> 0.92 -> 1.0 over 8 f). insert_table wrist: every
  change in seq spikes the screen emission, a cyan halo ring behind the bezel and it_wcL energy (seen at s08 f350; it is gone by
  f377). NOTE: the flip time comes from shots.py (V.w(41)="001." at 11.6 s). Caption "CLICKED OVER" is f332-348.
- [R3-2 night] bedroom(night=) / front_hall(night=) + `_interior_cast_light` (camera-side warm key + fill, floor wash,
  ceiling bounce) for day and night. Ambient changed from cool blue-grey to neutral-warm. Night uses look evening_kitchen,
  a lit desk-lamp practical and moon spill. Checked in stress-style tiles (bedroom_night cine, front_hall_night flat):
  faces are readable and there is no blue cast.

## R4 shots (test_seq/shots.py, owner: shot script/direction) 2026-11-14
- R3-3: cuts now land on the HEARD voice: shots.py snaps V.words starts to voice.wav onsets with the same rule as captions2.snap_to_voice ('Every' 4.44 -> 4.34 s), so the s03->s04 cut and the 'EVERY MORNING' caption start on the same frame (131). Flash moved entirely to s04 via fx.flash_cut (s03 ends clean: F128-130 luma 103; F131-132 255; decay 243/213/177/141/122).
- R2-5: mcu_live() puts the face on a vertical third (side=+-1, lead room), f/1.4 focus on the face, 16 %/s push + 10 deg arc, stronger handheld micro (0.8 deg / 4.5 cm). s05 Mom right third, s07 Tyler left third.
- R2-1/R3-1 (framing part): s08 builds its own ECU camera aimed AT the device face (focus_pts['ecu']), face at 58 % height, 25 % pulled back so the whole dial is inside 9:16, 22 % push + 6 deg arc to the last frame (no static tail).
- R3-5: V.end = max(voice.wav, existing mix.m4a) rounded up to a frame (finish measures the AAC container, 12.600 s vs voice 12.551 s) -> 378 frames, no held duplicate. Frames with KEEP_FRAMES are in videos/test_seq/frames (real dir, not ~/RobloxStories_tmp).

## 2026-11-14 ROUND 4 (acting agent: motion.py, acting.py, ACTING.md)
- [D2] present_cuff rebuilt (FK "show me your watch": upper arm on the torso, abduction measured 11 deg (was 40),
  elbow 88, forearm level, swung toward the partner by shoulder twist; chest twisted back toward the lens: Harry body
  42 -> 23 deg off camera). button_cuff: work point out front-right of Mom (was in front of her own chest = the "dark
  block"), cheat 0.4, fist on the LENS-SIDE/top face of the forearm (centre-on-centre contact hid the hand inside the
  1-stud sleeve). New contact metric = surface gap (centre distance - 0.5): s04 span max 0.083, mean 0.064 (< 0.2).
  Render check ~/RobloxStories_tmp/r4act/s04_155.png / s04_170.png: Mom's hand on Harry's wrist in the gap, both faces.
- [R3-1] acting.clamp_head on every keyed head pose: pitch -20..+16, roll +-10 (ch.head_free opts out). s04 Harry
  neck roll 4-8, pitch 15 (was 17 roll / 22 pitch), face 42 deg off lens (was 60-76).
- [D3] REST elbows 10 -> 5, POSES stand/relaxed/confident elbows <= 9 (flexed elbows threw the forearm at the lens);
  talk_cadence hands=False beat = forearm UP beside the chest (BEAT_LOW 140 deg flex, upper arm on the torso, held,
  fast drop) instead of a forearm toward the lens. Measured s05 f200 / s07 f280: upper-arm abduction 0-6 deg both arms.
- [D3 s02] tug_sleeve fists overlap (centres 0.90 measured, was 1.10 = visibly apart) at hip-local z 1.2.
- [R2-2] talk_cadence contrapposto per phrase (torso roll 5 + yaw 6, legs counter-rotate, free knee 12) and head
  counter-tilt 6.5-9 deg (measured roll 7.4 at s05 f200); one arm gestures at a time.
- [R2-1/R2-1b/R3-4] talk_cadence faces: mood also read from the mouth (Mom smile -> smile arc, no squint settle),
  TALK_MOUTH (smile lines flap open_smile/grin/smile), stressed word holds its face for the whole word (talk() no
  longer flaps over it), words ending ?/! are stressed (Tyler "Honestly?" gets brows-up + open mouth). Render: Mom
  open smile on "Covered", Tyler sad on "never" (f300).
- NOTE: running setup.py with "." as in the task text makes the KIT the workspace (rewrites ~/.roblox-story-kit.json
  and copies the engine into the kit root). Use `setup.py ~/RobloxStories --update --no-pip --no-music --no-test`.

## 2026-11-14 ROUND 4 (render agent)
- test_seq re-rendered completely (old ~/RobloxStories_tmp/test_seq frames deleted; KEEP_FRAMES=1). shots.py needed NO API
  changes (all 8 shots built in preview and final). 1080x1920, 24 samples, serial under blender.lock, 378 frames.
- finish --mood mystery: 12.60 s, -14.0 LUFS, TP -1.5. audio_qa: 3/3 transition accents on the cut (flash 4.333 s now ok,
  was CHECK in R3), duck -4.9 dB, LRA 4.8. pacing: only FIX = length 12.7 s / 42 words in 15 s (excerpt + placeholder voice).
- Out: out/test_seq_r4.mp4 (14.7 MB), test_seq_r4_phone.mp4 (2.5 MB, 720x1280), r4_contact16.jpg, r4_transitions.jpg
  (rows: flash F128-139, whip F216-227, push-through F312-323).
- Seen: caption EVERY MORNING now starts F132 during the flash decay (no longer on the aerial). Push-through has one
  near-black frame (F317) under "KNEW YOU". Whip ends on the dressed kitchen wall, s06 resolves on Tyler at F227.

## 2026-11-14 ROUND 5 (shot script / direction, test_seq/shots.py + captions.json)
- [R4-1] s07->s08 transition: fx.push_through black card replaced by shots.py locker_wipe(): a lit blue locker-door edge
  (vent slits, steel handle + edge, slight self-glow) crosses the lens in 3 frames with motion blur 1.0, same "push"
  sound cue / cut kind. Measured (50 % res, 10 spp): blender F317 YAVG 125, F318 (full cover) 113, s08 F319 153 (was 23).
  Seen: ~/RobloxStories_tmp/r5shots/tr.jpg.
- [R2-5] s05/s07 MCUs: mcu_live d 11 -> 9, 50 -> 60 mm, f/1.2, push 0.08/s, eyes 0.40: chest-up, face on a third
  (measured Mom x 0.64-0.76 right third, Tyler x 0.23-0.37 left third), visible push+arc, soft background. mcu3.jpg.
- [R4-2] s03 aerial: captions.json "3": "top"; aerial DoF f/8 -> f/2.8 focused on the street screen (focal subject).
- [R2-1] s08 insert framing: whole watch inside frame with slow push (s08_f355.png). The duplicate "001" CAPTION needs a
  captions2.py feature (per-shot "hide"/word suppression in captions.json) - reported to the captions owner.

## 2026-11-14 ROUND 5 (acting agent: cast.py, motion.py)
- [R4-1/R4-2] cast._hands: the 1x1 skin end of the R6 arm block (peach cube / mitten slab) is cut at z -1.28 and
  replaced by a real hand on every cast member: palm 0.66 wide, 4 curled finger blocks and a thumb. Contact empties unchanged.
- [D3] talk_cadence hands=False MCU beat is now low and small: elbow 16 (was 140), hand in front of the thigh. Seen at s05 f200:
  Mom's arm hangs on the torso and the hand reads below it. s07: Tyler's hands hang by his thighs.
- [R2-1b] stressed faces hold until the next stressed word (expr_on faces are not reset). The plain stress settle uses a
  closed mood mouth (TALK_SETTLE) plus a blink, and neutral speakers settle to half-lid eyes. Seen: s07 f280 smile and half-lid, f300 worried frown.
- [R2-2] sway: torso yaw 9 / roll 6.5 per phrase, head tilt 8-10.
- [D2] present_cuff swings the forearm perpendicular to the camera ray (up to 85 deg), so the cuff is side-on toward Mom. Mom's
  hand (with fingers) is on it, measured surface gap max 0.082 / mean 0.063.
- tug_sleeve: hands meet at the belt (z ~1.0) instead of the chest.

## Round 5 (fx_audio): R3-2 / R4-1 / R4-2
- score.py mystery: pizz ostinato removed (pulse none; earshot heard its plucks as glockenspiel/celesta/'chat message pop'); the bed is dark string pad + drone + bowed motif. Music stem alone now tags 'ambient synth pad music' (earshot timeline).
- score.py R4-1: rest bed level per mood (REST_BED_DB -9 default; mystery rest_bed_db 0 + rest_swell_db 3): drone/air/cluster/sub stay up in melodic rests. test_seq 6.15 s phrase gap: mix -35 dB -> -21 dB RMS; earshot no longer reports a drop.
- score.py R4-2: sub stem tuned into the 36-56 Hz octave (was 55-82 Hz, the 'low' band), level -17 -> -11 dB, plus a reveal/climax/dread/twist swell (mood reveal_sub_db, default 3 dB, mystery 5). test_seq full-mix sub band -23.2 -> -9.4 dB (REF1 -16.2..-4.1).
- mix.py R3-2 whip: two recorded whoosh layers high-passed at 350 Hz (WHIP_HP_HZ), no suck-in, no thud layer, +4 dB (WHIP_GAIN_DB), voice tucked -6 dB (WHIP_TUCK_DB) over cut-0.22..+0.10 s. The isolated whip sound now tags 'fast air whoosh' x3 (was drum hit/heavy thud); in the film it reads as a 34 dB swell peaking ON the 7.40 s cut and is earshot's best 'whoosh transition' match, but timeline still does not give it a WHOOSH tag because the placeholder voice talks straight through it.
- NOTE (not my file): the documented sync command `setup.py --update ... .` passes "." as the WORKSPACE, which rewrites ~/.roblox-story-kit.json to the kit master and copies the engine into the master root. Use `setup.py ~/RobloxStories --update --no-pip --no-music --no-test`.

## 2026-11-14 ROUND 5 (render agent)
- test_seq re-rendered completely with the current kit (old frames + blends deleted; KEEP_FRAMES=1). shots.py needed NO API
  changes (preview, cues and final built all 8 shots, no tracebacks). 1080x1920, 24 samples, serial under blender.lock, 378 frames.
- finish --mood mystery: 12.60 s, -14.0 LUFS, TP -1.4, LRA 5.0. audio_qa: 3/3 transition accents on the cut, duck -4.9 dB.
  pacing: only FIX = 42 words in first 15 s (excerpt + placeholder voice).
- Out: out/test_seq_r5.mp4 (13.6 MB), test_seq_r5_phone.mp4 (8.9 MB, 720x1280), r5_contact16.jpg, r5_transitions.jpg
  (flash F128-139, whip F216-227, locker wipe F312-323).
- Seen: flash = 2 white frames F131-132 + decay into the kitchen. Locker wipe F318 is a full blue cover, no near-black frame (was F317 black in R4).
  Open: whip-out end frames F220-222 still land on a mostly bare light-grey kitchen wall (not the fridge/art wall); s02 Harry's
  hands are clasped at the belt and hidden behind his sleeves; s08 insert reads soft/low contrast on the first frames after the wipe.
