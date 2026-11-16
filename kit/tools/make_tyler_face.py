"""Tyler's face: simple friendly dark oval 'dot' eyes (same 16 eye cells/indices as every face) + the Harry mouth set
(copied as tyler_mouth.png). python tools/make_tyler_face.py [out_dir]"""
import os, sys, shutil
from PIL import Image, ImageDraw
C, SS = 512, 3
S = C * SS
INK = (34, 26, 30, 255)
EX, EY = 0.17, 0.42


def P(x, y):
    return (x * S, y * S)


def cell(kind, look=(0, 0), r=(0.032, 0.05), brow=None, sweat=False, tears=False):
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for cx, side in ((0.5 - EX, -1), (0.5 + EX, 1)):
        k = ("dot" if side < 0 else "closed") if kind == "wink" else kind
        x, y = cx + look[0] * 0.015, EY + look[1] * 0.015
        if k == "dot":
            d.ellipse([P(x - r[0], y - r[1]), P(x + r[0], y + r[1])], fill=INK)
            d.ellipse([P(x - r[0] * 0.45, y - r[1] * 0.55), P(x - r[0] * 0.05, y - r[1] * 0.15)], fill=(255, 255, 255, 230))
        elif k == "half":
            d.chord([P(x - r[0], y - r[1]), P(x + r[0], y + r[1])], 0, 180, fill=INK)
            d.line([P(x - r[0] - 0.01, y), P(x + r[0] + 0.01, y)], fill=INK, width=int(0.014 * S))
        elif k == "closed":
            d.arc([P(x - 0.04, y - 0.02), P(x + 0.04, y + 0.03)], 15, 165, fill=INK, width=int(0.014 * S))
        elif k == "happy":
            d.arc([P(x - 0.04, y - 0.015), P(x + 0.04, y + 0.05)], 195, 345, fill=INK, width=int(0.016 * S))
        elif k == "line":
            d.line([P(x - 0.035, y), P(x + 0.035, y)], fill=INK, width=int(0.014 * S))
        if brow is not None:
            by = EY - 0.09
            d.line([P(cx - side * 0.03, by - brow * 0.0012), P(cx + side * 0.04, by + brow * 0.0005)], fill=INK, width=int(0.012 * S))
        if tears:
            d.line([P(cx, EY + 0.06), P(cx, EY + 0.2)], fill=(120, 190, 255, 230), width=int(0.018 * S))
    if sweat:
        d.polygon([P(0.78, 0.26), P(0.75, 0.33), P(0.78, 0.36), P(0.81, 0.33)], fill=(140, 205, 255, 240), outline=(60, 120, 200, 255))
    return im.resize((C, C), Image.LANCZOS)


EYES = [cell("dot"), cell("dot", r=(0.042, 0.066), brow=24), cell("half"), cell("closed"), cell("happy"), cell("line"),
        cell("dot", (-1.4, 0), brow=-4), cell("dot", (1.4, 0), brow=-4), cell("dot", r=(0.024, 0.04), brow=30, sweat=True),
        cell("dot", brow=26, sweat=True), cell("dot", brow=-24), cell("dot", r=(0.024, 0.04), brow=30, sweat=True),
        cell("wink"), cell("dot", (0, -1.5)), cell("dot", (0, 1.5)), cell("dot", brow=26, tears=True)]

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "faces")
    a = Image.new("RGBA", (C * 4, C * 4), (0, 0, 0, 0))
    for i, c in enumerate(EYES):
        a.paste(c, ((i % 4) * C, (i // 4) * C))
    a.save(os.path.join(out, "tyler_eyes.png"))
    shutil.copy(os.path.join(out, "harry_mouth.png"), os.path.join(out, "tyler_mouth.png"))
    print("wrote", out)
