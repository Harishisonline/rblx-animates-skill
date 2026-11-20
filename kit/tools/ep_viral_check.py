#!/usr/bin/env python3
"""ep_viral_check.py <episode dir>  - kit v5 (DRIPDYL guide section 10), 2026-11-17.

Static pre-render gate: reads shots*.py, audio/words.json, audio/pauses.json, tts_script.txt and story.json (no Blender,
no rendering). Prints PASS / FAIL / WARN per check and exits 1 if any FAIL. Run after the low-res pass, before look-dev.
Optional in story.json: "hook_word": "<word>" (+ "hook_nth": n) = the twist word that must land by 2.5 s.
Numbers are targets from the guide (Gemini + our measurements), not proven on our channel yet; tune them with results."""
import ast, json, os, re, sys, glob

EP = sys.argv[1].rstrip('/') if len(sys.argv) > 1 else os.environ['EP'].rstrip('/')
A = EP + '/audio/'
DYN = {'crash_zoom', 'whip_pan', 'whip', 'dutch', 'dutch_push', 'impact_shake', 'run_follow', 'hero_low', 'ground_low',
       'dolly_zoom', 'pull_reveal', 'track_side', 'overhead', 'crane', 'truck', 'handheld_follow', 'aerial_glide',
       'aerial_dive', 'push_in', 'ecu', 'mcu', 'close_up', 'insert', 'prop_macro', 'ots'}
ACT = {'strike', 'shock', 'gasp', 'recoil', 'laugh', 'cry', 'stomp', 'shrug', 'nod', 'shake', 'point', 'grab', 'turn',
       'dread_turn', 'look_at', 'walk', 'run', 'run_away', 'skid_stop', 'sit', 'stand', 'stumble', 'fall', 'embrace',
       'emote', 'talk_cadence', 'kneel_down', 'belly_laugh', 'crowd_laugh', 'read', 'hold_phone', 'hold', 'drop',
       'carry', 'react_pop'}
res = []


def rep(name, ok, val, target, warn=False):
    res.append(('PASS' if ok else ('WARN' if warn else 'FAIL'), name, val, target))


def calls(node):
    out = []
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            f = n.func
            nm = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else None)
            if nm:
                out.append((nm, n))
    return out


# ---- shots
shots = []
for p in sorted(glob.glob(EP + '/shots*.py')):
    try:
        tree = ast.parse(open(p).read())
    except SyntaxError as e:
        rep('shots parse ' + os.path.basename(p), False, str(e), 'valid python'); continue
    for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        dec = [d for d in fn.decorator_list if isinstance(d, ast.Call) and getattr(d.func, 'id', '') == 'S']
        if not dec:
            continue
        sid = dec[0].args[0].value if dec[0].args and isinstance(dec[0].args[0], ast.Constant) else None
        shots.append((sid, calls(fn)))
shots.sort(key=lambda s: (s[0] is None, s[0]))
W = json.load(open(A + 'words.json')) if os.path.exists(A + 'words.json') else []
dur = (W[-1]['end'] - W[0]['start']) if W else None
if shots:
    n = len(shots)
    idle_only = sum(1 for _, c in shots if any(k == 'idle' for k, _ in c) and not any(k in ACT for k, _ in c))
    rep('idle-only shots', idle_only / n <= 0.15, f'{idle_only}/{n} ({idle_only / n:.0%})', '<= 15 %')
    acts = sum(1 for _, c in shots for k, _ in c if k in ACT)
    if dur:
        rep('keyed actions per second', acts / dur >= 1.5, f'{acts / dur:.2f} ({acts} calls / {dur:.0f} s)', '>= 1.5')
    yaw0 = 0; fo = 0
    for _, c in shots:
        for k, node in c:
            if k == 'frame_on':
                fo += 1
                for kw in node.keywords:
                    if kw.arg == 'yaw' and isinstance(kw.value, ast.Constant) and kw.value.value in (0, 0.0):
                        yaw0 += 1
    rep('straight-on frame_on (yaw=0)', yaw0 / n <= 0.2, f'{yaw0}/{n}', '<= 20 % of shots')
    dyn = sum(1 for _, c in shots if any(k in DYN for k, _ in c))
    rep('shots with a recipe camera (not plain frame_on)', dyn / n >= 0.35, f'{dyn}/{n} ({dyn / n:.0%})', '>= 35 %')
    first = shots[0][1]
    hook_dyn = any(k in {'crash_zoom', 'run_follow', 'whip_pan', 'whip', 'impact_shake', 'dutch', 'dolly_zoom'} for k, _ in first)
    rep('hook shot uses a big camera move', hook_dyn, ','.join(sorted({k for k, _ in first if k in DYN})) or 'none',
        'crash_zoom / run_follow / whip / impact_shake / dutch')
    blur0 = [node for k, node in first if k == 'motion_blur' and node.args and isinstance(node.args[0], ast.Constant)
             and node.args[0].value > 0]
    rep('frame 0 motion blur', not blur0, 'on' if blur0 else 'off', 'off')
else:
    rep('shots found', False, 0, 'shots*.py with @S blocks')

# ---- voice
if W:
    rep('first word start', W[0]['start'] <= 0.05, f"{W[0]['start']:.2f} s", '<= 0.05 s')
    wps = len(W) / dur
    _st6 = json.load(open(EP + '/story.json')) if os.path.exists(EP + '/story.json') else {}
    _f6 = str(_st6.get('format', '')).lower(); V6 = ('town' in _f6 or 'world' in _f6) or os.path.exists(EP + '/audio/narrate_report.json')
    if V6:   # kit v6.0 (2026-11-19): EARS viral range, docs/VIRAL_V6.md section 2
        rep('words per second (v6)', 4.05 <= wps <= 4.65, f'{wps:.2f}', '4.05-4.65')
    else:
        rep('words per second', 3.7 <= wps <= 4.3, f'{wps:.2f}', '3.7-4.3')
    P = {int(k) for k in json.load(open(A + 'pauses.json'))} if os.path.exists(A + 'pauses.json') else set()
    gaps = [(W[i + 1]['start'] - W[i]['end'], i) for i in range(len(W) - 1)]
    # v5.2 (2026-11-18): eleven_v3 word ends come early, so alignment gaps overstate silence (INTOWN_01: 0.51 s by
    # alignment, 0.23 s in the audio). Judge silence on audio/voice.wav (ffmpeg silencedetect -40 dB); alignment = info.
    wav = A + 'voice.wav'
    sil = None
    if os.path.exists(wav):
        import subprocess
        r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', wav, '-af', 'silencedetect=noise=-40dB:d=0.12',
                            '-f', 'null', '-'], capture_output=True, text=True)
        sil = [float(l.split('silence_duration:')[1]) for l in r.stderr.splitlines() if 'silence_duration:' in l]
    mg_al = max((g for g, i in gaps if i not in P), default=0)
    mp = [g for g, i in gaps if i in P]
    if sil is not None:
        ms = max(sil, default=0.0)
        if V6:   # flow edit: ~0.18 s gaps, at most 3 deliberate beats of 0.3-0.5 s
            rep('longest silence (voice.wav, -40 dB, v6)', ms <= 0.55, f'{ms:.2f} s', '<= 0.55 s')
            n3 = sum(1 for g in sil if g > 0.3); per = n3 / max(1.0, W[-1]['end']) * 60
            rep('silences > 0.3 s per minute (v6)', per <= 3.5, f'{per:.1f} ({n3})', '<= 3.5 (viral 1.9-3.1)')
            rep('meme pauses (v6 flow: SFX under the voice)', len(P) == 0, f'{len(P)}', '0')
        else:
            rep('longest silence (voice.wav, -40 dB)', ms <= 0.35, f'{ms:.2f} s ({len(sil)} gaps >= 0.12 s)', '<= 0.35 s')
            rep('meme pauses', len(P) <= 8, f'{len(P)} (alignment max {max(mp, default=0):.2f} s, info)', '<= 8')
    else:
        rep('longest silence (alignment; no voice.wav)', mg_al <= 0.30, f'{mg_al:.2f} s', '<= 0.30 s')
        rep('meme pauses', len(mp) <= 8 and all(g <= 0.35 for g in mp), f'{len(mp)} x max {max(mp, default=0):.2f} s',
            '<= 8, each <= 0.35 s')
    st = json.load(open(EP + '/story.json')) if os.path.exists(EP + '/story.json') else {}
    hw = st.get('hook_word')
    if hw:
        hits = [w for w in W if re.sub(r'\W', '', w['word'].lower()) == re.sub(r'\W', '', hw.lower())]
        k = st.get('hook_nth', 1)
        if len(hits) >= k:
            t = hits[k - 1]['start']
            rep('hook/twist word time', t <= 2.5, f'"{hw}" at {t:.2f} s', '<= 2.5 s')
    else:
        rep('hook/twist word time', False, 'story.json has no "hook_word"', 'set it', warn=True)
    # v5.1 (owner 2026-11-18): In-this-town = no like/share/follow outro; Blox City keeps it.
    fmt = str(st.get('format', '')).lower(); town = ('town' in fmt or 'world' in fmt)
    _n = [re.sub(r'\W', '', w['word'].lower()) for w in W]      # a CTA = "like" with "share"/"follow" within 5 words
    li = [i for i, w in enumerate(_n) if w == 'like' and any(x in ('share', 'follow') for x in _n[i + 1:i + 6])]
    out = (W[-1]['end'] - W[li[-1]]['start']) if li else 0.0
    if town:
        rep('no like/share/follow outro (In this town)', not li, f'{out:.1f} s' if li else 'none', 'none')
    elif not fmt:
        rep('story.json format', False, 'missing', 'in_this_town / blox_city', warn=True)
    tier = str(st.get('tier', 'short')).lower()      # owner 2026-11-18: Shorts are 80-120 s; 'long' = ~20 min compilation
    lo, hi = {'full': (100, 165), 'lite': (60, 78), 'short': (80, 120)}.get(tier, (1080, 1500))   # v6.0: full / lite tiers
    rt = W[-1]['end'] + 0.6
    rep(f'runtime ({tier})', lo <= rt <= hi, f'{rt:.0f} s', f'{lo}-{hi} s')
else:
    rep('words.json', False, 'missing', 'run tts.py, words.py, post.py')

# ---- narration tags
T = EP + '/tts_script.txt'
if os.path.exists(T):
    L = [l.strip() for l in open(T) if l.strip() and not l.startswith('#')]
    tagged = sum(1 for l in L if l.startswith('['))
    NR = EP + '/audio/narrate_report.json'
    route = json.load(open(NR)).get('route') if os.path.exists(NR) else None
    if route in ('v2', 'sts'):   # v6: v2 would read tags aloud; sts takes the owner's delivery
        rep('tts tags (narrate_v3 route ' + route + ')', True, 'not used by this route', 'n/a')
    elif route == 'v3':
        secs = [b for b in open(T).read().split('\n\n') if b.strip() and not b.strip().startswith('#')]
        ts = sum(1 for b in secs if b.strip().startswith('['))
        rep('sections with an emotion tag (v3 route)', ts == len(secs), f'{ts}/{len(secs)}', 'every section')
    else:
        rep('tts lines with an emotion tag', tagged == len(L), f'{tagged}/{len(L)}', 'every line')

w = max(len(r[1]) for r in res)
for s, nm, v, t in res:
    print(f'{s:4}  {nm:<{w}}  {v}   (target {t})')
fails = sum(1 for r in res if r[0] == 'FAIL')
print(f'\n{fails} FAIL, {sum(1 for r in res if r[0] == "WARN")} WARN, {sum(1 for r in res if r[0] == "PASS")} PASS')
sys.exit(1 if fails else 0)
