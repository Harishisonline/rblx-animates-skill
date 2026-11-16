import os
import json,re,subprocess,numpy as np,wave,os
D=os.environ['EP'].rstrip('/')+'/'
al=json.load(open(D+'audio/alignment_raw.json'))
ch=al['characters'];st=al['character_start_times_seconds'];en=al['character_end_times_seconds']
s=''.join(ch); pre='[fast, urgent, breathless] '
assert s.startswith(pre), s[:40]
k=len(pre)
toks=[];cur=None
for i in range(k,len(ch)):
    c=ch[i]
    if c.isspace():
        if cur: toks.append(cur); cur=None
    else:
        if cur is None: cur=[c,st[i],en[i]]
        else: cur[0]+=c; cur[2]=en[i]
if cur: toks.append(cur)
script=[t for l in open(D+'script.txt') if l.strip() and not l.startswith('#') for t in l.split()]
print(len(toks),len(script))
bad=[(i,a[0],b) for i,(a,b) in enumerate(zip(toks,script)) if re.sub(r'[^a-z]','',a[0].lower().replace('blocks','blox'))!=re.sub(r'[^a-z]','',b.lower())]
print('mismatch',bad[:10])
json.dump([{'word':b,'start':a[1],'end':a[2]} for a,b in zip(toks,script)],open(D+'audio/words_raw.json','w'),indent=0)
gaps=[toks[i+1][1]-toks[i][2] for i in range(len(toks)-1)]
print('first',toks[0][1],'gaps>0.3',sum(g>0.3 for g in gaps),'max',max(gaps),'sum gaps>0.22 excess',sum(g-0.14 for g in gaps if g>0.22))
