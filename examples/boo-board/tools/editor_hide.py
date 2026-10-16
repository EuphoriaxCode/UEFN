"""Hide/show clutter in the editor viewport for promo renders (transient, editor-only: doesn't dirty the level).
    py -3.14 editor_hide.py 1|0"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "cli"))
from uefncli import api  # noqa: E402

LEVEL = "/176d0aa3-082b-479b-b3f0-d5ac722fe133/LikeAndFavoriteHallow_Euphoriax.LikeAndFavoriteHallow_Euphoriax:PersistentLevel."


def clutter():
    for a in api.tool("scene", "find_actors", {"collision_channels": []}):
        lab = a.get("label") or ""
        if "Spawn Pad" in lab or lab.startswith("BooBoard"):
            yield lab, {"refPath": LEVEL + a["name"]}


if __name__ == "__main__":
    on = sys.argv[1] == "1"
    for lab, ref in clutter():
        api.tool("scene", "set_actor_hidden", {"actor": ref, "hidden": on})
        print(("hidden " if on else "shown ") + lab)
