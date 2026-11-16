#!/usr/bin/env bash
# Install the RBLX ANIMATES kit to ~/RobloxStories (episode work goes to ~/RobloxStories_tmp).
# Safe to re-run: existing .env, config.json, assets/music and videos/ are kept.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
KIT="${RBX_HOME:-$HOME/RobloxStories}"
TMP="$HOME/RobloxStories_tmp"
echo "Installing kit to $KIT"
mkdir -p "$KIT" "$TMP" "$KIT/videos" "$KIT/assets/music"
rsync -a --exclude '.env' --exclude 'config.json' --exclude 'assets/music/' "$REPO/kit/" "$KIT/"
[ -f "$KIT/.env" ] || cp "$REPO/kit/.env.example" "$KIT/.env"
[ -f "$KIT/config.json" ] || cp "$REPO/kit/config.example.json" "$KIT/config.json"
PY=${PYTHON:-python3}
if [ ! -x "$KIT/.venv/bin/python" ]; then "$PY" -m venv "$KIT/.venv"; fi
"$KIT/.venv/bin/pip" install -q --upgrade pip
"$KIT/.venv/bin/pip" install -q -r "$KIT/requirements.txt"
if [ ! -d "$KIT/assets/tex/pbr" ]; then
  echo "Fetching CC0 PBR textures (Poly Haven, ~26 MB)..."
  (cd "$KIT" && "$KIT/.venv/bin/python" -I tools/fetch_pbr.py) || echo "  ! PBR fetch failed; re-run: python3 -I tools/fetch_pbr.py"
fi
echo
echo "Checks:"
BL="${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}"
if [ -x "$BL" ]; then "$BL" --version 2>/dev/null | head -1; else echo "  ! Blender not found at $BL (set BLENDER=/path/to/blender)"; fi
command -v ffmpeg >/dev/null && echo "  ffmpeg ok" || echo "  ! ffmpeg missing (brew install ffmpeg)"
grep -q '^ELEVENLABS_API_KEY=.\+' "$KIT/.env" && echo "  ElevenLabs key set" || echo "  ! put ELEVENLABS_API_KEY=... in $KIT/.env"
[ -f "$KIT/assets/music/default_bed.wav" ] && echo "  default music bed found" || echo "  (no default_bed.wav: the kit will compose an original bed unless you give music)"
echo
echo "Done. Install the skill: copy $REPO/skills/rblx-animates to ~/.claude/skills/ (or use the plugin marketplace)."
