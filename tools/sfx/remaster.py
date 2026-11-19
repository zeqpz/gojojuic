"""Remaster every shipped sound effect crisp (owner, 2026-11-18: "low quality and muffled").

Why they were dull: Seed Audio renders at 24 kHz, so nothing in them goes above ~11 kHz (measured: 99% of the energy
of most sets sits under 10 kHz, some under 2 kHz). This rebuilds each at 48 kHz:
  1. resample to 48 kHz;
  2. bandwidth extension: the 3-11 kHz band is driven through a soft saturator, which makes the harmonics the
     recording never had; only the part above 10.5 kHz is kept and mixed back in (an "exciter"), so the top end
     comes back without touching the body;
  3. EQ: -2.5 dB at 280 Hz (the boxy, muddy part) and a +3.5 dB high shelf from 6 kHz;
  4. a short transient lift on the first 25 ms (clicks, cuts and hits read sharper);
  5. peak -1 dBFS, Vorbis at high quality.
The originals are kept once in art/raw/audio/sfx_orig/ and every run starts from them, so it can be retuned.

    .venv/Scripts/python tools/sfx/remaster.py [name-prefix ...]
"""
import glob, os, shutil, sys
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfiltfilt, sosfilt, resample_poly, lfilter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SFX = os.path.join(ROOT, "frontend", "assets", "sfx")
ORIG = os.path.join(ROOT, "art", "raw", "audio", "sfx_orig")
SR = 48000

# how much new top end each kind gets (0 = EQ only): the bassy ones stay round, the cuts and chimes get the most
AIR = {"slice": .34, "swoosh": .32, "sword_draw": .36, "frost": .30, "star_ping": .28, "coin_tick": .25,
       "line_win": .26, "multiplier": .26, "fuse": .22, "big_win": .26, "frenzy_start": .24, "combo": .24,
       "gong": .22, "cam_whoosh": .22, "riser": .24, "drop": .16, "clack": .32, "ui_click": .32,
       "boom": .06, "impact": .10, "taiko": .10, "bump": .08, "heartbeat": 0, "slowmo_in": .06, "slowmo_out": .10}
SHELF = {"heartbeat": 1.0, "boom": 2.0, "bump": 2.0, "slowmo_in": 2.0}            # dB, default 3.5
TRANSIENT = {"slice": 1.35, "sword_draw": 1.3, "clack": 1.4, "ui_click": 1.4, "coin_tick": 1.25, "bump": 1.2,
             "taiko": 1.2, "impact": 1.15}


def kind(name):
    for k in sorted(AIR, key=len, reverse=True):
        if name.startswith(k): return k
    return None


def biquad(kind_, f0, gain_db, q=.707):
    """RBJ cookbook peaking / high-shelf coefficients at SR."""
    A, w = 10 ** (gain_db / 40), 2 * np.pi * f0 / SR
    cw, sw = np.cos(w), np.sin(w)
    if kind_ == "peak":
        al = sw / (2 * q)
        b = [1 + al * A, -2 * cw, 1 - al * A]; a = [1 + al / A, -2 * cw, 1 - al / A]
    else:                                                  # high shelf, slope 1
        al = sw / 2 * np.sqrt(2)
        b = [A * ((A + 1) + (A - 1) * cw + 2 * np.sqrt(A) * al), -2 * A * ((A - 1) + (A + 1) * cw),
             A * ((A + 1) + (A - 1) * cw - 2 * np.sqrt(A) * al)]
        a = [(A + 1) - (A - 1) * cw + 2 * np.sqrt(A) * al, 2 * ((A - 1) - (A + 1) * cw),
             (A + 1) - (A - 1) * cw - 2 * np.sqrt(A) * al]
    return np.array(b) / a[0], np.array(a) / a[0]


def process(x, sr, k):
    if x.ndim > 1: x = x.mean(axis=1)
    x = x.astype(np.float64)
    if sr != SR:
        g = np.gcd(SR, sr); x = resample_poly(x, SR // g, sr // g)
    amt = AIR.get(k, .2)
    if amt > 0 and len(x) > 256:
        band = sosfiltfilt(butter(4, [3000, 11000], "bandpass", fs=SR, output="sos"), x)
        pk = np.abs(band).max()
        if pk > 1e-5:
            b = band / pk
            harm = .65 * np.tanh(3.2 * b) + .35 * (np.abs(b) - np.abs(b).mean())     # odd + even harmonics
            air = sosfiltfilt(butter(6, 10500, "highpass", fs=SR, output="sos"), harm)
            br, ar = np.sqrt((band ** 2).mean()), np.sqrt((air ** 2).mean())
            if ar > 1e-9: x = x + air * (br / ar) * amt
    bb, aa = biquad("peak", 280, -2.5, 1.0); x = lfilter(bb, aa, x)
    bb, aa = biquad("shelf", 6000, SHELF.get(k, 3.5)); x = lfilter(bb, aa, x)
    t = TRANSIENT.get(k)
    if t:
        n = min(len(x), int(SR * .025))
        x[:n] *= np.linspace(t, 1, n)
    n = min(len(x) // 3, int(SR * .004)); x[:n] *= np.linspace(0, 1, n)
    n = min(len(x) // 3, int(SR * .03)); x[-n:] *= np.linspace(1, 0, n)
    return (x / (np.abs(x).max() or 1) * 10 ** (-1 / 20)).astype(np.float32)


if __name__ == "__main__":
    os.makedirs(ORIG, exist_ok=True)
    for f in glob.glob(os.path.join(SFX, "*.ogg")):            # keep the originals once
        o = os.path.join(ORIG, os.path.basename(f))
        if not os.path.exists(o): shutil.copy2(f, o)
    want = sys.argv[1:]
    for o in sorted(glob.glob(os.path.join(ORIG, "*.ogg"))):
        name = os.path.basename(o)[:-4]
        if want and not any(name.startswith(w) for w in want): continue
        if not os.path.exists(os.path.join(SFX, name + ".ogg")): continue      # dropped from the game since
        x, sr = sf.read(o, dtype="float32")
        y = process(x, sr, kind(name))
        sf.write(os.path.join(SFX, name + ".ogg"), y, SR, format="OGG", subtype="VORBIS", compression_level=.15)
        X = np.abs(np.fft.rfft(y)) ** 2; fr = np.fft.rfftfreq(len(y), 1 / SR)
        print(f"{name:16s} {kind(name) or '-':12s} >8k {100 * X[fr > 8000].sum() / X.sum():5.1f}%  >12k {100 * X[fr > 12000].sum() / X.sum():5.2f}%")
