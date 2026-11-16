# Kit v4.0 low-res ANIMATED preview + QA of every shot: Blender -b --factory-startup -P tools/ep_lo.py -- <slug> [all|ids]
# writes videos/<slug>/frames_lo/####.png and videos/<slug>/render_lo.log (BLOCKED AWAY FLOAT CLIP NOTOUCH EYELINE)
import importlib.util, os, sys, time, traceback, bpy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shotkit
from rbx.core import F
_a = sys.argv[sys.argv.index('--') + 1:]
vdir = os.path.join(shotkit.STUDIO, 'videos', _a[0])
spec = importlib.util.spec_from_file_location("video_shots", os.path.join(vdir, "shots.py"))
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
V = mod.V
argv = _a[1:]
ids = sorted(V.shots) if not argv or argv[0] == "all" else [int(x) for x in argv[0].split(",")]
os.makedirs(os.path.join(vdir, "frames_lo"), exist_ok=True)
log = open(os.path.join(vdir, os.environ.get("RBX_LO_LOG", "render_lo.log")), "a")  # v4.2: per-agent log
for p in V.check():
    log.write("TIMELINE: %s\n" % p)
for i in ids:
    t0 = time.time()
    try:
        from rbx import qa as _qa
        _qa.reset()
        S = V.build(i, samples=6, pct=34)
        sc = bpy.context.scene
        sc.render.use_motion_blur = False
        sc.render.filepath = os.path.join(vdir, "frames_lo", "")
        try:
            from mathutils import Vector as _V
            for fr_ in (sc.frame_start, (sc.frame_start + sc.frame_end) // 2, sc.frame_end):
                sc.frame_set(fr_); dg = bpy.context.evaluated_depsgraph_get(); cam = sc.camera
                o = cam.matrix_world.translation; fwd = cam.matrix_world.to_quaternion() @ _V((0, 0, -1))
                hit, loc, n_, ix, ob, m_ = sc.ray_cast(dg, o, fwd, distance=1.5)
                if hit:
                    log.write(f"BLOCKED shot {i:02d} frame {fr_} by {ob.name} at {(loc - o).length:.2f}\n")
            from bpy_extras.object_utils import world_to_camera_view as _w2c
            for fr_ in (sc.frame_start + 2, (sc.frame_start + sc.frame_end) // 2, sc.frame_end - 2):
                sc.frame_set(fr_); cam = sc.camera; co = cam.matrix_world.translation
                for hd in [o for o in sc.objects if o.name.endswith("_head") and o.parent and o.parent.name.endswith("_neck")]:
                    p = hd.matrix_world.translation; v = _w2c(sc, cam, p)
                    if not (0.15 < v.x < 0.85 and 0.05 < v.y < 0.95 and 0 < v.z < 16): continue
                    fw = hd.matrix_world.to_quaternion() @ _V((0, -1, 0))
                    dot = fw.dot((co - p).normalized())
                    if dot < -0.15:
                        log.write(f"AWAY shot {i:02d} frame {fr_} {hd.name} dot {dot:.2f} dist {v.z:.1f}\n")
        except Exception as e:
            log.write(f"guard err {e}\n")
        try:
            _qa.run(sc, log, i)
        except Exception as e:
            log.write(f"qa err {e}\n")
        bpy.ops.render.render(animation=True)
        log.write(f"shot {i:02d} ok {time.time()-t0:.1f}s\n")
    except Exception:
        log.write(f"shot {i:02d} FAILED\n" + traceback.format_exc())
    log.flush()
log.write("LO DONE\n"); log.close()
