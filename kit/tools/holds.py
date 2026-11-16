"""Protected silences ("holds") for tighten.py / retempo.py, and time-shifting of the cue/beat files that ride on the voice.
A hold is a dramatic pause the story needs (REF4: 300-800 ms after shock fragments, before the reveal, after a black-out).
Mark one in any of these (all in videos/<slug>/audio/):
    cues.json   {"t": 41.2, "beat": "hold", "dur": 0.6}     (also drives the music cut in score.py / mix.py)
    beats.json  {"t": 41.2, "type": "hold", "dur": 0.6}
    words.json  {"word": "Nothing.", ..., "hold": 0.6}       (pause of 0.6 s after this word)
tighten.py never shortens a gap that holds one below max(--max-gap, dur); retempo.py puts the original gap back after
speeding the voice up. Both shift every "t" in cues.json / beats.json so beat cues stay on their words."""
import json, os


def _load(p):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return None


def holds(adir, words=None):
    """[(t, dur)] from cues.json, beats.json and words.json."""
    out = []
    for fn, key in (("cues.json", "beat"), ("beats.json", "type")):
        for c in _load(os.path.join(adir, fn)) or []:
            if str(c.get(key, "")).lower() in ("hold", "silence"):
                out.append((float(c["t"]), float(c.get("dur") or 0.6)))
    words = words if words is not None else (_load(os.path.join(adir, "words.json")) or [])
    for w in words:
        if w.get("hold"):
            out.append((float(w["end"]) + 0.01, float(w["hold"])))
    return sorted(out)


def gap_holds(words, hl, slack=0.25):
    """{gap index i (between word i and i+1): required seconds}."""
    req = {}
    for t, d in hl:
        for i in range(len(words) - 1):
            a, b = words[i]["end"], words[i + 1]["start"]
            if a - slack <= t <= b + slack:
                req[i] = max(req.get(i, 0), d)
                break
    for i, w in enumerate(words[:-1]):
        if w.get("hold"):
            req[i] = max(req.get(i, 0), float(w["hold"]))
    return req


def shift_files(adir, fn):
    """apply fn(t)->t to every "t" (and "dur" end for holds is kept) in cues.json / beats.json."""
    for name in ("cues.json", "beats.json"):
        p = os.path.join(adir, name)
        d = _load(p)
        if not isinstance(d, list):
            continue
        for c in d:
            if "t" in c:
                c["t"] = round(max(0.0, fn(float(c["t"]))), 3)
        json.dump(d, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
