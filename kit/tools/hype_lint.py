"""Hype lint: checks a narration script for CONSTANT HYPE before any TTS credit is spent (docs/research/NARRATION_HYPE.md).
Pure Python, no network.      python tools/hype_lint.py <script.txt | slug> [--json] [--wps 3.9] [--max-words 14] [--format NAME]
Bands for wpm / spoken SFX / exclamations / flat stretch come from docs/FORMATS.json (--format, else the video's
story.json "format", else in_this_world). The text-estimate wpm band (235-290) is wider at the bottom than pacing.py's
DELIVERED band (255-290): both share the 290 ceiling; pacing.py on words.json after TTS is the real check.
Exit code 1 when any row FAILS.

Time model (no audio needed): each word = 1/wps s (default 4.5 w/s = 270 wpm raw, the measured high-view ref pace (262-302 wpm)), plus pauses:
sentence end 0.18 s, ellipsis/dash 0.35 s, comma 0.06 s, [pause] tag 0.4 s. Lines starting with '#' are notes; [tags] are
stripped from the word count but counted as delivery cues.
"Spark" = anything that re-lifts energy: '!' or '?' sentence, a spoken SFX word, a CAPS word (2+ letters), a 'Wait'/'Boom'
style interjection. Flat stretch = longest time between two sparks.

Targets                                   PASS                  FIX                 FAIL
  wpm estimate (incl. pauses)             235-290               215-235 / 290-310   outside
  longest flat stretch                    <= 6 s                6-10 s              > 10 s
  sentences > max-words (14)              0-2                   3-5 or any > 20     any > 26
  hook spark in first 3 s                 yes                   -                   no
  spoken SFX per 10 s                     >= 0.6                0.3-0.6             < 0.3
  exclamations per 10 s                   >= 1.0                0.5-1.0             < 0.5
  questions / direct address ('you')      >= 2                  1                   0
  CTA in the last 2 sentences             yes                   -                   no
  beat lines open with [tag], 30-250 ch   >= 50 %, all in band  >= 25 % / <= 2 off  else
"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import format_preset as FP
except Exception:
    FP = None
BANDS = dict(name="in_this_world", wpm=(225, 290), flat_ok=6, flat_fail=10, sfx=0.0, ex=0.0)  # measured on In-this-town refs 2026-11-14 (INTOWN_FORMAT.md)


def set_format(argv, slug=None):
    """Load per-format bands from docs/FORMATS.json into BANDS."""
    if FP is None:
        return BANDS
    n = FP.fmt_arg(argv, slug)
    nr = FP.narration(n)
    BANDS.update(name=n, wpm=tuple(nr["wpm_text_estimate"]), flat_ok=nr["spark_every_s"], flat_fail=nr["flat_fail_s"],
                 sfx=nr["spoken_sfx_per10"], ex=nr["exclam_per10"])
    return BANDS

SFX = """woosh whoosh swoosh swish zoom vroom boom bam bang kaboom pow wham smack slap thud thump bonk clunk crash
splash splat sploosh plop drip glug gulp gasp ding dong ring beep boop buzz bzz bzzz bzzzz zap crack snap click clack
tick tock knock creak slam poof pop fizz sizzle hiss whirr whir vrrr ka-ching cha-ching ching honk screech skrrt skrt
crunch munch chomp burp achoo yoink ugh oof ow ouch argh aah ahh huh dun duh-duh wee weee wooo yay boing sproing
rumble grr growl ribbit tweet meow woof bark tap thwack shh psst pew""".split()
SFX = set(SFX)
INTERJ = {"wait", "what", "boom", "bro", "nope", "yes", "no", "wow", "okay", "ok", "seriously", "guess", "plot", "twist",
          "then", "suddenly", "but"}
CTA = re.compile(r"\b(comment|follow|subscribe|like|likes|share|leave a like|part\s*2|next (story|episode|part))\b", re.I)
HOOK_START = re.compile(r"^(look|what if|imagine|in this (world|town)|i (let|got|found|woke|saw)|you|this|wait|stop|never)\b", re.I)


def norm(w):
    return re.sub(r"[^a-z\-]", "", w.lower())


def is_sfx(w):
    n = norm(w).strip("-")
    if not n:
        return False
    if n in SFX:
        return True
    return bool(re.fullmatch(r"(b?z{3,}|sh+|a+h+|o+h+|wo+sh|bo+m|wh?e{2,}|bzz+|zz+|vr+o*m|ah+)", n))


def load(path):
    if not os.path.exists(path):
        for base in (os.path.expanduser("~/RobloxStories/videos"),):
            p = os.path.join(base, path, "script.txt")
            if os.path.exists(p):
                path = p
                break
    lines = [l for l in open(path, encoding="utf-8").read().splitlines() if l.strip() and not l.lstrip().startswith("#")]
    return path, " ".join(lines)


def sentences(text):
    parts = re.findall(r"[^.!?…]+(?:[.!?…]+|$)[\"'”’]*", text)
    return [p.strip() for p in parts if re.search(r"[A-Za-z0-9]", p)]


def analyse(text, wps=4.5, max_words=14):
    tags = re.findall(r"\[[^\]]+\]", text)
    t, events, words, sent_rows = 0.0, [], [], []
    for s in sentences(text):
        clean = re.sub(r"\[[^\]]+\]", " ", s)
        toks = clean.split()
        t0 = t
        end = s.rstrip("\"'”’ ")[-1:] if s.strip() else "."
        excl, ques = "!" in s, "?" in s
        for tok in toks:
            t += 1.0 / wps
            words.append(tok)
            if tok.endswith(","):
                t += 0.06
            if "..." in tok or "…" in tok or tok in ("-", "—"):
                t += 0.35
            core = re.sub(r"[^A-Za-z]", "", tok)
            if is_sfx(tok):
                events.append((t, "sfx", tok))
            elif len(core) >= 2 and core.isupper() and core not in ("OK",):
                events.append((t, "caps", tok))
            elif norm(tok) in ("wait", "boom", "nope", "wow", "bro"):
                events.append((t, "interj", tok))
        t += 0.4 * s.count("[pause]")
        if excl:
            events.append((t, "!", s[-30:]))
        if ques:
            events.append((t, "?", s[-30:]))
        t += 0.35 if end in "…" or s.rstrip().endswith("...") else 0.18
        sent_rows.append(dict(text=s, n=len(toks), t0=round(t0, 2), t1=round(t, 2), spark=excl or ques))
    dur = max(t, 0.1)
    times = [0.0] + sorted(e[0] for e in events) + [dur]
    gaps = [(times[i + 1] - times[i], times[i]) for i in range(len(times) - 1)]
    flat, flat_at = max(gaps) if gaps else (dur, 0.0)
    flat_txt = next((r["text"] for r in sent_rows if r["t1"] > flat_at), "")
    n_sfx = sum(1 for e in events if e[1] == "sfx")
    n_ex = sum(1 for r in sent_rows if "!" in r["text"])
    n_q = sum(1 for r in sent_rows if "?" in r["text"])
    n_you = sum(1 for w in words if norm(w) in ("you", "your", "youre", "you'd", "yourself"))
    hook_ev = [e for e in events if e[0] <= 3.0]
    hook = bool(hook_ev) or bool(HOOK_START.match(text.strip()))
    long_s = [r for r in sent_rows if r["n"] > max_words]
    worst = max((r["n"] for r in sent_rows), default=0)
    cta = any(CTA.search(r["text"]) for r in sent_rows[-2:])
    wpm = len(words) / dur * 60
    per10 = lambda n: n / dur * 10
    return dict(words=len(words), dur=round(dur, 1), wpm=round(wpm), flat=round(flat, 1), flat_at=round(flat_at, 1),
                flat_txt=flat_txt[:70], long=[(r["n"], r["text"][:60]) for r in long_s], worst=worst,
                hook=hook, hook_ev=[e[2] for e in hook_ev][:3], sfx=n_sfx, sfx10=round(per10(n_sfx), 2),
                sfx_words=sorted({e[2].strip(".,!?").lower() for e in events if e[1] == "sfx"}),
                ex=n_ex, ex10=round(per10(n_ex), 2), q=n_q, you=n_you, cta=cta, tags=len(tags))


def grade(a):
    def band(v, ok, fix):
        return "PASS" if ok(v) else ("FIX" if fix(v) else "FAIL")
    nl = len(a["long"])
    B = BANDS
    return [
        ("wpm estimate", f'{a["wpm"]} ({a["words"]} words, ~{a["dur"]} s)',
         band(a["wpm"], lambda v: B["wpm"][0] <= v <= B["wpm"][1], lambda v: B["wpm"][0] - 20 <= v <= B["wpm"][1] + 20)),
        ("longest flat stretch", f'{a["flat"]} s from ~{a["flat_at"]} s: "{a["flat_txt"]}"',
         band(a["flat"], lambda v: v <= B["flat_ok"], lambda v: v <= B["flat_fail"])),
        ("long sentences", f'{nl} over limit, longest {a["worst"]} words',
         "FAIL" if a["worst"] > 26 else ("FIX" if nl > 2 or a["worst"] > 20 else "PASS")),
        ("hook spark in first 3 s", ", ".join(a["hook_ev"]) or ("opening pattern" if a["hook"] else "none"),
         "PASS" if a["hook"] else "FAIL"),
        ("spoken SFX", f'{a["sfx"]} ({a["sfx10"]}/10 s) {" ".join(a["sfx_words"][:10])}',
         band(a["sfx10"], lambda v: v >= B["sfx"], lambda v: v >= B["sfx"] / 2)),
        ("exclamations", f'{a["ex"]} ({a["ex10"]}/10 s)', band(a["ex10"], lambda v: v >= B["ex"], lambda v: v >= B["ex"] / 2)),
        ("questions + 'you'", f'{a["q"]} questions, {a["you"]} you/your',
         band(a["q"] + min(a["you"], 2), lambda v: v >= 2, lambda v: v >= 1)),
        ("CTA in last 2 sentences", "yes" if a["cta"] else "no", "PASS" if a["cta"] else "FAIL"),
    ]


def beat_row(path):
    """hype_v3 voices one TTS call per script line (kit.py VOICE_PRESETS): each line = a beat. Measured 2026-11-14
    (voice_tests/NOTES.md): per-line takes opening with a [tag] gave f0 range 21.6 st vs 16.7 st for one long take."""
    ls = [l.strip() for l in open(path, encoding="utf-8") if l.strip() and not l.lstrip().startswith("#")]
    tagged = sum(1 for l in ls if l.startswith("["))
    bad = [len(l) for l in ls if not 30 <= len(l) <= 250]
    frac = tagged / max(1, len(ls))
    st = "PASS" if frac >= 0.5 and not bad else ("FIX" if frac >= 0.25 or len(bad) <= 2 else "FAIL")
    return ("beat lines (per-take)", f"{len(ls)} lines, {tagged} open with a [tag], {len(bad)} outside 30-250 chars", st)


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    wps = float(argv[argv.index("--wps") + 1]) if "--wps" in argv else 4.5
    mw = int(argv[argv.index("--max-words") + 1]) if "--max-words" in argv else 14
    path, text = load(argv[0])
    set_format(argv, None if os.path.exists(argv[0]) else argv[0])
    lint = FP.narration(BANDS["name"]).get("script_lint") if FP else None
    if lint == "intown_lint" and "--hype" not in argv:  # calm storyteller format: hype rows are wrong here (INTOWN_FORMAT.md)
        print(f"format {BANDS['name']}: delegating to tools/intown_lint.py (pass --hype to force the old hype rows)")
        import intown_lint
        return intown_lint.main([a for a in argv if a not in ("--format",) and a != (argv[argv.index("--format") + 1] if "--format" in argv else None)])
    a = analyse(text, wps, mw)
    rows = grade(a) + [beat_row(path)]
    if "--json" in argv:
        print(json.dumps(dict(script=path, metrics=a, rows=rows), indent=1))
    else:
        print(f"HYPE LINT  {path}  (format {BANDS['name']}: wpm est {BANDS['wpm'][0]}-{BANDS['wpm'][1]}, SFX >= {BANDS['sfx']}/10 s, ! >= {BANDS['ex']}/10 s)")
        for name, val, st in rows:
            print(f"[{st:4s}] {name:24s} {val}")
        for n, s in a["long"][:6]:
            print(f"        long ({n}w): {s}")
        fails = [r for r in rows if r[2] == "FAIL"]
        fixes = [r for r in rows if r[2] == "FIX"]
        print("HYPE OK" if not fails and not fixes else ("HYPE FAIL: rewrite before TTS" if fails else "HYPE: soft issues (FIX)"))
    return 1 if any(r[2] == "FAIL" for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
