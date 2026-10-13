# Animating UI in UEFN

Two layers — use both:

| | Passive / continuous | One-shot "juice" |
|---|---|---|
| Where | UI material (`Time` node) | Verse tweens on bound float fields |
| Smoothness | perfect (client, every frame) | server tick (~30 Hz) — keep short (0.1–0.6 s) |
| Examples | rotating rays, pulsing glow, bobbing/wobbling icons (UV offset+rotate), shine sweep, twinkling sparkles, falling confetti, moving stripes | pop-in with overshoot, squash & stretch press, wiggle, flash, check stamp, popup scale, fades |

## Tween engine (see `examples/daily-reward/verse/dr_anim.verse`)
- Easing: Linear, InQuad, OutQuad, InOutSine, InBack, OutBack, OutElastic (`Pow`, `Sin`, `Cos` are `<reads>`).
- Abstract `dr_anim_target` with `ApplyProp(Id, V)` per widget class; per-property generation counters so a new tween on
  the same property cancels the old one (hover vs click never fight).
- Loop: `Sleep(0.0)` per tick, time from `GetSimulationElapsedTime()`.
- Helpers: `TweenTo`, `TweenXY` (sync two props), `Squash` (1.12/0.86 then OutElastic back), `Wiggle` (angle).
- Concurrency: `sync:` to run in parallel, `spawn{}` for fire-and-forget, `race:` with care (cancels losers).

## Choreography that felt good
- Open: backdrop 0→1 (0.25 s), panel 0.55→1 OutBack (0.5 s), cards stagger 55 ms each OutBack + slight angle, button OutElastic after 0.5 s.
- Claim: anticipation 1→0.84 (0.09 InQuad) → 1.32 + white flash (0.13) → swap state under the flash → 1.0 OutElastic (0.6) + wiggle + check stamp big→normal OutBack → popup (OutElastic, rays, confetti) 1.5 s → shrink InBack.
- Idle: every ~2.6 s wiggle today's card + bounce the CLAIM button.

## Material recipes (all standard nodes, Sine period 1 ⇒ "Speed" in Hz)
- Rays: `Rotator(UV, Time*Speed)` → texture → tint.
- Bob: `p = UV-0.5; angle = Wobble*sin(t*Speed*0.5+Phase); rotate p; p.y += Bob*sin(t*Speed+Phase); +0.5` (texture needs transparent padding, clamp addressing).
- Shine: `band = saturate(1-|((u+0.35v)/1.35) - (frac(t*S)*2.6-0.6)|/W)^2 * Strength` added to RGB × alpha; plus subtle UV breathing.
- Sparkle: rotate + scale by `|sin(t*S+Phase)|^2`, alpha × same.
- Confetti: wrap texture, two layers with different tiling/speeds, sway via sin.
- Make one material per effect, Material Instances per texture/phase/tint.

Widget animations (UMG `UWidgetAnimation`) can be authored via toolset, but **cannot be triggered from Verse** (pins not settable).

## World-space animation in materials (Scene Graph meshes) — `examples/boo-board`
For props, signs and showcases, put the WHOLE timeline in the materials (WPO + emissive) instead of moving entities from Verse:
- Every part's material reads the same loop clock (`tau`) → perfectly in sync, smooth at any client frame rate, no server cost.
- Recipes (all standard nodes): pop-in = `OutBack(saturate((tau-t0)/d))` scaling `(LocalPos - Centre)`; slide/stretch =
  offset vertices below a `LocalPosition.Z` threshold; keyframed paths = `K0 + Σ ΔK_i · SmoothStep(t_i, t_i+1, tau)`;
  press = half-sine bump; spin = `RotateAboutAxis`; particles = quads with the index in UV.x (see LOG E24).
- Verse only builds the entity once and sets per-entity parameters (colours, Phase, Speed, textures).
- Frame-exact renders for promo videos: add `FreezeTime`/`FrozenTime` params that replace `Time`, then step them per capture.
- Need the show to START on an event (player nearby)? Slide the entity slowly with a `keyframed_movement_component` and let
  the material read the slide as its clock (and cancel it in WPO) — client-smooth, server-started (LOG E29).
