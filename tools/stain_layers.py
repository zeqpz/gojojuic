"""Juice Dojo wall stains: turn the glossy juice sprites (frontend/assets/fx/splat1-4, drip1-4 - OpenRouter renders of
liquid in grey) into the layers the game composites for a realistic wet stain on the wood.

    python tools/stain_layers.py        (numpy + Pillow; ~2 s)

frontend/assets/fx/stain_<name>.webp - three tiles side by side, each the sprite's size, white with alpha:
  density  how much juice lies at each point: a thin film where it is thin (fingers, droplets), deep where it pools,
           the render's own ripples kept in it as texture (its highlights read as thinner, its shading as deeper),
           and a darker rim where drying juice gathers (the coffee-ring effect). The game tints it with the juice
           colour and MULTIPLIES it into the wood (#stain blends with mix-blend-mode: multiply), so the grain shows
           through the stain.
  glint    the render's own specular highlights (its brightest 5%: the render is light grey all over) - laid on
           while the stain is wet
  height   where the juice stands thick (pools, big drops; thin fingers and films ~0), soft-edged - the game lights
           the wet stain from it in screen space (fxkit.js): a bright rim where the thick juice faces the room's
           light (top left), a dark rim where it turns away
frontend/assets/fx/stains.json - for each drip: where its strand runs (centre and width per row, 64 rows), so the
           bead leading a running drip follows the strand.
"""
import json
import os

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FX = os.path.join(ROOT, "frontend", "assets", "fx")
NAMES = [f"splat{i}" for i in range(1, 5)] + [f"drip{i}" for i in range(1, 5)]


def box(a, r, axis):
    """Mean over a window of 2r+1 along one axis (edges clamped)."""
    if r < 1:
        return a
    pad = [(0, 0)] * a.ndim
    pad[axis] = (r + 1, r)
    c = np.cumsum(np.pad(a, pad, mode="edge"), axis=axis)
    n = a.shape[axis]
    hi = np.take(c, np.arange(2 * r + 1, 2 * r + 1 + n), axis=axis)
    lo = np.take(c, np.arange(0, n), axis=axis)
    return (hi - lo) / (2 * r + 1)


def blur(a, sigma):
    """Three box passes: close to a gaussian of this sigma."""
    r = max(1, int(round(sigma * 0.9)))
    for _ in range(3):
        a = box(box(a, r, 0), r, 1)
    return a


def layers(path):
    im = np.asarray(Image.open(path).convert("RGBA")).astype(np.float32) / 255.0
    A = im[..., 3]
    L = np.where(A > 0.02, im[..., 0] * 0.3 + im[..., 1] * 0.59 + im[..., 2] * 0.11, 0.0)
    # the render's local brightness against its neighbourhood (inside the liquid only): its ripples and glints
    local = blur(L * A, 4) / np.maximum(blur(A, 4), 1e-3)
    ripple = np.where(A > 0.02, L - local, 0.0)
    pool = np.clip(blur(A, 7) * 1.25, 0, 1)                       # 1 deep inside a pool, low on fingers and droplets
    dens = A * (0.42 + 0.5 * pool) * np.clip(1.0 - 0.9 * ripple, 0.55, 1.35)
    ring = A * np.clip((1.0 - blur(A, 2)) * 2.4, 0, 1)            # the rim
    dens = np.clip(dens + 0.3 * ring, 0, 1)
    inside = L[A > 0.5]
    lo, hi = (np.percentile(inside, 95), np.percentile(inside, 99.6)) if inside.size else (0.9, 1.0)
    glint = A * np.clip((L - lo) / max(hi - lo, 0.02), 0, 1) ** 1.2
    thick = blur(A, 4) * 1.2                                        # high in pools and big drops
    t = np.clip((thick - 0.35) / 0.45, 0, 1)
    height = A * t * t * (3 - 2 * t)
    return dens, glint, height


def strand(A, rows=64):
    """Per row band: the centre and width (fractions of the sprite width) of the widest run of liquid."""
    h, w = A.shape
    cx, wd = [], []
    for i in range(rows):
        band = A[int(i * h / rows):max(int(i * h / rows) + 1, int((i + 1) * h / rows))].max(axis=0) > 0.5
        best, run, start = (0, 0), 0, 0
        for x in range(w + 1):
            if x < w and band[x]:
                if run == 0:
                    start = x
                run += 1
            else:
                if run > best[1]:
                    best = (start, run)
                run = 0
        if best[1]:
            cx.append(round((best[0] + best[1] / 2) / w, 4))
            wd.append(round(best[1] / w, 4))
        else:
            cx.append(cx[-1] if cx else 0.5)
            wd.append(0.0)
    return cx, wd


def main():
    meta = {}
    for n in NAMES:
        dens, glint, height = layers(os.path.join(FX, f"{n}.webp"))
        A = np.asarray(Image.open(os.path.join(FX, f"{n}.webp")).convert("RGBA")).astype(np.float32)[..., 3] / 255.0
        h, w = A.shape
        out = np.zeros((h, w * 3, 4), np.float32)
        out[..., :3] = 1.0
        out[:, :w, 3], out[:, w:2 * w, 3], out[:, 2 * w:, 3] = dens, glint, height
        Image.fromarray((out * 255 + 0.5).clip(0, 255).astype(np.uint8), "RGBA").save(
            os.path.join(FX, f"stain_{n}.webp"), "WEBP", quality=90, alpha_quality=95, method=6)
        if n.startswith("drip"):
            cx, wd = strand(A)
            meta[n] = {"cx": cx, "w": wd}
        print(n, f"{w}x{h}", f"{os.path.getsize(os.path.join(FX, f'stain_{n}.webp')) / 1024:.0f} KiB")
    with open(os.path.join(FX, "stains.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh)


if __name__ == "__main__":
    main()
