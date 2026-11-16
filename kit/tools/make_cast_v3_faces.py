"""Cast v3 face atlases (REF2 bible §3): flat ink decals, 2-4 elements, one accent colour max.
python tools/make_cast_v3_faces.py [out_dir]  -> <out_dir>/v3_<role>_eyes.png + v3_<role>_mouth.png (default assets/faces)
Same 4x4 cell layout / indices as make_faces_layered.py (rbx.acting.EYE / MOUTH), so face()/blink/talk work.
Cell coordinates are matched to the v3 bevelled cube head (cast.py): face spans u 0.1..0.9, eye line y=0.44, mouth y=0.66.
Designed for hard-swap expressions: neutral, happy, sad, shock (white-circle eyes), angry (V brows + teeth bar), smirk,
scream (mouth ~40% of face), cry (tear streams); Luna gets an anime set (big iris, 2 catchlights, lash flicks, blush hatch)."""
import os, sys, math
from PIL import Image, ImageDraw

C = 512
SS = 3
S = C * SS
INK = (17, 17, 17, 255)
WHITE = (255, 255, 255, 255)
MOUTH_IN = (40, 14, 16, 255)
TONGUE = (216, 58, 64, 255)
TEAR = (120, 200, 255, 255)
TEETH = (250, 248, 242, 255)
EYE_N = ["normal", "wide", "half", "closed", "happy", "squint", "side_l", "side_r", "terror", "worried", "angry",
         "scared", "wink", "up", "down", "cry"]
MOUTH_N = ["flat", "smile", "open_smile", "laugh", "frown", "o", "talk", "talk_wide", "grimace", "grimace_wide",
           "scream", "smirk", "wavy", "yawn", "grin", "ah"]
EY, MY = 0.44, 0.665          # eye line / mouth line (cell units from top)

# per-character face design (all original; eye sizes in cell units)
STYLES = {
    # Harry: tall oval eyes with a white catchlight, confident thick brows
    "harry": dict(ex=0.15, rx=0.045, ry=0.072, brow=0.026, brow_len=0.075, brow_dy=0.105, glint=True, mouth_w=1.0),
    # Tyler: big friendly round dot eyes, thin high brows
    "tyler": dict(ex=0.155, rx=0.048, ry=0.063, brow=0.018, brow_len=0.06, brow_dy=0.11, glint=True, mouth_w=1.1),
    "luna": dict(anime=True, ex=0.16, rx=0.081, ry=0.096, brow=0.012, brow_len=0.07, brow_dy=0.11, mouth_w=0.6),
    # Mayor: small beady eyes, heavy brows (moustache is modelled in 3D, so the mouth sits low and small)
    "mayor": dict(ex=0.15, rx=0.034, ry=0.049, brow=0.034, brow_len=0.09, brow_dy=0.085, glint=False, mouth_w=0.85,
                  my=0.72),
    # Mom: oval eyes with two lash flicks, soft brows
    "mom": dict(ex=0.15, rx=0.041, ry=0.064, brow=0.018, brow_len=0.07, brow_dy=0.1, glint=True, lash=2, mouth_w=0.95),
    # Dad: square-ish brows, slightly smaller eyes
    "dad": dict(ex=0.15, rx=0.039, ry=0.058, brow=0.032, brow_len=0.085, brow_dy=0.095, glint=True, mouth_w=1.05),
    # Grandpa: tiny eyes (glasses are 3D), bushy brows, mouth hidden-ish under the moustache
    "grandpa": dict(ex=0.15, rx=0.031, ry=0.045, brow=0.036, brow_len=0.085, brow_dy=0.085, glint=False,
                    mouth_w=0.8, my=0.725),
    "grandma": dict(ex=0.15, rx=0.036, ry=0.052, brow=0.016, brow_len=0.065, brow_dy=0.095, glint=True,
                    mouth_w=0.85, cheeks=True),
}


def P(x, y):
    return (x * S, y * S)


def W(v):
    return max(1, int(v * S))


def ell(d, cx, cy, rx, ry, **kw):
    d.ellipse([P(cx - rx, cy - ry), P(cx + rx, cy + ry)], **kw)


def arc(d, cx, cy, rx, ry, a0, a1, w, fill=INK):
    """Round-capped arc (PIL arcs have flat ends, so add dots at the ends)."""
    d.arc([P(cx - rx, cy - ry), P(cx + rx, cy + ry)], a0, a1, fill=fill, width=W(w))
    for a in (a0, a1):
        x = cx + rx * math.cos(math.radians(a)) - (w / 2) * math.cos(math.radians(a))
        y = cy + ry * math.sin(math.radians(a)) - (w / 2) * math.sin(math.radians(a))
        ell(d, x, y, w / 2, w / 2, fill=fill)


def line(d, pts, w, fill=INK):
    d.line([P(*p) for p in pts], fill=fill, width=W(w), joint="curve")
    for p in (pts[0], pts[-1]):
        ell(d, p[0], p[1], w / 2, w / 2, fill=fill)


def quad(a, b, c, n=16):
    return [((1 - t) ** 2 * a[0] + 2 * (1 - t) * t * b[0] + t * t * c[0],
             (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * b[1] + t * t * c[1]) for t in [i / n for i in range(n + 1)]]


# ------------------------------------------------------------------------------------------------ eyes
def brow(d, st, cx, side, kind):
    """side -1 = image-left eye. kind: normal | raised | worried | angry | flat."""
    L, w = st["brow_len"], st["brow"]
    y = EY - st["ry"] - st["brow_dy"] + st["ry"] * 0.5
    if kind is None:
        return
    inner, outer = cx - side * L * 0.55, cx + side * L * 0.55
    if kind == "normal":
        line(d, quad((inner, y + 0.004), (cx, y - 0.014), (outer, y + 0.006)), w)
    elif kind == "raised":
        y -= 0.03
        line(d, quad((inner, y + 0.006), (cx, y - 0.018), (outer, y + 0.01)), w)
    elif kind == "worried":
        line(d, quad((inner, y - 0.022), (cx, y - 0.01), (outer, y + 0.016)), w)
    elif kind == "angry":
        line(d, [(inner, y + 0.03), (outer, y - 0.018)], w * 1.15)
    elif kind == "flat":
        line(d, [(inner, y + 0.008), (outer, y + 0.008)], w)


def dot_eye(d, st, cx, side, look=(0, 0), sx=1.0, sy=1.0):
    rx, ry = st["rx"] * sx, st["ry"] * sy
    x, y = cx + look[0] * 0.03, EY + look[1] * 0.025
    ell(d, x, y, rx, ry, fill=INK)
    if st.get("glint"):
        ell(d, x + rx * 0.3, y - ry * 0.42, rx * 0.34, rx * 0.34, fill=WHITE)
    for k in range(st.get("lash", 0)):
        a = math.radians(-35 - k * 28)
        bx, by = x + side * rx * math.cos(a) * 0.9, y + ry * math.sin(a) * 0.9
        line(d, [(bx, by), (bx + side * 0.026, by - 0.022 + k * 0.012)], st["brow"] * 0.9)


def white_eye(d, st, cx, side, pupil=0.32, look=(0, 0)):
    """Shock eyes: white circle with ink outline + small pupil."""
    r = max(st["rx"], st["ry"]) * 1.35
    ell(d, cx, EY, r, r, fill=WHITE, outline=INK, width=W(0.016))
    ell(d, cx + look[0] * r * 0.3, EY + look[1] * r * 0.3, r * pupil, r * pupil, fill=INK)


def anime_eye(d, im, st, cx, side, kind="open", look=(0, 0)):
    rx, ry = st["rx"], st["ry"]
    lw = 0.022
    if kind == "wide":
        r = rx * 1.05
        ell(d, cx, EY, r, ry * 1.05, fill=WHITE, outline=INK, width=W(0.014))
        ell(d, cx, EY, r * 0.26, r * 0.26, fill=INK)
        return
    ell(d, cx, EY + ry * 0.04, rx, ry, fill=WHITE)
    ix, iy = cx + look[0] * rx * 0.35, EY + ry * 0.12 + look[1] * ry * 0.2
    irx, iry = rx * 0.7, ry * 0.86
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0)); dl = ImageDraw.Draw(lay)
    ell(dl, ix, iy, irx, iry, fill=(70, 12, 26, 255))                    # deep crimson iris (matches hair)
    ell(dl, ix, iy + iry * 0.25, irx * 0.82, iry * 0.6, fill=(150, 30, 52, 255))
    ell(dl, ix, iy, irx * 0.5, iry * 0.58, fill=INK)
    ell(dl, ix + irx * 0.32, iy - iry * 0.42, irx * 0.36, irx * 0.36, fill=WHITE)  # big catchlight top-right
    ell(dl, ix - irx * 0.36, iy + iry * 0.4, irx * 0.16, irx * 0.16, fill=WHITE)   # small bottom-left
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).ellipse([P(cx - rx, EY + ry * 0.04 - ry), P(cx + rx, EY + ry * 0.04 + ry)], fill=255)
    im.paste(lay, (0, 0), Image.composite(lay.getchannel("A"), Image.new("L", im.size, 0), mask))
    if kind == "half":   # smug lid: skin-coloured cut is impossible on a transparent atlas -> heavy flat lid line
        d.rectangle([P(cx - rx - 0.004, EY - ry - 0.01), P(cx + rx + 0.004, EY - ry * 0.25)], fill=(0, 0, 0, 0))
        line(d, [(cx - rx * 1.02, EY - ry * 0.25), (cx + rx * 1.02, EY - ry * 0.25)], lw * 1.2)
    else:
        arc(d, cx, EY + ry * 0.04, rx * 1.02, ry * 1.02, 195, 345, lw * 1.25)   # heavy upper lid
    # lash flicks on the outer corner
    ox = cx + side * rx * 0.95
    for k in range(3 if kind != "half" else 2):
        line(d, [(ox, EY - ry * (0.45 - k * 0.32)), (ox + side * 0.03, EY - ry * (0.75 - k * 0.3))], 0.011)
    arc(d, cx, EY + ry * 0.06, rx * 0.8, ry * 0.95, 70, 110, 0.009)   # lower lash hint


def blush(d, st):
    for sx in (-1, 1):
        cx = 0.5 + sx * (st["ex"] + 0.005)
        ell(d, cx, EY + 0.105, 0.06, 0.026, fill=(255, 138, 160, 140))
        for k in range(3):
            x = cx - 0.03 + k * 0.022
            line(d, [(x + 0.008, EY + 0.093), (x - 0.006, EY + 0.117)], 0.0065, fill=(224, 64, 90, 255))


def eye_cell(name, st):
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    A = st.get("anime")
    for side in (-1, 1):
        cx = 0.5 + side * st["ex"]
        rx, ry = st["rx"], st["ry"]
        if name in ("normal", "up", "down", "side_l", "side_r"):
            look = dict(normal=(0, 0), up=(0, -1), down=(0, 1), side_l=(-1, 0), side_r=(1, 0))[name]
            (anime_eye(d, im, st, cx, side, "open", look) if A else dot_eye(d, st, cx, side, look))
            brow(d, st, cx, side, "raised" if name == "up" else "normal")
        elif name == "wide":
            (anime_eye(d, im, st, cx, side, "wide") if A else white_eye(d, st, cx, side))
            brow(d, st, cx, side, "raised")
        elif name == "half":
            if A:
                anime_eye(d, im, st, cx, side, "half")
            else:
                dot_eye(d, st, cx, side, (0, 0.2), 1.0, 0.8)
                d.rectangle([P(cx - rx * 1.6, EY - ry * 1.4), P(cx + rx * 1.6, EY - ry * 0.15)], fill=(0, 0, 0, 0))
                line(d, [(cx - rx * 1.35, EY - ry * 0.15), (cx + rx * 1.35, EY - ry * 0.15)], st["brow"] * 0.9)
            brow(d, st, cx, side, "flat")
        elif name in ("closed", "cry"):
            w = 0.02 if not A else 0.022
            arc(d, cx, EY - (ry * 0.3 if not A else 0.0), rx * (1.25 if not A else 0.95), ry * 0.5, 20, 160, w)
            if A:
                for k in range(2):
                    line(d, [(cx + side * rx * 0.9, EY + 0.01 + k * 0.012), (cx + side * (rx + 0.022), EY - 0.008 + k * 0.02)], 0.009)
            brow(d, st, cx, side, "worried" if name == "cry" else "normal")
            if name == "cry":   # tear streams down the cheeks
                tx = cx + side * rx * 0.2
                d.rounded_rectangle([P(tx - 0.018, EY + 0.02), P(tx + 0.018, EY + 0.3)], radius=W(0.018), fill=TEAR)
                ell(d, tx, EY + 0.3, 0.026, 0.03, fill=TEAR)
        elif name == "happy":
            arc(d, cx, EY + ry * 0.35, rx * (1.3 if not A else 0.95), ry * (0.75 if not A else 0.6), 200, 340, 0.022)
            brow(d, st, cx, side, "raised")
        elif name == "squint":
            line(d, [(cx - side * rx * 1.2, EY - 0.018), (cx + side * rx * 1.2, EY), (cx - side * rx * 1.2, EY + 0.018)], 0.02)
            brow(d, st, cx, side, "angry")
        elif name == "terror":
            white_eye(d, st, cx, side, pupil=0.18)
            brow(d, st, cx, side, "worried")
        elif name == "scared":
            white_eye(d, st, cx, side, pupil=0.28, look=(0, 0.3))
            brow(d, st, cx, side, "worried")
        elif name == "worried":
            (anime_eye(d, im, st, cx, side, "open", (0, 0.3)) if A else dot_eye(d, st, cx, side, (0, 0.2), 1.0, 0.92))
            brow(d, st, cx, side, "worried")
        elif name == "angry":
            (anime_eye(d, im, st, cx, side, "half") if A else dot_eye(d, st, cx, side, (0, 0.3), 1.0, 0.85))
            brow(d, st, cx, side, "angry")
        elif name == "wink":
            if side == 1:
                arc(d, cx, EY + ry * 0.35, rx * 1.2, ry * 0.7, 200, 340, 0.02)
            else:
                (anime_eye(d, im, st, cx, side, "open") if A else dot_eye(d, st, cx, side))
            brow(d, st, cx, side, "normal")
    if A or st.get("cheeks"):
        if A:
            blush(d, st)
        else:
            for sx in (-1, 1):
                ell(d, 0.5 + sx * (st["ex"] + 0.03), EY + 0.11, 0.045, 0.022, fill=(240, 120, 120, 90))
    return im


# ------------------------------------------------------------------------------------------------ mouths
def mouth_cell(name, st):
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    k = st.get("mouth_w", 1.0)
    my = st.get("my", MY)
    w = 0.02
    hw = 0.105 * k                     # half width of a normal mouth
    cx = 0.5
    if name == "flat":
        line(d, [(cx - hw * 0.55, my), (cx + hw * 0.55, my)], w)
    elif name == "smile":
        line(d, quad((cx - hw, my - 0.012), (cx, my + 0.05), (cx + hw, my - 0.012)), w)
    elif name == "smirk":
        line(d, quad((cx - hw * 0.7, my + 0.01), (cx + hw * 0.1, my + 0.03), (cx + hw * 0.95, my - 0.03)), w)
    elif name == "frown":
        line(d, quad((cx - hw * 0.8, my + 0.025), (cx, my - 0.03), (cx + hw * 0.8, my + 0.025)), w)
    elif name == "wavy":
        pts = [(cx - hw * 0.8 + i * hw * 1.6 / 20, my + 0.01 * math.sin(i / 20 * math.pi * 3)) for i in range(21)]
        line(d, pts, w * 0.9)
    elif name in ("open_smile", "laugh", "grin"):
        big = {"open_smile": 1.0, "laugh": 1.3, "grin": 1.25}[name]
        top = my - 0.012
        ww, hh = hw * big, (0.075 if name == "open_smile" else 0.105) * big ** 0.5
        if name == "grin":
            hh = 0.06
        pts = [(cx - ww, top)] + [(cx + ww * math.cos(math.radians(a)), top + hh * math.sin(math.radians(a)))
                                  for a in range(0, 181, 6)][::-1] + [(cx + ww, top)]
        pts = [(cx - ww, top)] + [(cx - ww * math.cos(math.radians(a)), top + hh * math.sin(math.radians(a))) for a in range(0, 181, 6)]
        d.polygon([P(*p) for p in pts], fill=MOUTH_IN)
        if name == "grin":
            d.polygon([P(*p) for p in pts if p[1] <= top + hh * 0.45] + [P(cx + ww * 0.82, top + hh * 0.45), P(cx - ww * 0.82, top + hh * 0.45)], fill=TEETH)
        else:
            tg = Image.new("RGBA", im.size, (0, 0, 0, 0)); dt = ImageDraw.Draw(tg)
            ell(dt, cx, top + hh * 0.95, ww * 0.55, hh * 0.45, fill=TONGUE)
            msk = Image.new("L", im.size, 0); ImageDraw.Draw(msk).polygon([P(*p) for p in pts], fill=255)
            im.paste(tg, (0, 0), Image.composite(tg.getchannel("A"), Image.new("L", im.size, 0), msk))
        d.line([P(*p) for p in pts + [pts[0]]], fill=INK, width=W(w * 0.85), joint="curve")
    elif name in ("o", "talk", "talk_wide", "yawn"):
        rx, ry = dict(o=(0.03, 0.036), talk=(0.045 * k, 0.026), talk_wide=(0.06 * k, 0.042), yawn=(0.045, 0.07))[name]
        ell(d, cx, my + 0.005, rx, ry, fill=MOUTH_IN, outline=INK, width=W(w * 0.85))
        if name in ("talk_wide", "yawn"):
            tg = Image.new("RGBA", im.size, (0, 0, 0, 0)); ell(ImageDraw.Draw(tg), cx, my + ry * 0.75, rx * 0.6, ry * 0.4, fill=TONGUE)
            msk = Image.new("L", im.size, 0); ImageDraw.Draw(msk).ellipse([P(cx - rx * 0.9, my - ry * 0.9), P(cx + rx * 0.9, my + ry * 0.95)], fill=255)
            im.paste(tg, (0, 0), Image.composite(tg.getchannel("A"), Image.new("L", im.size, 0), msk))
    elif name in ("grimace", "grimace_wide"):
        ww = hw * (1.0 if name == "grimace" else 1.3); hh = 0.05 if name == "grimace" else 0.07
        box = [P(cx - ww, my - hh / 2), P(cx + ww, my + hh / 2)]
        d.rounded_rectangle(box, radius=W(0.02), fill=MOUTH_IN)
        d.rounded_rectangle([P(cx - ww, my - hh / 2), P(cx + ww, my - hh / 2 + hh * 0.45)], radius=W(0.015), fill=TEETH)
        d.rounded_rectangle([P(cx - ww, my + hh / 2 - hh * 0.32), P(cx + ww, my + hh / 2)], radius=W(0.015), fill=TEETH)
        for i in range(1, 4):
            x = cx - ww + i * ww / 2
            d.line([P(x, my - hh / 2), P(x, my + hh / 2)], fill=INK, width=W(0.007))
        d.rounded_rectangle(box, radius=W(0.02), outline=INK, width=W(w * 0.85))
    elif name == "scream":     # ~40% of the face width (face = 0.8 cell)
        rx, ry = 0.16, 0.12
        cy = my + 0.04
        ell(d, cx, cy, rx, ry, fill=MOUTH_IN, outline=INK, width=W(w))
        tg = Image.new("RGBA", im.size, (0, 0, 0, 0)); ell(ImageDraw.Draw(tg), cx, cy + ry * 0.78, rx * 0.62, ry * 0.42, fill=TONGUE)
        msk = Image.new("L", im.size, 0); ImageDraw.Draw(msk).ellipse([P(cx - rx * 0.95, cy - ry * 0.95), P(cx + rx * 0.95, cy + ry * 0.95)], fill=255)
        im.paste(tg, (0, 0), Image.composite(tg.getchannel("A"), Image.new("L", im.size, 0), msk))
        d.chord([P(cx - rx * 0.86, cy - ry * 0.98), P(cx + rx * 0.86, cy - ry * 0.3)], 180, 360, fill=TEETH)
        ell(d, cx, cy, rx, ry, outline=INK, width=W(w))
    elif name == "ah":          # crying wail: wobbly open frown
        top = my + 0.005
        pts = [(cx - hw * 0.9, top + 0.05)] + [(cx - hw * 0.9 * math.cos(math.radians(a)), top + 0.05 - 0.06 * math.sin(math.radians(a)))
                                            for a in range(0, 181, 10)]
        pts += [(cx + hw * 0.6, top + 0.06), (cx - hw * 0.6, top + 0.06)]
        d.polygon([P(*p) for p in pts], fill=MOUTH_IN)
        d.line([P(*p) for p in pts + [pts[0]]], fill=INK, width=W(w * 0.85), joint="curve")
    return im


def atlas(cells):
    out = Image.new("RGBA", (C * 4, C * 4), (0, 0, 0, 0))
    for i, im in enumerate(cells):
        out.paste(im.resize((C, C), Image.LANCZOS), ((i % 4) * C, (i // 4) * C))
    return out


def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    for role, st in STYLES.items():
        atlas([eye_cell(n, st) for n in EYE_N]).save(os.path.join(out_dir, f"v3_{role}_eyes.png"))
        atlas([mouth_cell(n, st) for n in MOUTH_N]).save(os.path.join(out_dir, f"v3_{role}_mouth.png"))
        print("wrote", role)


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "..", "assets", "faces"))
