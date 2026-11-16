"""PBR material library for the 'real world / toy people' look (REF2 tier A). CC0 Poly Haven 1k textures live in
assets/tex/pbr/<key>/{diff,nor,arm}.jpg (see assets/ASSETS_LOG.md). Every material is box-projected in OBJECT space at a
real-world texel density (tile = metres per texture repeat in scene units; a Roblox character is ~5.3 units tall), so
any core.box()/cyl() gets correct texturing with no UVs. Edge highlight comes from the core.box bevel (harden normals)
plus a subtle fresnel-ish layer weight brightening; AO from the arm map's R channel multiplies base colour (EEVEE-cheap).

    from rbx import pbr
    m = pbr.get("brick")                          # default tint/scale
    m = pbr.get("plaster", tint="#f1e3c4")         # tinted (multiply) - cream, ochre, mint walls from one texture
    m = pbr.get("planks", tile=4.0, rot=90)        # bigger boards, rotated 90 deg around Z
    pbr.KEYS -> list of materials. Missing texture files fall back to a flat colour (never crashes).
Keys: cobble brick plaster planks steel asphalt grass concrete tile fabric roof woodfloor timber.
EEVEE speed: 1k jpgs, one image node per map, no displacement, no parallax."""
import math, os
from .core import D, hexc
from . import ASSETS

PBR_DIR = os.path.join(ASSETS, "tex", "pbr")
# key: (tile size in scene units, fallback hex, roughness mult, metallic, normal strength)
SPEC = {
    "cobble":    (6.0, "#8a8278", 1.0, 0.0, 1.0),
    "brick":     (5.0, "#9a4a36", 1.0, 0.0, 1.0),
    "plaster":   (8.0, "#e9e0cc", 1.0, 0.0, 0.5),
    "planks":    (5.0, "#8a5a36", 1.0, 0.0, 0.8),
    "steel":     (5.0, "#7d848c", 0.8, 0.9, 1.0),
    "asphalt":   (10.0, "#3c3c3e", 1.0, 0.0, 0.7),
    "grass":     (7.0, "#4f7a2e", 1.0, 0.0, 0.7),
    "concrete":  (7.0, "#a8a49c", 1.0, 0.0, 0.8),
    "tile":      (6.0, "#d8d6d0", 0.8, 0.0, 0.6),
    "fabric":    (2.0, "#3e5a8a", 1.0, 0.0, 0.6),
    "roof":      (6.0, "#9a4a32", 1.0, 0.0, 1.0),
    "woodfloor": (6.0, "#9a6a40", 0.9, 0.0, 0.6),
    "timber":    (5.0, "#5a4030", 1.0, 0.0, 0.8),
}
KEYS = list(SPEC)


def _img(path, non_color=False):
    im = D.images.load(path, check_existing=True)
    if non_color:
        try:
            im.colorspace_settings.name = "Non-Color"
        except TypeError:
            pass
    return im


def get(key, tint=None, tile=None, rot=0.0, rough=None, name=None, emissive=0.0, ao=1.0):
    """Return (cached) PBR material. tint '#rrggbb' multiplies base colour; tile overrides texture repeat size."""
    t0, fb, rmul, metal, nstr = SPEC[key]
    tile = tile or t0
    nm = name or f"pbr_{key}_{tint or 'x'}_{tile:g}_{rot:g}"
    if nm in D.materials:
        return D.materials[nm]
    m = D.materials.new(nm); m.use_nodes = True
    nt = m.node_tree; N, L = nt.nodes, nt.links
    b = next(n for n in N if n.type == "BSDF_PRINCIPLED")
    b.inputs["Metallic"].default_value = metal
    d = os.path.join(PBR_DIR, key)
    have = os.path.exists(os.path.join(d, "diff.jpg"))
    col_out = None
    if have:
        tc = N.new("ShaderNodeTexCoord")
        mp = N.new("ShaderNodeMapping")
        s = 1.0 / tile
        mp.inputs["Scale"].default_value = (s, s, s)
        mp.inputs["Rotation"].default_value = (0, 0, math.radians(rot))
        L.new(tc.outputs["Object"], mp.inputs[0])

        def tex(fn, nc):
            n = N.new("ShaderNodeTexImage"); n.image = _img(os.path.join(d, fn), nc)
            n.projection = "BOX"; n.projection_blend = 0.25
            L.new(mp.outputs[0], n.inputs[0]); return n
        dif = tex("diff.jpg", False)
        col_out = dif.outputs["Color"]
        arm_p = os.path.join(d, "arm.jpg")
        if os.path.exists(arm_p):
            arm = tex("arm.jpg", True)
            sep = N.new("ShaderNodeSeparateColor"); L.new(arm.outputs["Color"], sep.inputs[0])
            # AO multiply (cheap cavity darkening)
            mao = N.new("ShaderNodeMix"); mao.data_type = "RGBA"; mao.blend_type = "MULTIPLY"
            mao.inputs[0].default_value = ao
            L.new(col_out, mao.inputs[6]); L.new(sep.outputs[0], mao.inputs[7]); col_out = mao.outputs[2]
            rm = N.new("ShaderNodeMath"); rm.operation = "MULTIPLY"; rm.inputs[1].default_value = rough or rmul
            L.new(sep.outputs[1], rm.inputs[0]); L.new(rm.outputs[0], b.inputs["Roughness"])
            if metal > 0:
                L.new(sep.outputs[2], b.inputs["Metallic"])
        nor_p = os.path.join(d, "nor.jpg")
        if os.path.exists(nor_p):
            nn = tex("nor.jpg", True)
            nm_ = N.new("ShaderNodeNormalMap"); nm_.inputs["Strength"].default_value = nstr
            L.new(nn.outputs["Color"], nm_.inputs["Color"]); L.new(nm_.outputs[0], b.inputs["Normal"])
    else:
        b.inputs["Roughness"].default_value = 0.7
    if tint:
        c = hexc(tint)
        if col_out is None:
            b.inputs["Base Color"].default_value = (*c, 1)
        else:
            mt = N.new("ShaderNodeMix"); mt.data_type = "RGBA"; mt.blend_type = "MULTIPLY"
            mt.inputs[0].default_value = 1.0
            # brighten texture first so a tint reads as the tint, not muddy
            br = N.new("ShaderNodeBrightContrast"); br.inputs["Bright"].default_value = 0.25
            L.new(col_out, br.inputs[0])
            L.new(br.outputs[0], mt.inputs[6]); mt.inputs[7].default_value = (*c, 1)
            col_out = mt.outputs[2]
    if col_out is not None:
        L.new(col_out, b.inputs["Base Color"])
    elif not tint:
        b.inputs["Base Color"].default_value = (*hexc(fb), 1)
    if emissive:
        b.inputs["Emission Strength"].default_value = emissive
        if col_out is not None:
            L.new(col_out, b.inputs["Emission Color"])
    m.diffuse_color = (*hexc(tint or fb), 1)
    return m


def paint(hx, rough=0.45, name=None):
    """Clean painted/plastic surface for trims, frames, toy-ish props (non-PBR but consistent naming)."""
    from .core import mat
    return mat(name or f"paint_{hx}", hexc(hx), rough)


def glow(hx, strength=6.0):
    from .core import mat
    return mat(f"glow_{hx}_{strength:g}", hexc(hx), 0.4, emit=hexc(hx), estr=strength)


def swatch_board(origin=(0, 0, 0), coll=None):
    """Debug: one bevelled cube per material in a row (render to judge the library)."""
    from .core import box, text
    for i, k in enumerate(KEYS):
        x = origin[0] + (i % 7) * 5.5
        y = origin[1] + (i // 7) * 6
        box(f"sw_{k}", (4, 4, 4), (x, y, origin[2] + 2), get(k), 0.15, coll=coll)
        text(f"swt_{k}", k.upper(), (x, y - 2.3, origin[2] + 0.5), 0.6, glow("#ffffff", 2), coll=coll)
