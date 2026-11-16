"""INSTANCED CROWDS of simple Roblox-style extras (R6 blocks, ink faces, varied shirts/pants/skin/hair/hats).
Extras are NOT rigged: each variant is built once into a hidden source collection and placed as collection instances,
so 1,000-2,000 extras cost almost nothing in EEVEE. Use cast.py rigs for anyone who acts; extras are set dressing.

    from rbx import crowd
    crowd.crowd("plaza", center=(0, 30, 0), size=(60, 40), n=400, face=(0, 0, 0), seed=2)    # scatter, all look at face
    crowd.crowd("stands", center=(0, 0, 0), size=(80, 30), n=1500, mode="grid", spacing=2.6)  # stadium/festival block
    crowd.line("queue", p0, p1, n=12)                                                        # queue / sidewalk walkers
    crowd.extra("cop1", loc, rot, variant="police")                                          # one specific extra
    crowd.numbers(obs, values)  -> floating 3-digit badges above extras (white/amber/red), number_lies rule visual
Variants: crowd.VARIANTS keys (civilians c0..c11, 'police', 'doctor', 'student_a', 'student_b').
Scale: an extra is 5.3 units tall like the cast. Pass scale=0.95..1.05 jitter automatically."""
import math, random
import bpy
from mathutils import Vector
from .core import box, sphere, cyl, empty, mat, hexc, collection, instance, hide_coll_from_layer, D

SKIN = ["#f5cfa0", "#e0ac7c", "#c68a5a", "#8d5a3a", "#5c3a24", "#ffd9b8"]
SHIRT = ["#d9453a", "#2f7bff", "#f2c14e", "#2f8a55", "#ffffff", "#1d1d24", "#8a2be2", "#ff7a1f", "#19c2b0", "#c0182f",
         "#7b8794", "#f28cb8"]
PANTS = ["#2b2f3a", "#3b4f7a", "#1d1d24", "#6b5a44", "#4a4a4a", "#2f3f5f"]
HAIR = ["#2a1a10", "#5a3a20", "#d9b46a", "#111111", "#a33a1a", "#7a7a7a"]
VARIANTS = {}
for i in range(12):
    r = random.Random(100 + i)
    VARIANTS[f"c{i}"] = dict(skin=r.choice(SKIN), shirt=SHIRT[i], pants=r.choice(PANTS), hair=r.choice(HAIR),
                             hat=(r.random() < 0.3), hat_col=r.choice(SHIRT), hood=(r.random() < 0.25))
LIGHT = ["#ffffff", "#ffe08a", "#9ed8ff", "#ffb3c8", "#b8f0c0", "#ffcf9a", "#d8c8ff", "#f2c14e", "#ff7a6a", "#7ae0d0",
         "#c8e070", "#f4f0e4"]
for i in range(12):   # light palette: reads as individuals from aerials (pale tops, darker pants contrast)
    r = random.Random(300 + i)
    VARIANTS[f"l{i}"] = dict(skin=r.choice(SKIN), shirt=LIGHT[i], pants=r.choice(PANTS), hair=r.choice(HAIR),
                             hat=(r.random() < 0.35), hat_col=r.choice(SHIRT), hood=(r.random() < 0.2),
                             backpack=r.choice([None, None, "#d9453a", "#2f7bff", "#2f8a55"]))
VARIANTS["police"] = dict(skin="#e0ac7c", shirt="#1f2f5a", pants="#141a2e", hair="#2a1a10", hat=True, hat_col="#141a2e",
                          badge=True)
VARIANTS["doctor"] = dict(skin="#f5cfa0", shirt="#f4f6f8", pants="#3b4f7a", hair="#5a3a20", hat=False)
VARIANTS["student_a"] = dict(skin="#c68a5a", shirt="#2f7bff", pants="#2b2f3a", hair="#111111", backpack="#d9453a")
VARIANTS["student_b"] = dict(skin="#ffd9b8", shirt="#f2c14e", pants="#3b4f7a", hair="#a33a1a", backpack="#2f8a55")

_SRC = {}


def _m(hx, r=0.55):
    return mat(f"cr_{hx}", hexc(hx), r)


POSES = {  # (left arm pitch, right arm pitch, body lean fwd, head yaw, left arm out, right arm out)
    "stand": (0, 0, 0, 0, 0, 0), "hips": (0, 0, 0, 0, 28, 28), "phone": (0, -70, 3, 0, 0, -10), "point": (0, -85, 0, 15, 0, 0),
    "chat": (-25, 10, 2, 25, 0, 0), "wave": (0, -160, 0, -10, 0, 20), "cross": (-40, -40, 0, 0, -18, 18), "walk": (22, -22, 4, 0, 0, 0),
    "lookup": (6, 6, -6, 0, 6, 6), "pocket": (8, 8, 0, -20, 8, 8)}


def _build(name, v, coll, root=None, pose="stand"):
    """Builds one extra under `root` (feet at z=0, facing -Y)."""
    ink = _m("#111111", 0.4)
    if not isinstance(pose, str):
        pose = "stand"
    al, ar, lean, hy, ol, orr = POSES[pose]
    body = empty(name + "_body", (0, 0, 2.0), parent=root, coll=coll, rot=(-lean, 0, 0))
    head = empty(name + "_head", (0, 0, 2.0), parent=body, coll=coll, rot=(0, 0, hy))
    torso_m = _m(v["shirt"]); pants_m = _m(v["pants"]); skin_m = _m(v["skin"])
    box(name + "_to", (2, 1, 2), (0, 0, 1.0), torso_m, 0.09, parent=body, coll=coll)
    for s in (-1, 1):
        pitch = al if s < 0 else ar
        out = (ol if s < 0 else orr) * s
        sh = empty(f"{name}_sh{s}", (s * 1.5, 0, 1.9), parent=body, coll=coll, rot=(pitch, out, 0))
        box(f"{name}_ar{s}", (1, 1, 2), (0, 0, -0.9), torso_m, 0.09, parent=sh, coll=coll,
            mats=[(-0.45, skin_m), (9, torso_m)], cuts_z=[-0.45])
        lp = 14 * s if pose == "walk" else 0
        hp = empty(f"{name}_hp{s}", (s * 0.5, 0, 2.0), parent=root, coll=coll, rot=(lp, 0, 0))
        box(f"{name}_lg{s}", (0.98, 1, 2), (0, 0, -1.0), pants_m, 0.09, parent=hp, coll=coll)
    box(name + "_hd", (1.2, 1.2, 1.2), (0, 0, 0.62), skin_m, 0.3, parent=head, coll=coll)
    for s in (-1, 1):
        box(f"{name}_ey{s}", (0.12, 0.04, 0.2), (s * 0.22, -0.6, 0.72), ink, 0.04, parent=head, coll=coll)
    box(name + "_mo", (0.34, 0.04, 0.06), (0, -0.6, 0.42), ink, 0.02, parent=head, coll=coll)
    hm = _m(v["hair"], 0.7)
    box(name + "_hr", (1.3, 1.3, 0.4), (0, 0.04, 1.20), hm, 0.15, parent=head, coll=coll)
    box(name + "_hb", (1.3, 0.35, 0.9), (0, 0.5, 0.85), hm, 0.12, parent=head, coll=coll)
    if v.get("hat"):
        hc = _m(v.get("hat_col", "#333333"))
        box(name + "_ht", (1.36, 1.36, 0.42), (0, 0, 1.38), hc, 0.1, parent=head, coll=coll)
        box(name + "_hv", (1.1, 0.6, 0.08), (0, -0.85, 1.20), hc, 0.03, parent=head, coll=coll)
    if v.get("badge"):
        gold = mat("cr_gold", hexc("#d9a520"), 0.3, 0.8)
        box(name + "_bg", (0.3, 0.06, 0.36), (0.5, -0.52, 1.5), gold, 0.03, parent=body, coll=coll)
        box(name + "_belt", (2.04, 1.04, 0.2), (0, 0, 0.05), _m("#111111", 0.3), 0.03, parent=body, coll=coll)
    if v.get("hood"):
        box(name + "_hood", (1.6, 0.5, 0.5), (0, 0.45, 0.15), torso_m, 0.2, parent=head, coll=coll)
    if v.get("backpack"):
        box(name + "_bp", (1.6, 0.7, 1.7), (0, 0.85, 1.0), _m(v["backpack"]), 0.14, parent=body, coll=coll)


def source(variant, pose="stand"):
    """Hidden source collection for one variant (built once)."""
    k = (variant, str(pose))
    if k in _SRC:
        try:
            if _SRC[k].name in D.collections:
                return _SRC[k]
        except ReferenceError:
            pass
    c = collection(f"crowdsrc_{variant}_{pose}")
    _build(f"cx_{variant}_{pose}", VARIANTS[variant], c, None, pose)
    hide_coll_from_layer(c)
    _SRC[k] = c
    return c


def extra(name, loc, rot=0.0, variant="c0", coll=None, scale=1.0, pose="stand"):
    """One instanced extra. rot = yaw degrees (0 faces -Y)."""
    return instance(name, source(variant, pose), loc, (scale,) * 3, coll, (0, 0, rot))


def _yaw_to(p, face):
    d = Vector(face) - Vector(p)
    return math.degrees(math.atan2(d.x, -d.y)) if d.length > 0.01 else 0.0


def crowd(name, center=(0, 0, 0), size=(40, 30), n=200, mode="scatter", spacing=2.8, face=None, seed=0,
          variants=None, coll=None, min_gap=2.3, avoid=(), yaw_jitter=25.0,
          poses=("stand", "stand", "hips", "phone", "chat", "pocket", "cross", "lookup", "point", "walk"), palette="mixed"):
    """Scatter / grid / clusters of instanced extras. face: point everyone looks toward (else random). avoid: [(x, y, r)].
    mode="clusters": groups of 2-6 (chatting circles, facing each other or `face`) with open floor between groups plus a few
    walkers in lanes - reads as a crowd of people from aerials instead of a carpet. palette: mixed | light (pale tops)."""
    rnd = random.Random(seed)
    pre = "l" if palette == "light" else "c"
    vs = variants or [k for k in VARIANTS if k[0] == pre and k[1:].isdigit()]
    if mode == "clusters":
        return _clusters(name, center, size, n, face, rnd, vs, coll or collection("crowd_" + name), avoid)
    coll = coll or collection("crowd_" + name)
    pts = []
    cx, cy, cz = center
    if mode == "grid":
        nx = max(1, int(size[0] / spacing)); ny = max(1, int(size[1] / spacing))
        for j in range(ny):
            for i in range(nx):
                if len(pts) >= n:
                    break
                pts.append((cx - size[0] / 2 + (i + 0.5) * spacing + rnd.uniform(-0.3, 0.3),
                            cy - size[1] / 2 + (j + 0.5) * spacing + rnd.uniform(-0.3, 0.3)))
    else:
        tries = 0
        while len(pts) < n and tries < n * 30:
            tries += 1
            p = (cx + rnd.uniform(-size[0] / 2, size[0] / 2), cy + rnd.uniform(-size[1] / 2, size[1] / 2))
            if any((p[0] - a) ** 2 + (p[1] - b) ** 2 < r * r for a, b, r in avoid):
                continue
            if n <= 600 and any((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 < min_gap ** 2 for q in pts):
                continue
            pts.append(p)
    obs = []
    for i, (x, y) in enumerate(pts):
        yaw = _yaw_to((x, y, 0), face) if face else rnd.uniform(-180, 180)
        yaw += rnd.uniform(-yaw_jitter, yaw_jitter)
        pose = rnd.choice(poses)
        obs.append(extra(f"{name}_{i:04d}", (x, y, cz), yaw, rnd.choice(vs), coll, rnd.uniform(0.95, 1.05), pose))
    return obs


def _clusters(name, center, size, n, face, rnd, vs, coll, avoid):
    cx, cy, cz = center
    obs, cents = [], []
    i = 0
    tries = 0
    while i < n and tries < 4000:
        tries += 1
        g = rnd.choice((2, 3, 3, 4, 4, 5, 6))
        p = (cx + rnd.uniform(-size[0] / 2, size[0] / 2), cy + rnd.uniform(-size[1] / 2, size[1] / 2))
        rad = 1.3 + 0.35 * g
        if any((p[0] - a) ** 2 + (p[1] - b) ** 2 < (r + rad) ** 2 for a, b, r in avoid):
            continue
        if any((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 < (rad + qr + 2.2) ** 2 for q, qr in cents):
            continue
        cents.append((p, rad))
        walker = rnd.random() < 0.2
        a0 = rnd.uniform(0, 6.28)
        for k in range(min(g, n - i)):
            if walker:   # a small group walking in a lane toward/away from the screen
                pos = (p[0] + (k % 2) * 1.6 - 0.8, p[1] + (k // 2) * 2.0)
                yaw = 180 if rnd.random() < 0.5 else 0
                pose = "walk"
            else:
                a = a0 + k * 6.283 / g
                pos = (p[0] + math.cos(a) * rad * 0.75, p[1] + math.sin(a) * rad * 0.75)
                yaw = _yaw_to((*pos, 0), (p[0], p[1], 0)) if (not face or rnd.random() < 0.55) else _yaw_to((*pos, 0), face)
                pose = rnd.choice(("chat", "chat", "stand", "phone", "hips", "pocket", "point", "lookup", "wave"))
            obs.append(extra(f"{name}_{i:04d}", (pos[0], pos[1], cz), yaw + rnd.uniform(-12, 12), rnd.choice(vs), coll,
                             rnd.uniform(0.93, 1.05), pose))
            i += 1
    return obs


def line(name, p0, p1, n=8, variants=None, seed=0, coll=None, face=None):
    rnd = random.Random(seed)
    vs = variants or [k for k in VARIANTS if k.startswith("c")]
    a, b = Vector(p0), Vector(p1)
    d = b - a
    yaw = math.degrees(math.atan2(d.x, -d.y)) + 180
    out = []
    for i in range(n):
        p = a + d * (i / max(1, n - 1))
        y = _yaw_to(p, face) if face else yaw
        out.append(extra(f"{name}_{i:03d}", tuple(p), y + rnd.uniform(-10, 10), rnd.choice(vs), coll))
    return out


def numbers(obs, values=None, seed=0, z=6.3, size=0.55, coll=None, badge=False, tilt=0.0, every=1):
    """Floating number badges over extras (white < 40 <= amber < 90 <= red). values: list or None (random).
    badge=True puts a dark rounded plate behind the digits (reads over a busy plaza); tilt (deg) leans the badge back so
    it faces a high camera (aerials: 35-50); every=N labels only every Nth extra (less clutter)."""
    from .signs import label
    rnd = random.Random(seed)
    out = []
    for i, ob in enumerate(obs):
        v = values[i] if values else rnd.choice([rnd.randint(0, 39)] * 3 + [rnd.randint(40, 89)] * 2 + [rnd.randint(90, 140)])
        col = "#ff3b3b" if v >= 90 else ("#ffb020" if v >= 40 else "#ffffff")
        if i % every:
            continue
        loc = (ob.location.x, ob.location.y, ob.location.z + z)
        t = label(f"{ob.name}_num", f"{v:03d}", loc, size, col, "bold", 4.0, coll=coll, rot=(90 - tilt, 0, 0))
        if badge:
            pl = box(f"{ob.name}_nbg", (size * 2.5, 0.06, size * 1.25), (loc[0], loc[1] + 0.06, loc[2]),
                     mat("cr_badge", hexc("#14161c"), 0.5), min(0.2, size * 0.3), rot=(-tilt, 0, 0), coll=coll)
            out.append(pl)
        out.append(t)
    return out
