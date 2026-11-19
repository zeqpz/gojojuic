"""Pack the 2000s fruit-machine scene (tools/gen_scene.py wall2k / wall2k_tall / lantern2k -> art/raw/scene) into
frontend/assets/scene/casino.webp, casino_tall.webp and lantern2.webp, and write the marquee bulbs' positions
(fractions of each image, found as the bright blobs along its top beam) to casino.json for the chase lights."""
import json, os
import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "art", "raw", "scene")
DST = os.path.join(ROOT, "frontend", "assets", "scene")


def bulbs(path, band):
    im = np.asarray(Image.open(path).convert("RGB")).astype(float)
    h, w, _ = im.shape
    lab, k = ndimage.label(im[: int(h * band)].mean(axis=2) > 235)
    out = []
    for i in range(1, k + 1):
        m = lab == i
        if m.sum() < 40: continue
        cy, cx = ndimage.center_of_mass(m)
        out.append([round(cx / w, 4), round(cy / h, 4), round(float(np.sqrt(m.sum() / np.pi)) / w, 4)])
    # keep the row: the blobs sharing the most common height (the side lanterns sit lower)
    ys = np.array([p[1] for p in out])
    row = np.median(ys[np.abs(ys - np.median(ys)) < .01])
    keep = [p for p in out if abs(p[1] - row) < .006]
    # and the same size: a painted lantern's glow at the beam's ends reads as a bigger blob
    r = np.median([p[2] for p in keep])
    return sorted([p for p in keep if p[2] < r * 1.18])


meta = {}
for src, dst, band in (("wall2k", "casino", .09), ("wall2k_tall", "casino_tall", .08)):
    im = Image.open(os.path.join(SRC, src + ".png")).convert("RGB")
    im.save(os.path.join(DST, dst + ".webp"), "WEBP", quality=88, method=6)
    meta[dst] = {"w": im.width, "h": im.height, "bulbs": bulbs(os.path.join(SRC, src + ".png"), band)}
    print(dst, im.size, os.path.getsize(os.path.join(DST, dst + ".webp")) // 1024, "KB", len(meta[dst]["bulbs"]), "bulbs")
lan = Image.open(os.path.join(SRC, "lantern2k.png")).convert("RGBA")
lan = lan.crop(lan.split()[-1].point(lambda v: 255 if v > 8 else 0).getbbox())
k = 520 / lan.height
lan = lan.resize((round(lan.width * k), 520), Image.LANCZOS)
lan.save(os.path.join(DST, "lantern2.webp"), "WEBP", quality=90, method=6)
print("lantern2", lan.size, os.path.getsize(os.path.join(DST, "lantern2.webp")) // 1024, "KB")
with open(os.path.join(DST, "casino.json"), "w") as fh:
    json.dump(meta, fh, indent=1)
