"""rbx.shotlib v4.2 (2026-11-16: + ots, prop_cam, hide_head, follow, point_on, path_key, seat, mock_quack, shiver; v4.0 2026-11-15): the shot helpers that made EP2 "The Poor Boy Who Bought the School" (user-approved quality).
Import in every new video:  from rbx.shotlib import *   then call  install_snaps()  once at module level.
Rules behind every helper: docs/CLEAN_ANIMATION.md.
  cameras : still_cam, scam (occlusion + clearance safe), med / mcu (aim from the FACE: face_yaw), two_face, safe_pos
  contact : hand_pos (depsgraph-safe), carry (tray/books between fists), aim_prop + pencil, fit_desk_to_hands,
            seat_and_type (sit before the shot, fists on keys), night_desk (desk set at real seated heights), kneel
  physics : drop (gravity arc, tumble, land flat, bounce, slide), books (hold -> drop)
  sets    : car_door + appear (nobody walks through a car), _curb_z snap (feet on sidewalks), shoe_hole (hero prop)
"""
import math
import bpy
from mathutils import Vector
from . import story, cast, cams, qa, look, motion as mo, signs as SG, town as T
from .core import F, Cam, box, cyl, mat, hexc, light
from . import acting


def install_snaps():
    """Feet on sidewalks: wrap cast.make and mo.walk so z=0 positions snap onto low surfaces (0.05-0.6)."""
    if getattr(cast.make, "_snapped", False):
        return
    global _cast_make, _mo_walk
    _cast_make = cast.make; _mo_walk = mo.walk
    cast.make = _make_snapped; cast.make._snapped = True
    mo.walk = _walk_snapped


def _curb_z(x, y):
    """Top of a low surface (sidewalk / curb / step, 0.05-0.6 high) under (x, y); 0 if none. Ignores characters
    (a character standing there would otherwise report its own shoe as the ground). CLEAN_ANIMATION 2."""
    sc = bpy.context.scene; bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
    chars = tuple(o.name[:-5] + "_" for o in sc.objects if o.name.endswith("_head"))
    o = Vector((x, y, 0.9)); d = Vector((0, 0, -1))
    for _ in range(8):
        hit, loc, n, i, ob, m = sc.ray_cast(dg, o, d, distance=1.0)
        if not hit:
            return 0.0
        if chars and ob.name.startswith(chars):
            o = loc + d * 0.01
            continue
        return loc.z if 0.05 <= loc.z <= 0.6 else 0.0
    return 0.0


def _make_snapped(role, t0, t1, *a, **kw):
    loc = kw.get("loc")
    if loc is not None and abs(loc[2]) < 1e-6:
        kw["loc"] = (loc[0], loc[1], _curb_z(loc[0], loc[1]))
    return _cast_make(role, t0, t1, *a, **kw)


def _walk_snapped(ch, t0, t1, path, *a, **kw):
    """Feet follow the ground along the WHOLE path: densify every 0.5 and snap each point onto curbs/sidewalks
    (only points given at z=0; explicit heights are kept)."""
    pts = []
    for k, p in enumerate(path):
        p = Vector(p)
        if k > 0:
            q = Vector(path[k - 1]); n = max(1, int((p - q).length / 0.5))
            for j in range(1, n):
                m = q.lerp(p, j / n)
                pts.append((m.x, m.y, _curb_z(m.x, m.y) if abs(q.z) < 1e-6 and abs(p.z) < 1e-6 else m.z))
        pts.append((p.x, p.y, _curb_z(p.x, p.y) if abs(p.z) < 1e-6 else p.z))
    return _mo_walk(ch, t0, t1, pts, *a, **kw)


def head(ch, t, dz=0.55):
    bpy.context.scene.frame_set(F(t))
    return tuple(ch.head.matrix_world.translation + Vector((0, 0, dz)))


def still_cam(t0, t1, loc, tgt, lens=35, push=0.08, fstop=4.0, focus=None, name="Cam"):
    c = Cam(name, lens)
    lv, tv = Vector(loc), Vector(tgt)
    c.key(t0, tuple(lv), tuple(tv), lens, focus=tuple(focus or tv), fstop=fstop)
    c.key(t1, tuple(lv + (tv - lv) * push), tuple(tv), lens, focus=tuple(focus or tv), fstop=fstop, ease="EASE_IN_OUT")
    cams.micro(c, deg=0.4, loc=0.02, period=2.2)
    return c


def mcu(t0, t1, ch, rot, label, off=30, d=7.4, eyes=0.42, side=1, push=0.06, arc=8, fstop=1.6, zone=0.2, pitch=3):
    return scam(t0, t1, head(ch, t0, -0.15), yaw=face_yaw(ch, t0 + 0.3) + side * 15, dist=d, pitch=pitch, lens=55, push=push, fstop=fstop,
                ignore=(ch.name,), name="Cam_mcu")


def hand_pos(ch, t, arm="armR"):
    """World position of the fist at t. The fist empty is created lazily by mo.hand: refresh the depsgraph AFTER
    creating it, or a fresh empty reports the origin (lesson 2026-11-15: desk flew to y 0)."""
    hd = mo.hand(ch, arm)
    bpy.context.scene.frame_set(F(t))
    bpy.context.view_layer.update()
    return tuple(hd.matrix_world.translation)


def _blocked(a, b, ignore=()):
    """True if something (not in ignore names) sits between points a and b."""
    sc = bpy.context.scene; dg = bpy.context.evaluated_depsgraph_get()
    a, b = Vector(a), Vector(b); d = b - a; L = d.length
    if L < 1e-4:
        return False
    hit, loc, nrm, idx, ob, mtx = sc.ray_cast(dg, a, d.normalized(), distance=L)
    if not hit:
        return False
    return not any(ob.name.startswith(p) for p in ignore)


def _clear(p, r=0.8):
    """Camera needs free space around it (not inside/against a wall, locker or door)."""
    sc = bpy.context.scene; dg = bpy.context.evaluated_depsgraph_get(); p = Vector(p)
    for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
        hit = sc.ray_cast(dg, p, Vector(d), distance=r)[0]
        if hit and d != (0, 0, -1):
            return False
    return True


def safe_pos(target, yaw=-15, dist=9.0, pitch=4, ignore=()):
    """Camera position around target (yaw 0 = in front along -Y, + = to the right), pulled in or swung round until
    the line of sight is clear. Avoids the 'camera inside a wall / behind a head' black frames."""
    bpy.context.view_layer.update()
    t = Vector(target)
    for dy in (0, 20, -20, 40, -40, 65, -65):
        for k in (1.0, 0.8, 0.62, 0.48):
            dd = dist * k
            ya, pa = math.radians(yaw + dy), math.radians(pitch)
            p = t + Vector((math.sin(ya) * math.cos(pa), -math.cos(ya) * math.cos(pa), math.sin(pa))) * dd
            if not _blocked(t + (p - t).normalized() * 0.9, p, ignore) and _clear(p, 0.8):
                return p
    return t + Vector((0, -dist * 0.5, 1.0))


def scam(t0, t1, target, yaw=-15, dist=9.0, pitch=4, lens=40, push=0.10, fstop=2.8, ignore=(), name="Cam_s"):
    p = safe_pos(target, yaw, dist, pitch, ignore)
    tv = Vector(target)
    c = Cam(name, lens)
    c.key(t0, tuple(p), tuple(tv), lens, focus=tuple(tv), fstop=fstop)
    c.key(t1, tuple(p + (tv - p) * push), tuple(tv), lens, focus=tuple(tv), fstop=fstop, ease="EASE_IN_OUT")
    cams.micro(c, deg=0.4, loc=0.02, period=2.2)
    return c


def face_yaw(ch, t):
    """Camera yaw (safe_pos convention) that looks straight at the character's FACE at time t."""
    bpy.context.scene.frame_set(F(t))
    f = ch.head.matrix_world.to_quaternion() @ Vector((0, -1, 0))
    return math.degrees(math.atan2(f.x, -f.y))


def _rot_of(ch):
    try:
        return -math.degrees(ch.root.rotation_euler.z)
    except Exception:
        return 0.0


def med(t0, t1, ch, yaw=-12, d=9.0, lens=40, pitch=4, up=-0.8):
    off = yaw if abs(yaw) <= 60 else -12
    return scam(t0, t1, head(ch, t0, up), yaw=face_yaw(ch, t0 + 0.3) + off, dist=d, pitch=pitch, lens=lens,
                ignore=(ch.name,))


def two_face(t0, t1, a, b, favor=None, lens=30, extra=6.0, pitch=5, up=-1.0, ignore=()):
    """Two-shot that sees BOTH faces: camera on the open (-Y) side of the line between the two heads,
    swung 20 deg toward the favoured character's face."""
    pa, pb = Vector(head(a, t0 + 0.3, up)), Vector(head(b, t0 + 0.3, up))
    mid = (pa + pb) / 2; dv = pb - pa
    n = Vector((-dv.y, dv.x, 0)).normalized()
    if n.y > 0: n = -n
    yaw = math.degrees(math.atan2(n.x, -n.y))
    if favor is not None:
        fy = face_yaw(favor, t0 + 0.3)
        yaw += max(-25, min(25, (fy - yaw + 540) % 360 - 180))
    dist = max(9.0, dv.length * 1.5 + extra)
    return scam(t0, t1, tuple(mid), yaw=yaw, dist=dist, pitch=pitch, lens=lens, ignore=(a.name, b.name) + tuple(ignore))


def kneel(ch, t, expr=None):
    return mo.strike(ch, t, {"hipz": -1.25, "legL": (85, 0, 0), "kneeL": 95, "legR": (-15, 0, 0), "kneeR": 100,
                             "torso": (0, 14, 0)}, expr=expr)


def drop(obs, t_fall, push=(0, -1, 0), power=3.6, seed=0, rest=0.14):
    """Real fall (CLEAN_ANIMATION 4): each object flies on a gravity arc from where it is at t_fall, tumbles, lands
    flat, bounces once, slides and settles. Small stagger per object."""
    import random
    rnd = random.Random(7 + seed)
    P = Vector(push); P.z = 0
    P = P.normalized() if P.length > 0 else Vector((0, -1, 0))
    side = Vector((-P.y, P.x, 0)); n = len(obs)
    for k, b in enumerate(obs):
        b.rotation_mode = "XYZ"
        f0 = F(t_fall) + k
        bpy.context.scene.frame_set(f0)
        p = Vector(b.matrix_world.translation)
        v = P * (power * rnd.uniform(0.8, 1.2)) + side * ((k - (n - 1) / 2) * 1.4) + Vector((0, 0, rnd.uniform(1.0, 2.5)))
        rot = Vector(b.rotation_euler)
        w = Vector((rnd.uniform(-9, 9), rnd.uniform(-7, 7), rnd.uniform(-6, 6)))
        b.keyframe_insert("location", frame=f0); b.keyframe_insert("rotation_euler", frame=f0)
        dt = 1 / 30.0; landed = 0; f = f0
        rz = rest + 0.02 * k
        while f < f0 + 45:
            f += 1
            v.z -= 32 * dt
            p += v * dt
            if landed == 0:
                rot += w * dt
            if p.z <= rz:
                p.z = rz
                if landed == 0:
                    v = Vector((v.x * 0.45, v.y * 0.45, -v.z * 0.22)); landed = 1
                    rot = Vector((0, 0, rot.z)); w = Vector((0, 0, 0))
                else:
                    v = Vector((v.x * 0.6, v.y * 0.6, 0))
            b.location = p; b.rotation_euler = rot
            b.keyframe_insert("location", frame=f); b.keyframe_insert("rotation_euler", frame=f)
        qa.rest(b, t_fall + 1.6, t_fall + 30)          # v4.1: after landing it must lie ON the floor
    return obs


def books(name, loc, t_fall=None, n=3, floor=(0, 0, 0.1), seed=0, hold=None, push=(0, -1, 0), power=3.6):
    """School books. hold=(ch, t_from): ride in ch's hands (keyed every 2 f) until t_fall; then drop()."""
    cols = ["#2f6db3", "#c0392b", "#2e8b57", "#d4a017"]
    obs = []
    for k in range(n):
        m = mat(f"{name}_m{k}", hexc(cols[(k + seed) % 4]), 0.6)
        b = box(f"{name}{k}", (1.4, 1.0, 0.28), (loc[0], loc[1], loc[2] + k * 0.3), m, 0.04)
        obs.append(b)
    if hold is not None and t_fall is not None:
        ch, ta = hold
        for f in range(F(ta), F(t_fall) + 1, 2):
            hl = Vector(hand_pos(ch, f / 30.0, "armL")); hr = Vector(hand_pos(ch, f / 30.0, "armR"))
            c = (hl + hr) / 2
            for k, b in enumerate(obs):
                b.location = (c.x, c.y - 0.55, c.z - 0.25 + k * 0.28)
                b.keyframe_insert("location", frame=f)
    if t_fall is not None:
        drop(obs, t_fall, push, power, seed)
    return obs


def carry(obs, ch, t0, t1, up=0.12, fwd=-0.25, step=2):
    """Objects ride between the character's two fists (tray, box, books) - keyed every `step` frames."""
    base = [Vector(o.location) for o in obs]
    for f in range(F(t0), F(t1) + 1, step):
        hl = Vector(hand_pos(ch, f / 30.0, "armL")); hr = Vector(hand_pos(ch, f / 30.0, "armR"))
        c = (hl + hr) / 2
        for o, b0 in zip(obs, base):
            o.location = (c.x + b0.x, c.y + fwd + b0.y, c.z + up + b0.z)
            o.keyframe_insert("location", frame=f)


def pencil(name="pencil"):
    """Real pencil (pink eraser, metal band, yellow hex body, sharpened wood tip, graphite point), built along
    local +Z from the eraser end so the whole prop can be aimed with one rotation."""
    root = bpy.data.objects.new(name, None); bpy.context.scene.collection.objects.link(root)
    parts = [("_er", 0.075, 0.075, 0.12, 0.06, "#e88a9a", 0.7, 0.0), ("_fe", 0.08, 0.08, 0.08, 0.16, "#c9c9c9", 0.3, 0.9),
             ("_bd", 0.075, 0.075, 0.95, 0.675, "#f2b632", 0.5, 0.0), ("_wd", 0.075, 0.022, 0.2, 1.25, "#e3c08f", 0.8, 0.0),
             ("_gr", 0.022, 0.002, 0.07, 1.385, "#2b2b2b", 0.4, 0.0)]
    for suf, r1, r2, ln, zc, col, rough, met in parts:
        cyl(name + suf, r1, ln, (0, 0, zc), mat(name + suf + "_m", hexc(col), rough, met), 6 if suf == "_bd" else 16,
            parent=root, r2=r2)
    return root


def aim_prop(ob, t0, t1, grip, dir_fn, hold=0.45, step=2):
    """Key a prop every `step` frames: grip point from grip(t), pointing along dir_fn(t)."""
    for f in range(F(t0), F(t1) + 1, step):
        t = f / 30.0
        g = Vector(grip(t)); d = Vector(dir_fn(t)).normalized()
        ob.location = g - d * hold
        ob.rotation_mode = "QUATERNION"
        ob.rotation_quaternion = d.to_track_quat("Z", "Y")
        ob.keyframe_insert("location", frame=f); ob.keyframe_insert("rotation_quaternion", frame=f)


def car_door(cx, cy, t_open=None, name="bdoor"):
    """Side door on the camera (-Y) side of a T.car(rot=90) parked at (cx, cy): dark opening + door that swings OUT
    (hinge at the front end). Characters stand OUTSIDE the body (y <= cy-7.2) and step away: nobody walks through
    the car (CLEAN_ANIMATION 2). t_open None = already open."""
    body = mat("tw_car_door", hexc("#141416"), 0.25, 0.3)
    box(name + "_gap", (2.3, 0.05, 1.8), (cx + 0.4, cy - 2.53, 2.55), mat("door_gap", hexc("#050506"), 0.9), 0.0)
    pv = bpy.data.objects.new(name + "_hinge", None); bpy.context.scene.collection.objects.link(pv)
    pv.location = (cx + 1.6, cy - 2.6, 0)
    d = box(name, (2.4, 0.16, 2.0), (-1.2, -0.02, 2.5), body, 0.08, parent=pv)
    box(name + "_win", (1.8, 0.04, 0.9), (-1.2, -0.12, 3.25), mat("door_win", hexc("#22303c"), 0.1, 0.2), 0.02, parent=pv)
    pv.rotation_mode = "XYZ"
    if t_open is None:
        pv.rotation_euler = (0, 0, math.radians(72))
    else:
        pv.rotation_euler = (0, 0, 0); pv.keyframe_insert("rotation_euler", frame=F(t_open))
        pv.rotation_euler = (0, 0, math.radians(80)); pv.keyframe_insert("rotation_euler", frame=F(t_open + 0.35))
        pv.rotation_euler = (0, 0, math.radians(72)); pv.keyframe_insert("rotation_euler", frame=F(t_open + 0.55))
    return pv


def appear(ch, t):
    """Character hidden until t. v4.1: cast characters carry their OWN visibility keys (live window t0..t1), which
    overrode the old version (EP2 0:03: Harry stood next to the road before the car arrived). Key hidden at frame 1 AND
    at the shot's first frame (same-frame keys replace cast's), visible at t. Prefer a CUT instead (VEHICLE rule)."""
    f0 = bpy.context.scene.frame_start
    for o in ch.coll.all_objects:
        for f, v in ((1, True), (f0, True), (max(f0 + 1, F(t) - 1), True), (F(t), False)):
            o.hide_render = v; o.keyframe_insert("hide_render", frame=f)
            o.hide_viewport = v; o.keyframe_insert("hide_viewport", frame=f)


def shoe_hole(h):
    """Big readable hole on the FRONT of Harry's LEFT sneaker: dark torn opening + white sock toe poking out.
    Built from the shoe's real world bounds and parented to the shoe so it follows the walk."""
    sh = bpy.data.objects.get(h.name + "_harry_shoe_legL")
    if sh is None:
        print("shoe_hole: no shoe"); return None
    bpy.context.view_layer.update()
    mw = sh.matrix_world
    ys = [(mw @ Vector(c)).y for c in sh.bound_box]; zs = [(mw @ Vector(c)).z for c in sh.bound_box]
    xs = [(mw @ Vector(c)).x for c in sh.bound_box]
    fy = min(ys); cz = (min(zs) + max(zs)) / 2 + 0.02; cx = (min(xs) + max(xs)) / 2
    hole = cyl("shoe_hole", 0.27, 0.06, (cx, fy - 0.01, cz), mat("hole_m", hexc("#0e0c0b"), 0.95), 24, rot=(90, 0, 0),
               coll=h.coll)
    hole.scale = (1.35, 1.0, 0.85)
    sock = bpy.ops.mesh.primitive_uv_sphere_add(radius=0.2, location=(cx + 0.03, fy - 0.06, cz - 0.02), segments=16,
                                               ring_count=10)
    sk = bpy.context.active_object; sk.name = "shoe_sock"; sk.scale = (1.15, 0.7, 0.8)
    sk.data.materials.append(mat("sock_m", hexc("#f4efe6"), 0.9))
    for o in (sk,):
        for c in o.users_collection: c.objects.unlink(o)
        h.coll.objects.link(o)
    for k, (dx, dz, r) in enumerate([(-0.33, 0.12, 20), (0.34, -0.1, -25), (0.05, 0.24, 80)]):
        th = box(f"shoe_fray{k}", (0.16, 0.03, 0.05), (cx + dx, fy - 0.03, cz + dz), mat("fray_m", hexc("#cfcac2"), 0.9), 0.0,
                 rot=(0, r, 0), coll=h.coll)
        th.parent = sh; th.matrix_parent_inverse = sh.matrix_world.inverted()
    for o in (hole, sk):
        o.parent = sh; o.matrix_parent_inverse = sh.matrix_world.inverted()
    return hole


def stool():
    """Desk chair so Harry sits at a real desk height (he sank to chin level before)."""
    box("chair_seat", (2.4, 2.2, 0.4), (608, 13.4, 2.3), mat("chair_m", hexc("#3a3f4a"), 0.6), 0.06)
    box("chair_back", (2.4, 0.35, 3.2), (608, 12.2, 4.1), mat("chair_m", hexc("#3a3f4a"), 0.6), 0.08)
    cyl("chair_post", 0.18, 2.1, (608, 13.4, 1.05), mat("chair_p", hexc("#222222"), 0.4, 0.6), 12)


def desk_cam(t0, t1, lens=28):
    """Bedroom desk: camera above the desk's right end, beside the monitor, looking back at Harry's face (3/4 front).
    The desk lamp is hidden because it sits on that sight line."""
    for o in bpy.context.scene.objects:
        if o.name.startswith(("bd_lamp", "bd_mug")):
            o.hide_render = True; o.hide_viewport = True
    return still_cam(t0, t1, (612.0, 19.0, 6.0), (608.0, 14.0, 5.2), lens=lens, push=0.08, fstop=2.8)


def night_desk():
    """Harry's bedroom desk set at REAL seated heights (CLEAN_ANIMATION 2): chair seat 1.5, desk top 2.8,
    old beige CRT monitor with a glowing screen, keyboard on the front edge. Hides the room's tall desk."""
    L = T.bedroom(morning=False, night=True)
    story.V.look = "ref_night"
    look.cinematic("ref_practical", focus=(608, 16, 4))
    for o in bpy.context.scene.objects:
        if o.name.startswith(("bd_desk", "bd_lamp", "bd_mug", "bd_note")):
            o.hide_render = True; o.hide_viewport = True
    wood = mat("dk_wood", hexc("#7a5636"), 0.7)
    box("dk_top", (6.0, 3.2, 0.2), (608, 17.0, 2.7), wood, 0.04)
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(f"dk_leg{sx}{sy}", (0.25, 0.25, 2.6), (608 + sx * 2.8, 17.0 + sy * 1.4, 1.3), wood, 0.03)
    beige = mat("crt_m", hexc("#d8ccb0"), 0.7)
    box("crt_body", (2.8, 2.4, 2.3), (608, 17.9, 4.0), beige, 0.12)
    box("crt_neck", (1.2, 0.8, 0.3), (608, 17.9, 2.95), beige, 0.05)
    SG.screen("crt", [("build_school()", "#7cff9a"), ("+1 brick", "#ffffff")], (608, 16.68, 4.05), w=2.2, h=1.7,
              bg="#0b1020", size=0.26, bezel="#cdbf9f", glow=3.0)
    kb = box("kbd", (2.4, 0.8, 0.12), (608, 15.85, 2.86), mat("kbd_m", hexc("#e6e0d0"), 0.6), 0.03)
    seat = mat("chair_m", hexc("#3a3f4a"), 0.6)
    box("ch_seat", (2.2, 2.0, 0.3), (608, 14.3, 1.35), seat, 0.06)
    box("ch_back", (2.2, 0.3, 2.6), (608, 13.25, 2.8), seat, 0.08)
    cyl("ch_post", 0.16, 1.2, (608, 14.3, 0.6), mat("ch_p", hexc("#222222"), 0.4, 0.6), 12)
    light("crt_glow", "AREA", (608, 16.4, 4.1), 450, hexc("#9cc4ff"), 2.0, target=(608, 14.3, 4.4))
    light("crt_rim", "AREA", (611, 11.5, 7), 300, hexc("#ffb36b"), 3, target=(608, 14.3, 4.4))
    return dict(seat=(608, 14.3, 1.5), kbdL=(607.45, 15.8, 2.95), kbdR=(608.55, 15.8, 2.95), screen=(608, 16.6, 4.05))


def fit_desk_to_hands(h, t, D):
    """CONTACT BY CONSTRUCTION: R6 arms are short (1.55) and the reach solver clamps, so instead of hoping the fists
    reach a guessed keyboard, pose the typing arms first, MEASURE where the fists are, then move the keyboard/desk/
    monitor so the keys sit right under the fists (fist bottom ~0.22 below its centre)."""
    hl = Vector(hand_pos(h, t, "armL")); hr = Vector(hand_pos(h, t, "armR"))
    mid = (hl + hr) / 2
    kb = bpy.data.objects["kbd"]
    dz = (mid.z - 0.24 - 0.06) - kb.location.z
    dy = mid.y + 0.05 - kb.location.y
    for o in bpy.context.scene.objects:
        if o.name.startswith(("dk_top", "kbd", "crt")) and o.parent is None:
            o.location.z += dz; o.location.y += dy
        elif o.name.startswith("dk_leg"):
            o.location.y += dy
            o.scale.z = (2.6 + dz) / 2.6; o.location.z = (2.6 + dz) / 2
    kb.scale.x = max(1.0, (abs(hr.x - hl.x) + 0.9) / 2.4)
    D["kbdL"] = (hl.x, hl.y, mid.z - 0.24); D["kbdR"] = (hr.x, hr.y, mid.z - 0.24)
    D["screen"] = (D["screen"][0], D["screen"][1] + dy, D["screen"][2] + dz)
    return D


def seat_and_type(h, t0, t1, D, typing_until=None):
    """Seat character h (already built at loc=(seat_x, seat_y - 0.15, 0), rot=180) and keep both fists ON the keyboard."""
    mo.sit(h, t0 - 0.7, seat_h=1.5)       # seated and settled BEFORE the shot starts (sit keys arms at t+6 f)
    qa.sit(h)
    # typing: IK the fists to reachable points in front of the belly, keep them there with a small typing wobble,
    # THEN build the keyboard under where the fists actually are (contact by construction)
    body = {"torso": (0, 10, 0)}
    root = Vector((D["seat"][0], D["seat"][1] - 0.15, 0))
    tL = (root.x - 0.6, root.y + 1.25, 2.95); tR = (root.x + 0.6, root.y + 1.25, 2.95)
    tu = typing_until if typing_until is not None else t1
    mo.reach(h, t0 - 0.25, tL, hand="l", body=body); mo.reach(h, t0 - 0.25, tR, hand="r", body=body)
    mo.contact(h, t0 - 0.1, tu, tL, hand="l", body=body, wobble=0.05, seed=1)
    mo.contact(h, t0 - 0.1, tu, tR, hand="r", body=body, wobble=0.05, seed=2)
    mo.look_at(h, t0, D["screen"])
    fit_desk_to_hands(h, t0 + 0.3, D)    # v4.3: measure the fists AFTER every body key (look_at moved them 0.47)
    qa.touch(h, "armL", D["kbdL"], t0 + 0.1, tu, tol=0.45); qa.touch(h, "armR", D["kbdR"], t0 + 0.1, tu, tol=0.45)
    qa.look(h, D["screen"], t0 + 0.2, t1, tol=35)
    return h



# =====================================================================================================================
# v4.1 (2026-11-15, user review of the POSTED EP2): framing, object interaction, body animation. docs/CLEAN_ANIMATION.md 10-14
# =====================================================================================================================
from . import props3 as P3


def _head_top(ch, t):
    bpy.context.scene.frame_set(F(t))
    return ch.head.matrix_world.translation + Vector((0, 0, 0.9))


def _frame_points(ch, t, shot):
    """Points that MUST be inside the frame for a character, by shot size."""
    bpy.context.scene.frame_set(F(t)); bpy.context.view_layer.update()
    hd = ch.head.matrix_world.translation.copy()
    root = ch.root.matrix_world.translation.copy()
    fw = ch.root.matrix_world.to_quaternion() @ Vector((0, -1, 0)); side = Vector((-fw.y, fw.x, 0)).normalized()
    top = hd + Vector((0, 0, 1.0))
    low = {"mcu": hd.z - 2.4, "med": hd.z - 3.6, "cowboy": hd.z - 4.6, "full": root.z - 0.1}[shot]
    w = 0.9 if shot == "mcu" else 1.7
    c = Vector((hd.x, hd.y, low))
    return [top, top + side * w, top - side * w, c + side * w, c - side * w, c]


def frame_on(chars, t0, t1, shot="med", yaw=None, lens=35, margin=0.06, pitch=4, push=0.06, fstop=2.8, name="Cam_f",
             extra=(), headroom=0.04, register=True, clear=True):
    """CAMERA THAT FRAMES THE SUBJECTS (v4.1). Solves the distance so every subject's head (with headroom) and body down
    to the shot size (mcu|med|cowboy|full) sits INSIDE the 9:16 frame with a margin, from the subjects' face side
    (yaw = offset in deg from their mean face direction, default 0). Avoids walls (_clear/_blocked: swings yaw).
    EP2 lesson: still_cam guesses cut Ryan + his dad in half at 1:21 and Harry at 0:11. Registers qa.frame for each."""
    chars = list(chars)
    pts = [p for ch in chars for p in _frame_points(ch, t0 + 0.3, shot)] + [Vector(e) for e in extra]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    tgt = (mn + mx) / 2
    fy = sum(face_yaw(c, t0 + 0.3) for c in chars) / len(chars) if chars else 0.0
    ty = 12.0 / lens; tx = ty * 9 / 16        # core.Cam: sensor_fit VERTICAL, sensor_height 24 (half = 12 mm)
    lim_x, lim_y = tx * (1 - 2 * margin), ty * (1 - 2 * margin)

    def fits(p, aim):
        f = (aim - p).normalized(); r = f.cross(Vector((0, 0, 1))).normalized(); u = r.cross(f)
        for q in pts:
            v = q - p; z = v.dot(f)
            if z <= 0.3 or abs(v.dot(r) / z) > lim_x or abs(v.dot(u) / z) > lim_y - headroom:
                return False
        return True
    best = None
    for dy in ([0, 12, -12, 25, -25, 40, -40] if yaw is None else [0, 10, -10, 20, -20]):
        ya, pa = math.radians(fy + (yaw or 0) + dy), math.radians(pitch)
        dirv = Vector((math.sin(ya) * math.cos(pa), -math.cos(ya) * math.cos(pa), math.sin(pa)))
        lo, hi = 2.0, 80.0
        for _ in range(30):
            mid = (lo + hi) / 2
            if fits(tgt + dirv * mid, tgt): hi = mid
            else: lo = mid
        p = tgt + dirv * hi * 1.03
        if not _blocked(tgt + dirv * 1.2, p, tuple(c.name for c in chars)) and _clear(p, 0.6):
            best = p; break
        if best is None: best = p
    c = Cam(name, lens)
    c.key(t0, tuple(best), tuple(tgt), lens, focus=tuple(tgt), fstop=fstop)
    c.key(t1, tuple(best + (tgt - best) * push), tuple(tgt), lens, focus=tuple(tgt), fstop=fstop, ease="EASE_IN_OUT")
    cams.micro(c, deg=0.3, loc=0.015, period=2.2)
    if clear:
        clear_fg(c.ob, chars, t0, t1, shot=shot)
    if register:
        for ch in chars:
            qa.frame(ch, t0, t1, shot)
    return c


CLEARED = []          # (shot-time, name) of everything clear_fg hid; ep logs can print it


def _char_roots():
    """Every character in the scene: rigged cast/extra roots (<name>_root with children) and crowd instance empties."""
    out = []
    for o in bpy.context.scene.objects:
        if o.name.startswith("cx_"):
            continue                                   # hidden crowd SOURCE parts (hiding them hides every instance)
        if o.type == "EMPTY" and o.name.endswith("_root") and o.children:
            out.append(("rig", o))
        elif o.type == "EMPTY" and o.instance_type == "COLLECTION" and o.instance_collection is not None \
                and not o.hide_render:
            out.append(("inst", o))
    return out


def clear_fg(cam_ob, chars, t0, t1, shot="med", keep=(), near=3.0, gx=9, gy=16, passes=3):
    """FOREGROUND CLEANER (v4.3, EP3 QA): hide every NON-subject character (rigged extra/cast or crowd instance) that a
    camera ray hits IN FRONT of the subjects (closer than the nearest subject - 1.2), or closer than `near` to the lens.
    Ray grid gx x gy over the frame at three times of the shot. EP3 baseline: crowd backs filled s04/s07, Max's back
    filled s31, the seat-mate's shoulder s55/s57/s58. keep = name prefixes never hidden (an intended dirty-single FG)."""
    sc = bpy.context.scene
    sc.camera = cam_ob
    subj = [c.name for c in chars]
    roots = [(k, o) for k, o in _char_roots()
             if not any(o.name.startswith(n + "_") or o.name == n for n in subj)
             and not any(o.name.startswith(k_) for k_ in keep)]
    rig = {o.name: o for k, o in roots if k == "rig"}
    inst = [o for k, o in roots if k == "inst"]

    def owner(ob, loc):
        if ob.name.startswith("cx_"):                      # crowd instance: the source part -> nearest instancer
            best, bd = None, 1.9
            for o in inst:
                p = o.matrix_world.translation
                d = math.hypot(p.x - loc.x, p.y - loc.y)
                if d < bd and -0.5 < loc.z - p.z < 6.5:
                    best, bd = o, d
            return best
        o = ob
        while o is not None:
            if o.name in rig:
                return o
            o = o.parent
        nm = ob.name.split("_")[0]
        return rig.get(nm + "_root")

    hide = set()
    for _ in range(passes):
        new = set()
        for t in (t0 + 0.15, (t0 + t1) / 2, t1 - 0.1):
            sc.frame_set(F(t)); bpy.context.view_layer.update()
            dg = bpy.context.evaluated_depsgraph_get()
            co = cam_ob.matrix_world.translation.copy(); R = cam_ob.matrix_world.to_3x3()
            dsub = min(((c.hip.matrix_world.translation - co).length for c in chars), default=1e9) - 1.2
            tr, br, bl, tl = cam_ob.data.view_frame(scene=sc)
            for i in range(gx):
                for j in range(gy):
                    x = (i + 0.5) / gx; y = (j + 0.5) / gy
                    pl = bl + (tl - bl) * y; pr = br + (tr - br) * y
                    d = (R @ (pl + (pr - pl) * x)).normalized()
                    hit, loc, n_, ix, ob, m_ = sc.ray_cast(dg, co, d, distance=max(dsub, near))
                    if not hit or any(ob.name.startswith(n + "_") for n in subj):
                        continue
                    o = owner(ob, loc)
                    if o is not None and o.name not in hide:
                        new.add(o.name)
        if not new:
            break
        for nm in new:
            o = bpy.data.objects[nm]
            for ob in [o] + list(o.children_recursive):
                force_hidden(ob)
            CLEARED.append((round(t0, 2), nm))
        hide |= new
        bpy.context.view_layer.update()
    return sorted(hide)


def _grip_empties(prop):
    out = {}
    for k, v in prop["grips"].items():
        e = bpy.data.objects.new(prop["root"].name + "_grip" + k, None)
        bpy.context.scene.collection.objects.link(e); e.parent = prop["root"]; e.location = v
        out[k] = e
    return out


def hold(ch, prop, t0, t1, style=None, height=None, fwd=0.85, step=1, approach=0.3):
    """HOLD A PROP FOR REAL (v4.1). The fists go to the prop's grip points and the prop rides on the MEASURED fists
    every frame (contact by construction; no prop floating between empty hands - EP2 books 0:12, pizza 0:33).
      style 'sides' (books, tray, box): fists press the left/right faces, prop at belly height in front of the body.
      style 'under' (pizza box, cake): palms under the prop, prop flat on the fists at lower-chest height.
    Registers qa.touch for both grips and qa.prop (no clipping)."""
    style = style or prop["style"]
    w = prop["w"]
    bpy.context.scene.frame_set(F(t0)); bpy.context.view_layer.update()
    root = ch.root.matrix_world
    zc = (2.85 if style == "sides" else 3.05) if height is None else height
    halfw = (w / 2 + 0.22) if style == "sides" else max(0.45, w * 0.3)
    loc_t = {"l": Vector((halfw, -fwd, zc)), "r": Vector((-halfw, -fwd, zc))}        # local: +X = character's left
    body = {"torso": (0, 4, 0)}
    for hnd in ("l", "r"):
        tw = root @ loc_t[hnd]
        mo.reach(ch, t0 - approach, tuple(tw), hand=hnd, body=body)
        mo.contact(ch, t0 - approach + 0.05, t1, tuple(tw), hand=hnd, body=body, step=2)
        mo.contact(ch, t0, t0, tuple(tw), hand=hnd, body=body)      # v4.3: a key ON frame 1 beats the cast's t0 stance
    gr = _grip_empties(prop)
    r = prop["root"]; r.rotation_mode = "XYZ"
    for f in range(F(t0 - approach), F(t1) + 1, step):
        t = f / 30.0
        hl = Vector(hand_pos(ch, t, "armL")); hr = Vector(hand_pos(ch, t, "armR"))
        mid = (hl + hr) / 2
        yaw = math.atan2(hl.y - hr.y, hl.x - hr.x)            # prop +X from right fist to left fist
        r.rotation_euler = (0, 0, yaw)
        if style == "sides":
            r.location = (mid.x, mid.y, mid.z)
        else:
            r.location = (mid.x, mid.y, mid.z + 0.24 + prop["h"] * 0.5)
        r.keyframe_insert("location", frame=f); r.keyframe_insert("rotation_euler", frame=f)
    qa.touch(ch, "armL", gr["L" if style == "sides" else "L"], t0, t1, tol=0.45)
    qa.touch(ch, "armR", gr["R"], t0, t1, tol=0.45)
    qa.prop(r, holder=ch, arm="arm")
    return prop


def kneel_down(ch, t, dur=0.7, expr=None, knee="R"):
    """KNEEL WITH REAL BODY MECHANICS (v4.1). R6 legs = thigh 1 + shin 1, hip at z 2. One knee on the floor:
    hipz -0.75 (hip at 1.25), floor leg thigh vertical + shin back (knee 90), other leg thigh forward + shin down (knee 90).
    Path: weight shift + torso lean (40 %), lower (75 %), contact, settle. No overshoot strike (EP2 0:24 'glitching':
    an 8-frame strike with 12 % overshoot + hipz -1.25 sank the legs through the floor). t = moment the knee lands.
    BEST: start the shot already kneeling (t <= shot start) - big transitions go in the cut (craftee rule)."""
    up, dn = ("legL", "kneeL"), ("legR", "kneeR")
    if knee == "L": up, dn = dn, up
    t0 = t - dur
    ch.pose(t0, hipz=0.0, torso=(0, 0, 0), **{up[0]: (0, 0, 0), up[1]: 0, dn[0]: (0, 0, 0), dn[1]: 0})
    ch.pose(t0 + dur * 0.4, hipz=-0.15, torso=(0, 18, 0), **{up[0]: (45, 2, 0), up[1]: 35, dn[0]: (-8, 0, 0), dn[1]: 25})
    ch.pose(t0 + dur * 0.75, hipz=-0.5, torso=(0, 22, 0), **{up[0]: (80, 2, 0), up[1]: 80, dn[0]: (-4, 0, 0), dn[1]: 75})
    ch.pose(t, hipz=-0.64, torso=(0, 14, 0), **{up[0]: (90, 2, 0), up[1]: 90, dn[0]: (0, 0, 0), dn[1]: 90})
    ch.pose(t + 0.2, hipz=-0.62, torso=(0, 10, 0), **{up[0]: (90, 2, 0), up[1]: 90, dn[0]: (0, 0, 0), dn[1]: 90})
    if expr:
        acting.face(ch, t0 + 0.05, expr)
    return t + 0.2


KNEEL_POSE = dict(hipz=-0.62, torso=(0, 10, 0), legL=(90, 2, 0), kneeL=90, legR=(0, 0, 0), kneeR=90)


def belly_laugh(ch, t0, t1, target, point=True, hz=2.4, expr="joy", stagger=0.0):
    """LAUGH AT SOMEONE (v4.1): body already turned to the target before the shot, eyes ON the target the whole time,
    point at them first (0.7 s), then one fist to the belly, head tips back 10 deg, small shoulder shake 2.4 Hz.
    EP2 0:19: kids looked away and the old laugh (head yaw reset to 0, 4 Hz hip bounce) read as dancing.
    Registers qa.look on the target."""
    t_end = mo.turn(ch, t0 - 0.6, target=target, dur=4)
    yaw = mo.sample(ch, t_end + 0.02, ["rot"])["rot"]     # v4.3 (EP3 A-1): the cast's own rot key at t0 undid the turn
    ch.pose(t0, rot=yaw); ch.pose(t1, rot=yaw)
    ts = t0 + stagger
    if point:
        mo.point(ch, ts + 0.05, target, hold=0.6, expr="laugh_smug")
    tl = ts + (0.75 if point else 0.1)
    bpy.context.scene.frame_set(F(tl)); bpy.context.view_layer.update()
    belly = ch.root.matrix_world @ Vector((0.25, -0.75, 2.5))
    mo.reach(ch, tl, tuple(belly), hand="l", expr=expr)
    rel, pitch = mo.aim(ch, tl, target)
    hy = max(-55, min(55, rel * 0.85))
    t, k = tl + 0.15, 0
    while t < t1:
        a = 1.0 if k % 2 == 0 else -1.0
        ch.pose(t, head=(hy, -9 + 2.5 * a, 3 * a), torso=(0, -3, 2.0 * a), hipz=0.015 * a)
        t += 0.5 / hz; k += 1
    qa.look(ch, target, ts + 0.3, t1, tol=40)
    return ch


def crowd_laugh(chars, t0, t1, target, stagger=0.12):
    for k, c in enumerate(chars):
        belly_laugh(c, t0, t1, target, point=(k % 2 == 0), stagger=k * stagger, hz=2.2 + 0.25 * (k % 3))


def game_screen(name, o, t0, t1, title="BLOX SCHOOL TYCOON", build=True, w=6.4, h=3.6, players=None):
    """A monitor that SHOWS A GAME (v4.1): the screen is a window into a lit mini 3D diorama inside the monitor case:
    a blocky school assembling brick by brick + tiny avatars, with a UI bar (title, PLAYERS ONLINE). EP2 0:38: the
    'game' was plain text and numbers. Returns dict(root, screen_center)."""
    ox, oy, oz = o
    bez = mat("gs_bezel", hexc("#1a1b1f"), 0.4)
    for nm, sz, lc in (("t", (w + 0.6, 0.6, 0.3), (0, 0, h / 2 + 0.15)), ("b", (w + 0.6, 0.6, 0.3), (0, 0, -h / 2 - 0.15)),
                       ("l", (0.3, 0.6, h), (-w / 2 - 0.15, 0, 0)), ("r", (0.3, 0.6, h), (w / 2 + 0.15, 0, 0))):
        box(f"{name}_bz{nm}", sz, (ox + lc[0], oy + lc[1], oz + lc[2]), bez, 0.05)
    for nm, sz, lc in (("ct", (w + 0.6, 6.0, 0.2), (0, 3.3, h / 2 + 0.4)), ("cb", (w + 0.6, 6.0, 0.2), (0, 3.3, -h / 2 - 0.4)),
                       ("cl", (0.2, 6.0, h + 0.6), (-w / 2 - 0.4, 3.3, 0)), ("cr", (0.2, 6.0, h + 0.6), (w / 2 + 0.4, 3.3, 0))):
        box(f"{name}_{nm}", sz, (ox + lc[0], oy + lc[1], oz + lc[2]), bez, 0.05)     # HOLLOW case: the screen is a window
    D = Vector((ox, oy + 2.6, oz - h / 2 + 0.2))                     # diorama floor inside the case
    box(f"{name}_sky", (w + 0.4, 0.1, h + 0.4), (ox, oy + 6.0, oz), mat("gs_sky", hexc("#8fd0ff"), 1.0), 0.0)
    box(f"{name}_grass", (w + 0.4, 6.0, 0.2), (ox, oy + 3.3, D.z - 0.1), mat("gs_grass", hexc("#5cc04a"), 0.8), 0.0)
    cols = ["#d9573b", "#d9573b", "#e8e0cf"]
    bricks = []
    for lvl in range(4):
        for i in range(6):
            b = box(f"{name}_br{lvl}_{i}", (0.55, 0.5, 0.3), (D.x - 1.4 + i * 0.56, D.y + 0.5, D.z + 0.15 + lvl * 0.31),
                    mat("gs_brick" + str(lvl % 3), hexc(cols[lvl % 3]), 0.6), 0.02)
            bricks.append(b)
    roof = box(f"{name}_roof", (3.6, 1.0, 0.35), (D.x, D.y + 0.5, D.z + 1.45), mat("gs_roof", hexc("#2f4f8f"), 0.5), 0.04)
    bricks.append(roof)
    if build:
        n = len(bricks)
        for k, b in enumerate(bricks):
            ta = t0 + (t1 - t0 - 0.4) * k / n
            z1 = b.location.z
            b.location.z = z1 + 2.0; b.keyframe_insert("location", frame=max(1, F(ta) - 6))
            b.hide_render = True; b.keyframe_insert("hide_render", frame=1); b.keyframe_insert("hide_render", frame=max(1, F(ta) - 7))
            b.hide_render = False; b.keyframe_insert("hide_render", frame=max(1, F(ta) - 6))
            b.location.z = z1; b.keyframe_insert("location", frame=F(ta))
    for k in range(3):
        box(f"{name}_av{k}", (0.22, 0.16, 0.5), (D.x + 1.6 + k * 0.3, D.y - 0.6, D.z + 0.25),
            mat(f"gs_av{k}", hexc(["#ffd21e", "#2f7bff", "#e04a3a"][k]), 0.5), 0.03)
    light(f"{name}_sun", "AREA", (ox, oy + 1.2, oz + h / 2 - 0.2), 900, hexc("#ffffff"), 4, target=tuple(D))
    SG.label(f"{name}_ui", title, (ox, oy + 0.35, oz + h / 2 - 0.35), 0.32, "#ffffff", "bold", 2.0, rot=(90, 0, 0))
    box(f"{name}_uibar", (w, 0.05, 0.6), (ox, oy + 0.4, oz + h / 2 - 0.35), mat("gs_uibar", hexc("#2f7bff"), 0.5), 0.0)
    if players:
        SG.label(f"{name}_pl", players, (ox, oy + 0.35, oz - h / 2 + 0.35), 0.3, "#7cff9a", "bold", 2.0, rot=(90, 0, 0))
    return dict(screen_center=(ox, oy, oz))


def extra(name, t0, t1, expr="neutral", loc=(0, 0, 0), rot=0, shirt="#5aa0e0", pants="#2d3550", hair="short",
          hair_color="#2a1d16", skin="#f1d2b0", scale=1.0, face="kid"):
    """Background classmate built like the cast (hands, elbows/knees, stance, blinking face, cinematic finish)."""
    from . import chars
    ch = chars.Char(name, skin=skin, shirt=shirt, pants=pants, hair=hair, hair_color=hair_color, face=face,
                    sleeves="short", scale=scale, seed=sum(map(ord, name)))
    if abs(loc[2]) < 1e-6:
        loc = (loc[0], loc[1], _curb_z(loc[0], loc[1]))
    cast._finish(ch, t0, t1, expr, loc, rot, True, True, "#888888")
    try:
        cast.cine_finish(ch)
    except Exception as e:
        print("extra cine", e)
    return ch



# =====================================================================================================================
# v4.2 (2026-11-16, EP3 friend_secret): OTS, POV prop inserts, hands that FOLLOW a moving prop (handover, push-back,
# sleeve grab, handshake), seated framing, mock-quack crowd, shiver.
# =====================================================================================================================


def ots(t0, t1, fg, subj, lens=40, back=3.2, side=1.4, up=0.9, push=0.05, fstop=2.0, aim_dz=-0.35, shot="mcu",
        name="Cam_ots"):
    """OVER-THE-SHOULDER (CLEAN_ANIMATION 1.3): camera behind fg's shoulder (on fg's `side`: +1 = fg's left), looking
    at subj's face. fg's head/shoulder stays a soft foreground edge, subj faces the lens. Registers qa.frame(subj)."""
    a = Vector(head(fg, t0 + 0.2, -0.2)); b = Vector(head(subj, t0 + 0.2, aim_dz))
    d = (b - a); d.z = 0; d.normalize()
    sv = Vector((-d.y, d.x, 0)) * side           # +side = left of the line fg->subj
    p = a - d * back + sv * abs(side) + Vector((0, 0, up))
    c = Cam(name, lens)
    c.key(t0, tuple(p), tuple(b), lens, focus=tuple(b), fstop=fstop)
    c.key(t1, tuple(p + (b - p) * push), tuple(b), lens, focus=tuple(b), fstop=fstop, ease="EASE_IN_OUT")
    cams.micro(c, deg=0.3, loc=0.015, period=2.2)
    qa.frame(subj, t0, t1, shot)
    return c


def prop_cam(t0, t1, prop, dist=4.0, lens=50, normal=None, push=0.08, fstop=2.2, center=None, up=0.0, name="Cam_ins"):
    """STRAIGHT-ON INSERT of a prop face (screen, tag, duck): the camera sits on the face NORMAL (world) of the prop's
    readable side at time t0, so the text is frontal and fully in frame (CLEAN_ANIMATION 5). normal: world vector or
    None = the prop root's local -Y (the side props3 props show to the viewer)."""
    sc = bpy.context.scene; sc.frame_set(F(t0)); bpy.context.view_layer.update()
    r = prop["root"] if isinstance(prop, dict) else prop
    piv = prop.get("piv") if isinstance(prop, dict) else None
    ob = piv or r
    q = ob.matrix_world.to_quaternion()
    n = Vector(normal) if normal is not None else (q @ Vector((0, -1, 0)))
    n.normalize()
    c0 = Vector(center) if center is not None else ob.matrix_world.translation.copy()
    p = c0 + n * dist + Vector((0, 0, up))
    c = Cam(name, lens)
    c.key(t0, tuple(p), tuple(c0), lens, focus=tuple(c0), fstop=fstop)
    c.key(t1, tuple(p + (c0 - p) * push), tuple(c0), lens, focus=tuple(c0), fstop=fstop, ease="EASE_IN_OUT")
    cams.micro(c, deg=0.25, loc=0.01, period=2.4)
    return c


def force_hidden(ob):
    """Hide an object for the WHOLE shot even if it carries visibility keys (cast characters key their own live window,
    which silently overrides a plain hide_render = True)."""
    from .core import fcurves
    ob.hide_render = True; ob.hide_viewport = True
    ad = ob.animation_data
    if ad and ad.action:
        for fc in fcurves(ad.action):
            if fc.data_path in ("hide_render", "hide_viewport"):
                for kp in fc.keyframe_points:
                    kp.co[1] = 1.0
    return ob


def hide_head(ch):
    """POV shots from inside a character: hide its head, hair, hat and face parts (the camera is where the eyes are).
    Uses force_hidden (the cast's visibility keys would otherwise show them again)."""
    for o in bpy.context.scene.objects:
        n = o.name.lower()
        if o.name.startswith(ch.name + "_") and any(k in n for k in ("_head", "hair", "ltdhat", "_face", "_eye", "_brow", "_mouth")) \
                and o.type in ("MESH", "FONT", "CURVE"):
            force_hidden(o)
            for c in o.children_recursive:
                force_hidden(c)


def hide_for_pov(ch):
    """POV from inside a character holding something: hide EVERYTHING of it except the arms/hands (head, hair, collar,
    torso, legs would block or fill the lens)."""
    for o in bpy.context.scene.objects:
        if o.name.startswith(ch.name + "_") and o.type in ("MESH", "FONT", "CURVE") and "arm" not in o.name.lower() \
                and "fist" not in o.name.lower() and "hand" not in o.name.lower():
            force_hidden(o)


def follow(ch, t0, t1, target, hand="r", body=None, step=1, approach=0.25, register=True, tol=0.45):
    """The fist FOLLOWS a moving target (empty / object / Char) from t0 to t1: approach reach first, then contact
    re-solved every `step` frames. For two-character prop beats (handover, push-back, holding a sleeve, handshake),
    animate the PROP or the target empty first, then make every hand follow it. Registers qa.touch."""
    arm = "armL" if str(hand).lower() in ("l", "left", "arml") else "armR"
    mo.reach(ch, t0 - approach, target, hand=hand, body=body)
    mo.contact(ch, t0 - approach + 0.05, t1, target, hand=hand, body=body, step=step)
    mo.contact(ch, t0, t0, target, hand=hand, body=body)                # v4.3: key ON frame 1 (cast t0 stance)
    if register:
        qa.touch(ch, arm, target, t0, t1, tol=tol)
    return target


def point_on(parent, local, name):
    """Empty parented to an object at a local offset (a grip point / sleeve point that moves with its parent)."""
    e = bpy.data.objects.new(name, None); bpy.context.scene.collection.objects.link(e)
    e.parent = parent; e.location = local
    return e


def path_key(ob, keys, rot=None):
    """Key an object's location along [(t, (x, y, z)), ...] with eased bezier keys (a prop moved by hands)."""
    for t, p in keys:
        ob.location = p; ob.keyframe_insert("location", frame=F(t))
    if rot is not None:
        ob.rotation_mode = "XYZ"
        for t, r in rot:
            ob.rotation_euler = tuple(math.radians(a) for a in r); ob.keyframe_insert("rotation_euler", frame=F(t))
    return ob


def seat(ch, t0, seat_h=1.5, lead=0.7):
    """Seated BEFORE the shot (mo.sit lands at t0 - lead); registers qa.sit."""
    mo.sit(ch, t0 - lead, seat_h=seat_h)
    qa.sit(ch)
    return ch


def mock_quack(ch, t0, t1, target, hz=2.6, stagger=0.0, expr="toothy", turn=True):
    """MOCKING QUACK at someone (EP3 cafeteria): body turned to the target BEFORE the shot, head ON the target the whole
    time, hands tucked at the armpits and elbows FLAPPING like wings (no hip bounce, no dancing), beak mouth (o) / grin
    alternating. Registers qa.look."""
    if turn:                                     # seated characters: head only (a turning seated body clips the bench)
        mo.turn(ch, t0 - 0.6, target=target, dur=4)
    rel, pitch = mo.aim(ch, t0 + 0.1, target)
    hy = max(-55, min(55, rel * 0.85))
    t, k = t0 + stagger, 0
    acting.face(ch, t0, expr)
    while t < t1:
        a = 1.0 if k % 2 == 0 else 0.0
        pose = {"head": (hy, max(-20, min(20, pitch)) - 4 * a, 0), "torso": (0, -2 * a, 0)}
        for side, arm in ((1, "l"), (-1, "r")):          # fist tucked at the chest side, elbow out = wing; pole flaps it
            pose.update(mo.reach_pose(ch, t, (side * 1.05, -0.75, 1.55), hand=arm, local=True,
                                      pole=(side * 1.0, 0.1, -0.2 + 0.9 * a)))
        ch.pose(t, **pose)
        if k % 2 == 0:
            acting.face(ch, t, mouth="o" if (k // 2) % 2 == 0 else "grin_full")
        t += 0.5 / hz; k += 1
    qa.look(ch, target, t0 + 0.2, t1, tol=40)
    return ch


def shiver(ch, t0, t1, amp=1.6, hz=9.0, hug=True):
    """Shaking with fear: arms hugged in (optional), tiny fast shoulder/torso tremor (no big motion), eyes darting."""
    if hug:
        ch.pose(t0 - 0.2, armL=(55, -10, 20), armR=(55, -10, 20), elbowL=95, elbowR=95)
    t, k = t0, 0
    while t < t1:
        a = 1.0 if k % 2 == 0 else -1.0
        ch.pose(t, torso=(a * amp * 0.6, 2, a * amp), head=(a * amp * 0.8, 6, 0))
        t += 0.5 / hz; k += 1
    try:
        acting.dart(ch, t0, t1)
    except Exception as e:
        print("shiver dart", e)
    return ch
