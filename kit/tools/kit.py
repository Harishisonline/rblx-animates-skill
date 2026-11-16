"""Settings and machine lookups shared by the studio tools (plain python, not Blender).

config.json next to rbx/ overrides any key in DEFAULTS. Nothing here is required: with no
config.json every tool behaves as before (auto-detects Blender, fonts, whisper)."""
import glob, json, os, platform, re, shutil, subprocess, sys

STUDIO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYSTEM = platform.system()  # Windows / Darwin / Linux

# Named narrator presets (config.json "voice_preset"). hype_v3 = measured winner 2026-11-14 (VOICE_SPEC.md HYPE recipe).
VOICE_PRESETS = {
    # alex_ep1 = USER-APPROVED narrator voice (2026-11-14, chat): 'Alex upbeat like D_fix_m.m4a' = the EP1 number_lies narration.
    # eleven_v3, stability 0.0, similarity 0.75, style 0.25, speaker boost, light audio tags allowed ([fast, urgent, breathless], [whispers]).
    # Post (docs/VOICE_SPEC.md DECISION recipe): silenceremove stop 0.22 -> 0.14 s, atempo 1.08, HPF 80, +3 dB @ 4 kHz, compressor, loudnorm -14 LUFS / TP -1.5.
    # The In-this-town/hype tests (intown_v1, hype_v3) were REJECTED by the user by ear on 2026-11-14; they stay selectable only.
    "alex_ep1": {"voice_id": "yl2ZDV1MzN4HbQJbMihG", "tts_model": "eleven_v3", "tts_stability": 0.0, "tts_similarity": 0.75,
                 "tts_style": 0.25, "tts_speed": None, "tts_take_split": None, "tts_speaker_boost": True},
    # intown_v1 = In this town / In this world default (2026-11-14): calm deadpan storyteller, measured closest to the two
    # reference reels (closeness 0.84 vs 1.42-1.77; videos/number_lies/voice_tests/intown/NOTES.md). No tags, plain punctuation.
    # Post (docs/VOICE_SPEC.md 'INTOWN recipe'): gaps > 0.34 s -> 0.30 s, atempo to 257 wpm, HPF 70, comp 1.5:1 @ -12 dB,
    # limiter, 120 ms lead-in, two-pass loudnorm -14 LUFS / -1.5 dBTP, no presence boost. UNVERIFIED by ear.
    "intown_v1": {"voice_id": "yl2ZDV1MzN4HbQJbMihG", "tts_model": "eleven_multilingual_v2", "tts_stability": 0.55,
                  "tts_similarity": 0.75, "tts_style": 0.0, "tts_speed": 1.15, "tts_take_split": "paragraph",
                  "tts_take_chars": 900, "tts_target_wpm": 257, "tts_gap_cap_s": 0.30, "tts_lead_s": 0.12},
    "hype_v3": {"voice_id": "yl2ZDV1MzN4HbQJbMihG", "tts_model": "eleven_v3", "tts_stability": 0.0, "tts_similarity": 0.75,
                "tts_style": 0.45, "tts_speed": None, "tts_take_split": "line", "tts_target_wpm": 270},
    "legacy_liam": {"voice_id": "TX3LPaxmHKxFdv7VOQHJ", "tts_model": "eleven_multilingual_v2", "tts_speed": 1.12,
                    "tts_stability": 0.38, "tts_similarity": 0.8, "tts_style": 0.22, "tts_take_split": None},
}

DEFAULTS = {
    "voice_preset": "alex_ep1",          # in_this_world / in_this_town default; "hype_v3", "legacy_liam" or "" (loose tts_* keys) still selectable
    "blender": "",                        # Blender executable; empty = auto-detect
    "voice_id": "skghcThhrhzKre1Ny7M7",   # ElevenLabs narrator voice
    "tmp_dir": "~/RobloxStories_tmp",         # local scratch for frames/blend/caps (never on a cloud drive)
    "auto_clean_frames": True,              # delete frames/blend after finish.py (set False to keep them for partial re-renders)
    "tts_model": "eleven_v4",
    "tts_speed": 1.05,                    # applied by the voice model (natural). Never stack ffmpeg speed-ups on top
    "tts_stability": 0.4, "tts_similarity": 0.8, "tts_style": 0.4,
    "sfx_model": "eleven_text_to_sound_v2",
    "whisper_python": "",                 # a python that has faster-whisper; empty = the python running the tool
    "whisper_model": "medium.en",
    "music_url": "https://www.youtube.com/watch?v=ecvbCDTcAco",  # TEMPOREX - Numbers
    "music_speed": 1.5,
    "music_mode": "tempo",                # tempo = same pitch, speed = pitched up
    "caption_font": "",                   # empty = Segoe UI Black on Windows, Arial Black elsewhere
}


def cfg():
    c = dict(DEFAULTS)
    p = os.path.join(STUDIO, "config.json")
    if os.path.exists(p):
        c.update(json.load(open(p, encoding="utf-8")))
    pre = dict(VOICE_PRESETS, **c.get("voice_presets", {})).get(c.get("voice_preset") or "")
    if pre:  # a named voice preset wins over loose tts_* keys (docs/VOICE_SPEC.md 'HYPE recipe')
        c.update(pre)
    return c


def save_cfg(c):
    json.dump(c, open(os.path.join(STUDIO, "config.json"), "w", encoding="utf-8"), indent=2)


def caption_font(c=None):
    c = c or cfg()
    return c.get("caption_font") or ("Segoe UI Black" if SYSTEM == "Windows" else "Arial Black")


def api_key():
    """ElevenLabs key from the environment or a .env file next to config.json (never printed)."""
    k = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    p = os.path.join(STUDIO, ".env")
    if not k and os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            m = re.match(r"\s*ELEVENLABS_API_KEY\s*=\s*['\"]?([^'\"\s]+)", line)
            if m:
                k = m.group(1)
    return k


# ---- Blender ---------------------------------------------------------------------------
def _ver_key(path):
    m = re.search(r"(\d+)\.(\d+)", path)
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def blender_candidates():
    out = []
    if os.environ.get("BLENDER"):
        out.append(os.environ["BLENDER"])
    w = shutil.which("blender")
    if w:
        out.append(w)
    if SYSTEM == "Windows":
        roots = [os.environ.get("ProgramFiles", r"C:\Program Files"), os.environ.get("ProgramFiles(x86)", ""),
                 os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs")]
        found = []
        for r in roots:
            if r:
                found += glob.glob(os.path.join(r, "Blender Foundation", "Blender*", "blender.exe"))
        found += glob.glob(r"C:\Program Files (x86)\Steam\steamapps\common\Blender\blender.exe")
        out += sorted(found, key=_ver_key, reverse=True)
    elif SYSTEM == "Darwin":
        out += sorted(glob.glob("/Applications/Blender*.app/Contents/MacOS/Blender")
                      + glob.glob(os.path.expanduser("~/Applications/Blender*.app/Contents/MacOS/Blender")),
                      key=_ver_key, reverse=True)
    else:
        out += sorted(glob.glob(os.path.expanduser("~/blender*/blender")) + glob.glob("/opt/blender*/blender")
                      + ["/snap/bin/blender", "/usr/bin/blender"], key=_ver_key, reverse=True)
    seen, res = set(), []
    for p in out:
        if p and p not in seen and os.path.isfile(p):
            seen.add(p); res.append(p)
    return res


def find_blender(c=None):
    c = c or cfg()
    if c.get("blender") and os.path.isfile(c["blender"]):
        return c["blender"]
    cands = blender_candidates()
    return cands[0] if cands else None


def blender_version(path):
    try:
        r = subprocess.run([path, "-b", "--factory-startup", "--version"], capture_output=True, text=True, timeout=120)
        m = re.search(r"Blender\s+(\d+)\.(\d+)(?:\.(\d+))?", r.stdout)
        return tuple(int(x or 0) for x in m.groups()) if m else None
    except Exception:
        return None


# ---- fonts (for Pillow textures and contact sheets) -------------------------------------
_ROLE = {"ariblk.ttf": "black", "arialbd.ttf": "bold", "arial.ttf": "regular", "segoeprb.ttf": "hand",
         "segoepr.ttf": "hand", "inkfree.ttf": "hand", "impact.ttf": "black"}
_CHAIN = {
    "black": ["ariblk.ttf", "Arial Black.ttf", "Impact.ttf", "impact.ttf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"],
    "bold": ["arialbd.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"],
    "regular": ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"],
    "hand": ["segoeprb.ttf", "segoepr.ttf", "Inkfree.ttf", "Chalkduster.ttf", "Bradley Hand Bold.ttf",
             "Comic Sans MS Bold.ttf", "comicbd.ttf", "DejaVuSans-Bold.ttf"],
}
_index = None


def _font_index():
    global _index
    if _index is None:
        dirs = []
        if SYSTEM == "Windows":
            dirs = [os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"),
                    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Windows", "Fonts")]
        elif SYSTEM == "Darwin":
            dirs = ["/System/Library/Fonts/Supplemental", "/System/Library/Fonts", "/Library/Fonts",
                    os.path.expanduser("~/Library/Fonts")]
        else:
            dirs = ["/usr/share/fonts", "/usr/local/share/fonts", os.path.expanduser("~/.local/share/fonts"),
                    os.path.expanduser("~/.fonts")]
        dirs.insert(0, os.path.join(STUDIO, "assets", "fonts"))
        _index = {}
        for d in dirs:
            if os.path.isdir(d):
                for root, _, files in os.walk(d):
                    for f in files:
                        _index.setdefault(f.lower(), os.path.join(root, f))
    return _index


def font_path(name):
    idx = _font_index()
    for n in [name] + _CHAIN.get(_ROLE.get(name.lower(), "bold"), []):
        if n.lower() in idx:
            return idx[n.lower()]
    return None


def font(name, size):
    from PIL import ImageFont
    p = font_path(name)
    if p:
        return ImageFont.truetype(p, size)
    try:
        return ImageFont.load_default(size)
    except TypeError:
        return ImageFont.load_default()


def rm_tree(path):
    """Remove a directory, or a symlink to one (and its target)."""
    import shutil
    if os.path.islink(path):
        t = os.path.realpath(path)
        os.unlink(path)
        shutil.rmtree(t, ignore_errors=True)
    elif os.path.isdir(path):
        shutil.rmtree(path, ignore_errors=True)


def link_local_tmp(slug, names=("frames", "blend", "caps")):
    """Make videos/<slug>/frames|blend|caps symlinks into the LOCAL scratch dir (config tmp_dir), so that when the workspace's
    videos/ folder lives on Google Drive the thousands of render PNGs are never uploaded."""
    root = os.path.join(os.path.expanduser(cfg().get("tmp_dir", "~/RobloxStories_tmp")), slug)
    vdir = os.path.join(STUDIO, "videos", slug)
    if not os.path.isdir(vdir):
        return
    for n in names:
        p = os.path.join(vdir, n)
        if os.path.islink(p):
            os.makedirs(os.path.realpath(p), exist_ok=True)
            continue
        if os.path.isdir(p) and os.listdir(p):
            continue                      # real, non-empty: leave it alone
        if os.path.isdir(p):
            os.rmdir(p)
        os.makedirs(os.path.join(root, n), exist_ok=True)
        os.symlink(os.path.join(root, n), p)
