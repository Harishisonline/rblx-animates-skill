import os
import json,base64,sys,re,subprocess
import numpy as np
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)));
from el import call
# v5 (DRIPDYL guide, 2026-11-17): ONE REQUEST PER LINE with the line's own eleven_v3 audio tags.
#   tts_script.txt: one beat per line, tags at the start or inside the line, e.g.
#     [excited] In this town, every lie makes you SHRINK one inch.
#     [deadpan] The mayor is the size of a pencil.
#     [urgent] Until one night, I woke up to smoke. [whispers] "Run."
#   Untagged lines get DEFAULT_TAG. All [..] tags are stripped from the alignment, so words.py sees only spoken words.
#   Legacy (v4, whole script in one request): RBX_TTS_MODE=single.
# Voice and settings are the channel's fixed choice (Alex, eleven_v3) - change them only after the person says yes to a clip.
D=os.environ['EP'].rstrip('/')+'/audio/'
VOICE=os.environ.get('RBX_VOICE','yl2ZDV1MzN4HbQJbMihG')
SETTINGS={"stability":0.0,"similarity_boost":0.75,"style":0.25,"use_speaker_boost":True}
DEFAULT_TAG=os.environ.get('RBX_TTS_DEFAULT_TAG','[excited]')
MODE=os.environ.get('RBX_TTS_MODE','lines')
SR=44100
lines=[l.strip() for l in open(D+'../tts_script.txt') if l.strip() and not l.startswith('#')]

def tts(text):
    body={"text":text,"model_id":"eleven_v3","voice_settings":SETTINGS}
    r=json.loads(call(f'/text-to-speech/{VOICE}/with-timestamps?output_format=mp3_44100_192',body))
    return base64.b64decode(r['audio_base64']), (r.get('alignment') or r.get('normalized_alignment'))

def strip_tags(al):
    """Drop every [..] tag (and one following space) from a character alignment."""
    ch,st,en=al['characters'],al['character_start_times_seconds'],al['character_end_times_seconds']
    o=([],[],[]);i=0;n=len(ch)
    while i<n:
        if ch[i]=='[':
            j=i
            while j<n and ch[j]!=']': j+=1
            i=j+1
            if i<n and ch[i]==' ': i+=1
            continue
        o[0].append(ch[i]);o[1].append(st[i]);o[2].append(en[i]);i+=1
    while o[0] and o[0][0]==' ':
        for a in o: a.pop(0)
    return o

def decode(mp3):
    p=subprocess.run(['ffmpeg','-v','error','-i','pipe:0','-ac','1','-ar',str(SR),'-f','f32le','pipe:1'],input=mp3,capture_output=True,check=True)
    return np.frombuffer(p.stdout,dtype=np.float32)

if MODE=='single':
    text=" ".join(lines)
    if not text.startswith('['): text=DEFAULT_TAG+" "+text
    mp3,al=tts(text)
    open(D+'raw.mp3','wb').write(mp3)
    if os.path.exists(D+'raw.wav'): os.remove(D+'raw.wav')
    c,s,e=strip_tags(al)
    print('mode single, chars',len(text))
else:
    os.makedirs(D+'tts_lines',exist_ok=True)
    audio=[];C=[];S=[];E=[];off=0.0;nchar=0
    for k,l in enumerate(lines):
        text=l if l.startswith('[') else DEFAULT_TAG+" "+l
        cache=D+f'tts_lines/{k:03d}.json'
        if os.path.exists(cache) and json.load(open(cache)).get('text')==text:      # re-run only changed lines
            j=json.load(open(cache)); mp3=base64.b64decode(j['mp3']); al=j['al']
        else:
            mp3,al=tts(text); json.dump({'text':text,'mp3':base64.b64encode(mp3).decode(),'al':al},open(cache,'w'))
            nchar+=len(text)
        y=decode(mp3)
        c,s,e=strip_tags(al)
        if C: C.append(' '); S.append(off); E.append(off)
        C+=c; S+=[t+off for t in s]; E+=[t+off for t in e]
        audio.append(y); off+=len(y)/SR
    y=np.concatenate(audio)
    subprocess.run(['ffmpeg','-v','error','-y','-f','f32le','-ar',str(SR),'-ac','1','-i','pipe:0',D+'raw.wav'],input=y.astype(np.float32).tobytes(),check=True)
    subprocess.run(['ffmpeg','-v','error','-y','-i',D+'raw.wav','-b:a','192k',D+'raw.mp3'],check=True)   # for listening
    c,s,e=C,S,E
    print('mode lines,',len(lines),'requests, new chars billed',nchar,'duration',round(off,2))
al={'characters':c,'character_start_times_seconds':s,'character_end_times_seconds':e}
json.dump(al,open(D+'alignment.json','w'))
json.dump(al,open(D+'alignment_raw.json','w'))
