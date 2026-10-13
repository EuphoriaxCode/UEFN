"""Boo Board promo video: frame-exact editor renders + composited titles.

    py -3.14 promo.py render [shot]     # raw frames (resumable; ~1.8 s per frame)
    py -3.14 promo.py compose           # titles + encode -> examples/boo-board/promo/boo_board_promo.mp4

Needs the editor preview row (preview_row.py), the night Day Sequence settings and FreezeTime=1 on the MIs
(Renderer.freeze). Run `py -3.14 promo.py unfreeze` afterwards so editor-placed boards animate again.
"""
import math
import os
import re
import subprocess
import sys

import board as B
from frames import MIS, Renderer

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(os.environ["TEMP"], "bb_promo_raw")
FINAL = os.path.join(os.environ["TEMP"], "bb_promo_final")
OUT = os.path.abspath(os.path.join(HERE, "..", "promo"))
FPS = 30

ROW_X = -2000.0
ROW_Y = {"Arch": 1500.0, "Post": 2900.0, "Spider": 4300.0, "Float": 5700.0}
HANG = 70.0
BOARD_TOP = B.BEAM_Z - B.HOOK_DROP - HANG + abs(B.top_z(B.HOOK_S))      # arch / post boards
OPEN_MID = BOARD_TOP - (B.H0 + B.EXT) / 2


# ------------------------------------------------------------------ styles (parsed from the Verse device = one source)
def palettes():
    src = open(os.path.join(HERE, "..", "verse", "boo_board_device.verse"), encoding="utf-8").read()
    out = {}
    for m in re.finditer(r"(boo_style\.(\w+)|_) => boo_palette:\n((?:\s+\w+ := Col\([^)]*\)\n)+)", src):
        name = m.group(2) or "PumpkinNight"
        out[name] = {k: [float(x) for x in v.split(",")] for k, v in re.findall(r"(\w+) := Col\(([^)]*)\)", m.group(3))}
    return out


def style_sets(p):
    dim = lambda c, k: [x * k for x in c]
    return [
        ("Housing", {"ColorTop": p["BoardTop"], "ColorBottom": p["BoardBottom"], "RimColor": p["Rim"]}),
        ("Trim", {"Emissive": p["Trim"], "ColorTop": dim(p["Trim"], 0.08), "ColorBottom": dim(p["Trim"], 0.08)}),
        ("Divider", {"Emissive": p["Divider"]}),
        ("Header", {"FillColor": p["HeaderText"], "OutlineColor": p["HeaderOutline"], "AccentColor": p["HeaderAccent"]}),
        ("Thanks", {"FillColor": p["ThanksText"], "OutlineColor": p["ThanksOutline"], "AccentColor": p["ThanksAccent"]}),
        ("Ghost", {"GlowColor": p["GhostGlow"]}),
        ("Pumpkins", {"Color": p["Pumpkin"]}),
        ("Wood", {"Color": p["Wood"]}),
        ("Metal", {"Color": p["Metal"]}),
        ("Glow", {"Emissive": p["Glow"]}),
    ]


# ------------------------------------------------------------------ camera helpers
def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def lerp3(a, b, k):
    return tuple(a[i] + (b[i] - a[i]) * k for i in range(3))


def board_cam(y, dist, height, look_z, side=0.0):
    return (ROW_X + dist, y + side, height), (ROW_X, y, look_z)


# ------------------------------------------------------------------ shots
STYLE_ORDER = ["PumpkinNight", "GhostlyMint", "WitchBrew", "BloodMoon", "CandyPop"]


def shots():
    y = ROW_Y["Arch"]
    S = []
    # 1 hero: one full loop on the Graveyard Arch, slow push-in (title over the first seconds)
    a0, l0 = board_cam(y, 1150.0, 240.0, 330.0, side=-140.0)
    a1, l1 = board_cam(y, 640.0, 300.0, 300.0, side=30.0)
    def hero_cam(i):
        at = lerp3(a0, a1, ease(i / 329))
        lk = lerp3(l0, l1, ease(i / 329))
        k = 1.0 - ease((i - 80) / 75.0)          # board sits on the right while the title is up, then centres
        return at, (lk[0], lk[1] + 430.0 * k, lk[2])
    S.append(dict(name="hero", n=330, t=lambda i: i / FPS, cam=hero_cam))
    # 2 close-up on the menu + tiles while the ghost presses them
    c0, cl0 = (ROW_X + 560.0, y - 70.0, OPEN_MID + 120.0), (ROW_X, y, OPEN_MID + 70.0)
    c1, cl1 = (ROW_X + 500.0, y + 50.0, OPEN_MID + 70.0), (ROW_X, y, OPEN_MID + 10.0)
    S.append(dict(name="close", n=180, t=lambda i: 1.2 + i / FPS,
                  cam=lambda i: (lerp3(c0, c1, ease(i / 179)), lerp3(cl0, cl1, ease(i / 179)))))
    # 3 styles: 5 x 36 frames, same framing, slow drift
    for k, st in enumerate(STYLE_ORDER):
        d0, dl0 = board_cam(y, 600.0, 300.0, OPEN_MID + 20, side=-50.0 + 20 * k)
        d1, dl1 = board_cam(y, 585.0, 300.0, OPEN_MID + 20, side=-30.0 + 20 * k)
        S.append(dict(name=f"style{k}", n=36, style=st, t=lambda i: 4.25 + i / FPS,
                      cam=lambda i, d0=d0, d1=d1, dl0=dl0, dl1=dl1: (lerp3(d0, d1, i / 35), lerp3(dl0, dl1, i / 35))))
    # 4 mounts: 4 x 45 frames
    mounts = [("Arch", BOARD_TOP), ("Post", BOARD_TOP), ("Spider", B.FLOAT_TOP), ("Float", B.FLOAT_TOP)]
    for k, (m, top) in enumerate(mounts):
        yy = ROW_Y[m]
        mid = top - (B.H0 + B.EXT) / 2
        e0 = (ROW_X + 860.0, yy - 170.0, 230.0)
        e1 = (ROW_X + 790.0, yy - 70.0, 250.0)
        lk = (ROW_X, yy, 290.0 if m in ("Arch", "Post") else 250.0)
        S.append(dict(name=f"mount{k}", n=45, bob=(12.0 if m == "Float" else 0.0), t=lambda i: 6.6 + i / FPS,
                      cam=lambda i, e0=e0, e1=e1, lk=lk: (lerp3(e0, e1, i / 44), lk)))
    # 5 options card: board on the right of the frame, slow orbit
    S.append(dict(name="options", n=180, t=lambda i: 2.6 + i / FPS,
                  cam=lambda i: ((ROW_X + 760.0 * math.cos(math.radians(-28 + 10 * i / 179)),
                                  y + 760.0 * math.sin(math.radians(-28 + 10 * i / 179)) - 300.0, 300.0),
                                 (ROW_X, y - 300.0, OPEN_MID + 40.0))))
    # 6 outro: pull back while the thanks plays
    o0, ol0 = board_cam(y, 650.0, 300.0, 300.0)
    o1, ol1 = board_cam(y, 1250.0, 260.0, 350.0)
    S.append(dict(name="outro", n=120, t=lambda i: 6.7 + i / FPS,
                  cam=lambda i: (lerp3(o0, o1, ease(i / 119)), lerp3(ol0, ol1, ease(i / 119)))))
    return S


def render(only=None):
    R = Renderer()
    R.freeze(True)
    pals = palettes()
    current_style, current_bob = None, None
    for sh in shots():
        if only and not sh["name"].startswith(only):
            continue
        st = sh.get("style", "PumpkinNight")
        if st != current_style:
            R.set_params(style_sets(pals[st]))
            current_style = st
        bob = sh.get("bob", 0.0)
        if bob != current_bob:
            R.set_params([(n, {"BobHeight": bob}) for n in MIS if n not in ("Wood", "Metal", "Glow", "Chain", "Silk", "Spider", "SpiderEyes")])
            current_bob = bob
        d = os.path.join(RAW, sh["name"])
        os.makedirs(d, exist_ok=True)
        for i in range(sh["n"]):
            p = os.path.join(d, f"f_{i:04d}.png")
            if os.path.exists(p):
                continue
            at, look = sh["cam"](i)
            R.frame(p, sh["t"](i), at, look)
        print("rendered", sh["name"], flush=True)
    R.set_params(style_sets(pals["PumpkinNight"]))


def unfreeze():
    R = Renderer()
    R.freeze(False)
    R.set_params([(n, {"BobHeight": 0.0}) for n in MIS])


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "render"
    if cmd == "render":
        render(sys.argv[2] if len(sys.argv) > 2 else None)
    elif cmd == "unfreeze":
        unfreeze()
    elif cmd == "compose":
        import compose
        compose.main()
