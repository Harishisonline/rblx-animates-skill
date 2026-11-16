# REF2 — Character & World Bible (study of @craftee_films reels, 2026-11-13)

Private study notes. Study frames live in `~/RobloxStories/research/refs/craftee/` (contact sheets `*_sheet.jpg` = 20 evenly
spaced frames, `*_cuts.jpg` = scene-cut frames, `boards/hair_closeups_board.jpg`). They are NEVER to be used as textures,
models or plates. We copy the *finish level and construction logic*, never a specific design.

## 0. What the account actually is (important)
@craftee_films is a **compilation/repost account**: the 14 reels studied come from at least **6 different production styles**.
Grouping them is the first finding, because "make it look like REF2" must mean the top tier, not the average:

| Tier | Reels (id) | Look | Use as target? |
|---|---|---|---|
| A "Cinematic Unreal-ish" | DfpQxVRsy9l (laugh-detector town), Dfr3KAahSw3 (heist), Dfok_maswDg (bike race), Dfp0J1hh58X (winter) | photoreal-ish PBR world (cobblestone, half-timber, brick, riveted steel), golden-hour / overcast sky with real clouds, DoF, filmic grade; characters are clean R6 blocks + **chunky sculpted hair**, simple ink faces | **YES — primary target** |
| B "Soft clay 3D" | DfqDQaXNSve (ref 3) | pastel, flat-shaded, AO-heavy; big expressive anime face decals; glossy sculpted hair clumps; soft sunset/dusk light | YES for faces + hair |
| C "Bright Roblox Studio" | Dfo7DfbhDGD (rock), Dfps0jGBa8a (yellow noob) | saturated primaries, cartoon eyes, knit textures | faces/expressions only |
| D "In-engine Roblox capture" | DfrPEVQhquX (sand), DfrNwTgxVrq (lab), DfoASJgIz2J (ref 6 sword), 4×35 s shorts | real Roblox avatars + UGC hair, Roblox lighting/bloom | transitions, staging only |

## 1. Top-level rules (why ours read as "AI slop")
1. **Hair = 5-14 big sculpted clumps, not 30-80 thin strands.** Every tier-A/B hair is a handful of thick, smooth, tapering
   "petal/flame" chunks with clean silhouettes. Our `_strand` NURBS locks (radius 0.02-0.06, many of them) read as noodles/fur.
2. **Faces are flat, graphic, high-contrast decals** — pure black ink, 2-4 elements, huge negative space. No gradients, no
   realistic eyes, no small detail. One accent colour max (blush/red mouth interior).
3. **Body is a strict R6 block** with soft-bevelled edges; nothing is organic except hair and accessories.
4. **Finish comes from light, not geometry**: soft AO in creases, warm key + cool fill, gentle spec on plastic, DoF.
5. **Restraint**: one signature item per character (hat, sunglasses, star patch, tie, chain). Clothing = flat colour + one
   print or one material texture (plaid, knit, foil, denim), not five trims.

## 2. Proportion table (measured on tier A/B close-ups, R6; unit = head height H)
| Part | Size (W × H × D) in H | Notes |
|---|---|---|
| Head | 1.0 × 1.0 × 1.0 (a cube) with bevel radius 0.18-0.22 H (tier A) / 0.28 H (tier B "pillow") | tier-B heads slightly wider than tall (1.08 × 1.0) |
| Neck gap | 0.0-0.04 | head sits directly on torso; no visible neck |
| Torso | 1.75 W × 1.75 H × 0.85 D | top edge bevel 0.06 H |
| Arm | 0.85 × 1.75 × 0.85 | hangs flush to torso side, pivot at top 0.15 H down |
| Leg | 0.85 × 1.75 × 0.85 | two legs exactly fill torso width |
| Total height | ≈ 4.5 H (head 22%, torso 39%, legs 39%) | |
| Hair overhang | crown +0.25-0.45 H above head, sides 0.05-0.15 H proud, fringe ends at 0.55-0.65 H from top | |
| Face zone | eyes at 0.45-0.5 H from top, eye spacing 0.35-0.4 W, mouth at 0.72-0.8 H | eyes tall ovals 0.14 W × 0.2 H (simple) |

Kids vs adults: **no height change** in tier A — age is told by hair colour, beard, hats, glasses and posture
(grandpa slight hunch 8-10° forward). Scale variation ≤ ±6%. Keep ours (0.94-1.08).

## 3. Face texture spec (one 1024² atlas cell per expression, same layout as our current atlases)
- Ink: pure `#111111`, line weight 2.2-2.8% of face width, round caps. No outlines around the head.
- **Simple set (tier A default)**: eyes = filled black ovals 7% × 11% of face; or "open" eyes = white ellipse with black outline
  and small black pupil (surprised/derp). Brows = single short arcs (angled 15-25° for anger). Mouth = one curve; open
  mouths filled `#1a0d0d` with optional red tongue `#d8262e` lower 40%.
- **Anime set (tier B — crush/girls)**: eyes 18% × 22%, black iris with 2 white catchlights (big top-right, small bottom-left),
  2-3 lash flicks on the outer corner, lid line heavier (4%). Blush = soft pink ellipse `#ff8aa0` @ 55% alpha with 3 diagonal
  hatch strokes `#e0405a`. Mouth tiny (6-9% wide).
- Expression range seen (build all as cells): neutral, smile, big grin (closed-eye ^ ^ laugh), smug half-lid, angry (V brows +
  gritted teeth bar), shocked (round white eyes + O mouth), sad (droopy brows + frown), worried (sweat drop), deadpan
  (flat line eyes), sleepy, shy-blush, crying (tear streams), dizzy/x-eyes, star-eyes (wonder).
- Decals sit on the front face with 0.02 H inset; material: emission-free, same roughness as skin so the face catches spec.
- Expression changes are **hard cuts** (swap frame), not tweened — matches all reels.

## 4. HAIR — construction recipe (the key fix)
What the reference hair is: **solid, smooth, low-frequency sculpted shells**. Silhouette = big rounded mass + 3-8 pointed
"flame" tips. Edges are perfectly clean (no strand noise, no transparency, no cards). Shine = one broad soft spec band.
Colour = flat base with a slight darker root toward the scalp (AO does most of it). No per-strand colour.

Hair archetypes observed (silhouette only — we design our own):
- **Swoop quiff** (tier A boy): 6-8 tall tapered flames sweeping up and back, rising 0.4 H over the crown.
- **Curly mop** (ref 3 boy, silver): 10-14 short rounded "sausage" curls stacked in 2 rows around crown + fringe.
- **Straight long with blunt fringe** (ref 3 girl): one cap shell + a fringe slab cut into 5-7 points + 2 side curtains to chest.
- **Grandma swept bob**: 3 broad curved slabs swept to one side, soft volume.
- **Bun/puffs**: spheres (r 0.3-0.35 H) on a cap shell.
- **Spiky anime**: 7-9 large flat triangular spikes, fringe points over eyes.
- **Slick-back**: single cap shell with 4-6 shallow grooves (dad/mayor).

### Blender step list (per hairstyle; no particles, no curves-as-strands)
1. **Cap shell**: UV sphere 24×12, scale to (1.06, 1.06, 0.7) H, cut away below the hairline (front at 0.18 H below top,
   sides to ear height 0.45 H, back to 0.85 H). Solidify 0.04 H. This alone must already read as the haircut.
2. **Clumps**: each clump = a cone/"petal" mesh (cylinder 12 verts, 6 loops) — taper tip to 0 with proportional edit, bend
   with Simple Deform (Bend 25-60°), flatten Y to 0.5-0.7. Width at root 0.22-0.35 H, length 0.3-0.7 H. 5-14 per head.
   (A curve with bevel is OK **only** if bevel depth ≥ 0.08 H and converted to mesh; never < 0.05 H radius.)
3. Place clumps radiating from a crown point / part line, overlapping 30-50% so no scalp shows; fringe clumps end above the
   eyes (never cover eyes except deliberate emo/anime fringe).
4. **Join** cap + clumps, add Remesh (Voxel 0.015-0.02 H) → Corrective Smooth / Smooth (factor 0.5, 4 iters) → Subdivision 1.
   This fuses clumps into one clean sculpted mass (exactly the "molded plastic" look). Keep tips sharp by masking or by
   running remesh before adding the tip-most loops.
5. Shade Smooth + Auto Smooth off (it's all smooth). Polycount 3-8k after subdiv.
6. **Material** (Principled): Base = hair colour; Roughness 0.35-0.45; Specular IOR level 0.5; Coat 0.15 roughness 0.3;
   Sheen 0.2 (soft rim). Add a vertex-colour / AO-driven darken: mix base × (0.7 at roots → 1.0 at tips) via Geometry
   Pointiness or an AO node (distance 0.15 H). NO anisotropic strands, NO alpha.
7. Optional single highlight: an Anisotropic-free trick — a second, slightly lighter (+12% value) colour band driven by
   object-space Z gradient (0.6-0.8 H) at 30% mix. Tier B uses this for the "plastic gloss" ring.
8. Secondary motion: parent long hair pieces to a 2-bone sway rig (damped, ≤ 6° swing). Short hair = rigid, parented to head.

## 5. Skin, materials, light
- Skin: Principled, base sRGB from palette, Roughness 0.45, Specular 0.5, Coat 0.1, **Subsurface 0.05** (radius 0.1,0.05,0.03)
  only on tier-B-style close-ups. Palette seen: `#f6d7b8`, `#e9c29a`, `#c99067`, `#8a5a3c`, `#5a3a28`, classic yellow `#f5cd30`.
- Clothing plastic: Roughness 0.55-0.7, no coat; prints as flat decals (plaid, stripes, star). Knit = bump map (scale 40,
  strength 0.15). Denim = noise bump 0.05. Gold/foil = Metallic 1, Rough 0.25 (mayor/rich characters).
- All block edges bevel 0.03-0.06 H, 3 segments — this produces the bright edge highlight that sells "toy finish".
- Lighting (tier A): sun key 3.5-5 strength, 35° elevation, warm `#ffe3c0`; sky/world HDRI-like gradient fill 0.6;
  ambient occlusion ON (Eevee: distance 0.6 m); rim = back sun or area light 300-600 W cool `#cfe2ff` on close-ups.
  Night scenes (heist/winter): blue moonlight `#6a83c9` + warm practicals (lamp posts, windows) + volumetric haze 0.01.
- Grade: filmic/AgX "Medium High Contrast", slight teal shadows, saturation 1.05; vignette 10%; bloom subtle.

## 6. Per-character study sheets (recurring characters seen; for *understanding* only — do not reproduce)
- **Swoop-quiff boy** (DfpQxVRsy9l, narrator): white skin, golden-brown 7-flame quiff, plain blue tee, simple dot eyes with
  eyelid arcs. Reads instantly at thumbnail size because the hair is the only complex shape.
- **Gold-suit rich kid** (DfpQxVRsy9l rival): all-gold foil suit + gold fedora with feather, smug half-lid face, $ pendant.
  Villain coding = one material (gold) applied head-to-toe.
- **Grandma** (DfpQxVRsy9l, Dfok): white/silver swept bob, lilac zip top with pearl necklace; grey bun variant on bike.
- **Plaid dad / old man** (Dfr3KAahSw3, DfpQxVRsy9l): red-black plaid flannel, flat cap, big grey beard as a single sculpted
  slab, knit grey cardigan (bump-mapped).
- **Striped burglars** (Dfr3KAahSw3): blue/white horizontal stripes + beanie + money sack — costume = role.
- **Silver-curl boy** (ref 3): 12 glossy silver curls, navy hoodie with drawstrings modelled as 3D cylinders and a star patch;
  round black-ringed collar. Expression via big decal swaps.
- **Black-hair crush** (ref 3): straight black long hair w/ blunt fringe, anime eyes, blush hatch, black blazer, white collar,
  big 3D red tie. The 3D tie/drawstrings are the "finished" touch — accessories are modelled, not painted.
- **Sunglasses big shot** (Dfok): platinum slick quiff, black aviators (glossy), gold chain, silver foil jacket.
- **Grandpa racer** (Dfok): bald + white side tufts, flat cap, yellow sweater, rusty bike.
- **Bun girl** (Dfp0J1hh58X): two big dark puffs on top (spheres with knit bump), red scarf, black puffer.

## 7. World
- **Layout**: one hero street per story (cobblestone square / suburban main street / snowy lakeside), 3-6 distinct buildings
  dressed with signage (BAKERY, PIZZA, TOWN HALL, BIKE SHOP), plus 2-4 interiors (classroom, bedroom, kitchen, vault, gym).
- **Buildings**: real-world architectural typologies at Roblox scale — half-timber, brick, sandstone columns, clapboard.
  Doors ≈ 1.6× character height, windows with frames + sills + flower boxes. PBR textures (brick, cobble, plank) at
  realistic texel density; this contrast (real world / toy people) is THE tier-A look.
- **Props density**: close/medium shots always have 5-12 props in frame (clock, posters, fruit bowls, lamps, mailbox, bench,
  lamp posts every 6-8 m, parked cars, trees). Wide shots: crowds of 30-300 simple instanced extras.
- **Palette**: tier A — warm neutrals (ochre, brick red, cream, slate) + characters provide the saturated pops. Night =
  navy/indigo + amber windows. Avoid our over-saturated neon set dressing.
- **Sky**: real-cloud HDR-style sky (cumulus on blue), golden hour orange for endings, snowy overcast for winter.
  Ref 6 is over-bright (bloom, saturated purples) — do NOT copy its look.
- **Interiors**: walls with wainscot/stripe wallpaper, rugs, framed pictures, ceiling lights visible; warm practicals.

## 8. Animation & camera
- Acting is **pose-to-pose, snappy**: holds of 0.4-1.2 s, 3-5 frame transitions, big silhouette poses (arms up, hands on head,
  lean-in). Expression swap lands on the stressed word of narration. Running = exaggerated arm pump.
- Weight: squash on landings, small anticipation dips; tier A uses mocap-like walk cycles with hip sway.
- Camera: ~40% close-ups (head + shoulders, 35-50 mm, f/2 DoF), 30% mediums, 20% wides/establishing, 10% inserts (object
  close-ups: coin, sign, clock). Constant slow push-in or drift (2-5%/s); occasional whip pans; low angles for villains,
  top-down for crowds/overview. Dutch tilt 8-12° for tension (heist).
- Shot length: 1.0-2.5 s average (cuts every ~4-6 caption words). One-word captions, bold rounded font, yellow or white
  with dark stroke, centered at ~65% height.

## 9. Transitions (refs 2, 3, 6)
- Hard cuts on the beat are 90% of transitions.
- **Whip-pan blur** (ref 6, Dfp0) between locations, 6-8 frames of directional blur.
- **Match cut on object** (coin → coin close-up, clock → scene).
- **Push-through** into a dark object/door (heist) → fade from black.
- **Insert title cards** (scoreboard "9,999", poster, "FAKE!" detector) as full-frame graphics in-world.
- **Flash-white / bloom pop** on magic beats (ref 6 sword awaken); 3-4 frames.
- 3D text in-world ("WHOA" letters in snow) as an establishing gag.

## 10. Gap list vs our cast.py
| # | Ours | Reference | Fix |
|---|---|---|---|
| 1 | Hair from many thin NURBS `_strand` locks (Harry, Luna, Tyler, Dad) | 5-14 thick fused sculpted clumps | Rebuild per §4 (cap shell + clumps + remesh/smooth) |
| 2 | Hair materials with per-lock alternating colours + highlight locks | single colour + AO root darkening + 1 broad spec | One material per hair, AO-driven root darken |
| 3 | Many trims/patches/neon accents per outfit | 1 signature item, flat colours + 1 texture | Cut accessory count to ≤ 2 per character |
| 4 | Neon rim light in signature colour on every character | neutral/cool rim, warm key | Rim neutral `#cfe2ff`; signature colour only in costume |
| 5 | 5 of 8 characters still on old head | uniform bevelled cube head | Use one head style for whole cast |
| 6 | Accessories partly painted | tie, drawstrings, glasses, chains modelled in 3D | Model 1-2 hero accessories |
| 7 | Faces: varied atlases | consistent ink weight, 2-4 elements | Re-author atlases on one spec (§3) |
| 8 | World: stylised/neon dressing | PBR real-world architecture + toy people | Swap to PBR materials + prop density §7 |
| 9 | Long hair noodles sway | long hair = 2-3 slabs on damped rig | §4 step 8 |

## 11. NEW ORIGINAL cast concepts (permanent roles, tier-A finish)
All R6 per §2, faces per §3, hair per §4. Each has ONE signature read at thumbnail size.

1. **Host — Milo Vance, 15**. Hair: tall copper-orange "wave crest" — 6 broad clumps rolling forward like a breaking wave,
   crest 0.4 H above head, darker roots. Face: dot eyes with eyelid arcs, lopsided grin. Outfit: mustard-yellow hoodie
   (3D drawstrings), charcoal joggers, white sneakers. Signature: tiny 3D walkie-talkie clipped on hoodie pocket. Skin `#e9c29a`.
2. **Best friend — Dez Okafor, 15**. Hair: tight black high-top fade = cap shell + one flat-topped block (bevel 0.1 H) with a
   bump-mapped coil texture. Face: big round white eyes, wide open grin. Outfit: teal varsity jacket, white tee, rolled
   cuffs. Signature: oversized orange headphones around neck. Skin `#8a5a3c`.
3. **Crush — Iris Han, 15**. Hair: glossy ink-black long straight, blunt fringe cut into 6 soft points, 2 side curtains to
   chest, back slab to waist on sway rig; one pale-lilac streak clump. Face: anime set, grey-violet irises, blush hatch.
   Outfit: cream cable-knit cardigan (bump), plaid pleated skirt navy/green, knee socks. Signature: modelled film camera on strap.
4. **Mayor — Mayor Thaddeus Crump, 60**. Hair: silver side-part slick shell with 4 grooves + bushy white moustache (2 sculpted
   curls). Face: smug half-lids. Outfit: emerald-green three-piece suit, gold pocket watch chain (3D), bowler hat.
   Signature: megaphone. Villain-adjacent gold accents only.
5. **Mom — June Vance, 41**. Hair: chestnut messy high bun (sphere 0.32 H) + 3 loose face-framing clumps. Face: soft brows,
   knowing smirk. Outfit: denim shirt sleeves rolled, olive cargo pants. Signature: clipboard / car keys lanyard.
6. **Dad — Arlo Vance, 44**. Hair: dark brown short swoop + full trimmed beard as one sculpted slab (darker by 10%). Face:
   heavy brows, dad-joke grin. Outfit: red-and-cream buffalo-check flannel, khaki chinos. Signature: reading glasses pushed on head.
7. **Grandpa — Grandpa Walt, 80**. Hair: bald dome, cloud-white side puffs (2×3 round clumps), huge white walrus moustache.
   Face: squint eyes. Outfit: brown corduroy blazer (bump stripes) over sky-blue sweater vest. Signature: 3D hearing aid +
   flat cap; 8° hunch.
8. **Grandma — Grandma Rosalind, 76**. Hair: lavender-silver curled bob, 10 tight curls. Face: rosy cheeks, cat-eye glasses
   (glossy red frames). Outfit: mint-green twinset, string of pearls (3D spheres). Signature: oversized gardening gloves / trowel.
9. **Rival — Preston Gild, 15**. Hair: platinum-blond swept fringe over one eye, 5 sharp clumps. Face: smug half-lid smirk,
   one raised brow. Outfit: white blazer with gold buttons, black turtleneck. Signature: glossy black aviators on head.
10. **Kid sibling — Pip Vance, 8** (scale 0.82). Hair: two copper pigtail puffs. Face: huge sparkle eyes, gap-tooth smile.
    Outfit: green dinosaur-hood onesie (3D spikes). Signature: toy dino.
11. **Teacher — Ms. Okonjo**. Hair: tall natural afro (one big remeshed sphere cluster) with a yellow headwrap band. Outfit:
    burgundy cardigan, glasses on beaded chain. Signature: pointer stick.
12. **Cop — Officer Bram Dunlop**. Hair: buzz cut (cap shell only, brown) + ginger handlebar moustache. Outfit: navy uniform,
    3D badge, peaked cap with checkered band. Signature: donut box / whistle.
