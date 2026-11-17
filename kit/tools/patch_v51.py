"""Kit v5.1 patch (2026-11-18): owner decisions. In-this-town videos have NO like/share/follow ending (Blox City keeps it);
faster narration by default for In-this-town (TEMPO 1.12); viral gate knows the format and the long/short tier.
Backups: <file>.bak_v51."""
import os, shutil, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/RobloxStories")
MARK = "v5.1 (owner 2026-11-18)"


def patch(rel, pairs):
    p = os.path.join(ROOT, rel)
    s = open(p).read()
    if MARK in s:
        print("skip (already v5.1):", rel); return
    shutil.copy2(p, p + ".bak_v51")
    for old, new in pairs:
        assert s.count(old) == 1, (rel, old[:60])
        s = s.replace(old, new)
    open(p, "w").write(s)
    print("patched:", rel)


patch("tools/ep_endcard.py", [
    ('def ending(W):\n    iL = max(i for i, w in enumerate(W) if _n(w["word"]) == "like")\n',
     'def ending(W):\n    # v5.1 (owner 2026-11-18): In-this-town videos have no like/share/follow ending -> no end card (None).\n'
     '    likes = [i for i, w in enumerate(W) if _n(w["word"]) == "like"]\n'
     '    if not likes or not any(_n(w["word"]) == "follow" for w in W[likes[-1]:]):\n        return None\n'
     '    iL = likes[-1]\n'),
    ("def draw(img,t,W,D,icon,Wd=1080,Ht=1920):\n    E = ending(W); tL",
     "def draw(img,t,W,D,icon,Wd=1080,Ht=1920):\n    if ending(W) is None: return img   # v5.1: no end card\n    E = ending(W); tL"),
])

patch("tools/ep_captions.py", [
    ("y=int(Ht*(0.68 if CUR_T[0]>=W[END['like']]['start']-0.05 else 0.65))",
     "y=int(Ht*(0.68 if END and CUR_T[0]>=W[END['like']]['start']-0.05 else 0.65))   # v5.1 (owner 2026-11-18): END may be None"),
])

patch("tools/ep_audio/post.py", [
    ("TEMPO=opt('tempo','RBX_TEMPO',1.08)     # voice speed-up; a change is decided by ear at the voice gate\n",
     "_ST=json.load(open(D+'story.json')) if os.path.exists(D+'story.json') else {}\n"
     "_FMT=str(_ST.get('format','')).lower()\n"
     "# v5.1 (owner 2026-11-18): faster takes for In-this-town like the viral channels (1.12); Blox City keeps 1.08.\n"
     "TEMPO=opt('tempo','RBX_TEMPO',1.12 if ('town' in _FMT or 'world' in _FMT) else 1.08)\n"),
])

patch("tools/ep_viral_check.py", [
    ("    li = [i for i, w in enumerate(W) if re.sub(r'\\W', '', w['word'].lower()) == 'like']\n"
     "    if li:\n"
     "        out = W[-1]['end'] - W[li[-1]]['start']\n"
     "        rep('like/share/follow outro', False, f'{out:.1f} s', 'owner decision (winners use none)', warn=True)\n",
     "    # v5.1 (owner 2026-11-18): In-this-town = no like/share/follow outro; Blox City keeps it.\n"
     "    fmt = str(st.get('format', '')).lower(); town = ('town' in fmt or 'world' in fmt)\n"
     "    li = [i for i, w in enumerate(W) if re.sub(r'\\W', '', w['word'].lower()) == 'like']\n"
     "    out = (W[-1]['end'] - W[li[-1]]['start']) if li else 0.0\n"
     "    if town:\n"
     "        rep('no like/share/follow outro (In this town)', not li, f'{out:.1f} s' if li else 'none', 'none')\n"
     "    elif not fmt:\n"
     "        rep('story.json format', False, 'missing', 'in_this_town / blox_city', warn=True)\n"
     "    tier = str(st.get('tier', 'long')).lower()\n"
     "    lo, hi = (80, 120) if tier == 'long' else (35, 60)\n"
     "    rt = W[-1]['end'] + 0.6\n"
     "    rep(f'runtime ({tier})', lo <= rt <= hi, f'{rt:.0f} s', f'{lo}-{hi} s')\n"),
])
print("done")
