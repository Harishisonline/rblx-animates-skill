"""Look development: lighting rigs, colour grade and bloom so frames read as polished, not flat.

Why this exists (see research/LOOK.md): the reference channels (gibbsontv, harotalks, atlassdoc, Moon Animator
shorts) all have WARM/COOL light contrast, a rim light that separates the subject, soft shadows, real depth of
field, small bloom on bright things, and a mild saturation/contrast grade. The v1 kit used one flat sky + sun.

Usage inside a shot (after the set and characters exist):

    from rbx import look
    look.rig("night", focus=(0, -30, 4), cam_yaw=0)      # key + fill + rim around the subject
    ...
    # the grade (bloom, saturation, contrast, split tone) is applied automatically at the end of every shot
    # by shotkit using V.look (set once per video: V.look = "neon").

Presets: day, dusk, night, interior, neon (AI / cyberpunk), horror, story_warm (cosy amber key, soft shadows; pair with
fstop 1.8-2.8 cams for shallow DoF).
Every preset is a dict, copy and tweak: look.PRESETS["mine"] = dict(look.PRESETS["night"], bloom=0.5)."""
import math
import bpy
from mathutils import Vector
from .core import D, F, light, world, aim
from . import world as W

PRESETS = {
    #            world colour / strength      sun: strength, colour, rot (deg)           grade
    "day":      dict(world=("sky", 1.0), sun=(3.4, (1.0, 0.93, 0.82), (48, 0, 35)), key=None,
                     fill=(0.9, (0.75, 0.85, 1.0)), rim=(2200, (1.0, 0.95, 0.85)),
                     sat=1.14, contrast=1.06, gain=1.0, bloom=0.30, shadows=(0.96, 0.98, 1.04), lights=(1.04, 1.0, 0.94)),
    "dusk":     dict(world=((0.55, 0.38, 0.45), 0.9), sun=(2.2, (1.0, 0.62, 0.38), (12, 0, 70)), key=None,
                     fill=(0.7, (0.55, 0.6, 0.9)), rim=(2600, (1.0, 0.7, 0.45)),
                     sat=1.18, contrast=1.08, gain=1.0, bloom=0.40, shadows=(0.9, 0.95, 1.1), lights=(1.1, 1.0, 0.88)),
    "night":    dict(world=((0.08, 0.11, 0.26), 0.9), sun=(1.5, (0.62, 0.72, 1.0), (32, 0, 205)), key=(1800, (1.0, 0.8, 0.55)),
                     fill=(0.6, (0.45, 0.55, 1.0)), rim=(3000, (0.55, 0.7, 1.0)),
                     sat=1.12, contrast=1.10, gain=1.0, bloom=0.40, shadows=(0.88, 0.94, 1.12), lights=(1.1, 1.0, 0.9)),
    "interior": dict(world=((0.18, 0.18, 0.24), 0.5), sun=None, key=(2600, (1.0, 0.82, 0.58)),
                     fill=(0.5, (0.7, 0.8, 1.0)), rim=(2200, (0.6, 0.75, 1.0)),
                     sat=1.10, contrast=1.08, gain=1.0, bloom=0.30, shadows=(0.92, 0.96, 1.08), lights=(1.08, 1.0, 0.9)),
    "neon":     dict(world=((0.06, 0.08, 0.2), 1.0), sun=(0.8, (0.5, 0.6, 1.0), (30, 0, 200)), key=(4200, (0.75, 0.9, 1.0)),
                     fill=(2.0, (1.0, 0.75, 0.85)), rim=(3600, (1.0, 0.3, 0.75)),
                     sat=1.25, contrast=1.14, gain=1.0, bloom=0.65, shadows=(0.8, 0.9, 1.25), lights=(1.2, 1.0, 0.9)),
    # warm cosy story look (reference: soft amber key, deep soft shadow side, subtle cool rim, shallow DoF, light bloom)
    "story_warm": dict(world=((0.30, 0.24, 0.20), 0.35), sun=None, key=(5200, (1.0, 0.74, 0.48)),
                     fill=(0.22, (0.62, 0.7, 1.0)), rim=(1500, (0.6, 0.75, 1.0)),
                     sat=1.08, contrast=1.12, gain=1.0, bloom=0.22, shadows=(0.95, 0.96, 1.06), lights=(1.06, 1.0, 0.92)),
    "horror":   dict(world=((0.03, 0.04, 0.06), 0.4), sun=None, key=(1500, (1.0, 0.62, 0.35)),
                     fill=(0.2, (0.4, 0.5, 0.8)), rim=(2000, (0.45, 0.6, 1.0)),
                     sat=0.95, contrast=1.16, gain=0.95, bloom=0.35, shadows=(0.85, 0.95, 1.1), lights=(1.1, 1.0, 0.9)),
}


def _sun(strength, color, rot, angle=1.5):
    ld = D.lights.new("look_sun", "SUN")
    ld.energy = strength
    ld.color = color
    ld.angle = math.radians(angle)
    ob = D.objects.new("look_sun", ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.rotation_euler = [math.radians(a) for a in rot]
    return ob


def rig(preset="day", focus=(0, 0, 4), cam_yaw=0.0, scale=1.0, sky=True):
    """Lights the subject at `focus`. cam_yaw: direction the camera sits on (0 = camera on the -Y side of focus,
    90 = camera on the +X side). Key + fill come from the camera side, the rim from behind the subject.
    Returns dict of the light objects."""
    p = _resolve(PRESETS[preset] if isinstance(preset, str) else preset)
    f = Vector(focus)
    y = math.radians(cam_yaw)
    toward_cam = Vector((math.sin(y), -math.cos(y), 0))        # unit vector from subject to camera
    side = Vector((math.cos(y), math.sin(y), 0))
    out = {}
    wc, ws = p["world"]
    if wc == "sky":
        if sky:
            W.sky(ws)
    else:
        world(wc, ws)
    if p.get("sun"):
        s, c, r = p["sun"]
        out["sun"] = _sun(s * scale, c, r)
    if p.get("key"):
        e, c = p["key"]
        pos = f + toward_cam * 7 * scale + side * -4 * scale + Vector((0, 0, 5 * scale))
        out["key"] = light("look_key", "AREA", tuple(pos), e * scale, c, 4.5 * scale, target=tuple(f + Vector((0, 0, 0))))
    if p.get("fill"):
        e, c = p["fill"]
        if p.get("sun") is None or p["world"][0] == "sky":
            pass
        pos = f + toward_cam * 9 * scale + side * 5 * scale + Vector((0, 0, 3 * scale))
        out["fill"] = light("look_fill", "AREA", tuple(pos), 420 * e * scale, c, 7 * scale, target=tuple(f))
    if p.get("rim"):
        e, c = p["rim"]
        pos = f - toward_cam * 7 * scale + side * 3 * scale + Vector((0, 0, 7 * scale))
        out["rim"] = light("look_rim", "AREA", tuple(pos), e * scale, c, 3.5 * scale, target=tuple(f + Vector((0, 0, 3))))
    return out


EXPOSURE = 0.0


def exposure(v):
    """Per-shot exposure (stops) set from inside a shot; shotkit applies it (exposure.json still overrides)."""
    global EXPOSURE
    EXPOSURE = float(v)


def fog(density=0.012, color=(0.6, 0.7, 1.0), anisotropy=0.4):
    """Light atmospheric volume (god-ray feel under a sun/spot). Cheap values only: 0.005-0.02."""
    w = bpy.context.scene.world
    if w is None:
        return
    w.use_nodes = True
    nt = w.node_tree
    out = next(n for n in nt.nodes if n.type == "OUTPUT_WORLD")
    sc = nt.nodes.new("ShaderNodeVolumeScatter")
    sc.inputs["Density"].default_value = density
    sc.inputs["Color"].default_value = (*color, 1)
    sc.inputs["Anisotropy"].default_value = anisotropy
    nt.links.new(sc.outputs[0], out.inputs["Volume"])


def grade(preset="day", bloom=None, sat=None, contrast=None):
    """Replace the compositor with: bloom -> saturation/contrast -> warm lights / cool shadows split tone."""
    p = _resolve(PRESETS[preset] if isinstance(preset, str) else preset)
    sc = bpy.context.scene
    ng = D.node_groups.new("LookComp", "CompositorNodeTree")
    ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    rl = ng.nodes.new("CompositorNodeRLayers")
    last = rl.outputs["Image"]
    for fn in list(PRE_COMP):          # e.g. fx.ghost: mixed in BEFORE the grade so it is graded like the shot
        try:
            last = fn(ng, rl, last)
        except Exception as e:
            print("pre comp", e)
    gl = ng.nodes.new("CompositorNodeGlare")
    try:
        gl.inputs["Type"].default_value = "Bloom"
        gl.inputs["Quality"].default_value = "Medium"
        gl.inputs["Threshold"].default_value = 1.0
        gl.inputs["Strength"].default_value = p["bloom"] if bloom is None else bloom
        gl.inputs["Size"].default_value = 0.7
    except Exception as e:
        print("glare", e)
    ng.links.new(last, gl.inputs["Image"])
    last = gl.outputs[0]
    try:
        cc = ng.nodes.new("CompositorNodeColorCorrection")
        ins = [i for i in cc.inputs]
        ins[2].default_value = p["sat"] if sat is None else sat          # master saturation
        ins[3].default_value = p["contrast"] if contrast is None else contrast
        ins[5].default_value = p["gain"]
        ng.links.new(last, cc.inputs["Image"])
        last = cc.outputs[0]
    except Exception as e:
        print("colorcorrection", e)
    try:
        cb = ng.nodes.new("CompositorNodeColorBalance")
        for i in cb.inputs:
            if i.name == "Type":
                i.default_value = "Lift/Gamma/Gain"
        lifts = [i for i in cb.inputs if i.name == "Lift"]
        gains = [i for i in cb.inputs if i.name == "Gain"]
        sh = p["shadows"]; li = p["lights"]
        for i in lifts:
            if i.type == "RGBA":
                i.default_value = (sh[0], sh[1], sh[2], 1.0)
        for i in gains:
            if i.type == "RGBA":
                i.default_value = (li[0], li[1], li[2], 1.0)
        ng.links.new(last, cb.inputs["Image"])
        last = cb.outputs[0]
    except Exception as e:
        print("colorbalance", e)
    last = _grade_extra(ng, rl, last, p)
    for fn in list(EXTRA_COMP):
        try:
            last = fn(ng, rl, last)
        except Exception as e:
            print("extra comp", e)
    global VIEW_LOOK
    if p.get("view_look") and VIEW_LOOK is None:
        VIEW_LOOK = p["view_look"]
    out = ng.nodes.new("NodeGroupOutput")
    ng.links.new(last, out.inputs[0])
    sc.compositing_node_group = ng
    sc.render.use_compositing = True


def finish(preset="day"):
    """Called by shotkit at the end of every shot build."""
    grade(preset)


def ground_contact(ob_or_loc, r=1.0, strength=0.55, name="contact"):
    """Soft dark blob under a prop so it feels grounded (cheap fake contact shadow)."""
    from .core import mat, plane
    m = mat("contact_shadow_m", (0, 0, 0), 1.0, alpha=strength)
    loc = ob_or_loc.location if hasattr(ob_or_loc, "location") else ob_or_loc
    p = plane(name, r * 2, r * 2, (loc[0], loc[1], 0.02), m)
    return p


def hdri(path_or_name, strength=1.0, rotation=0.0):
    """Use an HDRI (assets/hdri/*.hdr, fetched with tools/assets.py) as the world: realistic reflections and ambient
    colour on glossy plastic. Pass a file name like "dresden_station_night_1k.hdr" or a full path."""
    import os
    import rbx
    p = path_or_name if os.path.isabs(path_or_name) else os.path.join(rbx.ASSETS, "hdri", path_or_name)
    if not os.path.exists(p):
        print("hdri missing:", p, "(run: python tools/assets.py starter)")
        return False
    w = D.worlds.new("HDRI")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    bg = next(n for n in nt.nodes if n.type == "BACKGROUND")
    tex = nt.nodes.new("ShaderNodeTexEnvironment")
    tex.image = bpy.data.images.load(p)
    mp = nt.nodes.new("ShaderNodeMapping")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp.inputs["Rotation"].default_value[2] = math.radians(rotation)
    nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Color"], bg.inputs[0])
    bg.inputs[1].default_value = strength
    return True


# =====================================================================================================================
# v3 CINEMATIC LOOK (REF1 mid-key: YAVG ~91, YLOW ~43, YHIGH ~151, sat moderate). See docs/CAMERA_AND_FX.md.
#   look.cinematic("cine_day", focus=(0,0,4), cam_yaw=0)   # lights + render quality + grade settings for this shot
#   look.motion_blur(0.5)                                   # per-shot shutter (0 = off, 0.5 = 180 deg, 1.0 = whip)
# Extra grade keys understood by grade(): vignette (0-0.3), haze=(r,g,b) + haze_amt + mist=(start, depth),
# tint=(r,g,b) multiply (sepia), desat (0-1), view_look (AgX look name).
# =====================================================================================================================
PRESETS.update({
    # day: warm key #FFE9C8 sun 30 deg elevation, cool sky fill, cool rim, AgX medium-high contrast
    "cine_day": dict(world=("sky", 1.0), sun=(4.5, (1.0, 0.914, 0.784), (58, 0, 35)), key=None,
                     fill=(0.55, (0.62, 0.77, 0.91)), rim=(2600, (0.75, 0.85, 1.0)),
                     sat=1.06, contrast=1.10, gain=1.0, bloom=0.08, shadows=(0.93, 0.98, 1.03), lights=(1.04, 1.0, 0.95),
                     vignette=0.18, haze=(0.56, 0.65, 0.71), haze_amt=0.4, mist=(40.0, 260.0),
                     view_look="AgX - Medium High Contrast"),
    # interior day: big warm window key, cool bounce fill at ~15 %
    "cine_room": dict(world=((0.55, 0.65, 0.8), 0.35), sun=None, key=(3200, (1.0, 0.945, 0.86)),
                      fill=(0.35, (0.62, 0.77, 0.91)), rim=(2000, (0.75, 0.85, 1.0)),
                      sat=1.06, contrast=1.10, gain=1.0, bloom=0.08, shadows=(0.93, 0.98, 1.03), lights=(1.04, 1.0, 0.95),
                      vignette=0.18, view_look="AgX - Medium High Contrast"),
    # night: indigo moon key + amber practicals (add lanterns/windows with fx.practical), faces keep a warm fill
    "cine_night": dict(world=((0.063, 0.094, 0.18), 1.0), sun=(0.45, (0.56, 0.66, 1.0), (40, 0, 210)),
                       key=(900, (1.0, 0.6, 0.35)), fill=(0.45, (0.45, 0.55, 1.0)), rim=(2600, (0.6, 0.72, 1.0)),
                       sat=0.98, contrast=1.08, gain=1.0, bloom=0.22, shadows=(0.88, 0.94, 1.10), lights=(1.08, 1.0, 0.9),
                       vignette=0.22, haze=(0.12, 0.16, 0.30), haze_amt=0.5, mist=(30.0, 200.0),
                       view_look="AgX - Medium High Contrast"),
    # horror: cold low-key, sickly desat, heavy vignette, one dim warm practical
    "night_dread": dict(world=((0.02, 0.03, 0.05), 1.0), sun=(0.15, (0.5, 0.62, 0.9), (35, 0, 160)),
                        key=(1100, (0.95, 0.7, 0.45)), fill=(0.22, (0.35, 0.45, 0.7)), rim=(1800, (0.45, 0.6, 1.0)),
                        sat=0.82, contrast=1.16, gain=0.96, bloom=0.15, shadows=(0.86, 0.95, 1.06), lights=(1.0, 1.0, 0.95),
                        vignette=0.32, haze=(0.05, 0.07, 0.09), haze_amt=0.7, mist=(15.0, 90.0),
                        view_look="AgX - High Contrast"),
    # sepia flashback (use on top of the scene's own lights: look.grade("sepia") or V.look="sepia" for that shot)
    "sepia": dict(world=("sky", 1.0), sun=(4.0, (1.0, 0.75, 0.45), (78, 0, 60)), key=None,
                  fill=(0.5, (1.0, 0.9, 0.75)), rim=(2400, (1.0, 0.8, 0.55)),
                  sat=1.0, contrast=1.15, gain=1.02, bloom=0.15, shadows=(1.0, 1.0, 1.0), lights=(1.0, 1.0, 1.0),
                  desat=0.85, tint=(1.0, 0.70, 0.34), vignette=0.25, view_look="AgX - Medium High Contrast"),
})

# ---- 2026-11-14 REF_IG_Dfe8B5Hs3G6 look (docs/research/REF_IG_Dfe8B5Hs3G6.md) -------------------------------------
# UNRENDERED / visually untested: values derived from measurements, not from a test render. Tune with
# tools/grade_check.py until it prints PASS (targets: blue-minus-red ~+3 (|B-R| <= 5 day/interior, <= 12 night),
# HSV sat ~0.30, p2 luma ~17, median ~49, p98 ~124 on 8-bit frames).
# Differences vs cine_*: NO blue-lifted shadows (shadows=(1,1,1)), NEUTRAL fill/rim (no sky-blue 0.62/0.77/0.91),
# one warm practical key, desat 0.25 on top of sat 0.85, lower contrast, lifted black + rolled highlight
# (keys lift / roll, handled in _grade_extra), exposure -0.6 stop, vignette 0.28, AgX Base Contrast.
REF_TARGETS = dict(b_minus_r=3.0, b_minus_r_tol=5.0, b_minus_r_night_max=12.0, sat=0.30, sat_tol=0.06,
                   p2=17.0, p2_tol=5.0, p50=49.0, p50_tol=12.0, p98=124.0, p98_tol=40.0)
NEUTRAL_FILL = (0.86, 0.86, 0.86)
PRESETS.update({
    # day/interior master: grey-neutral ambient, warm practical key (~2900 K), faint warm rim
    "ref_matte": dict(world=((0.42, 0.42, 0.42), 0.35), sun=None, key=(2600, (1.0, 0.80, 0.56)),
                      fill=(0.28, NEUTRAL_FILL), rim=(900, (1.0, 0.94, 0.86)),
                      sat=0.85, contrast=0.95, gain=0.97, bloom=0.08, shadows=(1.0, 1.0, 1.0), lights=(1.03, 1.0, 0.97),
                      desat=0.25, lift=0.006, roll=0.80, vignette=0.28, exposure=-0.6,
                      view_look="AgX - Base Contrast"),
    # exterior day variant: keep the sky, sun warm-white, neutral fill
    "ref_day": dict(world=("sky", 0.8), sun=(3.6, (1.0, 0.93, 0.82), (52, 0, 35)), key=None,
                    fill=(0.35, NEUTRAL_FILL), rim=(1200, (1.0, 0.95, 0.88)),
                    sat=0.85, contrast=0.95, gain=0.97, bloom=0.08, shadows=(1.0, 1.0, 1.0), lights=(1.03, 1.0, 0.97),
                    desat=0.25, lift=0.006, roll=0.82, vignette=0.25, exposure=-0.4,
                    haze=(0.55, 0.55, 0.56), haze_amt=0.35, mist=(40.0, 260.0), view_look="AgX - Base Contrast"),
    # night: grey-slate moon (weak, barely blue), warm windows/practicals carry the colour, deep but lifted blacks
    "ref_night": dict(world=((0.05, 0.055, 0.065), 1.0), sun=(0.35, (0.80, 0.84, 0.92), (40, 0, 210)),
                      key=(700, (1.0, 0.74, 0.48)), fill=(0.22, (0.70, 0.72, 0.76)), rim=(1200, (0.85, 0.88, 0.95)),
                      sat=0.85, contrast=0.97, gain=0.96, bloom=0.10, shadows=(1.0, 1.0, 1.0), lights=(1.02, 1.0, 0.98),
                      desat=0.2, lift=0.005, roll=0.78, vignette=0.32, exposure=-0.5,
                      haze=(0.10, 0.105, 0.115), haze_amt=0.5, mist=(30.0, 200.0), view_look="AgX - Base Contrast"),
    # interior lit ONLY by a warm practical (lamp/doorway/porch); use fx.practical / town lamps for the source itself
    "ref_practical": dict(world=((0.30, 0.30, 0.31), 0.18), sun=None, key=(3200, (1.0, 0.74, 0.46)),
                          fill=(0.14, NEUTRAL_FILL), rim=(600, (1.0, 0.86, 0.70)),
                          sat=0.85, contrast=0.97, gain=0.97, bloom=0.10, shadows=(1.0, 1.0, 1.0), lights=(1.04, 1.0, 0.95),
                          desat=0.22, lift=0.006, roll=0.80, vignette=0.32, exposure=-0.7,
                          view_look="AgX - Base Contrast"),
})
# v4.0 CLEAN STYLE (2026-11-15, user: "the video has a dusty look", ref instagram.com/p/Dfe8B5Hs3G6 = crisp plastic,
# real dark shadows, natural colour). STYLE="clean" turns every preset into its clean version at resolve time:
# no black lift (milky toe), no distance haze, no desaturation, AgX Medium High Contrast, light vignette, tiny bloom.
# STYLE="matte" restores the v3.6 ref_* look exactly.
STYLE = "clean"
CLEAN = dict(lift=0.0, haze_amt=0.0, desat=0.0, sat=1.0, roll=0.96, contrast=1.04, bloom=0.04,
             view_look="AgX - Medium High Contrast", vignette_max=0.18, exposure_add=0.25)


def _resolve(p):
    if STYLE != "clean" or p.get("keep_style"):
        return p
    q = dict(p)
    for k in ("lift", "haze_amt", "desat", "sat", "roll", "contrast", "bloom", "view_look"):
        q[k] = CLEAN[k]
    q["vignette"] = min(p.get("vignette", 0.0) or 0.0, CLEAN["vignette_max"])
    q["exposure"] = (p.get("exposure", 0.0) or 0.0) + CLEAN["exposure_add"]
    return q


DEFAULT_PRESET = "ref_matte"     # shotkit's default V.look; old presets (day/night/cine_*/story_warm...) stay selectable


def ref(base="ref_matte", warmth=0.0, sat=None, desat=None, lift=None, roll=None, exposure=None, vignette=None, name=None):
    """Tunable copy of a ref_* preset. warmth: -1..+1 nudges key colour and lights gain (+ = warmer, - = cooler).
    Registers PRESETS[name] (default base+'_t') and returns the name, e.g. V.look = look.ref(warmth=0.2, desat=0.3)."""
    p = dict(PRESETS[base])
    if warmth:
        e, c = p["key"] if p.get("key") else (None, None)
        if c:
            p["key"] = (e, (1.0, max(0.0, min(1.0, c[1] - 0.06 * warmth)), max(0.0, min(1.0, c[2] - 0.12 * warmth))))
        l = p["lights"]
        p["lights"] = (l[0] + 0.03 * warmth, l[1], l[2] - 0.03 * warmth)
    for k, v in dict(sat=sat, desat=desat, lift=lift, roll=roll, exposure=exposure, vignette=vignette).items():
        if v is not None:
            p[k] = v
    name = name or base + "_t"
    PRESETS[name] = p
    return name


VIEW_LOOK = None          # set by cinematic()/grade(); shotkit applies it instead of its default "AgX - Punchy"
SHUTTER = None


def motion_blur(shutter=0.5, steps=1):
    """Per-shot motion blur (camera + object, EEVEE, works headless). shutter: 0 off, 0.5 = 180 deg (runs, aerials),
    1.0 = whip/fly-through smear. steps>1 = smoother curved blur (cost x steps)."""
    global SHUTTER
    sc = bpy.context.scene
    sc.render.use_motion_blur = shutter > 0
    if shutter > 0:
        sc.render.motion_blur_shutter = shutter
        sc.render.motion_blur_position = "CENTER"
        try:
            sc.eevee.motion_blur_steps = steps
            sc.eevee.motion_blur_max = 64
        except Exception:
            pass
    SHUTTER = shutter
    return shutter


def quality(ao=True, raytrace=True, dof=True):
    """Render quality for the cinematic look: EEVEE raytracing + fast-GI AO (contact darkening), jittered bokeh."""
    ee = bpy.context.scene.eevee
    try:
        ee.use_raytracing = raytrace
        ee.use_fast_gi = ao
        ee.fast_gi_method = "GLOBAL_ILLUMINATION"
        ee.fast_gi_distance = 2.5
        ee.fast_gi_quality = 0.5
        ee.use_bokeh_jittered = dof
        ee.bokeh_max_size = 100
    except Exception as e:
        print("quality", e)


def cinematic(preset="ref_matte", focus=(0, 0, 4), cam_yaw=0.0, scale=1.0, sky=True, blur=None):
    """One call per shot: lighting rig + AO/raytrace + mist pass for haze + remembers the grade for shotkit.
    Grade itself is applied by shotkit at the end (V.look), or call look.grade(preset) yourself."""
    out = rig(preset, focus, cam_yaw, scale, sky)
    quality()
    p = _resolve(PRESETS[preset])
    if p.get("mist") and p.get("haze_amt"):
        haze_setup(*p["mist"])
    if blur is not None:
        motion_blur(blur)
    global VIEW_LOOK
    VIEW_LOOK = p.get("view_look")
    if p.get("exposure") is not None:
        exposure(p["exposure"])
    return out


def haze_setup(start=40.0, depth=250.0):
    """Distance haze via the mist pass (cheap, no volume): grade() mixes the preset's haze colour by mist."""
    sc = bpy.context.scene
    sc.view_layers[0].use_pass_mist = True
    if sc.world:
        ms = sc.world.mist_settings
        ms.start, ms.depth, ms.falloff = start, depth, "QUADRATIC"


def _mix(ng, a, b, fac=1.0, blend="MIX"):
    m = ng.nodes.new("ShaderNodeMix")
    m.data_type = "RGBA"
    m.blend_type = blend
    m.clamp_result = False
    m.inputs[0].default_value = fac
    ng.links.new(a, m.inputs[6])
    if isinstance(b, (tuple, list)):
        m.inputs[7].default_value = (*b[:3], 1.0)
    else:
        ng.links.new(b, m.inputs[7])
    return m, [o for o in m.outputs if o.type == "RGBA"][0]


def _grade_extra(ng, rl, last, p):
    """Haze, sepia (desat + tint), vignette. Returns new last socket."""
    sc = bpy.context.scene
    if p.get("haze") and p.get("haze_amt") and sc.view_layers[0].use_pass_mist:
        try:
            mist = rl.outputs["Mist"]
            mm = ng.nodes.new("ShaderNodeMath"); mm.operation = "MULTIPLY"
            ng.links.new(mist, mm.inputs[0]); mm.inputs[1].default_value = p["haze_amt"]
            m, last = _mix(ng, last, p["haze"], 0.0)
            ng.links.new(mm.outputs[0], m.inputs[0])
        except Exception as e:
            print("haze", e)
    if p.get("desat"):
        hs = ng.nodes.new("CompositorNodeHueSat")
        hs.inputs["Saturation"].default_value = 1.0 - p["desat"]
        ng.links.new(last, hs.inputs["Image"]); last = hs.outputs[0]
    if p.get("tint"):
        _, last = _mix(ng, last, tuple(p["tint"]), 1.0, "MULTIPLY")
    if p.get("roll") or p.get("lift"):
        # matte toe + highlight roll-off (linear, pre view transform): out = lift + in * (roll - lift)
        try:
            lift, roll = float(p.get("lift", 0.0)), float(p.get("roll", 1.0))
            _, last = _mix(ng, last, (roll - lift,) * 3, 1.0, "MULTIPLY")
            _, last = _mix(ng, last, (lift,) * 3, 1.0, "ADD")
        except Exception as e:
            print("lift/roll", e)
    if p.get("vignette"):
        try:
            em = ng.nodes.new("CompositorNodeEllipseMask")
            em.inputs["Size"].default_value = (0.95, 0.75)
            bl = ng.nodes.new("CompositorNodeBlur")
            w = sc.render.resolution_x * sc.render.resolution_percentage / 100
            bl.inputs["Size"].default_value = (w * 0.35, w * 0.35)
            ng.links.new(em.outputs[0], bl.inputs["Image"])
            mr = ng.nodes.new("ShaderNodeMapRange")
            mr.inputs["To Min"].default_value = 1.0 - p["vignette"]
            mr.inputs["To Max"].default_value = 1.0
            ng.links.new(bl.outputs[0], mr.inputs["Value"])
            m = ng.nodes.new("ShaderNodeMix"); m.data_type = "RGBA"; m.blend_type = "MULTIPLY"
            m.inputs[0].default_value = 1.0
            ng.links.new(last, m.inputs[6]); ng.links.new(mr.outputs[0], m.inputs[7])
            last = [o for o in m.outputs if o.type == "RGBA"][0]
        except Exception as e:
            print("vignette", e)
    return last


PRE_COMP = []             # callables(ng, rl, last) -> last, run before the grade (fx.ghost)
EXTRA_COMP = []           # callables(ng, rl, last) -> last, appended by fx (flash, ghost dissolve); run after grade
