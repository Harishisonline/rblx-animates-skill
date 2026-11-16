# WORLD v3.1 — Blox Town, materials, text props, crowds, map (2026-11-14)
Goal (REF2 tier A / REF1): real-world PBR architecture + toy R6 people, warm-neutral surroundings, 5-12 props in close shots,
indigo night + amber practicals. **Reuse these modules; extend them rather than writing a new world file.**

## Modules
| Module | Use |
|---|---|
| `rbx/pbr.py` | `pbr.get(key, tint=, tile=, rot=)` object-space box-projected PBR (diff/normal/ARM, AO multiply), no UVs needed. Keys: cobble brick plaster planks steel(riveted plate) asphalt grass concrete tile fabric roof woodfloor timber. Missing files -> flat colour. `pbr.swatch_board()` for a library check. |
| `rbx/town.py` | Locations (each at its own origin in `T.ORIGINS`, returns `{name, look, focus, cams{name:(loc,target,lens)}, t}`) and pieces. `T.frame(L,"wide")` makes a keyed Cam. |
| `rbx/signs.py` | Real font text (Poppins bold, Inter UI, Patrick Hand handwriting, Bangers). Everything faces -Y, `rot`=yaw, returns a root empty (parent to hands/walls). `show(ob,t_on,t_off)` visibility windows; `typed()` type-on; `wrist_counter(seq=[(t,"047"),...])` colours white/amber(40+)/red(90+), "???" magenta; `face=False` = digits only (caller supplies the bezel). |
| `rbx/crowd.py` | Instanced unrigged extras (variants c0-c11, police, doctor, student_a/b). `crowd(..., n=1500, mode="grid")` is cheap. `numbers(obs)` floating badges. Use cast.py rigs for anyone who acts. |
| `rbx/townmap.py` | Paper map (`town_map`), `pin`, `route(stops, t0, t1)` draws itself with a pin riding the head. |

## Locations (number_lies Ep 1 coverage)
main_street (shops with OPEN->CLOSED `t_flip`, police car + 2 officers, walkers, lamps/benches/planters/hydrants/A-frame/news box, RBLX ANIMATES plaque) ·
pharmacy_corner (dusk, giant `street_screen`, pass `screen_lines=`) · night_street (amber lamps, lit windows; cam `alone`) ·
school_exterior (brick school, steel gym, bike racks, hoop, students) · school_hallway (lockers w/ numbers, bulletin board w/ posters+notes, trophy case, EXIT, clock) ·
classroom (3x3 desks, chalkboard text, teacher desk with handwritten note, windows) · kitchen (night: laptop feed posts=, Mom's teal mug, pendant, fridge notes "Covered, Harry") ·
bedroom(night=) (delivery bag, desk note, brand plaque; night = desk-lamp practical + moon) · front_hall(night=) (door, coats, shoes, mirror, photos; cam `cuff`); both use `_interior_cast_light` (warm motivated cast key, never a blue-grey cast) · insert_table kind wrist|phone|map (ECU voids).
Bedroom/front-door/hallway names in beats.md map 1:1 to these.

## Conventions
- Units: character 5.3 tall, door 8.6, storey 10.5, road 14 wide, sidewalk 6. Ground z=0. Fronts face local -Y; yaw 90 -> faces +X.
- Interiors are open toward -Y (camera side); `room(..., fill=1.0)` adds a soft shadowless ceiling fill; windows take `view="#hex"` glow.
- Night: `street_lamp(on=True)` adds shadowless amber point lights (EEVEE shadow-buffer safe). Night main street/night_street
  call `night_cast_keys(o)`: shadowless warm shop-window SPILL area lights on both sidewalks every 20 studs + a streetlamp-side
  key and cool fill on the cast mark (focus), so faces in night close-ups are keyed, not sign-backlit silhouettes.
- Shadow budget: every location returns through `_L`, which calls `shadow_budget()` - scene shadow pool >= 1024 MB, soft
  wash lights (area >= 6 studs) page-res capped at 0.03, sun 0.008, small keys 0.004. Fixes 'Shadow buffer full' on big sets
  (hallway). `ceiling_panel` emitters are half the visible panel so contact shadows stay readable.
- Night kitchen: warm night ambient (0.16,0.12,0.09) + camera-side `kt_frontF` fill + `kt_floorW` floor wash - flat-mode
  (non-cine) dark costumes keep detail and the foreground floor is warm wood, not a navy band.
- Validate: `blender -b --factory-startup -P tools/world_stills.py -- <loc[,loc]|all> [samples] [cams]` -> `research/world_stills/<loc>_<cam>.png` (1080x1920, serial, single process; ~1-3 s/still at 8 samples).
- Assets: CC0 Poly Haven 1k textures (~26 MB) in `assets/tex/pbr/` (logged in ASSETS_LOG.md); re-fetch with `tools/fetch_pbr.py`.
- Legacy `robloxworld.py` (v2 studded Blox Town) still works for old videos; new stories use `town.py`.

## v3.1 fixes (2026-11-14)
- Town look presets in `town.LOOKS` (`evening_kitchen`, `warm_night`, `real_dusk`), resolved via `town.look_preset(name)` (dicts work with look.rig/grade). Night = indigo shadows + amber practicals; dusk = orange-to-indigo gradient sky + low warm sun.
- Kitchen night: woodfloor, under-cabinet strip, corner floor lamp, brighter pendant. Main street: second shadowless bounce sun for the shaded side; street lamps 2200 W shadowless.
- `tree()` molded canopy clumps with noise-tinted leaf material, root flare + limbs. `wheel()` torus tyre + rim + 12 spokes. Lockers glossy paint, hallway close cam moved.
- `crowd.POSES` (stand, hips, phone, point, chat, wave, cross, walk, lookup, pocket); extras get a pose per instance; sidewalk extras face the street screen.
- Phone + laptop are dark-mode UIs with bright bold text (legible at ECU); wrist insert has hand/fingers/sleeve + cuff.
- Facades add a perpendicular **blade sign** (both faces) so shop names read down the street (`blade=False` to skip); fascia signs taller.
- `signs.show()` bug fixed (items visible before t_off). `tools/world_anim_test.py anim` verifies OPEN->CLOSED, type-on, 000->001->099; `crowd` verifies 1,260 instanced extras (build 0.2 s, render 2 s at 8 samples).
- `WITH_CAST=1 blender ... tools/world_stills.py` drops cast host/bestie/mom at the location focus for a scale check.

## v3.2 dressing pass (2026-11-14)
- **Kitchen v2** `T.kitchen(night=True|False)` (day=True alias): sink window with painted view (`window_view`) + curtains + sill plants, open shelves (plates, books, labelled FLOUR/SUGAR/COFFEE jars), utensil rail, range hood, upper cabinet, kettle, toaster, bread board, dish rack, crock, paper towel, fridge (notes, magnets, photos, kid drawing, cereal boxes), NOVEMBER `calendar`, clock, "Home sweet home" plaque, left-wall art + cookbook `wall_shelf`, rug, table with laptop/mug/fruit/mail pile/vase/placemats, pendant, floor bounce light. Day = sun spot through window. Cams: wide, laptop, counter, fridge.
- **Hallway v2**: per-locker colour cycles, open dressed lockers (`locker_bank(color=[..], open_idx=(..))`), polished tile floor (`pbr.get(rough=)`, now cache-keyed), ceiling grid, 2 bulletin boards, pennants + HONOR ROLL / CLASS OF 2031 boards above lockers, GO BLOX BEARS banner, trophy case, WATER fountain, ROOM 12 door, wet-floor sign, backpack/papers.
- **Aerial**: `main_street(backlots=True)` adds `back_blocks()` (alleys, second building row with window-grid skins, pitched coloured roofs/chimneys or flat roofs via `roof_clutter` - AC units, tanks, skylights, dishes, rooftop billboards - parallel streets, park, parking lot, far rows, cross street). All facades use `roof_clutter`. `plaza()` adds fountain, planters, bunting, lamps, crosswalk. Street screen is 26x14 on the pharmacy (x=0, z=21), glow 7, light bar. `main_street(plaza_crowd=90)` builds a clustered light-palette crowd with badge numbers; cams `aerial` (0,22,62)->(0,132,6) and `aerial_end` (0,92,40)->(0,148,19) both keep the screen readable.
- **Crowd**: `crowd(mode="clusters", palette="light")` (groups of 2-6 + walking pairs, open floor between); variants l0-l11; `numbers(badge=True, tilt=40, every=N)`.
- **Inserts v2** `insert_table(kind=wrist|phone|laptop|map)`: bokeh room backdrop, R6 block forearm (`block_arm`) with ribbed cuff sleeve that slides back over `t_slide`, wristband device v3 (one strap ring + ONE round bezel with inset screen, `wrist_counter(face=False)` digits kept level; device front sits inside the closed sleeve so nothing glows through); backdrop has a lit tabletop, solid counter, low wash + low bokeh so vertical ECUs never have a black bottom half; ambient follows backdrop temperature (warm, phone = cool); per-cam fstops/focus/time (`L["fstops"]`, `L["focus_pts"]`, `L["cam_t"]`, honoured by `T.frame` and world_stills); `T.insert_rack(L, t0, t1)` keys the sleeve->counter rack focus. Insert cams must sit level with or above the prop (an up-angled ECU sees the unlit underside + sky); the backdrop wall is 60x70 with an upper wash; bokeh emitters are 40-seg spheres (low-seg spheres defocus into octagons); r5: `skin_mat` v3 (SSS + grazing falloff + crease AO) on every insert hand, wrist insert pulls exposure -0.6 (look rig clips skin otherwise), palm overlaps forearm, separate fingers; wrist v4 (r3): `block_hand` real Roblox fist (back of hand, 4 knuckle bumps, curled fingers, thumb) instead of crease
slats; `skin_mat(skin)` mottled SSS skin with micro-normal; dark continuous strap ring wrapping all 4 faces with keeper
ridges, bezel (dia 0.84) smaller than the 1.0 arm so the strap shows above/below the face; sleeve stops 0.75 past the
band so the cuff stays in the ECU; `insert_table(role=...)` picks skin/sleeve/cuff from `town.ARM_STYLE` (mirrors the
8 cast v3 designs - update it if CAST.md changes); top rim light on the arm edge; ecu frames fist + watch + cuff. Phone held in block hand (thumb+fingers); laptop OTS with block hands.
- world_stills: `loc@key=val;key=val` kwargs (e.g. `kitchen@night=False`, `main_street@plaza_crowd=90`).

## Known weak spots
wrist insert arm is not the cast rig (own block arm, matching skin); test_seq s03 still builds its own dense 60-extra crowd at (0,126) - switch it to plaza_crowd + cam aerial/aerial_end. Extras are static poses (no walk cycles); dense grid crowds read as a carpet from high angles (use scatter + numbers for hero crowds);
cast placement in stills is a naive line at focus (blocking is the shot author's job); close cams (main_street close) frame doors more than
props; night kitchen still on the dark side for wides; no lake/terrain, festival street or station location yet.

- r4 inserts: knit-rib cuffs use `town.knit_mat` (no tiled texture on small cuffs: it aliases into stripes). Counter changes pop + flash automatically (wrist_counter pulse, halo ring, screen spike). Put the flip ON the stressed word in shots.py.
