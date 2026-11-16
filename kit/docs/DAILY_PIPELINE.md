# DAILY PIPELINE (kit v4.0). The full version lives in the claude.ai Project RBLX ANIMATES (knowledge/DAILY_PIPELINE.md).
EP2 "The Poor Boy Who Bought the School" is the user-approved quality bar.
Run order for one episode:
1. Script, then the user approves it.
2. `tools/ep_audio/` with `EP=<ep dir>`, in order: tts.py, words.py, post.py, sfxgen.py, mix.py.
3. shots.py with `from rbx.shotlib import *` + `install_snaps()` (copy patterns from templates/EP2_poor_boy_school_shots.py).
4. `Blender -b --factory-startup -P tools/ep_lo.py -- <slug> all`, then fix every QA flag and look at the 2 fps sheets.
5. Look-dev strip: `tools/render.py <slug> still:T <shot> 24` on 6 shots.
6. `tools/ep_final.sh <slug> 32` (run detached; ETA: `tools/ep_eta.py <ep dir>`, about 1.4 min per second of video).
7. `tools/ep_finish.sh <ep dir>` -> out/final_nomusic.mp4 (post) + out/final_preview.mp4 (review).
8. Final contact sheet from frames/, then deliver.
Rules: docs/CLEAN_ANIMATION.md. Regression test after any kit change: ~/RobloxStories_tmp/shotlib_test (`Blender -b --factory-startup -P test.py`).
