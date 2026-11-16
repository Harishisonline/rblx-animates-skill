"""Validate Blox Town v3 locations: one still per location camera at 1080x1920 (low samples), serial, one process.
blender -b --factory-startup -P tools/world_stills.py -- [loc,loc|all] [samples] [cams]
  -> research/world_stills/<loc>_<cam>.png  (also prints prop/object counts)"""
import os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import bpy
from rbx import core, town as T, look

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
sel = argv[0] if argv else "all"
samples = int(argv[1]) if len(argv) > 1 else 12
camsel = argv[2].split(",") if len(argv) > 2 else None
names = list(T.LOCATIONS) if sel == "all" else sel.split(",")
out = os.path.join(ROOT, "research", "world_stills"); os.makedirs(out, exist_ok=True)
EXTERIOR = {"main_street", "pharmacy_corner", "school_exterior"}
import ast
for nm in names:
    kind = None
    kw = {}
    if "@" in nm:   # loc@key=val;key=val  e.g. main_street@plaza_crowd=90  kitchen@night=False
        nm, _, a = nm.partition("@")
        kw = {k: ast.literal_eval(v) for k, v in (x.split("=") for x in a.split(";"))}
    if nm.startswith("insert_table"):
        nm, _, kind = nm.partition(":"); kind = kind or "wrist"
    core.reset()
    t = time.time()
    L = T.LOCATIONS[nm](kind=kind, **kw) if kind else T.LOCATIONS[nm](**kw)
    tag = os.environ.get("TAG", "") + ("_" + "_".join(f"{k}{v}" for k, v in kw.items()) if kw else "")
    p = T.look_preset(L["look"]); p["world"] = ("sky", 1.0)
    if nm in EXTERIOR:
        p["sun"] = None
    look.rig(p, focus=L["focus"], sky=False)
    core.setup_render(core.F(L.get('t', 0)), core.F(L.get('t', 0)), samples=samples, blur=False)
    look.grade(T.look_preset(L["look"]))
    bpy.context.scene.view_settings.exposure = T.look_preset(L["look"]).get("exposure", 0.0)
    if os.environ.get("WITH_CAST") and not kind:
        try:
            from rbx import cast
            fx, fy, fz = L["focus"]
            spots = L.get("cast_spots") or [(fx + dx, fy - 1.5, L["origin"][2] + (0.2 if nm == "main_street" else 0), 0)
                                            for dx in (-2.6, 0.0, 2.8)]
            for role, (x, y, z, yaw) in zip(("host", "bestie", "mom"), spots):
                cast.make(role, 0, 2, loc=(x, y, z), rot=yaw)
        except Exception as e:
            import traceback; traceback.print_exc(); print("CAST_FAILED", e)
    for cam in (camsel or L["cams"]):
        if cam not in L["cams"]:
            continue
        tc = L.get("cam_t", {}).get(cam, L.get('t', 0))
        T.frame(L, cam, tc)
        sc = bpy.context.scene; sc.frame_end = max(sc.frame_end, core.F(tc)); sc.frame_set(core.F(tc))
        sc.render.filepath = os.path.join(out, f"{L['name']}{'_' + kind if kind else ''}{tag}_{cam}.png")
        bpy.ops.render.render(write_still=True)
        print("STILL", sc.render.filepath, f"{time.time() - t:.1f}s", len(bpy.data.objects), "objects", flush=True)
