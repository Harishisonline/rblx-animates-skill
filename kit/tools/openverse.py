"""Find and fetch license-clean real SFX from Openverse (api.openverse.org; mostly Freesound uploads) to fill library gaps.
    python tools/openverse.py search "<query>" [--n 8] [--max-dur 12]        list candidates (no download)
    python tools/openverse.py fetch  "<query>" [--n 3] [--max-dur 12] [--label NAME] [--allow-by]
    python tools/openverse.py gaps                                          fetch a starter set for the usual gaps
Default licences: CC0 and public domain only (no credit needed). --allow-by also accepts CC-BY (credit REQUIRED: it is written to
sfxlib/openverse/ATTRIBUTION.md, put those lines in the video description). Never NC/ND/SA.
Files go to <workspace>/sfxlib/openverse/<label>/ ; register once with:
    python ~/.claude/skills/real-sfx/scripts/setup.py add-library openverse <workspace>/sfxlib/openverse --tier main --index
Anonymous API limits apply (the tool waits between calls). The category filter is unreliable on Openverse: use query words."""
import json, os, sys, time, urllib.parse, urllib.request, datetime, re

STUDIO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "roblox-story-kit/2 (personal video tool)"}
API = "https://api.openverse.org/v1/audio/"
OK_EXT = {"mp3", "wav", "ogg", "flac", "m4a"}
GAPS = {"whoosh": "whoosh", "swoosh": "swoosh fast", "riser": "riser build up", "impact_boom": "cinematic boom impact",
        "crowd_cheer": "crowd cheering", "crowd_panic": "crowd screaming panic", "city_night": "city night ambience",
        "room_tone": "room tone ambience", "drone_hum": "drone propeller hum", "servo": "servo motor robot",
        "robot_beep": "robot beep", "alarm": "alarm siren", "laser": "laser zap", "glitch": "digital glitch",
        "spark": "electric spark zap", "door_slam": "door slam", "footsteps": "footsteps concrete", "thunder": "thunder",
        "glass_break": "glass break", "heartbeat": "heartbeat", "power_down": "power down shutdown", "power_up": "power up"}


def get(url, tries=4):
    for i in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
        except Exception as e:
            if "429" in str(e):
                time.sleep(20 * (i + 1))
                continue
            if i == tries - 1:
                raise
            time.sleep(3)


def search(q, n=8, max_dur=12.0, allow_by=False):
    lic = "cc0,pdm" + (",by" if allow_by else "")
    url = API + "?" + urllib.parse.urlencode({"q": q, "license": lic, "page_size": 20})
    d = json.loads(get(url))
    out = []
    for r in d.get("results", []):
        dur = (r.get("duration") or 0) / 1000.0
        ext = (r.get("filetype") or "").lower()
        if not r.get("url") or ext not in OK_EXT or dur <= 0.15 or dur > max_dur:
            continue
        out.append(dict(id=r["id"], title=r.get("title") or "", creator=r.get("creator") or "unknown", license=r["license"],
                        version=r.get("license_version") or "", dur=dur, ext=ext, url=r["url"], page=r.get("foreign_landing_url") or ""))
        if len(out) >= n:
            break
    return out


def fetch(q, n=3, max_dur=12.0, label=None, allow_by=False):
    label = label or re.sub(r"\W+", "_", q.lower()).strip("_")
    dest = os.path.join(STUDIO, "sfxlib", "openverse", label)
    os.makedirs(dest, exist_ok=True)
    got = 0
    for r in search(q, min(n * 4, 20), max_dur, allow_by):
        if got >= n:
            break
        fn = os.path.join(dest, f"{label}_{r['id'][:8]}.{r['ext']}")
        try:
            data = get(r["url"])
        except Exception as e:
            print("  skip", r["title"][:30], e)
            continue
        if len(data) > 4 * 1024 * 1024:
            continue
        open(fn, "wb").write(data)
        got += 1
        line = f"{label}/{os.path.basename(fn)} | {r['title']} | by {r['creator']} | {r['license'].upper()} {r['version']} | {r['page']}"
        open(os.path.join(STUDIO, "sfxlib", "openverse", "ATTRIBUTION.md"), "a", encoding="utf-8").write(f"- {line}\n")
        print("  ok", line[:140])
    return got


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    opt = {a[i]: a[i + 1] for i in range(len(a) - 1) if a[i].startswith("--") and a[i] not in ("--allow-by",)}
    by = "--allow-by" in a
    n, md = int(opt.get("--n", 3)), float(opt.get("--max-dur", 12))
    if a[0] == "search":
        for r in search(a[1], int(opt.get("--n", 8)), md, by):
            print(f"{r['dur']:5.1f}s {r['ext']:4s} {r['license'].upper():4s} {r['title'][:50]:50s} by {r['creator'][:20]} {r['page']}")
    elif a[0] == "fetch":
        print("fetched", fetch(a[1], n, md, opt.get("--label"), by))
    elif a[0] == "gaps":
        tot = 0
        for label, q in GAPS.items():
            print(label, "<-", q)
            tot += fetch(q, 2, md, label, False)
            time.sleep(2)
        print("total files:", tot)
    else:
        print(__doc__)
