# @rblxanimates permanent cast (Blox Town) — v3 "finished" designs

Code: `rbx/cast.py`. Status: **v3 APPROVED (2026-11-14)**; review renders in `videos/rblx_cast_v3/`
(look-dev script `videos/rblx_cast_v3/lookdev.py`). The approved v2 renders stay in `videos/rblx_cast/` until the user signs off.
Built to `docs/REF2_CHARACTERS_WORLD.md` (proportions §2, faces §3, hair §4).

```python
from rbx import cast
n = cast.host(t0, t1, "smug", loc=(0, 0, 0), rot=0)    # every function: (t0, t1, expr, name, loc, rot, scale, rim, prop, live)
gm = cast.grandma(t0, t1, gamer=True)                   # the twist look
ch = cast.make("dad", t0, t1, "grin")                   # by role; cast.ALL, cast.NAMES, cast.PALETTE, cast.SHEET_EXPR
ch.prop  # hand-prop root or None;  ch.sig = signature hex;  ch.hair / ch.hair_long (Luna);  bestie: ch.board
cast.hand(ch, "armR")                                   # cached fist empty (prop parent), same object every call
cast.hop(ch, t), cast.walk2(ch, t0, t1, p0, p1), cast.react(ch, t, "shock", "shock"), cast.squash(ch, t, amt)
```
`round_head=` is still accepted (ignored). `rim=True` adds a soft NEUTRAL cool rim (`#cfe2ff`); no character has emissive/neon parts.

## Construction (all 8)
- R6 `chars.Char` rig; head swapped for a bevelled cube 1.2 x 1.14 x 1.14 (bevel 0.22, 5 seg) — same head for everyone (Luna 1.06 wider).
- Faces: layered atlases `assets/faces/v3_<role>_eyes.png / _mouth.png` from `tools/make_cast_v3_faces.py` (same 4x4 cells as
  every face, so face/blink/talk/motion work; all EYE/MOUTH names exist incl. side_l/side_r/down/closed/wide, o/wavy).
  Expression set: neutral, happy, sad, shock (white-circle eyes), angry (V brows + teeth bar), smirk, scream (mouth ~40% of face),
  cry (tear streams); Luna adds beam/shy/pout with anime eyes (crimson iris, 2 catchlights, lash flicks, blush hatch).
- Hair: `cast.Hair` = closed boxy scalp shell (tucked under the hairline) + petal clumps + balls -> voxel remesh (0.02) + smooth,
  applied at build time (static mesh, no render-time modifiers). One material per hair: AO root darkening + one shine band
  (Dad: grey temples + 2 streaks by shader mask). Luna's long part is a second mass on a damped sway empty under the neck.

| Role | Name | Hair | Outfit / signature 3D accessory | Fn |
|---|---|---|---|---|
| Host | **Harry**, 16 | chestnut swoop quiff (5 flames + crown) | maroon varsity `#6e1b26`, cream sleeves, 3D chenille H patch, snaps, jeans | `host` |
| Best friend | **Tyler**, 16 | honey-brown spiky crop | navy hooded zip jacket `#1f2f5c`, 3D drawstrings, grey jeans, maple skateboard | `bestie` |
| Crush | **Luna**, 16 | long dark-crimson `#5e0f1c`: blunt fringe, side curtains, back slab to waist | anime face, denim jacket, white shirt, 3D black tie, pleated skirt, boots, hair clip | `crush` |
| Mayor | **Mayor Bigsby**, 58 | silver slick sides + sculpted white handlebar moustache | top hat w/ gold band, navy tailcoat, red sash, gold medal + watch chain, gold scissors | `mayor` |
| Mom | **Rosa**, 42 (skin `#b07a52`) | espresso side-part bob w/ flipped ends, coral headband | teal cardigan, cream top, coffee mug | `mom` |
| Dad | **Rick**, 48 (skin `#b07a52`, = Mom) | black slick-back, grey temples + streaks | red/black buffalo-check flannel, charcoal grill apron, khakis, spatula | `dad` |
| Grandpa | **Otto**, 78 | bald, white side puffs, sculpted walrus moustache | 3D round glasses, green sweater vest, 3D red bow tie, cane, hunch | `grandpa` |
| Grandma | **Pearl**, 74 | silver swept fringe + high bun w/ wooden needle | 3D rose cat-eye glasses, 3D pearls, lavender cardigan, rose dress, knitting; `gamer=True` headset | `grandma` |

## Personalities, catchphrases
- **Harry**: confident, warm, breaks the fourth wall, awkward around Luna. "Plot twist!"
- **Mayor Bigsby**: pompous showman who cuts a ribbon on everything. "I hereby declare this... OPEN!"
- **Tyler**: friendly fearless skater, every stunt fails. "Watch this!"
- **Luna**: cool, kind, a bit mysterious; always one step ahead. "Hi, Harry."
- **Mom (Rosa)**: runs the house on coffee and zero excuses; never touch the mug. "Five minutes. I'm counting."
- **Dad (Rick)**: grills every Sunday, burns everything, pun machine. "It's not burnt, it's crispy."
- **Grandpa Otto**: has a story for everything, falls asleep halfway. "Back in my day..."
- **Grandma Pearl**: sweet quiet knitter... secretly the world's #1 ranked gamer. "Gg, sweetie."

## Relationships
Harry and Tyler are best friends. Harry has a crush on Luna. Rosa and Rick are Harry's parents; Otto and Pearl are Harry's
grandparents (Rick's parents). Mayor Bigsby runs Blox Town. Running jokes: ribbons, Tyler's fails, Mom's mug, Dad's fires,
Grandpa's naps, Grandma's secret gaming.

## Two render styles (same designs, same rigs)
| Style | Call | Use for |
|---|---|---|
| **Animation** (default) | `cast.make(role, t0, t1, ...)` / `cast.host(...)` | craftee-style (REF2) animation: flat clean plastic, ink faces, fast to render |
| **Cinematic 3D** | `cast.make(role, t0, t1, ..., cine=True)` or `cast.cine(ch)` (= `cine_finish`) + `cast.cine_light(focus, cam_loc)` | REF1-style cinema shots: close-ups 50-85 mm at f/1.8-2.8, low angles 18-24 mm, hero mediums |

Cinematic mode only changes the finish, on cached `<mat>__cine` copies (animation-mode characters in the same scene stay flat):
head rounded (bevel 0.34 x 8 + Cast-to-sphere 0.16, so the face plane has real shading falloff; decals/expressions unchanged),
torso/limbs/sleeves/panels bevel 0.24 x 8, thicker extruded accessories (tie, patch, bow, collar points x1.8 depth), skin
subsurface + coat, face decal emboss + skin micro-normal, fabric weave + sheen, plastic/leather clearcoat, hair strand-normal +
anisotropic + coat. `cast.cine_light(focus, cam_loc, scale=1, receivers=[chars])`: warm key ~6:1 over cool fill, tight cool
rim, subtle top light, warm bounce; with `receivers` the key/rim/top/bounce are LIGHT-LINKED to the characters only (no light
wedges on walls/ceilings) — always pass it. scale ~1 MCU/medium, 1.6-2 wides.
Review: `videos/rblx_cast/compare_{close,low,med}.jpg` (left animation, right cinematic), `lineup_cine_{a,b}.png`.
Not done: eye-catchlight parallax (catchlights are in the decal), per-shot AO tuning (relies on EEVEE ray-traced GI/AO).

## v3.1 rig + hair notes (2026-11-14)
- All 8 cast members: elbow + knee joints (`ch.joints`), default `stand` key pose with weight shift (see ACTING.md).
  `cast.hand(ch, arm)` / `motion.hand` now hang off the elbow (props follow the forearm).
- Mom's bob rebuilt: deep side part with a big sweep + small counter-sweep fringe, 3 layered clumps per side and 3 at
  the back with staggered, out-flicking tips, stronger shine band (0.26) - no smooth side balls (they read as a helmet).
- Lighting: `cast.light_rig(chars, cam, look)` (auto in shotkit); per-character neutral rim from `_finish` unchanged.

## Identity check (R3)
Mom (Rosa) = espresso bob + CORAL headband; Luna = long dark-crimson hair + black tie + anime eyes. A dark-haired character
with a red band is Mom, not Luna. Only `cast.crush` builds Luna; there is one v3 design.
