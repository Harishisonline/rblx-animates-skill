# Final audio for a video: voice + sound cues from the sfx/ pack + optional music bed.
#   python tools/mix.py --video <slug>
# reads  videos/<slug>/audio/voice.wav   (tools/voice.py)
#        videos/<slug>/audio/cues.json   (tools/cues.mjs)
#        videos/<slug>/audio/music.*     (optional bed: looped to length, ducked under the voice)
# writes videos/<slug>/audio/mix.m4a     (48k stereo AAC, what tools/render.mjs picks up)
# Without --video it mixes the rent-control demo: source/audio.m4a + out/cues.json -> out/mix_sfx.m4a.
# Any path can be overridden: --voice --cues --music --out. Levels: --sfx-db --music-db --duck-db --amb-db.
#        videos/<slug>/audio/ambience.wav (optional room tone from tools/ambience.py: never ducked hard, never cut by holds)
# cues.json may also hold beat cues {"t","beat":"dread"} (music automation) and holds {"t","beat":"hold","dur":0.6}:
# a hold hard-cuts music + sfx to the room tone (REF4 'silence' layer). --music-level asis keeps a calibrated score's level
# (tools/score.py already shapes it per beat); peak = old behaviour (house track, peak at --music-db, beat gains applied).
# Everything is decoded and encoded through ffmpeg pipes; the mix itself is numpy.
import argparse, glob, json, os, re, subprocess, sys
import numpy as np

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SR = 48000
VOICE_PEAK_DB = -1.5   # the voice is the loudest thing: its peak is put here
SFX_DB = -6.0          # pack sounds peak ~4-8 dB under the voice peak so cut/cue hits land >= 12 dB over the bed
PEAK_BOOST_DB, VOL_CURVE = 4.0, 0.5
SC_MUSIC_DB, SC_AMB_DB = -5.0, -3.0   # side-chain: music / room tone dip this much under each SFX hit (fast in, ~180 ms out)
PRE_MAX = 0.17         # a peak-aligned sound may start at most this long before its peak (= a 5-frame whip at 30 fps)
PRE_ATTACK = 0.004     # ...and starts with this hard 4 ms attack: an audible ONSET where the motion starts (earshot D7)
PEAK_ALIGN = ('whoosh', 'swish', 'whip', 'rise', 'riser', 'flash', 'boom', 'thud')  # cue t = the sound's PEAK, not its start
MUSIC_DB = -13.0       # music peak in the gaps (~14 dB under the voice while talking, audible on phones)...
DUCK_DB = -5.0         # ...and this much lower while the voice is speaking
CEILING = 10 ** (-1.0 / 20)
REPEAT_WIN, REPEAT_STEP, REPEAT_FLOOR = 0.35, 0.8, 0.5  # the same sound again within 350ms gets quieter each time

db = lambda d: 10 ** (d / 20)

# ---- transitions (R2 D7 / R2-1): a cut cue {"t", "name", "cut": true, "kind": "whip|flash|push", "pan": [p0, p1]} is
# sound-designed here from REAL recordings, not one pack file: an air layer (recorded whoosh/swoosh, its natural swell
# peaking ON the cut, auto-panned p0 -> p1 in the direction of the camera move) + a low hit whose ATTACK is on the cut
# (the accent earshot hears as 'whoosh'/'hit'; the old 4 ms hard onset on a pack whoosh read as a 'chat message pop')
# + for a flash a recorded riser tail into it. Music drops out for a beat before every cut (DIP_*), so the hit lands
# out of near-quiet. Old cue files without "cut" still work: a "whoosh" cue is treated as a whip cut.
LIB = os.path.join(ROOT, 'sfxlib', 'openverse')
TRANS = {   # kind -> layers (source, role, gain dB); source 'lib:a|b' = folders in sfxlib/openverse, 'pack:x' = sfx/x.wav
    # R3-2: the whip at 7.40 s read as 'spoken word' (no whoosh tag): the -2 dB thud dominated the normalised sound and
    # the 50 ms suck-in cut the air just as the voice came in. A whip is AIR: two recorded whooshes, no suck, a soft thud.
    'whip':  [('lib:whoosh|swoosh', 'air', 0.0), ('lib:swoosh|whoosh', 'air', -5.0)],
    'push':  [('lib:swoosh|whoosh', 'air', -2.0), ('pack:thud', 'hit', -3.0), ('lib:impact_boom', 'hit', -12.0)],
    'flash': [('lib:riser', 'swell', -9.0), ('lib:impact_boom', 'hit', 0.0), ('pack:thud', 'hit', -3.0), ('lib:whoosh', 'air', -10.0)],
}
TRANS_NAMES = {'whoosh': 'whip', 'whip': 'whip', 'swish': 'whip', 'flash': 'flash', 'push': 'push'}
WHIP_TUCK_DB = -6.0                # voice under a whip's whoosh body (R3-2)
WHIP_HP_HZ = 350.0                 # whip air layers high-passed here (R3-2)
WHIP_GAIN_DB = 4.0                 # whip sound over the other transitions (no hit layer to carry it) (R3-2)
AIR_PRE, AIR_POST = 0.32, 0.45    # air layer: swell this long before the cut, tail after it
SUCK_S, SUCK_DB = 0.05, -14.0      # the swell dips this much over the last 50 ms before the cut: the hit lands out of it
DIP_DB, DIP_PRE, DIP_FALL = -12.0, 0.45, 0.15   # music: down DIP_DB from cut-DIP_PRE (fall DIP_FALL s), back ON the cut
DIP_BEATS = ('reveal', 'climax')                # ...and before these beats (beats.json / beat cues)
BED_SIDE_DB = dict(music=-1.5, amb=-1.0)        # bed width targets (side under mid)
# ---- v3.7 VOICE CLARITY option (docs/research/MUSIC_RESEARCH.md sec. 5, "mix D"). OFF by default: the user was sent the
# A/B clips A_base_m (EP1 style) vs D_fix_m and has NOT approved D yet. Turn on per run with --voice-clarity or
# config.json "voice_clarity": true only after that approval. Measured on EP1 stems (D): bed 6.6 LU under the voice static,
# ~10 LU under during speech, bed 40-150 Hz ~= voice, +2.8 dB presence, +400 Hz brightness vs A. NOT verified by ear.
CLARITY_VOICE_AF = 'highpass=f=80,equalizer=f=3000:t=o:w=1:g=2.5'          # rumble cut + presence +2.5 dB
CLARITY_BED_AF = 'highpass=f=35,lowshelf=f=120:g=-6'                       # bass-heavy bed: sub/bass shelf -6 dB
CLARITY_BED_SCOOP = ',equalizer=f=2500:t=o:w=1.5:g=-4'                     # only for beds WITH mids (--clarity-scoop)
CLARITY_DUCK_DB = -3.7                                                     # ~3.7 dB duck under speech (keep 3-5 dB)
CLARITY_BED_UNDER_DB = 6.6                                                 # static bed this far under the speech level (RMS approx.)
VOICE_ROOM_DB = -15.0   # the voice stays centre, plus a decorrelated early-reflection side this far under it (mono-safe)


def decode(path, ch=2, af=None):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path] + (['-af', af] if af else []) + ['-ac', str(ch), '-ar', str(SR), '-f', 'f32le', '-'], stdout=subprocess.PIPE, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64).reshape(-1, ch)


def encode(path, x):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    codec = ['-c:a', 'pcm_s16le'] if path.endswith('.wav') else ['-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart']
    p = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-'] + codec + [path], stdin=subprocess.PIPE)
    p.communicate(x.astype('<f4').tobytes())
    if p.returncode: sys.exit('ffmpeg failed writing ' + path)


def looped(x, n, xf=int(0.03 * SR)):
    # tile x to n samples, crossfading each join so an ambience loop does not click
    if len(x) >= n: return x[:n]
    xf = max(1, min(xf, len(x) // 4))
    step = len(x) - xf; out = np.zeros((n + len(x),) + x.shape[1:]); w = np.ones(len(x)); r = np.linspace(0, 1, xf)
    w[:xf] = r; w[-xf:] = r[::-1]
    w = w.reshape((-1,) + (1,) * (x.ndim - 1))
    for a in range(0, n, step): out[a:a + len(x)] += x * w
    out[:xf] = x[:xf]  # the very first fade-in is not a join
    return out[:n]


def fade(x, fi, fo):
    x = x.copy(); fi = min(fi, len(x) // 2); fo = min(fo, len(x) // 2); sh = (-1,) + (1,) * (x.ndim - 1)
    if fi: x[:fi] *= np.linspace(0, 1, fi).reshape(sh)
    if fo: x[-fo:] *= np.linspace(1, 0, fo).reshape(sh)
    return x


def pack_sounds(sfx_dir):
    # name -> sorted variant files: poof.wav, poof_1.wav, poof_2.wav ...
    out = {}
    for f in sorted(glob.glob(os.path.join(sfx_dir, '*.wav'))):
        m = re.match(r'^(.*?)(?:_(\d+))?$', os.path.splitext(os.path.basename(f))[0])
        out.setdefault(m.group(1), []).append(f)
    return out


def peak_time(s, hop=int(0.005 * SR)):
    n = len(s) // hop
    if n < 2: return 0.0
    e = np.sqrt((s[:n * hop].reshape(n, hop) ** 2).mean(axis=1))
    return float(np.argmax(np.convolve(e, np.ones(4) / 4, 'same')) * hop / SR)


def shape_pre(s, lead, floor_db=-9.0, hop=int(0.005 * SR)):
    # the part before the peak becomes a rising ramp that STARTS at floor_db under the peak (hard PRE_ATTACK onset) and
    # climbs to it: an audible attack where the motion starts, the loudest point on the cut (earshot: 'no onset, peak late').
    m = int(lead * SR)
    if m < 2 * hop: return s
    s = s.copy(); seg = s[:m]
    k = max(1, m // hop); e = np.sqrt((seg[:k * hop].reshape(k, hop) ** 2).mean(axis=1)) + 1e-9
    e = np.interp(np.arange(m), (np.arange(k) + 0.5) * hop, np.convolve(e, np.ones(3) / 3, 'same'))
    pk = np.sqrt((s[m:m + 4 * hop] ** 2).mean()) + 1e-9 if len(s) > m else e.max()
    target = pk * db(floor_db * (1 - np.linspace(0, 1, m)) ** 1.5)
    seg *= np.clip(target / e, 1.0, db(18))
    na = int(PRE_ATTACK * SR); seg[:na] *= np.linspace(0, 1, na)
    s[:m] = seg; return s / max(np.abs(s).max(), 1e-9) * max(np.abs(s[m:]).max() if len(s) > m else 1, 1e-9)


def sfx_key(bus, hop=int(0.005 * SR)):
    # 0..1 side-chain key from the SFX bus: ~5 ms attack, ~180 ms release (beds dip under every hit)
    n = len(bus) // hop + 1
    e = np.sqrt(np.pad(bus ** 2, (0, n * hop - len(bus))).reshape(n, hop).mean(axis=1))
    on = np.clip((20 * np.log10(e + 1e-9) + 40) / 20, 0, 1)   # -40 dBFS -> 0, -20 dBFS and up -> 1
    g = np.zeros(n); v = 0.0
    for i in range(n):
        v += (on[i] - v) * (0.7 if on[i] > v else 0.03)
        g[i] = v
    return np.interp(np.arange(len(bus)), (np.arange(n) + 0.5) * hop, g)


def speaking(voice, hop=int(0.01 * SR), bridge=0.12, look=0.04):
    # 0..1 per sample: 1 while the voice is talking, for ducking the bed. R2-2: the old gate (-35 dB under the PEAK,
    # 250 ms release) never re-opened in the 150-300 ms phrase gaps, so the music sat at one level (voice 'active'
    # 100 %, LRA 1.5 LU, no measurable duck). Now: gate 25 dB under the voice's typical loud level (p90), gaps shorter
    # than `bridge` (inside words) are bridged, the duck starts `look` s BEFORE each phrase and releases in ~60 ms,
    # so the bed breathes up in every phrase gap and is down again for the next word.
    mono = voice.mean(axis=1); n = len(mono) // hop
    env = 20 * np.log10(np.sqrt((mono[:n * hop].reshape(n, hop) ** 2).mean(axis=1) + 1e-12))
    loud = env[env > env.max() - 40]
    on = env > (np.percentile(loud, 90) if len(loud) else env.max()) - 25
    b = int(bridge / (hop / SR)); i = 0
    while i < n:                     # bridge short gaps
        if not on[i]:
            j = i
            while j < n and not on[j]: j += 1
            if i > 0 and j < n and j - i < b: on[i:j] = True
            i = j
        else:
            i += 1
    k = int(look / (hop / SR)); on = on.astype(float)
    if k: on = np.maximum(on, np.concatenate([on[k:], np.zeros(k)]))   # look-ahead
    g = np.zeros(n); v = 0.0
    for i in range(n):
        v += (on[i] - v) * (0.6 if on[i] > v else 0.15)   # ~15 ms attack, ~60 ms release
        g[i] = v
    return np.interp(np.arange(len(mono)), (np.arange(n) + 0.5) * hop, g)


def limit(x, ceiling=CEILING, block=48, look=5):
    # look-ahead peak limiter on 1ms blocks: gain dips before a peak and recovers after it
    n = -(-len(x) // block)
    pk = np.abs(np.pad(x, ((0, n * block - len(x)), (0, 0)))).max(axis=1).reshape(n, block).max(axis=1)
    g = np.minimum(1.0, ceiling / np.maximum(pk, 1e-9))
    p = np.pad(g, look, constant_values=1.0)
    g = np.min([p[i:i + n] for i in range(2 * look + 1)], axis=0)             # hold the dip around the peak
    p = np.pad(g, look, mode='edge')
    g = np.minimum(g, np.mean([p[i:i + n] for i in range(2 * look + 1)], axis=0))  # smooth the edges
    gs = np.interp(np.arange(len(x)), (np.arange(n) + 0.5) * block, g)
    gs = np.minimum(gs, np.repeat(g, block)[:len(x)])
    return np.clip(x * gs[:, None], -1.0, 1.0), float(g.min())


BEAT_GAIN_DB = {'hook': -3, 'rule': -4, 'plant': -2, 'dread': 0, 'reveal': 2, 'climax': 2, 'cliffhanger': 1, 'twist': -3, 'cta': -3}


def beat_gain(beats, n):
    # per-beat automation for a plain music file (a generated score shapes itself): step gains, 0.8 s glides
    hop = int(0.01 * SR); g = np.zeros(n // hop + 1)
    bs = [b for b in beats if b['beat'] != 'hold']
    for i, b in enumerate(bs):
        a = int(b['t'] * 100); e = int(bs[i + 1]['t'] * 100) if i + 1 < len(bs) else len(g)
        g[a:e] = BEAT_GAIN_DB.get(b['beat'], 0)
    k = 80; g = np.convolve(np.pad(g, k, mode='edge'), np.ones(k) / k, 'same')[k:-k]
    return np.interp(np.arange(n), np.arange(len(g)) * hop, db(g))


# R2-2 macro dynamics: the whole mix (voice included) follows the story's beats, like a mixer riding the fader:
# intimate set-up, a dread stretch that climbs back up, the reveal/climax on top. dB at the start/end of each beat.
# Without it a continuous narration over a ducked bed measured LRA 1.0-1.5 LU (REF1 median 5.5, target >= 4).
# Tuned on test_seq (12.6 s, hook/plant/dread/reveal): LRA 4.6 -> 5.9 LU with the ending 1.6 LU UNDER the body
# (earshot critique flags an ending > 0 LU over the body; the reveal at +1 dB gave +3.8 LU).
BEAT_RIDE_DB = {'hook': (1, 0), 'rule': (-1.5, -2.5), 'plant': (-3, -4.5), 'dread': (-6.5, -3), 'reveal': (-1, -2),
                'climax': (1, 1), 'cliffhanger': (-1, 0), 'twist': (-4, -3), 'cta': (-2, -2)}


def ride_curve(btypes, n, glide=0.35):
    # per-sample gain from the beat map (type -> start/end dB), linear inside a beat, glides between beats
    bs = sorted([b for b in btypes if str(b['beat']).lower() in BEAT_RIDE_DB], key=lambda b: b['t'])
    if not bs: return np.ones(n)
    hop = int(0.01 * SR); m = n // hop + 1; g = np.zeros(m)
    for i, b in enumerate(bs):
        a = int(b['t'] * 100); e = int(bs[i + 1]['t'] * 100) if i + 1 < len(bs) else m
        a = max(0, min(a, m)); e = max(a, min(e, m))
        if i == 0: a = 0
        d0, d1 = BEAT_RIDE_DB[str(b['beat']).lower()]
        g[a:e] = np.linspace(d0, d1, e - a) if e > a else g[a:e]
    k = max(1, int(glide * 100)); g = np.convolve(np.pad(g, k, mode='edge'), np.ones(k) / k, 'same')[k:-k]
    return np.interp(np.arange(n), np.arange(len(g)) * hop, db(g))


END_MAX_DB, END_WIN_S, END_RAMP_S = 1.0, 1.25, 0.5   # R3-4: the closing stretch may sit at most this far over the body


def end_guard(mix, n):
    """The landing: beat ride + score escalation + the reveal hit stack up at the very end (test_seq: last 1.25 s
    +2.9 LU over the body, earshot 'closing level high'). Measure the 400 ms RMS of the last max(END_WIN_S, 10 %) vs
    the body (10-88 %, median of 400 ms windows) and ride the tail down smoothly to END_MAX_DB over it. Returns (gain, dB)."""
    g = np.ones(n)
    if n < int(4 * SR):
        return g, 0.0
    w = int(0.4 * SR); hop = int(0.1 * SR)
    mono = mix.mean(axis=1)
    def lev(a, b):
        idx = range(max(0, a), max(a + 1, b - w), hop)
        v = [20 * np.log10(np.sqrt((mono[i:i + w] ** 2).mean()) + 1e-9) for i in idx]
        return np.array(v) if v else np.array([-120.0])
    body = float(np.median(lev(int(0.10 * n), int(0.88 * n))))
    t0 = n - max(int(END_WIN_S * SR), int(0.10 * n))
    tail = float(np.mean(lev(t0, n)))
    ex = tail - body - END_MAX_DB
    if ex <= 0:
        return g, 0.0
    r0 = max(0, t0 - int(END_RAMP_S * SR))
    g[r0:t0] = db(-ex * (0.5 - 0.5 * np.cos(np.linspace(0, np.pi, t0 - r0))))
    g[t0:] = db(-ex)
    return g, round(-ex, 1)


def hold_mask(beats, n):
    # 1 normally, 0 inside each hold (30 ms out, 250 ms back in): music and sfx stop, voice and room tone stay
    m = np.ones(n)
    for b in beats:
        if b['beat'] not in ('hold', 'silence'): continue
        a = int(b['t'] * SR); e = int((b['t'] + float(b.get('dur') or 0.6)) * SR)
        f1, f2 = int(0.03 * SR), int(0.25 * SR)
        a0 = max(0, a - f1); m[a0:a] = np.minimum(m[a0:a], np.linspace(1, 0, a - a0)); m[a:e] = 0
        seg = m[e:e + f2]; m[e:e + len(seg)] = np.minimum(seg, np.linspace(0, 1, len(seg)))
    return m


def _lib_files(spec, sounds):
    kind, _, names = spec.partition(':')
    if kind == 'pack':
        return sounds.get(names, [])
    out = []
    for nm in names.split('|'):
        out += sorted(f for f in glob.glob(os.path.join(LIB, nm, '*')) if f.lower().endswith(('.mp3', '.wav', '.ogg', '.flac')))
    return out


def _env(x, hop=int(0.005 * SR)):
    m = np.abs(x).max(axis=1) if x.ndim == 2 else np.abs(x)
    k = len(m) // hop
    return (np.sqrt((m[:k * hop].reshape(k, hop) ** 2).mean(axis=1)) if k else np.zeros(1)), hop


def onset_index(x, rel_db=-14.0):
    # first sample where the 5 ms envelope reaches rel_db under the sound's peak = the ATTACK
    e, hop = _env(x)
    return int(np.argmax(e >= e.max() * db(rel_db))) * hop


def autopan(x, p0, p1, centre_at):
    # equal-power balance sweep p0 -> p1 (-1 left .. +1 right), crossing 0 at sample centre_at (the cut)
    n = len(x); idx = np.arange(n)
    p = np.where(idx < centre_at, p0 * (1 - idx / max(centre_at, 1)), p1 * (idx - centre_at) / max(n - centre_at, 1))
    th = (np.clip(p, -1, 1) + 1) * np.pi / 4
    return x * np.stack([np.cos(th), np.sin(th)], 1) * np.sqrt(2)


def design_transition(kind, sounds, k, pan=(-0.7, 0.7)):
    """Stereo transition sound; returns (signal (n,2), lead, files) where lead = seconds from its start to the CUT."""
    pre = AIR_PRE + (0.25 if kind == 'flash' else 0.0)
    n = int((pre + 1.4) * SR); c = int(pre * SR)
    out = np.zeros((n, 2)); used = []
    layers = list(TRANS[kind])
    if not any(_lib_files(sp, sounds) for sp, _, _ in layers if sp.startswith('lib:')):   # no sfxlib on this machine:
        layers = [('pack:whoosh', 'air', 0.0), ('pack:thud', 'hit', -3.0)]               # the pack's own whoosh + thud
        print(f'warning: no sfxlib/openverse recordings for the {kind} transition: using the pack whoosh/thud')
    for li, (spec, role, gdb) in enumerate(layers):
        fs = _lib_files(spec, sounds)
        if not fs: continue
        f = fs[(k + li) % len(fs)]; used.append(os.path.relpath(f, ROOT))
        x = decode(f, 2)
        if kind == 'whip':   # R3-2: a whip is air: 2nd-order high-pass at WHIP_HP_HZ (library whooshes carry a low
            F = np.fft.rfft(x, axis=0); fr = np.fft.rfftfreq(len(x), 1 / SR)[:, None]   # thump earshot heard as 'drum hit')
            x = np.fft.irfft(F / np.sqrt(1 + (WHIP_HP_HZ / np.maximum(fr, 1)) ** 4), len(x), axis=0)
        x = x / max(np.abs(x).max(), 1e-9)
        if role == 'air':      # natural swell: peak ON the cut, raised-cosine fade-in (no hard onset = no 'pop')
            p = int(peak_time(x.mean(1)) * SR)
            a = max(0, p - int(AIR_PRE * SR)); seg = x[a:p + int(AIR_POST * SR)].copy()
            m = min(p - a, len(seg))
            if m > 8: seg[:m] *= ((0.5 - 0.5 * np.cos(np.linspace(0, np.pi, m))) ** 1.5)[:, None]
            seg = autopan(fade(seg, 0, int(0.12 * SR)), pan[0], pan[1], p - a)
            s0 = c - (p - a)
        elif role == 'hit':    # attack ON the cut, leaning to where the move ends
            o = onset_index(x, -20.0)
            seg = fade(x[max(0, o - int(0.002 * SR)):o + int(0.9 * SR)], int(0.002 * SR), int(0.35 * SR))
            seg = autopan(seg, pan[1] * 0.3, pan[1] * 0.3, 0)
            s0 = c - int(0.002 * SR)
        else:                  # swell: the riser's stretch before its peak, ending ON the cut
            p = int(peak_time(x.mean(1)) * SR) or len(x)
            a = max(0, p - c); seg = fade(x[a:p], int(0.5 * (p - a)), int(0.02 * SR))
            s0 = c - (p - a)
        s0 = max(0, s0); seg = seg[:n - s0]
        if role != 'hit' and kind != 'whip':   # suck-in: the swell ducks SUCK_DB over the last SUCK_S before the cut, so the hit's
            g = np.ones(len(seg)); ce = c - s0; ca = max(0, ce - int(SUCK_S * SR))   # attack is a big rise ON the cut
            if 0 < ce <= len(seg): g[ca:ce] = np.linspace(1, db(SUCK_DB), ce - ca); g[ce:ce + int(0.004 * SR)] = np.linspace(db(SUCK_DB), 1, len(g[ce:ce + int(0.004 * SR)]))
            seg = seg * g[:, None]
        out[s0:s0 + len(seg)] += seg * db(gdb)
    return out / max(np.abs(out).max(), 1e-9), pre, used


def decorrelate(m, delay=0.013, hp=180.0):
    # a side signal made from the mid: high-passed, Haas-delayed copy (mono-compatible: it cancels in L+R)
    d = int(delay * SR); y = np.zeros_like(m); y[d:] = m[:-d] if d else m
    F = np.fft.rfft(y); f = np.fft.rfftfreq(len(y), 1 / SR)
    return np.fft.irfft(F / np.sqrt(1 + (hp / np.maximum(f, 1)) ** 4), len(y))


def widen(x, side_db_target):
    # put a bed's side at side_db_target under its mid (adds decorrelated side when the source is near mono)
    M = (x[:, 0] + x[:, 1]) / 2; S = (x[:, 0] - x[:, 1]) / 2
    rm, rs = np.sqrt((M ** 2).mean()) + 1e-12, np.sqrt((S ** 2).mean()) + 1e-12
    want = rm * db(side_db_target)
    if rs < want * db(-6):
        D = decorrelate(M); S = S + D * (np.sqrt(max(want ** 2 - rs ** 2, 0)) / (np.sqrt((D ** 2).mean()) + 1e-12))
    else:
        S = S * min(want / rs, db(9))
    return np.stack([M + S, M - S], 1)


def side_db(x):
    M = (x[:, 0] + x[:, 1]) / 2; S = (x[:, 0] - x[:, 1]) / 2
    return float(20 * np.log10((np.sqrt((S ** 2).mean()) + 1e-12) / (np.sqrt((M ** 2).mean()) + 1e-12)))


def dip_curve(times, n):
    # music gain: falls DIP_DB over DIP_FALL s starting DIP_PRE s before each time, stays down, back up ON it (30 ms)
    g = np.ones(n); fall = int(DIP_FALL * SR)
    for t in times:
        c = int(t * SR); a = max(0, c - int(DIP_PRE * SR))
        if a >= n or c <= 0: continue
        r = min(fall, max(c - a, 1))
        g[a:a + r] = np.minimum(g[a:a + r], np.linspace(1, db(DIP_DB), r))
        g[a + r:c] = np.minimum(g[a + r:c], db(DIP_DB))
        b = min(n, c + int(0.03 * SR)); g[c:b] = np.minimum(g[c:b], np.linspace(db(DIP_DB), 1, b - c))
    return g


def rms_db(x):
    return float(20 * np.log10(np.sqrt((np.asarray(x) ** 2).mean()) + 1e-12))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--video', default='')
    for k in ('voice', 'cues', 'music', 'out'): ap.add_argument('--' + k, default='')
    ap.add_argument('--sfx', default=os.path.join(ROOT, 'sfx'))
    ap.add_argument('--sfx-db', type=float, default=SFX_DB)
    ap.add_argument('--music-db', type=float, default=MUSIC_DB)
    ap.add_argument('--duck-db', type=float, default=DUCK_DB)
    ap.add_argument('--amb-db', type=float, default=0.0)
    ap.add_argument('--music-level', default='peak', choices=['peak', 'asis'])
    ap.add_argument('--no-beat-auto', action='store_true')
    ap.add_argument('--no-ride', action='store_true')   # no beat-level fader ride (BEAT_RIDE_DB)
    ap.add_argument('--voice-clarity', action='store_true', help='mix D (MUSIC_RESEARCH): voice HPF+presence, bed bass shelf, '
                    'bed 6.6 dB under speech, 3.7 dB duck. DEFAULT ON since 2026-11-14 (user approved A/B: D clearer); set config.json "voice_clarity": false to disable')
    ap.add_argument('--clarity-scoop', action='store_true', help='with --voice-clarity: also scoop the bed 2.5 kHz -4 dB (beds with mids)')
    explicit_duck = any(a.startswith('--duck-db') for a in sys.argv[1:])
    o = ap.parse_args()
    try:
        _cfg = json.load(open(os.path.join(ROOT, 'config.json')))
    except Exception:
        _cfg = {}
    clarity = o.voice_clarity or bool(_cfg.get('voice_clarity', True))
    if clarity and not explicit_duck:
        o.duck_db = CLARITY_DUCK_DB
    if o.video:
        d = os.path.join(ROOT, 'videos', o.video, 'audio')
        voice_p, cues_p, out_p = os.path.join(d, 'voice.wav'), os.path.join(d, 'cues.json'), os.path.join(d, 'mix.m4a')
        music = [f for f in sorted(glob.glob(os.path.join(d, 'music.*')))   # audio only: a music.json sidecar sorted first
                 if f.lower().endswith(('.wav', '.mp3', '.m4a', '.aac', '.flac', '.ogg', '.mp4', '.webm'))]
        music_p = music[0] if music else ''
        amb_p = os.path.join(d, 'ambience.wav') if os.path.exists(os.path.join(d, 'ambience.wav')) else ''
    else:
        voice_p, cues_p, out_p, music_p = os.path.join(ROOT, 'source', 'audio.m4a'), os.path.join(ROOT, 'out', 'cues.json'), os.path.join(ROOT, 'out', 'mix_sfx.m4a'), ''
        amb_p = ''
    voice_p, cues_p, out_p, music_p = o.voice or voice_p, o.cues or cues_p, o.out or out_p, o.music or music_p

    voice = decode(voice_p, af=CLARITY_VOICE_AF if clarity else None)
    voice *= db(VOICE_PEAK_DB) / max(np.abs(voice).max(), 1e-9)
    allcues = json.load(open(cues_p)) if os.path.exists(cues_p) else []
    cues = [c for c in allcues if c.get('name')]          # sound cues; beat/amb cues have no name
    beats = sorted([c for c in allcues if c.get('beat')], key=lambda c: c['t'])
    if not cues: print('warning: no cues at', cues_p)
    sounds = pack_sounds(o.sfx)
    conf = json.load(open(os.path.join(o.sfx, 'pack.json'))) if os.path.exists(os.path.join(o.sfx, 'pack.json')) else {}
    cache = {}

    # ---- sfx bus (stereo) ----
    placed = []; used = {}; missing = {}; last = {}; trans = []
    for c in sorted(cues, key=lambda c: c['t']):
        name = c['name']
        kind = c.get('kind') or (TRANS_NAMES.get(name) if (c.get('cut') or name in ('whoosh', 'flash', 'push')) else None)
        if kind in TRANS:     # a transition: designed stereo sound, accent ON the cut, panned with the move
            k = used.get('~' + kind, 0); used['~' + kind] = k + 1
            pan = c.get('pan') or (-0.7, 0.7)
            s, lead, files = design_transition(kind, sounds, k, (float(pan[0]), float(pan[1])))
            vol = float(c.get('vol', 1)) ** VOL_CURVE
            tg = WHIP_GAIN_DB if kind == 'whip' else 0.0   # air has a low crest: same peak = far less heard
            placed.append((int(round((c['t'] - lead) * SR)), s * db(o.sfx_db + 1.0 + tg) * vol, bool(c.get('through'))))
            trans.append(dict(t=c['t'], kind=kind, pan=[float(pan[0]), float(pan[1])], files=files))
            continue
        if name not in sounds: missing[name] = missing.get(name, 0) + 1; continue
        k = used.get(name, 0); used[name] = k + 1
        f = sounds[name][k % len(sounds[name])]          # variants in rotation: deterministic, never the same one twice in a row
        if f not in cache:
            x = decode(f, 1)[:, 0]; cache[f] = x / max(np.abs(x).max(), 1e-9)   # every pack sound starts at 0 dBFS peak
            if name.startswith(PEAK_ALIGN): cache[f] *= db(PEAK_BOOST_DB)        # low-crest swells need more peak to read
        s = cache[f]; cf = conf.get(name, {})
        if c.get('dur'): s = fade(looped(s, int(c['dur'] * SR)), int(0.04 * SR), int(0.12 * SR))
        t0, k0 = last.get(name, (-9, 1.0))
        rep = max(REPEAT_FLOOR, k0 * REPEAT_STEP) if c['t'] - t0 < REPEAT_WIN else 1.0
        last[name] = (c['t'], rep)
        lead = cf.get('lead', 0)
        if cf.get('align', 'peak' if name.startswith(PEAK_ALIGN) else 'start') == 'peak':
            lead = peak_time(s)   # a swell's loud middle lands ON the cue
            pre = float(cf.get('pre', PRE_MAX))
            if lead > pre:
                cut = int(round((lead - pre) * SR)); s = s[cut:].copy(); lead = pre
            s = shape_pre(s, lead)
        a = int(round((c['t'] - lead) * SR))
        vol = float(c.get('vol', 1)) ** VOL_CURVE   # 0.3 -> 0.55: quiet cues still clear the bed, loud ones stay loud
        g = db(o.sfx_db + cf.get('gain', 0)) * vol * rep
        p = float(c.get('pan', 0) if not isinstance(c.get('pan'), (list, tuple)) else c['pan'][0])
        th = (np.clip(p, -1, 1) + 1) * np.pi / 4    # point sounds: equal-power pan (cue "pan": -1..1), centre default
        placed.append((a, s[:, None] * np.array([np.cos(th), np.sin(th)]) * np.sqrt(2) * g, bool(c.get('through'))))
    for name, k in missing.items(): print(f'warning: no sound "{name}" in the pack ({k} cue{"s" if k > 1 else ""} skipped)')

    n = max([len(voice)] + [a + len(s) for a, s, _ in placed])
    if o.video: n = len(voice); placed = [(a, s[:max(0, n - a)], th) for a, s, th in placed if a < n]   # the video is as long as its voice
    # R3-2: a whip lands where the next line starts (test_seq 7.40 s): the voice masked it (earshot 'spoken word', no
    # whoosh). Tuck the voice WHIP_TUCK_DB under the whoosh body (cut-0.22 .. cut+0.10 s, 40 ms ramps) so the air reads.
    for tr in trans:
        if tr['kind'] != 'whip': continue
        a, b, r = int((tr['t'] - 0.22) * SR), int((tr['t'] + 0.10) * SR), int(0.04 * SR)
        g = np.ones(len(voice)); lo = db(WHIP_TUCK_DB)
        for i0, i1, v0, v1 in ((a - r, a, 1, lo), (a, b, lo, lo), (b, b + r, lo, 1)):
            i0c, i1c = max(0, i0), min(len(g), i1)
            if i1c > i0c: g[i0c:i1c] = np.linspace(v0, v1, i1 - i0)[i0c - i0:i1c - i0]
        voice = voice * g[:, None]
    mix = np.zeros((n, 2)); mix[:len(voice)] += voice
    if VOICE_ROOM_DB is not None:   # R2-1: a dry mono voice over beds measured side -21.8 dB under mid (REF1 -14.5..-5)
        vr = decorrelate(voice.mean(axis=1), delay=0.009, hp=300.0) * db(VOICE_ROOM_DB)
        mix[:len(voice), 0] += vr; mix[:len(voice), 1] -= vr
    bus = np.zeros((n, 2)); bus_th = np.zeros((n, 2))   # bus_th: cues marked "through" play inside a hold
    for a, s, th in placed:
        if a < 0: s = s[-a:]; a = 0
        (bus_th if th else bus)[a:a + len(s)] += s
    hold = hold_mask(beats, n)
    sfx_all = bus * hold[:, None] + bus_th
    mix += sfx_all
    key = sfx_key(sfx_all.mean(axis=1))
    talk = np.zeros(n); talk[:len(voice)] = speaking(voice)

    # dips: the music drops out for a beat before every transition cut and before reveal/climax beats
    bj = os.path.join(os.path.dirname(cues_p), 'beats.json')
    btypes = [dict(t=b['t'], beat=b.get('type') or b.get('beat')) for b in (json.load(open(bj)) if os.path.exists(bj) else [])
              if b.get('type') or b.get('beat')] + beats
    # (a generated score already rests before reveal/climax itself: only plain music files get the beat dips here)
    beat_dips = {round(float(b['t']), 3) for b in btypes if str(b['beat']).lower() in DIP_BEATS} if o.music_level == 'peak' else set()
    dips = sorted({round(tr['t'], 3) for tr in trans} | beat_dips)
    report = dict(transitions=trans, dips=dips, voice_clarity=bool(clarity))

    # ---- music bed ----
    if music_p:
        m = decode(music_p, af=(CLARITY_BED_AF + (CLARITY_BED_SCOOP if o.clarity_scoop else '')) if clarity else None)
        m = looped(m, n, int(0.5 * SR))
        if clarity:   # static bed level relative to the voice WHILE SPEAKING (RMS; re-measure LUFS with audio_qa.py)
            vs = voice[:n][talk[:len(voice)] > 0.5] if (talk[:len(voice)] > 0.5).any() else voice
            m *= db(rms_db(vs) - CLARITY_BED_UNDER_DB - rms_db(m))
            report['bed_under_voice_db_rms'] = round(rms_db(vs) - rms_db(m), 1)
        elif o.music_level == 'peak':
            m *= db(o.music_db) / max(np.abs(m).max(), 1e-9)
            if beats and not o.no_beat_auto: m *= beat_gain(beats, n)[:, None]
        report['music_side_in'] = round(side_db(m), 1)
        m = widen(m, BED_SIDE_DB['music'])
        duck = 1 + (db(o.duck_db) - 1) * talk
        m *= (duck * (1 + (db(SC_MUSIC_DB) - 1) * key) * dip_curve(dips, n))[:, None]
        m = fade(m, int(0.3 * SR), int(0.25 * SR)) * hold[:, None]   # 1.0 s end fade sagged the last beat
        mix += m
        # measured duck: music level while the voice talks vs in the gaps (same 100 ms windows, dips excluded)
        h = int(0.02 * SR); kk = n // h
        e = np.sqrt((m[:kk * h] ** 2).mean(1).reshape(kk, h).mean(1) + 1e-12); tk = talk[:kk * h].reshape(kk, h).mean(1)
        dg = dip_curve(dips, n)[:kk * h].reshape(kk, h).min(1) > 0.9
        on, off = e[(tk > 0.95) & dg], e[(tk < 0.05) & dg]
        report['duck_db_measured'] = round(float(20 * np.log10(np.median(on) / np.median(off))), 1) if len(on) > 2 and len(off) > 2 else None
        report['duck_db_set'] = float(o.duck_db)
        gc = duck[:kk * h].reshape(kk, h).mean(1)   # the applied duck gain itself (independent of the music's own swells)
        report['duck_db_applied'] = round(float(20 * np.log10(np.median(gc[tk > 0.95]) / max(np.median(gc[tk < 0.05]), 1e-9))), 1) if (tk > 0.95).any() and (tk < 0.05).any() else None
        report['gap_pct'] = round(100 * float((tk < 0.05).mean()), 1)
        report['voice_active_pct'] = round(100 * float((tk > 0.5).mean()), 1)
        report['music_side'] = round(side_db(m), 1)
    if amb_p:
        a = looped(decode(amb_p), n, int(0.5 * SR)) * db(o.amb_db)
        report['amb_side_in'] = round(side_db(a), 1)
        a = widen(a, BED_SIDE_DB['amb'])
        a *= ((1 + (db(-2.0) - 1) * talk) * (1 + (db(SC_AMB_DB) - 1) * key) * (0.5 + 0.5 * dip_curve(dips, n)))[:, None]
        # room tone NEVER drops out: 15 ms anti-click in, and the tail only dips to -12 dB (the film's own end fade does the rest)
        a = fade(a, int(0.015 * SR), 0)
        r = int(0.6 * SR); a[-r:] *= np.linspace(1, db(-12), r)[:, None]
        mix += a
        report['amb_side'] = round(side_db(a), 1)

    if not o.no_ride and btypes:
        mix *= ride_curve(btypes, n)[:, None]; report['ride'] = True
    eg, report['end_guard_db'] = end_guard(mix, n)
    mix *= eg[:, None]
    mix, dip = limit(mix)
    report['mix_side_db'] = round(side_db(mix), 1)
    encode(out_p, mix)
    json.dump(report, open(os.path.join(os.path.dirname(out_p), 'mix_report.json'), 'w'), indent=1)
    print(f'wrote {out_p}: {n / SR:.2f}s, {len(placed)} cues placed ({", ".join(f"{k} {v}" for k, v in sorted(used.items(), key=lambda kv: -kv[1]))})'
          + (f', music {os.path.basename(music_p)}' if music_p else '') + f', peak {20 * np.log10(np.abs(mix).max() + 1e-9):.1f} dBFS, limiter max dip {20 * np.log10(dip):.1f} dB')
    print(f"  stereo side {report['mix_side_db']} dB under mid (target -14..-8), duck applied {report.get('duck_db_applied')} dB "
          f"(target -3..-6; music level talk vs gaps {report.get('duck_db_measured')} dB), {len(trans)} transitions, {len(dips)} music dips")


if __name__ == '__main__':
    main()
