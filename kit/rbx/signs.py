"""READABLE TEXT PROPS: real, legible in-world text (Blender font curves, not baked PNGs), so any line can be changed
per story in code. All builders face -Y (toward a camera looking +Y) and take `rot` = yaw in degrees; every builder
returns its root empty (parent it to a hand / wall / vehicle).

    from rbx import signs as S
    S.sign("bake", "BAKERY", loc, w=7, h=1.4, bg="#2f4a3a", fg="#f3e6c4")                 # shop fascia
    S.closed_sign("cs", loc, t_flip=3.2)                                                  # OPEN -> CLOSED flip at t
    S.poster("p", "LOST CAT", "Answers to 'Mochi'\\nCall 555-0192", loc)                   # paper poster
    S.note("n", "Don't forget\\nyour cuff, Harry", loc, rot=10)                           # handwriting
    S.screen("scr", ["ABOUT YOU", "not TO you"], loc, w=9, h=5)                           # glowing billboard / TV
    S.street_screen("big", lines, loc)                                                   # pole/building mounted LED wall
    S.phone("ph", loc, app="messages", title="MOM", msgs=[("them", "Don't come home.")])  # phone with message UI
    S.phone("ph", loc, app="choice", title="@Harry", buttons=["EXPOSE", "PROTECT"])        # choice UI
    S.laptop("lap", loc, title="KITCHEN-LAPTOP", posts=["Harry's so gentle <3", ...])     # open laptop, social feed
    S.wrist_counter("w", loc, seq=[(0.0, "000"), (2.1, "001")])                           # glowing 3-digit wrist number
    S.typed("msg", "Don't come home.", loc, t0=1.0, cps=14)                                # type-on text
    S.show(ob, t_on, t_off)                                                               # visibility window helper
Fonts: S.FONT['bold'|'ui'|'hand'|'comic'] (OFL, assets/fonts). Text sizes: size = cap height-ish in scene units; for a
1080x1920 close-up keep text >= 1/25 of frame height."""
import os
from .core import box, plane, text, empty, mat, hexc, F, D
from . import ASSETS

_FD = os.path.join(ASSETS, "fonts")
FONT = {k: os.path.join(_FD, f) for k, f in
        dict(bold="Poppins-ExtraBold.ttf", ui="Inter-Variable.ttf", hand="PatrickHand-Regular.ttf",
             comic="Bangers-Regular.ttf").items()}


def _f(kind):
    p = FONT.get(kind, kind)
    return p if p and os.path.exists(p) else None


def _flat(hx, rough=0.5):
    return mat(f"sg_{hx}_{rough:g}", hexc(hx), rough)


def _glow(hx, s=3.0):
    return mat(f"sg_glow_{hx}_{s:g}", hexc(hx), 0.4, emit=hexc(hx), estr=s)


def _root(name, loc, rot, coll, parent=None):
    return empty(name, loc, parent=parent, coll=coll, rot=(0, 0, rot))


def label(name, body, loc, size=0.6, color="#111111", font="bold", glow=0.0, parent=None, coll=None, align="CENTER",
          rot=(90, 0, 0), extrude=0.0, spacing=1.0):
    """Any text. glow>0 makes it emissive (screens). Multi-line with \\n."""
    m = _glow(color, glow) if glow else _flat(color, 0.6)
    ob = text(name, body, loc, size, m, rot, extrude, coll, _f(font), align, parent)
    ob.data.space_line = spacing
    return ob


def show(ob, t_on=None, t_off=None):
    """Hide an object (render + viewport) outside [t_on, t_off)."""
    def k(f, hidden):
        ob.hide_render = hidden; ob.hide_viewport = hidden
        ob.keyframe_insert("hide_render", frame=f); ob.keyframe_insert("hide_viewport", frame=f)
    if t_on is not None:
        k(1, True); k(F(t_on), False)
    else:
        k(1, False)
    if t_off is not None:
        k(F(t_off), True)
    if ob.animation_data and ob.animation_data.action:
        try:
            from .core import fcurves
            for fc in fcurves(ob.animation_data.action):
                for kp in fc.keyframe_points:
                    kp.interpolation = "CONSTANT"
        except Exception:
            pass
    return ob


# ------------------------------------------------------------------ boards
def sign(name, body, loc, w=6.0, h=1.3, bg="#24323f", fg="#f3e6c4", rot=0.0, coll=None, font="bold", lit=0.0,
         size=None, frame="#1a1a1a", parent=None, depth=0.25):
    r = _root(name, loc, rot, coll, parent)
    box(name + "_bd", (w, depth, h), (0, 0, 0), _flat(bg, 0.45), 0.05, parent=r, coll=coll)
    if frame:
        box(name + "_fr", (w + 0.16, depth * 0.8, h + 0.16), (0, 0.04, 0), _flat(frame, 0.4), 0.04, parent=r, coll=coll)
    t = label(name + "_t", body, (0, -depth / 2 - 0.08, 0), size or h * 0.55, fg, font, lit, r, coll)
    fit_text(t, w * 0.86, h * 0.72)
    return r


def fit_text(t, max_w, max_h):
    """Shrink a text object so it always sits INSIDE its board (lesson 2026-11-15: text ran off signs)."""
    try:
        import bpy
        bpy.context.view_layer.update()
        dw, dh = t.dimensions.x, t.dimensions.y
        if dw <= 0 or dh <= 0:
            return t
        k = min(1.0, max_w / dw, max_h / dh)
        if k < 1.0:
            t.data.size *= k
    except Exception as e:
        print("fit_text:", e)
    return t


def closed_sign(name, loc, rot=0.0, coll=None, t_flip=None, parent=None):
    """Hanging door sign; OPEN (green) until t_flip, then CLOSED (red). t_flip None = CLOSED always."""
    r = _root(name, loc, rot, coll, parent)
    box(name + "_bd", (2.2, 0.08, 1.0), (0, 0, 0), _flat("#f4efe2", 0.5), 0.04, parent=r, coll=coll)
    for s in (-1, 1):
        box(f"{name}_str{s}", (0.04, 0.04, 0.9), (s * 0.7, 0, 0.9), _flat("#222222"), 0, parent=r, coll=coll, rot=(0, s * 25, 0))
    c = label(name + "_c", "CLOSED", (0, -0.06, 0), 0.5, "#c62828", "bold", 0, r, coll)
    if t_flip is not None:
        o = label(name + "_o", "OPEN", (0, -0.06, 0), 0.55, "#1f8a3a", "bold", 0, r, coll)
        show(o, None, t_flip); show(c, t_flip, None)
    return r


def poster(name, title, body, loc, rot=0.0, w=2.4, h=3.2, paper="#f4ecd6", ink="#1d1d1d", accent="#c62828",
           coll=None, parent=None, tilt=0.0):
    r = _root(name, loc, rot, coll, parent)
    r.rotation_euler[1] = tilt * 0.01745
    box(name + "_pp", (w, 0.03, h), (0, 0, 0), _flat(paper, 0.8), 0.0, parent=r, coll=coll)
    label(name + "_ti", title, (0, -0.03, h * 0.32), w * 0.16, accent, "bold", 0, r, coll)
    label(name + "_bo", body, (0, -0.03, -h * 0.08), w * 0.075, ink, "bold", 0, r, coll, spacing=1.15)
    for sx in (-1, 1):  # tape corners
        box(f"{name}_tp{sx}", (0.4, 0.035, 0.14), (sx * (w / 2 - 0.1), -0.005, h / 2 - 0.05), _flat("#e8e0b8", 0.6), 0,
            parent=r, coll=coll, rot=(0, sx * 35, 0))
    return r


def note(name, body, loc, rot=0.0, w=1.6, h=1.6, paper="#fff27a", ink="#1b2a6b", coll=None, parent=None, tilt=6.0,
         size=None):
    """Sticky note / handwritten paper."""
    r = _root(name, loc, rot, coll, parent)
    r.rotation_euler[1] = tilt * 0.01745
    box(name + "_pp", (w, 0.02, h), (0, 0, 0), _flat(paper, 0.85), 0.0, parent=r, coll=coll)
    label(name + "_t", body, (0, -0.02, 0), size or w * 0.15, ink, "hand", 0, r, coll, spacing=1.05)
    return r


def chalk(name, body, loc, rot=0.0, w=10.0, h=4.0, coll=None, parent=None):
    """Chalkboard with handwritten chalk text."""
    r = _root(name, loc, rot, coll, parent)
    box(name + "_fr", (w + 0.4, 0.2, h + 0.4), (0, 0.05, 0), _flat("#6b4a2e", 0.6), 0.05, parent=r, coll=coll)
    box(name + "_bd", (w, 0.2, h), (0, 0, 0), _flat("#22352b", 0.9), 0.0, parent=r, coll=coll)
    label(name + "_t", body, (0, -0.11, 0.2), h * 0.14, "#e9efe6", "hand", 0, r, coll, spacing=1.1)
    box(name + "_ledge", (w, 0.4, 0.1), (0, -0.2, -h / 2 - 0.1), _flat("#6b4a2e"), 0.02, parent=r, coll=coll)
    return r


def screen(name, lines, loc, rot=0.0, w=9.0, h=5.0, bg="#0b1020", fg="#ffffff", accent="#ff3b3b", coll=None,
           parent=None, bezel="#111111", glow=4.0, size=None, header=None, header_bg="#c62828", font="bold"):
    """Glowing screen. lines: list of str or (str, hex) tuples, stacked top->bottom."""
    r = _root(name, loc, rot, coll, parent)
    box(name + "_bz", (w + 0.4, 0.3, h + 0.4), (0, 0.12, 0), _flat(bezel, 0.35), 0.06, parent=r, coll=coll)
    plane(name + "_bg", w, h, (0, -0.04, 0), _glow(bg, 1.0), (90, 0, 0), r, coll)
    top = h / 2
    if header:
        hh = h * 0.16
        plane(name + "_hb", w, hh, (0, -0.06, top - hh / 2), _glow(header_bg, 2.5), (90, 0, 0), r, coll)
        label(name + "_ht", header, (0, -0.08, top - hh / 2), hh * 0.55, "#ffffff", font, glow, r, coll)
        top -= hh
    n = max(1, len(lines))
    sz = size or min(h * 0.6 / n, w / 9)
    step = (top + h / 2) / n
    for i, ln in enumerate(lines):
        body, col = (ln, fg) if isinstance(ln, str) else ln
        label(f"{name}_l{i}", body, (0, -0.08, top - step * (i + 0.5)), sz, col, font, glow, r, coll)
    return r


def street_screen(name, lines, loc, rot=0.0, w=12.0, h=7.0, coll=None, header="BLOX TOWN LIVE", pole=True, **kw):
    """Big LED billboard on a steel pole (or set pole=False and bolt to a wall)."""
    r = _root(name, loc, rot, coll)
    if pole:
        from . import pbr
        box(name + "_pl", (0.8, 0.8, loc[2]), (0, 0.6, -loc[2] / 2), pbr.get("steel"), 0.05, parent=r, coll=coll)
    screen(name + "_s", lines, (0, 0, 0), 0, w, h, coll=coll, parent=r, header=header, **kw)
    return r


# ------------------------------------------------------------------ devices
def phone(name, loc, rot=0.0, app="messages", title="MOM", msgs=(), buttons=(), coll=None, parent=None, s=1.0,
          case="#1c1c22", time_str="9:41", accent="#2f7bff"):
    """Hand phone, ~0.75 x 1.5 at s=1 (fits R6 hand; scale up for inserts). app: messages | choice | blank | login.
    msgs: [("them"|"me", text)], buttons: ["EXPOSE", "PROTECT"]."""
    r = _root(name, loc, rot, coll, parent)
    r.scale = (s, s, s)
    W, H = 0.76, 1.5
    box(name + "_b", (W, 0.08, H), (0, 0.03, 0), _flat(case, 0.3), 0.06, parent=r, coll=coll)
    sw, sh = W - 0.06, H - 0.08
    plane(name + "_sc", sw, sh, (0, -0.015, 0), _glow("#0d1015", 1.0), (90, 0, 0), r, coll)
    z = sh / 2
    label(name + "_tm", time_str, (-sw / 2 + 0.06, -0.02, z - 0.045), 0.05, "#ffffff", "bold", 2.0, r, coll, align="LEFT")
    plane(name + "_hd", sw, 0.16, (0, -0.018, z - 0.15), _glow("#1b1f27", 1.0), (90, 0, 0), r, coll)
    label(name + "_ti", title, (0, -0.022, z - 0.155), 0.075, "#ffffff", "bold", 2.5, r, coll)
    y = z - 0.32
    if app == "messages":
        for i, (who, body) in enumerate(msgs):
            me = who == "me"
            lines = body.count("\n") + 1
            bh = 0.085 * lines + 0.06
            bx = 0.08 if me else -0.08
            col = accent if me else "#2c313c"
            box(f"{name}_bb{i}", (sw * 0.78, 0.01, bh), (bx, -0.02, y - bh / 2), _glow(col, 1.0), 0.02, parent=r, coll=coll)
            label(f"{name}_bt{i}", body, (bx, -0.028, y - bh / 2), 0.062, "#ffffff", "bold", 2.5,
                  r, coll)
            y -= bh + 0.06
    elif app == "choice":
        for i, b in enumerate(buttons):
            col = ["#d32f2f", "#2e7d32", accent][i % 3]
            box(f"{name}_btn{i}", (sw * 0.8, 0.012, 0.2), (0, -0.02, y - 0.12 - i * 0.3), _glow(col, 1.6), 0.04,
                parent=r, coll=coll)
            label(f"{name}_bl{i}", b, (0, -0.03, y - 0.12 - i * 0.3), 0.075, "#ffffff", "bold", 1.6, r, coll)
    elif app == "login":
        label(name + "_lg", "Last login:\n" + (msgs[0] if msgs else "KITCHEN-LAPTOP"), (0, -0.022, y - 0.15), 0.07,
              "#ffffff", "bold", 2.5, r, coll)
    return r


def laptop(name, loc, rot=0.0, title="Blox Social", posts=(), coll=None, parent=None, s=1.0, user="@anon"):
    """Open laptop (base on the table at loc) with a social-feed screen."""
    r = _root(name, loc, rot, coll, parent)
    r.scale = (s, s, s)
    alu = _flat("#9aa0a8", 0.35)
    box(name + "_base", (2.6, 1.8, 0.1), (0, 0, 0.05), alu, 0.03, parent=r, coll=coll)
    box(name + "_kb", (2.3, 0.9, 0.01), (0, -0.15, 0.105), _flat("#1d1f24", 0.6), 0, parent=r, coll=coll)
    lid = empty(name + "_hinge", (0, 0.88, 0.1), parent=r, coll=coll, rot=(-15, 0, 0))
    box(name + "_lid", (2.6, 0.08, 1.7), (0, 0.04, 0.85), alu, 0.03, parent=lid, coll=coll)
    sw, sh = 2.4, 1.5
    plane(name + "_sc", sw, sh, (0, -0.005, 0.85), _glow("#11141a", 1.0), (90, 0, 0), lid, coll)
    plane(name + "_hd", sw, 0.22, (0, -0.01, 0.85 + sh / 2 - 0.11), _glow("#3b5bdb", 0.8), (90, 0, 0), lid, coll)
    label(name + "_ti", title, (0, -0.015, 0.85 + sh / 2 - 0.11), 0.13, "#ffffff", "bold", 2.5, lid, coll)
    z = 0.85 + sh / 2 - 0.27
    for i, p in enumerate(posts[:3]):
        box(f"{name}_pc{i}", (sw * 0.94, 0.01, 0.36), (0, -0.012, z - 0.19), _glow("#232836", 1.0), 0.02, parent=lid, coll=coll)
        label(f"{name}_pu{i}", user, (-sw * 0.44, -0.02, z - 0.08), 0.065, "#7ea6ff", "bold", 2.5, lid, coll, align="LEFT")
        label(f"{name}_pt{i}", p, (-sw * 0.44, -0.02, z - 0.24), 0.12, "#ffffff", "bold", 2.5, lid, coll, align="LEFT")
        z -= 0.41
    return r


def wrist_counter(name, loc, rot=0.0, seq=((0.0, "000"),), coll=None, parent=None, s=1.0, red_over=90, amber_over=40, face=True,
                  pulse=1.45):
    """Glowing 3-digit counter (inner-wrist display). seq: [(t, "047"), ...] each value shown until the next.
    face=False: digits only (caller supplies the bezel/screen, e.g. town.insert_table round watch face).
    pulse: scale pop of each NEW value on its change frame (0/None = hard switch).
    Colour: white < amber_over <= amber < red_over <= red. '???' shows glitch magenta."""
    r = _root(name, loc, rot, coll, parent)
    r.scale = (s, s, s)
    if face:
        box(name + "_pad", (1.0, 0.04, 0.46), (0, 0.02, 0), _flat("#121418", 0.3), 0.06, parent=r, coll=coll)
        plane(name + "_gl", 0.9, 0.38, (0, -0.005, 0), _glow("#0a1830", 1.0), (90, 0, 0), r, coll)
    for i, (t, val) in enumerate(seq):
        try:
            n = int(val)
            col = "#ff3b3b" if n >= red_over else ("#ffb020" if n >= amber_over else "#ffffff")
        except ValueError:
            col = "#ff3bd5"
        ob = label(f"{name}_v{i}", val, (0, -0.02, 0), 0.3, col, "bold", 6.0, r, coll)
        t_off = seq[i + 1][0] if i + 1 < len(seq) else None
        show(ob, t if i else None, t_off)
        if i and pulse:   # R3-2 r4: the change must READ - pop the new value (1.45x -> 1.0 over ~0.3 s, overshoot ease)
            f0 = F(t)
            for f, sc_ in ((f0 - 1, 1.0), (f0, pulse), (f0 + 3, 0.92), (f0 + 8, 1.0)):
                ob.scale = (sc_, sc_, sc_); ob.keyframe_insert("scale", frame=f)
            ob.scale = (1, 1, 1)
            try:
                from .core import fcurves
                for fc in fcurves(ob.animation_data.action):
                    if fc.data_path == "scale":
                        for kp in fc.keyframe_points:
                            kp.interpolation = "BEZIER"; kp.easing = "EASE_OUT"
            except Exception:
                pass
    return r


def typed(name, body, loc, t0=0.0, cps=14.0, size=0.3, color="#111111", font="ui", glow=1.0, rot=(90, 0, 0),
          parent=None, coll=None, align="LEFT", cursor=True, max_steps=60):
    """Type-on text: one font object per visible prefix (capped at max_steps), switched by visibility keys."""
    n = len(body)
    step = max(1, -(-n // max_steps))
    cuts = list(range(step, n + 1, step))
    if cuts[-1] != n:
        cuts.append(n)
    obs = []
    for i, c in enumerate(cuts):
        s = body[:c] + ("|" if cursor and c < n else "")
        ob = label(f"{name}_{i:02d}", s, loc, size, color, font, glow, parent, coll, align, rot)
        t_on = t0 + (cuts[i - 1] if i else 0) / cps
        t_off = t0 + c / cps if i + 1 < len(cuts) else None
        show(ob, t_on if F(t_on) > 1 else None, t_off)
        obs.append(ob)
    return obs


def brand_sign(name="rblx_brand", loc=(0, 0, 8), rot=0.0, coll=None, lit=True):
    """Optional RBLX ANIMATES channel sign (purple/neon). Use sparingly: wall plaque, billboard corner, phone wallpaper."""
    r = _root(name, loc, rot, coll)
    box(name + "_bd", (8.4, 0.3, 2.0), (0, 0, 0), _flat("#121018", 0.4), 0.08, parent=r, coll=coll)
    label(name + "_a", "RBLX", (-2.35, -0.2, 0), 1.1, "#b46bff", "bold", 5.0 if lit else 0, r, coll)
    label(name + "_b", "ANIMATES", (1.55, -0.2, 0), 0.8, "#26d9ff", "bold", 5.0 if lit else 0, r, coll)
    return r
