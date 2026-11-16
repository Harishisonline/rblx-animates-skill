"""Audio QA with earshot (https://github.com/leonxlnx/earshot): ears for an agent that cannot hear.
    python tools/audio_qa.py <slug> [--quick] [--film=out/other.mp4]  -> videos/<slug>/out/audio_report.md (+ .json)
Runs on out/final.mp4 (falls back to final_nocaptions.mp4): loudness/true peak (measure), the listening transcript with
sync of sound to picture cuts and the SFX cue frames (timeline), and the launch-video scorecard (critique, heavy models).
Targets: integrated loudness about -14 LUFS, true peak <= -1 dBTP, no sound landing > 40 ms off its cue, voice clearly on top.
earshot lives in ~/earshot (its own Python 3.11 venv); override with env EARSHOT=/path/to/earshot.
First call downloads ~1.1 GB of models (done once by `earshot doctor --fetch`). Use --quick to run only `measure` (no models).
Always (no models, ffmpeg only): music share (from audio/score.json or music.wav), escalation slope of the short-term loudness
(first 18 % vs 70-88 % of the runtime, LU/min fit), digital-silence share (room tone must fill the holds), holds honoured."""
import json, os, re, subprocess, sys, wave
import numpy as np

STUDIO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EARSHOT = os.environ.get("EARSHOT") or os.path.expanduser("~/earshot/.venv/bin/earshot")


def run(args, out_json=None):
    cmd = [EARSHOT] + args + (["--out", out_json] if out_json else [])
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def short_term(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-v", "verbose", "-i", path, "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True)
    f = lambda v: -120.0 if "inf" in v else float(v)
    pts = [(float(a), f(b), f(c)) for a, b, c in re.findall(r"t:\s*([\d.]+)\s+TARGET.*?M:\s*(-?[\d.inf]+)\s+S:\s*(-?[\d.inf]+)", r.stderr)]
    return np.array(pts) if pts else np.zeros((0, 3))


def _escalation(label, path, mood):
    st = short_term(path)
    if len(st) < 10 or label == "full mix":
        return []
    T = st[-1, 0]; t = st[:, 0]; s = st[:, 2]; v = s > -70
    early = s[(t < 0.18 * T) & v]; late = s[(t > 0.70 * T) & (t < 0.88 * T) & v]
    if not (len(early) and len(late)):
        return []
    rise = late.mean() - early.mean()
    want = (3, 9) if mood in ("horror", "mystery", None) else (0, 9)
    return [f"- escalation of the {label}: first 18% {early.mean():.1f}, 70-88% {late.mean():.1f} LUFS-S -> rise {rise:+.1f} LU "
            f"(target {want[0]}..{want[1]}, REF4 4-6) -> {'ok' if want[0] <= rise <= want[1] else 'CHECK'}"]


def story_checks(film, vdir):
    """music share + loudness escalation + silence: REF4 rules (docs/REF4_HORROR_STORY_AUDIO.md section 4-5)."""
    adir = os.path.join(vdir, "audio")
    out = ["## Story-sound checks (ffmpeg, no models)"]
    sc = os.path.join(adir, "score.json")
    mood = None
    if os.path.exists(sc):
        info = json.load(open(sc)); mood = info.get("mood"); ap = info.get("active_pct", {})
        mel = ap.get("melodic", 0)
        lim = {"horror": 45, "mystery": 90}.get(mood, 100)
        out.append(f"- score: {mood}, key {info.get('key')} {info.get('bpm')} bpm, seed {info.get('seed')}, motif x{info.get('motif_placements')}")
        out.append(f"- music share: melodic {mel}% / bed {ap.get('bed')}% / pulse {ap.get('pulse')}% of runtime "
                   f"(target melodic <= {lim}% for {mood}) -> {'ok' if mel <= lim else 'TOO MUCH MUSIC: lower motif/pad beats'}")
    elif os.path.exists(os.path.join(adir, "music.wav")):
        with wave.open(os.path.join(adir, "music.wav")) as w:
            x = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(float).reshape(-1, w.getnchannels()).mean(1)
            hop = w.getframerate() // 10
        e = np.sqrt((x[:len(x) // hop * hop].reshape(-1, hop) ** 2).mean(1) + 1e-9)
        out.append(f"- music share: {100 * (e > e.max() * 10 ** (-35 / 20)).mean():.0f}% of runtime (plain music file, no score.json; "
                   "horror target <= 35-45%)")
    mp = os.path.join(adir, "music.wav")
    for label, path in ((("music bed (music.wav)", mp),) if os.path.exists(mp) else ()) + (("full mix", film),):
        out += _escalation(label, path, mood)
    st = short_term(film)
    if len(st) > 10:
        T = st[-1, 0]; s = st[:, 2]; t = st[:, 0]
        valid = s > -60
        early = s[(t < 0.18 * T) & valid]; late = s[(t > 0.70 * T) & (t < 0.88 * T) & valid]
        if len(early) and len(late):
            rise = late.mean() - early.mean()
            k = np.polyfit(t[valid], s[valid], 1)[0] * 60 if valid.sum() > 5 else 0
            want = (2, 8) if mood in ("horror", "mystery", None) else (-2, 8)
            out.append(f"- escalation (full mix, voice-dominated, info): first 18% {early.mean():.1f} LUFS-S, 70-88% {late.mean():.1f} LUFS-S -> rise {rise:+.1f} LU "
                       f"(target {want[0]}..{want[1]} LU, REF4 4-6), slope {k:+.1f} LU/min -> "
                       f"{'ok' if want[0] <= rise <= want[1] else 'CHECK: ' + ('flat/falling: lift late beats or lower the hook' if rise < want[0] else 'too steep')}")
        st_ = st[st[:, 0] >= 0.45]   # ebur128's 400 ms momentary window is empty (-120) for the first 0.3 s: not silence
        dz = (st_[:, 1] < -60).mean() if len(st_) else 0.0
        out.append(f"- near-silence (< -60 LUFS momentary): {100 * dz:.1f}% of 100 ms frames -> "
                   f"{'ok' if dz < 0.01 else 'digital silence found: room tone missing (tools/ambience.py)'}")
    hp = os.path.join(adir, "cues.json")
    if os.path.exists(hp) and len(st):
        hl = [c for c in json.load(open(hp)) if str(c.get("beat", "")).lower() in ("hold", "silence")]
        for h in hl:
            m = (st[:, 0] >= h["t"] + 0.4) & (st[:, 0] <= h["t"] + float(h.get("dur") or 0.6))
            out.append(f"- hold at {h['t']:.2f}s: momentary {st[m, 1].mean() if m.any() else float('nan'):.1f} LUFS-M (music/sfx cut, voice + room tone only)")
    return out + [""]


def _decode(path, sr=48000):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "2", "-ar", str(sr), "-f", "f32le", "-"],
                         stdout=subprocess.PIPE).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64).reshape(-1, 2)


def mix_checks(film, vdir, fps=30):
    """R2 targets (ffmpeg + numpy, no models): stereo width (side under mid, REF1 -14.5..-5, target -14..-8), loudness
    range (REF1 median 5.5 LU, target >= 4), the duck under the voice (3-6 dB, from audio/mix_report.json), music dips
    before cuts, and every transition cut's accent: the strongest onset within +-150 ms must sit within 1 frame."""
    out = ["## Mix checks (stereo, dynamics, ducking, transition accents)"]
    x = _decode(film); sr = 48000
    if not len(x):
        return out + ["- no audio", ""]
    M = (x[:, 0] + x[:, 1]) / 2; S = (x[:, 0] - x[:, 1]) / 2
    sd = 20 * np.log10((np.sqrt((S ** 2).mean()) + 1e-12) / (np.sqrt((M ** 2).mean()) + 1e-12))
    out.append(f"- stereo: side {sd:.1f} dB under mid (target -14..-8, REF1 -14.5..-5) -> {'ok' if -14.5 <= sd <= -5 else 'CHECK'}")
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", film, "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    m = re.search(r"LRA:\s+(-?[\d.]+) LU", r[r.rfind("Summary:"):])
    lra = float(m.group(1)) if m else None
    out.append(f"- loudness range: LRA {lra} LU (target >= 4, REF1 median 5.5) -> {'ok' if lra is not None and lra >= 4 else 'CHECK'}")
    rp = os.path.join(vdir, "audio", "mix_report.json")
    rep = json.load(open(rp)) if os.path.exists(rp) else {}
    if rep:
        du = rep.get("duck_db_applied")
        out.append(f"- duck under the voice: applied {du} dB (target -3..-6), music level talk vs gaps {rep.get('duck_db_measured')} dB, "
                   f"phrase gaps {rep.get('gap_pct')} % -> {'ok' if du is not None and -6.5 <= du <= -2.5 else 'CHECK'}")
        out.append(f"- music dips before cuts/reveals: {len(rep.get('dips', []))} at {rep.get('dips')}")
    trans = rep.get("transitions", [])
    if trans:
        mono = np.abs(M); hop = int(0.002 * sr); k = len(mono) // hop
        e = 20 * np.log10(np.sqrt((M[:k * hop].reshape(k, hop) ** 2).mean(1)) + 1e-9)
        sm = np.convolve(e, np.ones(5) / 5, "same")
        flux = np.maximum(0, sm[10:] - sm[:-10]); flux = np.concatenate([np.zeros(10), flux])   # 20 ms rise
        ok = 0
        for tr in trans:
            c = int(tr["t"] / 0.002); a, b = max(0, c - 75), min(k, c + 75)
            i = a + int(np.argmax(flux[a:b])); off = (i - c) * 2.0
            f1 = int(1000 / fps / 2.0); a1, b1 = max(0, c - f1), min(k, c + f1 + 1)
            j = a1 + int(np.argmax(flux[a1:b1])); off1, rise1 = (j - c) * 2.0, float(flux[j])
            good = rise1 >= 6          # an attack of >= 6 dB / 20 ms within ONE frame of the cut (voice onsets nearby may be bigger)
            ok += good
            out.append(f"- {tr['kind']} cut {tr['t']:.3f}s: attack within 1 frame {off1:+.0f} ms +{rise1:.1f} dB/20 ms "
                       f"(strongest in +-150 ms: {off:+.0f} ms +{float(flux[i]):.1f} dB), pan {tr.get('pan')} "
                       f"-> {'ok' if good else 'CHECK (no clear accent on the cut)'}")
        out.append(f"- transition accents on the cut: {ok}/{len(trans)}")
    return out + [""]


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    slug = sys.argv[1]
    quick = "--quick" in sys.argv
    vdir = os.path.join(STUDIO, "videos", slug)
    out = os.path.join(vdir, "out")
    os.makedirs(out, exist_ok=True)
    alt = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--film=")), None)   # e.g. --film=out/fix_audio_v2.mp4
    film = os.path.join(vdir, alt) if alt else next((p for p in [os.path.join(out, f) for f in ("final.mp4", "final_nocaptions.mp4")] + [os.path.join(vdir, "audio", "mix.m4a")]
                 if os.path.exists(p)), None)   # mix.m4a: after finish.py --audio-only
    if not film:
        sys.exit("no out/final.mp4 yet: run finish.py first")
    if not os.path.exists(EARSHOT):
        sys.exit(f"earshot not found at {EARSHOT} (install: see ~/.claude/skills/earshot/SKILL.md)")
    cues = os.path.join(vdir, "audio", "cues.json")
    lines = [f"# Audio QA: {slug}", f"file: {film}", ""]
    rc, txt = run(["measure", film], os.path.join(out, "audio_measure.json"))
    lines += ["## Loudness (measure)", "```", txt.strip()[:2500], "```", ""]
    lines += story_checks(film, vdir)
    lines += mix_checks(film, vdir)
    if not quick:
        tl = ["timeline", film] + (["--video", film] if film.endswith(".mp4") else [])
        if os.path.exists(cues):
            tl += ["--cues", cues]
        rc, txt = run(tl, os.path.join(out, "audio_timeline.json"))
        lines += ["## Listening transcript and sync (timeline)", "```", txt.strip()[:6000], "```", ""]
        rc, txt = run(["critique", film] + (["--video", film] if film.endswith(".mp4") else []), os.path.join(out, "audio_critique.json"))
        lines += ["## Scorecard (critique)", "```", txt.strip()[:4000], "```", ""]
    open(os.path.join(out, "audio_report.md"), "w", encoding="utf-8").write("\n".join(lines))
    print("\n".join(lines)[:3500])
    print("\nwritten:", os.path.join(out, "audio_report.md"))


if __name__ == "__main__":
    main()
