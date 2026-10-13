"""Generate the Boo Board OBJ meshes (board with one material slot per animated part, plus mount parts).

Every part is modelled in BOARD SPACE (origin = top-centre hang point) so all slots share the object pivot;
the materials animate them with World Position Offset relative to that pivot.
"""
import math
import os
import sys

import board as B
import meshes as K

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "meshes")
F = B.FRONT


def offset_outline(pts, d):
    """Offset a CCW outline inward by d (miter, fine for smooth outlines)."""
    if K._area(pts) < 0:
        pts = pts[::-1]
    nrm = K._vnormals(pts)
    return [(p[0] - mx * d, p[1] - mz * d) for p, (mx, mz, m) in zip(pts, nrm)]


def housing_outline():
    return K.arch_plaque(B.W, B.H0, B.ARCH, 26.0, seg=40, cz=-B.H0 / 2)


def tiny_tri(o, x, s, z):
    """A 0.05 cm triangle: invisible, but it widens the mesh bounds so WPO motion is never culled."""
    n = (1, 0, 0)
    a = o.vert((x, -s, z), (0.999, 0.999), n)
    b = o.vert((x, -s - 0.05, z), (0.999, 0.999), n)
    c = o.vert((x, -s, z + 0.05), (0.999, 0.999), n)
    o.tri(a, b, c)


def particles(o, n, cx, cs, cz, size=1.0):
    """n unit quads stacked at the emitter; UV.x = index + 0.02 + 0.96 * u (material decodes both)."""
    for i in range(n):
        x = cx + 0.01 * i            # tiny depth offset avoids z-fighting before WPO kicks in
        s0, s1, z0, z1 = cs - size / 2, cs + size / 2, cz - size / 2, cz + size / 2
        u0, u1 = i + 0.02, i + 0.98      # stay inside (i, i+1): floor() must give i on BOTH edges
        a = o.vert((x, -s0, z0), (u0, 1), (1, 0, 0))
        b = o.vert((x, -s1, z0), (u1, 1), (1, 0, 0))
        c = o.vert((x, -s1, z1), (u1, 0), (1, 0, 0))
        d = o.vert((x, -s0, z1), (u0, 0), (1, 0, 0))
        o.quad(a, b, c, d)


def ellipsoid(o, cx, cs, cz, rx, rs, rz, uv, seg=16, rings=10):
    idx = {}
    for i in range(rings + 1):
        th = math.pi * i / rings
        for j in range(seg + 1):
            ph = 2 * math.pi * j / seg
            u = (math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th))
            p = (cx + u[0] * rx, -(cs + u[1] * rs), cz + u[2] * rz)
            n = K._n3((u[0] / rx, -u[1] / rs, u[2] / rz))
            idx[i, j] = o.vert(p, uv, n)
    for i in range(rings):
        for j in range(seg):
            o.quad(idx[i, j], idx[i, j + 1], idx[i + 1, j + 1], idx[i + 1, j])


def ghost(o, seg=40):
    """Cute ghost centred at the origin (board space), facing +X. Height ~72 cm.
    UV: body u,v in [0,0.5]; features use palette points: eyes (0.8,0.2), blush (0.8,0.8), mouth (0.8,0.5)."""
    rows = []
    prof = []                                  # (radius, z) from the top of the head down to the hem
    for i in range(13):                        # head dome
        a = math.pi / 2 * (1 - i / 12)
        prof.append((27 * math.cos(a), 10 + 26 * math.sin(a)))
    for i in range(1, 9):                      # body flares out towards the hem
        t = i / 8
        prof.append((27 + 6 * t * t, 10 - 44 * t))
    n = len(prof)
    for i, (r, z) in enumerate(prof):
        row = []
        pa, pb = prof[max(0, i - 1)], prof[min(n - 1, i + 1)]
        tr, tz = pb[0] - pa[0], pb[1] - pa[1]
        nr, nz = tz, -tr
        l = math.hypot(nr, nz) or 1
        nr, nz = nr / l, nz / l
        for j in range(seg + 1):
            a = 2 * math.pi * j / seg
            zz = z
            if i == n - 1:
                zz += 5 * math.cos(6 * a)      # wavy hem
            elif i == n - 2:
                zz += 2 * math.cos(6 * a)
            row.append(o.vert((r * math.cos(a), r * math.sin(a), zz), (0.5 * j / seg, 0.5 * i / (n - 1)),
                              (nr * math.cos(a), nr * math.sin(a), nz)))
        rows.append(row)
    for r0, r1 in zip(rows, rows[1:]):
        for j in range(seg):
            o.quad(r0[j], r0[j + 1], r1[j + 1], r1[j])
    # inside of the skirt (so the hem isn't see-through from below)
    last = rows[-1]
    c = o.vert((0, 0, -20), (0.25, 0.49), (0, 0, -1))
    for j in range(seg):
        o.tri(c, last[j + 1], last[j])
    # face features
    for side in (-1, 1):
        ellipsoid(o, 23.5, side * 10.0, 16.0, 3.2, 4.6, 7.0, (0.8, 0.2))         # eyes
        ellipsoid(o, 22.0, side * 19.0, 5.0, 1.2, 5.0, 2.6, (0.8, 0.8))          # blush
        ellipsoid(o, 3.0, side * 29.5, -6.0, 7.0, 7.5, 9.0, (0.25, 0.3))         # little arms
    ellipsoid(o, 25.0, 0.0, 4.0, 2.0, 3.4, 3.8, (0.8, 0.5))                       # "o" mouth


def pumpkin(o, cs, cz, r=22.0, h=30.0):
    """Ridged jack-o'-lantern sitting at (s, z) = bottom centre. Front (u=0.5) faces +X; stem uses v > 1."""
    prof = []
    for i in range(17):
        t = i / 16                                   # 0 top -> 1 bottom
        a = math.pi * t
        prof.append((r * math.sin(a) * (1.0 + 0.06 * math.sin(a)), cz + h * (0.5 + 0.5 * math.cos(a))))
    prof[0] = (2.5, prof[0][1] - 1.5)
    prof[-1] = (2.5, prof[-1][1] + 1.5)
    seg = 48
    rows = []
    n = len(prof)
    for i, (rr, z) in enumerate(prof):
        row = []
        for j in range(seg + 1):
            a = 2 * math.pi * j / seg + math.pi        # u = 0.5 faces +X
            rib = 1.0 - 0.10 * (0.5 - 0.5 * math.cos(8 * a)) ** 0.5
            x, y = rr * rib * math.cos(a), rr * rib * math.sin(a)
            nx = math.cos(a) * math.sin(math.pi * i / (n - 1))
            ny = math.sin(a) * math.sin(math.pi * i / (n - 1))
            nz = math.cos(math.pi * i / (n - 1))
            row.append(o.vert((x, -cs + y, z), (j / seg, i / (n - 1)), K._n3((nx, ny, nz + 1e-4))))
        rows.append(row)
    for r0, r1 in zip(rows, rows[1:]):
        for j in range(seg):
            o.quad(r0[j], r0[j + 1], r1[j + 1], r1[j])
    # curly stem
    path = []
    for i in range(9):
        t = i / 8
        path.append((1.5 * math.sin(t * 2.2), -cs + 3 * t, cz + h - 2 + 10 * t))
    first = len(o.v)
    K.tube(o, path, 2.6, sides=8)
    for k in range(first, len(o.v)):
        o.vt[k] = (o.vt[k][0], 1.5)                     # v > 1 -> stem colour in the material


def board_mesh():
    o = K.Obj()
    out = housing_outline()

    o.group("Housing")
    K.extrude(o, out, B.DEPTH, B.BEVEL, bevel_seg=5)
    # bounds wideners (ghost peeks above the top, flies in front, particles fall below)
    tiny_tri(o, 95, 0, 120)
    tiny_tri(o, 95, 0, -B.H0 - B.EXT - 60)
    tiny_tri(o, -40, 250, -60)
    tiny_tri(o, -40, -250, -60)

    o.group("Trim")
    trim = offset_outline(out, B.TRIM_INSET)
    path = [(F, -s, z) for s, z in trim] + [(F, -trim[0][0], trim[0][1])]
    K.tube(o, path, B.TRIM_R, sides=10)

    o.group("Divider")
    dv = B.DIVIDER
    K.extrude(o, K.rounded_rect(dv["w"], dv["h"], dv["h"] / 2, seg=4, cz=dv["z"]), 3.0, 1.0, bevel_seg=2, x0=F + 0.6)

    o.group("Header")
    hd = B.HEADER
    K.quad(o, hd["w"], hd["h"], x=F + 0.35, cs=hd["s"], cz=hd["z"])

    o.group("BtnMenu")
    mn = B.MENU
    hw = mn["w"] / 2
    outline = [(s + mn["s"], z) for s, z in K.rounded_rect(mn["w"], mn["h"], 9.0, seg=6, cz=mn["z"])]
    K.extrude(o, outline, mn["depth"], mn["bevel"], bevel_seg=3, x0=F + 1.0,
              uv_rect=(mn["s"] - hw, mn["z"] - hw, mn["s"] + hw, mn["z"] + hw))

    o.group("TopBar")
    tb = B.TOPBAR
    K.quad(o, tb["w"], tb["h"], x=F + 0.3, cs=tb["s"], cz=tb["z"])

    o.group("Avatar")
    av = B.AVATAR
    K.quad(o, av["d"], av["d"], x=F + 0.5, cs=av["s"], cz=av["z"])

    for name, cs in zip(("BtnLike", "BtnSave", "BtnFollow"), B.BTN_S):
        o.group(name)
        bt = B.BTN
        hw = bt["w"] / 2
        outline = [(s + cs, z) for s, z in K.rounded_rect(bt["w"], bt["h"], bt["radius"], seg=6, cz=bt["z"])]
        K.extrude(o, outline, bt["depth"], bt["bevel"], bevel_seg=3, x0=F + 2.0,
                  uv_rect=(cs - hw, bt["z"] - hw, cs + hw, bt["z"] + hw))

    o.group("Thanks")
    th = B.THANKS
    K.quad(o, th["w"], th["h"], x=F + 1.0, cs=th["s"], cz=th["z"])

    o.group("Ghost")
    ghost(o)

    for name, cs in zip(("BurstLike", "BurstSave", "BurstFollow"), B.BTN_S):
        o.group(name)
        particles(o, 10, F + 16, cs, B.BTN["z"])

    o.group("Candy")
    particles(o, 22, F + 34, 0.0, 70.0)

    o.group("Bats")
    particles(o, 3, 0.0, 0.0, -60.0)

    o.group("Pumpkins")
    for cs in (-128.0, 128.0):
        pumpkin(o, cs, B.top_z(cs) - 4.0)
    return o


# ------------------------------------------------------------------ mounts
def beam(o, s0, s1, z, depth=22.0, height=24.0, bevel=3.0):
    """Horizontal bevelled beam along s, centred at height z."""
    outline = [(ss + (s0 + s1) / 2, zz) for ss, zz in K.rounded_rect(s1 - s0, height, bevel, seg=2, cz=z)]
    K.extrude(o, outline, depth, bevel, bevel_seg=2)


def post(o, s, z0, z1, w=24.0, bevel=3.0):
    """Vertical bevelled post (extrusion along X of a tall rounded rect)."""
    outline = [(ss + s, zz) for ss, zz in K.rounded_rect(w, z1 - z0, bevel, seg=2, cz=(z0 + z1) / 2)]
    K.extrude(o, outline, w, bevel, bevel_seg=2)


def brace(o, a, b, r=5.5):
    """Diagonal strut between two (s, z) points: chunky 6-sided tube."""
    K.tube(o, [(0.0, -a[0], a[1]), (0.0, -(a[0] + b[0]) / 2, (a[1] + b[1]) / 2), (0.0, -b[0], b[1])], r, sides=6)


def eye_hook(o, s, z):
    """Small iron eye in the x-z plane (the chain's first link threads through it)."""
    path = [(3.2 * math.cos(2 * math.pi * i / 16), -s, z + 3.2 * math.sin(2 * math.pi * i / 16)) for i in range(17)]
    K.tube(o, path, 1.1, sides=8)


def chain_mesh():
    """Chain hanging down from the origin: CHAIN_LINKS oval links in alternating planes.
    UV.x = link index + 0.02..0.98, so the material can collapse the links below ChainLength."""
    o = K.Obj()
    o.group("Chain")
    p = B.CHAIN_PITCH
    seg, sides = 14, 6
    for i in range(B.CHAIN_LINKS):
        cz = -(i + 0.5) * p
        rows = []
        for j in range(seg + 1):
            a = 2 * math.pi * j / seg
            cx, cv = 2.6 * math.cos(a), 5.0 * math.sin(a)          # oval centre line, 2.6 wide, 5.0 tall
            tx, tv = -2.6 * math.sin(a), 5.0 * math.cos(a)
            tl = math.hypot(tx, tv)
            nx_, nv_ = tv / tl, -tx / tl                           # in-plane outward normal
            row = []
            for k in range(sides + 1):
                b = 2 * math.pi * k / sides
                w, d = math.cos(b) * 1.05, math.sin(b) * 1.05
                px, pv, pd = cx + nx_ * w, cz + cv + nv_ * w, d
                n = (nx_ * math.cos(b), nv_ * math.cos(b), math.sin(b))
                if i % 2 == 0:      # link plane = s-z (faces the viewer)
                    pos, nn = (pd, -px, pv), (n[2], -n[0], n[1])
                else:               # link plane = x-z
                    pos, nn = (px, pd, pv), (n[0], n[2], n[1])
                row.append(o.vert(pos, (i + 0.02 + 0.96 * j / seg, k / sides), nn))
            rows.append(row)
        for r0, r1 in zip(rows, rows[1:]):
            for k in range(sides):
                o.quad(r0[k], r0[k + 1], r1[k + 1], r1[k])
    return o


def arch_mesh():
    o = K.Obj()
    bz = B.BEAM_Z
    o.group("Wood")
    for s in (-225.0, 225.0):
        post(o, s, 14.0, bz + 34.0)
    beam(o, -262.0, 262.0, bz + 12.0)
    for sg in (-1, 1):
        brace(o, (sg * 222.0, bz - 70.0), (sg * 150.0, bz + 2.0))
    o.group("Metal")
    for s in (-225.0, 225.0):
        K.box(o, 40.0, 40.0, 16.0, c=(0.0, s, 8.0), bevel=3.0)              # plinth
        K.box(o, 30.0, 30.0, 6.0, c=(0.0, s, bz + 37.0), bevel=1.5)          # post cap
        for zz in (bz - 40.0, 60.0):
            K.box(o, 27.0, 27.0, 5.0, c=(0.0, s, zz), bevel=1.2)             # iron bands
    for s in (-B.HOOK_S, B.HOOK_S):
        eye_hook(o, s, bz - B.HOOK_DROP + 3.2)
    o.group("Pumpkins")
    for s in (-225.0, 225.0):
        pumpkin(o, s, bz + 40.0, r=17.0, h=24.0)
    return o


def lantern(o, s, z_top):
    """Hanging lantern under an arm at (s, z_top): iron cap + glowing glass + base."""
    o.group("Metal")
    K.tube(o, [(0, -s, z_top), (0, -s, z_top - 14)], 0.9, sides=6)
    K.lathe(o, [(0.5, z_top - 14), (9.0, z_top - 22), (11.0, z_top - 25), (2.0, z_top - 25.5)], seg=6, y0=-s)
    K.lathe(o, [(2.0, z_top - 50), (10.0, z_top - 50.5), (9.0, z_top - 54), (0.5, z_top - 56)], seg=6, y0=-s)
    o.group("Glow")
    K.lathe(o, [(0.5, z_top - 25), (8.5, z_top - 26), (9.5, z_top - 38), (8.5, z_top - 50), (0.5, z_top - 50.5)],
            seg=6, y0=-s)


def lantern_post_mesh():
    o = K.Obj()
    bz = B.BEAM_Z
    ps = -250.0
    o.group("Wood")
    post(o, ps, 14.0, bz + 44.0, w=26.0)
    beam(o, ps - 16.0, 196.0, bz + 12.0)
    brace(o, (ps + 2.0, bz - 110.0), (ps + 110.0, bz + 2.0))
    o.group("Metal")
    K.box(o, 44.0, 44.0, 16.0, c=(0.0, ps, 8.0), bevel=3.0)
    K.box(o, 32.0, 32.0, 6.0, c=(0.0, ps, bz + 47.0), bevel=1.5)
    for zz in (bz - 60.0, 60.0):
        K.box(o, 29.0, 29.0, 5.0, c=(0.0, ps, zz), bevel=1.2)
    for s in (-B.HOOK_S, B.HOOK_S):
        eye_hook(o, s, bz - B.HOOK_DROP + 3.2)
    lantern(o, 182.0, bz)
    o.group("Pumpkins")
    pumpkin(o, ps, bz + 50.0, r=18.0, h=25.0)
    return o


def spider_mesh():
    """Board space: two silk threads up into the sky + a cute spider sitting on the board's top edge."""
    o = K.Obj()
    o.group("Silk")
    for s in (-B.HOOK_S, B.HOOK_S):
        K.tube(o, [(0.0, -s, B.top_z(s) - 2.0), (0.0, -s, 1600.0)], 0.45, sides=6)
    o.group("Spider")
    cs = -70.0
    cz = B.top_z(cs) + 11.0
    ellipsoid(o, -3.0, cs, cz + 2.0, 13.0, 15.0, 12.0, (0.25, 0.25))       # abdomen
    ellipsoid(o, 9.0, cs, cz - 1.0, 8.5, 9.0, 8.0, (0.25, 0.25))           # head
    for side in (-1, 1):
        for k in range(4):
            a = math.radians(-50 + k * 32)
            base = (4.0 + 6.0 * math.sin(a), cs + side * 7.0, cz)
            knee = (base[0] + 12.0 * math.sin(a), cs + side * 20.0, cz + 10.0)
            foot = (base[0] + 18.0 * math.sin(a), cs + side * 27.0, B.top_z(cs + side * 27.0) + 0.5)
            K.tube(o, [(p[0], -p[1], p[2]) for p in (base, knee, foot)], 1.3, sides=6)
    o.group("Eyes")
    for side in (-1, 1):
        ellipsoid(o, 16.5, cs + side * 3.6, cz + 1.0, 1.6, 2.6, 3.2, (0.25, 0.25))
    return o


def float_ring_mesh():
    """Glowing rune ring on the ground under a floating board (device space)."""
    o = K.Obj()
    o.group("Glow")
    for r, w in ((150.0, 2.2), (128.0, 1.2)):
        path = [(r * math.cos(2 * math.pi * i / 96), r * math.sin(2 * math.pi * i / 96), 1.5) for i in range(97)]
        K.tube(o, path, w, sides=6)
    for i in range(12):
        a = 2 * math.pi * i / 12
        ellipsoid(o, 139.0 * math.cos(a), -139.0 * math.sin(a), 1.5, 3.0, 3.0, 1.2, (0.25, 0.25))
    return o


MOUNTS = {"Chain": chain_mesh, "Arch": arch_mesh, "LanternPost": lantern_post_mesh,
          "SpiderThread": spider_mesh, "FloatRing": float_ring_mesh}


def main():
    which = sys.argv[1:] or ["Board"] + list(MOUNTS)
    if "Board" in which:
        o = board_mesh()
        print("SM_BB_Board", K.save(o, os.path.join(OUT, "board", "BB_Board.obj")))
    for name, fn in MOUNTS.items():
        if name in which:
            o = fn()
            print(f"SM_BB_{name}", K.save(o, os.path.join(OUT, name.lower(), f"BB_{name}.obj")))


if __name__ == "__main__":
    main()
