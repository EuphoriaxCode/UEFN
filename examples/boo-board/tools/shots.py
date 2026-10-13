"""Burst-capture the editor viewport (materials animate in the editor) -> contact sheet.
    py -3.14 shots.py out.jpg [n] [interval] [--at x,y,z --look x,y,z]"""
import os, sys, time, subprocess
from PIL import Image, ImageDraw
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
out = sys.argv[1]
n = int(sys.argv[2]) if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else 12
iv = float(sys.argv[3]) if len(sys.argv) > 3 and not sys.argv[3].startswith("--") else 0.8
at = sys.argv[sys.argv.index("--at") + 1] if "--at" in sys.argv else "780,0,300"
look = sys.argv[sys.argv.index("--look") + 1] if "--look" in sys.argv else "0,0,290"
tmp = os.path.join(os.environ["TEMP"], "bb_shots"); os.makedirs(tmp, exist_ok=True)
frames = []
t0 = time.time()
for i in range(n):
    p = os.path.join(tmp, f"s{i:02d}.png")
    subprocess.run([sys.executable, os.path.join(REPO, "cli", "uefn.py"), "shot", p, "--at", at, "--look", look],
                   capture_output=True)
    frames.append((time.time() - t0, p))
    dt = iv - ((time.time() - t0) - i * iv)
    if dt > 0: time.sleep(dt)
ims = [Image.open(p).convert("RGB") for _, p in frames]
w, h = ims[0].size
sc = 480 / w
cols = 4
rows = (len(ims) + cols - 1) // cols
sheet = Image.new("RGB", (int(w * sc) * cols, int(h * sc) * rows))
for i, ((t, _), im) in enumerate(zip(frames, ims)):
    im = im.resize((int(w * sc), int(h * sc)))
    ImageDraw.Draw(im).text((6, 6), f"{t:.1f}s", fill=(255, 255, 0))
    sheet.paste(im, ((i % cols) * int(w * sc), (i // cols) * int(h * sc)))
sheet.save(out, quality=88)
print(out, [round(t, 1) for t, _ in frames])
