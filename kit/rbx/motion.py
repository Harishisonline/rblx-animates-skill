"""Acting library: pose-to-pose body language with real timing (REF1 sec. 3.6, REF2 sec. 8).

Every preset takes a rigged chars.Char (cast.* characters included) and TIME IN SECONDS (like the rest of the kit).
Timing constants are in FRAMES at 30 fps; fr(n) converts. Read docs/ACTING.md for when to use what.

    from rbx import motion as mo          # or: from rbx import acting as act; act.shock(ch, t)
    mo.idle(ch)                           # breathing + weight shifts (additive, safe under every other move)
    mo.shock(ch, V.w(12))                 # pose HITS on the stressed word: anticipation is keyed before t
    mo.run(ch, t0, t1, [(0, 0, 0), (4, -6, 0), (9, -6, 0)])     # 12-frame run cycle along a path
    mo.read(ch, t, prop=phone)            # phone parented to the hand, head down, eyes down, thumb scroll
    mo.blocking([a, b], t, "two")         # stage 2-3 characters with matched eyelines

Core idea: strike(ch, t, pose) keys HOLD -> ANTICIPATION -> HIT(overshoot) -> SETTLE, reading the character's current
pose from its F-curves so moves chain without pops. The head always leads the body by LEAD frames and the face swaps
one frame before the hit."""
import math
import os
import random
from mathutils import Vector
from . import FPS
from .core import F, fcurves, empty

# ---------------------------------------------------------------- timing (frames @30)
ANTIC = 4          # anticipation before every big move (3-5 f)
MOVE = 4           # anticipation extreme -> hit (snappy 3-5 f transitions)
SETTLE = 5         # overshoot -> settle (4-6 f)
OVER = 0.12        # overshoot 10-15 %
LEAD = 2           # head leads body by 2-3 f; eyes lead head by 2 f
RUN_CYCLE = 12     # frames per full run cycle (two steps)
WALK_CYCLE = 24    # frames per full walk cycle

ARMS = ("armL", "armR", "legL", "legR")
ROTS = ("head", "torso")
JOINTS = ("elbowL", "elbowR", "kneeL", "kneeR")     # v3.1 flex pivots (degrees, + = natural bend)
PARTS = ARMS + ROTS + ("hipz",) + JOINTS
# v3.2: rest arms hang slightly INWARD (out -2) - with out +4 the R6 block arms splayed into an A-pose wing in MCUs.
# v3.3: rest elbows 10 -> 5: a flexed elbow throws the forearm block FORWARD and, seen from a low MCU lens, it reads as
# a horizontal block / wing next to the torso (test_seq D3). Arms hang straight at rest.
REST = {"armL": (2, -2, 0), "armR": (4, -2, 0), "legL": (0, 0, 0), "legR": (0, 0, 0),
        "elbowL": 5.0, "elbowR": 5.0, "kneeL": 0.0, "kneeR": 0.0,
        "head": (0, 0, 0), "torso": (0, 0, 0), "hipz": 0.0}


def fr(n):
    """frames -> seconds"""
    return n / FPS


# ---------------------------------------------------------------- f-curve sampling
def _fc(ob, path, idx):
    ad = ob.animation_data
    if ad and ad.action:
        for fc in fcurves(ad.action):
            if fc.data_path == path and fc.array_index == idx:
                return fc
    return None


def _val(ob, path, idx, t):
    fc = _fc(ob, path, idx)
    if fc is None:
        return getattr(ob, path)[idx]
    mods = [(m, m.mute) for m in fc.modifiers]
    for m, _ in mods:
        m.mute = True
    v = fc.evaluate(F(t))
    for m, mu in mods:
        m.mute = mu
    return v


def sample(ch, t, parts=PARTS):
    """The character's keyed pose at time t, in Char.pose() units (degrees; hipz offset)."""
    out = {}
    for p in parts:
        if p == "hipz":
            out[p] = _val(ch.hip, "location", 2, t) - 2.0
        elif p in ARMS:
            side = 1 if p.endswith("L") else -1
            ob = ch.piv(p)
            x, y, z = (math.degrees(_val(ob, "rotation_euler", i, t)) for i in range(3))
            out[p] = (-x, -y * side, z * side)
        elif p in ROTS:
            ob = ch.piv(p)
            x, y, z = (math.degrees(_val(ob, "rotation_euler", i, t)) for i in range(3))
            out[p] = (z, x, y)
        elif p in JOINTS:
            j = getattr(ch, "joints", {}).get(p)
            out[p] = 0.0 if j is None else math.degrees(_val(j, "rotation_euler", 0, t)) * (-1 if p[0] == "e" else 1)
        elif p == "rot":
            out[p] = math.degrees(_val(ch.root, "rotation_euler", 2, t))
        elif p == "loc":
            out[p] = tuple(_val(ch.root, "location", i, t) for i in range(3))
    return out


def _vec(v):
    return tuple(v) if isinstance(v, (tuple, list)) else v


def _lerp(a, b, k):
    if isinstance(a, tuple):
        a = tuple(a) + (0,) * (len(b) - len(a)); b = tuple(b) + (0,) * (len(a) - len(b))
        return tuple(x + (y - x) * k for x, y in zip(a, b))
    return a + (b - a) * k


def _key(ch, t, pose, interp="BEZIER"):
    if pose:
        ch.pose(t, interp=interp, **pose)


# ---------------------------------------------------------------- squash & stretch
def squash(ch, t, amt=0.0):
    """Root scale key: amt>0 squash (wide+short), amt<0 stretch, 0 = rest. Same convention as cast.squash."""
    if not hasattr(ch, "_base_s"):
        ch._base_s = ch.root.scale[0]
    s0 = ch._base_s
    ch.root.scale = (s0 * (1 + amt * 0.6), s0 * (1 + amt * 0.6), s0 * (1 - amt))
    ch.root.keyframe_insert("scale", frame=F(t))
    return ch


def _face(ch, t, expr=None, eyes=None, mouth=None):
    if expr is None and eyes is None and mouth is None:
        return
    try:
        ch.face(t, expr, eyes=eyes, mouth=mouth)
    except TypeError:            # legacy atlas faces: face(t, idx)
        if isinstance(expr, int):
            ch.face(t, expr)
    except KeyError:
        pass


# ---------------------------------------------------------------- the core: strike
def strike(ch, t, pose, antic=ANTIC, move=MOVE, settle=SETTLE, over=OVER, lead=LEAD, dip=0.08, akick=0.15,
           expr=None, eyes=None, mouth=None, sq=0.0, hold=None, drift=0.03, release=None):
    """Pose-to-pose hit. t = the HIT frame (put it on the stressed word / the cut).
      t-(antic+move): hold previous pose      t-move: anticipation (akick of the move reversed, hip dips `dip`)
      t: overshoot (over x the move)            t+settle: final pose
    The head runs `lead` frames early. Face swaps 1 f before the hit. sq>0 adds squash on the anticipation,
    stretch on the hit. hold=s keeps the pose alive (moving hold, `drift`) then release=s eases back to REST."""
    pose = {k: _vec(v) for k, v in pose.items() if v is not None}
    t_hold, t_ant, t_set = t - fr(antic + move), t - fr(move), t + fr(settle)
    prev = sample(ch, t_hold, [k for k in pose if k in PARTS])
    body = {k: v for k, v in pose.items() if k != "head"}
    for part, tl in (("body", 0.0), ("head", fr(lead))):
        keys = {k: v for k, v in (body.items() if part == "body" else [("head", pose["head"])] if "head" in pose else [])}
        if not keys:
            continue
        h, a, o, s = {}, {}, {}, {}
        for k, v in keys.items():
            if k not in prev:
                o[k] = s[k] = v
                continue
            p = prev[k]
            h[k] = p
            a[k] = _lerp(p, v, -akick) if antic > 0 else p
            o[k] = _lerp(p, v, 1 + over)
            s[k] = v
        if antic > 0 and part == "body":
            hz = prev["hipz"] if "hipz" in prev else sample(ch, t_hold, ["hipz"])["hipz"]   # v4.3 (EP3 A-2): seated
            a["hipz"] = (hz if "hipz" not in a else a["hipz"]) - dip                       # hips no longer drop to 0
            h.setdefault("hipz", hz)
            if "hipz" not in o:
                o["hipz"] = h["hipz"] + dip * 0.4; s["hipz"] = h["hipz"]
        if antic > 0:
            _key(ch, t_hold - tl, h)
            _key(ch, t_ant - tl, a)
        _key(ch, t - tl, o)
        _key(ch, t_set - tl, s)
    if sq:
        if antic > 0:
            squash(ch, t_hold, 0.0); squash(ch, t_ant, sq)
        squash(ch, t, -sq * 0.8); squash(ch, t_set, 0.0)
    _face(ch, t - fr(1), expr, eyes, mouth)
    if hold:
        live = {k: (_lerp(v, v, 0) if not isinstance(v, tuple) else tuple(x * (1 + drift) for x in v))
                for k, v in pose.items() if k in PARTS}
        _key(ch, t_set + hold, live)
        if release:
            back = {k: REST[k] for k in pose if k in REST}
            strike(ch, t_set + hold + release, back, antic=0, move=int(release * FPS), over=0.04, lead=lead)
    return t_set


def rest(ch, t, parts=None, dur=8, lead=LEAD):
    """Ease the listed parts (default all) back to the neutral stance, landing at t."""
    parts = parts or [k for k in REST]
    return strike(ch, t, {k: REST[k] for k in parts}, antic=0, move=dur, over=0.05, lead=lead)


# ---------------------------------------------------------------- idle: breathing + weight shifts
def _clear_noise(ob, path, idx):
    fc = _fc(ob, path, idx)
    if fc:
        for m in list(fc.modifiers):
            if m.type == "NOISE":
                fc.modifiers.remove(m)


def _noise(ob, path, idx, strength, scale, phase):
    fc = _fc(ob, path, idx)
    if fc is None:
        ob.keyframe_insert(path, index=idx, frame=1)
        fc = _fc(ob, path, idx)
    m = fc.modifiers.new("NOISE"); m.strength = strength; m.scale = scale; m.phase = phase
    return m


def idle(ch, t0=0.0, t1=60.0, energy=1.0, breath=75, seed=None):
    """Always-on life layer, ADDITIVE on top of any keyed acting (F-curve noise, replaces old breathe/idle noise):
    chest breath (torso scale 1.00-1.02 over `breath` frames), slow weight shifts hip side-sway + roll every 2-4 s,
    head drift, faint arm sway. energy 0.5 calm/sad, 1 normal, 1.6 nervous/excited."""
    rnd = random.Random(seed if seed is not None else sum(map(ord, ch.name)))
    for ob, path, idx, st, sc in ((ch.hip, "location", 0, 0.05, 95), (ch.hip, "location", 2, 0.025, 40),
                                  (ch.hip, "rotation_euler", 1, 0.025, 105), (ch.hip, "rotation_euler", 2, 0.02, 80),
                                  (ch.neck, "rotation_euler", 2, 0.06, 45), (ch.neck, "rotation_euler", 0, 0.035, 55),
                                  (ch.neck, "rotation_euler", 1, 0.03, 70),
                                  (ch.shL, "rotation_euler", 0, 0.035, 50), (ch.shR, "rotation_euler", 0, 0.035, 57),
                                  *[(j, "rotation_euler", 0, 0.03, 61 + 7 * k)
                                    for k, j in enumerate(getattr(ch, "joints", {}).values())]):
        _clear_noise(ob, path, idx)
        _noise(ob, path, idx, st * energy, sc / max(0.6, energy) ** 0.5, rnd.uniform(0, 100))
    # breathing: torso mesh scale keys (chest rises), sine via bezier extremes
    tor = getattr(ch, "torso", None)
    if tor is not None:
        s0 = tuple(tor.scale)
        t, k, half = t0, 0, fr(breath) / 2
        while t <= t1 + 1e-6:
            a = 0.02 * min(1.5, energy) if k % 2 else 0.0
            tor.scale = (s0[0] * (1 + a * 0.5), s0[1] * (1 + a), s0[2] * (1 + a * 0.4))
            tor.keyframe_insert("scale", frame=F(t)); t += half; k += 1
        tor.scale = s0
    return ch


# ---------------------------------------------------------------- locomotion
def _yaw_of(d):
    return math.degrees(math.atan2(d.x, -d.y))


def _unwrap(prev, yaw):
    while yaw - prev > 180:
        yaw -= 360
    while yaw - prev < -180:
        yaw += 360
    return yaw


def facing(ch, t):
    """Unit vector the character faces at time t (rot 0 faces -Y, toward the default camera)."""
    y = math.radians(sample(ch, t, ["rot"])["rot"])
    return Vector((math.sin(y), -math.cos(y), 0))


def _path_times(pts, t0, t1):
    L = [0.0]
    for a, b in zip(pts, pts[1:]):
        L.append(L[-1] + (b - a).length)
    tot = L[-1] or 1.0
    return [t0 + (t1 - t0) * l / tot for l in L], tot


def locomote(ch, t0, t1, path, cycle=WALK_CYCLE, swing=30, arm=28, arm_out=-1, bob=0.1, lean=3, twist=5,
             head_lead=3, run_mode=False, ease_in=True, ease_out=True):
    """Generic cycle along a polyline. Root slides at constant speed; yaw turns at corners with the head leading
    by head_lead frames. Walk: lowest point just after contact, highest at passing. Run: lowest at contact (impact),
    airborne highest mid-step, forward lean `lean` deg, arms pump."""
    pts = [Vector(p) for p in path]
    if len(pts) < 2:
        return ch
    times, tot = _path_times(pts, t0, t1)
    # root position: linear keys at path points
    for p, tt in zip(pts, times):
        ch.pose(tt, loc=tuple(p), interp="LINEAR")
    # yaw at each segment, turning around corners in 6 f, head leading
    yaw0 = sample(ch, t0 - fr(1), ["rot"])["rot"]
    yaws, prevy = [], yaw0
    for a, b in zip(pts, pts[1:]):
        y = _unwrap(prevy, _yaw_of(b - a)); yaws.append(y); prevy = y
    turn = fr(6)
    ch.pose(t0 - turn, rot=yaw0); ch.pose(t0 + turn * 0.5, rot=yaws[0])
    for i in range(1, len(yaws)):
        tc = times[i]
        ch.pose(tc - turn * 0.5, rot=yaws[i - 1]); ch.pose(tc + turn * 0.5, rot=yaws[i])
    ch.pose(t1, rot=yaws[-1])
    corners = [(t0, yaws[0] - yaw0)] + [(times[i], yaws[i] - yaws[i - 1]) for i in range(1, len(yaws))]
    # cycle keys
    step = fr(cycle) / 2
    n = max(1, int((t1 - t0) / step))
    for k in range(n + 1):
        t = t0 + k * step
        if t > t1 + 1e-4:
            break
        s = 1 if k % 2 == 0 else -1
        amp = 1.0
        if ease_in and k == 0:
            amp = 0.45
        if ease_out and t1 - t < step * 1.01:
            amp = 0.5
        tw = twist * s * amp
        pose = dict(legL=(swing * s * amp, 0), legR=(-swing * s * amp, 0),
                    armL=(-arm * s * amp, arm_out), armR=(arm * s * amp, arm_out),
                    torso=(tw, lean, -1.5 * s * amp),
                    kneeL=(6 if s > 0 else 22) * amp, kneeR=(22 if s > 0 else 6) * amp,   # v3.1 knees + elbows
                    elbowL=(70 if run_mode else 22), elbowR=(70 if run_mode else 22))
        ch.pose(t, **pose)
        if t + step * 0.5 <= t1:                         # passing: swing leg's knee lifts the foot
            ch.pose(t + step * 0.5, **{("kneeR" if s > 0 else "kneeL"): (60 if run_mode else 38) * amp,
                                       ("kneeL" if s > 0 else "kneeR"): 4})
        # head: stabilised against the twist, plus look into upcoming corners
        hy = -tw * 0.8
        for tc, dy in corners:
            if tc - fr(head_lead + 6) <= t <= tc + fr(2):
                hy += max(-55, min(55, dy * 0.5))
        ch.pose(t - fr(1), head=(hy, -lean * 0.6 + (2 if run_mode else 0), 0))
        if run_mode:
            ch.pose(t, hipz=-bob * amp)                       # impact
            if t + step * 0.5 <= t1:
                ch.pose(t + step * 0.5, hipz=bob * 0.9 * amp)  # flight
        else:
            ch.pose(t, hipz=0.0)
            if t + step * 0.25 <= t1:
                ch.pose(t + step * 0.25, hipz=-bob * amp)     # down (weight accept)
            if t + step * 0.6 <= t1:
                ch.pose(t + step * 0.6, hipz=bob * 0.7 * amp)  # up (passing)
    # arrive: settle with a small overshoot
    ch.pose(t1 + fr(4), kneeL=4, kneeR=10, elbowL=12, elbowR=16)
    ch.pose(t1 + fr(4), legL=(0, 0), legR=(0, 0), armL=(arm * 0.2, -1), armR=(arm * 0.2, -1),
            torso=(0, -lean * 0.3, 0), head=(0, 0, 0), hipz=-bob * 0.6)
    ch.pose(t1 + fr(10), armL=(2, -2), armR=(4, -2), torso=(0, 0, 0), hipz=0.0)
    return ch


def walk(ch, t0, t1, path, cycle=WALK_CYCLE, mood="normal"):
    """Walk along path [(x,y,z),...] between t0 and t1. mood: normal | happy (bouncy) | sad (slow, low, head down) |
    sneak (crouched, big steps) | confident (swagger, twist)."""
    k = dict(normal={}, happy=dict(bob=0.16, arm=34, swing=32),
             sad=dict(bob=0.05, arm=10, swing=20, lean=8, twist=2),
             sneak=dict(bob=0.04, arm=14, swing=36, lean=14, arm_out=18),
             confident=dict(bob=0.12, arm=34, twist=9, lean=-3))[mood]
    locomote(ch, t0, t1, path, cycle=cycle, **k)
    if mood == "sad":
        strike(ch, t0, {"head": (0, 18, 0)}, antic=0, move=8)
    if mood == "sneak":
        ch.pose(t0, hipz=-0.35); ch.pose(t1, hipz=-0.35)
    return ch


def run(ch, t0, t1, p0, p1=None, rate=None, cycle=RUN_CYCLE, lean=13, arm=60, swing=50, bob=0.13):
    """12-frame run cycle (REF1: arms pump +/-60, lean 10-15 deg, bob). run(ch,t0,t1,path) or legacy run(ch,t0,t1,p0,p1)."""
    path = [p0, p1] if p1 is not None else p0
    if rate:                          # legacy: rate = steps per second per leg
        cycle = max(8, int(round(FPS / rate)))
    return locomote(ch, t0, t1, path, cycle=cycle, swing=swing, arm=arm, arm_out=12, bob=bob, lean=lean,
                    twist=4, run_mode=True)


def skid_stop(ch, t, dist=1.4, dur=10, expr="shock"):
    """Brake at the end of a run: lean back, front leg planted, arms fling forward, root slides `dist` in `dur` f,
    squash on the plant, then overshoot forward and settle. Call with t = run end time."""
    fwd = facing(ch, t)
    p = Vector(sample(ch, t, ["loc"])["loc"])
    ch.pose(t, loc=tuple(p), interp="BEZIER")
    ch.pose(t + fr(dur), loc=tuple(p + fwd * dist))
    strike(ch, t + fr(3), dict(torso=(0, -20, 0), legL=(45, 6), legR=(-20, 0), armL=(70, 40), armR=(70, 40),
                               head=(0, -6, 0), hipz=-0.3), antic=0, move=3, settle=dur - 3, over=0.1, expr=expr, sq=0.12)
    strike(ch, t + fr(dur + 6), dict(torso=(0, 6, 0), legL=(0, 0), legR=(0, 0), armL=(15, 10), armR=(15, 10),
                                     head=(0, 4, 0), hipz=0.0), antic=0, move=6, settle=6, over=0.3)
    return rest(ch, t + fr(dur + 20), ["torso", "head", "armL", "armR"], dur=8)


def run_away(ch, t, path, t1, look_back=True, expr="terror"):
    """Panic flee: 4 f crouch anticipation, whip-turn to the run direction (head first), run the path,
    optional glance back over the shoulder at 40% of the run."""
    pts = [Vector(p) for p in path]
    yaw = _yaw_of(pts[1] - pts[0])
    cur = sample(ch, t, ["rot"])["rot"]
    yaw = _unwrap(cur, yaw)
    strike(ch, t, dict(head=(max(-70, min(70, yaw - cur)), 0, 0), hipz=-0.3, armL=(60, 30), armR=(60, 30)),
           antic=2, move=3, settle=2, expr=expr, sq=0.12)
    ch.pose(t, rot=cur); ch.pose(t + fr(5), rot=yaw)
    ch.pose(t + fr(5), head=(0, 0, 0))
    run(ch, t + fr(5), t1, pts)
    if look_back:
        tb = t + fr(5) + (t1 - t - fr(5)) * 0.4
        ch.pose(tb - fr(3), head=(0, 0, 0)); ch.pose(tb + fr(3), head=(65, -5, 0))
        ch.pose(tb + fr(12), head=(65, -5, 0)); ch.pose(tb + fr(16), head=(0, 0, 0))
    return ch


# ---------------------------------------------------------------- looks & turns
def _target_point(target):
    if hasattr(target, "head") and hasattr(target, "root"):      # a Char: aim at its face
        return target.head.matrix_world.translation.copy()
    if hasattr(target, "matrix_world"):
        return target.matrix_world.translation.copy()
    return Vector(target)


def _head_world(ch, t):
    loc = Vector(sample(ch, t, ["loc"])["loc"])
    return loc + Vector((0, 0, 4.6 * ch.root.scale[2]))


def aim(ch, t, target):
    """(yaw rel to body, pitch_down) in degrees from the character's head to a target (Char, object or point)."""
    p = _target_point(target)
    if hasattr(target, "head") and hasattr(target, "root"):
        p = _head_world(target, t)
    h = _head_world(ch, t)
    d = p - h
    body = sample(ch, t, ["rot"])["rot"]
    rel = _unwrap(0, _yaw_of(d) - body)
    pitch = -math.degrees(math.atan2(d.z, max(0.01, Vector((d.x, d.y)).length)))
    return rel, pitch


def look_at(ch, t, target, lead=LEAD, settle=SETTLE, max_head=65, torso_share=0.25, eyes=True, expr=None):
    """Head turns to a target (eyes swap toward it 2 f earlier), torso follows a share; beyond max_head the body
    should turn() instead."""
    rel, pitch = aim(ch, t, target)
    hy = max(-max_head, min(max_head, rel * (1 - torso_share)))
    ty = max(-25, min(25, rel * torso_share))
    pose = {"head": (hy, max(-30, min(30, pitch)), -hy * 0.08), "torso": (ty, 0, 0)}
    if eyes and abs(rel) > 12 and not expr:
        _face(ch, t - fr(lead + 4), eyes="side_l" if rel > 0 else "side_r")
        _face(ch, t + fr(settle + 2), eyes="normal")
    return strike(ch, t, pose, antic=2, move=4, settle=settle, over=0.1, lead=lead, dip=0.02, expr=expr)


def turn(ch, t, yaw=None, target=None, dur=8, expr=None, expr_t=None, lead=3):
    """Body turn to absolute yaw (deg) or toward target. Eyes lead head 2 f, head leads body `lead` f, body
    overshoots 8 % and settles. expr swaps at expr_t (put it on the stressed word), default at the hit."""
    cur = sample(ch, t, ["rot"])["rot"]
    if target is not None:
        d = _target_point(target) - Vector(sample(ch, t, ["loc"])["loc"])
        yaw = _yaw_of(d)
    yaw = _unwrap(cur, yaw)
    dy = yaw - cur
    side = "side_l" if dy > 0 else "side_r"
    t_end = t + fr(dur)
    _face(ch, t - fr(lead + 2), eyes=side)
    hd = max(-60, min(60, dy * 0.6))
    ch.pose(t - fr(lead + 1), head=sample(ch, t - fr(lead + 1), ["head"])["head"])
    ch.pose(t - fr(lead) + fr(dur) * 0.5, head=(hd, 0, 0))            # head gets there first
    ch.pose(t_end + fr(2), head=(-dy * 0.05, 0, 0))                    # lag back as body overshoots
    ch.pose(t_end + fr(6), head=(0, 0, 0))
    ch.pose(t, rot=cur)
    ch.pose(t_end, rot=cur + dy * 1.08)
    ch.pose(t_end + fr(5), rot=yaw)
    ch.pose(t - fr(2), hipz=0.0); ch.pose(t + fr(dur * 0.5), hipz=-0.06); ch.pose(t_end + fr(4), hipz=0.0)
    _face(ch, expr_t if expr_t is not None else t_end, expr, eyes="normal" if not expr else None)
    return t_end + fr(5)


def dread_turn(ch, t, yaw=None, target=None, dur=1.6, reveal_t=None, expr="terror"):
    """Slow horror turn: eyes slide first, head creeps (ease-in) to ~60 deg, body follows late, character sinks and
    arms lift a little; on reveal_t (stressed word, default end) the eyes pop and a small recoil fires."""
    cur = sample(ch, t, ["rot"])["rot"]
    if target is not None:
        yaw = _yaw_of(_target_point(target) - Vector(sample(ch, t, ["loc"])["loc"]))
    yaw = _unwrap(cur, yaw); dy = yaw - cur
    _face(ch, t, "worried", eyes="side_l" if dy > 0 else "side_r")
    ch.pose(t, head=(0, 0, 0), hipz=0.0, armL=(0, 4), armR=(0, 4), rot=cur)
    ch.pose(t + dur * 0.55, head=(max(-60, min(60, dy * 0.7)), 4, 0), hipz=-0.12, armL=(18, 14), armR=(18, 14))
    ch.pose(t + dur * 0.3, rot=cur + dy * 0.05)
    ch.pose(t + dur, rot=yaw, head=(0, 6, 0), hipz=-0.18, armL=(26, 18), armR=(26, 18))
    rt = reveal_t if reveal_t is not None else t + dur
    strike(ch, rt + fr(4), dict(torso=(0, -10, 0), head=(0, -8, 0), armL=(45, 40), armR=(45, 40), hipz=-0.05),
           antic=2, move=3, settle=6, expr=expr, sq=0.08)
    return rt + fr(10)


# ---------------------------------------------------------------- hands & props
def hand(ch, arm="armR"):
    """Empty at the fist (prop parent), cached per arm. Hand bottom is ~1.55 below the shoulder pivot."""
    cache = ch.__dict__.setdefault("_hands", {})
    if arm not in cache:
        j = getattr(ch, "joints", {}).get("elbow" + arm[-1])
        cache[arm] = (empty(f"{ch.name}_fist_{arm}", (0, -0.1, -0.8), j, ch.coll) if j is not None else
                      empty(f"{ch.name}_fist_{arm}", (0, -0.1, -1.55), ch.piv(arm), ch.coll))
    return cache[arm]


def attach(ch, prop, arm="armR", offset=(0, -0.25, -0.15), rot=(90, 0, 0)):
    """Parent a prop object to the fist (offset in hand space). Use for phones, letters, cups, swords."""
    h = hand(ch, arm)
    prop.parent = h
    prop.location = offset
    prop.rotation_euler = tuple(math.radians(a) for a in rot)
    return prop


def point(ch, t, target=None, arm="armR", hold=0.8, expr="determined", release=0.3):
    """Point at a target (Char/object/point) or straight ahead. Torso takes 30 % of the aim, head the rest,
    arm angle from target elevation."""
    rel, pitch = (0.0, 0.0) if target is None else aim(ch, t, target)
    ty = max(-25, min(25, rel * 0.3)); rest_ = rel - ty
    side = 1 if arm == "armL" else -1
    tw = max(-45, min(80, rest_ * side))          # arm forward: sideways aim is the twist channel
    pose = {arm: (90 - pitch * 0.8, 4, tw), "torso": (ty, -3, 0),
            "head": (max(-60, min(60, rest_ * 0.8)), pitch * 0.6, 0),
            ("armL" if arm == "armR" else "armR"): (10, 8, 0)}
    return strike(ch, t, pose, expr=expr, hold=hold, release=release, sq=0.04)


def grab(ch, t, arm="both", expr="determined", reach=1.0):
    """Reach (lean in, arm(s) overshoot forward) then pull the object in to a chest hold 8 f later."""
    arms = ("armL", "armR") if arm == "both" else (arm,)
    p = {a: (95 * reach, 4, 0) for a in arms}
    p.update(torso=(0, 14 * reach, 0), head=(0, 6, 0))
    strike(ch, t, p, expr=expr, akick=0.25)
    pull = {a: (72, 2, -22) for a in arms}
    pull.update(torso=(0, -3, 0), head=(0, 4, 0))
    return strike(ch, t + fr(10), pull, antic=0, move=5, settle=4, over=0.15, sq=0.05)


def hold_phone(ch, t, arm="armR", prop=None, expr=None):
    """Phone held at chest height in front of the face, head tilted down to it."""
    if prop is not None:
        attach(ch, prop, arm, offset=(0, -0.3, -0.1), rot=(70, 0, 0))
    other = "armL" if arm == "armR" else "armR"
    pose = {arm: (74, 2, -38), other: (8, 6, 0), "head": (0, 20, 0), "torso": (0, 4, 0)}
    return strike(ch, t, pose, antic=3, move=5, settle=5, over=0.08, expr=expr)


def read(ch, t, prop=None, dur=1.5, arm="armR", react=None, react_t=None):
    """Read a phone/letter/screen: hold_phone, eyes down, little scroll ticks (thumb = 2 deg arm wobble every 12 f),
    head micro-nods along the lines; optional react ("shock", "gasp", "laugh"...) at react_t."""
    hold_phone(ch, t, arm, prop, expr=None)
    _face(ch, t + fr(2), eyes="down")
    k, tt = 0, t + fr(14)
    while tt < t + dur:
        ch.pose(tt, head=(-2 + 4 * (k % 2), 20 + (k % 3), 0), **{arm: (74 + (2 if k % 2 else 0), 2, -38)})
        tt += fr(12); k += 1
    if react:
        PRESETS[react](ch, react_t if react_t is not None else t + dur)
    return ch


def gasp(ch, t, arm="armR", hold=0.6):
    """Hand-to-mouth gasp: small recoil back, one hand flies to the mouth, eyes wide + 'o' mouth on the hit."""
    other = "armL" if arm == "armR" else "armR"
    pose = {arm: (150, 38, 0), other: (25, 14, 0), "head": (0, -8, 0), "torso": (0, -7, 0)}
    return strike(ch, t, pose, antic=3, move=3, settle=6, over=0.14, expr="gasp", sq=0.08, hold=hold, release=0.35)


def shock(ch, t, recoil=0.0, hold=0.5, expr="shock"):
    """REF1 shock: 2 f hold, 4 f snap (head + shoulders up), eyes pop on the snap frame, stretch then squash settle.
    recoil>0 also steps the root back that many studs (shock recoil)."""
    pose = dict(armL=(38, 55, 0), armR=(38, 55, 0), torso=(0, -10, 0), head=(0, -12, 0), hipz=0.12)
    if recoil:
        p = Vector(sample(ch, t, ["loc"])["loc"]); back = -facing(ch, t) * recoil
        ch.pose(t - fr(4), loc=tuple(p)); ch.pose(t + fr(2), loc=tuple(p + back * 0.85))
        ch.pose(t + fr(8), loc=tuple(p + back))
        pose["legL"] = (-14, 4); pose["legR"] = (10, 4)
    strike(ch, t, pose, antic=2, move=4, settle=6, over=0.15, dip=0.1, expr=expr, sq=0.14)
    if hold:
        settle_t = t + fr(6) + hold
        ch.pose(settle_t, armL=(34, 50), armR=(34, 50), hipz=0.0, legL=(0, 0), legR=(0, 0))
    return t + fr(6)


def recoil(ch, t, dist=0.9, **kw):
    return shock(ch, t, recoil=dist, **kw)


def laugh(ch, t0, t1, hz=4.0, expr="joy", belly=True):
    """Head back 15 deg, eyes closed arcs, torso bounce 4 Hz decaying, hands to belly."""
    arms = dict(armL=(38, 0, -35), armR=(38, 0, -35)) if belly else {}
    strike(ch, t0, dict(head=(0, -15, 4), torso=(0, -6, 0), **arms), antic=3, move=4, settle=4, expr=expr, sq=0.06)
    t, k = t0 + fr(8), 0
    while t < t1 - fr(4):
        a = 1.0 - 0.5 * (t - t0) / max(0.01, t1 - t0)
        up = k % 2 == 0
        ch.pose(t, hipz=(0.07 if up else -0.04) * a, torso=(0, (-8 if up else -3) * a, 0),
                head=(0, (-17 if up else -12) * a, (5 if up else 2) * a))
        t += 0.5 / hz; k += 1
    return rest(ch, t1 + fr(8), ["head", "torso", "armL", "armR", "hipz"], dur=10)


def cry(ch, t0, t1, hz=3.0, hands=True, expr="cry"):
    """Head down, shoulders hunched, hands to face, shoulder shudder 3 Hz (2 deg) with sniff jolts."""
    arms = dict(armL=(150, 38, 0), armR=(150, 38, 0)) if hands else dict(armL=(10, -4, 0), armR=(10, -4, 0))
    strike(ch, t0, dict(head=(0, 22, 0), torso=(0, 12, 0), hipz=-0.08, **arms), antic=3, move=8, settle=6,
           over=0.06, expr=expr)
    t, k = t0 + fr(16), 0
    while t < t1:
        s = 1 if k % 2 == 0 else -1
        sniff = (k % 7 == 3)
        ch.pose(t, torso=(0, 12 + (4 if sniff else 0), 2 * s), head=(0, 22 - (6 if sniff else 0), 1.5 * s),
                hipz=-0.08 + (0.05 if sniff else 0))
        t += 0.5 / hz; k += 1
    return ch


def stomp(ch, t, n=2, interval=0.4, leg="legR", expr="furious"):
    """Angry stomp(s): fists clenched, knee-up lift (6 f), slam (2 f) with squash + hip drop, then the next."""
    strike(ch, t - fr(8), dict(armL=(55, 22, 0), armR=(55, 22, 0), torso=(0, 8, 0), head=(0, 6, 0)), expr=expr)
    for i in range(n):
        lg = leg if i % 2 == 0 else ("legL" if leg == "legR" else "legR")
        ti = t + i * interval
        ch.pose(ti - fr(8), **{lg: (0, 0)}, hipz=0.0)
        ch.pose(ti - fr(2), **{lg: (55, 4)}, hipz=0.14, torso=(0, 2, 0))
        ch.pose(ti, **{lg: (-4, 0)}, hipz=-0.16, torso=(0, 12, 0))
        squash(ch, ti - fr(2), -0.06); squash(ch, ti, 0.16); squash(ch, ti + fr(5), 0.0)
        ch.pose(ti + fr(5), **{lg: (0, 0)}, hipz=0.0, torso=(0, 8, 0))
    return ti + fr(5)


def shrug(ch, t, hold=0.5):
    """Arms out palms-up, shoulders (hip) pop up, head tilts; holds then drops with a little bounce."""
    pose = dict(armL=(38, 40, -20), armR=(38, 40, -20), head=(0, 0, 13), torso=(0, -2, 4), hipz=0.08)
    return strike(ch, t, pose, antic=3, move=4, settle=5, expr="confused", hold=hold, release=0.3)


def nod(ch, t, n=2, amp=12, rate=5.0):
    """Yes-nod: first beat strongest, decays; head leads (no body)."""
    for i in range(n):
        a = amp * (1 - 0.3 * i / max(1, n))
        ch.pose(t + i / rate, head=(0, a, 0)); ch.pose(t + (i + 0.5) / rate, head=(0, -a * 0.25, 0))
    ch.pose(t + n / rate + fr(3), head=(0, 0, 0))
    return ch


def shake(ch, t, n=3, amp=18, rate=6.0):
    """No-shake: yaw swings decaying, slight down-tilt, eyes closed-ish."""
    for i in range(n):
        s = 1 if i % 2 == 0 else -1
        ch.pose(t + i / rate, head=(amp * s * (1 - 0.25 * i / n), 6, 0))
    ch.pose(t + n / rate + fr(3), head=(0, 0, 0))
    return ch


def sit(ch, t, seat_h=1.5, dur=12):
    """Sit down landing at t: glance down, bend forward, lower hips onto a seat of height seat_h (studs), legs
    forward, then straighten the back with a settle bounce."""
    hz = seat_h + 0.5 - 2.0
    ch.pose(t - fr(dur + 4), head=(0, 0, 0))
    ch.pose(t - fr(dur), head=(0, 14, 0), torso=(0, 0, 0), hipz=0.0, legL=(0, 0), legR=(0, 0))
    ch.pose(t - fr(dur * 0.4), torso=(0, 22, 0), hipz=hz * 0.6, legL=(55, 4), legR=(55, 4), armL=(30, 8), armR=(30, 8))
    ch.pose(t, torso=(0, 6, 0), hipz=hz - 0.06, legL=(90, 4), legR=(90, 4), head=(0, 4, 0))
    squash(ch, t, 0.06)
    ch.pose(t + fr(6), torso=(0, -2, 0), hipz=hz, armL=(30, -6), armR=(30, -6), head=(0, 0, 0))
    squash(ch, t + fr(6), 0.0)
    return t + fr(6)


def stand(ch, t, dur=12):
    """Stand up landing at t: lean forward (anticipation), push up, overshoot tall, settle."""
    cur = sample(ch, t - fr(dur), ["hipz"])["hipz"]
    ch.pose(t - fr(dur), torso=(0, 0, 0), hipz=cur)
    ch.pose(t - fr(dur * 0.55), torso=(0, 26, 0), hipz=cur + 0.05, head=(0, -6, 0))
    ch.pose(t, torso=(0, -3, 0), hipz=0.06, legL=(0, 0), legR=(0, 0), armL=(0, 4), armR=(0, 4), head=(0, 0, 0))
    squash(ch, t, -0.05); squash(ch, t + fr(5), 0.0)
    ch.pose(t + fr(5), torso=(0, 0, 0), hipz=0.0)
    return t + fr(5)


def stumble(ch, t, dist=1.0):
    """Trip: toe catches (leg back), body pitches forward, arms windmill, root lurches, recovers with overshoot."""
    p = Vector(sample(ch, t, ["loc"])["loc"]); fwd = facing(ch, t)
    ch.pose(t - fr(2), loc=tuple(p)); ch.pose(t + fr(8), loc=tuple(p + fwd * dist))
    ch.pose(t - fr(2), torso=(0, 0, 0), legL=(0, 0), legR=(0, 0))
    ch.pose(t + fr(3), torso=(0, 32, 4), legR=(-35, 0), legL=(20, 0), armL=(110, 40), armR=(60, 50), head=(0, -16, 0),
            hipz=-0.25)
    ch.pose(t + fr(7), armL=(60, 50), armR=(120, 40))
    _face(ch, t, "shock")
    ch.pose(t + fr(12), torso=(0, -6, 0), legR=(0, 0), legL=(0, 0), armL=(30, 25), armR=(30, 25), head=(0, 0, 0),
            hipz=0.03)
    return rest(ch, t + fr(22), ["torso", "armL", "armR", "hipz"], dur=8)


def fall(ch, t, back=False, expr="scream"):
    """Fall flat (forward or on the back): lurch, 7 f drop rotating about the hip, squash on impact, 2 small bounces.
    t = impact frame. Body ends lying on the ground (hipz -1.5)."""
    sgn = -1 if back else 1
    p = Vector(sample(ch, t, ["loc"])["loc"]); fwd = facing(ch, t) * sgn
    ch.pose(t - fr(10), loc=tuple(p), torso=(0, 0, 0), hipz=0.0)
    ch.pose(t - fr(6), torso=(0, 18 * sgn, 0), hipz=0.05, armL=(100, 40), armR=(100, 40), head=(0, -20 * sgn, 0))
    _face(ch, t - fr(8), expr)
    ch.pose(t, torso=(0, 88 * sgn, 0), hipz=-1.5, armL=(165, 20), armR=(165, 20), legL=(0, 0), legR=(0, 0),
            loc=tuple(p + fwd * 1.6))
    squash(ch, t - fr(1), -0.06); squash(ch, t, 0.12); squash(ch, t + fr(4), 0.0)
    ch.pose(t + fr(4), torso=(0, 82 * sgn, 0), hipz=-1.38); ch.pose(t + fr(8), torso=(0, 90 * sgn, 0), hipz=-1.5)
    _face(ch, t + fr(10), eyes="closed", mouth="wavy")
    return t + fr(8)


def embrace(a, b, t, expr="relief", gap=1.9):
    """Hug: a steps in to b (b anticipates with arms opening), both wrap arms, heads tilt, squeeze-squash, sway."""
    pa = Vector(sample(a, t, ["loc"])["loc"]); pb = Vector(sample(b, t, ["loc"])["loc"])
    d = pb - pa; d.z = 0; dist = d.length; dn = d.normalized()
    ya = _yaw_of(dn); yb = _yaw_of(-dn)
    end = pb - dn * gap
    a.pose(t - fr(12), loc=tuple(pa)); a.pose(t, loc=tuple(end))
    for ch, yaw in ((a, ya), (b, yb)):
        cur = sample(ch, t - fr(12), ["rot"])["rot"]
        ch.pose(t - fr(12), rot=cur); ch.pose(t - fr(4), rot=_unwrap(cur, yaw))
        strike(ch, t - fr(6), dict(armL=(85, 4, 40), armR=(85, 4, 40), head=(0, -6, 0)), antic=2, move=4, settle=2,
               expr="happy")
        strike(ch, t + fr(2), dict(armL=(88, 2, -42), armR=(88, 2, -42), torso=(0, 8, 0), head=(0, 6, 10)),
               antic=0, move=6, settle=6, over=0.15, expr=expr, eyes="closed")
        squash(ch, t + fr(4), 0.06); squash(ch, t + fr(12), 0.0)
        for i, s in enumerate((1, -1, 1)):
            ch.pose(t + fr(14 + 10 * i), torso=(4 * s, 8, 3 * s))
    return t + fr(44)


# ---------------------------------------------------------------- talking cadence
def _norm(w):
    return "".join(c for c in w.lower() if c.isalnum())


# expression arcs for talk_cadence: base mood -> (opening eyes, stressed-word eyes/mouth, settle eyes)
# Eye cells are the v3 layered atlas names (brows live in the eye layer: wide = brows up, worried = brows knit,
# angry = V brows, squint/half = lids). 'normal' dot eyes are only used inside these arcs for a few frames.
TALK_ARC = {
    "neutral": ("normal", ("wide", "talk_wide"), "half"),      # v3.4: settles to a cool half-lid, not dot eyes
    "smile":   ("normal", ("wide", "open_smile"), "normal"),
    "happy":   ("happy", ("wide", "open_smile"), "happy"),
    "smug":    ("half", ("squint", "smirk"), "half"),
    "sad":     ("worried", ("worried", "frown"), "down"),
    "worried": ("worried", ("wide", "o"), "worried"),
    "angry":   ("angry", ("angry", "talk_wide"), "squint"),
    "shock":   ("wide", ("wide", "o"), "worried"),
}


def _mood_of(ch, t):
    """Best-guess current mood from the face track (eyes cell) - picks the TALK_ARC row."""
    try:
        from .acting import EYE, _eye_at
        e = _eye_at(ch, t)
    except Exception:
        return "neutral"
    inv = {v: k for k, v in EYE.items()}
    md = {"happy": "happy", "half": "smug", "worried": "sad", "angry": "angry", "wide": "shock",
          "squint": "smug"}.get(inv.get(e), "neutral")
    if md == "neutral":            # v3.3: dot eyes + a smile MOUTH = a smiling line (Mom 'Covered, Harry' read as a
        try:                       # squint because only the eye cell was consulted)
            from .acting import MOUTH
            mt = [m for tt, m in getattr(ch, "_mouth_track", []) if tt <= t + 1e-6]
            if mt and mt[-1] in (MOUTH["smile"], MOUTH["open_smile"], MOUTH["grin"]):
                md = "smile"
        except Exception:
            pass
    return md


# mouth sets for the lip flaps per mood: (open, wide, rest). A smiling line flaps through smile shapes (the old 'talk'
# 'o' flaps on a smile line read as surprise, test_seq R3-4).
TALK_SETTLE = {"neutral": "smirk", "smile": "smile", "happy": "smile", "sad": "frown", "smug": "smirk",
               "angry": "grimace", "shock": "o", "worried": "frown"}       # closed mouth held after a stressed word
EXPR_REST = {"sad": "frown", "worried": "frown", "smug": "smirk", "happy": "smile", "joy": "smile", "smile": "smile",
             "angry": "grimace", "shock": "o", "gasp": "o", "neutral": "flat"}


def _blink_at(ch, t):
    """3-frame blink at t that reopens to whatever eye cell is current (skips closed/happy eyes)."""
    try:
        from .acting import EYE, _eye_at, _key_map, _layered
        if not _layered(ch):
            return
        cur = _eye_at(ch, t)
        if cur in (EYE["closed"], EYE["happy"], EYE["wink"]):
            return
        _key_map(ch, "EyeMap", EYE["closed"], t); _key_map(ch, "EyeMap", cur, t + fr(3))
        ch.__dict__.setdefault("_blinks", []).append(t)
    except Exception:
        pass


TALK_MOUTH = {
    "smile": ("open_smile", "grin", "smile"), "happy": ("open_smile", "laugh", "smile"),
    "sad": ("talk", "ah", "frown"), "smug": ("talk", "smirk", "smirk"),
}


# v3.4 (R5 D3): the R4 'forearm UP beside the chest' beat (elbow 140) still read in every MCU as a horizontal block
# thrust at the lens / wing arms. An R6 forearm with ANY big elbow flex points at an MCU lens. MCU beats are now LOW
# and small: the hand swings a little forward + in in front of the thigh (elbow <= 30), upper arm on the torso.
BEAT_LOW = (8, -3, -10, 16)     # (fwd, out, twist, elbow): hand forward/in in front of the thigh, below the belt
BEAT_MID = (6, -3, -8, 12)
MCU_ELBOW_MAX = 35               # hands=False guard: no MCU pose may flex an elbow further (near-lens zone)


def talk_cadence(ch, t0, t1, words=None, stress=(), expr_on=None, energy=1.0, hands=True, mouth=True, seed=0,
                 mood=None, faces=True, sway=True, arms=True):
    """v4.3 (EP3 A-3): arms=False = no arm beats (a held prop / hat touch stays held); SEATED or kneeling speakers
    (|hipz| > 0.4 at t0) get the torso sway but no leg keys (it straightened seated legs).
    Speaking body language (v3.3, REF1 'faces change on stressed words, constant motion'):
      - FACE: mood-aware lip flaps (smile lines flap through smile shapes), a face change ON every stressed word
        (brows up + open mouth held for the whole word - talk() no longer flaps over it), a settle look after it,
        eye dart in the longest gap; words ending in ?/! count as stressed. expr_on {"word": "sad"} overrides.
      - HEAD: a persistent tilt (6-9 deg roll, alternating per phrase) + nod on stressed words; never above the
        readable-head clamp (acting.clamp_head).
      - SWAY: contrapposto per phrase - torso roll/yaw shifts weight onto one leg, legs counter-rotate so the feet
        stay planted, free knee flexes, head counter-tilts. Never frontal + square for a whole line.
      - GESTURE per stressed word, ONE arm at a time (alternating): hands=True = forearm beat up to chest;
        hands=False = MCU beat: upper arm stays on the torso, the forearm lifts UP beside the chest (BEAT_LOW), never
        a forearm pointing at the lens.
    words = [{word,start,end}] (audio/words.json); without words a 0.3 s phrase rhythm is used."""
    rnd = random.Random(seed)
    expr_on = expr_on or {}
    stress = {_norm(s) if isinstance(s, str) else s for s in stress}
    if words:
        ws = [(i, w.get("start", w.get("s")), w.get("end", w.get("e")), w.get("word", w.get("text", "")))
              for i, w in enumerate(words)]
        ws = [x for x in ws if x[1] is not None and t0 <= x[1] < t1]
    else:
        ws, t = [], t0
        while t < t1 - 0.2:
            ws.append((len(ws), t, t + 0.25, "")); t += 0.3
    big_idx = [k for k, (i, s, e, w) in enumerate(ws)
               if _norm(w) in stress or i in stress or _norm(w) in expr_on or i in expr_on
               or str(w).rstrip('"\'').endswith(("?", "!"))]
    if ws and not big_idx:                       # nothing flagged: the longest word carries the line
        big_idx = [max(range(len(ws)), key=lambda k: ws[k][2] - ws[k][1])]
    md = mood or _mood_of(ch, t0)
    o_eye, (b_eye, b_mouth), s_eye = TALK_ARC.get(md, TALK_ARC["neutral"])
    m_open, m_wide, m_rest = TALK_MOUTH.get(md, ("talk", "talk_wide", "flat"))
    if mouth and hasattr(ch, "talk"):
        try:
            small = [{"start": s, "end": e} for k, (_, s, e, _) in enumerate(ws) if k not in big_idx]
            if words and not small:
                ch.face(t1, mouth=m_rest)
            else:
                ch.talk(t0, t1, words=small if words else None, open_m=m_open, wide_m=m_wide, rest=m_rest)
        except Exception:
            pass
    base = sample(ch, t0, ["armL", "armR", "elbowL", "elbowR", "torso", "head", "legL", "legR", "kneeL", "kneeR"])
    seated = abs(sample(ch, t0, ["hipz"])["hipz"]) > 0.4
    beat_arm = "armR" if rnd.random() < 0.5 else "armL"
    side = 1 if rnd.random() < 0.5 else -1
    # ---- sway: per phrase (every ~3 words or at a gap > 0.25 s) contrapposto weight shift + head counter-tilt
    phrase = {}
    if ws:
        bounds = [0] + [k for k in range(1, len(ws)) if ws[k][1] - ws[k - 1][2] > 0.25 or k % 3 == 0]
        for k in bounds:
            phrase[k] = side
            if sway:
                tor0 = base["torso"]; r = side * 6.5 * min(1.3, max(0.8, energy))
                kk = {"torso": (tor0[0] + side * 9 * max(0.8, energy), tor0[1] + 1, r)}
                if not seated:
                    kk.update({"legL": (0, r, 0), "legR": (0, -r, 0),
                               "knee" + ("R" if side > 0 else "L"): 12, "knee" + ("L" if side > 0 else "R"): 2})
                _key(ch, ws[k][1] - fr(5), kk)
            side = -side
    tilt = phrase.get(0, 1)
    for k, (i, s, e, w) in enumerate(ws):
        key = _norm(w)
        big = k in big_idx
        tilt = -phrase[k] if k in phrase else tilt          # head counter-tilts the hip roll
        a = (9 if big else 3) * energy
        yaw = rnd.uniform(-5, 5) * energy
        roll = tilt * (10 if big else 8)
        ch.pose(s - fr(2), head=(yaw, a, roll))
        ch.pose(s + fr(4), head=(yaw * 0.6, -a * 0.3, roll * 0.85))
        if faces and k == 0 and not big:
            _face(ch, s - fr(1), eyes=o_eye)
        if big:
            ex = expr_on.get(key, expr_on.get(i))
            if ex:
                _face(ch, s - fr(1), ex); _face(ch, s, ex)
            elif faces:
                _face(ch, s - fr(1), eyes=b_eye); _face(ch, s, mouth=b_mouth)
            if mouth and not ex:                          # the stressed mouth holds through the word, then rests
                _face(ch, s + max(fr(3), (e - s) * 0.55), mouth=m_wide if b_mouth == m_open else b_mouth)
            # v3.4 (R5 R2-1b): the stressed face HOLDS into the next words (it reverted to dot eyes + dash mouth one
            # frame after the word, so 'Honestly?' / 'knew you' looked identical). expr_on faces hold until the next
            # stressed word / line end (no settle); plain stress holds >= 0.45 s, then a DIFFERENT settle face
            # (TALK_SETTLE mouth, not the flat dash), plus a blink on the settle.
            nxt = min([ws[j][1] for j in big_idx if j > k] + [t1])
            if mouth:
                _face(ch, max(e, s + fr(6)), mouth=(EXPR_REST.get(ex, m_rest) if ex else
                                                    TALK_SETTLE.get(md, m_rest)))
            if faces and not ex:                          # settle look after the stressed word
                ts = min(max(e + 0.2, s + 0.45), nxt - fr(2))
                if ts > s + fr(6):
                    _face(ch, ts, eyes=s_eye)
            if faces and hasattr(ch, "face"):             # a blink lands right after the stressed word
                tb = min(max(e, s + 0.3) + fr(3), nxt - fr(5))
                if tb > s + fr(5):
                    _blink_at(ch, tb)
            arm = beat_arm; sd = "L" if arm == "armL" else "R"
            rest_a = clamp_hang({arm: base[arm]})[arm]; rest_e = min(base["elbow" + sd], 9)
            if not arms:
                continue
            if hands:
                ch.pose(s - fr(6), **{arm: (12, -2), "elbow" + sd: rest_e})
                ch.pose(s, **{arm: (58, -12, -10), "elbow" + sd: 30})
                ch.pose(s + fr(10), **{arm: (48, -8, -6), "elbow" + sd: 26})
            else:                                         # MCU-safe beat: forearm lifts UP beside the chest
                ch.pose(s - fr(6), **{arm: rest_a, "elbow" + sd: rest_e})
                ch.pose(s, **{arm: BEAT_LOW[:3], "elbow" + sd: BEAT_LOW[3]})
                ch.pose(s + fr(10), **{arm: BEAT_MID[:3], "elbow" + sd: BEAT_MID[3]})
                ch.pose(s + fr(17), **{arm: BEAT_MID[:3], "elbow" + sd: BEAT_MID[3] - 10})   # hold up, drop fast
            ch.pose(s + fr(22), **{arm: rest_a, "elbow" + sd: rest_e})
            beat_arm = "armL" if beat_arm == "armR" else "armR"
    if faces and len(ws) >= 3:                          # eye dart in the longest gap between words
        gaps = [(ws[k + 1][1] - ws[k][2], ws[k][2]) for k in range(len(ws) - 1)]
        g, tg = max(gaps) if gaps else (0, 0)
        if g > 0.18:
            _face(ch, tg + 0.02, eyes="side_l" if rnd.random() < 0.5 else "side_r")
            _face(ch, tg + min(g, 0.3), eyes=s_eye)
    ch.pose(t1 + fr(6), head=(0, 0, tilt * 5))
    return ch


# ---------------------------------------------------------------- emotions
EMOTION = {
    # name: expr, pose, idle energy
    "happy": ("happy", dict(head=(0, -6, 4), torso=(0, -3, 0), armL=(14, 10), armR=(14, 10), hipz=0.04), 1.2),
    "joy": ("joy", dict(armL=(165, 30), armR=(165, 30), head=(0, -16, 0), torso=(0, -6, 0), hipz=0.1), 1.6),
    "sad": ("worried", dict(head=(0, 22, 0), torso=(0, 14, 0), armL=(2, 2), armR=(2, 2), hipz=-0.08), 0.5),
    "angry": ("angry", dict(armL=(55, 22), armR=(55, 22), torso=(0, 10, 0), head=(0, 8, 0)), 1.4),
    "furious": ("furious", dict(armL=(60, 40), armR=(60, 40), torso=(0, 14, 0), head=(0, 4, 0), hipz=-0.1), 1.8),
    "scared": ("scared", dict(armL=(70, 0, -30), armR=(70, 0, -30), torso=(0, 8, 0), head=(0, 10, 0), hipz=-0.2), 1.7),
    "shocked": ("shock", dict(armL=(38, 55), armR=(38, 55), torso=(0, -10, 0), head=(0, -12, 0), hipz=0.1), 1.3),
    "smug": ("smug", dict(armL=(80, 0, -55), armR=(80, 0, -55), head=(0, -8, 10), torso=(0, -4, 0)), 0.8),
    "bored": ("bored", dict(head=(0, 8, 14), torso=(0, 4, 5), armL=(0, 2), armR=(0, 2), hipz=-0.04), 0.5),
    "confused": ("confused", dict(armR=(130, 30, 0), armL=(40, 0, -30), head=(10, 4, 14)), 0.9),
    "love": ("joy", dict(armL=(140, 30, 0), armR=(140, 30, 0), head=(0, -4, 14), hipz=0.03), 1.1),
    "determined": ("determined", dict(armL=(50, 18), armR=(50, 18), torso=(0, 6, 0), head=(0, 4, 0)), 1.1),
    "embarrassed": ("worried", dict(armL=(150, 38, 0), armR=(30, 0, -20), head=(-14, 16, 6), torso=(0, 8, 0)), 1.0),
    "nervous": ("worried", dict(armL=(40, 0, -40), armR=(40, 0, -40), head=(6, 6, 0), hipz=-0.06), 1.8),
    "neutral": ("neutral", dict(REST), 1.0),
}


def emote(ch, t, emotion, hold=None, release=None, strength=1.0):
    """Emotion -> expression + full-body pose (+ suggested idle energy). Hits at t."""
    ex, pose, _ = EMOTION[emotion]
    p = {k: (tuple(x * strength for x in v) if isinstance(v, tuple) else v * strength) for k, v in pose.items()}
    return strike(ch, t, p, expr=ex, hold=hold, release=release, sq=0.05 * strength)


# ---------------------------------------------------------------- blocking
LAYOUTS = {
    # offsets (x along screen, depth y) in units of spacing; cheat = degrees each turns toward camera
    "two": [(-0.5, 0.0), (0.5, 0.0)],
    "two_deep": [(-0.45, -0.35), (0.45, 0.35)],          # one closer to camera (over-shoulder friendly)
    "three": [(-0.75, 0.15), (0.0, -0.2), (0.75, 0.15)],   # shallow arc
    "line": [(-1.0, 0.0), (0.0, 0.0), (1.0, 0.0)],
    "triangle": [(-0.6, 0.3), (0.6, 0.3), (0.0, -0.45)],
}


def blocking(chars, t, layout="two", center=(0, 0, 0), spacing=3.2, cam_yaw=0.0, cheat=35, speaker=None, ease=0):
    """Stage 2-3 characters at time t: positions from LAYOUTS (screen x, depth), bodies face the group centre but
    cheat `cheat` deg toward the camera (camera looks along +Y rotated by cam_yaw), heads aim at the speaker
    (or at each other) with height-correct eyelines. ease>0: move into place over `ease` frames instead of popping.
    Returns the placed positions."""
    offs = LAYOUTS[layout][:len(chars)]
    c = Vector(center); cy = math.radians(cam_yaw)
    right = Vector((math.cos(cy), math.sin(cy), 0)); depth = Vector((-math.sin(cy), math.cos(cy), 0))
    pos = [c + right * (ox * spacing) + depth * (oy * spacing) for ox, oy in offs]
    cam_face = cam_yaw                                    # yaw that faces the camera
    for ch, p in zip(chars, pos):
        to_c = c - p; to_c.z = 0
        y_in = _yaw_of(to_c) if to_c.length > 0.05 else cam_face
        y_in = _unwrap(cam_face, y_in)
        lim = max(0.0, abs(y_in - cam_face) - cheat)
        yaw = cam_face + math.copysign(lim, y_in - cam_face)
        if ease:
            cur = sample(ch, t - fr(ease), ["loc", "rot"])
            ch.pose(t - fr(ease), loc=cur["loc"], rot=cur["rot"])
        ch.pose(t, interp="BEZIER" if ease else "CONSTANT", loc=tuple(p), rot=yaw)
    eyeline(chars, t, speaker)
    return pos


def eyeline(chars, t, speaker=None, settle=SETTLE):
    """Heads re-aim: everyone looks at `speaker` (Char); the speaker looks at the nearest listener."""
    for ch in chars:
        if speaker is not None and ch is not speaker:
            tgt = speaker
        else:
            others = [o for o in chars if o is not ch]
            if not others:
                continue
            p = Vector(sample(ch, t, ["loc"])["loc"])
            tgt = min(others, key=lambda o: (Vector(sample(o, t, ["loc"])["loc"]) - p).length)
        rel, pitch = aim(ch, t, tgt)
        hy = max(-65, min(65, rel * 0.8)); ty = max(-20, min(20, rel * 0.2))
        ch.pose(t, head=(hy, max(-25, min(25, pitch)), 0), torso=(ty, 0, 0))
    return chars


# ---------------------------------------------------------------- registry
def _wrap(fn, **kw):
    return lambda ch, t: fn(ch, t, **kw)


PRESETS = {
    "shock": shock, "recoil": recoil, "gasp": gasp, "shrug": shrug, "point": point, "grab": grab,
    "nod": nod, "shake": shake, "stumble": stumble, "fall": fall, "stand": stand, "sit": sit,
    "stomp": stomp, "phone": hold_phone,
    "laugh": lambda ch, t: laugh(ch, t, t + 1.0), "cry": lambda ch, t: cry(ch, t, t + 1.5),
}
for _e in EMOTION:
    PRESETS.setdefault(_e, _wrap(emote, emotion=_e))

__all__ = ["fr", "sample", "strike", "rest", "squash", "idle", "locomote", "walk", "run", "skid_stop", "run_away",
           "facing", "aim", "look_at", "turn", "dread_turn", "hand", "attach", "point", "grab", "hold_phone", "read",
           "gasp", "shock", "recoil", "laugh", "cry", "stomp", "shrug", "nod", "shake", "sit", "stand", "stumble",
           "fall", "embrace", "talk_cadence", "EMOTION", "emote", "LAYOUTS", "blocking", "eyeline", "PRESETS",
           "ANTIC", "MOVE", "SETTLE", "OVER", "LEAD", "RUN_CYCLE", "WALK_CYCLE"]


# ================================================================ v3.1: two-bone IK reach, contact, key-pose library
# Hands REACH things: acting.reach(ch, t, target, hand="r") solves shoulder + elbow so the fist lands on a world point
# (an object, a Char part, or (x,y,z)). Use reach_pose(...) to get the pose dict and mix it into your own strike.
from mathutils import Matrix, Euler  # noqa: E402

UPPER, LOWER = 0.75, 0.8        # shoulder->elbow, elbow->fist (studs, character-local; matches acting.ELBOW_Z)


def _arm(hand):
    return "armL" if str(hand).lower() in ("l", "left", "arml") else "armR"


def _hip_matrix(ch, t, body=None):
    """World matrix of the hip at time t with the body pose `body` (torso/hipz dict, defaults to the keyed pose).
    Analytic (root world matrix at t x hip transform), so it is valid BEFORE the strike that will key the body."""
    import bpy
    sc = bpy.context.scene; sc.frame_set(F(t))
    b = sample(ch, t, ["torso", "hipz"]); b.update({k: v for k, v in (body or {}).items() if k in ("torso", "hipz")})
    yaw, pitch, roll = (tuple(b["torso"]) + (0, 0, 0))[:3]
    Mh = Matrix.Translation((0, 0, 2.0 + b["hipz"])) @ Euler((math.radians(pitch), math.radians(roll),
                                                               math.radians(yaw))).to_matrix().to_4x4()
    return ch.root.matrix_world @ Mh


def _target_world(target, t=None):
    import bpy
    if t is not None:
        bpy.context.scene.frame_set(F(t))
    if hasattr(target, "matrix_world"):
        return target.matrix_world.translation.copy()
    if hasattr(target, "head") and hasattr(target, "root"):
        return target.head.matrix_world.translation.copy()
    return Vector(target)


REACH = UPPER + LOWER - 0.03     # max shoulder->fist distance the solver can hit exactly
TORSO_HALF = (1.0, 0.5)          # torso half width / half depth (hip-local), fists may not sink into it
FIST_HALF = 0.5


def reachable(arm, p_local):
    """R6 reach envelope. Shoulders sit 1.5 studs off the midline and the arm is only 1.55 long, so many 'natural'
    targets (hands meeting at the midline, fist under the chin, crossed arms) are physically OUT of reach; the old
    solver then straightened the arm toward them and the fist landed in mid-air (wings, hands at the chin, hands that
    never meet). This keeps height + depth and slides the target sideways toward the arm's own side until it is
    reachable, then pushes it out of the torso, so a hand always LANDS (nearest reachable contact)."""
    side = 1 if arm == "armL" else -1
    p = Vector(p_local)
    sh = Vector((1.5 * side, 0, 1.55))
    d = p - sh
    if d.length > REACH:
        r2 = REACH ** 2 - d.y ** 2 - d.z ** 2
        if r2 > 0:                                   # slide x toward the shoulder line
            dx = math.sqrt(r2)
            p.x = sh.x - side * dx if side * (sh.x - p.x) > 0 else sh.x + side * dx
        else:                                        # even straight below/ahead is too far: aim at the target
            p = sh + d.normalized() * REACH
    if abs(p.x) < TORSO_HALF[0] + FIST_HALF * 0.6 and -TORSO_HALF[1] - FIST_HALF < p.y < TORSO_HALF[1] and -0.2 < p.z < 2.1:
        p.y = -TORSO_HALF[1] - FIST_HALF                     # in front of the chest, not inside it
        d = p - sh
        if d.length > REACH:
            p = sh + d.normalized() * REACH
    return p


def solve_arm(ch, arm, p_local, pole=None, twist=0.0):
    """Two-bone IK in hip space. p_local = fist target in hip-local coords. Returns (shoulder pose tuple, elbow flex).
    pole = hip-local direction the elbow should point (default down/back/out). Out-of-reach targets: arm straightens
    toward them."""
    side = 1 if arm == "armL" else -1
    sh = Vector((1.5 * side, 0, 1.55))
    d = reachable(arm, p_local) - sh
    L = max(0.25, min(UPPER + LOWER - 0.02, d.length))
    dh = d.normalized() if d.length > 1e-4 else Vector((0, 0, -1))
    ca = max(-1.0, min(1.0, (UPPER ** 2 + L ** 2 - LOWER ** 2) / (2 * UPPER * L)))
    a = math.acos(ca)
    pv = Vector(pole) if pole is not None else Vector((0.55 * side, 0.7, -0.6))
    p = pv - dh * pv.dot(dh)
    if p.length < 1e-4:
        p = Vector((side, 0, 0)) - dh * dh[0] * side
    p.normalize()
    u = dh * math.cos(a) - p * math.sin(a) * -1          # upper arm leans toward the pole
    elbow = u * UPPER
    fdir = (dh * L - elbow).normalized()
    bend = math.degrees(u.angle(fdir)) if (fdir - u).length > 1e-5 else 0.0
    z = -u
    yv = fdir - u * fdir.dot(u)
    y = -(yv.normalized()) if yv.length > 1e-5 else (-p - u * (-p).dot(u)).normalized()
    x = y.cross(z)
    R = Matrix((x, y, z)).transposed()
    if twist:
        R = R @ Matrix.Rotation(math.radians(twist), 3, "Z")
    e = R.to_euler("XYZ")
    fwd, out, tw = -math.degrees(e.x), -math.degrees(e.y) * side, math.degrees(e.z) * side
    return (fwd, out, tw), bend


def reach_pose(ch, t, target, hand="r", body=None, pole=None, offset=(0, 0, 0), local=False):
    """Pose dict {armX: (...), elbowX: flex} that puts the fist on `target` at time t (body = torso/hipz the character
    will have at t, so lean + reach solve together). local=True: target already in hip-local coords."""
    arm = _arm(hand)
    if local:
        pl = Vector(target) + Vector(offset)
    else:
        Mw = _hip_matrix(ch, t, body)
        pl = Mw.inverted() @ (_target_world(target, t) + Vector(offset))
    (fwd, out, tw), bend = solve_arm(ch, arm, pl, pole)
    return {arm: (fwd, out, tw), "elbow" + arm[-1]: bend}


def reach(ch, t, target, hand="r", body=None, expr=None, hold=None, release=None, pole=None, offset=(0, 0, 0),
          other=None, **kw):
    """Strike a REACH that lands on target at t+settle (hands really touch: cuff, locker, phone, shoulder).
    body: dict of torso/hipz/head to hit together (lean into the reach). other: pose for the free arm."""
    settle = kw.get("settle", SETTLE)
    pose = dict(body or {})
    pose.update(reach_pose(ch, t + fr(settle), target, hand, body, pole, offset))
    if other:
        pose.update(other)
    return strike(ch, t, pose, expr=expr, hold=hold, release=release, **kw)


def contact(ch, t0, t1, target, hand="r", body=None, pole=None, offset=(0, 0, 0), step=3, wobble=0.0, seed=0):
    """Keep the fist ON a (moving) target from t0 to t1: re-solves the IK every `step` frames (cuff being buttoned,
    hand on a moving shoulder, hand flat on a locker while the body sways). wobble = studs of fiddly hand motion
    (buttoning / adjusting). Key the approach yourself with reach(..., t0 - x)."""
    rnd = random.Random(seed)
    t = t0
    while t <= t1 + 1e-6:
        off = Vector(offset)
        if wobble:
            off += Vector((rnd.uniform(-1, 1) * wobble, rnd.uniform(-1, 1) * wobble * 0.5, rnd.uniform(-1, 1) * wobble))
        p = reach_pose(ch, t, target, hand, body, pole, off)
        _key(ch, t, p)
        t += fr(step)
    return t1


# ---------------------------------------------------------------- key-pose library (read at a glance)
# Every pose is asymmetric, has weight on one leg (contrapposto: hip roll + legs compensated so feet stay planted,
# the free knee flexes), a head tilt, and soft elbows. Values: Char.pose units. "ik" entries are hip-local fist
# targets solved at key time (hand on hip, hand to chin, arms crossed ...).
CHIN = (0.0, -1.05, 2.25)          # hip-local point just under the chin, in front of the face

# Arms: FK "out" values are the HANG relative to gravity (key_pose_dict cancels the hip roll, so a contrapposto never
# lifts an arm into a wing); 0-2 deg = the block arm brushes the torso. Elbows soft (8-20). IK hands stay below the
# chest and within the R6 reach envelope (see reachable()).
POSES = {
    "stand":      dict(torso=(6, 1, 3), head=(-5, 3, -7), armL=(3, -3, 0), armR=(4, -2, -6), elbowL=5, elbowR=9,
                       weight="R", kneeL=12),
    "relaxed":    dict(torso=(-6, 2, -3), head=(6, 3, 7), armL=(5, -2, -8), armR=(3, -3, 4), elbowL=9, elbowR=5,
                       weight="L", kneeR=14),
    "confident":  dict(torso=(10, -4, 4), head=(-10, -6, 7), armR=(4, -2, -6), elbowR=8, armL=(-4, -3, 8), elbowL=5,
                       weight="R", kneeL=10),      # loose hang, chest out. Old IK "thumb in pocket" (1.38,-0.75,0.42)
                                                   # left the fist floating 0.25 in front of the belly in MCUs (s07 R2)
    "hands_hips": dict(torso=(0, -5, 2), head=(-4, -8, 4), weight="R", kneeL=8,
                       ik={"armL": ((1.45, -0.62, 0.62), (0.5, 0.8, -0.6)), "armR": ((-1.45, -0.62, 0.62), (-0.5, 0.8, -0.6))}),
    "sad_slump":  dict(torso=(-6, 15, -4), head=(8, 26, 8), armL=(6, -3, 4), armR=(0, -2, -6), elbowL=8, elbowR=14,
                       hipz=-0.1, weight="L", kneeR=16),
    "thinking":   dict(torso=(-6, 3, 3), head=(-8, -6, 12), weight="L", kneeR=12,
                       ik={"armR": (CHIN, (-0.3, 0.2, -1)), "armL": ((0.35, -0.75, 1.0), (0.6, 0.6, -0.6))}),
    "arms_crossed": dict(torso=(5, -3, 2), head=(-6, -4, -6), weight="R", kneeL=10,
                       ik={"armL": ((-0.55, -0.85, 1.05), (1, 0.4, -0.6)), "armR": ((0.55, -0.95, 1.25), (-1, 0.4, -0.6))}),
    "shy":        dict(torso=(10, 6, -4), head=(-14, 16, 10), weight="L", kneeR=18,
                       ik={"armR": ((0.25, -0.75, 0.55), (-0.4, 0.6, -1)), "armL": ((0.6, -0.65, 0.5), (0.6, 0.6, -1))}),
    "excited":    dict(torso=(0, -6, 0), head=(0, -12, 8), armL=(150, 32, 0), armR=(40, 30, 0), elbowL=20, elbowR=70,
                       hipz=0.08, weight="L", kneeR=10),
    "point":      dict(torso=(-12, -2, 3), head=(-6, -2, 4), armR=(90, 6, 0), elbowR=4, armL=(6, -2, 6), elbowL=20,
                       weight="L", kneeR=10),
}
HANG_OUT = (-6.0, 3.0)     # allowed abduction (deg) of a HANGING FK arm (fwd < 45): keeps upper arms on the torso


def clamp_hang(pose):
    """Clamp the sideways 'out' of hanging FK arms into HANG_OUT (wing guard for idle / talk / stand poses).
    Raised or forward arms (|fwd| >= 45: points, waves, reaches) are left alone."""
    for arm in ("armL", "armR"):
        if arm in pose and isinstance(pose[arm], (tuple, list)):
            f_, o_, t_ = (tuple(pose[arm]) + (0, 0, 0))[:3]
            if abs(f_) < 45:
                pose[arm] = (f_, max(HANG_OUT[0], min(HANG_OUT[1], o_)), t_)
    return pose


def _weight(p, leg, roll=4.0):
    """Contrapposto: hip rolls toward the free leg, both legs counter-rotate so feet stay under the body, head
    counter-tilts. leg = weight-bearing leg 'L'/'R'."""
    s = 1 if leg == "L" else -1
    t = list(p.get("torso", (0, 0, 0))) + [0, 0, 0]
    r = t[2] if abs(t[2]) > 0.1 else -s * roll
    p["torso"] = (t[0], t[1], r)
    p.setdefault("legL", (0, r, 0)); p.setdefault("legR", (0, -r, 0))
    free = "legR" if leg == "L" else "legL"
    fl = list(p[free]) + [0, 0, 0]
    k = p.get("knee" + free[-1], 0)
    p[free] = (fl[0] + k * 0.45, fl[1] - s * 3, fl[2] + s * 6)      # free knee forward + toe out
    return p


def key_pose_dict(ch, name, mirror=False):
    """Resolve a POSES entry (IK hand targets, weight shift) into a plain pose dict. mirror swaps L/R."""
    src = dict(POSES[name])
    ik = src.pop("ik", {})
    leg = src.pop("weight", None)
    if mirror:
        sw = lambda k: k[:-1] + {"L": "R", "R": "L"}.get(k[-1], k[-1]) if k[-1] in "LR" else k  # noqa: E731
        out = {}
        for k, v in src.items():
            if k in ("torso", "head"):
                v = (-v[0], v[1], -v[2]) if isinstance(v, tuple) else v
            out[sw(k)] = v
        src = out
        ik = {sw(a): ((-p[0], p[1], p[2]), (-q[0], q[1], q[2])) for a, (p, q) in ik.items()}
        leg = {"L": "R", "R": "L"}.get(leg)
    for arm, (p, pole) in ik.items():
        (f, o, tw), b = solve_arm(ch, arm, p, pole)
        src[arm] = (f, o, tw); src["elbow" + arm[-1]] = b
    if leg:
        _weight(src, leg)
    roll = (tuple(src.get("torso", (0, 0, 0))) + (0, 0, 0))[2]
    for arm in ("armL", "armR"):             # gravity hang: FK arms cancel the hip roll (IK arms are hip-local targets)
        if arm in src and arm not in ik:
            side = 1 if arm == "armL" else -1
            f_, o_, t_ = (tuple(src[arm]) + (0, 0, 0))[:3]
            src[arm] = (f_, o_ + side * roll, t_)
    return clamp_hang(src) if not ik else _clamp_fk_only(src, ik)


def _clamp_fk_only(src, ik):
    fk = {k: v for k, v in src.items() if k in ("armL", "armR") and k not in ik}
    src.update(clamp_hang(fk))
    return src


def key_pose(ch, t, name, expr=None, mirror=False, hold=None, release=None, **kw):
    """Hit a library key pose at t with anticipation/overshoot/settle (strike)."""
    return strike(ch, t, key_pose_dict(ch, name, mirror), expr=expr, hold=hold, release=release, **kw)


def stance(ch, t, name="stand", mirror=False):
    """Set a key pose instantly at t (no anticipation) - the default non-stiff stand for any freshly built character."""
    ch.pose(t, **key_pose_dict(ch, name, mirror))
    return ch


# ---------------------------------------------------------------- v3.1 acting presets built on reach/contact
def cuff_point(ch, arm="armL"):
    """Cached empty ON the sleeve cuff of `arm` (forearm, ~0.42 above the fist centre: the cuff band of every cast
    sleeve). Contact targets for buttoning / tugging use this, not the fist."""
    cache = ch.__dict__.setdefault("_cuffs", {})
    if arm not in cache:
        j = getattr(ch, "joints", {}).get("elbow" + arm[-1])
        cache[arm] = (empty(f"{ch.name}_cuffpt_{arm}", (0, -0.05, -0.42), j, ch.coll) if j is not None else
                      empty(f"{ch.name}_cuffpt_{arm}", (0, -0.05, -1.17), ch.piv(arm), ch.coll))
    return cache[arm]


def _local_angle(Mw, pt):
    """Yaw (deg, Char convention: 0 = straight ahead, + = toward the character's LEFT/+x) of world point pt in the
    hip frame Mw. None when pt is on top of the hip."""
    q = Mw.inverted() @ Vector(pt); q.z = 0
    return math.degrees(math.atan2(q.x, -q.y)) if q.length > 1e-3 else None


def _cam_point(cam):
    camob = getattr(cam, "ob", cam)
    return camob.matrix_world.translation.copy() if hasattr(camob, "matrix_world") else Vector(cam)


def present_cuff(ch, t, arm="armL", expr=None, toward=None, cam=None):
    """Present the wrist so a partner can work on the cuff AND the camera reads it (v3.3 rebuild, test_seq s04 R4).
    Pose = 'show me your watch': upper arm HANGS on the torso (abduction <= 10 deg), elbow ~88 deg so the forearm is
    level at belly height, the whole arm swung about the vertical shoulder axis (twist) toward the partner (max 45 deg)
    - the cuff sits in front of the body on the presenting side, in the gap between the two characters.
    The old IK version pushed the fist OUT past the torso edge (|x| >= 1.6): the upper arm abducted ~40 deg (a wing at
    the partner) and its torso yaw turned the presenter's BACK to camera (body 42 deg off lens, face hidden).
    cam: the chest is twisted back toward the lens (torso yaw, max 20) until it is within 25 deg of camera.
    Head: upright (roll <= 4), yaw toward the cuff/partner, small downward look (pitch 12)."""
    side = "L" if arm == "armL" else "R"
    s_ = 1 if arm == "armL" else -1
    Mw = _hip_matrix(ch, t)
    ty = 0.0; ac = None
    if cam is not None:
        ac = _local_angle(Mw, _cam_point(cam))
        if ac is not None:
            ty = max(-20.0, min(20.0, ac - max(-25.0, min(25.0, ac))))
    pa = _local_angle(Mw, _target_point(toward)) if toward is not None else None
    pa = (pa - ty) if pa is not None else s_ * 20.0          # partner angle relative to the twisted chest
    tw = max(8.0, min(45.0, s_ * pa * 0.75))                 # swing the forearm toward the partner (outward = +)
    # v3.4 (R5 D2): the forearm must lie ACROSS the lens axis (cuff side-on to camera, readable) - a forearm aimed
    # toward the partner at a 3/4 camera pointed half at the lens and read as an end-on block. Pick the direction
    # perpendicular to the camera ray that is nearest the partner, swing up to 85 deg.
    if cam is not None and ac is not None:
        ac2 = ac - ty
        cands = [ac2 + 90.0, ac2 - 90.0]
        yaw_f = min(cands, key=lambda a: abs(((a - pa) + 180) % 360 - 180))
        tw = max(8.0, min(85.0, s_ * yaw_f))
    p = {"torso": (ty, 3, -s_ * 2), "head": (max(-30.0, min(30.0, pa * 0.55)), 12, s_ * 3),
         arm: (14, 2, tw), "elbow" + side: 88}
    other = "armR" if arm == "armL" else "armL"     # free arm: relaxed hang on the torso (no wing)
    p[other] = (4, -3, 0); p["elbow" + other[-1]] = 8
    ch._presented = (arm, t)
    return strike(ch, t, p, expr=expr, antic=2, move=5)


def _place_for_contact(ch, t, world_pt, hip_pt, yaw, body):
    """Root location (z kept) so that hip-local point `hip_pt` of ch, posed with `body` and facing `yaw`, lands on
    world_pt. Iterates on the analytic hip matrix (idle noise / squash included)."""
    p0 = Vector(sample(ch, t, ["loc"])["loc"])
    loc = Vector(p0)
    for _ in range(4):
        ch.pose(t, interp="CONSTANT", loc=tuple(loc), rot=yaw)
        Mw = _hip_matrix(ch, t, body)
        err = Vector(world_pt) - Mw @ Vector(hip_pt)
        loc.x += err.x; loc.y += err.y
    ch.pose(t, interp="CONSTANT", loc=tuple(loc), rot=yaw)
    return loc


def button_cuff(ch, t, other, cuff_arm="armL", dur=1.2, expr="smile", step_in=True, cam=None, cheat=0.4, present=True):
    """`ch` buttons `other`'s cuff. World-space solve, both characters together (v3.3):
      1. other presents the wrist (present_cuff toward ch, chest kept 3/4 to camera),
      2. ch faces the cuff, cheated `cheat` toward camera (0.4: 3/4 face, hands on the near side of her body),
      3. ch is placed (steps in over 10 f) so the cuff sits at her right-hand WORK point: front-right of her body at
         the cuff's own height (hip-local x -0.95, y -1.2) - the hand is out in the gap between the bodies, never in
         front of her own chest (R3: the old x -0.55 work point read as a dark block held against her torso),
      4. right fist ON TOP of the cuff (<0.2 studs, lens side), contact() re-solves every 2 f with a buttoning wobble;
         the left arm rests relaxed (no cradle across the partner's arm: out of R6 reach and it read as a wing).
    Verify: _contact_report measures fist->cuff over the span (ch._contact, STRESS_FAIL > 0.25)."""
    cpt = cuff_point(other, cuff_arm)
    tc = t + fr(SETTLE)
    if present:
        present_cuff(other, t - fr(3), cuff_arm, toward=ch, cam=cam)
    c = _target_world(cpt, tc)
    # lens-side grip: the fist sits on the camera-facing / top face of the forearm block, not inside it (R6 blocks are
    # 1 stud thick - a centre-on-centre contact hides the hand inside the sleeve, test_seq s04 R4).
    on_top = Vector((0, 0, 0.3))
    if cam is not None:
        tl = _cam_point(cam) - c; tl.z = 0
        if tl.length > 1e-3:
            on_top += tl.normalized() * 0.45
    c = c + on_top
    body = {"torso": (0, 8, 0), "head": (0, 14, 3), "hipz": -0.04}
    WORK_R = Vector((-0.95, -1.2, 1.0))
    if step_in:
        p0 = Vector(sample(ch, t - fr(10), ["loc"])["loc"])
        d = c - p0; d.z = 0
        if d.length < 1e-3:
            d = Vector((0, 1, 0))
        d.normalize()
        if cam is not None:
            tcam = _cam_point(cam) - c; tcam.z = 0
            d = (d * (1 - cheat) + tcam.normalized() * cheat).normalized()
        yaw = _unwrap(sample(ch, t - fr(10), ["rot"])["rot"], _yaw_of(d))
        ch.pose(t - fr(10), loc=tuple(p0), rot=sample(ch, t - fr(10), ["rot"])["rot"])
        _place_for_contact(ch, t - fr(1), c, WORK_R, yaw, body)
    pole_r = (-0.6, 0.6, -0.8)                     # elbow down/back/out a little: upper arm stays near the body
    left = {"armL": (4, -3, 0), "elbowL": 10}
    on_top = tuple(on_top)
    reach(ch, t, cpt, "r", body=body, expr=expr, pole=pole_r, offset=on_top, other=left)
    contact(ch, tc + fr(2), t + dur, cpt, "r", body, pole_r, on_top, step=2, wobble=0.03, seed=1)
    if os.environ.get("RBX_DEBUG"):
        import bpy
        hd = hand(ch, "armR")
        bpy.context.scene.frame_set(F(tc + fr(4))); bpy.context.view_layer.update()
        hr = hd.matrix_world.translation; cw = cpt.matrix_world.translation
        print(f"[button_cuff] {ch.name} R fist -> {other.name} cuff: centre {(hr - cw).length:.3f} studs")
    _contact_report(ch, other, cpt, t, t + dur)
    return t + dur


CUFF_HALF = 0.5          # half thickness of the forearm block: a fist centre this far from the cuff axis TOUCHES it


def _contact_report(ch, other, cpt, t0, t1):
    """Measure fist->cuff over the contact span (every 3 f) and store it on ch._contact (max, mean) as the SURFACE gap:
    centre distance minus CUFF_HALF (fist centre on the forearm's surface = 0). RBX_DEBUG prints it. Fails loudly
    (STRESS_FAIL tag) when the hand leaves the cuff (gap > 0.25)."""
    import bpy
    sc = bpy.context.scene; f0 = sc.frame_current
    hd = hand(ch, "armR"); ds = []
    for f in range(F(t0 + fr(SETTLE + 2)), F(t1) + 1, 3):
        sc.frame_set(f); bpy.context.view_layer.update()
        ds.append(max(0.0, (hd.matrix_world.translation - cpt.matrix_world.translation).length - CUFF_HALF))
    sc.frame_set(f0)
    if ds:
        ch._contact = (max(ds), sum(ds) / len(ds))
        if os.environ.get("RBX_DEBUG") or max(ds) > 0.25:
            print(f"[button_cuff] {ch.name}->{other.name} cuff contact over span: max {max(ds):.3f} mean "
                  f"{sum(ds) / len(ds):.3f}" + ("  STRESS_FAIL contact" if max(ds) > 0.25 else ""))


def tug_sleeve(ch, t, dur=1.2, expr="sad", sleeve_arm="armL", tugs=2):
    """Sad self-conscious tug (v3.2 rebuild). R6 truth: shoulders sit 1.5 off centre and the arm is 1.55 long, so two
    fists can only meet at the midline at belly height (hip-local z ~1.0, y -1.0) with near-straight arms
    angled IN and DOWN. Old version kept the fists at lower-chest height with the elbows pushed out (pole out/back):
    upper arms spread like wings and the fists stopped 0.15-0.33 apart. Now:
      - both elbows are tucked (pole down + slightly IN), upper arms angle in toward the belt -> no wing silhouette,
      - the held fist sits ON the midline, the tugging fist overlaps it (grip) - asserted < 1.05 between fist centres
        (fist blocks are 1.0 wide, so faces touch/overlap),
      - shoulders hunch forward (torso pitch), head down + tilted, asymmetric (tugging side leads),
      - each tug pulls the gripped sleeve DOWN and toward the tugging side, the held arm follows 60 %."""
    sx = 1 if sleeve_arm == "armL" else -1
    tug = "armR" if sleeve_arm == "armL" else "armL"
    # envelope math (hip-local, fist must stay at y <= -1.0 so it is in front of the torso): at z 1.0 the fist can
    # reach |x| >= 0.50, i.e. two 1.0-wide fists touch exactly at the midline. Lower = they cannot meet.
    # v3.3: fist centres 0.84 apart (the 1.0-wide blocks OVERLAP = a clasped grip). At 1.0 apart the angled blocks
    # touched only at one corner and read as two floating fists that never meet (test_seq s02 D3). z 1.2 is the
    # lowest height where both fists reach |x| 0.42 in front of the torso (R6 envelope, see reachable()).
    # v3.4 (R5 R4-2/D3): 1.2 still read as forearms held up in front of the chest (low lens). Hands now meet at the
    # LOWEST point the R6 envelope allows (z ~1.0, belt line) and are smaller (cast v3.4 hands with fingers); the
    # tugging hand sits a bit HIGHER on the held wrist (pinching the cuff edge), so the two hands read as one grip.
    H = Vector((sx * 0.36, -0.98, 0.98))                      # held hand at the belt, past the midline
    G = Vector((-sx * 0.36, -1.0, 1.12))                      # tugging hand on the held wrist/cuff
    pol_h, pol_g = (-sx * 0.15, 0.35, -1), (sx * 0.15, 0.35, -1)      # elbows DOWN and tucked in (never out)
    body = {"torso": (sx * -8, 14, sx * 3), "head": (sx * 10, 28, sx * 9), "hipz": -0.06, "kneeL": 8, "kneeR": 4,
            "legL": (0, 0, 0), "legR": (0, 0, 0)}
    p = dict(body)
    (f, o, tw), b = solve_arm(ch, sleeve_arm, H, pol_h)
    p[sleeve_arm] = (f, o, tw); p["elbow" + sleeve_arm[-1]] = b
    (f2, o2, tw2), b2 = solve_arm(ch, tug, G, pol_g)
    p[tug] = (f2, o2, tw2); p["elbow" + tug[-1]] = b2
    strike(ch, t, p, expr=expr, antic=3, move=6)
    n = tugs * 2
    for k in range(1, n + 1):
        tk = t + fr(SETTLE) + k * dur / n
        pull = Vector((-sx * 0.03, 0.0, -0.07)) if k % 2 else Vector()       # small tug down, fists stay together
        (f2, o2, tw2), b2 = solve_arm(ch, tug, G + pull, pol_g)
        (f, o, tw), b = solve_arm(ch, sleeve_arm, H + pull * 0.6, pol_h)
        _key(ch, tk, {tug: (f2, o2, tw2), "elbow" + tug[-1]: b2, sleeve_arm: (f, o, tw), "elbow" + sleeve_arm[-1]: b,
                      "head": (sx * 10, 28 + (4 if k % 2 else 0), sx * 9 + (2 if k % 2 else 0))})
    if os.environ.get("RBX_DEBUG"):
        import bpy
        bpy.context.scene.frame_set(F(t + fr(SETTLE) + 1e-3)); bpy.context.view_layer.update()
        d = (hand(ch, sleeve_arm).matrix_world.translation - hand(ch, tug).matrix_world.translation).length
        print(f"[tug_sleeve] {ch.name} fist-fist {d:.3f} studs (fists 1.0 wide: < 0.95 = overlapping grip)")
    return t + fr(SETTLE) + dur


def hide_wrist(ch, t, dur=1.2, expr="sad", arm="armL", rubs=2):
    """Sad self-conscious 'hide the wrist' (v3.5, replaces the two-handed tug in MCU/MS: R6 fists can only meet at the
    midline with both upper arms abducted ~25-35 deg = wing arms, test_seq R5 s02). ONE arm acts, asymmetric:
    upper arm HANGS on the torso (abduction <= 3 deg), elbow ~95 so the forearm crosses IN FRONT of the belly (twist
    inward), the wrist turned down and rubbed against the belly (forearm roll keys); the other arm hangs loose; head
    down + tilted toward the wrist, shoulders hunched, weight on the far leg."""
    sx = 1 if arm == "armL" else -1
    other = "armR" if arm == "armL" else "armL"
    p = {"torso": (sx * -6, 12, sx * 3), "head": (sx * 14, 26, sx * 8), "hipz": -0.05, "kneeL": 8 if sx < 0 else 3,
         "kneeR": 3 if sx < 0 else 8, arm: (16, -2, -sx * 38), "elbow" + arm[-1]: 95,
         other: (5, -3, 0), "elbow" + other[-1]: 10}
    strike(ch, t, p, expr=expr, antic=3, move=6)
    n = rubs * 2
    for k in range(1, n + 1):
        tk = t + fr(SETTLE) + k * dur / n
        r = (1 if k % 2 else -1)
        _key(ch, tk, {arm: (16 + 2 * r, -2, -sx * (38 + 6 * r)), "elbow" + arm[-1]: 95 - 4 * r,
                      "head": (sx * 14, 26 + (3 if k % 2 else 0), sx * 8 + (2 if k % 2 else 0))})
    return t + fr(SETTLE) + dur


def _cuff_local(ch, arm, pose, dz=0.0):
    """Hip-local position of the cuff of `arm` for the given pose dict (forward kinematics)."""
    side = 1 if arm == "armL" else -1
    fwd, out, tw = (tuple(pose[arm]) + (0, 0, 0))[:3]
    R = Euler((math.radians(-fwd), math.radians(-out * side), math.radians(tw * side))).to_matrix()
    bend = pose.get("elbow" + arm[-1], 0)
    Re = Euler((math.radians(-bend), 0, 0)).to_matrix()
    sh = Vector((1.5 * side, 0, 1.55))
    return sh + R @ (Vector((0, 0, -UPPER)) + Re @ Vector((-side * 0.0, -0.05, -0.62 + dz)))


def hand_to_face(ch, t, hand_="r", where="chin", expr=None, hold=None, release=None):
    """Hand to chin (thinking) / mouth (gasp) / forehead (facepalm) / cheek. Fist lands ON the face."""
    pts = {"chin": (0.0, -0.95, 2.3), "mouth": (0.0, -1.0, 2.55), "forehead": (0.0, -1.0, 3.05),
           "cheek": (0.45, -0.95, 2.6)}
    p = Vector(pts[where])
    arm = _arm(hand_)
    if arm == "armR" and where == "cheek":
        p.x = -p.x
    pose = {"head": (0, 6 if where != "forehead" else 14, 0)}
    (f, o, tw), b = solve_arm(ch, arm, p, (0.0, 0.3, -1))
    pose[arm] = (f, o, tw); pose["elbow" + arm[-1]] = b
    return strike(ch, t, pose, expr=expr, hold=hold, release=release)


def lean_on(ch, t, surface_pt, hand_="l", expr="smug", lean=12, pocket=True):
    """Casual lean: one hand FLAT on a wall/locker point (world), body tilts toward it, legs compensate so both feet
    stay planted with the outside ankle crossed over, head cocked away, free hand in the jacket pocket (no
    foreground arm). Put the character ~2.4-2.8 studs from the surface (shoulder-to-wall ~1.2), side-on to it."""
    arm = _arm(hand_)
    s = 1 if arm == "armL" else -1          # +1: wall on the character's left (+x local)
    roll = s * lean                          # hip roll toward the wall
    body = {"torso": (s * -8, 3, roll), "head": (s * -14, -2, -roll * 0.9), "hipz": -0.05}
    other = "armR" if arm == "armL" else "armL"
    os_ = 1 if other == "armL" else -1
    near, far = ("legL", "legR") if s > 0 else ("legR", "legL")
    side_of = lambda leg: 1 if leg == "legL" else -1  # noqa: E731
    rest_ = {near: (0, roll * side_of(near), 0),
             far: (10, roll * side_of(far) + 9, -s * 8), "knee" + far[-1]: 16, "knee" + near[-1]: 4}
    if pocket:     # v3.2: fist at its OWN hip pocket (x 1.3); the old (0.62,-0.62) target was pushed in front of the
                   # crotch by the torso guard and read as an arm crossing the chest (test_seq s06 R2)
        (f, o, tw), b = solve_arm(ch, other, (os_ * 1.3, -0.62, 0.5), (os_ * 0.9, 0.6, -0.2))
        rest_[other] = (f, o, tw); rest_["elbow" + other[-1]] = b
    else:
        rest_[other] = (8, 4, 0); rest_["elbow" + other[-1]] = 30
    # v3.2: the flat hand stays in a shoulder-height band (hip-local z 1.0-1.85). A target above the head (e.g. a
    # locker top at z 5.4) used to throw the arm up behind the head - it read as a broken mid-blend pose in MCUs.
    Mw = _hip_matrix(ch, t + fr(SETTLE), body)
    pl = Mw.inverted() @ _target_world(surface_pt, t + fr(SETTLE))
    pl.z = max(1.0, min(1.85, pl.z))
    tgt = Mw @ pl
    return reach(ch, t, tuple(tgt), hand_, body=body, expr=expr, other=rest_, pole=(s * 0.6, 0.6, -0.8), sq=0.04)


def hold_phone_ik(ch, t, arm="armR", prop=None, expr=None, look=True):
    """Phone held in front of the chest, screen to the face; head tips down to it (IK: the fist is in front of the
    sternum, so the phone reads in a 3/4 shot)."""
    if prop is not None:
        attach(ch, prop, arm, offset=(0, -0.25, 0.05), rot=(60, 0, 0))
    s = 1 if arm == "armL" else -1
    (f, o, tw), b = solve_arm(ch, arm, (s * 0.35, -1.05, 1.55), (s * 0.8, 0.6, -0.6))
    other = "armR" if arm == "armL" else "armL"
    pose = {arm: (f, o, tw), "elbow" + arm[-1]: b, other: (8, 6, 0), "elbow" + other[-1]: 18,
            "head": (0, 22 if look else 4, 0), "torso": (0, 4, 0)}
    return strike(ch, t, pose, antic=3, move=5, settle=5, over=0.08, expr=expr)


__all__ += ["reach", "reach_pose", "contact", "solve_arm", "POSES", "key_pose", "key_pose_dict", "stance",
            "button_cuff", "present_cuff", "tug_sleeve", "cuff_point", "reachable", "hand_to_face", "lean_on", "hold_phone_ik", "JOINTS"]
PRESETS.update({"phone": hold_phone_ik, "tug_sleeve": tug_sleeve, "hand_to_face": hand_to_face,
                "think": lambda ch, t: hand_to_face(ch, t, "r", "chin"), "sad_slump": lambda ch, t: key_pose(ch, t, "sad_slump", "sad"),
                "confident": lambda ch, t: key_pose(ch, t, "confident", "smug"),
                "arms_crossed": lambda ch, t: key_pose(ch, t, "arms_crossed")})


# ---------------------------------------------------------------- v3.1 camera-aware blocking (faces + hands read)
def stage(chars, t, cam, bias=0.45, partner=None, eyes=True):
    """Turn each character 3/4 to camera: body yaw = blend of 'face the camera' and 'face the partner' (bias 0 = full
    front, 1 = full profile toward partner; 0.35-0.5 reads best: both eyes + the gesture hand are visible).
    cam = Cam / camera object / location; partner: dict ch -> target (default: centroid of the others).
    Heads then aim at the partner (eyeline). Call AFTER the camera exists. Keys rot at t (CONSTANT)."""
    import bpy
    bpy.context.scene.frame_set(F(t))
    camob = getattr(cam, "ob", cam)
    cl = camob.matrix_world.translation.copy() if hasattr(camob, "matrix_world") else Vector(cam)
    for ch in chars:
        p = Vector(sample(ch, t, ["loc"])["loc"])
        others = [o for o in chars if o is not ch]
        tgt = (partner or {}).get(ch)
        if tgt is None and others:
            tgt = sum((Vector(sample(o, t, ["loc"])["loc"]) for o in others), Vector()) / len(others)
        tc = cl - p; tc.z = 0; tc.normalize()
        if tgt is not None:
            tp = _target_point(tgt) - p; tp.z = 0
            d = tc.lerp(tp.normalized(), bias) if tp.length > 1e-3 else tc
        else:
            d = tc
        ch.pose(t, interp="CONSTANT", rot=_yaw_of(d))
    if eyes and len(chars) > 1:
        eyeline(chars, t)
    return chars
__all__ += ["stage"]
