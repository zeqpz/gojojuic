"""Pack Blender frames into one WebP sheet per fruit for the game.

    python tools/pack_sprites.py            # every ID found in art/blender/frames
    python tools/pack_sprites.py H1 SC      # just these

Sheet layout (frontend/assets/fruit/<ID>.webp): CELL x CELL tiles, 8 per row; row 0-1 the whole
fruit's 16-frame tumble, rows 2-3 the half's (absent for the bomb). Writes frontend/assets/fruit/meta.json
with the cell size, frame counts and each tile's opaque bounds (for hit radii and juice colour).
Also writes art/blender/contact.png, every sheet on one dark page, for checking."""
import json
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "art", "blender", "frames")
OUT = os.path.join(ROOT, "frontend", "assets", "fruit")
CELL = 224
COLS = 8

# the colour juice splashes in, per fruit (sampled by eye from the inside materials)
JUICE = {"H1": "#ff3b4e", "H2": "#ffd23a", "H3": "#ffffff", "H4": "#f4f7ff", "L1": "#ff9a12", "L2": "#fff3c4",
         "L3": "#fff27a", "L4": "#7fd61f", "SC": "#ffe24a", "PW2": "#5ab4ff", "PW3": "#c56bff", "PW5": "#ff6a3a",
         "FRZ": "#bfeaff", "JM": "#ffd700", "BOMB": "#ffffff"}


def frames(ID, clip):
    d = os.path.join(SRC, ID)
    names = sorted(f for f in os.listdir(d) if f.startswith(clip + "_") and f.endswith(".png"))
    return [Image.open(os.path.join(d, f)).convert("RGBA") for f in names]


def pack(ID):
    whole, half = frames(ID, "whole"), frames(ID, "half")
    rows = 2 + (2 if half else 0)
    sheet = Image.new("RGBA", (CELL * COLS, CELL * rows), (0, 0, 0, 0))
    for base, seq in ((0, whole), (2, half)):
        for i, im in enumerate(seq):
            im = im.resize((CELL, CELL), Image.LANCZOS)
            sheet.paste(im, ((i % COLS) * CELL, (base + i // COLS) * CELL))
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"{ID}.webp")
    sheet.save(path, "WEBP", quality=88, method=6, alpha_quality=95)
    a = whole[0].split()[3].getbbox() or (0, 0, 1, 1)
    s = CELL / whole[0].width
    return sheet, {"whole": len(whole), "half": len(half), "bbox": [round(v * s) for v in a],
                   "juice": JUICE.get(ID, "#ffffff"), "bytes": os.path.getsize(path)}


def main(ids):
    meta_path = os.path.join(OUT, "meta.json")
    meta = {"cell": CELL, "cols": COLS, "fruit": {}}
    if os.path.exists(meta_path):
        with open(meta_path, encoding="utf-8") as fh:
            meta["fruit"] = json.load(fh).get("fruit", {})
    sheets = []
    for ID in ids:
        sheet, m = pack(ID)
        meta["fruit"][ID] = m
        sheets.append(sheet)
        print(f"{ID}: {m['whole']}+{m['half']} frames, {m['bytes'] / 1024:.0f} KiB")
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=1)
    # contact sheet: the first 8 frames of the whole and half of each, small
    t = 96
    page = Image.new("RGBA", (t * 16, t * len(sheets)), (24, 20, 22, 255))
    for r, sh in enumerate(sheets):
        for k in range(16):
            row = 0 if k < 8 else 2
            if row >= sh.height // CELL:
                continue
            tile = sh.crop(((k % 8) * CELL, row * CELL, (k % 8 + 1) * CELL, (row + 1) * CELL)).resize((t, t), Image.LANCZOS)
            page.alpha_composite(tile, (k * t, r * t))
    page.save(os.path.join(ROOT, "art", "blender", "contact.png"))


if __name__ == "__main__":
    ids = sys.argv[1:] or sorted(os.listdir(SRC))
    main(ids)
