"""Juice Dojo sound pass 2 (owner, 2026-11-18: "more sound effects for everything", cinematic + bonus stings).
Self-contained (no fallslotsga): Seed Audio takes -> trimmed, faded, peak-mastered mono OGG -> merged into
frontend/assets/sfx/sfx.json beside the first pass's sets.

    .venv/Scripts/python tools/sfx/gen_sfx2.py gen   [name ...]   # raw PCM takes -> art/raw/audio/sfx/<name>_<i>.pcm
    .venv/Scripts/python tools/sfx/gen_sfx2.py build [name ...]   # clean + OGG + manifest
Key: tools/orimg.key() (Documents/gamdevkey.txt), never printed. ~$0.008 a take.
"""
import json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import soundfile as sf

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from orimg import key  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, "art", "raw", "audio", "sfx")
OUT = os.path.join(ROOT, "frontend", "assets", "sfx")
SR = 24000
FX = "[Sound effect only. No voice, no speech, no music.] "

# name: (prompt, takes to make, takes to keep, (min s, max s), manifest volume)
S = {
    "heartbeat":  (FX + "A single deep, slow heartbeat, lub-dub, heavy and cinematic, close and bassy, then silence.", 3, 1, (.4, .9), .9),
    "riser":      (FX + "A tense cinematic riser: a rising whoosh of air and shimmering strings building up quickly over two seconds to a peak, then cut.", 3, 2, (1.0, 4.0), .6),
    "slowmo_in":  (FX + "Time slowing down: a deep cinematic whoom that drops in pitch, like a sound bending into slow motion.", 3, 2, (.6, 3.0), .7),
    "slowmo_out": (FX + "Time speeding back up: a reversed cinematic swell rushing upward, a quick suck of air into a soft snap.", 3, 2, (.4, 2.5), .55),
    "taiko":      (FX + "One huge Japanese taiko drum hit, deep and booming with a big room echo.", 3, 2, (.4, 3.0), .9),
    "gong":       (FX + "One big Asian gong struck hard, a bright shimmering crash that rings out.", 3, 2, (1.0, 5.0), .7),
    "star_ping":  (FX + "A magical golden sparkle chime, bright twinkling glockenspiel and shimmer, short and sweet.", 3, 2, (.3, 2.0), .6),
    "cam_whoosh": (FX + "A soft, smooth cinematic air whoosh, gentle and wide, like a camera gliding in.", 3, 2, (.3, 2.0), .35),
    "sword_draw": (FX + "A katana sword drawn quickly from its sheath, a crisp metallic shing.", 3, 2, (.2, 1.5), .45),
    "clack":      (FX + "Two hard wooden hyoshigi clappers struck together once, a sharp dry clack.", 3, 2, (.1, 1.0), .5),
    "ui_click":   (FX + "A soft short wooden button click, small and satisfying.", 3, 2, (.05, .6), .35),
    "impact":     (FX + "A heavy cinematic impact hit with a deep sub boom and a whoosh tail, like a trailer hit.", 3, 2, (.5, 3.5), .8),
}


def speech(text, retries=4):
    body = {"model": "bytedance-seed/seed-audio-1-0", "input": text, "response_format": "pcm"}
    last = None
    for a in range(retries):
        req = urllib.request.Request("https://openrouter.ai/api/v1/audio/speech", data=json.dumps(body).encode(),
                                     headers={"Authorization": "Bearer " + key(), "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read()[:200]!r}"      # moderation rejects ~1% at random: retry
        except Exception as e:
            last = repr(e)
        time.sleep(3 + 4 * a)
    raise RuntimeError(last)


def gen_one(job):
    name, i = job
    path = os.path.join(RAW, f"{name}_{i}.pcm")
    if os.path.exists(path) and os.path.getsize(path) > 1000:
        return f"have {name}_{i}"
    try:
        raw = speech(S[name][0])
    except RuntimeError as e:
        return f"FAIL {name}_{i} {e}"
    with open(path, "wb") as fh:
        fh.write(raw)
    return f"OK {name}_{i} {len(raw) / (SR * 4):.2f}s"


def load(path):
    a = np.frombuffer(open(path, "rb").read(), dtype="<i2").astype(np.float32) / 32768
    if len(a) % 2: a = a[:-1]
    return a.reshape(-1, 2).mean(axis=1)                    # stereo s16 -> mono


# one-shots: a take often holds a few hits in a row - keep only the first (it ends once the level stays 30 dB
# down for a gap); the heartbeat's "lub-dub" is two thumps close together, so its gap is longer
ONESHOT = {"clack": .08, "ui_click": .06, "taiko": .25, "sword_draw": .12, "star_ping": .2, "heartbeat": .3, "impact": .3}


# takes picked by ear/envelope: heartbeat_3 is the one clean lub-dub (1 and 2 are washy rumbles)
PICK = {"heartbeat": [3]}


def clean(x, gap=None):
    x = x - x.mean()
    win = int(SR * .01)
    env = np.sqrt(np.convolve(x * x, np.ones(win) / win, mode="same"))
    peak = env.max() or 1
    on = np.where(env > peak * 10 ** (-42 / 20))[0]          # -42 dB under its own peak = silence
    if not len(on): return None
    a, b = max(0, on[0] - int(SR * .005)), min(len(x), on[-1] + int(SR * .06))
    if gap:
        quiet = env < peak * 10 ** (-30 / 20)
        g, run = int(SR * gap), 0
        start = on[0] + int(SR * .03)
        for i in range(start, b):
            run = run + 1 if quiet[i] else 0
            if run >= g: b = i - g + int(SR * .06); break
    x = x[a:b].copy()
    fi, fo = int(SR * .003), min(len(x) // 3, int(SR * .05))
    x[:fi] *= np.linspace(0, 1, fi); x[-fo:] *= np.linspace(1, 0, fo)
    return x / (np.abs(x).max() or 1) * 10 ** (-1 / 20)     # peak -1 dBFS; the manifest sets the level


def build(names):
    man_path = os.path.join(OUT, "sfx.json")
    man = json.load(open(man_path))
    for name in names:
        _, make, keep, (lo, hi), vol = S[name]
        takes = []
        for i in PICK.get(name, range(1, make + 1)):
            p = os.path.join(RAW, f"{name}_{i}.pcm")
            if not os.path.exists(p): continue
            y = clean(load(p), ONESHOT.get(name))
            if y is None: continue
            d = len(y) / SR
            if d > hi: y = y[:int(hi * SR)]; y[-int(SR * .08):] *= np.linspace(1, 0, int(SR * .08)); d = hi
            if d >= lo: takes.append(y)
        if not takes:
            print("NO TAKES", name); continue
        med = np.median([len(t) for t in takes])                 # keep the takes most alike in length
        takes = sorted(takes, key=lambda t: abs(len(t) - med))[:keep]
        files = []
        for i, y in enumerate(takes, 1):
            f = f"sfx/{name}_{i}.ogg"
            sf.write(os.path.join(OUT, f"{name}_{i}.ogg"), y, SR, format="OGG", subtype="VORBIS")
            files.append(f)
        man[name] = {"files": files, "vol": vol}
        print("built", name, [round(len(t) / SR, 2) for t in takes])
    json.dump(man, open(man_path, "w"), indent=1)


if __name__ == "__main__":
    cmd, names = sys.argv[1], (sys.argv[2:] or list(S))
    os.makedirs(RAW, exist_ok=True)
    if cmd == "gen":
        jobs = [(n, i) for n in names for i in range(1, S[n][1] + 1)]
        with ThreadPoolExecutor(6) as ex:
            for line in ex.map(gen_one, jobs):
                print(line, flush=True)
    elif cmd == "build":
        build(names)
