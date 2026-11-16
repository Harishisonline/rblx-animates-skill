# Assets: free, license-clean sources (full detail in research/notes_assets.md)
Rule: our own characters and sets only. No real Roblox avatars/logos/UI/game audio, no ripped Roblox models, no other
creators' characters. Only CC0 / clearly free-for-commercial assets.

Fetched automatically: `python tools/assets.py starter` -> assets/hdri/*.hdr (Poly Haven, CC0) + assets/fonts (Poppins
ExtraBold, Bangers: SIL OFL). Everything fetched is logged in assets/ASSETS_LOG.md.

Manual one-time downloads (CC0, no account) for sci-fi/AI scenes, unzip into assets/models/<pack>/ and import with
`bpy.ops.import_scene.gltf` / FBX:
- Quaternius: Animated Robot Pack, Animated Mech Pack, Cyberpunk Game Kit, Sci-Fi Essentials Kit, Modular Sci-Fi MegaKit,
  Downtown City MegaKit (quaternius.com; check each pack's license text).
- Kenney: Space Station Kit, Modular Space Kit, City Kit Industrial, City Kit Roads, Mini Characters (kenney.nl, CC0).
- Poly Haven models/textures (api.polyhaven.com), ambientCG (CC0 PBR textures).
- Audio: Freesound (CC0 filter only), YouTube Audio Library (credit the CC-BY tracks), Kevin MacLeod (CC-BY 4.0, credit).
  Pixabay: check the Content-ID label on each track. Do not use CC-BY-NC for monetised videos.
- Mixamo animations: allowed commercially, no credit, but retargeting onto the blocky rig needs a manual step.
Not usable / dead ends: Roblox's own avatar assets and models (licence unclear), Blender Studio assets (subscription), Sketchfab
downloads (needs an OAuth token and per-model credit).

## SFX library (real-sfx)
Kenney audio packs (CC0): `python tools/sfx_library.py kenney`, registered in ~/.claude/skills/real-sfx. See docs/AUDIO.md.
