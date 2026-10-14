"""Point every material slot of the Boo Board meshes at /Engine/BasicShapes/BasicShapeMaterial (run before package.py).

    py -3.14 portable_meshes.py

build_instances.py makes the meshes use the project's material instances (nice for editor previews), but those are
references INTO the project, so the BooBoard folder would break when copied into another project. In game the Verse
device sets every slot anyway. BasicShapeMaterial passes UEFN validation; /Engine/EngineMaterials/DefaultMaterial doesn't.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "cli"))
from uefncli import api  # noqa: E402

ROOT = "/176d0aa3-082b-479b-b3f0-d5ac722fe133"
MESHES = ["SM_BB_Board", "SM_BB_Arch", "SM_BB_LanternPost", "SM_BB_Chain", "SM_BB_SpiderThread", "SM_BB_FloatRing"]
MAT = {"refPath": "/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"}


def main():
    for m in MESHES:
        ref = f"{ROOT}/BooBoard/Meshes/{m}.{m}"
        api.tool("asset", "load_asset", {"asset_path": ref})
        r = api.tool("object", "get_properties", {"instance": {"refPath": ref}, "properties": ["StaticMaterials"]})
        r = json.loads(r) if isinstance(r, str) else r
        for s in r["StaticMaterials"]:
            api.tool("mesh", "set_material", {"mesh": {"refPath": ref}, "slot_name": s["materialSlotName"], "material": MAT})
        print(m, len(r["StaticMaterials"]), "slots")
    print("saved:", api.tool("asset", "save_assets", {"asset_paths": []}))


if __name__ == "__main__":
    main()
