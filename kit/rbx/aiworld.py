"""v2.1 AI-world sets, robots, particles and animated props (built for videos/ai_world, reusable for any sci-fi story).

    from rbx import aiworld as A
    A.street(variant="main")            # wet neon street: sidewalks, puddles, lamps, vending machines, wreck, barricades...
    A.hideout()                         # survivors' bunker: shelves, cables, screens, lamps, bunk, map wall, racks, door
    A.core_hall()                       # server corridor to the AI core: rack rows, cameras, vault door with scanner
    A.core_room(t0, t1)                 # giant pulsing red eye, rings, cables, terminals
    u7 = A.enforcer(t0, t1)             # tall enforcer 'Unit Seven' (rim light, emissive trim, red visor)
    hb = A.helper_bot("hb", loc, t0, t1)
    A.sparks("sp", loc, t), A.dust(center, size), A.rain(center, size, t0, t1), A.pulse(mat, t0, t1)
    A.wrist_macro("wm", loc)            # big readable wrist tag for macro inserts (number faces -Y = the camera)

All sets keep the ground BRIGHT enough to read (lighter sidewalks, wet reflections, emissive strips, practical lights):
v2 frames had a pure-black lower third. Each set has 6-10 distinct prop types."""
import math, random
import bpy
from mathutils import Vector
from .core import (D, F, box, cyl, sphere, empty, mat, hexc, noise, text, plane, light, set_interp, fcurves, sfx)
from . import chars
from . import props2 as P

STREET = (0, -28, 0)


def _m(name, hx, rough=0.4, metal=0.0, **kw):
    return mat(name, hexc(hx), rough, metal, **kw)


def _glow(name, hx, s=6.0):
    return mat(name, hexc(hx), 0.3, emit=hexc(hx), estr=s)


# ------------------------------------------------------------------ material animation
def _bsdf(m):
    return next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def pulse(m, t0, t1, lo=3.0, hi=12.0, rate=1.2):
    """Keyframe a material's emission strength as a slow sine-ish pulse (cores, alarms, screens)."""
    inp = _bsdf(m).inputs["Emission Strength"]
    t, k = t0, 0
    step = 0.5 / rate
    while t <= t1 + step:
        inp.default_value = hi if k % 2 == 0 else lo
        inp.keyframe_insert("default_value", frame=F(t))
        t += step; k += 1
    return m


def flicker(m, strength=1.5, scale=3.0):
    """Noise on emission strength (screens, damaged lamps). Never 'dead' light."""
    inp = _bsdf(m).inputs["Emission Strength"]
    inp.keyframe_insert("default_value", frame=1)
    ad = m.node_tree.animation_data
    for fc in fcurves(ad.action):
        if "Emission Strength" in fc.data_path or fc.data_path.endswith("default_value"):
            md = fc.modifiers.new("NOISE"); md.strength = strength; md.scale = scale
            md.phase = hash(m.name) % 100
    return m


def spin(ob, t0, t1, turns=1.0, axis=2):
    ob.rotation_euler[axis] = 0
    ob.keyframe_insert("rotation_euler", index=axis, frame=F(t0))
    ob.rotation_euler[axis] = math.radians(360 * turns)
    ob.keyframe_insert("rotation_euler", index=axis, frame=F(t1))
    set_interp(ob, "rotation_euler", F(t0), "LINEAR")
    return ob


def cable(name, pts, r=0.07, m=None, coll=None):
    """Hanging cable through world points (bezier curve with round bevel)."""
    cu = D.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = r
    cu.bevel_resolution = 3
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(len(pts) - 1)
    for bp, p in zip(sp.bezier_points, pts):
        bp.co = p
        bp.handle_left_type = bp.handle_right_type = "AUTO"
    ob = D.objects.new(name, cu)
    (coll or bpy.context.scene.collection).objects.link(ob)
    cu.materials.append(m or _m("cable_m", "#16181d", 0.5))
    return ob


def sag(a, b, drop=1.2, n=5):
    a, b = Vector(a), Vector(b)
    return [tuple(a.lerp(b, i / (n - 1)) - Vector((0, 0, drop * math.sin(math.pi * i / (n - 1))))) for i in range(n)]


# ------------------------------------------------------------------ particles
def sparks(name, loc, t, n=26, speed=5.0, color="#ffb347", seed=0, life=0.7, size=0.05):
    """Burst of glowing sparks with gravity (hits, cable pull, blasts)."""
    rnd = random.Random(seed)
    M = _glow("spark_" + color[1:], color, 40.0)
    o = Vector(loc)
    for i in range(n):
        v = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(0.2, 1.4))).normalized() * speed * rnd.uniform(0.5, 1.1)
        s = sphere(f"{name}{i}", size * rnd.uniform(0.6, 1.4), tuple(o), M, scale=(1, 1, 2.2), seg=6)
        lf = life * rnd.uniform(0.6, 1.2)
        steps = 4
        s.scale = (0, 0, 0); s.keyframe_insert("scale", frame=F(t) - 1)
        for k in range(steps + 1):
            tt = lf * k / steps
            s.location = tuple(o + v * tt + Vector((0, 0, -4.9 * tt * tt)))
            s.keyframe_insert("location", frame=F(t + tt))
            sc = 1.0 - 0.9 * (k / steps)
            s.scale = (sc, sc, sc * 2.2); s.keyframe_insert("scale", frame=F(t + tt))
        s.scale = (0, 0, 0); s.keyframe_insert("scale", frame=F(t + lf) + 1)
    return n


def dust(center, size=(14, 10, 7), n=60, color="#bfd6ff", strength=3.0, seed=1, r=0.035, name="dust"):
    """Floating motes (catch light in beams). Each drifts on noise so the air is alive."""
    rnd = random.Random(seed)
    M = _glow(name + "_m" + color[1:], color, strength)
    c = Vector(center)
    for i in range(n):
        p = c + Vector((rnd.uniform(-1, 1) * size[0] / 2, rnd.uniform(-1, 1) * size[1] / 2, rnd.uniform(0, 1) * size[2]))
        s = sphere(f"{name}{i}", r * rnd.uniform(0.6, 1.5), tuple(p), M, seg=6)
        for ax in range(3):
            noise(s, "location", ax, 0.35, 40 + rnd.uniform(0, 30))


def rain(center, size=(30, 24), t0=0.0, t1=4.0, n=220, height=16, seed=2, name="rain"):
    """Light rain: thin bright streaks falling on a loop (cyclic keys). Adds life + wet sheen."""
    rnd = random.Random(seed)
    M = mat("rain_m", (0.75, 0.85, 1.0), 0.1, emit=(0.6, 0.75, 1.0), estr=1.6, alpha=0.55)
    c = Vector(center)
    period = 0.55
    for i in range(n):
        x = c.x + rnd.uniform(-1, 1) * size[0] / 2
        y = c.y + rnd.uniform(-1, 1) * size[1] / 2
        s = box(f"{name}{i}", (0.02, 0.02, 0.7), (x, y, height), M, 0.0)
        ph = rnd.uniform(0, period)
        s.location.z = height; s.keyframe_insert("location", index=2, frame=F(t0 - ph))
        s.location.z = -0.5; s.keyframe_insert("location", index=2, frame=F(t0 - ph + period))
        fc = next(f for f in fcurves(s.animation_data.action) if f.data_path == "location")
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
        fc.modifiers.new("CYCLES")


def searchcone(name, src, tgt, color=(1.0, 0.25, 0.25), r=2.2, alpha=0.10):
    """Visible light cone (cheap volumetric look) from src to tgt."""
    a, b = Vector(src), Vector(tgt)
    d = b - a
    M = mat(name + "_m", color, 0.5, emit=color, estr=1.2, alpha=alpha)
    c = cyl(name, 0.15, d.length, tuple((a + b) / 2), M, 24, r2=r)
    c.rotation_mode = "QUATERNION"
    c.rotation_quaternion = d.to_track_quat("-Z", "Y")
    return c


# ------------------------------------------------------------------ street props
def street_lamp(name, loc, color="#bfe6ff", h=9.0, rot=0, energy=900):
    root = empty(name, loc, None, None, (0, 0, rot), 0.4)
    Mp = _m("lamp_pole", "#3a4152", 0.35, 0.7)
    cyl(name + "_pole", 0.16, h, (0, 0, h / 2), Mp, 12, parent=root)
    box(name + "_arm", (0.2, 2.2, 0.2), (0, -1.0, h - 0.1), Mp, 0.05, parent=root)
    box(name + "_head", (0.9, 1.3, 0.3), (0, -2.0, h - 0.25), Mp, 0.08, parent=root)
    box(name + "_bulb", (0.7, 1.1, 0.06), (0, -2.0, h - 0.42), _glow("lamp_bulb" + color[1:], color, 25.0), 0.02, parent=root)
    L = light(name + "_L", "SPOT", (0, 0, 0), energy, hexc(color), 0.8, spot=95, blend=0.6)
    L.parent = root; L.location = (0, -2.0, h - 0.6); L.rotation_euler = (0, 0, 0)
    return root


def vending(name, loc, rot=0, color="#26d9ff", seed=0):
    rnd = random.Random(seed)
    root = empty(name, loc, None, None, (0, 0, rot), 0.4)
    box(name + "_body", (2.4, 1.6, 4.6), (0, 0, 2.3), _m("vend_body" + color[1:], color, 0.35), 0.1, parent=root)
    box(name + "_win", (1.6, 0.08, 3.0), (-0.25, -0.8, 2.7), _glow("vend_win", "#e9f6ff", 2.2), 0.03, parent=root)
    for r in range(4):
        for c in range(3):
            col = rnd.choice(["#ff5a5a", "#ffd34d", "#5aff9b", "#ff8de0", "#7db8ff"])
            box(name + f"_can{r}{c}", (0.3, 0.1, 0.5), (-0.75 + c * 0.5, -0.86, 1.65 + r * 0.7),
                _glow("can" + col[1:], col, 1.5), 0.02, parent=root)
    box(name + "_pad", (0.4, 0.08, 1.2), (0.85, -0.82, 2.9), _m("vend_pad", "#1b1f29", 0.3), 0.03, parent=root)
    box(name + "_slot", (1.5, 0.1, 0.4), (-0.25, -0.82, 0.7), _m("vend_slot", "#11131a", 0.4), 0.03, parent=root)
    box(name + "_top", (2.5, 1.7, 0.5), (0, 0, 4.85), _glow("vend_top" + color[1:], color, 4.0), 0.06, parent=root)
    return root


def holo_billboard(name, loc, body="OBEY THE COUNT", color="#ff2fb3", w=10.0, h=4.0, rot=0, flick=True):
    root = empty(name, loc, None, None, (0, 0, rot), 0.4)
    Mf = _m("holo_frame", "#2a3040", 0.3, 0.7)
    for sx in (-1, 1):
        cyl(name + f"_post{sx}", 0.14, loc[2] if loc[2] > 0 else 6, (sx * w * 0.4, 0.3, -(loc[2] if loc[2] > 0 else 6) / 2), Mf, 10, parent=root)
    box(name + "_frame", (w + 0.4, 0.3, h + 0.4), (0, 0.2, 0), Mf, 0.08, parent=root)
    Mp = mat("holo_panel" + color[1:], hexc(color), 0.2, emit=hexc(color), estr=0.9, alpha=0.55)
    box(name + "_panel", (w, 0.06, h), (0, 0, 0), Mp, 0.0, parent=root)
    Mt = _glow("holo_txt" + color[1:], "#ffffff", 8.0)
    t = text(name + "_txt", body, (0, -0.12, 0), h * 0.32, Mt, (90, 0, 0), 0.02, None, None)
    t.parent = root
    if flick:
        flicker(Mp, 0.5, 2.0)
    return root


def barricade(name, loc, rot=0, w=4.0):
    root = empty(name, loc, None, None, (0, 0, rot), 0.4)
    Mo = _m("barr_o", "#ff8a1f", 0.5); Mw = _m("barr_w", "#f1f1f1", 0.5); Ml = _m("barr_leg", "#2b2f38", 0.5)
    for k in range(6):
        box(name + f"_s{k}", (w / 6, 0.15, 0.55), (-w / 2 + (k + 0.5) * w / 6, 0, 1.6), Mo if k % 2 == 0 else Mw, 0.02,
            rot=(0, 0, 0), parent=root)
    for sx in (-1, 1):
        box(name + f"_l{sx}", (0.15, 0.9, 1.9), (sx * w * 0.42, 0, 0.95), Ml, 0.03, parent=root)
        sphere(name + f"_bl{sx}", 0.13, (sx * w * 0.42, 0, 2.0), _glow("barr_blink", "#ff3b2e", 10.0), parent=root, seg=8)
    return root


def wrecked_car(name, loc, rot=0, color="#3d5a80", tilt=6):
    root = empty(name, loc, None, None, (0, tilt, rot), 0.4)
    Mb = _m("wreck_b" + color[1:], color, 0.45, 0.4, coat=0.3)
    Md = _m("wreck_d", "#16181d", 0.6); Mg = mat("wreck_glass", (0.3, 0.45, 0.6), 0.05, 0.2, alpha=0.5)
    Mt = _m("wreck_tire", "#121316", 0.8); Mr = _m("wreck_rust", "#7a4a2a", 0.9)
    box(name + "_body", (3.4, 7.2, 1.5), (0, 0, 1.25), Mb, 0.3, parent=root)
    box(name + "_cab", (3.0, 3.6, 1.3), (0, 0.4, 2.55), Mb, 0.28, rot=(0, 0, 0), parent=root)
    box(name + "_ws", (2.7, 0.1, 1.0), (0, -1.45, 2.55), Mg, 0.02, rot=(-25, 0, 0), parent=root)
    box(name + "_dent", (1.8, 0.4, 0.9), (1.4, -2.0, 1.4), Mr, 0.1, rot=(0, 20, 15), parent=root)
    for i, (x, y) in enumerate(((-1.6, -2.4), (1.6, -2.4), (-1.6, 2.4), (1.6, 2.4))):
        cyl(name + f"_w{i}", 0.75, 0.6, (x, y, 0.72 if i != 1 else 0.5), Mt, 18, rot=(0, 90, 0), parent=root)
    for sx in (-1, 1):
        box(name + f"_hl{sx}", (0.7, 0.1, 0.35), (sx * 1.1, -3.62, 1.35), _glow("wreck_hl", "#ffe6a8", 3.0 if sx < 0 else 0.0), 0.04, parent=root)
        box(name + f"_tl{sx}", (0.7, 0.1, 0.3), (sx * 1.1, 3.62, 1.35), _glow("wreck_tl", "#ff3030", 4.0), 0.04, parent=root)
    box(name + "_bumper", (3.5, 0.3, 0.4), (0, -3.7, 0.6), Md, 0.08, rot=(0, 12, 0), parent=root)
    return root


def trash_bin(name, loc, color="#2e7d5b"):
    root = empty(name, loc, None, None, (0, 0, 0), 0.3)
    cyl(name + "_b", 0.7, 2.0, (0, 0, 1.0), _m("bin" + color[1:], color, 0.5), 18, 0.05, parent=root)
    cyl(name + "_l", 0.8, 0.2, (0, 0, 2.1), _m("bin_lid", "#1f2229", 0.4), 18, 0.04, parent=root)
    return root


def puddle(name, loc, r=2.4, sy=0.6):
    m = _m("puddle_m", "#0d1220", 0.02, 0.0, spec=1.0)
    p = cyl(name, r, 0.02, (loc[0], loc[1], 0.06), m, 28)
    p.scale = (1, sy, 1)
    return p


def sign_post(name, loc, body="SECTOR 9", color="#ffcf2e", rot=0):
    root = empty(name, loc, None, None, (0, 0, rot), 0.3)
    cyl(name + "_p", 0.1, 5.2, (0, 0, 2.6), _m("sign_pole", "#5a6272", 0.4, 0.6), 10, parent=root)
    box(name + "_b", (3.2, 0.12, 0.9), (0, 0, 5.0), _m("sign_b" + color[1:], color, 0.4), 0.05, parent=root)
    t = text(name + "_t", body, (0, -0.1, 5.0), 0.55, _m("sign_t", "#111318", 0.4), (90, 0, 0), 0.01, None, None)
    t.parent = root
    return root


def cam_pole(name, loc, rot=0, h=7.0):
    """Security camera on a pole/wall with a blinking red LED."""
    root = empty(name, loc, None, None, (0, 0, rot), 0.3)
    Mb = _m("scam_b", "#d9dee7", 0.35)
    if h > 0:
        cyl(name + "_p", 0.1, h, (0, 0.6, -h / 2), _m("scam_p", "#3a4152", 0.4, 0.6), 8, parent=root)
    box(name + "_mount", (0.25, 0.8, 0.25), (0, 0.3, 0), Mb, 0.05, parent=root)
    box(name + "_body", (0.6, 1.3, 0.55), (0, -0.4, -0.1), Mb, 0.12, rot=(-15, 0, 0), parent=root)
    led = sphere(name + "_led", 0.11, (0, -1.08, 0.05), _glow("scam_led", "#ff2a2a", 18.0), parent=root, seg=8)
    noise(root, "rotation_euler", 2, 0.25, 30)
    return root


def street(variant="main", fogd=0.008, rain_t=None, focus=STREET, lamps=True):
    """Neon AI-city street with a readable ground. variant: main | alley | plaza.
    Keeps the action lane around y=-28 (characters stand on the road at y -26..-32)."""
    P.ai_city()
    # brighter, wetter ground + sidewalks + curbs so the lower third is never black
    G = _m("st_asphalt", "#262c3a", 0.16, 0.15, spec=0.7)
    box("st_road", (240, 14, 0.06), (0, -29, 0.05), G, 0)
    Ms = _m("st_walk", "#4a5163", 0.55)
    Mc = _m("st_curb", "#6b7385", 0.5)
    for y, nm in ((-19.5, "back"), (-38.5, "front")):
        box(f"st_walk_{nm}", (240, 5.2, 0.3), (0, y, 0.15), Ms, 0.03)
        box(f"st_curb_{nm}", (240, 0.35, 0.36), (0, y + (2.6 if y < -29 else -2.6), 0.18), Mc, 0.04)
    for j in range(-12, 13):
        box(f"st_tile{j}", (0.06, 5.2, 0.02), (j * 4.0, -19.5, 0.31), _m("st_tile", "#3b4152", 0.6), 0)
    for j in range(-10, 11):
        box(f"st_lane{j}", (2.6, 0.22, 0.03), (j * 6.0, -29, 0.09), _glow("st_lane", "#26d9ff", 5.0), 0)
    for k, (x, y, r) in enumerate(((-4.5, -31.5, 2.6), (6.0, -27.0, 1.8), (-10, -27.5, 2.0), (2.5, -33.5, 1.6))):
        puddle(f"st_pud{k}", (x, y), r)
    box("st_edge_glow_b", (240, 0.12, 0.08), (0, -16.95, 0.34), _glow("st_edge", "#ff2fb3", 4.0), 0)
    # practicals and dressing on the back sidewalk (behind the action)
    if lamps:
        for k, x in enumerate((-15, 0, 15)):
            street_lamp(f"st_lamp{k}", (x + (3 if variant == "alley" else 0), -18.2, 0), "#bfe6ff" if k % 2 == 0 else "#ffd9a0")
    vending("st_vend0", (-8.5, -19.2, 0.3), 0, "#26d9ff", 1)
    vending("st_vend1", (10.5, -19.2, 0.3), 0, "#ff2fb3", 2)
    holo_billboard("st_holo", (3.0, -8.0, 17.5), "OBEY THE COUNT", "#ff2fb3", 12, 4.2)
    sign_post("st_sign", (-13.0, -21.0, 0.3), "SECTOR 9", "#ffcf2e")
    barricade("st_barr0", (13.5, -23.8, 0), 8)
    barricade("st_barr1", (-17.5, -24.0, 0), -12)
    trash_bin("st_bin0", (-4.5, -18.6, 0.3))
    trash_bin("st_bin1", (6.0, -18.4, 0.3), "#5b4ea8")
    cam_pole("st_cam", (16.5, -18.4, 8.0), 20)
    if variant in ("alley", "car"):
        wrecked_car("st_wreck", (7.5, -30.5, 0), 82, "#3d5a80", 4)
    else:
        wrecked_car("st_wreck", (21.0, -24.0, 0), 70, "#7a3d5a", 5)
    # overhead cables between buildings
    for k, (a, b) in enumerate((((-24, -16, 16), (24, -17, 18)), ((-24, -42, 14), (24, -40, 15)))):
        cable(f"st_wire{k}", sag(a, b, 2.2, 6), 0.05)
    # cool sky-fill so the ground/road reflects something
    light("st_skyfill", "AREA", (focus[0], focus[1] - 2, 26), 9000, (0.55, 0.65, 1.0), 40)
    light("st_bounce", "AREA", (focus[0], focus[1] - 9, 0.6), 700, (1.0, 0.45, 0.8), 14, target=(focus[0], focus[1], 4))
    return dict(street=STREET)


# ------------------------------------------------------------------ interiors
def _room(prefix, size=(30, 22, 12), floor="#4a4744", wall="#5a5048", back_y=10.0, left_x=-15.0, right_x=15.0, ceil=True):
    w, d, h = size
    Mf = _m(prefix + "_floor", floor, 0.45)
    Mw = _m(prefix + "_wall", wall, 0.8)
    box(prefix + "_floor", (w + 20, d + 30, 0.4), (0, back_y - d / 2, -0.2), Mf, 0)
    box(prefix + "_back", (w + 20, 0.6, h), (0, back_y + 0.3, h / 2), Mw, 0)
    box(prefix + "_left", (0.6, d + 30, h), (left_x - 0.3, back_y - d / 2, h / 2), Mw, 0)
    box(prefix + "_right", (0.6, d + 30, h), (right_x + 0.3, back_y - d / 2, h / 2), Mw, 0)
    if ceil:
        box(prefix + "_ceil", (w + 20, d + 30, 0.4), (0, back_y - d / 2, h + 0.2), _m(prefix + "_ceilm", "#2a2a2e", 0.8), 0)
    # floor grid lines (concrete slabs) for scale + texture
    for j in range(-8, 9):
        box(f"{prefix}_fl{j}", (0.05, d + 30, 0.01), (j * 3.0, back_y - d / 2, 0.005), _m(prefix + "_fll", "#3a3836", 0.6), 0)


def shelf(name, loc, rot=0, seed=0, w=4.0, h=6.0):
    rnd = random.Random(seed)
    root = empty(name, loc, None, None, (0, 0, rot), 0.3)
    Mm = _m("shelf_m", "#59606e", 0.4, 0.6)
    for sx in (-1, 1):
        box(name + f"_up{sx}", (0.15, 1.2, h), (sx * w / 2, 0, h / 2), Mm, 0.02, parent=root)
    for k in range(4):
        z = 0.4 + k * (h - 0.6) / 3
        box(name + f"_b{k}", (w, 1.2, 0.1), (0, 0, z), Mm, 0.02, parent=root)
        x = -w / 2 + 0.4
        while x < w / 2 - 0.5:
            kind = rnd.random()
            if kind < 0.45:
                s = rnd.uniform(0.5, 0.9)
                box(name + f"_bx{k}_{x:.1f}", (s, 0.8, s * 0.8), (x + s / 2, 0, z + 0.05 + s * 0.4),
                    _m("shelf_box" + str(rnd.randrange(3)), ["#b98852", "#8a6a45", "#c9a36e"][rnd.randrange(3)], 0.8), 0.03, parent=root)
                x += s + 0.12
            elif kind < 0.8:
                col = rnd.choice(["#d9453a", "#e8c547", "#5a9bd6", "#7bc47f"])
                cyl(name + f"_cn{k}_{x:.1f}", 0.18, 0.5, (x + 0.2, 0, z + 0.3), _m("can" + col[1:], col, 0.3, 0.5), 12, parent=root)
                x += 0.45
            else:
                box(name + f"_bt{k}_{x:.1f}", (0.5, 0.6, 0.35), (x + 0.25, 0, z + 0.22), _glow("shelf_batt", "#37ff8b", 1.2), 0.03, parent=root)
                x += 0.65
    return root


def desk_lamp(name, loc, color="#ffcf8a", energy=280, rot=0):
    root = empty(name, loc, None, None, (0, 0, rot), 0.3)
    Mm = _m("dlamp_m", "#2f343f", 0.35, 0.6)
    cyl(name + "_base", 0.35, 0.1, (0, 0, 0.05), Mm, 14, parent=root)
    cyl(name + "_arm", 0.05, 1.3, (0, 0.2, 0.65), Mm, 8, rot=(-18, 0, 0), parent=root)
    cyl(name + "_shade", 0.35, 0.45, (0, -0.15, 1.3), _m("dlamp_sh", "#2e7d5b", 0.4), 14, rot=(-60, 0, 0), parent=root, r2=0.12)
    sphere(name + "_bulb", 0.13, (0, -0.32, 1.2), _glow("dlamp_bulb", color, 20.0), parent=root, seg=10)
    L = light(name + "_L", "POINT", (0, 0, 0), energy, hexc(color), 0.4)
    L.parent = root; L.location = (0, -0.5, 1.1)
    return root


def screen(name, loc, rot=0, w=3.0, h=1.9, color="#37ff8b", body=None, flick=True):
    """Monitor with a glowing UI: header bar + text lines (procedural boxes), flickers."""
    root = empty(name, loc, None, None, (0, 0, rot), 0.3)
    Mc = _m("scr_case", "#232833", 0.4, 0.4)
    box(name + "_case", (w + 0.3, 0.3, h + 0.3), (0, 0.15, 0), Mc, 0.06, parent=root)
    Ms = _glow("scr_bg" + color[1:], "#0b1a16" if color == "#37ff8b" else "#0d1222", 1.0)
    box(name + "_bg", (w, 0.05, h), (0, -0.02, 0), Ms, 0.0, parent=root)
    Ml = _glow("scr_ln" + color[1:], color, 4.0)
    rnd = random.Random(hash(name) % 1000)
    box(name + "_hdr", (w * 0.9, 0.05, 0.14), (0, -0.06, h / 2 - 0.22), Ml, 0.0, parent=root)
    for k in range(5):
        lw = w * rnd.uniform(0.3, 0.8)
        box(name + f"_l{k}", (lw, 0.05, 0.07), (-w * 0.45 + lw / 2, -0.06, h / 2 - 0.5 - k * 0.25), Ml, 0.0, parent=root)
    if body:
        t = text(name + "_t", body, (0, -0.08, -h * 0.28), h * 0.22, Ml, (90, 0, 0), 0.0, None, None)
        t.parent = root
    if flick:
        flicker(Ml, 1.2, 2.5)
    return root


def bunk(name, loc, rot=0):
    root = empty(name, loc, None, None, (0, 0, rot), 0.3)
    Mm = _m("bunk_m", "#4a5160", 0.4, 0.6); Mb = _m("bunk_mat", "#6f7f9a", 0.8); Mp = _m("bunk_pil", "#e8e2d6", 0.8)
    Mbl = _m("bunk_blanket", "#b8463a", 0.8)
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(name + f"_post{sx}{sy}", (0.18, 0.18, 6.0), (sx * 1.6, sy * 3.6, 3.0), Mm, 0.02, parent=root)
    for z in (1.2, 4.2):
        box(name + f"_frame{z}", (3.4, 7.4, 0.25), (0, 0, z), Mm, 0.04, parent=root)
        box(name + f"_mat{z}", (3.1, 7.0, 0.45), (0, 0, z + 0.35), Mb, 0.15, parent=root)
        box(name + f"_pil{z}", (2.2, 1.1, 0.4), (0, 2.8, z + 0.75), Mp, 0.18, parent=root)
        box(name + f"_bl{z}", (3.2, 3.6, 0.2), (0, -1.4, z + 0.62), Mbl, 0.08, parent=root)
    return root


def map_wall(name, loc, rot=0, w=7.0, h=4.2):
    root = empty(name, loc, None, None, (0, 0, rot), 0.3)
    box(name + "_board", (w, 0.15, h), (0, 0, 0), _m("map_cork", "#a5814f", 0.9), 0.03, parent=root)
    box(name + "_map", (w * 0.86, 0.05, h * 0.82), (0, -0.09, 0), _m("map_paper", "#d8d3c2", 0.9), 0.0, parent=root)
    Mr = _m("map_road", "#7f8a9e", 0.8)
    for k in range(6):
        box(name + f"_rx{k}", (w * 0.84, 0.03, 0.06), (0, -0.12, -h * 0.38 + k * h * 0.15), Mr, 0, parent=root)
        box(name + f"_ry{k}", (0.06, 0.03, h * 0.8), (-w * 0.4 + k * w * 0.16, -0.12, 0), Mr, 0, parent=root)
    rnd = random.Random(3)
    pins = []
    for k in range(7):
        p = (rnd.uniform(-w * 0.38, w * 0.38), -0.2, rnd.uniform(-h * 0.35, h * 0.35))
        pins.append(p)
        sphere(name + f"_pin{k}", 0.12, p, _m("map_pin", "#e0302a", 0.3), parent=root, seg=8)
    box(name + "_core", (0.6, 0.03, 0.6), (w * 0.25, -0.13, h * 0.2), _glow("map_core", "#ff2a2a", 6.0), 0, parent=root)
    for k in range(len(pins) - 1):
        a, b = Vector(pins[k]), Vector(pins[k + 1])
        d = b - a
        c = cyl(name + f"_str{k}", 0.02, d.length, tuple((a + b) / 2), _m("map_str", "#ff3030", 0.6), 6, parent=root)
        c.rotation_mode = "QUATERNION"; c.rotation_quaternion = d.to_track_quat("Z", "Y")
    return root


def blast_door(name, loc, rot=0, w=6.0, h=8.0):
    root = empty(name, loc, None, None, (0, 0, rot), 0.3)
    Ms = _m("bdoor_s", "#5b6475", 0.35, 0.8); Mh = _m("bdoor_h", "#f2c14e", 0.5); Mk = _m("bdoor_k", "#15161a", 0.5)
    box(name + "_frame", (w + 1.2, 1.0, h + 0.8), (0, 0.2, h / 2 + 0.2), Mk, 0.08, parent=root)
    door = box(name + "_door", (w, 0.6, h), (0, -0.2, h / 2), Ms, 0.1, parent=root)
    for k in range(8):
        box(name + f"_hz{k}", (w / 8, 0.05, 0.45), (-w / 2 + (k + 0.5) * w / 8, -0.53, 0.5), Mh if k % 2 == 0 else Mk, 0, parent=root)
    box(name + "_lamp", (1.4, 0.3, 0.3), (0, -0.3, h + 0.5), _glow("bdoor_lamp", "#ff4b2e", 8.0), 0.05, parent=root)
    return root, door


def hideout(t0=0.0, t1=4.0, door=True):
    """Survivors' bunker behind an old server room. Origin ~ (0,0,0); back wall y=10; door on the right wall.
    Props: shelves, bunk, map wall, screens, desk + lamps, old racks, cables, crates, string lights, blast door."""
    _room("ho", (32, 24, 11), "#57524c", "#6a5d50", 10.0, -16.0, 16.0)
    shelf("ho_shelf0", (-12.5, 8.6, 0), 0, 1)
    shelf("ho_shelf1", (-7.8, 8.6, 0), 0, 2)
    bunk("ho_bunk", (-13.0, -2.0, 0), 0)
    map_wall("ho_map", (-1.0, 9.6, 5.2), 0)
    for i in range(2):
        P.server_rack(f"ho_rack{i}", (6.5 + i * 2.6, 8.6, 0), seed=i + 3, units=7)
    # desk with screens and a lamp
    Md = _m("ho_desk", "#6b4a32", 0.6)
    box("ho_desk_top", (6.0, 2.4, 0.2), (8.5, 2.5, 2.6), Md, 0.05)
    for sx in (-1, 1):
        box(f"ho_desk_leg{sx}", (0.2, 2.2, 2.5), (8.5 + sx * 2.8, 2.5, 1.25), Md, 0.03)
    screen("ho_scr0", (7.3, 3.2, 3.9), 0, 2.2, 1.4, "#37ff8b", None)
    screen("ho_scr1", (9.9, 3.1, 3.9), -12, 2.0, 1.3, "#26d9ff", None)
    desk_lamp("ho_dlamp", (11.0, 2.0, 2.7), rot=20)
    P.wood_crate("ho_crate0", (-4.5, 7.5, 0), 1.8, 10)
    P.wood_crate("ho_crate1", (-4.2, 7.4, 1.8), 1.3, -15)
    P.wood_crate("ho_crate2", (13.5, -4.0, 0), 1.6, 30)
    # cables along the ceiling and down the wall
    for k, (a, b) in enumerate((((-16, 9.5, 10), (16, 9.5, 10.2)), ((-10, 9.6, 10), (-10, 0, 10.4)), ((6, 9.6, 10), (14, -2, 9.8)))):
        cable(f"ho_cbl{k}", sag(a, b, 1.6, 6), 0.08)
    cable("ho_drop", [(5.0, 9.6, 10.5), (5.2, 9.5, 6.0), (6.0, 9.4, 1.0), (7.0, 8.6, 0.1)], 0.09)
    # string lights (warm bulbs) across the room
    pts = sag((-15, 6, 9.6), (15, 6, 9.6), 1.4, 13)
    cable("ho_string", pts, 0.025, _m("ho_str", "#2a2a2a", 0.6))
    for k, p in enumerate(pts[1:-1]):
        sphere(f"ho_bulb{k}", 0.16, (p[0], p[1], p[2] - 0.2), _glow("ho_bulb", "#ffc46b", 22.0), seg=8)
    # practical light from the string + a hanging work lamp + green monitor glow
    light("ho_warm", "AREA", (0, 4, 9.3), 4200, (1.0, 0.72, 0.45), 18, target=(0, 2, 0))
    light("ho_hang", "POINT", (-6, 1, 8.2), 1400, (1.0, 0.8, 0.55), 1.0)
    sphere("ho_hang_b", 0.3, (-6, 1, 8.4), _glow("ho_hangb", "#ffd9a0", 25.0), seg=10)
    cyl("ho_hang_sh", 0.8, 0.5, (-6, 1, 8.8), _m("ho_hangsh", "#2e7d5b", 0.5), 16, r2=0.25)
    cable("ho_hang_c", [(-6, 1, 9.0), (-6, 1, 10.6)], 0.03)
    light("ho_scr_glow", "AREA", (8.5, 1.0, 4.0), 500, (0.3, 1.0, 0.65), 3, target=(6, -3, 4))
    bd = None
    if door:
        bd = blast_door("ho_door", (15.6, -4.0, 0), 90)
    dust((0, 0, 0), (28, 18, 9), 70, "#ffe0b0", 2.0)
    return dict(door=bd)


def core_hall(t0=0.0, t1=4.0):
    """Corridor of server racks leading to the AI core vault door. Walk axis: +Y (away from camera)."""
    _room("ch", (16, 60, 11), "#3a4152", "#465068", 40.0, -8.0, 8.0)
    for side in (-1, 1):
        for k in range(8):
            P.server_rack(f"ch_r{side}_{k}", (side * 5.8, -14 + k * 6.5, 0), rot=-90 * side, seed=k + (side > 0) * 9, units=9)
    Mstrip = _glow("ch_strip", "#ff2a3a", 5.0)
    for sx in (-1, 1):
        box(f"ch_floor_strip{sx}", (0.18, 80, 0.05), (sx * 3.6, 6, 0.03), Mstrip, 0)
        box(f"ch_ceil_strip{sx}", (0.3, 80, 0.1), (sx * 2.0, 6, 10.9), _glow("ch_ceil", "#c9d8ff", 6.0), 0)
    for k in range(4):
        cam_pole(f"ch_cam{k}", ((-1) ** k * 7.0, -8 + k * 12, 9.0), 90 * (-1) ** k + 180, h=0)
    cable("ch_cbl0", sag((-7, -20, 10.5), (-7, 40, 10.5), 0.8, 8), 0.12)
    cable("ch_cbl1", sag((7, -20, 10.5), (7, 40, 10.5), 0.9, 8), 0.12)
    door_root, door = blast_door("ch_vault", (0, 39.4, 0), 180, 9, 10)
    # scanner beside the vault door
    box("ch_scan", (1.2, 0.4, 1.8), (5.8, 38.6, 4.2), _m("ch_scan_b", "#1d2230", 0.3, 0.5), 0.08)
    scr = box("ch_scan_s", (0.9, 0.1, 1.2), (5.8, 38.35, 4.3), _glow("ch_scan_g", "#ff2a2a", 6.0), 0.02)
    light("ch_fill", "AREA", (0, 10, 10.4), 22000, (0.7, 0.8, 1.0), 14)
    light("ch_red", "AREA", (0, 36, 9.5), 2500, (1.0, 0.25, 0.25), 10, target=(0, 30, 0))
    dust((0, 10, 0), (12, 50, 10), 80, "#ffb0b0", 1.6)
    return dict(door=door, door_root=door_root)


def core_room(t0=0.0, t1=4.0, eye_loc=(0, 18, 11), r=5.5):
    """The AI core: giant red eye in nested rotating rings, floor cables, terminals, catwalk. Eye pulses."""
    _room("cr", (44, 40, 26), "#1f2330", "#262b39", 30.0, -22.0, 22.0)
    Me = _glow("cr_eye_glow", "#ff2a2a", 10.0)
    Mi = _glow("cr_iris", "#ffd2a0", 30.0)
    Mm = _m("cr_metal", "#3a4152", 0.3, 0.8)
    Mk = _m("cr_black", "#0b0c10", 0.3, 0.3)
    e = Vector(eye_loc)
    sphere("cr_eye_shell", r * 1.06, tuple(e), Mk, seg=40)
    sphere("cr_eye", r, tuple(e + Vector((0, -0.6, 0))), Me, scale=(1, 0.75, 1), seg=40)
    sphere("cr_iris", r * 0.42, tuple(e + Vector((0, -r * 0.62, 0))), Mk, scale=(1, 0.4, 1), seg=24)
    sphere("cr_pupil", r * 0.18, tuple(e + Vector((0, -r * 0.8, 0))), Mi, scale=(1, 0.4, 1), seg=16)
    pulse(Me, t0, t1, 5.0, 14.0, 1.0)
    for k, (rr, tilt) in enumerate(((r * 1.45, 70), (r * 1.75, 110), (r * 2.05, 90))):
        ring = empty(f"cr_ring{k}", tuple(e), None, None, (math.radians(tilt), 0, 0), 0.3)
        tor_n = 28
        for j in range(tor_n):
            a = 2 * math.pi * j / tor_n
            box(f"cr_ring{k}_{j}", (0.5, 1.1, 0.5), (math.cos(a) * rr, math.sin(a) * rr, 0), Mm if j % 4 else Me, 0.06,
                rot=(0, 0, math.degrees(a)), parent=ring)
        ring.rotation_euler = (math.radians(tilt), 0, 0)
        ring.keyframe_insert("rotation_euler", frame=F(t0))
        ring.rotation_euler = (math.radians(tilt), math.radians(30 * (1 if k % 2 else -1) * (t1 - t0) / 4), math.radians(40 * (t1 - t0) / 4 * (1 if k != 1 else -1)))
        ring.keyframe_insert("rotation_euler", frame=F(t1))
        set_interp(ring, "rotation_euler", F(t0), "LINEAR")
    # pedestal, floor cables, terminals, catwalk rail
    cyl("cr_ped", 4.0, 3.0, (e.x, e.y, 1.5), Mm, 32, 0.2)
    cyl("cr_ped_ring", 4.3, 0.2, (e.x, e.y, 3.05), Me, 32)
    cyl("cr_ped_col", 1.6, e.z - r - 2.5, (e.x, e.y, 3 + (e.z - r - 2.5) / 2), Mm, 20)
    rnd = random.Random(4)
    for k in range(9):
        a = math.radians(-160 + k * 40 + rnd.uniform(-8, 8))
        far = e + Vector((math.cos(a) * 24, math.sin(a) * 18 - 6, 0))
        far.z = 0.2
        cable(f"cr_cbl{k}", [tuple(far), tuple(e.lerp(far, 0.6) + Vector((0, 0, 0.2))), (e.x + math.cos(a) * 4.3, e.y + math.sin(a) * 4.3, 0.6)],
              0.22, _m("cr_cbl_m", "#14161c", 0.5))
    for k, x in enumerate((-11, 11)):
        box(f"cr_cons{k}", (4.0, 2.2, 3.2), (x, 4.0, 1.6), Mm, 0.1, rot=(0, 0, 0))
        screen(f"cr_scr{k}", (x, 3.2, 4.4), 0, 3.4, 2.0, "#ff4b4b", "ERROR" if k else None)
    for k in range(2):
        P.server_rack(f"cr_rack{k}", ((-1) ** k * 18, 22, 0), rot=0, seed=20 + k, units=10)
    box("cr_rail", (40, 0.2, 0.2), (0, -6, 2.4), _m("cr_rail_m", "#f2c14e", 0.4), 0.02)
    for j in range(-9, 10):
        box(f"cr_post{j}", (0.15, 0.15, 2.4), (j * 2.2, -6, 1.2), _m("cr_rail_m", "#f2c14e", 0.4), 0.02)
    # light from the eye + cool top fill so people standing in front are readable
    L = light("cr_eye_L", "POINT", tuple(e + Vector((0, -r - 2, 0))), 26000, (1.0, 0.22, 0.2), 3.0)
    light("cr_fill", "AREA", (0, -8, 22), 9000, (0.6, 0.7, 1.0), 30, target=(0, 6, 0))
    dust((0, 8, 0), (36, 26, 18), 90, "#ff9a9a", 2.0)
    return dict(eye=tuple(e), eye_mat=Me, eye_light=L)


# ------------------------------------------------------------------ cast
def _rim(ch, color=(0.5, 0.8, 1.0), energy=600, off=(0, 2.2, 7.0), name=None):
    L = light((name or ch.name) + "_rimL", "POINT", (0, 0, 0), energy, color, 0.6, shadow=False)
    L.parent = ch.root; L.location = off
    return L


def enforcer(t0, t1, expr="neutral", name="Unit7", scale=1.32, visor="#ff2a2a", rim=True):
    """'Unit Seven': taller, darker armoured enforcer with red visor, emissive trim, number plate and a rim light
    so it reads in wide shots. Built on the rig (walks, acts, poses)."""
    ch = chars.Char(name, skin="#d9dee7", shirt="#2a3040", pants="#2a3040", hair="bald", face="plain", sleeves="long", scale=scale)
    Mv = _m(name + "_visor", "#0b0d12", 0.15, 0.3)
    Me = _glow(name + "_eye", visor, 14.0)
    Ma = _m(name + "_armor", "#e8ecf2", 0.28, 0.4, coat=0.5)
    Mt = _glow(name + "_trim", visor, 6.0)
    box(name + "_vis", (1.2, 0.14, 0.42), (0, -0.66, 0.08), Mv, 0.05, parent=ch.head, coll=ch.coll)
    box(name + "_visl", (1.0, 0.05, 0.12), (0, -0.74, 0.08), Me, 0.02, parent=ch.head, coll=ch.coll)
    box(name + "_crest", (0.22, 1.3, 0.3), (0, 0.0, 0.82), Ma, 0.06, parent=ch.head, coll=ch.coll)
    box(name + "_crestl", (0.08, 1.0, 0.06), (0, -0.05, 0.98), Mt, 0.0, parent=ch.head, coll=ch.coll)
    for nm in ("armL", "armR"):
        p = ch.piv(nm)
        box(name + "_pad" + nm, (1.15, 1.15, 0.45), (0, 0, 0.2), Ma, 0.12, parent=p, coll=ch.coll)
        box(name + "_padl" + nm, (1.18, 0.05, 0.08), (0, -0.58, 0.1), Mt, 0.0, parent=p, coll=ch.coll)
        box(name + "_cuff" + nm, (1.08, 1.08, 0.3), (0, 0, -1.25), Ma, 0.06, parent=p, coll=ch.coll)
    box(name + "_chest", (1.9, 0.18, 1.2), (0, -0.52, 1.35), Ma, 0.1, parent=ch.hip, coll=ch.coll)
    t = text(name + "_no", "07", (0, -0.63, 1.32), 0.6, Me, (90, 0, 0), 0.02, ch.coll, None)
    t.parent = ch.hip
    box(name + "_belt", (2.05, 1.05, 0.25), (0, 0, 0.12), Mt, 0.03, parent=ch.hip, coll=ch.coll)
    for nm in ("legL", "legR"):
        box(name + "_knee" + nm, (1.04, 0.2, 0.5), (0, -0.5, -0.9), Ma, 0.06, parent=ch.piv(nm), coll=ch.coll)
        box(name + "_boot" + nm, (1.1, 1.2, 0.5), (0, -0.08, -1.8), Ma, 0.08, parent=ch.piv(nm), coll=ch.coll)
    ch.face(t0, expr)
    ch.breathe(0.35)
    if rim:
        _rim(ch, (1.0, 0.35, 0.3), 900, (0, 3.0, 7.5))
        _rim(ch, (0.55, 0.8, 1.0), 500, (2.5, -3.5, 5.0), name + "_f")
    return ch


def robot2(t0, t1, name="Bot", scale=1.08, eye="#26d9ff", rim=True):
    """Standard white patrol robot (props2.robot) plus emissive trim and its own rim light."""
    ch = P.robot(t0, t1, "neutral", name=name, eye=eye, scale=scale)
    Mt = _glow(name + "_trim", eye, 5.0)
    box(name + "_belt", (2.05, 1.05, 0.18), (0, 0, 0.1), Mt, 0.02, parent=ch.hip, coll=ch.coll)
    for nm in ("legL", "legR"):
        box(name + "_kl" + nm, (1.02, 0.05, 0.1), (0, -0.52, -0.9), Mt, 0.0, parent=ch.piv(nm), coll=ch.coll)
    if rim:
        _rim(ch, (0.45, 0.8, 1.0), 600, (0, 3.0, 7.0))
    return ch


def helper_bot(name, loc, t0, t1, color="#ffcf2e", s=1.0, rot=0):
    """Small round helper bot (knee high) with one big eye and a wobble. Hovers on a glowing ring."""
    root = empty(name, loc, None, None, (0, 0, rot), 0.4)
    root.scale = (s,) * 3
    Mb = _m(name + "_body", color, 0.35, coat=0.4)
    Mk = _m(name + "_k", "#1b1f29", 0.3)
    Me = _glow(name + "_eye", "#7df2ff", 10.0)
    body = sphere(name + "_body", 0.9, (0, 0, 1.3), Mb, scale=(1, 1, 0.9), parent=root, seg=24)
    box(name + "_face", (1.1, 0.2, 0.7), (0, -0.78, 1.4), Mk, 0.15, parent=root)
    sphere(name + "_eye", 0.22, (0, -0.86, 1.4), Me, scale=(1, 0.5, 1), parent=root, seg=12)
    cyl(name + "_ant", 0.04, 0.6, (0.3, 0, 2.3), Mk, 8, parent=root)
    sphere(name + "_antb", 0.1, (0.3, 0, 2.65), _glow(name + "_ab", "#ff4b4b", 12.0), parent=root, seg=8)
    cyl(name + "_ring", 0.7, 0.08, (0, 0, 0.35), _glow(name + "_ring", "#7df2ff", 6.0), 24, parent=root)
    for sx in (-1, 1):
        box(name + f"_arm{sx}", (0.18, 0.18, 0.7), (sx * 0.95, -0.1, 1.1), Mk, 0.05, rot=(0, sx * 25, 0), parent=root)
    noise(root, "location", 2, 0.12, 8)
    noise(root, "rotation_euler", 1, 0.08, 10)
    return root


def drone2(name, loc, t0, t1, s=1.8, rot=0.0, eye="#ff2a2a", beam_to=None, beam_energy=60000):
    """Drone with blinking nav lights, an under-glow ring, antenna; optional searchlight + visible cone."""
    root = P.drone(name, loc, t0, t1, s=s, eye=eye, rot=rot)
    for k, (x, col) in enumerate(((-1.4, "#ff3030"), (1.4, "#37ff8b"))):
        b = sphere(name + f"_nav{k}", 0.1, (x, 1.05, 0.35), _glow(f"nav{k}", col, 20.0), parent=root, seg=8)
    cyl(name + "_ug", 0.42, 0.05, (0, 0, -0.38), _glow("dr_ug" + eye[1:], eye, 6.0), 20, parent=root)
    cyl(name + "_ant", 0.03, 0.6, (0.2, 0.3, 0.6), _m("dr_ant", "#1b1f29", 0.4), 6, parent=root)
    if beam_to is not None:
        P.searchlight(root, beam_to, color=hexc(eye) if eye != "#ff2a2a" else (1.0, 0.25, 0.25), energy=beam_energy, spot=22)
        searchcone(name + "_cone", tuple(Vector(loc) - Vector((0, 0, 0.6 * s))), beam_to, (1.0, 0.3, 0.3), 2.0, 0.06)
    return root


HAIRS = ["messy", "spiky", "bob", "buzz", "cap", "bun", "helmet"]
OUTFITS = [("#5a6f8f", "#2f3442"), ("#8a4b4b", "#33313a"), ("#4f7a5a", "#2c2f38"), ("#7a6a9a", "#30323e"),
           ("#b38a4a", "#3a3428"), ("#3f8a8a", "#2b3038"), ("#9a5a7a", "#343040"), ("#6a6f78", "#24272e")]
SKINS = ["#f1d3b3", "#c48a5c", "#8d5a3b", "#e8b98f", "#5e3a26", "#f6dcc5"]
HAIRC = ["#1b1410", "#5a3a22", "#c9a36e", "#7a2e22", "#2a2a33", "#d8d8d8"]


def citizen(i, t0, t1, expr="neutral", number=None, tag_color="#ff2fb3", scale=1.0, rim=False):
    """Varied, worn-down survivor/citizen: hair, outfit, skin, accessories (scarf/beanie/goggles/vest/backpack/
    glasses) picked from a seed; optional floating number."""
    r = random.Random(i * 13 + 5)
    sh, pa = OUTFITS[i % len(OUTFITS)]
    ex = []
    if r.random() < 0.3:
        ex.append("glasses")
    if r.random() < 0.35:
        ex.append("backpack")
    ch = chars.Char(f"Cit{i}", skin=r.choice(SKINS), shirt=sh, pants=pa, hair=r.choice(HAIRS), hair_color=r.choice(HAIRC),
                    face=r.choice(["plain", "kid", "girl"]), sleeves=r.choice(["long", "short"]), extras=tuple(ex),
                    scale=scale, seed=i)
    n = ch.name
    acc = r.random()
    col = r.choice(["#ffcf2e", "#ff6a3a", "#5ad1ff", "#9d7bff", "#7bd47f", "#e8e2d6"])
    if acc < 0.35:     # scarf
        box(n + "_scarf", (1.55, 1.0, 0.36), (0, -0.02, -0.7), _m("cit_sc" + col[1:], col, 0.7), 0.12, parent=ch.head, coll=ch.coll)
    elif acc < 0.6:    # vest
        box(n + "_vest", (2.08, 1.08, 1.7), (0, 0, 1.1), _m("cit_vest" + col[1:], col, 0.7), 0.08, parent=ch.hip, coll=ch.coll)
        box(n + "_vestgap", (0.3, 0.05, 1.7), (0, -0.55, 1.1), _m("cit_vgap", "#1b1f29", 0.6), 0.0, parent=ch.hip, coll=ch.coll)
    elif acc < 0.8:    # beanie
        box(n + "_beanie", (1.3, 1.3, 0.55), (0, 0, 0.62), _m("cit_bn" + col[1:], col, 0.8), 0.22, parent=ch.head, coll=ch.coll)
    if r.random() < 0.5:   # wrist tag on everybody (world rule)
        box(n + "_band", (1.06, 1.06, 0.3), (0, 0, -1.5), _glow("cit_band" + tag_color[1:], tag_color, 3.0), 0.05, parent=ch.shL, coll=ch.coll)
    ch.face(t0, expr)
    ch.blink(t0, t1)
    ch.breathe(0.8)
    if number is not None:
        P.floating_number(ch, number, tag_color)
    if rim:
        _rim(ch, (0.6, 0.8, 1.0), 350)
    return ch


def wrist_macro(name, loc, number="0", color="#7df2ff", sleeve="#1f6f7a", skin="#c48a5c", rot=0, scan=None):
    """Standalone big forearm + tag for INSERT shots. The arm lies along X, the tag screen faces -Y (camera side),
    the number is big, bright and centred so it reads in a macro. Origin = centre of the tag screen."""
    root = empty(name, loc, None, None, (0, 0, rot), 0.3)
    Mk = _m("wm_band", "#14161c", 0.3, 0.5)
    Msk = _m("wm_skin", skin, 0.45)
    Msl = _m("wm_sleeve", sleeve, 0.75)
    box(name + "_fore", (3.6, 1.0, 1.0), (0.4, 0.45, 0), Msk, 0.18, parent=root)
    box(name + "_sleeve", (2.6, 1.25, 1.25), (3.2, 0.45, 0), Msl, 0.25, parent=root)
    box(name + "_hand", (1.0, 1.0, 1.05), (-1.9, 0.45, 0), Msk, 0.25, parent=root)
    box(name + "_band", (1.5, 1.3, 1.3), (0, 0.45, 0), Mk, 0.12, parent=root)
    box(name + "_bezel", (1.3, 0.1, 1.0), (0, -0.22, 0), _m("wm_bezel", "#2a2f3c", 0.25, 0.6), 0.05, parent=root)
    box(name + "_glass", (1.1, 0.06, 0.8), (0, -0.27, 0), _glow("wm_glass", "#08202a", 1.5), 0.02, parent=root)
    t = text(name + "_num", number, (0, -0.31, 0.0), 0.72, _glow("wm_num" + color[1:], color, 18.0), (90, 0, 0), 0.02, None, None)
    t.parent = root
    for k in range(4):
        box(name + f"_tick{k}", (0.12, 0.04, 0.04), (-0.42 + k * 0.28, -0.3, -0.33), _glow("wm_tick", color, 6.0), 0, parent=root)
    L = light(name + "_L", "POINT", (0, 0, 0), 25, hexc(color), 0.3, shadow=False)
    L.parent = root; L.location = (0, -0.9, 0.2)
    return root


def face_light(target, color=(1.0, 0.85, 0.7), energy=260, d=3.2, yaw=-15, h=0.3, name="facefill"):
    """Small soft light just in front of a face (camera side) so the face always reads."""
    y = math.radians(yaw)
    p = Vector(target) + Vector((math.sin(y) * d, -math.cos(y) * d, h))
    return light(name, "AREA", tuple(p), energy, color, 1.6, target=target, shadow=False)
