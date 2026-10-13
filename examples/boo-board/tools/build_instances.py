"""Material instances per board slot (+ assign them as the mesh's default materials).

These are the "Pumpkin Night" defaults. Verse re-tints them per style at runtime; the drop-in mesh uses them as is.
"""
import json
import sys

import board as B
from matgraph import api

ROOT = "/176d0aa3-082b-479b-b3f0-d5ac722fe133"
BB = ROOT + "/BooBoard"
MATS = BB + "/Materials"
INST = MATS + "/Instances"
TEX = BB + "/Textures"

ORANGE = (0.95, 0.24, 0.01)
PURPLE = (0.42, 0.06, 0.95)
SLIME = (0.10, 0.62, 0.02)
BONE = (1.0, 0.93, 0.80)
LAVENDER = (0.80, 0.76, 1.0)      # in-game-menu highlight
INK = (0.012, 0.012, 0.025)
PILL = (0.03, 0.034, 0.062)
TILE = (0.019, 0.022, 0.042)
GREY = (0.74, 0.75, 0.82)

T = B.T
SLOTS = {
    # slot: (master, scalars, vectors, textures)
    "Housing": ("Panel", {}, {}, {}),
    "Trim": ("Panel", {"EmissiveStrength": 2.6, "Pulse": 0.18, "RimStrength": 0.0, "Roughness": 0.4},
             {"Emissive": ORANGE, "ColorTop": (0.08, 0.03, 0.0), "ColorBottom": (0.08, 0.03, 0.0)}, {}),
    "Divider": ("Panel", {"DividerMode": 1.0, "Stretch": 0.0, "EmissiveStrength": 1.6, "RimStrength": 0.0},
                {"Emissive": PURPLE, "ColorTop": (0.05, 0.02, 0.08), "ColorBottom": (0.05, 0.02, 0.08)}, {}),
    "Header": ("Card", {"AlwaysOn": 1.0, "Shine": 1.0, "Glow": 0.3, "CenterY": -B.HEADER["s"], "CenterZ": B.HEADER["z"]},
               {"FillColor": BONE, "OutlineColor": (0.45, 0.10, 0.0), "AccentColor": PURPLE}, {"Mask": "T_BB_Header_0"}),
    "Thanks": ("Card", {"AlwaysOn": 0.0, "InTime": T["thanks"][0], "OutTime": T["thanks"][1], "Glow": 0.35,
                        "CenterY": -B.THANKS["s"], "CenterZ": B.THANKS["z"]},
               {"FillColor": BONE, "OutlineColor": (0.22, 0.04, 0.38), "AccentColor": SLIME}, {"Mask": "T_BB_Thanks_0"}),
    "Avatar": ("Card", {"AlwaysOn": 1.0, "Shine": 0.0, "Glow": 0.25, "CenterY": -B.AVATAR["s"], "CenterZ": B.AVATAR["z"]},
               {"FillColor": (1.0, 1.0, 1.0), "OutlineColor": (0.05, 0.22, 0.9), "AccentColor": (0.1, 0.85, 0.15)}, {"Mask": "T_BB_Avatar"}),
    "BtnMenu": ("Button", {"InTime": -5.0, "OutTime": 99.0, "ClickTime": T["menu"], "OffTime": T["close"][0],
                           "CenterY": -B.MENU["s"], "CenterZ": B.MENU["z"], "ActiveGlow": 0.18},
                {"ActiveColor": LAVENDER, "GlyphActive": INK, "IdleColor": PILL, "GlyphIdle": GREY}, {"Mask": "T_BB_Btn_Menu"}),
    "TopBar": ("Card", {"AlwaysOn": 1.0, "Shine": 0.0, "Glow": 0.2, "CenterY": -B.TOPBAR["s"], "CenterZ": B.TOPBAR["z"]},
               {"FillColor": GREY, "OutlineColor": PILL, "AccentColor": PILL}, {"Mask": "T_BB_TopBar"}),
    "Ghost": ("Ghost", {}, {}, {}),
    "Bats": ("Bats", {}, {}, {}),
    "Pumpkins": ("Pumpkin", {}, {}, {}),
    "Candy": ("Burst", {"TriggerTime": T["rain"][0], "Delay": 1.5, "Life": 1.7, "Speed": 1.0, "Velocity": 0.0, "Gravity": 430.0,
                        "SpreadS": 175.0, "Toward": 12.0, "Size": 36.0, "SetStart": 9.0, "SetCount": 4.0, "Spin": 1.4},
              {}, {}),
}
MOUNT_SLOTS = {
    "Wood": ("Mount", {"Grain": 0.6, "Roughness": 0.7}, {"Color": (0.045, 0.028, 0.03)}, {}),
    "Metal": ("Mount", {"Roughness": 0.38, "Metallic": 0.85}, {"Color": (0.09, 0.08, 0.1)}, {}),
    "Glow": ("Mount", {"EmissiveStrength": 7.0, "Flicker": 0.25, "Roughness": 0.3},
             {"Color": (0.3, 0.12, 0.02), "Emissive": (1.0, 0.45, 0.06)}, {}),
    "Chain": ("Mount", {"Roughness": 0.35, "Metallic": 0.9, "ChainLength": 70.0, "ChainPitch": B.CHAIN_PITCH},
              {"Color": (0.1, 0.09, 0.11)}, {}),
    "Silk": ("Mount", {"EmissiveStrength": 0.6, "Roughness": 0.5}, {"Color": (0.8, 0.8, 0.85), "Emissive": (0.8, 0.8, 1.0)}, {}),
    "Spider": ("Mount", {"Roughness": 0.3}, {"Color": (0.03, 0.015, 0.05)}, {}),
    "SpiderEyes": ("Mount", {"EmissiveStrength": 3.0}, {"Color": (1.0, 1.0, 1.0), "Emissive": (1.0, 0.85, 0.3)}, {}),
}
# mesh -> {slot: MI suffix}
MESH_SLOTS = {
    "Arch": {"Wood": "Wood", "Metal": "Metal", "Pumpkins": "Pumpkins"},
    "LanternPost": {"Wood": "Wood", "Metal": "Metal", "Glow": "Glow", "Pumpkins": "Pumpkins"},
    "Chain": {"Chain": "Chain"},
    "SpiderThread": {"Silk": "Silk", "Spider": "Spider", "Eyes": "SpiderEyes"},
    "FloatRing": {"Glow": "Glow"},
}
BTN_NAMES = ("Like", "Save", "Follow")
BTN_COLORS = (ORANGE, PURPLE, SLIME)
for i, n in enumerate(BTN_NAMES):
    SLOTS["Btn" + n] = ("Button", {"InTime": T["btn_in"][i], "OutTime": T["btn_out"][i], "ClickTime": T["click"][i],
                                   "CenterY": -B.BTN_S[i], "CenterZ": B.BTN["z"], "ActiveGlow": 0.18},
                        {"ActiveColor": LAVENDER, "GlyphActive": INK, "IdleColor": TILE, "GlyphIdle": GREY},
                        {"Mask": f"T_BB_Btn_{n}"})
    SLOTS["Burst" + n] = ("Burst", {"TriggerTime": T["click"][i] + 0.05, "SetStart": 3.0 * i, "SetCount": 3.0,
                                    "Speed": 1.0, "Velocity": 120.0, "Gravity": 45.0, "Size": 34.0, "Life": 0.95}, {}, {})


def ref(folder, name):
    return {"refPath": f"{folder}/{name}.{name}"}


def make(slot):
    master, sc, vc, tx = SLOTS[slot] if slot in SLOTS else MOUNT_SLOTS[slot]
    name = f"MI_BB_{slot}"
    p = f"{INST}/{name}"
    if api.tool("asset", "exists", {"path": p}):
        mi = ref(INST, name)
    else:
        mi = api.tool("mi", "create", {"folder_path": INST, "asset_name": name, "parent": ref(MATS, f"M_BB_{master}")})
    for k, v in tx.items():
        api.tool("mi", "set_texture_parameter", {"instance": mi, "name": k, "value": ref(TEX, v)})
    for k, v in sc.items():
        api.tool("mi", "set_scalar_parameter", {"instance": mi, "name": k, "value": float(v)})
    for k, v in vc.items():
        api.tool("mi", "set_vector_parameter", {"instance": mi, "name": k, "value": {"r": v[0], "g": v[1], "b": v[2], "a": 1.0}})
    return mi


def main():
    only = sys.argv[1:]
    mesh = ref(BB + "/Meshes", "SM_BB_Board")
    for slot in SLOTS:
        if only and slot not in only:
            continue
        mi = make(slot)
        api.tool("mesh", "set_material", {"mesh": mesh, "slot_name": slot, "material": mi})
        print("  ", slot, "->", mi["refPath"].rsplit("/", 1)[-1])
    for mname, slots in MESH_SLOTS.items():
        if only and mname not in only:
            continue
        mesh = ref(BB + "/Meshes", f"SM_BB_{mname}")
        for slot, mi_name in slots.items():
            mi = make(mi_name) if mi_name in MOUNT_SLOTS else ref(INST, f"MI_BB_{mi_name}")
            api.tool("mesh", "set_material", {"mesh": mesh, "slot_name": slot, "material": mi})
        print("  ", mname, "->", list(slots.values()))
    api.tool("asset", "save_assets", {"asset_paths": []})


if __name__ == "__main__":
    main()
