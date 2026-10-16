r"""Build the release zip: a BooBoard folder you drop into any project's Content folder (save in UEFN first).

    py -3.14 package.py
-> C:\Aeon.Bonjé\Euphoriax\BooBoard_Release\BooBoard_v<version>.zip   (BooBoard/ + READ ME.txt)

Works as a plain copy because the shipped assets reference nothing inside the project: the materials are built
portable (build_materials.py: allowed engine textures as defaults, no MPC), the meshes' default slots use
/Engine/BasicShapes/BasicShapeMaterial and the Verse device sets every material and texture at runtime.
The material instances and the promo clock MPC stay home. check() refuses an asset that still points at another
asset of the project.
"""
import os
import re
import shutil
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = r"C:\Aeon.Bonjé\Euphoriax\UEFN Maps\LikeAndFavoriteHallow_Euphoriax"
MOUNT = "/176d0aa3-082b-479b-b3f0-d5ac722fe133/"
OUT = r"C:\Aeon.Bonjé\Euphoriax\BooBoard_Release"
VERSION = "1.1.6"
SKIP = ("Instances", "MPC_BB_Clock.uasset")
# textures / meshes remember where they were imported from (Source File); ship a neutral path of the same length
SOURCE_DIR = ("Aeon.Bonjé/Euphoriax/Github/UEFN-MCP-Guidelines/examples/boo-board/",
              "Euphoriax/UEFN Projects/Boo Board Halloween 2026/Source Files v1.1/")

README = r"""BOO BOARD v{v}
Free animated Halloween Like / Save / Follow sign for UEFN - made by Euphoriax

INSTALL
1. Close UEFN.
2. Put the "BooBoard" folder in the Content folder of your project
   (where your .umap is, e.g. Documents\Fortnite Projects\<YourProject>\Plugins\<YourProject>\Content).
   Updating? Delete the old BooBoard folder first.
3. Open your project > Verse > Build Verse Code.
4. Drag "boo_board_device" from the BooBoard folder into your level.
   Point the screen of the device at your players, pick a Style and a Mount and Launch Session.

Scene Graph has to be on (Project Settings > Scene Graph).

SETTINGS
 1 Board        Style (5), Headline (5 texts), Thanks Message (5 texts), Board Scale, Animation Speed,
                Sync All Boards, Play When Player Near + Trigger Distance (10 m)
 2 Mount        Graveyard Arch / Lantern Post / Spider Thread / Floating Magic / No Mount,
                Hang Length, Sway Amount, Float Height, Distance From Device
 3 Show / Hide  Ghost, Bats, Pumpkins, Candy Rain, Bursts
 4 Colors       Use Custom Colors + Board, Trim, Text, Like, Save, Follow, Ghost Glow, Mount

GOOD TO KNOW
- The board stands on the device and faces the same way as its screen. In game the device is hidden,
  in the editor you only see the device (Verse runs in a session).
- Everything animates on the players own PC, so it's smooth and costs nothing on the server.
- Players still like / save / follow in the real Fortnite menu, the board shows them where.
- Play When Player Near on: the show only plays when someone walks up.
- No Mount: only the board, 20 cm above the device (nice against a wall).

Free to use in your islands. Questions? Hit us up in the Discord.

discord.gg/euphoriax
youtube.com/@euphoriax_official
x.com/Euphoriax_Fn
instagram.com/euphoriax_official
"""


def own_path(src, p):
    rel = os.path.splitext(os.path.relpath(p, src))[0].replace(os.sep, "/")
    return MOUNT + "BooBoard/" + rel


def check(src, p, data):
    """No path to ANOTHER existing asset of the project (that would break in another project).
    Its own path, its own folder and stale names of assets that no longer exist are harmless."""
    me = own_path(src, p)
    content = os.path.join(PROJECT, "Content")
    for m in re.finditer(re.escape(MOUNT.encode()) + rb"[A-Za-z0-9_/.\-]+", data):
        path = m.group(0).decode()
        if path.startswith(me) or me.startswith(path.rstrip("/") + "/"):
            continue
        pkg = path[len(MOUNT):].split(".")[0]
        if os.path.exists(os.path.join(content, pkg.replace("/", os.sep) + ".uasset")):
            raise SystemExit(f"{os.path.basename(p)} references {path} - not portable")


def main():
    src = os.path.join(PROJECT, "Content", "BooBoard")
    files = []
    for root, dirs, fs in os.walk(src):
        dirs[:] = [d for d in dirs if d not in SKIP]
        files += [os.path.join(root, f) for f in fs if f not in SKIP]
    os.makedirs(OUT, exist_ok=True)
    old = os.path.join(OUT, "old")
    os.makedirs(old, exist_ok=True)
    for f in os.listdir(OUT):                       # superseded zips out of the way
        if f.startswith("BooBoard_v") and f.endswith(".zip") and f != f"BooBoard_v{VERSION}.zip":
            shutil.move(os.path.join(OUT, f), os.path.join(old, f))
    out = os.path.join(OUT, f"BooBoard_v{VERSION}.zip")
    if os.path.exists(out):                         # the installer edition of this version
        shutil.move(out, os.path.join(old, f"BooBoard_v{VERSION}_installer.zip"))
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("READ ME.txt", README.format(v=VERSION).replace("\n", "\r\n"))
        for p in files:
            data = open(p, "rb").read()
            if p.endswith(".uasset"):
                check(src, p, data)
                size = len(data)
                data = data.replace(SOURCE_DIR[0].encode("utf-16-le"), SOURCE_DIR[1].encode("utf-16-le"))
                assert len(data) == size
                if "Guidelines".encode("utf-16-le") in data or b"Guidelines" in data:
                    raise SystemExit(f"{p}: source path still in the asset")
            zf.writestr("BooBoard/" + os.path.relpath(p, src).replace(os.sep, "/"), data)
    with open(os.path.join(OUT, "READ ME.txt"), "w", encoding="utf-8") as f:
        f.write(README.format(v=VERSION))
    shutil.copy2(os.path.join(HERE, "..", "README.md"), OUT)
    print(f"{len(files)} files ->", out)
    for f in sorted(os.listdir(OUT)):
        p = os.path.join(OUT, f)
        if os.path.isfile(p):
            print(f"{os.path.getsize(p) / 1e6:8.2f} MB  {f}")


if __name__ == "__main__":
    main()
