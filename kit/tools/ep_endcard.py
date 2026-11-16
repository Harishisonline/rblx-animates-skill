"""Ending pop-ups (docs/ENDING_RULE.md): heart on LIKE, share on SHARE, red + FOLLOW button clicked by a cursor on FOLLOW,
comment bubble on COMMENT, then the two answer buttons on the two option words. Word indices are FOUND in words.json:
the last 'like' starts the ending; 'Comment X or Y' gives the two options."""
import re as _re


def _n(w):
    return _re.sub(r"[^a-z]", "", w.lower())


def ending(W):
    iL = max(i for i, w in enumerate(W) if _n(w["word"]) == "like")
    def after(word, start):
        return next(i for i in range(start, len(W)) if _n(W[i]["word"]) == word)
    iS = after("share", iL); iF = after("follow", iL); iC = after("comment", iL)
    iA = iC + 1; iOr = after("or", iA); iB = iOr + 1
    clean = lambda w: _re.sub(r"[^A-Z0-9]", "", w.upper())
    return dict(like=iL, share=iS, follow=iF, comment=iC, opt_a=iA, opt_b=iB,
                opt_a_text=clean(W[iA]["word"]), opt_b_text=clean(W[iB]["word"]))


# centre-screen end card: heart / share / FOLLOW button (+ mouse click) pop in on the spoken words; comment bubble + answers later
import math
from PIL import Image, ImageDraw, ImageFont
def _font(D,s): return ImageFont.truetype(__import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)),'ep_assets','Poppins-ExtraBold.ttf'),max(8,int(s)))
def pop(dt,FPS=30):
    if dt<0: return 0.0
    f=dt*FPS
    if f<4: return 1.25*f/4
    if f<8: return 1.25-0.25*(f-4)/4
    return 1.0+0.025*math.sin(dt*6)
def cursor(s):
    im=Image.new('RGBA',(s,s),(0,0,0,0)); d=ImageDraw.Draw(im)
    p=[(0.08,0.02),(0.08,0.80),(0.28,0.62),(0.42,0.95),(0.56,0.89),(0.42,0.57),(0.70,0.57)]
    d.polygon([(x*s,y*s) for x,y in p],fill='#ffffff',outline='#000000',width=max(2,s//22))
    return im
def draw(img,t,W,D,icon,Wd=1080,Ht=1920):
    E = ending(W); tL, tS, tF, tC = (W[E[k]]['start'] for k in ('like', 'share', 'follow', 'comment'))
    d=ImageDraw.Draw(img)
    row_fade = 1.0 if t<tC-0.15 else max(0.0,1-(t-(tC-0.15))/0.2)
    y=int(Ht*0.50)
    if row_fade>0:
        for kind,tt,x in (('heart',tL,0.22),('share',tS,0.42)):
            sc=pop(t-tt)
            if sc>0:
                s=int(190*sc); ic=icon(kind,s); 
                if row_fade<1: ic.putalpha(ic.getchannel('A').point(lambda a:int(a*row_fade)))
                img.alpha_composite(ic,(int(Wd*x)-s//2,y-s//2))
                d.text((int(Wd*x),y+int(125*sc)),{'heart':'LIKE','share':'SHARE'}[kind],font=_font(D,40*sc),fill='#ffffff',stroke_width=5,stroke_fill='#000',anchor='mm')
        tB=tS+0.2
        sc=pop(t-tB)
        if sc>0:
            t_click=tF+0.12; clicked=t>=t_click
            press=0.92 if t_click<=t<t_click+0.12 else 1.0
            bw,bh=int(330*sc*press),int(120*sc*press); cx=int(Wd*0.72)
            col='#5a5f66' if clicked else '#ff2d55'
            d.rounded_rectangle([cx-bw//2,y-bh//2,cx+bw//2,y+bh//2],radius=int(34*sc),fill=col,outline='#000',width=6)
            d.text((cx,y),'FOLLOWING' if clicked else '+ FOLLOW',font=_font(D,(46 if clicked else 54)*sc*press),fill='#ffffff',stroke_width=4,stroke_fill='#000',anchor='mm')
            # mouse: glides in from bottom-right, clicks, rests
            a=min(1.0,max(0.0,(t-(tB+0.1))/max(0.2,t_click-0.05-(tB+0.1)))); a=a*a*(3-2*a)
            sx,sy=Wd*0.98,Ht*0.78; ex,ey=cx+40,y+25
            mx,my=sx+(ex-sx)*a,sy+(ey-sy)*a
            cs=int(110*(0.85 if t_click<=t<t_click+0.12 else 1.0))
            if t>=tB+0.1 and row_fade>0:
                img.alpha_composite(cursor(cs),(int(mx),int(my)))
                if t_click<=t<t_click+0.25:
                    r=int(30+260*(t-t_click)); d.ellipse([mx-r,my-r,mx+r,my+r],outline=(255,255,255,int(220*(1-(t-t_click)/0.25))),width=6)
    sc=pop(t-tC)
    if sc>0:
        s=int(220*sc); img.alpha_composite(icon('comment',s),(Wd//2-s//2,y-s//2))
        d.text((Wd//2,y+int(140*sc)),'COMMENT',font=_font(D,44*sc),fill='#ffffff',stroke_width=5,stroke_fill='#000',anchor='mm')
    E = ending(W)
    for k,(lab,wi,col) in enumerate(((E['opt_a_text'],E['opt_a'],'#2fd06b'),(E['opt_b_text'],E['opt_b'],'#ff3b30'))):
        sc=pop(t-W[wi]['start'])
        if sc<=0: continue
        fs=56 if len(lab)<=7 else max(36,int(56*7/len(lab)))   # any option word fits its button (v4.2)
        bw=int(max(330,d.textlength(lab,font=_font(D,fs))+70)*sc); bh=int(110*sc); cx=int(Wd*(0.30+0.40*k)); cy=int(Ht*0.80)
        d.rounded_rectangle([cx-bw//2,cy-bh//2,cx+bw//2,cy+bh//2],radius=int(30*sc),fill=col,outline='#000',width=6)
        d.text((cx,cy),lab,font=_font(D,fs*sc),fill='#ffffff',stroke_width=4,stroke_fill='#000',anchor='mm')
