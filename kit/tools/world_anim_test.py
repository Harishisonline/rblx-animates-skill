"""Time-based prop test + big-crowd cost test. blender -b --factory-startup -P tools/world_anim_test.py -- [anim|crowd]
anim: OPEN->CLOSED flip (t=1.0), type-on message (t0=0.5), wrist counter 000->001->099 (t=1.0, 2.0); renders t=0.2,1.5,2.6
crowd: 1,500 instanced extras on a plaza, one still + timing."""
import os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, ROOT)
import bpy
from rbx import core, town as T, signs as S, crowd as C, look
mode = (sys.argv[sys.argv.index("--") + 1:] or ["anim"])[0]
out = os.path.join(ROOT, "research", "world_stills"); os.makedirs(out, exist_ok=True)
core.reset()
if mode == "anim":
    core.world((0.5, 0.5, 0.55), 0.8)
    core.box("bg", (12, 0.2, 14), (0, 1, 0), core.mat("bgm", core.hexc("#d8cfc0"), 0.8), 0)
    S.closed_sign("cs", (0, 0.5, 4.5), 0, None, t_flip=1.0)
    core.box("msgbg", (7, 0.05, 1.4), (0, 0.6, 2.2), core.mat("mb", core.hexc("#202530"), 0.5), 0.05)
    S.typed("ty", "Don't come home.", (-3.2, 0.5, 2.2), t0=0.5, cps=10, size=0.6, color="#ffffff", glow=2.0)
    S.wrist_counter("wc", (0, 0.5, 0.3), 0, [(0.0, "000"), (1.0, "001"), (2.0, "099")], s=2.5)
    light = core.light("k", "AREA", (0, -10, 6), 1500, (1, 1, 1), 6, target=(0, 0, 3))
    cam = core.Cam("C", 35); cam.key(0.0, (0, -16, 2.6), (0, 0, 2.6), 35)
    core.setup_render(1, 90, samples=6, blur=False)
    for t in (0.2, 1.5, 2.6):
        sc = bpy.context.scene; sc.frame_set(core.F(t))
        sc.render.filepath = os.path.join(out, f"animtest_t{t:.1f}.png"); bpy.ops.render.render(write_still=True)
        print("STILL", sc.render.filepath, flush=True)
else:
    t0 = time.time()
    T.sky("day"); T.sun(4.2, "#ffe3c0", 48, -35)
    core.box("plaza", (140, 110, 0.2), (0, 40, -0.1), T.pbr.get("cobble"), 0)
    T.pharmacy(o=(0, 100, 0))
    obs = C.crowd("big", (0, 45, 0), (110, 80), 1500, mode="grid", spacing=2.6, face=(-4, 100, 20), seed=1)
    C.numbers(obs[:60], seed=2)
    print("BUILD", len(obs), "extras", f"{time.time() - t0:.1f}s", flush=True)
    p = T.look_preset("day"); p["world"] = ("sky", 1.0); p["sun"] = None
    look.rig(p, focus=(0, 30, 3), sky=False)
    cam = core.Cam("C", 24); cam.key(0.0, (0, -30, 26), (0, 50, 4), 24)
    core.setup_render(1, 1, samples=8, blur=False); look.grade("day")
    t1 = time.time(); sc = bpy.context.scene
    sc.render.filepath = os.path.join(out, "crowd_1500.png"); bpy.ops.render.render(write_still=True)
    print("STILL", sc.render.filepath, f"render {time.time() - t1:.1f}s", flush=True)
