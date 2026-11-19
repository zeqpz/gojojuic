"""Pack the outdoor Japan scene (tools/gen_scene.py -> art/raw/scene/*.png) into frontend/assets/scene/*.webp.

Layers (owner, 2026-11-18): background = sky / sky_tall (the far landscape, no floor), midground = tree, pine and
three drifting clouds (cut-outs), foreground = board (the wooden board the fruit are cut on; the juice stains are
clipped to it). Cut-outs are trimmed to their opaque bounds; clouds.png is split into cloud1..3. The board's inner
plank area (inside its frame) is measured and written to scene.json so the grid sits on the planks."""
import json, os
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "art", "raw", "scene")
DST = os.path.join(ROOT, "frontend", "assets", "scene")

SPEC = {"sky": (1920, 1080, False), "sky_tall": (1080, 1920, False),
        "tree": (700, 1050, True), "pine": (700, 1050, True), "board": (1200, 1200, True)}


def trim(im):
    a = im.split()[-1].point(lambda v: 255 if v > 8 else 0)
    return im.crop(a.getbbox())


def save(im, name, mw, mh, opaque=False):
    k = min(mw / im.width, mh / im.height, 1.0 if not opaque else 99)
    im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    out = os.path.join(DST, name + ".webp")
    (im.convert("RGB") if opaque else im).save(out, "WEBP", quality=86 if opaque else 90, method=6)
    print(name, im.size, os.path.getsize(out) // 1024, "KB")
    return im


os.makedirs(DST, exist_ok=True)
meta = {}
for name, (mw, mh, cut) in SPEC.items():
    im = Image.open(os.path.join(SRC, name + ".png")).convert("RGBA")
    if cut: im = trim(im)
    im = save(im, name, mw, mh, opaque=not cut)
    meta[name] = {"w": im.width, "h": im.height}

# clouds: split at the fully transparent columns between them
cl = Image.open(os.path.join(SRC, "clouds.png")).convert("RGBA")
alpha = cl.split()[-1]
cols = [max(alpha.crop((x, 0, x + 1, cl.height)).getdata()) > 8 for x in range(cl.width)]
runs, start = [], None
for x, on in enumerate(cols + [False]):
    if on and start is None: start = x
    if not on and start is not None:
        if x - start > 40: runs.append((start, x))
        start = None
for i, (x0, x1) in enumerate(runs[:3], 1):
    im = save(trim(cl.crop((x0, 0, x1, cl.height))), f"cloud{i}", 640, 400)
    meta[f"cloud{i}"] = {"w": im.width, "h": im.height}

# the board's planks: scan the middle row and column for where the darker frame ends
b = Image.open(os.path.join(DST, "board.webp")).convert("L")
w, h = b.size
row = [b.getpixel((x, h // 2)) for x in range(w)]
col = [b.getpixel((w // 2, y)) for y in range(h)]


def inner(line):
    n = len(line); mid = sorted(line[n // 3: 2 * n // 3])[len(line[n // 3: 2 * n // 3]) // 2]
    lo = next(i for i in range(n // 3) if all(v > mid * .78 for v in line[i:i + 6]) and i > n * .03)
    hi = next(i for i in range(n - 1, 2 * n // 3, -1) if all(v > mid * .78 for v in line[i - 6:i]) and i < n * .97)
    return lo / n, hi / n


ix, iy = inner(row), inner(col)
meta["board"]["inner"] = {"x0": round(ix[0], 4), "x1": round(ix[1], 4), "y0": round(iy[0], 4), "y1": round(iy[1], 4)}
print("board inner", meta["board"]["inner"])
with open(os.path.join(DST, "scene.json"), "w") as fh:
    json.dump(meta, fh, indent=1)
