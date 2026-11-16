import json,os,sys,subprocess,math,re
from PIL import Image,ImageDraw,ImageFont
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
import ep_endcard as endcard
# kit v4.2 (EP3): no episode-specific word indices, words or durations in here. Captions = the words in audio/words.json
# (= script.txt spelling, e.g. "Blox"; the TTS-only "Blocks" spelling never reaches captions). Ending found by ep_endcard.ending().
# usage: ep_captions.py <episode_dir> final|test [frame numbers | t:<seconds> ...]
#   test -> <ep>/preview/comp_<n>.jpg (540x960); uses frames/<n>.png if present, else a blank grey 1080x1920 frame.
#   final -> out/video_only.mp4, length = audio/mix_nomusic.wav (else last word end + 0.6 s).
D=os.path.abspath(os.path.expanduser(sys.argv[1]))+'/'; sys.argv=[sys.argv[0]]+sys.argv[2:]; A=D+'audio/'
FPS=30; Wd,Ht=1080,1920
CUR_T=[0.0]
FONT=ImageFont.truetype(HERE+'/ep_assets/Poppins-ExtraBold.ttf',84)
FONT2=ImageFont.truetype(HERE+'/ep_assets/Poppins-ExtraBold.ttf',58)
W=json.load(open(A+'words.json'))
EMPH={l.strip().upper() for l in open(D+'emphasis.txt') if l.strip()} if os.path.exists(D+'emphasis.txt') else set()
def clean(w): return re.sub(r'[^A-Z0-9,\'$-]','',w.upper().replace('"','')).strip(',-')  # keeps NIGHT-LIGHT
# caption groups: up to 3 words, break after punctuation
_DD=ImageDraw.Draw(Image.new('RGB',(8,8))); MAXW=960   # v4.2: a group never runs off the 1080 frame (EP3 had 3 groups at 1170-1310 px)
def _gw(ix): return sum(_DD.textlength(clean(W[j]['word']),font=FONT) for j in ix)+_DD.textlength(' ',font=FONT)*(len(ix)-1)+18
groups=[];cur=[]
for i,w in enumerate(W):
    if cur and _gw(cur+[i])>MAXW: groups.append(cur);cur=[]
    cur.append(i)
    if len(cur)==3 or re.search(r'[.,?!"]$',w['word']) or (len(cur)==2 and len(''.join(W[j]['word'] for j in cur))>13):
        groups.append(cur);cur=[]
if cur: groups.append(cur)
G=[]
for k,g in enumerate(groups):
    t0=W[g[0]]['start']; t1=W[groups[k+1][0]]['start'] if k+1<len(groups) else W[-1]['end']+0.6
    G.append((t0,t1,[clean(W[j]['word']) for j in g]))
def draw_caption(img,words,scale=1.0):
    d=ImageDraw.Draw(img)
    txt=' '.join(words); 
    parts=[(w, '#FFD21E' if re.sub(r'[^A-Z]','',w) in EMPH or w in EMPH else '#FFFFFF') for w in words]
    sp=d.textlength(' ',font=FONT); widths=[d.textlength(w,font=FONT) for w,_ in parts]
    tw=sum(widths)+sp*(len(parts)-1); x=(Wd-tw)/2; y=int(Ht*(0.68 if CUR_T[0]>=W[END['like']]['start']-0.05 else 0.65))
    for (w,c),ww in zip(parts,widths):
        d.text((x,y),w,font=FONT,fill=c,stroke_width=9,stroke_fill='#000000',anchor='lm'); x+=ww+sp
# ---- icons (our own flat shapes)
def icon(kind,size):
    s=size; im=Image.new('RGBA',(s,s),(0,0,0,0)); d=ImageDraw.Draw(im)
    d.ellipse([0,0,s-1,s-1],fill=(20,20,24,210))
    c=s/2
    if kind=='heart':
        r=s*0.16; d.ellipse([c-2*r,c-1.6*r,c,c+0.4*r],fill='#ff2d55'); d.ellipse([c,c-1.6*r,c+2*r,c+0.4*r],fill='#ff2d55')
        d.polygon([(c-2*r+2,c-0.3*r),(c+2*r-2,c-0.3*r),(c,c+2.1*r)],fill='#ff2d55')
    elif kind=='share':
        d.polygon([(c-s*0.24,c+s*0.18),(c-s*0.24,c+s*0.02),(c+s*0.02,c-s*0.10),(c+s*0.02,c-s*0.26),(c+s*0.28,c-s*0.02),(c+s*0.02,c+s*0.22),(c+s*0.02,c+s*0.06),(c-s*0.12,c+s*0.06)],fill='#ffffff')
    elif kind=='follow':
        d.ellipse([c-s*0.2,c-s*0.3,c+s*0.02,c-s*0.08],fill='#ffffff'); d.pieslice([c-s*0.32,c-s*0.04,c+s*0.14,c+s*0.42],180,360,fill='#ffffff')
        d.rectangle([c+s*0.12,c-s*0.03,c+s*0.32,c+s*0.03],fill='#2fd06b'); d.rectangle([c+s*0.19,c-s*0.10,c+s*0.25,c+s*0.10],fill='#2fd06b')
    elif kind=='comment':
        d.rounded_rectangle([c-s*0.27,c-s*0.22,c+s*0.27,c+s*0.14],radius=s*0.08,fill='#ffffff'); d.polygon([(c-s*0.12,c+s*0.12),(c-s*0.18,c+s*0.27),(c+s*0.02,c+s*0.12)],fill='#ffffff')
        for k in (-1,0,1): d.ellipse([c+k*s*0.12-s*0.03,c-s*0.07,c+k*s*0.12+s*0.03,c-s*0.01],fill='#141418')
    return im
END=endcard.ending(W)
def draw_icons(img,t):
    endcard.draw(img,t,W,D,icon)
def frame_at(n):
    return D+f'frames/{n:04d}.png'
if __name__=='__main__':
    mode=sys.argv[1]
    if mode=='test':
        os.makedirs(D+'preview',exist_ok=True)
        for arg in sys.argv[2:]:
            n=int(round(float(arg[2:])*FPS))+1 if arg.startswith('t:') else int(arg)
            t=(n-1)/FPS; CUR_T[0]=t; src=frame_at(n)   # same frame->time map as the final pass
            img=Image.open(src).convert('RGBA') if os.path.exists(src) else Image.new('RGBA',(Wd,Ht),(60,60,70,255))
            for g in G:
                if g[0]<=t<g[1]: draw_caption(img,g[2])
            draw_icons(img,t)
            img.convert('RGB').resize((540,960)).save(D+f'preview/comp_{n}.jpg',quality=85)
        print('groups',len(G))
    else:
        out=D+'out/'+mode
        n0,n1=1,int(math.ceil(W[-1]['end']*FPS+0.6*FPS))
        if os.path.exists(A+'mix_nomusic.wav'):   # match the mastered audio length (EP3: 100.85 s) so -shortest cuts nothing
            ad=float(subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',A+'mix_nomusic.wav'],capture_output=True,text=True).stdout)
            n1=int(math.ceil(ad*FPS))
        p=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{Wd}x{Ht}','-r',str(FPS),'-i','-','-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p',D+'out/video_only.mp4'],stdin=subprocess.PIPE)
        last=None
        for n in range(n0,n1+1):
            src=frame_at(n)
            if os.path.exists(src): last=src
            if last is None: raise SystemExit('no frames in '+D+'frames/')
            img=Image.open(last).convert('RGBA')
            if img.size!=(Wd,Ht): img=img.resize((Wd,Ht))
            t=(n-1)/FPS; CUR_T[0]=t
            for g in G:
                if g[0]<=t<g[1]: draw_caption(img,g[2])
            draw_icons(img,t)
            p.stdin.write(img.convert('RGB').tobytes())
        p.stdin.close(); p.wait(); print('video frames',n1)
