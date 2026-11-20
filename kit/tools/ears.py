"""EARS (kit v6.0, 2026-11-19): measure a narration like the viral reference measurements - word timings (faster-whisper),
pauses by position, pitch (Praat) and sentence-end melody. Used by ears_check.py (QA gate), growth_scan.py (weekly
viral re-measure) and research/ears. For audio with music, separate=True first isolates the voice (demucs htdemucs).
Needs: faster-whisper, praat-parselmouth, soundfile, numpy (+ demucs, torch for separate=True). On the Mac the venv
~/RobloxStories_tmp/blocky_laugh/.venv has them all (`EARS_PY` env overrides)."""
import glob, json, os, re, subprocess, sys, tempfile
import numpy as np

_model = None

def _st(hz): return 12 * np.log2(hz / 100.0)

def to_vocals(src, workdir, separate=False):
    os.makedirs(workdir, exist_ok=True)
    base = os.path.splitext(os.path.basename(src))[0]
    wav = os.path.join(workdir, base + "_vox16k.wav")
    if os.path.exists(wav) and os.path.getmtime(wav) >= os.path.getmtime(src): return wav
    if not separate:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-ac", "1", "-ar", "16000", wav], check=True); return wav
    tmp = os.path.join(workdir, base + "_in.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-ac", "2", "-ar", "44100", tmp], check=True)
    subprocess.run([sys.executable, "-m", "demucs", "--two-stems=vocals", "-n", "htdemucs", "-o", os.path.join(workdir, "dm"), tmp],
                   check=True, capture_output=True)
    v = glob.glob(os.path.join(workdir, "dm", "htdemucs", base + "_in", "vocals.wav"))[0]
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", v, "-ac", "1", "-ar", "16000", wav], check=True)
    os.remove(tmp); return wav

def analyse(src, separate=False, workdir=None, model_size="small"):
    """Returns the metric dict (same keys as research/ears/out/*.json)."""
    global _model
    import soundfile as sf, parselmouth
    from faster_whisper import WhisperModel
    workdir = workdir or os.path.join(os.path.dirname(os.path.abspath(src)), ".ears")
    wav = to_vocals(src, workdir, separate)
    if _model is None: _model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segs, _ = _model.transcribe(wav, language="en", word_timestamps=True, beam_size=5, vad_filter=False)
    W = [{"w": w.word.strip(), "s": w.start, "e": w.end} for s in segs for w in s.words if w.word.strip()]
    y, sr = sf.read(wav); y = y.astype(np.float64)
    pitch = parselmouth.Sound(y, sr).to_pitch(time_step=0.01, pitch_floor=70, pitch_ceiling=500)
    f0 = pitch.selected_array["frequency"]; tt = pitch.xs()
    hop = int(0.01 * sr)
    db = 20 * np.log10(np.array([np.sqrt(np.mean(y[i:i + hop] ** 2) + 1e-12) for i in range(0, len(y) - hop, hop)]) + 1e-9)
    end_re = re.compile(r'[.!?]["\']?$')
    sents, cur = [], []
    for w in W:
        cur.append(w)
        if end_re.search(w["w"]): sents.append(cur); cur = []
    if cur: sents.append(cur)
    def f0_in(a, b):
        m = (tt >= a) & (tt <= b) & (f0 > 0); return f0[m]
    rows = []
    for s in sents:
        a, b = s[0]["s"], s[-1]["e"]; f = f0_in(a, b)
        tail = f0_in(max(a, b - 0.35), b); head = f0_in(a, min(b, a + 0.6))
        rows.append({"text": " ".join(w["w"] for w in s), "n": len(s), "t0": round(a, 2), "dur": round(b - a, 2),
                     "wps": round(len(s) / max(0.2, b - a), 2),
                     "f0_sd_st": round(float(np.std(_st(f))), 2) if len(f) > 5 else None,
                     "end_vs_start_st": round(float(np.mean(_st(tail)) - np.mean(_st(head))), 2) if len(tail) and len(head) else None})
    P = []
    for i in range(len(W) - 1):
        g = W[i + 1]["s"] - W[i]["e"]
        pos = "sent" if end_re.search(W[i]["w"]) else ("comma" if W[i]["w"].endswith((",", ";", ":")) else "mid")
        P.append({"g": round(g, 3), "pos": pos, "after": W[i]["w"], "before": W[i + 1]["w"], "t": round(W[i]["e"], 2)})
    span = (W[-1]["e"] - W[0]["s"]) if W else 1.0
    fv = f0[f0 > 0]
    q = lambda a, p: float(np.percentile(a, p))
    gs = lambda pos: [p["g"] for p in P if p["pos"] == pos]
    ends = [s["end_vs_start_st"] for s in rows if s["end_vs_start_st"] is not None]
    return {
        "src": src, "words": len(W), "span_s": round(span, 1), "wps": round(len(W) / span, 2),
        "first_word_s": round(W[0]["s"], 3) if W else None,
        "f0_median_hz": round(q(fv, 50), 1) if len(fv) else None,
        "f0_range_st_p10_p90": round(float(_st(q(fv, 90)) - _st(q(fv, 10))), 1) if len(fv) else None,
        "sent_end_falling_share": round(float(np.mean([e < -1 for e in ends])), 2) if ends else None,
        "sent_end_rising_share": round(float(np.mean([e > 1 for e in ends])), 2) if ends else None,
        "gap_after_sentence_med": round(float(np.median(gs("sent"))), 3) if gs("sent") else None,
        "gap_after_comma_med": round(float(np.median(gs("comma"))), 3) if gs("comma") else None,
        "sent_ends_paused_over_0.3": round(float(np.mean([g > 0.3 for g in gs("sent")])), 2) if gs("sent") else None,
        "pauses_0.3_0.6_per_min": round(sum(0.3 < p["g"] <= 0.6 for p in P) / span * 60, 1),
        "pauses_over_0.6_per_min": round(sum(p["g"] > 0.6 for p in P) / span * 60, 1),
        "long_pause_contexts": [f'{p["after"]} || {p["before"]} ({p["g"]}s @{p["t"]})' for p in P if p["g"] > 0.3][:30],
        "sentence_len_median": float(np.median([s["n"] for s in rows])) if rows else None,
        "sentences": rows, "transcript": " ".join(w["w"] for w in W), "words_t": W,
    }
