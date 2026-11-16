"""Finish a video: mix audio (voice + room tone + sfx cues + original score), burn word captions, mux the mp4.
python tools/finish.py <slug> [--no-captions] [--music-source score|house|none] [--mood horror] [--score-seed N]
                              [--amb room] [--music path] [--music-speed 1.5] [--music-mode speed|tempo] [--audio-only]
reads  videos/<slug>/frames/####.png, audio/voice.wav, audio/words.json, audio/cues.json (+ beats.json, see docs/AUDIO.md)
music  default (config "music_source": "score"): tools/score.py writes a NEW original score for this video from its beat map
       (mood from --mood / story.json / config "score_mood"), copied to audio/music.wav and mixed as is (it is already
       shaped per beat), side-chain ducked under the voice (--duck-db, default -5).
       --music path: that file instead (old behaviour, per-beat gain automation from beat cues applied).
       --music-source house: the first file in studio/music/ (the old house bed, sped up --music-speed). Avoid: it is the
       repetitive track the user does not want; kept only for backward compatibility.
room   tools/ambience.py renders audio/ambience.wav (cues {"t","amb":"school_hallway"} or --amb / config "ambience").
writes videos/<slug>/audio/mix.m4a (mastered -14 LUFS / -1.5 dBTP, two-pass), captions.ass, out/final.mp4 (+ out/final_nocaptions.mp4)"""
import argparse, glob, json, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import kit  # noqa: E402
CFG = kit.cfg()
ap = argparse.ArgumentParser()
ap.add_argument("slug"); ap.add_argument("--no-captions", action="store_true"); ap.add_argument("--music", default="")
ap.add_argument("--music-db", default="-13"); ap.add_argument("--sfx-db", default="-6")
ap.add_argument("--music-speed", type=float, default=float(CFG["music_speed"]))
ap.add_argument("--music-mode", default=CFG["music_mode"])  # tempo = same pitch (house choice), speed = pitched up
ap.add_argument("--no-music", action="store_true")
ap.add_argument("--music-source", default=CFG.get("music_source", "score"), choices=["score", "house", "none"])
ap.add_argument("--mood", default="")
ap.add_argument("--score-seed", default="")
ap.add_argument("--duck-db", default=str(CFG.get("duck_db", -5)))
ap.add_argument("--amb", default=CFG.get("ambience", "room"))   # "none" = no room tone
ap.add_argument("--amb-db", default="0")
ap.add_argument("--voice-clarity", action="store_true")  # v3.7 OPTION (mix D, MUSIC_RESEARCH.md); not default until the user approves the A/B
ap.add_argument("--audio-only", action="store_true")  # stop after the mastered mix (no frames needed)
ap.add_argument("--captions", default="v2", choices=["v2", "ass"])  # v2 = grouped words + accent colour (Pillow); ass = old one-word style (needs libass)
o = ap.parse_args()
vdir = os.path.join(STUDIO, "videos", o.slug)
adir = os.path.join(vdir, "audio"); odir = os.path.join(vdir, "out"); os.makedirs(odir, exist_ok=True)


def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


src = o.music
score_used = False
for f in glob.glob(os.path.join(adir, "music.*")):
    os.remove(f)
if o.no_music or (o.music_source == "none" and not src):
    print("music: none")
elif not src and o.music_source == "score":
    mood = o.mood or ""
    if not mood and os.path.exists(os.path.join(vdir, "story.json")):
        mood = json.load(open(os.path.join(vdir, "story.json"), encoding="utf-8")).get("mood", "")
    mood = mood or CFG.get("score_mood", "mystery")
    cmd = [sys.executable, os.path.join(HERE, "score.py"), o.slug, "--mood", mood,
           "--lufs", str(CFG.get("score_lufs", -19))]   # -24 read as 'no music' to earshot (REF1: music audible all through)
    if o.score_seed:
        cmd += ["--seed", str(o.score_seed)]
    subprocess.run(cmd, check=True)
    shutil.copy(os.path.join(adir, "score.wav"), os.path.join(adir, "music.wav"))
    score_used = True
else:
    if not src:
        mdir = os.path.join(STUDIO, "music")
        cands = sorted(f for f in glob.glob(os.path.join(mdir, "*"))
                       if os.path.splitext(f)[1].lower() in (".mp3", ".wav", ".m4a", ".mp4", ".aac", ".ogg", ".flac", ".webm"))
        src = cands[0] if cands else ""
        if src:
            print("warning: using the house track (repetitive across videos). Prefer --music-source score.")
    if src and duration(src) >= 2.0:
        sp = o.music_speed
        af = (f"asetrate=44100*{sp},aresample=44100" if o.music_mode == "speed" else f"atempo={sp}")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vn", "-ac", "2", "-ar", "44100", "-af",
                        "aresample=44100," + af, os.path.join(adir, "music.wav")], check=True)
        print(f"music: {os.path.basename(src)} x{sp} ({o.music_mode}) -> audio/music.wav")
    else:
        print(f"music: none ({'file looks broken: ' + src if src else 'no file'})")

# 0b. room tone / ambience bed (REF4 layer A: never digital silence)
_amb = os.path.join(adir, "ambience.wav")
if os.path.exists(_amb):
    os.remove(_amb)
if o.amb != "none":
    subprocess.run([sys.executable, os.path.join(HERE, "ambience.py"), "render", o.slug, "--amb", o.amb]
                   + (["--seed", str(o.score_seed)] if o.score_seed else []), check=True)   # a fixed seed = the same beds

# 1. audio mix (side-chain ducking, holds, per-beat automation for plain music files)
_clar = o.voice_clarity or bool(CFG.get("voice_clarity", False))
_duck = [] if (_clar and not any(a.startswith("--duck-db") for a in sys.argv[1:])) else ["--duck-db", o.duck_db]
subprocess.run([sys.executable, os.path.join(HERE, "mix.py"), "--video", o.slug, "--music-db", o.music_db,
                "--sfx-db", o.sfx_db, "--amb-db", o.amb_db] + _duck
               + (["--voice-clarity"] if _clar else [])
               + (["--music-level", "asis"] if score_used else []), check=True)

# 1b. master loudness to -14 LUFS / -1.5 dBTP (earshot audited v1 at -19.5 LUFS: 5.5 dB too quiet for web)
_mix = os.path.join(adir, "mix.m4a")
_tmp = os.path.join(adir, "mix_norm.m4a")
if os.path.exists(_mix) and not os.environ.get("NO_LOUDNORM"):
    # two-pass linear loudnorm: measure, then one static gain (single-pass dynamic mode pumps the bed)
    _r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", _mix, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json",
                         "-f", "null", "-"], capture_output=True, text=True).stderr
    _m = json.loads(_r[_r.rfind("{"):_r.rfind("}") + 1])
    _af = ("loudnorm=I=-14:TP=-1.5:LRA=11:linear=true:measured_I={input_i}:measured_TP={input_tp}:measured_LRA={input_lra}:"
           "measured_thresh={input_thresh}:offset={target_offset}").format(**_m)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", _mix, "-af", _af, "-ar", "48000",
                    "-c:a", "aac", "-b:a", "192k", _tmp], check=True)
    os.replace(_tmp, _mix)
    print("mastered to about -14 LUFS (check with tools/audio_qa.py)")
if o.audio_only:
    print("audio only: ", _mix)
    sys.exit(0)

# 2. captions (script words, one at a time; same look as the reference)
words = json.load(open(os.path.join(adir, "words.json"), encoding="utf-8"))
LAG = 1.3 / 30


def ts(t):
    cs = int(round(max(t, 0) * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


head = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Word,{FONT},150,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,0,0,0,0,100,100,1,0,1,9,3,5,20,20,20,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
lines = []
for i, w in enumerate(words):
    txt = re.sub(r"[^\w'$%,.]", "", w["word"]).strip(",.").upper()
    if not txt:
        continue
    s = 0.0 if i == 0 else w["start"] + LAG
    e = (words[i + 1]["start"] + LAG) if i + 1 < len(words) else w["end"] + 0.4
    lines.append(f"Dialogue: 0,{ts(s)},{ts(e)},Word,,0,0,0,,{{\\pos(540,1607)}}{txt}")
head = head.replace("{FONT}", kit.caption_font(CFG))
open(os.path.join(vdir, "captions.ass"), "w", encoding="utf-8").write(head + "\n".join(lines) + "\n")

# 3. mux
kit.link_local_tmp(o.slug, ("caps",))
os.chdir(vdir)
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                            os.path.join("audio", "mix.m4a")], capture_output=True, text=True).stdout)


def tail_check(fps=30, max_black=6, dark=10.0):
    """R2-2 (end of video): never end on dead black. Picture and sound must end together: frames shorter than the
    mix are held on the last frame (tpad clone), never left to a player's black; trailing frames that are black
    (mean luma < `dark`) beyond `max_black` (a <= 6-frame fade is allowed) are cut, the mix with them (60 ms fade).
    Returns (duration, pad_frames, report)."""
    from PIL import Image
    if not os.path.isdir("frames"):
        sys.exit("no frames/ to mux (render the shots first, or use --audio-only)")
    fr = sorted(f for f in os.listdir("frames") if re.match(r"^\d{4}\.png$", f))
    if not fr:
        return dur, 0, dict(frames=0)
    nfr = len(fr); need = int(round(dur * fps))
    used = fr[:min(nfr, need)]
    black = 0
    for f in reversed(used[-60:]):
        im = Image.open(os.path.join("frames", f)).convert("L").resize((54, 96))
        if sum(im.getdata()) / (54 * 96) < dark:
            black += 1
        else:
            break
    rep = dict(frames=nfr, frames_needed=need, trailing_black=black)
    d = dur
    if black > max_black:
        keep = len(used) - black + max_black
        d = keep / fps; rep["trimmed_to_frames"] = keep
        print(f"tail: {black} black frames at the end -> cut to {keep} frames ({d:.2f} s); end on picture, not black")
    pad = max(0, int(round(d * fps)) - nfr)
    if pad:
        rep["held_last_frame"] = pad
        print(f"tail: frames end {pad} frame(s) before the sound: holding the last frame (never a black tail)")
    rep["duration"] = round(d, 3)
    return d, pad, rep


dur, _pad, _tail = tail_check()
if _tail.get("trimmed_to_frames"):
    _t = os.path.join("audio", "mix_trim.m4a")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join("audio", "mix.m4a"), "-t", f"{dur:.3f}", "-af",
                    f"afade=t=out:st={max(0, dur - 0.06):.3f}:d=0.06", "-c:a", "aac", "-b:a", "192k", _t], check=True)
    os.replace(_t, os.path.join("audio", "mix.m4a"))
json.dump(_tail, open(os.path.join("out", "tail_report.json"), "w"), indent=1)
_vpad = [f"tpad=stop_mode=clone:stop={_pad}"] if _pad else []
base = ["ffmpeg", "-v", "error", "-y", "-framerate", "30", "-i", os.path.join("frames", "%04d.png"),
        "-i", os.path.join("audio", "mix.m4a")]
enc = ["-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p", "-c:a", "copy", "-t", f"{dur:.3f}",
       "-movflags", "+faststart"]
subprocess.run(base + (["-vf", ",".join(_vpad)] if _vpad else []) + enc + [os.path.join("out", "final_nocaptions.mp4")], check=True)
def _has_ass():
    r = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True)
    return re.search(r"\bass\b", r.stdout) is not None


if not o.no_captions:
    if o.captions == "ass" and _has_ass():
        subprocess.run(base + ["-vf", ",".join(_vpad + ["ass=captions.ass"])] + enc + [os.path.join("out", "final.mp4")], check=True)
    else:
        if o.captions == "ass":
            print("ffmpeg has no libass: using caption style v2 instead")
        subprocess.run([sys.executable, os.path.join(HERE, "captions2.py"), o.slug], check=True)
        enc_c = [x for x in enc]
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", "30", "-i", os.path.join("frames", "%04d.png"),
                        "-framerate", "30", "-i", os.path.join("caps", "%04d.png"), "-i", os.path.join("audio", "mix.m4a"),
                        "-filter_complex", f"[0:v]{_vpad[0] + ',' if _vpad else ''}null[b];[b][1:v]overlay=format=auto:eof_action=pass,format=yuv420p[v]",
                        "-map", "[v]", "-map", "2:a"] +
                       enc_c + [os.path.join("out", "final.mp4")], check=True)
        kit.rm_tree("caps")
# 3b. frames are scratch: the finished videos are the product
if kit.cfg().get("auto_clean_frames") and os.path.exists(os.path.join("out", "final.mp4")) and os.environ.get("KEEP_FRAMES") != "1":
    pass  # cleaned after the phone copy below
# 4. phone copy (under ~25 MB so it can be sent to a phone)
src_v = os.path.join("out", "final.mp4" if not o.no_captions else "final_nocaptions.mp4")
vbr = min(6000, max(800, int(25 * 8 * 1024 / dur) - 160))   # 25 MB budget, capped: short clips need no 15 Mbps at 720p
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src_v, "-vf", "scale=720:1280", "-c:v", "libx264", "-preset", "slow",
                "-b:v", f"{vbr}k", "-maxrate", f"{int(vbr * 1.2)}k", "-bufsize", f"{vbr * 2}k", "-c:a", "aac", "-b:a", "128k",
                "-movflags", "+faststart", os.path.join("out", "final_phone.mp4")], check=True)
print("done:", os.path.join(vdir, "out", "final.mp4"), f"{dur:.2f}s")
if os.path.exists(".keep_frames"):     # integration tests (test_seq) and any video marked keep: never auto-cleaned
    print("frames/blend kept (.keep_frames marker)")
elif kit.cfg().get("auto_clean_frames") and os.environ.get("KEEP_FRAMES") != "1":
    kit.rm_tree("frames")
    kit.rm_tree("blend")
    print("frames/blend removed (auto_clean_frames; set KEEP_FRAMES=1 to keep them)")
