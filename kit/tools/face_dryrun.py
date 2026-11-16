"""face_dryrun.py (v3.7): python -I tools/face_dryrun.py [workspace].  Dry-run of the v3.7 face additions WITHOUT Blender: stub bpy/mathutils, import rbx.acting + rbx.cast, test pure
plans and run ladder/dart/blink on a fake layered character whose _key_map is recorded."""
import sys, types, os
WS = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class D:
    def __init__(s, *a, **k): pass
    def __getattr__(s, n):
        if n.startswith("__"): raise AttributeError(n)
        return D()
    def __call__(s, *a, **k): return D()
    def __iter__(s): return iter([])
    def __getitem__(s, k): return D()
    def __setitem__(s, k, v): pass


for name in ("bpy", "mathutils", "bpy.types", "bpy.props", "bmesh", "bpy_extras", "mathutils.noise",
             "mathutils.bvhtree", "mathutils.geometry"):
    m = types.ModuleType(name); m.__getattr__ = lambda n: D(); sys.modules[name] = m
sys.modules["mathutils"].Vector = D; sys.modules["mathutils"].Matrix = D; sys.modules["mathutils"].Euler = D
sys.path[:0] = [WS]
from rbx import acting as A, cast  # noqa: E402

ok = True
def check(c, msg):
    global ok
    print(("PASS " if c else "FAIL ") + msg); ok &= bool(c)

# 1 fallback / grid
check(A.resolve_cell("eyes", "ring", 4) == A.EYE["wide"], "ring -> wide on 4x4")
check(A.resolve_cell("eyes", "ring", 5) == 19, "ring = 19 on 5x5")
check(A.resolve_cell("mouth", "scream_tongue", 4) == A.MOUTH["scream"], "scream_tongue -> scream on 4x4")
check(all(A.resolve_cell("eyes", n, 4) < 16 for n in A.EYE), "every eye name maps inside a 4x4 atlas")
check(all(A.resolve_cell("mouth", n, 4) < 16 for n in A.MOUTH), "every mouth name maps inside a 4x4 atlas")
check(A._cell(5, 4) == (0.25, 0.5, 0), "legacy _cell(5) unchanged")
check(A._cell(24, 5) == (0.8, 0.0, 0), "5x5 _cell(24) bottom-right")
for k in ("blank", "pop_shock", "sad_tear", "worried_dart", "smug_up", "content"):
    e, m = A.EXPR[k]; check(e in A.EYE and m in A.MOUTH, f"EXPR {k} = {A.EXPR[k]}")
# 2 plans
lp = A.ladder_plan(1.0, "surprise_laugh")
check([e for _, e in lp] == ["smug", "pop_shock", "toothy", "pop_shock"] and abs(lp[1][0] - lp[0][0] - 7 / 30) < 1e-3,
      f"ladder plan {lp}")
dp = A.dart_plan(2.0, 3.2, seed=3)
gaps = [round((b[0] - a[0]) * 30, 1) for a, b in zip(dp, dp[1:])]
check(dp[0][1] == "worried" and dp[-1][1] == "worried" and all(3.9 <= g <= 7.6 for g in gaps[:-1]),
      f"dart plan {len(dp)} keys, gaps (frames) {gaps}")
bs = A.blink_schedule(0, 20, skip=[(5, 7)], seed=1)
iv = [round(b[0] - a[0], 2) for a, b in zip(bs, bs[1:])]
check(all(not (4.88 <= t <= 7.12) for t, _ in bs) and all(abs(o - t - 0.1) < 1e-3 for t, o in bs),
      f"blink schedule {len(bs)} blinks, none in skip window, 3 f closed; intervals {iv}")

# 3 run on a fake layered char (record keys instead of Blender)
keys = []
A._key_map = lambda ch, node, idx, t: keys.append((round(t, 3), node, idx))
A._layered = lambda ch: True
A._grid = lambda ch, node="EyeMap": 4
class Ch: pass
ch = Ch(); ch.name = "harry"; ch._eye_track = []; ch._mouth_track = []
A.face(ch, 0.0, "neutral"); A.blink(ch, 0.0, 12.0, every=(0.4, 0.5))
nb = len(ch._blinks)
end = A.ladder(ch, 3.0, "surprise_scream")
A.dart(ch, 6.0, 7.5)
A.face(ch, 8.0, "sad_tear")
check(not any(3.0 - 0.12 <= tb <= end + 0.12 or 5.88 <= tb <= 7.62 for tb in ch._blinks),
      f"blinks cleared in ladder/dart windows ({nb} -> {len(ch._blinks)})")
check(any(n == "EyeMap" and i == A.EYE["wide"] for _, n, i in keys), "pop_shock keyed as 'wide' on a 4x4 atlas")
check(max(i for _, _, i in keys) < 16, "no key outside a 4x4 atlas")
check(callable(cast.ladder) and "erased" in A.EXPR and "in_this_world" in cast.FACE_SET, "cast exports ladder/dart/FACE_SET")
print("FACE DRY-RUN", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
