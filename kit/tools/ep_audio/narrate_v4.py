#!/usr/bin/env python3
"""Narration v4 = "delivery v4" (kit v6.1, owner 2026-11-20: "the hook v3 withbed is almost the exact output I am looking
for ... this is how all our future voice outputs will be"). THE default narration for every format:
  in_this_town / in_this_world -> Adam (premade pNInz6obpgDQGcFmaJgB) + the "D" alien FX
  blox_city (storylines)       -> Alex (yl2ZDV1MzN4HbQJbMihG), same delivery, no FX
Recipe (approved sample: ~/RobloxStories_tmp/yawn_curfew/voice_test/YawnCurfew_hook_v3_withbed.mp3, 4.2 w/s):
 1. eleven_v3, stability 0.0 (Creative), similarity 0.75, style 0.35, speaker boost; ONE request per story section
    (blank-line sections of tts_script.txt), each section starting with its emotion tag ([mischievously], [excited],
    [curious], [playful], [deadpan], [urgent], [whispers], [scared]...) + "[speaking quickly]" (added if missing).
 2. Per SENTENCE from the character alignment: trim the edges, cap every silence inside a sentence at 0.12 s, then
    time-stretch the sentence to a speech pace of 4.75 w/s (factor 0.80-1.35; short lines get the SAME pace as long
    ones - the viral narrators never rush them; sound words "Ahh-hh." "Thunk!" "Snap!" keep their natural length).
 3. Sentences joined with 0.06 s gaps (+ the sentence's own edges ~0.1 s = ~0.18 s, the viral gap); at most 3 planned
    beats from audio/beats.json [{"after": "<script word index>", "sec": 0.4}].
 4. Narrator FX (Adam: D alien; Alex: none), HPF 80, +3 dB at 4 kHz, 3:1 comp, loudnorm -14 LUFS / TP -1.5.
 5. Writes audio/voice.wav, audio/words.json (script.txt tokens with times, for shots + captions), audio/narrate_report.json.
    Then run tools/ears_check.py audio/voice.wav --script script.txt.
tts_script.txt rules: the same words as script.txt (numbers may be written as words in the TTS file - "46" in the
captions, "forty-six" here; times "2 a.m." -> "two a.m."), CAPS on the payoff word of key lines, [tags] anywhere, and
{name} lines for character voices (audio/voices.json {"pip": "<voice_id>"} or {"pip": {"id": ..., "fx": ...}}; ids only
from the ElevenLabs voice list with the owner's OK). Cached per section: re-runs only pay for changed sections.

usage: EP=<episode dir> python3 narrate_v4.py [--voice adam_d|alex] [--wps 4.75] [--gap 0.06]"""
import base64, difflib, json, os, re, subprocess, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from el import call

EP = os.environ["EP"].rstrip("/"); A = EP + "/audio/"; os.makedirs(A + "v4_cache", exist_ok=True)
arg = lambda k, d=None: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
ST = json.load(open(EP + "/story.json")) if os.path.exists(EP + "/story.json") else {}
FMT = str(ST.get("format", "in_this_town")).lower()
PRESET = arg("--voice", "alex" if "blox" in FMT else "adam_d")
VOICES_PRESET = {
    "adam_d": {"id": "pNInz6obpgDQGcFmaJgB", "fx": "asetrate=44100*1.1892,aresample=44100,atempo=0.8409,vibrato=f=5.5:d=0.08"},
    "alex": {"id": "yl2ZDV1MzN4HbQJbMihG", "fx": None},
}
NARR = VOICES_PRESET[PRESET]
SETTINGS = {"stability": 0.0, "similarity_boost": 0.75, "style": 0.35, "use_speaker_boost": True}
SPEECH_WPS = float(arg("--wps", 4.75)); GAP = float(arg("--gap", 0.06))
SR = 44100
CHAR = json.load(open(A + "voices.json")) if os.path.exists(A + "voices.json") else {}
SFX_WORD = re.compile(r"^(ahh|ah-|thunk|snap|ding|tink|crack|bang|boom|pop|whoosh|ugh|zzz)", re.I)

# ---------------------------------------------------------------- text helpers
ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()
def n2w(n):
    if n < 20: return ONES[n]
    if n < 100: return TENS[n // 10] + ("" if n % 10 == 0 else "-" + ONES[n % 10])
    if n < 1000: return ONES[n // 100] + " hundred" + ("" if n % 100 == 0 else " " + n2w(n % 100))
    if n < 1000000: return n2w(n // 1000) + " thousand" + ("" if n % 1000 == 0 else " " + n2w(n % 1000))
    return str(n)
def norm(tok):
    """A script token -> list of normalized spoken words (digits expanded)."""
    t = tok.lower().replace(",", "") if re.fullmatch(r"[\d,]+[.!?,]?", tok) else tok.lower()
    m = re.fullmatch(r"(\d+):(\d\d)\W*", t)
    if m: return n2w(int(m.group(1))).split() + ([] if m.group(2) == "00" else n2w(int(m.group(2))).split())
    m = re.fullmatch(r"(\d+)(%)?\W*", t)
    if m: return n2w(int(m.group(1))).replace("-", " ").split() + (["percent"] if m.group(2) else [])
    w = re.sub(r"[^a-z0-9']", "", t) if t.strip() else ""
    parts = [re.sub(r"[^a-z0-9']", "", p) for p in t.replace("-", " ").split()]
    return [p for p in parts if p] or ([w] if w else [])
clean = lambda t: re.sub(r"\s+", " ", re.sub(r"\[[^\]]*\]\s*", "", t)).strip()

def sections():
    secs, cur = [], []
    for l in open(EP + "/tts_script.txt"):
        l = l.rstrip("\n")
        if l.startswith("#"): continue
        if not l.strip():
            if cur: secs.append(cur); cur = []
            continue
        cur.append(l.strip())
    if cur: secs.append(cur)
    out = []   # list of segments (speaker, text)
    for sec in secs:
        segs = []
        for l in sec:
            m = re.match(r"\{(\w+)\}\s*(.*)", l)
            spk, txt = (m.group(1), m.group(2)) if m else ("narrator", l)
            if segs and segs[-1][0] == spk == "narrator": segs[-1] = (spk, segs[-1][1] + " " + txt)
            else: segs.append((spk, txt))
        out.append(segs)
    return out

def with_quick(text):
    """Every narrator section starts with its emotion tag + [speaking quickly] (the approved pace)."""
    if "[speaking quickly]" in text: return text
    m = re.match(r"^((?:\[[^\]]*\]\s*)+)", text)
    return (m.group(1).rstrip() + " [speaking quickly] " + text[m.end():]) if m else "[speaking quickly] " + text

# ---------------------------------------------------------------- audio helpers
def tts(text, voice):
    import hashlib
    key = A + "v4_cache/" + hashlib.md5(json.dumps([voice, text, SETTINGS], sort_keys=True).encode()).hexdigest() + ".json"
    if os.path.exists(key): return json.load(open(key)), 0
    body = {"text": text, "model_id": "eleven_v3", "voice_settings": SETTINGS}
    r = json.loads(call(f"/text-to-speech/{voice}/with-timestamps?output_format=mp3_44100_192", body))
    j = {"mp3": r["audio_base64"], "al": r.get("alignment") or r.get("normalized_alignment")}
    json.dump(j, open(key, "w")); return j, len(text)

def decode(b64, fx=None):
    af = ["-af", fx] if fx else []
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", "pipe:0", *af, "-ac", "1", "-ar", str(SR), "-f", "f32le", "pipe:1"],
                       input=base64.b64decode(b64), capture_output=True, check=True)
    return np.frombuffer(p.stdout, dtype=np.float32).copy()

def words_from_al(al):
    """char alignment -> spoken words [(text, start, end)] with [tags] removed."""
    ch, st, en = al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]
    W, cur, intag = [], None, False
    for c, a, b in zip(ch, st, en):
        if c == "[": intag = True; continue
        if intag:
            if c == "]": intag = False
            continue
        if c.isspace():
            if cur: W.append(cur); cur = None
        elif cur is None: cur = [c, a, b]
        else: cur[0] += c; cur[2] = b
    if cur: W.append(cur)
    return W

def tighten_map(x, t0):
    """Trim edges, cap inner silences at 0.12 s. Returns (audio, fn mapping original seconds (relative to t0) -> new)."""
    hop = int(0.01 * SR); n = len(x) // hop
    if n == 0: return x, lambda t: t
    db = 20 * np.log10(np.array([np.sqrt(np.mean(x[i * hop:(i + 1) * hop] ** 2)) + 1e-9 for i in range(n)]))
    loud = db > (np.percentile(db, 95) - 38)
    idx = np.where(loud)[0]
    if not len(idx): return x, lambda t: t
    a, b = max(0, idx[0] - 1), min(n, idx[-1] + 4)
    keep = np.zeros(n, bool); keep[a:b] = True
    run = 0
    for i in range(a, b):                      # cap silent runs at 12 frames
        if not loud[i]:
            run += 1
            if run > 12: keep[i] = False
        else: run = 0
    kept_before = np.concatenate([[0], np.cumsum(keep)])
    y = np.concatenate([x[i * hop:(i + 1) * hop] for i in range(n) if keep[i]])
    def f(t):
        i = int(np.clip((t - t0) / 0.01, 0, n)); return kept_before[i] * 0.01
    return y, f

def stretch(x, fac):
    if abs(fac - 1) < 0.01: return x
    p = subprocess.run(["ffmpeg", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "pipe:0", "-af", f"atempo={fac:.4f}",
                        "-f", "f32le", "pipe:1"], input=x.astype(np.float32).tobytes(), capture_output=True, check=True)
    return np.frombuffer(p.stdout, dtype=np.float32)

# ---------------------------------------------------------------- build
def main():
    S = sections(); billed = 0
    sent_units = []        # every sentence: audio + words with times relative to its own start
    for si, segs in enumerate(S):
        for spk, text in segs:
            if spk == "narrator":
                voice, fx, txt = NARR["id"], NARR["fx"], with_quick(text)
            else:
                v = CHAR.get(spk)
                if not v: sys.exit(f"no voice for {{{spk}}} in audio/voices.json (pick from the ElevenLabs list with the owner)")
                voice, fx = (v["id"], v.get("fx")) if isinstance(v, dict) else (v, None)
                txt = text
            j, b = tts(txt, voice); billed += b
            y = decode(j["mp3"], fx)
            W = words_from_al(j["al"])
            # split into sentences on . ! ? at word ends
            cur = []
            for w in W:
                cur.append(w)
                if re.search(r'[.!?]["\')]*$', w[0]):
                    sent_units.append((cur, y, spk)); cur = []
            if cur: sent_units.append((cur, y, spk))
    pieces, words_out, t = [], [], 0.0
    beats = json.load(open(A + "beats.json")) if os.path.exists(A + "beats.json") else []
    report = []
    for k, (ws, y, spk) in enumerate(sent_units):
        a, b = max(0.0, ws[0][1] - 0.02), min(len(y) / SR, ws[-1][2] + 0.06)
        seg = y[int(a * SR):int(b * SR)]
        seg, fmap = tighten_map(seg, a)
        n = len(ws); dur = max(0.05, len(seg) / SR); raw = n / dur
        txt = " ".join(w[0] for w in ws)
        if SFX_WORD.match(txt) or spk != "narrator": fac = 1.0
        else: fac = min(max(SPEECH_WPS / raw, 0.80), 1.35)
        seg2 = stretch(seg, fac)
        for w in ws:
            words_out.append({"w": w[0], "start": round(t + fmap(w[1]) / fac, 3), "end": round(t + fmap(w[2]) / fac, 3)})
        pieces.append(seg2); t += len(seg2) / SR
        g = GAP
        pieces.append(np.zeros(int(g * SR), np.float32)); t += g
        report.append({"text": txt[:70], "n": n, "raw_wps": round(raw, 2), "factor": round(fac, 3), "wps": round(n / (len(seg2) / SR), 2), "spk": spk})
    y = np.concatenate(pieces[:-1])
    # map spoken words -> script.txt tokens (digits expanded), so shots + captions keep their word indices
    script = [tok for l in open(EP + "/script.txt") if l.strip() and not l.startswith("#") for tok in l.split()]
    exp = [(i, w) for i, tok in enumerate(script) for w in norm(tok)]
    spoken = [re.sub(r"[^a-z0-9']", "", w["w"].lower().replace("-", "")) for w in words_out]
    sm = difflib.SequenceMatcher(None, [re.sub(r"[^a-z0-9']", "", w.replace("-", "")) for _, w in exp], spoken, autojunk=False)
    tok_t = {}
    for blk in sm.get_matching_blocks():
        for d in range(blk.size):
            ti = exp[blk.a + d][0]; sw = words_out[blk.b + d]
            s0, e0 = tok_t.get(ti, (sw["start"], sw["end"])); tok_t[ti] = (min(s0, sw["start"]), max(e0, sw["end"]))
    missing = [i for i in range(len(script)) if i not in tok_t]
    for i in missing:      # interpolate between neighbours
        prv = max([j for j in tok_t if j < i], default=None); nxt = min([j for j in tok_t if j > i], default=None)
        s0 = tok_t[prv][1] if prv is not None else 0.0; e0 = tok_t[nxt][0] if nxt is not None else s0 + 0.3
        tok_t[i] = (s0, max(s0 + 0.05, e0))
    # planned beats: insert silence after a script word index
    for bt in sorted(beats, key=lambda b: -int(b["after"])):
        i = int(bt["after"]); at = tok_t[i][1] + 0.03; L = float(bt.get("sec", 0.4)) - GAP
        k = int(at * SR); y = np.concatenate([y[:k], np.zeros(int(L * SR), np.float32), y[k:]])
        tok_t = {j: ((s + L, e + L) if s > at else (s, e)) for j, (s, e) in tok_t.items()}
    words_json = [{"word": script[i], "start": round(tok_t[i][0], 3), "end": round(tok_t[i][1], 3)} for i in range(len(script))]
    json.dump(words_json, open(A + "words.json", "w"), indent=0)
    json.dump(words_json, open(A + "words_raw.json", "w"), indent=0)
    chain = "highpass=f=80,equalizer=f=4000:t=o:w=1:g=3,acompressor=threshold=-20dB:ratio=3:attack=5:release=80,loudnorm=I=-14:TP=-1.5"
    # (narrator FX was applied per narrator segment at decode time; characters keep their own voice)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "pipe:0", "-af", chain,
                    "-ar", "48000", A + "voice.wav"], input=y.astype(np.float32).tobytes(), check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", A + "voice.wav", "-b:a", "192k", A + "voice.mp3"], check=True)
    dur = len(y) / SR
    rep = {"preset": PRESET, "voice": NARR["id"], "model": "eleven_v3", "settings": SETTINGS, "speech_wps": SPEECH_WPS,
           "gap": GAP, "chars_billed": billed, "dur_s": round(dur, 2), "script_words": len(script),
           "overall_wps": round(len(script) / dur, 2), "unmatched_script_words": len(missing), "sentences": report}
    json.dump(rep, open(A + "narrate_report.json", "w"), indent=1)
    print(json.dumps({k: v for k, v in rep.items() if k != "sentences"}))

if __name__ == "__main__":
    main()
