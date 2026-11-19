"""Pack the features screen's art (tools/gen_scene.py plate / icon_* -> art/raw/scene) into frontend/assets/features/.
The plate is trimmed to its outline and its dark inner panel is measured, so the CSS can keep the text inside it."""
import json, os
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "art", "raw", "scene")
DST = os.path.join(ROOT, "frontend", "assets", "features")
os.makedirs(DST, exist_ok=True)


def trim(im):
    a = im.split()[-1].point(lambda v: 255 if v > 8 else 0)
    return im.crop(a.getbbox())


meta = {}
plate = trim(Image.open(os.path.join(SRC, "plate.png")).convert("RGBA"))
k = 760 / plate.height
plate = plate.resize((round(plate.width * k), 760), Image.LANCZOS)
plate.save(os.path.join(DST, "plate.webp"), "WEBP", quality=90, method=6)
# the inner panel: the big near-black area in the middle (scan out from the centre along both axes)
a = np.asarray(plate.convert("RGB")).astype(float).mean(axis=2)
h, w = a.shape
dark = a < 45
cx, cy = w // 2, h // 2
row, col = dark[cy], dark[:, cx]
x0 = cx
while x0 > 0 and row[x0 - 1]: x0 -= 1
x1 = cx
while x1 < w - 1 and row[x1 + 1]: x1 += 1
y0 = cy
while y0 > 0 and col[y0 - 1]: y0 -= 1
y1 = cy
while y1 < h - 1 and col[y1 + 1]: y1 += 1
meta["plate"] = {"w": w, "h": h, "inner": {"left": round(x0 / w, 4), "right": round(1 - x1 / w, 4),
                                            "top": round(y0 / h, 4), "bottom": round(1 - y1 / h, 4)}}
print("plate", plate.size, meta["plate"]["inner"])
for n in ("icon_lines", "icon_frenzy", "icon_bomb"):
    im = trim(Image.open(os.path.join(SRC, n + ".png")).convert("RGBA"))
    s = 420 / max(im.size)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    im.save(os.path.join(DST, n.replace("icon_", "") + ".webp"), "WEBP", quality=90, method=6)
    print(n, im.size, os.path.getsize(os.path.join(DST, n.replace("icon_", "") + ".webp")) // 1024, "KB")
with open(os.path.join(DST, "features.json"), "w") as fh:
    json.dump(meta, fh, indent=1)
