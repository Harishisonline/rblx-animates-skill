#!/usr/bin/env python3
"""Packaging gate v6 (2026-11-19): YouTube Shorts + Instagram Reels metadata, from what the booming Roblox-story channels
do (yt-dlp, 2026-11-19, last 60 Shorts each of Gneef 2.2M, GreenBroRants 1.47M, ItsBaseplate 1.07M, Ashyyy- 890k,
dripdyl 511k: 3-4-word titles of 13-18 characters, 90-100 % with one emoji, 0 % hashtags or 'In this town' in the title)
and YouTube's own statements (Shorts are ranked on viewed-vs-swiped-away, % viewed, likes, satisfaction; more than 60
hashtags = all ignored). Ours before v6: median 94 characters, 86 % hashtags in the title, a typo ('aughing').

usage: package_check.py <episode dir | package.json>
package.json = {"title": "...", "description": "...", "ig_caption": "...", "pinned_comment": "...", "made_for_kids": false,
                "first_frame": "what frame 0 shows", "playlist": "In This Town"}
exit 1 on any FAIL."""
import json, os, re, sys, unicodedata

EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿⬀-⯿️]")
COMMON_OK = {"roblox", "robloxstory", "robloxanimation", "shorts", "blox", "noob", "obby", "rblx", "lol", "ok", "npc"}

def words_dict():
    for p in ("/usr/share/dict/words", "/usr/dict/words"):
        if os.path.exists(p): return {w.strip().lower() for w in open(p, errors="ignore")}
    return None

def spell(text, D):
    if not D: return []
    bad = []
    for w in re.findall(r"[A-Za-z][a-z']+", text):
        lw = w.lower().strip("'")
        base = re.sub(r"('s|s|es|ed|ing|ly)$", "", lw)
        if lw not in D and base not in D and (lw + "e") not in D and lw not in COMMON_OK: bad.append(w)
    return bad

def check(P):
    R = []; D = words_dict()
    def c(ok, sev, msg): R.append(("PASS" if ok else sev, msg))
    c(D is not None, "WARN", "spelling dictionary found (/usr/share/dict/words) - without it, check spelling by eye")
    t = P.get("title", "").strip()
    tw = re.findall(r"[A-Za-z0-9']+", t); em = EMOJI.findall(t)
    c(bool(t), "FAIL", "title present")
    c(2 <= len(tw) <= 5, "FAIL", f"title {len(tw)} words in 2-5 (booming channels: 3-4)")
    c(len(t) <= 32, "FAIL", f"title {len(t)} characters <= 32 (booming: 13-18; ours were 94)")
    c(len(em) <= 1, "FAIL", f"title emoji {len(em)} <= 1")
    c(len(em) == 1, "WARN", "one emoji in the title (90-100 % of booming titles)")
    c("#" not in t, "FAIL", "no hashtags in the title (they go in the description)")
    c(not re.search(r"\bin this (town|world)\b", t, re.I), "FAIL", "no 'In this town/world' in the title (0 % of booming titles; the video says it)")
    c(not re.search(r"\bpart\s*\d|\bpt\.?\s*\d|roblox (story|animation)", t, re.I), "FAIL", "no 'PART 2' / 'ROBLOX STORY' filler")
    letters = [ch for ch in t if ch.isalpha()]
    c(not letters or sum(ch.isupper() for ch in letters) / len(letters) < 0.6, "FAIL", "not ALL CAPS")
    bad = spell(t, D); c(not bad, "FAIL", f"title spelling {bad}" if bad else "title spelling")
    d = P.get("description", "")
    tags = re.findall(r"#\w+", d)
    first = d.strip().split("\n")[0] if d.strip() else ""
    c(bool(first) and not first.startswith("#"), "FAIL", "description line 1 = a teaser sentence (the rule as a question), not hashtags")
    c(3 <= len(tags) <= 5, "WARN", f"description hashtags {len(tags)} in 3-5")
    c(len(tags) <= 15, "FAIL", f"description hashtags {len(tags)} <= 15 (YouTube ignores all above 60; stuffing reads as spam)")
    c(any(x.lower() in ("#shorts", "#roblox") for x in tags), "WARN", "#roblox or #shorts in the description")
    bad = spell(re.sub(r"#\w+", "", d), D); c(not bad, "WARN", f"description spelling {bad[:8]}" if bad else "description spelling")
    ig = P.get("ig_caption", "")
    if ig:
        it = re.findall(r"#\w+", ig)
        c(3 <= len(it) <= 5, "WARN", f"Instagram hashtags {len(it)} in 3-5 (Instagram's own 2025-26 guidance)")
        c(not ig.strip().startswith("#"), "WARN", "Instagram caption starts with a hook line")
    pc = P.get("pinned_comment", "")
    c(bool(pc) and pc.strip().endswith("?"), "WARN", "pinned comment = one open question about the twist/loophole (comments come from the story)")
    c("made_for_kids" in P, "FAIL", "made-for-kids answered truthfully by the owner (never guessed)")
    c(bool(P.get("first_frame")), "WARN", "first frame written down (the rule visibly happening + first word at 0.0 s)")
    c(bool(P.get("playlist")), "WARN", "playlist set (one per format/series)")
    return R

if __name__ == "__main__":
    if len(sys.argv) < 2: print(__doc__); sys.exit(2)
    p = sys.argv[1]; p = os.path.join(p, "package.json") if os.path.isdir(p) else p
    R = check(json.load(open(p)))
    for s, m in R: print(f"{s:4}  {m}")
    nf = sum(s == "FAIL" for s, _ in R); print(f"package_check: {nf} FAIL, {sum(s == 'WARN' for s, _ in R)} WARN"); sys.exit(1 if nf else 0)
