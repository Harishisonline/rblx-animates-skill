"""BLOX TOWN: reusable classic-Roblox-style game map for @rblxanimates (original assets only; no real Roblox logos/UI).

    from rbx import robloxworld as RW
    RW.blox_town()                      # whole map: studded baseplate, sky, hills, plaza, town hall, bakery, skatepark,
                                        # family house + backyard grill, park, giant RBLX ANIMATES hill sign, banners
    RW.arch_on(t)                       # spawn-plaza neon arch flickers on at t
    RW.kitchen() / RW.living_room()     # interiors (use look 'story_warm'); built far away at x=300 / x=360
Key places (world coords, ground z=0, cameras look +Y):
    PLAZA (0,0) spawn pad, fountain, neon arch at y=14 | HALL (0,42) town hall, ribbon spot (0,33)
    SKATE (-46,4) ramps/rails | BAKERY (44,6) cafe + outdoor tables (Luna) | HOUSE (40,44) family house, GRILL (54,40)
    PARK (-42,40) bench, pond, trees (Grandpa) | HILL (0,150) giant block letters | KITCHEN (300,0) | LIVING (360,0)
Brand: purple #8a2be2/#b46bff, neon blue #26d9ff, black."""
import math, os, random
import bpy
from mathutils import Vector
from .core import box, cyl, sphere, text, empty, light, hexc, mat, F, D, noise, poly_extrude
from . import world as W
from . import ASSETS

PLAZA, HALL, SKATE, BAKERY, HOUSE, GRILL, PARK, HILL = (0, 0, 0), (0, 42, 0), (-46, 4, 0), (44, 6, 0), (40, 44, 0), (54, 40, 0), (-42, 40, 0), (0, 150, 0)
KITCHEN, LIVING = (300, 0, 0), (360, 0, 0)
PURPLE, LILAC, NEON, BLACK = "#8a2be2", "#b46bff", "#26d9ff", "#121018"
FONT = None


def _font():
    global FONT
    if FONT is None:
        p = os.path.join(ASSETS, "fonts", "Poppins-ExtraBold.ttf")
        FONT = p if os.path.exists(p) else ""
    return FONT or None


def M(name, hx, rough=0.55, metal=0.0, **kw):
    return mat("rw_" + name, hexc(hx), rough, metal, **kw)


def G(name, hx, s=8.0):
    return mat("rw_g_" + name, hexc(hx), 0.3, emit=hexc(hx), estr=s)


def stud_mat(name, hx, scale=0.5, rough=0.6):
    """Classic studded plastic: round studs (1 per 1/scale units) via object-coordinate maths + bump + slight tint."""
    key = "rw_stud_" + name
    if key in D.materials:
        return D.materials[key]
    m = D.materials.new(key); m.use_nodes = True
    nt = m.node_tree; N, L = nt.nodes, nt.links
    b = next(n for n in N if n.type == "BSDF_PRINCIPLED")
    b.inputs["Roughness"].default_value = rough
    tc = N.new("ShaderNodeTexCoord")
    mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (scale, scale, scale)
    L.new(tc.outputs["Object"], mp.inputs[0])
    fr = N.new("ShaderNodeVectorMath"); fr.operation = "FRACTION"; L.new(mp.outputs[0], fr.inputs[0])
    sub = N.new("ShaderNodeVectorMath"); sub.operation = "SUBTRACT"; sub.inputs[1].default_value = (0.5, 0.5, 0.5)
    L.new(fr.outputs[0], sub.inputs[0])
    sep = N.new("ShaderNodeSeparateXYZ"); L.new(sub.outputs[0], sep.inputs[0])
    cmb = N.new("ShaderNodeCombineXYZ"); L.new(sep.outputs[0], cmb.inputs[0]); L.new(sep.outputs[1], cmb.inputs[1])
    ln = N.new("ShaderNodeVectorMath"); ln.operation = "LENGTH"; L.new(cmb.outputs[0], ln.inputs[0])
    mr = N.new("ShaderNodeMapRange"); mr.inputs[1].default_value = 0.30; mr.inputs[2].default_value = 0.26
    mr.inputs[3].default_value = 0.0; mr.inputs[4].default_value = 1.0
    L.new(ln.outputs["Value"], mr.inputs[0])
    bump = N.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.45; bump.inputs["Distance"].default_value = 0.05
    L.new(mr.outputs[0], bump.inputs["Height"]); L.new(bump.outputs[0], b.inputs["Normal"])
    c = hexc(hx)
    mix = N.new("ShaderNodeMix"); mix.data_type = "RGBA"
    mix.inputs[6].default_value = (*c, 1); mix.inputs[7].default_value = (*[min(1, x * 1.18) for x in c], 1)
    L.new(mr.outputs[0], mix.inputs[0]); L.new(mix.outputs[2], b.inputs["Base Color"])
    m.diffuse_color = (*c, 1)
    return m


# ------------------------------------------------------------------ sky, ground, hills
def sky_day():
    W.sky(1.0, top=(0.01, 0.12, 0.7), bottom=(0.22, 0.5, 0.95))
    W.cloud_field("rw_cl", (0, 90, 55), (160, 60, 10), 22, seed=3, scale=(2.0, 4.0))


def ground():
    box("rw_base", (700, 700, 0.4), (0, 100, -0.2), stud_mat("grass", "#4caa3e", 1.0), 0)
    Mr = stud_mat("road", "#6f7480", 1.0)
    box("rw_road", (240, 9, 0.06), (0, -9, 0.03), Mr, 0)                     # main street (x)
    box("rw_road2", (9, 120, 0.06), (0, 30, 0.03), Mr, 0)                     # avenue to the hall + hill
    for k in range(-24, 25):
        box(f"rw_lane{k}", (2.2, 0.25, 0.02), (k * 5.0, -9, 0.07), M("lane", "#f4f4f2", 0.5), 0)
    box("rw_plaza", (26, 22, 0.08), (0, 2, 0.04), stud_mat("plaza", "#b9b2a4", 1.0), 0)
    for sx in (-1, 1):
        box(f"rw_walk{sx}", (240, 3.0, 0.2), (0, -9 + sx * 6.0, 0.1), stud_mat("walk", "#aaa598", 1.0), 0.03)


def hills():
    rnd = random.Random(2)
    Mh = stud_mat("hill", "#4fa846", 0.35)
    for k in range(14):
        a = math.radians(-80 + k * 160 / 13)
        r = rnd.uniform(150, 210)
        x, y = math.sin(a) * r, 60 + math.cos(a) * r * 0.9
        sphere(f"rw_hill{k}", rnd.uniform(35, 60), (x, y, -18), Mh, (1.6, 1.0, 0.65), seg=24)
    sphere("rw_bighill", 55, (HILL[0], HILL[1] + 10, -30), Mh, (1.8, 0.9, 0.62), seg=32)


# ------------------------------------------------------------------ small props
def tree(name, loc, s=1.0, seed=0):
    rnd = random.Random(seed)
    x, y, z = loc
    box(name + "_t", (0.9 * s, 0.9 * s, 4.5 * s), (x, y, z + 2.25 * s), M("trunk", "#7a4f2e", 0.8), 0.08)
    for i in range(3):
        c = ("#3f9a3a", "#4fb045", "#66c24f")[i]
        sz = (3.6 - i * 0.9) * s
        box(f"{name}_l{i}", (sz, sz, sz * 0.75), (x + rnd.uniform(-0.3, 0.3), y + rnd.uniform(-0.3, 0.3), z + (4.4 + i * 1.5) * s),
            stud_mat("leaf" + str(i), c, 1.0), 0.25 * s, rot=(0, 0, rnd.uniform(0, 40)))


def bush(name, loc, s=1.0):
    sphere(name, 1.0 * s, (loc[0], loc[1], loc[2] + 0.6 * s), stud_mat("bush", "#3f9a3a", 1.0), (1.3, 1.0, 0.8), seg=12)
    for k in range(4):
        a = k * 1.6
        sphere(f"{name}_f{k}", 0.16 * s, (loc[0] + math.cos(a) * 0.9 * s, loc[1] + math.sin(a) * 0.7 * s - 0.2, loc[2] + 1.0 * s),
               M("flower" + str(k % 3), ("#ff4bd8", "#ffd23a", "#ffffff")[k % 3], 0.5), seg=8)


def flowers(name, loc, n=10, seed=1):
    rnd = random.Random(seed)
    for k in range(n):
        x, y = loc[0] + rnd.uniform(-2, 2), loc[1] + rnd.uniform(-1, 1)
        cyl(f"{name}_s{k}", 0.05, 0.6, (x, y, 0.3), M("stem", "#2f7a2a"), 6)
        sphere(f"{name}_h{k}", 0.2, (x, y, 0.65), M("petal" + str(k % 4), ("#ff4bd8", "#ffd23a", "#b46bff", "#ff6a3a")[k % 4], 0.5), seg=8)


def lamp_post(name, loc, banner=True, rot=0):
    x, y, z = loc
    Mb = M("lamp", "#2a2833", 0.35, 0.6)
    cyl(name + "_p", 0.22, 9, (x, y, 4.5), Mb, 12)
    box(name + "_arm", (1.8, 0.2, 0.2), (x + 0.8, y, 9.0), Mb, 0.04)
    sphere(name + "_bulb", 0.45, (x + 1.6, y, 8.6), G("bulb", "#fff1c9", 6.0), seg=12)
    if banner:   # RBLX ANIMATES banner (purple with neon text) hanging from the post
        bn = box(name + "_bn", (0.08, 1.6, 3.0), (x - 0.35, y, 6.3), M("banner", PURPLE, 0.6), 0.03)
        t = text(name + "_bt", "RBLX", (x - 0.42, y, 6.9), 0.48, G("bt", NEON, 5.0), (90, 0, -90), 0.02, None, _font())
        t2 = text(name + "_bt2", "ANIMATES", (x - 0.42, y, 6.2), 0.26, G("bt2", "#ffffff", 3.0), (90, 0, -90), 0.02, None, _font())
        noise(bn, "rotation_euler", 1, 0.03, 18)


def fence(name, p0, p1, color="#ffffff"):
    p0, p1 = Vector(p0), Vector(p1)
    n = int((p1 - p0).length / 1.6)
    Mf = M("fence" + color[1:], color, 0.6)
    for k in range(n + 1):
        p = p0 + (p1 - p0) * (k / max(1, n))
        box(f"{name}_p{k}", (0.3, 0.3, 1.6), (p.x, p.y, 0.8), Mf, 0.04)
    mid = (p0 + p1) / 2; d = p1 - p0
    for z in (0.6, 1.2):
        box(f"{name}_r{z}", (d.length, 0.15, 0.2), (mid.x, mid.y, z), Mf, 0.03, rot=(0, 0, math.degrees(math.atan2(d.y, d.x))))


def bench(name, loc, rot=0):
    root = empty(name, loc, None, None, (0, 0, rot))
    Mw, Mm = M("benchw", "#a8693c", 0.6), M("benchm", "#2a2833", 0.4, 0.5)
    box(name + "_s", (4.0, 1.2, 0.2), (0, 0, 1.2), Mw, 0.05, parent=root)
    box(name + "_b", (4.0, 0.2, 1.0), (0, 0.6, 1.9), Mw, 0.05, parent=root)
    for sx in (-1, 1):
        box(f"{name}_l{sx}", (0.2, 1.2, 1.2), (sx * 1.7, 0, 0.6), Mm, 0.03, parent=root)
    return root


def mailbox(name, loc, color="#d9453a"):
    cyl(name + "_p", 0.12, 1.6, (loc[0], loc[1], 0.8), M("mbp", "#3a3a3a"), 8)
    box(name + "_b", (0.6, 1.1, 0.6), (loc[0], loc[1], 1.85), M("mb" + color[1:], color, 0.4), 0.2)


def crate(name, loc, s=1.2, rot=0):
    box(name, (s, s, s), (loc[0], loc[1], s / 2), M("crate", "#b07a46", 0.7), 0.06, rot=(0, 0, rot))


def fountain(name, loc, t0=0.0, t1=10.0):
    x, y, z = loc
    Ms = stud_mat("stone", "#c9c4b8", 0.8)
    cyl(name + "_b", 3.6, 1.0, (x, y, 0.5), Ms, 32, bev=0.1)
    cyl(name + "_w", 3.2, 0.1, (x, y, 1.0), M("water", "#5fc8ff", 0.05, spec=0.9), 32)
    cyl(name + "_c", 0.5, 2.6, (x, y, 2.3), Ms, 16)
    cyl(name + "_t", 1.4, 0.4, (x, y, 3.6), Ms, 24, bev=0.08)
    jet = cyl(name + "_j", 0.25, 1.4, (x, y, 4.4), M("jet", "#bfeaff", 0.05, emit=hexc("#bfeaff"), estr=0.6, alpha=0.6), 12)
    noise(jet, "scale", 2, 0.12, 6)


def spawn_pad(name, loc):
    x, y, z = loc
    box(name, (6, 6, 0.4), (x, y, 0.2), M("spawn", "#3a3a46", 0.4), 0.1)
    box(name + "_top", (5.2, 5.2, 0.08), (x, y, 0.44), G("spawn_top", NEON, 1.4), 0.02)
    poly = [(math.cos(a) * 1.4, math.sin(a) * 1.4) for a in [k * math.tau / 5 - math.pi / 2 for k in range(5)]]
    st = [(math.cos(k * math.pi / 5 - math.pi / 2) * (1.6 if k % 2 == 0 else 0.7), math.sin(k * math.pi / 5 - math.pi / 2) * (1.6 if k % 2 == 0 else 0.7)) for k in range(10)]
    poly_extrude(name + "_star", st, 0.05, (x, y, 0.48), G("spawn_star", "#ffffff", 3.0), rot=(0, 0, 0))


# ------------------------------------------------------------------ buildings
def building(name, loc, size, color, roof="#5a4a6a", windows=(3, 2), shutters="#ffffff", awning=None, sign=None,
             sign_color=PURPLE, door="#7a4f2e", rot=0):
    """Pastel blocky building: studded walls, framed windows with shutters, door, optional striped awning + sign.
    Front faces -Y (before rot)."""
    x, y, z = loc
    w, d, h = size
    root = empty(name, loc, None, None, (0, 0, rot))
    box(name + "_body", (w, d, h), (0, 0, h / 2), stud_mat("wall" + color[1:], color, 0.6), 0.1, parent=root)
    box(name + "_roof", (w + 1.0, d + 1.0, 0.8), (0, 0, h + 0.4), M("roof" + roof[1:], roof, 0.6), 0.15, parent=root)
    box(name + "_trim", (w + 0.3, d + 0.3, 0.3), (0, 0, h - 0.1), M("trim", "#ffffff", 0.5), 0.05, parent=root)
    nx, nz = windows
    Mg = M("glass", "#bfe8ff", 0.05, spec=0.9, emit=hexc("#9fd6ff"), estr=0.25)
    Msh = M("sh" + shutters[1:], shutters, 0.5)
    for i in range(nx):
        for j in range(nz):
            wx = -w / 2 + w * (i + 0.5) / nx
            wz = h * (0.45 + 0.42 * j) if nz > 1 else h * 0.6
            if j == 0 and nx >= 3 and i == nx // 2:
                continue
            box(f"{name}_wf{i}{j}", (1.9, 0.2, 2.1), (wx, -d / 2 - 0.05, wz), M("wframe", "#ffffff", 0.5), 0.04, parent=root)
            box(f"{name}_wg{i}{j}", (1.5, 0.22, 1.7), (wx, -d / 2 - 0.08, wz), Mg, 0.02, parent=root)
            for sx in (-1, 1):
                box(f"{name}_sh{i}{j}{sx}", (0.55, 0.15, 2.1), (wx + sx * 1.3, -d / 2 - 0.08, wz), Msh, 0.03, parent=root)
    box(name + "_door", (2.0, 0.25, 3.4), (0 if nx < 3 else -w / 2 + w * (nx // 2 + 0.5) / nx, -d / 2 - 0.05, 1.7),
        M("door" + door[1:], door, 0.5), 0.05, parent=root)
    if awning:
        for k in range(8):
            c = awning[k % 2]
            box(f"{name}_aw{k}", (w * 0.9 / 8, 2.2, 0.15), (-w * 0.45 + w * 0.9 / 8 * (k + 0.5), -d / 2 - 1.1, h * 0.36 + 0.45),
                M("aw" + c[1:], c, 0.6), 0.02, rot=(-18, 0, 0), parent=root)
    if sign:
        box(name + "_sb", (len(sign) * 0.75 + 1.2, 0.3, 1.5), (0, -d / 2 - 0.2, h - 1.2), M("sb" + sign_color[1:], sign_color, 0.5), 0.1,
            parent=root)
        t = text(name + "_st", sign, (0, -d / 2 - 0.4, h - 1.2), 0.95, G("st", "#ffffff", 2.5), (90, 0, 0), 0.04, None, _font())
        t.parent = root
    return root


def town_hall(t0=0.0, t1=10.0):
    x, y, _ = HALL
    building("rw_hall", (x, y + 6, 0), (26, 12, 14), "#f2ead8", "#3d4fa0", (5, 2), "#3d4fa0", sign="TOWN HALL", sign_color="#3d4fa0")
    for k in range(6):   # columns + steps + flag
        cyl(f"rw_col{k}", 0.6, 9, (x - 10 + k * 4, y - 1.5, 4.5), stud_mat("col", "#ffffff", 0.8), 16)
    box("rw_pedi", (26, 3, 1.2), (x, y - 1.5, 9.6), M("pedi", "#f2ead8", 0.5), 0.1)
    for k in range(3):
        box(f"rw_step{k}", (24 - k * 2, 2.0, 0.5), (x, y - 3.5 + k * 1.0, 0.25 + k * 0.5), stud_mat("step", "#d9d3c4", 0.6), 0.04)
    cyl("rw_clock", 2.0, 0.4, (x, y - 0.1, 16.5), M("clock", "#ffffff", 0.4), 32, rot=(90, 0, 0))
    box("rw_tower", (6, 6, 6), (x, y + 2, 16.0), stud_mat("tower", "#f2ead8", 0.6), 0.1)
    cyl("rw_flagp", 0.12, 8, (x + 2.6, y + 2, 23), M("lamp", "#2a2833", 0.35, 0.6), 8)
    fl = box("rw_flag", (3.0, 0.08, 1.8), (x + 4.2, y + 2, 25.8), M("banner", PURPLE, 0.6), 0.02)
    noise(fl, "rotation_euler", 2, 0.08, 10)
    text("rw_flagt", "RA", (x + 4.2, y + 1.9, 25.8), 0.9, G("bt", NEON, 5.0), (90, 0, 0), 0.02, None, _font())


def bakery():
    x, y, _ = BAKERY
    building("rw_bakery", (x, y + 8, 0), (16, 9, 9), "#ffd1e3", "#b0465f", (3, 2), "#ffffff", awning=("#ff4bd8", "#ffffff"),
             sign="BLOX BAKERY", sign_color="#b0465f")
    for k, dx in enumerate((-4.5, 4.5)):   # outdoor tables + chairs + umbrellas
        cyl(f"rw_tab{k}", 1.3, 0.15, (x + dx, y, 2.4), M("table", "#ffffff", 0.4), 24)
        cyl(f"rw_tabl{k}", 0.15, 2.4, (x + dx, y, 1.2), M("lamp", "#2a2833", 0.35, 0.6), 8)
        cyl(f"rw_umb{k}", 2.8, 0.8, (x + dx, y, 6.5), M("umb", "#b46bff", 0.5), 16, r2=0.2)
        cyl(f"rw_umbp{k}", 0.08, 4.5, (x + dx, y, 4.3), M("lamp", "#2a2833", 0.35, 0.6), 8)
        cyl(f"rw_cup{k}", 0.25, 0.4, (x + dx + 0.4, y, 2.7), M("cup", "#ffffff", 0.3), 12)
        for sx in (-1, 1):
            box(f"rw_ch{k}{sx}", (1.2, 1.2, 1.4), (x + dx + sx * 2.0, y, 0.7), M("chair", "#ffd23a", 0.5), 0.15)
    box("rw_menu", (1.4, 0.3, 2.2), (x - 7, y + 2.5, 1.1), M("menu", "#2a2833", 0.6), 0.05, rot=(-10, 0, 0))
    for k in range(3):
        sphere(f"rw_donut{k}", 0.5, (x - 2 + k * 1.6, y + 3.0, 3.4), M("donut" + str(k), ("#ff9ac8", "#c98a4a", "#b46bff")[k], 0.5), (1, 1, 0.45), seg=12)
    box("rw_shelfb", (6, 1, 0.3), (x, y + 3.0, 3.0), M("trim", "#ffffff", 0.5), 0.05)


def skatepark(t0=0.0, t1=10.0):
    x, y, _ = SKATE
    Mc = stud_mat("conc", "#b9bcc4", 0.6)
    box("rw_skbase", (30, 24, 0.12), (x, y + 4, 0.06), Mc, 0)
    # quarter pipe (wedge ramp) + kicker + rail + bank with graffiti stripes
    poly_extrude("rw_qp", [(0, 0), (6, 0), (6, 4.5), (5.2, 4.5), (2.5, 1.2)], 10, (x - 12, y + 12, 0), Mc, rot=(90, 0, 90))
    poly_extrude("rw_kick", [(0, 0), (4.0, 0), (4.0, 1.6)], 4, (x - 2, y + 4, 0), stud_mat("kick", "#8a2be2", 0.6), rot=(90, 0, 0))
    Mr = M("rail", "#d9dde4", 0.2, 0.9)
    box("rw_rail", (8, 0.2, 0.2), (x + 6, y + 6, 1.6), Mr, 0.03)
    for sx in (-1, 1):
        box(f"rw_railp{sx}", (0.2, 0.2, 1.6), (x + 6 + sx * 3.5, y + 6, 0.8), Mr, 0.03)
    box("rw_wall", (24, 1, 5), (x, y + 16, 2.5), Mc, 0.1)
    for k, c in enumerate((PURPLE, NEON, "#ff4bd8", "#ffd23a")):
        box(f"rw_graf{k}", (4.5, 0.1, 2.6), (x - 9 + k * 6, y + 15.45, 2.8), M("graf" + c[1:], c, 0.5), 0.3, rot=(0, 0, 0))
    text("rw_skt", "SKATE ZONE", (x, y + 15.3, 4.4), 1.1, G("bt", NEON, 5.0), (90, 0, 0), 0.04, None, _font())
    for k in range(4):
        cyl(f"rw_cone{k}", 0.4, 1.0, (x + 8 + k * 1.6, y - 2, 0.5), M("cone", "#ff6a1f", 0.5), 12, r2=0.06)


def family_house():
    x, y, _ = HOUSE
    building("rw_house", (x, y + 6, 0), (16, 11, 10), "#bfe3ff", "#b0465f", (3, 2), "#ffffff", door="#3d4fa0")
    building("rw_garage", (x + 12, y + 7, 0), (8, 9, 6), "#bfe3ff", "#b0465f", (1, 1), "#ffffff", door="#ffffff")
    fence("rw_hfence", (x - 9, y - 1, 0), (x + 16, y - 1, 0))
    mailbox("rw_mail", (x - 6, y - 2.5, 0))
    for k in range(3):
        bush(f"rw_hb{k}", (x - 6 + k * 5, y + 0.2, 0), 0.9)
    text("rw_hnum", "7", (x, y + 0.4, 6.2), 1.0, M("hnum", "#2a2833", 0.5), (90, 0, 0), 0.05, None, _font())


def grill_yard(t0=0.0, t1=10.0):
    x, y, _ = GRILL
    box("rw_patio", (14, 10, 0.1), (x, y, 0.05), stud_mat("patio", "#d9b48a", 0.6), 0)
    Mk = M("grill", "#1e1e24", 0.35, 0.4)
    box("rw_grill", (3.4, 2.0, 1.4), (x, y + 1, 3.0), Mk, 0.2)
    box("rw_grillid", (3.4, 0.4, 1.6), (x, y + 2.1, 4.2), Mk, 0.15, rot=(-20, 0, 0))
    for sx in (-1, 1):
        box(f"rw_gleg{sx}", (0.2, 0.2, 2.4), (x + sx * 1.5, y + 1, 1.2), Mk, 0.02)
    for k in range(4):
        box(f"rw_patty{k}", (0.7, 0.7, 0.15), (x - 1.1 + k * 0.75, y + 0.8, 3.78), M("patty", "#4a2a18", 0.7), 0.1)
    glow = box("rw_coal", (3.0, 1.7, 0.1), (x, y + 1, 3.65), G("coal", "#ff6a1f", 6.0), 0.02)
    box("rw_ptable", (4, 2, 0.2), (x - 5, y, 2.4), M("benchw", "#a8693c", 0.6), 0.05)
    cyl("rw_ketch", 0.25, 0.8, (x - 5.6, y, 2.9), M("ketch", "#d9262e", 0.4), 12)
    cyl("rw_mustard", 0.25, 0.8, (x - 4.8, y, 2.9), M("must", "#ffd23a", 0.4), 12)
    tree("rw_gtree", (x + 6, y + 6, 0), 1.0, 9)
    fence("rw_gfence", (x - 7, y + 5, 0), (x + 7, y + 5, 0), "#e8d6b8")
    return glow


def park(t0=0.0, t1=10.0):
    x, y, _ = PARK
    bench("rw_pbench", (x, y, 0))
    cyl("rw_pond", 5, 0.1, (x + 9, y + 6, 0.06), M("water", "#5fc8ff", 0.05, spec=0.9), 32)
    for k, (dx, dy, s) in enumerate(((-6, 5, 1.1), (5, 9, 1.2), (-10, -2, 0.9), (12, -1, 1.0), (-3, 12, 1.3))):
        tree(f"rw_ptree{k}", (x + dx, y + dy, 0), s, k)
    flowers("rw_pfl", (x - 4, y - 3, 0), 12)
    lamp_post("rw_plamp", (x + 4, y - 1, 0), banner=True)
    box("rw_bin", (0.9, 0.9, 1.4), (x + 2.6, y, 0.7), M("bin", "#3f7a4a", 0.5), 0.1)
    for k in range(3):   # pigeons (simple)
        sphere(f"rw_pig{k}", 0.35, (x - 1.5 + k * 1.2, y - 2.5, 0.35), M("pig", "#9aa0aa", 0.6), (1.2, 0.8, 0.8), seg=10)


def hill_letters(lit=True):
    """Giant 3D block-letter RBLX ANIMATES on the hill north of town (purple faces, black sides, neon edge lights)."""
    x, y, _ = HILL
    t1 = text("rw_big1", "RBLX", (x, y - 30, 14), 18, M("biglet", PURPLE, 0.35, coat=0.5), (78, 0, 0), 2.6, None, _font())
    t2 = text("rw_big2", "ANIMATES", (x, y - 33, 5.5), 9.5, M("biglet2", LILAC, 0.35, coat=0.5), (78, 0, 0), 1.8, None, _font())
    for t in (t1, t2):
        t.data.bevel_depth = 0.25; t.data.bevel_resolution = 2
    if lit:
        light("rw_bigL", "AREA", (x, y - 55, 16), 30000, hexc(NEON), 30, target=(x, y - 30, 12))
    for k in range(-3, 4):
        box(f"rw_bigbase{k}", (8, 4, 3), (x + k * 9, y - 31, 0.0), M("base", BLACK, 0.5), 0.2)


def neon_arch(t_on=None):
    """Spawn-plaza arch with the neon RBLX ANIMATES sign. t_on: flickers on at that time (off before)."""
    Mb = M("arch", BLACK, 0.35, 0.3)
    for sx in (-1, 1):
        box(f"rw_archp{sx}", (2, 2, 11), (sx * 9, 14, 5.5), Mb, 0.2)
        box(f"rw_archs{sx}", (2.1, 2.1, 0.3), (sx * 9, 14, 3.0), G("archs", NEON, 4.0), 0.02)
    box("rw_archt", (21, 2.2, 3.4), (0, 14, 12.5), Mb, 0.25)
    m1 = mat("rw_neon_main", hexc(NEON), 0.3, emit=hexc(NEON), estr=14.0)
    m2 = mat("rw_neon_sub", hexc(LILAC), 0.3, emit=hexc(LILAC), estr=14.0)
    t = text("rw_archtx", "RBLX ANIMATES", (0, 12.8, 12.6), 1.9, m1, (90, 0, 0), 0.1, None, _font())
    box("rw_archline", (19, 0.1, 0.12), (0, 12.85, 11.2), m2, 0.0)
    if t_on is not None:
        for m, base in ((m1, 14.0), (m2, 14.0)):
            b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Emission Strength"]
            for tt, v in ((0.0, 0.0), (t_on - 0.02, 0.0), (t_on + 0.04, base), (t_on + 0.1, 1.0), (t_on + 0.16, base), (t_on + 0.22, 3.0), (t_on + 0.3, base)):
                b.default_value = v; b.keyframe_insert("default_value", frame=F(max(0, tt)))
    return t


def arch_on(t):
    neon_arch(t)


def blox_town(t0=0.0, t1=10.0, arch_t_on=None, hill=True, lights=True):
    sky_day(); ground(); hills()
    spawn_pad("rw_spawn", (0, 0, 0)); fountain("rw_fount", (-9, 7, 0), t0, t1)
    neon_arch(arch_t_on)
    for k, (x, y) in enumerate(((-12, -3), (12, -3), (-12, 10), (12, 10), (-30, -4), (30, -4), (-6, 26), (6, 26))):
        lamp_post(f"rw_lamp{k}", (x, y, 0))
    for k, (x, y) in enumerate(((-10, -1), (9, 6))):
        bench(f"rw_bench{k}", (x, y, 0), 90 if x < 0 else -90)
    town_hall(t0, t1); bakery(); skatepark(t0, t1); family_house(); grill_yard(t0, t1); park(t0, t1)
    building("rw_shop1", (20, 22, 0), (10, 9, 8), "#c8f2c0", "#3f7a4a", (2, 2), "#ffffff", awning=("#3f9a3a", "#ffffff"), sign="TOYS")
    building("rw_shop2", (-22, 22, 0), (10, 9, 9), "#fff1b0", "#b07a2a", (2, 2), "#ffffff", awning=("#ffd23a", "#ffffff"), sign="BOOKS")
    building("rw_shop3", (-24, -22, 0), (12, 8, 8), "#ffd9b0", "#b0465f", (3, 1), "#ffffff", rot=180)
    building("rw_shop4", (22, -22, 0), (12, 8, 10), "#e0d0ff", PURPLE, (3, 2), "#ffffff", rot=180)
    rnd = random.Random(7)
    for k in range(18):
        x = rnd.choice([-1, 1]) * rnd.uniform(16, 80); yy = rnd.uniform(-30, 90)
        if abs(x) < 20 and -12 < yy < 50:
            continue
        tree(f"rw_tree{k}", (x, yy, 0), rnd.uniform(0.9, 1.4), k)
    for k in range(10):
        bush(f"rw_bush{k}", (rnd.uniform(-60, 60), rnd.uniform(14, 34), 0), rnd.uniform(0.7, 1.1))
    flowers("rw_fl1", (-7, -2, 0), 10, 2); flowers("rw_fl2", (7, -2, 0), 10, 3)
    for k in range(3):
        crate(f"rw_crate{k}", (34 + k * 1.3, 2 + (k % 2), 0), 1.2, k * 15)
    if hill:
        hill_letters(lights)


# ------------------------------------------------------------------ interiors (story_warm)
def _room(prefix, origin, size=(22, 16, 10), floor="#b5764e", wall="#e9d6bf"):
    from .sets import planks
    x, y, _ = origin
    w, d, h = size
    box(prefix + "_floor", (w, d + 10, 0.3), (x, y + d / 2 - 5, -0.15), planks(prefix + "_pl", floor, "#a86a44", "#5c3a27", 1.0), 0)
    box(prefix + "_back", (w, 0.5, h), (x, y + d - 5, h / 2), M(prefix + "_wall", wall, 0.85), 0)
    for sx in (-1, 1):
        box(f"{prefix}_side{sx}", (0.5, d + 10, h), (x + sx * w / 2, y + d / 2 - 5, h / 2), M(prefix + "_wall", wall, 0.85), 0)
    box(prefix + "_ceil", (w, d + 10, 0.3), (x, y + d / 2 - 5, h), M("ceil", "#f4ede2", 0.9), 0)
    box(prefix + "_base", (w, 0.2, 0.5), (x, y + d - 5.3, 0.25), M("baseb", "#ffffff", 0.5), 0.02)


def kitchen():
    x, y, _ = KITCHEN
    _room("kt", KITCHEN, wall="#d9efe6")
    Mc, Mt = M("cab", "#ffffff", 0.4), M("counter", "#2a2833", 0.25, spec=0.8)
    box("kt_cab", (14, 2.2, 3.0), (x, y + 9.6, 1.5), Mc, 0.08)
    box("kt_top", (14.4, 2.6, 0.3), (x, y + 9.6, 3.15), Mt, 0.04)
    box("kt_upper", (14, 1.4, 2.6), (x, y + 10.2, 7.2), Mc, 0.08)
    box("kt_fridge", (3, 2.6, 7.5), (x + 8.8, y + 9.4, 3.75), M("fridge", "#cfd6e0", 0.2, 0.5), 0.15)
    box("kt_island", (6, 3, 3.0), (x - 1, y + 3, 1.5), M("island", "#19c2b0", 0.5), 0.1)
    box("kt_itop", (6.4, 3.4, 0.3), (x - 1, y + 3, 3.15), Mt, 0.04)
    cyl("kt_coffee", 0.6, 1.6, (x - 4.5, y + 9.6, 4.1), M("cm", "#1e1e24", 0.3, 0.4), 16)
    for k in range(3):
        cyl(f"kt_pot{k}", 0.4, 0.7, (x + 2 + k * 1.4, y + 9.6, 3.65), M("pot" + str(k), ("#ff6f61", "#ffd23a", "#b46bff")[k], 0.4), 12)
    box("kt_win", (5, 0.2, 3), (x - 3, y + 10.7, 6.5), M("glass", "#bfe8ff", 0.05, emit=hexc("#cfeaff"), estr=1.5), 0.04)
    box("kt_clock", (1.2, 0.1, 1.2), (x + 4, y + 10.7, 7.8), M("clockk", "#ffffff", 0.4), 0.5)
    light("kt_winL", "AREA", (x - 3, y + 9.5, 6.5), 900, (1.0, 0.9, 0.75), 4, target=(x, y, 3))
    light("kt_pend", "POINT", (x - 1, y + 3, 8.0), 600, (1.0, 0.75, 0.45), 0.8)


def living_room(t0=0.0, t1=10.0, gamer=False):
    x, y, _ = LIVING
    _room("lv", LIVING, wall="#efdcc6")
    box("lv_rug", (10, 6, 0.05), (x, y + 2, 0.03), M("rug", "#8a2be2", 0.9), 0.0)
    Ms = M("sofa", "#b0465f", 0.8)
    box("lv_sofa", (8, 3, 1.6), (x, y + 7.5, 0.8), Ms, 0.3)
    box("lv_sofab", (8, 1, 3.2), (x, y + 8.8, 1.6), Ms, 0.3)
    for sx in (-1, 1):
        box(f"lv_arm{sx}", (1, 3, 2.4), (x + sx * 4.2, y + 7.5, 1.2), Ms, 0.3)
    box("lv_tvst", (6, 1.6, 1.6), (x + 0.5, y - 1.5, 0.8), M("tvst", "#5a3a26", 0.5), 0.06)
    tv = box("lv_tv", (5.4, 0.3, 3.2), (x + 0.5, y - 1.6, 3.4), G("tv", "#26d9ff" if gamer else "#1b1b24", 3.0 if gamer else 0.2), 0.06, rot=(0, 0, 180))
    box("lv_lamp", (0.3, 0.3, 4.5), (x - 6, y + 8, 2.25), M("lamp", "#2a2833", 0.35, 0.6), 0.03)
    cyl("lv_shade", 1.0, 1.4, (x - 6, y + 8, 5.0), G("shade", "#ffd9a0", 2.0), 16, r2=0.6)
    light("lv_lampL", "POINT", (x - 6, y + 8, 4.6), 700, (1.0, 0.75, 0.45), 1.0)
    from .aiworld import shelf
    shelf("lv_shelf", (x + 8, y + 9.5, 0), 0, 4, 4, 6)
    for k in range(3):
        box(f"lv_frame{k}", (1.6, 0.1, 1.2), (x - 3 + k * 2.6, y + 10.6, 6.5), M("frame" + str(k), ("#ff6f61", "#26d9ff", "#ffd23a")[k], 0.5), 0.05)
    sphere("lv_yarn", 0.5, (x + 3.2, y + 7.2, 1.9), M("yarn", "#e0263a", 0.9), seg=12)
    box("lv_plant", (1, 1, 1), (x + 6.5, y + 6, 0.5), M("pot", "#c98a4a", 0.6), 0.1)
    sphere("lv_leaves", 1.2, (x + 6.5, y + 6, 1.9), stud_mat("leaf1", "#4fb045", 1.0), seg=12)
    if gamer:
        light("lv_rgb", "AREA", (x + 0.5, y - 0.5, 3.5), 2500, hexc("#b46bff"), 4, target=(x, y + 7, 3))
    return tv
