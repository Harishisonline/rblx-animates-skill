"""BLOX TOWN v3 - believable, richly dressed town in the REF2 tier-A look (real PBR architecture + toy people).
Modular: every location is a function that builds at its own origin (they never overlap, so a shot can build several),
and every piece (facades, street, props, room shells) is reusable on its own. Locations return a dict:
    {"name", "origin", "look": look preset, "focus": (x,y,z), "cams": {"wide"|"close"|...: (loc, target, lens)}}

    from rbx import town as T
    L = T.main_street(night=False)         # shops (CLOSED signs), sidewalks, lamps, benches, extras, police cameo
    L = T.pharmacy_corner(t0=0)            # dusk corner + giant street screen (same street, its own camera set)
    L = T.school_exterior()                # brick school, flagpole, steel gym, bike racks, students
    L = T.school_hallway()                 # lockers, bulletin board, trophy case, fluorescent panels
    L = T.classroom()                      # desks, chalkboard text, teacher desk, windows
    L = T.kitchen(night=True)              # Harry's kitchen: laptop feed, mug, pendant, fridge notes
    L = T.bedroom() / T.front_hall()       # Harry's bedroom (morning) / front door hallway
    L = T.night_street()                   # empty street, indigo night, amber practicals
    L = T.insert_table(kind="wrist"|"phone")   # tabletop void for ECU inserts (wrist counter / phone UI)
    T.LOCATIONS -> {name: builder}; T.frame(L, "wide") -> returns a core.Cam keyed at t=0 on that camera.
Pieces: facade(), street(), street_lamp(), bench(), trash_can(), hydrant(), planter(), bike(), bike_rack(), car(),
tree(), a_frame(), newspaper_box(), room(), window(), door(), locker_bank(), desk_set(), kitchen_counter(), fridge(), bed().
Materials come from rbx.pbr (CC0 Poly Haven). Scale: character 5.3 tall, doors 8.6, storey 10.5, road lane 7."""
import math, os, random
import bpy
from mathutils import Vector
from .core import box, cyl, sphere, plane, empty, light, mat, hexc, collection, poly_extrude, D, F
from . import pbr, signs as S, crowd as C
from . import ASSETS

# 2026-11-14: hand/fingertip -> cuff/prop contact tolerance (studs). Was 0.2 (pinch) / 0.13 measured; EP1 0:10 left-hand
# sleeve gap shipped under that. Any 'keeps sleeve down / tugs sleeve / holds X' beat must stay under this.
CUFF_TOL = 0.05


def _bbox_gap(a, b):
    """Axis-aligned world-bbox gap between two objects (0 when they overlap/touch)."""
    import mathutils
    def bb(o):
        pts = [o.matrix_world @ mathutils.Vector(c) for c in o.bound_box]
        return [min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]
    (a0, a1), (b0, b1) = bb(a), bb(b)
    d = [max(0.0, b0[i] - a1[i], a0[i] - b1[i]) for i in range(3)]
    return (d[0] ** 2 + d[1] ** 2 + d[2] ** 2) ** 0.5


def hand_on_prop(hand, prop, t0, t1, step=2, tol=None, label="hand_on_prop", fps=None):
    """Build-time contact guard for ANY hand-on-object beat (sleeve cuff, door handle, phone, box).
    hand/prop: objects or names (use the fingertip/palm mesh and the cuff/handle mesh, not the whole rig).
    Samples every `step` frames over [t0, t1] (seconds), INCLUDING the start frame, and prints
    '[label] max gap X studs' plus 'STRESS_FAIL <label>' when the gap is >= tol (default CUFF_TOL).
    Returns (max_gap, per_frame list). Still LOOK at the start-frame still: a bbox touch is necessary, not sufficient."""
    sc = bpy.context.scene
    hand = bpy.data.objects[hand] if isinstance(hand, str) else hand
    prop = bpy.data.objects[prop] if isinstance(prop, str) else prop
    tol = CUFF_TOL if tol is None else tol
    fps = fps or sc.render.fps
    f0, f1 = int(round(t0 * fps)), int(round(t1 * fps))
    keep = sc.frame_current
    out = []
    for f in sorted(set(list(range(f0, f1 + 1, max(1, step))) + [f0, f1])):
        sc.frame_set(f)
        out.append((f, round(_bbox_gap(hand, prop), 4)))
    sc.frame_set(keep)
    gmax = max(g for _, g in out) if out else 9.0
    start = out[0][1] if out else 9.0
    print(f"[{label}] start-frame gap {start:.3f}, max gap {gmax:.3f} studs (tol {tol})"
          + (f"  STRESS_FAIL {label}" if gmax >= tol else ""))
    return gmax, out

ORIGINS = dict(main_street=(0, 0, 0), school_exterior=(220, 0, 0), school_hallway=(400, 0, 0), classroom=(470, 0, 0),
               kitchen=(540, 0, 0), bedroom=(600, 0, 0), front_hall=(660, 0, 0), insert_table=(720, 0, 0))


def _m(hx, r=0.5, metal=0.0):
    return mat(f"tw_{hx}_{r:g}_{metal:g}", hexc(hx), r, metal)


def _g(hx, s=4.0):
    return mat(f"tw_g_{hx}_{s:g}", hexc(hx), 0.4, emit=hexc(hx), estr=s)


GLASS = None


def glass(night=False):
    k = "tw_glass_n" if night else "tw_glass"
    if k in D.materials:
        return D.materials[k]
    return mat(k, hexc("#2a3a4a"), 0.06, 0.0, emit=hexc("#ffcf8a") if night else None, estr=1.6 if night else 0.0)


def _root(name, loc, rot, coll):
    return empty(name, loc, coll=coll, rot=(0, 0, rot))


# ------------------------------------------------------------------ town look presets (look.rig / look.grade accept dicts)
_BASE = dict(world=("sky", 1.0), sun=None, key=None, fill=None, rim=None, gain=1.0)
LOOKS = {
    # warm evening interior: amber practicals, gentle cool fill, NOT blue-graded
    "evening_kitchen": dict(_BASE, fill=None, rim=None, exposure=1.0, sat=1.06, contrast=1.04,
                            bloom=0.2, shadows=(0.99, 0.99, 1.01), lights=(1.05, 1.0, 0.93)),   # r2: no magenta split-tone (pink top third)
    # night exterior: indigo shadows, amber practicals, faces readable
    "warm_night": dict(_BASE, fill=(0.5, (0.6, 0.66, 1.0)), rim=(1600, (0.65, 0.72, 1.0)), sat=1.05, contrast=1.06,
                       bloom=0.35, shadows=(0.96, 0.98, 1.06), lights=(1.1, 1.0, 0.86)),
    "real_dusk": dict(_BASE, fill=(0.5, (0.7, 0.62, 0.9)), rim=(2200, (1.0, 0.62, 0.38)), sat=1.12, contrast=1.08,
                      bloom=0.4, shadows=(0.92, 0.94, 1.08), lights=(1.14, 1.0, 0.84)),
}


def look_preset(name):
    """Resolve a location's look to a dict usable by look.rig/look.grade (town presets first, else rbx.look)."""
    from . import look
    return dict(LOOKS[name]) if name in LOOKS else dict(look.PRESETS[name])


# ------------------------------------------------------------------ sky / environment
def sky(mode="day", strength=None, rot=0.0):
    """day: CC0 partly-cloudy HDRI (real clouds); dusk: sunset HDRI; night: indigo gradient. Returns world."""
    hd = {"day": "kloofendal_48d_partly_cloudy_puresky_1k.hdr"}.get(mode)
    w = D.worlds.new("TownSky"); bpy.context.scene.world = w; w.use_nodes = True
    nt = w.node_tree; bg = next(n for n in nt.nodes if n.type == "BACKGROUND")
    p = os.path.join(ASSETS, "hdri", hd) if hd else None
    if p and os.path.exists(p):
        tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Rotation"].default_value = (0, 0, math.radians(rot))
        env = nt.nodes.new("ShaderNodeTexEnvironment"); env.image = D.images.load(p, check_existing=True)
        nt.links.new(tc.outputs["Generated"], mp.inputs[0]); nt.links.new(mp.outputs[0], env.inputs[0])
        nt.links.new(env.outputs[0], bg.inputs[0])
        bg.inputs[1].default_value = strength or (1.0 if mode == "day" else 0.8)
    else:
        top, bot = {"night": ((0.02, 0.025, 0.09), (0.09, 0.09, 0.22)), "dusk": ((0.06, 0.06, 0.2), (1.0, 0.42, 0.18))}.get(
            mode, ((0.1, 0.25, 0.7), (0.6, 0.7, 0.9)))
        tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(tc.outputs["Generated"], sep.inputs[0])
        cr = nt.nodes.new("ShaderNodeValToRGB")
        cr.color_ramp.elements[0].position = 0.45; cr.color_ramp.elements[0].color = (*bot, 1)
        cr.color_ramp.elements[1].position = 0.8; cr.color_ramp.elements[1].color = (*top, 1)
        nt.links.new(sep.outputs["Z"], cr.inputs[0]); nt.links.new(cr.outputs[0], bg.inputs[0])
        bg.inputs[1].default_value = strength or 1.0
    return w


def sun(strength=4.0, color="#ffe3c0", elev=35, azim=35):
    ld = D.lights.new("TownSun", "SUN"); ld.energy = strength; ld.color = hexc(color); ld.angle = math.radians(2.5)
    ob = D.objects.new("TownSun", ld); bpy.context.scene.collection.objects.link(ob)
    ob.rotation_euler = (math.radians(90 - elev), 0, math.radians(azim))
    return ob


def haze(density=0.006, color=(0.75, 0.8, 0.9)):
    """Cheap world-volume haze for depth (lake town / dusk). Keep <= 0.01 for EEVEE speed."""
    w = bpy.context.scene.world
    nt = w.node_tree; out = next(n for n in nt.nodes if n.type == "OUTPUT_WORLD")
    sc = nt.nodes.new("ShaderNodeVolumeScatter"); sc.inputs["Density"].default_value = density
    sc.inputs["Color"].default_value = (*color, 1); nt.links.new(sc.outputs[0], out.inputs["Volume"])


# ------------------------------------------------------------------ street pieces
def street(name, o=(0, 0, 0), length=140, road=14.0, walk=6.0, coll=None, cobble_plaza=None):
    """Street along +Y from o: asphalt road, painted lanes, kerbs, concrete sidewalks both sides."""
    x0, y0, z0 = o
    yc = y0 + length / 2
    box(name + "_road", (road, length, 0.2), (x0, yc, z0 - 0.1), pbr.get("asphalt"), 0.0, coll=coll)
    paint = _m("#f2efe6", 0.6); yel = _m("#f2c14e", 0.6)
    for i in range(int(length / 6)):
        box(f"{name}_ln{i}", (0.3, 2.6, 0.02), (x0, y0 + 3 + i * 6, z0 + 0.01), yel, 0.0, coll=coll)
    for s in (-1, 1):
        box(f"{name}_kerb{s}", (0.5, length, 0.45), (x0 + s * (road / 2 + 0.25), yc, z0 + 0.0), pbr.get("concrete", tint="#cfcac0"), 0.06, coll=coll)
        box(f"{name}_walk{s}", (walk, length, 0.4), (x0 + s * (road / 2 + 0.5 + walk / 2), yc, z0 - 0.0), pbr.get("concrete"), 0.02, coll=coll)
        box(f"{name}_edge{s}", (0.15, length, 0.02), (x0 + s * (road / 2 - 0.6), yc, z0 + 0.01), paint, 0.0, coll=coll)
    # crosswalk near start
    for i in range(7):
        box(f"{name}_zb{i}", (1.2, 4.0, 0.02), (x0 - road / 2 + 1.5 + i * 1.9, y0 + 8, z0 + 0.015), paint, 0.0, coll=coll)
    cyl(name + "_manhole", 1.0, 0.04, (x0 + 3, y0 + 30, z0 + 0.02), pbr.get("steel", tint="#6a6a6a"), 24, coll=coll)
    if cobble_plaza:
        cx, cy, w, d = cobble_plaza
        box(name + "_plaza", (w, d, 0.2), (cx, cy, z0 + 0.08), pbr.get("cobble"), 0.0, coll=coll)


def street_lamp(name, loc, rot=0.0, on=False, coll=None, power=2200):
    r = _root(name, loc, rot, coll)
    iron = _m("#1e2124", 0.35, 0.6)
    cyl(name + "_base", 0.45, 1.0, (0, 0, 0.5), iron, 12, parent=r, coll=coll)
    cyl(name + "_p", 0.18, 9.5, (0, 0, 5.2), iron, 12, parent=r, coll=coll)
    box(name + "_cap", (1.0, 1.0, 0.25), (0, 0, 9.9), iron, 0.05, parent=r, coll=coll)
    box(name + "_lan", (0.8, 0.8, 1.2), (0, 0, 10.6), _g("#ffc977", 6.0 if on else 0.6), 0.08, parent=r, coll=coll)
    box(name + "_top", (1.2, 1.2, 0.3), (0, 0, 11.35), iron, 0.08, parent=r, coll=coll)
    if on:
        light(name + "_L", "POINT", (loc[0], loc[1], loc[2] + 10.4), power, hexc("#ffb867"), 0.6, coll=coll, shadow=False)
    return r


def bench(name, loc, rot=0.0, coll=None):
    r = _root(name, loc, rot, coll)
    wd = pbr.get("planks", tint="#c08a5a", tile=3)
    for k in range(3):
        box(f"{name}_s{k}", (4.2, 0.36, 0.14), (0, -0.45 + k * 0.42, 1.4), wd, 0.03, parent=r, coll=coll)
    for k in range(2):
        box(f"{name}_b{k}", (4.2, 0.12, 0.34), (0, 0.6, 1.9 + k * 0.45), wd, 0.03, parent=r, coll=coll)
    for s in (-1, 1):
        box(f"{name}_l{s}", (0.18, 1.3, 1.35), (s * 1.8, 0, 0.68), _m("#1e2124", 0.35, 0.6), 0.03, parent=r, coll=coll)
    return r


def trash_can(name, loc, coll=None):
    cyl(name, 0.6, 1.9, (loc[0], loc[1], loc[2] + 0.95), pbr.get("steel", tint="#2f5a3a"), 16, 0.04, coll=coll)
    cyl(name + "_lid", 0.66, 0.15, (loc[0], loc[1], loc[2] + 1.95), _m("#1e2124", 0.4, 0.5), 16, 0.03, coll=coll)


def hydrant(name, loc, coll=None):
    red = _m("#c62828", 0.35)
    cyl(name, 0.35, 1.3, (loc[0], loc[1], loc[2] + 0.65), red, 12, 0.03, coll=coll)
    sphere(name + "_t", 0.36, (loc[0], loc[1], loc[2] + 1.3), red, seg=12, coll=coll)
    cyl(name + "_n", 0.16, 0.9, (loc[0], loc[1], loc[2] + 0.9), red, 10, rot=(0, 90, 0), coll=coll)


def planter(name, loc, coll=None, s=1.0, flowers=True, seed=0):
    rnd = random.Random(seed)
    box(name, (2.2 * s, 2.2 * s, 1.2 * s), (loc[0], loc[1], loc[2] + 0.6 * s), pbr.get("concrete", tint="#bdb5a6"), 0.08, coll=coll)
    sphere(name + "_bu", 1.15 * s, (loc[0], loc[1], loc[2] + 1.6 * s), _m("#3f6e2a", 0.8), (1, 1, 0.7), coll=coll, seg=14)
    if flowers:
        for k in range(5):
            sphere(f"{name}_f{k}", 0.18 * s, (loc[0] + rnd.uniform(-0.8, 0.8) * s, loc[1] + rnd.uniform(-0.8, 0.8) * s,
                   loc[2] + 2.2 * s), _m(rnd.choice(["#ff5a7a", "#ffd23a", "#ffffff", "#b46bff"])), seg=8, coll=coll)


def tree(name, loc, s=1.0, seed=0, coll=None):
    """Molded canopy: 3-4 large smooth squashed clumps (one leaf material w/ noise tint), trunk w/ root flare + 2 limbs."""
    rnd = random.Random(seed)
    x, y, z = loc
    bark = pbr.get("timber", tint="#7a5a44", tile=2.5)
    cyl(name + "_t", 0.5 * s, 6.2 * s, (x, y, z + 3.1 * s), bark, 12, 0.05, coll=coll)
    cyl(name + "_fl", 0.85 * s, 0.6 * s, (x, y, z + 0.3 * s), bark, 12, 0.2, coll=coll)
    for k in range(2):
        a = rnd.uniform(0, 360)
        cyl(f"{name}_lb{k}", 0.22 * s, 3.0 * s, (x + math.cos(math.radians(a)) * 0.7 * s, y + math.sin(math.radians(a)) * 0.7 * s,
            z + 6.6 * s), bark, 8, rot=(35, 0, a), coll=coll)
    leaf = _leaf_mat()
    clumps = [(0, 0, 8.6, 3.0), (1.6, 0.6, 7.6, 2.2), (-1.5, -0.4, 7.8, 2.3), (0.3, -1.4, 9.6, 1.9)]
    for i, (dx, dy, dz, r) in enumerate(clumps):
        a = rnd.uniform(0, 6.28)
        ob = sphere(f"{name}_c{i}", r * s, (x + dx * s, y + dy * s, z + dz * s), leaf, (1.0, 1.0, 0.78), coll=coll, seg=24,
                    rot=(0, 0, math.degrees(a)))
        ob.data.polygons.foreach_set("use_smooth", [True] * len(ob.data.polygons))


def _leaf_mat():
    if "tw_leaf" in D.materials:
        return D.materials["tw_leaf"]
    m = D.materials.new("tw_leaf"); m.use_nodes = True
    nt = m.node_tree; N, L = nt.nodes, nt.links
    b = next(n for n in N if n.type == "BSDF_PRINCIPLED"); b.inputs["Roughness"].default_value = 0.75
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 1.6
    tc = N.new("ShaderNodeTexCoord"); L.new(tc.outputs["Object"], nz.inputs[0])
    cr = N.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].color = (*hexc("#3b6527"), 1); cr.color_ramp.elements[1].color = (*hexc("#6f9a3e"), 1)
    L.new(nz.outputs["Fac"], cr.inputs[0]); L.new(cr.outputs[0], b.inputs["Base Color"])
    nz2 = N.new("ShaderNodeTexNoise"); nz2.inputs["Scale"].default_value = 9.0
    L.new(tc.outputs["Object"], nz2.inputs[0])
    bp = N.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.35
    L.new(nz2.outputs["Fac"], bp.inputs["Height"]); L.new(bp.outputs[0], b.inputs["Normal"])
    m.diffuse_color = (*hexc("#4f7f34"), 1)
    return m


def _torus(name, R, r, loc, m, parent=None, coll=None, rot=(90, 0, 0), seg=32, mseg=8):
    import bmesh
    me = D.meshes.new(name); bm = bmesh.new()
    vs = []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        ring = []
        for j in range(mseg):
            b = 2 * math.pi * j / mseg
            rr = R + r * math.cos(b)
            ring.append(bm.verts.new((rr * math.cos(a), rr * math.sin(a), r * math.sin(b))))
        vs.append(ring)
    for i in range(seg):
        for j in range(mseg):
            bm.faces.new((vs[i][j], vs[(i + 1) % seg][j], vs[(i + 1) % seg][(j + 1) % mseg], vs[i][(j + 1) % mseg]))
    bm.to_mesh(me); bm.free()
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    ob = D.objects.new(name, me)
    (coll or bpy.context.scene.collection).objects.link(ob)
    ob.parent = parent; ob.location = loc; ob.rotation_euler = [math.radians(v) for v in rot]
    me.materials.append(m)
    return ob


def wheel(name, loc, parent=None, coll=None, R=1.0):
    """Bike wheel: rubber tyre torus, silver rim torus, 12 spokes, hub."""
    tyre = _m("#161616", 0.75); chrome = _m("#c8ccd0", 0.25, 0.95)
    _torus(name + "_ty", R - 0.09, 0.09, loc, tyre, parent, coll)
    _torus(name + "_rm", R - 0.2, 0.035, loc, chrome, parent, coll, mseg=6)
    cyl(name + "_hub", 0.1, 0.22, loc, chrome, 12, rot=(90, 0, 0), parent=parent, coll=coll)
    for k in range(12):
        a = k * 15.0
        box(f"{name}_sp{k}", (0.02, 0.02, 2 * (R - 0.22)), loc, chrome, 0.0, rot=(0, a, 0), parent=parent, coll=coll)


def bike(name, loc, rot=0.0, color="#d9453a", coll=None):
    r = _root(name, loc, rot, coll)
    fr = _m(color, 0.35, 0.3)
    for s in (-1, 1):
        wheel(f"{name}_w{s}", (s * 1.3, 0, 1.0), r, coll)
    box(name + "_f1", (2.0, 0.12, 0.14), (0.05, 0, 1.75), fr, 0.03, rot=(0, -4, 0), parent=r, coll=coll)
    box(name + "_f2", (1.75, 0.12, 0.14), (0.25, 0, 1.33), fr, 0.03, rot=(0, -28, 0), parent=r, coll=coll)
    box(name + "_f3", (0.12, 0.12, 1.2), (-0.65, 0, 1.55), fr, 0.03, rot=(0, -12, 0), parent=r, coll=coll)
    for sy in (-1, 1):
        box(f"{name}_cs{sy}", (1.4, 0.06, 0.08), (-0.6, sy * 0.1, 1.0), fr, 0.0, parent=r, coll=coll)
        box(f"{name}_ss{sy}", (0.06, 0.06, 1.25), (-0.95, sy * 0.1, 1.5), fr, 0.0, rot=(0, -35, 0), parent=r, coll=coll)
    box(name + "_seat", (0.75, 0.35, 0.16), (-0.75, 0, 2.3), _m("#111111", 0.6), 0.06, parent=r, coll=coll)
    box(name + "_sp", (0.08, 0.08, 0.5), (-0.72, 0, 2.05), _m("#c8ccd0", 0.25, 0.9), 0.0, parent=r, coll=coll)
    box(name + "_fk", (0.1, 0.1, 1.45), (1.18, 0, 1.65), fr, 0.0, rot=(0, -12, 0), parent=r, coll=coll)
    box(name + "_bar", (0.08, 1.4, 0.08), (1.05, 0, 2.4), _m("#222222", 0.4, 0.6), 0.02, parent=r, coll=coll)
    for sy in (-1, 1):
        box(f"{name}_gr{sy}", (0.14, 0.3, 0.14), (1.05, sy * 0.7, 2.4), _m("#111111", 0.8), 0.04, parent=r, coll=coll)
    cyl(name + "_cr", 0.28, 0.06, (0.0, -0.12, 1.0), _m("#888888", 0.3, 0.9), 16, rot=(90, 0, 0), parent=r, coll=coll)
    return r


def bike_rack(name, loc, rot=0.0, n_bikes=3, coll=None, seed=0):
    rnd = random.Random(seed)
    r = _root(name, loc, rot, coll)
    st = pbr.get("steel", tint="#9aa3ab")
    for k in range(6):
        box(f"{name}_u{k}", (0.12, 0.12, 2.0), (-5 + k * 2, 0, 1.0), st, 0.03, parent=r, coll=coll)
        box(f"{name}_ut{k}", (0.12, 1.6, 0.12), (-5 + k * 2, 0, 2.0), st, 0.03, parent=r, coll=coll)
    box(name + "_rail", (11, 0.14, 0.14), (0, 0, 0.3), st, 0.03, parent=r, coll=coll)
    for k in range(n_bikes):
        bk = bike(f"{name}_bk{k}", (0, 0, 0), 90, rnd.choice(["#d9453a", "#2f7bff", "#2f8a55", "#f2c14e", "#8a2be2"]), coll)
        bk.parent = r; bk.location = (-4 + k * 2.6, 0, 0); bk.rotation_euler[2] = 0
    return r


def car(name, loc, rot=0.0, color="#2f7bff", coll=None):
    """Chunky toy-ish sedan (Roblox car proportions), ~11 long."""
    r = _root(name, loc, rot, coll)
    body = mat(f"tw_car_{color}", hexc(color), 0.25, 0.3, coat=0.8)
    box(name + "_b", (5.0, 11, 2.0), (0, 0, 1.9), body, 0.3, parent=r, coll=coll)
    box(name + "_c", (4.4, 5.5, 1.8), (0, 0.5, 3.6), body, 0.3, parent=r, coll=coll)
    g = glass()
    box(name + "_ws", (4.0, 0.1, 1.4), (0, -2.3, 3.6), g, 0.05, rot=(-20, 0, 0), parent=r, coll=coll)
    for s in (-1, 1):
        box(f"{name}_sw{s}", (0.1, 4.6, 1.3), (s * 2.21, 0.5, 3.6), g, 0.02, parent=r, coll=coll)
        for yy in (-3.5, 3.5):
            cyl(f"{name}_t{s}{yy}", 1.0, 0.8, (s * 2.4, yy, 1.0), _m("#151515", 0.7), 20, rot=(0, 90, 0), parent=r, coll=coll)
            cyl(f"{name}_r{s}{yy}", 0.55, 0.82, (s * 2.4, yy, 1.0), _m("#c8ccd0", 0.3, 0.9), 16, rot=(0, 90, 0), parent=r, coll=coll)
        box(f"{name}_hl{s}", (1.0, 0.1, 0.45), (s * 1.6, -5.5, 2.2), _g("#fff4d6", 2), 0.05, parent=r, coll=coll)
        box(f"{name}_tl{s}", (1.0, 0.1, 0.4), (s * 1.6, 5.5, 2.2), _g("#ff2a2a", 2), 0.05, parent=r, coll=coll)
    return r


def police_car(name, loc, rot=0.0, coll=None, lights_on=True):
    r = car(name, loc, rot, "#f4f6f8", coll)
    box(name + "_door", (5.06, 4.0, 1.0), (0, 0.2, 1.9), _m("#141a2e", 0.3), 0.1, parent=r, coll=coll)
    box(name + "_bar", (3.0, 0.8, 0.3), (0, 0.5, 4.65), _m("#222222"), 0.05, parent=r, coll=coll)
    box(name + "_lr", (1.3, 0.7, 0.3), (-0.75, 0.5, 4.8), _g("#ff2a2a", 8 if lights_on else 1), 0.05, parent=r, coll=coll)
    box(name + "_lb", (1.3, 0.7, 0.3), (0.75, 0.5, 4.8), _g("#2a6aff", 8 if lights_on else 1), 0.05, parent=r, coll=coll)
    for s in (-1, 1):
        S.label(f"{name}_txt{s}", "POLICE", (s * 2.56, 0.2, 1.9), 0.55, "#ffffff", "bold", 0, r, coll, rot=(90, 0, s * 90))
    return r


def a_frame(name, loc, rot=0.0, body="TODAY:\nHot cocoa $2\nCookies!", coll=None):
    """Sandwich-board chalk sign (handwriting) - great foreground clutter."""
    r = _root(name, loc, rot, coll)
    wd = pbr.get("planks", tint="#b88a5a", tile=3)
    for s in (-1, 1):
        p = empty(f"{name}_pv{s}", (0, 0, 2.6), parent=r, coll=coll, rot=(s * 12, 0, 0))
        box(f"{name}_bd{s}", (1.9, 0.12, 2.8), (0, s * 0.06, -1.3), wd, 0.04, parent=p, coll=coll)
        if s < 0:
            box(f"{name}_ck", (1.6, 0.03, 2.3), (0, -0.08, -1.3), _m("#22352b", 0.9), 0, parent=p, coll=coll)
            S.label(f"{name}_t", body, (0, -0.1, -1.25), 0.22, "#eef2ea", "hand", 0, p, coll)
    return r


def newspaper_box(name, loc, rot=0.0, coll=None, color="#2f7bff", head="DAILY BLOX"):
    r = _root(name, loc, rot, coll)
    box(name + "_b", (1.4, 1.2, 2.6), (0, 0, 1.6), _m(color, 0.35, 0.2), 0.08, parent=r, coll=coll)
    box(name + "_w", (1.1, 0.05, 0.9), (0, -0.62, 2.2), glass(), 0.02, parent=r, coll=coll)
    S.label(name + "_h", head, (0, -0.62, 2.95), 0.18, "#ffffff", "bold", 0, r, coll)
    return r


# ------------------------------------------------------------------ architecture
def window(name, loc, w=2.6, h=3.4, parent=None, coll=None, trim="#efe9dc", night=False, lit=False, flower=False,
           shutters=None, view=None):
    """Framed sash window on a wall facing -Y (local). view='#hex' = glowing outside view (use for interiors)."""
    tm = _m(trim, 0.45)
    gm = _g(view, 2.0) if view else glass(night and lit)
    box(name + "_gl", (w, 0.12, h), (loc[0], loc[1] + 0.05, loc[2]), gm, 0.0, parent=parent, coll=coll)
    for s in (-1, 1):
        box(f"{name}_fv{s}", (0.22, 0.3, h + 0.2), (loc[0] + s * w / 2, loc[1], loc[2]), tm, 0.04, parent=parent, coll=coll)
        box(f"{name}_fh{s}", (w + 0.2, 0.3, 0.22), (loc[0], loc[1], loc[2] + s * h / 2), tm, 0.04, parent=parent, coll=coll)
        if shutters:
            box(f"{name}_sh{s}", (w * 0.45, 0.14, h), (loc[0] + s * (w * 0.75 + 0.2), loc[1] - 0.05, loc[2]),
                _m(shutters, 0.55), 0.04, parent=parent, coll=coll)
    box(name + "_mul", (0.1, 0.2, h), (loc[0], loc[1], loc[2]), tm, 0.0, parent=parent, coll=coll)
    box(name + "_mh", (w, 0.2, 0.1), (loc[0], loc[1], loc[2] + 0.2), tm, 0.0, parent=parent, coll=coll)
    box(name + "_sill", (w + 0.6, 0.6, 0.18), (loc[0], loc[1] - 0.2, loc[2] - h / 2 - 0.15), tm, 0.04, parent=parent, coll=coll)
    if flower:
        box(name + "_fb", (w, 0.6, 0.5), (loc[0], loc[1] - 0.45, loc[2] - h / 2 - 0.45), pbr.get("planks", tint="#8a5a36", tile=2), 0.04, parent=parent, coll=coll)
        for k in range(4):
            sphere(f"{name}_fl{k}", 0.3, (loc[0] - w / 2 + 0.4 + k * (w - 0.8) / 3, loc[1] - 0.45, loc[2] - h / 2 - 0.1),
                   _m(["#ff5a7a", "#ffd23a", "#3f6e2a", "#ff8a3a"][k], 0.7), seg=8, parent=parent, coll=coll)


def door(name, loc, w=4.0, h=8.6, parent=None, coll=None, color="#2f5a3a", glass_top=True, trim="#efe9dc"):
    box(name + "_d", (w, 0.3, h), (loc[0], loc[1] + 0.05, loc[2] + h / 2), _m(color, 0.4), 0.05, parent=parent, coll=coll)
    for s in (-1, 1):
        box(f"{name}_f{s}", (0.3, 0.45, h + 0.3), (loc[0] + s * (w / 2 + 0.15), loc[1], loc[2] + h / 2), _m(trim), 0.04, parent=parent, coll=coll)
    box(name + "_ft", (w + 0.9, 0.45, 0.35), (loc[0], loc[1], loc[2] + h + 0.15), _m(trim), 0.04, parent=parent, coll=coll)
    if glass_top:
        box(name + "_g", (w * 0.6, 0.35, h * 0.32), (loc[0], loc[1], loc[2] + h * 0.72), glass(), 0.02, parent=parent, coll=coll)
    sphere(name + "_kn", 0.16, (loc[0] + w * 0.36, loc[1] - 0.25, loc[2] + h * 0.47), _m("#d9a520", 0.25, 0.9), seg=10, parent=parent, coll=coll)
    box(name + "_step", (w + 1.2, 1.4, 0.4), (loc[0], loc[1] - 0.6, loc[2] + 0.2), pbr.get("concrete"), 0.04, parent=parent, coll=coll)


def facade(name, loc, rot=0.0, w=14.0, d=12.0, floors=2, style="brick", tint=None, sign=None, sign_bg="#24323f",
           sign_fg="#f3e6c4", awning=None, shop=True, closed=None, night=False, coll=None, seed=0, roof=None,
           door_color="#2f5a3a", shutters=None, display=True, blade=True):
    """Building with a dressed street front facing local -Y. style: brick | timber (half-timber) | plaster | steel.
    closed: None (no sign) | True (CLOSED) | float t_flip (OPEN -> CLOSED at t). Returns root empty."""
    rnd = random.Random(seed)
    r = _root(name, loc, rot, coll)
    H = floors * 10.5
    wall = {"brick": lambda: pbr.get("brick", tint=tint), "timber": lambda: pbr.get("plaster", tint=tint or "#f1e3c4"),
            "plaster": lambda: pbr.get("plaster", tint=tint or "#e8d2b0"), "steel": lambda: pbr.get("steel", tint=tint)}[style]()
    box(name + "_mass", (w, d, H), (0, d / 2, H / 2), wall, 0.05, parent=r, coll=coll)
    trim = "#efe9dc" if style != "steel" else "#3a4048"
    stone = pbr.get("concrete", tint="#d8d0c0")
    box(name + "_plinth", (w + 0.3, 0.5, 1.0), (0, -0.1, 0.5), stone, 0.04, parent=r, coll=coll)
    box(name + "_corn", (w + 0.8, 1.2, 0.8), (0, 0.1, H - 0.2), stone if style != "timber" else pbr.get("timber"), 0.06, parent=r, coll=coll)
    if (roof or ("pitched" if style == "timber" else "flat")) == "pitched":
        rf = pbr.get("roof")
        for s in (-1, 1):
            box(f"{name}_rf{s}", (w + 1.2, d * 0.62, 0.4), (0, d / 2 + s * d * 0.25, H + d * 0.18), rf, 0.05,
                rot=(s * 35, 0, 0), parent=r, coll=coll)
        poly_extrude(name + "_gab", [(0, H), (d, H), (d / 2, H + 0.36 * d)], w, (-w / 2, 0, 0), wall, rot=(90, 0, 90),
                     parent=r, coll=coll)
    else:
        roof_clutter(name, r, w, d, H, rnd, coll, stone=stone)
    # upper floors windows
    nwin = max(1, int(w / 4.6))
    for f in range(1, floors):
        z = f * 10.5 + 5.0
        for i in range(nwin):
            x = -w / 2 + (i + 0.5) * w / nwin
            window(f"{name}_w{f}{i}", (x, -0.15, z), 2.6, 3.8, r, coll, trim, night, lit=night and rnd.random() < 0.6,
                   flower=(style == "timber"), shutters=shutters)
    # half-timber beams
    if style == "timber":
        tb = pbr.get("timber", tint="#5a3e2c")
        for f in range(1, floors + 1):
            box(f"{name}_hb{f}", (w, 0.35, 0.5), (0, -0.2, f * 10.5 - 0.3), tb, 0.03, parent=r, coll=coll)
        for i in range(nwin + 1):
            x = -w / 2 + i * w / nwin
            box(f"{name}_vb{i}", (0.5, 0.35, 10.5 * (floors - 1)), (x, -0.2, 10.5 + 10.5 * (floors - 1) / 2), tb, 0.03, parent=r, coll=coll)
            if i < nwin:
                for sgn in (-1, 1):
                    box(f"{name}_br{i}{sgn}", (0.4, 0.3, 4.2), (x + w / nwin * (0.12 if sgn < 0 else 0.88), -0.2, 12.4), tb, 0.02,
                        rot=(0, sgn * 35, 0), parent=r, coll=coll)
    # ground floor
    if shop:
        dw = 4.0
        dx = w / 2 - dw / 2 - 1.0
        door(name + "_dr", (dx, -0.1, 0), dw, 8.4, r, coll, door_color)
        sw = w - dw - 3.5
        sx = -w / 2 + 1.0 + sw / 2
        box(name + "_sw", (sw, 0.2, 6.0), (sx, -0.05, 4.4), glass(night), 0.0, parent=r, coll=coll)
        tm = _m(trim, 0.45)
        for s in (-1, 1):
            box(f"{name}_swf{s}", (0.3, 0.45, 6.4), (sx + s * sw / 2, -0.1, 4.4), tm, 0.04, parent=r, coll=coll)
        box(name + "_swb", (sw + 0.3, 0.6, 1.4), (sx, -0.15, 0.7), tm, 0.04, parent=r, coll=coll)
        box(name + "_swt", (sw + 0.3, 0.45, 0.3), (sx, -0.1, 7.5), tm, 0.04, parent=r, coll=coll)
        if display:  # clutter inside the shop window
            for k in range(6):
                x = sx - sw / 2 + 0.8 + k * (sw - 1.6) / 5
                col = rnd.choice(["#c62828", "#2f7bff", "#f2c14e", "#2f8a55", "#ffffff", "#ff7a1f"])
                if k % 2:
                    cyl(f"{name}_dp{k}", 0.35, rnd.uniform(0.8, 1.6), (x, 0.8, 2.4), _m(col, 0.3), 12, parent=r, coll=coll)
                else:
                    box(f"{name}_dp{k}", (1.0, 0.8, rnd.uniform(0.8, 1.8)), (x, 0.8, 2.3), _m(col, 0.5), 0.05, parent=r, coll=coll)
            box(name + "_shelf", (sw, 1.6, 0.15), (sx, 0.9, 1.5), pbr.get("planks"), 0.02, parent=r, coll=coll)
            if night:
                light(name + "_in", "AREA", (sx, 3, 7), 300, hexc("#ffd29a"), 4, rot=(0, 0, 0), coll=coll, shadow=False).parent = r
        if sign:
            S.sign(name + "_sg", sign, (0, -0.4, 9.3), w=w - 1.5, h=2.2, bg=sign_bg, fg=sign_fg, coll=coll, parent=r,
                   lit=2.0 if night else 0.0)
        if blade:
            bl = _root(name + "_blade", (-w / 2 + 1.2, -1.9, 11.6), 90, coll); bl.parent = r
            box(name + "_bla", (0.12, 3.2, 0.12), (0, 1.0, 1.3), _m("#1e2124", 0.35, 0.6), 0.02, parent=bl, coll=coll)
            S.sign(name + "_bls", sign, (0, 0, 0), w=max(3.0, 0.62 * len(sign)), h=1.5, bg=sign_bg, fg=sign_fg, coll=coll,
                   parent=bl, lit=2.5 if night else 0.0, depth=0.3)
            S.label(name + "_blb", sign, (0, 0.18, 0), 0.75, sign_fg, "bold", 2.5 if night else 0, bl, coll, rot=(90, 0, 180))
        if awning:
            for k in range(int(sw / 1.2)):
                box(f"{name}_aw{k}", (1.2, 3.0, 0.12), (sx - sw / 2 + 0.6 + k * 1.2, -1.4, 8.3),
                    pbr.get("fabric", tint=awning if k % 2 else "#f4efe2", tile=2), 0.02, rot=(-22, 0, 0), parent=r, coll=coll)
        if closed is not None:
            S.closed_sign(name + "_cl", (dx, -0.35, 6.3), 0, coll, None if closed is True else closed, parent=r)
    else:
        if sign:
            S.sign(name + "_sg", sign, (0, -0.4, 9.6), w=min(12, w - 2), h=1.8, bg=sign_bg, fg=sign_fg, coll=coll, parent=r)
        door(name + "_dr", (0, -0.1, 0), 4.0, 8.4, r, coll, door_color)
        for s in (-1, 1):
            window(f"{name}_gw{s}", (s * w / 3.2, -0.15, 5.0), 2.6, 3.8, r, coll, trim, night, lit=night, shutters=shutters)
    return r


# ------------------------------------------------------------------ interior pieces
def room(prefix, o, w=24, d=18, h=11, floor="woodfloor", wall=("plaster", "#efe2c8"), coll=None, ceiling=True,
         wainscot=None, front=False, base="#f4efe2", fill=1.0, ceil="#f2efe8"):
    """Room shell open toward -Y (camera side). o = centre of the floor's front edge. Returns dict of surfaces."""
    x, y, z = o
    fm = pbr.get(floor) if isinstance(floor, str) else floor
    wm = pbr.get(wall[0], tint=wall[1])
    out = {}
    out["floor"] = box(prefix + "_floor", (w, d, 0.3), (x, y + d / 2, z - 0.15), fm, 0.0, coll=coll)
    out["back"] = box(prefix + "_back", (w, 0.4, h), (x, y + d + 0.2, z + h / 2), wm, 0.0, coll=coll)
    for s in (-1, 1):
        out[f"side{s}"] = box(f"{prefix}_side{s}", (0.4, d, h), (x + s * (w / 2 + 0.2), y + d / 2, z + h / 2), wm, 0.0, coll=coll)
    if front:
        box(prefix + "_front", (w, 0.4, h), (x, y - 0.2, z + h / 2), wm, 0.0, coll=coll)
    if fill:
        light(prefix + "_fill", "AREA", (x, y + d / 2, z + h - 0.4), w * d * 3.0 * fill, hexc("#fff1dc"), w * 0.8, coll=coll,
              size_y=d * 0.8, shadow=False)
    if ceiling:
        out["ceil"] = box(prefix + "_ceil", (w + 1, d + 1, 0.3), (x, y + d / 2, z + h + 0.15), _m(ceil, 0.95), 0.0, coll=coll)
    bm = _m(base, 0.45)
    box(prefix + "_bb", (w, 0.15, 0.5), (x, y + d - 0.05, z + 0.25), bm, 0.02, coll=coll)
    for s in (-1, 1):
        box(f"{prefix}_bbs{s}", (0.15, d, 0.5), (x + s * (w / 2 - 0.05), y + d / 2, z + 0.25), bm, 0.02, coll=coll)
    if wainscot:
        wsm = pbr.get(wainscot[0], tint=wainscot[1], tile=3)
        box(prefix + "_wsb", (w, 0.12, 3.6), (x, y + d - 0.06, z + 1.8), wsm, 0.02, coll=coll)
        for s in (-1, 1):
            box(f"{prefix}_wss{s}", (0.12, d, 3.6), (x + s * (w / 2 - 0.06), y + d / 2, z + 1.8), wsm, 0.02, coll=coll)
    return out


def ceiling_panel(name, loc, coll=None, power=900, color="#f4f7ff", size=(4, 2)):
    box(name, (size[0], size[1], 0.12), loc, _g(color, 3.0), 0.02, coll=coll)
    # emitter is half the visible panel: crisper contact shadows under feet / on walls (a 4x2 emitter washed them out)
    return light(name + "_L", "AREA", (loc[0], loc[1], loc[2] - 0.2), power, hexc(color), size[0] * 0.5, coll=coll,
                 size_y=size[1] * 0.5)


def wall_clock(name, loc, rot=0.0, coll=None):
    r = _root(name, loc, rot, coll)
    cyl(name + "_b", 0.9, 0.2, (0, 0, 0), _m("#1e1e1e", 0.4), 24, rot=(90, 0, 0), parent=r, coll=coll)
    cyl(name + "_f", 0.78, 0.22, (0, -0.02, 0), _m("#fbfaf5", 0.6), 24, rot=(90, 0, 0), parent=r, coll=coll)
    box(name + "_h", (0.08, 0.05, 0.45), (0, -0.14, 0.18), _m("#111111"), 0, parent=r, coll=coll)
    box(name + "_m", (0.06, 0.05, 0.65), (0.2, -0.14, 0.05), _m("#111111"), 0, rot=(0, 70, 0), parent=r, coll=coll)
    for k in range(12):
        a = k * math.pi / 6
        box(f"{name}_tk{k}", (0.05, 0.04, 0.12), (math.sin(a) * 0.65, -0.13, math.cos(a) * 0.65), _m("#111111"), 0,
            rot=(0, math.degrees(a), 0), parent=r, coll=coll)
    return r


def locker_bank(name, loc, rot=0.0, n=8, color="#2f5a8a", coll=None, start_no=101, open_idx=None, seed=0):
    """Row of school lockers (1.6 wide, 7.2 tall) with vents, handles, number plates. Faces local -Y.
    color: hex or list of hex (cycled per door, e.g. school colours). open_idx: int or tuple of open doors - open
    lockers get a back shelf, books, a hanging jacket and a photo/sticker on the inside of the door."""
    rnd = random.Random(seed + start_no)
    r = _root(name, loc, rot, coll)
    cols = color if isinstance(color, (list, tuple)) else [color]
    opens = () if open_idx is None else ((open_idx,) if isinstance(open_idx, int) else tuple(open_idx))
    dark = _m("#15181d", 0.5)
    for i in range(n):
        c = cols[i % len(cols)]
        st = mat(f"tw_lockpaint_{c}", hexc(c), 0.38, 0.35, coat=0.3)
        x = -n * 0.8 + 0.8 + i * 1.6
        box(f"{name}_c{i}", (1.56, 1.6, 7.2), (x, 0.8, 3.9), st, 0.03, parent=r, coll=coll)
        op = i in opens
        piv = empty(f"{name}_hg{i}", (x - 0.76, -0.02, 0), parent=r, coll=coll, rot=(0, 0, 100 if op else 0))
        box(f"{name}_d{i}", (1.48, 0.08, 7.0), (0.76, 0, 3.9), st, 0.02, parent=piv, coll=coll)
        for k in range(4):
            box(f"{name}_v{i}{k}", (0.9, 0.04, 0.08), (0.76, -0.05, 6.6 + k * 0.18), dark, 0, parent=piv, coll=coll)
        box(f"{name}_hd{i}", (0.12, 0.1, 0.6), (1.25, -0.08, 3.8), _m("#c9d0da", 0.25, 0.9), 0.02, parent=piv, coll=coll)
        S.label(f"{name}_no{i}", str(start_no + i), (0.76, -0.06, 5.9), 0.2, "#f0f0f0", "bold", 0, piv, coll)
        if not op and rnd.random() < 0.18:  # stickers on some closed doors
            sphere(f"{name}_stk{i}", 0.16, (0.76 + rnd.uniform(-0.3, 0.3), -0.06, rnd.uniform(4.4, 5.4)),
                   _m(rnd.choice(["#f2c14e", "#ff5a7a", "#19c2b0", "#ffffff"]), 0.5), scale=(1, 0.15, 1), seg=10,
                   parent=piv, coll=coll)
        if op:  # dressed interior
            box(f"{name}_in{i}", (1.4, 1.4, 6.8), (x, 0.9, 3.95), _m("#20242a", 0.7), 0.0, parent=r, coll=coll)
            box(f"{name}_ish{i}", (1.4, 1.3, 0.1), (x, 0.8, 6.1), st, 0.0, parent=r, coll=coll)
            for k in range(3):
                box(f"{name}_ibk{i}{k}", (0.22, 0.9, 0.9 + 0.12 * k), (x - 0.4 + k * 0.26, 0.9, 6.6 + 0.06 * k),
                    _m(rnd.choice(["#c62828", "#2f7bff", "#f2c14e", "#2f8a55"]), 0.6), 0.02, parent=r, coll=coll)
            box(f"{name}_ijk{i}", (1.0, 0.5, 2.8), (x, 0.9, 4.2), pbr.get("fabric", tint=rnd.choice(["#2f5a8a", "#c62828", "#2f8a55"]), tile=1.5),
                0.15, parent=r, coll=coll)
            box(f"{name}_ibp{i}", (1.1, 0.8, 1.3), (x, 0.7, 1.4), pbr.get("fabric", tint="#f2c14e", tile=1.5), 0.2, parent=r, coll=coll)
            S.note(f"{name}_iph{i}", "GO\nBEARS!", (0.76, 0.08, 4.8), 180, w=0.9, h=1.1, paper="#ffffff", ink="#c62828",
                   coll=coll, parent=piv, tilt=4)
            box(f"{name}_imr{i}", (0.8, 0.02, 1.0), (0.76, 0.06, 3.3), mat("tw_mirror", (0.9, 0.92, 0.95), 0.02, 1.0), 0.0,
                parent=piv, coll=coll)
    box(name + "_base", (n * 1.6, 1.6, 0.6), (0, 0.8, 0.3), dark, 0.02, parent=r, coll=coll)
    return r


def bulletin(name, loc, rot=0.0, coll=None, notes=None, posters=None):
    r = _root(name, loc, rot, coll)
    box(name + "_fr", (7.4, 0.2, 4.4), (0, 0.05, 0), pbr.get("planks", tint="#8a5a36", tile=2), 0.04, parent=r, coll=coll)
    box(name + "_ck", (7.0, 0.22, 4.0), (0, 0.04, 0), _m("#b98a5a", 0.95), 0, parent=r, coll=coll)
    p = posters or [("BAKE SALE", "Friday 3pm\nGym lobby", "#2f7bff"), ("TRYOUTS", "Bike club\nMeet at racks", "#2f8a55")]
    S.poster(name + "_p1", p[0][0], p[0][1], (-2.4, -0.1, 0.3), w=1.8, h=2.4, coll=coll, parent=r, accent=p[0][2])
    S.poster(name + "_p2", p[1][0], p[1][1], (0.2, -0.1, -0.2), w=1.8, h=2.4, coll=coll, parent=r, accent=p[1][2], tilt=-4)
    S.note(name + "_n1", notes or "Be kind.\nIt counts.", (2.5, -0.1, 0.8), w=1.4, h=1.4, coll=coll, parent=r)
    S.note(name + "_n2", "Lost: blue\nhoodie - T.", (2.4, -0.1, -1.0), w=1.4, h=1.2, coll=coll, parent=r, paper="#a8e6ff", tilt=-8)
    for k, (dx, dz, c) in enumerate([(-3.1, 1.75, "#c62828"), (-0.8, 1.6, "#2f7bff"), (1.6, 1.65, "#f2c14e"), (3.0, -1.7, "#2f8a55")]):
        sphere(f"{name}_pin{k}", 0.1, (dx, -0.16, dz), _m(c, 0.3), seg=8, parent=r, coll=coll)
    return r


# ------------------------------------------------------------------ dressing pieces (kitchen / hallway / roofs)
def jar(name, loc, label_txt=None, fill="#e8d8b0", coll=None, h=1.0, r=0.38):
    """Glass-look storage jar with a cork/metal lid and a readable paper label facing -Y."""
    cyl(name, r, h, (loc[0], loc[1], loc[2] + h / 2), mat("tw_jarglass", hexc("#dfe8ea"), 0.08, 0.0, coat=0.5), 16, 0.03, coll=coll)
    cyl(name + "_f", r * 0.88, h * 0.7, (loc[0], loc[1], loc[2] + h * 0.38), _m(fill, 0.8), 16, 0.0, coll=coll)
    cyl(name + "_lid", r * 1.04, 0.16, (loc[0], loc[1], loc[2] + h + 0.06), _m("#b07a52", 0.6), 16, 0.03, coll=coll)
    if label_txt:
        box(name + "_lb", (r * 1.5, 0.02, h * 0.34), (loc[0], loc[1] - r - 0.01, loc[2] + h * 0.5), _m("#fbf6e8", 0.8), 0.0, coll=coll)
        S.label(name + "_lt", label_txt, (loc[0], loc[1] - r - 0.03, loc[2] + h * 0.5), min(0.17, r * 1.4 / max(3, len(label_txt)) * 1.6),
                "#2a1a10", "bold", 0, coll=coll)


def calendar(name, loc, rot=0.0, coll=None, month="NOVEMBER", mark=(14, 21), note_txt="Mom: late shift", parent=None):
    """Wall calendar: photo, month title, 5x7 day grid, red circled days, handwritten note. Faces -Y."""
    r = _root(name, loc, rot, coll)
    if parent:
        r.parent = parent
    box(name + "_pg", (2.6, 0.04, 3.6), (0, 0, 0), _m("#fbf8f0", 0.85), 0, parent=r, coll=coll)
    box(name + "_img", (2.4, 0.05, 1.2), (0, -0.005, 1.05), _m("#7ab0d8", 0.7), 0, parent=r, coll=coll)
    box(name + "_hill", (2.4, 0.06, 0.5), (0, -0.01, 0.7), _m("#5c9a4a", 0.7), 0, parent=r, coll=coll)
    sphere(name + "_sun", 0.18, (0.7, -0.03, 1.35), _m("#ffd23a", 0.5), scale=(1, 0.2, 1), seg=10, parent=r, coll=coll)
    S.label(name + "_mo", month, (0, -0.04, 0.22), 0.3, "#c62828", "bold", 0, r, coll)
    day = 1
    for row in range(5):
        for col in range(7):
            if day > 30:
                break
            x = -1.08 + col * 0.36; z = -0.1 - row * 0.36
            S.label(f"{name}_d{day}", str(day), (x, -0.04, z), 0.14, "#2a2a2a", "ui", 0, r, coll)
            if day in mark:
                S.label(f"{name}_c{day}", "O", (x, -0.05, z - 0.02), 0.34, "#e53935", "hand", 0, r, coll)
            day += 1
    S.label(name + "_nt", note_txt, (0, -0.05, -1.62), 0.17, "#1b2a6b", "hand", 0, r, coll)
    cyl(name + "_nail", 0.05, 0.2, (0, 0.0, 1.85), _m("#888888", 0.3, 0.9), 8, rot=(90, 0, 0), parent=r, coll=coll)
    return r


def window_view(name, loc, w, h, night=False, coll=None, seed=0):
    """Painted-depth view for an interior window (sits just in front of window()'s glass, behind the mullions):
    sky gradient, distant hills, rooftops of neighbouring houses (lit windows at night), a tree, moon at night."""
    rnd = random.Random(seed)
    x0, y, z0 = loc
    yy = y - 0.08
    sky_lo, sky_hi = ("#2a3a7a", "#0e1638") if night else ("#e9f4ff", "#8cc4ff")
    box(name + "_sky1", (w, 0.01, h * 0.5), (x0, yy + 0.02, z0 + h * 0.25), _g(sky_hi, 1.6 if night else 2.2), 0, coll=coll)
    box(name + "_sky0", (w, 0.01, h * 0.5), (x0, yy + 0.02, z0 - h * 0.25), _g(sky_lo, 1.6 if night else 2.2), 0, coll=coll)
    box(name + "_hill", (w, 0.01, h * 0.28), (x0, yy + 0.01, z0 - h * 0.36), _g("#1a2a3a" if night else "#7fb86a", 0.8 if night else 1.4), 0, coll=coll)
    for k in range(4):
        hw = rnd.uniform(0.7, 1.1); hh = rnd.uniform(0.5, 0.8)
        hx = x0 - w / 2 + 0.5 + k * (w - 1.0) / 3
        hz = z0 - h / 2 + 0.35 + hh / 2
        box(f"{name}_h{k}", (hw, 0.01, hh), (hx, yy, hz), _g("#141a30" if night else rnd.choice(["#f2e2c8", "#e8c8a0", "#dfe6ee"]), 0.6 if night else 1.5), 0, coll=coll)
        box(f"{name}_r{k}", (hw + 0.15, 0.01, 0.22), (hx, yy - 0.005, hz + hh / 2 + 0.1), _g("#0c0f1c" if night else rnd.choice(["#b0503a", "#6a4a3a", "#4a6a8a"]), 0.6 if night else 1.3), 0, coll=coll)
        if night and k % 2 == 0:
            box(f"{name}_lw{k}", (0.2, 0.01, 0.2), (hx, yy - 0.01, hz), _g("#ffcf7a", 4.0), 0, coll=coll)
    sphere(name + "_tree", 0.6, (x0 + w * 0.3, yy - 0.01, z0 - h * 0.05), _g("#0c1a14" if night else "#4f8a3a", 0.6 if night else 1.3),
           scale=(1, 0.02, 1.2), seg=12, coll=coll)
    if night:
        sphere(name + "_moon", 0.25, (x0 - w * 0.28, yy - 0.01, z0 + h * 0.3), _g("#f4f0d8", 4.0), scale=(1, 0.05, 1), seg=12, coll=coll)


def curtains(name, loc, w, h, color="#c8503a", coll=None):
    """Pair of gathered curtains + rod around a window centred at loc (faces -Y)."""
    x, y, z = loc
    fab = pbr.get("fabric", tint=color, tile=1.2)
    for s in (-1, 1):
        for k in range(3):  # gathered folds
            box(f"{name}_{s}{k}", (0.45, 0.35, h + 1.2), (x + s * (w / 2 + 0.15 + k * 0.38), y - 0.45 - (k % 2) * 0.12, z - 0.2), fab, 0.15, coll=coll)
        box(f"{name}_tie{s}", (1.3, 0.5, 0.18), (x + s * (w / 2 + 0.55), y - 0.6, z - 0.6), _m("#f2e6c8", 0.6), 0.06, coll=coll)
    cyl(name + "_rod", 0.07, w + 3.4, (x, y - 0.55, z + h / 2 + 0.6), _m("#3a2a1a", 0.35, 0.4), 10, rot=(0, 90, 0), coll=coll)
    box(name + "_val", (w + 2.6, 0.3, 0.8), (x, y - 0.65, z + h / 2 + 0.35), fab, 0.12, coll=coll)


def hanging_rail(name, loc, length=3.0, coll=None, pans=True):
    """Wall rail with hanging utensils (spatula, ladle, whisk) and small pans. Faces -Y."""
    x, y, z = loc
    chrome = _m("#c0c6cc", 0.2, 0.9)
    cyl(name + "_rail", 0.06, length, (x, y, z), chrome, 10, rot=(0, 90, 0), coll=coll)
    items = ["spat", "ladle", "whisk", "spoon"] + (["pan", "pan2"] if pans else [])
    for k, it in enumerate(items):
        ix = x - length / 2 + 0.35 + k * (length - 0.7) / max(1, len(items) - 1)
        cyl(f"{name}_hk{k}", 0.025, 0.4, (ix, y - 0.05, z - 0.2), chrome, 6, coll=coll)
        if it in ("pan", "pan2"):
            r_ = 0.55 if it == "pan" else 0.42
            cyl(f"{name}_{it}", r_, 0.18, (ix, y - 0.12, z - 1.1 - r_), _m("#1e1e1e" if it == "pan" else "#c0582a", 0.35, 0.5), 20, 0.04,
                rot=(90, 0, 0), coll=coll)
            box(f"{name}_{it}h", (0.12, 0.08, 0.8), (ix, y - 0.12, z - 0.65), _m("#3a2a1a", 0.5), 0.03, coll=coll)
        else:
            box(f"{name}_{it}h", (0.08, 0.06, 1.0), (ix, y - 0.08, z - 0.75), _m("#2a2a2a" if it != "spoon" else "#b07a52", 0.4), 0.02, coll=coll)
            head = {"spat": (0.36, 0.05, 0.42), "ladle": (0.34, 0.2, 0.3), "whisk": (0.26, 0.26, 0.5), "spoon": (0.24, 0.06, 0.34)}[it]
            box(f"{name}_{it}", head, (ix, y - 0.1, z - 1.4), chrome if it != "spoon" else _m("#b07a52", 0.5), 0.08, coll=coll)


def bread_board(name, loc, coll=None):
    x, y, z = loc
    box(name, (2.0, 1.3, 0.14), (x, y, z + 0.07), pbr.get("planks", tint="#c89a6a", tile=2), 0.04, coll=coll)
    box(name + "_loaf", (1.2, 0.7, 0.55), (x - 0.25, y + 0.1, z + 0.42), _m("#c8843a", 0.7), 0.25, coll=coll)
    for k in range(3):
        box(f"{name}_sl{k}", (0.12, 0.62, 0.48), (x + 0.5 + k * 0.16, y + 0.1, z + 0.38), _m("#f0d8a8", 0.8), 0.06,
            rot=(0, 8, 0), coll=coll)
    box(name + "_kn", (0.9, 0.12, 0.03), (x + 0.2, y - 0.45, z + 0.16), _m("#c0c6cc", 0.2, 0.9), 0.01, rot=(0, 0, -12), coll=coll)


def utensil_crock(name, loc, coll=None):
    x, y, z = loc
    cyl(name, 0.36, 0.9, (x, y, z + 0.45), _m("#e8e2d4", 0.3), 16, 0.04, coll=coll)
    for k, (dx, dy, c) in enumerate([(-0.1, 0, "#b07a52"), (0.1, 0.05, "#2a2a2a"), (0, -0.1, "#c0c6cc"), (0.05, 0.1, "#b07a52")]):
        box(f"{name}_u{k}", (0.08, 0.08, 1.2), (x + dx, y + dy, z + 1.2), _m(c, 0.4), 0.02, rot=(dx * 90, -dy * 90, 0), coll=coll)


def kettle(name, loc, color="#d9453a", coll=None):
    x, y, z = loc
    m = _m(color, 0.25, 0.2)
    cyl(name, 0.55, 0.75, (x, y, z + 0.38), m, 20, 0.15, r2=0.42, coll=coll)
    cyl(name + "_lid", 0.3, 0.12, (x, y, z + 0.8), m, 16, 0.04, coll=coll)
    sphere(name + "_kn", 0.1, (x, y, z + 0.92), _m("#1e1e1e"), seg=8, coll=coll)
    box(name + "_sp", (0.5, 0.14, 0.14), (x - 0.62, y, z + 0.5), m, 0.05, rot=(0, -35, 0), coll=coll)
    box(name + "_hd", (0.1, 0.1, 0.5), (x + 0.0, y, z + 1.0), _m("#1e1e1e"), 0.03, rot=(0, 90, 0), coll=coll)


def toaster(name, loc, color="#c0c6cc", coll=None):
    x, y, z = loc
    box(name, (1.1, 0.7, 0.75), (x, y, z + 0.38), _m(color, 0.2, 0.8), 0.15, coll=coll)
    for k in (-1, 1):
        box(f"{name}_sl{k}", (0.7, 0.12, 0.02), (x, y + k * 0.15, z + 0.76), _m("#111111"), 0, coll=coll)
    box(name + "_lv", (0.08, 0.12, 0.2), (x + 0.58, y, z + 0.5), _m("#111111"), 0.02, coll=coll)


def dish_rack(name, loc, coll=None):
    x, y, z = loc
    chrome = _m("#c0c6cc", 0.25, 0.8)
    box(name, (1.6, 1.0, 0.1), (x, y, z + 0.05), chrome, 0.02, coll=coll)
    for k in range(4):
        cyl(f"{name}_p{k}", 0.45, 0.06, (x - 0.5 + k * 0.32, y, z + 0.5), _m(["#ffffff", "#f2e6c8", "#ffffff", "#9ec8e8"][k], 0.2), 20,
            rot=(0, 90, 0), coll=coll)
    for k in range(2):
        cyl(f"{name}_cup{k}", 0.2, 0.4, (x + 0.55, y - 0.25 + k * 0.45, z + 0.3), _m(["#2f7bff", "#f2c14e"][k], 0.3), 12, 0.02, coll=coll)


def mail_pile(name, loc, coll=None, top="To: Harry\n12 Maple Ln"):
    x, y, z = loc
    for k, c in enumerate(["#f4f0e4", "#e8f0ff", "#fff4d6", "#ffffff"]):
        box(f"{name}_{k}", (1.6, 0.9, 0.04), (x + 0.06 * k, y - 0.04 * k, z + 0.03 + k * 0.045), _m(c, 0.85), 0.0,
            rot=(0, 0, (k - 1.5) * 7), coll=coll)
    S.label(name + "_t", top, (x + 0.2, y - 0.12, z + 0.22), 0.13, "#1b2a6b", "hand", 0, coll=coll, rot=(0, 0, 8))
    box(name + "_st", (0.26, 0.02, 0.3), (x + 0.75, y + 0.25, z + 0.215), _m("#c62828", 0.6), 0, rot=(0, 0, 8), coll=coll)


def vase(name, loc, coll=None, flowers=("#ff5a7a", "#ffd23a", "#ffffff")):
    x, y, z = loc
    cyl(name, 0.3, 0.9, (x, y, z + 0.45), mat("tw_jarglass", hexc("#dfe8ea"), 0.08, 0.0, coat=0.5), 14, 0.04, r2=0.22, coll=coll)
    for k, c in enumerate(flowers):
        a = k * 2.1
        cyl(f"{name}_st{k}", 0.03, 1.0, (x + math.cos(a) * 0.1, y + math.sin(a) * 0.1, z + 1.2), _m("#3f7a2a"), 6, coll=coll)
        sphere(f"{name}_fl{k}", 0.2, (x + math.cos(a) * 0.18, y + math.sin(a) * 0.18, z + 1.75 + k * 0.05), _m(c, 0.6), seg=10, coll=coll)


def wall_shelf(name, loc, rot=0.0, w=3.0, coll=None, items=(), seed=0):
    """Floating wall shelf with brackets; items: list of 'books'|'plant'|'jar:TEXT'|'plates'|'frame'."""
    rnd = random.Random(seed)
    r = _root(name, loc, rot, coll)
    wd = pbr.get("planks", tint="#b88a5a", tile=2)
    box(name + "_b", (w, 1.0, 0.16), (0, 0, 0), wd, 0.03, parent=r, coll=coll)
    for s in (-1, 1):
        box(f"{name}_br{s}", (0.1, 0.8, 0.5), (s * (w / 2 - 0.4), 0.1, -0.3), _m("#2a2a2a", 0.4, 0.6), 0.02, parent=r, coll=coll)
    n = max(1, len(items)); step = w / n
    for k, it in enumerate(items):
        x = -w / 2 + step * (k + 0.5)
        if it == "books":
            for j in range(4):
                bh = rnd.uniform(0.75, 1.05)
                box(f"{name}_bk{k}{j}", (0.2, 0.8, bh), (x - 0.33 + j * 0.22, 0, 0.08 + bh / 2),
                    _m(rnd.choice(["#c62828", "#2f7bff", "#2f8a55", "#f2c14e", "#1d1d24"]), 0.6), 0.02, parent=r, coll=coll)
        elif it == "plates":
            for j in range(3):
                cyl(f"{name}_pl{k}{j}", 0.42, 0.05, (x + j * 0.08 - 0.08, 0.15, 0.5), _m(["#ffffff", "#9ec8e8", "#f2e6c8"][j], 0.2), 20,
                    rot=(80, 0, 0), parent=r, coll=coll)
        elif it == "plant":
            cyl(f"{name}_pp{k}", 0.25, 0.4, (x, 0, 0.28), _m("#c9774a", 0.6), 12, 0.03, parent=r, coll=coll)
            for j in range(5):
                a = j * 1.25
                box(f"{name}_lf{k}{j}", (0.12, 0.08, 0.7), (x + math.cos(a) * 0.15, math.sin(a) * 0.15, 0.6 - j * 0.06),
                    _m("#3f7a2a", 0.6), 0.03, rot=(math.sin(a) * 60, -math.cos(a) * 60 - 20, 0), parent=r, coll=coll)
        elif it == "frame":
            box(f"{name}_fr{k}", (0.8, 0.08, 1.0), (x, 0.1, 0.6), _m("#3a2a1a", 0.4), 0.02, rot=(-8, 0, 0), parent=r, coll=coll)
            box(f"{name}_fi{k}", (0.62, 0.09, 0.8), (x, 0.08, 0.6), _m(rnd.choice(["#7ab0d8", "#c8a070", "#a8c87a"]), 0.7), 0,
                rot=(-8, 0, 0), parent=r, coll=coll)
    return r


def framed_art(name, loc, rot=0.0, w=2.4, h=1.8, coll=None, kind="landscape", text=None):
    """Framed wall art with simple painted content (landscape | sunset | abstract | text plaque)."""
    r = _root(name, loc, rot, coll)
    box(name + "_fr", (w, 0.12, h), (0, 0, 0), _m("#2a1e14", 0.4), 0.03, parent=r, coll=coll)
    box(name + "_mt", (w - 0.2, 0.13, h - 0.2), (0, -0.005, 0), _m("#fbf8f0", 0.8), 0, parent=r, coll=coll)
    iw, ih = w - 0.5, h - 0.5
    if text:
        box(name + "_bg", (iw, 0.14, ih), (0, -0.01, 0), _m("#24323f", 0.7), 0, parent=r, coll=coll)
        S.label(name + "_t", text, (0, -0.09, 0), min(ih * 0.42, iw / max(4, len(text.split(chr(10))[0])) * 2.1), "#f3e6c4", "hand", 0, r, coll)
        return r
    sky_c, gnd_c = {"landscape": ("#9ec8e8", "#6aa04a"), "sunset": ("#ff9a55", "#5a3a6a"), "abstract": ("#f2c14e", "#2f7bff")}[kind]
    box(name + "_sk", (iw, 0.14, ih * 0.6), (0, -0.01, ih * 0.2), _m(sky_c, 0.7), 0, parent=r, coll=coll)
    box(name + "_gd", (iw, 0.14, ih * 0.4), (0, -0.01, -ih * 0.3), _m(gnd_c, 0.7), 0, parent=r, coll=coll)
    sphere(name + "_sn", ih * 0.14, (iw * 0.25, -0.08, ih * 0.25), _m("#fff4c0" if kind != "abstract" else "#c62828", 0.5), scale=(1, 0.1, 1),
           seg=12, parent=r, coll=coll)
    return r


def roof_clutter(name, r, w, d, H, rnd, coll, stone=None):
    """Flat-roof dressing seen from aerials: gravel/tar deck, parapet ring, AC units with fans, chimney or vent stacks,
    skylights, water tank, satellite dish, occasional rooftop billboard."""
    stone = stone or pbr.get("concrete", tint="#d8d0c0")
    deck = pbr.get("asphalt", tint=rnd.choice(["#8a8884", "#6e6c6a", "#9a958c", "#7a7f86"]), tile=6)
    box(name + "_deck", (w - 0.4, d - 0.4, 0.25), (0, d / 2, H + 0.1), deck, 0.0, parent=r, coll=coll)
    for s in (-1, 1):
        box(f"{name}_pa{s}", (w, 0.5, 1.3), (0, d / 2 + s * (d / 2 - 0.25), H + 0.6), stone, 0.04, parent=r, coll=coll)
        box(f"{name}_pb{s}", (0.5, d, 1.3), (s * (w / 2 - 0.25), d / 2, H + 0.6), stone, 0.04, parent=r, coll=coll)
    steel = pbr.get("steel", tint="#c8ccd0")
    for k in range(rnd.randint(1, 3)):
        ax, ay = rnd.uniform(-w / 2 + 2, w / 2 - 2), rnd.uniform(2.5, d - 2.5)
        box(f"{name}_ac{k}", (2.2, 2.2, 1.4), (ax, ay, H + 0.95), steel, 0.08, parent=r, coll=coll)
        cyl(f"{name}_acf{k}", 0.75, 0.08, (ax, ay, H + 1.68), _m("#2a2e33", 0.4, 0.5), 16, parent=r, coll=coll)
    roll = rnd.random()
    if roll < 0.35:
        cx = rnd.choice((-1, 1)) * (w / 2 - 1.6)
        box(name + "_chim", (1.4, 1.4, 3.4), (cx, d * 0.7, H + 1.7), pbr.get("brick", tile=4), 0.04, parent=r, coll=coll)
        box(name + "_chimc", (1.7, 1.7, 0.3), (cx, d * 0.7, H + 3.5), stone, 0.04, parent=r, coll=coll)
    elif roll < 0.6:
        tx, ty = rnd.uniform(-w / 4, w / 4), d * 0.75
        for sx in (-1, 1):
            for sy in (-1, 1):
                box(f"{name}_tl{sx}{sy}", (0.2, 0.2, 2.4), (tx + sx * 1.1, ty + sy * 1.1, H + 1.2), _m("#3a3028", 0.5), 0, parent=r, coll=coll)
        cyl(name + "_tank", 1.6, 2.8, (tx, ty, H + 3.8), pbr.get("planks", tint="#8a6a4a", tile=2), 20, 0.05, parent=r, coll=coll)
        cyl(name + "_tankr", 1.7, 0.6, (tx, ty, H + 5.5), _m("#4a4038", 0.6), 20, 0.05, r2=0.2, parent=r, coll=coll)
    else:
        for k in range(2):
            box(f"{name}_sky{k}", (2.4, 1.6, 0.6), (-w / 4 + k * w / 2, d * 0.45, H + 0.5), glass(), 0.05, parent=r, coll=coll)
    for k in range(rnd.randint(1, 3)):
        cyl(f"{name}_vp{k}", 0.2, 1.2, (rnd.uniform(-w / 2 + 1, w / 2 - 1), rnd.uniform(1.5, d - 1.5), H + 0.8), _m("#9aa0a8", 0.3, 0.7), 8,
            parent=r, coll=coll)
    if rnd.random() < 0.3:
        sphere(name + "_dish", 0.7, (w / 2 - 1.5, 1.5, H + 1.6), _m("#e8e8e8", 0.3), scale=(1, 0.35, 1), seg=12, parent=r, coll=coll)


# ------------------------------------------------------------------ back blocks (aerial depth around main street)
def _winwall(base, glass_hx="#2a3a4a", lit=None, scale=1.0):
    """Procedural building skin: window grid (Brick Texture on (x+y, z)) over a wall colour. Cheap for distant blocks."""
    k = f"tw_winwall_{base}_{glass_hx}_{lit}"
    if k in D.materials:
        return D.materials[k]
    m = D.materials.new(k); m.use_nodes = True
    N, Lk = m.node_tree.nodes, m.node_tree.links
    b = next(n for n in N if n.type == "BSDF_PRINCIPLED")
    tc = N.new("ShaderNodeTexCoord"); sep = N.new("ShaderNodeSeparateXYZ"); Lk.new(tc.outputs["Object"], sep.inputs[0])
    add = N.new("ShaderNodeMath"); add.operation = "ADD"; Lk.new(sep.outputs[0], add.inputs[0]); Lk.new(sep.outputs[1], add.inputs[1])
    cmb = N.new("ShaderNodeCombineXYZ"); Lk.new(add.outputs[0], cmb.inputs[0]); Lk.new(sep.outputs[2], cmb.inputs[1])
    bt = N.new("ShaderNodeTexBrick"); Lk.new(cmb.outputs[0], bt.inputs["Vector"])
    bt.offset = 0.0; bt.squash = 1.0
    bt.inputs["Scale"].default_value = 0.2 * scale
    bt.inputs["Mortar Size"].default_value = 0.85
    bt.inputs["Mortar Smooth"].default_value = 0.0
    bt.inputs["Brick Width"].default_value = 4.6
    bt.inputs["Row Height"].default_value = 5.25
    bt.inputs["Color1"].default_value = (*hexc(glass_hx), 1); bt.inputs["Color2"].default_value = (*hexc(glass_hx), 1)
    bt.inputs["Mortar"].default_value = (*hexc(base), 1)
    Lk.new(bt.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.6
    if lit:
        mx = N.new("ShaderNodeMath"); mx.operation = "SUBTRACT"; mx.inputs[0].default_value = 1.0
        Lk.new(bt.outputs["Fac"], mx.inputs[1])
        b.inputs["Emission Color"].default_value = (*hexc(lit), 1)
        Lk.new(mx.outputs[0], b.inputs["Emission Strength"])
    m.diffuse_color = (*hexc(base), 1)
    return m


def back_blocks(o=(0, 0, 0), coll=None, night=False, seed=11, y0=-30, y1=175):
    """Fills the town behind the main-street facades so aerials read as a town, not a beige plane: alleys, a second row
    of varied buildings (flat roofs with clutter / pitched coloured roofs), parallel streets with sidewalks and parked
    cars, a park block with grass paths and trees, a parking lot with painted bays. Cheap procedural window skins."""
    coll = coll or collection("town_back")
    rnd = random.Random(seed)
    ox, oy, oz = o
    walls = ["#e8d2b0", "#d8c8b0", "#c9d6c0", "#f2d0d6", "#d0dce8", "#f4e8c8", "#c8b8a8", "#e8f0d0", "#b8c8d8", "#e0b090"]
    roofs = ["#9a4a32", "#5a5a62", "#3f5a3a", "#6a4a3a", "#8a3a3a", "#4a5a7a"]
    for s in (-1, 1):
        # alley behind the facades + second street further out
        box(f"bb_alley{s}", (8, y1 - y0, 0.2), (ox + s * 31, oy + (y0 + y1) / 2, oz - 0.12), pbr.get("asphalt", tint="#9a9a98"), 0.0, coll=coll)
        street(f"bb_st{s}", (ox + s * 66, oy + y0, oz), y1 - y0, coll=coll)
        y = oy + y0 + 4
        blk = 0
        while y < oy + y1 - 10:
            bw = rnd.uniform(14, 22)
            if blk % 4 == 2 and s < 0:   # park block
                box(f"bb_park{s}{blk}", (16, bw, 0.25), (ox + s * 44, y + bw / 2, oz - 0.05), pbr.get("grass", tile=6), 0.0, coll=coll)
                box(f"bb_path{s}{blk}", (16, 2.0, 0.27), (ox + s * 44, y + bw / 2, oz - 0.04), pbr.get("concrete", tint="#e0d8c8"), 0.0, coll=coll)
                for k in range(3):
                    tree(f"bb_tr{s}{blk}{k}", (ox + s * (39 + k * 5), y + rnd.uniform(2, bw - 2), oz), rnd.uniform(0.8, 1.1), seed=k + blk, coll=coll)
                bench(f"bb_bn{s}{blk}", (ox + s * 44, y + bw / 2 - 2, oz), 0, coll)
            elif blk % 4 == 1 and s > 0:  # parking lot
                box(f"bb_lot{s}{blk}", (16, bw, 0.25), (ox + s * 44, y + bw / 2, oz - 0.05), pbr.get("asphalt", tint="#8a8a88"), 0.0, coll=coll)
                for k in range(int(bw / 3.2)):
                    box(f"bb_bay{s}{blk}{k}", (7, 0.2, 0.02), (ox + s * 42, y + 1.5 + k * 3.2, oz + 0.09), _m("#f2efe6", 0.6), 0, coll=coll)
                    if rnd.random() < 0.6:
                        car(f"bb_car{s}{blk}{k}", (ox + s * 42.5, y + 3.1 + k * 3.2, oz + 0.05), 90 + rnd.choice((0, 180)),
                            rnd.choice(["#2f7bff", "#c62828", "#f2c14e", "#ffffff", "#2f8a55", "#1d1d24", "#9aa0a8"]), coll)
            else:
                fl = rnd.choice((2, 2, 3, 3, 4))
                H = fl * 10.5
                dd = rnd.uniform(12, 16)
                cx = ox + s * (36 + dd / 2)
                base = rnd.choice(walls)
                rr = _root(f"bb_b{s}{blk}", (cx, y + bw / 2, oz), 90 if s < 0 else 270, coll)
                # local: width along local X (= world Y), depth along local Y
                box(f"bb_b{s}{blk}_m", (bw - 1, dd, H), (0, dd / 2 - dd / 2, H / 2), _winwall(base, "#3a4a5c", "#ffcf7a" if night else None),
                    0.05, parent=rr, coll=coll)
                if rnd.random() < 0.45:
                    rf = pbr.get("roof", tint=rnd.choice(roofs))
                    for sg in (-1, 1):
                        box(f"bb_b{s}{blk}_rf{sg}", (bw + 0.2, dd * 0.6, 0.4), (0, sg * dd * 0.25, H + dd * 0.17), rf, 0.05,
                            rot=(sg * 34, 0, 0), parent=rr, coll=coll)
                    if rnd.random() < 0.6:
                        box(f"bb_b{s}{blk}_ch", (1.3, 1.3, 4.5), (rnd.uniform(-bw / 3, bw / 3), dd * 0.2, H + 3.5), pbr.get("brick", tile=4), 0.04,
                            parent=rr, coll=coll)
                else:
                    rr2 = empty(f"bb_b{s}{blk}_rc", (0, -dd / 2, 0), parent=rr, coll=coll)
                    roof_clutter(f"bb_b{s}{blk}", rr2, bw - 1, dd, H, rnd, coll)
                    if rnd.random() < 0.25:
                        txt = rnd.choice(["BLOX COLA", "PIZZA 24/7", "RADIO 99.1", "GYM", "HOTEL"])
                        S.sign(f"bb_b{s}{blk}_bill", txt, (0, dd * 0.1, H + 4.2), w=max(8, len(txt) * 1.1), h=3.2,
                               bg=rnd.choice(["#c62828", "#1f2f5a", "#2f8a55", "#f2c14e"]), fg="#ffffff", coll=coll, parent=rr,
                               lit=3.0 if night else 0.6)
                        for sx in (-1, 1):
                            box(f"bb_b{s}{blk}_bl{sx}", (0.25, 0.25, 3.0), (sx * 3, dd * 0.1 + 0.3, H + 1.4), _m("#2a2e33", 0.4, 0.6), 0, parent=rr, coll=coll)
            y += bw + 1.0
            blk += 1
        # far row beyond the parallel street: cheap masses for the horizon
        y = oy + y0
        while y < oy + y1 + 40:
            bw = rnd.uniform(12, 20); H = rnd.choice((21, 31.5, 42))
            box(f"bb_far{s}{int(y)}", (16, bw - 1, H), (ox + s * 90, y + bw / 2, oz + H / 2),
                _winwall(rnd.choice(walls), "#3a4a5c", "#ffcf7a" if night else None), 0.05, coll=coll)
            box(f"bb_farr{s}{int(y)}", (16.4, bw - 0.6, 0.6), (ox + s * 90, y + bw / 2, oz + H + 0.3),
                pbr.get("asphalt", tint="#8a8884"), 0.03, coll=coll)
            y += bw
    # behind the pharmacy: a cross street + a row of houses closing the vista
    box("bb_xst", (180, 14, 0.2), (ox, oy + 172, oz - 0.1), pbr.get("asphalt"), 0.0, coll=coll)
    for k in range(9):
        x = ox - 80 + k * 20; H = rnd.choice((21, 31.5))
        box(f"bb_x{k}", (18, 16, H), (x, oy + 188, oz + H / 2), _winwall(rnd.choice(walls), "#3a4a5c", "#ffcf7a" if night else None), 0.05, coll=coll)
        rrx = empty(f"bb_xr{k}", (x, oy + 180, oz), coll=coll)
        roof_clutter(f"bb_x{k}", rrx, 18, 16, H, rnd, coll)


def desk_set(name, loc, rot=0.0, coll=None, seed=0, books=True):
    """Student desk + chair + clutter."""
    rnd = random.Random(seed)
    r = _root(name, loc, rot, coll)
    top = pbr.get("woodfloor", tint="#e0b88a", tile=3)
    leg = _m("#3a4048", 0.4, 0.6)
    box(name + "_t", (3.4, 2.4, 0.2), (0, 0, 3.1), top, 0.04, parent=r, coll=coll)
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(f"{name}_l{sx}{sy}", (0.14, 0.14, 3.0), (sx * 1.5, sy * 1.0, 1.5), leg, 0.0, parent=r, coll=coll)
    box(name + "_bin", (3.0, 2.0, 0.6), (0, 0.1, 2.6), leg, 0.03, parent=r, coll=coll)
    ch = _m(rnd.choice(["#2f7bff", "#d9453a", "#f2c14e", "#2f8a55"]), 0.45)
    box(name + "_cs", (2.0, 2.0, 0.2), (0, -2.0, 2.0), ch, 0.06, parent=r, coll=coll)
    box(name + "_cb", (2.0, 0.2, 2.0), (0, -3.0, 3.0), ch, 0.06, parent=r, coll=coll)
    for sx in (-1, 1):
        box(f"{name}_cl{sx}", (0.12, 1.8, 1.9), (sx * 0.9, -2.0, 0.95), leg, 0.0, parent=r, coll=coll)
    if books:
        for k in range(rnd.randint(1, 3)):
            box(f"{name}_bk{k}", (1.2, 0.9, 0.18), (rnd.uniform(-0.8, 0.8), rnd.uniform(-0.3, 0.6), 3.3 + k * 0.19),
                _m(rnd.choice(["#c62828", "#2f7bff", "#2f8a55", "#f2c14e", "#8a2be2"]), 0.6), 0.03,
                rot=(0, 0, rnd.uniform(-20, 20)), parent=r, coll=coll)
        cyl(name + "_pen", 0.04, 0.9, (1.0, -0.6, 3.25), _m("#f2c14e"), 6, rot=(0, 90, 30), parent=r, coll=coll)
    return r


def kitchen_counter(name, loc, rot=0.0, w=12.0, coll=None, sink=True, stove=True, upper=True):
    r = _root(name, loc, rot, coll)
    cab = pbr.get("planks", tint="#e8e2d4", tile=3)
    box(name + "_cab", (w, 2.6, 3.4), (0, 0, 1.7), cab, 0.04, parent=r, coll=coll)
    box(name + "_top", (w + 0.2, 2.9, 0.25), (0, -0.1, 3.5), pbr.get("tile", tint="#d8d4cc", tile=2), 0.03, parent=r, coll=coll)
    box(name + "_bs", (w, 0.15, 3.0), (0, 1.25, 5.1), pbr.get("tile", tile=1.5), 0.0, parent=r, coll=coll)
    for i in range(int(w / 2)):
        x = -w / 2 + 1 + i * 2
        box(f"{name}_dl{i}", (1.9, 0.05, 0.08), (x, -1.32, 2.9), _m("#15181d"), 0, parent=r, coll=coll)
        box(f"{name}_hd{i}", (0.6, 0.1, 0.08), (x, -1.4, 2.6), _m("#c9d0da", 0.25, 0.9), 0.02, parent=r, coll=coll)
    if upper:
        box(name + "_up", (w, 1.6, 3.0), (0, 0.6, 8.0), cab, 0.04, parent=r, coll=coll)
    if sink:
        box(name + "_sk", (2.6, 1.8, 0.3), (-w / 4, -0.1, 3.5), _m("#c0c6cc", 0.2, 0.9), 0.05, parent=r, coll=coll)
        cyl(name + "_tap", 0.08, 1.2, (-w / 4, 0.8, 4.2), _m("#c0c6cc", 0.2, 0.9), 8, parent=r, coll=coll)
        box(name + "_tapn", (0.12, 0.8, 0.12), (-w / 4, 0.45, 4.8), _m("#c0c6cc", 0.2, 0.9), 0.02, parent=r, coll=coll)
    if stove:
        box(name + "_st", (3.0, 2.4, 0.1), (w / 4, -0.1, 3.66), _m("#141414", 0.2), 0.02, parent=r, coll=coll)
        for k, (dx, dy) in enumerate([(-0.7, -0.5), (0.7, -0.5), (-0.7, 0.5), (0.7, 0.5)]):
            cyl(f"{name}_bn{k}", 0.4, 0.05, (w / 4 + dx, -0.1 + dy, 3.73), _m("#333333", 0.4, 0.5), 16, parent=r, coll=coll)
        cyl(name + "_pot", 0.6, 0.8, (w / 4 - 0.7, 0.4, 4.1), _m("#b0352a", 0.3, 0.2), 16, 0.05, parent=r, coll=coll)
    # clutter: jars, cutting board, bottles
    for k, (dx, c) in enumerate([(-w / 2 + 1, "#f2c14e"), (-w / 2 + 1.7, "#d9453a"), (-w / 2 + 2.4, "#2f8a55")]):
        cyl(f"{name}_jar{k}", 0.3, 0.8, (dx, 0.6, 4.05), _m(c, 0.3), 12, 0.03, parent=r, coll=coll)
    box(name + "_cb", (1.8, 1.2, 0.12), (w / 2 - 1.6, -0.2, 3.7), pbr.get("planks", tint="#c89a6a", tile=2), 0.03, parent=r, coll=coll)
    return r


def fridge(name, loc, rot=0.0, coll=None, notes=("Milk\nEggs\nBread",)):
    r = _root(name, loc, rot, coll)
    st = _m("#e6e8ea", 0.25, 0.3)
    box(name + "_b", (3.4, 3.0, 8.4), (0, 0, 4.2), st, 0.12, parent=r, coll=coll)
    box(name + "_gap", (3.42, 0.02, 0.06), (0, -1.51, 5.6), _m("#888888"), 0, parent=r, coll=coll)
    for z in (3.6, 6.8):
        box(f"{name}_h{z}", (0.14, 0.2, 1.4), (1.3, -1.6, z), _m("#b8bcc2", 0.2, 0.9), 0.04, parent=r, coll=coll)
    for i, n in enumerate(notes):
        S.note(f"{name}_n{i}", n, (-0.6 + i * 1.2, -1.55, 6.6 - i * 0.5), w=1.1, h=1.2, coll=coll, parent=r)
    for k, c in enumerate(["#d9453a", "#2f7bff", "#f2c14e"]):
        sphere(f"{name}_mg{k}", 0.12, (-1.2 + k * 0.4, -1.55, 4.6), _m(c), seg=8, parent=r, coll=coll)
    return r


def bed(name, loc, rot=0.0, coll=None, blanket="#2f5a8a"):
    r = _root(name, loc, rot, coll)
    wd = pbr.get("planks", tint="#9a6a40", tile=3)
    box(name + "_fr", (6.0, 10.0, 1.6), (0, 0, 1.0), wd, 0.06, parent=r, coll=coll)
    box(name + "_hb", (6.4, 0.5, 4.2), (0, 5.0, 2.1), wd, 0.08, parent=r, coll=coll)
    box(name + "_mt", (5.8, 9.6, 0.9), (0, 0, 2.2), _m("#f4f4f0", 0.8), 0.25, parent=r, coll=coll)
    box(name + "_bl", (6.0, 6.5, 0.5), (0, -1.6, 2.75), pbr.get("fabric", tint=blanket, tile=2), 0.25, parent=r, coll=coll)
    box(name + "_pl", (3.6, 1.6, 0.7), (0, 3.7, 3.0), _m("#ffffff", 0.8), 0.3, rot=(10, 0, 0), parent=r, coll=coll)
    return r


def shelf(name, loc, rot=0.0, coll=None, seed=0, w=5.0, rows=3):
    rnd = random.Random(seed)
    r = _root(name, loc, rot, coll)
    wd = pbr.get("planks", tint="#b88a5a", tile=3)
    for k in range(rows + 1):
        box(f"{name}_s{k}", (w, 1.4, 0.18), (0, 0, k * 1.8), wd, 0.03, parent=r, coll=coll)
    for s in (-1, 1):
        box(f"{name}_e{s}", (0.18, 1.4, rows * 1.8), (s * w / 2, 0, rows * 0.9), wd, 0.03, parent=r, coll=coll)
    for k in range(rows):
        x = -w / 2 + 0.4
        while x < w / 2 - 0.5:
            bw = rnd.uniform(0.2, 0.45); bh = rnd.uniform(0.9, 1.5)
            box(f"{name}_b{k}_{x:.1f}", (bw, 1.0, bh), (x + bw / 2, 0, k * 1.8 + 0.09 + bh / 2),
                _m(rnd.choice(["#c62828", "#2f7bff", "#2f8a55", "#f2c14e", "#8a2be2", "#1d1d24", "#ff7a1f"]), 0.6), 0.02,
                parent=r, coll=coll)
            x += bw + 0.04
    return r


def mug(name, loc, color="#c62828", coll=None, parent=None):
    m = _m(color, 0.3)
    cyl(name, 0.35, 0.7, loc, m, 16, 0.03, parent=parent, coll=coll)
    cyl(name + "_cof", 0.3, 0.02, (loc[0], loc[1], loc[2] + 0.3), _m("#3a1f10", 0.2), 16, parent=parent, coll=coll)
    box(name + "_h", (0.12, 0.08, 0.4), (loc[0] + 0.42, loc[1], loc[2]), m, 0.04, parent=parent, coll=coll)


def fruit_bowl(name, loc, coll=None, seed=0):
    rnd = random.Random(seed)
    cyl(name, 0.9, 0.35, loc, _m("#e8e2d4", 0.3), 20, 0.1, coll=coll)
    for k in range(5):
        a = k * 1.25
        sphere(f"{name}_f{k}", 0.3, (loc[0] + math.cos(a) * 0.45, loc[1] + math.sin(a) * 0.45, loc[2] + 0.35),
               _m(rnd.choice(["#c62828", "#f2c14e", "#ff8a3a", "#7ab83a"]), 0.4), seg=10, coll=coll)


def potted_plant(name, loc, s=1.0, coll=None):
    cyl(name, 0.6 * s, 1.0 * s, (loc[0], loc[1], loc[2] + 0.5 * s), pbr.get("concrete", tint="#c9774a", tile=2), 16, 0.05, coll=coll)
    for k in range(6):
        a = k * 1.05
        box(f"{name}_lf{k}", (0.25 * s, 0.9 * s, 0.06), (loc[0] + math.cos(a) * 0.4 * s, loc[1] + math.sin(a) * 0.4 * s, loc[2] + 1.6 * s),
            _m("#3f7a2a", 0.6), 0.1, rot=(55, 0, math.degrees(a) + 90), coll=coll)


def picture(name, loc, rot=0.0, w=1.6, h=1.2, coll=None, color="#7ab0d8", parent=None):
    r = _root(name, loc, rot, coll)
    if parent:
        r.parent = parent
    box(name + "_fr", (w, 0.12, h), (0, 0, 0), _m("#3a2a1a", 0.4), 0.03, parent=r, coll=coll)
    box(name + "_im", (w - 0.25, 0.13, h - 0.25), (0, -0.01, 0), _m(color, 0.7), 0.0, parent=r, coll=coll)
    return r


# ------------------------------------------------------------------ LOCATIONS
def shadow_budget(pool="1024", soft_res=0.03, sharp_res=0.004):
    """EEVEE virtual-shadow-map budget for big sets (R2-4: hallway logged 'Shadow buffer full 2056/2048' -> missing
    shadows). Raises the scene shadow pool to >= `pool` MB and caps the page resolution of large/soft lights (area >= 2
    studs, sun) - their penumbra never needs fine pages - while small keys/spots keep `sharp_res`. Called from _L, so
    every location (and any set built later) gets it; character lights added after this keep Blender's default."""
    sc = bpy.context.scene
    try:
        order = ["16", "32", "64", "128", "256", "512", "1024", "1536", "2048"]
        if order.index(sc.eevee.shadow_pool_size) < order.index(pool):
            sc.eevee.shadow_pool_size = pool
    except Exception:
        pass
    for ld in D.lights:
        if not getattr(ld, "use_shadow", False):
            continue
        big = ld.type == "AREA" and max(ld.size, getattr(ld, "size_y", 0)) >= 6.0   # room washes / bounces only
        res = 0.008 if ld.type == "SUN" else (soft_res if big else sharp_res)   # sun keeps crisp contact shadows
        try:
            ld.shadow_maximum_resolution = max(ld.shadow_maximum_resolution, res)
        except AttributeError:
            pass


def _L(name, o, look, focus, cams, t=0.0):
    shadow_budget()
    ox, oy, oz = o
    tr = lambda p: (p[0] + ox, p[1] + oy, p[2] + oz)
    return dict(name=name, origin=o, look=look, focus=tr(focus), t=t,
                cams={k: (tr(a), tr(b), lens) for k, (a, b, lens) in cams.items()})


def main_street(o=None, night=False, closed=True, extras=True, cops=True, t_flip=None, coll=None, screen_lines=None, env=True,
                backlots=True, plaza_crowd=0, numbers=True):
    """Main street of Blox Town (runs +Y). West side x<0 faces +X, east side faces -X. Pharmacy corner closes the end."""
    o = o or ORIGINS["main_street"]
    coll = coll or collection("town_main")
    ox, oy, oz = o
    if env and not night:
        sky("day", strength=1.25); sun(4.2, "#ffe3c0", 48, -35)
        f = sun(1.1, "#cfdcff", 30, 145); f.data.use_shadow = False   # bounce fill for the shaded side
    box("ms_ground", (500, 500, 0.2), (ox, oy + 60, oz - 0.45), pbr.get("grass", tile=10), 0.0, coll=coll)
    street("ms", (ox, oy - 20, oz), 160, coll=coll, cobble_plaza=(ox, oy + 138, 60, 26))
    west = [("BAKERY", "timber", None, "#f2c9a0", "#7a2a1a", 2), ("BOOKS & MORE", "brick", None, None, "#24323f", 3),
            ("HARDWARE", "plaster", "#c9d6c0", "#2f8a55", "#2f3a2f", 2), ("CAFE BLOX", "timber", "#f1e3c4", "#c62828", "#5a1a14", 2),
            ("POST OFFICE", "brick", "#c8b8a8", None, "#1f2f5a", 2), ("BARBER", "plaster", "#d0dce8", "#2f7bff", "#24323f", 2)]
    east = [("FLOWERS", "plaster", "#f2d0d6", "#ff5a7a", "#5a2a3a", 2), ("BLOX BANK", "brick", "#d8c8b0", None, "#1f2f5a", 3),
            ("TOY STORE", "timber", "#e8f0d0", "#2f7bff", "#1d2f6b", 2), ("DINER", "brick", None, "#c62828", "#24323f", 2),
            ("ARCADE", "steel", "#6a5a8a", None, "#121018", 2), ("GROCER", "timber", "#f4e8c8", "#2f8a55", "#2f3a2f", 2)]
    rnd = random.Random(4)
    y = oy + 6
    for i, ((sg, st, tint, aw, bg, fl), (sg2, st2, tint2, aw2, bg2, fl2)) in enumerate(zip(west, east)):
        w = 18
        cl = (t_flip if t_flip is not None else True) if closed else None
        facade(f"msW{i}", (ox - 13, y + w / 2, oz), 90, w, 14, fl, st, tint, sg, bg, "#f3e6c4", aw, True,
               cl if i % 2 == 0 else (True if closed else None), night, coll, seed=i, shutters="#2f5a3a" if st == "plaster" else None)
        facade(f"msE{i}", (ox + 13, y + w / 2, oz), 270, w, 14, fl2, st2, tint2, sg2, bg2, "#f3e6c4", aw2, True,
               True if closed and i % 2 else None, night, coll, seed=10 + i)
        y += w + 1.0
    # NOTE yaw: local -Y front; yaw 90 -> faces +X (west row), yaw 270 -> faces -X (east row)
    # pharmacy corner at the far end, facing -Y
    pharmacy(o=(ox, oy + 150, oz), night=night, coll=coll, screen_lines=screen_lines)
    # street furniture both sides
    for k in range(6):
        yy = oy + 4 + k * 22
        for s in (-1, 1):
            street_lamp(f"msL{k}{s}", (ox + s * 8.2, yy, oz + 0.2), 0, on=night, coll=coll)
        if k % 2 == 0:
            bench(f"msB{k}", (ox - 11.0, yy + 6, oz + 0.2), 90, coll)
            trash_can(f"msT{k}", (ox - 11.2, yy + 10, oz + 0.2), coll)
        else:
            planter(f"msP{k}", (ox + 11.0, yy + 6, oz + 0.2), coll, seed=k)
            hydrant(f"msH{k}", (ox + 8.6, yy + 10, oz + 0.2), coll)
    a_frame("msA1", (ox - 10.0, oy + 20, oz + 0.2), 120, coll=coll)
    newspaper_box("msN1", (ox + 11.2, oy + 14, oz + 0.2), 270, coll)
    for k, (yy, c) in enumerate([(30, "#2f7bff"), (58, "#c62828"), (96, "#f2c14e")]):
        car(f"msC{k}", (ox + 4.2, oy + yy, oz), 0, c, coll)
    for k in range(4):
        tree(f"msTr{k}", (ox + (-11.5 if k % 2 else 11.5), oy + 40 + k * 26, oz + 0.2), 0.9, seed=k, coll=coll)
    if cops:
        police_car("msPC", (ox - 4.2, oy + 46, oz), 180, coll, lights_on=True)
        C.extra("cop1", (ox - 9.5, oy + 40, oz + 0.2), 120, "police", coll, pose="hips")
        C.extra("cop2", (ox - 10.8, oy + 42.5, oz + 0.2), 150, "police", coll, pose="point")
    if extras and not night:
        C.crowd("ms_walkW", (ox - 10.5, oy + 70, oz + 0.2), (3.5, 90), 14, face=(ox + 4, oy + 150, 18), seed=3, coll=coll, min_gap=5, yaw_jitter=50)
        C.crowd("ms_walkE", (ox + 10.5, oy + 70, oz + 0.2), (3.5, 90), 14, face=(ox - 4, oy + 150, 18), seed=5, coll=coll, min_gap=5, yaw_jitter=50)
    S.brand_sign("ms_brand", (ox + 12.6, oy + 20, oz + 16), 270, coll, lit=night)
    if night:
        night_cast_keys(o, coll)
    plaza(o, coll, night)
    if backlots:
        back_blocks(o, night=night)
    L = _L("main_street", o, "night" if night else "day", (0, 30, 3),
           dict(wide=((0, -12, 7), (0, 60, 5), 26), close=((-6, 14, 4.2), (-11.5, 22, 3.2), 35),
                cops=((1, 28, 6), (-10, 41, 4), 30), high=((0, -30, 40), (0, 60, 0), 24),
                aerial=((0, 22, 62), (0, 132, 6), 24), aerial_end=((0, 92, 40), (0, 148, 19), 26)))
    if plaza_crowd:
        L["crowd"] = C.crowd("ms_plaza", (ox, oy + 132, oz + 0.2), (40, 22), plaza_crowd, mode="clusters", palette="light",
                             face=(ox, oy + 149, 21), seed=7, coll=coll, avoid=[(ox, oy + 135, 4.5)])
        if numbers:
            C.numbers(L["crowd"], seed=3, size=0.9, badge=True, tilt=40)
    return L


def night_cast_keys(o, coll=None, y0=-10, y1=150, step=20, focus=(0, 30, 3)):
    """R2-2: motivated keys for cast on night exteriors (faces were backlit only by signs -> unreadable in close-ups).
    - shop-window SPILL: soft warm area lights at storefront height on both sidewalks every `step` studs, aimed across
      the street and slightly toward the camera side (-Y), so a face anywhere on the street gets a warm 3/4 key
    - streetlamp-side KEY on the default cast mark (focus): soft amber from camera-left/high, matching cast.cine_light's
      key direction (45 deg off-axis, 35 deg high), plus a weak cool frontal fill so the shadow side keeps detail.
    Shadowless (no shadow-pool cost); the sets' own lamps/practicals still give the night mood."""
    ox, oy, oz = o
    for k, y in enumerate(range(y0, y1 + 1, step)):
        for s_ in (-1, 1):
            light(f"ms_spill{k}{'L' if s_ < 0 else 'R'}", "AREA", (ox + s_ * 10.5, oy + y, oz + 4.5), 420, hexc("#ffc98f"), 6,
                  target=(ox - s_ * 2.0, oy + y - 6, oz + 4.0), coll=coll, size_y=3.5, shadow=False)
    fx, fy, fz = focus
    light("ms_castKey", "AREA", (ox + fx - 5.5, oy + fy - 7.5, oz + 8.5), 520, hexc("#ffcf98"), 4,
          target=(ox + fx, oy + fy, oz + 4.6), coll=coll, shadow=False)
    light("ms_castFill", "AREA", (ox + fx + 3, oy + fy - 12, oz + 5), 120, hexc("#9fb4ff"), 8,
          target=(ox + fx, oy + fy, oz + 4.4), coll=coll, shadow=False)


def plaza(o=(0, 0, 0), coll=None, night=False):
    """Cobbled plaza in front of the pharmacy: fountain, planters, light poles, bunting, bollards, crosswalks."""
    ox, oy, oz = o
    cy = oy + 135
    stone = pbr.get("concrete", tint="#d8d0c0")
    cyl("pz_fnt", 4.0, 1.2, (ox, cy, oz + 0.6), stone, 32, 0.08, coll=coll)
    cyl("pz_fntw", 3.6, 0.1, (ox, cy, oz + 1.15), mat("tw_water", hexc("#4aa0d8"), 0.05, 0.0, coat=0.8), 32, coll=coll)
    cyl("pz_fntc", 0.8, 3.2, (ox, cy, oz + 1.6), stone, 16, 0.05, coll=coll)
    cyl("pz_fntb", 1.6, 0.4, (ox, cy, oz + 3.2), stone, 20, 0.05, coll=coll)
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        planter(f"pz_pl{k}", (ox + math.cos(a) * 15, cy + math.sin(a) * 9, oz + 0.2), coll, s=1.2, seed=20 + k)
    for s in (-1, 1):
        for k in range(5):
            cyl(f"pz_bol{s}{k}", 0.3, 1.2, (ox + s * 7.2, oy + 122 + k * 0.01 + k * 2.2 - 4, oz + 0.6), _m("#2a2e33", 0.4, 0.5), 10, coll=coll)
        street_lamp(f"pz_L{s}", (ox + s * 20, cy - 6, oz + 0.2), 0, on=night, coll=coll)
    # bunting between the lamps across the plaza
    cols = ["#c62828", "#f2c14e", "#2f7bff", "#2f8a55", "#ffffff", "#ff7a1f"]
    for k in range(20):
        x = ox - 19 + k * 2.0
        sag = 1.6 * (1 - ((x - ox) / 20) ** 2)
        box(f"pz_flag{k}", (1.0, 0.05, 1.1), (x, cy - 6, oz + 10.0 - sag), _m(cols[k % len(cols)], 0.6), 0.0, rot=(0, 45, 0), coll=coll)
    box("pz_xw", (14, 4, 0.02), (ox, oy + 120, oz + 0.02), _m("#f2efe6", 0.6), 0, coll=coll)
    for k in range(6):
        box(f"pz_xwg{k}", (1.0, 4.1, 0.03), (ox - 6.2 + k * 2.4 + 1.2, oy + 120, oz + 0.025), pbr.get("asphalt"), 0, coll=coll)


def pharmacy(o=(0, 150, 0), night=False, coll=None, screen_lines=None, t0=0.0):
    coll = coll or collection("town_pharmacy")
    ox, oy, oz = o
    facade("phm", (ox, oy, oz), 0, 30, 16, 3, "brick", "#c8b8a8", "PHARMACY +", "#1f6f4a", "#ffffff", "#2f8a55", True,
           None, night, coll, seed=21)
    lines = screen_lines or [("WE COUNT LIES", "#ffffff"), ("told ABOUT you", "#ffb020"), ("not TO you", "#ff3b3b")]
    S.street_screen("phm_scr", lines, (ox, oy - 1.4, oz + 21), 0, w=26, h=14, coll=coll, pole=False,
                    header="BLOX TOWN LIVE", glow=7.0, bezel="#1a1a1a")
    for s_ in (-1, 1):   # steel brackets + top light bar so it reads as a big LED wall from the air
        box(f"phm_scrb{s_}", (0.6, 1.6, 15.5), (ox + s_ * 13.6, oy - 0.8, oz + 21), pbr.get("steel"), 0.04, coll=coll)
    box("phm_scrt", (27.6, 1.2, 0.6), (ox, oy - 1.0, oz + 28.6), _g("#ffffff", 3.0), 0.05, coll=coll)
    light("phm_scrL", "AREA", (ox, oy - 8, oz + 21), 2500, hexc("#c0d8ff"), 18, rot=(-90, 0, 0), coll=coll, shadow=False)
    S.poster("phm_p1", "FLU SHOTS", "Walk-ins welcome\nMon-Sat", (ox + 10.5, oy - 0.25, oz + 4.5), w=2.2, h=3.0, coll=coll,
             accent="#2f8a55")
    S.closed_sign("phm_cl", (ox + 12.5, oy - 0.45, oz + 6.3), 0, coll)
    for k in range(2):
        street_lamp(f"phmL{k}", (ox + (-16 if k else 16), oy - 4, oz + 0.2), 0, on=night, coll=coll)
    planter("phm_pl", (ox - 13, oy - 3, oz + 0.2), coll, seed=7)
    trash_can("phm_tc", (ox + 14.5, oy - 2.5, oz + 0.2), coll)
    return _L("pharmacy_corner", o, "dusk", (0, -2, 6),
              dict(wide=((0, -42, 6), (0, 0, 14), 28), screen=((0, -30, 15), (0, 0, 21), 40),
                   crane=((6, -26, 3), (-4, 0, 18), 24)))


def pharmacy_corner(night=False, **kw):
    """Dusk corner shot set: builds the main street (needed for context) and returns the pharmacy cameras."""
    sky("dusk" if not night else "night", strength=0.45)
    if not night:
        sun(3.0, "#ff9a55", 7, -20)
    main_street(night=night, extras=False, env=False, **kw)
    return pharmacy_cams()


def pharmacy_cams():
    o = ORIGINS["main_street"]
    return _L("pharmacy_corner", (o[0], o[1] + 150, o[2]), "real_dusk", (0, -2, 6),
              dict(wide=((0, -42, 6), (0, 0, 14), 28), screen=((0, -30, 15), (0, 0, 21), 40),
                   crane=((6, -26, 3), (-4, 0, 18), 24)))


def night_street(**kw):
    sky("night")
    L = main_street(night=True, extras=False, cops=False, **kw)
    L["look"] = "warm_night"; L["name"] = "night_street"
    L["cams"]["alone"] = ((0 + 2, 70, 3.0), (0, 110, 4.5), 30)
    return L


def school_exterior(o=None, coll=None, students=True):
    o = o or ORIGINS["school_exterior"]
    coll = coll or collection("town_school")
    ox, oy, oz = o
    sky("day"); sun(4.0, "#ffd8a8", 22, 50)
    box("sx_lawn", (140, 120, 0.2), (ox, oy + 30, oz - 0.1), pbr.get("grass"), 0.0, coll=coll)
    box("sx_path", (16, 40, 0.22), (ox, oy + 6, oz - 0.05), pbr.get("concrete"), 0.0, coll=coll)
    box("sx_lot", (40, 30, 0.22), (ox + 42, oy + 14, oz - 0.05), pbr.get("asphalt"), 0.0, coll=coll)
    f = facade("sx_main", (ox, oy + 26, oz), 0, 50, 22, 2, "brick", None, None, shop=False, coll=coll, seed=31,
               door_color="#1f2f5a")
    S.sign("sx_sign", "BLOX TOWN MIDDLE SCHOOL", (ox, oy + 25.3, oz + 18.5), w=30, h=2.4, bg="#1f2f5a", fg="#f2c14e", coll=coll)
    for i, x in enumerate((-21.5, -9, 9, 21.5)):
        window(f"sx_gw{i}", (ox + x, oy + 25.85, oz + 5), 3.2, 4.0, None, coll)
    cyl("sx_flag_p", 0.18, 18, (ox - 12, oy + 10, oz + 9), _m("#c9d0da", 0.3, 0.8), 12, coll=coll)
    box("sx_flag", (4.5, 0.05, 2.8), (ox - 9.6, oy + 10, oz + 16.4), _m("#2f7bff", 0.6), 0.0, coll=coll)
    S.label("sx_flag_t", "BLOX", (ox - 9.6, oy + 9.95, oz + 16.4), 0.9, "#ffffff", "bold", 0, coll=coll)
    # gym: riveted steel building to the east, bike racks behind it
    gym = facade("sx_gym", (ox + 50, oy + 46, oz), 0, 30, 24, 2, "steel", "#7d8a96", "GYM", "#c62828", "#ffffff",
                 shop=False, coll=coll, seed=33, door_color="#3a4048")
    for i in range(10):
        box(f"sx_gym_rib{i}", (0.25, 0.4, 20.5), (ox + 36 + i * 3.1, oy + 45.8, oz + 10.5), pbr.get("steel", tint="#5a6470"), 0.03, coll=coll)
    bike_rack("sx_rack", (ox + 46, oy + 38, oz + 0.1), 0, 5, coll, seed=2)
    bike_rack("sx_rack2", (ox + 60, oy + 38, oz + 0.1), 0, 3, coll, seed=5)
    box("sx_hoopp", (0.4, 0.4, 10), (ox + 66, oy + 26, oz + 5), _m("#3a4048", 0.4, 0.6), 0.02, coll=coll)
    box("sx_hoopb", (4.0, 0.2, 2.6), (ox + 66, oy + 25.6, oz + 10.5), _m("#ffffff", 0.4), 0.04, coll=coll)
    cyl("sx_hoopr", 0.9, 0.08, (ox + 66, oy + 24.6, oz + 9.6), _m("#ff7a1f", 0.4, 0.5), 20, coll=coll)
    for k in range(6):
        tree(f"sx_tr{k}", (ox - 50 + k * 18, oy + 70, oz), 1.1, seed=k + 3, coll=coll)
    for k in range(3):
        bench(f"sx_bn{k}", (ox - 20 + k * 12, oy + 14, oz + 0.1), 0, coll)
    trash_can("sx_tc", (ox + 8, oy + 12, oz + 0.1), coll)
    S.poster("sx_post", "BIKE CLUB", "Racks behind gym\n3:30 sharp", (ox + 64.9, oy + 33.9, oz + 4.5), w=2.2, h=3.0,
             coll=coll, accent="#2f7bff")
    if students:
        C.crowd("sx_kids", (ox - 6, oy + 4, oz), (34, 14), 16, face=(ox, oy + 20, 0), seed=9, coll=coll,
                variants=["student_a", "student_b", "c1", "c2", "c4", "c6"], min_gap=3.5)
    return _L("school_exterior", o, "day", (46, 38, 3),
              dict(wide=((-10, -40, 8), (8, 26, 9), 26), racks=((40, 22, 4.2), (50, 40, 2.5), 32),
                   racks_low=((52, 28, 1.6), (46, 40, 2.4), 22)))


def school_hallway(o=None, coll=None, students=True):
    """School hallway v2: mixed locker colours with open dressed lockers, two bulletin boards with readable notes,
    trophy case, water fountain, classroom door with ROOM sign, GO BEARS banner, polished tile floor, ceiling grid."""
    o = o or ORIGINS["school_hallway"]
    coll = coll or collection("town_hall")
    ox, oy, oz = o
    from .core import world
    world((0.5, 0.52, 0.55), 0.2)   # r3: less flat ambient so cast separate from the lockers
    floor = pbr.get("tile", tint="#e6e0d2", tile=3, rough=0.22)
    room("sh", (ox, oy - 30, oz), 20, 70, 11, floor, ("plaster", "#eae4d4"), coll, wainscot=("steel", "#8aa6c0"), ceil="#eceae4")
    # ceiling tile grid
    for k in range(18):
        box(f"sh_cg{k}", (20, 0.12, 0.08), (ox, oy - 30 + k * 4, oz + 10.95), _m("#b8b8b2", 0.6), 0, coll=coll)
    for s in (-1, 1):
        box(f"sh_cgx{s}", (0.12, 70, 0.08), (ox + s * 3.3, oy + 5, oz + 10.95), _m("#b8b8b2", 0.6), 0, coll=coll)
    blues = ["#3f7cc4", "#3f7cc4", "#2f9a8a", "#3f7cc4", "#f2b030"]
    reds = ["#c84040", "#c84040", "#f2b030", "#c84040", "#2f6fb0"]
    locker_bank("sh_lk-1a", (ox - 8.8, oy - 6, oz), 90, 12, blues, coll, 100, open_idx=(4, 9))
    locker_bank("sh_lk1a", (ox + 8.8, oy - 6, oz), -90, 12, reds, coll, 200, open_idx=(2,))
    locker_bank("sh_lk-1b", (ox - 8.8, oy + 22, oz), 90, 10, blues[::-1], coll, 130, open_idx=(6,))
    locker_bank("sh_lk1b", (ox + 8.8, oy + 22, oz), -90, 10, reds[::-1], coll, 230)
    for k in range(6):
        ceiling_panel(f"sh_cp{k}", (ox, oy - 24 + k * 11, oz + 10.8), coll, 380)
    bulletin("sh_bb", (ox - 9.75, oy + 8.5, oz + 6.2), 90, coll, notes="Be kind.\nIt counts.")
    bulletin("sh_bb2", (ox + 9.75, oy - 22, oz + 6.2), -90, coll, notes="Study group\nRm 12 @ 3:30",
             posters=[("SPIRIT WEEK", "Mon: PJ day\nFri: Blue & Gold", "#c62828"), ("CHESS CLUB", "Wed lunch\nLibrary", "#8a2be2")])
    wall_clock("sh_clk", (ox, oy + 39.5, oz + 9.0), 0, coll)
    S.sign("sh_exit", "EXIT", (ox, oy + 39.6, oz + 10.1), w=2.0, h=0.7, bg="#2a1414", fg="#ff3b3b", coll=coll, lit=4.0, frame=None)
    door("sh_door", (ox, oy + 39.7, oz), 6.0, 8.6, None, coll, "#5a6470")
    # banner across the corridor
    S.sign("sh_banner", "GO BLOX BEARS!", (ox, oy + 30, oz + 9.0), w=13, h=1.9, bg="#1f2f5a", fg="#f2c14e", coll=coll, frame="#f2c14e")
    for s in (-1, 1):
        cyl(f"sh_banw{s}", 0.03, 1.2, (ox + s * 6, oy + 30, oz + 10.4), _m("#222222"), 6, coll=coll)
    # trophy case
    tc = _root("sh_tc", (ox + 9.6, oy + 8.5, oz), -90, coll)
    box("sh_tc_b", (6, 1.6, 7), (0, 0.6, 3.5), pbr.get("planks", tint="#6a4428"), 0.05, parent=tc, coll=coll)
    box("sh_tc_in", (5.6, 0.2, 4.6), (0, 1.0, 4.3), _m("#1f2f5a", 0.8), 0, parent=tc, coll=coll)
    box("sh_tc_sh", (5.6, 1.2, 0.1), (0, 0.6, 4.4), glass(), 0.0, parent=tc, coll=coll)
    box("sh_tc_g", (5.6, 0.1, 4.6), (0, -0.25, 4.3), glass(), 0.0, parent=tc, coll=coll)
    for k in range(4):
        cyl(f"sh_tr{k}", 0.25, 0.8, (-2 + k * 1.3, 0.6, 2.8), _m("#d9a520", 0.2, 1.0), 10, parent=tc, coll=coll)
        sphere(f"sh_trc{k}", 0.38, (-2 + k * 1.3, 0.6, 3.5), _m("#d9a520", 0.2, 1.0), seg=10, parent=tc, coll=coll)
    for k in range(3):
        box(f"sh_tpl{k}", (1.0, 0.2, 0.7), (-1.5 + k * 1.5, 0.7, 4.95), _m(["#c0c6cc", "#d9a520", "#b0703a"][k], 0.25, 0.9), 0.04, parent=tc, coll=coll)
    S.label("sh_tc_t", "CHAMPIONS 2026", (0, -0.32, 6.4), 0.32, "#f2c14e", "bold", 0, tc, coll)
    # water fountain + sign
    wf = _root("sh_wf", (ox - 9.4, oy - 23, oz), 90, coll)
    box("sh_wf_b", (2.0, 1.4, 0.9), (0, 0.4, 3.2), _m("#c0c6cc", 0.2, 0.9), 0.15, parent=wf, coll=coll)
    box("sh_wf_bs", (1.4, 0.9, 0.2), (0, 0.3, 3.62), _m("#8a9098", 0.15, 0.9), 0.05, parent=wf, coll=coll)
    box("sh_wf_bk", (2.0, 0.2, 2.6), (0, 1.0, 3.8), _m("#c0c6cc", 0.2, 0.9), 0.04, parent=wf, coll=coll)
    box("sh_wf_btn", (0.4, 0.2, 0.3), (0.7, -0.35, 3.25), _m("#2a2a2a", 0.4), 0.04, parent=wf, coll=coll)
    S.sign("sh_wf_s", "WATER", (0, 0.85, 5.7), w=1.8, h=0.6, bg="#2f7bff", fg="#ffffff", coll=coll, parent=wf, frame=None, depth=0.08)
    # classroom door on the right wall (front section) + room sign
    rd = _root("sh_rd", (ox + 9.8, oy - 26.5, oz), -90, coll)
    door("sh_rdd", (0, 0, 0), 4.0, 8.6, rd, coll, "#8a5a36")
    S.sign("sh_rds", "ROOM 12", (0, -0.4, 9.4), w=2.6, h=0.7, bg="#1f2f5a", fg="#ffffff", coll=coll, parent=rd, frame=None, depth=0.1)
    # posters
    S.poster("sh_ps1", "BE HONEST", "Words leave marks.", (ox + 9.75, oy - 15.0, oz + 9.0), -90, w=2.2, h=2.6, coll=coll, accent="#8a2be2")
    S.poster("sh_ps2", "SCIENCE FAIR", "Room 12\nThursday", (ox - 9.75, oy - 18.5, oz + 6.6), 90, w=2.4, h=3.2, coll=coll, accent="#2f7bff", tilt=3)
    S.poster("sh_ps3", "READ!", "Library open\nuntil 5pm", (ox - 9.75, oy + 34, oz + 6.6), 90, w=2.4, h=3.2, coll=coll, accent="#2f8a55", tilt=-2)
    S.poster("sh_ps4", "DANCE", "Sat 7pm\nGym", (ox + 9.75, oy + 34, oz + 6.6), -90, w=2.4, h=3.2, coll=coll, accent="#ff5a7a", tilt=2)
    # upper walls above the locker banks: pennants, class banners, honour-roll boards (fills close/OTS frames)
    pc = ["#c62828", "#f2c14e", "#2f7bff", "#2f8a55", "#ffffff"]
    for s_ in (-1, 1):
        for k in range(16):
            y = oy - 16 + k * 3.2
            pz = _root(f"sh_pn{s_}{k}", (ox + s_ * 9.78, y, oz + 9.9), -90 * s_, coll)
            poly_extrude(f"sh_pnf{s_}{k}", [(-0.7, 0), (0.7, 0), (0, -1.6)], 0.04, (0, 0, 0), _m(pc[k % 5], 0.6), rot=(90, 0, 0),
                         parent=pz, coll=coll)
        for k, (t_, sub, c) in enumerate([("CLASS OF 2031", "", "#1f2f5a"), ("HONOR ROLL", "Maya - Tyler - Sam\nLuna - Harry - Jo", "#2f8a55"),
                                          ("SCIENCE FAIR", "", "#8a2be2"), ("GO BEARS", "", "#c62828")]):
            yb = oy - 12 + k * 13 + (4 if s_ > 0 else 0)
            S.sign(f"sh_up{s_}{k}", t_, (ox + s_ * 9.7, yb, oz + 8.4), w=5.0, h=1.0, bg=c, fg="#ffffff", rot=-90 * s_, coll=coll,
                   frame=None, depth=0.08)
            if sub:
                S.note(f"sh_upn{s_}{k}", sub, (ox + s_ * 9.72, yb + (2.9 if s_ < 0 else -2.9), oz + 8.3), -90 * s_, w=2.4, h=1.0,
                       paper="#fbf8f0", ink="#1b2a6b", coll=coll, tilt=0)
    # floor clutter
    box("sh_bin", (1.2, 1.2, 2.2), (ox + 9.0, oy - 4.5 + 15, oz + 1.1), pbr.get("steel", tint="#2f8a55"), 0.05, coll=coll)
    box("sh_bp", (1.4, 0.9, 1.6), (ox - 7.6, oy - 1.0, oz + 0.8), pbr.get("fabric", tint="#c62828", tile=1.5), 0.25, rot=(0, 0, 20), coll=coll)
    box("sh_wet", (1.2, 0.08, 2.2), (ox + 5.0, oy + 26, oz + 1.1), _m("#f2c14e", 0.4), 0.04, rot=(12, 0, 15), coll=coll)
    S.label("sh_wet_t", "CAUTION\nWET FLOOR", (ox + 4.95, oy + 25.75, oz + 1.2), 0.2, "#111111", "bold", 0, coll=coll, rot=(78, 0, 15))
    for k in range(3):
        box(f"sh_paper{k}", (0.8, 1.0, 0.01), (ox - 4 + k * 2.2, oy + 6 + k * 1.8, oz + 0.02), _m("#fbf8f0", 0.8), 0, rot=(0, 0, k * 37), coll=coll)
    if students:
        C.crowd("sh_kids", (ox, oy + 22, oz), (12, 22), 9, seed=11, coll=coll,
                variants=["student_a", "student_b", "c0", "c3", "c5", "c7"], min_gap=3.0)
    return _L("school_hallway", o, "interior", (-6, -2, 4.5),
              dict(wide=((2, -28, 5.5), (0, 20, 4.5), 22), close=((1.5, -13, 5.2), (-8.6, -4, 4.6), 28),
                   ots=((3.5, -16, 5.4), (-7, -6, 4.8), 38)))



def classroom(o=None, coll=None, students=True, board="Kindness Week\n\"Say what you mean.\"\n- Mr. Otto"):
    o = o or ORIGINS["classroom"]
    coll = coll or collection("town_class")
    ox, oy, oz = o
    from .core import world
    world((0.6, 0.65, 0.75), 0.35)
    room("cr", (ox, oy - 4, oz), 36, 34, 11.5, "woodfloor", ("plaster", "#e9dcc0"), coll, wainscot=("planks", "#b88a5a"))
    S.chalk("cr_chalk", board, (ox, oy + 29.75, oz + 6.2), 0, w=16, h=5, coll=coll)
    for i in range(3):
        for j in range(3):
            desk_set(f"cr_d{i}{j}", (ox - 10 + i * 10, oy + 4 + j * 6.5, oz), 180, coll, seed=i * 3 + j)
    td = _root("cr_td", (ox + 11, oy + 22, oz), 0, coll)
    box("cr_td_t", (7, 3.4, 0.3), (0, 0, 3.4), pbr.get("planks", tint="#8a5a36", tile=3), 0.05, parent=td, coll=coll)
    box("cr_td_b", (6.6, 3.0, 3.2), (0, 0.1, 1.65), pbr.get("planks", tint="#7a4a2a", tile=3), 0.05, parent=td, coll=coll)
    sphere("cr_apple", 0.4, (ox + 9, oy + 21.5, oz + 3.95), _m("#c62828", 0.35), seg=12, coll=coll)
    sphere("cr_globe", 0.8, (ox + 13, oy + 22.5, oz + 5.0), _m("#3f7ac0", 0.4), seg=16, coll=coll)
    cyl("cr_globe_s", 0.1, 1.0, (ox + 13, oy + 22.5, oz + 3.9), _m("#d9a520", 0.3, 0.9), 8, coll=coll)
    S.note("cr_td_n", "Harry -\nso gentle!\n:)", (ox + 10.5, oy + 21.2, oz + 3.56), coll=coll, w=1.4, h=1.4, tilt=0)
    D.objects["cr_td_n"].rotation_euler = (math.radians(-80), 0, math.radians(8))
    for k in range(3):
        wr = _root(f"cr_wr{k}", (ox - 17.9, oy + 4 + k * 9, oz + 6), 90, coll)
        window(f"cr_w{k}", (0, 0, 0), 3.6, 5.0, wr, coll, view="#fff1d6")
    for k in range(3):
        light(f"cr_sunL{k}", "AREA", (ox - 20, oy + 4 + k * 9, oz + 7), 900, hexc("#ffe2b8"), 4, rot=(0, -70, 0), coll=coll)
        box(f"cr_wcut{k}", (0.5, 3.6, 5.0), (ox - 18.2, oy + 4 + k * 9, oz + 6), _g("#fff4dc", 3.0), 0.0, coll=coll)
    wall_clock("cr_clk", (ox + 8, oy + 29.75, oz + 9.6), 0, coll)
    shelf("cr_sh", (ox + 17.2, oy + 8, oz), -90, coll, seed=4, w=6, rows=3)
    S.poster("cr_ps1", "READ!", "Books are\ndoors.", (ox - 12, oy + 29.75, oz + 7), w=2.4, h=3.2, coll=coll, accent="#2f8a55")
    S.poster("cr_ps2", "MATH", "2 + 2 = 4\nalways.", (ox + 15, oy + 29.75, oz + 7), w=2.4, h=3.2, coll=coll, accent="#ff7a1f")
    for k in range(4):
        ceiling_panel(f"cr_cp{k}", (ox + (-8 if k % 2 else 8), oy + 6 + (k // 2) * 14, oz + 11.3), coll, 300)
    if students:
        for k, (i, j) in enumerate([(0, 1), (2, 0), (2, 2), (1, 2)]):
            C.extra(f"cr_kid{k}", (ox - 10 + i * 10, oy + 4 + j * 6.5 - 2.2, oz + 0.9), 180,
                    ["student_a", "student_b", "c3", "c6"][k], coll, pose="lookup")
    return _L("classroom", o, "interior", (11, 21, 4),
              dict(wide=((0, -2, 8.5), (0, 24, 4.5), 22), teacher=((15, 9, 5.5), (11, 22, 4.5), 30),
                   board=((0, 14, 6.5), (0, 30, 6.2), 30)))


def kitchen(o=None, coll=None, night=True, posts=None, day=None):
    """Harry's kitchen v2 (night = warm evening practicals; night=False / day=True = sunny morning).
    Dressing: counter with sink/stove/range hood, window over sink with painted view + curtains + sill plants, open shelf
    with labelled jars, utensil rail with pans, kettle, toaster, bread board, dish rack, utensil crock, fridge with
    magnets/photos/kid drawing/notes and cereal on top, calendar, clock, framed art, cookbook shelf, rug, table with
    laptop/mug/fruit/mail/vase, pendant. Cams: wide, laptop, counter, fridge."""
    if day is not None:
        night = not day
    o = o or ORIGINS["kitchen"]
    coll = coll or collection("town_kitchen")
    ox, oy, oz = o
    P = lambda x, y, z: (ox + x, oy + y, oz + z)
    from .core import world
    world((0.16, 0.12, 0.09) if night else (0.62, 0.64, 0.7), 0.6 if night else 0.45)   # r3: warm night ambient (was near-black navy)
    room("kt", (ox, oy - 4, oz), 30, 24, 11, "woodfloor", ("plaster", "#efdcbc" if night else "#f4e6c8"), coll,
         fill=0.7 if night else 1.0, ceil="#d9cbb6" if night else "#f2efe8", wainscot=("planks", "#f2ece0"))
    # crown moulding
    box("kt_crown", (30, 0.35, 0.4), P(0, 19.8, 10.8), _m("#f8f4ea", 0.5), 0.05, coll=coll)
    # ---- back wall: counter run, sink window, shelf, hood, upper cabinet
    kitchen_counter("kt_ct", P(-2, 18.6, 0), 0, 16, coll, upper=False)
    window("kt_win", P(-6, 19.65, 7.6), 5, 3.4, None, coll, view="#1c2a5a" if night else "#dfeeff")
    window_view("kt_view", P(-6, 19.65, 7.6), 5, 3.4, night, coll)
    curtains("kt_cur", P(-6, 19.65, 7.6), 5, 3.4, "#c8503a" if night else "#e8a24a", coll)
    potted_plant("kt_sill1", P(-7.3, 19.2, 5.55), 0.4, coll)
    jar("kt_sillj", P(-4.6, 19.25, 5.55), None, "#7ab83a", coll, h=0.6, r=0.25)
    wall_shelf("kt_osh1", P(-1.4, 19.3, 6.9), 0, 2.8, coll, ["plates", "books"], seed=3)
    sh2 = _root("kt_osh2", P(-1.4, 19.3, 8.9), 0, coll)
    box("kt_osh2_b", (2.8, 1.0, 0.16), (0, 0, 0), pbr.get("planks", tint="#b88a5a", tile=2), 0.03, parent=sh2, coll=coll)
    for k, (t, c) in enumerate([("FLOUR", "#f4f0e4"), ("SUGAR", "#ffffff"), ("COFFEE", "#4a2a14")]):
        jar(f"kt_jar{k}", P(-2.35 + k * 0.95, 19.3, 8.98), t, c, coll, h=1.05, r=0.36)
    hanging_rail("kt_rail", P(-1.4, 19.75, 6.3), 2.8, coll, pans=False)
    # range hood over the stove (stove at local x 2)
    hd = _m("#c8ccd0", 0.28, 0.85)
    box("kt_hood", (3.6, 2.2, 0.9), P(2, 18.9, 7.4), hd, 0.1, coll=coll)
    box("kt_hood2", (1.6, 1.3, 3.0), P(2, 19.3, 9.3), hd, 0.05, coll=coll)
    light("kt_hoodL", "AREA", P(2, 18.6, 6.85), 120 if night else 40, hexc("#ffd29a"), 1.6, rot=(0, 0, 0), coll=coll, shadow=False)
    box("kt_hoodS", (2.4, 0.8, 0.04), P(2, 18.6, 6.93), _g("#ffe2b0", 3.0), 0, coll=coll)
    # upper cabinet right of the hood + pots on it
    box("kt_upc", (2.4, 1.6, 3.0), P(5.0, 19.2, 8.4), pbr.get("planks", tint="#e8e2d4", tile=3), 0.04, coll=coll)
    box("kt_upcl", (0.04, 0.05, 2.6), P(5.0, 18.38, 8.4), _m("#15181d"), 0, coll=coll)
    for k in (-1, 1):
        box(f"kt_upch{k}", (0.08, 0.1, 0.5), P(5.0 + k * 0.3, 18.33, 7.6), _m("#c9d0da", 0.25, 0.9), 0.02, coll=coll)
    cyl("kt_upot", 0.6, 0.7, P(5.0, 19.2, 10.25), _m("#c0582a", 0.3, 0.3), 16, 0.05, coll=coll)
    # counter-top props (counter top z 3.62)
    kettle("kt_kettle", P(2.7, 18.2, 3.66), "#d9453a" if night else "#19c2b0", coll)
    toaster("kt_toast", P(5.3, 19.2, 3.62), coll=coll)
    bread_board("kt_bread", P(4.6, 17.9, 3.62), coll)
    dish_rack("kt_rack", P(-3.5, 18.8, 3.62), coll)
    utensil_crock("kt_crock", P(-0.6, 19.2, 3.62), coll)
    cyl("kt_towel", 0.32, 1.2, P(-1.6, 19.3, 4.4), _m("#ffffff", 0.9), 14, 0.02, rot=(0, 90, 0), coll=coll)
    box("kt_soap", (0.3, 0.3, 0.7), P(-7.9, 19.1, 3.97), _m("#2fb06a", 0.2), 0.08, coll=coll)
    box("kt_dtowel", (1.2, 0.08, 1.4), P(-6, 17.25, 2.8), pbr.get("fabric", tint="#c8503a", tile=0.6), 0.04, coll=coll)
    # ---- fridge with magnets, photos, kid drawing, notes; cereal on top
    fr = fridge("kt_fr", P(10.5, 18.2, 0), 0, coll, notes=("Milk\nEggs\nBread", "Covered,\nHarry. <3"))
    S.note("kt_fr_kid", "HARRY\nage 7", (0.6, -1.56, 3.4), w=1.3, h=1.5, paper="#ffffff", ink="#c62828", coll=coll, parent=fr, tilt=-5)
    for k, (dx, dz, c) in enumerate([(-0.9, 2.6, "#7ab0d8"), (-0.5, 4.0, "#c8a070"), (1.0, 5.0, "#a8c87a")]):
        picture(f"kt_fr_ph{k}", (dx, -1.58, dz), 0, 0.9, 0.7, coll, c, parent=fr)
    for k, c in enumerate(["#f2c14e", "#2f8a55", "#ff5a7a", "#2f7bff"]):
        box(f"kt_fr_mg{k}", (0.28, 0.08, 0.2), (-1.2 + k * 0.7, -1.56, 7.6 - (k % 2) * 0.5), _m(c, 0.4), 0.04, parent=fr, coll=coll)
    for k, (t, c) in enumerate([("BLOX\nO's", "#c62828"), ("OATS", "#f2c14e")]):
        box(f"kt_cer{k}", (1.2, 0.5, 1.7), (-0.8 + k * 1.4, 0, 9.25), _m(c, 0.5), 0.03, parent=fr, coll=coll)
        S.label(f"kt_cert{k}", t, (-0.8 + k * 1.4, -0.27, 9.3), 0.24, "#ffffff", "bold", 0, fr, coll)
    calendar("kt_cal", P(7.6, 19.75, 6.6), 0, coll, note_txt="Mom: late shift Thu")
    # ---- left part of back wall: clock + plaque
    wall_clock("kt_clk", P(-12.2, 19.75, 8.6), 0, coll)
    framed_art("kt_home", P(-12.2, 19.75, 5.6), 0, 3.8, 1.8, coll, text="Home sweet home")
    potted_plant("kt_plant", P(-13.2, 17.5, 0), 1.3, coll)
    # ---- left wall: art, cookbook shelf, photos
    framed_art("kt_art1", P(-14.75, 6, 7.2), 90, 3.0, 2.2, coll, "landscape")
    picture("kt_pic1", P(-14.75, 10.2, 7.6), 90, 1.6, 1.2, coll, "#c8a070")
    picture("kt_pic2", P(-14.75, 10.2, 5.9), 90, 1.2, 1.5, coll, "#7ab0d8")
    wall_shelf("kt_cbook", P(-14.3, 13.8, 6.4), 90, 3.6, coll, ["books", "plant", "frame"], seed=8)
    # ---- right wall: art + coat hooks
    framed_art("kt_art2", P(14.75, 8, 7.2), -90, 2.6, 2.0, coll, "sunset")
    # ---- table set
    box("kt_rug", (12, 9, 0.05), P(-4, 6, 0.03), pbr.get("fabric", tint="#b04a3a" if night else "#3f6ea0", tile=1.4), 0.02, coll=coll)
    tb = _root("kt_tb", P(-4, 6, 0), 0, coll)
    box("kt_tb_t", (9, 5.5, 0.3), (0, 0, 3.6), pbr.get("planks", tint="#b88a5a", tile=3), 0.05, parent=tb, coll=coll)
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(f"kt_tb_l{sx}{sy}", (0.3, 0.3, 3.5), (sx * 4, sy * 2.3, 1.75), _m("#5a3a20"), 0.03, parent=tb, coll=coll)
    for k, (dx, dy, yaw) in enumerate([(-2.5, -4.2, 0), (2.5, -4.2, 0), (5.8, 0, 90), (-2.5, 4.2, 180)]):
        ch = _root(f"kt_ch{k}", P(-4 + dx, 6 + dy, 0), yaw, coll)
        box(f"kt_ch{k}_s", (2.2, 2.2, 0.25), (0, 0, 2.3), pbr.get("planks", tint="#8a5a36", tile=2), 0.05, parent=ch, coll=coll)
        box(f"kt_ch{k}_b", (2.2, 0.25, 2.8), (0, -1.0, 3.7), pbr.get("planks", tint="#8a5a36", tile=2), 0.05, parent=ch, coll=coll)
        box(f"kt_ch{k}_cu", (1.9, 1.9, 0.2), (0, 0, 2.5), pbr.get("fabric", tint="#e8a24a", tile=1), 0.08, parent=ch, coll=coll)
        for sx in (-1, 1):
            for sy in (-1, 1):
                box(f"kt_ch{k}_l{sx}{sy}", (0.2, 0.2, 2.2), (sx * 0.9, sy * 0.9, 1.1), _m("#5a3a20"), 0.02, parent=ch, coll=coll)
    S.laptop("kt_lap", P(-4.5, 6.3, 3.75), 360, title="Blox Social", user="@kitchen_laptop",
             posts=posts or ["Harry is SO gentle <3", "Harry never lies!", "Best kid in town :)", "Harry helped me again"], coll=coll)
    mug("kt_mug", P(-1.5, 5.5, 4.1), "#19c2b0", coll)
    fruit_bowl("kt_fb", P(-7.0, 7.2, 3.95), coll)
    box("kt_nap", (1.0, 1.0, 0.05), P(-1.0, 7.5, 3.78), _m("#f4f0e4", 0.9), 0.0, coll=coll)
    mail_pile("kt_mail", P(-0.9, 7.6, 3.8), coll)
    vase("kt_vase", P(-6.6, 4.4, 3.75), coll)
    for k, c in enumerate(["#ffffff", "#2a2a2a"]):
        cyl(f"kt_sp{k}", 0.13, 0.45, P(-2.6 + k * 0.32, 8.0, 3.98), _m(c, 0.3), 10, 0.03, coll=coll)
    for k, (dx, dy) in enumerate([(-6.0, 4.2), (-2.0, 4.2)]):
        box(f"kt_pm{k}", (2.0, 1.4, 0.03), P(dx, dy, 3.77), pbr.get("fabric", tint="#f2e6c8", tile=0.8), 0.0, coll=coll)
    S.phone("kt_phone", P(-7.5, 4.6, 3.8), 0, app="blank", title="", coll=coll)
    D.objects["kt_phone"].rotation_euler = (math.radians(-90), 0, math.radians(20))
    # pendant over table
    cyl("kt_pcord", 0.03, 3.5, P(-4, 6, 9.2), _m("#111111"), 6, coll=coll)
    cyl("kt_pshade", 1.0, 0.9, P(-4, 6, 7.1), _m("#1e1e1e", 0.4, 0.4), 20, r2=0.35, coll=coll)
    sphere("kt_pbulb", 0.3, P(-4, 6, 6.6), _g("#ffc977", 8 if night else 3), seg=10, coll=coll)
    light("kt_pL", "SPOT", P(-4, 6, 6.5), 900 if night else 250, hexc("#ffb867"), 0.4, rot=(0, 0, 0), coll=coll, spot=80, blend=0.6)
    light("kt_lapL", "AREA", P(-4.5, 7.2, 4.6), 60, hexc("#a8c4ff"), 1.6, rot=(-75, 0, 0), coll=coll)
    light("kt_bounce", "AREA", P(0, 8, 0.6), 350 if night else 300, hexc("#ffd8b0" if night else "#fff2e0"), 22, rot=(180, 0, 0), coll=coll,
          size_y=16, shadow=False)   # floor bounce so the ceiling is not a black slab in vertical wides
    if night:   # warm practicals: under-cabinet strip, corner floor lamp, key; cool moon at the window
        light("kt_ucL", "AREA", P(-2, 18.4, 6.4), 260, hexc("#ffcf8a"), 14, coll=coll, size_y=0.6, shadow=False)
        # r2: warm up-bounce so the ceiling is not a dark band at night
        light("kt_ceilB", "AREA", P(0, 8, 9.2), 380, hexc("#ffe6c8"), 28, rot=(180, 0, 0), coll=coll, size_y=24, shadow=False)
        # r3: wash the top of the back wall / crown so the ceiling-wall junction is not a black band in wides
        light("kt_wallW", "AREA", P(0, 9, 7.5), 260, hexc("#ffe2c0"), 26, target=P(0, 20, 10), coll=coll, size_y=6, shadow=False)
        light("kt_keyL", "AREA", P(2, -6, 9.5), 700, hexc("#ffc890"), 6, target=P(2, 3, 4), coll=coll)
        light("kt_cnL", "SPOT", P(12, 4, 5.4), 700, hexc("#ffb867"), 0.5, coll=coll, spot=120, blend=0.8)
        cyl("kt_fl_p", 0.08, 6, P(12, 4, 3), _m("#2a2a2a", 0.4, 0.5), 8, coll=coll)
        cyl("kt_fl_s", 0.8, 1.2, P(12, 4, 6.2), _g("#ffe0b0", 1.5), 16, coll=coll)
        light("kt_moon", "AREA", P(-6, 18.6, 8.0), 220, hexc("#7a9cff"), 4, target=P(-5, 8, 3), coll=coll)
        # r3 (D8): camera-side warm fill over the playing area + low floor wash, so dark costumes (Dad flannel, Tyler navy)
        # keep detail without cine_light and the foreground floor is warm wood, not a navy band
        light("kt_frontF", "AREA", P(0, -8, 7), 420, hexc("#ffdcb4"), 16, target=P(0, 6, 3.5), coll=coll, size_y=6, shadow=False)
        light("kt_floorW", "AREA", P(0, -2, 4.5), 200, hexc("#ffd2a0"), 18, target=P(0, 4, 0), coll=coll, size_y=6, shadow=False)
    else:       # morning sun through the window: warm beam onto the table + soft sky bounce
        light("kt_sunL", "SPOT", P(-6, 19.2, 9.5), 4000, hexc("#ffe2b0"), 1.2, target=P(-4, 6, 3.6), coll=coll, spot=55, blend=0.7)
        light("kt_skyL", "AREA", P(-6, 18.8, 7.6), 500, hexc("#dfeeff"), 5, target=P(-4, 6, 3), coll=coll, shadow=False)
        light("kt_keyL", "AREA", P(2, -6, 9.5), 500, hexc("#fff2e0"), 8, target=P(2, 3, 4), coll=coll, shadow=False)
    L = _L("kitchen", o, "evening_kitchen" if night else "interior", (-4.5, 6, 4.5),
           dict(wide=((5, -7, 6.2), (-3, 12, 5.4), 22), laptop=((-2, 0.5, 6.5), (-4.5, 6.8, 4.6), 35),
                counter=((-1, 7.5, 5.8), (-1.5, 19, 5.6), 22), fridge=((4, 6, 6.2), (9, 19, 5.6), 24)))
    L["cast_spots"] = [(ox + 1.5, oy - 0.5, oz, -15), (ox + 4.5, oy + 0.5, oz, -25), (ox + 7.5, oy + 1.5, oz, -35)]
    return L



def _interior_cast_light(pre, o, coll, night, tgt=(0, 4, 4.0)):
    """R3-2 r4: motivated warm cast light for small interiors (bedroom / front hall), day AND night.
    Camera-side soft key (window/lamp-motivated) on the playing area + low warm floor wash + ceiling bounce, so faces and
    dark costumes keep detail and the room never sinks into a blue-grey cast. Shadowless fills; the key casts soft shadow."""
    ox, oy, oz = o
    T_ = (ox + tgt[0], oy + tgt[1], oz + tgt[2])
    light(pre + "_castK", "AREA", (ox - 5, oy - 9, oz + 8.5), 520 if night else 380, hexc("#ffcf9a" if night else "#fff0dc"), 6,
          target=T_, coll=coll)
    light(pre + "_castF", "AREA", (ox + 2, oy - 8, oz + 6), 360 if night else 260, hexc("#ffdcb4"), 14, target=T_, coll=coll,
          size_y=6, shadow=False)
    light(pre + "_floorW", "AREA", (ox, oy - 2, oz + 4.5), 160, hexc("#ffd2a0"), 16, target=(T_[0], T_[1], oz), coll=coll,
          size_y=6, shadow=False)
    light(pre + "_ceilB", "AREA", (ox, oy + 6, oz + 9.8), 300 if night else 200, hexc("#ffe6c8"), 18, rot=(180, 0, 0), coll=coll,
          size_y=16, shadow=False)


def bedroom(o=None, coll=None, morning=True, night=False):
    """Harry's bedroom. morning (default) = warm sun through the window; night=True = desk-lamp practical, faint moon at
    the window, warm motivated key on the cast (look 'evening_kitchen', never a blue-graded room)."""
    o = o or ORIGINS["bedroom"]
    coll = coll or collection("town_bedroom")
    ox, oy, oz = o
    from .core import world
    # r4 (R3-2): neutral-warm ambient (was a cool (0.55,0.6,0.75) that put a blue-grey cast on every shadow side)
    world((0.62, 0.56, 0.5) if not night else (0.3, 0.26, 0.26), 0.35 if not night else 0.4)
    if night:
        morning = False
    room("bd", (ox, oy - 2, oz), 26, 22, 10.5, "woodfloor", ("plaster", "#cfe0e8"), coll)
    bed("bd_bed", (ox - 7, oy + 13, oz), 0, coll)
    window("bd_win", (ox + 2, oy + 19.65, oz + 6), 5, 4, None, coll, view="#e6f2ff")
    if night:
        light("bd_moon", "AREA", (ox + 2, oy + 24, oz + 7.5), 260, hexc("#9db4ff"), 5, rot=(70, 0, 0), coll=coll)
        box("bd_wsky", (5, 0.1, 4), (ox + 2, oy + 19.75, oz + 6), _g("#26346a", 1.2), 0.0, coll=coll)
        light("bd_lampL", "SPOT", (ox + 10.2, oy + 17.2, oz + 5.2), 500, hexc("#ffb867"), 0.4, coll=coll, spot=120, blend=0.8)
    else:
        light("bd_sun", "AREA", (ox + 2, oy + 24, oz + 7.5), 1800 if morning else 400, hexc("#ffe2b0"), 5, rot=(70, 0, 0), coll=coll)
        box("bd_wsky", (5, 0.1, 4), (ox + 2, oy + 19.75, oz + 6), _g("#cfe6ff", 2.0), 0.0, coll=coll)
    _interior_cast_light("bd", o, coll, night, tgt=(-1, 6, 4.0))
    dk = _root("bd_desk", (ox + 8, oy + 17, oz), 0, coll)
    box("bd_desk_t", (7, 3, 0.25), (0, 0, 3.4), pbr.get("planks", tint="#d8b080", tile=3), 0.04, parent=dk, coll=coll)
    for sx in (-1, 1):
        box(f"bd_desk_l{sx}", (0.25, 2.8, 3.3), (sx * 3.3, 0, 1.65), pbr.get("planks", tint="#d8b080", tile=3), 0.03, parent=dk, coll=coll)
    cyl("bd_lamp_b", 0.5, 0.15, (ox + 10.5, oy + 17.5, oz + 3.6), _m("#2a2a2a", 0.4), 16, coll=coll)
    cyl("bd_lamp_a", 0.07, 1.8, (ox + 10.5, oy + 17.5, oz + 4.5), _m("#2a2a2a", 0.4), 8, coll=coll)
    cyl("bd_lamp_s", 0.6, 0.6, (ox + 10.2, oy + 17.2, oz + 5.4), _g("#ffd27a", 3.0) if night else _m("#f2c14e", 0.4), 16, coll=coll)
    box("bd_bag", (2.4, 1.6, 2.2), (ox + 6.5, oy + 13.5, oz + 1.1), pbr.get("fabric", tint="#c62828", tile=2), 0.2, coll=coll)
    S.label("bd_bag_t", "QUICK\nDELIVERY", (ox + 6.5, oy + 12.68, oz + 1.2), 0.24, "#ffffff", "bold", 0, coll=coll)
    S.poster("bd_ps1", "BLOX RACERS", "Season 4", (ox - 2, oy + 19.75, oz + 7), w=2.4, h=3.2, coll=coll, accent="#2f7bff")
    S.brand_sign("bd_brand", (ox + 8.5, oy + 19.6, oz + 8.2), 0, coll, lit=False)
    D.objects["bd_brand"].scale = (0.4, 0.4, 0.4)
    shelf("bd_sh", (ox + 12.75, oy + 6, oz + 0.2), -90, coll, seed=2, w=5, rows=3)
    cyl("bd_rug", 4.0, 0.06, (ox - 1, oy + 6, oz + 0.03), pbr.get("fabric", tint="#e8a050", tile=2), 32, coll=coll)
    S.note("bd_note", "deliveries:\n4pm - Oak St\n5pm - Mill Rd", (ox + 6.6, oy + 18.4, oz + 5.2), coll=coll, w=1.4, h=1.5)
    mug("bd_mug", (ox + 9.5, oy + 16.6, oz + 3.9), "#2f7bff", coll)
    return _L("bedroom", o, "evening_kitchen" if night else "day", (-1, 10, 4.5),
              dict(wide=((4, -12, 7), (-1, 12, 4), 22), desk=((3, 6, 6), (8, 17, 4), 26)))


def front_hall(o=None, coll=None, night=False):
    """Front-door hallway. night=True: warm ceiling practical + warm motivated cast key, dim cool spill at the door."""
    o = o or ORIGINS["front_hall"]
    coll = coll or collection("town_fhall")
    ox, oy, oz = o
    from .core import world
    world((0.62, 0.57, 0.52) if not night else (0.3, 0.26, 0.26), 0.35 if not night else 0.4)
    _interior_cast_light("fh", o, coll, night, tgt=(0, 5, 4.0))
    if night:
        light("fh_doorM", "AREA", (ox, oy + 13.2, oz + 5), 120, hexc("#9db4ff"), 3, target=(ox, oy + 6, oz + 3), coll=coll, shadow=False)
    room("fh", (ox, oy - 2, oz), 18, 16, 10.5, "woodfloor", ("plaster", "#ede0c6"), coll, wainscot=("planks", "#f2ece0"))
    door("fh_door", (ox, oy + 13.7, oz), 4.2, 8.6, None, coll, "#7a2a1a")
    light("fh_dl", "AREA", (ox, oy + 12.5, oz + 9.6), 300, hexc("#ffe2b8"), 3, coll=coll)
    box("fh_mat", (5, 2.6, 0.06), (ox, oy + 11.5, oz + 0.03), pbr.get("fabric", tint="#8a3a2a", tile=1.5), 0.02, coll=coll)
    rk = _root("fh_rack", (ox - 6, oy + 13.6, oz), 0, coll)
    box("fh_rack_b", (4, 0.3, 0.5), (0, 0, 7.4), pbr.get("planks", tint="#6a4428"), 0.03, parent=rk, coll=coll)
    for k, c in enumerate(["#2f5a8a", "#c62828", "#e8d8b0"]):
        box(f"fh_coat{k}", (1.2, 0.6, 3.2), (-1.3 + k * 1.3, -0.4, 5.6), pbr.get("fabric", tint=c, tile=2), 0.25, parent=rk, coll=coll)
    sr = _root("fh_shoe", (ox + 6, oy + 12.6, oz), 0, coll)
    box("fh_shoe_b", (4, 1.6, 2.0), (0, 0, 1.0), pbr.get("planks", tint="#b88a5a"), 0.04, parent=sr, coll=coll)
    for k in range(3):
        box(f"fh_sh{k}", (0.6, 1.2, 0.4), (-1.2 + k * 1.2, -0.1, 2.2), _m(["#111111", "#f4f4f4", "#c62828"][k], 0.5), 0.12, parent=sr, coll=coll)
    box("fh_keys", (0.4, 0.2, 0.05), (ox + 5.5, oy + 12.4, oz + 2.05), _m("#d9a520", 0.3, 0.9), 0.02, coll=coll)
    box("fh_mirror", (2.6, 0.1, 3.6), (ox + 6, oy + 13.75, oz + 5.6), mat("tw_mirror", (0.9, 0.92, 0.95), 0.02, 1.0), 0.03, coll=coll)
    for k in range(3):
        picture(f"fh_ph{k}", (ox - 8.75, oy + 4 + k * 3, oz + 6 + (k % 2) * 0.6), 90, 1.6, 1.3, coll,
                ["#c8a070", "#7ab0d8", "#a8c87a"][k])
    potted_plant("fh_plant", (ox - 7, oy + 10, oz), 1.0, coll)
    wall_clock("fh_clk", (ox + 8.75, oy + 6, oz + 7.5), -90, coll)
    return _L("front_hall", o, "evening_kitchen" if night else "interior", (0, 8, 4.6),
              dict(wide=((0, -10, 6), (0, 10, 4.5), 22), cuff=((3, 1, 5), (0, 9, 4), 32)))


# ------------------------------------------------------------------ inserts v2 (ECU)
def _bokeh_backdrop(prefix, o, coll, warm=True, seed=0, dist=14.0):
    """Out-of-focus room behind an insert: dim wall + counter shape + scattered small emissive spheres (bokeh balls)."""
    rnd = random.Random(seed)
    ox, oy, oz = o
    box(prefix + "_bgw", (60, 0.4, 70), (ox, oy + dist + 6, oz + 12), _m("#7a5a44" if warm else "#34405a", 0.9), 0, coll=coll)
    box(prefix + "_bgc", (24, 3, 3.2), (ox + 3, oy + dist, oz - 5.5), pbr.get("planks", tint="#8a6a4a", tile=3), 0.05, coll=coll)
    box(prefix + "_bgf", (3.4, 3, 9), (ox - 7, oy + dist + 1, oz - 2), _m("#c8ccd0", 0.3, 0.3), 0.1, coll=coll)
    for k in range(22):
        c = rnd.choice(["#ffb867", "#ffcf8a", "#ffe2b0", "#ff9a55"] if warm else ["#7ab0ff", "#a8c4ff", "#ffcf8a"])
        sphere(f"{prefix}_bk{k}", rnd.uniform(0.12, 0.3), (ox + rnd.uniform(-12, 12), oy + dist + rnd.uniform(-2, 4), oz + rnd.uniform(-3, 7)),
               _g(c, rnd.uniform(4, 10)), seg=40, coll=coll)
    light(prefix + "_bgL", "AREA", (ox + 4, oy + dist - 3, oz + 6), 900, hexc("#ffb867" if warm else "#7a9cff"), 12, target=(ox, oy + dist, oz), coll=coll)
    # upper wash: tall wall top stayed ~6 % luma above the arm in up-angled insert cams (black level must be > 8 %)
    light(prefix + "_bgL3", "AREA", (ox - 3, oy + dist - 4, oz + 14), 1200, hexc("#ffb08a" if warm else "#8aa4ff"), 16,
          target=(ox, oy + dist + 6, oz + 12), coll=coll, shadow=False)
    # lower half: tabletop + low wash + low bokeh, so vertical ECUs never sit on a black bottom half
    box(prefix + "_bgt", (40, 16, 0.4), (ox, oy + dist - 6, oz - 7.5), pbr.get("planks", tint="#a07a52" if warm else "#6a7488", tile=4), 0.05, coll=coll)
    light(prefix + "_bgL2", "AREA", (ox - 2, oy + dist - 8, oz - 2.5), 900, hexc("#ffcf9a" if warm else "#9ab4ff"), 14,
          target=(ox, oy + dist, oz - 6), coll=coll, shadow=False)
    for k in range(10):
        c = rnd.choice(["#ffb867", "#ffcf8a", "#ffe2b0"] if warm else ["#7ab0ff", "#a8c4ff", "#ffcf8a"])
        sphere(f"{prefix}_bkl{k}", rnd.uniform(0.15, 0.32), (ox + rnd.uniform(-12, 12), oy + dist + rnd.uniform(-1, 4), oz + rnd.uniform(-7, -2)),
               _g(c, rnd.uniform(4, 9)), seg=40, coll=coll)


# insert-arm palette per cast role (mirrors cast.py v3 designs: skin, sleeve, rib cuff) - keep in sync with CAST.md
ARM_STYLE = dict(host=("#e9b98f", "#efe6d2", "#5a141d"), mayor=("#f0c9a4", "#1f2a52", "#f2f0ea"),
                 bestie=("#efcfb0", "#1f2f5c", "#18244a"), crush=("#f3d3b8", "#4a5f80", "#7f93b3"),
                 mom=("#b07a52", "#2a9d8f", "#23877b"), dad=("#b07a52", "#a8262a", "#7e2420"),
                 grandpa=("#efcfae", "#efe6d2", "#d9cdb4"), grandma=("#f2d6c0", "#a58fd0", "#8e78bb"))


def skin_mat(skin):
    """Insert-grade skin (r5, D4/R4-1): subsurface + coat + low-frequency tone mottling, a strong grazing-angle falloff to
    a deeper, redder terminator tone (fake SSS), ambient-occlusion darkening in every crease (finger gaps, wrist, knuckle
    roots) and a micro-normal - so an ECU forearm/hand shades like skin instead of a flat peach plastic slab.
    Cached per skin colour."""
    key = f"tw_skinx3_{skin}"
    if key in D.materials:
        return D.materials[key]
    m = mat(key, hexc(skin), 0.5, coat=0.08)
    nt = m.node_tree; b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    for k, v in (("Subsurface Weight", 0.35), ("Subsurface Scale", 0.12), ("Subsurface Radius", (1.0, 0.35, 0.2)),
                 ("Coat Roughness", 0.45), ("Specular IOR Level", 0.35)):
        try:
            b.inputs[k].default_value = v
        except (KeyError, TypeError):
            pass
    base = hexc(skin)
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 2.2; nz.inputs["Detail"].default_value = 3.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.3; ramp.color_ramp.elements[1].position = 0.7
    ramp.color_ramp.elements[0].color = (*(c * 0.86 for c in base), 1)                     # cooler/darker patches
    ramp.color_ramp.elements[1].color = (min(1, base[0] * 1.05), base[1] * 0.96, base[2] * 0.9, 1)   # warm flush
    nt.links.new(nz.outputs["Fac"], ramp.inputs["Fac"])
    # grazing falloff: Facing -> curve (0 at the face centre, 1 at the silhouette) -> multiply toward a deep red-brown,
    # so every rounded block face shades centre-to-edge (the r4 0.35-blend version was invisible under the grade)
    lw = nt.nodes.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.55
    fr = nt.nodes.new("ShaderNodeMapRange"); fr.inputs["From Min"].default_value = 0.15; fr.inputs["From Max"].default_value = 0.85
    nt.links.new(lw.outputs["Facing"], fr.inputs["Value"])
    mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.blend_type = "MULTIPLY"
    nt.links.new(fr.outputs["Result"], mx.inputs["Factor"])
    nt.links.new(ramp.outputs["Color"], mx.inputs[6])
    mx.inputs[7].default_value = (0.86, 0.5, 0.4, 1)
    # crease AO: dark warm core in every gap/contact (finger separations, palm/wrist joint) - reads as real geometry
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion"); ao.inputs["Distance"].default_value = 0.25; ao.samples = 8
    ar = nt.nodes.new("ShaderNodeMapRange"); ar.inputs["To Min"].default_value = 0.45
    nt.links.new(ao.outputs["AO"], ar.inputs["Value"])
    ma = nt.nodes.new("ShaderNodeMix"); ma.data_type = "RGBA"; ma.blend_type = "MULTIPLY"; ma.inputs["Factor"].default_value = 1.0
    nt.links.new(mx.outputs[2], ma.inputs[6])
    cm = nt.nodes.new("ShaderNodeCombineColor")
    for ch, w in (("Red", 1.0), ("Green", 0.92), ("Blue", 0.88)):
        nt.links.new(ar.outputs["Result"], cm.inputs[ch])
    nt.links.new(cm.outputs["Color"], ma.inputs[7])
    nt.links.new(ma.outputs[2], b.inputs["Base Color"])
    mn = nt.nodes.new("ShaderNodeTexNoise"); mn.inputs["Scale"].default_value = 60.0
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.08; bp.inputs["Distance"].default_value = 0.01
    nt.links.new(mn.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def knit_mat(col):
    """Matte knit (rib cuffs): flat cuff colour, sheen for the soft fabric edge glow, no image texture (no tiling stripes)."""
    key = f"tw_knit_{col}"
    if key in D.materials:
        return D.materials[key]
    m = mat(key, hexc(col), 0.88)
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    for k, v in (("Sheen Weight", 0.3), ("Sheen Roughness", 0.5), ("Sheen Tint", (*hexc(col), 1))):
        try:
            b.inputs[k].default_value = v
        except (KeyError, TypeError):
            pass
    return m


def block_hand(name, root, x0, skin, coll=None):
    """Roblox block FIST at the -X end of a 1x1 forearm (x0 = wrist end), back of the hand toward -Y (camera).
    r5 (D4/R4-1): the palm OVERLAPS the forearm (no bevel groove, so arm+hand no longer read as a stack of separate
    blocks), a slightly narrower wrist neck, 4 SEPARATE fingers (different lengths, real 0.07 gaps with a dark crease
    core behind, slight fan) each with a proximal knuckle bump and a curled tip segment, and a two-segment thumb
    wrapped over the +Z side. Skin AO darkens every gap so the fingers read individually in an ECU."""
    sk = skin_mat(skin)
    crease = mat(f"tw_skin_crease_{skin}", tuple(c * 0.45 for c in hexc(skin)), 0.7)
    # palm runs 0.3 INTO the forearm (bevels overlap -> one continuous limb, the wrist reads as a soft swell, not a gap)
    box(name + "_palm", (1.12, 1.04, 1.06), (x0 - 0.26, 0.02, 0), sk, 0.24, parent=root, coll=coll)
    box(name + "_crs", (0.5, 0.7, 0.98), (x0 - 0.98, 0.18, 0), crease, 0.1, parent=root, coll=coll)  # shadow core between fingers
    lens_ = (0.40, 0.46, 0.44, 0.36)            # index..pinky: middle finger longest
    for k in range(4):
        z = -0.375 + k * 0.25
        fl = lens_[k]
        sphere(f"{name}_kn{k}", 0.13, (x0 - 0.76, -0.4, z), sk, seg=16, parent=root, coll=coll)
        box(f"{name}_fg{k}", (fl, 0.62, 0.18), (x0 - 0.8 - fl / 2, -0.12, z), sk, 0.08, rot=(0, 0, 0), parent=root, coll=coll)
        box(f"{name}_ft{k}", (0.24, 0.5, 0.18), (x0 - 0.86 - fl + 0.12, 0.32, z), sk, 0.08, rot=(0, 0, -25), parent=root, coll=coll)
    box(name + "_th", (0.5, 0.34, 0.3), (x0 - 0.46, -0.2, 0.64), sk, 0.12, rot=(0, -18, 0), parent=root, coll=coll)
    box(name + "_tt", (0.34, 0.3, 0.27), (x0 - 0.82, -0.3, 0.6), sk, 0.11, rot=(0, -40, 0), parent=root, coll=coll)


def block_arm(name, root, length=3.2, skin="#e9b98f", sleeve="#f3f1ec", cuff="#6e1b26", coll=None, sleeve_x=0.0, fist=True):
    """Roblox R6 block forearm along local -X (hand end at x=-length), 1x1 cross-section, with a hoodie/jacket sleeve
    (ribbed cuff) whose root empty is returned so it can be keyed to slide (sleeve_root.location.x). Skin matches cast;
    use ARM_STYLE[role] for skin/sleeve/cuff."""
    sk = skin_mat(skin)
    box(name + "_fa", (length + 0.1, 1.0, 1.0), (-length / 2 + 0.05, 0, 0), sk, 0.18, parent=root, coll=coll)
    if fist:
        block_hand(name + "_h", root, -length, skin, coll)
    sl = empty(name + "_sleeve", (sleeve_x, 0, 0), parent=root, coll=coll)
    fab = pbr.get("fabric", tint=sleeve, tile=1.2)
    box(name + "_sl", (4.0, 1.36, 1.36), (2.0 + 0.45, 0, 0), fab, 0.22, parent=sl, coll=coll)
    # R3-3/D4 r4: knit-rib cuff = solid cuff-colour band + raised ribs of the SAME knit material running along the arm on
    # all four faces (ribbing reads from shading, not from contrasting groove lines; the tiled fabric texture at tile 0.5
    # plus dark inset slats read as diagonal red stripe artefacts once the arm is tilted 32 deg in the ECU).
    knit = knit_mat(cuff)
    box(name + "_cf", (0.6, 1.40, 1.40), (0.3, 0, 0), knit, 0.16, parent=sl, coll=coll)
    for k in range(9):   # fine knit ribs: 0.06 wide, 0.02 proud, 0.13 pitch (subtle ribbing, not a comb)
        u = -0.52 + k * 0.13
        for (y_, z_, sy, sz) in ((-0.70, u, 0.04, 0.06), (0.70, u, 0.04, 0.06), (u, -0.70, 0.06, 0.04), (u, 0.70, 0.06, 0.04)):
            box(f"{name}_rb{k}_{y_:+.2f}{z_:+.2f}", (0.56, sy, sz), (0.3, y_, z_), knit, 0.012, parent=sl, coll=coll)
    for k in range(3):  # fabric folds
        box(f"{name}_fd{k}", (0.12, 1.39, 1.39), (1.2 + k * 0.9, 0, 0), fab, 0.1, rot=(0, 0, 6 - k * 5), parent=sl, coll=coll)
    return sl


def insert_table(o=None, kind="wrist", seq=(("0", "000"),), coll=None, msgs=None, buttons=None, title="MOM",
                 skin=None, sleeve=None, cuff=None, t_slide=(0.4, 1.3), posts=None, role="host"):
    """ECU inserts v2 (Roblox block arm + shallow DOF + bokeh room behind):
    wrist  - raised R6 forearm with a wristband device (counter display) on the wrist; the jacket sleeve slides back
             over t_slide=(t0, t1) to reveal it; cams 'ecu' (counter) and 'cuff' (rack-focus start on the sleeve).
             Use insert_rack(L, t0, t1) for the sleeve->counter rack focus. seq: [(t, "047"), ...].
    phone  - phone held in a block hand (thumb + finger wraps), readable UI, cam 'ecu'.
    laptop - over-the-shoulder on a laptop screen with block hands on the keyboard (soft foreground), cam 'ecu'.
    map    - flat town map with a self-drawing route (unchanged)."""
    o = o or ORIGINS["insert_table"]
    coll = coll or collection("town_insert")
    ox, oy, oz = o
    _sk, _sv, _cf = ARM_STYLE.get(role, ARM_STYLE["host"])
    skin, sleeve, cuff = skin or _sk, sleeve or _sv, cuff or _cf
    from .core import world
    # r3: ambient follows the backdrop temperature (was a fixed navy 0.5 that left every unlit surface near-black navy)
    world((0.2, 0.14, 0.1) if kind != "phone" else (0.08, 0.1, 0.16), 0.9)
    if kind == "map":
        from . import townmap
        mp = townmap.town_map(origin=(ox, oy + 80, oz))
        townmap.route("it_route", mp, ["HOUSE", "MAIN ST", "PHARMACY"], 0.5, 3.0)
        return _L("insert_map", (ox, oy + 80, oz), "day", (0, 0, 0), dict(ecu=((0, -70, 75), (0, -4, 0), 26),
                                                                             top=((0, 0, 120), (0, 0.01, 0), 26)), t=3.5)
    _bokeh_backdrop("it", (ox, oy, oz + 4), coll, warm=(kind != "phone"), seed=3)
    # r5 (D4/R4-1): the shot's look rig (cine_room key 3200 W + fill from the camera side, sized for a 5-stud
    # character) lands FLAT on the camera-facing arm face and clipped the skin at 245/255 (plastic slab). Pull the
    # shot exposure down 0.6 stop for the wrist ECU and give the backdrop/rim lights +0.6 stop back, so only the
    # front-lit skin comes down into its real tone range while the backdrop, bokeh and rims keep their level.
    # (phone/laptop keep exposure 0: their emissive screens carry the insert and were not re-verified at -0.6)
    if kind == "wrist":
        from . import look as _look
        _look.exposure(-0.6)
        for _n in ("it_bgL", "it_bgL2", "it_bgL3"):
            if _n in D.objects:
                D.objects[_n].data.energy *= 1.5
    if kind == "wrist":
        # arm rises from lower right to upper left, outer wrist toward camera (-Y)
        ar = empty("it_arm", (ox + 1.6, oy, oz + 3.0), coll=coll, rot=(0, 32, 0))
        ALEN = 3.0
        sl = block_arm("it_a", ar, ALEN, skin, sleeve, cuff, coll, sleeve_x=0.0)
        # wristband v4 (D4 r3): ONE continuous dark strap ring wrapping all four faces of the 1x1 wrist (thin wall, so it
        # hugs instead of floating), raised keeper ridges at both edges, and a bezel SMALLER than the arm (dia 0.84 < 1.0)
        # so the strap visibly runs past the face above and below it. Device front stays inside the sleeve inner face.
        bx = -ALEN + 0.95
        strap = mat("tw_strap", hexc("#26303c"), 0.55, coat=0.2)
        box("it_band", (0.6, 1.08, 1.08), (bx, 0, 0), strap, 0.06, parent=ar, coll=coll)
        for e_ in (-1, 1):
            box(f"it_band_l{e_}", (0.05, 1.1, 1.1), (bx + e_ * 0.29, 0, 0), mat("tw_strap_k", hexc("#3a4656"), 0.45), 0.02,
                parent=ar, coll=coll)
        cyl("it_bezel", 0.42, 0.1, (bx, -0.585, 0), _m("#9aa7b6", 0.25, 0.9), 40, 0.035, rot=(90, 0, 0), parent=ar, coll=coll)
        cyl("it_screen", 0.355, 0.01, (bx, -0.637, 0), mat("tw_wscreen", hexc("#0c2244"), 0.85, emit=hexc("#0c2244"), estr=1.4), 40, rot=(90, 0, 0), parent=ar, coll=coll)
        wc = S.wrist_counter("it_wc", (bx, -0.645, 0), 0, [(float(t), v) for t, v in seq], coll, parent=ar, s=0.66, face=False)
        wc.rotation_euler = (0, math.radians(-32), 0)   # digits level on screen (round face makes this read clean)
        wl = light("it_wcL", "POINT", (ox + 1.6 - 2.0, oy - 1.4, oz + 4.2), 6, hexc("#9ec8ff"), 0.3, coll=coll, shadow=False)
        # R3-2 r4: every counter CHANGE flashes - screen emission spike, a cyan glow ring around the bezel and a light
        # kick on the hand (keys only exist for change times in seq, so a static 000 insert is unaffected)
        ring = cyl("it_flash", 0.5, 0.012, (bx, -0.548, 0), mat("tw_wflash", (0.0, 0.0, 0.0), 0.6, emit=hexc("#7fe0ff"), estr=0.0),
                   48, rot=(90, 0, 0), parent=ar, coll=coll)
        ring.scale = (0.01, 0.01, 1)   # hidden behind the bezel except during a flash
        scr_e = next(n for n in D.materials["tw_wscreen"].node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Emission Strength"]
        rng_e = next(n for n in D.materials["tw_wflash"].node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Emission Strength"]
        for t_, _v in list(seq)[1:]:
            f0 = F(float(t_))
            for f, se, re, le in ((f0 - 1, 1.4, 0.0, 6), (f0, 6.0, 14.0, 60), (f0 + 4, 2.6, 4.0, 22), (f0 + 12, 1.4, 0.0, 6)):
                scr_e.default_value = se; scr_e.keyframe_insert("default_value", frame=f)
                rng_e.default_value = re; rng_e.keyframe_insert("default_value", frame=f)
                wl.data.energy = le; wl.data.keyframe_insert("energy", frame=f)
            for f, k_ in ((f0 - 1, 0.01), (f0, 1.0), (f0 + 10, 1.3), (f0 + 11, 0.01)):
                ring.scale = (k_, k_, 1); ring.keyframe_insert("scale", frame=f)
        scr_e.default_value = 1.4; rng_e.default_value = 0.0; wl.data.energy = 6; ring.scale = (0.01, 0.01, 1)
        # sleeve starts covering the band (pushed to the hand), slides back to the elbow
        t0, t1 = t_slide
        sl.location.x = bx - 0.85   # sleeve mouth well past the bezel: no digit glint through the opening
        sl.keyframe_insert("location", index=0, frame=F(t0))
        sl.location.x = bx + 0.40     # r4 (D4): stops 0.1 past the band edge so the knit cuff is IN the ecu frame
        sl.keyframe_insert("location", index=0, frame=F(t1))
        try:
            from .core import fcurves
            for fc in fcurves(sl.animation_data.action):
                for kp in fc.keyframe_points:
                    kp.interpolation = "BEZIER"; kp.easing = "EASE_IN_OUT"
        except Exception:
            pass
        light("it_key", "AREA", (ox - 4.5, oy - 3.5, oz + 7.5), 95, hexc("#ffe2c0"), 2.2, target=(ox, oy, oz + 4), coll=coll)
        light("it_rim", "AREA", (ox + 3, oy + 3, oz + 6.5), 330, hexc("#ffb867"), 2.5, target=(ox, oy, oz + 4), coll=coll)
        # r4 (D4): lower frame was near-black - warm bounce from below/front lifts the arm underside + strap,
        # low back rim separates the arm's lower edge from the backdrop
        light("it_bounce", "AREA", (ox, oy - 2.5, oz + 0.6), 45, hexc("#ffc28a"), 4, target=(ox, oy, oz + 3.8), coll=coll, shadow=False)
        light("it_rimL", "AREA", (ox - 1, oy + 3, oz + 1.5), 240, hexc("#ffd2a0"), 2, target=(ox, oy, oz + 3.6), coll=coll)
        a = math.radians(32)
        wcw = (ox + 1.6 + bx * math.cos(a), oy - 0.62, oz + 3.0 - bx * math.sin(a))
        cuffw = (ox + 1.6 + 0.4 * math.cos(a), oy - 0.65, oz + 3.0 - 0.4 * math.sin(a))
        # rim on the arm's upper edge (separates skin from the warm backdrop)
        light("it_rimT", "AREA", (ox + 0.5, oy + 2.2, oz + 6.0), 300, hexc("#ffe0b8"), 1.0, target=(ox + 0.2, oy, oz + 3.6), coll=coll)
        L = _L("insert_wrist", o, "interior", (wcw[0] - ox, wcw[1] - oy, wcw[2] - oz),
               # ecu frames watch + fist (hand/knuckles upper-left, cuff lower-right)
               dict(ecu=((wcw[0] - ox - 0.15, -5.4, wcw[2] - oz + 0.7), (wcw[0] - ox - 0.5, wcw[1] - oy, wcw[2] - oz + 0.3), 28),
                    cuff=((wcw[0] - ox + 0.9, -4.4, wcw[2] - oz + 0.5), (wcw[0] - ox + 0.15, wcw[1] - oy, wcw[2] - oz - 0.25), 26)),
               t=t1 + 0.2)
        L["fstops"] = dict(ecu=1.4, cuff=1.2)
        L["focus_pts"] = dict(ecu=wcw, cuff=cuffw)
        L["cam_t"] = dict(cuff=max(0.0, t0 - 0.2), ecu=t1 + 0.2)
        L["rack"] = (cuffw, wcw)
        return L
    if kind == "phone":
        ph = S.phone("it_ph", (ox, oy - 0.2, oz + 4.0), 0, app="messages" if not buttons else "choice", title=title,
                     msgs=msgs or [("them", "Where are you?"), ("them", "Don't come home.\nThey know your\nreal number.")],
                     buttons=buttons or (), coll=coll, s=1.0)
        ph.rotation_euler = (math.radians(-8), 0, math.radians(4))
        sk = skin_mat(skin)   # r5 (D4): shaded insert skin everywhere (was flat plastic)
        # block hand behind/below the phone, arm going down out of frame, thumb over the left edge, fingers on the right
        hr = empty("it_hand", (ox + 0.05, oy + 0.45, oz + 3.45), coll=coll, rot=(-20, 0, 6))
        box("it_hand_b", (1.0, 0.8, 1.05), (0, 0, 0), sk, 0.2, parent=hr, coll=coll)
        box("it_arm_b", (1.0, 1.0, 2.6), (0.05, 0.25, -1.7), sk, 0.15, parent=hr, coll=coll)
        sl = pbr.get("fabric", tint=sleeve, tile=1.2)
        box("it_slv", (1.22, 1.22, 2.0), (0.05, 0.3, -3.4), sl, 0.2, parent=hr, coll=coll)
        box("it_cuf", (1.3, 1.3, 0.5), (0.05, 0.3, -2.45), pbr.get("fabric", tint=cuff, tile=0.5), 0.18, parent=hr, coll=coll)
        box("it_thumb", (0.26, 0.3, 0.55), (-0.45, -0.62, 0.15), sk, 0.1, rot=(0, -20, 0), parent=hr, coll=coll)
        for k in range(3):
            box(f"it_fg{k}", (0.22, 0.34, 0.24), (0.47, -0.52, 0.25 - k * 0.27), sk, 0.08, parent=hr, coll=coll)
        light("it_scrL", "AREA", (ox, oy - 0.9, oz + 4.0), 8, hexc("#a8c4ff"), 0.8, rot=(90, 0, 0), coll=coll, shadow=False)
        light("it_key", "AREA", (ox - 3, oy - 4, oz + 6), 90, hexc("#cfdcff"), 3, target=(ox, oy, oz + 4), coll=coll)
        light("it_rim", "AREA", (ox + 2.5, oy + 2, oz + 6), 120, hexc("#7a9cff"), 2, target=(ox, oy, oz + 4), coll=coll)
        L = _L("insert_phone", o, "night", (0, -0.25, 4.0), dict(ecu=((0.15, -2.9, 4.0), (0, -0.25, 3.7), 30),
                                                                   wide=((1.0, -4.6, 4.6), (0, 0, 3.6), 40)))
        L["fstops"] = dict(ecu=2.0, wide=1.6)
        return L
    if kind == "laptop":
        box("it_tab", (16, 10, 0.4), (ox, oy + 2, oz + 2.8), pbr.get("planks", tint="#b88a5a", tile=3), 0.05, coll=coll)
        S.laptop("it_lap", (ox, oy + 0.4, oz + 3.0), 0, title="Blox Social", user="@kitchen_laptop",
                 posts=posts or ["Harry is SO gentle <3", "Harry never lies!", "Best kid in town :)"], coll=coll)
        sk = skin_mat(skin)   # r5 (D4): shaded insert skin everywhere (was flat plastic)
        for s_ in (-1, 1):
            hr = empty(f"it_lh{s_}", (ox + s_ * 0.75, oy - 0.6, oz + 3.35), coll=coll, rot=(0, 0, -s_ * 14))
            box(f"it_lhb{s_}", (0.75, 1.0, 0.45), (0, 0, 0), sk, 0.15, parent=hr, coll=coll)
            box(f"it_lha{s_}", (0.9, 2.6, 0.9), (s_ * 0.1, -1.7, 0.2), pbr.get("fabric", tint=sleeve, tile=1.2), 0.2, parent=hr, coll=coll)
        mug("it_mug", (ox + 2.2, oy - 0.2, oz + 3.35), "#19c2b0", coll)
        light("it_scrL", "AREA", (ox, oy - 0.4, oz + 4.2), 14, hexc("#a8c4ff"), 1.6, rot=(70, 0, 0), coll=coll, shadow=False)
        light("it_key", "AREA", (ox - 3, oy - 3, oz + 7), 160, hexc("#ffcf8a"), 3, target=(ox, oy, oz + 3.5), coll=coll)
        L = _L("insert_laptop", o, "interior", (0, 1.15, 3.95), dict(ecu=((0.5, -2.8, 5.0), (0, 1.0, 3.8), 22)))
        L["fstops"] = dict(ecu=2.2)
        return L
    raise ValueError(kind)


def insert_cuff_button(t0, t1, t_pinch, o=None, coll=None, role="host", helper="mom", t_click=None):
    """CLOSE INSERT on two hands at a cuff (v3.5, test_seq s04 R5 CRITICAL): the full-body two-shot of 'Mom buttons
    Harry's cuff' never read (R6 arms cannot pinch a cuff at body scale; it showed a teal block beside a sleeve, the near
    arm as a white slab at the frame edge). Cinematic references cut to the HANDS for this beat, so does the kit.
    Layout: `role`'s forearm lies across frame from the left (fist upper-left), cuff + placket + button facing the lens;
    `helper`'s block hand (own skin + sleeve colours from ARM_STYLE) enters from lower-right and its thumb + index
    fingertips PINCH the button from t_pinch to t1 (small buttoning twist about the pinch point; the button turns and
    seats on the click). Returns L with cams['ecu'], focus_pts and L['pinch'] = max pinch->button distance over the
    contact span (STRESS_FAIL when >= CUFF_TOL=0.05)."""
    from mathutils import Euler
    o = o or ORIGINS["insert_table"]
    coll = coll or collection("town_insert")
    ox, oy, oz = o
    from .core import world, fcurves
    world((0.2, 0.14, 0.1), 0.9)
    _bokeh_backdrop("it", (ox, oy, oz + 4), coll, warm=True, seed=5)
    from . import look as _look
    _look.exposure(-1.4)     # two skins in one frame: -0.6 still clipped Mom's brown hand to peach (R5 still)
    for _n in ("it_bgL", "it_bgL2", "it_bgL3"):
        if _n in D.objects:
            D.objects[_n].data.energy *= 2.0
    sk, sv, cf = ARM_STYLE.get(role, ARM_STYLE["host"])
    hsk, hsv, hcf = ARM_STYLE.get(helper, ARM_STYLE["mom"])
    ar_loc = Vector((ox + 1.5, oy, oz + 3.5))
    ar = empty("it_arm", tuple(ar_loc), coll=coll, rot=(0, 8, 0))
    sl = block_arm("it_a", ar, 3.0, sk, sv, cf, coll, sleeve_x=-1.0)
    box("it_plk", (0.30, 0.06, 0.62), (0.32, -0.725, 0.05), knit_mat(cf), 0.02, parent=sl, coll=coll)
    btn = empty("it_btn", (0.32, -0.80, 0.08), parent=sl, coll=coll, size=0.05)
    cyl("it_btn_m", 0.15, 0.08, (0, 0, 0), _m("#efe6d2", 0.3), 24, 0.02, rot=(90, 0, 0), parent=btn, coll=coll)
    for k_, dx in enumerate((-0.035, 0.035)):    # two thread holes so it reads as a BUTTON, not a dot
        cyl(f"it_btn_h{k_}", 0.022, 0.02, (dx * 1.3, -0.045, 0), _m("#6b5a48", 0.6), 10, rot=(90, 0, 0), parent=btn, coll=coll)
    bpy.context.view_layer.update()
    bw = btn.matrix_world.translation.copy()
    hsk_m = skin_mat(hsk)
    mh = empty("it_mh", (0, 0, 0), coll=coll)
    box("it_mh_palm", (0.9, 0.85, 1.0), (0, 0.08, 0), hsk_m, 0.22, parent=mh, coll=coll)
    box("it_mh_fa", (1.5, 0.92, 0.92), (1.1, 0.08, 0), hsk_m, 0.18, parent=mh, coll=coll)
    box("it_mh_sl", (3.0, 1.3, 1.3), (3.25, 0.08, 0), pbr.get("fabric", tint=hsv, tile=1.2), 0.22, parent=mh, coll=coll)
    box("it_mh_cf", (0.45, 1.36, 1.36), (1.85, 0.08, 0), knit_mat(hcf), 0.14, parent=mh, coll=coll)
    box("it_mh_th", (0.52, 0.26, 0.24), (-0.58, -0.16, 0.25), hsk_m, 0.1, rot=(0, -12, 0), parent=mh, coll=coll)
    box("it_mh_ix", (0.56, 0.24, 0.22), (-0.6, -0.16, -0.24), hsk_m, 0.1, rot=(0, 12, 0), parent=mh, coll=coll)
    for k_ in range(3):                              # remaining fingers curled into the palm
        box(f"it_mh_f{k_}", (0.34, 0.5, 0.2), (-0.5, 0.12, -0.15 - k_ * 0.2), hsk_m, 0.08, parent=mh, coll=coll)
    P = Vector((-0.80, -0.16, 0.0))
    pin = empty("it_pinch", tuple(P), parent=mh, coll=coll, size=0.05)
    tgt = bw + Vector((0, -0.01, 0))

    def put(f, ry, rz, lift=(0, 0, 0)):
        R = Euler((0, math.radians(ry), math.radians(rz)), "XYZ").to_matrix()
        mh.rotation_euler = (0, math.radians(ry), math.radians(rz))
        mh.location = tgt + Vector(lift) - R @ P
        mh.keyframe_insert("location", frame=f); mh.keyframe_insert("rotation_euler", frame=f)
    put(F(t0), 70, -14, (3.2, -1.2, -3.0))                   # off frame, lower right
    put(F(t0 + 0.25), 70, -14, (2.4, -0.9, -2.2))
    put(F(t_pinch), 68, -14)                                  # fingertips land ON the button
    f, k_ = F(t_pinch) + 6, 0
    while f < F(t1) - 3:                                      # buttoning twist about the pinch point
        put(f, 68 + (5 if k_ % 2 else -5), -14 + (3 if k_ % 2 else -3)); f += 7; k_ += 1
    put(F(t1), 68, -14)
    for fc in fcurves(mh.animation_data.action):
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"; kp.easing = "EASE_IN_OUT"
    tc = t_click or (t_pinch + 0.6 * (t1 - t_pinch))
    for tt, ang, yy in ((t_pinch, 0, -0.80), (tc - 0.1, -25, -0.80), (tc, 0, -0.76), (t1, 0, -0.76)):
        btn.rotation_euler = (0, math.radians(ang), 0); btn.location.y = yy
        btn.keyframe_insert("rotation_euler", frame=F(tt)); btn.keyframe_insert("location", frame=F(tt))
    for tt, dz in ((t0, 0.0), (t_pinch, 0.06), (t1, 0.1)):   # presenter's arm lifts a little toward the helper
        ar.location.z = ar_loc.z + dz; ar.keyframe_insert("location", index=2, frame=F(tt))
    light("it_key", "AREA", (ox - 4.5, oy - 3.5, oz + 7.5), 55, hexc("#ffe2c0"), 2.2, target=(ox, oy, oz + 4), coll=coll)
    light("it_rim", "AREA", (ox + 3, oy + 3, oz + 6.5), 330, hexc("#ffb867"), 2.5, target=(ox, oy, oz + 4), coll=coll)
    light("it_bounce", "AREA", (ox, oy - 2.5, oz + 0.6), 20, hexc("#ffc28a"), 4, target=(ox, oy, oz + 3.8), coll=coll, shadow=False)
    light("it_rimT", "AREA", (ox + 0.5, oy + 2.2, oz + 6.0), 300, hexc("#ffe0b8"), 1.0, target=(ox + 0.2, oy, oz + 3.6), coll=coll)
    sc = bpy.context.scene; f0 = sc.frame_current; ds = []
    for f in range(F(t_pinch) + 2, F(t1) + 1, 3):
        sc.frame_set(f); bpy.context.view_layer.update()
        ds.append((pin.matrix_world.translation - btn.matrix_world.translation).length)
    sc.frame_set(f0)
    pmax = max(ds) if ds else 9.0
    print(f"[cuff_insert] pinch->button max {pmax:.3f} studs" + ("  STRESS_FAIL pinch" if pmax >= CUFF_TOL else ""))
    rel = (bw.x - ox, bw.y - oy, bw.z - oz)
    L = _L("insert_cuff", o, "interior", rel,
           dict(ecu=((rel[0] - 0.7, rel[1] - 9.0, rel[2] + 2.0), (rel[0] - 0.7, rel[1], rel[2] - 0.45), 30)), t=t1)
    L["fstops"] = dict(ecu=1.4)
    L["focus_pts"] = dict(ecu=tuple(bw))
    L["pinch"] = pmax
    return L


def insert_rack(L, t0, t1, cam="cuff", t_rack=None):
    """Keyed insert camera with a rack focus from L['rack'][0] (sleeve/cuff) to L['rack'][1] (device) over [t0+.., t1]."""
    from .core import Cam
    loc, tgt, lens = L["cams"][cam]
    a, b = L["rack"]
    c = Cam("Cam_" + cam, lens)
    tr = t_rack or (t0 + 0.35 * (t1 - t0), t0 + 0.65 * (t1 - t0))
    fs = L.get("fstops", {}).get(cam, 1.4)
    c.key(t0, loc, tgt, lens, focus=a, fstop=fs)
    c.key(tr[0], loc, tgt, lens, focus=a, fstop=fs)
    c.key(tr[1], loc, tgt, lens, focus=b, fstop=fs, ease="EASE_IN_OUT")
    c.key(t1, loc, tgt, lens, focus=b, fstop=fs)
    return c


LOCATIONS = dict(main_street=main_street, pharmacy_corner=pharmacy_corner, night_street=night_street,
                 school_exterior=school_exterior, school_hallway=school_hallway, classroom=classroom, kitchen=kitchen,
                 bedroom=bedroom, front_hall=front_hall, insert_table=insert_table)


def frame(L, cam="wide", t=0.0, fstop=None):
    from .core import Cam
    loc, tgt, lens = L["cams"][cam]
    fstop = fstop or L.get("fstops", {}).get(cam)
    foc = L.get("focus_pts", {}).get(cam, tgt)
    c = Cam("Cam_" + cam, lens)
    c.key(t, loc, tgt, lens, focus=foc if fstop else None, fstop=fstop)
    return c


def insert_sleeve_pull(t0, t1, t_grip, t_done, role="host", o=None, coll=None, seq=(("0", "000"),)):
    """CLOSE INSERT, the wearer pulls his OWN sleeve down over the wrist device (v3.5b, number_lies s09/s49 user note:
    the helper-hand pinch sat far from the cuff and never connected). Built on insert_table(kind="wrist") (raised R6
    forearm + counter watch): the sleeve starts pulled back (watch visible) and slides DOWN over the watch between
    t_grip+0.1 and t_done; `role`'s other block hand (same skin / sleeve / cuff colours) enters from upper right and its
    fingertips land ON the cuff's top edge at t_grip. The hand is parented to the sleeve, so contact is held for the
    whole drag. Guard: grip->cuff-edge distance over [t_grip, t1] < CUFF_TOL=0.05 (STRESS_FAIL otherwise). Returns L from
    insert_table plus L['grip'] (max distance) and L['grip_obj'] / L['sleeve']."""
    from mathutils import Euler
    from .core import fcurves
    sk, sv, cf = ARM_STYLE.get(role, ARM_STYLE["host"])
    # insert_table keys the sleeve COVERED at t_slide[0] and REVEALED at t_slide[1]: swap = slide down over the watch
    L = insert_table(o=o, kind="wrist", seq=seq, coll=coll, skin=sk, sleeve=sv, cuff=cf,
                     t_slide=(t_done, t_grip + 0.1), role=role)
    coll = coll or collection("town_insert")
    sl = D.objects["it_a_sleeve"]
    for fc in fcurves(sl.animation_data.action):
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"; kp.easing = "EASE_IN_OUT"
    edge = empty("it_cuffedge", (0.30, -0.70, 0.32), parent=sl, coll=coll, size=0.05)   # front face of the cuff
    hsk = skin_mat(sk)
    # the hand is built IN the sleeve's frame: palm flat on top of the cuff, three fingers hooked down over the cuff's
    # FRONT face (toward the lens) = visible contact; forearm rises to upper right (elbow side), own sleeve on it.
    gh = empty("it_gh", (0, 0, 0), parent=sl, coll=coll)
    box("it_gh_palm", (0.95, 0.95, 0.5), (0.30, -0.22, 0.97), hsk, 0.18, parent=gh, coll=coll)
    for k_, x_ in enumerate((0.04, 0.30, 0.56)):
        box(f"it_gh_f{k_}", (0.23, 0.24, 0.62), (x_, -0.83, 0.62), hsk, 0.09, parent=gh, coll=coll)
        box(f"it_gh_k{k_}", (0.23, 0.42, 0.24), (x_, -0.66, 0.98), hsk, 0.09, parent=gh, coll=coll)   # knuckle bridge
    box("it_gh_th", (0.5, 0.26, 0.26), (0.05, 0.45, 0.78), hsk, 0.1, parent=gh, coll=coll)
    fa = empty("it_gh_fa_r", (0.75, -0.2, 1.05), parent=gh, coll=coll, rot=(0, -38, 0))
    box("it_gh_fa", (1.6, 0.92, 0.92), (0.8, 0, 0.0), hsk, 0.18, parent=fa, coll=coll)
    box("it_gh_cf", (0.45, 1.3, 1.3), (1.75, 0, 0), knit_mat(cf), 0.14, parent=fa, coll=coll)
    box("it_gh_sl", (3.0, 1.26, 1.26), (3.4, 0, 0), pbr.get("fabric", tint=sv, tile=1.2), 0.22, parent=fa, coll=coll)
    pin = empty("it_grip", (0.30, -0.83, 0.33), parent=gh, coll=coll, size=0.05)   # middle fingertip
    for f, off in ((F(t0), (2.4, -0.6, 2.8)), (F(max(t0 + 0.15, t_grip - 0.25)), (0.5, -0.15, 0.6)), (F(t_grip), (0, 0, 0)),
                   (F(t1), (0, 0, 0))):
        gh.location = off; gh.keyframe_insert("location", frame=f)
    for fc in fcurves(gh.animation_data.action):
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"; kp.easing = "EASE_IN_OUT"
    sc = bpy.context.scene; f0 = sc.frame_current; ds = []
    for f in range(F(t_grip), F(t1) + 1, 3):
        sc.frame_set(f); bpy.context.view_layer.update()
        ds.append((pin.matrix_world.translation - edge.matrix_world.translation).length)
    sc.frame_set(f0)
    gmax = max(ds) if ds else 9.0
    print(f"[sleeve_pull] grip->cuff max {gmax:.3f} studs" + ("  STRESS_FAIL grip" if gmax >= CUFF_TOL else ""))
    L["grip"] = gmax; L["grip_obj"] = pin; L["sleeve"] = sl
    return L
