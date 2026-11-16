"""Expressive acting layer on top of rbx.chars.Char: layered faces (eyes + mouth), named
expressions, blinks, lip flaps, gestures with overshoot, nods, head turns, jumps, run cycles.
Import order: chars first, then acting (it patches methods onto Char)."""
import math, os, random
from mathutils import Vector
from . import ASSETS
from .core import D, F, fcurves, set_interp
from . import chars as C

# eye / mouth cell indices (see tools/make_faces_layered.py)
EYE = dict(normal=0, wide=1, half=2, closed=3, happy=4, squint=5, side_l=6, side_r=7, terror=8,
           worried=9, angry=10, scared=11, wink=12, up=13, down=14, cry=15)
MOUTH = dict(flat=0, smile=1, open_smile=2, laugh=3, frown=4, o=5, talk=6, talk_wide=7, grimace=8,
             grimace_wide=9, scream=10, smirk=11, wavy=12, yawn=13, grin=14, ah=15)
# v3.7 (REF_IG_Dfs43n3oWqx FACIAL EXPRESSION SPEC) - UNRENDERED. New cells live in a 5x5 atlas (indices 16-24).
# A style's atlas grid comes from assets/faces/<style>_<layer>.json {"grid": 5}; without it the atlas is the old 4x4 and
# every new name FALLS BACK to the nearest existing cell (EYE_FALLBACK / MOUTH_FALLBACK), so old atlases never go blank.
EYE.update(half_up=16, closed_happy=17, dots=18, ring=19, worried_l=20, worried_r=21, tear1=22)
MOUTH.update(dash=16, o_small=17, cat_w=18, wavy_side=19, frown_wobble=20, grin_top=21, grin_full=22, scream_tongue=23)
EYE_FALLBACK = dict(half_up="half", closed_happy="happy", dots="normal", ring="wide", worried_l="side_l",
                    worried_r="side_r", tear1="cry")
MOUTH_FALLBACK = dict(dash="flat", o_small="o", cat_w="smile", wavy_side="smirk", frown_wobble="wavy",
                      grin_top="open_smile", grin_full="grin", scream_tongue="scream")
CLOSED_EYES = ("closed", "happy", "wink", "closed_happy")      # a blink is never keyed over these
EXPR = {
    "neutral": ("normal", "flat"), "happy": ("normal", "open_smile"), "joy": ("happy", "laugh"),
    "smile": ("normal", "smile"), "grin": ("happy", "grin"), "shock": ("wide", "grimace"),
    "gasp": ("wide", "o"), "terror": ("terror", "grimace_wide"), "scream": ("scared", "scream"),
    "worried": ("worried", "frown"), "angry": ("angry", "grimace"), "furious": ("angry", "scream"),
    "smug": ("half", "smirk"), "bored": ("half", "flat"), "sleepy": ("half", "wavy"),
    "yawn": ("closed", "yawn"), "sus": ("squint", "wavy"), "side_l": ("side_l", "frown"),
    "side_r": ("side_r", "frown"), "wink": ("wink", "smirk"), "cry": ("cry", "ah"),
    "scared": ("scared", "frown"), "talk": ("normal", "talk"), "shout": ("angry", "talk_wide"),
    "determined": ("angry", "flat"), "relief": ("closed", "smile"), "confused": ("squint", "o"),
    "lookup": ("up", "o"), "lookdown": ("down", "frown"), "panic": ("terror", "scream"),
    # v3.7 named expressions (REF_IG_Dfs43n3oWqx), UNRENDERED
    "blank": ("dots", "dash"), "pop_shock": ("ring", "o_small"), "sad_tear": ("tear1", "flat"),
    "worried_dart": ("worried", "frown_wobble"), "smug_up": ("half_up", "wavy_side"), "content": ("closed_happy", "cat_w"),
    "laugh_smug": ("half", "grin_top"), "toothy": ("happy", "grin_full"), "angry_shout": ("angry", "scream_tongue"),
}
# ladder presets (REF spec 8: base -> shock 6-8 f -> big laugh/scream -> shock -> cut)
LADDERS = {
    "surprise_laugh": ["smug", "pop_shock", "toothy", "pop_shock"],
    "surprise_scream": ["neutral", "pop_shock", "angry_shout", "pop_shock"],
    "anger_to_worry": ["angry_shout", "worried_dart"],
}
REF_BLINK_EVERY = (2.5, 4.0)    # REF: ~1 blink / 2.5-4 s on held shots
BLINK_CLOSED = 3 / 30           # 2-4 f closed; 3 f
DART_EVERY = 4.5 / 30           # pupils jump every 4-5 f
DART_REST = 7 / 30              # rest centre 6-8 f between bursts
LADDER_STEP = 7 / 30            # 6-8 f per ladder step


# ------------------------------------------------------------------ layered face material
def layered_face_material(name, style, skin):
    """Head material that projects an eyes atlas and a mouth atlas onto the head front."""
    m = D.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree; N, L = nt.nodes, nt.links
    b = next(n for n in N if n.type == "BSDF_PRINCIPLED")
    tc = N.new("ShaderNodeTexCoord"); sep = N.new("ShaderNodeSeparateXYZ")
    L.new(tc.outputs["Object"], sep.inputs[0])

    def M(op, a, bv=None):
        n = N.new("ShaderNodeMath"); n.operation = op
        (L.new(a, n.inputs[0]) if not isinstance(a, float) else setattr(n.inputs[0], "default_value", a))
        if bv is not None:
            (L.new(bv, n.inputs[1]) if not isinstance(bv, float) else setattr(n.inputs[1], "default_value", bv))
        return n.outputs[0]
    u = M("ADD", M("DIVIDE", sep.outputs["X"], C.FACE_W), 0.5)
    v = M("ADD", M("DIVIDE", M("SUBTRACT", sep.outputs["Z"], C.FACE_Z), C.FACE_H), 0.5)
    mask = M("MULTIPLY", M("MULTIPLY", M("MULTIPLY", M("GREATER_THAN", u, 0.0), M("LESS_THAN", u, 1.0)),
                              M("MULTIPLY", M("GREATER_THAN", v, 0.0), M("LESS_THAN", v, 1.0))),
             M("LESS_THAN", sep.outputs["Y"], -0.05))
    cmb = N.new("ShaderNodeCombineXYZ"); L.new(u, cmb.inputs[0]); L.new(v, cmb.inputs[1])
    col = N.new("ShaderNodeRGB"); col.name = "Skin"; col.outputs[0].default_value = (*skin, 1)
    cur = col.outputs[0]
    alphas = []
    for layer in ("eyes", "mouth"):
        mp = N.new("ShaderNodeMapping"); mp.name = "EyeMap" if layer == "eyes" else "MouthMap"
        g = atlas_grid(style, layer); mp["grid"] = g          # v3.7: 4x4 legacy or 5x5 atlas
        mp.vector_type = "POINT"; mp.inputs["Scale"].default_value = (1.0 / g, 1.0 / g, 1)
        mp.inputs["Location"].default_value = _cell(0, g)
        L.new(cmb.outputs[0], mp.inputs[0])
        tx = N.new("ShaderNodeTexImage")
        tx.image = D.images.load(os.path.join(ASSETS, "faces", f"{style}_{layer}.png"), check_existing=True)
        tx.extension = "CLIP"; tx.interpolation = "Cubic"
        L.new(mp.outputs[0], tx.inputs[0])
        a = M("MULTIPLY", tx.outputs["Alpha"], mask)
        mix = N.new("ShaderNodeMix"); mix.data_type = "RGBA"
        L.new(a, mix.inputs[0]); L.new(cur, mix.inputs[6]); L.new(tx.outputs["Color"], mix.inputs[7])
        cur = mix.outputs[2]; alphas.append(a)
    L.new(cur, b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.62
    try:
        b.inputs["Specular IOR Level"].default_value = 0.3
    except KeyError:
        pass
    m.diffuse_color = (*skin, 1)
    return m


def atlas_grid(style, layer):
    """4 (legacy 4x4 atlas) unless assets/faces/<style>_<layer>.json says {"grid": 5}."""
    try:
        import json as _j
        return int(_j.load(open(os.path.join(ASSETS, "faces", f"{style}_{layer}.json"))).get("grid", 4))
    except Exception:
        return 4


def resolve_cell(layer, name, grid=4):
    """Cell index for an eye/mouth name on an atlas of size grid x grid; names that do not exist on a 4x4 atlas fall
    back to their nearest legacy cell. Ints pass through. Pure function (no Blender)."""
    if not isinstance(name, str):
        return name
    table, fb = (EYE, EYE_FALLBACK) if layer == "eyes" else (MOUTH, MOUTH_FALLBACK)
    idx = table[name]
    while idx >= grid * grid and name in fb:
        name = fb[name]; idx = table[name]
    return idx


def _cell(idx, grid=4):
    s = 1.0 / grid
    return ((idx % grid) * s, (grid - 1 - idx // grid) * s, 0)


def _key_map(ch, node, idx, t):
    nt = ch.face_mat.node_tree
    mp = nt.nodes[node]
    mp.inputs["Location"].default_value = _cell(idx, _grid(ch, node))
    mp.inputs["Location"].keyframe_insert("default_value", frame=F(t))
    for fc in fcurves(nt.animation_data.action):
        for kp in fc.keyframe_points:
            kp.interpolation = "CONSTANT"


def _grid(ch, node="EyeMap"):
    try:
        return int(ch.face_mat.node_tree.nodes[node].get("grid", 4))
    except Exception:
        return 4


def _eye(ch, name):
    return resolve_cell("eyes", name, _grid(ch, "EyeMap"))


def _mouth(ch, name):
    return resolve_cell("mouth", name, _grid(ch, "MouthMap"))


def _layered(ch):
    return ch.face_mat is not None and "EyeMap" in ch.face_mat.node_tree.nodes


def face(ch, t, expr=None, eyes=None, mouth=None):
    """face(t, "shock") | face(t, eyes="wide", mouth="scream") | legacy int index."""
    if not _layered(ch):
        return C.Char._face_legacy(ch, t, expr)
    if isinstance(expr, str):
        e, m_ = EXPR[expr]
        eyes = eyes or e; mouth = mouth or m_
    if eyes is not None:
        ei = _eye(ch, eyes)
        _key_map(ch, "EyeMap", ei, t); ch._eye_track.append((t, ei))
        # v3.2: blinks keyed earlier reopen to the eye cell that was current when THEY were keyed; re-key the
        # reopen of every later blink so an expression swap is not undone by the next blink.
        for tb in getattr(ch, "_blinks", ()):
            if tb + 0.1 > t - 1e-6:
                cur = _eye_at(ch, tb + 0.1)
                if abs(tb - t) < 0.02:
                    continue
                _key_map(ch, "EyeMap", cur, tb + 0.1)
    if mouth is not None:
        mi = _mouth(ch, mouth)
        _key_map(ch, "MouthMap", mi, t); ch._mouth_track.append((t, mi))
    return ch


def _eye_at(ch, t):
    best = (-1e9, EYE["normal"])
    for tt, e in ch._eye_track:
        if tt <= t and tt >= best[0]:
            best = (tt, e)
    return best[1]


def blink_schedule(t0, t1, every=REF_BLINK_EVERY, closed=BLINK_CLOSED, skip=(), seed=0):
    """Pure blink plan: list of (t_close, t_open). No blink inside any skip window (t_a, t_b) (ladders, darts, tear
    holds) or within 0.12 s of its edges. Pure function, testable without Blender."""
    rnd = random.Random(seed)
    out, t = [], t0 + rnd.uniform(0.3, every[0])
    while t < t1 - closed - 0.02:
        if not any(a - 0.12 <= t <= b + 0.12 for a, b in skip):
            out.append((round(t, 4), round(t + closed, 4)))
        t += rnd.uniform(*every)
    return out


def _busy(ch):
    return ch.__dict__.setdefault("_face_busy", [])


def _clear_blinks(ch, a, b):
    """Undo already-keyed blinks inside [a, b] (cast._finish keys blinks before a later ladder/dart is added)."""
    keep = []
    for tb in getattr(ch, "_blinks", []):
        if a - 0.12 <= tb <= b + 0.12:
            _key_map(ch, "EyeMap", _eye_at(ch, tb), tb)      # the closed key becomes the eye that is current there
        else:
            keep.append(tb)
    ch._blinks = keep


def blink(ch, t0, t1, every=REF_BLINK_EVERY, seed=None, closed=BLINK_CLOSED):
    """Auto blinks (3 frames closed) where the eyes are open. v3.7: default every=(2.5, 4.0) s (REF_IG_Dfs43n3oWqx; was
    1.8-3.6) and no blinks inside ladder()/dart() windows registered on the character."""
    if not _layered(ch):
        return ch
    sd = seed if seed is not None else hash(ch.name) % 1000
    closed_ids = {_eye(ch, n) for n in CLOSED_EYES}
    for t, t_open in blink_schedule(t0, t1, every, closed, _busy(ch), sd):
        cur = _eye_at(ch, t)
        nxt = [tt for tt, _ in ch._eye_track if t - 0.02 < tt < t + 0.15]
        if cur not in closed_ids and not nxt:
            _key_map(ch, "EyeMap", _eye(ch, "closed"), t)
            _key_map(ch, "EyeMap", cur, t_open)
            ch.__dict__.setdefault("_blinks", []).append(t)
    return ch


def ladder_plan(t, exprs, step=LADDER_STEP):
    """Pure plan for a reaction ladder: [(t_i, expr_name)], hard swaps every `step` s. exprs may be a LADDERS key."""
    seq = LADDERS[exprs] if isinstance(exprs, str) else list(exprs)
    for e in seq:
        if e not in EXPR:
            raise KeyError(f"ladder: unknown expression '{e}'")
    return [(round(t + i * step, 4), e) for i, e in enumerate(seq)]


def ladder(ch, t, exprs="surprise_laugh", step=LADDER_STEP, hold_last=None):
    """Reaction ladder (REF spec 8): hard decal swaps base -> pop_shock -> big laugh/scream -> pop_shock, 6-8 f each.
    Align t to the beat word / SFX frame. Blinks are suppressed in the window. Returns the end time (cut there).
    UNRENDERED (data only; uses the existing face() atlas swap)."""
    plan = ladder_plan(t, exprs, step)
    end = plan[-1][0] + (hold_last if hold_last is not None else step)
    if _layered(ch):
        _busy(ch).append((t, end)); _clear_blinks(ch, t, end)
    for tt, e in plan:
        face(ch, tt, e)
    return end


def dart_plan(t0, t1, every=DART_EVERY, burst=(3, 5), rest=DART_REST, seed=0, left="worried_l", right="worried_r",
              centre="worried"):
    """Pure plan for fear eye darts (REF spec 9): pupils jump L/R every 4-5 f, 3-5 darts per burst, rest centre 6-8 f.
    Returns [(t, eye_name)] starting and ending on `centre`."""
    rnd = random.Random(seed)
    out, t, side = [(round(t0, 4), centre)], t0 + rest, rnd.random() < 0.5
    while t < t1 - every:
        for _ in range(rnd.randint(*burst)):
            if t >= t1 - every:
                break
            out.append((round(t, 4), left if side else right)); side = not side; t += every
        if t < t1 - rest:
            out.append((round(t, 4), centre)); t += rest
    if out[-1][1] != centre:
        out.append((round(min(t, t1), 4), centre))
    return out


def dart(ch, t0, t1, every=DART_EVERY, seed=None, mouth="frown_wobble", **kw):
    """Worried eye darts over a fear hold [t0, t1] (keys CONSTANT via the atlas). Blinks suppressed. Returns the plan.
    UNRENDERED: on a 4x4 atlas worried_l/r fall back to side_l/side_r."""
    plan = dart_plan(t0, t1, every, seed=seed if seed is not None else hash(ch.name) % 1000, **kw)
    if _layered(ch):
        _busy(ch).append((t0, t1)); _clear_blinks(ch, t0, t1)
        face(ch, t0, mouth=mouth)
        for tt, e in plan:
            face(ch, tt, eyes=e)
    return plan


def talk(ch, t0, t1, words=None, open_m="talk", wide_m="talk_wide", rest="flat", syll=0.12):
    """Lip flaps. With words ([{start,end}] or [{s,e}]) flap per word, else at a syllable rate."""
    if not _layered(ch):
        return ch
    k = 0
    if words:
        for w in words:
            s = w.get("start", w.get("s")); e = w.get("end", w.get("e"))
            if s is None or s < t0 or s >= t1:
                continue
            face(ch, s, mouth=open_m if k % 3 else wide_m)
            if e - s > 0.22:
                face(ch, s + (e - s) * 0.5, mouth=rest)
                face(ch, s + (e - s) * 0.7, mouth=open_m)
            k += 1
        face(ch, t1, mouth=rest)
    else:
        t = t0
        while t < t1:
            face(ch, t, mouth=(open_m, wide_m, rest, open_m)[k % 4]); k += 1; t += syll
        face(ch, t1, mouth=rest)
    return ch


# ------------------------------------------------------------------ gestures
G = {
    "idle": dict(armL=(2, -2), armR=(5, -3, -4), elbowL=10, elbowR=20, torso=(0, 0, 0), head=(0, 0, 0)),
    "shock": dict(armL=(35, 55), armR=(35, 55), torso=(0, -8, 0), head=(0, -10, 0)),
    "hands_head": dict(armL=(155, 30), armR=(155, 30), torso=(0, -4, 0), head=(0, 4, 0)),
    "hands_face": dict(armL=(140, -25), armR=(140, -25), head=(0, 6, 0)),
    "cheer": dict(armL=(170, 30), armR=(170, 30), head=(0, -18, 0), torso=(0, -6, 0)),
    "point": dict(armR=(92, -6), armL=(10, 8), head=(-8, 0, 0)),
    "point_l": dict(armL=(92, -6), armR=(10, 8), head=(8, 0, 0)),
    "shrug": dict(armL=(35, 38), armR=(35, 38), head=(0, 0, 12), torso=(0, 0, 4)),
    "recoil": dict(armL=(55, 30), armR=(55, 30), torso=(0, -14, 0), head=(0, -12, 0)),
    "lean": dict(torso=(0, 16, 0), head=(0, -10, 0), armL=(20, -2), armR=(14, -3), elbowL=20, elbowR=12),
    "slump": dict(torso=(0, 20, 0), head=(0, 28, 0), armL=(2, -2), armR=(0, -3), elbowL=8, elbowR=14),
    "think": dict(armR=(125, -38), armL=(40, -30), head=(12, 6, 8)),
    "cross": dict(armL=(80, -48), armR=(80, -48), head=(0, -4, 0)),
    "phone": dict(armR=(150, -42), armL=(15, 10), head=(-10, 0, 8)),
    "reach": dict(armR=(95, 4), armL=(70, 10), torso=(0, 12, 0)),
    "push": dict(armL=(90, -8), armR=(90, -8), torso=(0, 14, 0)),
    "hold": dict(armL=(75, -14), armR=(75, -14)),
    "wave": dict(armR=(165, 25), armL=(5, 6)),
    "fists": dict(armL=(60, 20), armR=(60, 20), torso=(0, 6, 0), head=(0, 4, 0)),
    "facepalm": dict(armR=(140, -30), head=(0, 18, 0), torso=(0, 8, 0)),
    "brace": dict(armL=(80, 40), armR=(80, 40), torso=(0, -10, 0), head=(0, 10, 0), hipz=-0.25),
}


def _scale(v, k):
    return tuple(x * k for x in v)


def act(ch, t, name, strength=1.0, settle=0.22, overshoot=0.18, expr=None, antic=3, **extra):
    """Pose pop: reaches 1+overshoot at ~45% of settle, settles to the pose at t+settle.
    antic>0 (frames, default 3) routes through motion.strike: holds the previous pose, dips the opposite way,
    head leads by 2 f, so the move reads as anticipation -> action -> overshoot -> settle. antic=0 = legacy pop."""
    p = dict(G[name]); p.update(extra)
    if antic:
        from . import motion
        pose = {k: (_scale(v, strength) if isinstance(v, tuple) else v * strength) for k, v in p.items()}
        hit = t + settle * 0.45
        motion.strike(ch, hit, pose, antic=antic, move=max(2, int(round(settle * 0.45 * 30))),
                      settle=max(2, int(round(settle * 0.55 * 30))), over=overshoot)
        if expr:
            face(ch, t, expr)
        return ch
    k_over = 1.0 + overshoot
    over = {k: (_scale(v, strength * k_over) if isinstance(v, tuple) else v * strength * k_over) for k, v in p.items()}
    final = {k: (_scale(v, strength) if isinstance(v, tuple) else v * strength) for k, v in p.items()}
    ch.pose(t + settle * 0.45, **over)
    ch.pose(t + settle, **final)
    if expr:
        face(ch, t, expr)
    return ch


def hold_pose(ch, t, name=None, **kw):
    """Key the current pose at t (to hold it until a later act)."""
    p = dict(G[name]) if name else {}
    p.update(kw)
    ch.pose(t, **p)
    return ch


def wiggle(ch, t0, t1, part="armL", amp=(25, 15), rate=7.0, base=(140, 30)):
    """Oscillating limb (panic flail, waving)."""
    t, k = t0, 0
    while t <= t1:
        s = 1 if k % 2 == 0 else -1
        ch.pose(t, **{part: (base[0] + amp[0] * s, base[1] + amp[1] * s)})
        t += 1.0 / rate; k += 1
    return ch


def panic(ch, t0, t1, rate=7.0):
    wiggle(ch, t0, t1, "armL", (30, 20), rate, (140, 35))
    wiggle(ch, t0 + 0.5 / rate, t1, "armR", (30, 20), rate, (140, 35))
    return ch


def nod(ch, t, n=2, amp=12, rate=6.0):
    for i in range(n):
        ch.pose(t + i / rate, head=(0, amp, 0)); ch.pose(t + (i + 0.5) / rate, head=(0, -amp * 0.3, 0))
    ch.pose(t + n / rate, head=(0, 0, 0))
    return ch


def shake(ch, t, n=3, amp=18, rate=7.0):
    for i in range(n):
        s = 1 if i % 2 == 0 else -1
        ch.pose(t + i / rate, head=(amp * s, 0, 0))
    ch.pose(t + n / rate, head=(0, 0, 0))
    return ch


def look(ch, t, yaw=0, pitch=0, roll=0, settle=0.18):
    """Head snap with overshoot."""
    ch.pose(t + settle * 0.5, head=(yaw * 1.15, pitch * 1.15, roll))
    ch.pose(t + settle, head=(yaw, pitch, roll))
    return ch


def jump(ch, t, height=1.6, dur=0.5, loc=None):
    """Hop in place (or from loc) with crouch anticipation and landing squash."""
    base = Vector(loc) if loc else Vector(ch.root.location)
    ch.pose(t, hipz=-0.35, armL=(-20, 10), armR=(-20, 10), loc=tuple(base))
    ch.pose(t + dur * 0.15, hipz=0.0)
    ch.pose(t + dur * 0.5, loc=tuple(base + Vector((0, 0, height))), armL=(150, 30), armR=(150, 30),
            legL=(25, 0), legR=(-15, 0))
    ch.pose(t + dur, loc=tuple(base), hipz=-0.3, armL=(40, 30), armR=(40, 30), legL=(0, 0), legR=(0, 0))
    ch.pose(t + dur + 0.12, hipz=0.0, armL=(5, 6), armR=(5, 6))
    return ch


def run(ch, t0, t1, p0, p1, rate=3.6):
    """Full-energy run: wide swings, forward lean, bounce."""
    ch.walk(t0, t1, p0, p1, rate=rate, swing=48, arm=55, bob=0.3)
    ch.pose(t0, torso=(0, 10, 0)); ch.pose(t1, torso=(0, 10, 0))
    return ch


def breathe(ch, strength=1.0):
    """Stronger idle than Char.idle: breathing hip bob + head drift + arm sway."""
    from .core import noise
    noise(ch.hip, "location", 2, 0.04 * strength, 18)
    noise(ch.neck, "rotation_euler", 2, 0.07 * strength, 22)
    noise(ch.neck, "rotation_euler", 0, 0.04 * strength, 26)
    noise(ch.shL, "rotation_euler", 0, 0.05 * strength, 30)
    noise(ch.shR, "rotation_euler", 0, 0.05 * strength, 33)
    return ch


# ------------------------------------------------------------------ patch onto Char
def install():
    if getattr(C.Char, "_acting_installed", False):
        return
    C.Char._face_legacy = C.Char.face
    orig_init = C.Char.__init__

    def init(self, name, *a, **kw):
        style = kw.get("face", "hero")
        layered = style and os.path.exists(os.path.join(ASSETS, "faces", f"{style}_eyes.png"))
        if layered:
            kw["face"] = None
        orig_init(self, name, *a, **kw)
        self._eye_track, self._mouth_track = [], []
        if layered:
            self.face_mat = layered_face_material(name + "_face", style, self.skin_c)
            self.head.data.materials.clear(); self.head.data.materials.append(self.face_mat)
            face(self, -10.0, "neutral")
    C.Char.__init__ = init
    for fn in (face, blink, talk, act, hold_pose, wiggle, panic, nod, shake, look, jump, run, breathe, ladder, dart):
        setattr(C.Char, fn.__name__, fn)
    C.Char._acting_installed = True


install()

# ------------------------------------------------------------------ v3 acting library (rbx/motion.py)
# acting.shock(ch, t), acting.run(ch, t0, t1, path), acting.read(ch, t, prop=...), acting.blocking([a, b], t) ...
from . import motion  # noqa: E402
from .motion import *  # noqa: E402,F401,F403  (run/nod/shake are upgraded, signature-compatible)
from .motion import run, nod, shake  # noqa: E402
for _fn in (run, nod, shake):
    setattr(C.Char, _fn.__name__, _fn)


# ------------------------------------------------------------------ v3.1 joints: elbows + knees (2026-11-14)
# R6 look kept: each arm/leg block (and every sleeve/cuff/shoe on it) is CUT at the joint into an upper and a lower
# piece; the lower piece hangs off a new pivot (ch.joints["elbowL"/"elbowR"/"kneeL"/"kneeR"]). Straight = identical
# silhouette to before (a thin bevel seam at the joint). Char.pose() accepts elbowL/elbowR/kneeL/kneeR = flex in degrees
# (positive = natural bend: forearm forward, shin back).
import bmesh as _bm  # noqa: E402
from mathutils import Matrix as _Mx  # noqa: E402
ELBOW_Z = -0.75          # shoulder-pivot local z of the elbow (arm spans +0.45 .. -1.55)
KNEE_Z = -1.0            # hip-pivot local z of the knee (leg spans 0 .. -2)
UPPER, LOWER = -ELBOW_Z, 1.55 + ELBOW_Z        # 0.75 / 0.8 studs (shoulder->elbow, elbow->fist)
JOINT_OVERLAP = 0.14     # upper limb piece overlaps the lower one (hides the bevel groove, fills the bent elbow)
JOINTS = ("elbowL", "elbowR", "kneeL", "kneeR")


def _cut(ob, zc, new_parent, Mcut):
    """Split mesh child `ob` of a limb pivot at pivot-local z=zc. Part below moves to new_parent (pivot at zc)."""
    M = ob.matrix_parent_inverse @ ob.matrix_basis     # (matrix_local/world are stale before a depsgraph update)
    zs = [(M @ v.co).z for v in ob.data.vertices]
    if not zs:
        return
    if min(zs) >= zc - 1e-4:
        return
    if max(zs) <= zc + 1e-4:                       # wholly below: just re-hang it
        ob.parent = new_parent; ob.matrix_parent_inverse = _Mx(); ob.matrix_basis = Mcut @ M
        return
    Mi = M.inverted()
    co = Mi @ Vector((0, 0, zc)); no = (M.to_3x3().transposed() @ Vector((0, 0, 1))).normalized()
    if ob.data.users > 1:
        ob.data = ob.data.copy()
    lo = ob.copy(); lo.data = ob.data.copy(); lo.name = ob.name + "_lo"
    for c in ob.users_collection:
        c.objects.link(lo)
    co_up = Mi @ Vector((0, 0, zc - JOINT_OVERLAP))       # upper piece runs a little past the joint: no seam
    for o, keep_up in ((ob, True), (lo, False)):
        bm = _bm.new(); bm.from_mesh(o.data)
        _bm.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=co_up if keep_up else co, plane_no=no,
                             clear_inner=keep_up, clear_outer=not keep_up)
        _bm.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary], sides=0)
        bm.to_mesh(o.data); bm.free()
    lo.parent = new_parent; lo.matrix_parent_inverse = _Mx(); lo.matrix_basis = Mcut @ M


def rig_joints(ch):
    """Add elbow + knee pivots to a built Char (idempotent). Call AFTER all limb geometry/props exist (cast does this in
    _finish). Hand/prop empties below the elbow follow the forearm."""
    if getattr(ch, "joints", None):
        return ch
    from .core import empty
    ch.joints = {}
    for limb, jn, zc in (("armL", "elbowL", ELBOW_Z), ("armR", "elbowR", ELBOW_Z), ("legL", "kneeL", KNEE_Z),
                         ("legR", "kneeR", KNEE_Z)):
        pv = ch.piv(limb)
        kids = list(pv.children)
        j = empty(f"{ch.name}_{jn}", (0, 0, zc), pv, ch.coll, size=0.2)
        Mcut = _Mx.Translation((0, 0, -zc))
        for ob in kids:
            if ob.type == "MESH":
                _cut(ob, zc, j, Mcut)
            else:
                M = ob.matrix_parent_inverse @ ob.matrix_basis
                if M.translation.z < zc:                       # hand empties, props
                    ob.parent = j; ob.matrix_parent_inverse = _Mx(); ob.matrix_basis = Mcut @ M
        ch.joints[jn] = j
    return ch


def _joint_key(ch, t, jn, deg, interp="BEZIER"):
    j = getattr(ch, "joints", {}).get(jn)
    if j is None:
        return
    sgn = -1 if jn.startswith("elbow") else 1
    j.rotation_euler = (math.radians(sgn * max(0.0, min(150.0, deg))), 0, 0)
    j.keyframe_insert("rotation_euler", frame=F(t))
    set_interp(j, "rotation_euler", F(t), interp)


# v3.3 readable-head guard (test_seq R3-1/D2): a Roblox cylinder head pitched > ~16 deg down or rolled > 10 deg shows
# the camera the top of its hair and reads as a broken neck. Every keyed head pose goes through this clamp; drive
# eyelines with YAW (and the eye cells: "down", "side_l"), not with roll. ch.head_free = True opts out (falls, gags).
HEAD_PITCH = (-20.0, 16.0)       # (up, down) degrees
HEAD_ROLL = 10.0


def clamp_head(v):
    yaw, pitch, roll = (list(v) + [0, 0, 0])[:3]
    return (yaw, max(HEAD_PITCH[0], min(HEAD_PITCH[1], pitch)), max(-HEAD_ROLL, min(HEAD_ROLL, roll)))


def _install_joints():
    if getattr(C.Char, "_joints_installed", False):
        return
    orig = C.Char.pose

    def pose(self, t, interp="BEZIER", **kw):
        jk = {k: kw.pop(k) for k in JOINTS if k in kw}
        if "head" in kw and kw["head"] is not None and not getattr(self, "head_free", False):
            kw["head"] = clamp_head(kw["head"])
        orig(self, t, interp, **kw)
        for k, v in jk.items():
            if v is not None:
                _joint_key(self, t, k, float(v[0] if isinstance(v, (tuple, list)) else v), interp)
        return self
    C.Char.pose = pose
    C.Char._joints_installed = True


_install_joints()
from .motion import reach, reach_pose, contact, stance, key_pose, POSES  # noqa: E402,F401
