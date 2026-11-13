"""Pack the generated juicy glyphs and lettering for the game.

    python tools/pack_numerals.py

- frontend/assets/num/<name>.webp   one glyph per image, every one on the same canvas height with its foot on a
                                    common baseline (so a row of <img> stands on one line, as orleans' numerals do):
                                    digits at full height, the dot / comma small at the foot, x a little shorter.
- frontend/assets/num/w_<name>.webp the same glyphs in white (the fill whitened, the dark outline kept) for the
                                    frenzy counter painted on the wall.
- frontend/assets/win/*.webp        the win headlines (BIG / MEGA / EPIC / TOTAL WIN) and the juice-splash plaque.
- frontend/assets/bonus/wm_upto.webp, wm_waves.webp, ww_*.webp   the intro's and the counter's lettering.
"""
import os

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "art", "raw")
A = os.path.join(ROOT, "frontend", "assets")
CANVAS_H = 200          # every glyph image is this tall
DIGIT_H = 184           # a digit fills this much of it, foot on the bottom
SMALL = {"dot": .26, "comma": .4, "x": .6, "pct": .9}
PREFIX = "NF_"          # the arcade score set (NF_*, 2026-11-13); the first juicy set was NUM_*


def trim(path):
    im = Image.open(path).convert("RGBA")
    return im.crop(im.getbbox())


def whiten(im):
    """Keep the dark outline, turn the juicy fill into white with its shading kept as soft greys."""
    a = np.asarray(im).astype(np.float32)
    rgb, al = a[..., :3], a[..., 3:]
    lum = (rgb * [.299, .587, .114]).sum(-1, keepdims=True)
    t = np.clip((lum - 55) / 60, 0, 1)                       # 0 = outline, 1 = fill
    shade = 205 + (np.clip(lum, 90, 255) - 90) / 165 * 50     # the fill's own light and shadow, as greys
    out = rgb * (1 - t) + np.repeat(shade, 3, -1) * t
    return Image.fromarray(np.concatenate([np.clip(out, 0, 255), al], -1).astype(np.uint8), "RGBA")


def save(im, path, q=90):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path, "WEBP", quality=q, alpha_quality=95, method=6)


def glyphs():
    for name in [*"0123456789", "dot", "comma", "x", "pct", "dollar", "euro"]:
        src = os.path.join(RAW, f"{PREFIX}{name}.png")
        if not os.path.exists(src):
            print("missing", name)
            continue
        g = trim(src)
        h = int(DIGIT_H * SMALL.get(name, 1))
        g = g.resize((max(1, round(g.width * h / g.height)), h), Image.LANCZOS)
        c = Image.new("RGBA", (g.width + 8, CANVAS_H), (0, 0, 0, 0))
        drop = 10 if name == "comma" else 0                  # the comma hangs a little under the line
        c.alpha_composite(g, (4, CANVAS_H - h - 6 + drop if name == "comma" else CANVAS_H - h - 6))
        save(c, os.path.join(A, "num", f"{name}.webp"))
        save(whiten(c), os.path.join(A, "num", f"w_{name}.webp"))
        print("glyph", name, c.size)


def words():
    jobs = {"WM_BIGWIN": "win/big_win.webp", "WM_MEGAWIN": "win/mega_win.webp", "WM_EPICWIN": "win/epic_win.webp",
            "WM_TOTALWIN": "win/total_win.webp", "WM_UPTO": "bonus/wm_upto.webp", "WM_WAVES": "bonus/wm_waves.webp",
            "WW_WAVE": "bonus/ww_wave.webp", "WW_MULTI": "bonus/ww_multi.webp", "WW_BOMB": "bonus/ww_bomb.webp",
            "PLAQUE": "win/plaque.webp", "PAPER": "win/paper.webp", "NF_BOOM": "win/boom.webp",
            "NF_MULTI": "bonus/ww_multi.webp",
            # the win headlines in the angular display face (owner, 2026-11-13: like the reference GAME OVER)
            "NF_BIGWIN": "win/big_win.webp", "NF_MEGAWIN": "win/mega_win.webp", "NF_EPICWIN": "win/epic_win.webp",
            "NF_TOTALWIN": "win/total_win.webp"}
    for k, dst in jobs.items():
        src = os.path.join(RAW, f"{k}.png")
        if not os.path.exists(src):
            print("missing", k)
            continue
        im = trim(src)
        if k == "PLAQUE":       # the plaque is re-coloured to berry juice separately; leave it be
            continue
        im.thumbnail((1100, 600), Image.LANCZOS)
        save(im, os.path.join(A, dst))
        print("art", dst, im.size)


if __name__ == "__main__":
    glyphs()
    words()
