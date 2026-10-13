# Boo Board — free animated Halloween "Like · Save · Follow" sign for UEFN

A 3D sign for your island that **shows players where the Like / Save / Follow buttons are**: a little ghost opens the
in-game-style menu (☰), boops **Like**, **Save** and **Follow Dev**, and the board says **"THANKS, BOO!"**.
Pumpkins, bats, chains, candy rain, 5 colour styles, 4 mounts. One Verse device, set up in the Details panel.

![Boo Board](promo/boo_board_still.jpg)

Promo video (37 s, 1080p): rendered by `tools/promo.py` + `tools/compose.py` (not in git; it is in the release folder).

**Why it's light:** every animation runs inside the materials on each player's own machine (World Position Offset +
`Time`). The Verse device only builds the board once when the game starts — no ticking, no server cost, perfectly
smooth at any frame rate, and every board on your island stays in sync (or not, your choice).

## Install (2 minutes)
1. Close UEFN. Copy the **`BooBoard`** folder into your project's **`Content`** folder
   (`Documents\Fortnite Projects\<YourProject>\Plugins\<YourProject>\Content\` or wherever your project's Content lives).
2. Open your project. It needs **Scene Graph** enabled (Project Settings → Scene Graph).
3. **Verse → Build Verse Code**.
4. Content Browser → **All → `<YourProject>` → CreativeDevices / Verse devices → `boo_board_device`** → drag it into the level.
   The board + mount stand **exactly on the device** and face the same way as the device's screen — place the device
   where the sign should stand and aim the screen at your players. The device hides itself when the game starts.
5. Pick a Style and a Mount in the Details panel → Launch Session. Done.

> No Verse / no Scene Graph? Drag the static meshes `BooBoard/Meshes/SM_BB_Board` (+ `SM_BB_Arch` and two
> `SM_BB_Chain`) straight into your level. They animate on their own with the Pumpkin Night look.
> Positions for a matching arch: arch at (0,0,0), chains at Y ±130 / Z 506, board at Z 444.

## Details panel
| Group | Setting | What it does |
|---|---|---|
| 1 Board | **Style** | Pumpkin Night · Ghostly Mint · Witch Brew · Blood Moon · Candy Pop |
| | **Headline** | ENJOYING THE MAP? · HAVING FUN? · HAPPY HALLOWEEN! · SUPPORT THIS MAP · SPOOKY GOOD TIME? |
| | **Thanks Message** | THANKS, BOO! · THANK YOU! · YOU ROCK! · SPOOKTACULAR! |
| | **Board Scale** | 0.4 – 3 (1 ≈ a 5.5 m arch) |
| | **Animation Speed** | 0.4 – 2.5 (1 = one show every 11 s) |
| | **Sync All Boards** | on: every board plays together · off: each starts at a random moment |
| | **Play When Player Near** | off (default): the show loops forever · on: the board waits closed until a player comes close, then plays from the start and repeats while someone is near; when everyone has left it finishes the current show and stays closed |
| | **Trigger Distance** | how close a player must be for Play When Player Near (3 – 60 m, default 10 m) |
| 2 Mount | **Mount** | Graveyard Arch · Lantern Post · Spider Thread · Floating Magic · No Mount (just the board, its open bottom edge 20 cm above the device — e.g. against a wall) |
| | **Hang Length** | chain length for the arch / post (20 – 140 cm) |
| | **Sway Amount** | how much a hanging board swings (0 = still) |
| | **Float Height** | height of the board for Floating Magic / Spider Thread |
| | **Distance From Device** | 0 (default) = exactly on the device; higher = that many cm in front of the device's screen |
| 3 Show / Hide | Ghost · Bats · Pumpkins · Candy Rain · Bursts | switch parts off |
| 4 Custom Colors | **Use Custom Colors** + Board, Trim, Text, Like, Save, Follow, Ghost Glow, Mount | your own palette |

The menu bar and the tiles deliberately use in-game-menu colours (dark navy, lavender highlight) in every style, so
players recognise them; the styles theme the frame, texts, ghost, pumpkins and mount.

## How "Play When Player Near" works
The show runs on every player's own clock, so the server can't simply say "start now". Instead the device slides the
board entity forward 2 cm per second with a `keyframed_movement_component` (client-interpolated, smooth) and the
materials read that slide as their clock — and cancel it in the World Position Offset, so the board stands still.
Shows alternate forward/backward so the board never has to jump back.

## Notes
- Players **can't click** the board; it is a looping guide. Liking/saving/following happens in the real Fortnite menu.
- There is no Verse API for a player's avatar picture (UEFN 42.30), so the avatar chip is a little ghost for everyone.
- The board has no collision; the posts of the arch / lantern post have invisible colliders.
- Everything (meshes, textures, icons) is generated from code in [`tools/`](tools) — no Epic assets, fonts are SIL OFL
  (Montserrat, Poppins). Free to use in your islands.

## How it's built (for the repo)
| File | What |
|---|---|
| `tools/board.py` | layout (cm) + the 11 s timeline + ghost keyframes — single source of truth |
| `tools/build_meshes.py`, `tools/meshes.py` | bevelled extrusions, lathes, tubes → OBJ with one material slot per part |
| `tools/art.py`, `tools/art_ui.py` | SDF-drawn textures (mask channels recoloured in the materials) |
| `tools/matgraph.py` | material graphs as Python expressions, built in one `execute_tool_script` call |
| `tools/build_materials.py` | the 8 master materials (Panel, Card, Button, Ghost, Burst, Bats, Pumpkin, Mount) |
| `tools/build_instances.py` | material instances = defaults for the drop-in meshes |
| `tools/gen_verse.py` | writes `verse/boo_board_layout.verse` from `board.py` |
| `verse/boo_board_device.verse` | the device: Details panel, palettes, spawning, per-part material instances |
| `tools/frames.py`, `tools/promo.py`, `tools/compose.py` | frame-exact promo renders (FreezeTime) + titles → MP4 |
| `verse/test/` | test-only device that moves the player in front of the board (not part of the release) |

Rebuild everything: `art.py` → `build_meshes.py` → `import_assets.py all` → `build_materials.py` → `build_instances.py`
→ `gen_verse.py` → push the `verse/*.verse` files → Build Verse. Lessons: `experiments/LOG.md` E24–E27.
