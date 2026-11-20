#!/usr/bin/env python3
"""Script v3 linter (kit v6.0, 2026-11-19): checks an In-this-town script against the numbers measured on viral
transcripts (Gneef J0OQXSo1chk 34M, RVszt4A-ucc 31M; Baseplate AYdbna6xYrU 19M; VoidCast TAYxdugYgzg 16M) - see
docs/research/SKILL_ENHANCEMENT_PLAN_2026-11-19.md section 3. Thresholds live in docs/FORMATS.json
formats.in_this_world.script_v3 (the weekly growth loop re-measures and may update them).

usage: script_lint_v3.py <script.txt | text file> [--tier full|lite] [--json] [--profile]
  --profile  print the raw metrics only (used by growth_scan.py on viral transcripts)
exit 1 when any FAIL."""
import json, os, re, sys, statistics as stt

HOME = os.environ.get("RBX_HOME", os.path.expanduser("~/RobloxStories"))
NUMW = set("one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen "
           "eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety hundred thousand million billion "
           "half dozen first second third fifth tenth".split())
TITLES = r"(?:Mr|Mrs|Ms|Miss|Dr|Coach|Officer|Mayor|Principal|Grandma|Grandpa|Aunt|Uncle|Sheriff|Captain|Old)"
STOP = set("""I I'm I've I'd I'll In The A An And But So Then When If It It's Its That This These Those There They Their
We Our You Your He She His Her Him My Me Mom Dad Nobody Everyone Everybody Every Some No Not Now One Two Three Ten Until
After Before Because Or Just Even What Who Why How Where Yes Okay OK Ok Night Day Today Tonight Tomorrow Monday Tuesday
Wednesday Thursday Friday Saturday Sunday Like Still Only All Also Right Here Well Oh Hey Wait Run Stop Go Look Most
Last Next Never Ever Once Twice Back Up Down Out On Off Over Under Into Then""".split())
SFXRE = re.compile(r"\b(?:snap|ding|crack|bang|boom|thud|tink|knock|click|beep|pop|whoosh|splat|crash|bonk|zap|buzz|"
                   r"ring|honk|thump|thunk|creak|drip|tick|tock|slam|smash|poof|bzzt|ka-?boom)\b[,!]", re.I)
CLOCK = re.compile(r"\b(\d+|one|two|three|five|ten|twenty|thirty|sixty)\s+(seconds?|minutes?|hours?|days?|nights?)\s+"
                   r"(away|left|until|before|later|to)\b|\bat (midnight|sunset|sunrise|dawn|\d{1,2}(:\d\d)?)\b|\b\d{1,2}:\d\d\b", re.I)
BANNED = ["little did i know", "in a world where", "everything changed", "it was then that", "that's when everything",
          "and that's how", "the moral", "lesson learned", "i learned that", "never judge", "suddenly,", "unbeknownst",
          "like, share", "like and share", "comment below", "smash that", "subscribe for"]

def sentences(text):
    t = re.sub(r"\[[^\]]*\]", " ", text)                    # drop SFX / tag marks
    t = re.sub(r"\s+", " ", t).strip()
    parts = re.split(r'(?<=[.!?])["”]?\s+', t)
    return [p.strip() for p in parts if re.search(r"[A-Za-z0-9]", p)]

def words(s): return re.findall(r"[A-Za-z0-9][A-Za-z0-9'’:-]*", s)

def metrics(text):
    S = sentences(text); W = [w for s in S for w in words(s)]
    lens = [len(words(s)) for s in S]
    names = set()
    for s in S:
        ws = words(s)
        for i, w in enumerate(ws):
            if i == 0 or not w[0].isupper() or w in STOP or w.isupper() and len(w) > 1: continue
            names.add(w.strip("'’s"))
        for m in re.finditer(TITLES + r"\.?\s+[A-Z][a-z]+", s): names.add(m.group(0))
    nums = [w for w in W if re.fullmatch(r"\d[\d,.:%]*", w) or w.lower() in NUMW]
    low = text.lower()
    quotes = re.findall(r'["“][^"”]{2,120}["”]', text)
    conn = sum(1 for w in W if w.lower() in ("and", "so", "but", "because", "then"))
    return {
        "words": len(W), "sentences": len(S),
        "sent_len_median": stt.median(lens) if lens else 0,
        "short_sent_share_le3": round(sum(l <= 3 for l in lens) / max(1, len(lens)), 2),
        "long_sent_share_ge15": round(sum(l >= 15 for l in lens) / max(1, len(lens)), 2),
        "names_distinct": len(names), "names": sorted(names)[:30],
        "numbers": len(nums), "numbers_per_100w": round(100 * len(nums) / max(1, len(W)), 1),
        "quotes": len(quotes),
        "sfx_words": len(SFXRE.findall(text)),
        "clock_marks": len(CLOCK.findall(text)),
        "connectors_per_100w": round(100 * conn / max(1, len(W)), 1),
        "questions": sum(s.endswith("?") for s in S),
        "you_see": int(bool(re.search(r"\byou see\b", low))),
        "me_question": int(bool(re.search(r"\b(and )?me\?", low))),
        "rule_recap": int(bool(re.search(r"\bthe rule(s)? (is|are|was|were) simple\b|\bthe rule is\b", low))),
        "then_one_night": int(bool(re.search(r"\b(then|until)\s*,?\s*one (night|day|morning)|\blast (friday|monday|tuesday|"
                                              r"wednesday|thursday|saturday|sunday|night|week)\b", low))),
        "first_sentence": S[0] if S else "",
        "last_sentence": S[-1] if S else "",
        "banned_hits": [b for b in BANNED if b in low],
    }

def targets():
    try:
        return json.load(open(os.path.join(HOME, "docs/FORMATS.json")))["formats"]["in_this_world"]["script_v3"]
    except Exception:
        return DEFAULT_T

DEFAULT_T = {   # measured 2026-11-19 on the 4 viral transcripts (min..max), widened slightly. Viral: 549-708 words,
    # names 2-9, numbers 2.3-4.0/100w, clock 1-4, fragments 19-41 %, connectors 3.9-6.7/100w, median sentence 4-8 words,
    # 4/4 have a 'Then one night / Last Friday' trigger, 3/4 'You see' or 'The rule is simple', 3/4 'Me?' or 'My name is'.
    # dripdyl In-this-town outliers (growth_scan 2026-11-19, 6.0-7.8M): 552-594 words, fragments 9-11 %, 15+-word
    # sentences 19-22 %, connectors 4.5-5.4/100w, 'You see' 2/2, 'Then one night' 2/2.
    # Ours (EP3/EP4/LCY): 343-358 words, connectors 2.3-5.0, fragments 30-48 %, 0/3 triggers, 1/3 'Me?'.
    "words": {"full": [450, 720], "lite": [250, 340]},
    "names_distinct_min": 1, "numbers_per_100w_min": 2.0, "quotes": [1, 6], "sfx_words_min": 1, "clock_marks_min": 1,
    "short_sent_share_le3_max": 0.42, "long_sent_share_ge15_max": 0.25, "connectors_per_100w_min": 3.8,
    "sent_len_median": [4, 9], "wps_plan": 4.35,
}

def lint(text, tier="full", fmt="in_this_world"):
    m = metrics(text); T = targets(); R = []
    def chk(ok, sev, msg): R.append(("PASS" if ok else sev, msg))
    lo, hi = T["words"][tier]
    chk(lo <= m["words"] <= hi, "FAIL", f"words {m['words']} in {lo}-{hi} ({tier}); runtime ~{m['words'] / T['wps_plan']:.0f} s at {T['wps_plan']} w/s")
    fs = m["first_sentence"].lower()
    chk(bool(re.match(r"in this (town|world|city|school|family|house)", fs)) or fmt != "in_this_world", "FAIL",
        f"sentence 1 states the rule ('In this town/world, ...'): \"{m['first_sentence'][:80]}\"")
    chk(len(words(m["first_sentence"])) <= 16, "WARN", f"sentence 1 is {len(words(m['first_sentence']))} words (viral 9-14)")
    chk(m["you_see"] or m["rule_recap"], "WARN", "mechanics opener: 'You see,' after the rule and/or 'The rule is simple.' (3 of 4 viral)")
    chk(m["me_question"] or re.search(r"\bmy name is\b", text.lower()), "WARN", "narrator intro: 'Me? I'm [age], and [my number/flaw].' or 'My name is X, and ...'")
    chk(m["then_one_night"], "FAIL", "trigger: 'Then one night, ...' / 'Last Friday, at sunset, ...'")
    chk(m["names_distinct"] >= T["names_distinct_min"], "WARN", f"named people/places {m['names_distinct']} >= {T['names_distinct_min']} ({', '.join(m['names'][:8])})")
    chk(m["numbers_per_100w"] >= T["numbers_per_100w_min"], "WARN", f"exact numbers {m['numbers']} ({m['numbers_per_100w']}/100 words) >= {T['numbers_per_100w_min']}/100")
    qlo, qhi = T["quotes"]
    chk(qlo <= m["quotes"] <= qhi, "WARN", f"short quoted lines {m['quotes']} in {qlo}-{qhi} (in character voices, VOICE_SPEC v6)")
    chk(m["sfx_words"] >= T["sfx_words_min"], "WARN", f"inline sound words ('Snap!', 'Ding!', 'Tink, tink') {m['sfx_words']} >= {T['sfx_words_min']}")
    chk(m["clock_marks"] >= T["clock_marks_min"], "FAIL", f"a clock ('20 minutes away', 'at midnight', '11:59') {m['clock_marks']} >= {T['clock_marks_min']}")
    chk(m["short_sent_share_le3"] <= T["short_sent_share_le3_max"], "WARN", f"1-3-word fragments {m['short_sent_share_le3']:.0%} <= {T['short_sent_share_le3_max']:.0%} (fragments only for lists, SFX and punch lines)")
    chk(m["long_sent_share_ge15"] <= T["long_sent_share_ge15_max"], "WARN", f"15+-word sentences {m['long_sent_share_ge15']:.0%} <= {T['long_sent_share_ge15_max']:.0%}")
    chk(m["connectors_per_100w"] >= T["connectors_per_100w_min"], "WARN", f"and/so/but/then/because {m['connectors_per_100w']}/100 words >= {T['connectors_per_100w_min']} (flowing, told-to-a-friend sentences)")
    a, b = T["sent_len_median"]
    chk(a <= m["sent_len_median"] <= b, "WARN", f"median sentence {m['sent_len_median']} words in {a}-{b}")
    chk(not m["banned_hits"], "FAIL", f"AI-slop / CTA phrases: {m['banned_hits']}")
    chk(len(words(m["last_sentence"])) <= 14, "WARN", f"last line {len(words(m['last_sentence']))} words (a 3-12-word wry callback/twist, then cut)")
    return m, R

if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    if not a: print(__doc__); sys.exit(2)
    text = "\n".join(l for l in open(a[0]) if not l.startswith("#"))
    if "--profile" in sys.argv:
        print(json.dumps(metrics(text), indent=1)); sys.exit(0)
    tier = "lite" if "--tier" in sys.argv and sys.argv[sys.argv.index("--tier") + 1] == "lite" else "full"
    m, R = lint(text, tier)
    if "--json" in sys.argv:
        print(json.dumps({"metrics": m, "checks": R}, indent=1))
    else:
        for s, msg in R: print(f"{s:4}  {msg}")
    nf = sum(s == "FAIL" for s, _ in R); nw = sum(s == "WARN" for s, _ in R)
    print(f"script_lint_v3: {nf} FAIL, {nw} WARN")
    sys.exit(1 if nf else 0)
