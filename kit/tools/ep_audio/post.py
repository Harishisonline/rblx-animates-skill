import os
import json,re,subprocess,numpy as np,os,wave
# v5 (DRIPDYL guide, 2026-11-17): tighter voice edit. Settings come from audio/post_cfg.json if present, else env, else
# the defaults below. Old episodes: {"pause": 0.45, "gap": 0.14, "lead": 0.10} reproduces v4.
D=os.environ['EP'].rstrip('/')+'/'
A=D+'audio/'
SR=44100
CFG=json.load(open(A+'post_cfg.json')) if os.path.exists(A+'post_cfg.json') else {}
def opt(k,env,dflt): return float(CFG.get(k, os.environ.get(env, dflt)))
PAUSE=opt('pause','RBX_PAUSE',0.24)     # meme pause length (v4: 0.45)
GAP=opt('gap','RBX_GAP',0.08)           # any silence longer than DET is shrunk to GAP (v4: 0.14)
DET=opt('detect','RBX_DET',0.16)        # silence detection length (v4: 0.22)
LEAD=opt('lead','RBX_LEAD',0.0)         # silence before the first word (v4: 0.10)
_ST=json.load(open(D+'story.json')) if os.path.exists(D+'story.json') else {}
_FMT=str(_ST.get('format','')).lower()
# v5.1 (owner 2026-11-18): faster takes for In-this-town like the viral channels (1.12); Blox City keeps 1.08.
TEMPO=opt('tempo','RBX_TEMPO',1.12 if ('town' in _FMT or 'world' in _FMT) else 1.08)
MAXP=int(opt('max_pauses','RBX_MAXP',8))
# v5.2 (2026-11-18, owner: "no emotion, no better pause"; ref BvvcR_LJRuQ measured ~0.5 s after sentences, 0.64-0.8 s
# before/after payoffs, ~4.2 words/s inside phrases). mode "beats": keep breathing room instead of crushing every gap.
MODE=str(CFG.get('mode', os.environ.get('RBX_POST_MODE','tight')))
SENT=opt('sentence_beat','RBX_SENT',0.40)    # total silence after . ? !
COMMA=opt('comma_beat','RBX_COMMA',0.16)     # total silence after , : ;
BSUB=opt('beat_sub','RBX_BSUB',-1)          # beats.json sec minus this = added silence (default GAP); v3 takes already pause ~0.3-0.4 s
if MODE=='beats' and 'gap' not in CFG: GAP=0.12
if MODE=='beats' and 'tempo' not in CFG and 'RBX_TEMPO' not in os.environ: TEMPO=1.04
# v6.0 (2026-11-19, EARS on 4 viral In-this-world Shorts 16-34M views): mode "flow" = near-continuous speech like the
# viral narrators: every silence > 0.20 s becomes 0.18 s (their gap after a full stop), meme cues play UNDER the voice
# (no inserted pause), at most 3 deliberate beats from beats.json (the trigger, the clock, the twist; 0.3-0.5 s).
# Tempo above 1.35 flattens the melody (F1/F2 at 1.6-1.9x measured 9.3 st, owner: "robotic"): regenerate faster instead.
if MODE=='flow':
    if 'gap' not in CFG and 'RBX_GAP' not in os.environ: GAP=0.18
    if 'detect' not in CFG and 'RBX_DET' not in os.environ: DET=0.20
    if 'pause' not in CFG and 'RBX_PAUSE' not in os.environ: PAUSE=0.0
    if 'tempo' not in CFG and 'RBX_TEMPO' not in os.environ: TEMPO=1.0
MAXB=int(opt('max_beats','RBX_MAXB',3))
if TEMPO>1.35: print(f'WARN tempo {TEMPO} > 1.35 flattens the voice (EARS 2026-11-19): regenerate the take faster instead')
src=A+'raw.wav' if os.path.exists(A+'raw.wav') else A+'raw.mp3'   # v5: tts.py chunk mode writes raw.wav (no mp3 delay)
subprocess.run(['ffmpeg','-v','error','-y','-i',src,'-ac','1','-ar',str(SR),'-f','f32le',A+'raw.f32'],check=True)
x=np.fromfile(A+'raw.f32',dtype=np.float32)
# silences
out=subprocess.run(['ffmpeg','-i',src,'-af',f'silencedetect=noise=-38dB:d={DET}','-f','null','-'],capture_output=True,text=True).stderr
ss=[float(v) for v in re.findall(r'silence_start: ([\d.]+)',out)]; se=[float(v) for v in re.findall(r'silence_end: ([\d.]+)',out)]
sil=list(zip(ss,se))
words=json.load(open(A+'words_raw.json'))
cues=json.load(open(A+'meme_cues.json')) if os.path.exists(A+'meme_cues.json') else []
# meme pause after word: map cue (line, after_word) -> word index
lines=[l.split() for l in open(D+'script.txt') if l.strip() and not l.startswith('#')]
starts=np.cumsum([0]+[len(l) for l in lines])
pause_after={}
for c in cues:
    li=c['line']-1; aw=c['after_word']
    if aw is None or c['sfx'].startswith('ICON') or c.get('no_pause'): continue
    seg=lines[li]
    idxs=[j for j,t in enumerate(seg) if t==aw]
    used=pause_after.get(('line',li),[])
    j=idxs[c['nth']-1] if 'nth' in c else [j for j in idxs if j not in used][0]  # v4.2: 'nth' picks a repeated word
    pause_after.setdefault(('line',li),[]).append(j)
    pause_after[int(starts[li]+j)]=c['sfx']
pauses={k:v for k,v in pause_after.items() if isinstance(k,int)}
if len(pauses)>MAXP and MODE!='flow':
    print(f'WARN {len(pauses)} meme pauses > {MAXP} (DRIPDYL guide): mark the rest "no_pause": true in meme_cues.json')
# shrink every silence longer than DET to GAP (centred)
h=GAP/2; keep=[];t=0.0
for a,b in sil:
    if b-a>DET:
        keep.append((t,a+h)); t=b-h
keep.append((t,len(x)/SR))
def mapt(tt):
    acc=0.0
    for a,b in keep:
        if tt<=b: return acc+max(0,tt-a) if tt>=a else acc
        acc+=b-a
    return acc
segs=[]
for a,b in keep: segs.append(x[int(a*SR):int(b*SR)])
y=np.concatenate(segs)
# v5: drop leading silence before the first word, keep LEAD
w0=mapt(words[0]['start']); cut=max(0.0,w0-0.02)
y=y[int(cut*SR):]
extra={i:PAUSE for i in pauses}
if MODE=='beats':
    for i,w in enumerate(words[:-1]):
        tw=w['word'].rstrip('"\')')
        if tw[-1:] in '.?!': extra[i]=max(extra.get(i,0),SENT-GAP)
        elif tw[-1:] in ',:;': extra[i]=max(extra.get(i,0),COMMA-GAP)
if MODE in ('beats','flow'):
    bj=A+'beats.json'; _B=json.load(open(bj)) if os.path.exists(bj) else []
    if MODE=='flow' and len(_B)>MAXB: print(f'WARN {len(_B)} beats > {MAXB}: viral narration pauses 0.3-0.6 s only 2-3 times a minute')
    for c in _B:
        li=c['line']-1; idxs=[j for j,t in enumerate(lines[li]) if t==c['after_word']]
        i=int(starts[li]+idxs[c.get('nth',1)-1]); extra[i]=max(extra.get(i,0),float(c['sec'])-(GAP if BSUB<0 else BSUB))
def _at(i):   # insert in the middle of the gap after word i (v3 word ends come early: never cut a tail)
    a=mapt(words[i]['end']); b=mapt(words[i+1]['start']) if i+1<len(words) else a
    return (a+max(a,b))/2-cut
ins=sorted((_at(i),i,L) for i,L in extra.items() if L>0)
parts=[];prev=0
for te,i,L in ins:
    k=int(te*SR); parts.append(y[prev:k]); parts.append(np.zeros(int(L*SR),np.float32)); prev=k
parts.append(y[prev:]); z=np.concatenate(parts)
def final_t(tt):
    m=mapt(tt)-cut
    return m+sum(L for te,_,L in ins if te<m-1e-6)
nw=[{'word':w['word'],'start':round(final_t(w['start'])/TEMPO+LEAD,3),'end':round(final_t(w['end'])/TEMPO+LEAD,3)} for w in words]
z.astype(np.float32).tofile(A+'edit.f32')
dl=f"adelay={int(LEAD*1000)}|{int(LEAD*1000)}," if LEAD>0 else ""
chain=f"{dl}atempo={TEMPO},highpass=f=80,equalizer=f=4000:t=o:w=1:g=3,acompressor=threshold=-20dB:ratio=3:attack=5:release=80,loudnorm=I=-14:TP=-1.5"
subprocess.run(['ffmpeg','-v','error','-y','-f','f32le','-ar',str(SR),'-ac','1','-i',A+'edit.f32','-af',chain,'-ar','48000',A+'voice.wav'],check=True)
json.dump(nw,open(A+'words.json','w'),indent=0)
json.dump({str(k):v for k,v in pauses.items()},open(A+'pauses.json','w'),indent=1)
dur=float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',A+'voice.wav'],capture_output=True,text=True).stdout)
sp=nw[-1]['end']-nw[0]['start']
print('mode',MODE,'cfg pause',PAUSE,'gap',GAP,'lead',LEAD,'tempo',TEMPO,'| silences cut',sum(1 for a,b in sil if b-a>DET),'pauses',len(pauses),
      'dur',round(dur,2),'first word',nw[0]['start'],'last word end',nw[-1]['end'],'wps',round(len(nw)/sp,2),'wpm',round(len(nw)/sp*60,1))
