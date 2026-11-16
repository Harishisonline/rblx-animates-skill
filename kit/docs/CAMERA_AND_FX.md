# CAMERA, LOOK, FX, PACING, CAPTIONS (v3, REF1 cinematic)

Target: REF1 (docs/REF1_CINEMATIC.md). Test harness + stills: `~/RobloxStories/research/camfx_tests/` (SHEET_v3.jpg,
captions/SHEET_captions.jpg). Harness script lives at the bottom of this doc's "Testing" section.

## 0. Rules of thumb
- One picture per narration phrase (2-8 words), mean shot 1.5-1.9 s, nothing over 3.3 s unless the @S description has `[hold]`.
- Every shot moves (eased push / drift / truck). Only emotional `cams.ecu(still=True)` is "static" (0.3 deg breathing drift).
- Per 10 shots: 3 prop inserts, 3 faces, 1-2 aerials, 1-2 low angles, 0-1 top-down/graphic. Never the same type twice in a row.
- Tag @S descriptions with the type word (`INSERT:`, `MCU`, `ECU`, `AERIAL`, `LOW`, `TOP`, `RUN`, `OTS`, `FLASH`) so
  `tools/pacing.py` can count the mix.
- v3 recipes use a **36 mm sensor on the long side** (`cams.SENSOR`), so lens numbers match REF1 (old `Cam()` default = 24 mm,
  which made every lens ~1.5x tighter). Units: 1 kit unit ~= 0.3 m (character 5.7 tall).

## 1. Camera recipes (`from rbx import cams`) - all return the Cam
| Recipe | Use | Key params (defaults) |
|---|---|---|
| `mcu(t0,t1,face)` | face MCU, the talking/reacting default | lens 45, 7 deg below eye line, push `rate` 0.08/s, f/2.2 |
| `push_in(t0,t1,target,d)` | generic eased push 6-10 %/s | `rate`, `pitch` (<0 = looking up), `roll` |
| `ecu(t0,t1,target)` | tear, shock, eye; prop text | lens 85, f/2.0, `still=True` (emotional hold) or push 4 %/s |
| `prop_macro(t0,t1,target)` | ~28 % of shots: phone, calendar, wrist, switch | lens 85, 40 deg down, f/2.0, `rack_from=pt, rack_at=t` |
| `ground_low(t0,t1,target)` | hero / authority / threat | lens 18, `h` 1.3 (~40 cm), `tilt` 28 (20-35 up), push 5 %/s |
| `dutch(t0,t1,target)` | wrong/urgent beat (switch slam, clock) | roll 16 (12-20), lens 24, low; ONE shot then level again |
| `aerial_glide(t0,t1,target)` | establish a place | h 60, pitch -35, lens 20, `speed` 0.15 (8-25 %/s), blur 0.5 |
| `aerial_dive(t0,t1,target)` | dive into crater/house/crowd | h 80->22, lens 18, ease-in, blur 0.75 |
| `fly_in_window(t0,t1,window,normal,inside)` | aerial -> through window -> character | glass must be open/hidden; passes at `t_pass` 0.62; blur 1.0 + whoosh |
| `truck(t0,t1,subject,fg=)` | sideways track past out-of-focus FG (memorial wall, flowers) | `heading` (look dir), `rate` 0.06 frame-width/s, f/2.8 |
| `rack(cam,t,near,far,frames=15)` | rack focus on ANY cam | 12-18 f |
| `run_follow(t0,t1,subject,offset)` | chase / run | lens 22, shake 0.75 deg @ 3 Hz, blur 0.5; subject = char, object or `f(t)` |
| `whip_pan(t0,t1,pos,h0,h1)` | in-shot whip | `whip_frames` 8, `shutter` 1.0 |
| `overhead(t0,t1,target)` | top-down, slow yaw | h 18, lens 24, spin 12 deg |
| `micro(cam,deg=0.3)` / `shake(cam,deg,hz)` | add drift / handheld to any Cam | |
`cams.CINE_BY_BEAT` lists recipes per beat (open, face, emotion, power, prop, run, overview, transition).
Old v2 recipes still work (eye_med, hero_low, insert, ...) but prefer v3.

## 2. Look (`from rbx import look`)
- `look.cinematic(preset, focus=, cam_yaw=, blur=None)` once per shot: light rig + EEVEE raytrace/fast-GI AO + jittered bokeh +
  mist pass for haze + AgX look. Grade (bloom, CC, lift/gain split tone, haze, sepia, vignette) is applied by shotkit
  at the end (set `V.look = "cine_day"` etc.).
- Presets: `cine_day` (sun #FFE9C8 4.5, cool fill/rim, haze #8FA6B5, vignette .18), `cine_room` (window key + 15 % cool
  bounce), `cine_night` (indigo moon + amber key; add `fx.practical` lanterns), `night_dread` (cold low-key, desat .82,
  vignette .32), `sepia` (desat 85 % + multiply amber + dust; use with `fx.dust`). Old presets unchanged.
- `look.motion_blur(shutter)`: per shot. 0 off, 0.5 = 180 deg (runs, aerials), 1.0 = whips/fly-throughs. EEVEE, headless OK
  (verified: 10_whip_pan_shutter0.0 vs 1.0). Note `tools/render.py preview` turns blur off; still/final keep it.
- Fixed in v3: the old grade's lift/gain split tone never applied (socket bug) - it now does on every preset.
- Resolution: `setup_render` default 1080x1920. Cost per frame measured (M-series, simple town + robot, EEVEE):
  1080x1920 16 samples 1.1 s, 32 samples 1.7 s, 1440x2560 16 samples 1.8 s (supersample: render 1440x2560 and let ffmpeg
  scale to 1080 with lanczos; ~1.6x cost). Real sets with characters will be 2-4x these numbers. Recommend 1080x1920 @ 24-32.

## 3. FX / transitions (`from rbx import fx`)
| Call | What | Notes |
|---|---|---|
| `fx.flash(t, fin=7, hold=5, fout=10)` | white-flash bloom pop (time travel, impact) | exposure ramp + keyed bloom + mix to white; sfx "flash" |
| `fx.ghost(path, t0, t1, peak=.45, fade=12)` | ghost dissolve of a still/sequence (same place, past) | `peak=1.0` = 12 f cross-dissolve FROM the image (e.g. previous shot's last frame `videos/<slug>/frames/NNNN.png`); mixed before the grade |
| `fx.whip_out(cam.ob, t1)` + `fx.whip_in(cam.ob, t0)` | whip-pan cut between two shots | 6 f each, yaw 75 deg, shutter 1.0, whoosh |
| `fx.push_through(cam.ob, t, mode="in"/"out")` | dark object crosses lens = hidden cut | call "in" at end of shot A, "out" at start of B |
| `fx.match_save(name, cam.ob, subject, t)` / `fx.match_frame(name, cam, subject, t0, t1)` | match cut (same framing, new subject/place) | stored in `$RBX_VIDEO_DIR/match_cuts.json` (or temp dir) - build A before B |
| `fx.dust(cam.ob, n=50)` | floating dust for sepia flashbacks | parented to camera |
| `fx.siren(loc, t0, t1, hz=4)` | flickering emergency light | emissive dome + 250 W point, CONSTANT keys |
| `fx.practical(loc)` | warm lantern/window bulb for night | |
| `fx.sign("FAKE!", loc, rot, size, t_pop=)` | in-world title card / scoreboard | board + black edge + pop with 15 % overshoot |
| countdown timer | overlay graphic, see captions | `videos/<slug>/timers.json` |
Compositor effects register on `look.PRE_COMP` / `look.EXTRA_COMP`; shotkit clears them each shot.

## 4. Pacing (`python tools/pacing.py <slug> [--json]`, exit 1 on FAIL)
FAIL: avg shot outside 1.3-2.2 s, any shot > 3.3 s without `[hold]`, holds > 4.5 s or > 3, > 10 % shots under 0.6 s,
a shot with > 12 words, shot count outside 40-55 for 75-95 s videos (else ~28-40/min).
FIX (soft): avg outside 1.5-1.9, > 9 words/shot, < 60 % cuts on phrases, prop close-ups outside 18-38 %, < 5 shot types,
> 15 % back-to-back same type, wpm/opening/gaps. Prints a length histogram vs REF1 (11/32/26/21/11 %).
Plan an 85 s video as ~48 shots: ~13 inserts, ~13 faces, 6 aerials, 6 low, 3 top/graphic, rest moves/OTS.

## 5. Captions (`python tools/captions2.py <slug>`, run by finish.py)
2-3 words (3rd word only if the group stays <= 16 chars), ALL CAPS Poppins ExtraBold (or Montserrat-Black if added),
white, black stroke 9 %, soft shadow, ONE key word #FFD21E, centred at 67 % height (clamped 62-72 %), max width 900/1080,
3-frame pop. `config.json caption_v2.theme = "brand"` switches key words to neon purple #B46BFF / blue #26D9FF.
Key words from `emphasis.txt`. Timers: `timers.json` `[{"t0":131.5,"t1":139,"from":"8:31","to":"8:36"}]` -> big white
digits, red outline + glow at 15 % height. Preview without a video: `python tools/captions2.py --demo <outdir> [bg.png]`.

## 6. Testing
`blender -b --factory-startup -P camfx_test.py -- <engine_dir> <outdir> [all|ground_low,whip,...] [pct] [samples]`
(copy at `~/RobloxStories/research/camfx_tests/camfx_test.py`). One still per recipe, ~0.3 s each at 30 %/8 samples.

## Fix round 2026-11-14: transitions + caption placement
- `fx.flash(t, fin=7, hold=4, fout=10, bloom=1.4, exposure=1.2, white=0.55)`: values clamped to REF1 (in <= 8, hold <= 6,
  out <= 12 f); eased curve (slow start, fast arrival, 45 % step at 30 % of the tail); white mix peaks at 0.55, not 1.0, so it
  reads as a bloom, not a flat white card. Sound cued at the peak. (Old: full white mix + exposure +2 smeared ~1/3 of a shot.)
- `fx.push_through(..., frames=6)`: card 2.15x frame half-width, QUAD ease-in into cover (full cover only on the last frame of shot A), "out" half keyed one frame early with ease-out (first frame of B already ~30 % open). Measured on test_seq s07->s08: 1 fully black frame, 2 frames >= 50 % dark in total (was 5).
- `fx.whip(cam_a, t1, cam_b, t0)`: matched pair, ONE `fx.WHIP` setting (75 deg, 5 f, shutter 1.0) for both halves.
- Captions (`tools/captions2.py`): per-shot y. `videos/<slug>/captions.json` = `{"5": "top", "default": "mid"}` or
  `[{"shot": 5, "pos": 0.64}, {"t": 7.4, "pos": "top"}]`; names top 0.20 / high 0.62 / mid 0.67 / low 0.72. Fallback from
  the shot description in shots.py: MCU/CU/two-shot/OTS/MS/LOW/full -> top third; INSERT/MACRO/ECU -> 0.62; AERIAL/WIDE -> 0.67.
  The shot holding the middle of a group decides. Yellow only on emphasis.txt words (earlier line = higher priority),
  max ~1 group in 3, never two in a row. Orphan one-word groups inside a clause are merged / re-split.

## Round 3 (2026-11-14): transition sounds are tagged at the source
- `fx.whip_out` (and `fx.whip`), `fx.flash` (A-side only), `fx.push_through(mode="in")`, `cams.whip_pan`,
  `cams.crash_zoom` and the window fly-through register their sound cue with `cut: true`, a `kind` (whip / flash /
  push) and a `pan` sweep in the direction of the move; tools/mix.py builds the actual sound (see AUDIO.md, Round 3).
  `push_through` used to be silent; `whip_pan` cued its whoosh at the START of the whip (now the middle); the fly-through
  cued 0.1 s early (now on the pass). Re-run `render.py <slug> cues` after changing a transition.
- `fx.flash` no longer falls back to the pack "sparkle" (a glockenspiel chime) - it cues "flash" and mix.py designs it.

## Round 4 (R3-1/R3-3): flash cut
- `fx.flash_cut(t0)` (or `fx.flash(t0, fin=0)` in shot B): frames F(t0), F(t0)+1 pure white (mix 1.0 + exposure +6 EV, AgX
  clips to 255), then a 4-frame decay (mix .72/.42/.18/.05). Sound cue "flash" at `fx.cut_time(t0)` = the exact first frame.
- The A-side call `fx.flash(t1 - x, fout=0)` is a no-op now: shot A ends on clean picture. In-shot pops keep the eased
  in/out but hold a FULL white peak (white=1.0, >= 2 frames).
- captions2 `snap_to_cuts`: no caption onset in the last 6 frames of a shot (moved onto the cut), never on the 2 white frames.
