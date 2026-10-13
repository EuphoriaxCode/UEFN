"""Boo Board: in-game-menu style UI textures (tiles, top bar, menu chip, avatar). Run: py -3.14 art_ui.py

The tiles mimic the look of the Fortnite pause menu so players recognise where to click: dark navy tiles, thin
outline icons, a short label, a lavender highlight when active. Everything is drawn from code (SDF shapes) and
labels use Poppins (SIL Open Font License) - no Epic assets or fonts.

Mask channels (recoloured in the materials):
  T_BB_Btn_<Like|Save|Follow>  R = idle glyph (outline icon + label)  G = active glyph (filled icon + label)  B = soft dome
  T_BB_Btn_Menu                R = G = three bars                       B = soft dome
  T_BB_TopBar                  R = icons (friends, chat, settings)      G = pill background
  T_BB_Avatar                  R = ring + ghost portrait   G = disc     B = online dot
"""
import math
import os

import numpy as np

from art import (FONTS, OUT, Field, dilate, save_rgba, sd_capsule, sd_circle, sd_ellipse, sd_heart, sd_poly, sd_rrect,
                 smin, stroke, subtract, text_mask, union)

FONT_LABEL = os.path.join(FONTS, "Poppins-SemiBold.ttf")      # SIL Open Font License
STROKE = 0.17          # outline width in icon units (icon spans about [-1, 1])


def P(cx, cy, u):
    return lambda x, y: (cx + x * u, cy + y * u)


# ------------------------------------------------------------------ tile icons
def thumb(F, cx, cy, u, filled):
    p = P(cx, cy, u)
    cuff = sd_rrect(F, *p(-0.74, 0.30), 0.15 * u, 0.42 * u, 0.07 * u)
    palm = sd_rrect(F, *p(0.12, 0.30), 0.50 * u, 0.42 * u, 0.20 * u)
    thumb_ = sd_capsule(F, *p(-0.26, -0.02), *p(0.02, -0.74), 0.18 * u)
    hand = smin(palm, thumb_, 0.14 * u)
    if filled:
        return union(hand, cuff)
    return union(stroke(hand, STROKE * u), stroke(cuff, STROKE * u))


def heart(F, cx, cy, u, filled):
    d = sd_heart(F, cx, cy + 0.04 * u, 1.70 * u)
    return d if filled else stroke(d, STROKE * u)


def plus(F, cx, cy, u, filled):
    p = P(cx, cy, u)
    if filled:      # active state: a bold check mark
        a = sd_capsule(F, *p(-0.78, 0.02), *p(-0.24, 0.56), 0.19 * u)
        b = sd_capsule(F, *p(-0.24, 0.56), *p(0.80, -0.52), 0.19 * u)
        return union(a, b)
    cross = union(sd_rrect(F, cx, cy, 0.82 * u, 0.22 * u, 0.08 * u), sd_rrect(F, cx, cy, 0.22 * u, 0.82 * u, 0.08 * u))
    return stroke(cross, STROKE * u)


ICONS = {"Like": thumb, "Save": heart, "Follow": plus}
LABELS = {"Like": ("Like", "Liked"), "Save": ("Save", "Saved"), "Follow": ("Follow Dev", "Following")}


def dome(size, hw_frac, r_frac):
    Fd = Field(size, size, ss=1)
    d = sd_rrect(Fd, size / 2, size / 2, size * hw_frac - 4, size / 2 - 4, size * r_frac)
    return 0.6 + 0.4 * np.clip(-d / (size * 0.25), 0, 1) ** 0.8


def tile_tex(name, size=512):
    """512 x 512 covers 100 x 100 cm; the 100 x 84 cm tile spans v 0.08 .. 0.92."""
    F = Field(size, size, ss=4)
    cx, cy, u = size / 2, size * 0.375, size * 0.13
    off = F.down(F.cov(ICONS[name](F, cx, cy, u, False)))
    on = F.down(F.cov(ICONS[name](F, cx, cy, u, True)))
    l0, l1 = LABELS[name]
    lab0 = text_mask(size, size, [l0], 62, [size * 0.715], font=FONT_LABEL, max_w=size * 0.86)
    lab1 = text_mask(size, size, [l1], 62, [size * 0.715], font=FONT_LABEL, max_w=size * 0.86)
    save_rgba(os.path.join(OUT, f"T_BB_Btn_{name}.png"), np.maximum(off, lab0), np.maximum(on, lab1),
              dome(size, 0.5, 0.12))


def menu_tex(size=512):
    """The menu chip (52 x 42 cm face, UV covers 52 x 52)."""
    F = Field(size, size, ss=4)
    bars = union(*[sd_capsule(F, size * 0.355, size * y, size * 0.645, size * y, size * 0.034) for y in (0.40, 0.50, 0.60)])
    m = F.down(F.cov(bars))
    save_rgba(os.path.join(OUT, "T_BB_Btn_Menu.png"), m, m, dome(size, 0.5, 0.2))


# ------------------------------------------------------------------ top bar icons (filled)
def friends(F, cx, cy, u):
    p = P(cx, cy, u)
    front = union(sd_circle(F, *p(-0.22, -0.30), 0.30 * u),
                  np.maximum(sd_rrect(F, *p(-0.22, 0.52), 0.56 * u, 0.40 * u, 0.36 * u), F.y - (cy + 0.74 * u)))
    back = union(sd_circle(F, *p(0.44, -0.44), 0.25 * u),
                 np.maximum(sd_rrect(F, *p(0.50, 0.30), 0.46 * u, 0.36 * u, 0.32 * u), F.y - (cy + 0.60 * u)))
    return union(front, subtract(back, front - 0.12 * u))


def chat(F, cx, cy, u):
    p = P(cx, cy, u)
    back = union(sd_rrect(F, *p(0.34, -0.36), 0.52 * u, 0.34 * u, 0.20 * u),
                 sd_poly(F, [p(0.56, -0.10), p(0.80, 0.14), p(0.70, -0.12)]))
    front = union(sd_rrect(F, *p(-0.16, 0.18), 0.66 * u, 0.44 * u, 0.22 * u),
                  sd_poly(F, [p(-0.60, 0.50), p(-0.82, 0.86), p(-0.30, 0.58)]))
    dots = union(*[sd_circle(F, *p(x, 0.18), 0.10 * u) for x in (-0.46, -0.16, 0.14)])
    return union(subtract(front, dots), subtract(back, front - 0.14 * u))


def gear(F, cx, cy, u):
    body = sd_circle(F, cx, cy, 0.60 * u)
    teeth = []
    for k in range(8):
        a = k * math.pi / 4
        x0, y0 = cx + 0.50 * u * math.cos(a), cy + 0.50 * u * math.sin(a)
        x1, y1 = cx + 0.80 * u * math.cos(a), cy + 0.80 * u * math.sin(a)
        teeth.append(sd_capsule(F, x0, y0, x1, y1, 0.15 * u))
    return subtract(smin(body, union(*teeth), 0.06 * u), sd_circle(F, cx, cy, 0.25 * u))


def topbar_tex(w=1024, h=232, slots=4):
    """Pill with friends / chat / settings in slots 1-3; slot 4 stays empty for the 3D menu chip."""
    F = Field(w, h, ss=4)
    pill = sd_rrect(F, w / 2, h / 2, w / 2 - 4, h / 2 - 4, h / 2 - 4)
    pad = h * 0.10
    sw = (w - 2 * pad) / slots
    u = h * 0.24
    icons = union(*[fn(F, pad + sw * (i + 0.5), h / 2, u) for i, fn in enumerate((friends, chat, gear))])
    save_rgba(os.path.join(OUT, "T_BB_TopBar.png"), F.down(F.cov(icons)), F.down(F.cov(pill)), np.zeros((h, w), np.float32))


def avatar_tex(size=512):
    """Round profile chip: a little ghost portrait, a light ring and the green 'online' dot."""
    F = Field(size, size, ss=4)
    c = size / 2
    R = size * 0.46
    disc = sd_circle(F, c, c, R)
    dot_x, dot_y, dot_r = c + R * 0.70, c + R * 0.70, R * 0.22
    dot = sd_circle(F, dot_x, dot_y, dot_r)
    cut = dot - R * 0.07
    ring = subtract(np.maximum(disc, -(disc + R * 0.08)), cut)
    u = R * 0.62
    head = sd_circle(F, c, c - u * 0.05, u * 0.60)
    body = np.maximum(sd_rrect(F, c, c + u * 0.70, u * 0.60, u * 0.80, u * 0.05), F.y - (c + R))
    ghost = smin(head, body, u * 0.08)
    eyes = union(sd_ellipse(F, c - u * 0.22, c - u * 0.08, u * 0.10, u * 0.15),
                 sd_ellipse(F, c + u * 0.22, c - u * 0.08, u * 0.10, u * 0.15))
    ghost = subtract(np.maximum(ghost, disc + R * 0.08), eyes)
    G = F.down(F.cov(subtract(disc, cut)))
    Rm = F.down(F.cov(union(ring, ghost)))
    B = F.down(F.cov(dot))
    save_rgba(os.path.join(OUT, "T_BB_Avatar.png"), Rm, G, B)


def main():
    os.makedirs(OUT, exist_ok=True)
    for n in ICONS:
        tile_tex(n)
    menu_tex()
    topbar_tex()
    avatar_tex()
    print("ui art ->", os.path.abspath(OUT))


if __name__ == "__main__":
    main()
