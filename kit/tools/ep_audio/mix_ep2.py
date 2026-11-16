import os
import json,subprocess,numpy as np,os
D=os.environ['EP'].rstrip('/')+'/'; A=D+'audio/'
K=os.path.join(os.environ.get('RBX_HOME',os.path.expanduser('~/RobloxStories')),'sfx')+'/'
SR=48000
def load(p,extra=''):
    af=['-af',extra] if extra else []
    raw=subprocess.run(['ffmpeg','-v','error','-i',p,*af,'-ac','1','-ar',str(SR),'-f','f32le','-'],capture_output=True,check=True).stdout
    return np.frombuffer(raw,np.float32).copy()
W=json.load(open(A+'words.json')); P={int(k):v for k,v in json.load(open(A+'pauses.json')).items()}
FILES={'VINE-STYLE BOOM':[(K+'boom.wav','lowpass=f=900',0.0)],'BOING':[(K+'boing.wav','',0)],'BONK':[(K+'bonk.wav','',0)],
 'CROWD "OHHH"':[(D+'sfx/ohhh.mp3','',0)],'CRICKETS':[(K+'crickets.wav','',0)],'SPLAT':[(K+'splat.wav','',0)],'BRUH':[(D+'sfx/bruh.mp3','',0)],
 'FAST-FORWARD WHOOSH':[(K+'whoosh.wav','',0)],'POP':[(K+'pop.wav','',0)],'CHA-CHING':[(K+'cashier.wav','',0)],'DUN DUN DUNNN':[(D+'sfx/dundun.mp3','',0)],
 'RECORD SCRATCH':[(D+'sfx/scratch.mp3','',0)],'FAHHH':[(D+'sfx/fahhh.mp3','',0)],'CROWD GASP + BOOM':[(K+'gasp.wav','',0.05),(K+'boom.wav','lowpass=f=900',0)],
 'SAD TROMBONE':[(D+'sfx/trombone.mp3','',0)],'AWW':[(K+'aww.wav','',0)],'CHEER':[(K+'cheer.wav','',0)],'DING':[(K+'ding.wav','',0)]}
GAIN={'CRICKETS':0.35,'DUN DUN DUNNN':0.45,'SAD TROMBONE':0.45,'CHEER':0.4,'CROWD "OHHH"':0.5,'BRUH':0.7,'FAHHH':0.7,'FAST-FORWARD WHOOSH':0.4}
voice=load(A+'voice.wav')
dur=len(voice)/SR+0.8
N=int(dur*SR); sfx=np.zeros(N,np.float32); cues=[]
def put(x,t,g):
    x=x/ (np.abs(x).max()+1e-9)*0.5*g
    i=int(t*SR); j=min(N,i+len(x)); sfx[i:j]+=x[:j-i]
for i,lab in sorted(P.items()):
    t=W[i]['end']+0.04
    for f,ex,off in FILES[lab]:
        put(load(f,ex),t+off,GAIN.get(lab,0.8))
    cues.append((round(t,2),lab))
for i,lab,dt in ((338,'ICON heart',0),(339,'ICON share',0),(339,'ICON follow button',0.2),(348,'ICON comment',0),(349,'ICON forgive',0),(351,'ICON forget',0)):
    t=W[i]['start']+dt; put(load(K+'pop.wav'),t,0.55); cues.append((round(t,2),lab))
tc=W[341]['start']+0.12; put(load(K+'click.wav'),tc,0.7); cues.append((round(tc,2),'MOUSE click follow'))
kl=load(K+'kids_laugh.wav'); put(kl,0.3,0.35); put(kl,W[64]['start'],0.5)
v=np.zeros(N,np.float32); v[:len(voice)]=voice
mix=v+sfx
mix.astype(np.float32).tofile(A+'nomusic.f32')
subprocess.run(['ffmpeg','-v','error','-y','-f','f32le','-ar',str(SR),'-ac','1','-i',A+'nomusic.f32','-af','loudnorm=I=-14:TP=-1.5:LRA=11,alimiter=limit=0.84:level=false','-ar','48000','-ac','2',A+'mix_nomusic.wav'],check=True)
# preview: + Numbers bed (kit house track = TEMPOREX Numbers) from 0 to the auditorium line, no Another Love file available
t_end=W[237]['start']
bed=load(A+'house_music.m4a','highpass=f=35,lowshelf=f=120:g=-6')
b=np.zeros(N,np.float32); n=min(len(bed),int(t_end*SR)); b[:n]=bed[:n]
fade=int(1.0*SR); b[n-fade:n]*=np.linspace(1,0,fade)
# bed ~ 7 dB under voice (rms during speech)
rv=np.sqrt(np.mean(v[:n]**2)); rb=np.sqrt(np.mean(b[:n]**2))+1e-9
b*= (rv/rb)*10**(-7/20)
# duck ~3.5 dB under voice envelope
env=np.convolve(np.abs(v),np.ones(4800)/4800,'same'); duck=np.where(env>rv*0.25,10**(-3.5/20),1.0).astype(np.float32)
duck=np.convolve(duck,np.ones(2400)/2400,'same')
pm=v+sfx+b*duck
pm.astype(np.float32).tofile(A+'preview.f32')
subprocess.run(['ffmpeg','-v','error','-y','-f','f32le','-ar',str(SR),'-ac','1','-i',A+'preview.f32','-af','loudnorm=I=-14:TP=-1.5:LRA=11,alimiter=limit=0.84:level=false','-ar','48000','-ac','2',A+'mix_preview.wav'],check=True)
json.dump(cues,open(A+'sfx_cues_placed.json','w'),indent=0)
print('dur',round(dur,2),'cues',len(cues),'bed until',round(t_end,2))
for f in ('mix_nomusic.wav','mix_preview.wav'):
    o=subprocess.run(['ffmpeg','-i',A+f,'-af','ebur128=peak=true','-f','null','-'],capture_output=True,text=True).stderr
    print(f,[l.strip() for l in o.splitlines() if l.strip().startswith(('I:','Peak:'))][-2:])
