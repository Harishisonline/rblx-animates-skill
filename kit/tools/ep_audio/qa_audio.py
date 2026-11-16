"""kit v4.2 ep_audio QA by MEASUREMENT (no ears). usage: EP=<ep dir> RBX_HOME=~/RobloxStories python qa_audio.py
Checks: each meme hit starts inside its word gap; hit level and tail-over-speech level vs the voice speech RMS (tail avg must be
<= -10 dB); mix_nomusic/mix_final loudness (-14 +-0.5 LUFS, TP <= -1.5); bed level under the voice in speech regions.
Exit 1 on FAIL. Written for EP3 friend_secret (2026-11-16)."""
import json, subprocess, numpy as np, os, sys
RBX_HOME=os.environ.get('RBX_HOME') or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # kit root
EP=os.environ['EP'].rstrip('/')+'/'; A=EP+'audio/'; RB=RBX_HOME; K=RB+'/sfx/'
SR=48000
def P(p): return p.replace('{K}',K).replace('{S}',EP+'sfx/').replace('{A}',A).replace('{RB}',RB+'/')
def load(p, extra=''):
    af=['-af',extra] if extra else []
    raw=subprocess.run(['ffmpeg','-v','error','-i',P(p),*af,'-ac','1','-ar',str(SR),'-f','f32le','-'],capture_output=True,check=True).stdout
    return np.frombuffer(raw,np.float32).copy()
db=lambda x:20*np.log10(max(x,1e-9))
W=json.load(open(A+'words.json')); PZ={int(k):v for k,v in json.load(open(A+'pauses.json')).items()}
cfg=json.load(open(A+'mix_cfg.json')); G=cfg.get('gain',{})
voice=load(A+'voice.wav'); vpk=np.abs(voice).max()
spmask=np.zeros(len(voice)+10*SR,bool)
for w in W: spmask[int(w['start']*SR):int(w['end']*SR)]=True
vrms=np.sqrt(np.mean(voice[spmask[:len(voice)]]**2))
def cue_sig(lab):
    s=np.zeros(int(4*SR),np.float32)
    for f,ex,off in cfg['files'][lab]:
        x=load(f,ex); x=x/(np.abs(x).max()+1e-9)*0.5*G.get(lab,0.8)
        a=int(off*SR); n=min(len(x),len(s)-a); s[a:a+n]+=x[:n]
    return s
FAIL=[]
print('MEME HITS: label | word | t | gap | hit pk re voice pk, rms re speech rms | tail avg / max(100 ms) over speech re speech rms')
for i, lab in sorted(PZ.items()):
    t = W[i]['end'] + 0.04; nxt = W[i + 1]['start'] if i + 1 < len(W) else 1e9; g = nxt - t
    if not (W[i]['end'] < t < nxt): FAIL.append('%s not in gap' % lab)
    s = cue_sig(lab); gi = int(max(g, 0.05) * SR); hit = s[:gi]; tail = s[gi:]
    m = spmask[int(nxt * SR):int(nxt * SR) + len(tail)] if nxt < 1e8 else np.zeros(0, bool); tl = tail[:len(m)][m]
    tr = np.sqrt(np.mean(tl ** 2)) if len(tl) else 0
    tm = max([np.sqrt(np.mean(tail[k:k + 4800] ** 2)) for k in range(0, max(1, len(tail) - 4800), 4800)] or [0])
    ta = db(tr) - db(vrms)
    if ta > -10: FAIL.append('%s tail %.1f dB over speech' % (lab, ta))
    print('%-22s %3d %6.2f %.2f  pk %+5.1f rms %+5.1f | tail %+6.1f max %+6.1f' % (lab, i, t, g, db(np.abs(hit).max()) - db(vpk), db(np.sqrt(np.mean(hit ** 2))) - db(vrms), ta, db(tm) - db(vrms)))
for name in ('mix_nomusic.wav', 'mix_final.wav'):
    if not os.path.exists(A + name): FAIL.append(name + ' missing'); continue
    o = subprocess.run(['ffmpeg', '-i', A + name, '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
    I = float([l for l in o.splitlines() if l.strip().startswith('I:')][-1].split()[1]); TP = float([l for l in o.splitlines() if l.strip().startswith('Peak:')][-1].split()[1])
    if abs(I + 14) > 0.5 or TP > -1.5: FAIL.append('%s %.1f LUFS TP %.1f' % (name, I, TP))
    print('%s  %.1f LUFS  true peak %.1f dBTP' % (name, I, TP))
if os.path.exists(A + 'mix_final.wav') and os.path.exists(A + 'mix_nomusic.wav'):
    nm = load(A + 'mix_nomusic.wav'); pv = load(A + 'mix_final.wav'); L = min(len(nm), len(pv)); mm = spmask[:L]
    a = np.dot(pv[:L], nm[:L]) / np.dot(nm[:L], nm[:L]); res = pv[:L] - a * nm[:L]
    under = db(np.sqrt(np.mean((a * nm[:L][mm]) ** 2))) - db(np.sqrt(np.mean(res[mm] ** 2)))
    print('bed in final: %.1f dB under voice+sfx in speech regions (research 6-8 LU; < 4 dB = voice dulled, EP1)' % under)
    if under < 4: FAIL.append('bed only %.1f dB under the voice' % under)
print('AUDIO QA ' + ('PASS' if not FAIL else 'FAIL: ' + '; '.join(FAIL)))
sys.exit(1 if FAIL else 0)
