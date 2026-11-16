import os
import json,re,subprocess,numpy as np,os,wave
D=os.environ['EP'].rstrip('/')+'/'
A=D+'audio/'
SR=44100
subprocess.run(['ffmpeg','-v','error','-y','-i',A+'raw.mp3','-ac','1','-ar',str(SR),'-f','f32le',A+'raw.f32'],check=True)
x=np.fromfile(A+'raw.f32',dtype=np.float32)
# silences
out=subprocess.run(['ffmpeg','-i',A+'raw.mp3','-af','silencedetect=noise=-38dB:d=0.22','-f','null','-'],capture_output=True,text=True).stderr
ss=[float(v) for v in re.findall(r'silence_start: ([\d.]+)',out)]; se=[float(v) for v in re.findall(r'silence_end: ([\d.]+)',out)]
sil=list(zip(ss,se))
words=json.load(open(A+'words_raw.json'))
cues=json.load(open(A+'meme_cues.json'))
# meme pause after word: map cue (line, after_word) -> word index
lines=[l.split() for l in open(D+'script.txt') if l.strip() and not l.startswith('#')]
starts=np.cumsum([0]+[len(l) for l in lines])
ICON=('ICON',)
pause_after={}
for c in cues:
    li=c['line']-1; aw=c['after_word']
    if aw is None or c['sfx'].startswith('ICON'): continue
    seg=lines[li]
    # find last occurrence of aw in that line before the cue: approximate with first occurrence scanning order of cues
    idxs=[j for j,t in enumerate(seg) if t==aw]
    used=pause_after.get(('line',li),[])
    j=idxs[c['nth']-1] if 'nth' in c else [j for j in idxs if j not in used][0]  # v4.2: 'nth' picks a repeated word
    pause_after.setdefault(('line',li),[]).append(j)
    pause_after[int(starts[li]+j)]=c['sfx']
pauses={k:v for k,v in pause_after.items() if isinstance(k,int)}
# build segments: keep everything except shrink silences to 0.14 (centered), then insert pause after cue words
keep=[];t=0.0
for a,b in sil:
    if b-a>0.22:
        keep.append((t,a+0.07)); t=b-0.07
keep.append((t,len(x)/SR))
# time map orig->edited
def mapt(tt):
    acc=0.0
    for a,b in keep:
        if tt<=b: return acc+max(0,tt-a) if tt>=a else acc
        acc+=b-a
    return acc
# assemble with pauses: insert silence at mapped word-end + small
PAUSE=0.45
segs=[]
for a,b in keep: segs.append(x[int(a*SR):int(b*SR)])
y=np.concatenate(segs)
ins=sorted((mapt(words[i]['end']),i) for i in pauses)
parts=[];prev=0;shift={}
for te,i in ins:
    k=int(te*SR); parts.append(y[prev:k]); parts.append(np.zeros(int(PAUSE*SR),np.float32)); prev=k
parts.append(y[prev:]); z=np.concatenate(parts)
def final_t(tt):
    m=mapt(tt); n=sum(1 for te,_ in ins if te<m-1e-6)
    return (m+n*PAUSE)
TEMPO=1.08
nw=[{'word':w['word'],'start':round(final_t(w['start'])/TEMPO+0.10,3),'end':round(final_t(w['end'])/TEMPO+0.10,3)} for w in words]
z.astype(np.float32).tofile(A+'edit.f32')
chain=f"adelay=100|100,atempo={TEMPO},highpass=f=80,equalizer=f=4000:t=o:w=1:g=3,acompressor=threshold=-20dB:ratio=3:attack=5:release=80,loudnorm=I=-14:TP=-1.5"
subprocess.run(['ffmpeg','-v','error','-y','-f','f32le','-ar',str(SR),'-ac','1','-i',A+'edit.f32','-af',chain,'-ar','48000',A+'voice.wav'],check=True)
json.dump(nw,open(A+'words.json','w'),indent=0)
json.dump({str(k):v for k,v in pauses.items()},open(A+'pauses.json','w'),indent=1)
dur=float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',A+'voice.wav'],capture_output=True,text=True).stdout)
sp=nw[-1]['end']-nw[0]['start']
print('silences cut',sum(1 for a,b in sil if b-a>0.22),'pauses',len(pauses),'dur',round(dur,2),'last word end',nw[-1]['end'],'wpm',round(len(nw)/sp*60,1))
