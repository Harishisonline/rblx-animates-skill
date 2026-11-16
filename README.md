# RBLX ANIMATES skill: make Roblox-style story reels like @rblxanimates

A Claude skill plus the full Blender production kit behind the Instagram channel **@rblxanimates**: original, blocky
Roblox-style 3D story reels (9:16, 90-120 s) with an upbeat narrator, meme sound effects, burned-in captions and a
like / share / follow end card. Two formats:

- **Blox City**: storyline episodes ("The Poor Boy Who Bought the School", "I Told ONE Secret. By Lunch, Everyone Knew.")
- **In this town / In this world**: one-rule worlds ("In this world, your number changes every time someone lies about you")

With the skill installed, ask Claude things like *"Make the next Blox City episode"*, *"Write a Day 04 script"*,
*"What Roblox story reels are trending?"* or *"Render EP4"*. Claude follows the same line the channel uses: research ->
script (you approve) -> music question -> voice (you listen) -> meme SFX + mix -> animation with QA -> look-dev stills (you
approve) -> final render -> delivery. It never posts anything for you.

| | |
|---|---|
| `skills/rblx-animates/SKILL.md` | the skill: the whole workflow, gates and rules |
| `skills/rblx-animates/references/` | formats, ending rule, music playbook, voice spec, clean-animation rules, lessons |
| `skills/rblx-animates/examples/` | EP2 and EP3: scripts, cue files, mix configs, shots, QA report, look-dev strip |
| `kit/` | the RobloxStories Blender kit (Python for Blender 5.3): characters, faces, sets, props, cameras, QA, render + finish tools, sound pack |
| `scripts/install.sh` | installs the kit to `~/RobloxStories` |

## Requirements
- macOS (tested on an Apple-silicon Mac mini) with **Blender 5.3+** in `/Applications` (Linux works with `BLENDER=/path/to/blender`)
- `ffmpeg`, Python 3.11+
- An **ElevenLabs** API key on a paid plan (narrator voice "Alex" + sound-effect generation): about 2,000 characters per episode
- Claude with this skill (Claude Code, or Claude Cowork linked to your computer). Optional: Gemini in a browser for listening reports
- Disk: about 8 GB free per episode while rendering (frames are deleted after delivery)
- Time: about 5 hours per episode, 2.5 of them unattended rendering

## Install
```bash
git clone https://github.com/Harishisonline/rblx-animates-skill.git
cd rblx-animates-skill
./scripts/install.sh            # copies kit/ to ~/RobloxStories, makes the Python venv, creates ~/RobloxStories_tmp
nano ~/RobloxStories/.env       # ELEVENLABS_API_KEY=...
```
Add the skill to Claude:
- **Claude Code:** `/plugin marketplace add Harishisonline/rblx-animates-skill` then `/plugin install rblx-animates`,
  or copy `skills/rblx-animates` into `~/.claude/skills/`.
- **Claude apps:** zip the `skills/rblx-animates` folder and upload it under Settings -> Capabilities -> Skills.

## Music
The channel's default bed is "Numbers" by TEMPOREX, the sound of viral "In this town" videos. It is copyrighted, so it is
**not** in this repository. Before each video Claude asks whether you have music:
- your own file -> used as the bed;
- none -> your licensed copy at `~/RobloxStories/assets/music/default_bed.wav` if you put one there, otherwise the kit
  composes an original bed (`kit/tools/score.py`, numpy only, free to use).
Never use CC BY-NC music on a monetised or business account.

## What is (and isn't) included
Included: all kit code, the generated face atlases, textures and sound-effect pack, Poly Haven HDRIs (CC0), fonts (SIL OFL),
scripts and configs of two finished episodes. Not included: API keys, copyrighted music, rendered frames, and the final
videos (watch them on @rblxanimates). See `ASSET_LICENSES.md`.

Content rules the skill follows: original characters and sets only (no real Roblox avatars, logos, UI or game audio), meme
sounds recreated as our own, no voice cloning from other people's videos, no posting without your explicit yes.

## Credits
Made by **Harish Pradhan** - GitHub [@Harishisonline](https://github.com/Harishisonline)

Code and docs: MIT (see `LICENSE`). Third-party assets keep their own licences (`ASSET_LICENSES.md`).
