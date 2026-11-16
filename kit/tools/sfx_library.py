"""Fetch a free, license-clean SFX library for the real-sfx skill (Kenney audio packs, CC0).
    python tools/sfx_library.py kenney [pack ...]      default: impact-sounds rpg-audio sci-fi-sounds interface-sounds digital-audio ui-audio
Downloads each pack's zip through kenney.nl's own public download endpoint (the same one the Download button uses),
unzips to <workspace>/sfxlib/kenney/<pack>/, appends to assets/ASSETS_LOG.md, and prints the real-sfx commands to register it.
Licence: CC0 1.0 (public domain), credit not required. Real recordings: impact-sounds, rpg-audio (foley). The others are
synthesized UI/sci-fi/digital sounds (use as tier 'extra').  Max 150 MB per pack."""
import io, json, os, sys, urllib.request, http.cookiejar, zipfile, datetime, binascii

STUDIO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "Mozilla/5.0"}
DEFAULT = ["impact-sounds", "rpg-audio", "sci-fi-sounds", "interface-sounds", "digital-audio", "ui-audio"]
REAL = {"impact-sounds", "rpg-audio"}


def fetch_pack(pack):
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    page = f"https://kenney.nl/assets/{pack}"
    op.open(urllib.request.Request(page, headers=UA), timeout=60).read()
    ident = binascii.hexlify(f"assets/{pack}".encode()).decode()
    meta = json.load(op.open(urllib.request.Request("https://kenney.nl/download-link/" + ident,
                                                    headers=dict(UA, Referer=page)), timeout=60))
    url = meta["url"]
    data = op.open(urllib.request.Request(url, headers=UA), timeout=300).read(150 * 1024 * 1024)
    dest = os.path.join(STUDIO, "sfxlib", "kenney", pack)
    os.makedirs(dest, exist_ok=True)
    zipfile.ZipFile(io.BytesIO(data)).extractall(dest)
    n = sum(1 for r, _, fs in os.walk(dest) for f in fs if f.lower().endswith((".wav", ".ogg", ".mp3", ".flac")))
    p = os.path.join(STUDIO, "assets", "ASSETS_LOG.md")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "a", encoding="utf-8").write(f"- {datetime.date.today()} Kenney {pack} audio pack, CC0 1.0 ({n} sounds, {len(data) // 1024} KB): {page}\n")
    print(f"ok {pack}: {n} sounds, {len(data) // 1024} KB -> {dest}")
    return dest


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] != "kenney":
        sys.exit(__doc__)
    for pk in (a[1:] or DEFAULT):
        try:
            fetch_pack(pk)
        except Exception as e:
            print("FAILED", pk, e)
    print("\nRegister with real-sfx (real recordings = main tier, synthesized packs = extra):")
    print(f"  python ~/.claude/skills/real-sfx/scripts/setup.py add-library kenney_real {os.path.join(STUDIO, 'sfxlib', 'kenney')} --tier main --index")
