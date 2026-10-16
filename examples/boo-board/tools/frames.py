"""Frame-exact viewport renders: freeze every Boo Board material at a given time, place the camera, capture.

    from frames import Renderer
    R = Renderer(); R.freeze(True)
    R.frame(path, t=3.2, at=(x, y, z), look=(x, y, z))
"""
import base64
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "cli"))
from uefncli import api  # noqa: E402

ROOT = "/176d0aa3-082b-479b-b3f0-d5ac722fe133"
INST = ROOT + "/BooBoard/BB_Materials/Instances"
MIS = ["Housing", "Trim", "Divider", "Header", "TopBar", "Avatar", "BtnMenu", "BtnLike", "BtnSave", "BtnFollow", "Thanks",
       "Ghost", "BurstLike", "BurstSave", "BurstFollow", "Candy", "Bats", "Pumpkins", "Wood", "Metal", "Glow", "Chain",
       "Silk", "Spider", "SpiderEyes"]

SANDBOX = r'''
import json
MI = "editor_toolset.toolsets.material_instance.MaterialInstanceTools."
def run():
    for name, vals in SETS:
        ref = {"refPath": INST + "/MI_BB_" + name + ".MI_BB_" + name}
        for k, v in vals.items():
            if isinstance(v, list):
                execute_tool(MI + "set_vector_parameter", json.dumps({"instance": ref, "name": k, "value": {"r": v[0], "g": v[1], "b": v[2], "a": 1.0}}))
            else:
                execute_tool(MI + "set_scalar_parameter", json.dumps({"instance": ref, "name": k, "value": float(v)}))
    return {"ok": len(SETS)}
'''


def pose(at, look):
    dx, dy, dz = (look[i] - at[i] for i in range(3))
    yaw = math.degrees(math.atan2(dy, dx))
    pitch = math.degrees(math.atan2(dz, math.hypot(dx, dy)))
    return {"location": {"x": at[0], "y": at[1], "z": at[2]}, "rotation": {"pitch": pitch, "yaw": yaw, "roll": 0.0},
            "scale": {"x": 1, "y": 1, "z": 1}}


class Renderer:
    def set_params(self, sets):
        """sets: [(mi_name, {param: float | [r,g,b]})] in ONE sandbox round-trip."""
        script = SANDBOX + f"\nINST = {INST!r}\nSETS = json.loads({json.dumps(json.dumps(sets))})\n"
        return api.tool("script", "execute_tool_script", {"script": script})

    def freeze(self, on=True):
        self.set_params([(n, {"FreezeTime": 1.0 if on else 0.0}) for n in MIS])

    def time(self, t):
        self.set_params([(n, {"FrozenTime": float(t)}) for n in MIS])

    def capture(self, path, at, look):
        r, images = api.tool_images("editor", "CaptureViewport", {"captureTransform": pose(at, look)})
        with open(path, "wb") as f:
            f.write(base64.b64decode(images[0]["data"]))
        return path

    def frame(self, path, t, at, look):
        self.time(t)
        return self.capture(path, at, look)


if __name__ == "__main__":
    import time
    R = Renderer()
    t0 = time.time()
    R.freeze(True)
    print("freeze", round(time.time() - t0, 2))
    for i in range(3):
        t1 = time.time()
        R.frame(os.path.join(os.environ["TEMP"], f"ff_{i}.png"), 3.0 + i * 0.5, (-1150, 1500, 320), (-2000, 1500, 330))
        print("frame", i, round(time.time() - t1, 2))
