"""Fire cards, embers, smoke volumes, flicker lights, flashes."""
import math, random
import bpy
from mathutils import Vector
from .core import D, F, plane, sphere, box, light, noise, fcurves, mat, _link


def _time_value(nt, speed=1.0):
    """Value node animated linearly forever (frame-based time)."""
    v = nt.nodes.new("ShaderNodeValue")
    v.outputs[0].default_value = 0.0
    v.outputs[0].keyframe_insert("default_value", frame=0)
    v.outputs[0].default_value = speed * 100
    v.outputs[0].keyframe_insert("default_value", frame=3000)
    for fc in fcurves(nt.animation_data.action):
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
    return v


_FIRE = {}


def fire_material(name="Fire", strength=8.0, speed=0.045, hue="orange"):
    key = (name, strength, hue)
    if key in _FIRE:
        return _FIRE[key]
    m = D.materials.new(name)
    m.use_nodes = True
    m.surface_render_method = "BLENDED"
    m.use_backface_culling = False
    try:
        m.use_transparency_overlap = True
    except Exception:
        pass
    nt = m.node_tree; N, L = nt.nodes, nt.links
    for n in list(N):
        if n.type != "OUTPUT_MATERIAL":
            N.remove(n)
    out = next(n for n in N if n.type == "OUTPUT_MATERIAL")
    tc = N.new("ShaderNodeTexCoord")
    oi = N.new("ShaderNodeObjectInfo")
    t = _time_value(nt, speed)
    # uv -> scrolling noise coords
    sep = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["UV"], sep.inputs[0])
    cmb = N.new("ShaderNodeCombineXYZ")
    rx = N.new("ShaderNodeMath"); rx.operation = "MULTIPLY_ADD"
    L.new(oi.outputs["Random"], rx.inputs[0]); rx.inputs[1].default_value = 37.0
    L.new(sep.outputs["X"], rx.inputs[2])
    ry = N.new("ShaderNodeMath"); ry.operation = "SUBTRACT"
    L.new(sep.outputs["Y"], ry.inputs[0]); L.new(t.outputs[0], ry.inputs[1])
    L.new(rx.outputs[0], cmb.inputs[0]); L.new(ry.outputs[0], cmb.inputs[1]); L.new(oi.outputs["Random"], cmb.inputs[2])
    stretch = N.new("ShaderNodeVectorMath"); stretch.operation = "MULTIPLY"
    stretch.inputs[1].default_value = (2.2, 0.75, 1.0)
    L.new(cmb.outputs[0], stretch.inputs[0])
    nz = N.new("ShaderNodeTexNoise"); nz.noise_dimensions = "3D"
    nz.inputs["Scale"].default_value = 2.6; nz.inputs["Detail"].default_value = 6.0
    nz.inputs["Roughness"].default_value = 0.6; nz.inputs["Distortion"].default_value = 0.4
    L.new(stretch.outputs[0], nz.inputs["Vector"])
    # vertical falloff: 1 at bottom -> 0 at top ; horizontal falloff
    fy = N.new("ShaderNodeMath"); fy.operation = "SUBTRACT"; fy.inputs[0].default_value = 1.0
    L.new(sep.outputs["Y"], fy.inputs[1])
    fx_ = N.new("ShaderNodeMath"); fx_.operation = "SUBTRACT"; fx_.inputs[1].default_value = 0.5
    L.new(sep.outputs["X"], fx_.inputs[0])
    fx2 = N.new("ShaderNodeMath"); fx2.operation = "ABSOLUTE"; L.new(fx_.outputs[0], fx2.inputs[0])
    fx3 = N.new("ShaderNodeMath"); fx3.operation = "MULTIPLY"; fx3.inputs[1].default_value = 2.0
    L.new(fx2.outputs[0], fx3.inputs[0])
    fx4 = N.new("ShaderNodeMath"); fx4.operation = "POWER"; fx4.inputs[1].default_value = 2.0
    L.new(fx3.outputs[0], fx4.inputs[0])
    hx = N.new("ShaderNodeMath"); hx.operation = "SUBTRACT"; hx.inputs[0].default_value = 1.0
    L.new(fx4.outputs[0], hx.inputs[1])
    shape = N.new("ShaderNodeMath"); shape.operation = "MULTIPLY"
    L.new(fy.outputs[0], shape.inputs[0]); L.new(hx.outputs[0], shape.inputs[1])
    # combine with noise : fire = shape*1.5 + (noise-0.5)*1.2 - 0.25
    a = N.new("ShaderNodeMath"); a.operation = "MULTIPLY_ADD"
    L.new(nz.outputs["Fac"], a.inputs[0]); a.inputs[1].default_value = 1.25; a.inputs[2].default_value = -0.85
    b = N.new("ShaderNodeMath"); b.operation = "MULTIPLY_ADD"
    L.new(shape.outputs[0], b.inputs[0]); b.inputs[1].default_value = 1.35; L.new(a.outputs[0], b.inputs[2])
    ramp = N.new("ShaderNodeValToRGB")
    e = ramp.color_ramp.elements
    e[0].position = 0.0; e[0].color = (0, 0, 0, 0)
    e[1].position = 1.0; e[1].color = (1.0, 0.95, 0.75, 1)
    cols = [(0.16, (0.35, 0.02, 0.0, 1)), (0.34, (1.0, 0.12, 0.0, 1)), (0.55, (1.0, 0.35, 0.02, 1)), (0.78, (1.0, 0.62, 0.15, 1))]
    for p, c in cols:
        el = ramp.color_ramp.elements.new(p); el.color = c
    L.new(b.outputs[0], ramp.inputs[0])
    al = N.new("ShaderNodeMapRange"); al.inputs["From Min"].default_value = 0.1; al.inputs["From Max"].default_value = 0.32
    L.new(b.outputs[0], al.inputs["Value"])
    em = N.new("ShaderNodeEmission"); em.inputs["Strength"].default_value = strength
    L.new(ramp.outputs["Color"], em.inputs["Color"])
    tr = N.new("ShaderNodeBsdfTransparent")
    mix = N.new("ShaderNodeMixShader")
    L.new(al.outputs[0], mix.inputs[0]); L.new(tr.outputs[0], mix.inputs[1]); L.new(em.outputs[0], mix.inputs[2])
    L.new(mix.outputs[0], out.inputs["Surface"])
    _FIRE[key] = m
    return m


def fire_card(name, loc, w=2.0, h=3.0, yaw=0.0, coll=None, strength=18.0, tilt=0.0):
    m = fire_material(strength=strength)
    ob = plane(name, w, h, loc, m, (90 + tilt, 0, yaw), None, coll)
    ob.visible_shadow = False
    try:
        ob.visible_volume_scatter = False
    except Exception:
        pass
    return ob


def fire_cluster(prefix, center, spread=(3, 1, 0), n=6, h=(2.5, 4.5), w=(1.5, 2.6), coll=None, seed=1,
                 strength=18.0, yaw_base=0.0):
    rnd = random.Random(seed)
    obs = []
    for i in range(n):
        hh = rnd.uniform(*h); ww = rnd.uniform(*w)
        p = Vector(center) + Vector((rnd.uniform(-1, 1) * spread[0], rnd.uniform(-1, 1) * spread[1],
                                     rnd.uniform(-1, 1) * spread[2] + hh / 2))
        obs.append(fire_card(f"{prefix}{i}", p, ww, hh, yaw_base + rnd.uniform(-35, 35), coll, strength))
    return obs


def ceiling_fire(prefix, center, size=(10, 10), n=10, coll=None, seed=3, strength=14.0):
    """Fire rolling along a ceiling: flame cards hanging down/tilted."""
    rnd = random.Random(seed)
    for i in range(n):
        p = Vector(center) + Vector((rnd.uniform(-0.5, 0.5) * size[0], rnd.uniform(-0.5, 0.5) * size[1], -rnd.uniform(0.3, 1.2)))
        ob = fire_card(f"{prefix}{i}", p, rnd.uniform(3, 6), rnd.uniform(2.5, 4), rnd.uniform(0, 180), coll, strength,
                       tilt=180 + rnd.uniform(-25, 25))


def embers(prefix, region_min, region_max, n=60, coll=None, seed=7, rise=6.0, life=(1.2, 2.6), size=0.035,
           color=(1.0, 0.45, 0.1), strength=40.0):
    """Looping glowing sparks drifting upward (keyframes + cycles + noise, no particle cache)."""
    rnd = random.Random(seed)
    M = mat("ember_" + prefix, (0, 0, 0), emit=color, estr=strength)
    me = None
    for i in range(n):
        p0 = Vector([rnd.uniform(a, b) for a, b in zip(region_min, region_max)])
        L = rnd.uniform(*life)
        ob = sphere(f"{prefix}{i}", size * rnd.uniform(0.6, 1.4), p0, M, coll=coll, seg=6)
        ob.visible_shadow = False
        off = rnd.uniform(0, L)
        f0 = 1 - off * 30
        ob.location = p0
        ob.keyframe_insert("location", frame=f0)
        ob.location = p0 + Vector((rnd.uniform(-1.5, 1.5), rnd.uniform(-1.0, 1.0), rise * rnd.uniform(0.6, 1.2)))
        ob.keyframe_insert("location", frame=f0 + L * 30)
        for fc in fcurves(ob.animation_data.action):
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
            fc.modifiers.new("CYCLES")
            nm = fc.modifiers.new("NOISE"); nm.strength = 0.6; nm.scale = 12; nm.phase = rnd.uniform(0, 100)


def smoke_volume(name, loc, size, coll=None, density=0.25, color=(0.25, 0.2, 0.18), emit=(1.0, 0.35, 0.08),
                 estr=0.15, speed=0.02):
    ob = box(name, size, loc, None, 0.0, coll=coll)
    m = D.materials.new(name + "_mat")
    m.use_nodes = True
    nt = m.node_tree; N, L = nt.nodes, nt.links
    for n in list(N):
        if n.type != "OUTPUT_MATERIAL":
            N.remove(n)
    out = next(n for n in N if n.type == "OUTPUT_MATERIAL")
    pv = N.new("ShaderNodeVolumePrincipled")
    pv.inputs["Color"].default_value = (*color, 1)
    pv.inputs["Emission Color"].default_value = (*emit, 1)
    pv.inputs["Emission Strength"].default_value = estr
    tc = N.new("ShaderNodeTexCoord")
    t = _time_value(nt, speed)
    add = N.new("ShaderNodeVectorMath"); add.operation = "ADD"
    cm = N.new("ShaderNodeCombineXYZ"); L.new(t.outputs[0], cm.inputs[2]); L.new(t.outputs[0], cm.inputs[0])
    L.new(tc.outputs["Object"], add.inputs[0]); L.new(cm.outputs[0], add.inputs[1])
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 1.6; nz.inputs["Detail"].default_value = 4
    L.new(add.outputs[0], nz.inputs["Vector"])
    mr = N.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = 0.42; mr.inputs["From Max"].default_value = 0.75
    mr.inputs["To Max"].default_value = density
    L.new(nz.outputs["Fac"], mr.inputs["Value"]); L.new(mr.outputs[0], pv.inputs["Density"])
    L.new(pv.outputs[0], out.inputs["Volume"])
    ob.data.materials.append(m)
    ob.visible_shadow = False
    return ob


def flicker(light_ob, strength=0.25, scale=3.0):
    """Fire flicker on light energy (relative)."""
    ld = light_ob.data
    base = ld.energy
    ld.keyframe_insert("energy", frame=1)
    for fc in fcurves(ld.animation_data.action):
        if fc.data_path == "energy":
            md = fc.modifiers.new("NOISE"); md.strength = base * strength; md.scale = scale
            md.phase = random.uniform(0, 100)


def fire_lights(prefix, points, energy=3000, color=(1.0, 0.45, 0.12), coll=None, radius=1.5):
    obs = []
    for i, p in enumerate(points):
        lo = light(f"{prefix}{i}", "POINT", p, energy, color, radius, coll=coll)
        flicker(lo, 0.35, 2.5)
        obs.append(lo)
    return obs


def white_flash(name, cam_ob, t0, t1, coll=None):
    """Emissive card parented in front of the camera, fading from white."""
    m = mat(name + "_m", (1, 1, 1), emit=(1, 1, 1), estr=30)
    p = plane(name, 4, 4, (0, 0, -0.3), m, (0, 0, 0), cam_ob, coll)
    return p


# =====================================================================================================================
# v3 TRANSITIONS + MOTION GRAPHICS (REF1). Docs: docs/CAMERA_AND_FX.md. All are per-shot and headless-safe.
# Compositor effects register with look.EXTRA_COMP and are built when shotkit grades the shot.
# =====================================================================================================================
import json as _json
import os as _os


def _fr(t):
    return F(t)


def _keys(sock, pts, interp="BEZIER"):
    """Key a compositor socket default_value at (frame, value) points."""
    for f, v in pts:
        sock.default_value = v
        sock.keyframe_insert("default_value", frame=f)


def _comp(fn, pre=False):
    from . import look
    (look.PRE_COMP if pre else look.EXTRA_COMP).append(fn)


def _ease_pts(f, fin, hold, fout, peak, base=0.0):
    """(frame, value) keys for an eased flash envelope: ease-in (slow start, fast arrival), short hold, ease-out tail.
    Extra mid keys shape the curve so BEZIER cannot overshoot or smear the white across the shot."""
    pts = []
    if fin > 0:
        pts += [(f - fin, base), (f - fin + max(1, round(fin * 0.6)), base + (peak - base) * 0.3)]
    pts += [(f, peak)]
    if hold > 0:
        pts += [(f + hold, peak)]
    if fout > 0:
        e = f + hold
        pts += [(e + max(1, round(fout * 0.3)), base + (peak - base) * 0.45), (e + fout, base)]
    return pts


# R3-1/R3-3: a cut flash is a HARD cut into full white (2 frames, scene exposure +FLASH_EV so AgX clips to 255 -
# the old partial mix of 0.55 at +1.2 EV was a pale grey 'dissolve'), then a 4-frame decay back to the picture.
# 6 frames in all, ALL on shot B, starting on its first frame; the sound cue sits on that exact frame.
FLASH_CUT_MIX = (1.0, 1.0, 0.72, 0.42, 0.18, 0.05, 0.0)    # per frame from the cut
FLASH_CUT_EV = (6.0, 6.0, 2.2, 1.0, 0.4, 0.1, 0.0)
FLASH_EV = 6.0


def cut_time(t):
    """The time of the first rendered frame of a shot that starts at t (frame-exact: what the viewer sees as the cut)."""
    from .core import FPS
    return (F(t) - 1) / float(FPS)


def _key_view(sc, pts):
    base = sc.view_settings.exposure
    for fr, v in pts:
        sc.view_settings.exposure = base + v
        sc.view_settings.keyframe_insert("exposure", frame=fr)
    sc.view_settings.exposure = base


def flash_cut(t, mix=FLASH_CUT_MIX, ev=FLASH_CUT_EV, color=(1, 1, 1), sound=True):
    """Hard white flash ON a cut: call it in shot B at its t0. Frame F(t) and F(t)+1 are pure white (255), then a
    4-frame decay. One key per frame (no BEZIER smear between frames). Registers the 'flash' transition cue at the
    exact cut frame (mix.py: dip -> riser tail -> impact with its attack on that frame)."""
    f = F(t)
    sc = bpy.context.scene
    _key_view(sc, [(f - 1, 0.0)] + [(f + i, v) for i, v in enumerate(ev)])
    if sound:
        from .core import sfx
        sfx(cut_time(t), "flash", 0.9)
        _cue_extra(cut=True, kind="flash", pan=[0.0, 0.0])

    def build(ng, rl, last):
        m = ng.nodes.new("ShaderNodeMix"); m.data_type = "RGBA"
        ng.links.new(last, m.inputs[6]); m.inputs[7].default_value = (*color, 1)
        _keys(m.inputs[0], [(f - 1, 0.0)] + [(f + i, v) for i, v in enumerate(mix)])
        return [o for o in m.outputs if o.type == "RGBA"][0]
    _comp(build)


def flash(t, fin=7, hold=4, fout=10, bloom=1.4, exposure=1.2, color=(1, 1, 1), white=1.0):
    """White flash. Three uses:
    - ACROSS A CUT (the REF1 transition): flash(t0, fin=0, ...) in shot B = flash_cut(t0): hard cut into 2 full-white
      frames + 4-frame decay, sound on the cut frame. The A-side call flash(t1 - x, fout=0) in shot A is now a no-op
      (kept so old shots.py still run): shot A ends on a clean picture frame and the white starts ON the cut.
    - IN-SHOT pop (impact, reveal; fin > 0 and fout > 0): eased bloom + exposure ramp to a FULL white peak (white=1.0
      held max(hold, 2) frames at +FLASH_EV, so it clips to 255 instead of a milky grey), then the eased tail.
    REF1 timing: 6-8 f in, 4-6 f hold, 8-12 f out; values are clamped to that."""
    from .core import sfx
    if fin > 0 and fout <= 0:
        return                       # A-side of a split flash: the B-side does the whole flash on the cut
    if fin <= 0:
        return flash_cut(t, color=color)
    fin, hold, fout = int(min(fin, 8)), int(min(max(hold, 2), 6)), int(min(fout, 12))
    f = _fr(t)
    sc = bpy.context.scene
    base = sc.view_settings.exposure
    pts = _ease_pts(f, fin, 0, fout, exposure)
    pk = [(f + i, FLASH_EV if white >= 1.0 else exposure) for i in range(hold)]
    pts = [p for p in pts if p[0] < f] + pk + [(fr + hold - 1, v) for fr, v in pts if fr > f]
    _key_view(sc, pts)
    try:   # keep the exposure flat outside the flash (fcurves(): Blender 5 layered actions have no .fcurves)
        for fc in fcurves(sc.animation_data.action):
            if fc.data_path.endswith("exposure"):
                for k in fc.keyframe_points:
                    k.interpolation = "BEZIER"; k.handle_left_type = k.handle_right_type = "AUTO_CLAMPED"
    except Exception:
        pass
    sfx(t, "flash", 0.9)
    _cue_extra(cut=True, kind="flash", pan=[0.0, 0.0])

    def build(ng, rl, last):
        gl = ng.nodes.new("CompositorNodeGlare")
        gl.inputs["Type"].default_value = "Bloom"
        gl.inputs["Threshold"].default_value = 0.6
        gl.inputs["Size"].default_value = 1.0
        _keys(gl.inputs["Strength"], _ease_pts(f, fin, hold - 1, fout, bloom))
        ng.links.new(last, gl.inputs["Image"])
        m = ng.nodes.new("ShaderNodeMix"); m.data_type = "RGBA"
        ng.links.new(gl.outputs[0], m.inputs[6]); m.inputs[7].default_value = (*color, 1)
        _keys(m.inputs[0], _ease_pts(f, fin, hold - 1, fout, white))
        return [o for o in m.outputs if o.type == "RGBA"][0]
    _comp(build)


def ghost(path, t0, t1, peak=0.45, fade=12, frame_start=None, sequence=False):
    """Ghost dissolve: overlay another image (a still or a numbered PNG sequence, e.g. the previous shot's last frame
    in videos/<slug>/frames/####.png, or a sepia 'past' render of the SAME place) fading up to `peak` over `fade`
    frames then out. peak=1.0 + fade=12 at the start of a shot = a classic 12 f cross-dissolve from that image."""
    f0, f1 = _fr(t0), _fr(t1)
    img = bpy.data.images.load(path, check_existing=True)
    if sequence:
        img.source = "SEQUENCE"

    def build(ng, rl, last):
        n = ng.nodes.new("CompositorNodeImage")
        n.image = img
        if sequence:
            for k, v in (("frame_duration", 9999), ("frame_start", frame_start or f0), ("frame_offset", 0)):
                try:
                    setattr(n, k, v)
                except Exception:
                    pass
        sc_ = ng.nodes.new("CompositorNodeScale")
        try:
            sc_.inputs["Type"].default_value = "Render Size"
            sc_.inputs["Frame Type"].default_value = "Crop"
        except Exception as e:
            print("ghost scale", e)
        ng.links.new(n.outputs[0], sc_.inputs["Image"])
        m = ng.nodes.new("ShaderNodeMix"); m.data_type = "RGBA"
        ng.links.new(last, m.inputs[6]); ng.links.new(sc_.outputs[0], m.inputs[7])
        if peak >= 0.99:      # straight cross-dissolve FROM the image
            _keys(m.inputs[0], [(f0, 1.0), (f0 + fade, 0.0)])
        else:
            _keys(m.inputs[0], [(f0, 0.0), (f0 + fade, peak), (max(f0 + fade, f1 - fade), peak), (f1, 0.0)])
        return [o for o in m.outputs if o.type == "RGBA"][0]
    _comp(build, pre=True)


def _cam_rot_key(cam_ob, f):
    sc = bpy.context.scene
    sc.frame_set(f)
    cam_ob.keyframe_insert("rotation_euler", frame=f)
    return Vector(cam_ob.rotation_euler)


WHIP = dict(deg=75, frames=5, shutter=1.0)   # ONE setting for both halves: out and in must have the same blur length


def _cue_extra(**kw):
    """Tag the sound cue just registered with core.sfx (render.py keeps extra keys in cues.json)."""
    from . import core
    if core.CUES:
        core.CUES[-1].update(kw)


def whip(cam_a, t1, cam_b, t0=None, deg=None, frames=None, shutter=None):
    """Matched whip-pan cut: whip_out on shot A + whip_in on shot B with identical angle, frame count and shutter
    (mismatched halves read as a jump). One whoosh, its peak ON the cut."""
    d, n, sh = deg or WHIP["deg"], frames or WHIP["frames"], shutter or WHIP["shutter"]
    whip_out(cam_a, t1, d, n, sh)
    whip_in(cam_b, t1 if t0 is None else t0, d, n, sh)


def whip_out(cam_ob, t1, deg=75, frames=5, shutter=1.0):
    """Whip-pan OUT at the end of a shot: the last `frames` frames yaw by deg with full motion blur. Pair with
    whip_in(next_cam, t0, same sign) on the next shot; SFX whoosh is added."""
    from .core import sfx
    from . import look
    fe = _fr(t1) - 1
    fs = fe - frames
    _cam_rot_key(cam_ob, fs)
    r = _cam_rot_key(cam_ob, fe)
    cam_ob.rotation_euler = (r.x, r.y, r.z + math.radians(deg))
    cam_ob.keyframe_insert("rotation_euler", frame=fe)
    from .core import set_interp
    set_interp(cam_ob, "rotation_euler", fs, "BEZIER", "EASE_IN")
    look.motion_blur(shutter)
    sfx(t1, "whoosh", 1.0)   # mix.py designs the whip sound: whoosh PEAK + low hit ATTACK on the cut
    # yaw +deg = camera turns left: the whoosh sweeps right -> left with it (and the other way for -deg)
    sg = 1.0 if deg >= 0 else -1.0
    _cue_extra(cut=True, kind="whip", pan=[0.7 * sg, -0.7 * sg])


def whip_in(cam_ob, t0, deg=75, frames=5, shutter=1.0):
    """Whip-pan IN at the start of a shot (lands on the framing `frames` frames in)."""
    from . import look
    fs = _fr(t0)
    fe = fs + frames
    r = _cam_rot_key(cam_ob, fe)
    _cam_rot_key(cam_ob, fs)
    cam_ob.rotation_euler = (r.x, r.y, r.z - math.radians(deg))
    cam_ob.keyframe_insert("rotation_euler", frame=fs)
    from .core import set_interp
    set_interp(cam_ob, "rotation_euler", fs, "BEZIER", "EASE_OUT")
    look.motion_blur(shutter)


def push_through(cam_ob, t, frames=6, mode="in", color=(0.02, 0.02, 0.025), side=1):
    """Push-through-dark-object wipe: a dark blocky shape (door frame / pillar / passer-by) slides across the lens.
    mode "in": covers the frame by the END of the shot (call with t = shot end). mode "out": starts covering at the
    shot START and clears (call with t = shot start). Cut between the two = invisible join. side = +1/-1 direction.
    Near-black budget: exactly ONE fully covered frame across the cut (the last frame of the "in" shot), <= 2 frames
    that are >= 50 % dark in total. How: the card ACCELERATES into full cover (QUAD ease-in) and the "out" half is keyed
    one frame early with QUAD ease-out, so its first rendered frame is already ~30 % open and moving fast. (The old
    LINEAR setter used action.fcurves, which does not exist on Blender 5 layered actions: the keys stayed BEZIER and the
    card lingered over the lens for 4-5 frames.)"""
    from .core import fcurves
    cd = cam_ob.data
    dist = 0.5
    sens_h = cd.sensor_height
    half_h = dist * (sens_h / 2) / cd.lens
    half_w = half_h * 9 / 16
    m = mat("pushthru_m", color, 0.6)
    ob = box("pushthru", (half_w * 2.15, half_h * 2.6, 0.05), (0, 0, -dist), m, bev=0.02, parent=cam_ob)
    ob.visible_shadow = False
    off = side * half_w * 2.2
    frames = max(2, int(frames))
    if mode == "in":
        a, b = _fr(t) - frames, _fr(t) - 1          # full cover on the LAST frame of this shot only
        xs, ease = ((a, off), (b, 0.0)), "EASE_IN"
    else:
        a, b = _fr(t) - 1, _fr(t) - 1 + frames      # x=0 one frame BEFORE this shot: first frame already opening
        xs, ease = ((a, 0.0), (b, -off)), "EASE_OUT"
    for fr, x in xs:
        ob.location.x = x
        ob.keyframe_insert("location", index=0, frame=fr)
    for fc in fcurves(ob.animation_data.action):
        for k in fc.keyframe_points:
            k.interpolation = "QUAD"
            k.easing = ease
    if mode == "in":   # ONE transition sound per push (the "out" half is the same cut): low swoosh + thud on the cut,
        from .core import sfx   # panned the way the card travels (side +1: right -> left). Was silent before (R2 D7).
        sfx(t, "push", 0.9)
        _cue_extra(cut=True, kind="push", pan=[0.7 * side, -0.7 * side])
    return ob


# ------------------------------------------------------------------ match cut helper
def _match_path(path=None):
    return path or _os.path.join(_os.environ.get("RBX_VIDEO_DIR", bpy.app.tempdir or "/tmp"), "match_cuts.json")


def match_save(name, cam_ob, subject, t, path=None):
    """Store the camera's framing relative to `subject` at time t (end of shot A)."""
    sc = bpy.context.scene
    sc.frame_set(_fr(t))
    s = Vector(subject.location if hasattr(subject, "location") else subject)
    mw = cam_ob.matrix_world
    data = {}
    p = _match_path(path)
    if _os.path.exists(p):
        data = _json.load(open(p))
    data[name] = dict(off=list(mw.translation - s), rot=list(mw.to_euler()), lens=cam_ob.data.lens,
                      sensor=cam_ob.data.sensor_height)
    _json.dump(data, open(p, "w"))
    return data[name]


def match_frame(name, cam, subject, t0, t1, drift=0.06, path=None):
    """Start shot B with the SAME framing on a new subject (match cut), then a small eased push (drift fraction)."""
    d = _json.load(open(_match_path(path)))[name]
    s = Vector(subject.location if hasattr(subject, "location") else subject)
    off = Vector(d["off"])
    cam.cd.sensor_height = d["sensor"]; cam.cd.lens = d["lens"]
    from mathutils import Euler
    for tt, k in ((t0, 0.0), (t1, drift)):
        cam.ob.location = s + off * (1 - k)
        cam.ob.rotation_euler = Euler(d["rot"])
        cam.ob.keyframe_insert("location", frame=_fr(tt)); cam.ob.keyframe_insert("rotation_euler", frame=_fr(tt))
    cam.cd.keyframe_insert("lens", frame=_fr(t0))
    return cam


# ------------------------------------------------------------------ flashback dust, siren, practicals, signs
def dust(cam_ob, n=50, seed=4, color=(1.0, 0.9, 0.7), strength=3.0, size=0.006, depth=(0.8, 6.0)):
    """Floating dust / confetti specks in front of the camera (sepia flashbacks, sunbeams)."""
    rnd = random.Random(seed)
    m = mat("dust_m", color, 0.5, emit=color, estr=strength)
    cd = cam_ob.data
    obs = []
    for i in range(n):
        z = rnd.uniform(*depth)
        hh = z * (cd.sensor_height / 2) / cd.lens
        x, y = rnd.uniform(-hh * 0.6, hh * 0.6), rnd.uniform(-hh, hh)
        s = sphere(f"dust{i}", size * z ** 0.5 * rnd.uniform(0.6, 1.6), (x, y, -z), m, parent=cam_ob, seg=6)
        s.visible_shadow = False
        for k in range(3):
            noise(s, "location", k, 0.04 * z ** 0.5, rnd.uniform(40, 90), rnd.uniform(0, 100))
        obs.append(s)
    return obs


def siren(loc, t0, t1, hz=4.0, energy=250.0, color=(1.0, 0.05, 0.03), r=0.35, coll=None):
    """Flickering emergency light: red emissive dome + point light, on/off at hz (REF1: 4 Hz, 0<->20 emission)."""
    m = mat("siren_m", color, 0.3, emit=color, estr=20.0)
    dome = sphere("siren", r, loc, m, coll=coll, scale=(1, 1, 0.7))
    lo = light("siren_L", "POINT", (loc[0], loc[1], loc[2] + r * 0.2), energy, color, 0.2, coll=coll)
    node = next(nd for nd in m.node_tree.nodes if nd.type == "BSDF_PRINCIPLED")
    es = node.inputs["Emission Strength"]
    period = 1.0 / hz
    t, on = t0, True
    while t <= t1 + period:
        f = _fr(t)
        es.default_value = 20.0 if on else 0.4
        es.keyframe_insert("default_value", frame=f)
        lo.data.energy = energy if on else 0.0
        lo.data.keyframe_insert("energy", frame=f)
        t += period / 2; on = not on
    for idb in (m.node_tree, lo.data):
        for fc in fcurves(idb.animation_data.action):
            for kp in fc.keyframe_points:
                kp.interpolation = "CONSTANT"
    return dome, lo


def practical(loc, color=(1.0, 0.6, 0.35), energy=60.0, r=0.18, estr=12.0, coll=None, name="lantern"):
    """Warm practical (lantern / window bulb) for cine_night: emissive bead + small point light."""
    m = mat(name + "_m", color, 0.4, emit=color, estr=estr)
    s = sphere(name, r, loc, m, coll=coll, seg=12)
    s.visible_shadow = False
    lo = light(name + "_L", "POINT", loc, energy, color, r, coll=coll)
    return s, lo


def sign(body, loc, rot=(90, 0, 0), size=1.2, fg=(1, 1, 1), bg=(0.85, 0.06, 0.05), t_pop=None, coll=None,
         board=True, emit=0.8):
    """In-world title card (e.g. 'FAKE!' sign, scoreboard, banner): bold extruded text on a board, optional pop-in
    with 15 % overshoot at t_pop. Returns the root empty."""
    from .core import text, empty
    root = empty("sign_root", loc, coll=coll, rot=rot)
    tm = mat("sign_txt_m", fg, 0.4, emit=fg, estr=emit)
    t = text("sign_txt", body, (0, 0, 0.06), size, tm, rot=(0, 0, 0), extrude=0.04, coll=coll, parent=root)
    try:
        t.data.offset = 0.02          # thick black-ish outline look comes from the board edge + bevel
        t.data.bevel_depth = 0.01
    except Exception:
        pass
    if board:
        bpy.context.view_layer.update()
        w = max(len(body) * size * 0.62, size * 1.5)
        bm = mat("sign_bg_m", bg, 0.5)
        box("sign_board", (w + size * 0.5, size * 1.5, 0.08), (0, 0, 0), bm, bev=0.05, parent=root, coll=coll)
        om = mat("sign_edge_m", (0.02, 0.02, 0.02), 0.5)
        box("sign_edge", (w + size * 0.7, size * 1.7, 0.06), (0, 0, -0.03), om, bev=0.06, parent=root, coll=coll)
    if t_pop is not None:
        f = _fr(t_pop)
        for fr, s in ((f, 0.01), (f + 5, 1.15), (f + 9, 0.95), (f + 12, 1.0)):
            root.scale = (s, s, s)
            root.keyframe_insert("scale", frame=fr)
    return root
