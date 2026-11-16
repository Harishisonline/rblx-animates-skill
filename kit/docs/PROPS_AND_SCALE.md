# Props and scale (rbx/props2.py)

v1 problems: grey cube "metal box", pigeon from 3 primitives, mosquitoes 2-4x the size of a head. Fixes:

## Scale policy (character 5.7 units tall, head 1.24, hand 0.6)
| Thing | Wide/medium shots | Close-up |
|---|---|---|
| mosquito, key, coin, switch | <= hand size (0.7) | separate `macro=True` copy, `cams.insert`, 40-60% of frame |
| pigeon, cat | 1.0-1.6 long | normal |
| drone | 1.6-2.4 across | normal |
| robot enforcer | 1.0-1.25x a person | normal |
Many SMALL mosquitoes (`P.swarm_cloud`, s=0.2) read as a cloud; a few large ones read as monsters.

## Build checklist for any new prop
1. 6-15 bevelled chunks (box/cyl/sphere with bevel), clear silhouette at 100 px tall.
2. 2-3 colours + one accent (an emissive part for anything electronic).
3. Secondary motion (noise on wings/rotors/tail) so it never freezes.
4. Origin on the ground, faces -Y, grounded with a contact shadow if it stands.
5. Check it alone in a lineup render before using it in a scene.

## v2 prop library
`mosquito, swarm_cloud, pigeon, helmet, steel_locker, wood_crate, robot (on the standard rig), drone, server_rack, terminal,
neon_sign, lit_building_mat, ai_city, survivor (hero), wrist_band, floating_number, searchlight, world_pos`.
Characters: build on `chars.Char` (rigged, faces, walk, act). Hero design for small screens: strong silhouette colour
(orange scarf), one glowing accent (goggle lenses), hood/backpack for shape, a readable symbol (wrist number).
