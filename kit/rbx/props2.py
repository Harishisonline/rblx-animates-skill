"""Polished props (v2). Every prop is built from chunky BEVELLED shapes, 2-3 colours, a clear silhouette and a
little secondary motion, and follows the SCALE POLICY below. v1 props (grey cube 'metal box', one-sphere pigeon,
2.2x-scale mosquito) were the main reason frames looked amateur.

SCALE POLICY (character is ~5.7 units tall, head 1.24 wide, hand ~0.6):
    mosquito / fly / key / coin / switch  -> in WIDE and MEDIUM shots no longer than a hand (<= 0.7 units incl. proboscis);
                                              use cams.insert() with a big 'macro' copy (macro=True) for close-ups.
    pigeon / cat / robot dog              -> 1.0-1.6 units long
    drone                                 -> 1.6-2.4 units across
    robot enforcer                        -> character scale (1.0-1.25x a person) so it reads as a threat

    from rbx import props2 as P
    mq = P.mosquito("mq", (0, 0, 5))                    # hand-sized
    big = P.mosquito("mq_macro", (0, 0, 5), macro=True)  # for an insert shot only
"""
import math, random
from mathutils import Vector
from .core import (D, F, box, cyl, sphere, empty, mat, hexc, noise, text, plane, light, set_interp, instance)
from . import chars

HEAD = 1.24
HAND = 0.6


def _m(name, hexcolor, rough=0.4, metal=0.0, **kw):
    return mat(name, hexc(hexcolor), rough, metal, **kw)


def _glow(name, hexcolor, strength=6.0):
    return mat(name, hexc(hexcolor), 0.3, emit=hexc(hexcolor), estr=strength)


# ------------------------------------------------------------------ insects
def mosquito(name, loc=(0, 0, 0), s=None, coll=None, rot=0.0, macro=False, flap=True):
    """Cartoon mosquito, faces -Y. Default size is HAND-sized in the world; macro=True is a large insert copy."""
    s = (1.4 if macro else 0.2) if s is None else s
    Mb = _m("mq2_body", "#23232b", 0.45)
    Ms = _m("mq2_stripe", "#e9e9ef", 0.5)
    Me = _glow("mq2_eye", "#ff3a2e", 3.0)
    Mw = mat("mq2_wing", (0.85, 0.92, 1.0), 0.1, alpha=0.4)
    Mp = _m("mq2_prob", "#caccd6", 0.3, 0.5)
    root = empty(name, loc, None, coll, (0, 0, rot), 0.4)
    root.scale = (s, s, s)
    sphere(name + "_th", 0.46, (0, 0, 0), Mb, scale=(0.9, 1.1, 0.95), parent=root, coll=coll, seg=14)
    sphere(name + "_ab", 0.36, (0, 1.0, -0.12), Mb, scale=(0.85, 1.9, 0.85), parent=root, coll=coll, seg=14)
    for k in range(3):
        sphere(name + f"_st{k}", 0.37, (0, 0.55 + k * 0.45, -0.12), Ms, scale=(0.9, 0.12, 0.9), parent=root, coll=coll, seg=10)
    sphere(name + "_hd", 0.3, (0, -0.66, 0.04), Mb, parent=root, coll=coll, seg=14)
    cyl(name + "_pr", 0.04, 1.6, (0, -1.55, -0.1), Mp, 8, rot=(90, 0, 0), parent=root, coll=coll, r2=0.008)
    for sx in (-1, 1):
        sphere(name + f"_ey{sx}", 0.14, (sx * 0.2, -0.84, 0.16), Me, parent=root, coll=coll, seg=8)
        cyl(name + f"_an{sx}", 0.012, 0.6, (sx * 0.12, -0.95, 0.38), Mb, 6, rot=(-35, sx * 25, 0), parent=root, coll=coll)
        piv = empty(name + f"_wp{sx}", (sx * 0.28, 0.0, 0.42), root, coll, (0, 0, sx * 14), 0.2)
        box(name + f"_w{sx}", (1.5, 0.62, 0.02), (sx * 0.75, 0.05, 0), Mw, 0.0, parent=piv, coll=coll)
        if flap:
            noise(piv, "rotation_euler", 1, 0.9, 1.1)
        for k in range(3):
            ang = (-40 + k * 40)
            cyl(name + f"_lg{sx}{k}", 0.018, 1.3, (sx * 0.5, -0.25 + k * 0.45, -0.5), Mb, 6, rot=(0, sx * 50, ang * 0.2),
                parent=root, coll=coll)
    return root


def swarm_cloud(name, t0, t1, n, center, radius, target=None, s=0.2, seed=0, jitter=0.5, parent=None):
    """n hand-sized mosquitoes milling around center (or flying toward target). Many SMALL ones read as a cloud;
    a few big ones read as monsters. Keep s <= 0.3 in wide shots."""
    src = D.collections.new(name + "_SRC")
    mosquito(name + "_src", (0, 0, 0), 1.0, coll=src)
    rnd = random.Random(seed)
    out = []
    tg = Vector(target) if target is not None else None
    for i in range(n):
        d = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-0.7, 1)))
        p0 = Vector(center) + d * radius
        p1 = (tg + Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))) * 1.2) if tg is not None else p0
        v = p1 - p0
        yaw = math.degrees(math.atan2(v.x, -v.y)) if v.length > 0.01 else rnd.uniform(-180, 180)
        ob = instance(f"{name}_i{i}", src, tuple(p0), (s,) * 3, rot=(0, 0, yaw + rnd.uniform(-20, 20)))
        if parent is not None:
            ob.parent = parent
        ob.keyframe_insert("location", frame=F(t0))
        ob.location = tuple(p1)
        ob.keyframe_insert("location", frame=F(t1))
        set_interp(ob, "location", F(t0), "LINEAR")
        for ax in range(3):
            noise(ob, "location", ax, jitter, 4)
        out.append(ob)
    return out


# ------------------------------------------------------------------ animals
def pigeon(name, loc=(0, 0, 0), rot=0.0, scale=1.0, coll=None, walk=True):
    """Chunky pigeon: two-tone grey, dark wing patches, iridescent neck, tail, legs, orange beak, eyes with highlight.
    Origin on the ground (feet at z=0). Faces -Y."""
    root = empty(name, loc, None, coll, (0, 0, rot), 0.4)
    root.scale = (scale,) * 3
    Mg = _m("pg2_grey", "#8f95a3", 0.7)
    Md = _m("pg2_dark", "#555a68", 0.7)
    Mn = _m("pg2_neck", "#4f9a8e", 0.4, coat=0.4)
    Mbk = _m("pg2_beak", "#e8a33a", 0.5)
    Mw = _m("pg2_white", "#f4f4f6", 0.5)
    Mb = _m("pg2_black", "#15151a", 0.2)
    Mleg = _m("pg2_leg", "#d66a6a", 0.6)
    body = sphere(name + "_body", 0.5, (0, 0.05, 0.78), Mg, scale=(0.82, 1.2, 0.85), parent=root, coll=coll, seg=18)
    sphere(name + "_breast", 0.36, (0, -0.32, 0.86), Mg, scale=(0.9, 0.85, 0.95), parent=root, coll=coll, seg=14)
    sphere(name + "_neck", 0.27, (0, -0.52, 1.14), Mn, scale=(0.95, 0.9, 1.0), parent=root, coll=coll, seg=14)
    sphere(name + "_head", 0.25, (0, -0.64, 1.32), Mg, parent=root, coll=coll, seg=14)
    cyl(name + "_beak", 0.07, 0.3, (0, -0.9, 1.28), Mbk, 10, rot=(90, 0, 0), parent=root, coll=coll, r2=0.015)
    for sx in (-1, 1):
        sphere(name + f"_eye{sx}", 0.065, (sx * 0.17, -0.8, 1.38), Mw, parent=root, coll=coll, seg=8)
        sphere(name + f"_pup{sx}", 0.035, (sx * 0.19, -0.84, 1.38), Mb, parent=root, coll=coll, seg=8)
        w = box(name + f"_wing{sx}", (0.18, 0.95, 0.55), (sx * 0.42, 0.12, 0.88), Md, 0.08, rot=(8, sx * 8, sx * -4),
                parent=root, coll=coll)
        for k in range(3):
            cyl(name + f"_leg{sx}{k}", 0.025, 0.55, (sx * 0.16, -0.12 - k * 0.0, 0.3), Mleg, 6, parent=root, coll=coll)
            break
        box(name + f"_foot{sx}", (0.22, 0.34, 0.05), (sx * 0.16, -0.2, 0.03), Mleg, 0.02, parent=root, coll=coll)
    box(name + "_tail", (0.5, 0.7, 0.07), (0, 0.78, 0.7), Md, 0.03, rot=(-14, 0, 0), parent=root, coll=coll)
    if walk:
        noise(root, "location", 2, 0.05, 3)
        noise(root, "rotation_euler", 0, 0.05, 5)
    return root


def helmet(ch_or_root, color="#d9453a", scale=1.0, on_head=None):
    """Tiny safety helmet that sits on a pigeon/robot/character head. Pass the head object in on_head."""
    M = _m("helm2_" + color[1:], color, 0.3, coat=0.4)
    par = on_head or ch_or_root
    h = sphere(par.name + "_helm", 0.3 * scale, (0, 0, 0.1 * scale), M, scale=(1, 1, 0.8), parent=par, seg=14)
    box(par.name + "_helmbrim", (0.5 * scale, 0.2 * scale, 0.04 * scale), (0, -0.2 * scale, 0.02 * scale), M, 0.01, parent=par)
    return h


# ------------------------------------------------------------------ furniture / shelter
def steel_locker(name, loc=(0, 0, 0), rot=0.0, door_open=True, coll=None, color="#6f7a8a"):
    """Walk-in steel 'safe pod': louvred door, riveted edges, hazard stripe, handle, little window. ~3 wide, 6.5 tall."""
    root = empty(name, loc, None, coll, (0, 0, rot), 0.5)
    Ms = _m("lk_steel", color, 0.35, 0.7)
    Md = _m("lk_dark", "#2b313c", 0.5, 0.5)
    Mh = _m("lk_hazard", "#f2c14e", 0.5)
    Mk = _m("lk_black", "#15161a", 0.5)
    Mr = _m("lk_rivet", "#c9d0da", 0.25, 0.9)
    box(name + "_back", (3.2, 0.3, 6.5), (0, 1.5, 3.25), Ms, 0.09, parent=root, coll=coll)
    box(name + "_l", (0.3, 3.3, 6.5), (-1.55, 0, 3.25), Ms, 0.09, parent=root, coll=coll)
    box(name + "_r", (0.3, 3.3, 6.5), (1.55, 0, 3.25), Ms, 0.09, parent=root, coll=coll)
    box(name + "_top", (3.4, 3.4, 0.3), (0, 0, 6.6), Md, 0.09, parent=root, coll=coll)
    box(name + "_floor", (3.2, 3.2, 0.35), (0, 0, 0.17), Md, 0.06, parent=root, coll=coll)
    for k in range(6):
        box(name + f"_vent{k}", (1.0, 0.06, 0.1), (0, 1.33, 4.6 + k * 0.28), Mk, 0.02, parent=root, coll=coll)
    for k in range(7):
        box(name + f"_stripe{k}", (0.5, 0.05, 0.28), (-1.35 + k * 0.45, -1.62, 0.5), Mh if k % 2 == 0 else Mk, 0.0,
            rot=(0, 0, 0), parent=root, coll=coll)
    for k in range(6):
        for sx in (-1, 1):
            sphere(name + f"_riv{k}{sx}", 0.07, (sx * 1.58, -1.6, 0.5 + k * 1.1), Mr, parent=root, coll=coll, seg=6)
    piv = empty(name + "_hinge", (-1.55, -1.65, 0), root, coll, (0, 0, 118 if door_open else 0), 0.3)
    box(name + "_door", (3.1, 0.22, 6.2), (1.55, 0, 3.2), Ms, 0.08, parent=piv, coll=coll)
    box(name + "_win", (1.1, 0.12, 0.5), (1.55, -0.12, 5.3), Mk, 0.04, parent=piv, coll=coll)
    box(name + "_hdl", (0.12, 0.2, 0.9), (2.6, -0.22, 3.2), Mh, 0.04, parent=piv, coll=coll)
    return root


def wood_crate(name, loc=(0, 0, 0), size=1.6, rot=0.0, coll=None):
    root = empty(name, loc, None, coll, (0, 0, rot), 0.4)
    Mw = _m("cr_wood", "#b98852", 0.8)
    Md = _m("cr_dark", "#7a5230", 0.8)
    s = size
    box(name + "_b", (s, s, s), (0, 0, s / 2), Mw, 0.05, parent=root, coll=coll)
    for k in range(4):
        a = k * 90
        for sgn in (-1, 1):
            box(name + f"_t{k}{sgn}", (s * 1.02, 0.08 * s, 0.14 * s), (0, 0, s / 2), Md, 0.02, rot=(0, 0, a),
                parent=root, coll=coll).location = (0, 0, s / 2)
    return root


# ------------------------------------------------------------------ AI / sci-fi set dressing
def robot(t0, t1, expr="neutral", name="Bot", body="#c4ccd8", accent="#2a3040", eye="#26d9ff", scale=1.1):
    """Humanoid robot built on the standard rig (so it can walk, act, pose, face, look_at like any character).
    Visor with glowing eyes, antenna, shoulder pads, chest light. scale 1.1 = slightly imposing."""
    from . import story
    ch = chars.Char(name, skin=body, shirt=accent, pants=accent, hair="bald", face="plain", sleeves="long", scale=scale)
    Mv = _m(name + "_visor", "#0b0d12", 0.15, 0.3)
    Me = _glow(name + "_eye", eye, 9.0)
    Ma = _m(name + "_acc", accent, 0.35, 0.6)
    Mb = _m(name + "_body", body, 0.3, 0.7)
    box(name + "_vis", (1.14, 0.14, 0.52), (0, -0.66, 0.04), Mv, 0.05, parent=ch.head, coll=ch.coll)
    for sx in (-1, 1):
        box(name + f"_ey{sx}", (0.3, 0.05, 0.14), (sx * 0.26, -0.75, 0.04), Me, 0.02, parent=ch.head, coll=ch.coll)
    cyl(name + "_ant", 0.035, 0.55, (0.28, 0.05, 0.9), Ma, 8, parent=ch.head, coll=ch.coll)
    sphere(name + "_antb", 0.09, (0.28, 0.05, 1.2), Me, parent=ch.head, coll=ch.coll, seg=8)
    for nm in ("armL", "armR"):
        try:
            box(name + "_pad" + nm, (0.85, 0.85, 0.28), (0, 0, 0.12), Ma, 0.08, parent=ch.piv(nm), coll=ch.coll)
        except Exception:
            pass
    box(name + "_chest", (0.72, 0.07, 0.72), (0, -0.58, 1.3), Mv, 0.05, parent=ch.hip, coll=ch.coll)
    sphere(name + "_core", 0.17, (0, -0.64, 1.3), Me, parent=ch.hip, coll=ch.coll, seg=10)
    ch.face(t0, "neutral")
    ch.blink(t0, t1) if hasattr(ch, "blink") else None
    ch.breathe(0.5)
    return ch


def drone(name, loc, t0, t1, s=1.0, eye="#ff2a2a", hover=0.18, coll=None, rot=0.0):
    """Surveillance quadcopter: rounded hull, 4 arms with spinning rotors, red camera eye, under-light. Faces -Y."""
    root = empty(name, loc, None, coll, (0, 0, rot), 0.5)
    root.scale = (s,) * 3
    Mh = _m("dr_hull", "#2d3340", 0.3, 0.6)
    Mw = _m("dr_white", "#dfe4ec", 0.4, 0.3)
    Mr = _m("dr_rotor", "#9aa3b2", 0.3, 0.6)
    Me = _glow("dr_eye", eye, 12.0)
    sphere(name + "_hull", 0.62, (0, 0, 0), Mh, scale=(1, 1.15, 0.6), parent=root, coll=coll, seg=18)
    sphere(name + "_cap", 0.4, (0, 0.05, 0.22), Mw, scale=(1, 1, 0.55), parent=root, coll=coll, seg=14)
    sphere(name + "_lens", 0.2, (0, -0.62, -0.02), Me, parent=root, coll=coll, seg=12)
    cyl(name + "_ring", 0.26, 0.07, (0, -0.58, -0.02), Mh, 20, rot=(90, 0, 0), parent=root, coll=coll)
    for i, (ax, ay) in enumerate(((1, 1), (-1, 1), (1, -1), (-1, -1))):
        arm = box(name + f"_arm{i}", (1.25, 0.14, 0.1), (ax * 0.78, ay * 0.6, 0.05), Mh, 0.04,
                  rot=(0, 0, math.degrees(math.atan2(ay * 0.6, ax * 0.78))), parent=root, coll=coll)
        piv = empty(name + f"_rp{i}", (ax * 1.4, ay * 1.05, 0.2), root, coll, (0, 0, 0), 0.2)
        cyl(name + f"_mot{i}", 0.13, 0.22, (0, 0, 0), Mh, 12, parent=piv, coll=coll)
        for b in range(2):
            box(name + f"_bl{i}{b}", (1.1, 0.12, 0.025), (0, 0, 0.14), Mr, 0.0, rot=(0, 0, b * 90), parent=piv, coll=coll)
        piv.rotation_euler = (0, 0, 0)
        piv.keyframe_insert("rotation_euler", index=2, frame=F(t0))
        piv.rotation_euler = (0, 0, math.radians(360 * 40 * (t1 - t0)))
        piv.keyframe_insert("rotation_euler", index=2, frame=F(t1))
        set_interp(piv, "rotation_euler", F(t0), "LINEAR")
    noise(root, "location", 2, hover, 6)
    noise(root, "rotation_euler", 0, 0.05, 8)
    noise(root, "rotation_euler", 1, 0.05, 9)
    return root


def server_rack(name, loc, rot=0.0, units=8, coll=None, seed=0):
    rnd = random.Random(seed)
    root = empty(name, loc, None, coll, (0, 0, rot), 0.4)
    Mc = _m("sv_case", "#1c2029", 0.4, 0.5)
    Mt = _m("sv_tray", "#2b3240", 0.4, 0.5)
    box(name + "_case", (2.2, 1.6, units * 0.7 + 0.6), (0, 0, (units * 0.7 + 0.6) / 2), Mc, 0.06, parent=root, coll=coll)
    cols = ["#37ff8b", "#26d9ff", "#ffcf2e", "#ff4b4b"]
    for u in range(units):
        z = 0.5 + u * 0.7
        box(name + f"_u{u}", (2.0, 0.12, 0.55), (0, -0.82, z), Mt, 0.03, parent=root, coll=coll)
        for k in range(8):
            c = rnd.choice(cols)
            box(name + f"_l{u}_{k}", (0.1, 0.05, 0.1), (-0.8 + k * 0.2, -0.9, z + 0.12), _glow("sv_led" + c[1:], c, 8.0), 0.0,
                parent=root, coll=coll)
    return root


def terminal(name, loc, rot=0.0, color="#37ff8b", coll=None, w=3.0, h=2.0):
    root = empty(name, loc, None, coll, (0, 0, rot), 0.4)
    Mc = _m("tm_case", "#232833", 0.4, 0.4)
    box(name + "_stand", (0.3, 0.3, 0.9), (0, 0.2, 0.45), Mc, 0.04, parent=root, coll=coll)
    box(name + "_base", (1.2, 0.8, 0.12), (0, 0.2, 0.06), Mc, 0.04, parent=root, coll=coll)
    box(name + "_mon", (w + 0.3, 0.25, h + 0.3), (0, 0.2, 0.9 + h / 2), Mc, 0.07, parent=root, coll=coll)
    scr = box(name + "_scr", (w, 0.04, h), (0, 0.04, 0.9 + h / 2), _glow("tm_scr" + color[1:], color, 3.0), 0.0, parent=root, coll=coll)
    return root


def neon_sign(name, body, loc, size=1.4, color="#ff2fb3", rot=(90, 0, 0), coll=None):
    return text(name, body, loc, size, _glow("neon_" + color[1:], color, 14.0), rot, 0.08, coll, None)


def lit_building_mat(name, base="#1a1f2e", window="#ffd27a", scale=(0.55, 0.6), density=0.3, strength=1.1):
    """Building with emissive windows: a checker grid (one window per cell) gated by a per-CELL random mask
    (white noise on the floored cell coordinate, so no grain). scale = windows per world unit (x, z)."""
    import bpy
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*hexc(base), 1)
    b.inputs["Roughness"].default_value = 0.45
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (scale[0], scale[0], scale[1])
    fl = nt.nodes.new("ShaderNodeVectorMath")
    fl.operation = "FLOOR"
    wn = nt.nodes.new("ShaderNodeTexWhiteNoise")
    wn.noise_dimensions = "3D"
    gt = nt.nodes.new("ShaderNodeMath")
    gt.operation = "GREATER_THAN"
    gt.inputs[1].default_value = 1 - density
    ck = nt.nodes.new("ShaderNodeTexChecker")
    ck.inputs["Scale"].default_value = 1.0
    ck.inputs["Color1"].default_value = (0, 0, 0, 1)
    ck.inputs["Color2"].default_value = (*hexc(window), 1)
    mx = nt.nodes.new("ShaderNodeVectorMath")
    mx.operation = "SCALE"
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], fl.inputs[0])
    nt.links.new(fl.outputs[0], wn.inputs["Vector"])
    nt.links.new(wn.outputs["Value"], gt.inputs[0])
    nt.links.new(mp.outputs["Vector"], ck.inputs["Vector"])
    nt.links.new(ck.outputs["Color"], mx.inputs[0])
    nt.links.new(gt.outputs[0], mx.inputs["Scale"])
    nt.links.new(mx.outputs[0], b.inputs["Emission Color"])
    b.inputs["Emission Strength"].default_value = strength
    return m


def bpy_mats():
    import bpy
    return bpy.data.materials


def ai_city(extent=160, seed=3, neon=("#ff2fb3", "#26d9ff"), coll=None):
    """Futuristic night city for the AI-takeover theme: dark ground with lane strips, lit towers, glowing
    antenna tips, a few neon signs. Open street along -Y around (0, -30). Cheap enough for wide shots."""
    rnd = random.Random(seed)
    box("city_ground", (extent * 2, extent * 2, 0.4), (0, 0, -0.2), _m("city_ground_m", "#141821", 0.35, 0.2), 0, coll=coll)
    Mroad = _m("city_road", "#0c0e14", 0.3)
    for k, y in enumerate((-30, -70, -110, 20, 60, 100)):
        box(f"city_rd{k}", (extent * 2, 8, 0.05), (0, y, 0.03), Mroad, 0, coll=coll)
        for j in range(-8, 9):
            box(f"city_ln{k}_{j}", (3.2, 0.25, 0.04), (j * 18, y, 0.07), _glow("city_lane", neon[1], 3.0), 0, coll=coll)
    wins = ["#ffd9a0", "#bfe9ff", "#ffc0e6"]
    for gx in range(-6, 7):
        for gy in range(-4, 6):
            cx, cy = gx * 22, -30 + gy * 40 + 20
            if abs(cx) < 26 and -62 < cy < 44:
                continue
            h = rnd.uniform(24, 70) if abs(cx) > 40 else rnd.uniform(12, 34)
            w = rnd.uniform(10, 16)
            m = lit_building_mat(f"cb{(gx + gy) % 5}", ["#1a1f2e", "#202637", "#151a28"][(gx + gy) % 3], wins[(gx + gy * 2) % 3],
                                 density=rnd.uniform(0.3, 0.55))
            box(f"city_b{gx}_{gy}", (w, w, h), (cx, cy, h / 2), m, 0.1, coll=coll)
            if rnd.random() < 0.35:
                sphere(f"city_a{gx}_{gy}", 0.5, (cx, cy, h + 1.2), _glow("city_ant", "#ff2a2a", 8.0), coll=coll, seg=8)
                cyl(f"city_as{gx}_{gy}", 0.12, 3, (cx, cy, h + 1.5), _m("city_mast", "#3a4150", 0.4), 8, coll=coll)
    return dict(open_street=(0, -30, 0))


# ------------------------------------------------------------------ characters for the AI-takeover theme
def survivor(t0, t1, expr="determined", name="Survivor", number="0", hoodie="#1f6f7a", scarf="#ff7a2e", scale=1.0):
    """Hero designed for small mobile frames: dark teal hoodie with hood, orange scarf (strong silhouette colour),
    goggles pushed up on the forehead, backpack, a glowing wrist band showing a number (the story's 'tag')."""
    ch = chars.Char(name, skin="#c48a5c", shirt=hoodie, pants="#35384a", hair="messy", hair_color="#1b1410",
                    face="kid", sleeves="long", extras=("backpack:",), scale=scale)
    Mh = _m(name + "_hood", hoodie, 0.7)
    Ms = _m(name + "_scarf", scarf, 0.6)
    Mg = _m(name + "_gog", "#2a2f3c", 0.25, 0.6)
    Ml = _glow(name + "_lens", "#7df2ff", 3.0)
    # hood rolled behind the neck + scarf
    box(name + "_hoodb", (1.5, 0.55, 0.6), (0, 0.55, -0.62), Mh, 0.18, parent=ch.head, coll=ch.coll)
    box(name + "_scarf", (1.6, 1.0, 0.42), (0, -0.04, -0.72), Ms, 0.14, parent=ch.head, coll=ch.coll)
    box(name + "_scarft", (0.38, 0.14, 1.2), (0.35, -0.62, -1.2), Ms, 0.06, parent=ch.head, coll=ch.coll)
    # goggles on the forehead
    box(name + "_gstrap", (1.3, 1.3, 0.14), (0, 0.0, 0.45), Mg, 0.04, parent=ch.head, coll=ch.coll)
    for sx in (-1, 1):
        cyl(name + f"_gl{sx}", 0.24, 0.12, (sx * 0.3, -0.64, 0.5), Mg, 18, rot=(90, 0, 0), parent=ch.head, coll=ch.coll)
        cyl(name + f"_gg{sx}", 0.17, 0.14, (sx * 0.3, -0.69, 0.5), Ml, 18, rot=(90, 0, 0), parent=ch.head, coll=ch.coll)
    wrist_band(ch, number)
    from . import story
    ch.face(t0, expr)
    ch.blink(t0, t1)
    ch.breathe(0.8)
    return ch


def wrist_band(ch, number="0", color="#7df2ff", arm="armL"):
    """Glowing band on the forearm with a number on it (the 'tag' the AI reads)."""
    p = ch.piv(arm)
    Mb = _m("wb_band", "#15171d", 0.3, 0.5)
    box(ch.name + "_band", (1.08, 1.08, 0.42), (0, 0, -1.62), Mb, 0.07, parent=p, coll=ch.coll)
    t = text(ch.name + "_num", str(number), (0, -0.58, -1.68), 0.55, _glow("wb_num" + color[1:], color, 10.0), (90, 0, 0), 0.03,
             ch.coll, None)
    t.parent = p
    return t


def floating_number(ch, number, color="#ff2fb3", z=7.3, size=1.1):
    """Neon number hovering over a character's head (the AI's score for them)."""
    t = text(ch.name + "_tag", str(number), (0, 0, z), size, _glow("fn_" + color[1:], color, 12.0), (90, 0, 0), 0.06, ch.coll, None)
    t.parent = ch.root
    t.location = (-0.35 * len(str(number)) * size * 0.5, 0, z)
    return t


def searchlight(drone_root, target, color=(1.0, 0.25, 0.25), energy=60000, spot=28):
    """Spot light under a drone pointing at target."""
    ob = light("sl_" + drone_root.name, "SPOT", tuple(drone_root.location - Vector((0, 0, 0.3))), energy, color, 0.25, target=target, spot=spot, blend=0.25)
    ob.parent = None
    return ob


def world_pos(ob, t=None):
    """World position of an object (e.g. a posed wrist band) at time t, for aiming insert shots."""
    import bpy
    if t is not None:
        bpy.context.scene.frame_set(F(t))
    bpy.context.view_layer.update()
    return tuple(ob.matrix_world.translation)
