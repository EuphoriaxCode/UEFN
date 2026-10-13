"""Boo Board mesh kit: bevelled extrusions of 2D outlines, lathes and tubes -> OBJ (one material slot).

Coordinates are Unreal (cm): X = out of the sign (towards the viewer), Y = right as seen from BEHIND,
Z = up. 2D outlines are given as (s, z) with s = screen-right for a viewer standing in front (+X) of the sign,
so a vertex is (x, -s, z). Writing goes through cli/uefncli/meshgen.Obj, which handles the OBJ axis flip and
auto-orients triangles from the vertex normals (verified in E13).
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "cli"))
from uefncli.meshgen import Obj as _Obj  # noqa: E402


class Obj(_Obj):
    """meshgen.Obj with material groups: o.group("Buttons") -> following faces go to that slot."""

    def __init__(self):
        super().__init__()
        self.cur = "Main"
        self.groups = []          # group name per face

    def group(self, name):
        self.cur = name
        return self

    def tri(self, a, b, c):
        super().tri(a, b, c)
        self.groups.append(self.cur)

    def text(self, mat=None):
        L = ["# boo-board meshes", "mtllib boo.mtl", "o mesh"]
        for x, y, z in self.v:
            L.append(f"v {x:.4f} {-y:.4f} {z:.4f}")
        for u, w in self.vt:
            L.append(f"vt {u:.5f} {1 - w:.5f}")
        for x, y, z in self.vn:
            L.append(f"vn {x:.5f} {-y:.5f} {z:.5f}")
        order = []
        for g in self.groups:
            if g not in order:
                order.append(g)
        for g in order:
            L.append(f"usemtl {g}")
            L.append("s off")
            for (a, b, c), fg in zip(self.f, self.groups):
                if fg == g:
                    L.append(f"f {a}/{a}/{a} {b}/{b}/{b} {c}/{c}/{c}")
        return "\n".join(L) + "\n"


# ------------------------------------------------------------------ 2D outlines (CCW, (s, z))

def rounded_rect(w, h, r, seg=8, cz=0.0):
    r = min(r, w / 2, h / 2)
    pts = []
    corners = [(w / 2 - r, -h / 2 + r, -90), (w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180)]
    for cx, cy, a0 in corners:
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a) + cz))
    return _dedupe(pts)


def arch_plaque(w, h, arch, r_bottom, seg=24, cz=0.0):
    """Flat bottom with rounded corners, sides straight, top a pointed-ish (ogee-free) gothic arch of height `arch`."""
    pts = []
    rb = r_bottom
    # bottom-right corner
    for i in range(seg // 3 + 1):
        a = math.radians(-90 + 90 * i / (seg // 3))
        pts.append((w / 2 - rb + rb * math.cos(a), -h / 2 + rb + rb * math.sin(a)))
    top = h / 2 - arch
    if arch > 0:
        # elliptical top: a "tombstone" dome when arch == w/2, a gentle arch when smaller
        for i in range(seg + 1):
            a = math.pi * i / seg
            pts.append((w / 2 * math.cos(a), top + arch * math.sin(a)))
    else:
        pts.append((w / 2, h / 2))
        pts.append((-w / 2, h / 2))
    for i in range(seg // 3 + 1):
        a = math.radians(180 + 90 * i / (seg // 3))
        pts.append((-w / 2 + rb + rb * math.cos(a), -h / 2 + rb + rb * math.sin(a)))
    return _dedupe([(s, z + cz) for s, z in pts])


def circle(r, seg=48, cs=0.0, cz=0.0):
    return [(cs + r * math.cos(2 * math.pi * i / seg), cz + r * math.sin(2 * math.pi * i / seg)) for i in range(seg)]


def _dedupe(pts, eps=1e-4):
    out = []
    for p in pts:
        if not out or abs(p[0] - out[-1][0]) > eps or abs(p[1] - out[-1][1]) > eps:
            out.append(p)
    if len(out) > 2 and abs(out[0][0] - out[-1][0]) < eps and abs(out[0][1] - out[-1][1]) < eps:
        out.pop()
    return out


def _area(pts):
    return sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts))) / 2


def _vnormals(pts):
    """Outward 2D normals per vertex for a CCW polygon (average of adjacent edge normals)."""
    n = len(pts)
    out = []
    for i in range(n):
        p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % n]
        e0 = (p1[0] - p0[0], p1[1] - p0[1])
        e1 = (p2[0] - p1[0], p2[1] - p1[1])
        n0 = _n2((e0[1], -e0[0]))
        n1 = _n2((e1[1], -e1[0]))
        m = _n2((n0[0] + n1[0], n0[1] + n1[1]))
        # miter length so the offset edge stays parallel (clamped for very sharp corners)
        c = max(0.35, m[0] * n1[0] + m[1] * n1[1])
        out.append((m[0] / c, m[1] / c, m))
    return out


def _n2(v):
    l = math.hypot(*v) or 1.0
    return (v[0] / l, v[1] / l)


def _earclip(pts):
    """Triangulate a simple CCW polygon; returns index triples."""
    idx = list(range(len(pts)))
    tris = []

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    def inside(p, a, b, c):
        return cross(a, b, p) >= -1e-9 and cross(b, c, p) >= -1e-9 and cross(c, a, p) >= -1e-9

    guard = 0
    while len(idx) > 3 and guard < 10000:
        guard += 1
        n = len(idx)
        for k in range(n):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % n]
            a, b, c = pts[i0], pts[i1], pts[i2]
            if cross(a, b, c) <= 1e-9:
                continue
            if any(inside(pts[j], a, b, c) for j in idx if j not in (i0, i1, i2)):
                continue
            tris.append((i0, i1, i2))
            idx.pop(k)
            break
        else:
            break
    if len(idx) == 3:
        tris.append(tuple(idx))
    return tris


# ------------------------------------------------------------------ 3D builders

def extrude(o, outline, depth, bevel, bevel_seg=4, x0=0.0, front=True, back=True, uv_rect=None, uv_mode="front"):
    """Bevelled slab: outline in the (s, z) plane, from x0 - depth/2 to x0 + depth/2.
    UVs: planar projection of (s, z) over uv_rect (smin, zmin, smax, zmax), v pointing down."""
    pts = list(outline)
    if _area(pts) < 0:
        pts.reverse()
    nrm = _vnormals(pts)
    if uv_rect is None:
        ss = [p[0] for p in pts]
        zs = [p[1] for p in pts]
        uv_rect = (min(ss), min(zs), max(ss), max(zs))
    smin, zmin, smax, zmax = uv_rect

    def uv(s, z):
        return ((s - smin) / (smax - smin), (zmax - z) / (zmax - zmin))

    hd = depth / 2
    rb = min(bevel, hd)
    rings = []
    # back bevel (phi from -90 → 0) then front bevel (0 → 90)
    phis = [(-90 + 90 * i / bevel_seg) for i in range(bevel_seg + 1)] + [(90 * i / bevel_seg) for i in range(bevel_seg + 1)]
    for k, ph in enumerate(phis):
        a = math.radians(ph)
        side = 1 if k > bevel_seg else -1
        xc = x0 + side * (hd - rb)
        x = xc + rb * math.sin(a)
        inset = rb * (1 - math.cos(a))
        ring = []
        for (p, (mx, mz, m)) in zip(pts, nrm):
            s = p[0] - mx * inset
            z = p[1] - mz * inset
            n = (math.sin(a), -m[0] * math.cos(a), m[1] * math.cos(a))
            ring.append(o.vert((x, -s, z), uv(s, z), n))
        rings.append(ring)
    N = len(pts)
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(N):
            j = (i + 1) % N
            o.quad(r0[i], r0[j], r1[j], r1[i])
    inner = [(p[0] - mx * rb, p[1] - mz * rb) for p, (mx, mz, m) in zip(pts, nrm)]
    tris = _earclip(inner)
    if front:
        ids = [o.vert((x0 + hd, -s, z), uv(s, z), (1, 0, 0)) for s, z in inner]
        for a, b, c in tris:
            o.tri(ids[a], ids[b], ids[c])
    if back:
        ids = [o.vert((x0 - hd, -s, z), uv(s, z), (-1, 0, 0)) for s, z in inner]
        for a, b, c in tris:
            o.tri(ids[a], ids[b], ids[c])
    return o


def quad(o, w, h, x=0.0, cs=0.0, cz=0.0, two_sided=False):
    """Flat sprite card facing +X, UV 0..1 over the card."""
    s0, s1, z0, z1 = cs - w / 2, cs + w / 2, cz - h / 2, cz + h / 2
    for nx in ((1, -1) if two_sided else (1,)):
        a = o.vert((x, -s0, z0), (0, 1), (nx, 0, 0))
        b = o.vert((x, -s1, z0), (1, 1), (nx, 0, 0))
        c = o.vert((x, -s1, z1), (1, 0), (nx, 0, 0))
        d = o.vert((x, -s0, z1), (0, 0), (nx, 0, 0))
        o.quad(a, b, c, d)
    return o


def lathe(o, profile, seg=32, x0=0.0, y0=0.0, z0=0.0, ridges=0, ridge_depth=0.0):
    """Revolve (r, z) profile around the Z axis. Optional pumpkin ridges modulate the radius."""
    rows = []
    n = len(profile)
    for i, (r, z) in enumerate(profile):
        row = []
        # profile tangent for normals
        pa = profile[max(0, i - 1)]
        pb = profile[min(n - 1, i + 1)]
        tr, tz = pb[0] - pa[0], pb[1] - pa[1]
        for j in range(seg + 1):
            a = 2 * math.pi * j / seg
            k = 1.0
            if ridges:
                k = 1.0 - ridge_depth * (0.5 - 0.5 * math.cos(ridges * a)) ** 0.6
            rr = r * k
            nr, nz = tz, -tr
            l = math.hypot(nr, nz) or 1
            nr, nz = nr / l, nz / l
            nvec = (nr * math.cos(a), nr * math.sin(a), nz)
            row.append(o.vert((x0 + rr * math.cos(a), y0 + rr * math.sin(a), z0 + z), (j / seg, i / (n - 1)), nvec))
        rows.append(row)
    for r0, r1 in zip(rows, rows[1:]):
        for j in range(seg):
            o.quad(r0[j], r0[j + 1], r1[j + 1], r1[j])
    return o


def tube(o, path, radius, sides=10, closed=False):
    """Sweep a circle along a 3D polyline (UE coords)."""
    n = len(path)
    rings = []
    for i in range(n):
        p = path[i]
        a = path[max(0, i - 1)]
        b = path[min(n - 1, i + 1)]
        t = _n3((b[0] - a[0], b[1] - a[1], b[2] - a[2]))
        up = (0, 0, 1) if abs(t[2]) < 0.9 else (1, 0, 0)
        u = _n3(_c3(t, up))
        v = _c3(t, u)
        ring = []
        for j in range(sides + 1):
            ang = 2 * math.pi * j / sides
            nv = tuple(u[k] * math.cos(ang) + v[k] * math.sin(ang) for k in range(3))
            ring.append(o.vert(tuple(p[k] + nv[k] * radius for k in range(3)), (j / sides, i / max(1, n - 1)), nv))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        for j in range(sides):
            o.quad(r0[j], r0[j + 1], r1[j + 1], r1[j])
    return o


def box(o, sx, sy, sz, c=(0, 0, 0), bevel=1.0):
    """Bevelled box built as an extrusion along X of a rounded rect in the (s, z) plane."""
    outline = rounded_rect(sy, sz, bevel, seg=2, cz=c[2])
    outline = [(s + c[1], z) for s, z in outline]
    return extrude(o, outline, sx, bevel, bevel_seg=2, x0=c[0])


def _c3(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _n3(v):
    l = math.sqrt(sum(c * c for c in v)) or 1.0
    return tuple(c / l for c in v)


def save(o, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(o.text())
    names = sorted(set(o.groups))
    with open(os.path.join(os.path.dirname(path), "boo.mtl"), "w") as f:
        f.write("".join(f"newmtl {g}\nKd 0.8 0.8 0.8\n" for g in names))
    return len(o.v), len(o.f), names
