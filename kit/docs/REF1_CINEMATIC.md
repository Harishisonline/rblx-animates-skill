# REF1 production bible: "You went back in time to save her..." (youtube.com/shorts/npdxivww0Xk)

The user's #1 quality target. Source: 2160x3840 (4K vertical), 30 fps, 155.2 s, -13.3 LUFS integrated, no silence gaps
(narration + music bed run wall to wall). Measured from a 270x480 proxy: scene-detect cuts (threshold 0.25), 2 fps and
6 fps contact sheets. Sheets + `cutlist.json` live in `~/RobloxStories/research/refs/ref1/`. Do NOT copy its characters or
frames; recreate the style with our own cast and sets.

## 1. Measured numbers (the headline)
| Metric | Value |
|---|---|
| Shots | 92 hard cuts in 155 s (plus ~6 in-shot whips/dissolves) |
| Mean / median shot | 1.69 s / 1.59 s (= 51 / 48 frames @30) |
| Shortest / longest | 0.63 s / 3.30 s. Nothing over 3.3 s, ever |
| Distribution | <1.0 s: 11% . 1.0-1.5 s: 32% . 1.5-2.0 s: 26% . 2.0-2.5 s: 21% . 2.5-3.3 s: 11% |
| Cut motivation | ~90% cut on a narration phrase boundary (2-4 words per shot); new noun in VO = new picture of that noun |
| Shot mix (approx) | inserts/macro props 28%, MCU/CU faces 27%, aerial/drone wides 15%, low-angle MS 15%, top-down 8%, 2D map/graphic 3%, white flash/VFX 4% |
| Luma (BT.601 8-bit, mean over film) | YAVG 91, YLOW (10th pct) 43, YHIGH (90th pct) 151: mid-key, never crushed, no clipped whites except flash beats |
| Saturation (signalstats SATAVG) | 20.5 (moderate; colour comes from saturated *props*, not a global sat boost) |
| Audio | -13.3 LUFS, continuous; music ducked under VO; SFX on every cut-to-action (whoosh, siren, impact) |

## 2. Shot-by-shot (condensed; full list with timestamps in cutlist.json)
| # | t (s) | dur | Shot | Camera |
|---|---|---|---|---|
| 1 | 0.00 | 2.6 | Hooded boy wakes, glow swirl, turns to camera | MCU 35mm, slight low, push-in ~8%/s, head turn leads |
| 2 | 2.60 | 1.6 | Girl in bed screams | MCU eye level, push 10%/s |
| 3 | 4.17 | 1.1 | Boy grins | MCU over blanket FG |
| 4 | 5.30 | 2.1 | Memorial wall of names, flowers/candles FG | low 24mm, lateral truck L->R ~6% frame/s, f/2.8 feel DOF |
| 5-7 | 7.4-10.9 | 1.0-1.5 | SEPIA flashback: overhead crib + confetti; low-angle cheer pyramid collapses | overhead slow rotate; low 24mm + whip blur |
| 8-9 | 10.9-15.1 | 2.1 | Aerial city -> crash into window to boy | drone 20mm, push ~25%/s, motion blur on whip-in |
| 10 | 15.1 | 0.9 | Kimi (girl) MCU smiles | 50mm, eye level, static+breath |
| 11 | 16.0 | 1.2 | Aerial lake town establish | 24mm drone, slow descend |
| 12-13 | 17-21 | 1.8-2.4 | Inserts: cereal bowl macro, arm with red cord + marker text | macro 70-90mm, rack focus, slow push |
| 14-16 | 21-26 | 1-2 | Field / panorama / girl waving in lake | crane rise; water-level 35mm |
| 17 | 26.0 | 2.0 | Calendar + hand points | macro push |
| 18-19 | 28-31.7 | 1.5-2.2 | Falling star streak over aerial lake -> white flash | VFX trail, night grade, flash 6-8 frames |
| 20-21 | 31.7-34.7 | 0.8-2.2 | Soccer goal + cheering team | low tracking 24mm, heavy motion blur |
| 22 | 34.7 | 2.4 | Top-down bedroom cleaning | overhead 24mm, props pop in |
| 23 | 37.1 | 1.0 | Classroom boy holds "A" paper | MCU |
| 24-26 | 38-43.6 | 1.3-2.7 | Mirror shot; red-cord wrist macro; blush CU | OTS mirror; macro |
| 27 | 43.6 | 1.5 | Warm train interior, boy crying | high wide, golden backlight |
| 28-29 | 45-48.9 | 1.6-2.2 | Red cord bow tied; girl sad ECU with tear | macro 85mm static; ECU |
| 30-31 | 48.9-52.8 | 1.7-2.3 | Calendar push to circled "12" | macro push ~10%/s, rack |
| 32-33 | 52.8-55.4 | 1.3 | Night star party (beach) | high wide, then MS |
| 34-35 | 55.4-58.9 | 1-2.5 | Phone "ONE STAR DIDN'T BURN UP"; boy shocked huge eyes | OTS insert, city bokeh BG; CU blue low key |
| 36-38 | 58.9-64.5 | 1.3-2.5 | Pastel bedroom wake, girl writes on arm, text insert | low 24mm push; macro pan |
| 39-40 | 64.5-68.6 | 1-2.6 | Two days later wide; wrist note "NOBODY LISTENS..." | wide 28mm push; macro |
| 41 | 68.7 | 1.6 | 2D map, train route line draws | flat motion graphic, slow push |
| 42-44 | 70-74.8 | 1.2-1.7 | Train interior; train exterior low sunset | MCU; low 20mm |
| 45-46 | 74.8-78 | 0.9-2.3 | Aerial: crater lake, push down into circle | drone 18mm dive |
| 47-50 | 78-82 | 1-1.3 | Memorial wall again, names ECU, wrist enters | 50mm macro |
| 51-53 | 82-86 | 1-1.6 | Girl runs main street | low handheld follow 24mm, motion blur |
| 54-57 | 86-91.8 | 1.4-2.3 | Fire station: truck low, siren sign + red lever, chief laughs | 20mm low; push ECU; CU 50mm low |
| 58-60 | 91.8-96.7 | 1.1-2 | Flip red switch (dutch low), siren tower from below, aerial crowd | 18mm extreme low; top-down |
| 61-64 | 96.7-105.8 | 1.2-3 | Crowd snakes up hill; empty beach; dad drags girl; dad CU angry | aerial; static wide; low MS; CU push |
| 65-70 | 105.8-118.7 | 1-3 | Calendar ECU, phone 8:42, boy decides, overhead swap glow beam | macro; high MS; overhead |
| 71-78 | 118.7-131.5 | 0.9-2.2 | Train station bench (ghost dissolve to sepia past), clock dutch whip, train ride | static wide, dissolve 12 f; whip |
| 79-84 | 131.5-139.8 | 1-3.3 | Night: star appears & grows over lake; red "8:31/8:36" timer overlays; doors open, run | wide night 24mm; low MS |
| 85-90 | 139.8-151.9 | 1-2.5 | Festival street lanterns, dad grabs arm, sprint, slam switch "8:40", siren screams, aerial crowd, dad grabs mic | low handheld; dutch; whip-pan aerial; top-down; 20mm low |
| 91-92 (+ in-shot) | 151.9-155.2 | | 8:42 impact, screen -> white, tsunami ring; wake in own bed, phone "NOBODY HURT", crying girl ECU end | wide; white flash 10-15 f; CU |
(Rows 71-92 are approximate groupings; from the 2 fps sheets: white flash ~137-138 s, aftermath/wake-up ~140-152 s, crying-girl ECU button ~152-155 s.)

## 3. RULES and numeric recipes

### 3.1 Editing / pacing
1. Shot length target: mean 48 frames, sd 15; clamp 19-99 frames. Hook shot 60-78 frames. Draw lengths from the distribution in sec. 1.
2. Cut on VO phrase boundaries; every concrete noun in the script gets its own picture (calendar, cord, phone, switch, siren, map).
3. Ratio per 10 shots: 3 inserts, 3 faces, 1-2 aerial/wide, 1-2 low-angle MS, 0-1 top-down/graphic.
4. Repeated motifs (calendar countdown x5, wrist cord x5, memorial wall x2, phone news x3) use the SAME framing each time
   with a 1-element change (cross-off, new text). This is the storytelling spine; plan 2-3 motifs per video.
5. Transitions: 95% hard cuts. Specials: white flash (6-8 f in, 4-6 f hold, 8-12 f out) for time travel/impact; whip with
   12-20 f motion-blurred camera rotation; cross-dissolve 10-14 f only for "same place, past" ghost.
6. Flashbacks: whole shot graded sepia (see 3.4) not a separate filter overlay.

### 3.2 Camera (Blender, sensor 36mm, 9:16 render 1080x1920 min, ideally 2160x3840)
| Recipe | Lens | Height / angle | Move | Speed |
|---|---|---|---|---|
| Face MCU | 40-50mm | lens at chin height, 5-10 deg up-tilt (slightly low) | push-in | 6-10% of distance per s, ease-in-out |
| Emotional ECU (tear, shock) | 65-85mm | eye level | static + 0.3 deg breathing drift | — |
| Insert / macro prop | 70-100mm, f/1.8-2.8 | 25-45 cm above, 30-60 deg down | slow push or rack | 5-10%/s; rack 12-18 f |
| Low hero / authority (chief, siren) | 18-24mm | 30-60 cm above ground, 20-35 deg up-tilt | push or none | 5%/s |
| Aerial establish | 18-24mm | 40-120 m high, 25-60 deg down | forward glide or descend | 8-25% frame/s; whip-ins use 1.5-2x |
| Top-down | 24-28mm | straight down | slow yaw 3-6 deg/s or push | |
| Run follow | 20-24mm | 40-80 cm above ground, low behind/front | handheld follow | shake amp 0.5-1.0 deg, 2-4 Hz |
| Dutch beat (switch slam, clock) | 20-28mm | low | roll 12-20 deg | 1-shot only |
| Lateral truck (memorial wall) | 24-35mm | low 0.4-0.8 m | truck parallel to wall | ~6% frame width/s, FG flowers out of focus |
- Camera ALWAYS moves (no locked-off shot except ECU emotion and calendar holds). Every move is ease-in-out over the full shot.
- DOF on: f/2.0-2.8 on faces & inserts (background clearly soft), f/5.6-8 on aerials. Focus on eyes.
- Motion blur ON for whips/runs/aerial whip-ins: shutter 0.5 (180 deg). This is a major "cinematic" cue we lack.
- Subjects big: faces fill 35-55% of frame height in MCU; captions sit over chest at 60-75% height.

### 3.3 Lighting rig (EEVEE/Cycles values)
- Day exterior: Sun 4-5 W/m2, colour #FFE9C8 (~5200K), elevation 25-40 deg, angle 1.5 deg (crisp shadows); sky HDRI/Nishita strength
  1.0; strong shadow side kept at ~35% of lit side (YLOW 43 vs YHIGH 151 => ~3.5:1 contrast).
- Interior bedroom: big window key (area 4x3 m, 400-800 W, #FFF1DC) from the side, cool bounce fill #9FC4E8 at 15%,
  teal wall #2E8C8C, skyline out window over-exposed +1.5 EV.
- Golden/flashback: sun 8-10 deg elevation #FFB45A, backlight, volumetric haze density 0.01-0.02, sepia grade.
- Night: moon key #8FA8FF 0.3-0.5 W, practical warm points (lanterns #FF9A5A emissive 8-15, windows #FFC878 emissive 3-5),
  sky gradient #10182E -> #2B3F70, star streak emissive 50+ with bloom. Faces get a small warm fill point (25-50 W) at 1 m.
- Rim: cool rim from behind on faces (#BFD8FF, 1.5-2x key on silhouette edge) in every MCU.
- Atmosphere: aerials always have distance haze (mist pass or volume 0.002-0.004) turning far mountains to #8FA6B5.

### 3.4 Grade (compositor)
- Default: contrast +10%, sat 1.05-1.10, lift shadows toward teal (#1E2A30 at 10%), gain highlights warm (#FFF0D8).
- Bloom: threshold 0.9, intensity 0.05-0.1 (lights/screens only; star streak bloom 0.3).
- Vignette: soft, 15-20% darkening at corners.
- Sepia flashback: desaturate 85%, multiply #C9A564, contrast +15%, add floating dust/confetti specks.
- Night: white balance 6500->cooler, sat 0.95, keep faces at Y>=70.
- Siren flicker: red emissive 0<->20 at 4 Hz with red point light 200 W.

### 3.5 Characters
- Classic blocky Roblox proportions: cube head ~1.0, torso 2x2x1, limbs 1x2x1; bevel 0.05-0.08 on everything.
- FACE is the star: large 2D decal faces with anime eyes (iris + 2 highlights, lashes, blush ovals, brows that move),
  mouths that open wide (scream = 40% of face). Separate face decals for: smile, grin, scream, shock (eyes become white circles),
  cry (tear decals, wobbly mouth), angry (V brows), eyes-closed. Swap expressions on cut, not mid-shot (except blinks).
- Hair: chunky but CLEAN silhouette, 4-8 large smooth clumps, glossy toon spec, no strand noise; accessory (sunflower clip,
  star clip). Hoodie drawstrings, aglets, red cord bracelet = small readable detail.
- Materials: cloth roughness 0.6-0.8 with subtle printed patterns (stars on blanket, polka dots), skin #D99A6C / #C47A4E,
  plastic sheen spec 0.3.

### 3.6 Acting (frames @30)
- Anticipation 3-5 f before every big move; overshoot 10-15% then settle 4-6 f.
- Head leads body by 2-3 f; eyes lead head by 2 f on looks.
- Shock: 2 f hold, 4 f snap back (head + shoulders up 8 cm), eyes pop to circles on frame of snap.
- Run cycle: 12 f per stride (2.5 strides/s), arms pump +/-60 deg, body lean 10-15 deg, 2-3 cm bob.
- Cry: shoulder shudder 3 Hz amp 2 deg, tear drop decal slides over 20 f.
- Laugh (chief): head tilt back 15 deg, torso bounce 4 Hz, eyes closed arcs.
- Every character always has idle breath (chest scale 1.00-1.02 over 75 f) and blinks every 2-4 s.

### 3.7 Environment
- Real-world scale towns with HIGH prop density: festival streets with string lanterns, awnings, flower boxes, 2000-extra
  crowd instancing (beach mats, glow sticks), fire station with truck, siren tower, memorial wall with hundreds of engraved names.
- Terrain: aerial lake with forested mountains, sand beach, piers. Water: glossy, blue #1B5E9C deep -> #3FB7D6 shallow.
- In-world text props are crisp and legible (calendar, phone UI, signs, handwriting on skin): treat text as story props.
- 2D flat map motion graphic (drawn route, toy train) used as a "plan" beat.

### 3.8 Captions / overlays
- 2-3 words at a time, centre, at ~62-72% frame height, heavy rounded sans (Montserrat/Lilita-like ExtraBold), white with
  ~8% black stroke + soft shadow, KEY word yellow #FFD21E. Word timing exact to VO.
- Countdown timers ("8:31", "8:40", "8:42") big white with red outline at top 12-18% for ticking-clock act.

### 3.9 Audio
- Narration 2nd person present tense, ~3.2-3.6 words/s, no pauses > 0.3 s. Music: soft emotional piano/strings in act 1,
  ticking pulse + risers in act 3, drop to near-silence before the white flash then swell. SFX on every action (whoosh on whips,
  siren loop, crowd walla, impact boom + high ring on flash). Master -13 to -14 LUFS.

### 3.10 Story structure
Hook (0-5 s: weird premise in 1 line) -> rules + stakes (5-30 s) -> attempts with countdown motif (30-120 s, each attempt fails)
-> final run with on-screen clock (120-150 s) -> white flash -> quiet twist/emotional button (last 10 s).

## 4. Gap list vs our kit (what to add, by owner module)
| Gap | Module | Exactly what to add |
|---|---|---|
| Shot length too long / no distribution | story.py / pacing | Enforce mean 48 f, clamp 19-99 f; one shot per VO phrase; checker fails >3.3 s shots |
| Motion blur | look.py | `look.motion_blur(shutter=0.5)` per-shot toggle; default on for whip/run/aerial recipes |
| Low/ground lenses (18-20mm) and up-tilt | cams.py | `ground_low(t0,t1,target,lens=18,h=0.4,tilt=30)`; current hero_low 28mm is too tame |
| Aerial drone recipes | cams.py | `aerial_glide(h=40-120m, pitch=-35, speed=0.15/s)`, `aerial_dive`, `whip_in_window` (aerial -> interior with blur) |
| Lateral truck recipe | cams.py | `truck(t0,t1,p0,p1,aim_offset)` parallel move with FG object |
| Rack focus | cams.py | `rack(t, from_obj, to_obj, frames=15)` |
| Always-moving cam | cams.py | default push 6-10%/s on every recipe; `_drift` amplitude + 0.3 deg micro-noise |
| White flash / dissolve / sepia transitions | fx.py + look.py | compositor `flash(t, in=7,hold=5,out=10)`, `dissolve(12 f)`, `look.grade("sepia")` preset with dust specks |
| Countdown timer overlay | fx.py / captions | timer text (white, red stroke) top 15% |
| Caption style | captions tool | 2-3 word chunks, yellow key word #FFD21E, y=0.67 |
| Expressive 2D face set | acting.py / cast.py | anime eyes with highlights, blush, tear decals, white-circle shock eyes, wide scream mouths; brow layer |
| Clean clumped hair | cast.py | 4-8 smooth beveled/subsurf clumps + clip accessory; no strand noise; toon spec |
| Acting timing presets | acting.py | anticipation/overshoot helper (`act(..., antic=4, over=0.12, settle=5)`), head-before-body offset 2-3 f, run cycle 12 f/stride, laugh/cry/shock presets |
| Night practicals | look.py | `look.rig("night_festival")` lantern strings + window emissives + face fill |
| Siren flicker light | fx.py | animated emissive + point light 4 Hz |
| Text props | props2.py | calendar with day grid and marker circles/crosses, phone with news UI, handwriting-on-skin decal, memorial name wall, flood-siren sign + lever |
| Big environments | locs.py / world2.py | lake-town terrain (lake, beach, forest mountains, haze), festival street, fire station, train + station, crowd instancer (1000-2000 extras with variation) |
| 2D map motion graphic | fx.py | flat map plane + animated dashed route + toy train |
| Shooting star VFX | fx.py | emissive head + trail (curve w/ gradient), bloom 0.3, impact ring + water wall |
| Resolution | render config | render 1080x1920 minimum (ref is 2160x3840); our sharpness must match |
