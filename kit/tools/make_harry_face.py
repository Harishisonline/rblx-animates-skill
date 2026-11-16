"""Harry's face atlases (same 4x4 cell layout + indices as make_faces_layered.py: face()/blink/talk work).
python tools/make_harry_face.py [out_dir] -> harry_eyes.png, harry_mouth.png (default assets/faces)
Original design: classic outlined white eyes with small pupils + glare, thick short brows; default look is the half-lidded
smug 'half' cell + 'smirk' mouth; side cells are deadpan half-lid side glances; wide = shocked white eyes."""
import os, sys
from PIL import Image, ImageDraw

C, SS = 512, 3
S = C * SS
SKIN = (233, 185, 143, 255)
INK = (18, 14, 14, 255)
WHITE = (255, 255, 255, 255)
MOUTH_IN = (30, 12, 14, 255)
TONGUE = (226, 96, 110, 255)
EX, EY, EW, EH = 0.2, 0.42, 0.1, 0.125
BW, BL, STUBBLE = 0.02, 0.07, False


def P(x, y):
    return (x * S, y * S)


def ell(d, cx, cy, rx, ry, **kw):
    d.ellipse([P(cx - rx, cy - ry), P(cx + rx, cy + ry)], **kw)


def eye(im, cx, side, kind, look=(0, 0), lid=0.0, wide=False, brow=0):
    d = ImageDraw.Draw(im)
    rx, ry = (EW * 1.25, EH * 1.25) if wide else (EW, EH)
    ow = int((0.022 if wide else 0.018) * S)
    if kind == "closed":
        d.arc([P(cx - rx, EY - ry * 0.5), P(cx + rx, EY + ry * 0.6)], 15, 165, fill=INK, width=ow)
    elif kind == "happy":
        d.arc([P(cx - rx, EY - ry * 0.4), P(cx + rx, EY + ry * 0.9)], 195, 345, fill=INK, width=ow)
    else:
        lay = Image.new("RGBA", im.size, (0, 0, 0, 0)); dl = ImageDraw.Draw(lay)
        ell(dl, cx, EY, rx, ry, fill=WHITE)
        pr = 0.026 if wide else 0.034
        px, py = cx + look[0] * rx * 0.5, EY + look[1] * ry * 0.45 + (0.01 if lid else 0)
        ell(dl, px, py, pr, pr * 1.15, fill=INK)
        ell(dl, px - pr * 0.35, py - pr * 0.4, pr * 0.32, pr * 0.32, fill=WHITE)
        if lid:   # upper lid: skin over the top part, flat lid line
            ly = EY - ry + 2 * ry * lid
            dl.rectangle([P(cx - rx - 0.02, EY - ry - 0.03), P(cx + rx + 0.02, ly)], fill=SKIN)
        mask = Image.new("L", im.size, 0); ImageDraw.Draw(mask).ellipse([P(cx - rx, EY - ry), P(cx + rx, EY + ry)], fill=255)
        im.paste(lay, (0, 0), Image.composite(lay.getchannel("A"), Image.new("L", im.size, 0), mask))
        d = ImageDraw.Draw(im)
        if lid:
            ly = EY - ry + 2 * ry * lid
            d.arc([P(cx - rx, EY - ry), P(cx + rx, EY + ry)], 0, 180, fill=INK, width=ow)
            import math
            half = rx * math.sqrt(max(0.0, 1 - ((ly - EY) / ry) ** 2))
            d.line([P(cx - half - 0.006, ly), P(cx + half + 0.006, ly)], fill=INK, width=int(ow * 1.4))
        else:
            ell(d, cx, EY, rx, ry, outline=INK, width=ow)
    by = EY - EH - 0.06 - (0.03 if wide else 0)
    inner, outer = cx - side * BL, cx + side * (BL + 0.01)
    d.line([P(inner, by - brow * 0.0016), P(outer, by + brow * 0.0006)], fill=INK, width=int(BW * S))


EYES = [  # kind, look, lid, wide, brow
    ("open", (0, 0), 0.0, False, 0),       # 0 normal
    ("open", (0, 0), 0.0, True, 22),       # 1 wide (shocked)
    ("open", (0.2, 0.2), 0.42, False, -6), # 2 half (smug)
    ("closed", (0, 0), 0, False, 0),       # 3 closed
    ("happy", (0, 0), 0, False, 6),        # 4 happy
    ("open", (0.3, 0.2), 0.5, False, -14), # 5 squint
    ("open", (-1, 0.3), 0.38, False, 4),   # 6 side_l (deadpan)
    ("open", (1, 0.3), 0.38, False, 4),    # 7 side_r (deadpan)
    ("open", (0, 0), 0.0, True, 30),       # 8 terror
    ("open", (0, 0.1), 0.15, False, 26),   # 9 worried
    ("open", (0, 0.1), 0.3, False, -24),   # 10 angry
    ("open", (0, 0), 0.0, True, 30),       # 11 scared
    ("wink", (0, 0), 0.0, False, 0),       # 12 wink
    ("open", (0, -1), 0.0, False, 10),     # 13 up
    ("open", (0, 1), 0.25, False, 0),      # 14 down
    ("open", (0, 0.3), 0.2, False, 26),    # 15 cry
]


def eye_cell(spec):
    kind, look, lid, wide, brow = spec
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    for cx, side in ((0.5 - EX, -1), (0.5 + EX, 1)):
        k = ("open" if side < 0 else "closed") if kind == "wink" else kind
        eye(im, cx, side, k, look, lid, wide, brow)
    return im.resize((C, C), Image.LANCZOS)


MY = 0.655
MS = 1.8


def PM(x, y):
    return P(0.5 + (x - 0.5) * MS, MY + (y - MY) * MS)


def ellm(d, cx, cy, rx, ry, **kw):
    d.ellipse([PM(cx - rx, cy - ry), PM(cx + rx, cy + ry)], **kw)


def mouth_cell(kind):
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    lw = int(0.02 * S)
    if STUBBLE:   # short stubble shadow around the mouth / chin
        import random
        rnd = random.Random(5)
        for _ in range(900):
            x, y = rnd.uniform(0.28, 0.72), rnd.uniform(0.6, 0.9)
            if ((x - 0.5) / 0.22) ** 2 + ((y - 0.74) / 0.16) ** 2 < 1 and not (abs(x - 0.5) < 0.11 and abs(y - MY) < 0.06):
                d.ellipse([P(x - 0.003, y - 0.003), P(x + 0.003, y + 0.003)], fill=(60, 40, 30, 150))
    if kind == "flat":
        d.line([PM(0.46, MY), PM(0.54, MY)], fill=INK, width=lw)
    elif kind in ("smile", "smirk", "grin"):
        w = {"smile": 0.06, "smirk": 0.05, "grin": 0.08}[kind]
        if kind == "smirk":
            d.arc([PM(0.47, MY - 0.06), PM(0.58, MY + 0.02)], 25, 120, fill=INK, width=lw)
        elif kind == "grin":
            d.chord([PM(0.5 - w, MY - 0.04), PM(0.5 + w, MY + 0.05)], 0, 180, fill=MOUTH_IN, outline=INK, width=lw)
            d.rectangle([PM(0.5 - w * 0.8, MY + 0.0), PM(0.5 + w * 0.8, MY + 0.016)], fill=WHITE)
        else:
            d.arc([PM(0.5 - w, MY - 0.05), PM(0.5 + w, MY + 0.03)], 25, 155, fill=INK, width=lw)
    elif kind == "frown":
        d.arc([PM(0.45, MY), PM(0.55, MY + 0.05)], 205, 335, fill=INK, width=lw)
    elif kind == "wavy":
        d.line([PM(0.45, MY), PM(0.475, MY - 0.01), PM(0.5, MY), PM(0.525, MY - 0.01), PM(0.55, MY)], fill=INK, width=lw, joint="curve")
    else:
        w, h, teeth, tongue = {"open_smile": (0.06, 0.045, True, True), "laugh": (0.075, 0.06, True, True),
                               "o": (0.025, 0.03, False, False), "talk": (0.035, 0.03, True, False),
                               "talk_wide": (0.05, 0.045, True, True), "grimace": (0.06, 0.035, True, False),
                               "grimace_wide": (0.08, 0.05, True, False), "scream": (0.05, 0.075, True, True),
                               "yawn": (0.04, 0.07, False, True), "ah": (0.04, 0.05, True, True)}[kind]
        lay = Image.new("RGBA", im.size, (0, 0, 0, 0)); dl = ImageDraw.Draw(lay)
        if kind in ("open_smile", "laugh"):
            dl.chord([PM(0.5 - w, MY - h), PM(0.5 + w, MY + h)], 0, 180, fill=MOUTH_IN)
        else:
            ellm(dl, 0.5, MY, w, h, fill=MOUTH_IN)
        if tongue:
            ellm(dl, 0.5, MY + h * 0.75, w * 0.6, h * 0.4, fill=TONGUE)
        if teeth:
            top = MY if kind in ("open_smile", "laugh") else MY - h
            dl.rectangle([PM(0.5 - w, top), PM(0.5 + w, top + h * 0.32)], fill=WHITE)
        mask = Image.new("L", im.size, 0); md = ImageDraw.Draw(mask)
        if kind in ("open_smile", "laugh"):
            md.chord([PM(0.5 - w, MY - h), PM(0.5 + w, MY + h)], 0, 180, fill=255)
        else:
            md.ellipse([PM(0.5 - w, MY - h), PM(0.5 + w, MY + h)], fill=255)
        im.paste(lay, (0, 0), Image.composite(lay.getchannel("A"), Image.new("L", im.size, 0), mask))
        if kind in ("open_smile", "laugh"):
            d.chord([PM(0.5 - w, MY - h), PM(0.5 + w, MY + h)], 0, 180, outline=INK, width=int(lw * 0.7))
        else:
            ellm(d, 0.5, MY, w, h, outline=INK, width=int(lw * 0.7))
    return im.resize((C, C), Image.LANCZOS)


MOUTHS = ["flat", "smile", "open_smile", "laugh", "frown", "o", "talk", "talk_wide",
          "grimace", "grimace_wide", "scream", "smirk", "wavy", "yawn", "grin", "ah"]


def atlas(cells):
    a = Image.new("RGBA", (C * 4, C * 4), (0, 0, 0, 0))
    for i, c in enumerate(cells):
        a.paste(c, ((i % 4) * C, (i // 4) * C))
    return a


if __name__ == "__main__":
    style = "harry"
    if "--dad" in sys.argv:      # Dad (Rick): smaller eyes, heavy brows, stubble, Mom's skin tone
        sys.argv.remove("--dad"); style = "dad"
        SKIN = (196, 138, 92, 255); EW, EH = 0.08, 0.095; BW, BL, STUBBLE = 0.034, 0.085, True
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "faces")
    atlas([eye_cell(s) for s in EYES]).save(os.path.join(out, f"{style}_eyes.png"))
    atlas([mouth_cell(m) for m in MOUTHS]).save(os.path.join(out, f"{style}_mouth.png"))
    print("wrote", out)
