"""Synthesised accent layers (44.1 kHz mono, noise-free by construction) mixed onto the special-fruit slices by
jd.py's 'accent' op, so each one's identity is certain: the star fruit's magic sparkle, the peach's rising
power-up zap, the gold melon's coin shimmer. Each returns a mono float array peaking at 1."""
import os, sys
import numpy as np
from scipy import signal

sys.path.insert(1, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
                                "fallslotsga", "tools", "sfx"))
import synth                                                    # noqa: E402  (fallslotsga's sparkle / ping)

SR = 44100


def _norm(x):
    return x / (np.abs(x).max() + 1e-12)


def sparkle(seed=0):
    """A rising run of glassy bell pings (C7 pentatonic) over a faint air shimmer, ~0.6 s."""
    st = synth.sparkle(seed, count=7, spread=.30, dur=.75, rising=True)
    return _norm(st.mean(1))


def zap(seed=0, dur=.32):
    """A power-up: a bright tone gliding up ~2 octaves with a fast buzzy tremolo, a sparkle ping on top at the end."""
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 420 * (2 ** (2.2 * (t / dur) ** 1.4)) * (1 + rng.uniform(-.03, .03))
    ph = 2 * np.pi * np.cumsum(f) / SR
    tone = np.sin(ph) + .45 * np.sin(2 * ph) + .25 * np.sin(3 * ph) + .12 * np.sin(5 * ph)
    trem = .75 + .25 * np.sin(2 * np.pi * 34 * t)
    env = np.minimum(1, t / .006) * (.55 + .45 * t / dur) * np.minimum(1, (dur - t) / .06)
    y = tone * trem * env
    y = signal.sosfilt(signal.butter(2, 9000, "lowpass", fs=SR, output="sos"), y)
    tail = np.zeros(n + int(.35 * SR))
    tail[:n] = _norm(y)
    p = synth.ping(f[-1] * 2, .09, int(.35 * SR), bright=1.2)
    tail[n - int(.02 * SR):n - int(.02 * SR) + len(p)] += .55 * _norm(p)
    return _norm(tail)


def coins(seed=0, count=9, spread=.28):
    """A soft shimmer of small gold coins: short metallic pings (inharmonic coin partials), randomly spaced."""
    rng = np.random.default_rng(seed)
    n = int((spread + .3) * SR)
    buf = np.zeros(n)
    t = np.arange(int(.3 * SR)) / SR
    for k in range(count):
        f = rng.uniform(3000, 5200)
        tau = rng.uniform(.04, .11)
        att = np.minimum(1, t / .0005)
        x = (np.sin(2 * np.pi * f * t) + .5 * np.sin(2 * np.pi * f * 1.51 * t + 1) * np.exp(-t / (tau * .6))
             + .3 * np.sin(2 * np.pi * f * 2.33 * t + 2) * np.exp(-t / (tau * .4))) * np.exp(-t / tau) * att
        at = int((rng.random() ** 1.2) * spread * SR)
        buf[at:at + len(x)] += x[:n - at] * rng.uniform(.4, 1.0) * (1 - .4 * k / count)
    return _norm(buf)
