#!/usr/bin/env python3
"""HOUSE NARRATION "v3" (kit v6.1, owner 2026-11-20: "This is what I want ... produce this exact voice each and every time
for all of my videos"). Reference takes the owner approved by ear:
  ~/RobloxStories_tmp/yawn_curfew/voice_test/YawnCurfew_hook_v3_withbed.mp3   (the hook sample)
  ~/RobloxStories_tmp/yawn_curfew/voice_test/YawnCurfew_FULL_v3_withbed.mp3   (the entire script, 109 s)
This tool reproduces that exact method (it is the generalised voice_test/full_v3.py):
  * voice: In-this-town = Adam pNInz6obpgDQGcFmaJgB + the D alien FX; Blox City = Alex yl2ZDV1MzN4HbQJbMihG, no FX
    (preset from story.json "format", or --voice adam_d|alex)
  * model eleven_v3, stability 0.0 (Creative), similarity 0.75, style 0.35, speaker boost; ONE request per section
    (blank-line sections of tts_script.txt; write each section exactly as it should be performed:
    "[emotion] [speaking quickly] text" - EXCEPT sections with a written sound word / [yawns] / [laughs] / [whispers],
    which get NO [speaking quickly]; that is how the approved yawns were made). The tool does not add tags.
  * per sentence (from the character alignment): cut, trim the edges and cap silences inside the sentence at 0.12 s
    (ffmpeg silenceremove -42 dB), then time-stretch to a 4.75 w/s speech pace (factor 0.80-1.35; short lines the same
    pace as long ones; sentences starting with a sound word - Ahh / Thunk / Snap / Ding - keep their natural length)
  * sentences joined with 0.06 s of silence (the approved takes have NO extra beats; audio/beats.json [{"after":
    <script word index>, "sec": 0.4}] - at most 3 - only when the owner asks for a pause)
  * THEN the narrator FX on the whole take, HPF 80, +3 dB at 4 kHz, 3:1 compression, loudnorm -14 LUFS / TP -1.5
  * {name} lines = character voices (audio/voices.json {"pip": "<voice_id>"} or {"pip": {"id": ..., "fx": ...}}; ids only
    from the ElevenLabs voice list with the owner's OK) - they are generated alone and never get the narrator FX.
Outputs: audio/voice.wav (48 kHz), voice.mp3, words.json (+ words_raw.json) keyed to script.txt tokens (faster-whisper on
the final take, matched with difflib; digits in captions match number words), narrate_report.json. Cached per section
(md5 of voice+text+settings in audio/v3_cache): re-runs only pay for changed sections and rebuild the identical take.
Gate after it: tools/ears_check.py audio/voice.wav --script script.txt. No voice samples (owner 2026-11-20).

usage: EP=<episode> python3 narrate_house.py [--voice adam_d|alex] [--words-only]"""
import base64, difflib, hashlib, json, os, re, subprocess, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from el import call

EP = os.environ["EP"].rstrip("/"); A = EP + "/audio/"; C = A + "v3_cache/"; os.makedirs(C, exist_ok=True)
arg = lambda k, d=None: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
ST = json.load(open(EP + "/story.json")) if os.path.exists(EP + "/story.json") else {}
PRESETS = {"adam_d": ("pNInz6obpgDQGcFmaJgB", "asetrate=44100*1.1892,aresample=44100,atempo=0.8409,vibrato=f=5.5:d=0.08"),
           "alex": ("yl2ZDV1MzN4HbQJbMihG", None)}
PRESET = arg("--voice", "alex" if "blox" in str(ST.get("format", "")).lower() else "adam_d")
VOICE, FX = PRESETS[PRESET]
SET = {"model_id": "eleven_v3", "voice_settings": {"stability": 0.0, "similarity_boost": 0.75, "style": 0.35, "use_speaker_boost": True}}
SR = 44100; TARGET = 4.75; GAP = 0.06
SFX_WORDS = re.compile(r"^(ahh|thunk|snap|ding)", re.I)
CHAR = json.load(open(A + "voices.json")) if os.path.exists(A + "voices.json") else {}

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
    out = []
    for sec in secs:        # a section = narrator text (lines joined) or a {name} line on its own
        for l in sec:
            m = re.match(r"\{(\w+)\}\s*(.*)", l)
            spk, txt = (m.group(1), m.group(2)) if m else ("narrator", l)
            out.append([spk, txt])
        out.append(None)     # section boundary marker
    merged, buf = [], None    # merge consecutive narrator lines of one section into one request
    for it in out:
        if it is None:
            if buf: merged.append(buf); buf = None
            continue
        if it[0] == "narrator" and buf and buf[0] == "narrator": buf[1] += " " + it[1]
        else:
            if buf: merged.append(buf)
            buf = list(it)
    if buf: merged.append(buf)
    return merged

def tts(text, voice):
    key = C + hashlib.md5(json.dumps([voice, text, SET], sort_keys=True).encode()).hexdigest() + ".json"
    if os.path.exists(key): return json.load(open(key)), 0
    r = json.loads(call(f"/text-to-speech/{voice}/with-timestamps?output_format=mp3_44100_192", dict(SET, text=text)))
    j = {"mp3": r["audio_base64"], "al": r.get("alignment") or r.get("normalized_alignment")}
    json.dump(j, open(key, "w")); return j, len(text)

def run_ff(x, af):
    p = subprocess.run(["ffmpeg", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "pipe:0", "-af", af,
                        "-f", "f32le", "pipe:1"], input=x.astype(np.float32).tobytes(), capture_output=True, check=True)
    return np.frombuffer(p.stdout, dtype=np.float32)

def decode(b64, fx=None):
    af = ["-af", fx] if fx else []
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", "pipe:0", *af, "-ac", "1", "-ar", str(SR), "-f", "f32le", "pipe:1"],
                       input=base64.b64decode(b64), capture_output=True, check=True)
    return np.frombuffer(p.stdout, dtype=np.float32)

def sentences(al):
    ch, st, en = al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]
    out, buf, s0, intag, last = [], "", None, False, 0.0
    for c, a, b in zip(ch, st, en):
        if c == "[": intag = True; continue
        if intag:
            if c == "]": intag = False
            continue
        if s0 is None and c.strip(): s0 = a
        buf += c; last = b
        if c in ".!?" and buf.strip():
            out.append((buf.strip(), s0, last)); buf, s0 = "", None
    if buf.strip(): out.append((buf.strip(), s0 if s0 is not None else 0.0, last))
    return out

TIGHT = ("silenceremove=start_periods=1:start_threshold=-42dB:start_silence=0.01,areverse,"
         "silenceremove=start_periods=1:start_threshold=-42dB:start_silence=0.03,areverse,"
         "silenceremove=stop_periods=-1:stop_duration=0.12:stop_threshold=-42dB")

def build():
    billed = 0; pieces = []
    for spk, text in sections():
        if spk == "narrator": voice, cfx = VOICE, None
        else:
            v = CHAR.get(spk)
            if not v: sys.exit(f"no voice for {{{spk}}} in audio/voices.json (pick from the ElevenLabs list with the owner)")
            voice, cfx = (v["id"], v.get("fx")) if isinstance(v, dict) else (v, None)
        j, b = tts(text, voice); billed += b
        y = decode(j["mp3"], cfx)
        for stext, a, e in sentences(j["al"]):
            n = len(re.findall(r"[A-Za-z0-9']+", stext))
            seg = y[int(max(0, a - 0.02) * SR): int(min(len(y) / SR, e + 0.06) * SR)]
            seg0 = seg; seg = run_ff(seg, TIGHT)
            if len(seg) < int(0.15 * SR): seg = seg0          # tighten ate a quiet sound word: keep it as generated
            if len(seg) < int(0.05 * SR): continue
            pieces.append({"text": stext, "n": n, "dur": len(seg) / SR, "x": seg, "spk": spk})
    out, report = [], []
    for p in pieces:
        raw = p["n"] / p["dur"] if p["n"] else TARGET
        if SFX_WORDS.match(p["text"]) or p["spk"] != "narrator": f = 1.0
        else: f = min(max(TARGET / raw, 0.80), 1.35)
        x = p["x"] if abs(f - 1) < 0.01 else run_ff(p["x"], f"atempo={f:.4f}")
        out.append(x); out.append(np.zeros(int(GAP * SR), np.float32))
        report.append({"text": p["text"][:70], "n": p["n"], "raw_wps": round(raw, 2), "factor": round(f, 3), "spk": p["spk"]})
    y = np.concatenate(out[:-1])
    chain = (FX + "," if FX else "") + "highpass=f=80,equalizer=f=4000:t=o:w=1:g=3,acompressor=threshold=-20dB:ratio=3:attack=5:release=80,loudnorm=I=-14:TP=-1.5"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "pipe:0", "-af", chain,
                    "-ar", "48000", A + "voice.wav"], input=y.astype(np.float32).tobytes(), check=True)
    return billed, report

# ---------------------------------------------------------------- words.json from the final take
ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()
def n2w(n):
    if n < 20: return ONES[n]
    if n < 100: return TENS[n // 10] + ("" if n % 10 == 0 else " " + ONES[n % 10])
    if n < 1000: return ONES[n // 100] + " hundred" + ("" if n % 100 == 0 else " " + n2w(n % 100))
    if n < 1000000: return n2w(n // 1000) + " thousand" + ("" if n % 1000 == 0 else " " + n2w(n % 1000))
    return str(n)
def norm(tok):
    t = tok.lower()
    m = re.fullmatch(r"\W*(\d+):(\d\d)\W*", t)
    if m: return n2w(int(m.group(1))).split() + ([] if m.group(2) == "00" else n2w(int(m.group(2))).split())
    m = re.fullmatch(r"\W*([\d,]+)(%)?\W*", t)
    if m and m.group(1).replace(",", "").isdigit(): return n2w(int(m.group(1).replace(",", ""))).split() + (["percent"] if m.group(2) else [])
    parts = [re.sub(r"[^a-z0-9']", "", p) for p in t.replace("-", " ").split()]
    return [p for p in parts if p]

def words_json():
    from faster_whisper import WhisperModel
    segs, _ = WhisperModel("small", device="cpu", compute_type="int8").transcribe(A + "voice.wav", language="en", word_timestamps=True, beam_size=5)
    W = [{"w": w.word.strip(), "s": w.start, "e": w.end} for s in segs for w in s.words if w.word.strip()]
    heard = []
    for w in W:
        for k in norm(w["w"]) or [""]:
            heard.append((k, w))
    script = [tok for l in open(EP + "/script.txt") if l.strip() and not l.startswith("#") for tok in l.split()]
    exp = [(i, k) for i, tok in enumerate(script) for k in (norm(tok) or [""])]
    sm = difflib.SequenceMatcher(None, [k for _, k in exp], [k for k, _ in heard], autojunk=False)
    tt = {}
    for blk in sm.get_matching_blocks():
        for d in range(blk.size):
            i = exp[blk.a + d][0]; w = heard[blk.b + d][1]
            s0, e0 = tt.get(i, (w["s"], w["e"])); tt[i] = (min(s0, w["s"]), max(e0, w["e"]))
    for i in range(len(script)):     # words whisper did not hear (sound words): between neighbours
        if i not in tt:
            p = max([j for j in tt if j < i], default=None); q = min([j for j in tt if j > i], default=None)
            s0 = tt[p][1] if p is not None else 0.0; e0 = tt[q][0] if q is not None else s0 + 0.4
            tt[i] = (s0, max(s0 + 0.05, e0))
    words = [{"word": script[i], "start": round(tt[i][0], 3), "end": round(tt[i][1], 3)} for i in range(len(script))]
    json.dump(words, open(A + "words.json", "w"), indent=0); json.dump(words, open(A + "words_raw.json", "w"), indent=0)
    return len(script)

def beats():
    """Insert planned beats (silence) after script word indices, using words.json, then shift the later words."""
    bp = A + "beats.json"
    if not os.path.exists(bp): return 0
    B = json.load(open(bp))[:3]
    if not B: return 0
    import soundfile as sf
    y, sr = sf.read(A + "voice.wav"); words = json.load(open(A + "words.json"))
    for b in sorted(B, key=lambda b: -int(b["after"])):
        i = int(b["after"]); at = words[i]["end"] + 0.02; L = max(0.0, float(b.get("sec", 0.4)) - GAP)
        k = int(at * sr); y = np.concatenate([y[:k], np.zeros(int(L * sr)), y[k:]])
        for w in words:
            if w["start"] > at: w["start"] = round(w["start"] + L, 3); w["end"] = round(w["end"] + L, 3)
    sf.write(A + "voice.wav", y, sr); json.dump(words, open(A + "words.json", "w"), indent=0)
    return len(B)

if __name__ == "__main__":
    billed, report = (0, []) if "--words-only" in sys.argv else build()
    words_json(); nb = beats()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", A + "voice.wav", "-b:a", "192k", A + "voice.mp3"], check=True)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", A + "voice.wav"],
                               capture_output=True, text=True).stdout)
    nw = len(json.load(open(A + "words.json")))
    rep = {"method": "house v3 (= voice_test/full_v3.py)", "preset": PRESET, "voice": VOICE, "settings": SET,
           "chars_billed": billed, "beats": nb, "dur_s": round(dur, 2), "script_words": nw, "overall_wps": round(nw / dur, 2),
           "sentences": report}
    json.dump(rep, open(A + "narrate_report.json", "w"), indent=1)
    print(json.dumps({k: v for k, v in rep.items() if k != "sentences"}))
