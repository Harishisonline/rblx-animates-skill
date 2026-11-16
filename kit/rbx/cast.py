"""PERMANENT CAST of @rblxanimates ("Blox Town") - v3 "finished" designs (2026-11-13, per docs/REF2_CHARACTERS_WORLD.md).
See docs/CAST.md for the bible (personality, catchphrases, palettes, relationships). Designs are locked once approved.

Every function returns a rigged chars.Char (pose/walk/act/face/look/jump/talk work) with blinks + breathing idle:

    from rbx import cast
    n = cast.host(t0, t1, "happy", loc=(0, 0, 0), rot=0)       # Harry, the narrator
    m = cast.mayor(t0, t1); b = cast.bestie(t0, t1); c = cast.crush(t0, t1)
    mo = cast.mom(t0, t1); d = cast.dad(t0, t1); gp = cast.grandpa(t0, t1); gm = cast.grandma(t0, t1)
    cast.ALL  -> {"host": host, ...}   cast.make("dad", t0, t1, ...)

Common kwargs: expr, loc, rot, scale, rim (soft NEUTRAL cool rim light, never a signature colour), prop (False hides the
hand prop), live (blink + breathe). Extra parts on the Char: ch.prop (hand prop root), ch.sig (signature hex colour),
ch.hair (main hair mesh), ch.hair_long (Luna's long hair on the sway rig). round_head is accepted for old callers (ignored:
every v3 character uses the same bevelled cube head).

v3 construction (REF2 bible): strict R6 blocks, bevelled cube head (1.2 x 1.14 x 1.14, bevel 0.22), flat ink-decal faces
(atlases v3_<role>_eyes/mouth.png from tools/make_cast_v3_faces.py), HAIR = closed scalp shell + 5-14 petal clumps fused by a
voxel remesh + smooth into one molded mass (applied at build time, so render cost is a plain static mesh), one hair material
with AO root darkening + one broad shine band, modelled 3D accessories, restrained trims, no emissive/neon parts.
Motion polish helpers: squash(ch,t,amt), hop(ch,t,...), walk2(ch,...), react(ch,t,gesture,expr)."""
import math
import bpy
import bmesh
from mathutils import Vector
from .core import box, cyl, sphere, text, empty, poly_extrude, light, hexc, mat, F, set_interp, noise, D, fcurves
from . import chars, acting  # noqa: F401  (acting patches Char)

PALETTE = {   # signature colour per role (costume only; used for labels/graphics, never for lights)
    "host": "#7a1f2b", "mayor": "#c9a043", "bestie": "#1f2f5c", "crush": "#5e0f1c",
    "mom": "#2a9d8f", "dad": "#b0302a", "grandpa": "#2f6b4a", "grandma": "#a58fd0",
}
RIM = "#cfe2ff"   # neutral cool rim for everybody
HEAD_W, HEAD_H, HEAD_D, HEAD_BEV = 1.2, 1.14, 1.14, 0.22
HT = HEAD_H / 2          # head top (head-local z)
HF = -HEAD_D / 2         # head front (head-local y)

for _k, _v in dict(sad=("worried", "frown"), smirk=("normal", "smirk"), exasperated=("squint", "frown"),
                   grumpy=("angry", "frown"), deadpan=("half", "flat"), shocked=("wide", "talk_wide"),
                   pout=("normal", "flat"), shy=("side_l", "wavy"), surprised=("wide", "o"),
                   beam=("happy", "open_smile")).items():
    acting.EXPR.setdefault(_k, _v)

# v3.7 natural faces (docs/research/REF_IG_Dfs43n3oWqx.md FACIAL EXPRESSION SPEC) - UNRENDERED, data only.
# Hard decal swaps on beats; ch.ladder(t, "surprise_laugh") / ch.dart(t0, t1) / blinks every 2.5-4 s (acting.blink).
# Narrator-POV character during VO: one mouth per beat, never talk(). Until the v3 atlases are regenerated as 5x5
# (tools/make_cast_v3_faces.py + assets/faces/v3_<role>_eyes.json {"grid": 5}) the new cells fall back to 4x4 ones.
for _k, _v in dict(tear=("tear1", "flat"), erased=("dots", "dash"), dart=("worried", "frown_wobble")).items():
    acting.EXPR.setdefault(_k, _v)
ladder, dart, blink_schedule = acting.ladder, acting.dart, acting.blink_schedule
FACE_SET = {   # expression set per format (mirrors docs/FORMATS.json "expressions")
    "in_this_world": ["neutral", "worried", "worried_dart", "pop_shock", "sad_tear", "smug_up", "blank", "content"],
    "horror": ["worried", "worried_dart", "pop_shock", "terror", "scream", "sad_tear", "blank"],
    "comedy": ["content", "smug_up", "grin", "joy", "blank", "pop_shock", "sus"],
}


# =================================================================== materials
def _m(name, hx, rough=0.6, metal=0.0, **kw):
    return mat("cast_" + name, hexc(hx), rough, metal, **kw)


def _hair_mat(name, hx, shine=0.14, band=(0.35, 0.62), streaks=None, temples=None, grey="#9c9ca3"):
    """REF2 §4.6-7: flat base, AO-driven root darkening, one broad soft shine band (object-space Z), coat + sheen.
    streaks: list of object-space x positions of grey streaks; temples: |x| above which the hair turns grey."""
    key = "cast_hair_" + name
    if key in D.materials:
        return D.materials[key]
    m = D.materials.new(key); m.use_nodes = True
    nt = m.node_tree; N, L = nt.nodes, nt.links
    b = next(n for n in N if n.type == "BSDF_PRINCIPLED")
    for k, v in (("Roughness", 0.4), ("Specular IOR Level", 0.5), ("Coat Weight", 0.15), ("Coat Roughness", 0.3),
                 ("Sheen Weight", 0.2), ("Sheen Roughness", 0.4)):
        try:
            b.inputs[k].default_value = v
        except KeyError:
            pass
    base = hexc(hx)

    def MR(src, a, b_, interp="SMOOTHSTEP"):
        n = N.new("ShaderNodeMapRange"); n.interpolation_type = interp
        n.inputs["From Min"].default_value = a; n.inputs["From Max"].default_value = b_
        L.new(src, n.inputs["Value"]); return n.outputs[0]

    def MATH(op, a, b_=None):
        n = N.new("ShaderNodeMath"); n.operation = op
        (L.new(a, n.inputs[0]) if not isinstance(a, float) else setattr(n.inputs[0], "default_value", a))
        if b_ is not None:
            (L.new(b_, n.inputs[1]) if not isinstance(b_, float) else setattr(n.inputs[1], "default_value", b_))
        return n.outputs[0]

    def MIX(fac, c1, c2, blend="MIX"):
        n = N.new("ShaderNodeMix"); n.data_type = "RGBA"; n.blend_type = blend
        (L.new(fac, n.inputs[0]) if not isinstance(fac, float) else setattr(n.inputs[0], "default_value", fac))
        for i, c in ((6, c1), (7, c2)):
            (L.new(c, n.inputs[i]) if not isinstance(c, tuple) else setattr(n.inputs[i], "default_value", (*c[:3], 1)))
        return n.outputs[2]

    tc = N.new("ShaderNodeTexCoord"); sep = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Object"], sep.inputs[0])
    col = base
    cur = None
    if temples is not None or streaks:
        gmask = None
        if temples is not None:
            gmask = MR(MATH("ABSOLUTE", sep.outputs["X"]), temples, temples + 0.06)
        for xs in streaks or ():
            s = MATH("SUBTRACT", 1.0, MR(MATH("ABSOLUTE", MATH("SUBTRACT", sep.outputs["X"], float(xs))), 0.018, 0.042))
            s = MATH("MULTIPLY", s, MR(sep.outputs["Z"], 0.25, 0.4))      # streaks only on the top/back
            gmask = s if gmask is None else MATH("MAXIMUM", gmask, s)
        cur = MIX(gmask, base, hexc(grey))
    # shine band on Z (head-local, because the hair object sits at the head origin)
    bnd = MATH("SUBTRACT", MR(sep.outputs["Z"], band[0] - 0.12, band[0]), MR(sep.outputs["Z"], band[1], band[1] + 0.14))
    lite = tuple(min(1.0, c * 1.9 + 0.012) for c in base)
    cur = MIX(MATH("MULTIPLY", bnd, shine), cur if cur is not None else col, lite)
    # AO root darkening
    ao = N.new("ShaderNodeAmbientOcclusion"); ao.inputs["Distance"].default_value = 0.22; ao.samples = 8
    dark = MR(ao.outputs["AO"], 0.2, 0.95)
    darkc = MIX(dark, tuple(c * 0.45 for c in base), (1, 1, 1))
    cur = MIX(1.0, cur, darkc, "MULTIPLY")
    L.new(cur, b.inputs["Base Color"])
    m.diffuse_color = (*base, 1)
    return m


def _plaid(name, red, dark, black, scale=3.2):
    """Buffalo plaid: two perpendicular square-wave stripe sets (object space X and Z); red / dark red where one stripe
    crosses / black where both cross, plus a faint twill line. Object-space so it tiles per part like printed fabric."""
    key = "cast_plaid_" + name
    if key in D.materials:
        return D.materials[key]
    m = D.materials.new(key); m.use_nodes = True
    nt = m.node_tree; N, L = nt.nodes, nt.links
    b = next(n for n in N if n.type == "BSDF_PRINCIPLED"); b.inputs["Roughness"].default_value = 0.78
    tc = N.new("ShaderNodeTexCoord"); sep = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Object"], sep.inputs[0])

    def stripe(sock):
        a = N.new("ShaderNodeMath"); a.operation = "MULTIPLY"; a.inputs[1].default_value = scale; L.new(sock, a.inputs[0])
        f = N.new("ShaderNodeMath"); f.operation = "FRACT"; L.new(a.outputs[0], f.inputs[0])
        lt = N.new("ShaderNodeMath"); lt.operation = "LESS_THAN"; lt.inputs[1].default_value = 0.5; L.new(f.outputs[0], lt.inputs[0])
        return lt.outputs[0]
    sx, sz = stripe(sep.outputs["X"]), stripe(sep.outputs["Z"])
    sy = stripe(sep.outputs["Y"])
    one = N.new("ShaderNodeMath"); one.operation = "MAXIMUM"; L.new(sx, one.inputs[0]); L.new(sz, one.inputs[1])
    both = N.new("ShaderNodeMath"); both.operation = "MULTIPLY"; L.new(sx, both.inputs[0]); L.new(sz, both.inputs[1])
    both2 = N.new("ShaderNodeMath"); both2.operation = "MULTIPLY"; L.new(sy, both2.inputs[0]); L.new(sz, both2.inputs[1])
    bb = N.new("ShaderNodeMath"); bb.operation = "MAXIMUM"; L.new(both.outputs[0], bb.inputs[0]); L.new(both2.outputs[0], bb.inputs[1])
    m1 = N.new("ShaderNodeMix"); m1.data_type = "RGBA"; L.new(one.outputs[0], m1.inputs[0])
    m1.inputs[6].default_value = (*hexc(red), 1); m1.inputs[7].default_value = (*hexc(dark), 1)
    m2 = N.new("ShaderNodeMix"); m2.data_type = "RGBA"; L.new(bb.outputs[0], m2.inputs[0]); L.new(m1.outputs[2], m2.inputs[6])
    m2.inputs[7].default_value = (*hexc(black), 1)
    L.new(m2.outputs[2], b.inputs["Base Color"])
    m.diffuse_color = (*hexc(red), 1)
    return m


# =================================================================== geometry helpers
def _H(ch, nm, size, loc, M, bev=0.06, rot=(0, 0, 0)):
    """Box parented to the head (head-local: centre of head, front = -Y, top of head z = HT)."""
    return box(f"{ch.name}_{nm}", size, loc, M, bev, rot=rot, parent=ch.head, coll=ch.coll)


def _B(ch, nm, size, loc, M, bev=0.05, rot=(0, 0, 0)):
    """Box parented to the hip (torso spans z 0..2, front surface y=-0.5)."""
    return box(f"{ch.name}_{nm}", size, loc, M, bev, rot=rot, parent=ch.hip, coll=ch.coll)


def _A(ch, arm, nm, size, loc, M, bev=0.06):
    return box(f"{ch.name}_{nm}_{arm}", size, loc, M, bev, parent=ch.piv(arm), coll=ch.coll)


def hand(ch, arm="armR"):
    """Public, cached fist empty of an arm (prop parent; ~1.55 below the shoulder pivot). Same object on every call."""
    cache = ch.__dict__.setdefault("_hands", {})
    if arm not in cache:
        j = getattr(ch, "joints", {}).get("elbow" + arm[-1])
        cache[arm] = (empty(f"{ch.name}_hand_{arm}", (0, -0.1, -0.8), j, ch.coll) if j is not None else
                      empty(f"{ch.name}_hand_{arm}", (0, -0.1, -1.55), ch.piv(arm), ch.coll))
    return cache[arm]


_hand = hand


def _cube_head(ch, sx=1.0):
    """Swap the stock cylinder head for the v3 bevelled cube (keeps the object, its face material, parenting, rig)."""
    h = ch.head
    for md in list(h.modifiers):
        h.modifiers.remove(md)
    me = D.meshes.new(ch.name + "_head3")
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector((HEAD_W * sx, HEAD_D, HEAD_H)), verts=bm.verts)
    bm.to_mesh(me); bm.free()
    for m in h.data.materials:
        me.materials.append(m)
    old = h.data; h.data = me
    if old.users == 0:
        D.meshes.remove(old)
    h.location = (0, 0, HT + 0.01)
    h.scale = (1, 1, 1)
    md = h.modifiers.new("Bevel", "BEVEL"); md.width = HEAD_BEV; md.segments = 5; md.limit_method = "ANGLE"
    md.harden_normals = True
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))


def _ring_frame(T, up):
    T = T.normalized()
    B = T.cross(up)
    if B.length < 1e-4:
        B = T.cross(Vector((1, 0, 0)))
    B.normalize()
    Nn = B.cross(T).normalized()
    return B, Nn


class Hair:
    """Builds one molded hair mass: closed scalp shell + petal clumps + balls, voxel-remeshed + smoothed (REF2 §4)."""

    def __init__(self):
        self.bm = bmesh.new()
        self.tips = []          # (tip point, direction) for the post-remesh hard-tip pinch

    def shell(self, c, r, front_z=None, side_z=None, back_z=None, seg=40, inset=0.42, box_q=0.55):
        """Closed boxy ellipsoid (superellipse, box_q<1 = boxier, hugs the cube head); vertices below the hairline are pulled inside the head so only the haircut shows.
        front_z: hairline on the face side, side_z at the ears, back_z at the nape (head-local z)."""
        g = bmesh.ops.create_uvsphere(self.bm, u_segments=seg, v_segments=seg // 2, radius=1.0)
        for v in g["verts"]:
            q = [math.copysign(abs(a) ** box_q, a) for a in v.co]
            p = Vector((q[0] * r[0] + c[0], q[1] * r[1] + c[1], q[2] * r[2] + c[2]))
            fy = max(0.0, -v.co.y)            # 1 = front, 0 = sides/back
            by = max(0.0, v.co.y)
            if front_z is not None:
                hl = (front_z * fy + (side_z if side_z is not None else front_z) * (1 - fy) * (1 - by)
                      + (back_z if back_z is not None else front_z) * by)
                k = max(0.0, min(1.0, (hl - p.z) / 0.18))      # smooth tuck over 0.18 below the hairline
                k = k * k * (3 - 2 * k)
                if k > 0:
                    cx_ = max(-HEAD_W / 2 * inset * 2, min(HEAD_W / 2 * inset * 2, p.x))
                    cy_ = max(-HEAD_D / 2 * inset * 2, min(HEAD_D / 2 * inset * 2, p.y))
                    p.x += (cx_ - p.x) * k; p.y += (cy_ - p.y) * k
            v.co = p

    def ball(self, c, r, seg=16):
        g = bmesh.ops.create_uvsphere(self.bm, u_segments=seg, v_segments=seg // 2, radius=1.0)
        for v in g["verts"]:
            v.co = Vector((v.co.x * r[0] + c[0], v.co.y * r[1] + c[1], v.co.z * r[2] + c[2]))

    def clump(self, pts, r0, flat=0.6, tip=0.045, bulge=0.25, n=16, ring=10, up=None, power=1.3):
        """Petal / flame clump along a smooth path through pts (2-4 points, quadratic/cubic Bezier). Width r0 at the root,
        tapering to a point; flattened (thickness = flat * width) along `up` (default: outward from the head centre)."""
        P = [Vector(p) for p in pts]
        power *= 0.6       # keep clumps wide until late, then close: chunky petal tips instead of needles (REF2 §4)

        def at(t):
            if len(P) == 2:
                return P[0].lerp(P[1], t)
            if len(P) == 3:
                return (1 - t) ** 2 * P[0] + 2 * (1 - t) * t * P[1] + t * t * P[2]
            return ((1 - t) ** 3 * P[0] + 3 * (1 - t) ** 2 * t * P[1] + 3 * (1 - t) * t * t * P[2] + t ** 3 * P[3])
        rings = []
        for i in range(n + 1):
            t = i / n
            p = at(t)
            T = at(min(1, t + 0.02)) - at(max(0, t - 0.02))
            u = Vector(up) if up is not None else (p - Vector((0, 0, -0.1)))
            B, Nn = _ring_frame(T, u.normalized())
            r = max(tip, r0 * ((1 - t) ** power) * (1 + bulge * math.sin(math.pi * min(1, t * 1.6))))
            if i == 0:
                r *= 0.9
            rr = []
            for k in range(ring):
                a = 2 * math.pi * k / ring
                rr.append(self.bm.verts.new(p + B * math.cos(a) * r + Nn * math.sin(a) * r * flat))
            rings.append(rr)
        for i in range(n):
            for k in range(ring):
                self.bm.faces.new((rings[i][k], rings[i][(k + 1) % ring], rings[i + 1][(k + 1) % ring], rings[i + 1][k]))
        self.bm.faces.new(list(reversed(rings[0])))
        tipv = self.bm.verts.new(at(1.0) + (at(1.0) - at(0.97)).normalized() * tip * 1.5)
        self.tips.append((at(1.0), (at(1.0) - at(0.9)).normalized(), r0))
        for k in range(ring):
            self.bm.faces.new((rings[-1][k], rings[-1][(k + 1) % ring], tipv))

    def build(self, ch, nm, M, parent, voxel=0.02, smooth=(0.6, 6), pinch=True):
        me = D.meshes.new(f"{ch.name}_{nm}_src")
        self.bm.to_mesh(me); self.bm.free()
        ob = D.objects.new(f"{ch.name}_{nm}", me)
        ch.coll.objects.link(ob)
        r = ob.modifiers.new("Remesh", "REMESH"); r.mode = "VOXEL"; r.voxel_size = voxel; r.adaptivity = 0.0
        r.use_smooth_shade = True
        s = ob.modifiers.new("Smooth", "SMOOTH"); s.factor = smooth[0]; s.iterations = smooth[1]
        dg = bpy.context.evaluated_depsgraph_get()
        me2 = D.meshes.new_from_object(ob.evaluated_get(dg))
        ob.modifiers.clear(); ob.data = me2; D.meshes.remove(me)
        if pinch and self.tips:   # hard-tip pass: pull the rounded voxel tip into a crisp point along the clump axis
            for v in me2.vertices:
                for tp, dr, r0 in self.tips:
                    R = max(0.1, r0 * 0.9)
                    d = (v.co - tp).length
                    if d < R:
                        w = (1 - d / R) ** 2
                        ax = tp + dr * ((v.co - tp).dot(dr))
                        v.co = v.co.lerp(ax, w * 0.75) + dr * (0.05 * w)
        me2.name = f"{ch.name}_{nm}"
        me2.polygons.foreach_set("use_smooth", [True] * len(me2.polygons))
        me2.materials.append(M)
        ob.parent = parent
        return ob


HAND_TRIM = -1.28        # shoulder-pivot z below which the R6 arm block is cut away and replaced by a real hand


def _hands(ch):
    """v3.4 hands (test_seq R4-1/R4-2): the bare 1x1 skin end of the R6 arm block read as a peach CUBE / mitten slab
    (no fingers; 'Mom holds a block'). Cut the arm block at HAND_TRIM (just inside the cuff) and hang a smaller hand
    on the arm: palm 0.66 wide, 4 curled finger blocks (bevel seams read as fingers) and a thumb on the inner front
    edge. Idempotent. Hand/cuff empties keep their positions (contacts unchanged)."""
    if getattr(ch, "_hands_built", False):
        return ch
    Msk = bpy.data.materials.get(ch.name + "_skin")
    for arm in ("armL", "armR"):
        side = 1 if arm == "armL" else -1
        pv = ch.piv(arm)
        base = bpy.data.objects.get(ch.name + "_" + arm)
        if base is not None and base.type == "MESH":
            M = base.matrix_parent_inverse @ base.matrix_basis
            Mi = M.inverted()
            co = Mi @ Vector((0, 0, HAND_TRIM)); no = (M.to_3x3().transposed() @ Vector((0, 0, 1))).normalized()
            if base.data.users > 1:
                base.data = base.data.copy()
            bm = bmesh.new(); bm.from_mesh(base.data)
            bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co, plane_no=no,
                                   clear_inner=True)
            bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary], sides=0)
            bm.to_mesh(base.data); bm.free()
        nm = f"{ch.name}_hand"
        box(f"{nm}palm_{arm}", (0.66, 0.56, 0.34), (0, 0.02, -1.42), Msk, 0.08, parent=pv, coll=ch.coll)
        for k in range(4):                                     # fingers curl forward (-y) under the palm
            x = (-0.24 + k * 0.16) * side
            box(f"{nm}f{k}_{arm}", (0.145, 0.46, 0.2), (x, -0.06, -1.66 + (0.02 if k in (1, 2) else 0)), Msk, 0.05,
                parent=pv, coll=ch.coll)
        box(f"{nm}th_{arm}", (0.17, 0.22, 0.34), (-side * 0.36, -0.2, -1.47), Msk, 0.06, parent=pv, coll=ch.coll)
    ch._hands_built = True
    return ch


PRE_KEY = 1.5      # v4.3 (EP3 B-2): build/stance keys land PRE_KEY s before t0; settle_stance() re-holds untouched parts at t0


def _finish(ch, t0, t1, expr, loc, rot, rim, live, sig, rim_energy=260):
    ch.sig = sig
    _hands(ch)                                # v3.4 real hands (no peach cube) - before the joints cut the arms
    acting.rig_joints(ch)                    # v3.1 elbows + knees (cut limbs, R6 silhouette kept)
    # v4.3 (EP3 QA): the build keys go PRE_KEY s BEFORE t0. Keyed AT t0 they overrode everything a shot prepares
    # before its first frame (sit at t0-0.7, turn at t0-0.6, hold/reach approach) -> 1-frame pops on frame 1:
    # fists 1.7 off the held phone, laughing kids that never turned (EP3 A-1, B 'stance key drops the fists').
    ch.pose(t0 - PRE_KEY, loc=loc, rot=rot)
    from . import motion as _mo
    _mo.stance(ch, t0 - PRE_KEY, "stand", mirror=bool(sum(map(ord, ch.name)) % 2))   # never a stiff T/I-pose
    ch._stance_t = (t0 - PRE_KEY, t0)
    ch.face(t0, expr)
    if live:
        ch.blink(t0, t1)
        ch.breathe(0.7)
    if rim:
        L = light(ch.name + "_rim", "POINT", (0, 0, 0), rim_energy, hexc(RIM), 0.8, shadow=False)
        L.parent = ch.root; L.location = (0.9, 2.8, 6.4)
    return ch


def _base(name, skin, shirt, pants, face, scale, head_sx=1.0, **kw):
    ch = chars.Char(name, skin=skin, shirt=shirt, pants=pants, hair="none", face="v3_" + face, sleeves="long",
                    scale=scale, **kw)
    _cube_head(ch, head_sx)
    ch.hair = ch.hair_long = None
    return ch


def _shoes(ch, nm, hx, sole="#f4f1ea", h=0.36):
    for leg in ("legL", "legR"):
        box(f"{ch.name}_{nm}_{leg}", (1.03, 1.12, h), (0, -0.05, -2.0 + h / 2 + 0.06), _m(nm, hx, 0.45), 0.08,
            parent=ch.piv(leg), coll=ch.coll)
        box(f"{ch.name}_{nm}s_{leg}", (1.05, 1.14, 0.09), (0, -0.05, -1.97), _m(nm + "_sole", sole, 0.6), 0.03,
            parent=ch.piv(leg), coll=ch.coll)


def _sleeves(ch, M, cuff=None, length=1.75, w=1.05):
    for arm in ("armL", "armR"):
        _A(ch, arm, "sleeve", (w, w, length), (0, 0, -0.1 - length / 2 + 0.55), M, 0.09)
        if cuff is not None:
            _A(ch, arm, "cuff", (w + 0.03, w + 0.03, 0.2), (0, 0, -0.1 - length + 0.55 + 0.1), cuff, 0.05)


def _drawstring(ch, nm, x, z0, ln, M, Mtip):
    cyl(f"{ch.name}_{nm}", 0.035, ln, (x, -0.6, z0 - ln / 2), M, 10, parent=ch.hip, coll=ch.coll)
    cyl(f"{ch.name}_{nm}t", 0.045, 0.12, (x, -0.6, z0 - ln - 0.04), Mtip, 10, parent=ch.hip, coll=ch.coll)


def _glasses(ch, nm, M, shape="round", lens_z=0.03, w=0.2, h=0.17):
    """3D glasses on the face: rims (bevelled frames), bridge and arms to the ears."""
    y = HF - 0.045
    for sx in (-1, 1):
        x = sx * 0.225
        if shape == "round":
            o = cyl(f"{ch.name}_{nm}r{sx}", w, 0.05, (x, y, lens_z), M, 28, rot=(90, 0, 0), parent=ch.head, coll=ch.coll)
            i_ = cyl(f"{ch.name}_{nm}h{sx}", w * 0.78, 0.2, (x, y, lens_z), M, 28, rot=(90, 0, 0), parent=ch.head,
                     coll=ch.coll)
            md = o.modifiers.new("hole", "BOOLEAN"); md.object = i_; md.operation = "DIFFERENCE"; md.solver = "EXACT"
            i_.hide_render = True; i_.hide_viewport = True
        else:   # cat-eye: two flat frames with upswept outer corners
            pts = [(-0.2, -0.08), (0.14, -0.1), (0.22, 0.02), (0.27, 0.14), (0.1, 0.11), (-0.2, 0.08)]
            pts = [(px * sx, py) for px, py in pts]
            inner = [(px * 0.78, py * 0.7 - 0.005) for px, py in pts]
            o = poly_extrude(f"{ch.name}_{nm}r{sx}", pts, 0.05, (x, y + 0.02, lens_z), M, rot=(90, 0, 0), parent=ch.head,
                             coll=ch.coll, bev=0.015)
            i_ = poly_extrude(f"{ch.name}_{nm}h{sx}", inner, 0.4, (x, y + 0.2, lens_z), M, rot=(90, 0, 0), parent=ch.head,
                              coll=ch.coll)
            md = o.modifiers.new("hole", "BOOLEAN"); md.object = i_; md.operation = "DIFFERENCE"; md.solver = "EXACT"
            i_.hide_render = True; i_.hide_viewport = True
        _H(ch, f"{nm}arm{sx}", (0.04, 0.62, 0.04), (sx * 0.6, HF + 0.28, lens_z + 0.02), M, 0.015)
    _H(ch, f"{nm}br", (0.06, 0.04, 0.035), (0, y, lens_z + 0.04), M, 0.012)


# =================================================================== 1. HARRY (host / narrator)
def host(t0, t1, expr="smug", name="Harry", loc=(0, 0, 0), rot=0, scale=1.0, rim=True, prop=True, live=True,
         round_head=True):
    """Harry, 16, the storyteller (v3 2026-11-13). Chestnut SWOOP QUIFF: 7 broad flames rising off the hairline and
    sweeping up/back + crown clumps, fused into one molded mass. Face v3_harry (tall oval eyes w/ catchlight, confident
    brows; default smug). Maroon varsity jacket with cream sleeves, cream/maroon rib trim, 3D chenille 'H' letter patch,
    3D snaps, white tee, dark-indigo jeans, white sneakers. Signature: MAROON varsity."""
    ch = _base(name, "#e9b98f", "#f3f1ec", "#2d3550", "harry", scale)
    Hh = Hair()
    Hh.shell((0, 0.03, 0.14), (0.675, 0.655, 0.54), front_z=0.42, side_z=0.02, back_z=-0.4)
    for k, x in enumerate((-0.4, -0.2, 0.0, 0.2, 0.4)):                        # 5 broad front flames: up, back, to +x
        lift = 1.12 - abs(x - 0.05) * 0.4
        Hh.clump([(x, -0.52, 0.4), (x * 1.05 - 0.02, -0.76, 0.8), (x * 0.85 + 0.12, -0.42, lift + 0.08),
                  (x * 0.7 + 0.2, -0.05, lift - 0.1)], 0.22 if abs(x) < 0.3 else 0.19, flat=0.55, bulge=0.3, power=1.0,
                 tip=0.06)
    for k, x in enumerate((-0.33, 0.0, 0.33)):                                 # crown -> back, laid flat
        Hh.clump([(x * 0.6, -0.2, 0.74), (x * 1.1, 0.35, 0.8), (x * 1.2, 0.68, 0.3)], 0.22, flat=0.5, bulge=0.15, power=1.0)
    ch.hair = Hh.build(ch, "hair", _hair_mat("harry", "#5a2f17", band=(0.62, 0.86)), ch.head)
    # --- varsity jacket: maroon body panels (open front over the white tee), cream sleeves, rib trims
    Mj = _m("harry_jacket", "#6e1b26", 0.65)
    Mc = _m("harry_cream", "#efe6d2", 0.7)
    Mr = _m("harry_rib", "#5a141d", 0.8)
    for sx in (-1, 1):
        _B(ch, f"panel{sx}", (0.7, 1.08, 1.92), (sx * 0.67, 0, 1.02), Mj, 0.07)
        for k in range(3):
            cyl(f"{name}_snap{sx}{k}", 0.05, 0.04, (sx * 0.36, -0.555, 1.5 - k * 0.42), _m("harry_snap", "#d9d4ca", 0.3, 0.7),
                14, rot=(90, 0, 0), parent=ch.hip, coll=ch.coll)
    _B(ch, "hem", (2.08, 1.12, 0.2), (0, 0, 0.1), Mr, 0.05)
    _B(ch, "hemst", (2.1, 1.14, 0.045), (0, 0, 0.14), Mc, 0.01)
    _B(ch, "collar", (1.3, 1.1, 0.1), (0, 0.03, 1.97), Mr, 0.04)
    _sleeves(ch, Mc, cuff=Mr)
    for arm in ("armL", "armR"):
        _A(ch, arm, "cuffst", (1.11, 1.11, 0.04), (0, 0, -1.08), Mc, 0.01)
    # chenille letter patch (cream H with a maroon felt border) on the left chest
    Hs = [(-0.2, -0.24), (-0.08, -0.24), (-0.08, -0.04), (0.08, -0.04), (0.08, -0.24), (0.2, -0.24), (0.2, 0.24),
          (0.08, 0.24), (0.08, 0.06), (-0.08, 0.06), (-0.08, 0.24), (-0.2, 0.24)]
    _B(ch, "patchbg", (0.5, 0.05, 0.58), (0.66, -0.555, 1.38), Mc, 0.06)
    poly_extrude(name + "_patchH", [(x * 0.95, y * 0.95) for x, y in Hs], 0.05, (0.66, -0.575, 1.38), Mj, rot=(90, 0, 0),
                 parent=ch.hip, coll=ch.coll, bev=0.012)
    _shoes(ch, "harry_shoe", "#f4f2ee", "#d8d3c8")
    ch.prop = None
    return _finish(ch, t0, t1, expr, loc, rot, rim, live, PALETTE["host"])


# =================================================================== 2. MAYOR BIGSBY
def mayor(t0, t1, expr="grin", name="Mayor", loc=(0, 0, 0), rot=0, scale=1.06, rim=True, prop=True, live=True):
    """Mayor Bigsby, 58, ribbon-cutting showman (v3). Satin black top hat with a gold band, silver slicked sides, big white
    sculpted handlebar moustache, navy tailcoat over a round belly, red sash + gold medal, gold watch chain (3D links),
    giant gold scissors (ch.prop). Signature: GOLD (metal only, no glow)."""
    ch = _base(name, "#f0c9a4", "#1f2a52", "#1b2038", "mayor", scale)
    Mg = _m("mayor_gold", "#d4a73f", 0.28, 1.0)
    Mh = _m("mayor_hat", "#141418", 0.32, coat=0.4)
    Hh = Hair()                                                            # slick silver sides + back under the hat
    Hh.shell((0, 0.03, 0.08), (0.67, 0.65, 0.52), front_z=0.45, side_z=-0.05, back_z=-0.32)
    for sx in (-1, 1):
        Hh.clump([(sx * 0.5, -0.4, 0.3), (sx * 0.68, -0.05, 0.2), (sx * 0.62, 0.45, 0.0)], 0.16, flat=0.45)
    ch.hair = Hh.build(ch, "hair", _hair_mat("mayor", "#c9cbd3", band=(0.05, 0.3)), ch.head)
    Ms = Hair()                                                            # handlebar moustache, 2 sculpted curls
    for sx in (-1, 1):
        Ms.clump([(sx * 0.02, HF - 0.04, -0.2), (sx * 0.2, HF - 0.1, -0.28), (sx * 0.33, HF - 0.08, -0.2),
                  (sx * 0.36, HF - 0.04, -0.08)], 0.11, flat=0.55, bulge=0.4, up=(0, -1, 0.2), power=1.0)
    Ms.build(ch, "stache", _hair_mat("mayor_stache", "#f2efe8", band=(-0.3, -0.2)), ch.head, voxel=0.014, smooth=(0.5, 3))
    cyl(name + "_hatbrim", 0.9, 0.07, (0, 0, HT + 0.05), Mh, 40, bev=0.03, parent=ch.head, coll=ch.coll)
    cyl(name + "_hattop", 0.6, 1.1, (0, 0, HT + 0.62), Mh, 40, bev=0.05, parent=ch.head, coll=ch.coll)
    cyl(name + "_hatband", 0.615, 0.18, (0, 0, HT + 0.18), Mg, 40, parent=ch.head, coll=ch.coll)
    Mcoat = _m("mayor_coat", "#1f2a52", 0.6)
    _B(ch, "belly", (1.9, 0.28, 1.15), (0, -0.5, 0.78), Mcoat, 0.13)
    for sx in (-1, 1):
        _B(ch, f"tail{sx}", (0.85, 0.14, 1.25), (sx * 0.5, 0.58, -0.32), Mcoat, 0.06, rot=(-8, 0, 0))
        _B(ch, f"lapel{sx}", (0.3, 0.07, 0.95), (sx * 0.64, -0.6, 1.5), _m("mayor_lapel", "#161e3e", 0.45, coat=0.3), 0.04,
           rot=(0, sx * -12, 0))
    _B(ch, "shirt", (0.55, 0.06, 0.5), (0, -0.55, 1.75), _m("mayor_shirt", "#f2f0ea", 0.6), 0.04)
    sash = _B(ch, "sash", (3.2, 1.4, 0.36), (0, 0, 1.05), _m("mayor_sash", "#a9232b", 0.55), 0.03, rot=(0, 40, 0))
    clipb = _B(ch, "sashclip", (2.08, 1.44, 2.0), (0, 0, 1.0), None, 0.0)       # sash = band clipped to the torso block
    clipb.hide_render = clipb.hide_viewport = True
    md = sash.modifiers.new("clip", "BOOLEAN"); md.object = clipb; md.operation = "INTERSECT"; md.solver = "EXACT"
    sash.modifiers.move(len(sash.modifiers) - 1, 0)
    cyl(name + "_medal", 0.22, 0.07, (0.45, -0.75, 1.32), Mg, 28, bev=0.02, rot=(90, 0, 0), parent=ch.hip, coll=ch.coll)
    for k in range(9):                                                     # watch chain across the belly
        a = k / 8
        sphere(f"{name}_wc{k}", 0.045, (-0.6 + a * 0.75, -0.8 + 0.04 * math.sin(a * math.pi), 0.75 - 0.18 * math.sin(a * math.pi)),
               Mg, (1.4, 0.8, 0.8), parent=ch.hip, coll=ch.coll, seg=10)
    for sx in (-1, 1):
        cyl(f"{name}_btn{sx}", 0.065, 0.05, (sx * 0.3, -0.66, 0.45), Mg, 14, rot=(90, 0, 0), parent=ch.hip, coll=ch.coll)
    _sleeves(ch, Mcoat, cuff=_m("mayor_cuffw", "#f2f0ea", 0.6))
    _shoes(ch, "mayor_shoe", "#16161a", "#0c0c0e", 0.3)
    ch.prop = None
    if prop:
        hd = _hand(ch, "armR"); ch.prop = hd
        for k, a in enumerate((-12, 12)):
            box(f"{name}_blade{k}", (0.2, 0.07, 2.0), (0, -0.6, -0.8), _m("mayor_steel", "#dfe4ec", 0.18, 1.0), 0.02,
                rot=(0, a, 0), parent=hd, coll=ch.coll)
        for sx in (-1, 1):
            cyl(f"{name}_ring{sx}", 0.24, 0.09, (sx * 0.2, -0.55, 0.25), Mg, 24, rot=(0, 90, 0), parent=hd, coll=ch.coll)
    return _finish(ch, t0, t1, expr, loc, rot, rim, live, PALETTE["mayor"])


# =================================================================== 3. TYLER (best friend)
def bestie(t0, t1, expr="happy", name="Tyler", loc=(0, 0, 0), rot=0, scale=1.0, rim=True, prop=True, live=True,
           round_head=True):
    """Tyler, 16, Harry's best friend: fearless skater whose stunts always fail (v3). Honey-brown SPIKY crop (big flat
    triangular spikes + pointed fringe), big friendly dot eyes (v3_tyler). Navy hooded zip jacket with 3D drawstrings,
    hood roll and an orange zip pull, white tee, grey cuffed jeans, skate shoes, skateboard under the arm (prop=True,
    ch.board). Signature: NAVY."""
    ch = _base(name, "#efcfb0", "#f4f4f2", "#6b7080", "tyler", scale)
    Hh = Hair()
    Hh.shell((0, 0.03, 0.14), (0.675, 0.655, 0.52), front_z=0.38, side_z=0.0, back_z=-0.32)
    for k, x in enumerate((-0.4, -0.2, 0.0, 0.2, 0.4)):                     # pointed fringe, falling forward
        Hh.clump([(x * 0.7, -0.2, 0.68), (x, -0.62, 0.62), (x * 1.05 + 0.05, -0.68, 0.38 + abs(x) * 0.1)], 0.2, flat=0.42,
                 power=1.0, tip=0.05)
    spikes = [(-30, 0.05, 62, 0.5), (30, 0.05, 62, 0.5), (-110, 0.0, 70, 0.45), (110, 0.0, 70, 0.45), (180, 0.0, 70, 0.5)]
    for yaw, dz, tilt, ln in spikes:                                       # crown spikes radiating out/up
        ya, ti = math.radians(yaw), math.radians(tilt)
        d = Vector((math.sin(ya) * math.sin(ti), -math.cos(ya) * math.sin(ti) + 0.08, math.cos(ti)))
        root = Vector((math.sin(ya) * 0.25, -math.cos(ya) * 0.25 + 0.05, 0.62 + dz))
        Hh.clump([tuple(root), tuple(root + d * ln * 0.55 + Vector((0, 0.05, 0))), tuple(root + d * ln * 0.85 + Vector((0, 0.1, -0.05)))],
                 0.3, flat=0.35, bulge=0.1, power=1.0, tip=0.04, up=(math.sin(ya), -math.cos(ya), 0.8))
    ch.hair = Hh.build(ch, "hair", _hair_mat("tyler", "#8a5a2b", band=(0.55, 0.8)), ch.head)
    Mn = _m("ty_navy", "#1f2f5c", 0.7)
    Mn2 = _m("ty_navy2", "#18244a", 0.8)
    for sx in (-1, 1):
        _B(ch, f"panel{sx}", (0.74, 1.08, 1.94), (sx * 0.64, 0, 1.0), Mn, 0.07)
        _B(ch, f"pocket{sx}", (0.5, 0.06, 0.42), (sx * 0.6, -0.55, 0.42), Mn2, 0.05)
    _B(ch, "zipL", (0.035, 0.04, 1.9), (-0.28, -0.555, 1.0), _m("ty_zip", "#c9ccd2", 0.3, 0.8), 0.0)
    box(name + "_pull", (0.08, 0.04, 0.16), (-0.28, -0.6, 1.62), _m("ty_pull", "#e8762b", 0.5), 0.02, parent=ch.hip, coll=ch.coll)
    _B(ch, "hem", (2.06, 1.12, 0.18), (0, 0, 0.09), Mn2, 0.05)
    _B(ch, "hood", (1.7, 0.55, 0.42), (0, 0.42, 2.05), Mn, 0.18)
    for sx in (-1, 1):
        _drawstring(ch, f"ds{sx}", sx * 0.16, 1.98, 0.62, _m("ty_cord", "#f2f0ea", 0.6), _m("ty_aglet", "#c9ccd2", 0.3, 0.8))
    _sleeves(ch, Mn, cuff=Mn2)
    for leg in ("legL", "legR"):
        box(f"{name}_roll_{leg}", (1.03, 1.05, 0.18), (0, 0, -1.55), _m("ty_roll", "#8a8f9c", 0.85), 0.05,
            parent=ch.piv(leg), coll=ch.coll)
    _shoes(ch, "ty_shoe", "#2a2a30", "#f4f1ea")
    ch.prop = ch.board = None
    if prop:
        ch.board = ch.prop = skateboard(name + "_board", (0, 0, 0), coll=ch.coll)
        ch.board.parent = ch.piv("armL"); ch.board.location = (0.72, 0.1, -1.0)
        ch.board.rotation_euler = (0, math.radians(80), math.radians(90))
    return _finish(ch, t0, t1, expr, loc, rot, rim, live, PALETTE["bestie"])


def skateboard(name, loc, rot=0, coll=None):
    """Tyler's board: maple deck, black grip, orange stripe graphic, steel trucks, cream wheels. Origin = deck centre, X axis."""
    root = empty(name, loc, None, coll, (0, 0, rot), 0.3)
    box(name + "_deck", (3.0, 1.0, 0.1), (0, 0, 0.42), _m("board_deck", "#c89a5e", 0.55), 0.045, parent=root, coll=coll)
    box(name + "_grip", (2.92, 0.94, 0.02), (0, 0, 0.475), _m("board_grip", "#1b1b1e", 0.9), 0.01, parent=root, coll=coll)
    box(name + "_str", (2.4, 0.2, 0.02), (0, 0, 0.365), _m("board_str", "#e8762b", 0.5), 0.0, parent=root, coll=coll)
    for sx in (-1, 1):
        box(f"{name}_tr{sx}", (0.2, 0.7, 0.12), (sx * 1.0, 0, 0.3), _m("board_tr", "#a7adb6", 0.3, 1.0), 0.02, parent=root, coll=coll)
        for sy in (-1, 1):
            cyl(f"{name}_wh{sx}{sy}", 0.15, 0.14, (sx * 1.0, sy * 0.42, 0.16), _m("board_wh", "#efe6cf", 0.4), 18,
                bev=0.03, rot=(90, 0, 0), parent=root, coll=coll)
    return root


# =================================================================== 4. LUNA (the crush)
def crush(t0, t1, expr="pout", name="Luna", loc=(0, 0, 0), rot=0, scale=1.0, rim=True, prop=True, live=True):
    """Luna, 16, cool, kind, a little mysterious (v3). Anime face v3_luna (big crimson irises, 2 catchlights, lash flicks,
    blush hatch, tiny mouth). Long glossy DARK-CRIMSON hair as one smooth molded mass: scalp shell, blunt fringe cut into
    6 soft points, two side curtains to the chest and a back slab to the waist (long part on a damped sway rig,
    ch.hair_long). Denim jacket over a white shirt with a modelled black tie, pleated charcoal skirt, black boots, a small
    cream hair-clip. Signature: DARK CRIMSON hair."""
    ch = _base(name, "#f3d3b8", "#f2f2f4", "#2b2a33", "luna", scale, head_sx=1.06)
    Mh = _hair_mat("luna", "#5e0f1c", shine=0.18, band=(0.45, 0.72))
    Hh = Hair()
    Hh.shell((0, 0.04, 0.12), (0.71, 0.675, 0.58), front_z=0.3, side_z=-0.3, back_z=-0.45)
    for k, x in enumerate((-0.44, -0.22, 0.0, 0.22, 0.44)):                  # blunt fringe cut into soft points
        Hh.clump([(x * 0.85, -0.15, 0.72), (x, -0.63, 0.64), (x * 1.0, -0.655, 0.36 + abs(x) * 0.06)], 0.22, flat=0.32,
                 bulge=0.12, power=1.2, tip=0.06)
    ch.hair = Hh.build(ch, "hair", Mh, ch.head)
    # long hair on the sway rig (follows head turns through the neck, damped noise sway)
    sway = empty(name + "_sway", (0, 0, HT + 0.01), ch.neck, ch.coll)
    noise(sway, "rotation_euler", 0, 0.012, 34); noise(sway, "rotation_euler", 1, 0.01, 40)
    Lh = Hair()
    for sx in (-1, 1):   # one broad side curtain per side, framing the face and falling onto the chest
        Lh.clump([(sx * 0.5, -0.22, 0.66), (sx * 0.8, -0.48, 0.1), (sx * 0.66, -0.66, -0.75), (sx * 0.78, -0.68, -1.5)],
                 0.32, flat=0.42, bulge=0.12, power=0.75, tip=0.07, ring=16, up=(sx * 0.35, -1, 0.2))
        Lh.ball((sx * 0.66, -0.12, 0.0), (0.12, 0.42, 0.5), 16)          # fills the side of the head behind the curtain
    Lh.ball((0, 0.44, 0.05), (0.6, 0.15, 0.48), 20)                          # nape volume joins slab to the head
    for k, x in enumerate((-0.42, 0.0, 0.42)):                              # back slab to the waist
        Lh.clump([(x * 0.9, 0.45, 0.5), (x * 1.05, 0.7, -0.4), (x * 1.1, 0.8, -1.6), (x * 1.05, 0.84, -2.3)],
                 0.42, flat=0.36, bulge=0.08, power=0.5, tip=0.07, ring=14, up=(0, 1, 0))
    ch.hair_long = Lh.build(ch, "hairlong", Mh, sway, voxel=0.024, smooth=(0.6, 6))
    ch.hair_long.location = (0, 0, 0)
    # outfit
    Md = _m("luna_denim", "#4a5f80", 0.85)
    Mds = _m("luna_seam", "#7f93b3", 0.8)
    for sx in (-1, 1):
        _B(ch, f"panel{sx}", (0.6, 1.08, 1.94), (sx * 0.71, 0, 1.02), Md, 0.07)
        _B(ch, f"pocket{sx}", (0.36, 0.05, 0.3), (sx * 0.72, -0.555, 1.45), Mds, 0.03)
        poly_extrude(f"{name}_col{sx}", [(0, 0), (sx * 0.34, 0.04), (sx * 0.12, -0.3)], 0.05, (sx * 0.02, -0.52, 1.99),
                     _m("luna_shirt", "#f2f2f4", 0.6), rot=(90, 0, 0), parent=ch.hip, coll=ch.coll, bev=0.01)
    _B(ch, "jcollar", (1.3, 1.1, 0.1), (0, 0.04, 1.97), Md, 0.04)
    Mt = _m("luna_tie", "#141418", 0.35, coat=0.3)
    _B(ch, "tie_knot", (0.2, 0.08, 0.17), (0, -0.57, 1.87), Mt, 0.04)
    poly_extrude(name + "_tie", [(-0.09, 0), (0.09, 0), (0.15, -0.95), (0, -1.08), (-0.15, -0.95)], 0.05, (0, -0.56, 1.79),
                 Mt, rot=(90, 0, 0), parent=ch.hip, coll=ch.coll, bev=0.015)
    _sleeves(ch, Md, cuff=Mds)
    Msk = _m("luna_skirt", "#2b2a33", 0.7)
    _B(ch, "skirt", (2.12, 1.14, 0.8), (0, 0, -0.3), Msk, 0.08)
    for k in range(7):                                                       # pleats
        _B(ch, f"pleat{k}", (0.05, 0.03, 0.78), (-0.9 + k * 0.3, -0.575, -0.3), _m("luna_pleat", "#1f1e26", 0.8), 0.0)
    for leg in ("legL", "legR"):
        box(f"{name}_boot_{leg}", (1.04, 1.12, 0.9), (0, -0.04, -1.53), _m("luna_boot", "#18171c", 0.35, coat=0.4), 0.08,
            parent=ch.piv(leg), coll=ch.coll)
    clip = _H(ch, "clip", (0.24, 0.05, 0.06), (0.36, HF - 0.07, 0.43), _m("luna_clip", "#efe6d2", 0.4), 0.02, rot=(0, -25, 0))
    ch.prop = clip
    return _finish(ch, t0, t1, expr, loc, rot, rim, live, PALETTE["crush"])


# =================================================================== 5. MOM (Rosa)
def mom(t0, t1, expr="smile", name="Mom", loc=(0, 0, 0), rot=0, scale=1.0, rim=True, prop=True, live=True):
    """Mom (Rosa), 42, runs the house on coffee and zero excuses (v3). Warm-brown skin (#b07a52, same as Rick). Espresso
    shoulder BOB with a deep side part, swept fringe and flipped ends, modelled coral headband. Teal cardigan with 3D
    buttons over a cream top, dark slacks, big white coffee mug (ch.prop). Signature: TEAL."""
    ch = _base(name, "#b07a52", "#f1e6d2", "#3a3446", "mom", scale)
    Hh = Hair()
    # v3.1 (2026-11-14): no more smooth side balls (read as a helmet in MCU). Deep side part at x=+0.24 with the
    # fringe split into a big sweep and a small counter-sweep (visible part groove), then LAYERED clumps: 3 per side +
    # 3 at the back, staggered lengths, tips flicking out at the jaw, so the silhouette and the AO show separate locks.
    Hh.shell((0, 0.04, 0.12), (0.69, 0.665, 0.56), front_z=0.46, side_z=-0.1, back_z=-0.3)
    Hh.clump([(0.2, -0.28, 0.76), (-0.12, -0.7, 0.68), (-0.52, -0.67, 0.4), (-0.66, -0.5, 0.1)], 0.23, flat=0.42,
             bulge=0.2, power=0.9, tip=0.05)                              # main swept fringe (toward her right)
    Hh.clump([(0.3, -0.3, 0.74), (0.48, -0.67, 0.6), (0.64, -0.6, 0.34)], 0.14, flat=0.42, tip=0.045)  # counter-sweep
    for sx in (-1, 1):
        for k, (y, ln) in enumerate(((-0.36, 0.0), (0.02, 0.08), (0.38, 0.04))):
            z_end = -0.42 - ln - (0.06 if (sx > 0) == (k == 1) else 0.0)
            Hh.clump([(sx * 0.42, y * 0.8, 0.66), (sx * 0.73, y, 0.18), (sx * 0.74, y + 0.02, z_end + 0.14),
                      (sx * 0.83, y + 0.03, z_end)], 0.21 if k != 1 else 0.24, flat=0.5, bulge=0.12, power=0.8,
                     tip=0.05, up=(sx, 0.1 * y, 0.2))
    for k, x in enumerate((-0.38, 0.0, 0.38)):
        Hh.clump([(x * 0.7, 0.3, 0.66), (x, 0.66, 0.15), (x, 0.68, -0.3), (x * 1.05, 0.74, -0.44 - 0.05 * (k == 1))],
                 0.25, flat=0.45, bulge=0.1, power=0.8, tip=0.05, up=(0, 1, 0.2))
    ch.hair = Hh.build(ch, "hair", _hair_mat("mom", "#3d2418", shine=0.26, band=(0.42, 0.66)), ch.head)
    # headband v3.5 (R5: it floated ~0.25 above the hair - the old Bezier controls (+-0.74, z 0.98) made a boxy arch whose
    # shoulders stood far off the 0.56-tall cap). Now a semi-ellipse CONFORMED to the hair shell slice at y=-0.12 (just
    # behind the fringe): cubic with endpoints at the cap's side (z = shell centre, hidden under the side locks) and
    # controls at 4/3 of the cap height -> the band rides 0.02-0.05 above the shell all the way over.
    _rx, _rz, _cz = 0.69 * 0.985 + 0.04, 0.56 * 0.985 + 0.03, 0.12
    band = Hair()
    band.clump([(-_rx, -0.12, _cz), (-_rx, -0.12, _cz + _rz * 4 / 3), (_rx, -0.12, _cz + _rz * 4 / 3), (_rx, -0.12, _cz)], 0.075, flat=0.5,
               bulge=0.0, power=0.01, tip=0.06, up=(0, 0, 1))
    band.build(ch, "band", _m("mom_band", "#e2675a", 0.5, coat=0.2), ch.head, voxel=0.012, smooth=(0.5, 2))
    Mt = _m("mom_teal", "#2a9d8f", 0.75)
    for sx in (-1, 1):
        _B(ch, f"card{sx}", (0.7, 1.08, 1.98), (sx * 0.67, 0, 0.99), Mt, 0.08)
        for k in range(3 if sx < 0 else 0):
            cyl(f"{name}_cbtn{sx}{k}", 0.055, 0.04, (sx * 0.36, -0.56, 1.45 - k * 0.38), _m("mom_btn", "#efe6d2", 0.35),
                14, rot=(90, 0, 0), parent=ch.hip, coll=ch.coll)
    _B(ch, "rib", (2.08, 1.12, 0.16), (0, 0, 0.08), _m("mom_teal2", "#23877b", 0.85), 0.05)
    _sleeves(ch, Mt, cuff=_m("mom_teal2", "#23877b", 0.85))
    _shoes(ch, "mom_shoe", "#5a3a2a", "#3a261b", 0.28)
    ch.prop = None
    if prop:
        hd = _hand(ch, "armR"); ch.prop = hd
        Mm = _m("mom_mug", "#f6f4ef", 0.3, coat=0.4)
        cyl(name + "_mug", 0.32, 0.6, (0, -0.55, 0.05), Mm, 28, bev=0.03, parent=hd, coll=ch.coll)
        cyl(name + "_coffee", 0.27, 0.02, (0, -0.55, 0.355), _m("mom_coffee", "#3b2416", 0.15), 24, parent=hd, coll=ch.coll)
        box(name + "_handle", (0.1, 0.3, 0.34), (0.37, -0.55, 0.05), Mm, 0.05, parent=hd, coll=ch.coll)
    return _finish(ch, t0, t1, expr, loc, rot, rim, live, PALETTE["mom"])


# =================================================================== 6. DAD (Rick)
def dad(t0, t1, expr="exasperated", name="Dad", loc=(0, 0, 0), rot=0, scale=1.04, rim=True, prop=True, live=True,
        round_head=True):
    """Dad (Rick), 48, grill enthusiast who burns everything (v3). Same warm-brown skin as Mom (#b07a52), face v3_dad (heavy
    brows; default exasperated). BLACK slicked-back hair with GREY temples and two grey streaks (one molded mass, grey by
    shader mask). Red/black buffalo-check flannel, charcoal grill apron with 3D neck strap + pocket, khaki chinos,
    spatula (ch.prop). Signature: RED FLANNEL."""
    ch = _base(name, "#b07a52", "#a8302a", "#b49a74", "dad", scale)
    Hh = Hair()
    Hh.shell((0, 0.03, 0.12), (0.67, 0.655, 0.53), front_z=0.42, side_z=0.02, back_z=-0.32)
    for k, x in enumerate((-0.4, -0.22, -0.05, 0.12, 0.29, 0.44)):            # slicked back from a side part at x=-0.3
        sw = 0.08 if x > -0.3 else -0.05
        Hh.clump([(x, -0.52, 0.42), (x + sw, -0.6, 0.78), (x + sw * 1.6, -0.05, 0.8), (x + sw * 1.8, 0.55, 0.45)], 0.15,
                 flat=0.45, bulge=0.15, power=0.7)
    for sx in (-1, 1):
        Hh.clump([(sx * 0.6, -0.4, 0.3), (sx * 0.68, -0.1, 0.25), (sx * 0.64, 0.45, 0.15)], 0.13, flat=0.45, power=0.8)
    ch.hair = Hh.build(ch, "hair", _hair_mat("dad", "#17171a", shine=0.2, band=(0.6, 0.82), streaks=(-0.12, 0.22),
                                             temples=0.62), ch.head)
    Mp = _plaid("dad_flannel", "#a8262a", "#5a1216", "#141214")
    ch.torso.data.materials.clear(); ch.torso.data.materials.append(Mp)
    _sleeves(ch, Mp, cuff=_m("dad_cuff", "#7e2420", 0.7))
    Ma = _m("dad_apron", "#34343a", 0.8)
    _B(ch, "apron", (1.5, 0.06, 2.4), (0, -0.56, 0.6), Ma, 0.06)
    _B(ch, "apronpk", (0.8, 0.05, 0.4), (0, -0.6, 0.55), _m("dad_apron2", "#2a2a30", 0.85), 0.04)
    for sx in (-1, 1):
        _B(ch, f"strap{sx}", (0.1, 0.06, 0.55), (sx * 0.45, -0.56, 1.95), Ma, 0.02, rot=(0, sx * 25, 0))
    _B(ch, "collar", (1.4, 1.1, 0.12), (0, 0.03, 1.97), _m("dad_cuff", "#7e2420", 0.7), 0.05)
    _shoes(ch, "dad_shoe", "#5a3d2a", "#2e2018", 0.32)
    ch.prop = None
    if prop:
        hd = _hand(ch, "armR"); ch.prop = hd
        cyl(name + "_sp_h", 0.08, 0.95, (0, -0.5, -0.25), _m("dad_handle", "#2a1d14", 0.5), 12, bev=0.02, parent=hd, coll=ch.coll)
        box(name + "_sp_b", (0.56, 0.05, 0.6), (0, -0.5, -0.93), _m("dad_steel", "#cfd6e0", 0.22, 1.0), 0.04, parent=hd, coll=ch.coll)
    return _finish(ch, t0, t1, expr, loc, rot, rim, live, PALETTE["dad"])


# =================================================================== 7. GRANDPA OTTO
def grandpa(t0, t1, expr="smile", name="Grandpa", loc=(0, 0, 0), rot=0, scale=0.96, rim=True, prop=True, live=True):
    """Grandpa Otto, 78, endless storyteller who falls asleep mid-story (v3). Bald dome with cloud-white side puffs and a
    big white walrus moustache (sculpted), round tortoiseshell glasses (3D), forest-green sweater vest over a cream shirt
    with a 3D red bow tie, brown trousers, slight hunch, wooden cane (ch.prop). Signature: FOREST GREEN."""
    ch = _base(name, "#efcfae", "#efe6d2", "#5e4c3c", "grandpa", scale)
    Mw = _hair_mat("grandpa", "#eceae4", shine=0.1, band=(0.0, 0.3))
    Hh = Hair()
    Hh.shell((0, 0.12, -0.04), (0.665, 0.56, 0.36), front_z=0.6, side_z=-0.12, back_z=-0.34)   # fringe of hair round the back
    for sx in (-1, 1):
        Hh.clump([(sx * 0.62, -0.22, 0.12), (sx * 0.74, 0.1, 0.22), (sx * 0.7, 0.45, 0.08)], 0.24, flat=0.6, bulge=0.35,
                 power=0.8, tip=0.06, up=(sx, 0, 0.3))                   # one soft swept-back puff per side
        Hh.clump([(sx * 0.6, 0.0, -0.02), (sx * 0.72, 0.25, 0.0), (sx * 0.66, 0.5, -0.12)], 0.18, flat=0.6, bulge=0.3,
                 power=0.8, tip=0.06, up=(sx, 0, 0.3))
    ch.hair = Hh.build(ch, "hair", Mw, ch.head, voxel=0.024, smooth=(0.7, 10))
    Ms = Hair()
    for sx in (-1, 1):
        Ms.clump([(sx * 0.02, HF - 0.03, -0.12), (sx * 0.22, HF - 0.12, -0.2), (sx * 0.34, HF - 0.08, -0.36)], 0.15,
                 flat=0.55, bulge=0.35, power=0.8, up=(0, -1, 0))
    Ms.build(ch, "stache", Mw, ch.head, voxel=0.015, smooth=(0.5, 3))
    _glasses(ch, "gl", _m("gp_glass", "#5a3a22", 0.3, coat=0.5), "round", lens_z=0.06, w=0.17)
    _B(ch, "vest", (2.06, 1.08, 1.55), (0, 0, 0.82), _m("gp_vest", "#2f6b4a", 0.85), 0.07)
    poly_extrude(name + "_vneck", [(-0.36, 0), (0.36, 0), (0, -0.55)], 0.05, (0, -0.52, 1.6), _m("gp_shirt", "#efe6d2", 0.6),
                 rot=(90, 0, 0), parent=ch.hip, coll=ch.coll)
    Mb = _m("gp_bow", "#a3262b", 0.5)
    for sx in (-1, 1):
        poly_extrude(f"{name}_bow{sx}", [(0, 0), (sx * 0.24, 0.12), (sx * 0.24, -0.12)], 0.08, (0, -0.56, 1.86), Mb,
                     rot=(90, 0, 0), parent=ch.hip, coll=ch.coll, bev=0.02)
    _B(ch, "bowknot", (0.1, 0.1, 0.12), (0, -0.6, 1.86), Mb, 0.03)
    for k in range(3):
        cyl(f"{name}_vbtn{k}", 0.05, 0.04, (0, -0.565, 1.15 - k * 0.3), _m("gp_btn", "#c9b07a", 0.4), 12, rot=(90, 0, 0),
            parent=ch.hip, coll=ch.coll)
    _shoes(ch, "gp_shoe", "#4a3122", "#2e1f16", 0.3)
    ch.prop = None
    if prop:
        hd = _hand(ch, "armR"); ch.prop = hd
        Mc = _m("gp_cane", "#6e4424", 0.45, coat=0.4)
        cyl(name + "_cane", 0.09, 2.6, (0, -0.35, -1.2), Mc, 14, parent=hd, coll=ch.coll)
        cyl(name + "_hook", 0.09, 0.6, (0, -0.1, 0.1), Mc, 14, rot=(90, 0, 0), parent=hd, coll=ch.coll)
        ch.pose(t0, armR=(18, 6))
    ch.pose(t0, torso=(0, 8, 0), head=(0, -6, 0))    # slight hunch, head lifted to keep the face up
    return _finish(ch, t0, t1, expr, loc, rot, rim, live, PALETTE["grandpa"])


# =================================================================== 8. GRANDMA PEARL
def grandma(t0, t1, expr="smile", name="Grandma", loc=(0, 0, 0), rot=0, scale=0.94, rim=True, prop=True, live=True,
            gamer=False):
    """Grandma Pearl, 74, sweet quiet knitter... and secretly the #1 ranked gamer in the world (v3). Silver hair swept
    up from a soft side-swept fringe into a high round bun with a wooden knitting needle through it, rose cheeks, glossy
    rose cat-eye glasses (3D), pearl necklace (3D), lavender cardigan over a rose dress, knitting + red yarn ball (ch.prop).
    gamer=True adds a black gaming headset (no glow). Signature: LAVENDER."""
    ch = _base(name, "#f2d6c0", "#c75b74", "#c75b74", "grandma", scale)
    Hh = Hair()
    Hh.shell((0, 0.03, 0.14), (0.69, 0.665, 0.55), front_z=0.44, side_z=0.0, back_z=-0.3)
    Hh.clump([(0.35, -0.3, 0.75), (-0.05, -0.7, 0.62), (-0.5, -0.62, 0.45)], 0.26, flat=0.45, bulge=0.2)   # swept fringe
    for sx in (-1, 1):
        Hh.clump([(sx * 0.55, -0.4, 0.4), (sx * 0.74, 0.0, 0.3), (sx * 0.4, 0.5, 0.65)], 0.2, flat=0.55, power=0.6)
    Hh.ball((0, 0.16, 0.8), (0.34, 0.34, 0.31), 20)
    ch.hair = Hh.build(ch, "hair", _hair_mat("grandma", "#cfd1da", shine=0.12, band=(0.75, 1.0)), ch.head)
    cyl(name + "_pin", 0.035, 1.05, (0, 0.16, 0.86), _m("gm_needle", "#b58a5a", 0.4), 10, rot=(0, 72, 0), parent=ch.head,
        coll=ch.coll)
    _glasses(ch, "gl", _m("gm_frames", "#c2486a", 0.25, coat=0.6), "cat", lens_z=0.04)
    for k in range(13):
        a = math.radians(-66 + k * 11)
        sphere(f"{name}_pearl{k}", 0.065, (math.sin(a) * 0.6, -0.52 - math.cos(a) * 0.06, 1.98 - math.cos(a) * 0.32),
               _m("gm_pearl", "#f7f1e6", 0.18, coat=0.8), parent=ch.hip, coll=ch.coll, seg=12)
    Ml = _m("gm_lav", "#a58fd0", 0.85)
    _sleeves(ch, Ml, cuff=_m("gm_lav2", "#8e78bb", 0.9))
    for sx in (-1, 1):
        _B(ch, f"card{sx}", (0.64, 1.08, 1.98), (sx * 0.71, 0, 0.99), Ml, 0.08)
    _B(ch, "skirt", (2.14, 1.14, 0.85), (0, 0, -0.32), _m("gm_dress", "#c75b74", 0.7), 0.1)
    _shoes(ch, "gm_shoe", "#efe6d2", "#c9bfae", 0.28)
    ch.prop = None
    if prop:
        hd = _hand(ch, "armR"); ch.prop = hd
        sphere(name + "_yarn", 0.4, (0.3, -0.7, 0.1), _m("gm_yarn", "#b82230", 0.95), parent=hd, coll=ch.coll, seg=20)
        for k, a in enumerate((-30, 30)):
            cyl(f"{name}_ndl{k}", 0.035, 1.4, (0.0, -0.6, 0.4), _m("gm_needle", "#b58a5a", 0.4), 10, rot=(a, 20, 0),
                parent=hd, coll=ch.coll)
        box(name + "_knit", (0.7, 0.12, 0.5), (-0.2, -0.65, 0.4), _m("gm_knit", "#b82230", 0.95), 0.1, parent=hd, coll=ch.coll)
    if gamer:
        Mk = _m("gm_head", "#141418", 0.35)
        _H(ch, "gh_band", (1.4, 0.2, 0.14), (0, 0.0, HT + 0.12), Mk, 0.06)
        for sx in (-1, 1):
            cyl(f"{name}_gh{sx}", 0.28, 0.22, (sx * 0.7, 0.0, 0.05), Mk, 28, bev=0.04, rot=(0, 90, 0), parent=ch.head, coll=ch.coll)
            cyl(f"{name}_ghr{sx}", 0.2, 0.04, (sx * 0.82, 0.0, 0.05), _m("gm_ring", "#a58fd0", 0.4), 28, rot=(0, 90, 0),
                parent=ch.head, coll=ch.coll)
        _H(ch, "mic", (0.07, 0.55, 0.07), (0.6, -0.4, -0.22), Mk, 0.02, rot=(0, 0, 30))
    return _finish(ch, t0, t1, expr, loc, rot, rim, live, PALETTE["grandma"])


ALL = dict(host=host, mayor=mayor, bestie=bestie, crush=crush, mom=mom, dad=dad, grandpa=grandpa, grandma=grandma)
NAMES = dict(host="Harry", mayor="Mayor Bigsby", bestie="Tyler", crush="Luna", mom="Mom (Rosa)", dad="Dad (Rick)",
             grandpa="Grandpa Otto", grandma="Grandma Pearl")
SHEET_EXPR = ["neutral", "happy", "sad", "shock", "angry", "smirk", "scream", "cry"]


def make(role, t0, t1, *a, cine=False, **kw):
    """Build a cast member by role. cine=True applies the CINEMATIC 3D finish (cast.cine) after building."""
    ch = ALL[role](t0, t1, *a, **kw)
    return cine_finish(ch) if cine else ch


# =================================================================== CINEMATIC 3D MODE
_LIMBS = ("_torso", "_armL", "_armR", "_legL", "_legR")


def _bsdf(m):
    return next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None) if m and m.use_nodes else None


def _set(b, k, v):
    try:
        b.inputs[k].default_value = v
    except (KeyError, TypeError):
        pass


def _bump(m, height_sock, strength, dist):
    nt = m.node_tree; b = _bsdf(m)
    bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = strength
    bp.inputs["Distance"].default_value = dist
    nt.links.new(height_sock, bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return bp


def _tex(m, kind, scale, **kw):
    nt = m.node_tree
    tc = nt.nodes.new("ShaderNodeTexCoord")
    t = nt.nodes.new(kind); t.inputs["Scale"].default_value = scale
    for k, v in kw.items():
        if k in t.inputs:
            t.inputs[k].default_value = v
        else:
            setattr(t, k, v)
    nt.links.new(tc.outputs["Object"], t.inputs["Vector"])
    return t


CLEAN = True   # v4.0: no micro-noise / weave / strand bump maps (they read as dust and grain on Instagram); keep SSS + coat


def _cine_mat(m):
    """Cinematic copy of a material (cached by name, the flat original stays untouched for animation-mode characters)."""
    key = m.name + "__cine"
    if key in D.materials:
        return D.materials[key]
    c = m.copy(); c.name = key
    b = _bsdf(c)
    if b is None:
        return c
    nt = c.node_tree
    rough = b.inputs["Roughness"].default_value if not b.inputs["Roughness"].is_linked else 0.5
    metal = b.inputs["Metallic"].default_value
    if "EyeMap" in nt.nodes:                                   # face: skin SSS + decal emboss
        _set(b, "Subsurface Weight", 0.12); _set(b, "Subsurface Scale", 0.06)
        _set(b, "Subsurface Radius", (1.0, 0.35, 0.2)); _set(b, "Coat Weight", 0.08); _set(b, "Coat Roughness", 0.35)
        alphas = [n.inputs[0].links[0].from_socket for n in nt.nodes
                  if n.type == "MIX" and n.inputs[0].is_linked]
        if alphas:
            acc = alphas[0]
            for a2 in alphas[1:]:
                ad = nt.nodes.new("ShaderNodeMath"); ad.operation = "MAXIMUM"
                nt.links.new(acc, ad.inputs[0]); nt.links.new(a2, ad.inputs[1]); acc = ad.outputs[0]
            if not CLEAN:
                nz = _tex(c, "ShaderNodeTexNoise", 45.0, **{"Detail": 3.0})
                sm = nt.nodes.new("ShaderNodeMath"); sm.operation = "MULTIPLY_ADD"
                nt.links.new(nz.outputs["Fac"], sm.inputs[0]); sm.inputs[1].default_value = 0.08
                nt.links.new(acc, sm.inputs[2])
                _bump(c, sm.outputs[0], 0.4, 0.006)              # decal emboss + skin micro-normal (face plane catches light)
            _set(b, "Specular IOR Level", 0.45)
    elif m.name.startswith("cast_hair_"):                    # hair: strand-normal + anisotropic-ish gloss
        _set(b, "Anisotropic", 0.55); _set(b, "Coat Weight", 0.3); _set(b, "Coat Roughness", 0.22)
        _set(b, "Roughness", 0.32); _set(b, "Sheen Weight", 0.35)
        w = _tex(c, "ShaderNodeTexWave", 22.0, wave_type="BANDS", bands_direction="X", Distortion=6.0,
                 **{"Detail": 3.0, "Detail Scale": 1.5})
        if not CLEAN:
            _bump(c, w.outputs["Fac"], 0.07, 0.01)
    elif m.name.endswith("_skin"):
        _set(b, "Subsurface Weight", 0.12); _set(b, "Subsurface Scale", 0.06)
        _set(b, "Subsurface Radius", (1.0, 0.35, 0.2)); _set(b, "Coat Weight", 0.08)
    elif metal > 0.5:
        _set(b, "Coat Weight", 0.3); _set(b, "Coat Roughness", 0.15)
    elif rough >= 0.55:                                      # fabric: micro weave + sheen
        if CLEAN:
            _set(b, "Sheen Weight", 0.15); _set(b, "Sheen Roughness", 0.5)
            return c
        _set(b, "Sheen Weight", 0.45); _set(b, "Sheen Roughness", 0.35)
        wv = _tex(c, "ShaderNodeTexWave", 90.0, wave_type="BANDS", bands_direction="DIAGONAL", Distortion=0.6)
        nz = _tex(c, "ShaderNodeTexNoise", 160.0, **{"Detail": 2.0})
        mx = nt.nodes.new("ShaderNodeMath"); mx.operation = "MULTIPLY"
        nt.links.new(wv.outputs["Fac"], mx.inputs[0]); nt.links.new(nz.outputs["Fac"], mx.inputs[1])
        _bump(c, mx.outputs[0], 0.22, 0.012)
    else:                                                    # plastic / leather / ceramic: soft clearcoat
        _set(b, "Coat Weight", 0.35); _set(b, "Coat Roughness", 0.18)
    return c


def cine_finish(ch, bevel=0.24, segs=8):
    """CINEMATIC 3D MODE: same design, more dimensional finish for close-ups / shallow-DOF cinema shots (REF1).
    - rounder blocks: torso/limbs bevel `bevel` with `segs` segments (catches a wide edge highlight), all bevels >= 4 seg
    - skin subsurface + light coat, face decal micro-emboss, fabric weave micro-normal + sheen, plastic clearcoat,
      hair strand-normal + anisotropic gloss (on cached '__cine' material copies: animation-mode characters are untouched)
    Pair with cast.cine_light(...) for the key/fill/rim/bounce rig. Returns ch (ch.cine = True)."""
    for ob in list(ch.coll.objects):
        if ob.type != "MESH":
            continue
        for md in ob.modifiers:
            if md.type == "BEVEL" and md.width > 0:
                md.segments = max(md.segments, 4)
                if ob.name.removesuffix("_lo").endswith(_LIMBS) or "_sleeve_" in ob.name or "_panel" in ob.name:
                    md.width = max(md.width, bevel); md.segments = max(md.segments, segs)
                    md.use_clamp_overlap = True
        for i, m in enumerate(ob.data.materials):
            if m is not None and not m.name.endswith("__cine"):
                ob.data.materials[i] = _cine_mat(m)
    # rounder head: wider bevel + gentle spherical inflate so the face plane gets real shading falloff (decals are
    # projected along Y in object space, so they still map; expressions/blink/talk keep using the same nodes)
    h = ch.head
    for md in h.modifiers:
        if md.type == "BEVEL":
            md.width = 0.34; md.segments = 8
    if "cine_round" not in h.modifiers:
        cm = h.modifiers.new("cine_round", "CAST"); cm.cast_type = "SPHERE"; cm.factor = 0.16
    for ob in ch.coll.objects:                # thicker modelled accessories (extrusion depth = local Z)
        if ob.type == "MESH" and any(k in ob.name for k in ("_tie", "_patchH", "_bow", "_col", "_bolt")):
            ob.scale = (ob.scale[0], ob.scale[1], ob.scale[2] * 1.8)
    if getattr(ch, "face_mat", None) is not None and not ch.face_mat.name.endswith("__cine"):
        ch.face_mat = ch.head.data.materials[0]
    ch.cine = True
    return ch


cine = cine_finish


def cine_light(focus, cam_loc, scale=1.0, key=1.0, warm="#ffe3c0", cool="#cfe2ff", bounce="#e8c9a0", name="cl",
               fill=1 / 6, rim=1.4, top=0.25, coll=None, receivers=None):
    """Character light rig for cinematic shots (18-85 mm, f/1.8-2.8). Key ~6:1 over fill: big warm key 55 deg off
    camera-left and high (spread-limited = snooted, so it does not paint walls/ceilings), cool fill from camera-right,
    tight cool rim from behind, subtle top light for hair, warm floor bounce. focus = face point, cam_loc = camera.
    scale ~1 MCU/medium, 1.6-2 wides. Returns dict of lights."""
    f = Vector(focus); c = Vector(cam_loc)
    d = c - f; d.z = 0
    d = d.normalized() if d.length > 1e-4 else Vector((0, -1, 0))
    side = Vector((-d.y, d.x, 0))
    s = scale
    E = 650 * key * s * s
    out = {}
    out["key"] = light(f"{name}_key", "AREA", tuple(f + (d * 0.55 + side * 0.85).normalized() * 5 * s + Vector((0, 0, 2.6 * s))),
                       E, hexc(warm), 2.2 * s, target=tuple(f), coll=coll)
    out["fill"] = light(f"{name}_fill", "AREA", tuple(f + (d - side * 0.9).normalized() * 6 * s + Vector((0, 0, 0.5 * s))),
                        E * fill, hexc(cool), 5.0 * s, target=tuple(f), coll=coll, shadow=False)
    out["rim"] = light(f"{name}_rim", "AREA", tuple(f - d * 3.5 * s - side * 1.8 * s + Vector((0, 0, 2.2 * s))),
                       E * rim, hexc(cool), 0.8 * s, target=tuple(f + Vector((0, 0, 0.4))), coll=coll, shadow=False)
    out["top"] = light(f"{name}_top", "AREA", tuple(f + Vector((0, 0.3 * s, 3.5 * s))), E * top, hexc("#fff4e6"), 1.5 * s,
                       target=tuple(f + Vector((0, 0, 0.6))), coll=coll, shadow=False)
    out["bounce"] = light(f"{name}_bnc", "AREA", tuple(f + d * 3 * s + Vector((0, 0, -f.z + 0.2))), E * 0.06,
                          hexc(bounce), 4.0 * s, target=tuple(f), coll=coll, shadow=False)
    for k in ("key", "rim", "top"):
        try:
            out[k].data.spread = math.radians(70 if k == "key" else 50)
        except AttributeError:
            pass
    if receivers:   # light linking: key/rim/top/bounce light only these characters (no wedges on walls/ceilings)
        rc = D.collections.get(name + "_recv") or D.collections.new(name + "_recv")
        for r in receivers:
            cc = getattr(r, "coll", r)
            if cc.name not in rc.children:
                rc.children.link(cc)
        for k in ("key", "rim", "top", "bounce"):
            try:
                out[k].light_linking.receiver_collection = rc
            except AttributeError:
                pass
    return out


# =================================================================== motion polish
def squash(ch, t, amt=0.2, dur=0.0):
    """Key root scale: amt>0 squash (wide+short), amt<0 stretch. Keys scale at t (pair with another call to return)."""
    s0 = ch.root.scale[0] if not hasattr(ch, "_base_s") else ch._base_s
    ch._base_s = s0
    ch.root.scale = (s0 * (1 + amt * 0.6), s0 * (1 + amt * 0.6), s0 * (1 - amt))
    ch.root.keyframe_insert("scale", frame=F(t))
    return ch


def hop(ch, t, height=1.8, dur=0.55, p0=None, p1=None, arms=True):
    """Jump with anticipation crouch + squash, stretch on take-off, squash on landing, overshoot settle."""
    p0 = Vector(p0) if p0 else Vector(ch.root.location)
    p1 = Vector(p1) if p1 else p0
    a = 0.12
    squash(ch, t - a - 0.01, 0.0)
    ch.pose(t - a - 0.01, loc=tuple(p0), hipz=0.0)
    ch.pose(t, hipz=-0.4, armL=(-30, 12) if arms else None or (0, 4), armR=(-30, 12) if arms else (0, 4)); squash(ch, t, 0.18)
    mid = (p0 + p1) / 2 + Vector((0, 0, height))
    ch.pose(t + dur * 0.18, hipz=0.05); squash(ch, t + dur * 0.18, -0.16)
    ch.pose(t + dur * 0.5, loc=tuple(mid), armL=(155, 30), armR=(155, 30), legL=(30, 0), legR=(-10, 0)); squash(ch, t + dur * 0.5, 0.0)
    ch.pose(t + dur, loc=tuple(p1), hipz=-0.35, armL=(45, 35), armR=(45, 35), legL=(0, 0), legR=(0, 0)); squash(ch, t + dur, 0.22)
    ch.pose(t + dur + 0.1, hipz=0.06); squash(ch, t + dur + 0.1, -0.06)
    ch.pose(t + dur + 0.22, hipz=0.0, armL=(4, 6), armR=(4, 6)); squash(ch, t + dur + 0.22, 0.0)
    return ch


def walk2(ch, t0, t1, p0, p1, rate=2.2, swing=30, arm=26, bob=0.14, twist=6):
    """Walk cycle: contact-down-pass-up hip bob (lowest just after heel strike), torso counter-twist, head stabilised.
    v3.2: arm swing clamped to +-30 deg with arms hanging IN (out -1), elbows keyed every step (forward arm 18,
    back arm 6): before, the swing ran on the stand pose's elbow + out 4 and the forward forearm rotated into a
    detached-looking block in front of the torso that clipped a neighbour (stress_suite front_hall/kitchen R2)."""
    arm = max(-30.0, min(30.0, arm))
    ch.walk(t0, t1, p0, p1, rate=rate, swing=swing, arm=arm, bob=0.0)
    step = 1.0 / (rate * 2)
    t, k = t0, 0
    while t <= t1 + 1e-4:
        s = 1 if k % 2 == 0 else -1
        ch.pose(t, torso=(twist * s, 3, 0), head=(-twist * s * 0.7, -2, 0), hipz=-bob * 0.3,
                armL=(-arm * s, -1, 0), armR=(arm * s, -1, 0),
                elbowL=18 if s < 0 else 6, elbowR=18 if s > 0 else 6)
        if t + step * 0.25 <= t1:
            ch.pose(t + step * 0.25, hipz=-bob)
        if t + step * 0.7 <= t1:
            ch.pose(t + step * 0.7, hipz=bob * 0.6)
        t += step; k += 1
    ch.pose(t1, torso=(0, 0, 0), head=(0, 0, 0), hipz=0.0, armL=(2, -2, 0), armR=(4, -2, 0), elbowL=10, elbowR=14)
    return ch


def react(ch, t, gesture="shock", expr="shock", strength=1.0, anticip=0.1):
    """Anticipation (small opposite dip) -> gesture pop with overshoot (acting.act) -> squash accent."""
    ch.pose(t - anticip, hipz=-0.12, torso=(0, 5, 0))
    squash(ch, t - anticip, 0.06)
    ch.act(t, gesture, strength=strength, expr=expr)
    squash(ch, t + 0.08, -0.08); squash(ch, t + 0.25, 0.0)
    ch.pose(t + 0.3, hipz=0.0)
    return ch


# =================================================================== v3.1 automatic character light rig
LOOK_RIG = {   # per-look strength of the character-only rig (key multiplier, rim multiplier)
    "cine_day": (0.55, 1.2), "cine_room": (0.8, 1.5), "cine_night": (1.0, 2.0), "cine_dusk": (0.8, 1.8),
    "day": (0.5, 1.1), "night": (0.9, 1.8), None: (0.7, 1.4),
    # 2026-11-14 ref_* looks (REF_IG_Dfe8B5Hs3G6): softer rim, warm key carries the face. UNRENDERED values.
    "ref_matte": (0.75, 0.6), "ref_day": (0.55, 0.6), "ref_night": (0.9, 0.8), "ref_practical": (0.85, 0.5),
}
# fill/rim colour per look for the character rig; the old default #cfe2ff (sky blue) is what made EP1 faces blueish
LOOK_COOL = {"ref_matte": "#e6e4e0", "ref_day": "#e8e6e2", "ref_night": "#d4d8de", "ref_practical": "#e8e2da"}
AUTO_LIGHT = True          # shotkit calls auto_light() after every shot fn unless a shot sets cast.AUTO_LIGHT = False


def _live_chars():
    out = []
    for ch in list(chars.CHARS.values()):
        try:
            if ch.root.name in D.objects and getattr(ch, "sig", None) is not None:
                out.append(ch)
        except ReferenceError:
            pass
    return out


def light_rig(chs, cam, look=None, strength=1.0, t=None, name="cr"):
    """Key / fill / rim / top / bounce LINKED TO THE CHARACTERS ONLY (receivers), placed from the camera and the
    framed heads at time t (default shot middle). Rim always on (separation from any background).
    look = look name for LOOK_RIG strengths. cam = Cam, camera object or location. Returns the light dict."""
    import bpy
    sc = bpy.context.scene
    if t is not None:
        sc.frame_set(F(t))
    camob = getattr(cam, "ob", cam)
    cl = camob.matrix_world.translation.copy() if hasattr(camob, "matrix_world") else Vector(camob)
    heads = []
    for ch in chs:
        p = ch.head.matrix_world.translation
        if hasattr(camob, "matrix_world") and camob.type == "CAMERA":
            from bpy_extras.object_utils import world_to_camera_view
            v = world_to_camera_view(sc, camob, p)
            if not (-0.3 < v.x < 1.3 and -0.6 < v.y < 1.6 and v.z > 0):
                continue
        heads.append(p.copy())
    if not heads:
        return {}
    f = sum(heads, Vector()) / len(heads)
    dist = (cl - f).length
    k, r = LOOK_RIG.get(look, LOOK_RIG[None])
    s = max(0.8, min(2.4, dist / 9.0))
    kw = {"cool": LOOK_COOL[look]} if look in LOOK_COOL else {}
    if str(look).startswith("ref_t") or (isinstance(look, str) and look.endswith("_t")):
        kw = {"cool": "#e6e4e0"}
    out = cine_light(tuple(f), tuple(cl), scale=s, key=k * strength, rim=r, name=name, receivers=chs, **kw)
    try:
        out["fill"].light_linking.receiver_collection = out["key"].light_linking.receiver_collection
    except (AttributeError, KeyError):
        pass
    return out


def settle_stance():
    """v4.3 (EP3 B-2): runs after every shot fn (from auto_light). The build stance is keyed at t0 - PRE_KEY so poses a
    shot prepares BEFORE t0 (sit, turn, look_at, kneel, hold approach) survive frame 1. Every location/rotation channel
    that the shot did NOT key between the stance and t0 gets a hold key AT t0 with the stance value, so untouched parts
    behave exactly like before (no long stance -> first-key blends that float the feet)."""
    for ch in _live_chars():
        st = getattr(ch, "_stance_t", None)
        if not st or st[0] >= st[1]:
            continue
        f_pre, f0 = F(st[0]), F(st[1])
        for ob in list(ch.coll.all_objects):
            ad = ob.animation_data
            if not ad or not ad.action:
                continue
            for fc in fcurves(ad.action):
                if fc.data_path not in ("location", "rotation_euler"):
                    continue
                fr_ = [k.co[0] for k in fc.keyframe_points]
                if not any(abs(f - f_pre) < 0.5 for f in fr_) or any(f_pre + 0.5 < f <= f0 + 0.5 for f in fr_):
                    continue
                fc.keyframe_points.insert(f0, fc.evaluate(f_pre), options={"FAST"})
                fc.update()
        ch._stance_t = None


def auto_light(look=None):
    """shotkit hook: if the scene has cast members and no shot-made character rig (cine_light 'cl_*' / 'cr_*'),
    add light_rig() for the scene camera. Opt out per shot with cast.AUTO_LIGHT = False."""
    import bpy
    settle_stance()
    sc = bpy.context.scene
    if not AUTO_LIGHT or sc.camera is None:
        return None
    if any(o.type == "LIGHT" and (o.name.startswith("cl_") or o.name.startswith("cr_")) for o in D.objects):
        return None
    chs = _live_chars()
    if not chs:
        return None
    t = (sc.frame_start + sc.frame_end) / 2 / sc.render.fps
    return light_rig(chs, sc.camera, look=look, t=t)
