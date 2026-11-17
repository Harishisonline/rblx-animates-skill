"""Per-video shot framework (runs inside Blender).
In videos/<slug>/shots.py:

    from shotkit import *
    V = Video(__file__)
    @V.shot(1, V.w(0), V.w(8), "Eddie sprinting, a runner glued to his back")
    def s01():
        ...build the set, characters, camera; sfx(t, "whoosh")...

Shot times come from the voice timing (audio/words.json), by SCRIPT WORD INDEX, so regenerating
the voice never breaks the edit. V.w(i) = start of word i, V.find("cliff") = index of a word.
The last shot should end at V.end (audio length)."""
import json, os, re, sys
import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.dirname(HERE)
if STUDIO not in sys.path:
    sys.path.insert(0, STUDIO)
import rbx


def _assets_readable(p, timeout=4.0):
    """EP4 2026-11-16: Google Drive (assets symlink) can hang every file READ (listing still works) -> Blender froze
    for ever in an image mmap. Probe one small read in a daemon thread with a timeout."""
    import threading
    out = {}

    probes = ("faces/harry_eyes.png", "tex/pbr/planks/diff.jpg", "tex/pbr/plaster/diff.jpg", "tex/pbr/concrete/diff.jpg")

    def rd():
        try:
            for q in probes:                     # some files can be cached, others hang: probe a few (faces + pbr)
                with open(os.path.join(p, q), "rb") as f:
                    f.seek(-4096, 2); out["n"] = out.get("n", 0) + len(f.read(4096))
        except Exception as e:
            out["e"] = repr(e)
        out["done"] = True
    th = threading.Thread(target=rd, daemon=True); th.start(); th.join(timeout)
    return bool(out.get("done")) and out.get("n", 0) > 0 and "e" not in out


_ASSETS = os.environ.get("RBX_ASSETS") or os.path.join(STUDIO, "assets")
rbx.ASSETS_FALLBACK = False
if not os.environ.get("RBX_ASSETS") and not _assets_readable(_ASSETS):
    _TMP = os.path.join(os.path.dirname(STUDIO), "RobloxStories_tmp")
    for _LOCAL in (os.environ.get("RBX_ASSETS_FALLBACK", ""), os.path.join(_TMP, "kit_assets_local"),
                   os.path.join(_TMP, "rblx-animates-skill", "kit", "assets")):
        if _LOCAL and os.path.isdir(_LOCAL):
            _pbr = os.path.exists(os.path.join(_LOCAL, "tex", "pbr", "planks", "diff.jpg"))
            print("SHOTKIT WARNING: kit assets unreadable (Google Drive stuck?) -> LOCAL FALLBACK", _LOCAL,
                  "(PBR textures present: same CC0 Poly Haven set)" if _pbr else "(NO PBR textures = flat colours: lo-res only)")
            _ASSETS = _LOCAL; rbx.ASSETS_FALLBACK = "pbr" if _pbr else True
            break
rbx.ASSETS = _ASSETS
from rbx.core import *          # noqa: F401,F403  (reset, setup_render, Cam, mat, box, light, sfx, ...)
from rbx import core, chars, sets, locs, fx, acting, world as W, world2 as W2   # noqa: F401
from rbx import look, cams, props2 as P
from rbx import aiworld as A   # noqa: F401  (v2.1 sci-fi sets, robots, particles)
from rbx import look as _lookmod   # noqa: F401  (v2: lighting/grade, camera recipes, polished props)
from rbx.core import CUES, fix_euler, ensure_motion

norm = lambda w: re.sub(r"[^a-z0-9]", "", w.lower())


class Video:
    def __init__(self, shots_file):
        self.dir = os.path.dirname(os.path.abspath(shots_file))
        self.slug = os.path.basename(self.dir)
        wp = os.path.join(self.dir, "audio", "words.json")
        self.words = json.load(open(wp, encoding="utf-8")) if os.path.exists(wp) else []
        self.end = self.words[-1]["end"] + 0.25 if self.words else 60.0
        self.shots = {}
        self.look = _lookmod.DEFAULT_PRESET   # 2026-11-14 was "day" (cool fill). grade preset applied to every shot (day, dusk, night, interior, neon, horror)
        self.exposure = {}
        ep = os.path.join(self.dir, "exposure.json")
        if os.path.exists(ep):
            self.exposure = json.load(open(ep))

    # --- timing
    def w(self, i):
        """Start time of script word i (first shot should use 0.0)."""
        return 0.0 if i <= 0 else self.words[i]["start"]

    def we(self, i):
        return self.words[i]["end"]

    def find(self, text, n=1, after=0):
        """Index of the n-th word matching text (normalised), searching from word index `after`."""
        k = 0
        for i in range(after, len(self.words)):
            if norm(self.words[i]["word"]) == norm(text):
                k += 1
                if k == n:
                    return i
        raise KeyError(f"word {text!r} #{n} not found after {after}")

    def t(self, text, n=1, after=0):
        return self.w(self.find(text, n, after))

    def span(self, t0, t1):
        return [w for w in self.words if t0 <= w["start"] < t1]

    # --- registry
    def shot(self, i, t0, t1, desc=""):
        def deco(fn):
            self.shots[i] = dict(id=i, t0=float(t0), t1=float(t1), fn=fn, desc=desc)
            return fn
        return deco

    def check(self):
        """Shots must tile the timeline with no gaps or overlaps."""
        ids = sorted(self.shots)
        problems = []
        prev = 0.0
        for i in ids:
            s = self.shots[i]
            if abs(s["t0"] - prev) > 1e-3:
                problems.append(f"shot {i} starts at {s['t0']:.3f}, previous ended {prev:.3f}")
            if s["t1"] <= s["t0"]:
                problems.append(f"shot {i} has no length")
            prev = s["t1"]
        if abs(prev - self.end) > 0.05:
            problems.append(f"last shot ends {prev:.3f}, audio ends {self.end:.3f}")
        return problems

    def build(self, i, samples=24, pct=100, look="AgX - Punchy"):
        S = self.shots[i]
        reset()
        CUES.clear()
        setup_render(F(S["t0"]), F(S["t1"]) - 1, samples=samples, pct=pct, blur=False)   # v5 (DRIPDYL guide): blur off unless the shot asks
        _lookmod.EXPOSURE = 0.0
        _lookmod.VIEW_LOOK = None; _lookmod.SHUTTER = None; _lookmod.EXTRA_COMP.clear(); _lookmod.PRE_COMP.clear()   # v3 per-shot look state
        from rbx import cast as _cast
        _cast.AUTO_LIGHT = getattr(self, "auto_char_light", True)   # v3.1: shots may set cast.AUTO_LIGHT = False
        S["fn"]()
        try:
            _cast.auto_light(self.look)        # key/fill/rim/top/bounce linked to the cast (skipped if a shot made one)
        except Exception as e:
            print("cast.auto_light failed:", e)
        try:
            _lookmod.finish(self.look)
        except Exception as e:
            print("look.finish failed:", e)
        sc = bpy.context.scene
        if sc.camera:
            fix_euler(sc.camera)
            ensure_motion(sc.camera, S["t0"], S["t1"])
        sc.view_settings.exposure = float(self.exposure.get(str(i), _lookmod.EXPOSURE))
        try:
            sc.view_settings.look = _lookmod.VIEW_LOOK or look
        except TypeError:
            pass
        sc.frame_set(F(S["t0"]))
        return S
