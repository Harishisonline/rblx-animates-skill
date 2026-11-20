#!/usr/bin/env python3
"""Weekly self-learning scan (kit v6.0, 2026-11-19). Measures our channel and the booming Roblox-story channels with
yt-dlp (public data only, no downloads unless --ears), finds outliers, profiles their titles and scripts, re-measures
our latest narration, and writes a ranked GAP LIST that the weekly growth-loop run turns into rules, experiments and
skill updates (docs/GROWTH_LOOP.md section 9 "self-learning loop").

usage: growth_scan.py [--quick] [--ears] [--discover] [--out DIR]
  --quick     listings only (no per-video metadata or transcripts)
  --discover  also search YouTube for new outliers (adds candidates to research/growth/roster.json as "candidate")
  --ears      try to download the top 2 outlier audios and measure the narration (YouTube may bot-block; then skipped)
writes ~/RobloxStories_tmp/research/growth/<date>/scan.json + GAPS.md, appends our Shorts to docs/CHANNEL_LOG.md.
Never invents a number: anything that failed to load is reported as n/a with the reason."""
import datetime as dt, json, os, re, statistics as stt, subprocess, sys, time

HOME = os.environ.get("RBX_HOME", os.path.expanduser("~/RobloxStories"))
sys.path.insert(0, os.path.join(HOME, "tools"))
ENV = dict(os.environ, PATH="/opt/homebrew/bin:/usr/local/bin:" + os.path.expanduser("~/.local/bin:") + os.environ.get("PATH", ""))
TODAY = dt.date.today().isoformat()
GROWTH = os.environ.get("RBX_GROWTH", os.path.expanduser("~/RobloxStories_tmp/research/growth"))   # local disk (research/ is a Drive link)
OUT = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else os.path.join(GROWTH, TODAY)
ROSTER_P = os.path.join(GROWTH, "roster.json")
OURS = "rblxanimates"
DEFAULT_ROSTER = {"ceiling": ["Gneef", "GreenBroRants", "ItsBaseplate", "Ashyyy-", "GeloStories98", "UnluckyGuyStories",
                              "Noobifiedd", "dripdyl", "VoidCastRants", "butterbloxe"],
                  "peers": ["itsRedBear", "FriendBobN1"], "candidate": []}
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿⬀-⯿]")
LOG = []

def ytdlp(args, timeout=240):
    try:
        p = subprocess.run(["yt-dlp", "--no-warnings", *args], capture_output=True, text=True, timeout=timeout, env=ENV)
        if p.returncode != 0: LOG.append(f"yt-dlp {' '.join(args[-1:])}: {p.stderr.strip().splitlines()[-1:] if p.stderr else p.returncode}")
        return p.stdout
    except Exception as ex:
        LOG.append(f"yt-dlp {' '.join(args[-1:])}: {ex}"); return ""

def listing(handle, n=60):
    out = ytdlp(["--flat-playlist", "-J", "--playlist-end", str(n), "--extractor-args", "youtubetab:approximate_date",
                 f"https://www.youtube.com/@{handle}/shorts"])
    try: return json.loads(out)
    except Exception: return None

def title_stats(titles):
    if not titles: return {}
    f = lambda pred: round(sum(1 for t in titles if pred(t)) / len(titles), 2)
    return {"n": len(titles), "chars_median": stt.median(len(t) for t in titles),
            "words_median": stt.median(len(re.findall(r"[A-Za-z0-9']+", t)) for t in titles),
            "emoji_share": f(lambda t: bool(EMOJI.search(t))), "hashtag_share": f(lambda t: "#" in t),
            "in_this_share": f(lambda t: bool(re.search(r"in this (town|world)", t, re.I))),
            "caps_share": f(lambda t: (lambda L: bool(L) and sum(c.isupper() for c in L) / len(L) > 0.6)([c for c in t if c.isalpha()]))}

def channel(handle):
    d = listing(handle)
    if not d: return {"handle": handle, "error": "listing failed (see log)"}
    E = [e for e in d.get("entries", []) if e.get("view_count") is not None]
    v = sorted(e["view_count"] for e in E)
    med = stt.median(v) if v else 0
    per_week = None      # shorts listings carry no dates: read the 6 newest Shorts' upload dates (skipped with --quick)
    if "--quick" not in sys.argv and len(E) >= 2:
        ds = []
        for e in E[:6]:
            u = video_meta(e["id"]).get("upload_date"); time.sleep(2)
            if u: ds.append(dt.datetime.strptime(u, "%Y%m%d"))
        if len(ds) >= 2:
            span = max(1, (max(ds) - min(ds)).days)
            per_week = round((len(ds) - 1) / span * 7, 1)
    outl = sorted(({"id": e["id"], "title": e.get("title", ""), "views": e["view_count"],
                    "outlier": round(e["view_count"] / med, 1) if med else None} for e in E), key=lambda x: -x["views"])[:5]
    return {"handle": handle, "subs": d.get("channel_follower_count"), "shorts_listed": len(E), "median_views": med,
            "hit_100k": round(sum(x >= 1e5 for x in v) / max(1, len(v)), 2), "hit_1m": round(sum(x >= 1e6 for x in v) / max(1, len(v)), 2),
            "uploads_per_week_newest6": per_week, "titles": title_stats([e.get("title", "") for e in E]), "top": outl}

def video_meta(vid):
    out = ytdlp(["--skip-download", "-J", f"https://www.youtube.com/watch?v={vid}"])
    try:
        j = json.loads(out)
        return {k: j.get(k) for k in ("id", "title", "view_count", "like_count", "comment_count", "duration", "upload_date",
                                      "channel_follower_count", "tags")} | {"desc_hashtags": len(re.findall(r"#\w+", j.get("description") or ""))}
    except Exception: return {"id": vid, "error": "metadata failed"}

def transcript(vid, workdir):
    os.makedirs(workdir, exist_ok=True)
    ytdlp(["--skip-download", "--write-auto-subs", "--sub-langs", "en.*", "--sub-format", "json3", "-o", f"{workdir}/%(id)s.%(ext)s",
           f"https://www.youtube.com/watch?v={vid}"])
    fs = [f for f in os.listdir(workdir) if f.startswith(vid) and f.endswith(".json3")]
    if not fs: return None
    j = json.load(open(os.path.join(workdir, fs[0])))
    txt = " ".join(s.get("utf8", "") for ev in j.get("events", []) for s in ev.get("segs", []) or [])
    return re.sub(r"\s+", " ", txt).strip()

def main():
    os.makedirs(OUT, exist_ok=True)
    roster = json.load(open(ROSTER_P)) if os.path.exists(ROSTER_P) else DEFAULT_ROSTER
    os.makedirs(os.path.dirname(ROSTER_P), exist_ok=True)
    R = {"date": TODAY, "channels": {}, "ours": {}, "viral_scripts": {}, "ears": {}, "log": LOG}
    for grp in ("ceiling", "peers", "candidate"):
        for h in roster.get(grp, []):
            R["channels"][h] = channel(h) | {"group": grp}; time.sleep(4)
    o = channel(OURS); R["ours"] = o
    if "--quick" not in sys.argv and "error" not in o:
        d = listing(OURS, 100) or {}
        R["ours"]["videos"] = [video_meta(e["id"]) for e in d.get("entries", [])[:30] if not time.sleep(3)]
    # top outliers across the ceiling + peers (the mechanism to study this week)
    tops = sorted((t | {"channel": h} for h, c in R["channels"].items() if "top" in c for t in c["top"]
                   if t.get("outlier") and t["outlier"] >= 3), key=lambda x: -x["views"])[:8]
    R["top_outliers"] = tops
    if "--quick" not in sys.argv:
        import script_lint_v3 as SL
        for t in tops[:4]:
            tx = transcript(t["id"], os.path.join(OUT, "subs")); time.sleep(8)
            R["viral_scripts"][t["id"]] = ({"channel": t["channel"], "views": t["views"], "metrics": SL.metrics(tx)}
                                           if tx else {"channel": t["channel"], "error": "no transcript (429/bot check?)"})
    if "--discover" in sys.argv:
        found = {}
        for q in ("roblox story in this town", "roblox animation story", "in this world roblox", "roblox story shorts"):
            out = ytdlp(["--flat-playlist", "-J", f"ytsearchdate40:{q}"])
            try: E = json.loads(out).get("entries", [])
            except Exception: E = []
            for e in E:
                if (e.get("view_count") or 0) >= 300000 and e.get("channel"):
                    found.setdefault(e.get("uploader_id") or e.get("channel"), []).append({"id": e["id"], "views": e["view_count"], "title": e.get("title")})
            time.sleep(5)
        known = {h.lower() for g in roster.values() for h in g} | {OURS}
        new = [h.lstrip("@") for h in found if h and h.lstrip("@").lower() not in known][:5]
        roster.setdefault("candidate", []).extend(new); R["discovered"] = {h: found.get(h) or found.get("@" + h) for h in new}
        json.dump(roster, open(ROSTER_P, "w"), indent=1)
    elif not os.path.exists(ROSTER_P):
        json.dump(roster, open(ROSTER_P, "w"), indent=1)
    if "--ears" in sys.argv:
        try:
            import ears
            for t in tops[:2]:
                ad = os.path.join(OUT, "audio"); os.makedirs(ad, exist_ok=True)
                ytdlp(["-f", "bestaudio", "-o", f"{ad}/%(id)s.%(ext)s", f"https://www.youtube.com/watch?v={t['id']}"], timeout=300)
                fs = [f for f in os.listdir(ad) if f.startswith(t["id"]) and not f.endswith(".part")]
                if fs:
                    m = ears.analyse(os.path.join(ad, fs[0]), separate=True)
                    R["ears"][t["id"]] = {k: v for k, v in m.items() if k not in ("sentences", "words_t", "transcript")}
                else: R["ears"][t["id"]] = "download blocked (YouTube bot check) - see log"
                time.sleep(20)
        except Exception as ex: R["ears"]["error"] = str(ex)
    json.dump(R, open(os.path.join(OUT, "scan.json"), "w"), indent=1)
    write_gaps(R); log_ours(R)
    print("scan written", OUT)

def write_gaps(R):
    C = [c for c in R["channels"].values() if "titles" in c and c.get("group") == "ceiling" and c["titles"]]
    o = R["ours"]; ot = o.get("titles", {}) or {}
    med = lambda k, src=C: stt.median([c["titles"][k] for c in src]) if src else None
    rows = []
    def gap(name, ours, theirs, fix, weight, level="observed"):
        rows.append((weight, name, ours, theirs, fix, level))
    if C and ot:
        gap("title length (chars, median)", ot.get("chars_median"), med("chars_median"), "2-4 words + 1 emoji (package_check.py)", 3)
        gap("hashtags in title (share)", ot.get("hashtag_share"), med("hashtag_share"), "hashtags only in the description", 3)
        gap("emoji in title (share)", ot.get("emoji_share"), med("emoji_share"), "one emoji per title", 2)
        gap("'In this town' in title (share)", ot.get("in_this_share"), med("in_this_share"), "the video says it, the title names the object", 2)
    vw = [c.get("median_views") for c in C if c.get("median_views")]
    gap("median views per Short", o.get("median_views"), stt.median(vw) if vw else None, "the sum of every other gap; check YouTube Studio 'viewed vs swiped away'", 5)
    up = [c.get("uploads_per_week_newest6") for c in C if c.get("uploads_per_week_newest6")]
    gap("uploads per week (from the 6 newest Shorts)", o.get("uploads_per_week_newest6"), stt.median(up) if up else None, "lite tier + overnight render queue", 4)
    vs = [v["metrics"] for v in R["viral_scripts"].values() if "metrics" in v]
    if vs:
        for k, fix in (("words", "script length (script_lint_v3)"), ("connectors_per_100w", "flowing and/so/but sentences"),
                       ("short_sent_share_le3", "fewer fragments"), ("then_one_night", "a 'Then one night' trigger")):
            gap(f"viral script {k} (this week's outliers, median)", "see ours in script_lint_v3", stt.median([m[k] for m in vs]), fix, 2, "measured")
    rows.sort(key=lambda r: -r[0])
    L = [f"# Growth scan {R['date']} - gap list (auto-generated by tools/growth_scan.py; numbers from yt-dlp, n/a = not loaded)", "",
         f"Ours @{OURS}: subs {o.get('subs')}, Shorts listed {o.get('shorts_listed')}, median views {o.get('median_views')}, "
         f"hit 100k {o.get('hit_100k')}", "", "| weight | gap | ours | booming median | fix | level |", "|---|---|---|---|---|---|"]
    L += [f"| {w} | {n} | {a} | {b} | {f} | {lv} |" for w, n, a, b, f, lv in rows]
    L += ["", "## Top outliers this week (study the mechanism, never copy)", "", "| channel | id | views | x median | title |", "|---|---|---|---|---|"]
    L += [f"| {t['channel']} | {t['id']} | {t['views']:,} | {t['outlier']} | {t['title']} |" for t in R.get("top_outliers", [])]
    if R.get("discovered"): L += ["", "## New candidate channels (added to roster.json as 'candidate')", ""] + [f"- @{h}: {v}" for h, v in R["discovered"].items()]
    if LOG: L += ["", "## Load problems (numbers missing because of these)", ""] + [f"- {x}" for x in LOG[:30]]
    open(os.path.join(OUT, "GAPS.md"), "w").write("\n".join(L) + "\n")

def log_ours(R):
    p = os.path.join(HOME, "docs", "CHANNEL_LOG.md")
    vids = [v for v in R["ours"].get("videos", []) if "error" not in v]
    if not vids: return
    new = not os.path.exists(p)
    with open(p, "a") as f:
        if new: f.write("# CHANNEL_LOG (append-only; growth_scan.py rows are yt-dlp public numbers)\n\n"
                        "| scan date | id | upload | title | dur s | views | likes | comments |\n|---|---|---|---|---|---|---|---|\n")
        for v in vids:
            f.write(f"| {R['date']} | {v['id']} | {v.get('upload_date')} | {(v.get('title') or '')[:60]} | {v.get('duration')} | "
                    f"{v.get('view_count')} | {v.get('like_count')} | {v.get('comment_count')} |\n")

if __name__ == "__main__":
    main()
