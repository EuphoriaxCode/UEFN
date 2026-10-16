"""Write verse/boo_board_layout.verse from board.py (timeline + layout constants used by the device)."""
import os

import board as B

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "verse", "boo_board_layout.verse")


def f(x):
    s = f"{float(x):.4f}".rstrip("0")
    s = s + "0" if s.endswith(".") else s
    return "0.0" if s in ("-0.0", "0.0") else s


def main():
    T = B.T
    header = open(os.path.join(os.path.dirname(OUT), "euphoriax_header.txt"), encoding="utf-8").read()
    L = [header, "# show timings (seconds) and board sizes (cm), the materials use the same numbers", ""]
    consts = {
        "BB_Period": B.PERIOD,
        "BB_BtnInLike": T["btn_in"][0], "BB_BtnInSave": T["btn_in"][1], "BB_BtnInFollow": T["btn_in"][2],
        "BB_BtnOutLike": T["btn_out"][0], "BB_BtnOutSave": T["btn_out"][1], "BB_BtnOutFollow": T["btn_out"][2],
        "BB_ClickLike": T["click"][0], "BB_ClickSave": T["click"][1], "BB_ClickFollow": T["click"][2],
        "BB_MenuClick": T["menu"], "BB_MenuOff": T["close"][0],
        "BB_CenterYMenu": -B.MENU["s"], "BB_MenuZ": B.MENU["z"],
        "BB_HeaderCenterY": -B.HEADER["s"], "BB_HeaderZ": B.HEADER["z"],
        "BB_AvatarCenterY": -B.AVATAR["s"], "BB_AvatarZ": B.AVATAR["z"],
        "BB_TopBarCenterY": -B.TOPBAR["s"], "BB_TopBarZ": B.TOPBAR["z"],
        "BB_ThanksIn": T["thanks"][0], "BB_ThanksOut": T["thanks"][1], "BB_RainStart": T["rain"][0],
        # material CenterY is UE local Y = -s
        "BB_CenterYLike": -B.BTN_S[0], "BB_CenterYSave": -B.BTN_S[1], "BB_CenterYFollow": -B.BTN_S[2],
        "BB_ButtonZ": B.BTN["z"], "BB_ThanksCenterY": -B.THANKS["s"], "BB_ThanksZ": B.THANKS["z"],
        "BB_DividerZ": B.DIVIDER["z"], "BB_SplitZ": B.SPLIT_Z,
        "BB_BeamZ": B.BEAM_Z, "BB_HookS": B.HOOK_S, "BB_HookDrop": B.HOOK_DROP, "BB_ChainPitch": B.CHAIN_PITCH,
        "BB_BoardHookZ": B.top_z(B.HOOK_S), "BB_FloatTop": B.FLOAT_TOP,
        "BB_OpenHeight": B.H0 + B.EXT,
    }
    for k, v in consts.items():
        L.append(f"{k}<internal>:float = {f(v)}")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
