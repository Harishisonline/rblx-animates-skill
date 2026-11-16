"""Synthesise sci-fi SFX with numpy (no credits): drone (hum + rotor buzz), scan (rising beep sweep),
powerdown (falling whine + thump), beep (terminal blip). Writes sfx/<name>.wav (48 kHz mono 16-bit), adds pack.json gains.
    python tools/synth_sfx.py"""
import json, os, wave
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SR = 48000


def env(n, a=0.01, r=0.2):
    e = np.ones(n); na, nr = int(a * SR), int(r * SR)
    e[:na] = np.linspace(0, 1, na); e[-nr:] *= np.linspace(1, 0, nr); return e


def save(name, x, gain=0):
    x = x / (np.max(np.abs(x)) + 1e-9) * 0.85
    with wave.open(os.path.join(ROOT, "sfx", name + ".wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((x * 32767).astype(np.int16).tobytes())
    p = os.path.join(ROOT, "sfx", "pack.json"); pk = json.load(open(p))
    pk.setdefault(name, {})["gain"] = gain; json.dump(pk, open(p, "w"), indent=2)


rng = np.random.default_rng(1)
t = np.arange(int(2.2 * SR)) / SR
hum = np.sin(2 * np.pi * 110 * t) * 0.5 + np.sin(2 * np.pi * 220.5 * t) * 0.25
rot = np.sign(np.sin(2 * np.pi * 180 * t)) * (0.5 + 0.5 * np.sin(2 * np.pi * 24 * t)) * 0.18
save("drone", (hum + rot + rng.normal(0, 0.05, t.size)) * env(t.size, 0.25, 0.6), -6)
t = np.arange(int(0.6 * SR)) / SR
f = 600 + 1800 * t / t[-1]
save("scan", np.sin(2 * np.pi * np.cumsum(f) / SR) * (0.6 + 0.4 * np.sign(np.sin(2 * np.pi * 30 * t))) * env(t.size, 0.01, 0.1), -8)
t = np.arange(int(1.4 * SR)) / SR
f = 900 * np.exp(-t * 2.2) + 40
x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.2) + np.sin(2 * np.pi * 50 * t) * np.exp(-t * 6) * 1.2
save("powerdown", x * env(t.size, 0.005, 0.3), -2)
t = np.arange(int(0.18 * SR)) / SR
save("beep", np.sin(2 * np.pi * 1320 * t) * env(t.size, 0.005, 0.05), -10)
print("wrote drone scan powerdown beep")
