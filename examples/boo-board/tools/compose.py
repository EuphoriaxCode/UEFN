"""Compose the Boo Board promo from the raw renders: crop/scale to 1080p, crossfades, titles, captions -> MP4.

    py -3.14 compose.py            # all frames + encode
    py -3.14 compose.py --still 120 # one frame for checking (written to %TEMP%/bb_still.png)
"""
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from art import FONTS

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(os.environ["TEMP"], "bb_promo_raw")
FINAL = os.path.join(os.environ["TEMP"], "bb_promo_final")
OUT_DIR = os.path.abspath(os.path.join(HERE, "..", "promo"))
FPS = 30
W, H = 1920, 1080
CROP = (140, 0, 1529, 781)          # drops the viewport axis gizmo, exact 16:9
XF = 8                              # crossfade frames

F_TITLE = os.path.join(FONTS, "Montserrat-Black.otf")
F_BOLD = os.path.join(FONTS, "Poppins-Bold.ttf")
F_SEMI = os.path.join(FONTS, "Poppins-SemiBold.ttf")
F_MED = os.path.join(FONTS, "Poppins-Medium.ttf")

BONE = (255, 240, 220)
ORANGE = (255, 138, 36)
LAV = (214, 205, 255)
INK = (16, 10, 28)

SEQ = [("hero", 330), ("close", 180)] + [(f"style{k}", 36) for k in range(5)] + \
      [(f"mount{k}", 45) for k in range(4)] + [("options", 180), ("outro", 120)]
CUT = {"style1", "style2", "style3", "style4", "mount1", "mount2", "mount3"}   # hard cuts inside a section
STYLE_NAMES = ["Pumpkin Night", "Ghostly Mint", "Witch Brew", "Blood Moon", "Candy Pop"]
MOUNT_NAMES = ["Graveyard Arch", "Lantern Post", "Spider Thread", "Floating Magic"]


def font(path, size, _cache={}):
    key = (path, size)
    if key not in _cache:
        _cache[key] = ImageFont.truetype(path, size)
    return _cache[key]


def timeline():
    """List of output frames: [(shot, idx, weight), ...] (two entries during a crossfade)."""
    out = []
    starts = {}
    for k, (name, n) in enumerate(SEQ):
        if k == 0 or name in CUT:
            starts[name] = len(out)
            out += [[(name, i, 1.0)] for i in range(n)]
            continue
        # crossfade the first XF frames of this shot over the last XF frames of the output
        start = len(out) - XF
        starts[name] = start
        for i in range(n):
            j = start + i
            if i < XF:
                w = (i + 1) / (XF + 1)
                out[j] = [(a, b, c * (1 - w)) for a, b, c in out[j]] + [(name, i, w)]
            else:
                out.append([(name, i, 1.0)])
    return out, starts


def load(shot, i):
    p = os.path.join(RAW, shot, f"f_{i:04d}.png")
    im = Image.open(p).convert("RGB").crop(CROP).resize((W, H), Image.LANCZOS)
    return np.asarray(im).astype(np.float32)


VIGNETTE = None


def vignette():
    global VIGNETTE
    if VIGNETTE is None:
        y, x = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.hypot((x - W / 2) / (W / 2), (y - H / 2) / (H / 2))
        VIGNETTE = (1.0 - 0.32 * np.clip(d - 0.55, 0, 1) ** 1.5)[..., None]
    return VIGNETTE


# ------------------------------------------------------------------ overlay helpers
def fade(t, t0, t1, d=0.35):
    """0..1 envelope: fades in at t0, out at t1 (seconds)."""
    if t < t0 or t > t1:
        return 0.0
    return min(1.0, (t - t0) / d, (t1 - t) / d)


def slide(a, px=26):
    return int((1 - a) ** 2 * px)


def text(layer, xy, s, f, fill, a, anchor="la", glow=None, shadow=True):
    if a <= 0:
        return
    x, y = xy
    if glow:
        g = Image.new("RGBA", layer.size, (0, 0, 0, 0))
        ImageDraw.Draw(g).text((x, y), s, font=f, fill=glow + (int(200 * a),), anchor=anchor)
        layer.alpha_composite(g.filter(ImageFilter.GaussianBlur(14)))
    d = ImageDraw.Draw(layer)
    if shadow:
        d.text((x + 3, y + 4), s, font=f, fill=(0, 0, 0, int(150 * a)), anchor=anchor)
    d.text((x, y), s, font=f, fill=fill + (int(255 * a),), anchor=anchor)


def pill(layer, xy, s, f, a, fg=INK, bg=LAV, pad=(26, 14), anchor="center"):
    if a <= 0:
        return
    d = ImageDraw.Draw(layer)
    l, t, r, b = d.textbbox((0, 0), s, font=f)
    w, h = r - l + 2 * pad[0], b - t + 2 * pad[1]
    x, y = xy
    if anchor == "center":
        x -= w // 2
    box = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    bd = ImageDraw.Draw(box)
    bd.rounded_rectangle((x + 4, y + 6, x + w + 4, y + h + 6), radius=h // 2, fill=(0, 0, 0, int(110 * a)))
    bd.rounded_rectangle((x, y, x + w, y + h), radius=h // 2, fill=bg + (int(240 * a),))
    bd.text((x + pad[0] - l, y + pad[1] - t), s, font=f, fill=fg + (int(255 * a),))
    layer.alpha_composite(box)


def left_shade(layer, a, width=0.62):
    if a <= 0:
        return
    g = np.zeros((H, W, 4), np.uint8)
    ramp = np.clip(1.0 - np.linspace(0, 1, W) / width, 0, 1) ** 1.4
    g[..., 3] = (ramp[None, :] * 210 * a).astype(np.uint8)
    g[..., :3] = (10, 4, 20)
    layer.alpha_composite(Image.fromarray(g, "RGBA"))


def right_shade(layer, a, width=0.6):
    if a <= 0:
        return
    g = np.zeros((H, W, 4), np.uint8)
    ramp = np.clip(1.0 - (1.0 - np.linspace(0, 1, W)) / width, 0, 1) ** 1.3
    g[..., 3] = (ramp[None, :] * 215 * a).astype(np.uint8)
    g[..., :3] = (10, 4, 20)
    layer.alpha_composite(Image.fromarray(g, "RGBA"))


def dim(layer, a, k=0.55):
    if a > 0:
        layer.alpha_composite(Image.new("RGBA", (W, H), (8, 3, 16, int(255 * k * a))))


def step_badge(layer, x, y, n, s, a):
    if a <= 0:
        return
    d = ImageDraw.Draw(layer)
    r = 30
    d.ellipse((x, y, x + 2 * r, y + 2 * r), fill=ORANGE + (int(255 * a),))
    d.text((x + r, y + r + 1), str(n), font=font(F_BOLD, 34), fill=INK + (int(255 * a),), anchor="mm")
    text(layer, (x + 2 * r + 18, y + r + 2), s, font(F_SEMI, 44), BONE, a, anchor="lm")


# ------------------------------------------------------------------ per-shot overlays
def overlay(layer, shot, i):
    t = i / FPS
    if shot == "hero":
        a = fade(t, 0.15, 2.5, 0.4)
        left_shade(layer, max(a, 0.0))
        dy = slide(a)
        text(layer, (130, 330 + dy), "HALLOWEEN  ·  FREE FOR UEFN", font(F_SEMI, 34), ORANGE, a, shadow=False)
        text(layer, (122, 398 + dy), "BOO BOARD", font(F_TITLE, 128), BONE, a, glow=ORANGE)
        text(layer, (130, 575 + dy), "An animated Like · Save · Follow sign", font(F_MED, 44), LAV, a)
        text(layer, (130, 631 + dy), "that shows players where to click.", font(F_MED, 44), LAV, a)
        for n, (t0, t1, s) in enumerate([(2.45, 3.4, "Opens the menu"), (3.4, 6.1, "Like  ·  Save  ·  Follow Dev"),
                                         (6.45, 8.7, "Says thanks")], 1):
            b = fade(t, t0, t1, 0.25)
            step_badge(layer, 120, 900 + slide(b), n, s, b)
    elif shot == "close":
        b = fade(t, 0.3, 5.7)
        pill(layer, (W // 2, 978 + slide(b)), "Looks just like the in-game menu", font(F_SEMI, 44), b)
    elif shot.startswith("style"):
        k = int(shot[-1])
        b = fade(i + k * 36, 4, 5 * 36 - 2, 6) if True else 0
        text(layer, (120, 110), "5 STYLES", font(F_TITLE, 88), BONE, b, glow=ORANGE)
        text(layer, (124, 220), "+ your own colours", font(F_MED, 40), LAV, b)
        pill(layer, (W // 2, 940), STYLE_NAMES[k], font(F_BOLD, 46), 1.0)
    elif shot.startswith("mount"):
        k = int(shot[-1])
        b = fade(i + k * 45, 4, 4 * 45 - 2, 6)
        text(layer, (120, 110), "PICK A MOUNT", font(F_TITLE, 88), BONE, b, glow=ORANGE)
        text(layer, (124, 220), "or none - hang it on any wall", font(F_MED, 40), LAV, b)
        pill(layer, (W // 2, 940), MOUNT_NAMES[k], font(F_BOLD, 46), 1.0)
    elif shot == "options":
        a = fade(t, 0.2, 5.8, 0.4)
        right_shade(layer, a)
        x0 = 960
        text(layer, (x0, 150 + slide(a)), "ALL IN THE", font(F_TITLE, 70), ORANGE, a)
        text(layer, (x0, 228 + slide(a)), "DETAILS PANEL", font(F_TITLE, 96), BONE, a, glow=ORANGE)
        items = ["Style  &  custom colours", "Headline  (5 texts)", "Thanks message  (4 texts)", "Mount, chain length, sway",
                 "Size  &  animation speed", "Show / hide ghost, bats, pumpkins, candy"]
        for k, s_ in enumerate(items):
            b = fade(t, 0.6 + 0.28 * k, 5.8, 0.3)
            y = 410 + 92 * k + slide(b, 18)
            d = ImageDraw.Draw(layer)
            if b > 0:
                d.rounded_rectangle((x0 + 2, y + 14, x0 + 26, y + 38), radius=7, fill=LAV + (int(255 * b),))
            text(layer, (x0 + 52, y), s_, font(F_SEMI, 39), BONE, b)
    elif shot == "outro":
        a = fade(t, 0.3, 4.2, 0.5)
        dim(layer, a, 0.6)
        d = ImageDraw.Draw(layer)
        text(layer, (W // 2, 330 + slide(a)), "FREE", font(F_TITLE, 190), BONE, a, anchor="mm", glow=ORANGE)
        text(layer, (W // 2, 470 + slide(a)), "One Verse device  ·  Drop in, pick a style, done", font(F_MED, 46), LAV, a, anchor="mm")
        text(layer, (W // 2, 530 + slide(a)), "Animated on every player's screen  ·  zero server cost", font(F_MED, 40), LAV, a, anchor="mm")
        text(layer, (W // 2, 660 + slide(a)), "BOO BOARD  by  EUPHORIAX", font(F_BOLD, 44), ORANGE, a, anchor="mm")


def frame(entries, k_out, starts):
    acc = None
    for shot, i, w in entries:
        img = load(shot, i) * w
        acc = img if acc is None else acc + img
    acc = acc * vignette()
    base = Image.fromarray(np.clip(acc, 0, 255).astype(np.uint8)).convert("RGBA")
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for shot, i, w in entries:
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        overlay(lay, shot, i)
        if w < 1.0:
            arr = np.asarray(lay).copy()
            arr[..., 3] = (arr[..., 3] * w).astype(np.uint8)
            lay = Image.fromarray(arr, "RGBA")
        layer.alpha_composite(lay)
    base.alpha_composite(layer)
    # fade from / to black
    n_total = len(TL)
    f = min(1.0, (k_out + 1) / 12, (n_total - k_out) / 18)
    out = base.convert("RGB")
    if f < 1.0:
        out = Image.fromarray((np.asarray(out).astype(np.float32) * f).astype(np.uint8))
    return out


TL, STARTS = timeline()


def main():
    if "--still" in sys.argv:
        k = int(sys.argv[sys.argv.index("--still") + 1])
        p = os.path.join(os.environ["TEMP"], "bb_still.png")
        frame(TL[k], k, STARTS).save(p)
        print(p)
        return
    os.makedirs(FINAL, exist_ok=True)
    for k, entries in enumerate(TL):
        p = os.path.join(FINAL, f"{k:05d}.png")
        frame(entries, k, STARTS).save(p, compress_level=1)
        if k % 60 == 0:
            print("composed", k, "/", len(TL), flush=True)
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, "boo_board_promo.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", os.path.join(FINAL, "%05d.png"),
                    "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                    out], check=True)
    print("wrote", out, f"{len(TL) / FPS:.1f}s")


if __name__ == "__main__":
    main()
