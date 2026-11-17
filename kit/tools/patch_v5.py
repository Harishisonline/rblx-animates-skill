"""Kit v5.0 patch (2026-11-17): applies the DRIPDYL_STYLE_GUIDE defaults. Run from the kit root. Idempotent-ish:
refuses to patch a file that already carries the v5 marker. Backups: <file>.bak_v5."""
import os, re, shutil, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/RobloxStories")
MARK = "v5 (DRIPDYL guide)"


def patch(rel, fn):
    p = os.path.join(ROOT, rel)
    s = open(p).read()
    if MARK in s:
        print("skip (already v5):", rel); return
    shutil.copy2(p, p + ".bak_v5")
    s2 = fn(s)
    assert s2 != s, rel
    open(p, "w").write(s2)
    print("patched:", rel)


# 1. shotlib.frame_on: 3/4 yaw alternating, pitch -4, 45 mm, 15 % push from frame 1, focus on the main head, f/5.6 two-shots
def p_shotlib(s):
    old_sig = '''def frame_on(chars, t0, t1, shot="med", yaw=None, lens=35, margin=0.06, pitch=4, push=0.06, fstop=2.8, name="Cam_f",
             extra=(), headroom=0.04, register=True, clear=True):'''
    new_sig = '''FRAME_YAW = 22.0     # v5 (DRIPDYL guide): 3/4 angle, side alternates call to call (was 0 = straight-on)
FRAME_PITCH = -4.0   # v5: camera slightly low (was +4, looking down)
FRAME_LENS = 45.0    # v5: was 35
FRAME_PUSH = 0.15    # v5: 15 % push that starts on frame 1 (was 6 % ease-in-out)
_FRAME_SIDE = [1]


def frame_on(chars, t0, t1, shot="med", yaw=None, lens=None, margin=0.06, pitch=None, push=None, fstop=None, name="Cam_f",
             extra=(), headroom=0.04, register=True, clear=True, focus="head", alternate=True):'''
    assert s.count(old_sig) == 1
    s = s.replace(old_sig, new_sig)
    old_head = '''    chars = list(chars)
    pts = [p for ch in chars for p in _frame_points(ch, t0 + 0.3, shot)] + [Vector(e) for e in extra]'''
    new_head = '''    # v5 (DRIPDYL guide) defaults; pass the ACTIVE character(s) only - the speaker/reactor, not everyone in the room.
    lens = FRAME_LENS if lens is None else lens
    pitch = FRAME_PITCH if pitch is None else pitch
    push = FRAME_PUSH if push is None else push
    if yaw is None:
        yaw = FRAME_YAW * _FRAME_SIDE[0]
        if alternate:
            _FRAME_SIDE[0] *= -1
    chars = list(chars)
    if fstop is None:
        fstop = 2.8 if len(chars) <= 1 else 5.6     # two-shots stay sharp on both faces
    pts = [p for ch in chars for p in _frame_points(ch, t0 + 0.3, shot)] + [Vector(e) for e in extra]'''
    assert s.count(old_head) == 1
    s = s.replace(old_head, new_head)
    old_key = '''    c = Cam(name, lens)
    c.key(t0, tuple(best), tuple(tgt), lens, focus=tuple(tgt), fstop=fstop)
    c.key(t1, tuple(best + (tgt - best) * push), tuple(tgt), lens, focus=tuple(tgt), fstop=fstop, ease="EASE_IN_OUT")
    cams.micro(c, deg=0.3, loc=0.015, period=2.2)'''
    new_key = '''    floor = min(p.z for p in pts) + 0.8                # v5: a low camera never goes under the floor
    if best.z < floor:
        best = Vector((best.x, best.y, floor))
    end = best + (tgt - best) * push
    if end.z < floor:
        end = Vector((end.x, end.y, floor))
    ftgt = tgt                                          # v5: focus on the main character's head, not between people
    if focus == "head" and chars:
        try:
            ftgt = mo._head_world(chars[0], t0 + 0.3)
        except Exception as e:
            print("frame_on focus", e)
    c = Cam(name, lens)
    c.key(t0, tuple(best), tuple(tgt), lens, focus=tuple(ftgt), fstop=fstop, interp="CUBIC", ease="EASE_OUT")
    c.key(t1, tuple(end), tuple(tgt), lens, focus=tuple(ftgt), fstop=fstop)
    cams.micro(c, deg=0.3, loc=0.015, period=2.2)'''
    assert s.count(old_key) == 1
    return s.replace(old_key, new_key)


patch("rbx/shotlib.py", p_shotlib)


# 2. shotkit.build: motion blur OFF by default; recipes that need it (whip_pan, run_follow, aerials) or a shot calling
#    look.motion_blur(0.35-0.5) switch it on. Frame 0 is always sharp.
def p_shotkit(s):
    old = "        setup_render(F(S[\"t0\"]), F(S[\"t1\"]) - 1, samples=samples, pct=pct)\n        _lookmod.EXPOSURE = 0.0"
    new = ("        setup_render(F(S[\"t0\"]), F(S[\"t1\"]) - 1, samples=samples, pct=pct, blur=False)   "
           "# v5 (DRIPDYL guide): blur off unless the shot asks\n        _lookmod.EXPOSURE = 0.0")
    assert s.count(old) == 1
    return s.replace(old, new)


patch("tools/shotkit.py", p_shotkit)


# 3. motion.py: named timing presets for strike()
def p_motion(s):
    old = "LEAD = 2           # head leads body by 2-3 f; eyes lead head by 2 f\n"
    new = old + ('# v5 (DRIPDYL guide): timing presets for strike(ch, t, pose, **SNAP)\n'
                 'NORMAL = dict(antic=4, move=4, over=0.12, settle=5)   # everyday gesture / turn\n'
                 'SNAP = dict(antic=2, move=3, over=0.18, settle=3)     # comedy hit, reaction pop\n')
    assert s.count(old) == 1
    return s.replace(old, new)


patch("rbx/motion.py", p_motion)

# 4. words.py: alignment may carry no global tag prefix (v5 tts.py strips all tags)
def p_words(s):
    old = "s=''.join(ch); pre='[fast, urgent, breathless] '\nassert s.startswith(pre), s[:40]\nk=len(pre)"
    new = ("s=''.join(ch); pre='[fast, urgent, breathless] '\n"
           "k=len(pre) if s.startswith(pre) else 0   # v5 (DRIPDYL guide): tts.py v5 strips tags from the alignment")
    assert s.count(old) == 1, 'words.py anchor'
    return s.replace(old, new)


patch("tools/ep_audio/words.py", p_words)
print("done")
