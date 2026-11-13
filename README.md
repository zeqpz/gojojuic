# Juice Dojo

An original fruit-slicing slot for [Stake Engine](https://stake-engine.com), built on the workflow and HUD of
[zeqpz/orleans](https://github.com/zeqpz/orleans) and the skills/agents in [zeqpz/workflow](https://github.com/zeqpz/workflow).

## How it plays

- **Base spin = one wave.** A 4x4 formation of fruit falls through the dojo as real bodies (gravity + quadratic air
  drag, so each settles at its own terminal speed; collisions with mass and spin). As it passes through the board the
  blade slices every paying line, halves and juice fly, and the rest falls on out the bottom, bumping into whatever is
  in the way. 10 lines (4 rows, 4 columns, 2 diagonals) pay **both ways**: 3 or 4 of a kind from either end. 3+ lines in
  one wave is a combo (x2, 5+ lines x3). **No bombs in the base game.**
- **Fruit Frenzy** (3+ golden star fruit): up to **50 waves**, faster as it goes. Every wave may carry a **bomb**:
  5% on the first wave, +0.6% each wave, capped at 25%. A bomb ends the frenzy (wins are kept). Multiplier peaches
  (x2/x3/x5/x10) add into one multiplier; frost grapes knock the bomb chance back to 5%; side fruit pays every wave;
  clearing all 50 brings the Gold Melon finale. 4 star fruit start at x2, 5+ at x3.
- **Bonus Buy** (orleans' 3-card shop): **Fruit Frenzy 77x**, **Xtreme Frenzy 265x** (starts x3, peaches x3/x5/x10
  more often, bomb 4% +0.5%/wave), **Bonus Boost 1.25x per spin** (toggle; Frenzy 1.6x as likely).
- RTP 96.70% in all four modes, max win 5,000x. Base hit rate 31.9%, frenzy ~1 in 193 spins (1 in ~120 boosted).

## Layout

| Path | What |
|---|---|
| `math/juice_math.py` | The whole math model: simulates books and writes `math/publish_files` (books, LUTs, index.json). `stats` for a quick estimate, `sim` to publish. LUT weights pin RTP to exactly 0.967. |
| `frontend/index.html`, `game.js` | The game: canvas physics, blade, juice, frenzy, finale, bet replay, resume. |
| `frontend/bonus.css` | **The orleans bonus UI, identical**: the Bonus Buy shop, the bonus intro and the in-bonus counter plate, extracted the same way; Juice Dojo overrides at the end. |
| `frontend/hud.css`, `hud.js` | **The orleans HUD, identical**: every orleans rule that styles `.bottom` and its pop-ups, extracted from the live orleans page in cascade order, plus its `buildHud`, `placePop`, `spinArrows` and its page-fit scaling (`--fit`, `--hs`). Restyle in overrides, don't hand-edit the extracted block. |
| `frontend/rgs.js`, `mock_rgs.py` | RGS client and local mock RGS (from orleans; port 8766). |
| `tools/blender/fruitkit.py` (+ `fruits_more.py`) | Procedural toon-shaded 3D fruit in Blender 4.2: cel bands, specular blob, rim light, inverted-hull outline; halves are real bisected geometry with an INSIDE material on the cut. Renders a 16-frame tumble for each whole fruit and each half. |
| `tools/pack_sprites.py` | Packs the Blender frames into one WebP sheet per fruit (`frontend/assets/fruit/`) + `meta.json`, and `art/blender/contact.png`. |
| `tools/sfx/jd.py`, `jd_spec.py`, `accents.py` | Sound effects: OpenRouter Seed Audio takes (prompts in `jd_spec.py`) cut, cleaned and mastered with fallslotsga's sfx tools -> `frontend/assets/sfx/*.ogg` + `sfx.json` (24 sets, 67 takes: a slice per fruit, swoosh, drop, bump, fuse, boom, frenzy_start, multiplier, frost, combo x3 rising, line_win, big_win, coin_tick). `game.js` plays a different take each time with a pitch nudge; synth fallback. Run `fallslotsga/.venv python tools/sfx/jd.py all`. |
| `tools/gen_art.py`, `tools/orimg.py` | OpenRouter image generation (background, logo, 2D references). Key: `%USERPROFILE%\.juicedojo\openrouter-key.txt`, never printed. |

## Run

```
C:\Users\CooperHinkel\Documents\fallslotsga\.venv\Scripts\python.exe frontend/mock_rgs.py
```
then http://localhost:8766/index.html?sessionID=test&rgs_url=http://localhost:8766&lang=en&device=desktop

Rebuild art: `blender -b --factory-startup --python tools/blender/fruitkit.py -- all build,render` (~3 min), then
`python tools/pack_sprites.py`. Live: in the Blender MCP session `exec` fruitkit.py and call `gallery()`.

Rebuild math: `python math/juice_math.py sim --base 300000 --bonus 60000` (~10 min), delete `math/mock_cache/`,
restart the mock. Keep `frontend/rules.js` (pays, frenzy numbers) in step with the constants in `juice_math.py`.
