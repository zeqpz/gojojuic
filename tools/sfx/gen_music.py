"""Juice Dojo music via OpenRouter Lyria 3 (owner, 2026-11-18). Streams the chat completion (audio output needs
stream: true), joins the base64 audio deltas and writes art/raw/audio/<name>.<ext> (ext from the magic bytes).

    python tools/sfx/gen_music.py [name ...]      # all by default
Key: tools/orimg.key() (Documents/gamdevkey.txt), never printed. Then tools/sfx/pack_audio.py makes the OGGs.
"""
import base64, json, os, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from orimg import key  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "art", "raw", "audio")

COMMON = ("Instrumental only, no vocals, no voice, no lyrics. Warm, clean, high-fidelity mix that sits in the "
          "background of a game. Even dynamics the whole way through: no sudden loud hits, no drops, no big build-ups, "
          "no intro and no ending, so it can loop.")
# Owner, 2026-11-18: the first themes were too intense - "relaxing, ninja like". Both in D minor so the game's
# in-key koto and bell stingers (game.js SFX.music.cue) sit with either. Two takes each; pack_music.py picks.
BASE = ("Relaxing, mysterious ninja theme for a calm Japanese fruit-slicing game, like a quiet zen garden at dusk: a "
        "soft, breathy shakuhachi flute melody, gentle koto plucks, a warm low string pad, distant soft taiko and light "
        "wooden percussion, a few wind chimes. Peaceful and unobtrusive. 80 BPM, in D minor (D minor pentatonic). ")
BONUS = ("Flowing ninja theme for the bonus round of a calm Japanese fruit-slicing game: a steady soft taiko and hand-drum "
         "pulse, a rolling koto ostinato, a shakuhachi melody, light plucked shamisen accents and warm strings; a sense "
         "of gentle forward motion and anticipation, but still relaxed and tasteful, never harsh or loud. 92 BPM, in D "
         "minor (D minor pentatonic). ")
JOBS = {
    "calm_base_1": ("google/lyria-3-pro-preview", BASE + COMMON),
    "calm_base_2": ("google/lyria-3-pro-preview", BASE + COMMON),
    "calm_bonus_1": ("google/lyria-3-pro-preview", BONUS + COMMON),
    "calm_bonus_2": ("google/lyria-3-pro-preview", BONUS + COMMON),
}


def magic(raw):
    if raw[:4] == b"RIFF": return "wav"
    if raw[:3] == b"ID3" or raw[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"): return "mp3"
    if raw[:4] == b"OggS": return "ogg"
    if raw[:4] == b"fLaC": return "flac"
    return "bin"


def run(name):
    model, prompt = JOBS[name]
    body = {"model": model, "modalities": ["audio", "text"], "stream": True,
            "messages": [{"role": "user", "content": prompt}]}
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Authorization": "Bearer " + key(), "Content-Type": "application/json"})
    chunks, text, fmt, cost = [], [], None, None
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            for line in r:
                line = line.decode("utf-8", "replace").strip()
                if not line.startswith("data:"): continue
                data = line[5:].strip()
                if data == "[DONE]": break
                try: ev = json.loads(data)
                except ValueError: continue
                if ev.get("usage"): cost = ev["usage"].get("cost")
                for ch in ev.get("choices") or []:
                    d = ch.get("delta") or {}
                    a = d.get("audio") or {}
                    if a.get("data"): chunks.append(a["data"])
                    if a.get("format"): fmt = a["format"]
                    if d.get("content"): text.append(d["content"])
    except urllib.error.HTTPError as e:
        return f"FAIL {name} HTTP {e.code} {e.read()[:300]!r}"
    if not chunks:
        return f"FAIL {name} no audio; text={''.join(text)[:200]!r}"
    raw = base64.b64decode("".join(chunks))
    ext = magic(raw) if magic(raw) != "bin" else (fmt or "bin")
    out = os.path.join(OUT, f"{name}.{ext}")
    with open(out, "wb") as fh:
        fh.write(raw)
    return f"OK {name} {ext} {len(raw)//1024} KB fmt={fmt} cost={cost}"


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    names = sys.argv[1:] or list(JOBS)
    with ThreadPoolExecutor(len(names)) as ex:
        for line in ex.map(run, names):
            print(line, flush=True)
