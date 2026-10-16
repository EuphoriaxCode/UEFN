"""Global material clock for every Boo Board in the editor (MPC_BB_Clock): freeze + set time with ONE write."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "cli"))
from uefncli import api  # noqa: E402

MPC = {"refPath": "/176d0aa3-082b-479b-b3f0-d5ac722fe133/BooBoard/BB_Materials/MPC_BB_Clock.MPC_BB_Clock"}


def set_clock(freeze, t=0.0):
    v = [{"parameterName": "GlobalFreeze", "defaultValue": float(freeze)},
         {"parameterName": "GlobalTime", "defaultValue": float(t)}]
    return api.tool("object", "set_properties", {"instance": MPC, "values": json.dumps({"scalarParameters": v})})


if __name__ == "__main__":
    set_clock(float(sys.argv[1]), float(sys.argv[2]) if len(sys.argv) > 2 else 0.0)
