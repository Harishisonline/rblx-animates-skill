"""Generative ORIGINAL score: a unique music bed per video, written from the story's beat map (numpy only, no samples,
no copyrighted music). Replaces the old house track that was reused on every video.

    python tools/score.py <slug> [--mood horror] [--seed N]          -> videos/<slug>/audio/score.wav (+ score.json, stems/)
    python tools/score.py --beats beats.json --dur 85 --mood mystery --out demo.wav [--lufs -14] [--stems DIR]
    python tools/score.py --demo-beats 85 > beats.json               a template beat map (REF4 proportions) to edit

BEAT MAP (where each beat starts; a beat lasts until the next one):
    [{"t": 0, "type": "hook"}, {"t": 4, "type": "rule"}, {"t": 18, "type": "dread"}, {"t": 41, "type": "hold", "dur": 0.6},
     {"t": 52, "type": "reveal"}, ... {"t": 80, "type": "cta"}]
  With a slug the map is read from videos/<slug>/audio/beats.json, else from beat cues inside cues.json
  ({"t":..,"beat":"dread"}), else built automatically from sentences.json at the STORY_ENGINE proportions.
  Types: hook rule plant dread reveal climax cliffhanger twist cta hold (aliases: warm=plant, escalate/turn=dread,
  name=reveal, callback=cta, silence=hold). "hold" = hard cut of the music to silence for "dur" seconds (default 0.6),
  the room tone keeps going (mix.py) so it is never digital zero.

MOODS: horror mystery comedy emotional adventure. Every run draws a new key, tempo, motif, chord path and timbre detail
from the seed (default: random; the seed is printed and saved in score.json so a take can be re-made exactly).

LAYERS (each a stem): drone (detuned saws + slow LFO, lowpass opens with intensity), pad (chord, slow attack),
cluster (minor-second shimmer for dread), air (filtered noise band), pulse (heartbeat / clock tick / pizzicato bounce /
low toms, by mood), motif (a 4-6 note theme on an FM bell / celesta / marimba / soft piano / horn, placed only on
plant/reveal/cta for horror and phrase-wise otherwise), riser (noise sweep + rising glide, into reveal/climax),
hit (sub drop + air burst on reveal/climax), all through a convolution reverb made per run.
The score level is calibrated (default -24 LUFS) so mix.py can lay it under the voice as is (finish.py --music-source score).
"""
import argparse, json, os, subprocess, sys, zlib
import numpy as np

SR = 48000
HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
ALIAS = {"warm": "plant", "escalate": "dread", "turn": "dread", "name": "reveal", "callback": "cta", "silence": "hold",
         "rules": "rule", "outro": "cta", "intro": "hook"}
TYPES = ("hook", "rule", "plant", "dread", "reveal", "climax", "cliffhanger", "twist", "cta", "hold")

# per beat type: target layer levels 0..1 and brightness 0..1 (mood multipliers applied later)
SECTION = {
    "hook":        dict(drone=.8, pad=.15, cluster=.0, air=.5, pulse=.0, bright=.25, rate=1.0),
    "rule":        dict(drone=.6, pad=.25, cluster=.0, air=.5, pulse=.45, bright=.3, rate=1.0),
    "plant":       dict(drone=.35, pad=.55, cluster=.0, air=.3, pulse=.2, bright=.45, rate=1.0),
    "dread":       dict(drone=.8, pad=.3, cluster=.55, air=.6, pulse=.7, bright=.45, rate=1.0),
    "reveal":      dict(drone=.95, pad=.5, cluster=.35, air=.5, pulse=.0, bright=.7, rate=1.0),
    "climax":      dict(drone=1., pad=.7, cluster=.6, air=.6, pulse=1., bright=.85, rate=2.0),
    "cliffhanger": dict(drone=.85, pad=.45, cluster=.7, air=.7, pulse=.8, bright=.6, rate=1.5),
    "twist":       dict(drone=.4, pad=.7, cluster=.0, air=.5, pulse=.0, bright=.4, rate=1.0),
    "cta":         dict(drone=.45, pad=.55, cluster=.0, air=.35, pulse=.3, bright=.4, rate=1.0),
    "hold":        dict(drone=0, pad=0, cluster=0, air=0, pulse=0, bright=.2, rate=1.0),
}
# moods: modes (scale steps), bass root MIDI range, tempo range, instruments, layer multipliers, motif placement
MOODS = {
    "horror": dict(modes=[[0, 1, 3, 5, 7, 8, 10], [0, 2, 3, 5, 7, 8, 10]], root=(36, 42), bpm=(54, 64), motif="musicbox",
                   pad_kind="glass", drone_harm=4, rests=(3.0, 5.0, 1.5, 2.5),
                   pulse="heart", reverb=3.8, mult=dict(drone=1.0, pad=.55, cluster=1.0, air=1.0, pulse=.9, motif=1.0),
                   motif_on=("plant", "reveal", "cta", "twist"), motif_max=4, pad_on=("plant", "reveal", "twist", "cta"), chords=[[0, 5, 3, 4], [0, 3, 5, 6], [0, 6, 5, 4]],
                   detune_reveal=True, escalate_db=4.0),
    # mystery = dark and sparse (D7: the old glass/celesta motif + 2 kHz clock ticks read as 'inspirational corporate,
    # celesta' and 'chat message pop'): low aeolian/phrygian-ish root, slow, a BOWED motif (no strike), bowed metal
    # throughout at low level, a muffled low clock instead of bright ticks, motif on hook/plant/reveal/cliffhanger.
    # The HOOK states the motif: a drone-only hook is not heard as music under the VO (earshot AST Music < 0.3 in the
    # first 5 s window -> critical "no music at 0:00-0:05"; 2 of 4 test_seq seeds failed before, 0 of 6 after).
    # R2 D7: the full mix still tagged 'inspirational corporate background music'. Causes: the chord paths [0,5,2,4] /
    # [0,5,6,4] are i-VI-III-v / i-VI-VII-v (the pop/corporate loop), a steady 2x-tempo clock tick under it, and a
    # glass/sine pad. Now: low dark STRING pad (filtered saws, octave down), a low PIZZ ostinato on the root/fifth
    # (cello pizz, uneven accents) instead of the clock, the bowed motif in the cello/viola range, and modal paths that never
    # resolve upward (i-bII, i-iv-i, i-bVI-iv): no bright glock/celesta/chime lead anywhere.
    "mystery": dict(modes=[[0, 2, 3, 5, 7, 8, 10], [0, 1, 3, 5, 7, 8, 10]], root=(33, 40), bpm=(58, 70), motif="bowed",
                    motif_oct=1, pad_kind="strings_dark", pad_oct=0, drone_harm=3, rests=(4.0, 6.5, 1.3, 2.0), no_pizz=True,
                    # R3-2: no pizz ostinato (earshot tagged its plucks 'glockenspiel/celesta note', 'chat message pop'):
                    # a dark pad + drone + bowed motif only; rests keep the bed up (R4-1), sub swells on reveals (R4-2)
                    pulse="none", reverb=3.2, mult=dict(drone=1.0, pad=.75, cluster=.8, air=.6, pulse=.0, motif=.85),
                    rest_bed_db=0.0, rest_swell_db=3.0, reveal_sub_db=5.0,
                    motif_on=("hook", "plant", "reveal", "cliffhanger", "twist"), motif_max=4, bowed_always=True,
                    chords=[[0, 3, 0, 5], [0, 1, 0, 3], [0, 5, 3, 0]], detune_reveal=False, escalate_db=4.0),
    "comedy": dict(modes=[[0, 2, 4, 5, 7, 9, 11], [0, 2, 4, 5, 7, 9, 10]], root=(41, 48), bpm=(104, 124), motif="marimba",
                   pulse="pizz", reverb=1.3, mult=dict(drone=.0, pad=.45, cluster=.0, air=.15, pulse=1.1, motif=1.0),
                   motif_on=("hook", "rule", "plant", "dread", "reveal", "climax", "cliffhanger", "cta", "twist"), motif_max=99,
                   chords=[[0, 3, 4, 0], [0, 5, 3, 4], [0, 4, 5, 3]], detune_reveal=False, escalate_db=2.0),
    "emotional": dict(modes=[[0, 2, 4, 5, 7, 9, 11], [0, 2, 3, 5, 7, 8, 10]], root=(38, 46), bpm=(64, 76), motif="piano",
                      pulse="none", reverb=3.2, mult=dict(drone=.45, pad=1.0, cluster=.0, air=.4, pulse=.0, motif=1.0),
                      motif_on=("hook", "plant", "reveal", "twist", "cta", "cliffhanger"), motif_max=8,
                      chords=[[0, 5, 3, 4], [0, 4, 5, 3], [5, 3, 0, 4]], detune_reveal=False, escalate_db=3.0),
    "adventure": dict(modes=[[0, 2, 3, 5, 7, 9, 10], [0, 2, 4, 6, 7, 9, 11]], root=(38, 45), bpm=(92, 112), motif="horn",
                      pulse="toms", reverb=2.4, mult=dict(drone=.7, pad=.85, cluster=.0, air=.5, pulse=1.0, motif=.9),
                      motif_on=("hook", "plant", "reveal", "climax", "cliffhanger", "cta", "twist"), motif_max=9,
                      chords=[[0, 6, 5, 4], [0, 3, 4, 6], [0, 5, 6, 4]], detune_reveal=False, escalate_db=4.0),
}
PRE_HIT_REST = 0.5   # melodic layers rest this long before a reveal/climax hit (0.9 s left the last window musicless)
FIRST_REST_S = 5.0
END_PLAY_S = 3.0     # and none in the last 3 s
END_FADE_S = 0.35    # final fade of the score   # no rest before this: earshot critique scores music presence per 5 s window (3.5 failed seed 22)
HOOK_ESC_DB = -1.0   # escalation floor inside the hook section (dB)
# R3-2: melodic layers (motif + pad) must be OUT for a share of the runtime: mood limit (audio_qa) minus a margin.
# The rest pass guarantees it: random rests first, then breaths before section boundaries (= cuts, where mix.py dips
# the music anyway), then the longest remaining stretch, until the budget is met. Every melodic stem obeys the rests
# (the motif used to ring straight through them: a rest only gated pad + pulse -> 96.8 % melodic on test_seq).
MELODIC_MAX = dict(horror=45, mystery=90)
MELODIC_MARGIN = 6.0      # aim this many % under the limit (smoothing + reverb tails eat into the rests)
BREATH_S = (0.55, 0.9)    # a pre-boundary breath: rest this long before a section start
# R3-4: a hit in the last END_HIT_S of the film is the ending button, not a new section bed: shorter sub tail and lower
# level, so the ending does not jump 2-3 LU over the body (earshot: 'sub bass drop' 1.9 s tails at the end, +2.7 LU).
END_HIT_S, END_HIT_DB, END_HIT_TAIL = 2.5, -4.0, 0.4
# R4-2: sub -17 -> -11 and tuned into the 36-56 Hz octave (it sat at 55-82 Hz = 'low' band): the full mix measured
# sub -23.2 dB share vs REF1 -16.2..-4.1. Reveal/climax/dread/twist sections lift it further (mood reveal_sub_db).
LEVEL_DB = dict(bowed=-22, drone=-14, pad=-20, cluster=-34, air=-34, pulse=-15, motif=-14, riser=-20, hit=-15, sub=-11)
# R4-1: in a melodic rest the bed dips REST_BED_DB (mood rest_bed_db overrides) and swells rest_swell_db: -9 dB for every
# mood left a rest under a 0.3 s phrase gap at -35 LUFS (earshot 'drop' at 6.15 s on test_seq).
REST_BED_DB = -9.0
SEND = dict(bowed=.6, sub=0.0, drone=.12, pad=.35, cluster=.5, air=.25, pulse=.18, motif=.5, riser=.35, hit=.55)


def mtof(m):
    return 440.0 * 2 ** ((np.asarray(m, float) - 69) / 12)


def db(d):
    return 10 ** (d / 20)


# ---------------------------------------------------------------- dsp helpers (numpy only)
def spectral_filter(x, lo_curve=None, hi_curve=None, n_fft=2048, order=2):
    """Time-varying filter by STFT masks. x: (n,) or (n,2). hi_curve = lowpass cutoff per sample (Hz), lo_curve = highpass."""
    if x.ndim == 2:
        return np.stack([spectral_filter(x[:, c], lo_curve, hi_curve, n_fft, order) for c in range(x.shape[1])], 1)
    hop = n_fft // 4
    n = len(x)
    pad = np.pad(x, (n_fft, n_fft + hop))
    win = np.hanning(n_fft)
    nfr = (len(pad) - n_fft) // hop
    idx = np.arange(n_fft)[None, :] + hop * np.arange(nfr)[:, None]
    F = np.fft.rfft(pad[idx] * win, axis=1)
    f = np.fft.rfftfreq(n_fft, 1 / SR)[None, :]
    centers = np.clip(np.arange(nfr) * hop + n_fft // 2 - n_fft, 0, n - 1)
    M = np.ones_like(F, dtype=float)
    if hi_curve is not None:
        fc = np.asarray(hi_curve, float)[centers][:, None] if np.ndim(hi_curve) else np.full((nfr, 1), hi_curve)
        M *= 1 / np.sqrt(1 + (f / fc) ** (2 * order))
    if lo_curve is not None:
        fc = np.asarray(lo_curve, float)[centers][:, None] if np.ndim(lo_curve) else np.full((nfr, 1), lo_curve)
        M *= 1 / np.sqrt(1 + (fc / np.maximum(f, 1)) ** (2 * order))
    y = np.fft.irfft(F * M, n_fft, axis=1) * win
    out = np.zeros(len(pad) + n_fft); norm = np.zeros(len(pad) + n_fft)
    _ola(out, y, hop); _ola(norm, np.broadcast_to(win ** 2, y.shape), hop)
    out = out / np.maximum(norm, 1e-3)
    return out[n_fft:n_fft + n]


def _ola(out, frames, hop):
    """overlap-add: frames hop apart; every (n_fft/hop)-th frame does not overlap, so add those groups as one slab."""
    nf, n_fft = frames.shape
    k = n_fft // hop
    for g in range(k):
        fr = frames[g::k]
        a = g * hop
        out[a:a + fr.size] += fr.reshape(-1)


def compress(x, thr_db=-10.0, ratio=2.5, win=0.4):
    """slow RMS bus compressor (relative to the score's own loud level): keeps the loudness range for an underscore."""
    hop = int(0.01 * SR)
    m = (x ** 2).mean(1)
    nb = len(m) // hop
    e = np.sqrt(m[:nb * hop].reshape(nb, hop).mean(1) + 1e-12)
    e = np.sqrt(smooth(e ** 2, win, 100))
    ref = np.percentile(e[e > 0], 95)
    lvl = 20 * np.log10(e / ref + 1e-9)
    gdb = np.where(lvl > thr_db, (thr_db - lvl) * (1 - 1 / ratio), 0.0)
    gdb = smooth(gdb, 0.05, 100)
    g = np.interp(np.arange(len(x)), (np.arange(nb) + 0.5) * hop, db(gdb))
    return x * g[:, None]


def fftconv(x, h):
    n = len(x) + len(h) - 1
    N = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, N) * np.fft.rfft(h, N), N)[:n]


def make_ir(rng, rt60, bright=7000.0):
    n = int(SR * rt60 * 1.1)
    t = np.arange(n) / SR
    ir = np.zeros((n, 2))
    for c in range(2):
        noise = rng.standard_normal(n) * np.exp(-6.9 * t / rt60)
        cut = bright * np.exp(-t / (rt60 * 0.45)) + 600   # high frequencies die first: a dark, warm tail
        ir[:, c] = spectral_filter(noise, lo_curve=120.0, hi_curve=cut)
    pre = int(0.025 * SR)
    ir = np.vstack([np.zeros((pre, 2)), ir])
    ir[:int(0.004 * SR) + pre] *= 0
    return ir / np.sqrt((ir ** 2).sum() / 2)


def reverb(x, ir):
    y = np.stack([fftconv(x[:, c], ir[:, c]) for c in range(2)], 1)[:len(x)]
    return y


def smooth(c, sec, rate):
    """one-pole smoothing of a control curve (forward + backward = no lag)."""
    a = np.exp(-1 / max(sec * rate, 1e-6))
    def run(v):
        out = np.empty_like(v); s = v[0]
        for i, x in enumerate(v):
            s = a * s + (1 - a) * x; out[i] = s
        return out
    return run(run(c)[::-1])[::-1]


def env_adsr(n, a, d, s, r, sus_len):
    t = np.arange(n) / SR
    e = np.where(t < a, t / max(a, 1e-4), 1.0)
    e = np.where((t >= a) & (t < a + d), 1 - (1 - s) * (t - a) / max(d, 1e-4), e)
    e = np.where(t >= a + d, s, e)
    rel = np.clip((t - sus_len) / max(r, 1e-4), 0, 1)
    return e * (1 - rel)


def place(buf, start, sig, pan=0.0, gain=1.0):
    a = int(start * SR)
    if a >= len(buf) or len(sig) == 0:
        return
    if a < 0:
        sig = sig[-a:]; a = 0
    sig = sig[:len(buf) - a]
    if sig.ndim == 1:
        l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        buf[a:a + len(sig), 0] += sig * l * gain * 1.414
        buf[a:a + len(sig), 1] += sig * r * gain * 1.414
    else:
        buf[a:a + len(sig)] += sig * gain


# ---------------------------------------------------------------- instruments
def inst_note(kind, midi, dur, rng, vel=1.0, detune_c=0.0):
    f = float(mtof(midi)) * 2 ** (detune_c / 1200)
    tail = {"bowed": 1.2, "glass": 2.4, "bassoon": 0.2, "musicbox": 2.6, "celesta": 2.2, "marimba": 0.9, "piano": 3.0, "horn": 0.6, "pizz": 0.5}[kind]
    n = int((dur + tail) * SR)
    t = np.arange(n) / SR
    if kind == "bowed":   # bowed glass / string harmonic: 220 ms swell, no transient, slight bow noise + vibrato
        e = env_adsr(n, min(0.22, dur * 0.5), 0.1, 0.85, 0.9, dur)
        vib = 1 + 0.0035 * np.sin(2 * np.pi * 4.7 * t) * np.clip(t / 0.4, 0, 1)
        ph = 2 * np.pi * np.cumsum(f * vib) / SR
        y = (np.sin(ph) + 0.3 * np.sin(2 * ph + 0.4) + 0.12 * np.sin(3 * ph) + 0.06 * np.sin(2.76 * ph)) * e
        y += 0.03 * np.random.default_rng(int(midi * 7)).standard_normal(n) * e
        y = spectral_filter(y, hi_curve=2500.0, order=2)
    elif kind == "glass":   # struck/rubbed glass: soft 25 ms attack, inharmonic 2.76x partial, long shimmer, no pluck
        y = (np.sin(2 * np.pi * f * t) + 0.22 * np.sin(2 * np.pi * f * 2.76 * t + 1.0) * np.exp(-t / 0.7)
             + 0.08 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t / 0.25)) * np.exp(-t / 1.8)
        y *= np.minimum(1, t / 0.025) * (1 + 0.04 * np.sin(2 * np.pi * 5.0 * t))
    elif kind in ("musicbox", "celesta"):
        ratio, idx, dec = (3.5, 1.3, 1.6) if kind == "musicbox" else (4.0, 0.9, 1.3)
        mod = idx * np.exp(-t / 0.25) * np.sin(2 * np.pi * f * ratio * t)
        y = np.sin(2 * np.pi * f * t + mod) * np.exp(-t / dec)
        y += 0.18 * np.sin(2 * np.pi * f * 2.0 * t) * np.exp(-t / 0.4)
        y *= np.minimum(1, t / 0.002)
    elif kind == "marimba":
        y = (np.sin(2 * np.pi * f * t) * np.exp(-t / 0.45) + 0.35 * np.sin(2 * np.pi * f * 3.93 * t) * np.exp(-t / 0.08)
             + 0.12 * np.sin(2 * np.pi * f * 9.2 * t) * np.exp(-t / 0.02)) * np.minimum(1, t / 0.001)
    elif kind == "piano":
        y = np.zeros(n)
        for k in range(1, 9):
            fk = f * k * np.sqrt(1 + 0.0004 * k * k)
            if fk > 12000:
                break
            y += (1 / k ** 1.6) * np.sin(2 * np.pi * fk * t + rng.uniform(0, 6.28)) * np.exp(-t * (0.6 + 0.9 * k))
        y *= np.minimum(1, t / 0.004)
        y *= np.where(t < dur + 0.05, 1, np.exp(-(t - dur - 0.05) / 0.35))
    elif kind == "horn":
        y = np.zeros(n)
        e = env_adsr(n, 0.09, 0.2, 0.8, 0.35, dur)
        bright = np.clip(e * 1.1, 0, 1)
        vib = 1 + 0.004 * np.sin(2 * np.pi * 5.2 * t) * np.clip(t - 0.3, 0, 1)
        ph = 2 * np.pi * np.cumsum(f * vib) / SR
        for k in range(1, 10):
            if f * k > 9000:
                break
            y += (bright ** (k * 0.7)) / k * np.sin(k * ph)
        y *= e
    elif kind == "bassoon":   # reedy: odd-heavy harmonics, quick swell, short
        y = np.zeros(n); e = env_adsr(n, 0.015, 0.06, 0.7, 0.07, dur)
        for k in range(1, 9):
            y += (1.0 if k % 2 else 0.45) / k * np.sin(2 * np.pi * f * k * t)
        y *= e
    else:  # pizz
        y = np.zeros(n)
        for k in range(1, 8):
            y += (1 / k ** 1.3) * np.sin(2 * np.pi * f * k * t) * np.exp(-t * (5 + 4 * k))
        y *= np.minimum(1, t / 0.002)
    return y * vel


def osc_saw(freq, harm=10):
    ph = 2 * np.pi * np.cumsum(freq) / SR
    y = np.zeros(len(freq))
    fmax = float(np.max(freq))
    for k in range(1, harm + 1):
        if fmax * k > SR / 2.4:
            break
        y += np.sin(k * ph) / k
    return y


# ---------------------------------------------------------------- beat map
def norm_type(t):
    t = ALIAS.get(str(t).lower(), str(t).lower())
    return t if t in SECTION else "dread"


def demo_beats(T):
    p = [(0, "hook"), (.045, "rule"), (.13, "plant"), (.21, "dread"), (.36, "hold"), (.37, "dread"), (.52, "hold"),
         (.53, "reveal"), (.72, "climax"), (.83, "hold"), (.84, "twist"), (.92, "cliffhanger"), (.965, "cta")]
    return [dict(t=round(f * T, 2), type=k, **({"dur": 0.6} if k == "hold" else {})) for f, k in p]


def load_beats(adir, T):
    bp = os.path.join(adir, "beats.json")
    if os.path.exists(bp):
        return json.load(open(bp, encoding="utf-8")), "beats.json"
    cp = os.path.join(adir, "cues.json")
    if os.path.exists(cp):
        b = [dict(t=c["t"], type=c["beat"], dur=c.get("dur", 0.6)) for c in json.load(open(cp)) if c.get("beat")]
        if len(b) >= 3:
            return b, "cues.json beat cues"
    beats = demo_beats(T)
    sp = os.path.join(adir, "sentences.json")
    if os.path.exists(sp):  # snap section starts to the nearest sentence start (holds to the nearest gap)
        S = json.load(open(sp, encoding="utf-8"))
        starts = np.array([s["start"] for s in S]); ends = np.array([s["end"] for s in S])
        for b in beats:
            if b["type"] == "hold":
                i = int(np.argmin(np.abs(ends - b["t"]))); b["t"] = round(float(ends[i]) + 0.05, 2)
            elif b["t"] > 0:
                b["t"] = round(float(starts[np.argmin(np.abs(starts - b["t"]))]), 2)
    return beats, "auto (STORY_ENGINE proportions, snapped to sentences)"


def sections(beats, T):
    bs = sorted([dict(b, type=norm_type(b.get("type") or b.get("beat"))) for b in beats if b.get("type") or b.get("beat")],
                key=lambda b: b["t"])   # ambience cues {"t","amb"} in the same file are not beats
    out = []
    holds = []
    main = [b for b in bs if b["type"] != "hold"]
    for b in bs:
        if b["type"] == "hold":
            holds.append((float(b["t"]), float(b["t"]) + float(b.get("dur") or 0.6)))
    if not main or main[0]["t"] > 0.01:
        main.insert(0, dict(t=0.0, type="hook"))
    for i, b in enumerate(main):
        e = main[i + 1]["t"] if i + 1 < len(main) else T
        if e > b["t"]:
            out.append(dict(t0=float(b["t"]), t1=float(e), type=b["type"]))
    return out, holds


# ---------------------------------------------------------------- the score
def compose(beats, T, mood, seed):
    rng = np.random.default_rng(seed)
    M = MOODS[mood]
    secs, holds = sections(beats, T)
    n = int(T * SR) + 1
    mode = M["modes"][rng.integers(len(M["modes"]))]
    root = int(rng.integers(M["root"][0], M["root"][1] + 1))
    bpm = float(rng.uniform(*M["bpm"]))
    beat_s = 60 / bpm
    prog = M["chords"][rng.integers(len(M["chords"]))]
    rot = int(rng.integers(len(prog)))
    prog = prog[rot:] + prog[:rot] if prog[0] != 0 else prog

    def deg(d, octv=0):
        return root + 12 * (octv + d // 7) + mode[d % 7]

    # motif: 4-6 notes, mostly stepwise, one leap, resolves to 1 or 5; rhythm in eighths
    k = int(rng.integers(4, 7))
    d = [int(rng.choice([0, 2, 4]))]
    for i in range(k - 2):
        step = int(rng.choice([-2, -1, 1, 2, 3, -3, 4], p=[.17, .25, .25, .15, .07, .06, .05]))
        nxt = d[-1] + step
        if nxt < -2 or nxt > 9:
            nxt = d[-1] - step          # reflect at the range edge (clipping made repeated notes)
        if len(d) >= 2 and nxt == d[-1] == d[-2]:
            nxt = d[-1] + (1 if d[-1] < 4 else -1)
        d.append(int(nxt))
    d.append(int(rng.choice([0, 4, 7]) if d[-1] > 3 else rng.choice([0, -3])))
    pats = {4: [[2, 1, 1, 4], [1, 1, 2, 4], [3, 1, 2, 4]], 5: [[2, 1, 1, 2, 4], [1, 1, 1, 1, 4], [3, 1, 2, 1, 5]],
            6: [[1, 1, 2, 1, 1, 4], [2, 1, 1, 2, 2, 4], [1, 2, 1, 2, 1, 5]]}
    rhythm = pats[k][rng.integers(3)]
    motif = list(zip(d, rhythm))
    motif_oct = M.get("motif_oct", {"bowed": 1, "glass": 3, "musicbox": 3, "celesta": 3, "marimba": 2, "piano": 2, "horn": 1}[M["motif"]])

    stems = {k_: np.zeros((n, 2)) for k_ in ("bowed", "drone", "sub", "pad", "cluster", "air", "pulse", "motif", "riser", "hit")}
    t = np.arange(n) / SR
    CR = 100  # control rate
    nc = int(T * CR) + 2
    tc = np.arange(nc) / CR
    ctrl = {k_: np.zeros(nc) for k_ in ("drone", "pad", "cluster", "air", "pulse", "bright", "rate")}
    chord_c = np.zeros(nc, int)
    for i, s in enumerate(secs):
        a, b = int(s["t0"] * CR), int(s["t1"] * CR) + 1
        p = SECTION[s["type"]]
        ramp = np.linspace(0.85, 1.15, max(b - a, 1)) if s["type"] in ("dread", "cliffhanger", "climax") else 1.0
        for k_ in ("drone", "pad", "cluster", "air", "pulse"):
            on = k_ != "pad" or s["type"] in M.get("pad_on", SECTION)
            ctrl[k_][a:b] = p[k_] * M["mult"].get(k_, 1) * ramp * on
        ctrl["bright"][a:b] = p["bright"] * (ramp if np.ndim(ramp) else 1)
        ctrl["rate"][a:b] = p["rate"]
        chord_c[a:b] = prog[i % len(prog)]
    for k_ in ("drone", "pad", "cluster", "air", "pulse", "bright"):
        ctrl[k_] = smooth(ctrl[k_], 0.9 if k_ != "pulse" else 0.3, CR)
    # escalation: the whole score rises across the video (REF4: first 15 s ~4-6 LU under the 60-75 s stretch)
    esc = db(M["escalate_db"] * (np.clip(tc / T, 0, 1) - 1))
    # the HOOK is exempt from most of the escalation dip (floor HOOK_ESC_DB): music must be HEARD from 0:00 (earshot
    # critique 'no music at 0:00-0:05' was critical on test_seq at score levels -17..-20 LUFS with the full -4 dB dip)
    hook_end = next((s_["t1"] for s_ in secs if s_["type"] == "hook"), 0.0)
    hk = smooth((tc < hook_end).astype(float), 0.4, CR) if hook_end > 0 else np.zeros(nc)
    esc_floor = db(HOOK_ESC_DB) * hk
    esc = np.maximum(esc, esc_floor)
    for k_ in ("drone", "pad", "cluster", "air", "pulse"):
        ctrl[k_] *= esc
    # RESTS (REF4 'let it breathe'): melodic layers + pulse drop out for 1-2 s every few seconds, so the voice and the
    # SFX hits get air (mystery target: melodic <= 90 % of runtime, horror <= 45 %). Drone/air dip -9 dB in a rest.
    rest = np.ones(nc)
    if M.get("rests"):
        on_a, on_b, off_a, off_b = M["rests"]
        # first rest no earlier than FIRST_REST_S: the hook must establish the music first (earshot critique scores
        # music presence per 5 s window; drone-only hook + a rest at 2.4 s read as "no music at 0:00-0:05", critical)
        # (first rest from FIRST_REST_S; none in the last END_PLAY_S either: a random rest at 10-12 s of a 12.6 s
        # excerpt left the final 5 s window with no music at all for 2 of 3 seeds, earshot AST Music 0.03)
        x = max(FIRST_REST_S, float(rng.uniform(on_a * 0.6, on_a)))
        while x < T - END_PLAY_S:
            L_ = min(float(rng.uniform(off_a, off_b)), T - END_PLAY_S - x)
            if L_ >= 0.6:
                rest[int(x * CR):int((x + L_) * CR)] = 0.0
            x += L_ + float(rng.uniform(on_a, on_b))
        for s_ in secs:   # also breathe right before each reveal/climax hit (the hit lands out of near-quiet)
            if s_["type"] in ("reveal", "climax") and s_["t0"] > 1.5:
                rest[int((s_["t0"] - PRE_HIT_REST) * CR):int(s_["t0"] * CR)] = 0.0
        lim = MELODIC_MAX.get(mood)
        if lim is not None and T > 4.0:
            need = max(0.0, 1.0 - (lim - MELODIC_MARGIN) / 100.0)
            have = lambda: float((rest < 0.5).mean())
            bounds = sorted((s_["t0"] for s_ in secs if s_["t0"] > 1.5), key=lambda b: (b < FIRST_REST_S, b))
            for b in bounds:              # breaths before cuts/sections, past the hook first
                if have() >= need:
                    break
                L_ = float(rng.uniform(*BREATH_S))
                rest[int(max(0.0, b - L_) * CR):int(b * CR)] = 0.0
            guard = 0
            while have() < need and guard < 20:   # still short: open a rest in the middle of the longest playing run
                guard += 1
                on = np.concatenate([[0], (rest >= 0.5).astype(int), [0]])
                d = np.diff(on); st_, en_ = np.where(d == 1)[0], np.where(d == -1)[0]
                lo, hi = int(1.5 * CR), int(max(1.5, T - 1.0) * CR)
                runs = [(min(e_, hi) - max(a_, lo), max(a_, lo), min(e_, hi)) for a_, e_ in zip(st_, en_) if min(e_, hi) - max(a_, lo) > int(1.6 * CR)]
                if not runs:
                    break
                ln, a_, e_ = max(runs)
                L_ = int(min(0.9 * CR, (need - have()) * nc + 0.1 * CR, ln - int(1.2 * CR)))
                if L_ < int(0.3 * CR):
                    break
                m_ = (a_ + e_) // 2
                rest[m_ - L_ // 2:m_ + L_ - L_ // 2] = 0.0
        rest = np.clip(smooth(rest, 0.12, CR), 0, 1)
        for k_ in ("pad", "pulse"):
            ctrl[k_] *= rest
        rb = db(M.get("rest_bed_db", REST_BED_DB) + M.get("rest_swell_db", 0.0))
        for k_ in ("drone", "air", "cluster"):
            ctrl[k_] *= rb + (1 - rb) * rest
    up = lambda c: np.interp(t, tc, c)

    # drone: root an octave below + fifth, 3 detuned saws each, wobbling slowly; cutoff follows brightness
    lfo = lambda hz, ph: np.sin(2 * np.pi * hz * t + ph)
    drone = np.zeros((n, 2))
    for j, (iv, amp) in enumerate([(0, 1.0), (7, .45), (12, .3)]):
        for c in range(2):
            for dc in (-9, 0, 8):
                f = mtof(root - 12 + iv) * 2 ** ((dc + 3 * lfo(0.05 + 0.02 * j, rng.uniform(0, 6)) + (c - .5) * 4) / 1200)
                drone[:, c] += amp * osc_saw(np.full(n, 1.0) * f * (1 + 0.0015 * lfo(0.11, rng.uniform(0, 6))), M.get("drone_harm", 7))
    cut = 110 + 1700 * up(ctrl["bright"]) ** 1.8
    drone = spectral_filter(drone, lo_curve=28.0, hi_curve=cut, order=2)
    drone *= (1 + 0.18 * lfo(0.07, 0))[:, None]
    stems["drone"] = drone / (np.abs(drone).max() + 1e-9) * up(ctrl["drone"])[:, None]
    # sub: a pure low root (gives the bed body on phones' small speakers via its 2nd harmonic)
    # R4-2: always in the 36-56 Hz octave whatever the mood's root (harmonics carry it on phones); swells under
    # reveal/climax/dread/twist sections (mood reveal_sub_db, default 3 dB).
    fsub = float(mtof(root))
    while fsub > 56.0: fsub /= 2.0
    while fsub < 36.0: fsub *= 2.0
    sub = np.sin(2 * np.pi * fsub * t) + 0.3 * np.sin(4 * np.pi * fsub * t) + 0.1 * np.sin(6 * np.pi * fsub * t)
    sw = np.zeros(nc)
    for s_ in secs:
        if s_["type"] in ("reveal", "climax", "dread", "twist"):
            sw[int(s_["t0"] * CR):int(s_["t1"] * CR) + 1] = 1.0
    sw = db(M.get("reveal_sub_db", 3.0) * smooth(sw, 0.6, CR))
    stems["sub"] = (sub * (0.85 + 0.15 * lfo(0.06, 1)) * up(ctrl["drone"] * sw))[:, None] * np.ones((1, 2))

    # pad: chord changes per section, strings-like (saw stack, slow vibrato), dark lowpass
    pad = np.zeros((n, 2))
    cc = np.interp(t, tc, chord_c.astype(float)).round().astype(int)
    for dgi, octv in ((0, 0), (2, 0), (4, 0), (7, 0)):
        for c in range(2):
            f = np.empty(n)
            for chd in np.unique(cc):
                m = cc == chd
                f[m] = mtof(deg(int(chd) + dgi, M.get("pad_oct", 1) + octv))
            f = np.exp(smooth(np.log(f[::480]), 0.25, 100))
            f = np.interp(t, np.arange(len(f)) * 480 / SR, f) * (1 + 0.003 * lfo(4.6 + c * 0.3, rng.uniform(0, 6)))
            if M.get("pad_kind") == "strings_dark":   # low string section: detuned saws, slow bow swell, dark lowpass below
                for dc in (-7, 6):
                    pad[:, c] += 0.6 * osc_saw(f * 2 ** ((dc + (c - .5) * 12) / 1200), 10)
            elif M.get("pad_kind") == "glass":   # bowed-glass pad: sine + soft octave/12th, no saw buzz (earshot heard 'guitar/house')
                ph = 2 * np.pi * np.cumsum(f * 2 ** ((c - .5) * 10 / 1200)) / SR
                pad[:, c] += np.sin(ph) + 0.25 * np.sin(2 * ph) + 0.1 * np.sin(3 * ph)
            else:
                pad[:, c] += osc_saw(f * 2 ** ((c - .5) * 10 / 1200), 8)
    hc = (260 + 900 * up(ctrl["bright"])) if M.get("pad_kind") == "strings_dark" else (500 + 2200 * up(ctrl["bright"]))
    pad = spectral_filter(pad, lo_curve=60.0 if M.get("pad_kind") == "strings_dark" else 150.0, hi_curve=hc, order=2)
    stems["pad"] = pad / (np.abs(pad).max() + 1e-9) * up(ctrl["pad"])[:, None]

    # cluster: two sines a minor second apart, high, beating + slow tremolo
    cl = np.zeros((n, 2))
    for c, (a_, b_) in enumerate(((24, 25), (31, 32))):
        cl[:, c] = np.sin(2 * np.pi * mtof(root + a_) * t) + 0.8 * np.sin(2 * np.pi * mtof(root + b_) * t + 1)
    cl *= (0.6 + 0.4 * lfo(0.23, 1))[:, None]
    stems["cluster"] = cl / 2 * up(ctrl["cluster"])[:, None]

    # bowed metal (horror/mystery dread): narrow noise resonances at inharmonic partials, slow swells, gliding a little
    if mood in ("horror", "mystery"):
        bw = np.zeros((n, 2))
        partials = mtof(root + 24) * np.array([1.0, 2.76, 5.40, 8.93])
        F = np.fft.rfftfreq(n, 1 / SR)
        for c in range(2):
            sp = np.fft.rfft(rng.standard_normal(n))
            m = sum(np.exp(-0.5 * ((F - p * (1 + 0.004 * c)) / (1.5 + p * 0.0015)) ** 2) / (1 + k) for k, p in enumerate(partials))
            bw[:, c] = np.fft.irfft(sp * m, n)
        sw = np.zeros(nc)
        for s_ in secs:
            if s_["type"] in ("dread", "cliffhanger", "climax") or M.get("bowed_always"):
                tt0 = s_["t0"] + rng.uniform(1, 3)
                while tt0 < s_["t1"] - 2:
                    L_ = rng.uniform(3, 6); a_ = int(tt0 * CR); b_ = min(nc, int((tt0 + L_) * CR))
                    sw[a_:b_] = np.maximum(sw[a_:b_], np.sin(np.linspace(0, np.pi, b_ - a_)) ** 2)
                    tt0 += L_ + rng.uniform(2, 6)
                if M.get("bowed_always") and s_["t1"] - s_["t0"] <= 5 and s_["type"] not in ("dread", "cliffhanger", "climax"):
                    a_, b_ = int(s_["t0"] * CR), min(nc, int(s_["t1"] * CR))   # short section: one swell over it
                    sw[a_:b_] = np.maximum(sw[a_:b_], 0.6 * np.sin(np.linspace(0, np.pi, max(b_ - a_, 1))) ** 2)
        stems["bowed"] = bw / (np.abs(bw).max() + 1e-9) * up(sw * esc * (0.35 + 0.65 * rest))[:, None]

    # air: noise band that breathes
    noise = rng.standard_normal((n, 2))
    centre = 520 + 300 * lfo(0.031, 2) + 1000 * up(ctrl["bright"])
    air = spectral_filter(noise, lo_curve=centre * 0.5, hi_curve=centre * 1.6, order=2)
    air = air / (np.abs(air).max() + 1e-9) * (0.8 + 0.2 * lfo(0.045, 0))[:, None]
    hiss = spectral_filter(rng.standard_normal((n, 2)), lo_curve=6500.0, order=2)   # tape-like top air, keeps it from sounding muffled
    air += hiss / (np.abs(hiss).max() + 1e-9) * 0.12
    stems["air"] = air * up(np.maximum(ctrl["air"], 0.25 * (ctrl["drone"] > 0.05)))[:, None]

    # pulse
    pk = M["pulse"]
    if pk != "none":
        pt = 0.0; i = 0
        while pt < T:
            ci = min(int(pt * CR), nc - 1)
            g = ctrl["pulse"][ci]
            if g > 0.02:
                if pk == "heart":
                    for off, amp in ((0, 1.0), (0.27, 0.65)):
                        nn = int(0.35 * SR); tt = np.arange(nn) / SR
                        f = 38 + 30 * np.exp(-tt / 0.04)
                        s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / 0.11) * np.minimum(1, tt / 0.003)
                        place(stems["pulse"], pt + off, s, 0, g * amp)
                elif pk == "lowclock":   # muffled wooden clock: 400-900 Hz band, no 2 kHz 'UI ding'; low thump on 1
                    nn = int(0.06 * SR); tt = np.arange(nn) / SR
                    s = spectral_filter(rng.standard_normal(nn), lo_curve=380.0, hi_curve=900.0, order=2) * np.exp(-tt / 0.01)
                    s = s / (np.abs(s).max() + 1e-9) * (0.6 if i % 2 else 0.45)
                    place(stems["pulse"], pt, s, -.2 if i % 2 else .2, g * 0.5)
                    if i % 4 == 0:
                        nn = int(0.3 * SR); tt = np.arange(nn) / SR
                        th = np.sin(2 * np.pi * np.cumsum(55 + 25 * np.exp(-tt / 0.03)) / SR) * np.exp(-tt / 0.12)
                        place(stems["pulse"], pt, th * np.minimum(1, tt / 0.004), 0, g * 0.7)
                elif pk == "pizzlow":   # cello pizz ostinato: root on 1, fifth/b6 between, uneven accents, sparse
                    chd = int(chord_c[ci]); pat = (0, None, None, 4, None, 0, 5, None)[i % 8]
                    # 3+2+1+2 eighths, 4 notes a bar: a steady 4-of-8 pattern read as 'tech house', a 4-of-12 one was
                    # too sparse to be heard as music in the 0-5 s window (earshot critique: presence 33 %, critical)
                    if pat is not None:
                        acc = (1.0, 0, 0, .6, 0, .75, .5, 0)[i % 8] * rng.uniform(.85, 1.05)
                        place(stems["pulse"], pt + rng.uniform(0, .01), inst_note("pizz", deg(chd + pat, 0), 0.25, rng),
                              (-.35, .3, .15, -.2)[(i // 2) % 4], g * acc)
                elif pk == "tick":
                    nn = int(0.05 * SR); tt = np.arange(nn) / SR
                    s = np.sin(2 * np.pi * (2400 if i % 2 else 1800) * tt) * np.exp(-tt / 0.006)
                    s += 0.3 * rng.standard_normal(nn) * np.exp(-tt / 0.003)
                    place(stems["pulse"], pt, s, -.35 if i % 2 else .35, g * 0.5)
                    if i % 4 == 0 and not M.get("no_pizz"):
                        place(stems["pulse"], pt, inst_note("pizz", deg(0, 0), 0.2, rng) * 0.9, 0, g)
                elif pk == "pizz":   # oom-pah: staccato bassoon-ish bass on the beat, short chord stab off the beat
                    chd = int(chord_c[ci])
                    if i % 2 == 0:
                        bass = [0, 4][(i // 2) % 2]
                        place(stems["pulse"], pt, inst_note("bassoon", deg(chd + bass, 0), 0.16, rng), -.1, g * 1.1)
                    else:
                        for dd, pn in ((0, -.4), (2, .1), (4, .45)):
                            place(stems["pulse"], pt, inst_note("pizz", deg(chd + dd, 2), 0.08, rng) * 0.4, pn, g)
                    if i % 8 == 7:
                        nn = int(0.06 * SR); tt = np.arange(nn) / SR
                        wb = np.sin(2 * np.pi * 1250 * tt) * np.exp(-tt / 0.018) + 0.4 * np.sin(2 * np.pi * 2900 * tt) * np.exp(-tt / 0.008)
                        place(stems["pulse"], pt + beat_s / 4, wb * 0.5, .5, g)
                elif pk == "toms":
                    nn = int(0.5 * SR); tt = np.arange(nn) / SR
                    f0 = 95 if i % 4 in (0, 3) else 72
                    s = np.sin(2 * np.pi * np.cumsum(f0 * (1 + 0.6 * np.exp(-tt / 0.05))) / SR) * np.exp(-tt / 0.2)
                    s += 0.15 * spectral_filter(rng.standard_normal(nn), hi_curve=900.0) * np.exp(-tt / 0.03)
                    acc = 1.0 if i % 4 == 0 else (0.55 if i % 2 == 0 else 0.4)
                    place(stems["pulse"], pt, s, (-.25, .25)[i % 2], g * acc)
            rate = ctrl["rate"][ci]
            step = beat_s / (2 if pk in ("pizz", "tick", "toms", "lowclock", "pizzlow") else 1) / max(rate, 0.5)
            if pk == "heart":
                step = beat_s / max(rate, 0.5) * 1.0
            pt += step; i += 1

    # motif placements
    placed = 0
    for s in secs:
        if s["type"] not in M["motif_on"] or placed >= M["motif_max"]:
            continue
        reps = 1 if mood in ("horror", "mystery") else max(1, int((s["t1"] - s["t0"]) // (sum(rhythm) * beat_s / 2 + beat_s * 2)))
        reps = min(reps, 3)
        for r in range(reps):
            if placed >= M["motif_max"]:
                break
            # on a reveal/climax the motif enters right after the hit (was +0.35 s: in a short last section it
            # never sounded before the end -> earshot heard no music in the final 5 s window)
            start = s["t0"] + (0.12 if s["type"] in ("reveal", "climax") else 0.35) + r * (sum(rhythm) * beat_s / 2 + beat_s * 2)
            slow = 2.0 if (s["type"] == "reveal" and M["detune_reveal"]) else 1.0
            det = -45.0 if (s["type"] == "reveal" and M["detune_reveal"]) else 0.0
            shift = 0 if r % 2 == 0 else int(rng.choice([2, -1, 4]))
            pt = start
            for j, (dd, rh) in enumerate(motif):
                dur = rh * beat_s / 2 * slow
                if pt + dur > s["t1"] + 1.0:
                    break
                if rest[min(int(pt * CR), nc - 1)] < 0.5:
                    pt += dur; continue
                vel = 0.8 + 0.2 * (j == 0) - 0.1 * (j == len(motif) - 1) + rng.uniform(-.05, .05)
                note = inst_note(M["motif"], deg(dd + shift, motif_oct - (1 if slow > 1 else 0)), dur, rng, vel, det)
                place(stems["motif"], pt + rng.uniform(0, 0.012), note, rng.uniform(-.3, .3),
                      M["mult"]["motif"] * db(M["escalate_db"] * (pt / T - 1) * 0.5))
                pt += dur
            placed += 1

    stems["motif"] *= up(rest)[:, None] ** 2     # rests silence the motif too (notes no longer ring through them)

    # risers into reveal / climax, hits on them
    for s in secs:
        if s["type"] not in ("reveal", "climax"):
            continue
        L = min(4.0, max(1.5, s["t0"] - 0.5))
        nn = int(L * SR); tt = np.arange(nn) / SR; u = tt / L
        nz = rng.standard_normal((nn, 2))
        rs = spectral_filter(nz, lo_curve=250 * 2 ** (4 * u), hi_curve=600 * 2 ** (4 * u), order=2) * (u ** 2.2)[:, None]
        gl = sum(np.sin(2 * np.pi * np.cumsum(mtof(root + 12 + iv) * 2 ** (u * 1.0)) / SR) for iv in (0, 1, 7))
        trem = 0.7 + 0.3 * np.sin(2 * np.pi * np.cumsum(3 + 13 * u) / SR)
        rs += (0.25 * gl * trem * u ** 2)[:, None]
        rs /= np.abs(rs).max() + 1e-9
        rs[-int(0.06 * SR):] *= np.linspace(1, 0, int(0.06 * SR))[:, None]   # tiny suck-in before the hit
        place(stems["riser"], s["t0"] - L - 0.06, rs, 0, 1.0)
        nn = int(3.0 * SR); tt = np.arange(nn) / SR
        last = s["t0"] > T - END_HIT_S                 # R3-4: the ending button: short tail, lower level
        sub = np.sin(2 * np.pi * np.cumsum(30 + 32 * np.exp(-tt / 0.18)) / SR) * np.exp(-tt / (END_HIT_TAIL if last else 0.9)) * np.minimum(1, tt / 0.002)
        br = spectral_filter(rng.standard_normal(nn), lo_curve=60.0, hi_curve=1800.0) * np.exp(-tt / 0.12) * 0.5
        low = inst_note("piano", deg(0, -1), 1.5, rng) * 0.6 + inst_note("piano", deg(0, 0) + 1, 1.5, rng) * 0.25
        hit = sub + br
        hit[:len(low)] += low[:nn]
        place(stems["hit"], s["t0"], hit / (np.abs(hit).max() + 1e-9), 0, db(END_HIT_DB) if last else 1.0)

    # mix stems, reverb, hold cuts
    ir = make_ir(rng, M["reverb"])
    dry = np.zeros((n, 2)); send = np.zeros((n, 2))
    for k_, x in stems.items():
        x = x * db(LEVEL_DB[k_])
        stems[k_] = x
        dry += x; send += x * SEND[k_]
    wet = reverb(send, ir) * 0.7
    mix = dry + wet
    hold_mask = np.ones(n)
    for a, b in holds:
        ia, ib = int(a * SR), int(b * SR)
        f1, f2 = int(0.03 * SR), int(0.25 * SR)
        hold_mask[max(0, ia - f1):ia] = np.minimum(hold_mask[max(0, ia - f1):ia], np.linspace(1, 0, ia - max(0, ia - f1)))
        hold_mask[ia:ib] = 0
        hold_mask[ib:ib + f2] = np.minimum(hold_mask[ib:ib + f2], np.linspace(0, 1, len(hold_mask[ib:ib + f2])))
    mix *= hold_mask[:, None]
    for k_ in stems:
        stems[k_] *= hold_mask[:, None]
    mix = compress(mix)
    mix *= up(np.maximum(db(0.8 * M["escalate_db"] * (np.clip(tc / T, 0, 1) - 1)), esc_floor))[:, None]   # escalation survives the compressor
    mix = np.tanh(mix * 1.2) / 1.2   # gentle glue
    # end: a 0.35 s tail-off only. The old 1.5 s fade emptied the last 5 s window (earshot: no music at 10-12.6 s on
    # 2 of 3 seeds) and made the ending sag into the cut to black; the film ends ON the score, the mix clips it.
    fo = int(END_FADE_S * SR)
    mix[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 1.5
    info = dict(mood=mood, seed=int(seed), key=["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"][root % 12],
                root_midi=root, mode=mode, bpm=round(bpm, 1), motif=[[int(a), int(b)] for a, b in motif],
                motif_instrument=M["motif"], motif_placements=placed, chords=prog,
                sections=[dict(s) for s in secs], holds=[[round(a, 3), round(b, 3)] for a, b in holds])
    # music-share bookkeeping: melodic layers vs. bed (drone/air) active > -35 dB under their own peak
    def active(x):
        e = np.sqrt((x.mean(1)[: len(x) // 4800 * 4800].reshape(-1, 4800) ** 2).mean(1))
        return float((e > e.max() * db(-35)).mean()) if e.max() > 0 else 0.0
    mel = stems["motif"] + stems["pad"]
    info["active_pct"] = dict(melodic=round(100 * active(mel), 1), bed=round(100 * active(stems["drone"] + stems["air"]), 1), pulse=round(100 * active(stems["pulse"]), 1),
                              any=round(100 * active(mix), 1))
    return mix, stems, info


def lufs(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True)
    txt = r.stderr[r.stderr.rfind("Summary:"):]
    import re
    m = re.search(r"I:\s+(-?[\d.]+) LUFS", txt); p = re.search(r"Peak:\s+(-?[\d.]+) dBFS", txt)
    return (float(m.group(1)) if m else None), (float(p.group(1)) if p else None)


def write_wav(path, x):
    import wave
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())


def render(beats, T, mood, seed, out, level=-24.0, stems_dir=None, tp=-1.0):
    mix, stems, info = compose(beats, T, mood, seed)
    pk = np.abs(mix).max() + 1e-9
    mix = mix / pk * 0.5
    write_wav(out, mix)
    L, _ = lufs(out)
    g = db(level - L) if L is not None else 1.0
    g = min(g, db(tp) / (np.abs(mix).max() + 1e-9))   # never clip / exceed the true-peak ceiling (approx.)
    mix *= g
    write_wav(out, mix)
    info["lufs"], info["peak_dbfs"] = lufs(out)
    info["level_target"] = level
    if stems_dir:
        sc = 0.5 / pk * g
        for k, x in stems.items():
            if np.abs(x).max() > 0:
                write_wav(os.path.join(stems_dir, k + ".wav"), x * sc)
    json.dump(info, open(os.path.splitext(out)[0] + ".json", "w"), indent=1)
    return info


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug", nargs="?")
    ap.add_argument("--mood", default="")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--beats", default="")
    ap.add_argument("--dur", type=float, default=0)
    ap.add_argument("--out", default="")
    ap.add_argument("--lufs", type=float, default=-24.0, help="score loudness (default -24: sits under the voice in mix.py)")
    ap.add_argument("--stems", default="")
    ap.add_argument("--demo-beats", type=float, default=0)
    o = ap.parse_args()
    if o.demo_beats:
        print(json.dumps(demo_beats(o.demo_beats), indent=1)); return
    seed = o.seed if o.seed is not None else int.from_bytes(os.urandom(4), "little") % 2_000_000_000
    mood = o.mood or "mystery"
    if o.slug:
        adir = os.path.join(STUDIO, "videos", o.slug, "audio")
        voice = os.path.join(adir, "voice.wav")
        T = o.dur
        if not T and os.path.exists(voice):
            T = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", voice],
                                     capture_output=True, text=True).stdout.strip() or 0)
        if not T:
            sys.exit("no duration: need audio/voice.wav or --dur")
        if o.beats:
            beats, src = json.load(open(o.beats)), o.beats
        else:
            beats, src = load_beats(adir, T)
        if not o.mood:
            sp = os.path.join(STUDIO, "videos", o.slug, "story.json")
            if os.path.exists(sp):
                mood = json.load(open(sp)).get("mood", mood)
        out = o.out or os.path.join(adir, "score.wav")
        stems = o.stems or os.path.join(adir, "score_stems")
    else:
        if not (o.beats and o.dur and o.out):
            sys.exit("without a slug pass --beats FILE --dur SECONDS --out FILE.wav")
        beats, src, T, out, stems = json.load(open(o.beats)), o.beats, o.dur, o.out, (o.stems or None)
    if mood not in MOODS:
        sys.exit(f"mood must be one of {', '.join(MOODS)}")
    info = render(beats, T, mood, seed, out, o.lufs, stems)
    info["beats_from"] = src
    json.dump(info, open(os.path.splitext(out)[0] + ".json", "w"), indent=1)
    print(f"score: {mood}, key {info['key']} {'minor-ish' if info['mode'][2] == 3 else 'major-ish'}, {info['bpm']} bpm, seed {seed}, "
          f"motif {info['motif']} on {info['motif_instrument']} x{info['motif_placements']}; beats from {src}")
    print(f"       {len(info['sections'])} sections, {len(info['holds'])} holds; music active {info['active_pct']}; "
          f"{info['lufs']} LUFS, peak {info['peak_dbfs']} dBFS -> {out}")


if __name__ == "__main__":
    main()
