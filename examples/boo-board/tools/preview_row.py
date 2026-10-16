"""Editor preview: one board per mount in a row (editor-placed entities with the mesh default materials).
These are the 'drop-in' variants: they animate in the editor and in game without any Verse."""
import json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "cli"))
import board as B
from uefncli import sg

ROOT_AT = (-2000.0, 1500.0, 0.0)
GAP = 1400.0
M = "BooBoard-BB_Meshes-"
hang = 70.0
hook_z = B.BEAM_Z - B.HOOK_DROP
board_up = hook_z - hang + abs(B.top_z(B.HOOK_S))
spec = {"name": "BooPreviewRow", "at": list(ROOT_AT), "rot": [0, 0, 0], "children": [
    {"name": "Arch", "at": [0, 0, 0], "children": [
        {"name": "Mount", "components": {M + "SM_BB_Arch": {"Collidable": False}}},
        {"name": "ChainL", "at": [0, -B.HOOK_S, hook_z], "components": {M + "SM_BB_Chain": {"Collidable": False}}},
        {"name": "ChainR", "at": [0, B.HOOK_S, hook_z], "components": {M + "SM_BB_Chain": {"Collidable": False}}},
        {"name": "Board", "at": [0, 0, board_up], "components": {M + "SM_BB_Board": {"Collidable": False}}}]},
    {"name": "Post", "at": [0, GAP, 0], "children": [
        {"name": "Mount", "components": {M + "SM_BB_LanternPost": {"Collidable": False}}},
        {"name": "ChainL", "at": [0, -B.HOOK_S, hook_z], "components": {M + "SM_BB_Chain": {"Collidable": False}}},
        {"name": "ChainR", "at": [0, B.HOOK_S, hook_z], "components": {M + "SM_BB_Chain": {"Collidable": False}}},
        {"name": "Board", "at": [0, 0, board_up], "components": {M + "SM_BB_Board": {"Collidable": False}}}]},
    {"name": "Spider", "at": [0, 2 * GAP, 0], "children": [
        {"name": "Silk", "at": [0, 0, B.FLOAT_TOP], "components": {M + "SM_BB_SpiderThread": {"Collidable": False}}},
        {"name": "Board", "at": [0, 0, B.FLOAT_TOP], "components": {M + "SM_BB_Board": {"Collidable": False}}}]},
    {"name": "Float", "at": [0, 3 * GAP, 0], "children": [
        {"name": "Ring", "components": {M + "SM_BB_FloatRing": {"Collidable": False}}},
        {"name": "Board", "at": [0, 0, B.FLOAT_TOP], "components": {M + "SM_BB_Board": {"Collidable": False}}}]},
]}
path = os.path.join(os.environ["TEMP"], "bb_preview_row.json")
json.dump(spec, open(path, "w"), indent=1)
print(path)
