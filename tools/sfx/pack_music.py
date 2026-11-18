"""Juice Dojo music (tools/sfx/gen_music.py -> art/raw/audio/calm_*.mp3) -> frontend/assets/music/{base,frenzy}.ogg
plus music.json, which the game's music director reads (owner, 2026-11-18: relaxing ninja music that changes with
the bonus icons, lines, wins and the bonus).

For each role it measures every take and keeps the calmest one that is steady enough to loop:
  * key: chroma (55 Hz - 2 kHz) against the Krumhansl-Kessler profiles -> tonic + major/minor;
  * tempo and beat phase: spectral-flux onsets, a coarse autocorrelation, then a fine comb search over BPM and
    phase across the whole song (so the beat grid holds for minutes);
  * calmness: how much the loudness swings and how busy the onsets are.
The loop starts on a beat and is cut to a whole number of bars, its tail crossfaded (equal power) into its head,
so the beat grid carries on across the loop point - the game quantises its in-key stingers to it.
Mastered quiet (RMS -21 dBFS, peaks under -1.5 dBFS) so it sits under the effects. 32 kHz stereo Vorbis.

    .venv/Scripts/python tools/sfx/pack_music.py
"""
import glob, json, os
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly, stft

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "art", "raw", "audio")
DST = os.path.join(ROOT, "frontend", "assets", "music")
ROLES = {"base": ("calm_base_*.mp3", 80), "frenzy": ("calm_bonus_*.mp3", 92)}    # role: (takes, BPM asked for)
XF, SR_OUT = 2.0, 32000
NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
KK_MAJ = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KK_MIN = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def read(path):            # (one big sf.read of an mp3 overflows the native stack on Windows: read in blocks)
    sr = sf.info(path).samplerate
    return np.concatenate(list(sf.blocks(path, blocksize=sr * 5, always_2d=True, dtype="float32"))), sr


def key_of(mono, sr):
    f, _, Z = stft(mono, sr, nperseg=8192, noverlap=4096)
    P = (np.abs(Z) ** 2).mean(axis=1)
    sel = (f > 55) & (f < 2000)
    pc = np.round(12 * np.log2(f[sel] / 261.6256)).astype(int) % 12
    chroma = np.bincount(pc, weights=np.sqrt(P[sel]), minlength=12)
    best = max(((np.corrcoef(np.roll(prof, t), chroma)[0, 1], t, m) for t in range(12)
                for m, prof in (("major", KK_MAJ), ("minor", KK_MIN))))
    return best[1], best[2], round(float(best[0]), 3)


def tempo_of(mono, sr, hint):
    hop = 256
    f, t, Z = stft(mono, sr, nperseg=1024, noverlap=1024 - hop)
    L = np.log1p(np.abs(Z) * 100)
    flux = np.maximum(0, np.diff(L, axis=1)).sum(axis=0)
    flux = flux - np.convolve(flux, np.ones(64) / 64, mode="same")       # local mean off: onsets stand out
    flux = np.maximum(0, flux)
    fps = sr / hop
    ac = np.correlate(flux, flux, mode="full")[len(flux) - 1:]
    lags = np.arange(len(ac)) / fps
    ok = (lags > 60 / 150) & (lags < 60 / 55)
    bpms = 60 / lags[ok]
    score = ac[ok] * np.exp(-((np.log2(bpms / hint)) ** 2) / (2 * .35 ** 2))  # prefer near the asked tempo
    coarse = float(bpms[np.argmax(score)])
    # fine comb: BPM +-2% in 0.01 steps, phase in 10 ms steps, over the whole song
    tt = np.arange(len(flux)) / fps
    best = (-1, coarse, 0.0)
    for bpm in np.arange(coarse * .98, coarse * 1.02, .01):
        P = 60 / bpm
        beats = np.arange(0, tt[-1] - P, P)
        for ph in np.arange(0, P, .01):
            s = np.interp(beats + ph, tt, flux).sum()
            if s > best[0]: best = (s, bpm, ph)
    s, bpm, ph = best
    P = 60 / bpm
    off = np.mean([np.interp(np.arange(0, tt[-1] - P, P) + ph + P / 2, tt, flux).sum()])   # off-beat comb
    return round(float(bpm), 3), float(ph), round(float(s / max(off, 1e-9)), 2)


def calmness(x, sr):
    blk = sr // 2
    rms = np.array([np.sqrt((x[i:i + blk] ** 2).mean() + 1e-12) for i in range(0, len(x) - blk, blk)])
    db = 20 * np.log10(rms)
    return float(np.std(db[db > db.max() - 40]))      # lower = steadier


def master(x):
    x = x / (np.sqrt((x ** 2).mean()) + 1e-9) * 10 ** (-21 / 20)
    pk = 10 ** (-1.5 / 20)
    over = np.abs(x) > pk * .8                          # soft knee limiter for the odd peak
    x[over] = np.sign(x[over]) * (pk * .8 + (pk * .2) * np.tanh((np.abs(x[over]) - pk * .8) / (pk * .2)))
    return x.astype(np.float32)


os.makedirs(DST, exist_ok=True)
meta = {}
for role, (pat, hint) in ROLES.items():
    cands = []
    for path in sorted(glob.glob(os.path.join(SRC, pat))):
        x, sr = read(path)
        mono = resample_poly(x.mean(axis=1), 1, 2) if sr > 40000 else x.mean(axis=1)
        msr = sr // 2 if sr > 40000 else sr
        tonic, mode, kc = key_of(mono, msr)
        bpm, ph, beat_conf = tempo_of(mono, msr, hint)
        calm = calmness(x, sr)
        cands.append(dict(path=path, x=x, sr=sr, tonic=tonic, mode=mode, kc=kc, bpm=bpm, ph=ph, conf=beat_conf, calm=calm))
        print(f"{role:6s} {os.path.basename(path):18s} key {NAMES[tonic]} {mode} ({kc})  {bpm} BPM (beat/off-beat {beat_conf})  swing {calm:.2f} dB")
    # the calmest steady take; a take in D minor (what was asked, and what the stingers expect) wins a tie
    pick = min(cands, key=lambda c: c["calm"] - (.6 if (c["tonic"], c["mode"]) == (2, "minor") else 0))
    x, sr = pick["x"], pick["sr"]
    P = 60 / pick["bpm"]
    s0 = int(round(pick["ph"] * sr))
    while s0 < sr * .3: s0 += int(round(P * sr))          # start on a beat, past any fade-in
    n = int(XF * sr)
    bar = 4 * P * sr
    bars = int((len(x) - s0 - n - sr * 1.0) // bar)        # whole bars, leaving the tail for the crossfade
    Lf = bars * bar
    L = int(round(Lf))
    seg = x[s0:s0 + L + n].copy()
    t = np.linspace(0, np.pi / 2, n, dtype=np.float32)[:, None]
    seg[:n] = seg[:n] * np.sin(t) + seg[L:L + n] * np.cos(t)
    loop = seg[:L]
    loop = resample_poly(loop, SR_OUT, sr, axis=0).astype(np.float32)
    loop = master(loop)
    out = os.path.join(DST, role + ".ogg")
    with sf.SoundFile(out, "w", SR_OUT, 2, format="OGG", subtype="VORBIS") as fh:     # in chunks: one huge
        for i in range(0, len(loop), SR_OUT): fh.write(loop[i:i + SR_OUT])             # vorbis write overflows
    meta[role] = {"src": os.path.basename(pick["path"]), "tonic": pick["tonic"], "key": NAMES[pick["tonic"]],
                  "mode": pick["mode"], "bpm": pick["bpm"], "bars": bars, "loopSec": round(Lf / sr, 4),
                  "quantize": pick["conf"] > 1.15}
    print(f"  -> {role}.ogg from {meta[role]['src']}: {bars} bars, {Lf / sr:.1f}s, {os.path.getsize(out) // 1024} KB, quantize {meta[role]['quantize']}")
with open(os.path.join(DST, "music.json"), "w") as fh:
    json.dump(meta, fh, indent=1)
