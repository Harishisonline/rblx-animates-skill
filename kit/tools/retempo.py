"""Speed an already-processed voice (voice.wav + words.json + sentences.json) by a further factor,
scaling every timestamp exactly. Use it to hit the target words-per-minute without re-running whisper.
python tools/retempo.py <slug> <factor>        e.g. 1.06
python tools/retempo.py <slug> --wpm 258       computes the factor from the current wpm
Holds (tools/holds.py) keep their original pause length: silence is put back in the middle of those gaps after the
speed-up, and every later timestamp (words, sentences, cues.json, beats.json) moves with it."""
import json, os, subprocess, sys, wave
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import holds as H  # noqa: E402

STUDIO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
slug = sys.argv[1]
adir = os.path.join(STUDIO, "videos", slug, "audio")
words = json.load(open(os.path.join(adir, "words.json"), encoding="utf-8"))
dur = words[-1]["end"]
wpm = len(words) / dur * 60
f = (float(sys.argv[3]) / wpm) if sys.argv[2] == "--wpm" else float(sys.argv[2])
if f > 1.12 and "--force" not in sys.argv:
    sys.exit(f"factor {f:.3f} is above 1.12: it would sound sped-up. Re-read the script slower/tighter, or pass --force.")
src, tmp = os.path.join(adir, "voice.wav"), os.path.join(adir, "voice_tmp.wav")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af", f"atempo={f:.5f}", "-ar", "48000", "-ac", "1", tmp], check=True)
os.replace(tmp, src)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-c:a", "aac", "-b:a", "192k", os.path.join(adir, "voice.m4a")], check=True)
req = H.gap_holds(words, H.holds(adir, words))
orig_gap = {i: words[i + 1]["start"] - words[i]["end"] for i in req}
for w in words:
    w["start"] = round(w["start"] / f, 3); w["end"] = round(w["end"] / f, 3)
# put the protected pauses back: insert silence mid-gap so each hold gap is as long as before the speed-up
ins = []  # (time in sped-up voice, seconds)
for i in sorted(req):
    a, b = words[i]["end"], words[i + 1]["start"]
    add = round(max(0.0, min(orig_gap[i], max(orig_gap[i], req[i])) - (b - a)), 3)
    if add > 0.01: ins.append(((a + b) / 2, add))
if ins:
    with wave.open(src) as w_:
        sr_, ch_ = w_.getframerate(), w_.getnchannels(); x = np.frombuffer(w_.readframes(w_.getnframes()), "<i2").reshape(-1, ch_)
    parts, last = [], 0
    for t_, d_ in ins:
        k = int(t_ * sr_); parts += [x[last:k], np.zeros((int(d_ * sr_), ch_), "<i2")]; last = k
    parts.append(x[last:])
    with wave.open(src, "wb") as w_:
        w_.setnchannels(ch_); w_.setsampwidth(2); w_.setframerate(sr_); w_.writeframes(np.concatenate(parts).tobytes())
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-c:a", "aac", "-b:a", "192k", os.path.join(adir, "voice.m4a")], check=True)
def later(t):
    return t + sum(d_ for t_, d_ in ins if t >= t_)
for w in words:
    w["start"] = round(later(w["start"]), 3); w["end"] = round(later(w["end"]), 3)
H.shift_files(adir, lambda t: later(t / f))
json.dump(words, open(os.path.join(adir, "words.json"), "w", encoding="utf-8"), indent=0, ensure_ascii=False)
sp = os.path.join(adir, "sentences.json")
if os.path.exists(sp):
    S = json.load(open(sp, encoding="utf-8"))
    for s in S:
        s["start"] = round(later(s["start"] / f), 3); s["end"] = round(later(s["end"] / f), 3)
        s["startFrame"] = int(round(s["start"] * 30)); s["endFrame"] = int(round(s["end"] * 30))
    json.dump(S, open(sp, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
log = os.path.join(adir, "tempo_log.txt")
open(log, "a").write(f"retempo x{f:.4f}: {wpm:.1f} wpm -> {wpm * f:.1f} wpm, {dur:.2f}s -> {dur / f:.2f}s\n")
print(f"x{f:.4f}: {wpm:.1f} -> {wpm * f:.1f} wpm, {dur:.2f}s -> {dur / f:.2f}s"
      + (f"; {len(ins)} hold pauses restored (+{sum(d for _, d in ins):.2f}s)" if ins else ""))
