"""Automatic shot QA (v3.9, 2026-11-15). See docs/CLEAN_ANIMATION.md section 7.
Shots DECLARE what must hold; render_lo.py calls qa.reset() before each build and qa.run(sc, log, shot) after it.
  qa.sit(ch)                          ch is seated (skip the floor check, check the seat instead)
  qa.air(ch)                          ch is allowed off the ground (jumps, cars, stage edge)
  qa.prop(ob, holder=None, arm="armR")  ob must not pass through any character (holder's gripping arm excluded)
  qa.touch(ch, arm, target, t0, t1, tol=0.35)   the fist stays on target
  qa.look(ch, target, t0, t1, tol=35)  the head points at target (Char, object or point)
Flags written to the log: FLOAT, CLIP, NOTOUCH, EYELINE (plus BLOCKED / AWAY from render_lo)."""
import math
import bpy, bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree

REG = {"sit": set(), "air": set(), "props": [], "touch": [], "look": [], "frame": [], "rest": []}


def reset():
    for k in ("sit", "air"):
        REG[k] = set()
    for k in ("props", "touch", "look", "frame", "rest"):
        REG[k] = []


def sit(ch): REG["sit"].add(ch.name); return ch
def air(ch): REG["air"].add(ch.name); return ch
def prop(ob, holder=None, arm="armR"): REG["props"].append((ob, holder.name if holder else None, arm)); return ob
def touch(ch, arm, target, t0, t1, tol=0.35): REG["touch"].append((ch, arm, target, t0, t1, tol))
def look(ch, target, t0, t1, tol=35): REG["look"].append((ch, target, t0, t1, tol))
def rest(ob, t0, t1, tol=0.12): REG["rest"].append((ob, t0, t1, tol))   # v4.1: an unheld prop must SIT on a surface
def frame(ch, t0, t1, shot="med"): REG["frame"].append((ch, t0, t1, shot))   # v4.1: subject must be IN the frame


def _pt(target):
    if hasattr(target, "head") and hasattr(target, "name") and not isinstance(target, bpy.types.Object):
        return target.head.matrix_world.translation.copy()
    if isinstance(target, bpy.types.Object):
        return target.matrix_world.translation.copy()
    return Vector(target)


def _chars(sc):
    out = []
    for o in sc.objects:
        if o.name.endswith("_head") and o.parent and o.parent.name.endswith("_neck"):
            out.append(o.name[:-5])
    return out


def _visible(o):
    return o.type == "MESH" and not o.hide_render and o.visible_get()


def _parts(sc, name):
    p = name + "_"
    return [o for o in sc.objects if o.name.startswith(p) and _visible(o)]


def _ground_z(sc, dg, x, y, z_from, skip_prefix):
    o = Vector((x, y, z_from)); d = Vector((0, 0, -1))
    for _ in range(8):
        hit, loc, n, i, ob, m = sc.ray_cast(dg, o, d, distance=40)
        if not hit:
            return None
        if not ob.name.startswith(skip_prefix) and _visible(ob):
            return loc.z
        o = loc + d * 0.01
    return None


def _bvh(ob, dg):
    bm = bmesh.new()
    bm.from_object(ob, dg)
    bm.transform(ob.matrix_world)
    t = BVHTree.FromBMesh(bm)
    bm.free()
    return t


def run(sc, log, shot, samples=5):
    dg = bpy.context.evaluated_depsgraph_get()
    f0, f1 = sc.frame_start, sc.frame_end
    frames = sorted(set(int(f0 + (f1 - f0) * k / (samples - 1)) for k in range(samples)))
    cam = sc.camera
    names = _chars(sc)
    flags = 0
    for f in frames:
        sc.frame_set(f); dg = bpy.context.evaluated_depsgraph_get()
        # FLOAT: feet on the surface (only characters the camera can see)
        from bpy_extras.object_utils import world_to_camera_view as w2c
        for nm in names:
            if nm in REG["air"]:
                continue
            legs = [o for o in _parts(sc, nm) if "leg" in o.name.lower() or "shoe" in o.name.lower()]
            if not legs:
                continue
            vs = [o.matrix_world @ Vector(c) for o in legs for c in o.bound_box]
            low = min(vs, key=lambda v: v.z)
            v = w2c(sc, cam, low)
            if not (0 <= v.x <= 1 and 0 <= v.y <= 1 and v.z > 0):
                continue                                     # feet out of frame: nobody sees it
            gz = _ground_z(sc, dg, low.x, low.y, low.z + 0.3, nm + "_")
            if gz is None:
                continue
            gap = low.z - gz
            if nm in REG["sit"]:
                continue
            if gap > 0.15 or gap < -0.2:
                log.write(f"FLOAT shot {shot:02d} frame {f} {nm} feet {gap:+.2f} from surface\n"); flags += 1
        # HALF (v4.1): any character whose head is PARTLY in frame and big enough to matter = sliced by the edge
        for nm in names:
            hd = bpy.data.objects.get(nm + "_head")
            if hd is None or not _visible(hd):
                continue
            cs = [w2c(sc, cam, hd.matrix_world @ Vector(c)) for c in hd.bound_box]
            if any(v.z <= 0 for v in cs):
                continue
            inside = [0.0 <= v.x <= 1.0 and 0.0 <= v.y <= 1.0 for v in cs]
            hh = max(v.y for v in cs) - min(v.y for v in cs)
            if any(inside) and not all(inside) and hh > 0.07:
                log.write(f"HALF shot {shot:02d} frame {f} {nm} head sliced by the frame edge\n"); flags += 1
        # CLIP: props through bodies
        for ob, holder, arm in REG["props"]:
            if not _visible(ob):
                continue
            pieces = [ob] + [c for c in ob.children_recursive if _visible(c)]
            pt = [_bvh(p, dg) for p in pieces if p.type == "MESH"]
            for nm in names:
                for part in _parts(sc, nm):
                    low = part.name.lower()
                    if holder == nm and (arm[-1].lower() in low[-2:].lower() or "fist" in low or arm.lower() in low
                                         or ("elbow" + arm[-1]).lower() in low):
                        continue
                    tb = _bvh(part, dg)
                    if any(t.overlap(tb) for t in pt):
                        log.write(f"CLIP shot {shot:02d} frame {f} {ob.name} through {part.name}\n"); flags += 1
                        break
        # NOTOUCH
        from . import motion as mo
        for ch, arm, target, t0, t1, tol in REG["touch"]:
            if not (int(t0 * 30) <= f <= int(t1 * 30)):
                continue
            hd = mo.hand(ch, arm); bpy.context.view_layer.update()
            d = (hd.matrix_world.translation - _pt(target)).length
            if d > tol:
                log.write(f"NOTOUCH shot {shot:02d} frame {f} {ch.name} {arm} {d:.2f} from target\n"); flags += 1
        # CUTOFF / TINY (v4.1): declared subjects must have the whole head + body down to the shot size inside the frame
        from bpy_extras.object_utils import world_to_camera_view as _w2c
        for ch, t0, t1, shot_kind in REG["frame"]:
            if not (int(t0 * 30) <= f <= int(t1 * 30)):
                continue
            hd = ch.head
            cs = [_w2c(sc, cam, hd.matrix_world @ Vector(c)) for c in hd.bound_box]
            if any(not (0.0 <= v.x <= 1.0 and 0.0 <= v.y <= 1.0) or v.z <= 0 for v in cs):
                log.write(f"CUTOFF shot {shot:02d} frame {f} {ch.name} head out of frame ({shot_kind})\n"); flags += 1
                continue
            hh = max(v.y for v in cs) - min(v.y for v in cs)
            if shot_kind in ("mcu", "med") and hh < 0.06:
                log.write(f"TINY shot {shot:02d} frame {f} {ch.name} head {hh:.2f} of frame height in a {shot_kind}\n"); flags += 1
            if shot_kind in ("med", "cowboy", "full"):
                body = [o for o in sc.objects if o.name.startswith(ch.name + "_") and _visible(o) and "torso" in o.name.lower()]
                for o in body[:1]:
                    vs = [_w2c(sc, cam, o.matrix_world @ Vector(c)) for c in o.bound_box]
                    if any(not (-0.02 <= v.x <= 1.02) for v in vs):
                        log.write(f"CUTOFF shot {shot:02d} frame {f} {ch.name} torso cut by the frame edge ({shot_kind})\n"); flags += 1
        # PROPFLOAT (v4.1): declared resting props must touch the surface under them (no levitating objects)
        for ob, t0, t1, tol in REG["rest"]:
            if not (int(t0 * 30) <= f <= int(t1 * 30)) or not _visible(ob):
                continue
            parts = [ob] + [c for c in ob.children_recursive if _visible(c)]
            vs = [p.matrix_world @ Vector(c) for p in parts if p.type == "MESH" for c in p.bound_box]
            if not vs:
                continue
            low = min(vs, key=lambda v: v.z)
            cx = sum(v.x for v in vs) / len(vs); cy = sum(v.y for v in vs) / len(vs)
            gz = _ground_z(sc, dg, cx, cy, low.z + 0.05, ob.name)
            if gz is not None and low.z - gz > tol:
                log.write(f"PROPFLOAT shot {shot:02d} frame {f} {ob.name} {low.z - gz:+.2f} above the surface\n"); flags += 1
        # EYELINE
        for ch, target, t0, t1, tol in REG["look"]:
            if not (int(t0 * 30) <= f <= int(t1 * 30)):
                continue
            hp = ch.head.matrix_world.translation
            fw = ch.head.matrix_world.to_quaternion() @ Vector((0, -1, 0))
            to = (_pt(target) - hp)
            if to.length < 1e-3:
                continue
            ang = math.degrees(fw.angle(to.normalized()))
            if ang > tol:
                log.write(f"EYELINE shot {shot:02d} frame {f} {ch.name} {ang:.0f} deg off target\n"); flags += 1
    return flags
