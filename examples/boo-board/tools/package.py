"""Build the release folder (run with UEFN CLOSED so the .uasset files are consistent).

    py -3.14 package.py
-> C:\\Aeon.Bonjé\\Euphoriax\\BooBoard_Release\\
     BooBoard_v1.0_assets.zip            the BooBoard folder for your own project (+ INSTALL.txt)
     boo_board_promo.mp4, README.md
"""
import os
import shutil
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = r"C:\Aeon.Bonjé\Euphoriax\UEFN Maps\LikeAndFavoriteHallow_Euphoriax"
OUT = r"C:\Aeon.Bonjé\Euphoriax\BooBoard_Release"
VERSION = "1.1.3"
SKIP_DIRS = {".lore", "Saved", "Intermediate", "DerivedDataCache", "Binaries", ".vs", ".vscode", "BooBoardTest", "SpookySupport"}

INSTALL = """BOO BOARD v{v} - free animated Halloween Like / Save / Follow sign for UEFN
==========================================================================

INSTALL
1. Close UEFN.
2. Copy the "BooBoard" folder into your project's Content folder
   (the folder that holds your .umap and your other assets).
3. Open your project. Scene Graph must be enabled (Project Settings > Scene Graph).
4. Verse > Build Verse Code.
5. Content Browser > your project > CreativeDevices (or search "boo_board_device") > drag it into your level.
   The board and its mount stand exactly on the device and face the same way as the device's SCREEN:
   put the device where the sign should be and aim its screen at your players.
   The device hides itself in game. Verse devices only run in a session: in the editor you only see the device.
6. Pick a Style and a Mount in the Details panel and launch a session.

DETAILS PANEL
 1 Board        Style, Headline (5 texts), Thanks Message (4 texts), Board Scale, Animation Speed, Sync All Boards,
                Play When Player Near (tick it: the show only plays when a player comes close) + Trigger Distance
 2 Mount        Graveyard Arch / Lantern Post / Spider Thread / Floating Magic / No Mount,
                Hang Length, Sway Amount, Float Height, Distance From Device
 3 Show / Hide  Ghost, Bats, Pumpkins, Candy Rain, Bursts
 4 Colors       Use Custom Colors + Board, Trim, Text, Like, Save, Follow, Ghost Glow, Mount

GOOD TO KNOW
- All animation runs in the materials on each player's machine: smooth and zero server cost.
- The board is a guide; players like / save / follow in the real Fortnite menu.
- By default the show loops forever. Tick "Play When Player Near" to start it only when someone walks up.
- Everything was drawn/modelled from code; fonts used for the textures are SIL OFL (Montserrat, Poppins).

Made by Euphoriax - free to use in your islands.
"""


def zip_dir(zf, src, arc_root, skip=SKIP_DIRS):
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in skip]
        for f in files:
            p = os.path.join(root, f)
            zf.write(p, os.path.join(arc_root, os.path.relpath(p, src)))


def main():
    os.makedirs(OUT, exist_ok=True)
    assets = os.path.join(OUT, f"BooBoard_v{VERSION}_assets.zip")
    with zipfile.ZipFile(assets, "w", zipfile.ZIP_DEFLATED) as zf:
        zip_dir(zf, os.path.join(PROJECT, "Content", "BooBoard"), "BooBoard")
        zf.writestr("INSTALL.txt", INSTALL.format(v=VERSION))
    # The whole demo project is NOT zipped automatically: its .uefnproject carries the owner's project id.
    for src in (os.path.join(HERE, "..", "promo", "boo_board_promo.mp4"), os.path.join(HERE, "..", "promo", "boo_board_promo_small.mp4"),
                os.path.join(HERE, "..", "promo", "boo_board_cover.jpg"), os.path.join(HERE, "..", "README.md")):
        if os.path.exists(src):
            shutil.copy2(src, OUT)
    with open(os.path.join(OUT, "INSTALL.txt"), "w", encoding="utf-8") as f:
        f.write(INSTALL.format(v=VERSION))
    for f in sorted(os.listdir(OUT)):
        print(f"{os.path.getsize(os.path.join(OUT, f)) / 1e6:8.2f} MB  {f}")


if __name__ == "__main__":
    main()
