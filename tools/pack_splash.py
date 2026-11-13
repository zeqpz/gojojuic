"""Pack the splash FX for the game.

    python tools/pack_splash.py

- frontend/assets/fx/drip1-4.webp, splat1-4.webp   glossy greyscale juice (OpenRouter, art/raw/DRIP*, GSPLAT*); the
                                                    game tints them per fruit and keeps the gloss
- frontend/assets/fx/burst<V>.webp                  the Blender metaball juice burst (art/blender/splash), frames in a
                                                    row-major grid, greyscale
- frontend/assets/fx/boom.webp                      the Blender volumetric bomb explosion (art/blender/explosion)
- frontend/assets/fx/fx.json                        cell sizes and frame counts
"""
import glob
import json
import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "art", "raw")
FX = os.path.join(ROOT, "frontend", "assets", "fx")


def save(im, path, q=88):
    im.save(path, "WEBP", quality=q, alpha_quality=92, method=6)


def stamps():
    for k in range(1, 5):
        for src, dst, box in ((f"DRIP{k}.png", f"drip{k}.webp", (160, 420)), (f"GSPLAT{k}.png", f"splat{k}.webp", (360, 360))):
            p = os.path.join(RAW, src)
            if not os.path.exists(p):
                continue
            im = Image.open(p).convert("RGBA")
            im = im.crop(im.getbbox())
            im.thumbnail(box, Image.LANCZOS)
            save(im, os.path.join(FX, dst))
            print(dst, im.size)


def sheet(frames, cell, cols, dst):
    rows = (len(frames) + cols - 1) // cols
    out = Image.new("RGBA", (cell * cols, cell * rows), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        im = Image.open(f).convert("RGBA").resize((cell, cell), Image.LANCZOS)
        out.paste(im, ((i % cols) * cell, (i // cols) * cell))
    save(out, os.path.join(FX, dst), 86)
    print(dst, out.size, len(frames), "frames")
    return {"cell": cell, "cols": cols, "frames": len(frames)}


def main():
    os.makedirs(FX, exist_ok=True)
    stamps()
    meta = {}
    for v in range(1, 6):
        fr = sorted(glob.glob(os.path.join(ROOT, "art", "blender", "splash", f"burst{v}_*.png")))
        if fr:
            meta[f"burst{v}"] = sheet(fr, 192, 6, f"burst{v}.webp")
    fr = sorted(glob.glob(os.path.join(ROOT, "art", "blender", "explosion", "boom_*.png")))
    if fr:
        meta["boom"] = sheet(fr, 256, 6, "boom.webp")
    with open(os.path.join(FX, "fx.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=1)


if __name__ == "__main__":
    main()
