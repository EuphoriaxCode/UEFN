"""Boo Board layout + timeline: the single source of truth shared by meshes, art and materials.

Board space (cm, Unreal axes): origin = top-centre hang point, X = towards the viewer, Z = up,
s = screen-right for a viewer in front (vertex Y = -s).
"""

# ---------------------------------------------------------------- layout
W = 360.0            # board width
ARCH = 26.0          # arch rise of the top edge
H0 = 160.0           # collapsed height (headline + top bar)
EXT = 150.0          # how far the body slides open
DEPTH = 20.0
BEVEL = 6.0
FRONT = DEPTH / 2    # x of the front face
SPLIT_Z = -140.0     # vertices below this move with the opening body

TRIM_INSET = 13.0    # neon trim distance from the outline
TRIM_R = 1.7

HEADER = dict(w=260.0, h=60.0, s=0.0, z=-50.0)            # headline card (texture 1024x236)
TOPBAR = dict(w=230.0, h=52.0, s=-35.0, z=-112.0)         # menu bar pill (texture 1024x232)
MENU = dict(w=50.0, h=40.0, depth=6.0, bevel=3.0, s=47.4, z=-112.0)   # menu chip in the 4th slot of the pill
AVATAR = dict(d=50.0, s=118.0, z=-112.0)                  # avatar chip (texture 512x512)
DIVIDER = dict(w=300.0, h=4.0, z=-174.0)
BTN = dict(w=100.0, h=84.0, depth=8.0, bevel=3.0, radius=10.0, z=-236.0, gap=110.0)
BTN_S = [-BTN["gap"], 0.0, BTN["gap"]]                      # Like, Save, Follow Dev
THANKS = dict(w=252.0, h=126.0, s=-32.0, z=-236.0)         # text card (texture 1024x512)
GHOST_H = 72.0


# ---------------------------------------------------------------- mounts (device space: origin on the ground)
BEAM_Z = 520.0       # beam / arm height of the arch and the lantern post
HOOK_S = 130.0       # chains hang at s = +-HOOK_S
HOOK_DROP = 14.0     # chain top (hook eye) below the beam centre
CHAIN_PITCH = 7.2
CHAIN_LINKS = 60
FLOAT_TOP = 430.0    # board top height for the floating / spider mounts


def top_z(s):
    """z of the arched top edge at horizontal position s."""
    import math
    k = max(0.0, 1.0 - (s / (W / 2)) ** 2)
    return -ARCH + ARCH * math.sqrt(k)


# ---------------------------------------------------------------- timeline (seconds in one loop)
PERIOD = 11.0
T = dict(
    peek=(0.30, 0.90),          # ghost rises behind the top edge
    menu=1.55,                  # ghost presses the menu chip ...
    open=(1.75, 2.30),          # ... and the body slides open
    btn_in=[2.00, 2.10, 2.20],  # button pop-in starts (0.42 s each)
    btn_in_d=0.42,
    click=[3.10, 4.20, 5.30],   # ghost boops Like / Save / Follow
    btn_out=[6.05, 6.15, 6.25], # button pop-out starts (0.28 s each)
    btn_out_d=0.28,
    thanks=(6.50, 8.60),        # thanks card in / out
    rain=(6.50, 8.90),          # candy rain
    close=(9.05, 9.65),         # body slides shut (menu chip switches off)
    ghost_out=(9.25, 9.65),     # ghost shrinks away behind the board
    shine=(10.0, 10.70),        # idle shine over the header
)

# Ghost keyframes: (time, (x, s, z)) in board space. Motion between keys is eased (smoothstep).
GHOST_KEYS = [
    (0.30, (-28.0, 118.0, -70.0)),
    (0.90, (-28.0, 118.0, 34.0)),
    (1.35, (58.0, MENU["s"] + 30.0, -80.0)),
    (1.80, (58.0, MENU["s"] + 30.0, -80.0)),
    (2.95, (58.0, BTN_S[0] + 36.0, -170.0)),
    (3.65, (58.0, BTN_S[0] + 36.0, -170.0)),
    (4.10, (58.0, BTN_S[1] + 36.0, -170.0)),
    (4.75, (58.0, BTN_S[1] + 36.0, -170.0)),
    (5.20, (58.0, BTN_S[2] + 36.0, -170.0)),
    (6.00, (58.0, BTN_S[2] + 36.0, -170.0)),
    (6.70, (54.0, 132.0, -236.0)),
    (8.65, (54.0, 132.0, -236.0)),
    (9.15, (58.0, 118.0, 44.0)),
    (9.55, (-28.0, 118.0, -40.0)),
]
