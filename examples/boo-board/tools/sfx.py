"""Edit sound effects for the promo videos, synthesised from scratch (numpy only, no samples -> no licences).

    py -3.14 sfx.py [storyboard.json]     # mixes the SFX for that storyboard and muxes them into its output MP4

The cues follow the edit, not the board: a hit on the hook, whooshes on cuts, the brand transition (rise, sting,
bats, wipe swish), an impact on the title and on FREE CODE, ticks on the tutorial subtitles, a sting on the end card.
Levels per cue live in LEVELS; compose2.py calls add() after every render.
"""
import os
import subprocess
import sys

import numpy as np

SR = 48000
LEVELS = {"hit": 0.95, "hook_line2": 0.45, "cut": 0.42, "hook_cut": 0.55, "xfade": 0.30, "rise": 0.55, "sting": 0.32,
          "bats": 0.40, "wipe": 0.55, "title": 0.80, "free": 0.90, "heading": 0.45, "guide": 0.35, "endcard": 0.50}
RNG = np.random.default_rng(31)


def secs(d):
    return np.arange(int(d * SR)) / SR


def pan(mono, p):
    """Equal-power pan; p is a scalar or an array in [-1, 1]."""
    a = (np.asarray(p) + 1) * np.pi / 4
    return np.stack([mono * np.cos(a), mono * np.sin(a)], axis=1)


def stft_filter(x, gain):
    """Time-varying spectral filter: gain(u in 0..1, freqs) -> per-bin gains."""
    n, hop = 1024, 256
    w = np.hanning(n)
    pad = np.concatenate([np.zeros(n), x, np.zeros(n)])
    out, norm = np.zeros(len(pad)), np.zeros(len(pad))
    f = np.fft.rfftfreq(n, 1 / SR)
    frames = (len(pad) - n) // hop + 1
    for i in range(frames):
        s = i * hop
        y = np.fft.irfft(np.fft.rfft(pad[s:s + n] * w) * gain(i / max(1, frames - 1), f), n) * w
        out[s:s + n] += y
        norm[s:s + n] += w * w
    return (out / np.maximum(norm, 1e-6))[n:n + len(x)]


def lowpass(x, fc):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(X / np.sqrt(1 + (f / fc) ** 4), len(x))


def highpass(x, fc):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(X * (f / fc) ** 2 / np.sqrt(1 + (f / fc) ** 4), len(x))


def reverb(st, tail=1.2, wet=0.25, bright=3000):
    """Cheap stereo room: convolve with decorrelated, decaying, low-passed noise."""
    n = int(tail * SR)
    t = secs(tail)
    L = len(st) + n                                       # keep the whole tail, never cut it off
    out = np.zeros((L, 2))
    for ch in range(2):
        ir = lowpass(RNG.standard_normal(n) * np.exp(-t / (tail / 5)), bright)
        ir /= np.sqrt((ir ** 2).sum())
        size = 1 << (L - 1).bit_length()
        y = np.fft.irfft(np.fft.rfft(st[:, ch], size) * np.fft.rfft(ir, size), size)[:L]
        out[:len(st), ch] += st[:, ch] * (1 - wet)
        out[:, ch] += y * wet
    return out


def norm(x, peak=1.0):
    m = np.abs(x).max()
    return x * (peak / m) if m > 0 else x


# ------------------------------------------------------------------ the sounds
def whoosh(dur=0.45, f0=250, f1=3200, peak=0.62, pan0=-0.6, pan1=0.6, width=0.7):
    n = int(dur * SR)
    lf0, lf1 = np.log2(f0), np.log2(f1)

    def g(u, f):
        fc = lf0 + (lf1 - lf0) * u
        return np.exp(-0.5 * ((np.log2(np.maximum(f, 20)) - fc) / width) ** 2)
    x = norm(stft_filter(RNG.standard_normal(n), g))
    u = np.linspace(0, 1, n)
    env = np.where(u < peak, (u / peak) ** 2.2, ((1 - u) / (1 - peak)) ** 1.6)
    return norm(pan(x * env, np.linspace(pan0, pan1, n)))


def hit(dur=1.6, boom=1.0, crack=0.6):
    t = secs(dur)
    f = 95 * np.exp(-t / 0.18) + 38                       # pitch drop 133 -> 38 Hz
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.42) * (1 - np.exp(-t / 0.004))
    body = lowpass(RNG.standard_normal(len(t)), 380) * np.exp(-t / 0.10) * 1.4
    cr = highpass(RNG.standard_normal(len(t)), 2500) * np.exp(-t / 0.035) * crack
    st = pan(norm(sub) * boom + norm(body) * 0.6 + cr, 0.0)
    return norm(reverb(st, 1.6, 0.22, 2500))


def pop(f=760, dur=0.12):
    t = secs(dur)
    fr = f * (1 + 0.7 * np.exp(-t / 0.012))
    x = np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t / 0.035) * (1 - np.exp(-t / 0.002))
    return norm(pan(x, 0.0))


def tick(dur=0.08):
    t = secs(dur)
    x = (np.sin(2 * np.pi * 1750 * t) + 0.5 * np.sin(2 * np.pi * 3480 * t)) * np.exp(-t / 0.014)
    x += highpass(RNG.standard_normal(len(t)), 4000) * np.exp(-t / 0.003) * 0.6
    return norm(pan(x, 0.0))


def bell(f, dur, tau):
    t = secs(dur)
    x = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / (tau / r ** 0.7))
            for r, a in ((1.0, 1.0), (2.0, 0.45), (3.01, 0.22), (4.17, 0.12), (5.43, 0.06)))
    return x * (1 - np.exp(-t / 0.003))


def sting(dur=2.2):
    """Spooky E-minor bell arpeggio with a high shimmer."""
    n = int(dur * SR)
    st = np.zeros((n, 2))
    for k, (f, p) in enumerate(((659.3, -0.35), (784.0, 0.25), (987.8, -0.1), (1318.5, 0.35))):
        off = int(k * 0.045 * SR)
        b = pan(bell(f, dur - k * 0.045, 0.9), p)[:n - off]
        st[off:off + len(b)] += b * (1 - 0.12 * k)
    t = secs(dur)
    sh = stft_filter(RNG.standard_normal(n), lambda u, f: ((f > 6000) & (f < 11000)) * 1.0) * np.exp(-t / 0.45)
    st += pan(norm(sh) * 0.12, 0.0)
    return norm(reverb(st, 2.0, 0.3, 6000))


def sparkle(dur=1.2, count=14):
    n = int(dur * SR)
    st = np.zeros((n, 2))
    notes = [1318.5, 1568.0, 1760.0, 1975.5, 2349.3, 2637.0, 3136.0]
    for _ in range(count):
        off = int(RNG.uniform(0, dur * 0.55) * SR)
        b = bell(RNG.choice(notes) * RNG.choice([1, 2]), dur - off / SR, 0.25) * RNG.uniform(0.3, 1.0)
        b = pan(b, RNG.uniform(-0.8, 0.8))[:n - off]
        st[off:off + len(b)] += b
    return norm(reverb(st, 1.2, 0.3, 8000))


def bats(dur=1.6, direction=1):
    """Wing flutter of a few bats crossing the screen, plus tiny squeaks."""
    n = int(dur * SR)
    t = secs(dur)
    st = np.zeros((n, 2))
    for v in range(4):
        fc = RNG.uniform(1300, 2600)
        x = stft_filter(RNG.standard_normal(n), lambda u, f, fc=fc: np.exp(-0.5 * ((f - fc) / (fc * 0.45)) ** 2))
        flap = (0.5 + 0.5 * np.sin(2 * np.pi * RNG.uniform(11, 16) * t + RNG.uniform(0, 6))) ** 3
        s0, s1 = RNG.uniform(0, 0.35), RNG.uniform(0.7, 1.0)
        u = np.clip((t / dur - s0) / (s1 - s0), 0, 1)
        env = np.sin(np.pi * u) ** 1.5
        st += pan(norm(x) * flap * env * RNG.uniform(0.5, 1.0), direction * (2 * u - 1) * 0.8)
    for _ in range(3):
        off = int(RNG.uniform(0.15, dur - 0.2) * SR)
        tt = secs(0.05)
        sq = np.sin(2 * np.pi * np.cumsum(6500 + 3000 * tt / 0.05) / SR) * np.sin(np.pi * tt / 0.05) ** 2
        st[off:off + len(sq)] += pan(sq * 0.12, RNG.uniform(-0.6, 0.6))
    return norm(st)


def swish(dur=0.32):
    return whoosh(dur, 900, 7000, peak=0.55, pan0=0.7, pan1=-0.7, width=0.9)


def free_hit():
    a, b = hit(1.8, 1.0, 0.5), sparkle(1.4)
    out = np.zeros((max(len(a), len(b)), 2))
    out[:len(a)] += a
    out[:len(b)] += b * 0.45
    return norm(out)


# ------------------------------------------------------------------ the mix
def cues(c):
    """(seconds, sound, level) for the storyboard loaded in compose2 module c."""
    fps = c.FPS
    out = []
    for o in c.SPANNED:
        if o["kind"] == "hook":
            out.append((0.0, hit(), "hit"))
            if o.get("line2"):
                out.append((o.get("line2_at", 0.45), pop(880), "hook_line2"))
        elif o["kind"] == "heading":
            out.append((o["at"][0], pop(620), "heading"))
    hook_end = next((o["at"][1] for o in c.SPANNED if o["kind"] == "hook"), 0.0)
    for k, sg in enumerate(c.SEGS):
        s = sg["s"]
        t0 = sg["start"] / fps
        join = s.get("join", "cut") if k else "first"
        if join.startswith("xfade"):
            w = whoosh(0.55, 200, 2200, peak=0.6, width=0.8)
            out.append(((sg["start"] + sg["xin"] / 2) / fps - 0.6 * 0.55, w, "xfade"))
        elif join == "cut":
            w = whoosh(0.32, 400, 4200, peak=0.62, pan0=0.5 * (-1) ** k, pan1=-0.5 * (-1) ** k)
            out.append((t0 - 0.62 * 0.32, w, "hook_cut" if t0 < hook_end else "cut"))
        for o in s.get("text", []):
            at = o.get("at", [0.12, 0])[0]
            if o["kind"] == "title":
                out.append((t0 + at, hit(1.6, 0.8, 0.4), "title"))
            elif o["kind"] == "free":
                out.append((t0 + at, free_hit(), "free"))
            elif o["kind"] == "guide":
                out.append((t0 + at, tick(), "guide"))
            elif o["kind"] == "endcard":
                out.append((t0 + 0.15, sting(2.4), "endcard"))
    ends = {sg["start"] for sg in c.SEGS if any(o["kind"] == "endcard" for o in sg["s"].get("text", []))}
    for k, e in enumerate(c.EVENTS):                         # Euphoriax brand transition
        out.append(((e + 1) / fps, whoosh(0.7, 150, 2600, peak=0.75, pan0=0, pan1=0, width=0.6), "rise"))
        if e + c.TRANS_CUT not in ends:                      # into the end card: its own sting plays instead
            out.append(((e + 17) / fps, sting(1.6), "sting"))
        out.append(((e + 12) / fps, bats(1.6, 1 if k % 2 == 0 else -1), "bats"))
        out.append(((e + c.TRANS_CUT) / fps - 0.55 * 0.32, swish(), "wipe"))
    return out


def mix(c):
    total = c.TOTAL / c.FPS
    n = int(total * SR)
    bus = np.zeros((n + 4 * SR, 2))
    cs = cues(c)
    for t, snd, lvl in cs:
        i = max(0, int(round(t * SR)))
        if i >= n:
            continue
        m = min(len(snd), len(bus) - i)
        f = min(m, int(0.02 * SR))                           # click-free end even when a sound is clipped short
        snd = snd[:m].copy()
        snd[m - f:] *= np.linspace(1, 0, f)[:, None]
        bus[i:i + m] += snd * LEVELS[lvl]
    bus = bus[:n]
    fo = int(c.SB["fade_out"] / c.FPS * SR)                  # follow the picture's fade to black
    bus[-fo:] *= np.linspace(1, 0, fo)[:, None]
    bus = np.tanh(bus * 1.1) / np.tanh(1.1)                  # gentle safety saturation
    return norm(bus, 0.80).astype(np.float32), len(cs)


def add(board):
    os.environ["BB_STORYBOARD"] = os.path.abspath(board)
    import compose2 as c
    c.prepare()
    audio, count = mix(c)
    raw = os.path.join(c.CACHE, f"sfx_{c.TAG}.f32")
    audio.tofile(raw)
    video = c.xp(c.SB["output"])
    tmp = video + ".tmp.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", raw,
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-af", "loudnorm=I=-16:TP=-2:LRA=11,alimiter=limit=0.84:level=false", "-ar", str(SR), "-shortest", "-movflags", "+faststart", tmp],
                   check=True)
    os.replace(tmp, video)
    print("sfx ->", video, f"({count} cues)")


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    add(next((a for a in sys.argv[1:] if a.endswith(".json")), os.path.join(here, "..", "promo2", "storyboard.json")))
