"""Pacing checker v3 (REF1 cinematic cutting) for a video BEFORE rendering: reads audio/words.json + the @S(...) shot
list in shots.py.      python tools/pacing.py <slug> [--json] [--format in_this_world|horror|comedy|emotional_twist|chase_action|natural]
Exit code 1 when any hard rule FAILS (so the pipeline can stop before a render).

Targets (REF1, docs/REF1_CINEMATIC.md sec. 1 + 3.1, docs/STORY_ENGINE.md):
    average shot      1.5-1.9 s (about 48 frames)                              FAIL outside 1.3-2.2
    longest shot      <= 3.3 s, ever. Exception: emotional holds flagged with "[hold]" in the shot description
                      (max 4.5 s, at most 3 per video)                         FAIL
    shots < 0.6 s     at most 10 % (impact / flash cuts only)                  FAIL
    words per shot    one picture per narration phrase: 2-8 words; > 9 words = two phrases on one picture  FAIL (>12) / FIX
    cut on phrase     >= 60 % of cuts land on punctuation or after >= 2 words  FIX
    prop close-ups    ~28 % of shots (ok 18-38 %): INSERT/MACRO/PROP in the description, or cams.insert/macro/prop_macro
    shot-type variety >= 5 types; same type twice in a row <= 15 % of cuts
    shot count / rate cuts per minute in the format's band (in_this_world 26-40/min; refs ~30/min)
    narration         FORMAT band from docs/FORMATS.json (v3.7): in_this_world/horror/comedy 255-290 wpm (measured
                      high-view refs 262-293), chase 260-295, emotional 245-290, natural (legacy calm) 215-245;
                      words in first 15 s per format (62-75); no gap > 0.45 s; length per format (up to 120 s)
                      Format = --format, else videos/<slug>/story.json "format", else FORMATS.json default.
Shot types are read from the description prefix ("INSERT:", "MCU", "AERIAL", "LOW", "TOP", "RUN", ...) and from the
cams.* recipe the shot calls. Tag descriptions clearly; untagged shots count as "other"."""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import format_preset as FP
except Exception:   # FORMATS.json missing: keep the kit usable with the in_this_world numbers
    FP = None
FALLBACK = dict(name="in_this_world", wpm=(225, 290), w15=(50, 75), length=(60, 120), cpm=(26, 40), avg=(1.5, 1.9))


def fmt_targets(slug, argv):
    if FP is None:
        return FALLBACK
    n = FP.fmt_arg(argv, slug)
    p = FP.get(n)[1]
    return dict(name=n, wpm=tuple(p["narration"]["wpm_delivered"]), w15=tuple(p["narration"]["words_first_15s"]),
                length=tuple(p["length_s"]), cpm=tuple(p["cutting"]["cuts_per_min"]), avg=tuple(p["cutting"]["avg_shot_s"]))

STUDIO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TYPES = [  # (type, description keywords, cams recipe names)
    ("insert", ("INSERT", "MACRO", "PROP", "PHONE", "CALENDAR", "WRIST", "SCREEN", "SIGN"),
     ("insert", "macro", "prop_macro")),
    ("face", ("ECU", "MCU", "CLOSE", "CU", "FACE", "REACT", "TEAR"), ("close_up", "mcu", "ecu", "eye_med", "push_in")),
    ("aerial", ("AERIAL", "DRONE", "ESTABLISH", "WIDE", "CITY", "SKY"), ("aerial_glide", "aerial_dive", "establish",
                                                                      "fly_in_window", "pull_reveal", "crane")),
    ("low", ("LOW", "HERO", "DUTCH", "POWER"), ("ground_low", "hero_low", "dutch", "dutch_push")),
    ("top", ("TOP", "OVERHEAD", "MAP", "BIRD"), ("top_down", "overhead")),
    ("move", ("RUN", "CHASE", "TRACK", "FOLLOW", "WHIP", "TRUCK"), ("run_follow", "handheld_follow", "track_side", "truck",
                                                                    "whip_pan", "whip", "pov")),
    ("two", ("OTS", "TWO", "FACE-OFF", "DIALOG"), ("ots", "two_shot")),
    ("fx", ("FLASH", "TITLE", "GRAPHIC"), ()),
]


def classify(desc, body):
    d = desc.upper()
    head = d.split(":", 1)[0] if ":" in d[:24] else ""      # the type tag prefix ("AERIAL:", "MCU two-shot:") wins
    for part in (head, d):
        for name, kws, _ in TYPES:
            if part and any(re.search(r"(^|[^A-Z])" + re.escape(k) + r"($|[^A-Z])", part) for k in kws):
                return name
    for name, kws, _ in TYPES:
        if any(re.search(r"(^|[^A-Z])" + re.escape(k) + r"($|[^A-Z])", d) for k in kws):
            return name
    for c in re.findall(r"cams\.(\w+)\(", body):
        for name, _, recipes in TYPES:
            if c in recipes:
                return name
    return "other"


def parse_shots(src):
    pat = re.compile(r"@S\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(None|\d+)\s*(?:,\s*(?P<q>['\"])(.*?)(?P=q))?")
    ms = list(pat.finditer(src))
    out = []
    for k, m in enumerate(ms):
        body = src[m.end(): ms[k + 1].start() if k + 1 < len(ms) else len(src)]
        out.append(dict(id=int(m.group(1)), a=int(m.group(2)), b=None if m.group(3) == "None" else int(m.group(3)),
                        desc=m.group(5) or "", body=body))
    return out


def main(slug, as_json=False, argv=()):
    ft = fmt_targets(slug, list(argv))
    vdir = os.path.join(STUDIO, "videos", slug)
    words = json.load(open(os.path.join(vdir, "audio", "words.json"), encoding="utf-8"))
    end = words[-1]["end"] + 0.25
    shots = parse_shots(open(os.path.join(vdir, "shots.py"), encoding="utf-8").read())
    if not shots:
        print("no @S(...) shots found in shots.py"); return 1
    t = lambda i: 0.0 if i <= 0 else words[min(i, len(words) - 1)]["start"]
    for s in shots:
        s["t0"] = t(s["a"]); s["t1"] = end if s["b"] is None else t(s["b"])
        s["len"] = s["t1"] - s["t0"]
        s["nw"] = (len(words) if s["b"] is None else s["b"]) - s["a"]
        s["hold"] = "[hold]" in s["desc"].lower()
        s["type"] = classify(s["desc"], s["body"])
    n = len(shots)
    lens = [s["len"] for s in shots]
    avg = sum(lens) / n
    # wpm over the SPOKEN span (first word start -> last word end): a lead-in silence is not slow narration
    wpm = len(words) / max(words[-1]["end"] - words[0]["start"], 1e-3) * 60
    adir = os.path.join(vdir, "audio")
    placeholder = any(re.search(r"placeholder", f, re.I) for f in (os.listdir(adir) if os.path.isdir(adir) else []))
    w15 = sum(1 for w in words if w["start"] < 15)
    gaps = [(i, round(words[i + 1]["start"] - words[i]["end"], 2)) for i in range(len(words) - 1)
            if words[i + 1]["start"] - words[i]["end"] > 0.45]
    too_long = [s["id"] for s in shots if s["len"] > 3.3 and not s["hold"]]
    holds = [s for s in shots if s["hold"]]
    bad_holds = [s["id"] for s in holds if s["len"] > 4.5]
    short = [s["id"] for s in shots if s["len"] < 0.6]
    wordy = [s["id"] for s in shots if s["nw"] > 9 and not s["hold"]]
    very_wordy = [s["id"] for s in shots if s["nw"] > 12 and not s["hold"]]
    on_phrase = 0
    for s in shots[1:]:
        prev = words[s["a"] - 1]["word"].strip() if s["a"] > 0 else "."
        if re.search(r"[.!?,;:]$", prev) or s["nw"] >= 2:
            on_phrase += 1
    phrase_pct = on_phrase / max(1, n - 1)
    ins = sum(1 for s in shots if s["type"] == "insert") / n
    types = {}
    for s in shots:
        types[s["type"]] = types.get(s["type"], 0) + 1
    repeats = sum(1 for a, b in zip(shots, shots[1:]) if a["type"] == b["type"] and a["type"] != "other") / max(1, n - 1)
    cpm = n / end * 60
    cnt_ok = ft["cpm"][0] - 2 <= cpm <= ft["cpm"][1] + 2   # FAIL only well outside the format's cut-rate band
    rows = [  # (name, value, status) status: ok / FIX (soft) / FAIL (hard)
        ("format", ft["name"], "info"),
        ("length (s)", f"{end:.1f} (format {ft['length'][0]}-{ft['length'][1]})",
         "ok" if ft["length"][0] <= end <= ft["length"][1] else "FIX"),
        ("narration wpm", f"{wpm:.0f} (format {ft['wpm'][0]}-{ft['wpm'][1]})"
         + (" (PLACEHOLDER voice: re-check after the real take)" if placeholder else ""),
         "ok" if ft["wpm"][0] <= wpm <= ft["wpm"][1] else ("info" if placeholder else "FIX")),
        ("words in first 15 s", f"{w15} (format {ft['w15'][0]}-{ft['w15'][1]})",
         "ok" if ft["w15"][0] <= w15 <= ft["w15"][1] else "FIX"),
        ("gaps over 0.45 s", str(gaps) if gaps else "none", "ok" if not gaps else "FIX"),
        ("shots", f"{n} ({cpm:.0f}/min, format {ft['cpm'][0]}-{ft['cpm'][1]}/min)", "ok" if cnt_ok else "FAIL"),
        ("average shot (s)", f"{avg:.2f} ({avg * 30:.0f} f, format {ft['avg'][0]}-{ft['avg'][1]})",
         "ok" if ft["avg"][0] <= avg <= ft["avg"][1] else ("FIX" if min(1.3, ft["avg"][0]) <= avg <= max(2.2, ft["avg"][1]) else "FAIL")),
        ("cuts/min vs REF_IG (~30)", f"{cpm:.0f}/min, avg {avg:.2f} s (ref ~2.0 s)",
         "ok" if ft["cpm"][0] <= cpm <= ft["cpm"][1] else "FIX"),
        ("shots over 3.3 s", str(too_long) if too_long else "none", "ok" if not too_long else "FAIL"),
        ("[hold] shots", f"{len(holds)}" + (f" too long: {bad_holds}" if bad_holds else ""),
         "ok" if len(holds) <= 3 and not bad_holds else "FAIL"),
        ("shots under 0.6 s", f"{len(short)} ({len(short) / n:.0%})", "ok" if len(short) / n <= 0.10 else "FAIL"),
        ("words per shot > 9", str(wordy) if wordy else "none",
         "ok" if not wordy else ("FAIL" if very_wordy else "FIX")),
        ("cuts on a phrase", f"{phrase_pct:.0%}", "ok" if phrase_pct >= 0.6 else "FIX"),
        ("prop close-ups", f"{ins:.0%} (target ~28 %)", "ok" if 0.18 <= ins <= 0.38 else "FIX"),
        ("shot types", ", ".join(f"{k} {v}" for k, v in sorted(types.items(), key=lambda x: -x[1])),
         "ok" if len([k for k in types if k != "other"]) >= 5 else "FIX"),
        ("same type back-to-back", f"{repeats:.0%}", "ok" if repeats <= 0.15 else "FIX"),
    ]
    fails = [r for r in rows if r[2] == "FAIL"]
    fixes = [r for r in rows if r[2] == "FIX"]
    if as_json:
        print(json.dumps(dict(rows=rows, shots=[{k: s[k] for k in ("id", "t0", "len", "nw", "type", "hold", "desc")}
                                                 for s in shots]), indent=1))
    else:
        for name, val, st in rows:
            print(f"[{st:4s}] {name:24s} {val}")
        hist = [0] * 5
        for l in lens:
            hist[0 if l < 1 else 1 if l < 1.5 else 2 if l < 2 else 3 if l < 2.5 else 4] += 1
        print("        length histogram  <1.0 {:.0%} | 1-1.5 {:.0%} | 1.5-2 {:.0%} | 2-2.5 {:.0%} | 2.5+ {:.0%}"
              "   (REF1: 11/32/26/21/11 %)".format(*[h / n for h in hist]))
        print("PACING OK" if not fails and not fixes else
              ("PACING FAIL: fix the FAIL items before rendering" if fails else "PACING: soft issues (FIX) above"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], "--json" in sys.argv, sys.argv[2:]))
