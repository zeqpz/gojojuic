"""Pack Blender frames into one WebP sheet per fruit for the game.

    python tools/pack_sprites.py            # every ID found in art/blender/frames
    python tools/pack_sprites.py H1 SC      # just these

Sheet layout (frontend/assets/fruit/<ID>.webp): CELL x CELL tiles, COLS per row, clips back to back:
  whole  the 32-frame tumble               (the game crossfades between frames, so it turns smoothly)
  wob    the right half rocking, 12 frames (its roll is done in 2D; the left half is the same, mirrored)
  openR  the right half opening on a slice, 8 frames (frame 0 + openL frame 0 = the whole fruit)
  openL  the left half opening, 8 frames
frontend/assets/fruit/meta.json: {"cell", "cols", "fruit": {ID: {"clips": {name: [first tile, count]}, "bbox",
"juice", "bytes", "track"?}}}. Also writes art/blender/contact.png (the first frames of every clip, small) for checking."""
import json
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "art", "blender", "frames")
OUT = os.path.join(ROOT, "frontend", "assets", "fruit")
CELL = 192
COLS = 8
CLIPS = ("whole", "wob", "openR", "openL")

# the colour juice splashes in, per fruit (sampled by eye from the inside materials)
JUICE = {"H1": "#ff3b4e", "H2": "#ffd23a", "H3": "#ffffff", "H4": "#f4f7ff", "L1": "#ff9a12", "L2": "#fff3c4",
         "L3": "#fff27a", "L4": "#7fd61f", "SC": "#ffe24a", "PW2": "#5ab4ff", "PW3": "#c56bff", "PW5": "#ff6a3a",
         "FRZ": "#bfeaff", "JM": "#ffd700", "BOMB": "#ffffff"}


def frames(ID, clip):
    d = os.path.join(SRC, ID)
    names = sorted(f for f in os.listdir(d) if f.startswith(clip + "_") and f.endswith(".png"))
    return [Image.open(os.path.join(d, f)).convert("RGBA") for f in names]


def pack(ID):
    seqs = [(c, frames(ID, c)) for c in CLIPS]
    total = sum(len(s) for _, s in seqs)
    rows = (total + COLS - 1) // COLS
    sheet = Image.new("RGBA", (CELL * COLS, CELL * rows), (0, 0, 0, 0))
    clips, t = {}, 0
    for name, seq in seqs:
        if not seq:
            continue
        clips[name] = [t, len(seq)]
        for im in seq:
            sheet.paste(im.resize((CELL, CELL), Image.LANCZOS), ((t % COLS) * CELL, (t // COLS) * CELL))
            t += 1
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"{ID}.webp")
    sheet.save(path, "WEBP", quality=88, method=6)
    first = seqs[0][1][0]
    a = first.split()[3].getbbox() or (0, 0, 1, 1)
    s = CELL / first.width
    m = {"clips": clips, "bbox": [round(v * s) for v in a], "juice": JUICE.get(ID, "#ffffff"), "bytes": os.path.getsize(path)}
    tr = os.path.join(SRC, ID, "track.json")          # points the FX follow (the bomb's fuse spark), from fruitkit's track step
    if os.path.exists(tr):
        m["track"] = json.load(open(tr, encoding="utf-8"))
    return sheet, clips, m


def main(ids):
    meta_path = os.path.join(OUT, "meta.json")
    meta = {"cell": CELL, "cols": COLS, "fruit": {}}
    if os.path.exists(meta_path):
        old = json.load(open(meta_path, encoding="utf-8"))
        if old.get("cell") == CELL:
            meta["fruit"] = old.get("fruit", {})
    shown = []
    for ID in ids:
        sheet, clips, m = pack(ID)
        meta["fruit"][ID] = m
        shown.append((sheet, clips))
        print(f"{ID}: {', '.join(f'{k} {v[1]}' for k, v in clips.items())}  {m['bytes'] / 1024:.0f} KiB")
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=1)
    # contact sheet: a few frames of each clip, small
    t = 80
    page = Image.new("RGBA", (t * 20, t * len(shown)), (24, 20, 22, 255))
    for r, (sh, clips) in enumerate(shown):
        x = 0
        for name in CLIPS:
            if name not in clips:
                continue
            first, n = clips[name]
            for k in range(0, n, max(1, n // 5)):
                tile = first + k
                im = sh.crop(((tile % COLS) * CELL, (tile // COLS) * CELL, (tile % COLS + 1) * CELL, (tile // COLS + 1) * CELL))
                page.alpha_composite(im.resize((t, t), Image.LANCZOS), (x * t, r * t))
                x += 1
                if x >= 20:
                    break
    page.save(os.path.join(ROOT, "art", "blender", "contact.png"))


if __name__ == "__main__":
    ids = sys.argv[1:] or sorted(os.listdir(SRC))
    main(ids)
