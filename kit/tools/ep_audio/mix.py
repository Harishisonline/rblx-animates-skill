# kit v4.2: per-episode mix. Config: $EP/audio/mix_cfg.json
#  files: {LABEL: [[path, ffmpeg_filter, offset_s], ...]}  tokens: {K}=kit sfx dir, {S}=$EP/sfx/, {A}=$EP/audio/, {RB}=kit root
#  gain: {LABEL: g}   extra: [[path, word_index or "t:<sec>", gain]]
#  bed: {"file":..., "from_word":0, "to_word":-1, "under_db":7, "duck_db":3.5, "fade_out":2.0}  (preview only; nomusic = post file)
# Ending pops/click are found from the words (Like / share / follow / Comment + the two options). EP2's version: mix_ep2.py.
import os, json, subprocess, re, numpy as np
D = os.environ['EP'].rstrip('/') + '/'; A = D + 'audio/'
RB = os.environ.get('RBX_HOME', os.path.expanduser('~/RobloxStories'))
K = os.path.join(RB, 'sfx') + '/'
SR = 48000
cfg = json.load(open(A + 'mix_cfg.json'))
def P(p): return p.replace('{K}', K).replace('{S}', D + 'sfx/').replace('{A}', A).replace('{RB}', RB + '/')
def load(p, extra=''):
    af = ['-af', extra] if extra else []
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', P(p), *af, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()
W = json.load(open(A + 'words.json')); PZ = {int(k): v for k, v in json.load(open(A + 'pauses.json')).items()}
voice = load(A + 'voice.wav'); dur = len(voice) / SR + 0.8
N = int(dur * SR); sfx = np.zeros(N, np.float32); cues = []
def put(x, t, g):
    x = x / (np.abs(x).max() + 1e-9) * 0.5 * g
    i = int(t * SR); j = min(N, i + len(x)); sfx[i:j] += x[:j - i]
G = cfg.get('gain', {})
for i, lab in sorted(PZ.items()):
    t = W[i]['end'] + 0.04
    for f, ex, off in cfg['files'][lab]:
        put(load(f, ex), t + off, G.get(lab, 0.8))
    cues.append((round(t, 2), lab))
w = [re.sub(r'[^a-z]', '', x['word'].lower()) for x in W]
def last(k): return max(i for i, x in enumerate(w) if x == k)
iL, iS, iF, iC = last('like'), last('share'), last('follow'), last('comment')
opts = [i for i in range(iC + 1, len(w)) if w[i] not in ('or', '')][:2]
for i, lab, dt in ((iL, 'ICON heart', 0), (iS, 'ICON share', 0), (iS, 'ICON follow button', 0.2), (iC, 'ICON comment', 0), (opts[0], 'ICON option A', 0), (opts[1], 'ICON option B', 0)):
    t = W[i]['start'] + dt; put(load('{K}pop.wav'), t, 0.55); cues.append((round(t, 2), lab))
tc = W[iF]['start'] + 0.12; put(load('{K}click.wav'), tc, 0.7); cues.append((round(tc, 2), 'MOUSE click follow'))
for f, at, g in cfg.get('extra', []):
    t = float(at[2:]) if isinstance(at, str) else W[at]['start']
    put(load(f), t, g); cues.append((round(t, 2), 'extra ' + os.path.basename(f)))
v = np.zeros(N, np.float32); v[:len(voice)] = voice
def master(sig, name):
    sig.astype(np.float32).tofile(A + name + '.f32')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', A + name + '.f32', '-af',
                    'loudnorm=I=-14:TP=-1.5:LRA=11,alimiter=limit=0.84:level=false', '-ar', '48000', '-ac', '2', A + 'mix_' + name + '.wav'], check=True)
    os.remove(A + name + '.f32')
master(v + sfx, 'nomusic')
bc = cfg.get('bed')
if bc:
    b = np.zeros(N, np.float32)
    t0 = W[bc['from_word']]['start'] if bc.get('from_word', 0) else 0.0
    t1 = W[bc['to_word']]['start'] if bc.get('to_word', -1) != -1 else dur
    bed = load(bc['file'], 'highpass=f=35,lowshelf=f=120:g=-6')
    i0 = int(t0 * SR); n = min(len(bed), int((t1 - t0) * SR), N - i0); b[i0:i0 + n] = bed[:n]
    fi = int(0.3 * SR); b[i0:i0 + fi] *= np.linspace(0, 1, fi)
    fo = int(bc.get('fade_out', 2.0) * SR); b[i0 + n - fo:i0 + n] *= np.linspace(1, 0, fo)
    sp = slice(i0, i0 + n); rv = np.sqrt(np.mean(v[sp] ** 2)); rb = np.sqrt(np.mean(b[sp] ** 2)) + 1e-9
    b *= (rv / rb) * 10 ** (-bc.get('under_db', 7) / 20)
    env = np.convolve(np.abs(v), np.ones(4800) / 4800, 'same')
    duck = np.where(env > rv * 0.25, 10 ** (-bc.get('duck_db', 3.5) / 20), 1.0).astype(np.float32)
    for t, lab in cues:  # music dips -8 dB for 1.2 s under each meme hit (BLOX_CITY rule)
        if lab.startswith(('ICON', 'MOUSE', 'extra')): continue
        a = int(t * SR); duck[a:a + int(1.2 * SR)] = np.minimum(duck[a:a + int(1.2 * SR)], 10 ** (-8 / 20))
    duck = np.convolve(duck, np.ones(2400) / 2400, 'same')
    master(v + sfx + b * duck, 'preview')
json.dump(cues, open(A + 'sfx_cues_placed.json', 'w'), indent=0)
print('dur', round(dur, 2), 'cues', len(cues), 'ending words', iL, iS, iF, iC, opts, [W[i]['word'] for i in opts])
for f in ('mix_nomusic.wav', 'mix_preview.wav'):
    if not os.path.exists(A + f): continue
    o = subprocess.run(['ffmpeg', '-i', A + f, '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
    print(f, [l.strip() for l in o.splitlines() if l.strip().startswith(('I:', 'Peak:'))][-2:])
