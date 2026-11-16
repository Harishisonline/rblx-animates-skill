"""Luna's custom anime face atlases (same 4x4 cell layout + indices as make_faces_layered.py, so face()/blink/talk work).
python tools/make_luna_face.py [out_dir]   -> <out_dir>/luna_eyes.png, luna_mouth.png  (default assets/faces)
Original design: big red slit-pupil eyes with winged lash line, thin brows, three-stroke blush, tiny pout with fangs."""
import os, sys
from PIL import Image, ImageDraw

C = 512           # cell size in the final atlas
SS = 3            # supersampling
S = C * SS
SKIN = (242, 208, 180, 255)
INK = (28, 16, 22, 255)
IRIS = (214, 22, 40, 255)
IRIS_D = (120, 8, 22, 255)
BLUSH = (255, 120, 140, 255)
MOUTH_IN = (110, 20, 34, 255)
TONGUE = (240, 110, 130, 255)
WHITE = (255, 255, 255, 255)
EX, EY = 0.205, 0.40          # eye centres (cell units, y from top)
EW, EH = 0.125, 0.135         # eye half sizes


def P(x, y):
    return (x * S, y * S)


def ell(d, cx, cy, rx, ry, **kw):
    d.ellipse([P(cx - rx, cy - ry), P(cx + rx, cy + ry)], **kw)


def eye(im, d, cx, side, kind="open", look=(0, 0), wide=False, brow=0, half=False):
    """side: -1 = left of the image, +1 = right. Outer corner is on the 'side' direction."""
    rx, ry = (EW * 1.08, EH * 1.12) if wide else (EW, EH)
    lw = int(0.018 * S)
    if kind in ("closed", "happy"):
        # closed: lash curve down (U) ; happy: arc up (n)
        box = [P(cx - rx, EY - ry * 0.7), P(cx + rx, EY + ry * 0.7)]
        if kind == "closed":
            d.arc(box, 10, 170, fill=INK, width=lw)
            d.line([P(cx + side * rx * 0.95, EY + 0.0), P(cx + side * (rx + 0.04), EY - 0.03)], fill=INK, width=lw)
        else:
            d.arc(box, 190, 350, fill=INK, width=int(lw * 1.2))
    else:
        ell(d, cx, EY, rx, ry, fill=WHITE)
        lay = Image.new("RGBA", im.size, (0, 0, 0, 0)); d0 = d; d = ImageDraw.Draw(lay)
        ir = (rx * (0.62 if wide else 0.74), ry * (0.78 if wide else 0.9))
        ix, iy = cx + look[0] * rx * 0.32, EY + look[1] * ry * 0.25 + ry * 0.06
        ell(d, ix, iy, ir[0], ir[1], fill=IRIS_D)
        ell(d, ix, iy + ir[1] * 0.08, ir[0] * 0.86, ir[1] * 0.86, fill=IRIS)
        ell(d, ix, iy, ir[0] * 0.2, ir[1] * 0.78, fill=INK)                      # vertical slit pupil
        ell(d, ix - ir[0] * 0.38, iy - ir[1] * 0.42, ir[0] * 0.2, ir[1] * 0.2, fill=WHITE)   # highlights
        ell(d, ix + ir[0] * 0.3, iy + ir[1] * 0.38, ir[0] * 0.11, ir[1] * 0.11, fill=WHITE)
        mask = Image.new("L", im.size, 0); ImageDraw.Draw(mask).ellipse([P(cx - rx, EY - ry), P(cx + rx, EY + ry)], fill=255)
        im.paste(lay, (0, 0), Image.composite(lay.getchannel("A"), Image.new("L", im.size, 0), mask))
        d = d0
        if half:
            d.rectangle([P(cx - rx - 0.01, EY - ry - 0.02), P(cx + rx + 0.01, EY - ry * 0.1)], fill=SKIN)
        # outline + thick upper lash line with outer wing spike
        if half:
            d.arc([P(cx - rx, EY - ry), P(cx + rx, EY + ry)], 0, 180, fill=INK, width=int(lw * 0.55))
        else:
            ell(d, cx, EY, rx, ry, outline=INK, width=int(lw * 0.55))
        top = EY - (ry * 0.1 if half else ry)
        d.arc([P(cx - rx, EY - ry), P(cx + rx, EY + ry)], 195, 345, fill=INK, width=int(lw * 1.7)) if not half else \
            d.line([P(cx - rx, top), P(cx + rx, top)], fill=INK, width=int(lw * 1.7))
        ox = cx + side * rx * 0.92
        wy = top if half else EY - ry * 0.5
        d.polygon([P(ox - side * 0.01, wy - 0.012), P(ox + side * 0.07, wy - 0.03), P(ox + side * 0.01, wy + 0.03)], fill=INK)
        d.line([P(cx + side * rx * 0.85, EY + ry * 0.55), P(cx + side * (rx + 0.025), EY + ry * 0.75)], fill=INK, width=int(lw * 0.6))
    # brow: thin, slightly arched; brow>0 raised/worried (inner up), brow<0 angry (inner down)
    by = EY - EH - 0.075 - (0.02 if wide else 0)
    inner, outer = cx - side * rx * 0.75, cx + side * rx * 0.95
    d.line([P(inner, by - brow * 0.0015), P(cx, by - 0.012), P(outer, by + 0.008 + brow * 0.0008)], fill=INK,
           width=int(0.011 * S), joint="curve")


def blush(d, heavy=False):
    for cx in (0.5 - EX - 0.02, 0.5 + EX + 0.02):
        y = EY + EH + 0.07
        if heavy:
            ell(d, cx, y, 0.12, 0.058, fill=(255, 95, 130, 255))
        for k in range(3):
            x = cx - 0.05 + k * 0.05
            d.line([P(x - 0.016, y + 0.016), P(x + 0.016, y - 0.016)], fill=BLUSH, width=int(0.02 * S))


EYES = [  # (kind, look, wide, brow, half, heavy_blush, tears)
    ("open", (0, 0), False, 0, False, False, False),     # 0 normal
    ("open", (0, 0), True, 22, False, False, False),     # 1 wide (surprised)
    ("open", (0, 0.3), False, 0, True, False, False),    # 2 half
    ("closed", (0, 0), False, 0, False, False, False),   # 3 closed (blink)
    ("happy", (0, 0), False, 6, False, False, False),    # 4 happy arcs
    ("open", (0.6, 0), False, -8, True, False, False),   # 5 squint
    ("open", (-1, 0.4), False, 14, False, True, False),  # 6 side_l (SHY: heavy blush)
    ("open", (1, 0.4), False, 14, False, True, False),   # 7 side_r
    ("open", (0, 0), True, 30, False, False, False),     # 8 terror
    ("open", (0, 0), False, 28, False, False, False),    # 9 worried
    ("open", (0, 0), False, -24, False, False, False),   # 10 angry
    ("open", (0, 0), True, 30, False, False, False),     # 11 scared
    ("wink", (0, 0), False, 0, False, False, False),     # 12 wink
    ("open", (0, -1), False, 10, False, False, False),   # 13 up
    ("open", (0, 1), False, 0, False, False, False),     # 14 down
    ("open", (0, 0.2), False, 28, False, True, True),    # 15 cry
]


def draw_eye_cell(spec):
    kind, look, wide, brow, half, heavy, tears = spec
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    blush(d, heavy)
    for cx, side in ((0.5 - EX, -1), (0.5 + EX, 1)):
        k = kind
        if kind == "wink":
            k = "open" if side < 0 else "closed"
        eye(im, d, cx, side, k, look, wide, brow, half)
        if tears:
            d.line([P(cx, EY + EH), P(cx, EY + EH + 0.2)], fill=(120, 190, 255, 230), width=int(0.02 * S))
    return im.resize((C, C), Image.LANCZOS)


MY = 0.635   # mouth centre
MS = 1.7     # mouth scale


def PM(x, y):
    return P(0.5 + (x - 0.5) * MS, MY + (y - MY) * MS)


def ellm(d, cx, cy, rx, ry, **kw):
    d.ellipse([PM(cx - rx, cy - ry), PM(cx + rx, cy + ry)], **kw)


def fangs(d, x0, x1, y, h=0.035):
    for x in (x0, x1):
        d.polygon([PM(x - 0.014, y), PM(x + 0.014, y), PM(x, y + h)], fill=WHITE, outline=INK)


def draw_mouth_cell(kind):
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    lw = int(0.016 * S)
    if kind in ("flat", "wavy"):      # tiny pout: little 'w' line + two fangs
        a = 0.03 if kind == "flat" else 0.022
        pts = [PM(0.5 - 0.06, MY + 0.008), PM(0.5 - a, MY - 0.006), PM(0.5, MY + 0.006), PM(0.5 + a, MY - 0.006), PM(0.5 + 0.06, MY + 0.008)]
        d.line(pts, fill=INK, width=lw, joint="curve")
        fangs(d, 0.5 - 0.035, 0.5 + 0.035, MY - 0.002, 0.026)
    elif kind in ("smile", "smirk", "grin"):
        w = {"smile": 0.06, "smirk": 0.05, "grin": 0.085}[kind]
        off = 0.02 if kind == "smirk" else 0
        d.arc([PM(0.5 - w + off, MY - 0.045), PM(0.5 + w + off, MY + 0.025)], 20, 160, fill=INK, width=lw)
        fangs(d, 0.5 - w * 0.55 + off, 0.5 + w * 0.55 + off, MY + 0.016, 0.024)
    elif kind == "frown":
        d.arc([PM(0.45, MY), PM(0.55, MY + 0.05)], 200, 340, fill=INK, width=lw)
    else:   # open shapes
        w, h, top_flat = {"open_smile": (0.07, 0.06, True), "laugh": (0.09, 0.08, True), "o": (0.032, 0.04, False),
                          "talk": (0.045, 0.035, True), "talk_wide": (0.06, 0.055, True), "grimace": (0.08, 0.03, False),
                          "grimace_wide": (0.1, 0.05, False), "scream": (0.06, 0.09, False), "yawn": (0.05, 0.08, False),
                          "ah": (0.05, 0.06, False)}[kind]
        if top_flat:   # D-shape (open smile), fangs hanging from the top edge
            d.chord([PM(0.5 - w, MY - h), PM(0.5 + w, MY + h)], 0, 180, fill=MOUTH_IN, outline=INK, width=lw)
            ellm(d, 0.5, MY + h * 0.6, w * 0.55, h * 0.35, fill=TONGUE)
            d.chord([PM(0.5 - w, MY - h), PM(0.5 + w, MY + h)], 0, 180, outline=INK, width=lw)
            fangs(d, 0.5 - w * 0.55, 0.5 + w * 0.55, MY + 0.002, 0.028)
        else:
            ellm(d, 0.5, MY + h * 0.3, w, h, fill=MOUTH_IN, outline=INK, width=lw)
            if kind in ("grimace", "grimace_wide"):
                d.rectangle([PM(0.5 - w * 0.8, MY + h * 0.3 - h * 0.45), PM(0.5 + w * 0.8, MY + h * 0.3 + h * 0.1)], fill=WHITE)
            else:
                fangs(d, 0.5 - w * 0.5, 0.5 + w * 0.5, MY + h * 0.3 - h * 0.92, 0.022)
    return im.resize((C, C), Image.LANCZOS)


MOUTHS = ["flat", "smile", "open_smile", "laugh", "frown", "o", "talk", "talk_wide",
          "grimace", "grimace_wide", "scream", "smirk", "wavy", "yawn", "grin", "ah"]


def atlas(cells):
    a = Image.new("RGBA", (C * 4, C * 4), (0, 0, 0, 0))
    for i, c in enumerate(cells):
        a.paste(c, ((i % 4) * C, (i // 4) * C))
    return a


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "faces")
    os.makedirs(out, exist_ok=True)
    atlas([draw_eye_cell(s) for s in EYES]).save(os.path.join(out, "luna_eyes.png"))
    atlas([draw_mouth_cell(m) for m in MOUTHS]).save(os.path.join(out, "luna_mouth.png"))
    print("wrote", out)
