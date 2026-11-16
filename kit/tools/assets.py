"""Fetch license-clean assets into the workspace (assets/hdri, assets/fonts, assets/models). Free, no account.
    python tools/assets.py hdri <id> [...]      Poly Haven HDRI (CC0), 1k .hdr  -> assets/hdri/<id>_1k.hdr
    python tools/assets.py hdri-list [query]    list Poly Haven HDRI ids (optionally filter by words in the id)
    python tools/assets.py fonts                Poppins ExtraBold + Bangers (SIL OFL) -> assets/fonts
    python tools/assets.py starter              the default starter set (a few night/city/interior HDRIs + fonts)
Poly Haven asks for a descriptive User-Agent. Everything fetched is logged to assets/ASSETS_LOG.md with its licence.
Quaternius/Kenney packs are CC0 but have no stable direct-download API: see assets/ASSETS.md for the page URLs
(download once by hand, unzip into assets/models/<pack>/, then import with rbx/props2 helpers or bpy.ops.import_scene.gltf)."""
import json, os, sys, urllib.request, datetime

STUDIO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "roblox-story-kit/2 (personal video tool; contact: local user)"}
STARTER_HDRI = ["dresden_station_night", "modern_buildings_night", "boiler_room", "kloofendal_48d_partly_cloudy_puresky",
                "industrial_sunset_02_puresky", "empty_warehouse_01"]
FONTS = {
    "Poppins-ExtraBold.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/poppins/Poppins-ExtraBold.ttf",
    "Bangers-Regular.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/bangers/Bangers-Regular.ttf",
}


def get(url, binary=True):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r:
        d = r.read()
    return d if binary else json.loads(d)


def log(line):
    p = os.path.join(STUDIO, "assets", "ASSETS_LOG.md")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "a", encoding="utf-8").write(f"- {datetime.date.today()} {line}\n")


def hdri(aid, res="1k"):
    files = get(f"https://api.polyhaven.com/files/{aid}", False)
    url = files["hdri"][res]["hdr"]["url"]
    out = os.path.join(STUDIO, "assets", "hdri", f"{aid}_{res}.hdr")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if not os.path.exists(out):
        open(out, "wb").write(get(url))
    log(f"HDRI {aid} ({res}) from Poly Haven, CC0: {url}")
    print("ok", out, os.path.getsize(out) // 1024, "KB")


def fonts():
    d = os.path.join(STUDIO, "assets", "fonts")
    os.makedirs(d, exist_ok=True)
    for n, u in FONTS.items():
        p = os.path.join(d, n)
        if not os.path.exists(p):
            open(p, "wb").write(get(u))
        log(f"font {n} (SIL OFL 1.1) from Google Fonts repo: {u}")
        print("ok", p)


if __name__ == "__main__":
    a = sys.argv[1:] or ["-h"]
    if a[0] == "hdri":
        for i in a[1:]:
            try:
                hdri(i)
            except Exception as e:
                print("FAILED", i, e)
    elif a[0] == "hdri-list":
        ids = list(get("https://api.polyhaven.com/assets?t=hdris", False))
        q = [w.lower() for w in a[1:]]
        for i in ids:
            if all(w in i.lower() for w in q):
                print(i)
    elif a[0] == "fonts":
        fonts()
    elif a[0] == "starter":
        fonts()
        for i in STARTER_HDRI:
            try:
                hdri(i)
            except Exception as e:
                print("FAILED", i, e)
    else:
        print(__doc__)
