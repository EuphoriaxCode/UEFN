"""Render the editor shots of promo2/shots.json frame-exact (global material clock, one write per frame).
    py -3.14 render_shots.py [shot-name-prefix] [--preview] [--shots file.json]   (--preview: first + last frame only)
A shot with "roll": 90 is captured with the camera rolled and stored upright (portrait, for Shorts)."""
import base64
import json
import os
import sys

from PIL import Image

from clock import set_clock
from frames import Renderer, api, pose

HERE = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(HERE, "..", "promo2", "shots.json")
RAW = os.path.join(os.environ["TEMP"], "bb_promo2_raw")
R = Renderer()


def ease(x, kind="inout"):
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3 if kind == "out" else x * x * (3 - 2 * x)


def lerp(a, b, k):
    return [a[i] + (b[i] - a[i]) * k for i in range(3)]


def capture(path, at, look, roll):
    if not roll:
        return R.capture(path, at, look)
    p = pose(at, look)
    p["rotation"]["roll"] = float(roll)
    r, images = api.tool_images("editor", "CaptureViewport", {"captureTransform": p})
    with open(path, "wb") as f:
        f.write(base64.b64decode(images[0]["data"]))
    Image.open(path).rotate(-roll, expand=True).save(path)
    return path


def main():
    shots = sys.argv[sys.argv.index("--shots") + 1] if "--shots" in sys.argv else SHOTS
    spec = json.load(open(shots, encoding="utf-8"))
    fps = spec["fps"]
    args = [a for k, a in enumerate(sys.argv[1:], 1) if not a.startswith("--") and sys.argv[k - 1] != "--shots"]
    only = args[0] if args else None
    preview = "--preview" in sys.argv
    for sh in spec["shots"]:
        if only and not sh["name"].startswith(only):
            continue
        d = os.path.join(RAW, sh["name"])
        os.makedirs(d, exist_ok=True)
        n = sh["frames"]
        idx = [0, n - 1] if preview else range(n)
        for i in idx:
            p = os.path.join(d, f"f_{i:04d}.png")
            if os.path.exists(p) and not preview:
                continue
            k = ease(i / max(1, n - 1), sh.get("ease", "inout"))
            set_clock(1.0, sh["t"] + i / fps)
            capture(p, lerp(*sh["cam"], k), lerp(*sh["look"], k), sh.get("roll", 0))
        print("rendered", sh["name"], flush=True)
    set_clock(0.0)


if __name__ == "__main__":
    main()
