#!/usr/bin/env python3
"""Narration v3 generator (kit v6.0, 2026-11-19). Replaces tts.py for In-this-town (and, owner 2026-11-19, every format):
the narrator is ElevenLabs premade Adam pNInz6obpgDQGcFmaJgB + the "D" alien FX the owner picked by ear; quoted lines
can be spoken by character voices. Output is drop-in for words.py -> post.py (mode "flow") -> ears_check.py.

WHY (EARS, research/ears, 4 viral Shorts 16-34M views vs ours): viral narration runs 4.1-4.4 words/s with ~0.18 s after a
full stop and a pitch range of 12-17 semitones. Adam alone moves 8-10 st (the "robotic" sound) and speeding a take past
1.35x flattens it further. So: generate per story SECTION (the model keeps intonation across a whole paragraph but resets
energy per act), get the speed from the model, not from atempo, and measure every take.

ROUTES (audio/narrate_cfg.json {"route": ...} or RBX_ROUTE; the owner picks one by ear at the voice gate):
  v2   eleven_multilingual_v2, stability 0.30 / similarity 0.75 / style 0.45 / speaker boost / speed 1.2, one request per
       section with previous_text/next_text for continuity. [tags] are removed (v2 would read them aloud).
  v3   eleven_v3 "Creative" (stability 0.0) / similarity 0.75 / style 0.35, one request per section, [tags] kept
       ([excited], [whispers], [deadpan], [urgent], [laughs]...). No speed parameter on v3: post tempo <= 1.35.
  sts  Speech-to-Speech: audio/performance.wav (the owner reading the script with energy, ~4.3 words/s, on a phone) is
       converted into Adam's voice; the owner's timing and melody are kept. Model eleven_multilingual_sts_v2. Word timing
       from ElevenLabs forced alignment (fallback: faster-whisper). Never use a performance taken from someone else's video.

tts_script.txt v3 syntax (one SECTION = lines up to a blank line; '#' lines are comments):
  [excited] In this town, your laugh charges your battery. You see, every laugh is two percent. Ding!
  Me? I'm twelve, and I'm at three percent.
  {grandma} "Nico, sweetie, tell me a joke."
  ...blank line = next section
A {name} line is spoken by the voice in audio/voices.json {"grandma": "<voice_id>"} or {"ghost": {"id": "<voice_id>",
"fx": "<ffmpeg filter>"}} - ids ONLY from the ElevenLabs voice
list or the owner (never invented); the alien FX applies to the narrator only.

usage: EP=<episode dir> python3 narrate_v3.py [--route v2|v3|sts] [--only 0,1] [--target-wps 4.35]
writes audio/raw.wav, raw.mp3, alignment.json, alignment_raw.json, narrate_report.json and (if absent) post_cfg.json
{"mode": "flow", "tempo": t} with t = target / estimated post-edit pace, clamped to 0.9-1.35."""
import base64, json, os, re, subprocess, sys, uuid, urllib.request
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from el import call, KEY

EP = os.environ["EP"].rstrip("/"); A = EP + "/audio/"; os.makedirs(A + "narr_cache", exist_ok=True)
CFG = json.load(open(A + "narrate_cfg.json")) if os.path.exists(A + "narrate_cfg.json") else {}
arg = lambda k, d=None: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
ROUTE = arg("--route", os.environ.get("RBX_ROUTE", CFG.get("route", "v2")))
VOICE = CFG.get("voice", os.environ.get("RBX_VOICE", "pNInz6obpgDQGcFmaJgB"))      # Adam - Dominant, Firm (premade)
FX = CFG.get("fx", "alien")                                                       # owner pick "D" 2026-11-19
TARGET = float(arg("--target-wps", CFG.get("target_wps", 4.35)))
ONLY = [int(v) for v in (arg("--only", "") or "").split(",") if v.strip()]
SR = 44100
SET = {"v2": {"model": "eleven_multilingual_v2", "vs": {"stability": 0.30, "similarity_boost": 0.75, "style": 0.45, "use_speaker_boost": True, "speed": 1.2}},
       "v3": {"model": "eleven_v3", "vs": {"stability": 0.0, "similarity_boost": 0.75, "style": 0.35, "use_speaker_boost": True}},
       "sts": {"model": "eleven_multilingual_sts_v2", "vs": {"stability": 0.5, "similarity_boost": 0.8, "style": 0.0, "use_speaker_boost": True}}}
S = SET[ROUTE]; S["vs"].update(CFG.get("voice_settings", {}))
FXCHAIN = {"alien": "asetrate=44100*1.1892,aresample=44100,atempo=0.8409,vibrato=f=5.5:d=0.08", "none": None}[FX]
VOICES = json.load(open(A + "voices.json")) if os.path.exists(A + "voices.json") else {}

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
    return secs

def segments(sec):
    """Split a section into speaker runs: [(speaker, text)] - narrator lines are joined, {name} lines stand alone."""
    out = []
    for l in sec:
        m = re.match(r"\{(\w+)\}\s*(.*)", l)
        spk, txt = (m.group(1), m.group(2)) if m else ("narrator", l)
        if out and out[-1][0] == spk == "narrator": out[-1] = (spk, out[-1][1] + " " + txt)
        else: out.append((spk, txt))
    return out

def clean(t): return re.sub(r"\s+", " ", re.sub(r"\[[^\]]*\]\s*", "", t)).strip()

def decode(mp3, fx=None):
    af = ["-af", fx] if fx else []
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", "pipe:0", *af, "-ac", "1", "-ar", str(SR), "-f", "f32le", "pipe:1"], input=mp3, capture_output=True, check=True)
    return np.frombuffer(p.stdout, dtype=np.float32)

def multipart(path, fields, files):
    b = uuid.uuid4().hex; body = b""
    for k, v in fields.items(): body += f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    for k, (fn, data, ct) in files.items():
        body += f'--{b}\r\nContent-Disposition: form-data; name="{k}"; filename="{fn}"\r\nContent-Type: {ct}\r\n\r\n'.encode() + data + b"\r\n"
    body += f"--{b}--\r\n".encode()
    req = urllib.request.Request("https://api.elevenlabs.io/v1" + path, data=body, method="POST",
                                 headers={"xi-api-key": KEY, "Content-Type": f"multipart/form-data; boundary={b}"})
    with urllib.request.urlopen(req, timeout=600) as r: return r.read()

def tts(text, voice, prev="", nxt=""):
    body = {"text": text if ROUTE == "v3" else clean(text), "model_id": S["model"] if ROUTE != "sts" else "eleven_multilingual_v2", "voice_settings": S["vs"]}
    if ROUTE == "sts": body["voice_settings"] = SET["v2"]["vs"]
    if ROUTE != "v3" and (prev or nxt): body.update({"previous_text": clean(prev)[-400:], "next_text": clean(nxt)[:400]})
    r = json.loads(call(f"/text-to-speech/{voice}/with-timestamps?output_format=mp3_44100_192", body))
    return base64.b64decode(r["audio_base64"]), (r.get("alignment") or r.get("normalized_alignment"))

def strip_tags(al):
    ch, st, en = al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]
    o = ([], [], []); i = 0; n = len(ch)
    while i < n:
        if ch[i] == "[":
            while i < n and ch[i] != "]": i += 1
            i += 1
            if i < n and ch[i] == " ": i += 1
            continue
        o[0].append(ch[i]); o[1].append(st[i]); o[2].append(en[i]); i += 1
    while o[0] and o[0][0] == " ":
        for a in o: a.pop(0)
    return o

def align_audio(wav_bytes, text):
    """ElevenLabs forced alignment -> character alignment; fallback faster-whisper words spread over characters."""
    try:
        r = json.loads(multipart("/forced-alignment", {"text": text}, {"file": ("perf.wav", wav_bytes, "audio/wav")}))
        cs = r["characters"]
        return {"characters": [c["text"] for c in cs], "character_start_times_seconds": [c["start"] for c in cs],
                "character_end_times_seconds": [c["end"] for c in cs]}
    except Exception as ex:
        print("forced alignment failed (", ex, ") -> faster-whisper fallback")
        from faster_whisper import WhisperModel
        tmp = A + "narr_cache/_fa.wav"; open(tmp, "wb").write(wav_bytes)
        ws = [w for s in WhisperModel("small", device="cpu", compute_type="int8").transcribe(tmp, language="en", word_timestamps=True)[0] for w in s.words]
        C, St, En = [], [], []
        for w in ws:
            t = w.word.strip(); d = (w.end - w.start) / max(1, len(t))
            if C: C.append(" "); St.append(w.start); En.append(w.start)
            for k, c in enumerate(t): C.append(c); St.append(w.start + k * d); En.append(w.start + (k + 1) * d)
        return {"characters": C, "character_start_times_seconds": St, "character_end_times_seconds": En}

def run():
    secs = sections(); flat = [s for sec in secs for s in segments(sec)]
    audio, C, St, En, off, billed = [], [], [], [], 0.0, 0
    if ROUTE == "sts":
        perf = A + "performance.wav"
        if not os.path.exists(perf): sys.exit("route sts needs audio/performance.wav (the owner's read of tts_script.txt)")
        key = A + "narr_cache/sts.mp3"
        if not os.path.exists(key):
            data = open(perf, "rb").read()
            mp3 = multipart(f"/speech-to-speech/{VOICE}?output_format=mp3_44100_192",
                            {"model_id": S["model"], "voice_settings": json.dumps(S["vs"]), "remove_background_noise": "true"},
                            {"audio": ("performance.wav", data, "audio/wav")})
            open(key, "wb").write(mp3)
        y = decode(open(key, "rb").read(), FXCHAIN)
        wavb = subprocess.run(["ffmpeg", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "pipe:0", "-f", "wav", "pipe:1"],
                              input=y.astype(np.float32).tobytes(), capture_output=True, check=True).stdout
        al = align_audio(wavb, " ".join(clean(t) for _, t in flat))
        audio = [y]; C, St, En = al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]
        off = len(y) / SR
    else:
        for k, (spk, text) in enumerate(flat):
            if ONLY and k not in ONLY: continue
            vv = VOICE if spk == "narrator" else VOICES.get(spk)
            if not vv: sys.exit(f'no voice id for {{{spk}}} in audio/voices.json (pick from the ElevenLabs voice list with the owner)')
            voice, cfx = (vv["id"], vv.get("fx")) if isinstance(vv, dict) else (vv, None)   # v6.0.1: per-character fx
            prev = flat[k - 1][1] if k else ""; nxt = flat[k + 1][1] if k + 1 < len(flat) else ""
            sig = json.dumps([ROUTE, voice, S, text, prev[-400:], nxt[:400]], sort_keys=True)
            cache = A + f"narr_cache/{k:03d}.json"
            if os.path.exists(cache) and json.load(open(cache)).get("sig") == sig:
                j = json.load(open(cache)); mp3 = base64.b64decode(j["mp3"]); al = j["al"]
            else:
                mp3, al = tts(text, voice, prev, nxt); billed += len(text)
                json.dump({"sig": sig, "mp3": base64.b64encode(mp3).decode(), "al": al}, open(cache, "w"))
            y = decode(mp3, FXCHAIN if spk == "narrator" else cfx)
            c, s, e = strip_tags(al)
            if C: C.append(" "); St.append(off); En.append(off)
            C += c; St += [t + off for t in s]; En += [t + off for t in e]
            audio.append(y); off += len(y) / SR
    y = np.concatenate(audio)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "pipe:0", A + "raw.wav"], input=y.astype(np.float32).tobytes(), check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", A + "raw.wav", "-b:a", "192k", A + "raw.mp3"], check=True)
    al = {"characters": C, "character_start_times_seconds": St, "character_end_times_seconds": En}
    json.dump(al, open(A + "alignment.json", "w")); json.dump(al, open(A + "alignment_raw.json", "w"))
    # estimated pace after post.py flow (gaps > 0.20 s -> 0.18 s), then the tempo that reaches TARGET
    toks, cur = [], None
    for c, s, e in zip(C, St, En):
        if c.isspace():
            if cur: toks.append(cur); cur = None
        elif cur is None: cur = [s, e]
        else: cur[1] = e
    if cur: toks.append(cur)
    span = toks[-1][1] - toks[0][0] if toks else 1.0
    span -= sum(max(0.0, (toks[i + 1][0] - toks[i][1]) - 0.18) for i in range(len(toks) - 1) if toks[i + 1][0] - toks[i][1] > 0.20)
    raw_wps = len(toks) / max(0.5, span); tempo = round(min(1.35, max(0.9, TARGET / raw_wps)), 3)
    rep = {"route": ROUTE, "voice": VOICE, "fx": FX, "settings": S, "sections": len(secs), "segments": len(flat),
           "chars_billed": billed, "raw_dur_s": round(off, 2), "words": len(toks), "est_wps_after_flow_edit": round(raw_wps, 2),
           "tempo_for_target": tempo, "target_wps": TARGET,
           "note": "est pace still below target at tempo 1.35 -> regenerate (v2 speed is already max; shorten sections / use sts)" if TARGET / raw_wps > 1.35 else ""}
    json.dump(rep, open(A + "narrate_report.json", "w"), indent=1)
    if not os.path.exists(A + "post_cfg.json"):
        json.dump({"mode": "flow", "tempo": tempo}, open(A + "post_cfg.json", "w"), indent=1)
    print(json.dumps(rep))

if __name__ == "__main__":
    run()
