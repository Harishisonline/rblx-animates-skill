#!/usr/bin/env python3
"""Narration QA gate v6 (2026-11-19): measures a voice take with EARS and compares it with the viral numbers.
Targets: docs/FORMATS.json formats.in_this_world.narration_v3.targets (measured on 4 viral In-this-world Shorts,
16-34M views; every one of them passes these). Run on audio/voice.wav after post.py, BEFORE the voice gate.

usage: ears_check.py <voice.wav|final.mp4|ears.json> [--script script.txt] [--sep] [--save out.json]
  --sep     the audio has music under it (a reference video, a final mix): separate the voice first (demucs)
  --script  also check every script word was spoken (faster-whisper, >= 97 % match)
exit 1 on any FAIL. Prints the long pauses with their words so you can see WHERE the take breaks the flow."""
import difflib, json, os, re, sys

HOME = os.environ.get("RBX_HOME", os.path.expanduser("~/RobloxStories"))
DEFAULT = {  # viral min..max 2026-11-19: wps 4.07-4.41, gap 0.18-0.20, ends>0.3 4-7 %, 0.3-0.6 s 1.9-3.1/min,
             # >0.6 s 0-0.4/min, f0 166-196 Hz, range 12.1-16.8 st, falling 54-74 %, rising 5-15 %
    "wps": [4.05, 4.65], "gap_after_sentence_med": [0.13, 0.24], "sent_ends_paused_over_0.3_max": 0.16,
    "pauses_0.3_0.6_per_min_max": 5.5, "pauses_over_0.6_per_min_max": 0.6, "f0_range_st_min": 11.0,
    "f0_median_hz": [155, 210], "rising_min": 0.05, "falling_max": 0.80, "first_word_s_max": 0.06, "script_match_min": 0.97,
}

def targets():
    try: return {**DEFAULT, **json.load(open(os.path.join(HOME, "docs/FORMATS.json")))["formats"]["in_this_world"]["narration_v3"]["targets"]}
    except Exception: return DEFAULT

def check(m, T, script=None):
    R = []
    def c(ok, sev, msg): R.append(("PASS" if ok else sev, msg))
    def rng(k, sev, label):
        v = m.get(k); lo, hi = T[k]
        c(v is not None and lo <= v <= hi, sev, f"{label} {v} in {lo}-{hi}")
    rng("wps", "FAIL", "pace words/s")
    rng("gap_after_sentence_med", "FAIL", "gap after a full stop (median s)")
    v = m.get("sent_ends_paused_over_0.3"); c(v is not None and v <= T["sent_ends_paused_over_0.3_max"], "FAIL", f"sentence ends with a >0.3 s pause {v} <= {T['sent_ends_paused_over_0.3_max']}")
    v = m.get("pauses_0.3_0.6_per_min"); c(v <= T["pauses_0.3_0.6_per_min_max"], "FAIL", f"0.3-0.6 s pauses per min {v} <= {T['pauses_0.3_0.6_per_min_max']}")
    v = m.get("pauses_over_0.6_per_min"); c(v <= T["pauses_over_0.6_per_min_max"], "FAIL", f">0.6 s pauses per min {v} <= {T['pauses_over_0.6_per_min_max']}")
    v = m.get("f0_range_st_p10_p90"); c(v is not None and v >= T["f0_range_st_min"], "FAIL", f"melody: pitch range {v} st >= {T['f0_range_st_min']} (Adam alone is 8-10 st = 'robotic')")
    rng("f0_median_hz", "WARN", "pitch median Hz (young, bright)")
    v = m.get("sent_end_rising_share"); c(v is not None and v >= T["rising_min"], "WARN", f"rising sentence ends {v} >= {T['rising_min']}")
    v = m.get("sent_end_falling_share"); c(v is not None and v <= T["falling_max"], "WARN", f"falling sentence ends {v} <= {T['falling_max']} ('reading aloud' if higher)")
    v = m.get("first_word_s")
    if v is not None: c(v <= T["first_word_s_max"], "FAIL", f"first word at {v} s <= {T['first_word_s_max']}")
    if script:
        NUM = set("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
                  "seventeen eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety hundred thousand million "
                  "percent".split())
        keep = lambda w: w and not any(ch.isdigit() for ch in w) and w not in NUM   # numbers: digits vs words differ
        sw = [w for w in (re.sub(r"[^a-z0-9]", "", w.lower()) for l in open(script) if not l.startswith("#")
                          for w in re.sub(r"\[[^\]]*\]|\{\w+\}", " ", l).split()) if keep(w)]
        hw = [w for w in (re.sub(r"[^a-z0-9]", "", w["w"].lower()) for w in m.get("words_t", [])) if keep(w)]
        a, b = "".join(sw), "".join(hw)    # compare letters, so "knock-knock"/"knockknock", "street lights" match
        sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
        ratio = sum(x.size for x in sm.get_matching_blocks()) / max(1, len(a))
        miss = [a[i1:i2] for op, i1, i2, j1, j2 in sm.get_opcodes() if op in ("delete", "replace") and i2 - i1 > 3][:8]
        c(ratio >= T["script_match_min"], "FAIL", f"script words spoken {ratio:.1%} >= {T['script_match_min']:.0%} (whisper; check by ear) {miss if ratio < 1 else ''}")
    return R

if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    if not a: print(__doc__); sys.exit(2)
    opt = lambda k: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else None
    src = a[0]
    if src.endswith(".json"): m = json.load(open(src))
    else:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import ears
        m = ears.analyse(src, separate="--sep" in sys.argv)
        json.dump(m, open(opt("--save") or os.path.splitext(src)[0] + ".ears.json", "w"), indent=1)
    R = check(m, targets(), opt("--script"))
    for s, msg in R: print(f"{s:4}  {msg}")
    lp = m.get("long_pause_contexts", [])
    if lp: print("pauses > 0.3 s (word || next word):", *lp[:12], sep="\n   ")
    nf = sum(s == "FAIL" for s, _ in R); print(f"ears_check: {nf} FAIL, {sum(s == 'WARN' for s, _ in R)} WARN  ({m.get('src', src)})")
    sys.exit(1 if nf else 0)
