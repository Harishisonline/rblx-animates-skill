"""format_preset.py - print the recommended settings for a video format (pure Python, no Blender/network).

    python tools/format_preset.py                     # list formats
    python tools/format_preset.py in_this_town        # full preset (look, bed, wpm, duck, SFX, captions, expressions)
    python tools/format_preset.py horror --json       # machine-readable
    python tools/format_preset.py <slug> --video      # the format of videos/<slug> (story.json "format", else default)

Data lives in docs/FORMATS.json (one source of truth). Other tools import load()/get()/narration()/grade_profile()
from here: pacing.py (--format), hype_lint.py (--format), grade_check.py (--profile / --format), qa_gate.py.
"""
import json, os, sys

STUDIO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(STUDIO, "docs", "FORMATS.json")


def load():
    with open(PATH, encoding="utf-8") as f:
        return json.load(f)


def resolve(name=None, data=None):
    d = data or load()
    n = (name or d["default"]).strip().lower().replace("-", "_").replace(" ", "_")
    n = d.get("aliases", {}).get(n, n)
    if n not in d["formats"]:
        raise KeyError(f"unknown format '{name}'. Known: {', '.join(d['formats'])} (aliases: {', '.join(d.get('aliases', {}))})")
    return n


def get(name=None):
    d = load()
    n = resolve(name, d)
    return n, d["formats"][n]


def narration(name=None):
    return get(name)[1]["narration"]


def grade_profile(profile=None, fmt=None):
    d = load()
    if not profile:
        profile = d["formats"][resolve(fmt, d)]["look"].get("grade_profile", "matte")
    return profile, d["grade_profiles"][profile]


def video_format(slug):
    """format name for videos/<slug>: story.json "format" key, else the default."""
    p = os.path.join(STUDIO, "videos", slug, "story.json")
    try:
        f = json.load(open(p, encoding="utf-8")).get("format")
    except Exception:
        f = None
    try:
        return resolve(f)
    except KeyError:
        return resolve(None)


def fmt_arg(argv, slug=None):
    """--format X from argv, else the video's story.json, else the default."""
    if "--format" in argv:
        return resolve(argv[argv.index("--format") + 1])
    return video_format(slug) if slug else resolve(None)


def _print(n, p):
    print(f"FORMAT {n}: {p.get('what', '')}")
    for k, v in p.items():
        if k == "what":
            continue
        if isinstance(v, dict):
            print(f"  {k}:")
            for kk, vv in v.items():
                print(f"    {kk:22s} {vv}")
        else:
            print(f"  {k:24s} {v}")


def main(argv):
    d = load()
    if not argv or argv[0] in ("-h", "--help", "list"):
        print(__doc__)
        print("formats:", ", ".join(d["formats"]), "| default:", d["default"])
        print("aliases:", ", ".join(f"{a}->{b}" for a, b in d.get("aliases", {}).items()))
        return 0
    name = video_format(argv[0]) if "--video" in argv else argv[0]
    try:
        n = resolve(name, d)
    except KeyError as e:
        print(e); return 2
    p = d["formats"][n]
    if "--json" in argv:
        gp = p["look"].get("grade_profile", "matte")
        print(json.dumps(dict(format=n, preset=p, grade_profile={gp: d["grade_profiles"][gp]}), indent=1))
    else:
        _print(n, p)
        print("  evidence: measured / inferred / UNVERIFIED tags inline; see docs/research/*.md")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
