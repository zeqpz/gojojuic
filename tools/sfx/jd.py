"""Juice Dojo sound pass, end to end, on fallslotsga's sound tools (tools/sfx there: fall.py, process2, clean3,
pick_takes). Nothing in fallslotsga is changed: its modules are imported and pointed at this game's spec, key and
work folder.

  python tools/sfx/jd.py gen     [name ...]   # Seed Audio takes -> %TEMP%/juicedojo_sfx/raw/<name>_<t>.pcm (resumable)
  python tools/sfx/jd.py cand    [name ...]   # each take cleaned whole and cut into events -> cand/ + cand.json
  python tools/sfx/jd.py pick    [name ...]   # best + most alike `keep` per set -> picks.json (jd_spec.MANUAL wins)
  python tools/sfx/jd.py build   [name ...]   # clean3's strict denoise + gate + master -> %TEMP%/juicedojo_sfx/wav
  python tools/sfx/jd.py texture [name ...]   # for a sound that IS a noise (the fuse): level + fade only
  python tools/sfx/jd.py windows [name ...]   # jd_spec.WINDOWS: stretches cut by hand from raw takes (the fuse)
  python tools/sfx/jd.py slices  [name ...]   # the slices: build + 'impact' cut + checks, falling back to the next take
  python tools/sfx/jd.py shape   [name ...]   # jd_spec.SHAPE for the rest: whoosh windows, lead trims, caps
  python tools/sfx/jd.py final   [name ...]   # mono, peak check, OGG Vorbis -> frontend/assets/sfx + sfx.json
  python tools/sfx/jd.py report  [name ...]   # analysis of the shipped files (dur, peak, loudness, silence, bed)
  python tools/sfx/jd.py all     [name ...]   # gen cand pick build(/texture) windows slices shape final

Python: Documents/fallslotsga/.venv (numpy, scipy, noisereduce, soundfile). Key: %USERPROFILE%/.juicedojo/
openrouter-key.txt (never printed). Prompts and levels: jd_spec.py."""
import os, sys, json, glob
import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
FALL = os.path.join(os.path.dirname(ROOT), "fallslotsga", "tools", "sfx")
sys.path.insert(0, HERE)
sys.path.insert(1, FALL)

import orapi                                      # noqa: E402  (fallslotsga's OpenRouter helpers)
orapi.KEY_PATH = os.path.join(os.environ.get("USERPROFILE", os.path.expanduser("~")), ".juicedojo", "openrouter-key.txt")
import jd_spec as JS                              # noqa: E402
import fall                                       # noqa: E402  (its pipeline steps; repointed below)
import process2 as P                              # noqa: E402
import clean3 as C                                # noqa: E402
from audiolib import read_wav, lufs, noise_floor  # noqa: E402
import soundfile as sf                            # noqa: E402

W = os.path.join(os.environ.get("TEMP", "/tmp"), "juicedojo_sfx")
STAGE = os.path.join(W, "wav")
OUT = os.path.join(ROOT, "frontend", "assets", "sfx")
MANIFEST = os.path.join(OUT, "sfx.json")
SR = fall.SR
os.makedirs(STAGE, exist_ok=True)

# point fall.py's steps at Juice Dojo: its spec, work folder, and a staging folder in place of its game's assets
fall.FS = JS
fall.W, fall.RAW, fall.CAND, fall.ASSETS = W, os.path.join(W, "raw"), os.path.join(W, "cand"), STAGE
P.RAW = fall.RAW
for _name, (_, _, _kind, _t, _) in JS.S.items():
    P.T[_name] = _t
    C.KIND[_name] = _kind
P.FOUT.update(JS.FOUT)
C.TONAL |= JS.TONAL


def _files(name):
    _, _, _, (_, _, keep, _), out = JS.S[name]
    return [os.path.join(STAGE, f"sfx_{out[1]}_{i}.wav") for i in range(1, keep + 1)]


def _env(y, w):
    n = max(1, int(w * SR))
    return np.sqrt(signal.convolve((y ** 2).mean(1), np.ones(n) / n, mode="same"))


def _fade_out(y, secs):
    n = min(len(y) // 2, int(secs * SR))
    y[-n:] *= (.5 + .5 * np.cos(np.linspace(0, np.pi, n)))[:, None]
    return y


def _gap(y, after, db=-35, ms=40):
    """Start of the first stretch after `after` quieter than `db` re the peak for over `ms` that the sound comes back
    from (two events glued together), or None."""
    e = _env(y, .005)
    q = e < e.max() * 10 ** (db / 20)
    n = int(ms / 1000 * SR)
    i = after
    while i < len(q):
        if q[i]:
            j = i
            while j < len(q) and q[j]:
                j += 1
            if j - i > n and j < len(q) and e[j:].max() > e.max() * 10 ** (-25 / 20):
                return i
            i = j
        else:
            i += 1
    return None


def apply_ops(y, ops, name):
    """One file through jd_spec.SHAPE's ops. Returns (y, note, problem or '')."""
    note, bad = "", ""
    if "impact" in ops:
        pre, hz, cap = ops["impact"]
        lo = signal.sosfiltfilt(signal.butter(4, hz, "lowpass", fs=SR, output="sos"), y, axis=0)
        e = _env(lo, .005)
        top = int(np.argmax(e))
        j = top
        while j > 0 and e[j - 1] > e[top] * 10 ** (-18 / 20):
            j -= 1
        a = max(0, j - int(pre * SR))
        y = y[a:].copy()
        k = j - a
        if k > 8:                                 # the swish in front, eased in so it leads into the crunch
            r = np.linspace(0, 1, k)
            y[:k] *= (.7 * r ** 2 + .3 * r ** .5)[:, None]
        g = _gap(y, k + int(.03 * SR))
        if g is not None:                         # a second event after a silence: end before it
            y = _fade_out(y[:g + int(.01 * SR)], .02)
        if len(y) > cap * SR:
            y = _fade_out(y[:int(cap * SR)], .08)
        note = f"onset {j / SR * 1000:.0f}ms (cut {a / SR * 1000:.0f}ms){' gap-cut' if g is not None else ''}"
        if len(y) < (.2 if "accent" in ops else min(.35, cap * .6)) * SR:     # an accent carries the special ones on
            bad = f"too short after the cut ({len(y) / SR:.2f}s)"
    if "peakwin" in ops:
        pre, post = ops["peakwin"]
        top = int(np.argmax(_env(y, .02)))
        a, b = max(0, top - int(pre * SR)), min(len(y), top + int(post * SR))
        y = y[a:b].copy()
        k = top - a
        y[:k] *= (np.linspace(0, 1, k) ** 2)[:, None]
        y[k:] *= (np.linspace(1, 0, len(y) - k) ** 1.6)[:, None]
        note = f"peak at {top / SR * 1000:.0f}ms"
    if "lead" in ops:
        e = np.abs(y).max(1)
        a = int(np.argmax(e > e.max() * 10 ** (-20 / 20)))
        y = y[max(0, a - int(.004 * SR)):]
    if "cap" in ops and len(y) > ops["cap"] * SR:
        y = _fade_out(y[:int(ops["cap"] * SR)], .08)
    if "accent" in ops:
        import accents
        kind, at, db = ops["accent"]
        x = getattr(accents, kind)(seed=sum(map(ord, name)) * 7 + len(y) % 997)
        x = x * 10 ** (db / 20) * np.abs(y).max() / (np.abs(x).max() + 1e-12)
        i = int(at * SR) + (int(ops["impact"][0] * SR) if "impact" in ops else 0)
        n = max(len(y), i + len(x))
        z = np.zeros((n, y.shape[1]))
        z[:len(y)] += y
        z[i:i + len(x)] += x[:, None]
        y = z
        note += f" +{kind}"
    return y, note, bad


def _finish(y, tgt):
    y = fall._level(y, tgt)
    y = _fade_out(y, .006)
    y[0] = 0; y[-1] = 0
    return y


def shape(names):
    """jd_spec.SHAPE on the built files, from kept pre-shape copies (re-runnable); back to the loudness target."""
    os.makedirs(os.path.join(W, "preshape"), exist_ok=True)
    import shutil
    from audiolib import write_wav
    rec_p = os.path.join(W, "preshape", "shaped.json")      # mtimes of our own outputs: anything else is a new build
    rec = json.load(open(rec_p)) if os.path.exists(rec_p) else {}
    for name in names:
        ops = JS.SHAPE.get(name)
        if not ops or name in SLICED:
            continue
        tgt = JS.S[name][4][2]
        for path in _files(name):
            keep = os.path.join(W, "preshape", os.path.basename(path))
            if os.path.exists(path) and rec.get(os.path.basename(path)) != os.path.getmtime(path):
                shutil.copy2(path, keep)              # a fresh build replaces the kept copy
            if not os.path.exists(keep):
                continue
            y, sr, _ = read_wav(keep)
            y, note, bad = apply_ops(y, ops, name)
            y = _finish(y, tgt)
            write_wav(path, y, SR)
            rec[os.path.basename(path)] = os.path.getmtime(path)
            json.dump(rec, open(rec_p, "w"), indent=0)
            _, M = lufs(y, SR)
            print(f"{os.path.basename(path):24s} {sorted(ops)} {len(y) / SR:.2f}s M {M:.1f} {note} {bad}")


SLICED = {n for n, o in JS.SHAPE.items() if "impact" in o}


def slices(names):
    """build + shape in one for the slices: candidates in pick order (one per take while there are takes left), each
    cleaned the way fall.build does (gentler and gentler), cut by its 'impact' op and checked (long enough, not
    two events glued together); the first `keep` that pass are the set."""
    from audiolib import write_wav
    db = json.load(open(os.path.join(W, "cand.json")))
    picks = json.load(open(os.path.join(W, "picks.json")))
    for name in names:
        if name not in SLICED:
            continue
        _, _, kind, (mn, mx, keep, _), out = JS.S[name]
        tgt, ops = out[2], JS.SHAPE[name]
        ranked = sorted(db[name], key=lambda c: c.get("pen", 99))
        want = [next(c for c in db[name] if c["file"] == f) for f in picks[name]]
        order = want + [c for c in ranked if c not in want]
        res, used, tried = [], set(), set()
        for second in (False, True):              # first one per take, then any
            for c in order:
                if len(res) == keep:
                    break
                if c["file"] in {r[0]["file"] for r in res} or (not second and c["take"] in used):
                    continue
                if c["file"] in tried:
                    continue
                tried.add(c["file"])
                y = None
                for j, (prop, ns) in enumerate(((1.0, True), (1.0, False), (.85, False), (.6, False), (0.0, False))):
                    yy, info = C.build_one(name, c, tgt, prop=prop, nonstat=ns)
                    bed = info["n_after"] + info["gain"]
                    if info["guard"]["ok"] and bed <= JS.BED.get(name, C.BED_MAX) and len(yy) >= int(mn * .6 * SR):
                        y = yy; info["pass"] = j; break
                if y is None:
                    print(f"  {name} {c['file']}: rejected by the clean (bed {bed:.1f})"); continue
                z, note, bad = apply_ops(y, ops, name)
                if bad:
                    print(f"  {name} {c['file']}: rejected, {bad} [{note}]"); continue
                res.append((c, _finish(z, tgt), note, info["pass"]))
                used.add(c["take"])
        for i, (c, y, note, ps) in enumerate(res, 1):
            fn = f"sfx_{out[1]}_{i}.wav"
            write_wav(os.path.join(STAGE, fn), y, SR)
            _, M = lufs(y, SR)
            print(f"{fn:24s} {name}:{c['file']:7s} {len(y) / SR:.2f}s pk {20 * np.log10(np.abs(y).max()):5.1f} M {M:6.1f} pass {ps} {note}")
        for i in range(len(res) + 1, keep + 1):
            p = os.path.join(STAGE, f"sfx_{out[1]}_{i}.wav")
            if os.path.exists(p):
                os.remove(p)
        if len(res) < keep:
            print(f"  !! {name}: {len(res)} of {keep}")


def windows(names):
    """jd_spec.WINDOWS: stretches cut by hand from raw takes (a sound that is itself a noise, like the fuse)."""
    from audiolib import write_wav
    for name in names:
        if name not in JS.WINDOWS:
            continue
        out = JS.S[name][4]
        hp = 250 if JS.S[name][2] == "spray" else 40
        for i, (take, segs) in enumerate(JS.WINDOWS[name], 1):
            st = np.frombuffer(open(os.path.join(fall.RAW, f"{name}_{take}.pcm"), "rb").read(), "<i2")
            st = st.reshape(-1, 2).astype(np.float64) / 32768
            st = st - st.mean(0)
            x = int(.03 * fall.SR0)
            y = st[int(segs[0][0] * fall.SR0):int(segs[0][1] * fall.SR0)].copy()
            for a, b in segs[1:]:                  # joined with 30 ms equal-power crossfades
                z = st[int(a * fall.SR0) - x:int(b * fall.SR0)]
                t = np.linspace(0, np.pi / 2, x)[:, None]
                y[-x:] = y[-x:] * np.cos(t) + z[:x] * np.sin(t)
                y = np.concatenate([y, z[x:]])
            y = signal.resample_poly(y, 147, 80, axis=0)
            y = signal.sosfiltfilt(signal.butter(4, hp, "highpass", fs=SR, output="sos"), y, axis=0)
            y *= 10 ** ((out[2] - lufs(y, SR)[1]) / 20)          # to the target, the crackle's spikes into the limiter
            y = P.limit(y, SR)
            fi = int(.015 * SR)
            y[:fi] *= np.linspace(0, 1, fi)[:, None]
            y = _fade_out(y, JS.FOUT.get(name, 90) / 1000)
            y[0] = 0; y[-1] = 0
            fn = f"sfx_{out[1]}_{i}.wav"
            write_wav(os.path.join(STAGE, fn), y, SR)
            print(f"{fn:24s} {name} take {take} {segs} {len(y) / SR:.2f}s M {lufs(y, SR)[1]:.1f}")


def _pitch(y, st):
    """Varispeed up `st` semitones (pitch and speed together, like a tape: an escalating combo)."""
    if st == 0:
        return y
    r = 2 ** (st / 12)
    n = int(len(y) / r)
    return np.interp(np.arange(n) * r, np.arange(len(y)), y)


def _ogg(path, y):
    """OGG Vorbis, mono 44.1 kHz; the decoded file must stay under -1.5 dBFS (Vorbis can overshoot a little)."""
    for _ in range(4):
        sf.write(path, y, SR, format="OGG", subtype="VORBIS")
        d, _sr = sf.read(path)
        pk = 20 * np.log10(np.abs(d).max() + 1e-12)
        if pk <= -1.5:
            return d
        y = y * 10 ** ((-1.6 - pk) / 20)
    return d


def final(names):
    os.makedirs(OUT, exist_ok=True)
    man = json.load(open(MANIFEST)) if os.path.exists(MANIFEST) else {}
    for name in names:
        _, _, _, _, out = JS.S[name]
        stem, tgt, vol = out[1], out[2], out[3]
        srcs = [p for p in _files(name) if os.path.exists(p)]
        if not srcs:
            print(f"{name:14s} NOTHING BUILT"); continue
        ys = []
        for p in srcs:
            x, sr, _ = read_wav(p)
            assert sr == SR
            ys.append(x.mean(1))
        if name in JS.PITCH_STEPS:
            ys = [_pitch(ys[0], s) for s in JS.PITCH_STEPS[name]]
        for old in glob.glob(os.path.join(OUT, f"{stem}_*.ogg")):
            if old[len(os.path.join(OUT, stem)) + 1:-4].isdigit():
                os.remove(old)
        files = []
        for i, y in enumerate(ys, 1):
            # the mono fold drops a stereo take's loudness more than its peak: back to the target, letting at most
            # 3 dB of peaks into the -1.5 dBFS limiter (process2.limit, 1.5 ms look-ahead)
            _, M = lufs(y, SR)
            g = min(tgt - M, -1.5 + 3 - 20 * np.log10(np.abs(y).max() + 1e-12))
            y = P.limit((y * 10 ** (g / 20))[:, None], SR)[:, 0]
            y[0] = 0; y[-1] = 0
            fn = f"{stem}_{i}.ogg"
            _ogg(os.path.join(OUT, fn), y)
            files.append(f"sfx/{fn}")
        man[stem] = {"files": files, "vol": vol}
        print(f"{name:14s} -> {len(files)} files")
    man = {k: man[k] for k in sorted(man)}
    json.dump(man, open(MANIFEST, "w"), indent=1)
    report(names)


def report(names):
    tot = 0
    for name in names:
        stem = JS.S[name][4][1]
        for p in sorted(glob.glob(os.path.join(OUT, f"{stem}_*.ogg"))):
            if not p[len(os.path.join(OUT, stem)) + 1:-4].isdigit():
                continue
            y, sr = sf.read(p)
            sz = os.path.getsize(p); tot += sz
            I, M = lufs(y, sr)
            e = np.sqrt(signal.convolve(y ** 2, np.ones(int(.01 * sr)) / int(.01 * sr), mode="same")) + 1e-12
            d = 20 * np.log10(e / e.max())
            lead = np.argmax(d > -30) / sr * 1000
            # longest stretch inside the sound under -45 dB re its loudest 10 ms (a gap / dead air)
            live = np.nonzero(d > -45)[0]
            q = d[live[0]:live[-1]] < -45 if len(live) else np.array([])
            run = best = 0
            for v in q:
                run = run + 1 if v else 0; best = max(best, run)
            nf = noise_floor(y[:, None], sr)
            print(f"{os.path.basename(p):18s} {len(y) / sr:5.2f}s {sz / 1024:5.1f}KB pk {20 * np.log10(np.abs(y).max()):5.1f} "
                  f"M {M:6.1f} lead {lead:4.0f}ms gap {best / sr * 1000:4.0f}ms floor {nf:6.1f}")
    print(f"total {tot / 1024:.0f} KB")


def main():
    step, names = sys.argv[1], sys.argv[2:] or list(JS.S)
    if step == "all":
        fall.gen(names); fall.cand(names); fall.pick(names)
        fall.build([n for n in names if n not in JS.TEXTURE and n not in SLICED and n not in JS.WINDOWS])
        fall.texture([n for n in names if n in JS.TEXTURE])
        windows(names); slices(names); shape(names); final(names)
    elif step in ("final", "report", "shape", "slices", "windows"):
        globals()[step](names)
    else:
        getattr(fall, step)(names)


if __name__ == "__main__":
    main()
