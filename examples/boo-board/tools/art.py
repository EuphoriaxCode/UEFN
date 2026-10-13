"""Boo Board textures, all drawn from code (SDF shapes + SIL-OFL fonts). Run: py -3.14 art.py

Mask textures (linear, recoloured in the material):
  T_BB_Btn_<Like|Favorite|Follow>  R = idle glyph (outline icon + label)   G = active glyph (filled icon + label)
                                   B = face shading (soft dome)            A = 1
  T_BB_Header_<n>                  R = text   G = outline   B = ornaments (bats)
  T_BB_Thanks_<n>                  R = text   G = outline   B = slime drips
  T_BB_PumpkinFace                 R = carved face
Colour textures (sRGB):
  T_BB_Sprites                     4x4 atlas of particle sprites (see SPRITES)
"""
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "art")
FONTS = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Windows", "Fonts")
FONT_BLACK = os.path.join(FONTS, "Montserrat-Black.otf")      # SIL Open Font License
FONT_ROUND = os.path.join(FONTS, "Poppins-Black.ttf")         # SIL Open Font License

HEADLINES = ["ENJOYING THE MAP?", "HAVING FUN?", "HAPPY HALLOWEEN!", "SUPPORT THIS MAP", "SPOOKY GOOD TIME?"]
THANKS = [("THANKS,", "BOO!"), ("THANK", "YOU!"), ("YOU", "ROCK!"), ("SPOOK-", "TACULAR!")]


# ------------------------------------------------------------------ SDF canvas
class Field:
    """Pixel-centre coordinates at `ss`x supersampling; shapes are SDFs in final pixels."""

    def __init__(self, w, h, ss=4):
        self.w, self.h, self.ss = w, h, ss
        ys, xs = np.mgrid[0:h * ss, 0:w * ss].astype(np.float32)
        self.x = (xs + 0.5) / ss
        self.y = (ys + 0.5) / ss

    def cov(self, d, soft=0.0):
        """Coverage from an SDF (negative inside). `soft` widens the edge (px) for glows."""
        if soft > 0:
            return np.clip(0.5 - d / soft, 0, 1)
        return np.clip(0.5 - d * self.ss, 0, 1)

    def down(self, a):
        s = self.ss
        return a.reshape(self.h, s, self.w, s).mean(axis=(1, 3))


def sd_circle(F, cx, cy, r):
    return np.hypot(F.x - cx, F.y - cy) - r


def sd_rrect(F, cx, cy, hw, hh, r):
    qx = np.abs(F.x - cx) - hw + r
    qy = np.abs(F.y - cy) - hh + r
    return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r


def sd_capsule(F, ax, ay, bx, by, r):
    px, py = F.x - ax, F.y - ay
    bax, bay = bx - ax, by - ay
    h = np.clip((px * bax + py * bay) / (bax * bax + bay * bay), 0, 1)
    return np.hypot(px - bax * h, py - bay * h) - r


def sd_ellipse(F, cx, cy, rx, ry):
    # cheap approximation, good enough for soft shapes
    k0 = np.hypot((F.x - cx) / rx, (F.y - cy) / ry)
    return (k0 - 1.0) * min(rx, ry)


def sd_heart(F, cx, cy, size):
    """Inigo Quilez' exact heart; the heart spans ~1.1*size tall, tip at the bottom."""
    px = np.abs(F.x - cx) / size
    py = (cy + 0.55 * size - F.y) / size        # y up, tip at y=0
    a = np.hypot(px - 0.25, py - 0.75) - math.sqrt(2) / 4
    m = np.maximum(px + py, 0) * 0.5
    b1 = (px - 0.0) ** 2 + (py - 1.0) ** 2
    b2 = (px - m) ** 2 + (py - m) ** 2
    b = np.sqrt(np.minimum(b1, b2)) * np.sign(px - py)
    return np.where(py + px > 1.0, a, b) * size


def sd_poly(F, pts):
    d = np.full(F.x.shape, 1e9, np.float32)
    s = np.ones(F.x.shape, np.float32)
    n = len(pts)
    for i in range(n):
        ax, ay = pts[i - 1]
        bx, by = pts[i]
        ex, ey = bx - ax, by - ay
        wx, wy = F.x - ax, F.y - ay
        h = np.clip((wx * ex + wy * ey) / (ex * ex + ey * ey), 0, 1)
        d = np.minimum(d, np.hypot(wx - ex * h, wy - ey * h))
        c1 = F.y >= ay
        c2 = F.y < by
        c3 = ex * wy > ey * wx
        flip = (c1 & c2 & c3) | (~c1 & ~c2 & ~c3)
        s = np.where(flip, -s, s)
    return d * s


def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)


def union(*ds):
    out = ds[0]
    for d in ds[1:]:
        out = np.minimum(out, d)
    return out


def subtract(a, b):
    return np.maximum(a, -b)


def stroke(d, w):
    return np.abs(d) - w / 2


# ------------------------------------------------------------------ text
def text_mask(w, h, lines, size, cy_list, font=FONT_BLACK, ss=3, tracking=0.0, max_w=None):
    """Returns a float mask (h, w) with the given lines centred at cy_list (px). Auto-shrinks to max_w."""
    W, H = w * ss, h * ss
    img = Image.new("L", (W, H), 0)
    dr = ImageDraw.Draw(img)
    for line, cy in zip(lines, cy_list):
        sz = size
        while True:
            f = ImageFont.truetype(font, int(sz * ss))
            widths = [dr.textlength(ch, font=f) for ch in line]
            tw = sum(widths) + tracking * ss * (len(line) - 1)
            if max_w is None or tw <= max_w * ss or sz < 10:
                break
            sz *= 0.96
        x = (W - tw) / 2
        asc, desc = f.getmetrics()
        bbox = f.getbbox(line)
        th = bbox[3] - bbox[1]
        y = cy * ss - th / 2 - bbox[1]
        for ch, cw in zip(line, widths):
            dr.text((x, y), ch, font=f, fill=255)
            x += cw + tracking * ss
    img = img.resize((w, h), Image.LANCZOS)
    return np.asarray(img).astype(np.float32) / 255.0


def dilate(mask, px, blur=0.0):
    img = Image.fromarray((np.clip(mask, 0, 1) * 255).astype(np.uint8))
    r = int(round(px))
    out = img
    while r > 0:
        k = min(r, 4)
        out = out.filter(ImageFilter.MaxFilter(2 * k + 1))
        r -= k
    if blur:
        out = out.filter(ImageFilter.GaussianBlur(blur))
    return np.asarray(out).astype(np.float32) / 255.0


def save_rgba(path, r, g, b, a=None, srgb_note=False):
    h, w = r.shape
    a = np.ones((h, w), np.float32) if a is None else a
    arr = np.stack([r, g, b, a], -1)
    Image.fromarray((np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA").save(path)


# ------------------------------------------------------------------ icons (unit = icon half-size in px)
def icon_thumb(F, cx, cy, u, filled):
    def P(x, y):
        return cx + x * u, cy + y * u
    sleeve = sd_rrect(F, *P(-0.74, 0.30), 0.17 * u, 0.44 * u, 0.08 * u)
    palm = sd_rrect(F, *P(0.10, 0.30), 0.54 * u, 0.44 * u, 0.24 * u)
    ax, ay = P(-0.28, 0.02)
    bx, by = P(0.06, -0.78)
    thumb = sd_capsule(F, ax, ay, bx, by, 0.20 * u)
    hand = smin(palm, thumb, 0.10 * u)
    lines = []
    for y in (0.10, 0.32, 0.54):
        lx0, ly = P(0.24, y)
        lx1, _ = P(0.66, y)
        lines.append(sd_capsule(F, lx0, ly, lx1, ly, 0.035 * u))
    knuckles = union(*lines)
    if filled:
        return subtract(union(hand, sleeve), knuckles)
    sw = 0.16 * u
    return union(stroke(hand, sw), stroke(sleeve, sw), knuckles - 0.01 * u)


def icon_heart(F, cx, cy, u, filled):
    d = sd_heart(F, cx, cy + 0.06 * u, 1.62 * u)
    return d if filled else stroke(d, 0.16 * u)


def icon_follow(F, cx, cy, u, filled):
    def P(x, y):
        return cx + x * u, cy + y * u
    head = sd_circle(F, *P(-0.18, -0.38), 0.34 * u)
    body = sd_rrect(F, *P(-0.18, 0.62), 0.66 * u, 0.46 * u, 0.44 * u)
    body = np.maximum(body, (F.y - (cy + 0.78 * u)))            # flat bottom
    person = union(head, body)
    bx, by = P(0.56, 0.42)
    br = 0.40 * u
    badge = sd_circle(F, bx, by, br)
    person = subtract(person, badge - 0.12 * u)                  # gap around the badge
    if filled:
        # check mark cut out of a solid badge
        c1 = sd_capsule(F, bx - 0.20 * u, by + 0.01 * u, bx - 0.05 * u, by + 0.16 * u, 0.07 * u)
        c2 = sd_capsule(F, bx - 0.05 * u, by + 0.16 * u, bx + 0.21 * u, by - 0.14 * u, 0.07 * u)
        return union(person, subtract(badge, union(c1, c2)))
    sw = 0.16 * u
    p1 = sd_capsule(F, bx - 0.19 * u, by, bx + 0.19 * u, by, 0.065 * u)
    p2 = sd_capsule(F, bx, by - 0.19 * u, bx, by + 0.19 * u, 0.065 * u)
    return union(stroke(person, sw), stroke(badge, sw), p1, p2)


ICONS = {"Like": icon_thumb, "Save": icon_heart, "Follow": icon_follow}
LABELS = {"Like": ("LIKE", "LIKED!"), "Save": ("SAVE", "SAVED!"), "Follow": ("FOLLOW", "FOLLOWING!")}


def dome(size, half_w_frac, radius_frac=0.12):
    Fd = Field(size, size, ss=1)
    d = sd_rrect(Fd, size / 2, size / 2, size * half_w_frac - 6, size / 2 - 6, size * radius_frac)
    return np.clip(-d / (size * 0.22), 0, 1) ** 0.7


def menu_tex(size=512):
    """The menu chip (56 x 50 cm face, UV covers 56 x 56): three rounded bars."""
    F = Field(size, size, ss=4)
    bars = union(*[sd_capsule(F, size * 0.33, size * y, size * 0.67, size * y, size * 0.042) for y in (0.37, 0.5, 0.63)])
    m = F.down(F.cov(bars))
    save_rgba(os.path.join(OUT, "T_BB_Btn_Menu.png"), m, m, dome(size, 25.0 / 56.0, 0.2))


def avatar_tex(size=512):
    """Avatar chip: G = disc, R = little ghost (eyes cut out), B = 'online' dot (with a gap ring)."""
    F = Field(size, size, ss=4)
    c = size / 2
    disc = sd_circle(F, c, c, size * 0.45)
    dot_x, dot_y, dot_r = c + size * 0.32, c + size * 0.32, size * 0.105
    dot = sd_circle(F, dot_x, dot_y, dot_r)
    disc = subtract(disc, dot - size * 0.035)
    u = size * 0.30
    head = sd_circle(F, c, c - u * 0.18, u * 0.62)
    body = sd_rrect(F, c, c + u * 0.42, u * 0.62, u * 0.6, u * 0.1)
    hem = union(*[sd_circle(F, c - u * 0.42 + u * 0.42 * i, c + u * 0.98, u * 0.22) for i in range(3)])
    ghost = smin(smin(head, body, u * 0.1), hem, u * 0.05)
    ghost = subtract(ghost, union(*[sd_circle(F, c - u * 0.25 + u * 0.5 * i, c + u * 1.10, u * 0.17) for i in range(2)]))
    eyes = union(sd_ellipse(F, c - u * 0.22, c - u * 0.18, u * 0.1, u * 0.15), sd_ellipse(F, c + u * 0.22, c - u * 0.18, u * 0.1, u * 0.15))
    ghost = subtract(np.maximum(ghost, disc - 0.0), eyes)          # clip to the disc, cut the eyes
    G = F.down(F.cov(disc))
    R = F.down(F.cov(ghost))
    B = F.down(F.cov(dot))
    save_rgba(os.path.join(OUT, "T_BB_Avatar.png"), R, G, B)


def button_tex(name, size=512):
    """512x512 covers 112x112 cm of the button face (the 100 cm wide button spans u 0.027..0.973)."""
    F = Field(size, size, ss=4)
    cx, cy, u = size / 2, size * 0.39, size * 0.165
    icon_off = F.down(F.cov(ICONS[name](F, cx, cy, u, False)))
    icon_on = F.down(F.cov(ICONS[name](F, cx, cy, u, True)))
    off_l, on_l = LABELS[name]
    lab_off = text_mask(size, size, [off_l], 62, [size * 0.79], max_w=size * 0.80, tracking=1.5)
    lab_on = text_mask(size, size, [on_l], 62, [size * 0.79], max_w=size * 0.80, tracking=1.5)
    R = np.maximum(icon_off, lab_off)
    G = np.maximum(icon_on, lab_on)
    B = dome(size, 50.0 / 112.0)     # soft dome: 1 in the centre, falling off towards the rounded edge
    save_rgba(os.path.join(OUT, f"T_BB_Btn_{name}.png"), R, G, B)


def bat_shape(F, cx, cy, s, up):
    """Bat silhouette SDF. s = half wingspan (px). up = wings raised (flap frame A), else lowered (frame B)."""
    body = sd_ellipse(F, cx, cy + 0.06 * s, 0.15 * s, 0.22 * s)
    head = sd_circle(F, cx, cy - 0.17 * s, 0.12 * s)
    ear1 = sd_poly(F, [(cx - 0.11 * s, cy - 0.20 * s), (cx - 0.12 * s, cy - 0.40 * s), (cx - 0.01 * s, cy - 0.25 * s)])
    ear2 = sd_poly(F, [(cx + 0.01 * s, cy - 0.25 * s), (cx + 0.12 * s, cy - 0.40 * s), (cx + 0.11 * s, cy - 0.20 * s)])
    # wing in "unit wing space": x 0 (shoulder) .. 1 (tip), y down; frame A raised, frame B drooping
    if up:
        sh, ctrl, tip, fingers = (0.08, -0.08), (0.45, -0.75), (1.0, -0.62), [(1.0, -0.62), (0.80, -0.18), (0.56, -0.02), (0.30, 0.12), (0.10, 0.16)]
    else:
        sh, ctrl, tip, fingers = (0.08, -0.10), (0.50, -0.42), (1.0, 0.30), [(1.0, 0.30), (0.78, 0.40), (0.54, 0.36), (0.30, 0.30), (0.10, 0.18)]
    wings = []
    for side in (-1, 1):
        def W(p):
            return (cx + side * p[0] * s, cy + p[1] * s)
        pts = []
        for i in range(9):                       # top edge: quadratic bezier shoulder -> tip
            t = i / 8
            pts.append(W(((1 - t) ** 2 * sh[0] + 2 * (1 - t) * t * ctrl[0] + t * t * tip[0],
                          (1 - t) ** 2 * sh[1] + 2 * (1 - t) * t * ctrl[1] + t * t * tip[1])))
        for a, b in zip(fingers, fingers[1:]):   # lower edge: scallops bulging up between finger tips
            for i in range(1, 7):
                t = i / 6
                x = a[0] + (b[0] - a[0]) * t
                y = a[1] + (b[1] - a[1]) * t - math.sin(math.pi * t) * 0.13
                pts.append(W((x, y)))
        if side > 0:
            pts = pts[::-1]
        wings.append(sd_poly(F, pts))
    return smin(union(body, head, ear1, ear2), union(*wings), 0.04 * s)


def header_tex(idx, text, w=1024, h=236):
    """Headline card (260 x 60 cm) at the top of the board."""
    fill = text_mask(w, h, [text], 132, [h * 0.52], max_w=w * 0.92, tracking=2.0)
    outline = dilate(fill, 10, blur=1.2)
    B = np.zeros_like(fill)
    save_rgba(os.path.join(OUT, f"T_BB_Header_{idx}.png"), fill, outline, B)


def thanks_tex(idx, lines, w=1024, h=512, seed=7):
    fill = text_mask(w, h, list(lines), 190, [h * 0.27, h * 0.66], max_w=w * 0.92, tracking=3.0)
    outline = dilate(fill, 12, blur=1.5)
    # slime drips hanging from the bottom edge of the outline
    rng = np.random.default_rng(seed)
    F = Field(w, h, ss=2)
    dr = np.full(F.x.shape, 1e9, np.float32)
    col = outline.max(axis=0)
    rows = np.arange(h)
    for _ in range(40):
        x = int(rng.uniform(w * 0.08, w * 0.92))
        colmask = outline[:, x] > 0.5
        if not colmask.any():
            continue
        # bottom of the outline in the lower line
        ys = rows[colmask & (rows > h * 0.5)]       # only below the second line
        if len(ys) == 0:
            continue
        y0 = ys.max() - 6
        ln = rng.uniform(18, 70)
        r = rng.uniform(7, 12)
        d = sd_capsule(F, x, y0, x, y0 + ln, r * 0.55)
        d = smin(d, sd_circle(F, x, y0 + ln, r), 6)
        dr = np.minimum(dr, d)
    B = np.maximum(F.down(F.cov(dr)) * (1 - fill), 0)
    save_rgba(os.path.join(OUT, f"T_BB_Thanks_{idx}.png"), fill, np.maximum(outline, B), B)


def pumpkin_face(w=512, h=256):
    """Carved jack-o'-lantern face centred at u=0.5 (front of the lathe), v 0=top."""
    F = Field(w, h, ss=4)
    cx = w / 2
    eye_l = sd_poly(F, [(cx - 70, 120), (cx - 30, 120), (cx - 52, 78)])
    eye_r = sd_poly(F, [(cx + 30, 120), (cx + 70, 120), (cx + 52, 78)])
    nose = sd_poly(F, [(cx - 12, 150), (cx + 12, 150), (cx, 132)])
    mouth_top = 168
    pts = [(cx - 78, mouth_top), (cx - 52, mouth_top + 10), (cx - 40, mouth_top), (cx - 22, mouth_top + 12),
           (cx, mouth_top + 2), (cx + 22, mouth_top + 12), (cx + 40, mouth_top), (cx + 52, mouth_top + 10),
           (cx + 78, mouth_top), (cx + 56, mouth_top + 34), (cx + 30, mouth_top + 42), (cx + 18, mouth_top + 30),
           (cx + 4, mouth_top + 44), (cx - 14, mouth_top + 32), (cx - 30, mouth_top + 44), (cx - 56, mouth_top + 34)]
    mouth = sd_poly(F, pts[::-1])
    R = F.down(F.cov(union(eye_l, eye_r, nose, mouth)))
    z = np.zeros_like(R)
    save_rgba(os.path.join(OUT, "T_BB_PumpkinFace.png"), R, z, z)


# ------------------------------------------------------------------ colour sprites
def hexc(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)


class Painter:
    def __init__(self, n=256, ss=4):
        self.F = Field(n, n, ss)
        self.rgb = np.zeros(self.F.x.shape + (3,), np.float32)
        self.a = np.zeros(self.F.x.shape, np.float32)

    def paint(self, d, col, soft=0.0, alpha=1.0):
        c = (self.F.cov(d, soft) if soft else self.F.cov(d)) * alpha
        col = np.asarray(col, np.float32)
        if col.ndim == 1:
            col = np.broadcast_to(col, self.rgb.shape)
        self.rgb = self.rgb * (1 - c[..., None]) + col * c[..., None]
        self.a = self.a + c * (1 - self.a)

    def vgrad(self, c0, c1, y0, y1):
        t = np.clip((self.F.y - y0) / (y1 - y0), 0, 1)[..., None]
        return c0 * (1 - t) + c1 * t

    def image(self):
        s = self.F.ss
        n = self.F.w
        rgb = self.rgb.reshape(n, s, n, s, 3).mean(axis=(1, 3))
        a = self.a.reshape(n, s, n, s).mean(axis=(1, 3))
        return np.concatenate([rgb, a[..., None]], -1)


INK = hexc("#1b1028")


def spr_pumpkin(P, scale=1.0):
    F = P.F
    c = 128
    r = 86 * scale
    lobes = union(sd_ellipse(F, c, c + 14, r, r * 0.82), sd_ellipse(F, c - r * 0.45, c + 14, r * 0.62, r * 0.80),
                  sd_ellipse(F, c + r * 0.45, c + 14, r * 0.62, r * 0.80))
    stem = sd_rrect(F, c + 6, c - r * 0.78, 9 * scale, 20 * scale, 6 * scale)
    P.paint(union(lobes, stem) - 7, INK)
    P.paint(stem, hexc("#5a8a2a"))
    P.paint(lobes, P.vgrad(hexc("#ffb02e"), hexc("#e8590c"), c - r, c + r))
    for k in (-0.45, 0.45):
        P.paint(sd_capsule(F, c + k * r * 0.62, c - r * 0.5, c + k * r * 0.62, c + r * 0.6, 3), hexc("#c94a08"), alpha=0.6)
    P.paint(sd_ellipse(F, c - r * 0.45, c - r * 0.25, r * 0.22, r * 0.13), hexc("#ffe2a8"), alpha=0.55)
    face = union(sd_poly(F, [(c - 40 * scale, c + 2), (c - 12 * scale, c + 2), (c - 26 * scale, c - 24 * scale)]),
                 sd_poly(F, [(c + 12 * scale, c + 2), (c + 40 * scale, c + 2), (c + 26 * scale, c - 24 * scale)]),
                 sd_ellipse(F, c, c + 38 * scale, 42 * scale, 14 * scale))
    P.paint(face, hexc("#3a1300"))


def spr_heart(P, c0, c1):
    F = P.F
    d = sd_heart(F, 128, 132, 150)
    P.paint(d - 8, INK)
    P.paint(d, P.vgrad(c0, c1, 50, 210))
    P.paint(sd_ellipse(F, 92, 92, 22, 14), hexc("#ffffff"), alpha=0.6)


def spr_sparkle(P, col):
    F = P.F
    c = 128
    pts = []
    for i in range(8):
        a = -math.pi / 2 + i * math.pi / 4
        r = 100 if i % 2 == 0 else 26
        pts.append((c + r * math.cos(a), c + r * math.sin(a)))
    d = sd_poly(F, pts[::-1])
    P.paint(sd_circle(F, c, c, 60), col, soft=70, alpha=0.6)
    P.paint(d, hexc("#ffffff"))
    P.paint(d + 6, col)


def spr_thumb(P):
    F = P.F
    d = icon_thumb(F, 128, 132, 70, True)
    P.paint(d - 8, INK)
    P.paint(d, P.vgrad(hexc("#ffc14d"), hexc("#ff7a1a"), 60, 200))


def spr_ghost(P):
    F = P.F
    c = 128
    head = sd_circle(F, c, c - 18, 66)
    skirt = sd_rrect(F, c, c + 34, 66, 56, 10)
    waves = union(*[sd_circle(F, c - 44 + 44 * i, c + 92, 24) for i in range(3)])
    body = subtract(smin(head, skirt, 10), union(*[sd_circle(F, c - 22 + 44 * i, c + 98, 20) for i in range(2)]))
    body = smin(body, waves, 4)
    P.paint(body - 7, INK)
    P.paint(body, P.vgrad(hexc("#ffffff"), hexc("#cfe9ff"), 50, 220))
    P.paint(union(sd_ellipse(F, c - 24, c - 18, 11, 16), sd_ellipse(F, c + 24, c - 18, 11, 16)), INK)
    P.paint(sd_ellipse(F, c, c + 16, 10, 12), INK)


def spr_slime_star(P):
    F = P.F
    c = 128
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        r = 96 if i % 2 == 0 else 44
        pts.append((c + r * math.cos(a), c + 8 + r * math.sin(a)))
    d = sd_poly(F, pts[::-1]) - 10
    P.paint(d - 8, INK)
    P.paint(d, P.vgrad(hexc("#c6ff4d"), hexc("#3ccf3c"), 40, 220))
    P.paint(sd_ellipse(F, c - 22, c - 18, 16, 10), hexc("#ffffff"), alpha=0.6)


def spr_candy_corn(P):
    F = P.F
    tri = sd_poly(F, [(70, 200), (186, 200), (128, 44)]) - 16
    P.paint(tri - 8, INK)
    band = np.where(F.y > 160, 0, np.where(F.y > 105, 1, 2))
    cols = np.stack([hexc("#ffd23f"), hexc("#ff8a1d"), hexc("#fff6e8")])
    P.paint(tri, cols[band])


def spr_wrapped(P):
    F = P.F
    c = 128
    body = sd_ellipse(F, c, c, 56, 44)
    w1 = sd_poly(F, [(c - 50, c), (c - 108, c - 40), (c - 100, c + 42)])
    w2 = sd_poly(F, [(c + 50, c), (c + 100, c + 42), (c + 108, c - 40)])
    d = union(body, w1 - 6, w2 - 6)
    P.paint(d - 8, INK)
    P.paint(union(w1 - 6, w2 - 6), hexc("#b04dff"))
    P.paint(body, P.vgrad(hexc("#d38bff"), hexc("#8a2be2"), c - 44, c + 44))
    for k in (-24, 0, 24):
        P.paint(sd_capsule(F, c + k - 10, c - 40, c + k + 10, c + 40, 6), hexc("#ffffff"), alpha=0.5)


def spr_lollipop(P):
    F = P.F
    c = 120
    stick = sd_rrect(F, c, c + 92, 7, 46, 6)
    disc = sd_circle(F, c, c - 6, 70)
    P.paint(union(stick, disc) - 8, INK)
    P.paint(stick, hexc("#fff3e0"))
    ang = np.arctan2(F.y - (c - 6), F.x - c)
    rad = np.hypot(F.x - c, F.y - (c - 6))
    sw = (np.sin(ang * 1 + rad * 0.12) > 0)
    P.paint(disc, np.where(sw[..., None], hexc("#ff4fa3"), hexc("#ffe0f0")))


def spr_bat(P, up):
    d = bat_shape(P.F, 128, 128, 112, up)
    P.paint(d - 7, hexc("#9b6bff"), alpha=0.9)
    P.paint(d, hexc("#1a1024"))
    P.paint(union(sd_circle(P.F, 120, 102, 5), sd_circle(P.F, 136, 102, 5)), hexc("#ffcf3a"))


def spr_glow(P):
    P.paint(sd_circle(P.F, 128, 128, 10), hexc("#ffffff"), soft=110)


SPRITES = [
    ("pumpkin", lambda P: spr_pumpkin(P)),
    ("spark_orange", lambda P: spr_sparkle(P, hexc("#ff9a1f"))),
    ("thumb", spr_thumb),
    ("heart_purple", lambda P: spr_heart(P, hexc("#c77dff"), hexc("#7b2cbf"))),
    ("heart_pink", lambda P: spr_heart(P, hexc("#ff8fc8"), hexc("#ff2d87"))),
    ("spark_pink", lambda P: spr_sparkle(P, hexc("#ff4fd1"))),
    ("ghost", spr_ghost),
    ("slime_star", spr_slime_star),
    ("spark_green", lambda P: spr_sparkle(P, hexc("#7dff3a"))),
    ("candy_corn", spr_candy_corn),
    ("wrapped", spr_wrapped),
    ("lollipop", spr_lollipop),
    ("pumpkin_small", lambda P: spr_pumpkin(P, 0.8)),
    ("bat_up", lambda P: spr_bat(P, True)),
    ("bat_down", lambda P: spr_bat(P, False)),
    ("glow", spr_glow),
]


def sprites(n=256):
    atlas = np.zeros((4 * n, 4 * n, 4), np.float32)
    for i, (name, fn) in enumerate(SPRITES):
        P = Painter(n, ss=3)
        fn(P)
        img = P.image()
        r, c = divmod(i, 4)
        atlas[r * n:(r + 1) * n, c * n:(c + 1) * n] = img
    # bleed colour into transparent texels so mips/bilinear don't show dark fringes
    rgb, a = atlas[..., :3], atlas[..., 3:4]
    img = Image.fromarray((np.clip(atlas, 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA")
    img.save(os.path.join(OUT, "T_BB_Sprites.png"))


def main():
    os.makedirs(OUT, exist_ok=True)
    import art_ui
    art_ui.main()
    for i, t in enumerate(HEADLINES):
        header_tex(i, t)
    for i, t in enumerate(THANKS):
        thanks_tex(i, t)
    pumpkin_face()
    sprites()
    print("art ->", os.path.abspath(OUT))


if __name__ == "__main__":
    main()
