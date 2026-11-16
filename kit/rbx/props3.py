"""rbx.props3 v4.2 (2026-11-16, EP3 adds phone(image screen), duck_light, coin_bag, limited_hat, tent, camp_lamp, camp_ground; v4.1 2026-11-15): story props that READ at phone size, each with GRIP points for rbx.shotlib.hold().
Lesson from EP2 (user review): a plain brown box is not a pizza box, a white slab is not a keyboard, a coloured box is not a
book. Every story prop needs its identifying details (logo, keys, page block, spine, screen UI) and defined hand grips.
Every builder returns a dict: root (Empty at the prop centre, local +X = the HOLDER'S LEFT, -Y = away from the holder),
w (width along X), d (depth), h (height), grips {'L': local point, 'R': local point}, style ('sides' | 'under')."""
import math
import bpy
from mathutils import Vector
from .core import box, cyl, mat, hexc
from . import signs as SG


def _root(name, loc=(0, 0, 0)):
    r = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(r)
    r.location = loc
    return r


def _p(name, size, loc, col, rough=0.6, root=None, bev=0.03, metal=0.0):
    return box(name, size, loc, mat(name + "_m" if not col.startswith("#") else "p3_" + col.strip("#") + f"_{rough}",
                                    hexc(col), rough, metal), bev, parent=root)


def pizza_box(name="pizza", w=2.2, h=0.32, open_lid=False, loc=(0, 0, 0)):
    """Square cardboard pizza box: kraft body, lid seam, red round logo + PIZZA print on the lid, air vents."""
    r = _root(name, loc)
    _p(name + "_body", (w, w, h * 0.6), (0, 0, -h * 0.2), "#c9a46c", 0.85, r, 0.02)
    _p(name + "_lid", (w + 0.04, w + 0.04, h * 0.42), (0, 0, h * 0.29), "#d6b37a", 0.85, r, 0.02)
    cyl(name + "_logo", w * 0.27, 0.02, (0, 0, h * 0.51), mat("p3_pizzalogo", hexc("#c62828"), 0.5), 32, parent=r)
    SG.label(name + "_t", "PIZZA", (0, 0, h * 0.53), w * 0.11, "#ffffff", "bold", 0, parent=r, rot=(0, 0, 0))
    SG.label(name + "_t2", "HOT & FRESH", (0, -w * 0.36, h * 0.52), w * 0.06, "#7a2a14", "bold", 0, parent=r, rot=(0, 0, 0))
    for k in (-1, 1):
        _p(f"{name}_vent{k}", (w * 0.25, 0.05, 0.02), (k * w * 0.3, w * 0.42, h * 0.51), "#9c7a48", 0.9, r, 0.0)
    return dict(root=r, w=w, d=w, h=h, grips={"L": (w * 0.32, -w * 0.05, -h * 0.5), "R": (-w * 0.32, -w * 0.05, -h * 0.5)},
                style="under")


def book_stack(name="books", n=3, w=1.5, d=1.05, t=0.26, seed=0, loc=(0, 0, 0)):
    """Books that read as books: coloured hard cover, white page block inset on 3 sides, darker spine, title strip."""
    cols = ["#2f6db3", "#c0392b", "#2e8b57", "#d4a017"]
    r = _root(name, loc)
    for k in range(n):
        c = cols[(k + seed) % 4]; z = (k - (n - 1) / 2) * (t + 0.02)
        rot = (k * 7 - 7) * math.pi / 180
        b = _root(f"{name}_b{k}"); b.parent = r; b.location = (0.04 * (k - 1), 0, z); b.rotation_euler = (0, 0, rot)
        _p(f"{name}_c{k}", (w, d, t), (0, 0, 0), c, 0.55, b, 0.03)
        _p(f"{name}_pg{k}", (w - 0.08, d - 0.1, t * 0.72), (0.05, -0.02, 0), "#f3eee2", 0.9, b, 0.0)
        _p(f"{name}_sp{k}", (0.08, d + 0.01, t + 0.01), (-w / 2, 0, 0), c, 0.4, b, 0.02)
        _p(f"{name}_ti{k}", (w * 0.45, 0.02, t * 0.35), (0, -d / 2 - 0.005, 0), "#ffffff", 0.7, b, 0.0)
    H = n * (t + 0.02)
    return dict(root=r, w=w, d=d, h=H, grips={"L": (w / 2 + 0.05, 0, 0), "R": (-w / 2 - 0.05, 0, 0)}, style="sides")


def keyboard(name="kbd", w=2.6, d=0.9, loc=(0, 0, 0), body="#2b2d33", keys="#e9e4d6"):
    """Keyboard that reads as a keyboard: dark body, 4 rows x 12 light keycaps + space bar."""
    r = _root(name, loc)
    _p(name + "_body", (w, d, 0.12), (0, 0, 0), body, 0.5, r, 0.03)
    kw, kd = (w - 0.3) / 12, (d - 0.25) / 5
    for row in range(4):
        for c in range(12):
            _p(f"{name}_k{row}_{c}", (kw * 0.8, kd * 0.8, 0.06), (-w / 2 + 0.15 + kw * (c + 0.5), d / 2 - 0.12 - kd * (row + 0.5), 0.08),
               keys, 0.55, r, 0.012)
    _p(name + "_space", (kw * 6, kd * 0.8, 0.06), (0, d / 2 - 0.12 - kd * 4.5, 0.08), keys, 0.55, r, 0.012)
    return dict(root=r, w=w, d=d, h=0.16, top=0.11, grips={"L": (w * 0.22, 0, 0.28), "R": (-w * 0.22, 0, 0.28)}, style="type")


def laptop(name="laptop", w=2.4, d=1.6, open_deg=108, lines=(("SYSTEM CHECK", "#7cff9a"), ("VIRUS REMOVED", "#ffffff"), ("FIXED!", "#7cff9a")),
           loc=(0, 0, 0)):
    """Open laptop: silver base with dark keyboard + trackpad, hinged screen with readable UI text."""
    r = _root(name, loc)
    _p(name + "_base", (w, d, 0.1), (0, 0, 0.05), "#b9bec6", 0.35, r, 0.03, 0.4)
    kb = keyboard(name + "_kb", w * 0.86, d * 0.48, loc=(0, 0, 0)); kb["root"].parent = r; kb["root"].location = (0, 0.12, 0.08)
    kb["root"].scale = (1, 1, 0.5)
    _p(name + "_pad", (w * 0.3, d * 0.22, 0.01), (0, -d * 0.32, 0.105), "#9aa0a8", 0.3, r, 0.01)
    hinge = _root(name + "_hinge"); hinge.parent = r; hinge.location = (0, d / 2, 0.1)
    hinge.rotation_euler = (math.radians(open_deg - 90), 0, 0)
    _p(name + "_lid", (w, 0.08, d), (0, 0, d / 2), "#b9bec6", 0.35, hinge, 0.03, 0.4)
    scr = SG.screen(name + "_scr", list(lines), (0, -0.05, d / 2), w=w * 0.9, h=d * 0.82, bg="#0b1020", size=d * 0.1,
                    bezel="#111111", glow=3.0)
    scr.parent = hinge
    return dict(root=r, w=w, d=d, h=0.1, keys=(0, 0.12, 0.2), grips={"L": (w * 0.2, 0.1, 0.25), "R": (-w * 0.2, 0.1, 0.25)},
                style="type")


def tray(name="tray", w=2.0, d=1.2, loc=(0, 0, 0)):
    """Lunch tray with compartments: burger, apple, milk carton."""
    r = _root(name, loc)
    _p(name + "_t", (w, d, 0.1), (0, 0, 0), "#e04a3a", 0.4, r, 0.03)
    _p(name + "_bun", (0.55, 0.55, 0.22), (-0.5, 0, 0.17), "#d9a35a", 0.7, r, 0.1)
    _p(name + "_patty", (0.58, 0.58, 0.08), (-0.5, 0, 0.14), "#5a3220", 0.7, r, 0.03)
    cyl(name + "_apple", 0.2, 0.36, (0.15, -0.15, 0.25), mat("p3_apple", hexc("#cc2a2a"), 0.4), 16, parent=r)
    _p(name + "_milk", (0.32, 0.32, 0.55), (0.65, 0.2, 0.33), "#f4f4f4", 0.6, r, 0.03)
    _p(name + "_milkb", (0.33, 0.33, 0.15), (0.65, 0.2, 0.33), "#2f7bff", 0.6, r, 0.01)
    return dict(root=r, w=w, d=d, h=0.6, grips={"L": (w / 2 + 0.05, 0, 0), "R": (-w / 2 - 0.05, 0, 0)}, style="sides")


# =====================================================================================================================
# v4.2 (2026-11-16, EP3 friend_secret): phone with an IMAGE screen, duck night-light (real light), coin bag, limited
# hat (accessory), tent + camp ground + camp lamp. Same return convention: dict(root, w, d, h, grips{L,R}, style),
# local +X = the HOLDER'S LEFT, -Y = away from the holder (the side a held prop SHOWS to the people in front).
# =====================================================================================================================
import os
from .core import sphere, plane, light, img_mat, empty, poly_extrude


def _shadowless(ob):
    """Shell of a light source must not block its own light (point light inside a closed mesh)."""
    for o in [ob] + list(ob.children_recursive):
        try:
            o.visible_shadow = False
        except AttributeError:
            pass


def _key_input(m, sock, frames_vals):
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    for f, v in frames_vals:
        b.inputs[sock].default_value = v
        b.inputs[sock].keyframe_insert("default_value", frame=f)


def _constant(idb):
    from .core import fcurves
    ad = getattr(idb, "animation_data", None)
    if ad and ad.action:
        for fc in fcurves(ad.action):
            for kp in fc.keyframe_points:
                kp.interpolation = "CONSTANT"


def _key_energy(lt, frames_vals):
    for f, v in frames_vals:
        lt.data.energy = v
        lt.data.keyframe_insert("energy", frame=f)


def phone(name="phone", screens=None, w=0.9, h=1.8, case="#22252c", loc=(0, 0, 0), glow=1.4, facing="out"):
    """Smartphone that READS at phone size: rounded dark case, side buttons, camera bump on the back and a screen that
    shows an IMAGE (readable UI made with Pillow). screens = path or [(t_on, path), ...] (each shown from t_on until the
    next one). facing 'out' = screen on local -Y (shown to whoever stands in front of the holder / to the lens in an
    insert), 'in' = screen faces the holder (+Y). Grips on the long edges ('sides')."""
    from .core import F
    r = _root(name, loc)
    piv = _root(name + "_piv"); piv.parent = r
    if facing == "in":
        piv.rotation_euler = (0, 0, math.pi)
    _p(name + "_case", (w, 0.12, h), (0, 0, 0), case, 0.35, piv, 0.07)
    _p(name + "_bump", (0.3, 0.05, 0.3), (-w * 0.25, 0.08, h * 0.36), "#15171c", 0.3, piv, 0.04)
    cyl(name + "_lens", 0.07, 0.04, (-w * 0.25, 0.105, h * 0.36), mat("p3_lens", hexc("#05070a"), 0.1, 0.3), 16,
        rot=(90, 0, 0), parent=piv)
    _p(name + "_btn", (0.04, 0.06, 0.3), (w / 2 + 0.01, 0, h * 0.18), "#3a3d45", 0.3, piv, 0.01)
    if screens is None:
        screens = []
    if isinstance(screens, str):
        screens = [(None, screens)]
    sw, sh = w - 0.08, h - 0.1
    if not screens:
        plane(name + "_scr", sw, sh, (0, -0.062, 0), mat("p3_scr_off", hexc("#07080a"), 0.15), (90, 0, 0), piv)
    for k, (t_on, path) in enumerate(screens):
        m = img_mat(f"p3_scr_{os.path.basename(path)}", path, rough=0.2, emit=glow)
        sc = plane(f"{name}_scr{k}", sw, sh, (0, -0.062 - 0.001 * k, 0), m, (90, 0, 0), piv)
        t_off = screens[k + 1][0] if k + 1 < len(screens) else None
        if t_on is not None or t_off is not None:
            SG.show(sc, t_on, t_off)
    return dict(root=r, w=w, d=0.12, h=h, grips={"L": (w / 2 + 0.05, 0, -h * 0.15), "R": (-w / 2 - 0.05, 0, -h * 0.15)},
                style="sides", piv=piv)


def duck_light(name="duck", s=1.0, loc=(0, 0, 0), on=None, off=None, power=260.0, color="#ffd27a", radius=0.35, lit=True,
               glow=0.9, glow_col="#ffb81f"):
    """Yellow DUCK NIGHT-LIGHT: white base with a switch, round body, head, orange beak, black eyes, little wings and tail.
    The shell glows (emission) and a warm point light inside lights faces at night (shell casts no shadow).
    on/off: times; on=None + off=None = always on; on=t = dark until t (click), off=t = dies at t; lit=False = off.
    Root = body CENTRE (0.7*s above the base bottom: stand it on a surface at z + 0.7*s). Faces local -Y (beak).
    Grips on the body sides ('sides'). Returns dict(..., light, glow_mat, bottom=-0.7*s, top=0.85*s)."""
    from .core import F
    r0 = _root(name, loc)
    k = s
    r = _root(name + "_c"); r.parent = r0; r.location = (0, 0, -0.7 * k)
    _p(name + "_base", (0.95 * k, 0.8 * k, 0.2 * k), (0, 0, 0.1 * k), "#f4f1ea", 0.4, r, 0.08 * k)
    _p(name + "_sw", (0.18 * k, 0.06 * k, 0.1 * k), (0.25 * k, -0.42 * k, 0.11 * k), "#ff8a1e", 0.4, r, 0.02 * k)
    gm = mat(name + "_glow", hexc("#ffd21e"), 0.45, emit=hexc(glow_col), estr=glow)
    body = sphere(name + "_body", 0.5 * k, (0, 0.05 * k, 0.62 * k), gm, (1.1, 1.0, 0.82), parent=r, seg=32)
    tail = sphere(name + "_tail", 0.2 * k, (0, 0.5 * k, 0.85 * k), gm, (0.8, 1.0, 0.7), parent=r, rot=(-35, 0, 0))
    hd = sphere(name + "_head", 0.34 * k, (0, -0.25 * k, 1.18 * k), gm, (1, 1, 1), parent=r, seg=32)
    for sx in (-1, 1):
        sphere(f"{name}_wing{sx}", 0.24 * k, (sx * 0.5 * k, 0.1 * k, 0.66 * k), gm, (0.35, 1.0, 0.65), parent=r)
        sphere(f"{name}_eye{sx}", 0.055 * k, (sx * 0.14 * k, -0.53 * k, 1.27 * k), mat("p3_duckeye", hexc("#111111"), 0.2),
               parent=r, seg=12)
        sphere(f"{name}_hi{sx}", 0.02 * k, (sx * 0.14 * k - 0.02 * k, -0.585 * k, 1.29 * k), mat("p3_duckhi", hexc("#ffffff"), 0.2,
               emit=hexc("#ffffff"), estr=2.0), parent=r, seg=8)
    sphere(name + "_beak", 0.17 * k, (0, -0.62 * k, 1.1 * k), mat("p3_beak", hexc("#ff8a1e"), 0.4, emit=hexc("#ff8a1e"), estr=0.3),
           (1.0, 0.9, 0.45), parent=r)
    lt = light(name + "_L", "POINT", (0, 0, 0), power, hexc(color), radius * k)
    lt.parent = r; lt.location = (0, -0.3 * k, 0.9 * k)
    _shadowless(body); _shadowless(hd); _shadowless(tail)
    for o in r0.children_recursive:
        if o.name.startswith((name + "_wing", name + "_beak", name + "_eye", name + "_hi")):
            _shadowless(o)
    try:                                             # light linking: the inner light skips the duck's own shell
        lc = bpy.data.collections.new(name + "_shell_x")
        for o in r0.children_recursive:
            if o.type == "MESH":
                lc.objects.link(o)
        lt.light_linking.receiver_collection = lc
        for co in lc.collection_objects:
            co.light_linking.link_state = "EXCLUDE"
    except Exception as e:
        print("duck light linking", e)
    keys_e, keys_l = [], []
    if on is not None:
        keys_e += [(1, 0.0), (F(on) - 1, 0.0), (F(on), glow * 1.25), (F(on) + 3, glow)]
        keys_l += [(1, 0.0), (F(on) - 1, 0.0), (F(on), power * 1.15), (F(on) + 3, power)]
    if off is not None:
        keys_e += [(F(off) - 1, glow), (F(off), 0.0)]
        keys_l += [(F(off) - 1, power), (F(off), 0.0)]
    if not lit:
        keys_e, keys_l = [], []
        _key_input(gm, "Emission Strength", [(1, 0.04)]); _key_energy(lt, [(1, 0.0)])
    if keys_e:
        _key_input(gm, "Emission Strength", keys_e)
        _key_energy(lt, keys_l)
    w = 1.2 * k
    return dict(root=r0, w=w, d=1.0 * k, h=1.55 * k, grips={"L": (w / 2 + 0.05, 0.05 * k, -0.08 * k), "R": (-w / 2 - 0.05, 0.05 * k, -0.08 * k)},
                style="sides", light=lt, glow_mat=gm, bottom=-0.7 * k, top=0.85 * k, head_top=(0, -0.25 * k, 0.82 * k),
                switch=(0.25 * k, -0.45 * k, -0.59 * k))


def coin_bag(name="coinbag", loc=(0, 0, 0), label="500", s=1.0):
    """Burlap money sack tied with gold rope, gold coins showing at the mouth, a white tag with a BIG '500' on the
    front (-Y) so the amount reads in a medium shot. Root = CENTRE (0.85*s above the bottom). Grips under it ('under')."""
    r0 = _root(name, loc)
    k = s
    r = _root(name + "_c"); r.parent = r0; r.location = (0, 0, -0.85 * k)
    sack = mat("p3_burlap", hexc("#b98a52"), 0.9)
    sphere(name + "_sack", 0.66 * k, (0, 0, 0.6 * k), sack, (1.0, 0.86, 0.92), parent=r, seg=32)
    cyl(name + "_neck", 0.24 * k, 0.32 * k, (0, 0, 1.25 * k), sack, 20, parent=r, r2=0.2 * k)
    cyl(name + "_rope", 0.235 * k, 0.09 * k, (0, 0, 1.22 * k), mat("p3_rope", hexc("#d4a73f"), 0.5, 0.6), 20, parent=r)
    sphere(name + "_frill", 0.34 * k, (0, 0, 1.47 * k), sack, (1.0, 1.0, 0.45), parent=r)
    gold = mat("p3_coin", hexc("#f2c230"), 0.25, 1.0)
    for i, (x, y, rx) in enumerate(((-0.12, -0.05, 20), (0.1, 0.06, -15), (0.0, -0.12, 35))):
        cyl(f"{name}_c{i}", 0.13 * k, 0.04 * k, (x * k, y * k, 1.62 * k), gold, 24, rot=(rx, 0, 0), parent=r)
    _p(name + "_tag", (0.86 * k, 0.04 * k, 0.5 * k), (0, -0.62 * k, 0.6 * k), "#fbf6e8", 0.6, r, 0.03 * k)
    SG.label(name + "_t", label, (0, -0.655 * k, 0.58 * k), 0.42 * k, "#1d1d1d", "bold", 0, parent=r)
    return dict(root=r0, w=1.3 * k, d=1.14 * k, h=1.7 * k, grips={"L": (0.42 * k, 0, -0.8 * k), "R": (-0.42 * k, 0, -0.8 * k)},
                style="under", front=(0, -0.62 * k, -0.25 * k), neck=(0, 0, 0.6 * k), bottom=-0.85 * k)


def limited_hat(ch, name=None, col="#f2c230", hide_hair=True):
    """Shiny 'LIMITED' cap ON a cast/Char head (parented to the head, sits ON TOP: never covers the eyes): metallic gold
    crown (truncated cone + dome), red band with LIMITED, black brim forward, white star badge. Hides the hair."""
    from .cast import HT, HF
    name = name or ch.name + "_ltdhat"
    hdo = ch.head
    gold = mat("p3_ltd_gold", hexc(col), 0.16, 1.0, coat=0.6)
    cyl(name + "_crown", 0.68, 0.36, (0, 0.03, HT + 0.08), gold, 40, parent=hdo, r2=0.5)
    sphere(name + "_dome", 0.5, (0, 0.03, HT + 0.25), gold, (1.0, 1.0, 0.42), parent=hdo, seg=32)
    cyl(name + "_band", 0.69, 0.23, (0, 0.03, HT + 0.0), mat("p3_ltd_band", hexc("#c62828"), 0.4), 40, parent=hdo)
    br = cyl(name + "_brim", 0.62, 0.07, (0, HF - 0.12, HT - 0.08), mat("p3_ltd_brim", hexc("#141418"), 0.3, coat=0.4), 32,
             parent=hdo)
    br.scale = (0.95, 0.85, 1.0)
    SG.label(name + "_t", "LIMITED", (0, -0.672, HT + 0.02), 0.155, "#ffffff", "bold", 0, parent=hdo)   # v4.3: reads in a CU
    cyl(name + "_star", 0.11, 0.03, (0, -0.5, HT + 0.2), mat("p3_ltd_star", hexc("#ffffff"), 0.3, emit=hexc("#ffffff"),
        estr=0.6), 5, rot=(62, 0, 0), parent=hdo)
    sphere(name + "_btn", 0.07, (0, 0.03, HT + 0.47), gold, parent=hdo)
    if hide_hair:
        for o in ch.coll.all_objects:
            if "hair" in o.name.lower() and o.type == "MESH":
                o.hide_render = True; o.hide_viewport = True
    return bpy.data.objects[name + "_crown"]


def tent(name, loc, rot=0.0, w=7.0, d=8.0, h=5.5, col="#e8742a", fly="#2f5a8a", door_open=True):
    """A-frame camping tent: fabric prism (front faces local -Y), contrasting rain-fly ridge, dark door triangle with
    rolled-up flap, ground sheet edge, guy lines + pegs. Origin = ground centre."""
    r = _root(name, loc); r.rotation_euler = (0, 0, math.radians(rot))
    fab = mat(f"p3_tent_{col}", hexc(col), 0.85)
    tri = [(-w / 2, 0), (w / 2, 0), (0, h)]
    body = poly_extrude(name + "_body", tri, d, (0, d / 2, 0), fab, rot=(90, 0, 0), parent=r)
    rid = mat(f"p3_tentfly_{fly}", hexc(fly), 0.8)
    for sx in (-1, 1):                                                       # fly panels on the upper slopes
        a = math.atan2(h, w / 2)
        ln = 0.45 * math.hypot(w / 2, h)
        box(f"{name}_fly{sx}", (ln, d + 0.3, 0.08), (sx * (w / 4) * 0.55, 0, h * 0.78), rid, 0.03,
            rot=(0, -sx * math.degrees(a), 0), parent=r)
    dw, dh = w * 0.42, h * 0.62
    poly_extrude(name + "_door", [(-dw / 2, 0.02), (dw / 2, 0.02), (0, dh)], 0.04, (0, -d / 2 + 0.02, 0),
                 mat("p3_tent_door", hexc("#141210"), 0.95), rot=(90, 0, 0), parent=r)
    if door_open:
        cyl(name + "_roll", 0.16, dh * 0.75, (-dw / 2 - 0.15, -d / 2 - 0.08, dh * 0.42), fab, 12, rot=(0, -18, 0), parent=r)
    box(name + "_sheet", (w + 0.4, d + 0.4, 0.06), (0, 0, 0.03), mat("p3_tent_sheet", hexc("#3b4a3a"), 0.9), 0.02, parent=r)
    peg = mat("p3_peg", hexc("#c9ccd2"), 0.4, 0.8)
    for sx in (-1, 1):
        for sy in (-1, 1):
            cyl(f"{name}_peg{sx}{sy}", 0.06, 0.4, (sx * (w / 2 + 1.0), sy * (d / 2 - 0.5), 0.15), peg, 8, parent=r)
            p0 = Vector((sx * w * 0.18, sy * (d / 2 - 0.3), h * 0.66)); p1 = Vector((sx * (w / 2 + 1.0), sy * (d / 2 - 0.5), 0.3))
            dv = p1 - p0; c = (p0 + p1) / 2
            gl = cyl(f"{name}_guy{sx}{sy}", 0.025, dv.length, tuple(c), mat("p3_guy", hexc("#e8e4da"), 0.7), 6, parent=r)
            gl.rotation_mode = "QUATERNION"; gl.rotation_quaternion = dv.to_track_quat("Z", "Y")
    return dict(root=r, w=w, d=d, h=h)


def camp_lamp(name, loc, power=900.0, color="#ffd08a", off=None, flicker=None, h=6.5):
    """Camp light pole: wooden post, bulb in a cage that glows, a warm area/point light. off=t: dies at t (power cut);
    flicker=(t0, t1) quick stutter before it dies."""
    from .core import F
    r = _root(name, loc)
    cyl(name + "_post", 0.18, h, (0, 0, h / 2), mat("p3_lamppost", hexc("#6b4a2e"), 0.85), 8, parent=r)
    box(name + "_arm", (1.2, 0.2, 0.2), (0.5, 0, h - 0.2), mat("p3_lamppost", hexc("#6b4a2e"), 0.85), 0.03, parent=r)
    gm = mat(name + "_bulb", hexc("#fff2cc"), 0.3, emit=hexc(color), estr=6.0)
    b = sphere(name + "_b", 0.32, (1.0, 0, h - 0.6), gm, parent=r)
    _shadowless(b)
    cyl(name + "_cap", 0.42, 0.18, (1.0, 0, h - 0.25), mat("p3_lampcap", hexc("#2a2a2a"), 0.4, 0.6), 16, parent=r)
    lt = light(name + "_L", "POINT", (0, 0, 0), power, hexc(color), 0.6)
    lt.parent = r; lt.location = (1.0, 0, h - 0.75)
    if off is not None:
        ke = [(F(off) - 1, 6.0), (F(off), 0.0)]; kl = [(F(off) - 1, power), (F(off), 0.0)]
        if flicker:
            f0, f1 = F(flicker[0]), F(flicker[1])
            seq = []
            for f in range(f0, f1, 2):
                v = 1.0 if (f // 2) % 2 == 0 else 0.15
                seq.append((f, v))
            ke = [(f, 6.0 * v) for f, v in seq] + ke; kl = [(f, power * v) for f, v in seq] + kl
        _key_input(gm, "Emission Strength", ke)
        _key_energy(lt, kl)
        _constant(gm.node_tree); _constant(lt.data)
    return dict(root=r, light=lt, mat=gm)


def camp_ground(o=(0, 0, 0), size=90.0, night=True, seed=3, coll=None):
    """Camp clearing: grass ground (displaced slightly, two-tone), a ring of trees, stumps/logs to sit by, a few rocks,
    backpacks and a CAMP BLOX wooden sign. The clearing centre (o) is kept free for the circle."""
    import random
    from . import town as T
    rnd = random.Random(seed)
    ox, oy, oz = o
    g = mat("p3_grass_n" if night else "p3_grass_d", hexc("#4f7a32" if not night else "#3d5a2a"), 0.9)
    box("camp_ground", (size, size, 0.4), (ox, oy, oz - 0.2), g, 0.0)
    dirt = mat("p3_dirt", hexc("#8a6a48"), 0.95)
    cyl("camp_dirt", 11.0, 0.05, (ox, oy, oz + 0.02), dirt, 48)
    for i in range(14):                                   # tree ring, gap toward -Y (camera side)
        a = math.radians(20 + i * (320 / 13) + rnd.uniform(-6, 6))
        rr = rnd.uniform(26, 36)
        x, y = ox + math.sin(a) * rr, oy + math.cos(a) * rr
        T.tree(f"camp_tree{i}", (x, y, oz), s=rnd.uniform(1.1, 1.6), seed=seed + i)
    rock = mat("p3_rock", hexc("#8d8f93"), 0.8)
    for i in range(10):                                   # stone ring (no fire) the class sits around
        a = math.radians(i * 36)
        sphere(f"camp_stone{i}", 0.4, (ox + math.sin(a) * 1.6, oy + math.cos(a) * 1.6, oz + 0.15), rock, (1.2, 1.0, 0.6))
    wood = mat("p3_log", hexc("#7a5636"), 0.85)
    for i, (x, y, rz) in enumerate(((-13, 6, 20), (12, 8, -25), (2, 15, 90))):
        cyl(f"camp_log{i}", 0.7, 5.0, (ox + x, oy + y, oz + 0.7), wood, 16, rot=(0, 90, rz))
    sg = SG.sign("camp_sign", "CAMP BLOX", (ox - 16, oy + 17, oz + 5.0), w=6.0, h=1.6, bg="#7a5636", fg="#fff3d6", rot=15)
    cyl("camp_signpost", 0.2, 5.0, (ox - 16, oy + 17.3, oz + 2.5), wood, 8)
    return dict(center=(ox, oy, oz))
