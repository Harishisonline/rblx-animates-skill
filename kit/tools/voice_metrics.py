"""Voice hype metrics for a narration take (docs/VOICE_SPEC.md 'HYPE recipe').
    <earshot venv python> tools/voice_metrics.py <audio> [--words words.json] [--json]
Measures (no listening, numbers only):
  wpm            words / (last word end - first word start)       needs --words (list of {word,start,end})
  pause_med/p90  gaps between consecutive words >= 0.12 s           needs --words
  f0 median Hz, f0 range st (p95/p5 in semitones), f0 sd st          librosa pyin on voiced frames
  rms_sd_db      std of 50 ms RMS (dB) over voiced frames            loudness movement = 'energy variance'
  energy10       mean RMS dB per 10 s window (energy curve)
Target band for hype formats (measured EP1 vs tests, 2026-11-14): see VOICE_SPEC.md."""
import json, sys
import numpy as np
import librosa


def metrics(path, words=None):
    y, sr = librosa.load(path, sr=22050, mono=True)
    hop = int(0.05 * sr)
    rms = librosa.feature.rms(y=y, frame_length=2 * hop, hop_length=hop)[0]
    db = 20 * np.log10(rms + 1e-9)
    voiced_e = db > (db.max() - 35)
    f0, vf, _ = librosa.pyin(y, fmin=70, fmax=500, sr=sr, frame_length=2048, hop_length=512)
    f0 = f0[vf & ~np.isnan(f0)]
    st = 12 * np.log2(f0 / np.median(f0)) if len(f0) else np.array([0.0])
    out = dict(dur_s=round(len(y) / sr, 2), f0_med_hz=round(float(np.median(f0)), 1) if len(f0) else None,
               f0_range_st=round(float(np.percentile(st, 95) - np.percentile(st, 5)), 2),
               f0_sd_st=round(float(np.std(st)), 2), rms_sd_db=round(float(np.std(db[voiced_e])), 2))
    win = int(10 / 0.05)
    out["energy10_db"] = [round(float(np.mean(db[i:i + win][voiced_e[i:i + win]])), 1)
                          for i in range(0, len(db), win) if voiced_e[i:i + win].any()]
    if words:
        t0, t1 = words[0]["start"], words[-1]["end"]
        gaps = [b["start"] - a["end"] for a, b in zip(words, words[1:]) if b["start"] - a["end"] >= 0.12]
        out.update(words=len(words), wpm=round(len(words) / (t1 - t0) * 60, 1),
                   pause_med_s=round(float(np.median(gaps)), 2) if gaps else 0,
                   pause_p90_s=round(float(np.percentile(gaps, 90)), 2) if gaps else 0, pauses=len(gaps))
    return out


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    w = json.load(open(a[a.index("--words") + 1])) if "--words" in a else None
    if isinstance(w, dict):
        w = w.get("words", [])
    print(json.dumps(metrics(a[0], w), indent=None if "--json" in a else 1))
