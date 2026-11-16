# REF 5 entity bible: cats, monsters, creatures (2026-11-13)

Source: REF 5 https://www.youtube.com/shorts/E9TTaFj-YXU (cat "Mittens" + "the yawning man"). Notes:
`~/RobloxStories/research/refs/ref5/`. CAVEAT: the video could not be downloaded (403), so the design numbers below are our
recipe built from the script's shot-by-shot demands and the Roblox-animation genre, not measured from its frames. Verify against
frames when the mp4 is available. All designs here are original; do not copy the ref's models.

## 1. Principles from REF 5
- Cute -> uncanny -> hero arc for the pet: the SAME model is cute on a low warm camera and menacing on a high-angle unblinking
  stare. Menace comes from stillness, eye shine and proximity, not from changing the model.
- The monster is revealed by parts across ~12 s (fog -> fingers -> head tilt -> smile -> yawn). Each part gets its own shot.
- One impossible action defines the monster (yawn wider than its face). Build the rig around that action.
- Scale contrast in the climax: tiny cat in hiss pose vs giant mouth, both in one frame.
- Stylised Roblox-adjacent shapes (blocky/bevelled), but with smooth shading, rim light and real-feeling motion.

## 2. Cat recipe (quadruped, Roblox-styled)
Proportions (cat ~0.55 of R6 kid height at shoulder 0.28 m when kid = 1.0 scale):
- Body: bevelled box 0.42 x 0.20 x 0.18 m (L x W x H), bevel 0.06, 2 subdiv levels; chest 10 % wider than hips.
- Head: rounded box 0.17 x 0.16 x 0.14, big for cuteness (head:body length 0.4). Ears: 2 tapered cones/pyramids 0.06 tall, rotate 10 deg out.
- Eyes: 2 inset spheres 0.035, black glossy sclera-less pupil disc that can scale (round = cute, slit Y-scale 0.25 = menace);
  emission 0-2 for eye shine (tapetum glow, green-gold `#c8ff6a` or amber `#ffb52e`).
- Legs: 4 cylinders r 0.025, 2 segments each (upper 0.09, lower 0.09), paws = squashed spheres.
- Tail: curve with 6-8 bones, bevel taper 0.022 -> 0.008, length 0.32.
Materials: base fur colour principled, roughness 0.75, sheen 0.6 (fake fur), subtle noise bump 0.05; optional fur shell
(Geometry Nodes or hair curves, length 6-12 mm, density 3000/m2; scale length x2.2 for "every hair standing up").
Rig (armature, ~24 bones): root, hips, spine1-3, neck, head, jaw, ear.L/R, tail1-7, per leg: upper, lower, paw (IK on paw
with pole), eyelid.L/R (blink), pupil scale driven by a custom prop `menace` 0-1 (also drives ear flatten -40 deg and fur length).
Cycles at 24 fps:
- Walk: 24 frames, diagonal pairs (LF+RH, RF+LH) offset 12 f; head stabilised (counter-bob), tail S-curve wave period 48 f.
- Trot: 16 f; gallop/run (hero dash): 10-12 f, spine flex +-12 deg, both front then both hind, 2-frame flight phase.
- Pounce: crouch 8 f (butt wiggle 3 x 4 f), hold 4 f, launch 4 f, arc 8-10 f, land squash 3 f.
- Stare: no blinks for 3+ s, pupils slow-dilate over 48 f, head micro-tilt 3 deg, tail tip flick every 30-40 f only.
- Hiss: back arch +25 deg spine, side-on stance, ears flat, jaw open 35 deg, fur x2, 2-frame pre-tremor.
- Loaf/sleep on chest: legs tucked, breathing scale 1.0-1.03 at 70 f period.
Framing: cute = camera at cat eye height, 50 mm, warm key, tail visible. Menace = high angle from the kid's pillow POV,
35 mm, cat face 50 % of frame, eye shine only light source detail. Hero = low tracking, 24 mm, rim light strong.
Shot lengths: cute inserts 1.5-2 s; stares 2.5-3.5 s (hold is the scare); hero dash 1-1.5 s cuts.

## 3. Tall monster recipe (humanoid, wrong proportions)
- Height 2.4-3.0x the kid; limbs 1.5x human ratio, torso narrow (0.6x), head small or tilted; fingers 2-3x long (finger
  length ~ palm x 2), 3 joints each, rigged so they can lie flat on glass/floor.
- Skin: grey `#8d8f94` -> `#5d6066`, roughness 0.55, subsurface 0.05 (pale, slightly translucent), a darker crease AO; no
  saturated colours. Eyes: small, pale or absent; the money feature is the MOUTH.
- Rig: standard biped (~40 bones) + extra: finger chains 3 bones x 5 x 2, neck 3 bones (for 40-60 deg sideways tilt),
  jaw with a shape key "unhinge" (mouth height x3, corners pulled up/out), spine 4 bones for sway.
- Motion: stalk = 40-48 f stride, long holds (12-20 f still) between moves; lurch = sudden 3-4 f move after a hold;
  head tilt = 16 f ease-in, overshoot 4 deg; yawn = 36 f open (slow), 12 f hold, 6 f snap shut. Never idle-breath like a human:
  either perfectly still or wrong-rhythm motion.
- Lighting: backlit/rim only (moon behind), face lit from below or by the window glow; 70 % of frame in shadow.

## 4. Generic creature checklist
1. One silhouette idea readable as a black shape (test: render with emission-black material on grey).
2. One impossible action + a rig control for it.
3. One callback detail (missing fingernail, torn ear, white feather).
4. Eyes: shine control + pupil scale.
5. Motion rule: still-then-fast for threats; bouncy overlap for allies.
6. Reveal plan: 3-5 parts, each a shot; full body only once.

## 5. Original entity concepts (design specs)
1. **Pocket (cat ally)**: soot-black shorthair, one white sock (callback), copper eyes. Rule: purrs only next to someone the
   house is about to swallow. Signature: purr vibrates objects. Hero action: hiss that cracks mirrors.
2. **The Lender (shadow figure)**: flat 2D shadow that lives on walls, borrows one thing each night (a shoe, a tooth, a name).
   Built as an emission-negative decal on a wall plane with an armature; casts no light; only seen when the lamp flickers.
3. **Tallman Tom (tall monster)**: 3.0x height, coat to the floor, no feet visible, slides instead of walking; head always
   tilted 50 deg. Impossible action: neck extends 1 m to look into second-floor windows.
4. **Wren (ghost child)**: R6 kid scale 0.85, desaturated, frame-skipping motion (holds 2 frames, jumps 3), wet hair, always
   facing away until the reveal. Alpha 0.85, cold rim, no shadow. Ally twist possible.
5. **The Hushers (swarm)**: palm-sized moth-like things, 200 instances via GN, cover lamps to make dark. Sound: soft paper
   fluttering. Threat = scale and darkness.
6. **Grandma Clock (object entity)**: grandfather clock that steps one tile when nobody looks; pendulum = heartbeat; face cracks
   into a smile. Rig: 2 hidden legs, pendulum bone, face shape keys.
7. **The Drain Dog (quadruped monster)**: hairless grey hound, legs 1.6x too long, too many knees (3 segments), walks on
   ceilings; jaw splits sideways. Uses the cat rig scaled with an extra leg segment.
8. **Mr. Smiles (mascot)**: friendly school mascot costume, head too big, mouth fixed, eyes track the camera. Menace comes from
   it moving only between cuts (position changes between shots, never on screen).

## 6. Gaps for the kit
- No quadruped rig or cat in `rbx/cast.py` / `chars.py` (all R6 biped). Need `rbx/creatures.py`: cat(), hound(), tall(), ghost().
- No fur shell or eye-shine material helper; no pupil-scale/menace driver.
- No shape-key jaw "unhinge" or long-finger chains.
- No walk/trot/gallop/pounce cycle generator for quadrupeds.
- Cameras: need POV-from-bed, floor-gap tilt-up and scale-contrast two-shot recipes in `cams.py`.
- Frames from REF 5 still need to be studied for exact proportions (download blocked).
