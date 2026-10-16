"""Vector bat silhouettes with flapping wings, for the promo transitions (drawn, not AI art).

    swarm(cfg, w, h)  -> list of flight paths
    draw_swarm(layer, paths, frame)  draws every bat that is on screen at `frame` onto an RGBA layer
"""
import math
import random

from PIL import Image, ImageDraw

SS = 2                      # supersampling for clean edges


def _quad(p0, c, p1, n=8):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t * t * p1[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t * t * p1[1]) for t in (k / n for k in range(1, n + 1))]


def _scallop(p0, p1, pull, k=0.30):
    """Concave wing-membrane edge from p0 to p1, bowed toward `pull`."""
    mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
    dx, dy = pull[0] - mx, pull[1] - my
    d = math.hypot(dx, dy) or 1.0
    seg = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    return _quad(p0, (mx + dx / d * seg * k, my + dy / d * seg * k), p1)


def bat_shape(phase):
    """Polygon (unit half-span, y down) of one bat at flap phase (radians); 0 = wings level going up."""
    a = math.sin(phase)                         # +1 wings up, -1 wings down
    squash = 1.0 - 0.16 * abs(a)                # foreshortening at the ends of the stroke
    shoulder = (0.10, -0.05)
    wrist = (0.44 * squash, -0.30 - 0.30 * a)
    tip1 = (1.00 * squash, -0.16 - 0.66 * a)
    tip2 = (0.80 * squash, 0.10 - 0.44 * a)
    tip3 = (0.55 * squash, 0.22 - 0.24 * a)
    hip = (0.12, 0.20)
    right = [shoulder] + _quad(shoulder, (0.26 * squash, -0.26 - 0.2 * a), wrist, 6) + \
        _quad(wrist, ((wrist[0] + tip1[0]) / 2, min(wrist[1], tip1[1]) - 0.04), tip1, 6) + \
        _scallop(tip1, tip2, wrist) + _scallop(tip2, tip3, wrist) + _scallop(tip3, hip, wrist, 0.22)
    belly = [(0.11 * math.cos(t), 0.06 + 0.21 * math.sin(t)) for t in (0.8 + (math.pi / 2 - 0.8) * k / 5 for k in range(6))]
    ear = [(0.0, -0.22), (0.035, -0.235), (0.085, -0.37), (0.105, -0.16)]
    half = ear + right + belly + [(0.0, 0.30)]     # right half, top centre -> tail, clockwise
    return half + [(-x, y) for x, y in reversed(half)]


def swarm(cfg, w, h):
    """Deterministic flight paths. cfg: {count, seed, start, frames, size:[min,max], from:'left'|'right'}."""
    rnd = random.Random(cfg.get("seed", 7))
    out = []
    n = cfg.get("count", 14)
    lo, hi = cfg.get("size", [26, 86])
    for i in range(n):
        depth = rnd.random()                                     # 0 far .. 1 near
        size = lo + (hi - lo) * depth ** 1.6
        dur = cfg.get("frames", 34) * (1.25 - 0.5 * depth) * rnd.uniform(0.9, 1.1)
        t0 = cfg.get("start", 0) + rnd.uniform(0, cfg.get("spread", 16))
        y0 = h * rnd.uniform(0.55, 1.15)
        y1 = y0 - h * rnd.uniform(0.55, 1.05)
        p0 = (-size * 2 - rnd.uniform(0, w * 0.15), y0)
        p1 = (w + size * 2 + rnd.uniform(0, w * 0.15), y1)
        if cfg.get("from", "left") == "right":
            p0, p1 = (w - p0[0], p0[1]), (w - p1[0], p1[1])
        out.append({"t0": t0, "dur": dur, "p0": p0, "p1": p1, "size": size, "depth": depth,
                    "flap": rnd.uniform(4.2, 6.0) * (1.15 - 0.3 * depth), "ph": rnd.uniform(0, 6.28),
                    "bob": rnd.uniform(6, 22), "bobf": rnd.uniform(1.2, 2.2), "arc": rnd.uniform(-0.12, 0.12)})
    out.sort(key=lambda b: b["depth"])                            # far bats first
    return out


def draw_swarm(layer, paths, frame, fps=30, color=(12, 7, 18)):
    w, h = layer.size
    mask = None
    for b in paths:
        u = (frame - b["t0"]) / b["dur"]
        if u < 0 or u > 1:
            continue
        if mask is None:
            mask = Image.new("L", (w * SS, h * SS), 0)
            d = ImageDraw.Draw(mask)
        x = b["p0"][0] + (b["p1"][0] - b["p0"][0]) * u
        y = b["p0"][1] + (b["p1"][1] - b["p0"][1]) * u + math.sin(u * math.pi) * b["arc"] * h
        tsec = frame / fps
        y += math.sin(tsec * b["bobf"] * 6.283 + b["ph"]) * b["bob"]
        phase = tsec * b["flap"] * 6.283 + b["ph"]
        y -= math.sin(phase) * b["size"] * 0.08                   # body lifts on the down-stroke
        ang = math.atan2(b["p1"][1] - b["p0"][1], b["p1"][0] - b["p0"][0]) * 0.35
        ca, sa = math.cos(ang), math.sin(ang)
        s = b["size"]
        pts = [((x + (px * ca - py * sa) * s) * SS, (y + (px * sa + py * ca) * s) * SS) for px, py in bat_shape(phase)]
        shade = int(255 * (0.78 + 0.22 * b["depth"]))             # far bats slightly see-through
        d.polygon(pts, fill=shade)
    if mask is None:
        return
    mask = mask.resize((w, h), Image.LANCZOS)
    layer.alpha_composite(Image.merge("RGBA", (*[Image.new("L", (w, h), c) for c in color], mask)))
