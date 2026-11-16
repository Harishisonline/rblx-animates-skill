"""Caption style v3.6 (2026-11-14 defaults = REF_IG_Dfe8B5Hs3G6: size 64 @1080w (~2.4 % cap height), y 0.65, no pop, 1-3 words, one yellow key word)
Caption style v3 (REF1 default): 2-3 words at a time, ALL CAPS heavy sans, centred at ~67 % of frame height (per shot: captions.json / framing fallback, see placements()), white
with a black outline + soft shadow, key word in yellow #FFD21E ONLY on stressed words (emphasis.txt), max ~1 group in 3, never two in a row. Rendered with Pillow as transparent PNG frames
(works on any ffmpeg, no libass). Also draws countdown / timer overlays (big white digits, red outline, top 12-18 %).

    python tools/captions2.py <slug>                  -> videos/<slug>/caps/%04d.png  (one per video frame, 30 fps)
    python tools/captions2.py --demo <outdir> [bg]    -> sample PNGs of every style (no video needed)
finish.py overlays them. Options in config.json -> caption_v2 (all optional):
    {"theme": "ref1" | "brand", "font": "<ttf>", "size": 84, "y": 0.67, "group": 3, "pop": true}
    theme ref1  = white + yellow #FFD21E key word (default; matches the reference)
    theme brand = white + neon purple #B46BFF / neon blue #26D9FF alternating key words (Harish brand look)
Key words: videos/<slug>/emphasis.txt (one word per line) else the longest non-filler word in each group.
Timers: videos/<slug>/timers.json, a list of {"t0": 131.5, "t1": 134.0, "text": "8:31"} or a live countdown
{"t0": 131.5, "t1": 139.0, "from": "8:31", "to": "8:36"} (steps evenly across t0-t1); optional "y" (0.12-0.18).
Safe zone (9:16): text kept inside x 90-990 px (of 1080) and y 62-72 %, clear of the bottom 20 % app UI."""
import json, os, re, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

FILLER = set("a an the and or but so to of in on at it its is was were be been i me my you your he she we they them his her "
             "that this with for as by from if then than just very really are am do did has have had not no".split())
THEMES = {"ref1": ["#FFD21E"], "brand": ["#B46BFF", "#26D9FF"]}
TIMER_RED = "#E0141E"


def cfg():
    try:
        import kit
        return kit.cfg().get("caption_v2", {})
    except Exception:
        return {}


def font_for(size, path=""):
    cands = [path, os.path.join(STUDIO, "assets", "fonts", "Montserrat-Black.ttf"),
             os.path.join(STUDIO, "assets", "fonts", "Poppins-ExtraBold.ttf"),
             "/System/Library/Fonts/Supplemental/Arial Black.ttf", "C:/Windows/Fonts/ariblk.ttf"]
    for p in cands:
        if p and os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def groups_of(words, n=3, max_chars=16):
    """Chunks of 2-3 words that never cross sentence/clause punctuation; a 3rd word is only added while the group
    stays short (max_chars), so long words go 2 at a time like the reference."""
    out, cur = [], []
    for i, w in enumerate(words):
        txt = w["word"].strip()
        if len(cur) >= 2 and len(" ".join(words[j]["word"].strip() for j in cur + [i])) > max_chars:
            out.append(cur); cur = []
        cur.append(i)
        if len(cur) >= n or re.search(r"[.!?,;:\u2026]$", txt.rstrip("\"'\u201d\u2019)]")):
            out.append(cur); cur = []
    if cur:
        out.append(cur)
    return merge_lone(words, out, max_chars + 2)


def _ends(words, g):
    return bool(re.search(r"[.!?,;:\u2026]$", words[g[-1]]["word"].strip().rstrip("\"'\u201d\u2019)]")))


def merge_lone(words, gs, max_chars=18):
    """No orphan one-word groups ('YOU', 'OVER') inside a clause: join the previous group when it fits, else steal its
    last word ([A DIGIT CLICKED][OVER] -> [A DIGIT][CLICKED OVER]). A one-word group that follows punctuation is a
    deliberate beat ('COVERED,' / 'HONESTLY?' / '001.') and stays alone."""
    out = []
    for g in gs:
        if len(g) == 1 and out and not _ends(words, out[-1]):
            prev = out[-1]
            txt = " ".join(words[j]["word"].strip() for j in prev + g)
            if len(prev) <= 2 and len(txt) <= max_chars:
                out[-1] = prev + g; continue
            if len(prev) >= 2:
                out[-1] = prev[:-1]; out.append([prev[-1]] + g); continue
        out.append(g)
    return out


def draw_line(im, parts, colors, cx, cy, font, size):
    """Words centred at (cx, cy): fill colour, black outline ~9 % of size, soft drop shadow."""
    stroke = max(4, int(size * 0.09))
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    shadow = Image.new("RGBA", im.size, (0, 0, 0, 0)); ds = ImageDraw.Draw(shadow)
    space = d.textlength(" ", font=font) + stroke * 1.5
    ws = [d.textlength(p, font=font) for p in parts]
    x = cx - (sum(ws) + space * (len(parts) - 1)) / 2
    for p, w, c in zip(parts, ws, colors):
        ds.text((x + size * 0.04, cy + size * 0.07), p, font=font, fill=(0, 0, 0, 150), anchor="lm",
                stroke_width=stroke, stroke_fill=(0, 0, 0, 150))
        d.text((x, cy), p, font=font, fill=c, anchor="lm", stroke_width=stroke, stroke_fill="#000000")
        x += w + space
    im.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(size * 0.08)))
    im.alpha_composite(layer)


def render_caption(W, H, toks, key, accent, c, yf=None):
    size = int(c.get("size", 64) * W / 1080)
    font = font_for(size, c.get("font", ""))
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    maxw = W * (900 / 1080)
    width = lambda ps, f: sum(d.textlength(p + " ", font=f) for p in ps)
    while width(toks, font) > maxw and size > int(56 * W / 1080):   # shrink a little before wrapping
        size = int(size * 0.93); font = font_for(size, c.get("font", ""))
    lines = [(toks, 0)]
    if width(toks, font) > maxw:
        half = max(1, len(toks) // 2)
        lines = [(toks[:half], 0), (toks[half:], half)]
    y = (yf if yf is not None else min(0.72, max(0.62, float(c.get("y", 0.65))))) * H
    for row, (ps, off) in enumerate(lines):
        cols = [accent if (j + off) == key else "#FFFFFF" for j in range(len(ps))]
        draw_line(im, ps, cols, W / 2, y + (row - (len(lines) - 1) / 2) * size * 1.08, font, size)
    return im


def _clock(s):
    m, sec = s.split(":")
    return int(m) * 60 + int(sec)


def timer_text(tm, t):
    if "text" in tm:
        return tm["text"]
    a, b = _clock(tm["from"]), _clock(tm["to"])
    k = min(1.0, max(0.0, (t - tm["t0"]) / max(0.01, tm["t1"] - tm["t0"])))
    v = int(round(a + (b - a) * k))
    return f"{v // 60}:{v % 60:02d}"


def render_timer(W, H, text, c, y=0.15):
    """Countdown overlay: big white digits, thick red outline + red glow, centred at y (top 12-18 %)."""
    size = int(c.get("timer_size", 190) * W / 1080)
    font = font_for(size, c.get("font", ""))
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).text((W / 2, y * H), text, font=font, fill=(224, 20, 30, 200), anchor="mm",
                              stroke_width=int(size * 0.14), stroke_fill=(224, 20, 30, 200))
    im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(size * 0.12)))
    ImageDraw.Draw(im).text((W / 2, y * H), text, font=font, fill="#FFFFFF", anchor="mm",
                            stroke_width=int(size * 0.07), stroke_fill=TIMER_RED)
    return im


def pick_keys(words, gs, emph, share=1 / 3):
    """Yellow ONLY on the stressed word, at most ~1 group in 3 and never two groups in a row (REF1: emphasis dilutes
    when every group has it). Stressed words come from emphasis.txt (ordered: earlier line = higher priority; a list,
    or a set from older callers). Without emphasis.txt the longest content words are used under the same cap."""
    order = list(emph) if not isinstance(emph, set) else sorted(emph)
    w = lambda i: re.sub(r"[^\w']", "", words[i]["word"]).lower()
    cands = []
    for gi, g in enumerate(gs):
        for k, i in enumerate(g):
            if order and w(i) in order:
                cands.append((order.index(w(i)), -len(w(i)), gi, k))
            elif not order and w(i) not in FILLER and len(w(i)) >= 5:
                cands.append((0, -len(w(i)), gi, k))
    cap = max(1, int(round(len(gs) * share + 0.49)))
    keys = {}
    for _, _, gi, k in sorted(cands):
        if len(keys) >= cap:
            break
        if gi in keys or (gi - 1) in keys or (gi + 1) in keys:
            continue
        keys[gi] = k
    return keys


# ------------------------------------------------------------------ per-shot placement
# framing -> caption centre (fraction of height). REF1 band is 0.62-0.72; when a face/torso/hands fill that band the
# caption moves to the safe top third (0.20, above the head room of MCU/LOW/OTS framings; clear of the top UI ~8 %).
POS = {"top": 0.20, "high": 0.62, "mid": 0.65, "low": 0.70}   # 2026-11-14 ref spec: centre 60-65 %
FRAMING_POS = [(r"\bINSERT|\bMACRO|\bECU\b", "high"), (r"\bAERIAL|\bWIDE|\bEST|\bDRONE|\bTOP.?DOWN", "mid"),
               (r"\bMCU|\bCU\b|\bCLOSE|TWO.?SHOT|\bOTS|\bMS\b|\bMEDIUM|\bLOW\b|\bFULL|\bCOWBOY|\bPOV", "top")]


def framing_pos(desc):
    for rx, p in FRAMING_POS:
        if re.search(rx, desc.upper()):
            return p
    return "mid"


def shot_spans(vdir, words):
    """[(t0, shot_no, desc)] from shots.py @S(n, w0, w1, "desc") (word-index timing) - no Blender needed."""
    p = os.path.join(vdir, "shots.py")
    out = []
    if os.path.exists(p):
        for m in re.finditer(r'@S\(\s*(\d+)\s*,\s*([\d.]+)\s*,\s*([\w.]+)\s*,\s*"([^"]*)"', open(p, encoding="utf-8").read()):
            n, w0, desc = int(m.group(1)), m.group(2), m.group(4)
            i = int(float(w0))
            t0 = 0.0 if i == 0 else (words[min(i, len(words) - 1)]["start"] if "." not in w0 else float(w0))
            out.append((t0, n, desc))
    return sorted(out)


def placements(vdir, words, c):
    """caption y per shot: captions.json {"<shot>": "top"|"high"|"mid"|"low"|0.64, "default": ...} or a list of
    {"t": sec, "pos": ...} / {"shot": n, "pos": ...}; else the framing word in the shot description (fallback)."""
    spans = shot_spans(vdir, words)
    over, tcues = {}, []
    cp = os.path.join(vdir, "captions.json")
    if os.path.exists(cp):
        j = json.load(open(cp, encoding="utf-8"))
        items = j.items() if isinstance(j, dict) else [(str(x.get("shot", "")), x) for x in j]
        for k, v in items:
            if k == "hide":          # v3.5: per-shot / per-word hide rules, see hide_rules()
                continue
            pos = v.get("pos") if isinstance(v, dict) else v
            if isinstance(v, dict) and "t" in v:
                tcues.append((float(v["t"]), pos))
            elif k:
                over[str(k)] = pos
    def at(t):
        pos = over.get("default", c.get("pos"))
        src = "config"
        for t0, n, desc in spans:
            if t0 <= t + 1e-3:
                pos, src = over.get(str(n), framing_pos(desc)), ("captions.json" if str(n) in over else "framing")
        for t0, p in sorted(tcues):
            if t0 <= t + 1e-3:
                pos, src = p, "captions.json t"
        if pos is None:
            pos = "mid"
        y = POS.get(pos, None) if isinstance(pos, str) else float(pos)
        return (y if y is not None else 0.67), src
    return at


def hide_rules(vdir, words):
    """v3.5 (test_seq R5: a '001' caption sat above the watch that already reads 001 - the picture said it, the caption
    doubled it). captions.json "hide": [{"shot": 8, "words": ["001"]}, {"words": ["UM"]}, {"shot": 9}] - a rule with
    words hides those tokens (cleaned, upper case) while that shot is on screen (no shot = everywhere); a rule with only
    a shot hides every caption in it. Returns f(t, tokens) -> tokens to DRAW. Timing/alignment report is unaffected
    (hidden words count as deliberately hidden, listed in caption_report.json 'hidden')."""
    cp = os.path.join(vdir, "captions.json")
    rules = []
    if os.path.exists(cp):
        j = json.load(open(cp, encoding="utf-8"))
        if isinstance(j, dict):
            rules = j.get("hide", []) or []
    spans = shot_spans(vdir, words) if rules else []
    def shot_at(t):
        n = None
        for t0, k, _d in spans:
            if t0 <= t + 1e-3:
                n = k
        return n
    def f(t, toks):
        n = shot_at(t)
        out = list(toks)
        for r in rules:
            if "shot" in r and str(r["shot"]) != str(n):
                continue
            ws = r.get("words")
            if not ws:
                return []
            ws = {re.sub(r"[^\w'$%:]", "", w).upper() for w in ws}
            out = [x for x in out if x not in ws]
        return out
    return f


def events_for(words, emph, c):
    clean = lambda s: re.sub(r"[^\w'$%:]", "", s).upper()
    accents = THEMES.get(c.get("theme", "ref1"), THEMES["ref1"])
    gs = groups_of(words, int(c.get("group", 3)))
    keys = pick_keys(words, gs, emph, float(c.get("key_share", 1 / 3)))
    ev = []
    for gi, g in enumerate(gs):
        toks = [clean(words[i]["word"]) for i in g]
        key = keys.get(gi)
        s = 0.0 if gi == 0 else words[g[0]]["start"]
        e = words[gs[gi + 1][0]]["start"] if gi + 1 < len(gs) else words[g[-1]]["end"] + 0.4
        ev.append((s, e, toks, key, accents[gi % len(accents)]))
    return ev


def frame_size(vdir, c):
    fr = os.path.join(vdir, "frames")
    if os.path.isdir(fr):
        fs = sorted(f for f in os.listdir(fr) if f.endswith(".png"))
        if fs:
            return Image.open(os.path.join(fr, fs[0])).size
    return tuple(c.get("res", (1080, 1920)))


def main(slug):
    vdir = os.path.join(STUDIO, "videos", slug)
    words = json.load(open(os.path.join(vdir, "audio", "words.json"), encoding="utf-8"))
    c = cfg()
    W, H = frame_size(vdir, c)
    emph = set()
    ep = os.path.join(vdir, "emphasis.txt")
    if os.path.exists(ep):
        emph = [re.sub(r"[^\w']", "", l).lower() for l in open(ep, encoding="utf-8") if l.strip()]
    timers = []
    tp = os.path.join(vdir, "timers.json")
    if os.path.exists(tp):
        timers = json.load(open(tp, encoding="utf-8"))
    words = snap_to_voice(vdir, words)
    events = events_for(words, emph, c)
    # the last caption holds to the end of the sound (R2-2: never end on a bare frame after the last word)
    import subprocess
    vd = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                         os.path.join(vdir, "audio", "voice.wav")], capture_output=True, text=True).stdout.strip()
    if events and vd:
        e = events[-1]; events[-1] = (e[0], max(e[1], float(vd) + 0.2), *e[2:])
    events = snap_to_cuts(vdir, words, events)
    at = placements(vdir, words, c)
    ypos = {}
    for e in events:
        ypos[id(e)] = at((e[0] + e[1]) / 2)   # the shot that holds most of the group decides
    print("caption placement:", ", ".join(f"{e[0]:.2f}s {' '.join(e[2])}{'*' if e[3] is not None else ''} y={ypos[id(e)][0]:.2f}({ypos[id(e)][1]})" for e in events))
    hide = hide_rules(vdir, words)
    hidden = []
    for e in events:
        shown = hide((e[0] + e[1]) / 2, e[2])
        if len(shown) != len(e[2]):
            hidden.append(dict(t=round(e[0], 3), words=[x for x in e[2] if x not in shown]))
    if hidden:
        print("caption hide (captions.json):", hidden)
    pop = c.get("pop", False)   # REF_IG_Dfe8B5Hs3G6: hard-cut word groups, no pop
    capdir = os.path.join(vdir, "caps")
    os.makedirs(capdir, exist_ok=True)
    nfr = int(round(max([words[-1]["end"], events[-1][1] if events else 0] + [tm["t1"] for tm in timers]) * 30)) + 12
    blank = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cache, tcache = {}, {}
    for f in range(nfr):
        t = f / 30.0
        layers = []
        # frame-exact: a group is on from the frame NEAREST its first word's start (was the first frame after it: up
        # to 1 frame late) to the frame nearest the next group's start (R2-4: <= 0.5 frame offset by construction)
        ev = next((x for x in events if round(x[0] * 30) <= f < round(x[1] * 30)), None)
        im = None
        if ev is not None:
            k = id(ev)
            toks = hide((ev[0] + ev[1]) / 2, ev[2])
            if k not in cache:
                key_ = ev[3] if (ev[3] is None or (ev[3] < len(ev[2]) and ev[2][ev[3]] in toks)) else None
                if key_ is not None:
                    key_ = toks.index(ev[2][ev[3]])
                cache[k] = render_caption(W, H, toks, key_, ev[4], c, ypos[k][0]) if toks else None
            im = cache[k]
        if ev is not None and im is not None:
            yc = ypos[k][0] * H
            age = f - int(round(ev[0] * 30))
            if pop and age < 3:            # 3-frame 108 % -> 100 % pop on each new group
                s = 1.0 + 0.08 * (3 - age) / 3
                big = im.resize((int(W * s), int(H * s)))
                ox, oy = int((W * s - W) / 2), int(yc * s - yc)
                im = big.crop((ox, oy, ox + W, oy + H))
            layers.append(im)
        for tm in timers:
            if tm["t0"] <= t < tm["t1"]:
                txt = timer_text(tm, t)
                if (txt, tm.get("y", 0.15)) not in tcache:
                    tcache[(txt, tm.get("y", 0.15))] = render_timer(W, H, txt, c, tm.get("y", 0.15))
                layers.append(tcache[(txt, tm.get("y", 0.15))])
        if not layers:
            img = blank
        elif len(layers) == 1:
            img = layers[0]
        else:
            img = layers[0].copy()
            for L in layers[1:]:
                img.alpha_composite(L)
        img.save(os.path.join(capdir, f"{f + 1:04d}.png"), compress_level=1)
    print(f"{nfr} caption frames ({W}x{H}) -> {capdir}")
    rep = alignment_report(vdir, words, events)
    print(f"caption alignment: group onset vs first word max {rep['onset_max_frames']} f, words not on screen while spoken "
          f"{rep['words_not_visible']}, words.json vs voice onsets max {rep['voice_offset_max_frames']} f "
          f"(median {rep['voice_offset_median_frames']} f), {len(rep['snapped'])} group starts snapped to the voice "
          f"-> {rep['verdict']}{' ' + str(rep['off_by_more_than_1_frame']) if rep['off_by_more_than_1_frame'] else ''}  (out/caption_report.json)")


CUT_PRE_F = 6        # a group may not come on in the last 6 frames of a shot: it moves onto the cut (R3-1/R3-3)
FLASH_WHITE_F = 2    # ...and never over the full-white frames of a flash cut (fx.flash_cut): it starts after them


def cut_frames(vdir, words):
    """{frame: kind} of every picture cut (0-based video frame of the first frame of the new shot). Plain cuts from the
    @S spans (same snapped word timing shots.py uses), transition kinds from audio/cues.json (cut: true)."""
    cuts = {round(t0 * 30): "cut" for t0, n, d in shot_spans(vdir, words) if t0 > 0}
    cp = os.path.join(vdir, "audio", "cues.json")
    if os.path.exists(cp):
        for q in json.load(open(cp, encoding="utf-8")):
            if q.get("cut") and q.get("kind"):
                f = round(float(q["t"]) * 30)
                near = [k for k in cuts if abs(k - f) <= 2]   # a transition cue sits on (or 1 f before) its cut frame
                cuts[near[0] if near else f] = q["kind"]
    return cuts


def snap_to_cuts(vdir, words, events):
    """Caption onsets never anticipate a cut: a group that would start within CUT_PRE_F frames before a cut starts ON
    the cut frame instead (shot B's first frame), and after the white frames of a flash; the previous group ends at the
    cut, so no caption straddles the cut or sits on a pure white frame."""
    cuts = cut_frames(vdir, words)
    ev = [list(e) for e in events]
    for k, e in enumerate(ev):
        f = round(e[0] * 30)
        for c, kind in sorted(cuts.items()):
            hold = FLASH_WHITE_F if kind == "flash" else 0
            if c - CUT_PRE_F <= f < c + hold and k > 0:
                nf = c + hold
                if nf >= round(e[1] * 30) - 2:   # too short to survive the move: keep it where it is
                    break
                print(f"caption: '{' '.join(e[2])}' onset frame {f} -> {nf} ({kind} cut at frame {c})")
                e[0] = nf / 30.0
                if ev[k - 1][1] > c / 30.0:
                    ev[k - 1][1] = c / 30.0
                e.append(("cut", c, nf - f))
                break
    return [tuple(e[:5]) + tuple(e[5:]) for e in ev]


def voice_onsets(path, hop=0.005):
    """Onset times (s) of speech in voice.wav: rises of the 5 ms envelope out of a gap (>= 10 dB jump)."""
    import subprocess, numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         stdout=subprocess.PIPE).stdout
    x = np.frombuffer(raw, np.float32); h = int(16000 * hop); n = len(x) // h
    if n < 4:
        return np.zeros(0)
    e = 20 * np.log10(np.sqrt((x[:n * h].reshape(n, h) ** 2).mean(1)) + 1e-9)
    thr = np.percentile(e, 90) - 22
    on = e > thr
    return np.array([i * hop for i in range(1, n) if on[i] and not on[i - 1:i].any() and not on[max(0, i - 6):i].any()])


def snap_to_voice(vdir, words, early=0.15, late=0.05):
    """Captions follow the HEARD voice: a word that starts after a pause (>= 80 ms) and has a speech onset in voice.wav
    up to `early` s before / `late` s after its words.json start is moved onto that onset (test_seq: 'Every' was 3
    frames late in words.json, 'A' 1.2 frames). Returns a corrected copy; words.json itself is not changed."""
    import numpy as np
    vo = voice_onsets(os.path.join(vdir, "audio", "voice.wav"))
    if not len(vo):
        return words
    out = [dict(w) for w in words]
    for i, w in enumerate(out):
        if i and w["start"] - out[i - 1]["end"] < 0.08:
            continue
        d = vo - w["start"]; j = int(np.argmin(np.abs(d)))
        if -early <= d[j] <= late and abs(d[j]) >= 1 / 60 and (i == 0 or vo[j] > out[i - 1]["end"] - 0.02):
            w["start_words_json"] = w["start"]; w["start"] = round(float(vo[j]), 3)
            print(f"caption: '{w['word']}' starts {d[j] * 1000:+.0f} ms off words.json in the voice: snapped")
    return out


def alignment_report(vdir, words, events, fps=30):
    """R2-4: per-word caption timing report -> out/caption_report.json. Measures (1) each group's first on-screen frame
    vs its first word's start, (2) every word on screen during its own spoken time, (3) words.json starts vs the
    speech onsets heard in audio/voice.wav (catches a stale/misaligned words.json). Targets: (1) and (3) <= 1 frame."""
    import numpy as np
    rows = []
    vis = []
    for e in events:
        vis.append((round(e[0] * fps) / fps, round(e[1] * fps) / fps))
    onset = []; idx = 0
    for k, e in enumerate(events):
        n = len(e[2])
        for j in range(n):
            if idx >= len(words):
                break
            w = words[idx]; a, b = vis[k]
            visible = a <= w["start"] + 0.5 / fps and (w["end"] <= b + 0.5 / fps or k == len(events) - 1)
            if not visible and len(e) > 5 and e[5][0] == "cut" and j == 0 and e[5][2] <= CUT_PRE_F + FLASH_WHITE_F:
                visible = True    # held back to the cut on purpose (snap_to_cuts, <= 8 f): reported, not an error
            r = dict(word=w["word"], start=w["start"], end=w["end"], group=k, on=a, off=b, visible=bool(visible))
            if j == 0 and k > 0:
                r["onset_offset_frames"] = round((a - w["start"]) * fps, 2)
                if len(e) > 5 and e[5][0] == "cut":   # moved onto a cut on purpose (snap_to_cuts): reported, not an error
                    r["snapped_to_cut_frame"] = e[5][1]
                else:
                    onset.append(abs(r["onset_offset_frames"]))
            rows.append(r); idx += 1
    vo = voice_onsets(os.path.join(vdir, "audio", "voice.wav"))
    offs = []
    if len(vo):
        for r in rows:   # word starts that follow a pause must sit on a heard speech onset
            if r is rows[0] or r["start"] - rows[rows.index(r) - 1]["end"] >= 0.08:
                d = vo - r["start"]; i = int(np.argmin(np.abs(d)))
                if abs(d[i]) < 0.25:
                    r["voice_onset_offset_frames"] = round(float(d[i]) * fps, 2); offs.append(abs(float(d[i]) * fps))
    nv = [r["word"] for r in rows if not r["visible"]]
    late = [(r["word"], r["voice_onset_offset_frames"]) for r in rows if abs(r.get("voice_onset_offset_frames", 0)) > 1]
    rep = dict(fps=fps, words=len(rows), groups=len(events),
               onset_max_frames=round(max(onset), 2) if onset else 0.0,
               words_not_visible=nv,
               voice_offset_max_frames=round(max(offs), 2) if offs else None,
               voice_offset_median_frames=round(float(np.median(offs)), 2) if offs else None,
               voice_checked=len(offs), off_by_more_than_1_frame=late,
               snapped=[(r["word"], r.get("start")) for r in rows if "start_words_json" in words[rows.index(r)]] if len(words) == len(rows) else [],
               rows=rows)
    ok = rep["onset_max_frames"] <= 1 and not nv and not late
    rep["verdict"] = "OK" if ok else "CHECK"
    os.makedirs(os.path.join(vdir, "out"), exist_ok=True)
    json.dump(rep, open(os.path.join(vdir, "out", "caption_report.json"), "w"), indent=1)
    return rep


def demo(outdir, bg=None):
    """Sample frames of each theme (+ a timer) over a background image (or grey)."""
    os.makedirs(outdir, exist_ok=True)
    W, H = 1080, 1920
    base = Image.open(bg).convert("RGBA").resize((W, H)) if bg else Image.new("RGBA", (W, H), (90, 110, 130, 255))
    words = [dict(word=w, start=i * 0.3, end=i * 0.3 + 0.28) for i, w in
             enumerate("In this world, everyone swaps bodies with the person they'll marry.".split())]
    for theme in ("ref1", "brand"):
        c = dict(cfg(), theme=theme)
        for j, e in enumerate(events_for(words, {"swaps", "marry"}, c)[:4]):
            im = base.copy(); im.alpha_composite(render_caption(W, H, e[2], e[3], e[4], c))
            if j == 3:
                im.alpha_composite(render_timer(W, H, "8:42", c))
            im.convert("RGB").save(os.path.join(outdir, f"cap_{theme}_{j}.png"))
    print("demo ->", outdir)


if __name__ == "__main__":
    if sys.argv[1] == "--demo":
        demo(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    else:
        main(sys.argv[1])
