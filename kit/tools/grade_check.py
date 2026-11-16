"""grade_check.py - measure the colour grade of a render against the REF_IG_Dfe8B5Hs3G6 look spec (no Blender).

  python3 tools/grade_check.py <video.mp4 | folder of stills | still.png> [--fps 1] [--json] [--per-frame]
        [--profile matte|day] [--format NAME]
  Targets come from docs/FORMATS.json grade_profiles (v3.7): matte = REF_IG_Dfe8B5Hs3G6 (default), day = REF_IG_Dfs43n3oWqx
  day exteriors (median ~100, p2 ~38, p98 ~202). --format picks that format's grade_profile.

Decodes with ffmpeg to 108x192 RGB (aspect-agnostic downsample), then per frame:
  B-R (mean blue minus mean red, 8-bit), HSV saturation mean, luma p2 / p50 / p98 (Rec.709).
Targets (look.REF_TARGETS, measured on the reference reel 2026-11-14):
  B-R clip mean -15..+8 on day/interior frames (ref +3; warm shots allowed), no single day frame > +15, night mean <= +12
  sat 0.30 +- 0.06 | p2 17 +- 5 | median 49 +- 12 | p98 124 +- 40
Prints one PASS/FIX line per metric for the whole clip, then the worst frames (cool cast, over-saturated).
The reference itself measures: B-R +3.4, sat 0.30, p2 17, p50 49, p98 124. EP1 v2: B-R -3 mean but +35 on cool shots,
sat 0.60, p2 5.5, p50 83, p98 212.
Exit code 0 = all PASS, 1 = at least one FIX.
"""
import json
import os
import subprocess
import sys

W, H = 108, 192
T = dict(b_minus_r=3.0, b_minus_r_tol=5.0, b_minus_r_night_max=12.0, sat=0.30, sat_tol=0.06,
         p2=17.0, p2_tol=5.0, p50=49.0, p50_tol=12.0, p98=124.0, p98_tol=40.0)
NIGHT_P50 = 30
PROFILE = "matte"


def use_profile(argv):
    """Swap T to a FORMATS.json grade profile (--profile, or --format's look.grade_profile). Falls back to built-ins."""
    global PROFILE, NIGHT_P50
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import format_preset as FP
        prof = argv[argv.index("--profile") + 1] if "--profile" in argv else None
        fmt = argv[argv.index("--format") + 1] if "--format" in argv else None
        PROFILE, g = FP.grade_profile(prof, fmt)
        T.update({k: float(v) for k, v in g.items() if not k.startswith("_") and k != "night_p50"})
        NIGHT_P50 = g.get("night_p50", NIGHT_P50)
    except Exception as e:  # noqa: BLE001
        print(f"(grade_check: FORMATS.json profile not loaded: {e}; using built-in matte targets)")
COOL_FRAME = 15          # any single day/interior frame with B-R above this is listed as a cool-cast frame
IMG = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff")


def decode(src, fps=1.0):
    vf = f"scale={W}:{H}"
    if os.path.isdir(src):
        files = sorted(os.path.join(src, f) for f in os.listdir(src) if f.lower().endswith(IMG))
        frames, names = [], []
        for f in files:
            frames += decode_one(f, vf); names.append(os.path.basename(f))
        return frames, names
    if src.lower().endswith(IMG):
        return decode_one(src, vf), [os.path.basename(src)]
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", src, "-vf", f"fps={fps},{vf}", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    fs = W * H * 3
    frames = [raw[i:i + fs] for i in range(0, len(raw) - fs + 1, fs)]
    return frames, [f"{k / fps:.1f}s" for k in range(len(frames))]


def decode_one(path, vf):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-vf", vf, "-frames:v", "1", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return [raw[:W * H * 3]] if len(raw) >= W * H * 3 else []


def stats(f):
    n = W * H
    r, g, b = f[0::3], f[1::3], f[2::3]
    R, G, B = sum(r) / n, sum(g) / n, sum(b) / n
    sat = 0.0
    L = []
    for i in range(n):
        x, y, z = r[i], g[i], b[i]
        mx = max(x, y, z)
        if mx:
            sat += (mx - min(x, y, z)) / mx
        L.append(0.2126 * x + 0.7152 * y + 0.0722 * z)
    L.sort()
    return dict(R=R, G=G, B=B, bmr=B - R, sat=sat / n, p2=L[n // 50], p50=L[n // 2], p98=L[n * 49 // 50])


def check(rows):
    mean = lambda k, rs=rows: sum(r[k] for r in rs) / max(1, len(rs))
    day = [r for r in rows if r["p50"] >= NIGHT_P50]
    night = [r for r in rows if r["p50"] < NIGHT_P50]
    out = []

    def row(name, val, ok, target):
        out.append(("PASS" if ok else "FIX", name, val, target))

    if day:
        v = mean("bmr", day)
        # whole-clip mean ~+3 like the ref; single warm shots (porch/lamp, B-R -10..-30) are allowed, cool ones are not
        row("B-R day/interior (mean)", round(v, 1), -15.0 <= v <= T["b_minus_r"] + T["b_minus_r_tol"],
            f"-15 .. {T['b_minus_r'] + T['b_minus_r_tol']:+.0f} (ref clip +3)")
        cool = [r for r in day if r["bmr"] > COOL_FRAME]
        row("cool-cast frames (B-R>15)", f"{len(cool)}/{len(day)}", len(cool) <= 0.05 * len(day), "<= 5 %")
    if night:
        v = mean("bmr", night)
        row("B-R night", round(v, 1), v <= T["b_minus_r_night_max"], f"<= {T['b_minus_r_night_max']:+.0f}")
    row("saturation", round(mean("sat"), 3), abs(mean("sat") - T["sat"]) <= T["sat_tol"], f"{T['sat']} +- {T['sat_tol']}")
    row("black p2", round(mean("p2"), 1), abs(mean("p2") - T["p2"]) <= T["p2_tol"], f"{T['p2']:.0f} +- {T['p2_tol']:.0f}")
    row("median p50", round(mean("p50"), 1), abs(mean("p50") - T["p50"]) <= T["p50_tol"], f"{T['p50']:.0f} +- {T['p50_tol']:.0f}")
    row("highlight p98", round(mean("p98"), 1), abs(mean("p98") - T["p98"]) <= T["p98_tol"], f"{T['p98']:.0f} +- {T['p98_tol']:.0f}")
    return out


def hint(name):
    return {"B-R day/interior (mean)": "neutral fill/rim (look.ref_* / cast.LOOK_COOL), shadows=(1,1,1); look.ref(warmth=+0.2)",
            "cool-cast frames (B-R>15)": "those shots use a cool preset or blue practicals: switch to ref_matte/ref_practical",
            "B-R night": "ref_night (grey-slate moon), warm windows; no indigo world colour",
            "saturation": "raise preset desat (ref(desat=...)) or lower sat",
            "black p2": "raise/lower preset lift (ref(lift=...)); low p2 = crushed blacks",
            "median p50": "preset exposure (ref(exposure=...)) / look.exposure()",
            "highlight p98": "lower roll (ref(roll=...)) / smaller practical energy; bloom <= 0.12"}.get(name, "")


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__); return 2
    src = argv[0]
    use_profile(argv)
    fps = float(argv[argv.index("--fps") + 1]) if "--fps" in argv else 1.0
    frames, names = decode(src, fps)
    if not frames:
        print("no frames decoded from", src); return 2
    rows = []
    for nm, f in zip(names, frames):
        s = stats(f); s["at"] = nm; rows.append(s)
    res = check(rows)
    if "--json" in argv:
        print(json.dumps(dict(src=src, frames=len(rows), result=res,
                              per_frame=[{k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items()}
                                         for r in rows] if "--per-frame" in argv else None), indent=1))
    else:
        print(f"grade_check {src}  ({len(rows)} frames @ {fps} fps)  vs profile {PROFILE} (docs/FORMATS.json)")
        for st, name, val, target in res:
            print(f"[{st:4s}] {name:28s} {str(val):>10s}   target {target}" + (f"   -> {hint(name)}" if st == "FIX" else ""))
        worst = sorted((r for r in rows if r["p50"] >= NIGHT_P50), key=lambda r: -r["bmr"])[:5]
        if worst:
            print("coolest day/interior frames:", ", ".join(f"{r['at']} B-R {r['bmr']:+.0f}" for r in worst))
        sat = sorted(rows, key=lambda r: -r["sat"])[:5]
        print("most saturated frames:", ", ".join(f"{r['at']} S {r['sat']:.2f}" for r in sat))
        if "--per-frame" in argv:
            for r in rows:
                print(f"  {r['at']:>8s}  B-R {r['bmr']:+6.1f}  S {r['sat']:.2f}  p2 {r['p2']:5.1f}  p50 {r['p50']:5.1f}  p98 {r['p98']:5.1f}")
    return 0 if all(st == "PASS" for st, *_ in res) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
