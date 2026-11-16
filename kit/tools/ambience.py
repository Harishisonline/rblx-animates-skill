"""Room tone / ambience bed (REF4 layer A: never true silence). Real CC0 recordings first, procedural fallback.
    python tools/ambience.py list                                  beds available (library files per name)
    python tools/ambience.py render <slug> [--amb room] [--seed N]   -> videos/<slug>/audio/ambience.wav (mix.py picks it up)
    python tools/ambience.py make <name> --dur 20 --out x.wav [--procedural]   one bed, for auditioning
    python tools/ambience.py fetch                                 (re)fetch the CC0 starter set via tools/openverse.py
NAMES: room (indoor room tone), street, school_hallway, wind, night_crickets, kitchen_hum.
LOCATIONS come from cues.json entries {"t": 12.0, "amb": "school_hallway"} (each runs until the next one, 0.5 s crossfade);
with none, --amb (default: config "ambience", else room) covers the whole video.
LIBRARY: <workspace>/sfxlib/openverse/amb_<name>/ (CC0, every file logged in sfxlib/openverse/ATTRIBUTION.md).
Pick the best file with earshot before a final: `earshot rank "quiet bedroom room tone at night" sfxlib/openverse/amb_room`.
Level: calibrated to about -46 LUFS (beds sit ~28-32 dB under the voice before mastering, REF4 table)."""
import argparse, glob, json, os, subprocess, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
SR = 48000
NAMES = ("room", "street", "school_hallway", "wind", "night_crickets", "kitchen_hum")
QUERIES = {"room": "room tone", "street": "street ambience traffic", "school_hallway": "school hallway",
           "wind": "wind ambience", "night_crickets": "night crickets", "kitchen_hum": "refrigerator hum"}
LEVEL = -46.0


def libdir(name):
    return os.path.join(STUDIO, "sfxlib", "openverse", "amb_" + name)


def files(name):
    return sorted(f for f in glob.glob(os.path.join(libdir(name), "*")) if f.lower().endswith((".mp3", ".wav", ".ogg", ".flac")))


def decode(p):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"],
                         stdout=subprocess.PIPE, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64).reshape(-1, 2)


def lowpass(x, fc, hp=None):
    n = len(x)
    F = np.fft.rfft(x, axis=0)
    f = np.fft.rfftfreq(n, 1 / SR)[:, None] if x.ndim == 2 else np.fft.rfftfreq(n, 1 / SR)
    M = 1 / np.sqrt(1 + (f / fc) ** 4)
    if hp:
        M = M / np.sqrt(1 + (hp / np.maximum(f, 1)) ** 4)
    return np.fft.irfft(F * M, n, axis=0)


def procedural(name, dur, rng):
    n = int(dur * SR); t = np.arange(n) / SR
    w = rng.standard_normal((n, 2))
    lfo = lambda hz: np.sin(2 * np.pi * hz * t + rng.uniform(0, 6.28))[:, None]
    if name == "room":
        x = lowpass(np.cumsum(w, 0) * 0.02, 400, 30) * (1 + 0.15 * lfo(0.1))
        x += 0.02 * np.sin(2 * np.pi * 60 * t)[:, None] + 0.01 * np.sin(2 * np.pi * 120 * t)[:, None]
    elif name == "kitchen_hum":
        x = sum(a * np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) for f, a in ((60, 1), (120, .6), (180, .3), (240, .15)))[:, None]
        x = x * (1 + 0.1 * lfo(0.3)) * 0.2 + 0.4 * lowpass(w, 800, 200) * 0.2
    elif name == "street":
        x = lowpass(w, 900, 40) * (0.6 + 0.4 * lfo(0.05))
        for c in rng.uniform(0, dur, int(dur / 6)):    # cars passing: slow swells
            x += lowpass(w, 1500, 80) * np.exp(-((t - c) / 1.8) ** 2)[:, None] * 0.9
    elif name == "school_hallway":
        x = lowpass(w, 2500, 250) * (0.5 + 0.5 * np.abs(lowpass(rng.standard_normal(n), 3)))[:, None] * 2
        x = x + 0.3 * lowpass(w[::-1], 500, 60)
    elif name == "wind":
        gust = 0.5 + 0.5 * np.clip(lowpass(rng.standard_normal(n), 0.15) * 40, -1, 1)
        x = lowpass(w, 300 + 0, 60) * gust[:, None] + 0.35 * lowpass(w, 1400, 500) * (gust ** 2)[:, None]
    else:  # night_crickets
        x = 0.4 * lowpass(np.cumsum(w, 0) * 0.02, 300, 30)
        for k in range(3):
            f0 = rng.uniform(3800, 5200); rate = rng.uniform(2.5, 4.5)
            gate = (np.sin(2 * np.pi * rate * t) > 0.6) * (np.sin(2 * np.pi * 28 * t) > 0)
            x[:, k % 2] += 0.08 * np.sin(2 * np.pi * f0 * t) * lowpass(gate.astype(float), 400) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.07 * t))
    return x


def lufs_gain(x, target=LEVEL):
    from score import write_wav, lufs  # same helpers
    p = os.path.join(os.environ.get("TMPDIR", "/tmp"), f"amb_{os.getpid()}.wav")
    y = x / (np.abs(x).max() + 1e-9) * 0.5
    write_wav(p, y); L, _ = lufs(p); os.remove(p)
    return y * (10 ** ((target - L) / 20) if L is not None else 0.05)


def loop_to(x, n, xf=int(1.0 * SR)):
    if len(x) >= n:
        return x[:n]
    xf = min(xf, len(x) // 3)
    out = np.zeros((n + len(x), 2)); step = len(x) - xf
    w = np.ones(len(x)); w[:xf] = np.linspace(0, 1, xf); w[-xf:] = np.linspace(1, 0, xf)
    for a in range(0, n, step):
        out[a:a + len(x)] += x * w[:, None]
    out[:xf] = x[:xf]
    return out[:n]


def bed(name, dur, rng, force_proc=False, log=None):
    fs = [] if force_proc else files(name)
    n = int(dur * SR)
    if fs:
        f = fs[int(rng.integers(len(fs)))]
        x = decode(f)
        x = lowpass(x, 14000, 40)
        if len(x) > n:   # start at a random point so two videos never share the same stretch
            a = int(rng.integers(0, len(x) - n)); x = x[a:a + n]
        x = loop_to(x, n)
        if log is not None:
            log.append(dict(name=name, file=os.path.relpath(f, STUDIO), licence="CC0 (see sfxlib/openverse/ATTRIBUTION.md)"))
    else:
        x = procedural(name, dur, rng)
        if log is not None:
            log.append(dict(name=name, file="procedural"))
    return lufs_gain(x)


def render(slug, amb, seed):
    from score import write_wav
    adir = os.path.join(STUDIO, "videos", slug, "audio")
    voice = os.path.join(adir, "voice.wav")
    T = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", voice],
                             capture_output=True, text=True).stdout.strip() or 0)
    cp = os.path.join(adir, "cues.json")
    bp = os.path.join(adir, "beats.json")      # amb cues may live in beats.json too (blend.py cues rewrites cues.json)
    src = [c for f in (cp, bp) if os.path.exists(f) for c in json.load(open(f))]
    locs = sorted({(c["t"], c["amb"]): c for c in src if c.get("amb")}.values(), key=lambda c: c["t"])
    if not locs or locs[0]["t"] > 0.05:
        locs.insert(0, dict(t=0.0, amb=amb))
    rng = np.random.default_rng(seed)
    n = int(T * SR) + 1
    out = np.zeros((n, 2)); log = []
    xf = int(0.5 * SR)
    for i, c in enumerate(locs):
        a = int(c["t"] * SR); e = int(locs[i + 1]["t"] * SR) if i + 1 < len(locs) else n
        name = c["amb"] if c["amb"] in NAMES else amb
        s0 = max(0, a - xf) if i > 0 else 0
        L = min(e + xf, n) - s0
        if L <= 0:
            continue
        seg = bed(name, L / SR + 0.01, rng, log=log)[:L] * (10 ** (float(c.get("gain", 0)) / 20))
        w = np.ones(L)
        if i > 0: k = min(2 * xf, L // 2); w[:k] = np.linspace(0, 1, k)
        if i + 1 < len(locs): k = min(2 * xf, L // 2); w[-k:] = np.minimum(w[-k:], np.linspace(1, 0, k))
        out[s0:s0 + L] += seg * w[:, None]
    write_wav(os.path.join(adir, "ambience.wav"), out)
    json.dump(dict(seed=seed, beds=log, locations=locs), open(os.path.join(adir, "ambience.json"), "w"), indent=1)
    print(f"ambience: {', '.join(f'{c['amb']}@{c['t']:.1f}s' for c in locs)} -> audio/ambience.wav "
          f"({', '.join(os.path.basename(b['file']) for b in log)})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd"); ap.add_argument("arg", nargs="?")
    ap.add_argument("--amb", default=""); ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--dur", type=float, default=20); ap.add_argument("--out", default="")
    ap.add_argument("--procedural", action="store_true")
    o = ap.parse_args()
    seed = o.seed if o.seed is not None else int.from_bytes(os.urandom(4), "little")
    if o.cmd == "list":
        for nm in NAMES:
            print(f"{nm:15s} {len(files(nm))} CC0 files  ({libdir(nm)})")
    elif o.cmd == "render":
        import kit
        render(o.arg, o.amb or kit.cfg().get("ambience", "room"), seed)
    elif o.cmd == "make":
        from score import write_wav
        write_wav(o.out, bed(o.arg, o.dur, np.random.default_rng(seed), o.procedural))
        print("wrote", o.out)
    elif o.cmd == "fetch":
        import openverse
        for nm in NAMES:
            openverse.fetch(QUERIES[nm], 3, 90, "amb_" + nm)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
