"""Editor mirror of every placed boo_board_device: builds the same board + mount the device spawns in game, as
editor entities, so the boards are VISIBLE in UEFN (and renderable frame-exact).

Per-entity slot materials (assetForEditor) don't show in the editor viewport here (42.30), so every board gets its own
COPY of the meshes with its material instances as the mesh defaults. Everything lives in /BooPromo (never in the
BooBoard release folder).

    py -3.14 mirror.py build      # read all devices, (re)build MIs, mesh copies and the "BooMirror" entities
    py -3.14 mirror.py build --skip-mis --row   # promo row: the 5 boards on y = 1289 at x = 1866 + 700k, y = -2700
    py -3.14 mirror.py remove     # delete the mirror entities
    py -3.14 mirror.py hide 1|0   # hide/show the real device actors in the editor (they are only markers)

Keep this in sync with verse/boo_board_device.verse (Build / *Mat functions).
"""
import json
import math
import os
import re
import subprocess
import sys

import board as B
from promo import palettes

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "cli"))
from uefncli import api, sg  # noqa: E402

ROOT = "/176d0aa3-082b-479b-b3f0-d5ac722fe133"
MATS = ROOT + "/BooBoard/BB_Materials"
PROMO = ROOT + "/BooPromo"
MIRROR = PROMO + "/Materials"
PMESH = PROMO + "/Meshes"
TEX = ROOT + "/BooBoard/BB_Textures"
M = "BooPromo-Meshes-"
SRC = ROOT + "/BooBoard/BB_Meshes"
PROPS = ["Style", "Headline", "ThanksMessage", "BoardScale", "AnimationSpeed", "SyncAllBoards", "Mount", "HangLength",
         "SwayAmount", "FloatHeight", "DistanceFromDevice", "ShowGhost", "ShowBats", "ShowPumpkins", "ShowCandyRain",
         "ShowBursts", "UseCustomColors", "BoardColor", "TrimColor", "TextColor", "LikeColor", "SaveColor",
         "FollowColor", "GhostGlowColor", "MountColor"]
HEADLINES = {"EnjoyingTheMap": 0, "HavingFun": 1, "HappyHalloween": 2, "SupportThisMap": 3, "SpookyGoodTime": 4}
THANKS = {"ThanksBoo": 0, "ThankYou": 1, "YouRock": 2, "Spooktacular": 3, "StaySpooky": 4}
LAV = [0.80, 0.76, 1.0]
INK = [0.012, 0.012, 0.025]
PILL = [0.03, 0.034, 0.062]


def tref(name):
    return f"{TEX}/{name}.{name}"


def devices():
    out = subprocess.run([sys.executable, os.path.join(REPO, "cli", "uefn.py"), "device", "placed"],
                         capture_output=True, text=True, encoding="utf-8").stdout
    res = []
    for line in out.splitlines():
        if line.startswith("BooBoard-boo") and "VerseDevice_C" in line:
            ref = line.split()[-1]
            props = api.tool("device", "GetDeviceProperties", {"device": {"refPath": ref}, "propertyNames": PROPS})
            props = json.loads(props) if isinstance(props, str) else props
            xf = api.tool("actor", "get_actor_transform", {"actor": {"refPath": ref}})
            res.append({"label": line[:46].strip(), "ref": ref, "props": props, "xf": xf})
    res.sort(key=lambda d: (d["xf"]["location"]["x"], d["xf"]["location"]["y"]))
    return res


def col(c):
    if isinstance(c, dict):
        return [float(c.get("R", c.get("r", 0))), float(c.get("G", c.get("g", 0))), float(c.get("B", c.get("b", 0)))]
    return list(c)


def dim(c, k):
    return [x * k for x in c]


def bright(c, k):
    return [min(1.0, x * k) for x in c]


def palette(p):
    pal = palettes()[p.get("Style", "PumpkinNight")]
    if not p.get("UseCustomColors"):
        return pal
    bc, tc, tx = col(p["BoardColor"]), col(p["TrimColor"]), col(p["TextColor"])
    return dict(pal, BoardTop=bc, BoardBottom=dim(bc, 0.3), Rim=bright(bc, 4.0), Trim=tc, Divider=tc, HeaderText=tx,
                HeaderOutline=dim(tc, 0.35), HeaderAccent=col(p["SaveColor"]), ThanksText=tx, ThanksOutline=dim(bc, 2.0),
                ThanksAccent=col(p["FollowColor"]), ButtonIdle=bright(bc, 1.6), GlyphIdle=tx, Like=col(p["LikeColor"]),
                Save=col(p["SaveColor"]), Follow=col(p["FollowColor"]), GhostGlow=col(p["GhostGlowColor"]),
                Wood=col(p["MountColor"]), Metal=bright(col(p["MountColor"]), 2.0), Glow=tc)


def motion_params(A):
    return {"Speed": A["Speed"], "Phase": A["Phase"], "SwayDegrees": A["Sway"], "PivotUp": A["PivotUp"],
            "BobHeight": A["Bob"], "ClockMode": 0.0}


def board_mis(p, P, A):
    """Mirror of SpawnBoard + the *Mat helpers in the Verse device: {slot: (master, scalars, vectors, textures)}."""
    T = B.T
    mo = motion_params(A)
    nomo = {k: v for k, v in mo.items() if k not in ("Speed", "Phase")}
    hide = lambda on: 0.0 if on else 1.0

    def panel(top, bot, rim, em, strength, dmode, rimoff):
        return ("Panel", dict(mo, RimStrength=0.0 if rimoff > 0.5 else 0.6, EmissiveStrength=strength,
                              Pulse=0.18 if strength > 0 else 0.0, DividerMode=dmode, Stretch=1.0 - dmode,
                              SplitZ=B.SPLIT_Z, DividerZ=B.DIVIDER["z"]),
                {"ColorTop": top, "ColorBottom": bot, "RimColor": rim, "Emissive": em}, {})

    def card(mask, fill, outl, acc, always, cy, cz, glow=0.32, shine=None):
        return ("Card", dict(mo, AlwaysOn=always, Shine=always if shine is None else shine, Glow=glow,
                             InTime=T["thanks"][0], OutTime=T["thanks"][1], CenterY=cy, CenterZ=cz),
                {"FillColor": fill, "OutlineColor": outl, "AccentColor": acc}, {"Mask": tref(mask)})

    def button(mask, tin, tout, tclick, cy, active, cz=B.BTN["z"], off=99.0, idle=None):
        return ("Button", dict(mo, InTime=tin, OutTime=tout, ClickTime=tclick, CenterY=cy, CenterZ=cz, OffTime=off,
                               ActiveGlow=0.18),
                {"IdleColor": idle or P["ButtonIdle"], "GlyphIdle": P["GlyphIdle"], "ActiveColor": active,
                 "GlyphActive": INK}, {"Mask": tref(mask)})

    def burst(trig, start, show):
        return ("Burst", dict(mo, TriggerTime=trig, SetStart=start, SetCount=3.0, Velocity=120.0, Gravity=45.0,
                              Size=34.0, Life=0.95, Hide=hide(show)), {}, {"Atlas": tref("T_BB_Sprites")})

    hl = HEADLINES.get(p.get("Headline", "EnjoyingTheMap"), 0)
    th = THANKS.get(p.get("ThanksMessage", "ThanksBoo"), 0)
    bs = B.BTN_S
    return {
        "Housing": panel(P["BoardTop"], P["BoardBottom"], P["Rim"], [0, 0, 0], 0.0, 0.0, 0.0),
        "Trim": panel(dim(P["Trim"], 0.08), dim(P["Trim"], 0.08), [0, 0, 0], P["Trim"], 2.6, 0.0, 0.0),
        "Divider": panel(dim(P["Divider"], 0.1), dim(P["Divider"], 0.1), [0, 0, 0], P["Divider"], 1.6, 1.0, 1.0),
        "Header": card(f"T_BB_Header_{hl}", P["HeaderText"], P["HeaderOutline"], P["HeaderAccent"], 1.0,
                       -B.HEADER["s"], B.HEADER["z"]),
        "TopBar": card("T_BB_TopBar", P["GlyphIdle"], PILL, [0, 0, 0], 1.0, -B.TOPBAR["s"], B.TOPBAR["z"], 0.2, 0.0),
        "Avatar": card("T_BB_Avatar", [1, 1, 1], [0.05, 0.22, 0.9], [0.1, 0.85, 0.15], 1.0, -B.AVATAR["s"],
                       B.AVATAR["z"], 0.25, 0.0),
        "Thanks": card(f"T_BB_Thanks_{th}", P["ThanksText"], P["ThanksOutline"], P["ThanksAccent"], 0.0,
                       -B.THANKS["s"], B.THANKS["z"]),
        "BtnMenu": button("T_BB_Btn_Menu", -5.0, 99.0, T["menu"], -B.MENU["s"], P["Like"], B.MENU["z"],
                          T["close"][0], PILL),
        "BtnLike": button("T_BB_Btn_Like", T["btn_in"][0], T["btn_out"][0], T["click"][0], -bs[0], P["Like"]),
        "BtnSave": button("T_BB_Btn_Save", T["btn_in"][1], T["btn_out"][1], T["click"][1], -bs[1], P["Save"]),
        "BtnFollow": button("T_BB_Btn_Follow", T["btn_in"][2], T["btn_out"][2], T["click"][2], -bs[2], P["Follow"]),
        "BurstLike": burst(T["click"][0] + 0.05, 0.0, p.get("ShowBursts", True)),
        "BurstSave": burst(T["click"][1] + 0.05, 3.0, p.get("ShowBursts", True)),
        "BurstFollow": burst(T["click"][2] + 0.05, 6.0, p.get("ShowBursts", True)),
        "Candy": ("Burst", dict(mo, TriggerTime=T["rain"][0], Delay=1.5, Life=1.7, Velocity=0.0, Gravity=430.0,
                                SpreadS=175.0, Toward=12.0, Size=36.0, SetStart=9.0, SetCount=4.0, Spin=1.4,
                                Hide=hide(p.get("ShowCandyRain", True))), {}, {"Atlas": tref("T_BB_Sprites")}),
        "Ghost": ("Ghost", dict(mo, Hide=hide(p.get("ShowGhost", True))), {"GlowColor": P["GhostGlow"]}, {}),
        "Bats": ("Bats", dict(nomo, Hide=hide(p.get("ShowBats", True))), {}, {"Atlas": tref("T_BB_Sprites")}),
        "Pumpkins": ("Pumpkin", dict(nomo, Hide=hide(p.get("ShowPumpkins", True))), {"Color": P["Pumpkin"]},
                     {"Face": tref("T_BB_PumpkinFace")}),
    }


def mount_mi(base, rough, metal, grain, em, strength, A, extra=None):
    s = dict({k: v for k, v in motion_params(A).items() if k not in ("Speed", "Phase")}, Roughness=rough,
             Metallic=metal, Grain=grain, EmissiveStrength=strength, Flicker=0.25 if strength > 0 else 0.0)
    s.update(extra or {})
    return ("Mount", s, {"Color": base, "Emissive": em}, {})


SANDBOX = r'''
import json
MI = "editor_toolset.toolsets.material_instance.MaterialInstanceTools."
AT = "editor_toolset.toolsets.asset.AssetTools."
def T(n, a):
    return execute_tool(n, json.dumps(a))
def rv(r):
    return r["returnValue"] if isinstance(r, dict) and "returnValue" in r else r
def run():
    errs = []
    for name, parent, sc, vc, tx in ITEMS:
        p = FOLDER + "/" + name
        if rv(T(AT + "exists", {"path": p})):
            mi = {"refPath": p + "." + name}
        else:
            mi = rv(T(MI + "create", {"folder_path": FOLDER, "asset_name": name, "parent": {"refPath": parent}}))
        for k, v in tx.items():
            T(MI + "set_texture_parameter", {"instance": mi, "name": k, "value": {"refPath": v}})
        for k, v in sc.items():
            try:
                T(MI + "set_scalar_parameter", {"instance": mi, "name": k, "value": float(v)})
            except Exception as ex:
                errs.append(name + "." + k)
        for k, v in vc.items():
            T(MI + "set_vector_parameter", {"instance": mi, "name": k, "value": {"r": v[0], "g": v[1], "b": v[2], "a": 1.0}})
    return {"made": len(ITEMS), "errors": errs[:20]}
'''


def make_mis(items):
    script = SANDBOX + f"\nFOLDER = {MIRROR!r}\nITEMS = json.loads({json.dumps(json.dumps(items))})\n"
    return api.tool("script", "execute_tool_script", {"script": script})


MESH_SANDBOX = r'''
import json
AT = "editor_toolset.toolsets.asset.AssetTools."
SM = "editor_toolset.toolsets.static_mesh.StaticMeshTools."
def T(n, a):
    return execute_tool(n, json.dumps(a))
def rv(r):
    return r["returnValue"] if isinstance(r, dict) and "returnValue" in r else r
def run():
    done = []
    for src, dst, slots in MESHES:
        if not rv(T(AT + "exists", {"path": dst})):
            T(AT + "duplicate", {"path": src, "new_path": dst})
        name = dst.rsplit("/", 1)[1]
        for slot, mi in slots.items():
            T(SM + "set_material", {"mesh": {"refPath": dst + "." + name}, "slot_name": slot, "material": {"refPath": mi}})
        done.append(name)
    return {"meshes": done}
'''


def copy_meshes(meshes):
    script = MESH_SANDBOX + f"\nMESHES = json.loads({json.dumps(json.dumps(meshes))})\n"
    return api.tool("script", "execute_tool_script", {"script": script})


ROW = {"line_y": 1289.0, "x0": 1866.0, "step": 700.0, "y": -2700.0}   # promo row, away from the real devices


def layout(d, k, row=False):
    """(root spec node, mi items) for device d (index k), mirroring boo_board_device.Build()."""
    p = d["props"]
    loc, rot = d["xf"]["location"], d["xf"]["rotation"]
    if row:
        loc = {"x": ROW["x0"] + ROW["step"] * (k - 1), "y": ROW["y"], "z": 0.0}
    scale = float(p.get("BoardScale", 1.0))
    yaw = rot["yaw"] + 90.0                                 # board faces the device's screen side (local +Y)
    fwd = (math.cos(math.radians(yaw)), math.sin(math.radians(yaw)))
    ahead = float(p.get("DistanceFromDevice", 0.0))
    at = [loc["x"] + fwd[0] * ahead, loc["y"] + fwd[1] * ahead, loc["z"]]
    speed = max(0.1, float(p.get("AnimationSpeed", 1.0)))
    phase = 0.0 if p.get("SyncAllBoards") else (k * 2.3) % B.PERIOD
    P = palette(p)
    mount = p.get("Mount", "GraveyardArch")
    hang = min(140.0, max(20.0, float(p.get("HangLength", 70.0))))
    hook_z = B.BEAM_Z - B.HOOK_DROP
    sway = float(p.get("SwayAmount", 2.5))
    still = {"Speed": 1.0, "Phase": 0.0, "Sway": 0.0, "PivotUp": 0.0, "Bob": 0.0}
    kids, items, meshes = [], [], []

    def mesh(src, dst, prefix, mapping):
        """Copy SM_BB_<src> -> SM_BBM<k>_<dst> whose slots default to this board's MIs; returns its component class."""
        slotmap = {}
        for slot, (master, sc, vc, tx) in mapping.items():
            name = f"MI_BBM{k}_{prefix}{slot}"
            items.append([name, f"{MATS}/M_BB_{master}.M_BB_{master}", sc, vc, tx])
            slotmap[slot] = f"{MIRROR}/{name}.{name}"
        mname = f"SM_BBM{k}_{dst}"
        meshes.append([f"{SRC}/SM_BB_{src}", f"{PMESH}/{mname}", slotmap])
        return M + mname

    if mount in ("GraveyardArch", "LanternPost"):
        board_up = hook_z - hang + abs(B.top_z(B.HOOK_S))
        A = {"Speed": speed, "Phase": phase, "Sway": sway, "PivotUp": hook_z - board_up, "Bob": 0.0}
        ch = {"Speed": speed, "Phase": phase, "Sway": sway, "PivotUp": 0.0, "Bob": 0.0}
        src = "Arch" if mount == "GraveyardArch" else "LanternPost"
        mm = {"Wood": mount_mi(P["Wood"], 0.7, 0.0, 0.6, [0, 0, 0], 0.0, still),
              "Metal": mount_mi(P["Metal"], 0.38, 0.85, 0.0, [0, 0, 0], 0.0, still),
              "Pumpkins": ("Pumpkin", {"Hide": 0.0}, {"Color": P["Pumpkin"]}, {"Face": tref("T_BB_PumpkinFace")})}
        if mount == "LanternPost":
            mm["Glow"] = mount_mi(dim(P["Glow"], 0.3), 0.3, 0.0, 0.0, P["Glow"], 7.0, still)
        kids.append({"name": "Mount", "components": {mesh(src, "Mount", "Mount", mm): {"Collidable": False}}})
        cm = {"Chain": mount_mi(bright(P["Metal"], 1.2), 0.35, 0.9, 0.0, [0, 0, 0], 0.0, ch,
                                {"ChainLength": hang, "ChainPitch": B.CHAIN_PITCH})}
        chain_cls = mesh("Chain", "Chain", "Chain", cm)
        for side, s in (("L", -B.HOOK_S), ("R", B.HOOK_S)):
            kids.append({"name": "Chain" + side, "at": [0, s, hook_z], "components": {chain_cls: {"Collidable": False}}})
    elif mount == "SpiderThread":
        board_up = float(p.get("FloatHeight", 430.0))
        A = {"Speed": speed, "Phase": phase, "Sway": sway * 0.15, "PivotUp": 1600.0, "Bob": 0.0}
        sm = {"Silk": mount_mi([0.8, 0.8, 0.85], 0.5, 0.0, 0.0, [0.8, 0.8, 1.0], 0.6, A),
              "Spider": mount_mi([0.03, 0.015, 0.05], 0.3, 0.0, 0.0, [0, 0, 0], 0.0, A),
              "Eyes": mount_mi([1, 1, 1], 0.3, 0.0, 0.0, P["Glow"], 3.0, A)}
        kids.append({"name": "Spider", "at": [0, 0, board_up],
                     "components": {mesh("SpiderThread", "Spider", "Spider", sm): {"Collidable": False}}})
    elif mount == "FloatingMagic":
        board_up = float(p.get("FloatHeight", 430.0))
        A = {"Speed": speed, "Phase": phase, "Sway": 0.0, "PivotUp": 0.0, "Bob": 12.0}
        rm = {"Glow": mount_mi(dim(P["Glow"], 0.3), 0.3, 0.0, 0.0, P["Glow"], 5.0, still)}
        kids.append({"name": "Ring", "components": {mesh("FloatRing", "Ring", "Ring", rm): {"Collidable": False}}})
    else:
        board_up = B.H0 + B.EXT + 20.0
        A = {"Speed": speed, "Phase": phase, "Sway": 0.0, "PivotUp": 0.0, "Bob": 0.0}
    kids.append({"name": "Board", "at": [0, 0, board_up],
                 "components": {mesh("Board", "Board", "", board_mis(p, P, A)): {"Collidable": False}}})
    node = {"name": f"Board{chr(64 + k)}", "at": at, "rot": [0, yaw, 0], "scale": scale, "children": kids}
    return node, items, meshes


def build(skip_mis=False, row=False):
    for f in (PROMO, MIRROR, PMESH):
        api.tool("asset", "create_folder", {"path": f})
    devs = devices()
    if row:     # only the showcase line of devices, so board k keeps its MI_BBM<k> names
        devs = [d for d in devs if abs(d["xf"]["location"]["y"] - ROW["line_y"]) < 50.0]
    root = {"name": "BooMirror", "children": []}
    all_meshes = []
    for k, d in enumerate(devs, 1):
        node, items, meshes = layout(d, k, row)
        if not skip_mis:
            r = make_mis(items)
            print(f"  {d['label']}: {d['props'].get('Style')} / {d['props'].get('Mount')} -> {r}")
        all_meshes += meshes
        root["children"].append(node)
    print(" ", copy_meshes(all_meshes))
    api.tool("asset", "save_assets", {"asset_paths": []})
    print("  build verse:", api.tool("verse", "BuildAll", {}) or "ok")
    sg.component_classes(refresh=True)
    print("  entities:", sg.apply(root, prune=True, log=lambda *a: None))
    api.tool("asset", "save_assets", {"asset_paths": []})
    print("mirror built:", len(devs), "boards")


def hide(on):
    for d in devices():
        api.tool("scene", "set_actor_hidden", {"actor": {"refPath": d["ref"]}, "hidden": bool(on)})
    print("devices hidden" if on else "devices visible")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "build":
        build(skip_mis="--skip-mis" in sys.argv, row="--row" in sys.argv)
    elif cmd == "hide":
        hide(sys.argv[2] == "1")
    elif cmd == "remove":
        sc = sg.Scene()
        e = sc.resolve("BooMirror", required=False)
        if e:
            api.tool("entity", "DeleteEntity", {"entity": e["entity"]})
        print("removed")
