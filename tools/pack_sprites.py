"""Pack Blender frames into one WebP sheet per fruit for the game.

    python tools/pack_sprites.py            # every ID found in art/blender/frames
    python tools/pack_sprites.py H1 SC      # just these
    python tools/pack_sprites.py --q=84     # WebP quality (default QUALITY)

Sheet layout (frontend/assets/fruit/<ID>.webp): CELL x CELL tiles, COLS per row, clips back to back:
  whole  the 64-frame tumble, one full turn (the game crossfades between frames, so it turns smoothly)
  wob    the right half rocking, 24 frames (its roll is done in 2D; the left half is the same, mirrored)
  openR  the right half opening on a slice, 8 frames (frame 0 + openL frame 0 = the whole fruit)
  openL  the left half opening, 8 frames
frontend/assets/fruit/meta.json: {"cell", "cols", "fruit": {ID: {"clips": {name: [first tile, count]}, "bbox",
"juice", "bytes", "track"?}}}. Also writes art/blender/contact.png (every 4th tumble frame, every 4th wob frame and
the openings, one row per fruit) and prints a QA line per fruit: the mean step between neighbouring frames, the
loop seam (last -> first) against it, the biggest framing jump (alpha-centroid shift, px) and any empty frames."""
import json
import math
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "art", "blender", "frames")
OUT = os.path.join(ROOT, "frontend", "assets", "fruit")
CELL = 192
COLS = 8
CLIPS = ("whole", "wob", "openR", "openL")
QUALITY = 86

# the colour juice splashes in, per fruit (sampled by eye from the inside materials)
JUICE = {"H1": "#ff3b4e", "H2": "#ffd23a", "H3": "#ffffff", "H4": "#f4f7ff", "L1": "#ff9a12", "L2": "#fff3c4",
         "L3": "#fff27a", "L4": "#7fd61f", "SC": "#ffe24a", "PW2": "#5ab4ff", "PW3": "#c56bff", "PW5": "#ff6a3a",
         "FRZ": "#bfeaff", "JM": "#ffd700", "BOMB": "#ffffff"}


def frames(ID, clip):
    d = os.path.join(SRC, ID)
    names = sorted(f for f in os.listdir(d) if f.startswith(clip + "_") and f.endswith(".png"))
    return [Image.open(os.path.join(d, f)).convert("RGBA") for f in names]


def qa(ID, seqs):
    """Numbers for the owner's QA rule: a loop seam much bigger than the average step, a framing jump or a blank
    frame shows here before anyone has to spot it by eye."""
    import numpy as np
    out = []
    for name, seq in seqs:
        if not seq:
            continue
        arr = [np.asarray(im.resize((96, 96), Image.BILINEAR), dtype=np.float32) for im in seq]
        diff = lambda a, b: float(np.abs(a - b).mean())
        steps = [diff(arr[i], arr[i + 1]) for i in range(len(arr) - 1)]
        cen = []
        empty = 0
        for a in arr:
            al = a[..., 3]
            if al.sum() < 1:
                empty += 1
                cen.append((48.0, 48.0))
                continue
            ys, xs = np.mgrid[0:96, 0:96]
            cen.append((float((xs * al).sum() / al.sum()), float((ys * al).sum() / al.sum())))
        jump = max(math.hypot(cen[i + 1][0] - cen[i][0], cen[i + 1][1] - cen[i][1]) for i in range(len(cen) - 1)) * (CELL / 96)
        line = f"{name} n={len(seq)} step {np.mean(steps):.2f} (max {max(steps):.2f})"
        if name in ("whole", "wob"):
            line += f" seam {diff(arr[-1], arr[0]):.2f}"
        line += f" jump {jump:.1f}px" + (f" EMPTY {empty}" if empty else "")
        out.append(line)
    print(f"  QA {ID}: " + " | ".join(out))


def pack(ID, quality=QUALITY):
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
    sheet.save(path, "WEBP", quality=quality, method=6)
    qa(ID, seqs)
    first = seqs[0][1][0]
    a = first.split()[3].getbbox() or (0, 0, 1, 1)
    s = CELL / first.width
    m = {"clips": clips, "bbox": [round(v * s) for v in a], "juice": JUICE.get(ID, "#ffffff"), "bytes": os.path.getsize(path)}
    tr = os.path.join(SRC, ID, "track.json")          # points the FX follow (the bomb's fuse spark), from fruitkit's track step
    if os.path.exists(tr):
        m["track"] = json.load(open(tr, encoding="utf-8"))
    return sheet, clips, m


def main(ids, quality=QUALITY):
    meta_path = os.path.join(OUT, "meta.json")
    meta = {"cell": CELL, "cols": COLS, "fruit": {}}
    if os.path.exists(meta_path):
        old = json.load(open(meta_path, encoding="utf-8"))
        if old.get("cell") == CELL:
            meta["fruit"] = old.get("fruit", {})
    shown = []
    for ID in ids:
        sheet, clips, m = pack(ID, quality)
        meta["fruit"][ID] = m
        shown.append((sheet, clips))
        print(f"{ID}: {', '.join(f'{k} {v[1]}' for k, v in clips.items())}  {m['bytes'] / 1024:.0f} KiB")
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=1)
    # contact sheet: every 4th tumble and wob frame, the openings at 0, 1/3, 2/3, end - one row per fruit, on a
    # dark wood tone like the game's wall, with a gap between clips
    from PIL import ImageDraw
    t, lab = 96, 52
    pick = {"whole": 4, "wob": 4, "openR": None, "openL": None}
    def frames_of(name, n):
        return list(range(0, n, pick[name])) if pick[name] else sorted({0, n // 3, (2 * n) // 3, n - 1})
    width = max(sum(len(frames_of(nm, cl[nm][1])) for nm in CLIPS if nm in cl) * t + 12 * 3 for _, cl in shown) + lab
    page = Image.new("RGBA", (width, t * len(shown)), (46, 29, 17, 255))
    d = ImageDraw.Draw(page)
    for y in range(0, page.height, 6):
        d.line([(0, y), (page.width, y + 2)], fill=(52 + (y * 37) % 14, 33 + (y * 13) % 8, 19, 255))
    for r, ((sh, clips), ID) in enumerate(zip(shown, ids)):
        d.text((6, r * t + t // 2 - 6), ID, fill=(255, 235, 200, 255))
        x = lab
        for name in CLIPS:
            if name not in clips:
                continue
            first, n = clips[name]
            for k in frames_of(name, n):
                tile = first + k
                im = sh.crop(((tile % COLS) * CELL, (tile // COLS) * CELL, (tile % COLS + 1) * CELL, (tile // COLS + 1) * CELL))
                page.alpha_composite(im.resize((t, t), Image.LANCZOS), (x, r * t))
                x += t
            x += 12
    page.save(os.path.join(ROOT, "art", "blender", "contact.png"))


if __name__ == "__main__":
    q = next((int(a[4:]) for a in sys.argv[1:] if a.startswith("--q=")), QUALITY)
    ids = [a for a in sys.argv[1:] if not a.startswith("--")] or sorted(d for d in os.listdir(SRC) if not d.startswith("_"))
    main(ids, q)
