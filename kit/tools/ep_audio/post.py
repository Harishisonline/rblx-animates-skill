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
if len(pauses)>MAXP:
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
ins=sorted((mapt(words[i]['end'])-cut,i) for i in pauses)
parts=[];prev=0
for te,i in ins:
    k=int(te*SR); parts.append(y[prev:k]); parts.append(np.zeros(int(PAUSE*SR),np.float32)); prev=k
parts.append(y[prev:]); z=np.concatenate(parts)
def final_t(tt):
    m=mapt(tt)-cut; n=sum(1 for te,_ in ins if te<m-1e-6)
    return (m+n*PAUSE)
nw=[{'word':w['word'],'start':round(final_t(w['start'])/TEMPO+LEAD,3),'end':round(final_t(w['end'])/TEMPO+LEAD,3)} for w in words]
z.astype(np.float32).tofile(A+'edit.f32')
dl=f"adelay={int(LEAD*1000)}|{int(LEAD*1000)}," if LEAD>0 else ""
chain=f"{dl}atempo={TEMPO},highpass=f=80,equalizer=f=4000:t=o:w=1:g=3,acompressor=threshold=-20dB:ratio=3:attack=5:release=80,loudnorm=I=-14:TP=-1.5"
subprocess.run(['ffmpeg','-v','error','-y','-f','f32le','-ar',str(SR),'-ac','1','-i',A+'edit.f32','-af',chain,'-ar','48000',A+'voice.wav'],check=True)
json.dump(nw,open(A+'words.json','w'),indent=0)
json.dump({str(k):v for k,v in pauses.items()},open(A+'pauses.json','w'),indent=1)
dur=float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',A+'voice.wav'],capture_output=True,text=True).stdout)
sp=nw[-1]['end']-nw[0]['start']
print('cfg pause',PAUSE,'gap',GAP,'lead',LEAD,'tempo',TEMPO,'| silences cut',sum(1 for a,b in sil if b-a>DET),'pauses',len(pauses),
      'dur',round(dur,2),'first word',nw[0]['start'],'last word end',nw[-1]['end'],'wps',round(len(nw)/sp,2),'wpm',round(len(nw)/sp*60,1))
