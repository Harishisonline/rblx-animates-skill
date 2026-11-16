"""FLAT 2D MAP + ANIMATED ROUTE (REF1 gap: 'flat 2D map with animated route'). Paper-style top-down map built from
flat shapes + labels on the ground plane at `origin`; a route curve draws itself over time with a pin riding its head.
Shoot it from straight above (cam at origin + (0, 0, 60), lens 35) or a low tilted angle for drama.

    from rbx import townmap
    mp = townmap.town_map(origin=(0, 0, -200))                  # roads, blocks, park, river, labels (Blox Town layout)
    townmap.route("r1", mp, ["HOUSE", "SCHOOL", "PHARMACY"], t0=1.0, t1=4.0)     # draws the route, pin follows
    townmap.pin("p_house", mp, "HOUSE", color="#ff3b3b")       # static marker
Places are keys of mp["places"] (local 2D coords); add your own: mp["places"]["LAKE"] = (20, 30)."""
import math
import bpy
from mathutils import Vector
from .core import box, plane, cyl, sphere, empty, mat, hexc, F, D, collection
from .signs import label

PLACES = {"HOUSE": (-24, -16), "SCHOOL": (20, 18), "GYM": (30, 26), "PHARMACY": (18, -14), "MAIN ST": (0, -2),
          "PARK": (-22, 18), "TOWN HALL": (0, 30), "POLICE": (-6, -24)}


def _m(hx, r=0.9):
    return mat(f"map_{hx}", hexc(hx), r)


def town_map(origin=(0, 0, -200), w=80, h=70, coll=None, title="BLOX TOWN"):
    coll = coll or collection("townmap")
    o = Vector(origin)
    root = empty("map_root", tuple(o), coll=coll)
    box("map_paper", (w, h, 0.2), (0, 0, -0.1), _m("#efe6cf"), 0.0, parent=root, coll=coll)
    box("map_edge", (w + 2, h + 2, 0.15), (0, 0, -0.2), _m("#7a5a3a"), 0.0, parent=root, coll=coll)
    road = _m("#d8cbb0")
    for i, (x, y, rw, rh) in enumerate([(0, -2, w - 6, 3), (0, 10, w - 6, 2.2), (-12, 0, 2.2, h - 6), (12, 0, 3, h - 6),
                                        (0, -20, w - 6, 2.2)]):
        box(f"map_rd{i}", (rw, rh, 0.05), (x, y, 0.03), road, 0.0, parent=root, coll=coll)
    blocks = [(-24, -16, 14, 8, "#e9a87a"), (20, 18, 14, 10, "#9ab7d9"), (18, -14, 9, 6, "#a8d6a0"), (-22, 18, 14, 12, "#9fc77a"),
              (0, 30, 10, 6, "#d9c27a"), (-6, -26, 8, 5, "#8aa0c8"), (30, 26, 6, 6, "#9ab7d9"), (0, 4, 8, 4, "#e8c9a0"),
              (-30, 4, 10, 5, "#e0b8a0"), (30, 2, 8, 6, "#d8b0c0")]
    for i, (x, y, bw, bh, c) in enumerate(blocks):
        box(f"map_bk{i}", (bw, bh, 0.25), (x, y, 0.12), _m(c), 0.05, parent=root, coll=coll)
    box("map_river", (6, h - 4, 0.06), (-36, 0, 0.04), _m("#7fb0d8", 0.3), 0.0, parent=root, coll=coll)
    ink = "#3a2a1a"
    for k, (x, y) in PLACES.items():
        label(f"map_lb_{k}", k, (x, y - 1.5, 0.3), 1.6, ink, "bold", 0, root, coll, rot=(0, 0, 0))
    label("map_title", title, (0, h / 2 - 4, 0.3), 3.2, "#8a2be2", "bold", 0, root, coll, rot=(0, 0, 0))
    # compass
    box("map_cmp", (0.4, 5, 0.1), (w / 2 - 6, -h / 2 + 7, 0.3), _m(ink), 0, parent=root, coll=coll)
    label("map_N", "N", (w / 2 - 6, -h / 2 + 10.5, 0.3), 1.6, ink, "bold", 0, root, coll, rot=(0, 0, 0))
    return dict(root=root, coll=coll, places=dict(PLACES), origin=o)


def pin(name, mp, place, color="#ff3b3b", z=0.3, s=1.0):
    x, y = mp["places"][place] if isinstance(place, str) else place
    r = empty(name, (x, y, z), parent=mp["root"], coll=mp["coll"])
    m = mat(f"map_pin_{color}", hexc(color), 0.3, emit=hexc(color), estr=1.5)
    sphere(name + "_h", 1.0 * s, (0, 0, 2.6 * s), m, parent=r, coll=mp["coll"])
    cyl(name + "_s", 0.25 * s, 2.2 * s, (0, 0, 1.1 * s), m, 12, parent=r, coll=mp["coll"])
    return r


def route(name, mp, stops, t0=0.0, t1=3.0, color="#ff3b3b", width=0.6, pin_head=True, z=0.35):
    """Polyline route through stops (place keys or (x, y)); bevel_factor_end animates 0->1 over [t0, t1]."""
    pts = [mp["places"][s] if isinstance(s, str) else s for s in stops]
    # Manhattan-ish legs so it follows roads visually
    path = [pts[0]]
    for a, b in zip(pts, pts[1:]):
        path.append((b[0], a[1])); path.append(b)
    cu = D.curves.new(name, "CURVE"); cu.dimensions = "3D"
    sp = cu.splines.new("POLY"); sp.points.add(len(path) - 1)
    for i, (x, y) in enumerate(path):
        sp.points[i].co = (x, y, z, 1)
    cu.bevel_depth = width / 2; cu.bevel_resolution = 2; cu.use_fill_caps = True
    m = mat(f"map_route_{color}", hexc(color), 0.4, emit=hexc(color), estr=2.0)
    cu.materials.append(m)
    ob = D.objects.new(name, cu); mp["coll"].objects.link(ob); ob.parent = mp["root"]
    cu.bevel_factor_end = 0.0; cu.keyframe_insert("bevel_factor_end", frame=F(t0))
    cu.bevel_factor_end = 1.0; cu.keyframe_insert("bevel_factor_end", frame=F(t1))
    # start + end dots
    for i, (x, y) in ((0, pts[0]), (1, pts[-1])):
        cyl(f"{name}_dot{i}", 1.0, 0.2, (x, y, z), m, 24, parent=mp["root"], coll=mp["coll"])
    if pin_head:
        p = pin(name + "_pin", mp, path[0], color)
        # follow the path at constant speed
        L = [0.0]
        for a, b in zip(path, path[1:]):
            L.append(L[-1] + math.dist(a, b))
        tot = L[-1] or 1.0
        n = max(2, int((t1 - t0) * 10))
        for k in range(n + 1):
            d = tot * k / n
            j = max(i for i in range(len(L)) if L[i] <= d + 1e-6)
            j = min(j, len(path) - 2)
            f = (d - L[j]) / max(1e-6, L[j + 1] - L[j])
            x = path[j][0] + (path[j + 1][0] - path[j][0]) * f
            y = path[j][1] + (path[j + 1][1] - path[j][1]) * f
            p.location = (x, y, z); p.keyframe_insert("location", frame=F(t0 + (t1 - t0) * k / n))
    return ob
