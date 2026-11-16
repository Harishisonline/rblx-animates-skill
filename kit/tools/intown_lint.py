"""In-this-town / In-this-world SCRIPT + TAKE lint (calm deadpan first-person storyteller; NOT hype).
Bands are MEASURED on the user's two reference reels (docs/research/INTOWN_FORMAT.md, research/intown_refs/MEASUREMENTS.md).
Supersedes hype_lint.py for this format (hype_lint demands '!', spoken SFX and a question CTA: all wrong here).

    python tools/intown_lint.py <script.txt | transcript.txt | stt.json | slug> [--words words.json] [--json]

Inputs: a plain script (one or more sentences per line, '#' lines = notes); an intown_refs *_transcript.txt
(lines "t0- t1 [Nw] sentence", timings used); an ElevenLabs *_stt.json or a words.json ([{word,start,end}]).
A slug uses videos/<slug>/script.txt plus videos/<slug>/audio/words.json when it exists.
Timing rows (first word, gaps, delivered wpm) run only when timings exist; otherwise they print 'skip'.
Exit code 1 when any row FAILS.

Rows (FAIL unless stated)                       reels R1 / R2 (measured)
  '!' in narration                              0 / 0
  spoken SFX words / ad-libs                    0 / 0
  [tags] or whisper cues                        0 / 0
  CTA anywhere / 'X or Y?' question near end    none / none
  sentence length: median 7-13, share > 16 w    10, 13 % / 9, 6 %   FAIL median outside 6-14, share > 25 %, any > 34
  'Blox Town' / 'Blox City' branding            never in this format
  premise in sentence 1: 'In this town/world,' + an exact rule (number, time, 'every', 'if', 'exactly', quoted phrase)
  word count 470-530 (FAIL outside 440-560)     496 / 499
  wpm: delivered 225-290 (timings), else text estimate of length 100-135 s at 257 wpm
  first word <= 0.3 s (timings)                 0.10 / 0.16 s
  gaps > 0.6 s (timings)                        0 / 0
  escalation / time markers >= 3               R1 9 / R2 8 ('The following night', 'One night', 'In March', 'again'...)
  ending: last sentence <= 8 words, no '?', twist ('was my', 'wasn't', 'always'...) or callback to the first 5 sentences
"""
import json, os, re, statistics, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hype_lint import is_sfx  # one spoken-SFX word list for the whole kit

STUDIO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TS_LINE = re.compile(r"^\s*([\d.]+)-\s*([\d.]+)\s+\[\s*\d+w\]\s+(.*)$")
CTA = re.compile(r"\b(comment|follow|subscribe|like and|leave a like|smash|share this|part\s*2|next (story|episode|part)|"
                 r"let me know|would you)\b", re.I)
BRAND = re.compile(r"\bblox\s*(town|city)\b", re.I)
PREMISE = re.compile(r"^\W*in this (town|world|city|village|school)\b", re.I)
RULE = re.compile(r"\d|\b(every|each|exactly|if|whenever|when|always|never|only|once|one|two|three|four|five|six|seven|"
                  r"eight|nine|ten|twelve|hundred|midnight|noon)\b|[\"“]", re.I)
TIME = re.compile(r"\b(the following (night|day|morning|week)|the next (night|day|morning|week)|next (night|day|morning)|"
                  r"one (night|day|morning|evening)|that (night|day|morning|evening)|this time|again|after (a|an|two|three|that|school)\b|"
                  r"by (january|february|march|april|may|june|july|august|september|october|november|december|then|the end)|"
                  r"in (january|february|march|april|may|june|july|august|september|october|november|december)|"
                  r"on (our|my|her|his) birthday|every (night|day|morning)|weeks? later|days? later|years? later|later that|"
                  r"tonight|tomorrow|yesterday)\b", re.I)
TWIST = re.compile(r"\b(was my|is my|were my|wasn't|isn't|always|never|still|all along|it was|it's)\b", re.I)
# real English nouns/verbs that are also SFX words: flag only when spoken AS a sound (own sentence <= 3 words,
# doubled 'knock knock', or CAPS/stretched). 'the bark of the oak' (R2) is not a spoken SFX.
AMBIG = set("bark pop tap ring snap crack click knock tick tock slap crash splash bang buzz ding dong beep hiss thud thump "
            "smack bonk creak slam fizz honk crunch munch chomp burp tweet growl rumble zap whir whirr tap gasp gulp drip "
            "plop glug ugh oof ow ouch huh yay".split())
STOP = set("the a an and or but of to in on at it is was i my me we you he she they her his this that with for as be "
           "had have so then just every one not no".split())


def _words_from_json(p):
    d = json.load(open(p, encoding="utf-8"))
    ws = d.get("words", d) if isinstance(d, dict) else d
    out = []
    for w in ws:
        if w.get("type", "word") != "word":
            continue
        out.append(dict(word=(w.get("word") or w.get("text") or "").strip(), start=float(w["start"]), end=float(w["end"])))
    return [w for w in out if w["word"]]


def load(arg, words_path=None):
    """-> (path, sentences [str], words with timings or None)"""
    path, words = arg, None
    if not os.path.exists(arg):
        v = os.path.join(os.path.expanduser("~/RobloxStories/videos"), arg)
        path = os.path.join(v, "script.txt")
        wj = os.path.join(v, "audio", "words.json")
        if os.path.exists(wj) and not words_path:
            words_path = wj
    if path.endswith(".json"):
        words = _words_from_json(path)
        text = " ".join(w["word"] for w in words)
        sents = split(text)
    else:
        raw = [l for l in open(path, encoding="utf-8").read().splitlines() if l.strip() and not l.lstrip().startswith("#")]
        ts = [TS_LINE.match(l) for l in raw]
        if any(ts):  # intown_refs transcript: one timed sentence per line
            rows = [(float(m.group(1)), float(m.group(2)), m.group(3).strip()) for m in ts if m]
            sents = [r[2] for r in rows]
            words = []
            for t0, t1, s in rows:  # spread words evenly inside each timed sentence (gaps between lines are real)
                toks = s.split()
                step = (t1 - t0) / max(1, len(toks))
                words += [dict(word=t, start=t0 + i * step, end=t0 + (i + 1) * step - 0.001) for i, t in enumerate(toks)]
        else:
            sents = split(" ".join(raw))
    if words_path:
        words = _words_from_json(words_path)
    return path, sents, words


def split(text):
    parts = re.findall(r"[^.!?…]+(?:[.!?…]+|$)[\"'”’]*", text)
    return [p.strip() for p in parts if re.search(r"[A-Za-z0-9]", p)]


def nw(s):
    return len(re.sub(r"\[[^\]]+\]", " ", s).split())


def unquoted(s):
    return re.sub(r"[\"“][^\"”]*[\"”]", " ", s)


def content(s):
    return {w for w in re.findall(r"[a-z']+", s.lower()) if w not in STOP and len(w) > 2}


def sfx_hits(sents):
    out = set()
    for s in sents:
        ts = re.sub(r"\[[^\]]+\]", " ", s).split()
        for i, t in enumerate(ts):
            if not is_sfx(t):
                continue
            core = re.sub(r"[^A-Za-z]", "", t)
            n = core.lower()
            dup = i + 1 < len(ts) and re.sub(r"[^a-z]", "", ts[i + 1].lower()) == n
            if n not in AMBIG or len(ts) <= 3 or dup or (core.isupper() and len(core) > 1) or re.search(r"(.)\1\1", n):
                out.add(n)
    return out


def analyse(sents, words):
    text = " ".join(sents)
    toks = re.sub(r"\[[^\]]+\]", " ", text).split()
    lens = [nw(s) for s in sents]
    a = dict(words=len(toks), sentences=len(sents), len_med=statistics.median(lens) if lens else 0,
             len_max=max(lens, default=0), long_share=round(sum(1 for n in lens if n > 16) / max(1, len(lens)), 3),
             longest=[s[:70] for s in sents if nw(s) > 24][:4])
    a["excl"] = text.count("!")
    a["sfx"] = sorted(sfx_hits(sents))
    a["tags"] = re.findall(r"\[[^\]]+\]", text) + re.findall(r"\bwhisper(s|ed|ing)?\b", text, re.I)
    tail = sents[-5:]
    a["cta"] = [s[:60] for s in sents if CTA.search(unquoted(s))]
    a["q_cta"] = [s[:60] for s in tail if "?" in unquoted(s) or re.search(r"\b\w+ or \w+\?", s)]
    a["brand"] = sorted({m.group(0) for m in BRAND.finditer(text)})
    s1 = sents[0] if sents else ""
    a["premise"] = bool(PREMISE.match(s1)) and bool(RULE.search(s1[15:]))
    a["s1"] = s1[:80]
    a["time_markers"] = [m.group(0) for m in TIME.finditer(text)]
    last = sents[-1] if sents else ""
    early = set().union(*[content(s) for s in sents[:5]]) if sents else set()
    a["last"] = last
    a["callback"] = sorted(content(last) & early)
    a["ending_ok"] = nw(last) <= 8 and "?" not in last and bool(TWIST.search(last) or a["callback"])
    if words:
        t0, t1 = words[0]["start"], words[-1]["end"]
        gaps = [round(b["start"] - x["end"], 2) for x, b in zip(words, words[1:])]
        a.update(first_word=round(t0, 2), wpm=round(len(words) / max(t1 - t0, 1e-3) * 60), dur=round(t1, 1),
                 gaps_over=[g for g in gaps if g > 0.6], gap_max=max(gaps, default=0),
                 gap_med=statistics.median([g for g in gaps if g >= 0.12] or [0]))
    else:
        a["est_dur"] = round(len(toks) / 257 * 60, 1)
    return a


def grade(a):
    F, P, X, S = "FAIL", "PASS", "FIX", "skip"
    r = [
        ("no '!'", f"{a['excl']} found", P if a["excl"] == 0 else F),
        ("no spoken SFX / ad-libs", ", ".join(a["sfx"]) or "none", P if not a["sfx"] else F),
        ("no [tags] / whisper cues", ", ".join(a["tags"][:6]) or "none", P if not a["tags"] else F),
        ("no CTA", "; ".join(a["cta"][:2]) or "none", P if not a["cta"] else F),
        ("no question ending", "; ".join(a["q_cta"][:2]) or "none", P if not a["q_cta"] else F),
        ("sentence length", f"median {a['len_med']}, {a['long_share']:.0%} over 16 w, max {a['len_max']} (reels 9-10, 6-13 %)",
         P if 7 <= a["len_med"] <= 13 and a["long_share"] <= 0.2 and a["len_max"] <= 34 else
         (F if not 6 <= a["len_med"] <= 14 or a["long_share"] > 0.25 or a["len_max"] > 34 else X)),
        ("no Blox Town/City", ", ".join(a["brand"]) or "none", P if not a["brand"] else F),
        ("premise in sentence 1", a["s1"], P if a["premise"] else F),
        ("word count", f"{a['words']} words, {a['sentences']} sentences (reels 496-499 / 46-50)",
         P if 470 <= a["words"] <= 530 else (X if 440 <= a["words"] <= 560 else F)),
    ]
    if "wpm" in a:
        r += [("delivered wpm", f"{a['wpm']} over {a['dur']} s (band 225-290)",
               P if 225 <= a["wpm"] <= 290 else (X if 205 <= a["wpm"] <= 310 else F)),
              ("first word <= 0.3 s", f"{a['first_word']} s", P if a["first_word"] <= 0.3 else F),
              ("gaps > 0.6 s", f"{len(a['gaps_over'])} (max {a['gap_max']} s, median pause {a['gap_med']} s)",
               P if not a["gaps_over"] else F)]
    else:
        r += [("length estimate @257 wpm", f"~{a['est_dur']} s (target 100-135 s)",
               P if 100 <= a["est_dur"] <= 135 else F),
              ("first word / gaps", "no timings (run on words.json after TTS)", S)]
    r += [("escalation / time markers", f"{len(a['time_markers'])}: {', '.join(a['time_markers'][:6])}",
           P if len(a["time_markers"]) >= 3 else F),
          ("twist / callback ending", f"\"{a['last'][:60]}\" ({nw(a['last'])} w; callback {', '.join(a['callback'][:4]) or '-'})",
           P if a["ending_ok"] else F)]
    return r


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__); return 0
    wp = argv[argv.index("--words") + 1] if "--words" in argv else None
    path, sents, words = load(argv[0], wp)
    a = analyse(sents, words)
    rows = grade(a)
    if "--json" in argv:
        print(json.dumps(dict(script=path, metrics=a, rows=rows), indent=1))
    else:
        print(f"INTOWN LINT  {path}")
        for n, v, s in rows:
            print(f"[{s:4s}] {n:26s} {v}")
        for s in a["longest"]:
            print(f"        long: {s}")
        f = [x for x in rows if x[2] == "FAIL"]
        print("INTOWN OK" if not f and not any(x[2] == "FIX" for x in rows) else
              (f"INTOWN FAIL ({len(f)}): rewrite before TTS" if f else "INTOWN: soft issues (FIX)"))
    return 1 if any(x[2] == "FAIL" for x in rows) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
