"""Story / script engine for RBLX ANIMATES (rules: docs/STORY_ENGINE.md). No audio, no API calls.

    PY tools/story.py parse <playbook.pdf>          -> engine/stories/episodes.json (needs pdftotext)
    PY tools/story.py list                          -> one line per episode (number, genre, title)
    PY tools/story.py show <N>                      -> one episode's hook / beats / cliffhanger / engagement
    PY tools/story.py check <script.txt|slug> [--episode N] [--wpm 270]
                                                    -> validates against the rules, prints beat sheet + timing
    PY tools/story.py beats <script.txt|slug> [--wpm 270]   -> beat sheet/timing only

A <slug> resolves to <workspace>/videos/<slug>/script.txt. script.txt = spoken words only, one line per caption
sentence; lines starting with '#' and text in [brackets] are ignored (notes / stage directions).
Exit code 1 if any rule FAILs (warnings do not fail)."""
import json, os, re, subprocess, sys

ENGINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EP_JSON = os.path.join(ENGINE, "stories", "episodes.json")
WORKSPACE = os.path.expanduser("~/RobloxStories")
try:
    WORKSPACE = json.load(open(os.path.expanduser("~/.roblox-story-kit.json")))["workspace"]
except Exception:
    pass

# ---- rules (keep in sync with docs/STORY_ENGINE.md) -------------------------------------------------------
# v3.7: from docs/FORMATS.json default format (in_this_world): 255-290 wpm delivered, length 60-120 s (was 215-245 / 80-90)
WPM_MIN, WPM_TARGET, WPM_MAX = 255, 270, 290          # tools/pacing.py narration window (format in_this_world)
DUR_MIN, DUR_MAX = 60.0, 120.0                        # up to 120 s
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import format_preset as _FP
    _n, _p = _FP.get(None)
    WPM_MIN, WPM_MAX = _p["narration"]["wpm_delivered"]; WPM_TARGET = round((WPM_MIN + WPM_MAX) / 2)
    DUR_MIN, DUR_MAX = map(float, _p["length_s"])
except Exception:
    pass
WORDS_MIN = round(DUR_MIN * WPM_TARGET / 60)          # 270 at 270 wpm / 60 s
WORDS_MAX = round(DUR_MAX * WPM_TARGET / 60)          # 540 at 120 s
HOOK_RULE_BY_S = 3.0                                  # the rule must be being stated inside 3 s
HOOK_MAX_WORDS = 18
BEATS = [(0, 12, "Rule + visual proof"), (12, 25, "Character + stakes"), (25, 40, "First complication"),
         (40, 56, "Investigation / escalation"), (56, 72, "Reveal + emotional choice")]
BANNED = ["little did i know", "everything changed", "but then", "plot twist", "you won't believe",
          "suddenly", "and that's when", "smash that like", "hit that like", "out of nowhere",
          "one day", "i'll never forget", "wait for it", "and then", "nobody expected", "it was just a normal day",
          "the end", "stay tuned", "like and subscribe"]
CTA_WORDS = ("comment", "like, share", "follow")
GENRE_KEYS = {
    "horror": ["breath", "whisper", "dark", "midnight", "scream", "dead", "ghost", "blood", "watching", "peephole",
               "shadow", "missing", "vanish", "grave", "haunt", "creature", "monster", "behind", "wall", "lights out"],
    "mystery": ["clue", "secret", "investigat", "reveal", "source", "trace", "real ", "truth", "hidden", "account",
                "detective", "message", "map", "code"],
    "comedy": ["funny", "laugh", "joke", "pizza", "dance", "sneeze", "chicken", "cat ", "dog ", "prank", "banana",
               "silly", "awkward", "embarrass"],
    "emotional": ["mother", "father", "mom", "dad", "family", "grand", "friend", "love", "remember", "goodbye",
                  "forgive", "sister", "brother", "lonely"],
}


def norm(s):
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("…", "...").replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", s).strip()


def words(s):
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9'\-]*", norm(s))


def squash(s):
    return re.sub(r"[^a-z0-9]", "", norm(s).lower())


# ---- PDF -> episodes.json --------------------------------------------------------------------------------
def guess_genre(ep):
    blob = " ".join([ep["title"], ep["engine"], ep["hook"], ep["cliffhanger"]] + [b["text"] for b in ep["beats"]]).lower()
    score = {g: sum(blob.count(k) for k in ks) for g, ks in GENRE_KEYS.items()}
    return max(score, key=lambda g: (score[g], g == "mystery"))


def parse_pdf(pdf):
    txt = subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True, check=True).stdout
    txt = re.sub(r"RBLX ANIMATES \| EVERY BLOCK HAS A STORY\s+Page \d+", "", txt)
    chunks = re.split(r"\n\s*EPISODE (\d{2})\s*\n", txt)
    eps = []
    for i in range(1, len(chunks), 2):
        n, body = int(chunks[i]), chunks[i + 1]
        flat = lambda s: norm(" ".join(l.strip() for l in s.splitlines()))
        title = flat(body.split("Story engine:")[0])
        engine = flat(re.search(r"Story engine:(.*?)OPENING HOOK", body, re.S).group(1))
        hook = flat(re.search(r"OPENING HOOK \(0.3 SECONDS\)(.*?)80.90 SECOND STORY FLOW", body, re.S).group(1)).strip('"')
        flow = re.search(r"STORY FLOW(.*?)FINISHING CLIFFHANGER", body, re.S).group(1)
        beats = []
        for m in re.finditer(r"(\d+)\D(\d+)s \| ([^\n]+)\n(.*?)(?=\n\s*\d+\D\d+s \||\Z)", flow, re.S):
            beats.append({"t0": int(m.group(1)), "t1": int(m.group(2)), "label": flat(m.group(3)), "text": flat(m.group(4))})
        cliff = flat(re.search(r"FINISHING CLIFFHANGER(.*?)ENGAGEMENT", body, re.S).group(1)).strip('"')
        eng = flat(re.search(r"ENGAGEMENT \+ COMMENT PROMPT \(FINAL 5.8 SECONDS\)(.*?)CLAUDE CODE PROMPT", body, re.S).group(1)).strip('"')
        prompt = flat(re.search(r"CLAUDE CODE PROMPT(.*?)Creative QA:", body, re.S).group(1))
        qa = flat(re.search(r"Creative QA:(.*?)(?:\n\s*\n|\Z)", body, re.S).group(1))
        ep = {"number": n, "title": title, "world": "town" if title.lower().startswith("in this town") else "world",
              "engine": engine, "hook": hook, "beats": beats, "cliffhanger": cliff, "engagement": eng,
              "comment_words": re.findall(r"Comment ([A-Z]+(?: [A-Z]+)*?) or ([A-Z]+)", eng),
              "claude_prompt": prompt, "creative_qa": qa}
        ep["genre"] = guess_genre(ep)
        eps.append(ep)
    os.makedirs(os.path.dirname(EP_JSON), exist_ok=True)
    json.dump({"source": os.path.basename(pdf), "count": len(eps), "episodes": eps}, open(EP_JSON, "w"), indent=1,
              ensure_ascii=False)
    bad = [e["number"] for e in eps if len(e["beats"]) != 5]
    print(f"wrote {EP_JSON}: {len(eps)} episodes" + (f"  (beat parse issues: {bad})" if bad else ""))


def load_eps():
    return {e["number"]: e for e in json.load(open(EP_JSON))["episodes"]}


# ---- script checks ---------------------------------------------------------------------------------------
def load_script(arg):
    path = arg if os.path.isfile(arg) else os.path.join(WORKSPACE, "videos", arg, "script.txt")
    lines = []
    for l in open(path, encoding="utf-8"):
        l = re.sub(r"\[[^\]]*\]", "", l).strip()
        if l and not l.startswith("#"):
            lines.append(l)
    return path, lines


def timeline(lines, wpm):
    """(t0, t1, line) per line; ellipsis and line ends get small pauses (the kit's voice keeps them short)."""
    out, t, sec = [], 0.0, 60.0 / wpm
    for l in lines:
        w = len(words(l))
        d = w * sec * 0.97 + 0.12 * norm(l).count("...")
        out.append((t, t + d, l))
        t += d + 0.03
    return out


def beat_of(t):
    for a, b, name in BEATS:
        if a <= t < b:
            return f"{a}-{b}s {name}"
    return "72s+ Cliffhanger / CTA"


def beat_sheet(lines, wpm):
    tl = timeline(lines, wpm)
    cur = None
    print(f"\nBeat sheet at {wpm} wpm (estimate; real timing comes from audio/words.json via pacing.py):")
    for t0, t1, l in tl:
        b = beat_of(t0)
        if b != cur:
            print(f"  -- {b}")
            cur = b
        print(f"  {t0:5.1f}-{t1:5.1f}  {l}")
    return tl


def check(arg, ep_no=None, wpm=WPM_TARGET):
    path, lines = load_script(arg)
    full = " ".join(lines)
    n = len(words(full))
    res = []
    add = lambda lvl, name, msg: res.append((lvl, name, msg))

    d_lo, d_mid, d_hi = n / WPM_MAX * 60, n / wpm * 60, n / WPM_MIN * 60
    lvl = "ok" if DUR_MIN <= d_mid <= DUR_MAX else "FAIL"
    add(lvl, "length", f"{n} words -> {d_mid:.1f}s at {wpm} wpm (range {d_lo:.1f}-{d_hi:.1f}s at {WPM_MAX}-{WPM_MIN}); "
                       f"budget {WORDS_MIN}-{WORDS_MAX} words")

    hook = lines[0]
    hw = len(words(hook))
    first3 = " ".join(words(full)[: int(HOOK_RULE_BY_S * WPM_MAX / 60)]).lower()
    rule_kw = any(k in first3 for k in ("in this world", "in this town", "number", "rule", "your", "every"))
    add("ok" if rule_kw else "FAIL", "hook rule in 3 s", f"first ~3 s: '{first3}'")
    add("ok" if hw <= HOOK_MAX_WORDS else "warn", "hook length",
        f"{hw} words = {hw / wpm * 60:.1f}s (rule must START in 3 s; whole hook line ideally <= {HOOK_MAX_WORDS} words)")
    if re.match(r"(?i)(hey|hi|hello|what's up|welcome|guys)\b", hook):
        add("FAIL", "hook greeting", "no greetings before the hook")

    last = lines[-1]
    low = last.lower()
    cta_ok = "comment" in low and ("like" in low or "follow" in low)
    add("ok" if cta_ok else "FAIL", "CTA last", "final line must contain 'Comment X or Y' + like/share/follow")
    m = re.search(r"(?i)comment ([A-Z]+) or ([A-Z]+)", last)
    add("ok" if m else "warn", "comment choice", m.group(0) if m else "no binary 'Comment A or B' choice found")
    qpos, cpos = low.find("?"), low.find("comment")
    add("ok" if 0 <= qpos < cpos or "?" in low else "warn", "question", "engagement line asks a question")
    if len(lines) >= 2:
        cl = lines[-2]
        cliff_ok = len(words(cl)) >= 6 and not any(k in cl.lower() for k in CTA_WORDS)
        add("ok" if cliff_ok else "FAIL", "cliffhanger", f"line before CTA: '{cl[:90]}'")

    hits = [b for b in BANNED if re.search(r"(?<![a-z])" + re.escape(b) + r"(?![a-z])", norm(full).lower())]
    add("FAIL" if hits else "ok", "banned phrases", ", ".join(hits) if hits else "none")

    sents = [s for s in re.split(r"(?<=[.!?])\s+", norm(full)) if s]
    longs = [s for s in sents if len(words(s)) > 22 and not any(k in s.lower() for k in CTA_WORDS)]
    add("warn" if longs else "ok", "sentence length", f"{len(longs)} sentences > 22 words" if longs else "all <= 22 words")

    toks = [w.lower() for w in words(full)]
    grams = {}
    for i in range(len(toks) - 3):
        g = " ".join(toks[i:i + 4])
        grams[g] = grams.get(g, 0) + 1
    rep = [g for g, c in grams.items() if c > 1]
    add("warn" if len(rep) > 3 else "ok", "self-repetition", ", ".join(rep[:5]) if rep else "none")

    # cross-video repetition: 6-word phrases shared with other scripts in the workspace
    vroot = os.path.join(WORKSPACE, "videos")
    mine = {" ".join(toks[i:i + 6]) for i in range(len(toks) - 5)}
    fixed = set()
    if ep_no:
        e = load_eps()[ep_no]
        for s in (e["hook"], e["cliffhanger"], e["engagement"]):
            t = [w.lower() for w in words(s)]
            fixed |= {" ".join(t[i:i + 6]) for i in range(len(t) - 5)}
    shared = {}
    if os.path.isdir(vroot):
        for v in os.listdir(vroot):
            p = os.path.join(vroot, v, "script.txt")
            if os.path.isfile(p) and os.path.abspath(p) != os.path.abspath(path):
                o = [w.lower() for w in words(open(p, encoding="utf-8").read())]
                ov = (mine & {" ".join(o[i:i + 6]) for i in range(len(o) - 5)}) - fixed
                ov = {g for g in ov if "like share and follow" not in g}
                if ov:
                    shared[v] = sorted(ov)[:3]
    add("warn" if shared else "ok", "cross-video repeats", json.dumps(shared) if shared else "none")

    if ep_no:
        e = load_eps()[ep_no]
        add("ok" if squash(e["hook"]) in squash(hook) else "FAIL", "episode hook", f"Ep{ep_no:02d}: '{e['hook']}'")
        add("ok" if squash(e["cliffhanger"]) in squash(" ".join(lines[-3:])) else "FAIL", "episode cliffhanger",
            e["cliffhanger"])
        add("ok" if squash(e["engagement"]) in squash(last) else "FAIL", "episode engagement", e["engagement"])

    print(f"{path}\n")
    for lvl, name, msg in res:
        print(f"[{lvl:4s}] {name:20s} {msg}")
    tl = beat_sheet(lines, wpm)
    print(f"\nEstimated runtime {tl[-1][1]:.1f}s (+0.25s tail). Shot target: ~{tl[-1][1] / 2.2:.0f}-{tl[-1][1] / 1.6:.0f} "
          f"shots (avg 1.6-2.2s; key beats 2.5-3.5s).")
    return not any(l == "FAIL" for l, _, _ in res)


def main(a):
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd = a[0]
    opt = lambda k, d: type(d)(a[a.index(k) + 1]) if k in a else d
    if cmd == "parse":
        parse_pdf(a[1])
    elif cmd == "list":
        for n, e in sorted(load_eps().items()):
            print(f"{n:02d} [{e['genre']:9s}] {e['title']}")
    elif cmd == "show":
        print(json.dumps({k: v for k, v in load_eps()[int(a[1])].items() if k != "claude_prompt"}, indent=1,
                         ensure_ascii=False))
    elif cmd == "check":
        return 0 if check(a[1], opt("--episode", 0) or None, opt("--wpm", WPM_TARGET)) else 1
    elif cmd == "beats":
        beat_sheet(load_script(a[1])[1], opt("--wpm", WPM_TARGET))
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
