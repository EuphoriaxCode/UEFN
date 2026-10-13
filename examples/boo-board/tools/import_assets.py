"""Import Boo Board textures and meshes into the project (re-import = delete + import, see MCP_RULES 5).

    py -3.14 import_assets.py textures | meshes | all [--only NAME]
"""
import json
import os
import sys

from matgraph import api

ROOT = "/176d0aa3-082b-479b-b3f0-d5ac722fe133"
BB = ROOT + "/BooBoard"
HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.abspath(os.path.join(HERE, "..", "art"))
MESHES = os.path.abspath(os.path.join(HERE, "..", "meshes"))

MASK_SETTINGS = {"sRGB": False, "compressionSettings": "TC_Masks", "lODGroup": "TEXTUREGROUP_World",
                 "addressX": "TA_Clamp", "addressY": "TA_Clamp"}
COLOR_SETTINGS = {"sRGB": True, "compressionSettings": "TC_Default", "lODGroup": "TEXTUREGROUP_World",
                  "addressX": "TA_Wrap", "addressY": "TA_Wrap"}


def exists(p):
    return api.tool("asset", "exists", {"path": p})


def import_texture(fname, only=None):
    name = os.path.splitext(fname)[0]
    if only and only not in name:
        return
    folder = BB + "/Textures"
    p = f"{folder}/{name}"
    if exists(p):
        api.tool("asset", "delete", {"path": p})
    r = api.tool("texture", "import_file", {"folder_path": folder, "asset_name": name,
                                            "source_file": os.path.join(ART, fname)})
    tex = r if isinstance(r, dict) else {"refPath": f"{p}.{name}"}
    settings = COLOR_SETTINGS if "Sprites" in name else MASK_SETTINGS
    try:
        ok = api.tool("object", "set_properties", {"instance": tex, "values": json.dumps(settings)})
    except Exception as e:
        ok = f"settings failed: {str(e)[:200]}"
    print(f"  {name}: {ok}")


def import_mesh(sub, obj, name):
    folder = BB + "/Meshes"
    p = f"{folder}/{name}"
    if exists(p):
        # Remove level entities using it first. delete() may return False while the old object is still
        # in memory; the next import can then fail once with "already exists" -> retry (seen in 42.30).
        api.tool("asset", "delete", {"path": p})
    for attempt in range(4):
        try:
            api.tool("mesh", "import_file", {"folder_path": folder, "asset_name": name,
                                             "source_file": os.path.join(MESHES, sub, obj),
                                             "import_materials": False, "import_textures": False,
                                             "combine_meshes": True})
            break
        except Exception as e:
            if "already exists" not in str(e) or attempt == 3:
                raise
            import time
            time.sleep(1.5)
    m = {"refPath": f"{p}.{name}"}
    print(f"  {name}: bounds {api.tool('mesh', 'get_bounds', {'mesh': m})}")
    print(f"  slots {api.tool('mesh', 'get_material_slots', {'mesh': m})}")


def main():
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    for f in ("Meshes", "Materials", "Materials/Instances", "Textures"):
        api.tool("asset", "create_folder", {"path": f"{BB}/{f}"})
    if what in ("textures", "all"):
        for f in sorted(os.listdir(ART)):
            if f.endswith(".png"):
                import_texture(f, only)
    if what in ("meshes", "all"):
        for n in ["Board", "Chain", "Arch", "LanternPost", "SpiderThread", "FloatRing"]:
            if only and only != n:
                continue
            import_mesh(n.lower(), f"BB_{n}.obj", f"SM_BB_{n}")
    api.tool("asset", "save_assets", {"asset_paths": []})


if __name__ == "__main__":
    main()
