"""Regression stress suite: all 8 cast members x varied poses x locations x day/night x cine/flat x 18/45/85 mm, plus a
1,000-extra crowd. Low-res stills (540x960, few samples) for catching rig/pose/grade/prop regressions before a video.

Driver (plain python, takes the global blender lock per Blender run, releases it even on failure):
    python tools/stress_suite.py [job,job|all] [samples]        -> ~/RobloxStories/research/stress/<run>/*.png + sheet.jpg
Inside Blender (one job per process; called by the driver):
    blender -b --factory-startup -P tools/stress_suite.py -- --job kitchen_night --out DIR --samples 8
Poses rotate per job so across all jobs every cast member appears in many different poses. Errors are written to
<out>/errors.txt; a crash in one job never stops the rest."""
import os, sys, time, subprocess, shutil, traceback

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
ROLES = ["host", "bestie", "crush", "mayor", "mom", "dad", "grandpa", "grandma"]
# (name, acting gesture or special, expression)
POSES = [("stand", "idle", "neutral"), ("walk", "WALK", "happy"), ("run", "RUN", "shock"), ("point", "point", "determined"),
         ("reach", "reach", "worried"), ("phone", "phone", "smug"), ("sit", "SIT", "bored"), ("laugh", "cheer", "joy"),
         ("cry", "slump", "cry"), ("lean", "lean", "sus"), ("cross", "cross", "angry"), ("wave", "wave", "smile")]
# job -> (location, kwargs, cine)
JOBS = {
    "kitchen_day": ("kitchen", dict(night=False), True), "kitchen_night": ("kitchen", dict(night=True), True),
    "kitchen_night_flat": ("kitchen", dict(night=True), False), "hallway": ("school_hallway", {}, True),
    "classroom": ("classroom", {}, False), "main_street_day": ("main_street", dict(night=False), True),
    "main_street_night": ("night_street", {}, True), "bedroom": ("bedroom", {}, True), "front_hall": ("front_hall", {}, False),
    "crowd1000": ("main_street", dict(night=False), False),
}
LOCK = os.path.expanduser("~/RobloxStories_tmp/blender.lock")


# ------------------------------------------------------------------------------------------------ driver (no bpy)
def _lock():
    os.makedirs(os.path.dirname(LOCK), exist_ok=True)
    while True:
        try:
            os.mkdir(LOCK); return
        except FileExistsError:
            age = time.time() - os.path.getmtime(LOCK)
            busy = subprocess.run(["pgrep", "-x", "blender", "-i"], capture_output=True).returncode == 0 \
                or subprocess.run(["pgrep", "-if", "Blender.app"], capture_output=True).returncode == 0
            if age > 5400 and not busy:
                shutil.rmtree(LOCK, ignore_errors=True); continue
            time.sleep(5)


def driver(argv):
    sys.path.insert(0, HERE)
    import kit
    sel = argv[0] if argv else "all"
    samples = argv[1] if len(argv) > 1 else "8"
    jobs = list(JOBS) if sel == "all" else sel.split(",")
    out = os.path.join(os.path.expanduser("~/RobloxStories/research/stress"), time.strftime("%Y%m%d_%H%M"))
    os.makedirs(out, exist_ok=True)
    b = kit.find_blender()
    for i, j in enumerate(jobs):
        _lock()
        try:
            t = time.time()
            r = subprocess.run([b, "-b", "--factory-startup", "-P", os.path.abspath(__file__), "--", "--job", j,
                                "--out", out, "--samples", samples, "--rot", str(i * 3)],
                               capture_output=True, text=True, errors="replace", timeout=1800)
            log = r.stdout + r.stderr
            open(os.path.join(out, f"{j}.log"), "w").write(log)
            bad = [l for l in log.splitlines() if "Traceback" in l or "Error" in l or "STRESS_FAIL" in l]
            print(f"{j}: rc={r.returncode} {time.time() - t:.0f}s {len(bad)} error lines", flush=True)
            if r.returncode or bad:
                with open(os.path.join(out, "errors.txt"), "a") as f:
                    f.write(f"== {j} rc={r.returncode}\n" + "\n".join(bad[:40]) + "\n")
        except subprocess.TimeoutExpired:
            print(j, "TIMEOUT"); open(os.path.join(out, "errors.txt"), "a").write(f"== {j} TIMEOUT\n")
        finally:
            shutil.rmtree(LOCK, ignore_errors=True)
    pngs = sorted(p for p in os.listdir(out) if p.endswith(".png"))
    if pngs:   # labelled contact sheet, 6 per row
        if True:   # plain sheet (this ffmpeg build has no drawtext); file order = sorted names
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-pattern_type", "glob", "-i", os.path.join(out, "*.png"),
                            "-vf", f"scale=270:480,tile=6x{(len(pngs) + 5) // 6}", "-frames:v", "1",
                            os.path.join(out, "sheet.jpg")])
    print("STRESS_OUT", out)


# ------------------------------------------------------------------------------------------------ in Blender
def _apply_pose(ch, kind, expr, acting, cast, x, y, z):
    if kind == "WALK":
        cast.walk2(ch, 0.0, 1.0, (x, y + 0.6, z), (x, y - 0.6, z))
    elif kind == "RUN":
        acting.run(ch, 0.0, 1.0, (x, y + 1.0, z), (x, y - 1.0, z))
    elif kind == "SIT":
        acting.hold_pose(ch, 0.0, "slump", hipz=-1.2)
    else:
        acting.hold_pose(ch, 0.0, kind)
    try:
        acting.face(ch, 0.0, expr)
    except Exception as e:
        print("STRESS_FAIL face", expr, e)


def in_blender(argv):
    sys.path.insert(0, ROOT)
    import bpy
    from mathutils import Vector
    from rbx import core, town as T, look, cast, acting, crowd
    a = dict(zip(argv[::2], argv[1::2]))
    job, out, samples, rot = a["--job"], a["--out"], int(a.get("--samples", 8)), int(a.get("--rot", 0))
    loc, kw, cine = JOBS[job]
    core.reset()
    L = T.LOCATIONS[loc](**kw)
    p = T.look_preset(L["look"]); p["world"] = ("sky", 1.0)
    look.rig(p, focus=L["focus"], sky=False)
    core.setup_render(core.F(0.5), core.F(0.5), res=(540, 960), samples=samples, blur=False)
    look.grade(p)
    bpy.context.scene.view_settings.exposure = p.get("exposure", 0.0)
    fx, fy, fz = L["focus"]; oz = L["origin"][2] if "origin" in L else 0.0
    # the location's wide camera defines "toward camera"; line the cast up across that view
    wl, wt, _ = L["cams"][next(iter(L["cams"]))]
    fwd = (Vector(wt) - Vector(wl)); fwd.z = 0; fwd.normalize()
    side = Vector((fwd.y, -fwd.x, 0))
    import math
    yaw = math.degrees(math.atan2(-fwd.x, fwd.y))
    base = Vector((fx, fy, oz)) - fwd * float(os.environ.get('STRESS_PULL', 5.0))
    chars = []
    for i, role in enumerate(ROLES):
        name, kind, expr = POSES[(i + rot) % len(POSES)]
        pos = base + side * ((i - 3.5) * 2.9)
        try:
            ch = cast.make(role, 0.0, 1.0, cine=cine, loc=tuple(pos), rot=yaw)
            _apply_pose(ch, kind, expr, acting, cast, pos.x, pos.y, pos.z)
            chars.append((role, name, pos))
            print("STRESS_CAST", role, name)
        except Exception as e:
            traceback.print_exc(); print("STRESS_FAIL cast", role, name, e)
    if job == "crowd1000":
        try:
            crowd.crowd("stress_crowd", center=(fx, fy + 30, oz), size=(40, 70), n=1000, mode="clusters", seed=7)
        except Exception as e:
            traceback.print_exc(); print("STRESS_FAIL crowd", e)
    sc = bpy.context.scene
    tgt_mid = base + Vector((0, 0, 3.0))
    shots = {"18low": (base - fwd * 14 + Vector((0, 0, 1.2)), tgt_mid + Vector((0, 0, 1.5)), 18, tgt_mid),
             "45med": (base + side * (-5.8) - fwd * 14 + Vector((0, 0, 3.6)), base + side * (-5.8) + Vector((0, 0, 3.4)), 45, None),
             "85close": (chars[rot % len(chars)][2] - fwd * 13 + Vector((0, 0, 5.2)) if chars else wl,
                         chars[rot % len(chars)][2] + Vector((0, 0, 4.9)) if chars else wt, 85, None)}
    if job == "crowd1000":
        shots["18aerial"] = (Vector((fx, fy - 18, oz + 30)), Vector((fx, fy + 30, oz)), 18, None)
    for nm, (cl, ct, lens, _) in shots.items():
        c = core.Cam("Stress_" + nm, lens)
        c.key(0.5, tuple(cl), tuple(ct), lens, focus=tuple(ct), fstop=2.8)
        sc.camera = c.ob
        sc.frame_set(core.F(0.5))
        sc.render.filepath = os.path.join(out, f"{job}_{'cine' if cine else 'flat'}_{nm}.png")
        try:
            bpy.ops.render.render(write_still=True)
            print("STRESS_STILL", sc.render.filepath, flush=True)
        except Exception as e:
            print("STRESS_FAIL render", nm, e)
    with open(os.path.join(out, f"{job}_cast.txt"), "w") as f:
        f.write("\n".join(f"{r}: {n}" for r, n, _ in chars))


if __name__ == "__main__":
    if "--" in sys.argv and "--job" in sys.argv:
        in_blender(sys.argv[sys.argv.index("--") + 1:])
    else:
        driver(sys.argv[1:])
