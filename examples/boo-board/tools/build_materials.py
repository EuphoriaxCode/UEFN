"""Build the Boo Board master materials (all animation lives here, evaluated on the client every frame).

    py -3.14 build_materials.py            # all
    py -3.14 build_materials.py Ghost      # one (name without M_BB_)

Shared conventions
- tau = loop time in seconds: frac((Time * Speed + Phase) / PERIOD) * PERIOD. Every board part reads the same tau,
  so the whole show stays in sync without any Verse ticking.
- Offsets are built in mesh-LOCAL space (board space: X out, Y = -s, Z up), then Transform(Local -> World),
  so the board can be rotated/scaled freely. Then the shared board motion (sway/bob) is applied.
"""
import sys

import board as B
from matgraph import Graph

ROOT = "/176d0aa3-082b-479b-b3f0-d5ac722fe133"
MATS = ROOT + "/BooBoard/Materials"
TEX = ROOT + "/BooBoard/Textures"
TL = "1 Timeline"
LOOK = "2 Look"
MOVE = "3 Board Motion"
ANIM = "4 Animation"
CLOCK = "5 Trigger Clock"

C1 = 1.70158
C3 = C1 + 1.0


def tex(name):
    return f"{TEX}/{name}.{name}"


# ------------------------------------------------------------------ shared building blocks
def now(g):
    """Material time. FreezeTime = 1 replaces the engine clock with FrozenTime (frame-exact video renders)."""
    return g.scalar("FreezeTime", 0.0, TL, 8).lerp(g.time(), g.scalar("FrozenTime", 0.0, TL, 9))


def clock_mode(g):
    return g.scalar("ClockMode", 0.0, CLOCK, 0)


def clock_anchor(g):
    # three scalars: a Verse `color` written to a vector parameter does not carry world-size values (seen in 42.30)
    return vec3(g, g.scalar("ClockAnchorX", 0.0, CLOCK, 4), g.scalar("ClockAnchorY", 0.0, CLOCK, 5),
                g.scalar("ClockAnchorZ", 0.0, CLOCK, 6))


def clock_base(g):
    """Where the board really stands. In clock mode ("play when a player is near") Verse slides the board entity
    slowly forward with a keyframed_movement_component; that slide IS the show clock (client-interpolated, starts
    when Verse says so) and is cancelled again in the WPO, so the board looks still."""
    return clock_mode(g).lerp(g.pivot(), clock_anchor(g))


def clock_comp(g):
    """World offset that cancels the clock slide (zero when ClockMode = 0)."""
    return clock_base(g) - g.pivot()


def timeline(g):
    speed = g.scalar("Speed", 1.0, TL, 0)
    phase = g.scalar("Phase", 0.0, TL, 1)
    loop = ((now(g) * speed + phase) / B.PERIOD).frac() * B.PERIOD
    xw = g.local_to_world_vec(g.c((1.0, 0.0, 0.0)))
    slide = g.pivot() - clock_anchor(g)
    d = g.node("DotProduct", {}, A=slide, B=xw) / g.node("DotProduct", {}, A=xw, B=xw)
    # Shows alternate direction so the board never has to jump back: forward 0 -> D, then backward D -> 0.
    # The direction flag is a tiny upward offset (> 0.25 local cm) that Verse sets while the board is idle.
    zw = g.local_to_world_vec(g.c((0.0, 0.0, 1.0)))
    dz = g.node("DotProduct", {}, A=slide, B=zw) / g.node("DotProduct", {}, A=zw, B=zw)
    backward = ((dz - 0.25) * 1000.0).sat()
    rate = g.scalar("ClockRate", 2.0, CLOCK, 2)
    d = backward.lerp(d, rate * B.PERIOD - d)
    clock = (d / rate).clamp(0.0, B.PERIOD)
    tau = clock_mode(g).lerp(loop, clock)
    return tau * g.scalar("ForceIdle", 0.0, CLOCK, 3).one_minus()


def prog(tau, t0, d):
    """0..1 progress of a window starting at t0 lasting d (numbers or nodes)."""
    return ((tau - t0) / d).sat()


def out_back(x, c1=C1):
    y = x - 1.0
    return y * y * y * (c1 + 1.0) + y * y * c1 + 1.0


def in_back(x, c1=C1):
    return x * x * x * (c1 + 1.0) - x * x * c1


def out_cubic(x):
    y = x.one_minus()
    return (y * y * y).one_minus()


def bump(g, tau, t0, d):
    """Smooth 0 -> 1 -> 0 pulse over [t0, t0+d] (half sine)."""
    return (prog(tau, t0, d) * 0.5).sin()


def vec3(g, x, y, z):
    """Append three scalar nodes/numbers into a float3."""
    return g.c(x).append(y).append(z) if not all(isinstance(v, (int, float)) for v in (x, y, z)) else g.c((x, y, z))


def board_motion(g, local_offset):
    """local_offset (float3, mesh space) -> final WPO (world), with the shared sway + bob.
    Sway rotates around the board's local Y axis through a pivot PivotUp cm above the origin."""
    sway_deg = g.scalar("SwayDegrees", 0.0, MOVE, 0)
    sway_hz = g.scalar("SwaySpeed", 0.32, MOVE, 1)
    pivot_up = g.scalar("PivotUp", 0.0, MOVE, 2)
    bob = g.scalar("BobHeight", 0.0, MOVE, 3)
    bob_hz = g.scalar("BobSpeed", 0.22, MOVE, 4)
    t = now(g)
    # Hide = 1 collapses the whole part onto its pivot (used for "Show Ghost/Bats/..." switches)
    local_offset = g.scalar("Hide", 0.0, MOVE, 5).lerp(local_offset, g.local_pos().at("XYZ") * -1.0)
    lw = g.local_to_world_vec(local_offset)
    comp = clock_comp(g)
    bob_w = g.local_to_world_vec(g.c((0.0, 0.0, 1.0)) * ((t * bob_hz).sin() * bob))
    axis = g.node("Normalize", {}, VectorInput=g.local_to_world_vec(g.c((0.0, 1.0, 0.0))))
    pivot = clock_base(g) + g.local_to_world_vec(g.c((0.0, 0.0, 1.0)) * pivot_up)
    angle = (t * sway_hz).sin() * sway_deg / 360.0
    sway = g.rotate_about_axis(axis, angle, pivot, g.world_pos() + comp + lw)
    return comp + lw + sway + bob_w


def finish_lit(g, base, emissive=None, rough=0.45, metal=0.0, opacity_mask=None):
    g.out("MP_BaseColor", base)
    if emissive is not None:
        g.out("MP_EmissiveColor", emissive)
    g.out("MP_Roughness", rough)
    g.out("MP_Metallic", metal)
    if opacity_mask is not None:
        g.out("MP_OpacityMask", opacity_mask)


def hash1(g, n, k):
    return ((n * (12.9898 + k * 3.17) + k * 0.123).sin() * 43758.5453).frac()


MASKED = {"opacityMaskClipValue": 0.4}


# ------------------------------------------------------------------ materials
def m_panel():
    """Housing / Trim / Divider. Stretch=1: vertices below SplitZ slide down with the opening body.
    DividerMode=1: scale across s (grows out of the centre) with the opening instead."""
    g = Graph("M_BB_Panel", MATS)
    tau = timeline(g)
    lp = g.local_pos()
    lx, ly, lz = lp.at("XYZ").r, lp.at("XYZ").gg, lp.at("Z")
    opening = out_back(prog(tau, B.T["open"][0], B.T["open"][1] - B.T["open"][0]), 0.9)
    closing = g.smoothstep(B.T["close"][0], B.T["close"][1], tau)
    ext = opening * closing.one_minus()
    stretch = g.scalar("Stretch", 1.0, ANIM, 0)
    split = g.scalar("SplitZ", B.SPLIT_Z, ANIM, 1)
    mask = ((split - lz) * 1000.0).sat() * stretch
    housing_off = vec3(g, 0.0, 0.0, ext * mask * -B.EXT)
    dmode = g.scalar("DividerMode", 0.0, ANIM, 2)
    dz = g.scalar("DividerZ", B.DIVIDER["z"], ANIM, 3)
    k = ext.sat() - 1.0
    div_off = vec3(g, 0.0, ly * k, (lz - dz) * k)
    off = dmode.lerp(housing_off, div_off)
    g.out("MP_WorldPositionOffset", board_motion(g, off))

    top = g.vector("ColorTop", (0.075, 0.03, 0.12), LOOK, 0)
    bot = g.vector("ColorBottom", (0.02, 0.008, 0.035), LOOK, 1)
    gz = ((lz + B.H0) / B.H0).sat()
    base = gz.lerp(bot, top)
    emis = g.vector("Emissive", (0, 0, 0), LOOK, 2)
    estr = g.scalar("EmissiveStrength", 0.0, LOOK, 3)
    pulse = g.scalar("Pulse", 0.0, LOOK, 4)
    flick = (now(g) * 0.55).sin() * pulse + 1.0
    rim = g.vector("RimColor", (0.35, 0.12, 0.6), LOOK, 5)
    rimk = g.scalar("RimStrength", 0.6, LOOK, 6)
    fres = g.node("Fresnel", {"exponent": 3.5, "baseReflectFraction": 0.0})
    e = emis * estr * flick + rim * fres * rimk
    finish_lit(g, base, e, g.scalar("Roughness", 0.32, LOOK, 7), g.scalar("Metallic", 0.0, LOOK, 8))
    return g


def m_card():
    """Header / Thanks text cards (masked). R = fill, G = outline, B = accent (bats / slime drips)."""
    g = Graph("M_BB_Card", MATS, blend="BLEND_Masked", extra=MASKED)
    tau = timeline(g)
    uv = g.uv()
    t = g.texture("Mask", tex("T_BB_Header_0"), uv, "SAMPLERTYPE_Masks", LOOK)
    R, G, Bc = t.at("R"), t.at("G"), t.at("B")
    fill = g.vector("FillColor", (1.0, 0.93, 0.82), LOOK, 0)
    outl = g.vector("OutlineColor", (0.35, 0.08, 0.02), LOOK, 1)
    acc = g.vector("AccentColor", (0.55, 0.35, 1.0), LOOK, 2)
    glow = g.scalar("Glow", 0.35, LOOK, 3)
    col = R.lerp(Bc.lerp(outl, acc), fill)
    # shine sweep (header idles): a soft diagonal band crossing the card during the shine window
    sh = prog(tau, B.T["shine"][0], B.T["shine"][1] - B.T["shine"][0])
    band = ((uv.r + uv.gg * 0.3 - (sh * 1.6 - 0.3)).abs() * -6.0 + 1.0).sat()
    shine = band * g.scalar("Shine", 0.0, ANIM, 9) * R
    e = col * glow + fill * shine * 3.0
    alpha = R.max(G).max(Bc)
    # pop in/out (AlwaysOn = 1 keeps it visible)
    t_in, t_out = g.scalar("InTime", B.T["thanks"][0], ANIM, 0), g.scalar("OutTime", B.T["thanks"][1], ANIM, 1)
    s_in = out_back(prog(tau, t_in, 0.5), 2.2)
    s_out = in_back(prog(tau, t_out, 0.3)).one_minus()
    always = g.scalar("AlwaysOn", 0.0, ANIM, 2)
    sc = always.lerp((s_in * s_out).max(0.0), 1.0)
    # gentle wobble while shown
    wob = (now(g) * 0.9).sin() * 0.025 * always.one_minus()
    cy, cz = g.scalar("CenterY", -B.THANKS["s"], ANIM, 3), g.scalar("CenterZ", B.THANKS["z"], ANIM, 4)
    lp = g.local_pos().at("XYZ")
    rel = lp - vec3(g, B.FRONT, cy, cz)
    off = rel * (sc * (wob + 1.0) - 1.0)
    g.out("MP_WorldPositionOffset", board_motion(g, off))
    finish_lit(g, col, e, 0.55, 0.0, alpha)
    return g


def m_button():
    """Keycap buttons. Texture R = idle glyph, G = active glyph, B = dome shading."""
    g = Graph("M_BB_Button", MATS)
    tau = timeline(g)
    t = g.texture("Mask", tex("T_BB_Btn_Like"), g.uv(), "SAMPLERTYPE_Masks", LOOK)
    R, G, Bm = t.at("R"), t.at("G"), t.at("B")
    t_in = g.scalar("InTime", B.T["btn_in"][0], ANIM, 0)
    t_out = g.scalar("OutTime", B.T["btn_out"][0], ANIM, 1)
    t_click = g.scalar("ClickTime", B.T["click"][0], ANIM, 2)
    s_in = out_back(prog(tau, t_in, B.T["btn_in_d"]), 2.0)
    s_out = in_back(prog(tau, t_out, B.T["btn_out_d"]), 2.2).one_minus()
    press = bump(g, tau, t_click, 0.16)
    rebound = bump(g, tau, t_click + 0.16, 0.34)
    sc = (s_in * s_out).max(0.0) * (press * -0.14 + rebound * 0.07 + 1.0)
    t_off = g.scalar("OffTime", 99.0, ANIM, 5)
    on = prog(tau, t_click + 0.04, 0.10) * prog(tau, t_off, 0.25).one_minus()
    cy, cz = g.scalar("CenterY", 0.0, ANIM, 3), g.scalar("CenterZ", B.BTN["z"], ANIM, 4)
    lp = g.local_pos().at("XYZ")
    rel = lp - vec3(g, B.FRONT + 3.0, cy, cz)
    off = rel * (sc - 1.0) + vec3(g, press * -5.0, 0.0, 0.0)
    g.out("MP_WorldPositionOffset", board_motion(g, off))

    idle = g.vector("IdleColor", (0.13, 0.06, 0.2), LOOK, 0)
    act = g.vector("ActiveColor", (1.0, 0.42, 0.05), LOOK, 1)
    gi = g.vector("GlyphIdle", (0.92, 0.88, 0.8), LOOK, 2)
    ga = g.vector("GlyphActive", (1.0, 1.0, 1.0), LOOK, 3)
    aglow = g.scalar("ActiveGlow", 0.35, LOOK, 4)
    shade = Bm * 0.55 + 0.45
    face = on.lerp(idle, act) * shade
    glyph = on.lerp(R, G)
    gcol = on.lerp(gi, ga)
    base = glyph.lerp(face, gcol)
    e = act * on * aglow * shade * glyph.one_minus() + gcol * glyph * (on * 0.5 + 0.12) + g.c((1.0, 0.9, 0.8)) * press * 1.2
    finish_lit(g, base, e, 0.35)
    return g


def m_ghost():
    g = Graph("M_BB_Ghost", MATS)
    tau = timeline(g)
    t = now(g)
    # keyframed path (board space -> UE local: y = -s)
    keys = B.GHOST_KEYS
    x0, s0, z0 = keys[0][1]
    path = g.c((x0, -s0, z0))
    for (ta, pa), (tb, pb) in zip(keys, keys[1:]):
        d = (pb[0] - pa[0], -(pb[1] - pa[1]), pb[2] - pa[2])
        if d == (0.0, 0.0, 0.0) or d == (0.0, -0.0, 0.0):
            continue
        path = path + g.c(d) * g.smoothstep(ta, tb, tau)
    bob = vec3(g, 0.0, (t * 0.31).sin() * 3.0, (t * 0.7).sin() * 4.0)
    boop = None
    for c in [B.T["menu"]] + B.T["click"]:
        b = bump(g, tau, c - 0.12, 0.34)
        boop = b if boop is None else boop + b
    boop_off = vec3(g, boop * -12.0, boop * 15.0, boop * -17.0)
    th0, th1 = B.T["thanks"]
    happy = g.smoothstep(th0 + 0.2, th0 + 0.5, tau) * g.smoothstep(th1 - 0.3, th1, tau).one_minus()
    hop = vec3(g, 0.0, 0.0, happy * (t * 1.7).sin().abs() * 16.0)
    center = path + bob + boop_off + hop
    # pop-in / shrink-out + squash on boops + stretch on hops
    pop = out_back(prog(tau, B.T["peek"][0], 0.40), 2.0) * g.smoothstep(B.T["ghost_out"][0], B.T["ghost_out"][1], tau).one_minus()
    sq = boop * 0.16
    S = vec3(g, sq + 1.0, sq + 1.0, sq * -1.0 + 1.0) * pop
    lp = g.local_pos().at("XYZ")
    local_off = center + lp * (S - 1.0)
    # one full happy spin around local Z during the thanks moment (RotateAboutAxis angle is in turns)
    spin = g.smoothstep(th0 + 0.35, th0 + 1.15, tau)
    axis = g.node("Normalize", {}, VectorInput=g.local_to_world_vec(g.c((0.0, 0.0, 1.0))))
    piv = clock_base(g) + g.local_to_world_vec(center)
    lw = g.local_to_world_vec(local_off)
    spun = g.rotate_about_axis(axis, spin, piv, g.world_pos() + clock_comp(g) + lw)
    off = local_off + g.node("Transform", {"transformSourceType": "TRANSFORMSOURCE_World",
                                           "transformType": "TRANSFORM_Local"}, _in=spun)
    g.out("MP_WorldPositionOffset", board_motion(g, off))

    uv = g.uv()
    feat = ((uv.r - 0.6) * 1000.0).sat()
    blush = ((uv.gg - 0.65) * 1000.0).sat()
    body = g.vector("BodyColor", (0.93, 0.96, 1.0), LOOK, 0)
    eyes = g.vector("EyeColor", (0.015, 0.01, 0.03), LOOK, 1)
    bl = g.vector("BlushColor", (1.0, 0.35, 0.55), LOOK, 2)
    glow = g.vector("GlowColor", (0.45, 0.85, 1.0), LOOK, 3)
    gk = g.scalar("Glow", 0.55, LOOK, 4)
    fcol = blush.lerp(eyes, bl)
    base = feat.lerp(body, fcol)
    fres = g.node("Fresnel", {"exponent": 2.2, "baseReflectFraction": 0.15})
    e = feat.one_minus() * glow * gk * (fres * 0.8 + 0.25) + bl * blush * feat * 0.35
    rough = feat.lerp(0.55, 0.12)
    finish_lit(g, base, e, rough)
    return g


def m_burst():
    """Material particles. Each quad: UV.x = index + u. Burst (Spread=0) or rain (Spread>0, Delay>0)."""
    g = Graph("M_BB_Burst", MATS, blend="BLEND_Masked", extra=MASKED)
    tau = timeline(g)
    uv = g.uv()
    idn = uv.r.floor()
    lu, lv = (uv.r.frac() - 0.02) / 0.96, uv.gg
    h1, h2, h3, h4, h5, h6 = (hash1(g, idn + 1.0, k) for k in range(1, 7))
    trig = g.scalar("TriggerTime", B.T["click"][0], ANIM, 0)
    life_s = g.scalar("Life", 1.1, ANIM, 1)
    delay = g.scalar("Delay", 0.0, ANIM, 2)
    pt = tau - trig - h3 * delay
    life = (pt / life_s).sat()
    alive = ((pt * 1000.0).sat()) * ((life_s - pt) * 1000.0).sat()
    speed = g.scalar("Velocity", 120.0, ANIM, 3)
    grav = g.scalar("Gravity", 90.0, ANIM, 4)
    spread = g.scalar("SpreadS", 0.0, ANIM, 5)
    toward = g.scalar("Toward", 25.0, ANIM, 6)
    # burst directions fan out over the upper half (AngleMin..AngleMax in turns, 0 = right, 0.25 = up)
    ang = g.scalar("AngleMin", 0.02, ANIM, 10) + h1 * (g.scalar("AngleMax", 0.48, ANIM, 11) - g.scalar("AngleMin", 0.02, ANIM, 10))
    dist = out_cubic(life) * speed * (h2 * 0.5 + 0.6)
    ds = ang.cos() * dist
    dz = ang.sin() * dist - life * life * grav
    s_off = ds + (h4 - 0.5) * 2.0 * spread
    pos = vec3(g, life * toward * (h5 + 0.5), s_off * -1.0, dz)
    size = g.scalar("Size", 26.0, ANIM, 7) * (h6 * 0.6 + 0.7)
    pop = out_back(prog(life, 0.0, 0.14), 2.5) * g.smoothstep(0.65, 1.0, life).one_minus() * alive
    rot = (h5 - 0.5) * g.scalar("Spin", 0.6, ANIM, 8) * life + (h4 - 0.5) * 0.25
    cs, sn = rot.cos(), rot.sin()
    cu, cv = lu - 0.5, lv.one_minus() - 0.5
    ru = cu * cs - cv * sn
    rv = cu * sn + cv * cs
    corner_new = vec3(g, 0.0, ru * size * pop * -1.0, rv * size * pop)
    corner_old = vec3(g, 0.0, cu * -1.0, cv)
    off = pos + corner_new - corner_old
    g.out("MP_WorldPositionOffset", board_motion(g, off))
    # atlas cell = SetStart + floor(hash * SetCount)
    cell = g.scalar("SetStart", 0.0, LOOK, 0) + (h2 * g.scalar("SetCount", 3.0, LOOK, 1)).floor()
    col = (cell / 4.0).frac() * 4.0
    row = (cell / 4.0).floor()
    auv = (col + lu).append(row + lv) / 4.0
    t = g.texture("Atlas", tex("T_BB_Sprites"), auv, "SAMPLERTYPE_Color", LOOK)
    rgb, a = t.at("RGB"), t.at("A")
    finish_lit(g, rgb, rgb * g.scalar("Glow", 0.9, LOOK, 2), 0.5, 0.0, a)
    return g


def m_bats():
    g = Graph("M_BB_Bats", MATS, blend="BLEND_Masked", extra=MASKED)
    t = now(g)
    uv = g.uv()
    idn = uv.r.floor()
    lu, lv = (uv.r.frac() - 0.02) / 0.96, uv.gg
    sp = g.scalar("OrbitSpeed", 0.05, ANIM, 0)
    a = t * sp + idn / 3.0 + hash1(g, idn + 1.0, 1) * 0.1
    rs = g.scalar("OrbitWidth", 225.0, ANIM, 1)
    rx = g.scalar("OrbitDepth", 90.0, ANIM, 2)
    zc = g.scalar("OrbitZ", -55.0, ANIM, 3)
    s = a.cos() * rs
    x = a.sin() * rx
    z = zc + (a * 2.0 + idn * 0.37).sin() * 45.0 + (t * 0.9 + idn).sin() * 6.0
    size = g.scalar("Size", 44.0, ANIM, 4) * (hash1(g, idn + 1.0, 2) * 0.35 + 0.8) * g.scalar("BatsOn", 1.0, ANIM, 5)
    cu, cv = lu - 0.5, lv.one_minus() - 0.5
    flap_raw = (t * g.scalar("FlapRate", 3.2, ANIM, 6) + hash1(g, idn + 1.0, 3)).frac()
    frame = ((flap_raw - 0.5) * 1000.0).sat()
    # wing beat also squashes the sprite a little for life
    squash = (flap_raw * 1.0).sin() * 0.08 + 1.0
    corner_new = vec3(g, 0.0, cu * size * -1.0, cv * size * squash)
    corner_old = vec3(g, 0.0, cu * -1.0, cv)
    off = vec3(g, x, s * -1.0, z) - g.c((0.0, 0.0, -60.0)) + corner_new - corner_old
    g.out("MP_WorldPositionOffset", board_motion(g, off))
    cell = frame + 13.0
    col = (cell / 4.0).frac() * 4.0
    row = (cell / 4.0).floor()
    auv = (col + lu).append(row + lv) / 4.0
    tx = g.texture("Atlas", tex("T_BB_Sprites"), auv, "SAMPLERTYPE_Color", LOOK)
    rgb, al = tx.at("RGB"), tx.at("A")
    finish_lit(g, rgb, rgb * g.scalar("Glow", 0.5, LOOK, 0), 0.6, 0.0, al)
    return g


def m_pumpkin():
    g = Graph("M_BB_Pumpkin", MATS)
    g.out("MP_WorldPositionOffset", board_motion(g, g.c((0.0, 0.0, 0.0))))
    uv = g.uv()
    stem = ((uv.gg - 1.2) * 1000.0).sat()
    face = g.texture("Face", tex("T_BB_PumpkinFace"), uv, "SAMPLERTYPE_Masks", LOOK).at("R")
    rib = (uv.r * 8.0).cos() * 0.5 + 0.5
    orange = g.vector("Color", (1.0, 0.33, 0.02), LOOK, 0)
    base = orange * (rib * 0.35 + 0.65)
    base = stem.lerp(base, g.vector("StemColor", (0.12, 0.16, 0.03), LOOK, 1))
    base = face.lerp(base, g.c((0.05, 0.015, 0.0)))
    t = now(g)
    flick = (t * 7.3).sin() * (t * 3.1 + 0.4).sin() * 0.22 + 0.85
    e = g.vector("FaceGlow", (1.0, 0.55, 0.08), LOOK, 2) * face * flick * g.scalar("GlowStrength", 6.0, LOOK, 3)
    finish_lit(g, base, e, 0.5)
    return g


def m_mount():
    """Static mount parts (wood, iron, glow). ChainLinks > 0: the mesh is a chain whose links (UV.x = link index)
    below ChainLength collapse, so one chain mesh serves every hang length."""
    g = Graph("M_BB_Mount", MATS)
    uv = g.uv()
    idx = uv.r.floor()
    pitch = g.scalar("ChainPitch", 7.2, ANIM, 0)
    length = g.scalar("ChainLength", 1000.0, ANIM, 1)
    keep = ((length - idx * pitch) * 1000.0).sat()
    lp = g.local_pos().at("XYZ")
    centre = vec3(g, 0.0, 0.0, (idx + 0.5) * pitch * -1.0)
    off = (centre - lp) * keep.one_minus()
    g.out("MP_WorldPositionOffset", board_motion(g, off))
    col = g.vector("Color", (0.05, 0.03, 0.03), LOOK, 0)
    grain_k = g.scalar("Grain", 0.0, LOOK, 1)
    grain = ((lp.mask("b") * 0.045 + (lp.mask("r") * 0.08 + lp.mask("g") * 0.05).sin() * 0.6).sin() * 0.5 + 0.5)
    base = col * (grain * grain_k + (1.0 - grain_k * 0.5))
    em = g.vector("Emissive", (0, 0, 0), LOOK, 2)
    ek = g.scalar("EmissiveStrength", 0.0, LOOK, 3)
    t = now(g)
    flick = (t * 6.1).sin() * (t * 2.3 + 0.7).sin() * g.scalar("Flicker", 0.0, LOOK, 4) + 1.0
    finish_lit(g, base, em * ek * flick, g.scalar("Roughness", 0.6, LOOK, 5), g.scalar("Metallic", 0.0, LOOK, 6))
    return g


ALL = {"Mount": m_mount, "Panel": m_panel, "Card": m_card, "Button": m_button, "Ghost": m_ghost, "Burst": m_burst,
       "Bats": m_bats, "Pumpkin": m_pumpkin}

if __name__ == "__main__":
    import json
    names = sys.argv[1:] or list(ALL)
    for n in names:
        g = ALL[n]()
        print(n, len(g.order), "nodes")
        r = g.build()
        print(json.dumps(r, indent=1)[:1200] if isinstance(r, dict) and r.get("errors") else
              f"  ok: {r.get('nodes')} nodes, {r.get('links')} links, recompile {r.get('recompile')}" if isinstance(r, dict) else r)
