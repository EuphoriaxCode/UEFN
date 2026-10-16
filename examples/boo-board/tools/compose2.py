"""Compose the v2 promo (Euphoriax brand) from a storyboard -> MP4. Landscape and vertical (Shorts) use the same code.

    py -3.14 compose2.py [storyboard.json]                # render + encode (output path in the storyboard)
    py -3.14 compose2.py [storyboard.json] --sheet        # contact sheet, one frame per second -> %TEMP%/eupx/
    py -3.14 compose2.py [storyboard.json] --still 12.5   # one frame at 12.5 s -> %TEMP%/eupx/

Default storyboard: promo2/storyboard.json. Sources: editor shots rendered by render_shots.py (%TEMP%/bb_promo2_raw),
the in-game recording made with scripts/windows/record_window.ps1 (interpolated to the storyboard fps once and
cached), the Recordly clip (cut by source seconds, optional crop rect) and the Euphoriax brand transition (green
screen, keyed here).
"""
import hashlib
import json
import math
import os
import subprocess
import sys
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from art import FONTS
from bats import draw_swarm, swarm

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(os.environ["TEMP"], "bb_promo2_raw")
CACHE = os.path.join(os.environ["TEMP"], "eupx")
OLD_CROP = (140, 0, 1529, 781)      # first-batch shots (1529x847 viewport): drop the axis gizmo, exact 16:9
KEY = (27, 253, 28)                 # green of the brand transition
TRANS_CUT = 36                      # transition frame where the wipe fully covers the screen -> new segment starts


def _board_path():
    args = [a for a in sys.argv[1:] if a.endswith(".json")]
    p = os.environ.get("BB_STORYBOARD") or (args[0] if args else os.path.join(HERE, "..", "promo2", "storyboard.json"))
    return os.path.abspath(p)


BOARD = _board_path()
os.environ["BB_STORYBOARD"] = BOARD          # worker processes load the same storyboard
SB = json.load(open(BOARD, encoding="utf-8"))
FPS = SB["fps"]
W, H = SB.get("size", [1920, 1080])
VERT = H > W
ACCENT = tuple(SB["accent"])
TAG = os.path.splitext(os.path.basename(BOARD))[0]

F_BLACK = os.path.join(FONTS, "Montserrat-Black.otf")
F_XBOLD = os.path.join(FONTS, "Montserrat-ExtraBold.otf")
F_SEMI = os.path.join(FONTS, "Poppins-SemiBold.ttf")
F_MED = os.path.join(FONTS, "Poppins-Medium.ttf")

WHITE = (248, 248, 250)
GREY = (205, 205, 214)
INK = (14, 12, 18)


def xp(p):
    return os.path.expandvars(p.replace("%TEMP%", os.environ["TEMP"]))


def font(path, size, _c={}):
    if (path, size) not in _c:
        _c[(path, size)] = ImageFont.truetype(path, size)
    return _c[(path, size)]


def key(*parts):
    return hashlib.md5(json.dumps(parts).encode()).hexdigest()[:10]


# ------------------------------------------------------------------ cached sources
def game_dir():
    g = SB["game"]
    return os.path.join(CACHE, f"game_{key(g, W, H, FPS)}")


def build_game():
    """Re-time the PrintWindow frames with frames.txt and motion-interpolate to the storyboard fps (once)."""
    if "game" not in SB:
        return
    out = game_dir()
    if os.path.isdir(out) and os.listdir(out):
        return
    g = SB["game"]
    src = xp(g["dir"])
    t = [float(x) for x in open(os.path.join(src, "frames.txt")).read().split()]
    idx = [i for i in range(len(t)) if g["t0"] <= t[i] <= g["t1"]]
    lst = os.path.join(CACHE, f"concat_{TAG}.txt")
    with open(lst, "w") as f:
        for a, b in zip(idx, idx[1:]):
            f.write(f"file '{os.path.join(src, f'f_{a:05d}.jpg').replace(os.sep, '/')}'\nduration {t[b] - t[a]:.4f}\n")
        f.write(f"file '{os.path.join(src, f'f_{idx[-1]:05d}.jpg').replace(os.sep, '/')}'\n")
    x0, y0, x1, y1 = g["crop"]
    os.makedirs(out, exist_ok=True)
    print("interpolating in-game clip (a few minutes, once)...", flush=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-vf",
                    f"crop={x1 - x0}:{y1 - y0}:{x0}:{y0},scale={W}:{H}:flags=lanczos,"
                    f"minterpolate=fps={FPS}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1",
                    "-fps_mode", "cfr", os.path.join(out, "g_%04d.png")], check=True)


def rec_dir(s):
    p = xp(SB["recordly"])
    st = os.stat(p)
    return os.path.join(CACHE, "rec_" + key(int(st.st_mtime), st.st_size, s["t0"], s["t1"], s.get("rect"), s.get("fit"), W, H, FPS))


def build_recordly(s):
    """Cut the Recordly clip [t0, t1] (source seconds) and crop/scale it to the frame (or to a band for fit=band)."""
    d = rec_dir(s)
    if os.path.isdir(d) and os.listdir(d):
        return
    os.makedirs(d, exist_ok=True)
    if s.get("fit") == "track":                                # full-res frames + per-frame Details-panel edge
        print("cutting Recordly", s["t0"], "-", s["t1"], "(panel tracking)", flush=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(s["t0"]), "-to", str(s["t1"]), "-i", xp(SB["recordly"]),
                        "-vf", f"fps={FPS}", "-q:v", "2", os.path.join(d, "r_%04d.jpg")], check=True)
        edges = [panel_edge(Image.open(os.path.join(d, f))) for f in sorted(os.listdir(d)) if f.endswith(".jpg")]
        sm = [int(np.median(edges[max(0, k - 4):k + 5])) for k in range(len(edges))]
        json.dump(sm, open(os.path.join(d, "edges.json"), "w"))
        return
    vf = []
    if s.get("rect"):
        x0, y0, x1, y1 = s["rect"]
        vf.append(f"crop={x1 - x0}:{y1 - y0}:{x0}:{y0}")
    if s.get("fit") == "band":
        vf.append(f"scale={W}:-2:flags=lanczos")
    else:
        vf.append(f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H}")
    vf.append(f"fps={FPS}")
    print("cutting Recordly", s["t0"], "-", s["t1"], flush=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(s["t0"]), "-to", str(s["t1"]), "-i", xp(SB["recordly"]),
                    "-vf", ",".join(vf), "-q:v", "2", os.path.join(d, "r_%04d.jpg")], check=True)


def panel_edge(im):
    """x (source px) where the blue viewport ends and the grey Details panel starts."""
    sm = np.asarray(im.convert("RGB").resize((640, 360), Image.BILINEAR)).astype(np.int16)
    rows = sm[int(360 * 0.3):int(360 * 0.9)]
    blue = ((rows[..., 2] - rows[..., 0] > 25) & (rows[..., 2] > 50)).mean(axis=0)
    for x in range(96, 620):
        if blue[x:x + 20].max() < 0.2:
            return x * im.width // 640
    return im.width // 2


_EDGES = {}


def track_crop(s, i, im):
    d = rec_dir(s)
    if d not in _EDGES:
        _EDGES[d] = json.load(open(os.path.join(d, "edges.json")))
    cw = s.get("track_w", 1000)
    x0 = min(max(_EDGES[d][min(i, len(_EDGES[d]) - 1)] - 12, 0), im.width - cw)
    return im.crop((x0, 0, x0 + cw, im.height))


def trans_dir():
    return os.path.join(CACHE, f"trans_{SB['transition']['logo']}_{W}x{H}")


def build_transition():
    """Key the green-screen brand transition into RGBA frames (unmixing the green so edges stay clean)."""
    out = trans_dir()
    if os.path.isdir(out) and os.listdir(out):
        return
    tmp = os.path.join(CACHE, f"trans_src_{W}x{H}")
    os.makedirs(tmp, exist_ok=True)
    os.makedirs(out, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", xp(SB["transition"]["file"]), "-vf",
                    f"fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H}",
                    os.path.join(tmp, "t_%03d.png")], check=True)
    keyc = np.array(KEY, np.float32)
    for f in sorted(os.listdir(tmp)):
        a = np.asarray(Image.open(os.path.join(tmp, f)).convert("RGB")).astype(np.float32)
        spill = a[..., 1] - np.maximum(a[..., 0], a[..., 2])
        al = 1.0 - np.clip(spill / (KEY[1] - max(KEY[0], KEY[2])), 0, 1)
        al[al < 0.03] = 0.0
        al[al > 0.97] = 1.0
        fg = np.clip((a - (1 - al[..., None]) * keyc) / np.maximum(al[..., None], 1e-3), 0, 255)
        if SB["transition"]["logo"] == "white":
            fg[:] = 255.0                                     # white emblem + white wipe
        Image.fromarray(np.dstack([fg, al * 255]).astype(np.uint8), "RGBA").save(os.path.join(out, f), compress_level=1)


# ------------------------------------------------------------------ timeline
def src_count(s):
    if s["src"] == "game":
        return len(os.listdir(game_dir()))
    if s["src"] == "recordly":
        return len([f for f in os.listdir(rec_dir(s)) if f.endswith(".jpg")])
    if s["src"].startswith("shot:"):
        return len(os.listdir(os.path.join(RAW, s["src"][5:])))
    return 10 ** 6


def seg_len(s):
    if "len" in s:
        return s["len"]
    end = min(s.get("out", 10 ** 6), src_count(s) - 1)
    return int((end - s.get("in", 0)) / s.get("speed", 1.0)) + 1


def timeline():
    segs, events, pos = [], [], 0
    for k, s in enumerate(SB["segments"]):
        n = seg_len(s)
        join = s.get("join", "cut") if k else "cut"
        xin = int(join.split(":")[1]) if join.startswith("xfade") else 0
        start = pos - xin
        if join == "euphoriax":
            events.append(pos - TRANS_CUT)
            if segs:                                  # captions leave before the emblem flies in
                segs[-1]["cap"] = (segs[-1]["n"] - TRANS_CUT + 6) / FPS
        segs.append({"s": s, "start": start, "n": n, "xin": xin})
        pos = start + n
    return segs, events, pos


# ------------------------------------------------------------------ drawing helpers
def ease(x):
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


def env(t, at, d=0.25):
    t0, t1 = at
    if t < t0 or t > t1:
        return 0.0
    return min(1.0, (t - t0) / d if t0 > 0.01 else 1.0, (t1 - t) / d)


def rgba(c, a):
    return tuple(c) + (int(255 * max(0.0, min(1.0, a))),)


def faded(img, a):
    if a >= 0.999:
        return img
    arr = np.asarray(img).copy()
    arr[..., 3] = (arr[..., 3] * a).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def shadow_text(layer, xy, s, f, fill, a, anchor="ls", blur=6, strength=0.75):
    """Text with a soft drop shadow (no boxes, no outlines)."""
    if a <= 0:
        return
    sh = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((xy[0], xy[1] + 4), s, font=f, fill=(0, 0, 0, int(255 * strength * a)), anchor=anchor)
    layer.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)))
    ImageDraw.Draw(layer).text(xy, s, font=f, fill=rgba(fill, a), anchor=anchor)


def wrap(s, f, width):
    words, lines, cur = s.split(), [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if f.getlength(t) <= width or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w_
    return lines + [cur]


_LOGO = {}


def logo(color, height):
    k = (color, height)
    if k not in _LOGO:
        im = Image.open(SB["logo_white" if color == "white" else "logo_black"]).convert("RGBA")
        im = im.crop(im.getbbox())
        _LOGO[k] = im.resize((round(im.width * height / im.height), height), Image.LANCZOS)
    return _LOGO[k]


_GRAD = {}


def grad(edge, size, strength):
    """Soft dark gradient from the top or bottom edge so white text reads on any footage."""
    k = (edge, size, strength)
    if k not in _GRAD:
        r = np.clip(1 - np.arange(size, dtype=np.float32) / size, 0, 1) ** 1.6 * strength
        col = r if edge == "top" else r[::-1]
        arr = np.zeros((size, W, 4), np.uint8)
        arr[..., :3] = (6, 4, 12)
        arr[..., 3] = (col[:, None] * 255).astype(np.uint8)
        _GRAD[k] = Image.fromarray(arr, "RGBA")
    return _GRAD[k]


def put_grad(layer, edge, size, strength, a):
    g = faded(grad(edge, size, strength), a)
    layer.alpha_composite(g, (0, 0 if edge == "top" else H - size))


# ------------------------------------------------------------------ overlays
def ov_hook(layer, o, t, a):
    """Big two-line hook, fully readable from the very first frame."""
    put_grad(layer, "top", 620 if VERT else 360, 0.7, a)
    f1 = font(F_BLACK, o.get("size", 104 if VERT else 98))
    f2 = f1
    lines = [ln for part in o["line1"].splitlines() for ln in wrap(part, f1, W - 120)]   # "\n" = forced break
    y = (330 if VERT else 150) + 4 * (1 - ease(t / 0.2))
    for ln in lines:
        shadow_text(layer, (W // 2, y), ln, f1, WHITE, a, anchor="ms")
        y += f1.size * 1.05
    if o.get("line2"):
        e = ease((t - o.get("line2_at", 0.45)) / 0.18)
        shadow_text(layer, (W // 2, y + 6 + (1 - e) * 14), o["line2"], f2, ACCENT, a * e, anchor="ms")


def ov_caption(layer, o, t, a):
    """One clean caption: name of what you see. Bottom-left (landscape) or upper third (vertical)."""
    e = ease((t - o["_t0"]) / 0.35)
    fb = font(F_XBOLD, 70 if VERT else 60)
    if VERT:
        put_grad(layer, "top", 560, 0.55, a)
        y = 300 + (1 - e) * 18
        for ln in wrap(o["text"], fb, W - 140):
            shadow_text(layer, (W // 2, y), ln, fb, WHITE, a, anchor="ms")
            y += fb.size * 1.1
        if o.get("sub"):
            shadow_text(layer, (W // 2, y + 4), o["sub"], font(F_MED, 40), GREY, a * e, anchor="ms")
    else:
        put_grad(layer, "bottom", 300, 0.6, a)
        y = H - (118 if o.get("sub") else 84) + (1 - e) * 14
        shadow_text(layer, (96, y), o["text"], fb, WHITE, a)
        if o.get("sub"):
            shadow_text(layer, (98, y + 52), o["sub"], font(F_MED, 34), GREY, a * e)


def ov_guide(layer, o, t, a):
    """Tutorial subtitle over the Recordly clip: white text on a dark rounded box."""
    f = font(F_SEMI, 56 if VERT else 46)
    lines = wrap(o["text"], f, W - (160 if VERT else 400))
    lh = int(f.size * 1.25)
    bw = max(f.getlength(ln) for ln in lines) + 2 * 34
    bh = lh * len(lines) + 2 * 22
    cy = (300 if VERT else H - 120) + (1 - ease((t - o["_t0"]) / 0.3)) * 10
    x0, y0 = (W - bw) / 2, cy - bh / 2
    box = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(box)
    d.rounded_rectangle((x0, y0, x0 + bw, y0 + bh), radius=18, fill=(10, 8, 16, int(215 * a)))
    for i, ln in enumerate(lines):
        d.text((W / 2, y0 + 22 + lh * i + lh * 0.78), ln, font=f, fill=rgba(WHITE, a), anchor="ms")
    layer.alpha_composite(box)


def ov_heading(layer, o, t, a):
    """Section heading at the top centre, e.g. "The different mounts"."""
    put_grad(layer, "top", 300, 0.6, a)
    f = font(F_XBOLD, 72 if VERT else 64)
    y = (300 if VERT else 118) + (1 - ease((t - o["_t0"]) / 0.35)) * 12
    for ln in wrap(o["text"], f, W - 140):
        shadow_text(layer, (W // 2, y), ln, f, WHITE, a, anchor="ms")
        y += f.size * 1.1


def ov_title(layer, o, t, a):
    cx, cy = W // 2, H // 2
    e1, e2 = ease((t - o["_t0"]) / 0.5), ease((t - o["_t0"] - 0.25) / 0.5)
    shadow_text(layer, (cx, cy + 40 + (1 - e1) * 24), o["title"], font(F_BLACK, 124 if VERT else 168), WHITE, a * e1, anchor="ms")
    for i, ln in enumerate(wrap(o["sub"], font(F_MED, 40), W - 160)):
        shadow_text(layer, (cx, cy + 120 + 52 * i + (1 - e2) * 16), ln, font(F_MED, 40), GREY, a * e2, anchor="ms")


def ov_free(layer, o, t, a):
    layer.alpha_composite(Image.new("RGBA", (W, H), rgba((6, 4, 12), a * 0.45)))
    cx, cy = W // 2, H // 2
    e1, e2 = ease((t - o["_t0"]) / 0.5), ease((t - o["_t0"] - 0.3) / 0.5)
    fb = font(F_BLACK, o.get("size", 230 if VERT else 250))
    shadow_text(layer, (cx, cy + 40 + (1 - e1) * 30), o["big"], fb, WHITE, a * e1, anchor="ms")
    for i, ln in enumerate(wrap(o["line"], font(F_SEMI, 48), W - 160)):
        shadow_text(layer, (cx, cy + 140 + 62 * i + (1 - e2) * 16), ln, font(F_SEMI, 48), ACCENT, a * e2, anchor="ms")


def ov_endcard(layer, o, t, a):
    d = ImageDraw.Draw(layer)
    cx = W // 2
    e1, e2 = ease((t - 0.15) / 0.7), ease((t - 0.45) / 0.7)
    lg = logo("black", 300)
    top = H // 2 - 290
    layer.alpha_composite(faded(lg, a * e1), (cx - lg.width // 2, int(top + (1 - e1) * 30)))
    f = font(F_BLACK, 64)
    s, track = o["name"], 14
    ws = [f.getlength(c) for c in s]
    x = cx - (sum(ws) + track * (len(s) - 1)) / 2
    y = top + 450 + (1 - e2) * 20
    for c, w_ in zip(s, ws):
        d.text((x, y), c, font=f, fill=rgba(INK, a * e2), anchor="ls")
        x += w_ + track
    for i, ln in enumerate(wrap(o["line"], font(F_MED, 32), W - 160)):
        d.text((cx, y + 60 + 44 * i), ln, font=font(F_MED, 32), fill=rgba((96, 96, 104), a * e2), anchor="ms")


OVERLAYS = {"hook": ov_hook, "caption": ov_caption, "guide": ov_guide, "heading": ov_heading, "title": ov_title,
            "free": ov_free, "endcard": ov_endcard}


def draw_overlays(layer, items, t, dur, cap=1e9):
    for o in items:
        at = o.get("at", [0.12, dur - 0.12])
        at = [at[0], min(at[1], cap)]
        a = env(t, at)
        if a > 0:
            OVERLAYS[o["kind"]](layer, dict(o, _t0=at[0]), t, a)


# ------------------------------------------------------------------ frames
def load_shot(name, i, s):
    im = Image.open(os.path.join(RAW, name, f"f_{i:04d}.png")).convert("RGB")
    if s.get("crop"):
        im = im.crop(tuple(s["crop"]))
    elif im.size == (1529, 847):
        im = im.crop(OLD_CROP)
    else:                                                     # centre crop to the output aspect
        w, h = im.size
        if w / h > W / H:
            cw = round(h * W / H)
            im = im.crop(((w - cw) // 2, 0, (w - cw) // 2 + cw, h))
        else:
            ch = round(w * H / W)
            im = im.crop((0, (h - ch) // 2, w, (h - ch) // 2 + ch))
    return im.resize((W, H), Image.LANCZOS)


def base(seg, local):
    s = seg["s"]
    src = s["src"]
    if src in ("black", "white"):
        return Image.new("RGB", (W, H), (0, 0, 0) if src == "black" else (255, 255, 255))
    i = min(s.get("in", 0) + int(round(local * s.get("speed", 1.0))), src_count(s) - 1)
    if src.startswith("shot:"):
        im = load_shot(src[5:], i, s)
    elif src == "game":
        im = Image.open(os.path.join(game_dir(), f"g_{i + 1:04d}.png")).convert("RGB")
    else:
        im = Image.open(os.path.join(rec_dir(s), f"r_{i + 1:04d}.jpg")).convert("RGB")
        if s.get("fit") == "track":
            im = track_crop(s, i, im)
            im = im.resize((W, round(im.height * W / im.width)), Image.LANCZOS)
        if s.get("fit") in ("band", "track"):                 # sharp band on a blurred copy of itself
            bg = im.resize((W // 6, H // 6), Image.BILINEAR, box=((im.width - im.height * W / H) / 2, 0,
                                                                  (im.width + im.height * W / H) / 2, im.height))
            bg = bg.filter(ImageFilter.GaussianBlur(6)).resize((W, H), Image.BICUBIC)
            bg = Image.blend(bg, Image.new("RGB", (W, H), (6, 4, 12)), 0.45)
            bg.paste(im, (0, (H - im.height) // 2 + s.get("band_dy", 0)))
            im = bg
    if "zoom" in s:
        z0, z1 = s["zoom"]
        z = z0 + (z1 - z0) * (local / max(1, seg["n"] - 1))
        cw, ch = W / z, H / z
        fx, fy = s.get("focus", [0.5, 0.5])
        x0 = min(max(fx * W - cw / 2, 0), W - cw)
        y0 = min(max(fy * H - ch / 2, 0), H - ch)
        im = im.resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + cw, y0 + ch))
    if s.get("blur"):
        small = im.resize((W // 4, H // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(s["blur"] / 4))
        im = small.resize((W, H), Image.BICUBIC)
    if s.get("dim"):
        im = Image.blend(im, Image.new("RGB", (W, H), (6, 4, 12)), s["dim"])
    return im


def seg_frame(seg, local):
    img = base(seg, local).convert("RGBA")
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_overlays(lay, seg["s"].get("text", []), local / FPS, seg["n"] / FPS, seg.get("cap", 1e9))
    if seg["s"].get("watermark", SB.get("watermark", True)):
        lg = logo("white", 46)
        lay.alpha_composite(faded(lg, 0.5), (W - 72 - lg.width, (H - 64 - lg.height) if not VERT else 120))
    img.alpha_composite(lay)
    return img


SEGS, EVENTS, TOTAL, SWARMS, SPANNED = [], [], 0, [], []


def init():
    """Build the timeline (needs the cached sources, so it runs after prepare() and in every worker)."""
    global SEGS, EVENTS, TOTAL, SWARMS, SPANNED
    SEGS, EVENTS, TOTAL = timeline()
    ids = {sg["s"].get("id"): sg for sg in SEGS}
    SPANNED = []
    for o in SB.get("overlays", []):                  # "span": [first_id, last_id] -> seconds on the timeline
        if "span" in o:
            a, b = ids[o["span"][0]], ids[o["span"][1]]
            o = dict(o, at=[(a["start"] + a["xin"]) / FPS + 0.1, (b["start"] + b["n"]) / FPS - 0.15])
        SPANNED.append(o)
    SWARMS = [swarm({"count": 16, "seed": 11 + k, "start": e + 12, "frames": 34 if not VERT else 40, "spread": 14,
                     "from": "left" if k % 2 == 0 else "right", "size": [26, 86] if not VERT else [30, 96]}, W, H)
              for k, e in enumerate(EVENTS)]


_TR = {}


def trans_frame(i):
    if i not in _TR:
        fs = sorted(os.listdir(trans_dir()))
        _TR[i] = Image.open(os.path.join(trans_dir(), fs[i])).convert("RGBA") if 0 <= i < len(fs) else None
    return _TR[i]


_DARK = None


def darken(a):
    global _DARK
    if _DARK is None:
        y, x = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.hypot((x - W / 2) / (900 if not VERT else 700), (y - H / 2) / (560 if not VERT else 800))
        arr = np.zeros((H, W, 4), np.uint8)
        arr[..., :3] = (4, 2, 8)
        arr[..., 3] = (np.clip(1.15 - d, 0, 1) * 255).astype(np.uint8)
        _DARK = Image.fromarray(arr, "RGBA")
    return faded(_DARK, a)


def render(f):
    parts = []
    for seg in SEGS:
        local = f - seg["start"]
        if 0 <= local < seg["n"]:
            w = (local + 1) / (seg["xin"] + 1) if local < seg["xin"] else 1.0
            parts.append([seg, local, w])
    if len(parts) == 2:                                    # crossfade: earlier segment gets the remainder
        parts[0][2] = 1.0 - parts[1][2]
    acc = None
    for seg, local, w in parts:
        arr = np.asarray(seg_frame(seg, local).convert("RGB")).astype(np.float32) * w
        acc = arr if acc is None else acc + arr
    out = Image.fromarray(np.clip(acc, 0, 255).astype(np.uint8)).convert("RGBA")
    if SPANNED:                                            # storyboard-wide overlays (hook, section headings)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw_overlays(lay, SPANNED, f / FPS, TOTAL / FPS)
        out.alpha_composite(lay)
    for k, e in enumerate(EVENTS):
        i = f - e
        if 2 <= i <= TRANS_CUT and SB["transition"].get("darken"):   # dark halo so the white emblem reads
            out.alpha_composite(darken(SB["transition"]["darken"] * min(1.0, (i - 2) / 8)))
        tr = trans_frame(i)
        if tr is not None:
            out.alpha_composite(tr)
        draw_swarm(out, SWARMS[k], f, FPS)
    g = min(1.0, (f + 1) / max(1, SB.get("fade_in", 0)), (TOTAL - f) / max(1, SB["fade_out"]))
    rgb = out.convert("RGB")
    if g < 1.0:
        rgb = Image.fromarray((np.asarray(rgb).astype(np.float32) * g).astype(np.uint8))
    return rgb


def render_bytes(f):
    return render(f).tobytes()


def prepare():
    os.makedirs(CACHE, exist_ok=True)
    build_game()
    for s in SB["segments"]:
        if s["src"] == "recordly":
            build_recordly(s)
    build_transition()
    init()


def main():
    prepare()
    workers = min(12, os.cpu_count() or 4)
    if "--still" in sys.argv:
        f = int(float(sys.argv[sys.argv.index("--still") + 1]) * FPS)
        p = os.path.join(CACHE, f"still_{TAG}.png")
        render(f).save(p)
        print(p)
        return
    if "--sheet" in sys.argv:
        fr = list(range(FPS // 2, TOTAL, FPS))
        cols = 6 if not VERT else 10
        tw, th = (384, 216) if not VERT else (216, 384)
        sheet = Image.new("RGB", (cols * tw, ((len(fr) + cols - 1) // cols) * th))
        with Pool(workers, initializer=init) as pool:
            for n, im in enumerate(pool.imap(render, fr)):
                im = im.resize((tw, th), Image.LANCZOS)
                ImageDraw.Draw(im).text((6, 4), f"{fr[n] / FPS:.1f}s", fill=(255, 255, 0))
                sheet.paste(im, ((n % cols) * tw, (n // cols) * th))
        p = os.path.join(CACHE, f"sheet_{TAG}.png")
        sheet.save(p)
        print(p, f"{TOTAL / FPS:.1f}s")
        return
    out = xp(SB["output"])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "16",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    with Pool(workers, initializer=init) as pool:
        for n, b in enumerate(pool.imap(render_bytes, range(TOTAL), chunksize=2)):
            enc.stdin.write(b)
            if n % 300 == 0:
                print("frame", n, "/", TOTAL, flush=True)
    enc.stdin.close()
    enc.wait()
    print("wrote", out, f"{TOTAL / FPS:.1f}s")
    import sfx                                               # edit sound effects on top
    sfx.add(BOARD)


if __name__ == "__main__":
    main()
