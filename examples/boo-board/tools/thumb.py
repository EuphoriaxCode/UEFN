"""YouTube Shorts thumbnail (1080x1920) from a portrait editor render.

    py -3.14 thumb.py            -> BooBoard_Release/BooBoard_Shorts_Thumbnail.png (+ .jpg)

Keeps everything important in the top ~75%: the Shorts player covers the bottom with the title and buttons.
"""
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from art import FONTS
from bats import bat_shape

RAW = os.path.join(os.environ["TEMP"], "bb_promo2_raw")
OUT = r"C:\Aeon.Bonjé\Euphoriax\BooBoard_Release"
LOGO = r"C:\Aeon.Bonjé\Euphoriax\Logos\wit.png"
W, H = 1080, 1920
ORANGE = (255, 138, 36)
INK = (22, 8, 30)

SHOT, FRAME = "vclose_D", 52              # Blood Moon board: Liked / Saved / Following all lit, ghost on the right
ZOOM, FOCUS = 1.04, (0.5, 0.55)            # slight push in on the board (focus = board centre in the frame)
SHIFT = 280                                # move the picture down; the sky is extended above it for the headline
LINES = ["EVERY MAP", "NEEDS THIS"]
BADGE = "FREE"


def font(name, size):
    return ImageFont.truetype(os.path.join(FONTS, name), size)


def background():
    im = Image.open(os.path.join(RAW, SHOT, f"f_{FRAME:04d}.png")).convert("RGB")
    w, h = im.size
    cw = round(h * 9 / 16)
    im = im.crop(((w - cw) // 2, 0, (w - cw) // 2 + cw, h))
    zw, zh = im.width / ZOOM, im.height / ZOOM
    x0 = min(max(FOCUS[0] * im.width - zw / 2, 0), im.width - zw)
    y0 = min(max(FOCUS[1] * im.height - zh / 2, 0), im.height - zh)
    im = im.resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + zw, y0 + zh))
    if SHIFT:
        sky = im.crop((0, 0, W, 240)).resize((W, SHIFT + 240), Image.BICUBIC)
        moved = Image.new("RGB", (W, H))
        moved.paste(im.crop((0, 0, W, H - SHIFT)), (0, SHIFT))
        mask = Image.fromarray(np.tile(np.clip((np.arange(SHIFT + 240) - SHIFT) / 240, 0, 1)[:, None] * 255,
                                       (1, W)).astype(np.uint8))
        moved.paste(sky, (0, 0), Image.eval(mask, lambda v: 255 - v))     # stretched sky fades into the real one
        im = moved
    im = ImageEnhance.Contrast(im).enhance(1.08)
    im = ImageEnhance.Color(im).enhance(1.15)
    return im.filter(ImageFilter.UnsharpMask(radius=2, percent=70, threshold=2)).convert("RGBA")


def gradient(top_alpha=0.78, size=900):
    a = (np.clip(1 - np.arange(size) / size, 0, 1) ** 1.4 * top_alpha * 255).astype(np.uint8)
    arr = np.zeros((size, W, 4), np.uint8)
    arr[..., :3] = (10, 4, 20)
    arr[..., 3] = a[:, None]
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    lay.alpha_composite(Image.fromarray(arr, "RGBA"))
    return lay


def glow(center, radius, color, strength):
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.hypot((x - center[0]) / radius[0], (y - center[1]) / radius[1])
    arr = np.zeros((H, W, 4), np.uint8)
    arr[..., :3] = color
    arr[..., 3] = (np.clip(1 - d, 0, 1) ** 2 * 255 * strength).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def bats_layer():
    lay = Image.new("L", (W * 2, H * 2), 0)
    d = ImageDraw.Draw(lay)
    for x, y, s, ph, ang in ((150, 690, 46, 0.6, -0.2), (905, 610, 62, 2.1, 0.15), (800, 770, 34, 4.0, -0.1),
                             (250, 560, 30, 5.2, 0.25), (990, 860, 26, 1.2, -0.3)):
        ca, sa = math.cos(ang), math.sin(ang)
        d.polygon([((x + (px * ca - py * sa) * s) * 2, (y + (px * sa + py * ca) * s) * 2) for px, py in bat_shape(ph)], fill=235)
    m = lay.resize((W, H), Image.LANCZOS)
    return Image.merge("RGBA", (Image.new("L", (W, H), 14), Image.new("L", (W, H), 6), Image.new("L", (W, H), 22), m))


def headline(img):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    f = font("Montserrat-Black.otf", 168)
    ys = [330, 500]
    for s, y in zip(LINES, ys):
        size = 168
        while f.getlength(s) > W - 90:                       # fit the width
            size -= 4
            f = font("Montserrat-Black.otf", size)
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((W // 2, y + 10), s, font=f, fill=(0, 0, 0, 200), anchor="ms", stroke_width=14, stroke_fill=(0, 0, 0, 200))
        lay.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)))
        ImageDraw.Draw(lay).text((W // 2, y), s, font=f, fill=(255, 255, 255), anchor="ms", stroke_width=9, stroke_fill=INK)
    img.alpha_composite(lay)


def badge(img, center, angle=-7):
    f = font("Montserrat-Black.otf", 150)
    tw = f.getlength(BADGE)
    bw, bh = int(tw + 110), 205
    b = Image.new("RGBA", (bw + 60, bh + 60), (0, 0, 0, 0))
    d = ImageDraw.Draw(b)
    d.rounded_rectangle((30, 30, 30 + bw, 30 + bh), radius=38, fill=ORANGE + (255,), outline=INK + (255,), width=9)
    d.text((30 + bw / 2, 30 + bh / 2 + 4), BADGE, font=f, fill=(255, 255, 255), anchor="mm", stroke_width=7, stroke_fill=INK)
    b = b.rotate(angle, resample=Image.BICUBIC, expand=True)
    sh = Image.new("RGBA", b.size, (0, 0, 0, 0))
    sh.putalpha(b.getchannel("A").point(lambda v: v * 0.6))
    sh = sh.filter(ImageFilter.GaussianBlur(12))
    x, y = int(center[0] - b.width / 2), int(center[1] - b.height / 2)
    img.alpha_composite(sh, (x + 8, y + 16))
    img.alpha_composite(b, (x, y))


def main():
    img = background()
    img.alpha_composite(glow((W / 2, 1130), (620, 520), (255, 110, 40), 0.20))
    img.alpha_composite(gradient())
    img.alpha_composite(bats_layer())
    headline(img)
    badge(img, (W / 2 + 255, 690))
    lg = Image.open(LOGO).convert("RGBA")
    lg = lg.crop(lg.getbbox())
    lg = lg.resize((round(lg.width * 74 / lg.height), 74), Image.LANCZOS)
    img.alpha_composite(lg, (W // 2 - lg.width // 2, 92))
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, "BooBoard_Shorts_Thumbnail.png")
    img.convert("RGB").save(p)
    img.convert("RGB").save(p[:-4] + ".jpg", quality=93)
    print(p)


if __name__ == "__main__":
    main()
