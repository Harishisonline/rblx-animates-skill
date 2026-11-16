"""Camera recipes: named shots with sane lens, distance, height and SMALL, eased moves.

v1 problem: nearly every shot was a big push-in (7 -> 3 units in ~1 s) plus handheld shake, which reads as frantic
("1.5x speed"). Reference channels (atlassdoc, harotalks, gibbsontv) mix many shot TYPES and keep most moves
gentle; the big moves (whip, crash zoom, dolly zoom) are saved for beats. Use these recipes, one per shot, and
vary them cut to cut (never the same recipe twice in a row).

    from rbx import cams
    cam = cams.hero_low(t0, t1, target=up(P, 4.4))
    cam = cams.ots(t0, t1, a=(0,-20,0), b=(4,-24,0))

All recipes return the Cam. Units: character is ~5.7 tall, head 1.24 wide (see PROPS scale notes).
Rule of thumb: push amount <= 18% unless it is a 'beat' recipe; hold at least 0.8 s before any move starts."""
import math
from mathutils import Vector
from .core import Cam, F, sfx, orbit_pos


def _tag(**kw):
    """Tag the sound cue just registered with sfx() (cues.json keeps the extra keys; tools/mix.py reads them)."""
    from . import core
    if core.CUES:
        core.CUES[-1].update(kw)

SLOW = 0.15     # fraction of distance a normal push moves
LATE = 0.12     # moves start this fraction into the shot (a short hold reads calmer)


def _drift(cam, strength=0.5):
    cam.handheld(strength)      # v1 used 1.0-2.0; keep it under 0.7 except for panic beats
    return cam


# ---------------------------------------------------------------- calm, character shots
def eye_med(t0, t1, target, d=7.5, yaw=-14, lens=40, pitch=3, push=SLOW, fstop=2.8):
    """Medium, eye level, 3/4 view, gentle push. The default 'person talks / reacts' shot."""
    cam = Cam()
    cam.push(t0, t1, target, d, d * (1 - push), yaw=yaw, pitch=pitch, lens=lens, fstop=fstop)
    return _drift(cam, 0.4)


def hero_low(t0, t1, target, d=8.0, lens=28, yaw=-16, pitch=-9, push=0.10, fstop=3.5):
    """Low angle looking up: power / pride / threat moments. Camera sits low, lens wide-ish."""
    cam = Cam()
    t = Vector(target)
    cam.push(t0, t1, (t.x, t.y, t.z - 1.6), d, d * (1 - push), yaw=yaw, pitch=pitch, lens=lens, fstop=fstop)
    return _drift(cam, 0.4)


def close_up(t0, t1, target, d=4.2, lens=55, yaw=-8, pitch=2, push=0.12, fstop=2.0):
    """Face fills ~60% of the frame. Use after every surprise (reaction), 0.8-1.6 s."""
    cam = Cam()
    cam.push(t0, t1, target, d, d * (1 - push), yaw=yaw, pitch=pitch, lens=lens, fstop=fstop)
    return _drift(cam, 0.3)


def ots(t0, t1, a, b, d=3.2, h=4.4, lens=45, side=1, fstop=2.4, drift=0.8):
    """Over-the-shoulder: camera behind character at `a` (xyz feet), looking at `b`. Alternate side=+1/-1 in dialogue."""
    a, b = Vector(a), Vector(b)
    fwd = (b - a); fwd.z = 0; fwd.normalize()
    right = Vector((fwd.y, -fwd.x, 0))
    c0 = a + Vector((0, 0, h)) - fwd * d + right * side * 1.0
    c1 = c0 + fwd * drift
    tgt = b + Vector((0, 0, h - 0.4))
    cam = Cam()
    cam.key(t0, tuple(c0), tuple(tgt), lens=lens, focus=tuple(tgt), fstop=fstop)
    cam.key(t1, tuple(c1), tuple(tgt), lens=lens, focus=tuple(tgt), fstop=fstop, ease="EASE_IN_OUT")
    return _drift(cam, 0.3)


def two_shot(t0, t1, a, b, lens=20, d=12.0, h=4.4, yaw=-10, fstop=5):
    """Both characters in frame, slow lateral drift. Establishes a conversation or a confrontation."""
    mid = (Vector(a) + Vector(b)) / 2
    cam = Cam()
    cam.push(t0, t1, (mid.x, mid.y, mid.z + h), d, d * 0.9, yaw=yaw, pitch=3, lens=lens, yaw1=yaw + 14, fstop=fstop)
    return _drift(cam, 0.3)


# ---------------------------------------------------------------- establishing / scale
def establish(t0, t1, target, d=22.0, lens=24, yaw=-20, pitch=12, push=0.18, fstop=8):
    """Wide, slightly high, slow push-in. First shot of a new location (2.0-3.0 s)."""
    cam = Cam()
    cam.push(t0, t1, target, d, d * (1 - push), yaw=yaw, pitch=pitch, lens=lens, yaw1=yaw + 10, fstop=fstop)
    return _drift(cam, 0.3)


def top_down(t0, t1, target, h=26.0, lens=32, spin=18, fstop=8):
    """Map / crowd / chaos overview, slow rotate."""
    cam = Cam()
    cam.push(t0, t1, target, h, h * 0.9, yaw=0, pitch=78, lens=lens, yaw1=spin, fstop=fstop)
    return cam


def pull_reveal(t0, t1, target, d0=5.0, d1=14.0, lens=28, yaw=0, pitch=6, fstop=6):
    """Start tight, pull back to reveal the scale of what is behind. Great for 'the whole city is...' beats."""
    cam = Cam()
    cam.push(t0, t1, target, d0, d1, yaw=yaw, pitch=pitch, lens=lens, fstop=fstop)
    return _drift(cam, 0.3)


def orbit_slow(t0, t1, target, d=8.0, yaw0=-35, yaw1=25, pitch=6, lens=32, fstop=3.5):
    cam = Cam()
    cam.orbit(t0, t1, target, d, yaw0, yaw1, pitch=pitch, lens=lens, steps=5, fstop=fstop)
    return _drift(cam, 0.25)


def track_side(ch, t0, t1, offset=(5.0, -4.0, 1.6), lens=30, look_up=4.0):
    """Tracking shot alongside a walking/running character."""
    cam = Cam()
    cam.track(ch, t0, t1, offset=offset, look_up=look_up, lens=lens)
    return _drift(cam, 0.5)


def pov(t0, t1, p0, p1, h=4.6, lens=24, bob=0.06):
    """First-person walk toward p1: camera at head height with a small walking bob."""
    cam = Cam()
    steps = max(4, int((t1 - t0) / 0.28))
    for i in range(steps + 1):
        k = i / steps
        p = Vector(p0).lerp(Vector(p1), k)
        z = h + math.sin(k * steps * math.pi) * bob
        look = Vector(p1) + Vector((0, 0, h - 0.2))
        cam.key(t0 + (t1 - t0) * k, (p.x, p.y, z), tuple(look), lens=lens, interp="LINEAR")
    return cam


# ---------------------------------------------------------------- insert for small things
def insert(t0, t1, target, d=2.0, lens=90, yaw=-25, pitch=8, rack_from=None, fstop=1.8):
    """Macro/insert on anything smaller than a hand (mosquito, key, switch, coin). Object fills 40-60% of the frame.
    rack_from: optional world point to start focused on (e.g. the character) then rack to the object."""
    cam = Cam()
    pos0 = orbit_pos(target, d * 1.15, yaw, pitch)
    pos1 = orbit_pos(target, d, yaw + 6, pitch)
    pos0 = (pos0[0], pos0[1], max(pos0[2], 0.6))      # never let the macro camera dip under the floor
    pos1 = (pos1[0], pos1[1], max(pos1[2], 0.6))
    cam.key(t0, pos0, target, lens=lens, focus=rack_from if rack_from else target, fstop=fstop)
    cam.key(t1, pos1, target, lens=lens, focus=target, fstop=fstop, ease="EASE_IN_OUT")
    return _drift(cam, 0.25)


# ---------------------------------------------------------------- beat moves (use sparingly, <= 1 per 6 shots)
def dutch_push(t0, t1, target, d=6.5, roll=11.0, lens=35, yaw=-12, pitch=2, push=0.22, fstop=3.0):
    """Something is wrong: tilted horizon plus a push-in."""
    cam = Cam()
    cam.push(t0, t1, target, d, d * (1 - push), yaw=yaw, pitch=pitch, lens=lens, roll=roll, fstop=fstop)
    return _drift(cam, 0.6)


def crash_zoom(t0, t1, target, t_hit, d=7.0, lens0=30, lens1=60, yaw=-10, pitch=3, dur=0.12, sfx_name="whoosh"):
    """Reveal/shock: hold, then lens punch at t_hit (0.4-1.0 s shots, comedy/horror beats)."""
    cam = Cam()
    cam.push(t0, t1, target, d, d * 0.92, yaw=yaw, pitch=pitch, lens=lens0)
    cam.crash(t_hit, lens0, lens1, dur)
    if sfx_name:
        sfx(t_hit, sfx_name, 0.8)
        if sfx_name == "whoosh":   # mix.py designs it: air swell + hit ATTACK on the lens punch, centred
            _tag(cut=True, kind="push", pan=[0.0, 0.0])
    return _drift(cam, 0.6)


def dolly_zoom(t0, t1, target, d0=10.0, d1=4.5, lens0=24, lens1=60, yaw=0, pitch=3):
    """Vertigo effect: move closer while zooming out the lens (or reverse). Realisation moments, 1.6-2.2 s."""
    cam = Cam()
    cam.push(t0, t1, target, d0, d1, yaw=yaw, pitch=pitch, lens=lens0, lens1=lens1, fstop=3.2)
    return cam


def whip(t0, t1, loc0, aim0, loc1, aim1, lens=26):
    """Transition between locations: 0.25-0.4 s, motion blur does the smear."""
    cam = Cam()
    cam.whip(t0, t1, loc0, aim0, loc1, aim1, lens=lens)
    return cam


def impact_shake(cam, t, strength=0.02, dur=0.25):
    """Short decaying shake on a hit. Call on any camera right after building it."""
    import bpy
    from .core import noise
    for i in range(3):
        noise(cam.ob, "location", i, strength * 3, 2)
    return cam


# ---------------------------------------------------------------- v2.1 additions
def crane(t0, t1, target, d=12.0, h0=2.0, h1=9.0, yaw=-15, lens=28, fstop=5.0):
    """Crane up: start low near the subject, rise while keeping it framed (arrivals, reveals, endings)."""
    cam = Cam()
    t = Vector(target)
    y = math.radians(yaw)
    off = Vector((math.sin(y) * d, -math.cos(y) * d, 0))
    cam.key(t0, tuple(t + off + Vector((0, 0, h0 - t.z))), tuple(t), lens=lens, focus=tuple(t), fstop=fstop)
    cam.key(t1, tuple(t + off * 1.05 + Vector((0, 0, h1 - t.z))), tuple(t), lens=lens, focus=tuple(t), fstop=fstop, ease="EASE_IN_OUT")
    return _drift(cam, 0.3)


def handheld_follow(ch, t0, t1, offset=(3.0, -7.0, 0.8), look_up=3.8, lens=32, shake=0.6):
    """Chase/escape: tracks the character with a little handheld energy (<= 0.7)."""
    cam = Cam()
    cam.track(ch, t0, t1, offset=offset, look_up=look_up, lens=lens)
    return _drift(cam, min(shake, 0.7))


def macro(t0, t1, target, d=3.4, lens=70, yaw=-6, pitch=6, fstop=2.2, push=0.12):
    """Macro insert straight onto a flat thing facing -Y (wrist tag, screen, scanner). Clamped above the floor."""
    cam = Cam()
    p0 = orbit_pos(target, d, yaw, pitch); p1 = orbit_pos(target, d * (1 - push), yaw + 3, pitch)
    p0 = (p0[0], p0[1], max(p0[2], 0.6)); p1 = (p1[0], p1[1], max(p1[2], 0.6))
    cam.key(t0, p0, target, lens=lens, focus=target, fstop=fstop)
    cam.key(t1, p1, target, lens=lens, focus=target, fstop=fstop, ease="EASE_IN_OUT")
    return _drift(cam, 0.2)


# ---------------------------------------------------------------- shot-type planner (used by the script->shots step)
SEQUENCE = ["establish", "eye_med", "close_up", "ots", "hero_low", "two_shot", "insert", "pull_reveal", "orbit_slow",
            "track_side", "dutch_push", "top_down", "pov"]


def pick(prev, beat="talk"):
    """Choose a recipe name that is not the same as the previous one and fits the beat."""
    by_beat = {
        "open": ["establish", "pull_reveal", "orbit_slow"],
        "talk": ["eye_med", "ots", "two_shot", "close_up"],
        "power": ["hero_low", "orbit_slow", "pull_reveal"],
        "scary": ["dutch_push", "close_up", "pov"],
        "small": ["insert"],
        "action": ["track_side", "orbit_slow", "hero_low"],
        "overview": ["top_down", "establish", "pull_reveal"],
        "shock": ["crash_zoom", "close_up", "dolly_zoom"],
    }
    opts = [o for o in by_beat.get(beat, by_beat["talk"]) if o != prev]
    return opts[0] if opts else "eye_med"


# =====================================================================================================================
# v3 CINEMATIC RECIPES (REF1, see docs/CAMERA_AND_FX.md). Lens numbers here mean a 36 mm sensor on the LONG (vertical)
# side, like a full-frame camera turned to portrait, so "18mm" really is the REF1 18mm look (the old Cam default of a
# 24 mm sensor made every lens ~1.5x tighter). Every recipe: ease-in-out over the whole shot + micro drift, so no frame
# is ever locked off, except ecu(..., still=True) for emotional holds.
# Units: kit units (character 5.7 tall). 1 unit ~= 0.3 m, so 30-60 cm above ground = h 1.0-2.0.
# =====================================================================================================================
SENSOR = 36.0
PUSH_RATE = 0.08          # default push-in: 8 % of the camera-subject distance per second (REF1: 6-10 %/s)


def _cine(cam):
    cam.cd.sensor_height = SENSOR
    return cam


def micro(cam, deg=0.3, loc=0.015, period=2.5):
    """Constant, slow 'breathing' drift (REF1: 0.3 deg). Smooth noise (period in s), never jittery."""
    from . import FPS
    from .core import noise
    sc = max(8, period * FPS)
    for i in range(3):
        noise(cam.ob, "rotation_euler", i, math.radians(deg) * (0.5 if i == 1 else 1.0), sc)
        if loc:
            noise(cam.ob, "location", i, loc, sc * 1.2)
    return cam


def shake(cam, deg=0.75, hz=3.0, loc=0.05):
    """Handheld run shake: amplitude deg (0.5-1.0), frequency hz (2-4)."""
    from . import FPS
    from .core import noise
    sc = max(2, FPS / hz)
    for i in range(3):
        noise(cam.ob, "rotation_euler", i, math.radians(deg) * (0.4 if i == 1 else 1.0), sc)
        noise(cam.ob, "location", i, loc, sc)
    return cam


def frac(t0, t1, rate=PUSH_RATE, cap=0.35):
    """Push fraction for a shot of this length at `rate` per second."""
    return min(cap, rate * max(0.0, t1 - t0))


def _blur(shutter):
    try:
        from . import look
        look.motion_blur(shutter)
    except Exception as e:
        print("motion_blur", e)


def _aim_pitch(pos, heading, pitch_deg):
    """A look-at point from pos along a compass heading (deg, 0 = +Y) tilted pitch_deg (+ = up)."""
    h, p = math.radians(heading), math.radians(pitch_deg)
    return tuple(Vector(pos) + Vector((math.sin(h) * math.cos(p), math.cos(h) * math.cos(p), math.sin(p))) * 10)


def push_in(t0, t1, target, d=7.0, lens=45, yaw=-12, pitch=-6, rate=PUSH_RATE, fstop=2.4, roll=0.0):
    """Generic eased push-in at rate (6-10 %/s). pitch < 0 = camera slightly below eye line looking up (REF1 MCU)."""
    cam = _cine(Cam())
    cam.push(t0, t1, target, d, d * (1 - frac(t0, t1, rate)), yaw=yaw, pitch=pitch, lens=lens, fstop=fstop, roll=roll)
    return micro(cam)


def mcu(t0, t1, face, d=None, lens=45, yaw=-12, rate=PUSH_RATE, fstop=2.2):
    """REF1 face MCU: 40-50mm, lens at chin height, 5-10 deg up-tilt, push 6-10 %/s. face = eye-level point."""
    d = d or lens * 0.10
    f = Vector(face)
    cam = _cine(Cam())
    p0 = orbit_pos(f, d, yaw, -7); p1 = orbit_pos(f, d * (1 - frac(t0, t1, rate)), yaw + 2, -7)
    cam.key(t0, p0, tuple(f), lens=lens, focus=tuple(f), fstop=fstop)
    cam.key(t1, p1, tuple(f), lens=lens, focus=tuple(f), fstop=fstop, ease="EASE_IN_OUT")
    return micro(cam)


def ground_low(t0, t1, target, lens=18, h=1.3, d=6.0, yaw=-15, tilt=28, rate=0.05, fstop=4.0, roll=0.0):
    """Very low hero angle: camera h above ground (1.3 ~= 40 cm), 18-20mm, tilted UP `tilt` deg (20-35),
    slow push 5 %/s. target = point on the subject (focus); the frame is aimed by tilt, not at the target."""
    cam = _cine(Cam())
    t = Vector(target)
    y = math.radians(yaw)
    back = Vector((math.sin(y), -math.cos(y), 0))
    heading = math.degrees(math.atan2(-back.x, -back.y))
    d1 = d * (1 - frac(t0, t1, rate))
    for tt, dd, ez in ((t0, d, None), (t1, d1, "EASE_IN_OUT")):
        pos = Vector((t.x, t.y, 0)) + back * dd + Vector((0, 0, h))
        cam.key(tt, tuple(pos), _aim_pitch(pos, heading, tilt), lens=lens, roll=roll, focus=tuple(t), fstop=fstop, ease=ez)
    return micro(cam)


def aerial_glide(t0, t1, target, h=60.0, dist=70.0, pitch=-35, lens=20, speed=0.15, heading=0.0, fstop=8.0, blur=0.5):
    """Drone establish: h up, looking down `pitch`, gliding forward speed*dist per second (8-25 %/s)."""
    cam = _cine(Cam())
    t = Vector(target)
    hd = math.radians(heading)
    fwd = Vector((math.sin(hd), math.cos(hd), 0))
    move = dist * speed * (t1 - t0)
    for tt, k, ez in ((t0, 0.0, None), (t1, 1.0, "EASE_IN_OUT")):
        pos = t - fwd * (dist - move * k) + Vector((0, 0, h))
        cam.key(tt, tuple(pos), _aim_pitch(pos, heading, pitch), lens=lens, focus=tuple(t), fstop=fstop, ease=ez)
    _blur(blur)
    return micro(cam, deg=0.15, loc=0.08)


def aerial_dive(t0, t1, target, h0=80.0, h1=22.0, d0=60.0, d1=18.0, lens=18, heading=0.0, fstop=8.0, blur=0.75):
    """Drone dive: descend and push toward the target (crater, house, crowd), accelerating (ease-in)."""
    cam = _cine(Cam())
    t = Vector(target)
    hd = math.radians(heading)
    fwd = Vector((math.sin(hd), math.cos(hd), 0))
    p0 = t - fwd * d0 + Vector((0, 0, h0)); p1 = t - fwd * d1 + Vector((0, 0, h1))
    cam.key(t0, tuple(p0), tuple(t), lens=lens, focus=tuple(t), fstop=fstop)
    cam.key(t1, tuple(p1), tuple(t), lens=lens, focus=tuple(t), fstop=fstop, ease="EASE_IN")
    _blur(blur)
    return micro(cam, deg=0.2, loc=0.05)


def fly_in_window(t0, t1, window, normal, inside_target, out_dist=60.0, out_h=25.0, lens=20, end_dist=6.0, blur=1.0,
                  t_pass=0.62):
    """Aerial -> through a window -> interior (REF1 #8-9). window: window centre, normal: unit vector pointing OUT of
    the building. Passes the glass at t_pass of the shot with a heavy motion-blur smear, ends end_dist from
    inside_target (looking at it). Hide the glass pane (or make it 1 face) so the camera can pass."""
    cam = _cine(Cam())
    w, n, it = Vector(window), Vector(normal).normalized(), Vector(inside_target)
    p0 = w + n * out_dist + Vector((0, 0, out_h))
    pa = w + n * 6.0 + Vector((0, 0, 0.5))
    pin = w - n * 1.5
    dirin = (it - pin); dirin.z = 0
    p1 = it - dirin.normalized() * end_dist + Vector((0, 0, 0.6))
    tp = t0 + (t1 - t0) * t_pass
    cam.key(t0, tuple(p0), tuple(w), lens=lens, focus=tuple(w), fstop=8)
    cam.key(t0 + (t1 - t0) * (t_pass - 0.18), tuple(pa), tuple(w - n * 4), lens=lens, focus=tuple(w), fstop=8, ease="EASE_IN")
    cam.key(tp, tuple(pin), tuple(it), lens=lens, focus=tuple(it), fstop=4, interp="LINEAR")
    cam.key(t1, tuple(p1), tuple(it), lens=lens, focus=tuple(it), fstop=2.8, ease="EASE_OUT")
    _blur(blur)
    sfx(tp, "whoosh", 0.9)   # the pass through the window = the accent (was tp - 0.1: 3 frames early)
    _tag(cut=True, kind="push", pan=[0.0, 0.0])
    return micro(cam, deg=0.2)


def truck(t0, t1, subject, fg=None, d=7.0, h=2.0, lens=28, heading=0.0, rate=0.06, fstop=2.8, tilt=6):
    """Sideways tracking (lateral truck) parallel to the subject, past an out-of-focus foreground object.
    heading = compass direction the camera LOOKS (0 = +Y). Travel per second = rate * frame width at subject distance.
    fg: optional foreground object/point; the camera line is placed so it sweeps past it."""
    cam = _cine(Cam())
    s = Vector(subject)
    hd = math.radians(heading)
    look = Vector((math.sin(hd), math.cos(hd), 0)); side = Vector((look.y, -look.x, 0))
    width = d * SENSOR * (9 / 16) / lens
    travel = width * rate * (t1 - t0)
    base = Vector((s.x, s.y, 0)) - look * d + Vector((0, 0, h))
    if fg is not None:
        fp = Vector(fg.location if hasattr(fg, "location") else fg)
        base += side * ((fp - base).dot(side))      # centre the sweep on the FG object
    for tt, k, ez in ((t0, -0.5, None), (t1, 0.5, "EASE_IN_OUT")):
        pos = base + side * travel * k
        cam.key(tt, tuple(pos), _aim_pitch(pos, heading, tilt), lens=lens, focus=tuple(s), fstop=fstop, ease=ez)
    return micro(cam, deg=0.2)


def rack(cam, t, near, far, frames=15, fstop=None):
    """Rack focus on an existing camera: focus on `near` at t, land on `far` frames later (12-18 f). Points/objects."""
    from . import FPS
    cd, ob = cam.cd, cam.ob
    cd.dof.use_dof = True
    if fstop:
        cd.dof.aperture_fstop = fstop
    sc = __import__("bpy").context.scene
    for tt, p in ((t, near), (t + frames / FPS, far)):
        sc.frame_set(F(tt))
        pv = Vector(p.location if hasattr(p, "location") else p)
        cd.dof.focus_distance = (pv - ob.matrix_world.translation).length
        cd.dof.keyframe_insert("focus_distance", frame=F(tt))
    from .core import set_interp
    set_interp(cd, "dof.focus_distance", F(t), "BEZIER", "EASE_IN_OUT")
    # hold focus before t: drop any earlier focus keys that would fight the rack
    return cam


def run_follow(t0, t1, subject, offset=(1.5, -6.0, 2.2), lens=22, deg=0.75, hz=3.0, fstop=3.5, step=0.2, look_up=3.2,
               blur=0.5):
    """Handheld run-follow, low behind/front (40-80 cm), shake 0.5-1 deg at 2-4 Hz, motion blur 180 deg.
    subject: character (with .root), any object, or a callable t -> (x,y,z)."""
    import bpy
    cam = _cine(Cam())
    sc = bpy.context.scene

    def pos_at(t):
        if callable(subject):
            return Vector(subject(t))
        ob = getattr(subject, "root", subject)
        sc.frame_set(F(t))
        return Vector(ob.matrix_world.translation)
    t = t0
    while t <= t1 + 1e-6:
        p = pos_at(t)
        tgt = p + Vector((0, 0, look_up))
        cam.key(t, tuple(p + Vector(offset)), tuple(tgt), lens=lens, focus=tuple(tgt), fstop=fstop, interp="LINEAR")
        t += step
    shake(cam, deg, hz)
    _blur(blur)
    return cam


def dutch(t0, t1, target, roll=16.0, lens=24, d=5.5, yaw=-20, pitch=-14, rate=0.08, fstop=3.0):
    """Dutch beat (switch slam, clock): low, rolled 12-20 deg, push-in. One shot only, then back to level."""
    cam = _cine(Cam())
    cam.push(t0, t1, target, d, d * (1 - frac(t0, t1, rate)), yaw=yaw, pitch=pitch, lens=lens, roll=roll, fstop=fstop)
    return micro(cam, deg=0.35)


def ecu(t0, t1, target, lens=85, d=None, yaw=-6, pitch=0, fstop=2.0, still=True, rate=0.04):
    """Extreme close-up 70-100mm f/1.8-2.8 (eye + tear, shocked face, prop text). still=True: emotional hold, only
    the 0.3 deg breathing drift; still=False: slow 4 %/s push."""
    d = d or lens * 0.045
    cam = _cine(Cam())
    k = 0.0 if still else frac(t0, t1, rate)
    cam.push(t0, t1, target, d, d * (1 - k), yaw=yaw, pitch=pitch, lens=lens, fstop=fstop)
    return micro(cam, deg=0.3, loc=0.004)


def prop_macro(t0, t1, target, lens=85, d=None, down=40, yaw=-20, fstop=2.0, rate=0.08, rack_from=None, rack_at=None):
    """Prop insert: 70-100mm f/1.8-2.8, 25-45 cm above, 30-60 deg down, slow push 5-10 %/s, optional rack from a
    point (rack_at = time of the rack, default 25 % in)."""
    d = d or lens * 0.035
    cam = _cine(Cam())
    p0 = orbit_pos(target, d, yaw, down); p1 = orbit_pos(target, d * (1 - frac(t0, t1, rate)), yaw + 4, down)
    p0 = (p0[0], p0[1], max(p0[2], 0.15)); p1 = (p1[0], p1[1], max(p1[2], 0.15))
    cam.key(t0, p0, target, lens=lens, focus=rack_from if rack_from is not None else target, fstop=fstop)
    cam.key(t1, p1, target, lens=lens, focus=target, fstop=fstop, ease="EASE_IN_OUT")
    if rack_from is not None:
        rack(cam, rack_at if rack_at is not None else t0 + (t1 - t0) * 0.25, rack_from, target)
    return micro(cam, deg=0.2, loc=0.003)


def whip_pan(t0, t1, pos, heading0, heading1, pitch=0.0, lens=24, t_whip=None, whip_frames=8, shutter=1.0, focus=8.0):
    """In-shot whip pan from heading0 to heading1 (deg) around a fixed camera position, taking whip_frames
    (6-12) starting at t_whip (default: middle). The motion blur makes the smear. Also use fx.whip_out/whip_in for
    a whip CUT between two shots."""
    from . import FPS
    cam = _cine(Cam())
    tw = t_whip if t_whip is not None else (t0 + t1) / 2 - whip_frames / FPS / 2
    te = tw + whip_frames / FPS
    cam.key(t0, tuple(pos), _aim_pitch(pos, heading0 - 3, pitch), lens=lens, focus=focus, fstop=4)
    cam.key(tw, tuple(pos), _aim_pitch(pos, heading0, pitch), lens=lens, focus=focus, fstop=4, ease="EASE_IN_OUT")
    cam.key(te, tuple(pos), _aim_pitch(pos, heading1, pitch), lens=lens, focus=focus, fstop=4, ease="EASE_IN_OUT")
    cam.key(t1, tuple(pos), _aim_pitch(pos, heading1 + 3, pitch), lens=lens, focus=focus, fstop=4, ease="EASE_OUT")
    from .core import fix_euler
    fix_euler(cam.ob)
    _blur(shutter)
    # whoosh PEAK in the middle of the whip (was at its start: half a whip early), swept with the turn
    sfx((tw + te) / 2, "whoosh", 0.9)
    sg = 1.0 if heading1 >= heading0 else -1.0   # compass heading up = turning right: sweep left -> right
    _tag(cut=True, kind="whip", pan=[-0.7 * sg, 0.7 * sg])
    return micro(cam, deg=0.2)


def overhead(t0, t1, target, h=18.0, lens=24, spin=12.0, rate=0.05, fstop=6.0):
    """Top-down 24-28mm straight down, slow yaw 3-6 deg/s plus a small push."""
    cam = _cine(Cam())
    t = Vector(target)
    for tt, k, ez in ((t0, 0, None), (t1, 1, "EASE_IN_OUT")):
        hh = h * (1 - frac(t0, t1, rate) * k)
        pos = t + Vector((0, 0, hh))
        cam.ob.location = pos
        cam.ob.rotation_euler = (0, 0, math.radians(spin * k))
        cam.ob.keyframe_insert("location", frame=F(tt)); cam.ob.keyframe_insert("rotation_euler", frame=F(tt))
        cam.cd.lens = lens; cam.cd.keyframe_insert("lens", frame=F(tt))
        cam.cd.dof.use_dof = True; cam.cd.dof.aperture_fstop = fstop; cam.cd.dof.focus_distance = hh
        cam.cd.dof.keyframe_insert("focus_distance", frame=F(tt))
    return micro(cam, deg=0.15)


CINE_BY_BEAT = {
    "open": ["aerial_glide", "aerial_dive", "truck"],
    "face": ["mcu", "push_in", "ecu"],
    "emotion": ["ecu", "mcu"],
    "power": ["ground_low", "dutch"],
    "prop": ["prop_macro", "ecu"],
    "run": ["run_follow", "truck", "ground_low"],
    "overview": ["overhead", "aerial_glide"],
    "transition": ["fly_in_window", "whip_pan", "aerial_dive"],
}


def hands_guard(cam, chars, t0, t1, zone=0.2, step=3, label=""):
    """v3.5 MCU near-lens guard (test_seq R5 s02/s05/s07: big block hands/forearms at the bottom of the frame read as
    wings / fists thrust at the lens). Samples every fist over [t0, t1]; a fist that projects INSIDE the frame's bottom
    `zone` (or within 0.06 of the left/right edge) prints 'STRESS_FAIL hand_near_lens' (qa_gate scans render logs).
    Fix by cropping at mid-chest (eyes ~0.33 from the top, d <= 7 at 60 mm), camera at/above eye level, body 3/4."""
    import bpy
    from bpy_extras.object_utils import world_to_camera_view
    from . import motion as _mo
    camob = getattr(cam, "ob", cam)
    sc = bpy.context.scene; f0 = sc.frame_current; bad = []
    for ch in chars:
        for arm in ("armL", "armR"):
            hd = _mo.hand(ch, arm)
            for f in range(F(t0), F(t1), step):
                sc.frame_set(f); bpy.context.view_layer.update()
                p = world_to_camera_view(sc, camob, hd.matrix_world.translation)
                if p.z > 0 and 0.0 <= p.x <= 1.0 and 0.0 <= p.y <= 1.0:      # fist centre inside the frame
                    if p.y < zone or p.x < 0.06 or p.x > 0.94:
                        bad.append((ch.name, arm, f, round(p.x, 2), round(p.y, 2)))
    sc.frame_set(f0)
    if bad:
        print(f"[hands_guard] {label} STRESS_FAIL hand_near_lens: {len(bad)} samples, first {bad[:3]}")
    else:
        print(f"[hands_guard] {label} ok: no fist in the bottom {int(zone * 100)} % / edges")
    return bad
