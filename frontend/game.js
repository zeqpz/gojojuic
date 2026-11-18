/* Juice Dojo - the game.
 *
 * A round is a list of events from the RGS (math/juice_math.py writes them):
 *   wave        a 4x4 board of fruit thrown up through the dojo. Each fruit flies a real ballistic arc
 *               whose apex is its cell; at the apex time slows right down (the board "hangs"), the blade
 *               slashes every paying line (3-4 in a row from the line's start), halves and juice fly,
 *               then time snaps back and everything falls out the bottom. A wave with a BOMB explodes.
 *   frenzyStart / frenzyEnd   Fruit Frenzy: faster waves, side fruit, multiplier peaches, frost grapes
 *   finale      the Gold Melon, slashed `hits` times
 *   finalWin    the round total
 * Amounts in events are hundredths of the bet. The fruit are 3D toon renders from Blender
 * (tools/blender/fruitkit.py): a 16-frame tumble per fruit and per half (assets/fruit/<ID>.webp).
 */
"use strict";

const T = s => (RGS.social ? s.replace(/\bBet\b/g, "Play").replace(/\bBuy\b/g, "Get").replace(/\bbet\b/g, "play")
                              .replace(/\bbuy\b/g, "get").replace(/\bBonus Buy\b/g, "Bonus").replace(/\bCost\b/g, "Price") : s);
const UNIT = RGS.UNIT;
const MAX_WIN = 5000;
const REDUCED = matchMedia("(prefers-reduced-motion: reduce)").matches;
const NAME = { H1: "Watermelon", H2: "Pineapple", H3: "Dragon Fruit", H4: "Coconut", L1: "Orange", L2: "Apple",
               L3: "Lemon", L4: "Kiwi", SC: "Star Fruit", BOMB: "Bomb", PW2: "x2 Peach", PW3: "x3 Peach",
               PW5: "x5 Peach", PW10: "x10 Peach", FRZ: "Frost Grapes", JM: "Gold Melon" };
// on-screen size of each fruit, as a share of a cell (a watermelon is big, a kiwi is small)
const SIZE = { H1: 1.18, H2: 1.12, H3: 1.08, H4: 1.0, L1: .94, L2: .94, L3: .92, L4: .86, SC: 1.0, BOMB: .98,
               PW2: 1.0, PW3: 1.0, PW5: 1.0, PW10: 1.04, FRZ: 1.02, JM: 2.6 };
const SPRITE = id => (id === "PW10" ? "PW5" : id);
// the falling fruit are drawn at this share of a cell so there is clear space around each one
const FRUIT_SCALE = .74;

const state = {
  bets: [], betIdx: 0, playing: false, auto: 0, autoPick: 10, turbo: false, skip: false,
  mode: "base", roundWin: 0, frenzy: false, replay: false,
};
const bet = () => state.bets[state.betIdx] || UNIT;
const fmt = a => RGS.money(a);
const fromHundredths = h => Math.round(h * bet() / 100);
let modeCost = { base: 1, bonus: 77, extremebonus: 265, boost: 1.25 };

/* ---------------------------------------------------------------- canvases */
const fx = $("fx"), stain = $("stain");
const g = fx.getContext("2d"), gs = stain.getContext("2d");
let W = 0, H = 0, DPR = 1, S = 120, GX = 0, GY = 0, BOARD = { x: 0, y: 0, w: 0, h: 0 };
function layout() {
  DPR = Math.min(2, window.devicePixelRatio || 1);
  W = innerWidth; H = innerHeight;
  for (const c of [fx, stain]) { c.width = Math.round(W * DPR); c.height = Math.round(H * DPR); }
  g.setTransform(DPR, 0, 0, DPR, 0, 0);
  gs.setTransform(DPR, 0, 0, DPR, 0, 0);
  const hud = document.querySelector(".bottom").getBoundingClientRect();
  document.documentElement.style.setProperty("--hud-h", Math.round(H - hud.top) + "px");
  const portrait = H > W * 1.05;
  const top = portrait ? Math.max(90, H * 0.14) : Math.max(70, H * 0.13);
  const bottom = hud.top - (portrait ? 70 : 24);
  S = Math.max(56, Math.min((bottom - top) / 4.25, (portrait ? W * 0.94 : W * 0.5) / 4, 175));
  GX = W / 2 - 2 * S;
  GY = top + Math.max(0, (bottom - top - 4 * S) / 2);
  // (the juice can splash anywhere on the wood wall: no board, no clip - owner, 2026-11-18)
  const b = $("board");
  Object.assign(b.style, { left: GX + "px", top: GY + "px", width: 4 * S + "px", height: 4 * S + "px" });
  // the frenzy counter is painted on the wall beside the board; on a narrow screen, in the two top corners
  const rs = document.documentElement.style, side = GX;
  if (side >= 130) {
    const cw = Math.min(side * .86, 280);
    rs.setProperty("--wcw", cw + "px");
    rs.setProperty("--wl", (side - cw) / 2 + "px");
    rs.setProperty("--wr", (GX + 4 * S + (side - cw) / 2) + "px");
    rs.setProperty("--wtop", (GY + S * .35) + "px");
  } else {
    const cw = Math.min(W * .34, 220);
    rs.setProperty("--wcw", cw + "px");
    rs.setProperty("--wl", W * .03 + "px");
    rs.setProperty("--wr", (W * .97 - cw) + "px");
    rs.setProperty("--wtop", Math.max(6, GY - S * .9) + "px");
  }
}
const cell = (r, c) => ({ x: GX + (c + 0.5) * S, y: GY + (r + 0.5) * S });

/* ---------------------------------------------------------------- sprites */
const SHEETS = {};
let META = null;
async function loadArt(progress) {
  // the lettering's typeface, before any canvas pop or badge is drawn with it
  const font = document.fonts ? document.fonts.load('40px "Gang of Three"').catch(() => 0) : 0;
  META = await (await fetch("assets/fruit/meta.json")).json();
  FX.warm();                                 // the glows, flares and rays the FX kit stamps, built while it loads
  const stains = FX.loadStains();            // the wall stains' layers (tools/stain_layers.py)
  for (let i = 1; i <= 4; i++) { const im = new Image(); im.src = `assets/fx/splat${i}.webp`; SPLATS.push(im); }
  for (let i = 1; i <= 4; i++) { const im = new Image(); im.src = `assets/fx/drip${i}.webp`; DRIPS.push(im); }
  try {
    FXMETA = await (await fetch("assets/fx/fx.json")).json();
    for (const k of Object.keys(FXMETA)) {
      if (k.startsWith("burst")) continue;   // (the big burst splash is retired: the stain on the wall says it)
      const im = new Image(); im.src = `assets/fx/${k}.webp`; FXIMG[k] = im;
    }
  } catch (e) { FXMETA = {}; }
  const ids = Object.keys(META.fruit);
  let done = 0;
  await Promise.all(ids.map(id => new Promise(res => {
    const img = new Image();
    img.onload = () => { SHEETS[id] = img; done++; progress(done / ids.length); res(); };
    img.onerror = () => { done++; progress(done / ids.length); res(); };
    img.src = `assets/fruit/${id}.webp`;
  })));
  // decode up front so the first throw never hitches on an image upload
  await Promise.all(Object.values(SHEETS).map(i => i.decode ? i.decode().catch(() => 0) : 0));
  await font;
  await stains;
}
// One fruit from its sheet (tools/pack_sprites.py). clip: "whole" (or false) - the 32-frame tumble, t = the turn in
// radians; "wob" (or true) - a half rocking on its back, t = the rocking phase in radians; "openR" / "openL" - a half
// opening out of the cut, t = 0..1. Between two frames it crossfades, so even a slow turn never steps.
const clipOf = c => c === true ? "wob" : (c === false || c == null) ? "whole" : c;
function drawFruit(ctx, id, clip, t, x, y, size, rot, alpha = 1, flip = false) {
  const sid = SPRITE(id), img = SHEETS[sid], m = META && META.fruit[sid];
  if (!img || !m || !m.clips) return;
  const name = clipOf(clip), cl = m.clips[name] || m.clips.whole;
  if (!cl) return;
  const [first, n] = cl, loop = name === "whole" || name === "wob", C = META.cell, cols = META.cols;
  const u = loop ? ((t / (Math.PI * 2)) % 1 + 1) % 1 * n : Math.max(0, Math.min(1, t)) * (n - 1);
  const i0 = Math.min(n - 1, Math.floor(u)), fr = u - i0, i1 = loop ? (i0 + 1) % n : Math.min(n - 1, i0 + 1);
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(rot);
  if (flip) ctx.scale(-1, 1);
  const k = size * 1.06;   // the render frames the fruit at ~89% of the tile
  const tile = (i, a) => {
    const q = first + i;
    ctx.globalAlpha = a;
    ctx.drawImage(img, (q % cols) * C, Math.floor(q / cols) * C, C, C, -k / 2, -k / 2, k, k);
  };
  tile(i0, alpha);
  if (fr > .02 && i1 !== i0) tile(i1, alpha * fr);
  ctx.restore();
}
// the soft shadow a fruit throws on the wall, drawn once and stamped
const SHADOW = (() => {
  const c = document.createElement("canvas"); c.width = c.height = 128;
  const x = c.getContext("2d"), rg = x.createRadialGradient(64, 64, 0, 64, 64, 64);
  rg.addColorStop(0, "rgba(25,12,4,.34)"); rg.addColorStop(.6, "rgba(25,12,4,.16)"); rg.addColorStop(1, "rgba(25,12,4,0)");
  x.fillStyle = rg; x.fillRect(0, 0, 128, 128);
  return c;
})();
const shadowAt = (x, y, r) => g.drawImage(SHADOW, x - r, y - r, r * 2, r * 2);

/* ---------------------------------------------------------------- lettering */
// Fruit Ninja's typeface (Gang of Three, see fn.css): one word as its stacked outline, fill and sheen layers.
// cls: the colour (gold, red, pink, violet, white) and any extras (shine, num, ...); attrs go on the outer span.
const escHTML = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
function fnHTML(text, cls = "gold", attrs = "") {
  const t = escHTML(text);
  return `<span class="fnt ${cls}"${attrs ? " " + attrs : ""}><span class="fo">${t}</span>` +
         `<span class="ff" aria-hidden="true">${t}</span><span class="fs" aria-hidden="true">${t}</span></span>`;
}

/* ---------------------------------------------------------------- world */
const world = { fruit: [], pieces: [], drops: [], blades: [], pops: [], rings: [], blocks: [], mists: [], cuts: [], runs: [], lens: [], drips: [], bursts: [], booms: [] };
let timeScale = 1, simClock = 0, shake = 0;
const speed = () => (state.skip ? 3.2 : state.turbo ? 1.7 : 1);
const simWaiters = [];
const untilSim = t => new Promise(res => simWaiters.push({ t, res }));
const sleep = ms => new Promise(res => setTimeout(res, ms / speed()));
let GRAV = 2400;

function tweenTime(to, ms) {
  const from = timeScale, t0 = performance.now(), dur = ms / speed();
  return new Promise(res => {
    const step = () => {
      const k = Math.min(1, (performance.now() - t0) / dur);
      timeScale = from + (to - from) * (1 - (1 - k) * (1 - k));
      k < 1 ? requestAnimationFrame(step) : res();
    };
    step();
  });
}

/* ---------------------------------------------------------------- cinematic camera */
// One camera for the whole scene: the fx canvas is drawn through it, and the wall (#bg) and the stains
// (#stain) get the same transform in CSS, so the room zooms as one. camFocus(list) frames a set of fruit
// (followed as they fall; a sliced one is held at where it was cut), camFocus(null) eases back to the full
// view. `cine` (0..1) fades in a vignette while a close-up is on. (Owner, 2026-11-18: line close-ups.)
const cam = { x: 0, y: 0, z: 1, track: null, cine: 0, css: "", maxZ: 1.6 };
function camFocus(list) {
  if (list && list.some(Boolean)) SFX.camWhoosh();
  cam.track = list ? list.filter(Boolean).map(f => ({ f, x: f.x, y: f.y })) : null;
  if (cam.track && !cam.track.length) cam.track = null;
}
function camUpdate(rdt) {
  let tx = W / 2, ty = H / 2, tz = 1;
  if (cam.track) {
    let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
    for (const t of cam.track) {
      if (!t.f.gone && t.f.mode !== "wait") { t.x = t.f.x; t.y = t.f.y; }
      x0 = Math.min(x0, t.x); x1 = Math.max(x1, t.x); y0 = Math.min(y0, t.y); y1 = Math.max(y1, t.y);
    }
    tz = Math.max(1, Math.min(cam.maxZ, W / (x1 - x0 + S * 2.6), H / (y1 - y0 + S * 2.4)));
    tx = (x0 + x1) / 2; ty = (y0 + y1) / 2;
  }
  // gentle easing in and out (owner, 2026-11-18: a little slower and smoother)
  const ez = 1 - Math.exp(-rdt * 3.2), ep = 1 - Math.exp(-rdt * 4.4);
  cam.z += (tz - cam.z) * ez;
  // keep the view inside the room: never show past the edges of the wall
  const hw = W / (2 * cam.z), hh = H / (2 * cam.z);
  tx = Math.min(W - hw, Math.max(hw, tx)); ty = Math.min(H - hh, Math.max(hh, ty));
  cam.x += (tx - cam.x) * ep; cam.y += (ty - cam.y) * ep;
  cam.x = Math.min(W - hw, Math.max(hw, cam.x)); cam.y = Math.min(H - hh, Math.max(hh, cam.y));
  cam.cine += ((cam.track ? 1 : 0) - cam.cine) * (1 - Math.exp(-rdt * 6));
  if (!cam.track && Math.abs(cam.z - 1) < .001) { cam.z = 1; cam.x = W / 2; cam.y = H / 2; }
  // the wall moves exactly with the scene (its stains are painted on it); what hangs in front moves a touch more
  const key = cam.z === 1 ? "" : `${cam.x.toFixed(1)},${cam.y.toFixed(1)},${cam.z.toFixed(4)}`;
  if (key !== cam.css) {
    cam.css = key;
    for (const [el, f] of [[$("bg"), 1], [stain, 1], [$("mid"), 1.15]]) {
      if (!key) { el.style.transform = ""; continue; }
      const z = 1 + (cam.z - 1) * f, cx = W / 2 + (cam.x - W / 2) * f, cy = H / 2 + (cam.y - H / 2) * f;
      el.style.transformOrigin = "0 0";
      el.style.transform = `translate(${(W / 2 - cx * z).toFixed(2)}px, ${(H / 2 - cy * z).toFixed(2)}px) scale(${z.toFixed(4)})`;
    }
  }
}
const camApply = ctx => { if (cam.z !== 1) { ctx.translate(W / 2, H / 2); ctx.scale(cam.z, cam.z); ctx.translate(-cam.x, -cam.y); } };

/* ---------------------------------------------------------------- petals */
// Cherry blossom petals drifting down the dojo wall (on #petals inside #bg, so the camera carries them).
// They run on the scene's clock, so a slow-motion close-up slows them too. Cheap: 1x resolution, ~30 petals.
const petals = { cv: null, g: null, list: [], w: 0, h: 0 };
function petalsUpdate(dt) {
  if (!petals.cv) {
    petals.cv = $("petals"); if (!petals.cv) return;
    petals.g = petals.cv.getContext("2d");
  }
  if (petals.w !== W || petals.h !== H) { petals.w = petals.cv.width = W; petals.h = petals.cv.height = H; }
  const L = petals.list, n = Math.round(Math.min(34, 14 + W * H / 90000));
  const spawn = top => ({ x: Math.random() * W * 1.2 - W * .1, y: top ? -20 - Math.random() * 40 : Math.random() * H,
                          r: 5 + Math.random() * 6, vy: 28 + Math.random() * 34, sway: 20 + Math.random() * 40,
                          ph: Math.random() * 6.3, fs: 1.2 + Math.random() * 1.6, rot: Math.random() * 6.3, vr: (Math.random() - .5) * 2,
                          hue: Math.random() < .25 ? "#fff0f4" : Math.random() < .5 ? "#ffb8cc" : "#ff9fbb" });
  while (L.length < n) L.push(spawn(L.length > n / 2));
  const g2 = petals.g;
  g2.clearRect(0, 0, W, H);
  for (let i = L.length - 1; i >= 0; i--) {
    const p = L[i];
    p.ph += p.fs * dt; p.rot += p.vr * dt;
    p.y += p.vy * dt; p.x += (Math.cos(p.ph) * p.sway + 14) * dt;           // a light breeze from the left
    if (p.y > H + 20 || p.x > W + 40) { L[i] = spawn(true); continue; }
    const flip = Math.cos(p.ph * 1.3);                                      // tumbling: it narrows as it turns
    g2.save(); g2.translate(p.x, p.y); g2.rotate(p.rot); g2.scale(1, .35 + .65 * Math.abs(flip));
    g2.fillStyle = p.hue; g2.globalAlpha = .9;
    g2.beginPath(); g2.moveTo(0, -p.r); g2.quadraticCurveTo(p.r * .95, -p.r * .2, 0, p.r); g2.quadraticCurveTo(-p.r * .95, -p.r * .2, 0, -p.r); g2.fill();
    g2.strokeStyle = "rgba(150,40,70,.55)"; g2.lineWidth = 1; g2.stroke();  // the cartoon outline
    g2.restore();
  }
}

let last = performance.now();
function frame(now) {
  const rdt = Math.min(0.05, (now - last) / 1000);
  last = now;
  const dt = rdt * timeScale * speed();
  simClock += dt;
  for (let i = simWaiters.length - 1; i >= 0; i--) if (simClock >= simWaiters[i].t) { simWaiters[i].res(); simWaiters.splice(i, 1); }
  step(dt, rdt);
  camUpdate(rdt);
  petalsUpdate(rdt * timeScale);
  draw(rdt);
  requestAnimationFrame(frame);
}

// Every body falls the same way: gravity, and quadratic air drag that settles it at its own terminal
// speed (vt). A wave's fruit start at that speed above the screen, so they enter already falling, keep
// their 4x4 shape through the board (their vt differ by a few %), then gravity takes over below it.
const G = 2600;
function integrate(b, dt) {
  const gg = b.g || G, k = gg / (b.vt * b.vt);
  b.vy += (gg - k * b.vy * Math.abs(b.vy)) * dt;
  b.vx -= k * .6 * b.vx * Math.abs(b.vx) * dt;
  b.x += b.vx * dt; b.y += b.vy * dt;
  b.vr += b.vx * .004 * dt;                 // drifting sideways makes it roll that way
  b.rot += b.vr * dt; b.spin += b.vs * dt;
  b.vr *= Math.max(0, 1 - .35 * dt);
  if (b.wobA) b.ph += b.wobF * dt;          // the air rocks it a little as it falls
}
function step(dt, rdt) {
  // each wave has a ghost of its formation, falling with the formation's own physics: the cutting is timed off it
  for (const b of world.blocks) {
    const k = G / (b.vt * b.vt);
    b.vy += (G - k * b.vy * Math.abs(b.vy)) * dt;
    b.off += b.vy * dt;
    for (let i = b.waits.length - 1; i >= 0; i--) if (b.off >= b.waits[i].at) { b.waits[i].res(); b.waits.splice(i, 1); }
    if (b.off > S * 2.4) for (const f of b.fruits) releaseOne(f);   // anything still in formation well under the board goes now
    if (b.off > H + S * 6) b.state = "gone";
  }
  for (const f of world.fruit) {
    if (f.mode === "wait") {                  // out of sight until its own moment
      if (simClock < f.dropAt) continue;
      f.mode = "fall";
      f.x = f.x0; f.y = f.y0; f.vx = f.vx0; f.vy = f.v0;
      f.entering = true;                       // spawned above the frame: it falls in, no pop-in scale
      continue;
    }
    if (f.entering && f.y > -f.size * .45) {  // its sound when it first shows at the top edge
      f.entering = false;
      SFX.pop && SFX.pop();                    // (no ring as it comes in: owner, 2026-11-17)
    }
    if (f.popAge != null && f.popAge < 1) f.popAge += dt;
    if (f.mode === "held") { f.rot += f.vr * rdt; f.spin += f.vs * rdt; continue; }
    if (f.delay > 0) { f.delay -= dt; continue; }
    integrate(f, dt);
  }
  world.blocks = world.blocks.filter(b => b.state !== "gone");
  collide();
  world.fruit = world.fruit.filter(f => !f.gone && (f.mode === "held" || f.mode === "wait" || (f.y < H + S * 2 && f.y > -H * 3 && f.x > -S * 3 && f.x < W + S * 3)));
  for (const p of world.pieces) {
    p.age = (p.age || 0) + dt;
    if (p.age < OPEN_T) p.vr = p.vr0 * (p.age / OPEN_T) ** 2;   // it opens out of the cut before it starts to roll
    integrate(p, dt);
  }
  world.pieces = world.pieces.filter(p => p.y < H + S * 2);
  for (const d of world.drops) {
    d.vy += G * .85 * dt; d.vx *= 1 - 1.2 * dt; d.x += d.vx * dt; d.y += d.vy * dt; d.life -= dt;
    if (d.life <= 0 && d.juice && !d.spray && !d.landed) { d.landed = true; if (Math.random() < .5 && d.y < H) FX.dropStain(d); }
  }
  for (const d of world.drips) {
    d.t += rdt;
    if (d.t >= d.dur) {           // settled: bake it into the wall
      gs.save(); gs.globalAlpha = .82; gs.drawImage(d.img, d.x - d.w / 2, d.y, d.w, d.h); gs.restore();
      d.done = true;
    }
  }
  world.drips = world.drips.filter(d => !d.done);
  for (const b of world.bursts) b.t += dt;
  world.bursts = world.bursts.filter(b => b.t < b.dur);
  for (const b of world.booms) b.t += rdt * speed();
  world.booms = world.booms.filter(b => b.t < b.dur);
  for (const r of world.runs) {
    const step = Math.min(r.len - r.d, r.v * dt);
    if (step > 0) {
      gs.save(); gs.globalAlpha = .3; gs.fillStyle = r.col;
      const n = Math.max(1, Math.ceil(step / 2));
      for (let i = 1; i <= n; i++) {
        const d = r.d + step * i / n, wx = r.x + Math.sin(r.wob + d * .05) * r.w * .4;
        gs.beginPath(); gs.arc(wx, r.y + d, r.w * (.5 + .25 * (1 - d / r.len)), 0, Math.PI * 2); gs.fill();
      }
      gs.restore();
      r.d += step;
      r.v *= Math.max(0, 1 - .9 * dt);
    }
    if (r.d >= r.len - .5 || r.v < 4) {
      gs.save(); gs.globalAlpha = .38; gs.fillStyle = r.col;
      gs.beginPath(); gs.arc(r.x + Math.sin(r.wob + r.d * .05) * r.w * .4, r.y + r.d + r.w * .4, r.w * 1.05, 0, Math.PI * 2); gs.fill();
      gs.restore();
      r.done = true;
    }
  }
  world.runs = world.runs.filter(r => !r.done);
  for (const L of world.lens) {
    L.age += rdt;
    L.y += L.vy * rdt; L.vy = Math.min(60, L.vy + 22 * rdt);        // it clings, then slides down the glass
    for (const t of L.trails) t.len = Math.min(t.max, t.len + t.v * rdt);
  }
  world.lens = world.lens.filter(L => L.age < L.dur);
  for (const m of world.mists) m.age += dt;
  world.mists = world.mists.filter(m => m.age < m.dur);
  for (const c of world.cuts) c.age += rdt * speed();
  world.cuts = world.cuts.filter(c => c.age < c.dur);
  world.drops = world.drops.filter(d => d.life > 0 && d.y < H + 40);
  for (const b of world.blades) b.age += rdt * speed();
  world.blades = world.blades.filter(b => b.age < b.dur + 0.25);
  for (const p of world.pops) p.age += rdt * speed();
  world.pops = world.pops.filter(p => p.age < p.dur);
  for (const r of world.rings) r.age += rdt * speed();
  world.rings = world.rings.filter(r => r.age < r.dur);
  shake = Math.max(0, shake - rdt * 2.6);
  FX.update(dt, rdt);
  // juice stains on the wall fade slowly
  stainFade += rdt;
  if (stainFade > 0.1) {
    stainFade = 0;
    gs.save(); gs.globalCompositeOperation = "destination-out"; gs.fillStyle = "rgba(0,0,0,0.012)"; gs.fillRect(0, 0, W, H); gs.restore();
  }
}
let stainFade = 0;

// Whole fruit and halves are round bodies with mass (size squared; a half weighs less): any two that meet
// are eased apart (60% of the overlap a frame, so a stack never jitters) and bounce softly (restitution .28),
// and a glancing hit sets them spinning. A half joins in once it has opened.
function collide() {
  const list = [];
  for (const f of world.fruit) if (!f.gone && f.mode !== "held" && f.mode !== "wait" && !(f.delay > 0) && f.y > -S * 1.5 && f.y < H + S) list.push([f, f.size * .4, f.size * f.size]);
  for (const p of world.pieces) if (p.y > -S && p.y < H + S && p.age > OPEN_T) list.push([p, p.size * .3, p.size * p.size * .4]);
  for (let i = 0; i < list.length; i++) {
    const [a, ra, ma] = list[i];
    for (let j = i + 1; j < list.length; j++) {
      const [b, rb, mb] = list[j];
      if (a.half && b.half) continue;
      const dx = b.x - a.x, dy = b.y - a.y, rr = ra + rb;
      const d2 = dx * dx + dy * dy;
      if (d2 >= rr * rr || d2 < 1e-6) continue;
      const d = Math.sqrt(d2), nx = dx / d, ny = dy / d, overlap = rr - d;
      const wa = mb / (ma + mb), wb = ma / (ma + mb);
      a.x -= nx * overlap * wa * .6; a.y -= ny * overlap * wa * .6;
      b.x += nx * overlap * wb * .6; b.y += ny * overlap * wb * .6;
      const rvx = b.vx - a.vx, rvy = b.vy - a.vy, rel = rvx * nx + rvy * ny;
      if (rel >= 0) continue;
      const jimp = -(1.28) * rel / (1 / ma + 1 / mb);
      a.vx -= jimp / ma * nx; a.vy -= jimp / ma * ny;
      b.vx += jimp / mb * nx; b.vy += jimp / mb * ny;
      const tang = (rvx * -ny + rvy * nx) / S;     // a glancing hit spins them
      a.vr += tang * 1.1; b.vr -= tang * 1.1;
      if (-rel > 220 && !(a.half && b.half)) SFX.bump();
    }
  }
}

function draw() {
  g.setTransform(DPR, 0, 0, DPR, 0, 0);
  g.clearRect(0, 0, W, H);
  if (shake > 0) g.translate((Math.random() - .5) * 26 * shake, (Math.random() - .5) * 26 * shake);
  camApply(g);
  FX.drawRoom(g);                           // warm bokeh and dust in the light, behind everything
  for (const r of world.rings) {
    const k = r.age / r.dur;
    g.save(); g.globalAlpha = (1 - k) * r.a; g.strokeStyle = r.col; g.lineWidth = r.w * (1 - k) + 1;
    g.beginPath(); g.arc(r.x, r.y, r.r0 + (r.r1 - r.r0) * (1 - (1 - k) ** 3), 0, Math.PI * 2); g.stroke(); g.restore();
  }
  // the wet stains and the drips running down are on the board, so they are clipped to its planks too
  FX.drawWet(g);                             // wet stains catching the light, drying; running drips' beads
  FX.drawMists(g, world.mists);              // a soft puff of juice where a fruit was cut
  g.globalAlpha = 1;
  for (const p of world.pieces) {      // the halves: opening out of the cut, then rocking as they roll away
    shadowAt(p.x + S * .08, p.y + S * .13, p.size * .4);
    if (p.age < OPEN_T) drawFruit(g, p.id, p.side, p.age / OPEN_T, p.x, p.y, p.size, p.rot);
    else drawFruit(g, p.id, "wob", p.spin, p.x, p.y, p.size, p.rot, 1, p.side === "openL");
  }
  for (const d of world.drips) {      // a drip unrolling down the wall: shown down to its creeping head
    const k = 1 - Math.pow(1 - Math.min(1, d.t / d.dur), 2.6), sh = d.h * k;
    if (sh < 1) continue;
    g.save(); g.globalAlpha = .82;
    g.drawImage(d.img, 0, 0, d.img.width, d.img.height * k, d.x - d.w / 2, d.y, d.w, sh);
    g.restore();
  }
  // soft shadows on the wall behind the fruit, offset down-right: they are in front of it
  for (const f of world.fruit) {
    if (f.delay > 0 || f.mode === "wait") continue;
    shadowAt(f.x + S * .1, f.y + S * .16, f.size * .52);
  }
  for (const f of world.fruit) {
    if (f.delay > 0 || f.mode === "wait") continue;
    FX.auraBack(g, f);                       // a special fruit's halo, rays, light streak (fxkit.js)
    // the tumble (crossfaded frames), the air's rocking tilt, and the little pop as it comes out of the top
    const pk = f.popAge == null ? 1 : Math.min(1, f.popAge / .16), popS = pk >= 1 ? 1 : .35 + .65 * (1 + 2.2 * Math.pow(pk - 1, 3) + 1.2 * Math.pow(pk - 1, 2));
    drawFruit(g, f.id, "whole", f.spin, f.x, f.y, f.size * popS, f.rot + (f.wobA ? Math.sin(f.ph) * f.wobA : 0));
    FX.auraFront(g, f);                      // its twinkles, crackling arcs, spitting fuse
    if (f.id.startsWith("PW")) badge(g, f.x, f.y + f.size * .05, "x" + f.id.slice(2), f.size * .42);
  }
  for (const b of world.bursts) drawSheet(b, b.img, FXMETA[b.key], false);
  // juice in flight: glossy lit drops stretched along their flight (the bomb's embers as streaks)
  FX.drawDrops(g, world.drops);
  g.globalAlpha = 1;
  FX.drawParts(g);                           // juice beads, chunks, seeds, smoke; glitter, sparks, embers, frost
  // cut flashes: a hot line across the fruit along the stroke, and a four-point glint
  g.save(); g.globalCompositeOperation = "lighter";
  for (const c of world.cuts) {
    const k = c.age / c.dur, a = 1 - k, len = c.len * (.6 + .6 * k);
    g.globalAlpha = a;
    g.strokeStyle = "#fff"; g.lineWidth = 5 * (1 - k) + 1;
    g.beginPath(); g.moveTo(c.x - Math.cos(c.ang) * len, c.y - Math.sin(c.ang) * len); g.lineTo(c.x + Math.cos(c.ang) * len, c.y + Math.sin(c.ang) * len); g.stroke();
    FX.glint(g, c.x, c.y, c.len * .9 * (1 - k * .4), c.col, c.ang + Math.PI / 4);
  }
  g.restore();
  for (const b of world.blades) drawBlade(b);
  for (const b of world.booms) drawSheet(b, FXIMG.boom, FXMETA.boom, true);
  FX.drawTop(g);                             // burst flares and rays, lightning
  for (const p of world.pops) drawPop(p);
  if (cam.cine > .01) {                      // the close-up's vignette, in screen space
    g.setTransform(DPR, 0, 0, DPR, 0, 0);
    const vg = g.createRadialGradient(W / 2, H / 2, Math.min(W, H) * .3, W / 2, H / 2, Math.hypot(W, H) * .6);
    vg.addColorStop(0, "rgba(8,3,1,0)"); vg.addColorStop(1, `rgba(8,3,1,${(.6 * cam.cine).toFixed(3)})`);
    g.fillStyle = vg; g.fillRect(0, 0, W, H);
  }
  if (world.lens.length) { g.setTransform(DPR, 0, 0, DPR, 0, 0); drawLens(); }
}

// one frame of an FX sheet (Blender renders packed by tools/pack_splash.py), sized, turned and faded
function drawSheet(b, img, m, glow) {
  if (!img || !m || !img.complete) return;
  const k = Math.min(.999, b.t / b.dur), f = Math.floor(k * m.frames), C = m.cell;
  const sy = Math.floor(f / m.cols) * C;
  g.save();
  g.translate(b.x, b.y); g.rotate(b.ang || 0);
  g.globalAlpha = b.alpha == null ? 1 : b.alpha;
  if (b.smoke && k > .4) g.globalAlpha *= 1 - Math.pow((k - .4) / .6, .8) * .85;   // the smoke thins to a haze, never a black blot
  if (glow && k < .35) {                 // the fireball's first frames light the scene up
    g.globalCompositeOperation = "lighter";
    g.globalAlpha = .5 * (1 - k / .35);
    g.drawImage(img, (f % m.cols) * C, sy, C, C, -b.size * .6, -b.size * .6, b.size * 1.2, b.size * 1.2);
    g.globalCompositeOperation = "source-over";
    g.globalAlpha = 1;
  }
  g.drawImage(img, (f % m.cols) * C, sy, C, C, -b.size / 2, -b.size / 2, b.size, b.size);
  g.restore();
}
function badge(ctx, x, y, text, px) {
  ctx.save();
  ctx.font = `${px}px "Gang of Three", Fredoka, sans-serif`;
  ctx.textAlign = "center"; ctx.textBaseline = "middle";
  ctx.lineWidth = px * .22; ctx.strokeStyle = "#140a04"; ctx.lineJoin = "round";
  ctx.strokeText(text, x, y); ctx.fillStyle = "#fff"; ctx.fillText(text, x, y);
  ctx.restore();
}

function drawBlade(b) {
  // a katana stroke: a slightly curved arc (quadratic, bowed to one side), drawn from its fading tail to its
  // head as a ribbon that tapers to nothing at the tail - a cool outer glow added on top, a white-hot core
  const k = Math.min(1, b.age / b.dur), fade = b.age > b.dur ? Math.max(0, 1 - (b.age - b.dur) / .25) : 1;
  const head = k, tail = Math.max(0, k - .7);
  const P = b.path ? t => {               // a Catmull-Rom curve through every fruit of the line
    const q = b.path, n = q.length - 1, f = Math.min(n - 1e-6, Math.max(0, t * n)), i = Math.floor(f), u = f - i;
    const p0 = q[Math.max(0, i - 1)], p1 = q[i], p2 = q[i + 1], p3 = q[Math.min(n, i + 2)];
    const cr = (a0, a1, a2, a3) => .5 * (2 * a1 + (-a0 + a2) * u + (2 * a0 - 5 * a1 + 4 * a2 - a3) * u * u + (-a0 + 3 * a1 - 3 * a2 + a3) * u * u * u);
    return [cr(p0[0], p1[0], p2[0], p3[0]), cr(p0[1], p1[1], p2[1], p3[1])];
  } : t => {
    const u = 1 - t;
    return [u * u * b.x0 + 2 * u * t * b.cx + t * t * b.x1, u * u * b.y0 + 2 * u * t * b.cy + t * t * b.y1];
  };
  const N = 18, pts = [];
  for (let i = 0; i <= N; i++) pts.push(P(tail + (head - tail) * i / N));
  const ribbon = (w) => {
    const L = [], R = [];
    for (let i = 0; i <= N; i++) {
      const [x, y] = pts[i], [x2, y2] = pts[Math.min(N, i + 1)], [x1, y1] = pts[Math.max(0, i - 1)];
      let nx = -(y2 - y1), ny = x2 - x1; const nl = Math.hypot(nx, ny) || 1; nx /= nl; ny /= nl;
      const ww = w * Math.sin(Math.PI * Math.min(1, i / N * 1.08)) ** .7 * (i === N ? .4 : 1);
      L.push([x + nx * ww / 2, y + ny * ww / 2]); R.push([x - nx * ww / 2, y - ny * ww / 2]);
    }
    g.beginPath(); g.moveTo(...L[0]);
    for (const q of L) g.lineTo(...q);
    for (let i = R.length - 1; i >= 0; i--) g.lineTo(...R[i]);
    g.closePath(); g.fill();
  };
  g.save();
  g.globalCompositeOperation = "lighter";
  g.globalAlpha = .45 * fade; g.fillStyle = b.glow; ribbon(b.w * 3.2);
  g.globalAlpha = .7 * fade; ribbon(b.w * 1.7);
  g.globalCompositeOperation = "source-over";
  g.globalAlpha = fade; g.fillStyle = "#fff"; ribbon(b.w * .8);
  // a spark at the tip while it moves
  if (k < 1) {
    const [hx, hy] = pts[N];
    g.globalCompositeOperation = "lighter"; g.globalAlpha = fade;
    FX.bladeHead(g, b, hx, hy);
  }
  g.restore();
}

function drawPop(p) {
  const k = p.age / p.dur;
  const s = k < .15 ? .5 + k / .15 * .7 : 1.2 - Math.min(.2, (k - .15) * .6);
  g.save();
  g.globalAlpha = k > .7 ? 1 - (k - .7) / .3 : 1;
  g.translate(p.x, p.y - p.rise * k);
  g.scale(s, s);
  g.font = `${p.px}px "Gang of Three", Fredoka, sans-serif`;
  g.textAlign = "center"; g.textBaseline = "middle"; g.lineJoin = "round";
  g.save(); g.globalCompositeOperation = "lighter"; g.globalAlpha *= .38;
  FX.textGlow(g, p.col, g.measureText(p.text).width * 1.4 + p.px, p.px * 2.3);
  g.restore();
  g.lineWidth = p.px * .22; g.strokeStyle = "#1a0b04"; g.strokeText(p.text, 0, 0);
  const gr = g.createLinearGradient(0, -p.px * .5, 0, p.px * .5);
  gr.addColorStop(0, "#ffffff"); gr.addColorStop(.45, p.col); gr.addColorStop(1, shade(p.col, -.35));
  g.fillStyle = gr; g.fillText(p.text, 0, 0);
  g.restore();
}

function shade(hex, k) {
  const n = parseInt(hex.slice(1), 16), f = c => Math.max(0, Math.min(255, Math.round(c + (k < 0 ? c * k : (255 - c) * k))));
  return "#" + ((f(n >> 16) << 16) | (f((n >> 8) & 255) << 8) | f(n & 255)).toString(16).padStart(6, "0");
}
const pop = (x, y, text, col = "#fff", px = 34, dur = 1.1, rise = 50) => { world.pops.push({ x, y, text, col, px, dur, rise, age: 0 }); FX.sparkle(x, y, col, 8); };
const ring = (x, y, col, r0, r1, dur = .5, w = 8, a = 1) => world.rings.push({ x, y, col, r0, r1, dur, w, a, age: 0 });

/* ---------------------------------------------------------------- slicing */
const SPLATS = [], DRIPS = [], FXIMG = {};   // glossy greyscale juice (OpenRouter) and the Blender FX sheets
let FXMETA = {};
const tintCache = new Map(), glintCache = new Map();
// the bright specular parts of a grey liquid sprite, as a white layer of their own (computed once per sprite)
function glintsOf(src) {
  if (glintCache.has(src)) return glintCache.get(src);
  const c = document.createElement("canvas");
  c.width = src.naturalWidth; c.height = src.naturalHeight;
  const x = c.getContext("2d");
  x.drawImage(src, 0, 0);
  let ok = true;
  try {
    const d = x.getImageData(0, 0, c.width, c.height), a = d.data;
    for (let i = 0; i < a.length; i += 4) {
      const l = (a[i] * .3 + a[i + 1] * .59 + a[i + 2] * .11) / 255;
      const k = Math.max(0, Math.min(1, (l - .86) / .12));
      a[i] = a[i + 1] = a[i + 2] = 255; a[i + 3] = a[i + 3] * k;
    }
    x.putImageData(d, 0, 0);
  } catch (e) { ok = false; }
  glintCache.set(src, ok ? c : null);
  return ok ? c : null;
}
function tinted(src, col) {
  if (!src || !src.complete || !src.naturalWidth) return null;
  let m = tintCache.get(src);
  if (!m) { m = new Map(); tintCache.set(src, m); }
  if (m.has(col)) return m.get(col);
  const c = document.createElement("canvas");
  c.width = src.naturalWidth; c.height = src.naturalHeight;
  const x = c.getContext("2d");
  x.drawImage(src, 0, 0);
  x.globalCompositeOperation = "multiply"; x.fillStyle = col; x.fillRect(0, 0, c.width, c.height);   // colour x the liquid's shading
  x.globalCompositeOperation = "destination-in"; x.drawImage(src, 0, 0);                           // back to its own outline
  x.globalCompositeOperation = "source-over";
  const gl = glintsOf(src);
  if (gl) { x.globalAlpha = .9; x.drawImage(gl, 0, 0); }                                           // and its gloss on top
  m.set(col, c);
  return c;
}
const tintedSplat = (i, col) => tinted(SPLATS[i], col);
function juice(x, y, col, n = 18, power = 1, dx = 0, dy = 0) {
  for (let i = 0; i < n; i++) {
    // most of the juice sprays along the stroke and out of the cut, some everywhere
    const along = Math.random() < .6, a = along ? Math.atan2(dy, dx) + (Math.random() - .5) * 1.4 + (Math.random() < .5 ? Math.PI / 2 : -Math.PI / 2) * .6
                                                  : Math.random() * Math.PI * 2;
    const v = (160 + Math.random() * 620) * power;
    world.drops.push({ x, y, vx: Math.cos(a) * v + dx * 220, vy: Math.sin(a) * v - 140 + dy * 220,
                       r: 1.6 + Math.random() ** 2 * 5.5 * power, col, life: .45 + Math.random() * .6, juice: true });
  }
  for (let i = 0; i < 14 * power; i++) {     // and a fine spray, fast and short-lived
    const a = Math.random() * Math.PI * 2, v = (500 + Math.random() * 700) * power;
    world.drops.push({ x, y, vx: Math.cos(a) * v + dx * 200, vy: Math.sin(a) * v - 60 + dy * 200, r: .6 + Math.random() * .8, col,
                       life: .18 + Math.random() * .25, juice: true, spray: true });
  }
  world.mists.push({ x, y, col, r0: S * .15, r1: S * .9 * power, age: 0, dur: .55 });
  // the stain it leaves on the wall (fxkit.js): the juice soaking into the wood, wet and lit at first, drying; a run
  // or two creeping down from it. The wall's stains fade slowly (see step).
  FX.stain(x, y, col, power);
  // (juice on the camera - lensSplat - is off: the owner didn't want the big splash sliding down the screen)
}

// Juice on the camera: a splat on the glass in front of everything - see-through, with a wet rim and a glint -
// that clings a moment, slides down, runs streaks below it, and fades. A few at most.
function lensSplat(x, y, col, power = 1) {
  if (world.lens.length > 6) return;
  const k = Math.min(4, 1 + Math.floor(Math.random() * 3 * power));
  for (let i = 0; i < k; i++) {
    const R = (i ? 22 + Math.random() * 40 : 75 + Math.random() * 80) * Math.min(1.5, power) * Math.max(.7, Math.min(1.3, W / 1000));
    const lx = Math.max(R, Math.min(W - R, x + (Math.random() - .5) * 360)), ly = Math.max(R, Math.min(H * .8, y + (Math.random() - .6) * 260));
    world.lens.push({ x: lx, y: ly, R, col, ang: Math.random() * 6.3, splat: Math.floor(Math.random() * 4), age: 0,
                      dur: 2.6 + Math.random() * 1.8, vy: -6 + Math.random() * 6,
                      trails: Array.from({ length: 1 + Math.floor(Math.random() * 3) }, () => ({
                        dx: (Math.random() - .5) * R * .9, w: R * (.08 + Math.random() * .08), len: 0, max: R * (1 + Math.random() * 2.2), v: 30 + Math.random() * 60 })) });
  }
}
function drawLens() {
  for (const L of world.lens) {
    const fade = Math.min(1, L.age / .06) * (1 - Math.max(0, (L.age - L.dur * .55) / (L.dur * .45)));
    const st = tintedSplat(L.splat, L.col);
    g.save();
    g.globalAlpha = .5 * fade;
    g.fillStyle = L.col;
    for (const t of L.trails) {                // the runs it leaves on the glass
      g.fillRect(L.x + t.dx - t.w / 2, L.y, t.w, t.len);
      g.beginPath(); g.arc(L.x + t.dx, L.y + t.len, t.w * .85, 0, Math.PI * 2); g.fill();
    }
    if (st) {
      g.translate(L.x, L.y); g.rotate(L.ang);
      const k = L.R * 2 / Math.max(st.width, st.height);
      g.globalAlpha = .62 * fade;
      g.filter = "blur(1.6px)";               // it is on the lens, out of focus
      g.drawImage(st, -st.width * k / 2, -st.height * k / 2, st.width * k, st.height * k);
      g.filter = "none";
      g.rotate(-L.ang); g.translate(-L.x, -L.y);
    }
    // the wet look: a darker rim and a bright glint, as light catches the drop on the lens
    g.globalAlpha = .35 * fade;
    g.strokeStyle = shade(L.col, -.45); g.lineWidth = Math.max(1.5, L.R * .05);
    g.beginPath(); g.arc(L.x, L.y, L.R * .52, 0, Math.PI * 2); g.stroke();
    const gl = g.createRadialGradient(L.x - L.R * .18, L.y - L.R * .2, 0, L.x - L.R * .18, L.y - L.R * .2, L.R * .3);
    gl.addColorStop(0, "rgba(255,255,255,.9)"); gl.addColorStop(1, "rgba(255,255,255,0)");
    g.globalAlpha = .8 * fade; g.fillStyle = gl;
    g.beginPath(); g.ellipse(L.x - L.R * .18, L.y - L.R * .2, L.R * .3, L.R * .16, -.6, 0, Math.PI * 2); g.fill();
    g.restore();
  }
}
// A cut fruit comes apart in 3D: its two halves start as the whole fruit, split along the stroke and swing open
// (the Blender openR / openL frames, OPEN_T long) as they fly apart, then rock on their backs as they roll away.
const OPEN_T = .24;
function slice(f, dirx, diry) {
  if (!f || f.gone) return;
  f.gone = true;
  const l = Math.hypot(dirx, diry) || 1, dx = dirx / l, dy = diry / l;
  const m = META.fruit[SPRITE(f.id)] || {}, col = m.juice || "#fff";
  const rot = Math.atan2(dy, dx) - Math.PI / 2;    // the sprites' cut line (their local y) along the stroke
  if (m.clips && m.clips.openR) for (const s of [1, -1]) {
    // the right half (local +x) goes off to the stroke's right, the left half to its left
    const ox = dy * s, oy = -dx * s, v = S * (2.4 + Math.random() * .9), vs = 4.5 + Math.random() * 3;
    world.pieces.push({ id: f.id, half: true, side: s > 0 ? "openR" : "openL", age: 0, vt: 1500, g: f.g, x: f.x, y: f.y,
                        vx: f.vx * .5 + ox * v + dx * 90, vy: f.vy * .55 + oy * v - 120,
                        rot, vr: 0, vr0: s * (2 + Math.random() * 3), spin: -vs * OPEN_T, vs, size: f.size });
  }
  juice(f.x, f.y, col, 22, f.id === "JM" ? 2 : 1, dx, dy);
  FX.cut(f, dx, dy);                         // beads, chunks, seeds, sparkles; a special fruit's burst
  world.cuts.push({ x: f.x, y: f.y, ang: Math.atan2(dy, dx), len: f.size * .6, col, age: 0, dur: .22 });
  SFX.squish(f.id);
}

async function swipe(x0, y0, x1, y1, ms, glow = "#7fd4ff", w = 14, path = null) {
  // bow the stroke a little to one side, like a wrist flick
  const bow = (Math.random() < .5 ? -1 : 1) * Math.hypot(x1 - x0, y1 - y0) * (.06 + Math.random() * .06);
  const nl = Math.hypot(x1 - x0, y1 - y0) || 1;
  const cx = (x0 + x1) / 2 - (y1 - y0) / nl * bow, cy = (y0 + y1) / 2 + (x1 - x0) / nl * bow;
  const b = { x0, y0, x1, y1, cx, cy, path, dur: ms / 1000, age: 0, glow, w };
  world.blades.push(b);
  SFX.swoosh();
  await new Promise(res => setTimeout(res, ms / speed()));
}

/* slash a line of cells: the blade enters before the first and leaves after the last */
async function slashLine(cells, glow) {
  const fr = cells.map(([r, c]) => world.fruit.find(o => o.r === r && o.c === c && !o.gone && o.wave === curWave));
  const ms = 100 + 20 * cells.length;
  // aim where each fruit will be when the blade reaches it (they keep falling while it travels)
  // (the blade runs in real time; in slow motion the fruit only move timeScale as far meanwhile)
  const at = (i, t) => (t *= timeScale, fr[i] ? { x: fr[i].x + fr[i].vx * t, y: fr[i].y + fr[i].vy * t + .5 * (fr[i].g || G) * t * t } : cell(...cells[i]));
  let pts = cells.map((_, i) => at(i, 0));
  for (let pass = 0; pass < 2; pass++) {
    const a = pts[0], b = pts[pts.length - 1], len = Math.hypot(b.x - a.x, b.y - a.y) + S * 1.6;
    pts = cells.map((_, i) => at(i, ((Math.hypot(pts[i].x - a.x, pts[i].y - a.y) + S * .8) / len) * ms / 1000));
  }
  const a = pts[0], b = pts[pts.length - 1];
  const dx = b.x - a.x, dy = b.y - a.y, l = Math.hypot(dx, dy) || 1, ux = dx / l, uy = dy / l;
  const x0 = a.x - ux * S * .8, y0 = a.y - uy * S * .8, x1 = b.x + ux * S * .8, y1 = b.y + uy * S * .8;
  const blade = swipe(x0, y0, x1, y1, ms, glow, 14, [[x0, y0], ...pts.map(q => [q.x, q.y]), [x1, y1]]);
  // the blade's tip reaches the i-th fruit at its point on the curve: (i + 1) / (points - 1) of the stroke
  const segs = pts.length + 1;
  pts.forEach((p, i) => {
    const prev = i ? pts[i - 1] : { x: x0, y: y0 }, nx = pts[i + 1] || { x: x1, y: y1 };
    setTimeout(() => slice(fr[i], nx.x - prev.x, nx.y - prev.y), (i + 1) / segs * ms / speed());
  });
  await blade;
}

/* ---------------------------------------------------------------- a wave */
let curWave = 0;
const fruitAt = (fruits, r, c) => fruits.find(o => o.r === r && o.c === c);
// Every fruit of a wave is dropped on its own from just above the top edge, from rest-ish, and falls under
// gravity with its own air drag (a bigger fruit falls a touch faster), a little sideways drift and a rocking
// tilt. Each one's drop time is solved backwards from its own fall time, so that the wave passes through
// the board around one moment (the cut) - the lower rows leave first - but every fruit is a fraction of a
// second early or late, so the 4x4 streams through loose rather than as a block. After the cut nothing is
// done to them: they keep falling and leave the screen one by one.
function fallTime(dy, v0, vt, g) {
  const k = g / (vt * vt), h = 1 / 240;
  let y = 0, v = v0, t = 0;
  while (y < dy && t < 6) { v += (g - k * v * Math.abs(v)) * h; y += v * h; t += h; }
  return t;
}
function dropBoard(e) {
  curWave++;
  const pace = Math.min(1.7, e.pace * (e.frenzy ? 1.1 : 1));
  const FALL = .9;   // overall fall speed: 10% slower (owner, 2026-11-18). Speeds scale by FALL, gravity by FALL^2
  const g = 720 * (H / 786) * pace * pace * FALL * FALL;   // a touch floaty: they fall a little slower than real   // so the bottom row is still on screen when the last fruit pops
  const jobs = (e.power || []).length + (e.wins || []).length + ((e.scatters || []).length >= 3 ? 1 : 0) + (e.bomb ? 2 : 0);
  const work = .1 + jobs * .08;
  const fruits = [];
  // The 4x4 comes down as one loose, connected formation: every fruit spawns out of sight above the frame and
  // falls in under its own gravity and drag, and its drop time is solved backwards so that at the cut it is on
  // its own cell, give or take a few percent. The bottom row leaves first (it has furthest to go), the rows
  // follow at whatever gaps that takes, so they stay stacked; a small jitter in place, speed, drift and tilt
  // keeps it reading as real fruit, not a rigid block. (Owner, 2026-11-18: spawn above, more organized.)
  for (let r = 3; r >= 0; r--) {
    const rowJ = (Math.random() - .5) * S * .06;            // the row as a whole sags or leads a touch
    for (const c of [0, 1, 2, 3]) {
      const id = e.board[r][c], p = cell(r, c), size = S * (SIZE[id] || 1) * FRUIT_SCALE;
      const light = (SIZE[id] || 1) < .95;
      const f = { id, r, c, wave: curWave, mode: "wait", g,
                  vt: 1000 * Math.sqrt(SIZE[id] || 1) * pace * FALL * (.98 + Math.random() * .04),
                  dropAt: 0, ty: p.y + rowJ + (Math.random() - .5) * S * .08,
                  x0: p.x + (Math.random() - .5) * S * .06, y0: -size * .75 - S * .9,
                  vx0: (Math.random() - .5) * 30 * FALL, v0: (115 + Math.random() * 30) * pace * FALL,
                  x: p.x, y: -S * 3, vx: 0, vy: 0,
                  rot: (Math.random() - .5) * .35, vr: (Math.random() - .5) * 2, spin: Math.random() * 7,
                  vs: (Math.random() < .5 ? -1 : 1) * (1.5 + Math.random() * 2.5),
                  ph: Math.random() * 6.3, wobA: (light ? .11 : .055) * (.7 + Math.random() * .6), wobF: 3 + Math.random() * 2,
                  size, delay: 0,
                  glow: id === "SC" ? "#ffd84a" : id === "BOMB" ? "#ff3b2b" : id === "FRZ" ? "#c8f0ff" : null };
      if (id.startsWith("PW")) f.glow = { PW2: "#5ab4ff", PW3: "#c56bff", PW5: "#ff6a3a", PW10: "#ffd700" }[id];
      fruits.push(f);
      world.fruit.push(f);
    }
  }
  const need = fruits.map(f => fallTime(f.ty - f.y0, f.v0, f.vt, g));
  const cut = simClock + .03 + Math.max(...need);            // when the formation sits on the board
  fruits.forEach((f, i) => { f.dropAt = cut - need[i]; delete f.ty; });
  SFX.throw();
  const blk = { fruits, released: false };
  // the blade strikes as the formation reaches the board; the next wave waits until this one has mostly fallen away
  return { fruits, blk, hang: untilSim(cut), through: untilSim(cut + work + .45 / (pace * FALL)) };
}
function releaseOne(f) { f.rel = true; }
function releaseBoard(fruits, blk) { blk.released = true; }   // (they fall on by themselves)

async function playWave(e) {
  setWave(e);
  if (e.frenzy && !state.skip) SFX.clack();
  const { fruits, blk, hang, through } = dropBoard(e);
  await hang;
  if (e.bomb) {
    await bombWave(e, fruits, blk);
    return;
  }
  const sc = e.scatters || [];
  let starsCut = false;
  if (sc.length >= 2 && !state.skip) starsCut = await starCinematic(sc, fruits);
  else if (sc.length) {
    SFX.chime(sc.length);
    for (const [r, c] of sc) { const f = fruitAt(fruits, r, c); ring(f.x, f.y, "#ffd84a", S * .3, S * .8, .6, 6); FX.ping(f); }
  }
  // power fruit first: sliced, and their effect flies to the frenzy panel
  for (const p of (e.power || [])) {
    const [r, c] = p.cell, f = fruitAt(fruits, r, c);
    const q = { x: f.x, y: f.y };
    await swipe(f.x - S * .7, f.y + S * .5, f.x + S * .7, f.y - S * .5, 110, p.kind === "mult" ? "#b9a2ff" : "#bff0ff", 16);
    q.x = f.x; q.y = f.y;
    slice(f, 1, -.7);
    if (p.kind === "mult") {
      pop(q.x, q.y, `x${p.value}`, "#bfe4ff", S * .55, 1.1, 70);
      ring(q.x, q.y, "#9ad7ff", S * .2, S * 1.4, .55, 10);
      SFX.power();
      flyTo(q.x, q.y, $("fsMult"), `x${p.value}`, "#9ad7ff");
    } else {
      pop(q.x, q.y, T("BOMB CHANCE RESET"), "#d8f6ff", S * .3, 1.3, 70);
      SFX.freeze();
      frost();
      setTimeout(() => setBomb(p.bombChance, true), 520 / speed());
    }
    await sleep(40);
  }
  // the paying lines
  const glow = e.frenzy ? "#ffb347" : "#7fd4ff";
  const lineFruit = w => w.cells.map(([r, c]) => fruitAt(fruits, r, c));
  const cutLine = async (w, overlap) => {
    const ends = [w.cells[0], w.cells[w.cells.length - 1]].map(([r, c]) => fruitAt(fruits, r, c) || cell(r, c));
    const mid = { x: (ends[0].x + ends[1].x) / 2, y: (ends[0].y + ends[1].y) / 2 };
    const cutting = slashLine(w.cells, glow);
    await sleep(55);                                  // the next line starts while this blade is still out
    const e2 = [w.cells[0], w.cells[w.cells.length - 1]].map(([r, c]) => fruitAt(fruits, r, c));
    const px = e2.every(Boolean) ? (e2[0].x + e2[1].x) / 2 : mid.x, py = e2.every(Boolean) ? (e2[0].y + e2[1].y) / 2 : mid.y;
    pop(px, py - S * .2, fmt(fromHundredths(w.win)), "#ffe36b", Math.max(22, S * .3), 1.2, 40);
    SFX.coin(w.count);
    SFX.music.cue("line", { i: e.wins.indexOf(w), n: w.count });
    if (!overlap) await cutting; else return cutting;
  };
  // Cinematic: the world drops into slow motion and the camera closes in. Up to 3 lines in the base game get
  // a close-up each, cut one after another; more lines, or any line in the frenzy (50 waves of it), get one
  // shorter wide shot of every paying fruit with the lines cut overlapping as before. Skip plays it straight.
  const cine = e.wins.length && !state.skip;
  if (cine) {
    const solo = !e.frenzy && e.wins.length <= 3;
    tweenTime(e.frenzy ? .45 : .2, 300);
    if (!e.frenzy) SFX.slowIn();
    SFX.music.duck(e.frenzy ? .75 : .5, 500);
    if (solo) {
      for (let i = 0; i < e.wins.length; i++) {
        camFocus(lineFruit(e.wins[i]));
        await sleep(i ? 380 : 480);                   // let the camera settle on the line
        await cutLine(e.wins[i]);
        await sleep(220);                             // hold on the juice in slow motion
      }
    } else {
      camFocus(e.wins.flatMap(lineFruit));
      await sleep(e.frenzy ? 240 : 380);
      const cuts = [];
      for (const w of e.wins) cuts.push(await cutLine(w, true));
      await Promise.all(cuts);
      await sleep(e.frenzy ? 80 : 200);
    }
    camFocus(null);
    SFX.music.duck(1, 900);
    if (!e.frenzy) SFX.slowOut();
    await tweenTime(1, 560);
  } else {
    for (const w of e.wins) await cutLine(w);
  }
  if (e.combo > 1) {
    pop(W / 2, GY - S * .05, `${e.wins.length} ${T("LINE COMBO")}  x${e.combo}`, "#ff9a3c", Math.max(26, S * .34), 1.4, 20);
    SFX.combo(e.combo, e.wins.length);
  }
  // 3+ star fruit: they burst and the frenzy is on (unless the star cinematic already cut them)
  if (sc.length >= 3 && !starsCut) {
    for (const [r, c] of sc) {
      const f = fruitAt(fruits, r, c);
      swipe(f.x - S * .6, f.y - S * .6, f.x + S * .6, f.y + S * .6, 110, "#ffd84a", 18);
      setTimeout(() => slice(f, 1, 1), 55 / speed());
      await sleep(70);
    }
  }
  if (e.waveWin > 0) { addWin(e.total); SFX.music.cue("win", { lines: e.wins.length, combo: e.combo }); }
  setCombo(e);
  releaseBoard(fruits, blk);                          // the rest drop out one at a time
  await through;                                      // the next wave can start falling in behind this one
  if (e.side && e.side.length) sideFruit(e);
  await sleep(e.frenzy ? 20 : 80);
}

// The bonus icons (golden star fruit), cinematic (owner, 2026-11-18): the world nearly stops, the camera closes
// in on the stars and the music drops away under a filter; each star lights up on a heartbeat, the beats coming
// faster and faster. Two stars is a tease - so close - and time comes back. Three or more: a riser builds, a beat
// of silence, then one hard hit - flash, taiko, impact, every star cut at once, a gong - and back to speed for
// the lines and the frenzy. Returns whether it cut the stars. (Skip plays the plain version.)
async function starCinematic(sc, fruits) {
  const stars = sc.map(([r, c]) => fruitAt(fruits, r, c)).filter(Boolean);
  if (!stars.length) return false;
  const big = stars.length >= 3;
  SFX.slowIn(); SFX.music.duck(big ? .35 : .6, 900);
  SFX.music.cue("tension", { on: true });          // a low drone holds under the stars
  tweenTime(big ? .06 : .12, 420);
  cam.maxZ = big ? 1.75 : 1.6;
  camFocus(stars);
  await sleep(700);                                   // the camera glides in
  const gaps = big ? [620, 470, 360, 280, 230, 200] : [640, 520];
  for (let i = 0; i < stars.length; i++) {
    const f = stars[i];
    SFX.heartbeat(i); SFX.starPing(i);
    ring(f.x, f.y, "#ffd84a", S * .25, S * (1 + i * .15), .8, 8);
    FX.ping(f); FX.sparkle(f.x, f.y, "#ffe27a", 10);
    shake = Math.min(.45, .08 + i * .07);
    if (big && i === 1) SFX.riser();                  // the build starts under the second beat
    await sleep(gaps[Math.min(i, gaps.length - 1)]);
  }
  if (!big) {                                         // a tease: two stars, time comes back
    await sleep(260);
    camFocus(null); SFX.slowOut(); SFX.music.duck(1, 1200); SFX.music.cue("tension", { on: false });
    await tweenTime(1, 700);
    return false;
  }
  SFX.music.duck(0, 300); SFX.music.cue("tension", { on: false });   // a beat of silence...
  await sleep(380);
  const fl = $("flash");                              // ...and the hit
  fl.style.transition = "none"; fl.style.opacity = ".85";
  requestAnimationFrame(() => { fl.style.transition = "opacity .6s ease-out"; fl.style.opacity = "0"; });
  SFX.impact(); SFX.taiko(); shake = .8;
  stars.forEach((f, i) => {
    swipe(f.x - S * .7, f.y - S * .7, f.x + S * .7, f.y + S * .7, 90, "#ffd84a", 20);
    setTimeout(() => { slice(f, 1, 1); ring(f.x, f.y, "#fff2b0", S * .2, S * 1.6, .7, 12); }, (30 + i * 25) / speed());
  });
  setTimeout(() => SFX.gong(), 160 / speed());
  await sleep(650);                                   // the juice hangs in the air
  cam.maxZ = 1.6;
  camFocus(null); SFX.slowOut(); SFX.music.duck(1, 1500);
  await tweenTime(1, 800);
  return true;
}

function sideFruit(e) {
  e.side.forEach((s, i) => {
    const fromL = s.from === "L";
    const y = GY + S * (0.3 + Math.random() * 3.4);
    const f = { id: s.sym, r: -1, c: -1, wave: -1, vt: 2200, x: fromL ? -S : W + S, y, vx: (fromL ? 1 : -1) * (W * .9 + Math.random() * 200),
                vy: -500 - Math.random() * 300, rot: 0, vr: (Math.random() - .5) * 6, spin: Math.random() * 7, vs: 5, size: S * .85 * (SIZE[s.sym] || 1) * FRUIT_SCALE, delay: i * 0.07 };
    world.fruit.push(f);
    setTimeout(() => {
      if (f.gone) return;
      swipe(f.x - S * .5, f.y + S * .4, f.x + S * .5, f.y - S * .4, 90, "#ffb347", 10);
      slice(f, 1, -.8);
      SFX.music.cue("side");
      pop(f.x, f.y, fmt(fromHundredths(s.win)), "#ffe9a8", Math.max(16, S * .2), .8, 30);
    }, (420 + i * 70 + Math.random() * 120) / speed());
  });
}

async function bombWave(e, fruits, blk) {
  const [r, c] = e.bomb, b = fruitAt(fruits, r, c);
  SFX.fuse();
  for (let i = 0; i < 2; i++) { ring(b.x, b.y, "#ff3b2b", S * .2, S * .9, .35, 7); await sleep(170); }
  await swipe(b.x - S * 1.4, b.y - S * .3, b.x + S * .1, b.y + S * .05, 140, "#ff8a7a", 16);
  const p = { x: b.x, y: b.y };
  b.gone = true;
  SFX.boom(); SFX.impact(); SFX.music.cue("bomb");
  const fl = $("flash");
  fl.style.transition = "none"; fl.style.opacity = "1";
  requestAnimationFrame(() => { fl.style.transition = "opacity .7s ease-out"; fl.style.opacity = "0"; });
  shake = 1;
  ring(p.x, p.y, "#fff", S * .3, S * 4, .7, 26);
  ring(p.x, p.y, "#ffb347", S * .2, S * 3, .55, 16);
  world.booms.push({ x: p.x, y: p.y - S * .3, size: S * 5.4, t: 0, dur: 1.15, smoke: true });
  FX.boom(p.x, p.y);
  for (let i = 0; i < 40; i++) {           // embers: hot sparks thrown out and falling
    const a = Math.random() * Math.PI * 2, v = 300 + Math.random() * 900;
    world.drops.push({ x: p.x, y: p.y, vx: Math.cos(a) * v, vy: Math.sin(a) * v - 250, r: 1.5 + Math.random() * 2.8,
                       col: Math.random() < .5 ? "#ffd27a" : "#ff7a12", life: .5 + Math.random() * .8 });
  }
  for (let i = 0; i < 9; i++) {            // pieces of the bomb's iron shell
    const a = Math.random() * Math.PI * 2, v = 500 + Math.random() * 700;
    world.drops.push({ x: p.x, y: p.y, vx: Math.cos(a) * v, vy: Math.sin(a) * v - 300, r: 4 + Math.random() * 6,
                       col: "#22232b", life: .9 + Math.random() * .6 });
  }
  // a scorch on the wood where it went off
  gs.save(); const sg = gs.createRadialGradient(p.x, p.y, 0, p.x, p.y, S * 1.5);
  sg.addColorStop(0, "rgba(15,8,4,.55)"); sg.addColorStop(1, "rgba(15,8,4,0)");
  gs.fillStyle = sg; gs.beginPath(); gs.arc(p.x, p.y, S * 1.5, 0, Math.PI * 2); gs.fill(); gs.restore();
  for (const f of fruits) {
    if (f.gone) continue;
    f.vt *= 2.6;
    const dx = f.x - p.x, dy = f.y - p.y, d = Math.hypot(dx, dy) || 1;
    f.vx = dx / d * (900 + Math.random() * 500); f.vy = dy / d * (900 + Math.random() * 500) - 300; f.vr *= 4;
  }
  blk.released = true;
  timeScale = 1;
  banner(T("BOOM!"), T("The frenzy is over"), "bomb");
  await sleep(1300);
  hideBanner();
}

/* ---------------------------------------------------------------- frenzy */
let frenzyWin = 0;
async function frenzyStart(e) {
  state.frenzy = true;
  frenzyWin = 0;
  SFX.gong(); SFX.taiko();
  SFX.music.cue("bonusStart");
  setTimeout(() => SFX.music.play("frenzy", 2.6), 600);
  await bonusIntro(e);
  document.body.classList.add("frenzy");
  document.body.classList.toggle("xf", !!e.xtreme);
  FX.setFrenzy(e.xtreme ? 2 : 1);
}

// The bonus lands (orleans' bonusIntro, in our paint): the game fades to black, the wall comes up with the
// FRUIT FRENZY lettering (XTREME FRENZY for the bought Xtreme), the waves on offer and how it works, and the
// player's click (or Space / Enter) takes them in: black again, then the frenzy with its counter plate.
// Autoplay holds long enough to read and goes on by itself.
function bonusHow(e) {
  const x = !!e.xtreme;
  return `<p><strong>${T("How the frenzy works")}</strong></p>` +
    `<p>${T("Waves keep falling, faster and faster, for up to")} <b>50</b>. ${T("Every wave may carry a")} <b>${T("bomb")}</b>: ` +
    `${T("the chance starts at")} <b>${Math.round((e.bombChance || .05) * 100)}%</b> ${T("and rises a little every wave. A bomb ends the frenzy - everything you won is kept.")}</p>` +
    `<p>${T("Slice")} <b>${T("multiplier peaches")}</b> ${x ? "(x3, x5, x10)" : "(x2, x3, x5, x10)"} ${T("and they add together into one multiplier for every win after. Frost grapes knock the bomb chance back down. Side fruit pays every wave.")}</p>` +
    `<p>${(e.mult || 1) > 1 ? `${T("Your frenzy starts at")} <b>x${e.mult}</b>. ` : ""}${T("Survive all 50 waves to slice the")} <b>${T("Gold Melon")}</b>.</p>`;
}
function bonusIntro(e) {
  return new Promise(resolve => {
    const x = !!e.xtreme;
    const wrap = document.createElement("div");
    wrap.className = "bonusintro" + (x ? " x" : "");
    wrap.setAttribute("role", "dialog");
    wrap.setAttribute("aria-label", x ? "Xtreme Frenzy" : "Fruit Frenzy");
    wrap.innerHTML =
      `<div class="wall"></div>` +
      `<div class="inner"><div class="bstack">` +
        `<div class="blogo">${fnHTML(x ? "Xtreme Frenzy" : "Fruit Frenzy", x ? "pink shine" : "red shine")}</div>` +
        `<div class="byou">${fnHTML(T("Up to"), "white")}</div>` +
        `<div class="bnum" aria-label="${e.maxWaves || 50}"><i class="brays" aria-hidden="true"></i><div class="bfig">${numeralRow(String(e.maxWaves || 50))}</div></div>` +
        `<div class="bfs">${fnHTML(T("Frenzy waves"), "gold")}</div>` +
        `<div class="bhow">${bonusHow(e)}</div>` +
        `<div class="bcont">${T("Click or press Space to continue")}</div>` +
      `</div></div>`;
    document.body.appendChild(wrap);
    const stack = wrap.querySelector(".bstack");
    const fit = () => stack.style.setProperty("--fit", Math.min(1, wrap.clientHeight * .94 / Math.max(1, stack.offsetHeight)).toFixed(3));
    fit();
    if (document.fonts) document.fonts.ready.then(fit);
    addEventListener("resize", fit);
    let phase = 0, hold = null;
    const onKey = ev => { if (ev.code !== "Space" && ev.code !== "Enter") return; ev.preventDefault(); ev.stopPropagation(); go(); };
    const go = () => {
      if (phase !== 1) return;
      phase = 2;
      clearTimeout(hold);
      document.removeEventListener("keydown", onKey, true);
      removeEventListener("resize", fit);
      SFX.tick();
      wrap.classList.remove("up");
      setTimeout(() => {
        const card = $("fsCard");
        card.classList.remove("leaving");
        card.classList.toggle("x", x);
        paintFs(0, e.maxWaves || 50, e.mult || 1, e.bombChance || .05);
        card.classList.add("on");
        wrap.classList.remove("black");
        setTimeout(() => { wrap.remove(); resolve(); }, 520);
      }, 700);
    };
    wrap.addEventListener("click", go);
    document.addEventListener("keydown", onKey, true);
    requestAnimationFrame(() => {
      wrap.classList.add("black");
      setTimeout(() => {
        wrap.classList.add("up");
        phase = 1;
        if (state.auto > 0 || state.replay) hold = setTimeout(go, 3200 / speed());
      }, 520);
    });
  });
}
async function frenzyEnd(e) {
  if (e.reason !== "bomb") { banner(T("ALL 50 WAVES!"), ""); await sleep(1400); hideBanner(); }
  await sleep(300);
  state.frenzy = false;
  state.hadFrenzy = true;
  SFX.music.cue("bonusEnd");
  SFX.music.play("base", 2.8);
  document.body.classList.remove("frenzy", "xf");
  FX.setFrenzy(0);
  frostOff();
  const card = $("fsCard");
  if (card.classList.contains("on")) {
    card.classList.add("leaving");
    setTimeout(() => card.classList.remove("on", "leaving"), 380);
  }
  await sleep(300);
}
async function finale(e) {
  banner("GOLD MELON", T("slice it!"));
  await sleep(1000);
  hideBanner();
  const x = W / 2, y = GY + 2 * S;
  const m = { id: "JM", r: -1, c: -1, wave: -1, mode: "held", vt: 1800, x, y: -S * 2, vx: 0, vy: 0, rot: 0, vr: .4, spin: 0, vs: 1.2, size: S * SIZE.JM, delay: 0, glow: "#ffd700" };
  world.fruit.push(m);
  // drop in and hover
  const t0 = performance.now(), from = m.y;
  await new Promise(res => { const st = () => { const k = Math.min(1, (performance.now() - t0) / (600 / speed())); m.y = from + (y - from) * (1 - (1 - k) ** 3); m.vy = 0; k < 1 ? requestAnimationFrame(st) : res(); }; st(); });
  let acc = 0;
  for (let i = 0; i < e.hits; i++) {
    const a = Math.random() * Math.PI, dx = Math.cos(a) * S * 1.6, dy = Math.sin(a) * S * 1.2;
    swipe(x - dx, y - dy, x + dx, y + dy, 90, "#ffd84a", 14);
    acc += e.perHit;
    juice(x + (Math.random() - .5) * S, y + (Math.random() - .5) * S, "#ff3b4e", 8, .8);
    pop(x + (Math.random() - .5) * S * 1.6, y - S * (0.6 + Math.random() * .6), fmt(fromHundredths(e.perHit)), "#ffe36b", Math.max(16, S * .2), .7, 40);
    m.vr = Math.min(6, m.vr + .3); shake = Math.min(.35, shake + .08);
    SFX.hit(i);
    await sleep(Math.max(55, 150 - i * 4));
  }
  m.mode = "fall";
  slice(m, 1, 0);
  frenzyWin += e.win;
  addWin(e.total);
  pop(x, y, fmt(fromHundredths(e.win)), "#ffd84a", Math.max(36, S * .55), 1.8, 60);
  await sleep(1200);
}

function frost() { $("frost").style.opacity = "1"; }
function frostOff() { $("frost").style.opacity = "0"; }

/* ---------------------------------------------------------------- side panels */
function paintFs(done, total, mult, bombP) {
  const m = $("fsMult"), was = m.dataset.v;
  m.dataset.v = mult;
  m.innerHTML = numeralRowWhite("x" + mult);
  if (was != null && was !== String(mult) && done > 0) { m.classList.remove("bump"); void m.offsetWidth; m.classList.add("bump"); }
  setBomb(bombP);
}
function setBomb(p, reset = false) {
  const el = $("fsBomb");
  if (!el) return;                          // (the bomb chance is no longer shown on the wall)
  el.innerHTML = numeralRowWhite(Math.round(p * 100) + "%");
  el.classList.toggle("hot", p >= .15);
  el.classList.toggle("cool", reset);
  if (reset) { el.classList.remove("bump"); void el.offsetWidth; el.classList.add("bump"); }
}
function setWave(e) {
  if (!e.frenzy) { frostOff(); return; }
  paintFs(e.n + 1, e.maxWaves || 50, e.mult, e.bombChance || 0);
}
function setCombo(e) {
  if (e.frenzy) {
    frenzyWin += e.waveWin;
    if ((e.power || []).some(p => p.kind === "frost")) setTimeout(frostOff, 1400 / speed());
  }
}
function flyTo(x, y, el, text, col) {
  const d = document.createElement("div");
  d.className = "winpop";
  d.textContent = text;
  Object.assign(d.style, { left: x + "px", top: y + "px", fontSize: Math.max(22, S * .35) + "px", color: col, translate: "-50% -50%", transition: `left .55s cubic-bezier(.5,0,.3,1), top .55s cubic-bezier(.5,0,.3,1), opacity .2s .5s` });
  document.body.appendChild(d);
  const r = el.getBoundingClientRect();
  requestAnimationFrame(() => requestAnimationFrame(() => { d.style.left = r.left + r.width / 2 + "px"; d.style.top = r.top + r.height / 2 + "px"; d.style.opacity = "0"; }));
  setTimeout(() => { d.remove(); el.classList.remove("bump"); void el.offsetWidth; el.classList.add("bump"); }, 560 / speed());
}

/* ---------------------------------------------------------------- banner, win */
function banner(big, sub, cls = "") {
  const b = $("banner");
  $("bannerBig").innerHTML = fnHTML(big, cls === "bomb" ? "red shine" : "gold shine");
  $("bannerSub").textContent = sub;
  b.className = "banner show " + cls;
}
function hideBanner() { const b = $("banner"); if (b.classList.contains("show")) b.className = b.className.replace("show", "hide"); }
let shownWin = 0;
// a figure mid-count shows whole cents (whole units for a 0-decimal currency), never sub-cent digits
const cents = a => { const step = Math.pow(10, 6 - (({ JPY: 0, IDR: 0, KRW: 0, VND: 0, CLP: 0 })[RGS.state.currency] ?? 2)); return Math.round(a / step) * step; };
function addWin(totalHundredths) {
  const target = fromHundredths(totalHundredths);
  const from = shownWin, t0 = performance.now(), dur = 500;
  shownWin = target;
  const el = $("roundWin");
  $("winStat").classList.toggle("zero", target <= 0);
  const st = () => {
    const k = Math.min(1, (performance.now() - t0) / dur);
    el.textContent = fmt(k < 1 ? cents(from + (target - from) * k) : target);
    if (k < 1) requestAnimationFrame(st);
  };
  st();
  el.classList.remove("pop"); void el.offsetWidth; el.classList.add("pop");
}
async function bigWin(total) {
  const x = total / bet();
  if (x < 10) return;
  const tier = x >= 100 ? "EPIC WIN" : x >= 50 ? "MEGA WIN" : x >= 25 ? "SUPER WIN" : "BIG WIN";
  SFX.taiko(); SFX.music.cue("bigwin");
  banner(tier, fmt(0));
  SFX.coinShower();
  const t0 = performance.now(), dur = Math.min(4500, 1500 + x * 25) / speed();
  await new Promise(res => {
    const st = () => {
      const k = Math.min(1, (performance.now() - t0) / dur);
      $("bannerSub").textContent = fmt(cents(total * (1 - (1 - k) ** 2)));
      if (Math.random() < .3) juice(Math.random() * W, Math.random() * H * .7, ["#ff3b4e", "#ffd23a", "#7fd61f", "#ff9a12"][Math.floor(Math.random() * 4)], 6, .7);
      k < 1 && !state.skipBig ? requestAnimationFrame(st) : res();
    };
    st();
  });
  $("bannerSub").textContent = fmt(total);
  await sleep(1400);
  hideBanner();
}

/* ---------------------------------------------------------------- the round */
async function playEvents(events) {
  for (const e of events) {
    if (e.type === "wave") await playWave(e);
    else if (e.type === "frenzyStart") await frenzyStart(e);
    else if (e.type === "finale") await finale(e);
    else if (e.type === "frenzyEnd") await frenzyEnd(e);
  }
  await sleep(500);
}

async function spin(mode = "base") {
  if (mode === "base" && state.boost && modeCost.boost > 0) mode = "boost";
  if (state.playing) { state.skip = true; return; }
  SFX.swordDraw();
  const cost = Math.round(bet() * (modeCost[mode] || 1));
  if (cost > RGS.state.balance) { notice(T("Not enough balance for this bet.")); stopAuto(); return; }
  state.playing = true; state.skip = false; state.mode = mode;
  setButtons(false);
  shownWin = 0; $("roundWin").textContent = fmt(0); $("winStat").classList.add("zero");
  const sb = $("spinBtn");
  sb.classList.remove("spun"); void sb.offsetWidth; sb.classList.add("spun", "armed");
  spinArrows.start();
  let d;
  try {
    d = await RGS.play(bet(), mode);
  } catch (err) {
    state.playing = false; setButtons(true); $("spinBtn").classList.remove("armed");
    handleError(err);
    stopAuto();
    return;
  }
  showBalance(RGS.state.balance, true);
  const rnd = d.round || {};
  await runRound(rnd);
}

async function runRound(rnd) {
  const events = rnd.events || rnd.state || [];
  try { await playEvents(events); } catch (e) { console.error(e); }
  const payout = rnd.payout != null ? rnd.payout : Math.round((rnd.payoutMultiplier || 0) * (rnd.amount || bet()));
  const hadFrenzy = !!state.hadFrenzy;
  state.hadFrenzy = false;
  const stake = rnd.amount || bet();
  if (payout > 0 && (hadFrenzy || payout > OVER_BOARD_AT * stake)) await totalWinScreen(payout, { total: hadFrenzy });
  try { await RGS.endRound(); } catch (err) { handleError(err); }
  showBalance(RGS.state.balance);
  state.playing = false; state.skip = false;
  $("spinBtn").classList.remove("armed");
  spinArrows.stop();
  setButtons(true);
  if (state.auto > 0) {
    state.auto--;
    paintAuto();
    if (state.auto > 0) setTimeout(() => spin("base"), 350);
  }
}

/* ---------------------------------------------------------------- HUD wiring */
function fitFigure(el, text) {   // orleans: long figures step down a size
  el.classList.toggle("long", text.length > 12 && text.length <= 16);
  el.classList.toggle("vlong", text.length > 16);
}
function showBalance(a) {
  const el = $("balance");
  el.textContent = fmt(a);
  fitFigure(el, fmt(a));
  $("balanceLbl").innerHTML = `${T("Balance")}<span class="cur">${RGS.currencyName()}</span>`;
}
function refreshBet() {
  const boost = !!state.boost && modeCost.boost > 0, shown = Math.round(bet() * (boost ? modeCost.boost : 1));
  $("betVal").textContent = fmt(shown);
  fitFigure($("betVal"), fmt(shown));
  const st = $("betVal").closest(".hudstat");
  if (st) { st.classList.toggle("boost", boost); const l = st.querySelector(".lbl"); if (l) l.textContent = boost ? T("Boost") : T("Bet"); }
  if (!state.playing && !shownWin) $("roundWin").textContent = fmt(0);
  try { sessionStorage.setItem("juicedojo.bet", String(bet())); } catch (e) { /* ignore */ }
  paintBonus();
  setButtons(!state.playing);
}
function setButtons(on) {
  $("spinBtn").textContent = on ? T("Spin") : T("Skip >>");
  $("betUp").disabled = !on || state.betIdx >= state.bets.length - 1;
  $("betDown").disabled = !on || state.betIdx <= 0;
  $("bonusBtn").disabled = !on || state.replay;
  $("autoBtn").disabled = !(on || state.auto > 0);
}
function notice(msg) {
  const n = $("notice");
  n.textContent = msg; n.classList.add("on");
  clearTimeout(n._t); n._t = setTimeout(() => n.classList.remove("on"), 2600);
}
function handleError(err) {
  const code = err && err.code;
  if (code === "ERR_IPB") return notice(T("Not enough balance for this bet."));
  if (code === "ERR_IS" || code === "ERR_ATE") return fatal("Session expired", "Your session has ended. Reload the game to continue.");
  notice((err && err.message) || "Something went wrong - please try again.");
}
function fatal(title, msg) {
  $("errorTitle").textContent = title; $("errorMsg").textContent = msg; $("errorWrap").hidden = false;
}
$("errorRetry").onclick = () => location.reload();

$("spinBtn").onclick = () => { SFX.unlock(); spin("base"); };
$("betUp").onclick = () => { if (state.betIdx < state.bets.length - 1) { state.betIdx++; refreshBet(); SFX.tick(); } };
$("betDown").onclick = () => { if (state.betIdx > 0) { state.betIdx--; refreshBet(); SFX.tick(); } };
$("rapidBtn").onclick = () => {
  state.turbo = !state.turbo;
  $("rapidBtn").classList.toggle("on", state.turbo);
  $("rapidBtn").setAttribute("aria-pressed", state.turbo);
};
document.addEventListener("keydown", e => {
  if (e.code === "Space" && !e.repeat && document.activeElement.tagName !== "BUTTON" && $("bonusWrap").hidden && $("infoWrap").hidden && !document.querySelector(".bonusintro")
      && !$("intro") && !document.querySelector(".features")) {   // (not under the opening screens)
    e.preventDefault(); if (!state.replay) spin("base");
  }
});

// pop-ups over the bar use orleans' own placePop (hud.js)
function togglePop(id, btn) {
  const p = $(id), open = p.hidden;
  for (const q of ["autoPop", "volPop"]) $(q).hidden = true;
  $("audioBtn").classList.remove("open");
  if (open) { p.hidden = false; placePop(p, btn); if (id === "volPop") btn.classList.add("open"); }
}
document.addEventListener("pointerdown", e => {
  if (!e.target.closest(".hudpop, #autoBtn, #audioBtn")) { $("autoPop").hidden = true; $("volPop").hidden = true; $("audioBtn").classList.remove("open"); }
});

// auto play
function paintAuto() {
  const n = $("autoN");
  n.hidden = !(state.auto > 0);
  n.textContent = state.auto;
  $("autoBtn").classList.toggle("on", state.auto > 0);
}
function stopAuto() { state.auto = 0; paintAuto(); }
$("autoBtn").onclick = () => {
  if (state.auto > 0) { stopAuto(); return; }
  $("autoBet").textContent = fmt(bet());
  togglePop("autoPop", $("autoBtn"));
};
for (const b of document.querySelectorAll("#autoOpts button")) b.onclick = () => {
  state.autoPick = +b.dataset.n;
  for (const o of document.querySelectorAll("#autoOpts button")) { o.classList.toggle("on", o === b); o.setAttribute("aria-pressed", o === b); }
};
$("autoYes").onclick = () => { $("autoPop").hidden = true; state.auto = state.autoPick; paintAuto(); if (!state.playing) spin("base"); };

// volume
const vol = { sfx: 80, music: 60 };
try { Object.assign(vol, JSON.parse(localStorage.getItem("juicedojo.vol") || "{}")); } catch (e) { /* ignore */ }
// the music was replaced with calm themes (owner, 2026-11-18): a slider muted for the old ones comes back up once
try { if (localStorage.getItem("juicedojo.musicv") !== "2") { if (vol.music < 20) vol.music = 60; localStorage.setItem("juicedojo.musicv", "2"); localStorage.setItem("juicedojo.vol", JSON.stringify(vol)); } } catch (e) { /* ignore */ }
function paintVol() {
  for (const [k, bar, num] of [["sfx", "sfxBar", "sfxNum"], ["music", "musicBar", "musicNum"]]) {
    $(bar).style.setProperty("--v", vol[k] + "%"); $(num).textContent = vol[k]; $(bar).setAttribute("aria-valuenow", vol[k]);
  }
  $("audioBtn").classList.toggle("off", vol.sfx === 0 && vol.music === 0);
  SFX.setVolume(vol.sfx / 100, vol.music / 100);
}
for (const [k, bar] of [["sfx", "sfxBar"], ["music", "musicBar"]]) {
  const el = $(bar);
  const set = x => { const r = el.getBoundingClientRect(); vol[k] = Math.round(Math.max(0, Math.min(1, (x - r.left) / r.width)) * 100); paintVol(); try { localStorage.setItem("juicedojo.vol", JSON.stringify(vol)); } catch (e) { /* */ } };
  el.addEventListener("pointerdown", e => { el.setPointerCapture(e.pointerId); el.classList.add("dragging"); set(e.clientX); });
  el.addEventListener("pointermove", e => { if (el.hasPointerCapture(e.pointerId)) set(e.clientX); });
  el.addEventListener("pointerup", () => el.classList.remove("dragging"));
  el.addEventListener("keydown", e => { if (e.key === "ArrowRight" || e.key === "ArrowUp") { vol[k] = Math.min(100, vol[k] + 5); paintVol(); } if (e.key === "ArrowLeft" || e.key === "ArrowDown") { vol[k] = Math.max(0, vol[k] - 5); paintVol(); } });
}
$("audioBtn").onclick = () => { SFX.unlock(); togglePop("volPop", $("audioBtn")); };
document.addEventListener("click", ev => { const b = ev.target.closest && ev.target.closest("button"); if (b && b.id !== "spinBtn") SFX.uiClick(); }, true);

// rules
$("menuBtn").onclick = () => { $("rulesBody").innerHTML = RULES.html({ T, fmt, bet: bet(), cost: modeCost.bonus, xcost: modeCost.extremebonus, boost: modeCost.boost, social: RGS.social }); RULES.paint(SHEETS, META, drawFruit); $("infoWrap").hidden = false; };
$("infoClose").onclick = () => { $("infoWrap").hidden = true; };
$("infoWrap").addEventListener("pointerdown", e => { if (e.target === $("infoWrap")) $("infoWrap").hidden = true; });

// bonus shop
// The shop's cards (orleans' format), in order. A mode the RGS does not offer shows no card.
const BUYS = [
  { mode: "bonus", key: "frenzy", title: "Fruit Frenzy", desc: "Up to 50 waves until a bomb. Peaches stack one multiplier.", heat: 3, acc: "#F2B230", icon: "assets/bonus/icon_frenzy.webp" },
  { mode: "extremebonus", key: "xfrenzy", title: "Xtreme Frenzy", desc: "Starts at x3. Peaches x3 or more, bombs climb slower.", heat: 5, acc: "#ff5fa2", icon: "assets/bonus/icon_xfrenzy.webp", x: true },
  // Bonus Boost is not a buy: it is switched on, and every base spin after it is a boosted one (spin)
  { mode: "boost", key: "boost", title: "Bonus Boost", desc: "Every spin 1.6x as likely to land Fruit Frenzy.", heat: 2, acc: "#F2B230", toggle: true },
];
// the Boost card's banner mark: "1.6x" in vector, as orleans draws it
const BOOST_MARK = `<svg class="bs16" viewBox="0 0 200 110" aria-hidden="true">
  <g transform="rotate(-7 100 58)">
    <text class="glow" x="100" y="80" text-anchor="middle" font-size="78" fill="none" stroke="#F2B230" stroke-width="14" opacity=".35" style="filter:blur(6px)">1.6x</text>
    <text x="100" y="80" text-anchor="middle" font-size="78" fill="#F2B230" stroke="#000" stroke-width="11">1.6x</text>
    <path d="M62 84 q3 16 0 22 a4 4 0 0 0 8 0 q-3 -6 0 -22z M128 86 q2 10 0 14 a3.4 3.4 0 0 0 7 0 q-2 -4 0 -14z" fill="#F2B230" stroke="#000" stroke-width="3"/>
    <text x="100" y="80" text-anchor="middle" font-size="78" fill="none" stroke="#fff" stroke-width="1.6" opacity=".55" transform="translate(-2 -3)">1.6x</text>
  </g></svg>`;
const fmtMult = c => (Math.round(c * 100) / 100).toString();
let bshopArmed = null, bshopArmT = 0;
function bshopCard(o) {
  const card = document.createElement("div");
  card.className = "bscard" + (o.x ? " x" : "") + (o.toggle ? " tog" : "");
  card.dataset.mode = o.mode;
  card.style.setProperty("--acc", o.acc);
  const ban = document.createElement("div");
  ban.className = "bsban";
  if (o.toggle) { ban.classList.add("boostban"); ban.innerHTML = BOOST_MARK; }
  const art = new Image();
  art.className = "bsart"; art.alt = ""; art.draggable = false;
  art.onload = () => ban.classList.add("art");
  art.onerror = () => art.remove();
  art.src = `assets/bonus/banner_${o.key}.webp`;
  ban.append(art);
  if (o.icon) {
    const ic = new Image();
    ic.className = "bsico"; ic.alt = ""; ic.draggable = false; ic.src = o.icon;
    ban.append(ic);
  }
  card.append(ban);
  card.insertAdjacentHTML("beforeend",
    `<div class="bsbody"><div class="bspips">${Array.from({ length: 5 }, (_, i) => `<i class="${i < o.heat ? "on" : ""}"></i>`).join("")}</div>` +
    `<div class="bsttl"></div><div class="bsdesc"></div><div class="bsmax"></div></div>` +
    `<div class="bsfoot"><div class="bsprice"></div><div class="bsx"></div><button type="button" class="bsget"></button></div>`);
  card.querySelector(".bsttl").textContent = T(o.title);
  card.querySelector(".bsdesc").textContent = T(o.desc);
  card.querySelector(".bsget").addEventListener("click", () => bshopGet(o));
  return card;
}
function bshopGet(o) {
  if (o.toggle) {   // Bonus Boost: on or off for the spins that follow
    state.boost = !state.boost;
    SFX.tick();
    refreshBet();
    return;
  }
  if (bshopArmed !== o.mode) {   // the first press asks; the second, within a few seconds, buys
    bshopArmed = o.mode;
    clearTimeout(bshopArmT);
    bshopArmT = setTimeout(() => { bshopArmed = null; paintBonus(); }, 4000);
    SFX.tick();
    paintBonus();
    return;
  }
  bshopArmed = null; clearTimeout(bshopArmT);
  closeBonus();
  SFX.unlock();
  spin(o.mode);
}
function paintBonus() {
  const wrap = $("bonusWrap");
  if (!wrap || wrap.hidden) return;
  const row = $("bshopRow");
  const live = BUYS.filter(o => modeCost[o.mode] > 0);
  if (row.dataset.modes !== live.map(o => o.mode).join()) {
    row.replaceChildren(...live.map(bshopCard));
    row.dataset.modes = live.map(o => o.mode).join();
  }
  for (const card of row.children) {
    const o = BUYS.find(x => x.mode === card.dataset.mode), cost = modeCost[o.mode], price = Math.round(cost * bet());
    const over = price > RGS.state.balance, btn = card.querySelector(".bsget"), armed = bshopArmed === o.mode;
    card.querySelector(".bsprice").textContent = fmt(price);
    card.querySelector(".bsx").textContent = o.toggle ? T(`${fmtMult(cost)}× per spin`) : T(`${fmtMult(cost)}× bet`);
    card.querySelector(".bsmax").textContent = T("Max win") + " x" + MAX_WIN.toLocaleString("en-US");
    if (o.toggle) {
      card.classList.toggle("on", !!state.boost);
      btn.classList.toggle("lit", !!state.boost);
      btn.setAttribute("aria-pressed", String(!!state.boost));
      btn.textContent = state.boost ? T("On") : T("Activate");
      btn.disabled = false;
      continue;
    }
    card.classList.toggle("on", armed);
    btn.classList.toggle("armed", armed && !over);
    btn.textContent = over ? T("Low balance") : armed ? T("Confirm") : T("Get");
    btn.disabled = over;
  }
  $("bonusTitle").textContent = T("Bonus Buy");
  $("bshopPlayLbl").textContent = T("Play");
  $("bshopBal").textContent = fmt(RGS.state.balance);
  $("bonusBetVal").textContent = fmt(bet());
  $("bonusBetUp").disabled = state.betIdx >= state.bets.length - 1;
  $("bonusBetDown").disabled = state.betIdx <= 0;
}
function closeBonus() {
  $("bonusWrap").hidden = true;
  $("bonusBtn").classList.remove("open");
}
function openBonus() {
  if (state.replay || !RGS.state.authenticated || state.playing) return;
  if (!$("bonusWrap").hidden) { closeBonus(); return; }
  $("autoPop").hidden = true; $("volPop").hidden = true;
  $("bonusWrap").hidden = false;
  $("bonusBtn").classList.add("open");
  bshopArmed = null;
  paintBonus();
  fitBonus();
}
// a short window: the whole shop shrinks to fit rather than running off the screen (orleans' fitBonus)
function fitBonus() {
  const pop = document.querySelector("#bonusWrap .bonuspop"), panel = document.querySelector("#bonusWrap .bshop");
  if (!pop || !panel || $("bonusWrap").hidden) return;
  const k = Math.min((innerHeight - 28) / (panel.offsetHeight + 12), (innerWidth - 28) / (panel.offsetWidth + 12));
  pop.style.scale = k < 1 ? k.toFixed(3) : "";
}
addEventListener("resize", fitBonus);
$("bonusBtn").onclick = () => { SFX.unlock(); openBonus(); };
$("bonusClose").onclick = () => closeBonus();
$("bonusBetUp").onclick = () => $("betUp").onclick();
$("bonusBetDown").onclick = () => $("betDown").onclick();
$("bonusWrap").addEventListener("click", e => { if (e.target === $("bonusWrap")) closeBonus(); });
document.addEventListener("keydown", e => { if (e.key === "Escape" && !$("bonusWrap").hidden) closeBonus(); });

/* ---------------------------------------------------------------- sound: synthesised, no files */
const SFX = (() => {
  let ac = null, out = null, sv = .8, noiseBuf = null;
  const ensure = () => {
    if (ac) return ac;
    try {
      ac = new (window.AudioContext || window.webkitAudioContext)();
      out = ac.createGain(); out.gain.value = sv; out.connect(ac.destination);
      noiseBuf = ac.createBuffer(1, ac.sampleRate, ac.sampleRate);
      const d = noiseBuf.getChannelData(0); for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    } catch (e) { ac = null; }
    return ac;
  };
  const noise = (dur, f0, f1, q, gain, type = "bandpass", t = 0) => {
    if (!ensure() || sv <= 0) return;
    const now = ac.currentTime + t, s = ac.createBufferSource(), f = ac.createBiquadFilter(), gn = ac.createGain();
    s.buffer = noiseBuf; f.type = type; f.Q.value = q;
    f.frequency.setValueAtTime(f0, now); f.frequency.exponentialRampToValueAtTime(Math.max(30, f1), now + dur);
    gn.gain.setValueAtTime(0.0001, now); gn.gain.exponentialRampToValueAtTime(gain, now + Math.min(.02, dur / 4)); gn.gain.exponentialRampToValueAtTime(0.0001, now + dur);
    s.connect(f); f.connect(gn); gn.connect(out); s.start(now, Math.random() * .5); s.stop(now + dur + .05);
  };
  const tone = (freq, dur, gain = .2, type = "sine", t = 0, slide = 1) => {
    if (!ensure() || sv <= 0) return;
    const now = ac.currentTime + t, o = ac.createOscillator(), gn = ac.createGain();
    o.type = type; o.frequency.setValueAtTime(freq, now); o.frequency.exponentialRampToValueAtTime(freq * slide, now + dur);
    gn.gain.setValueAtTime(0.0001, now); gn.gain.exponentialRampToValueAtTime(gain, now + .01); gn.gain.exponentialRampToValueAtTime(0.0001, now + dur);
    o.connect(gn); gn.connect(out); o.start(now); o.stop(now + dur + .05);
  };
  // The generated sets (tools/sfx/jd.py -> assets/sfx/sfx.json): each name a few takes; a play picks a take
  // other than the last one and nudges its pitch, so a burst of slices never sounds like one sample.
  const bank = {}, lastTake = {};
  let manifest = null;
  async function loadBank(only = null) {
    if (!ensure()) return;
    if (!manifest) { try { manifest = await (await fetch("assets/sfx/sfx.json")).json(); } catch (e) { return; } }
    await Promise.all(Object.entries(manifest).filter(([name]) => (only ? only.includes(name) : true) && !bank[name]).map(async ([name, m]) => {
      bank[name] = { bufs: [], vol: 0 };          // (claimed: a second load never decodes it twice)
      const bufs = await Promise.all(m.files.map(async f => {
        try { return await ac.decodeAudioData(await (await fetch("assets/" + f)).arrayBuffer()); } catch (e) { return null; }
      }));
      bank[name] = { bufs: bufs.filter(Boolean), vol: m.vol == null ? 1 : m.vol };
    }));
  }
  function sample(name, { rate = 1, jitter = .04, gain = 1, take = null } = {}) {
    const set = bank[name];
    if (!ac || !set || !set.bufs.length || sv <= 0) return false;
    let i = take;
    if (i == null) {
      i = Math.floor(Math.random() * set.bufs.length);
      if (set.bufs.length > 1 && i === lastTake[name]) i = (i + 1) % set.bufs.length;
    }
    i = Math.min(i, set.bufs.length - 1);
    lastTake[name] = i;
    const src = ac.createBufferSource(), gn = ac.createGain();
    src.buffer = set.bufs[i];
    src.playbackRate.value = rate * (1 + (Math.random() * 2 - 1) * jitter) * (state.skip ? 1.12 : 1);
    gn.gain.value = set.vol * gain;
    src.connect(gn); gn.connect(out);
    src.start();
    return true;
  }
  const SLICE = id => (id && id.startsWith("PW") ? "slice_PW" : "slice_" + id);
  let unlocked = false;
  let comboStep = 0;
  // Music (tools/sfx/gen_music.py + pack_music.py, Lyria 3; owner, 2026-11-18: "relaxing, ninja like", and the
  // music should change with the bonus icons, the lines, every kind of win and the bonus). Two calm loops - base and
  // frenzy - cut to whole bars, crossfaded at the bonus. Over them a music director plays in-key stingers on the
  // track's own beat grid (assets/music/music.json: key, mode, BPM): a koto (Karplus-Strong, tuned with an allpass)
  // and a temple bell (inharmonic partials), synthesised at the device's rate so they are crisp, through a soft
  // hall reverb; a low tension pad under the star fruit; swells for big wins; a tape-stop for the bomb.
  // Everything follows the HUD's music slider; a cinematic can duck the loop (gently: quieter, a little darker).
  const music = (() => {
    let mv = .6, bus = null, lp = null, duckG = null, swellG = null, cur = null, want = null, loading = null, meta = {};
    let instIn = null, verbIn = null, pad = null;
    const bufs = {}, kotoCache = {}, bellCache = {};
    const PENTA = { minor: [0, 3, 5, 7, 10], major: [0, 2, 4, 7, 9] };
    const graph = () => {
      if (bus || !ensure()) return !!bus;
      bus = ac.createGain(); bus.gain.value = mv; bus.connect(ac.destination);
      swellG = ac.createGain(); swellG.gain.value = 1; swellG.connect(bus);
      // the loop: low-pass (open) -> duck -> swell -> bus
      lp = ac.createBiquadFilter(); lp.type = "lowpass"; lp.frequency.value = 20000; lp.Q.value = .5;
      duckG = ac.createGain(); duckG.gain.value = 1;
      lp.connect(duckG); duckG.connect(swellG);
      // the stingers: a little body EQ, straight to the bus (never ducked), and a send into the hall
      const body = ac.createBiquadFilter(); body.type = "peaking"; body.frequency.value = 320; body.gain.value = 2.5; body.Q.value = .9;
      const air = ac.createBiquadFilter(); air.type = "highshelf"; air.frequency.value = 5000; air.gain.value = 2;
      instIn = ac.createGain(); instIn.gain.value = .55;
      instIn.connect(body); body.connect(air); air.connect(bus);
      const verb = ac.createConvolver(); verb.buffer = hall(2.6);
      verbIn = ac.createGain(); verbIn.gain.value = .7;
      verbIn.connect(verb); verb.connect(bus);
      return true;
    };
    function hall(dur) {                          // a soft, dark hall: decaying noise that darkens as it fades
      const sr = ac.sampleRate, n = Math.floor(sr * dur), b = ac.createBuffer(2, n, sr);
      for (let ch = 0; ch < 2; ch++) {
        const d = b.getChannelData(ch); let y = 0;
        for (let i = 0; i < n; i++) {
          const k = i / n, a = .62 - .54 * k;
          y += a * ((Math.random() * 2 - 1) - y);
          d[i] = y * Math.exp(-4.2 * k) * (i < sr * .012 ? i / (sr * .012) : 1);
        }
      }
      return b;
    }
    // a koto note: Karplus-Strong, plucked a seventh of the way along, fractional delay by an allpass so it is in tune
    function koto(freq) {
      const key = Math.round(freq * 10);
      if (kotoCache[key]) return kotoCache[key];
      const sr = ac.sampleRate, dur = Math.min(2.6, .9 + 220 / freq), len = Math.floor(sr * dur);
      const buf = ac.createBuffer(1, len, sr), out = buf.getChannelData(0);
      const Ld = sr / freq - .5, N = Math.max(2, Math.floor(Ld)), fr = Ld - N, C = (1 - fr) / (1 + fr);
      const line = new Float32Array(N), pos = Math.max(1, Math.round(N / 7));
      let l = 0;
      for (let i = 0; i < N; i++) { l += .6 * ((Math.random() * 2 - 1) - l); line[i] = l; }
      for (let i = N - 1; i >= pos; i--) line[i] -= .85 * line[i - pos];
      const g = Math.pow(.001, 1 / (dur * freq));
      let idx = 0, last = 0, apX = 0, apY = 0, pk = 0;
      for (let n = 0; n < len; n++) {
        const c = line[idx];
        out[n] = c; pk = Math.max(pk, Math.abs(c));
        const avg = .5 * (c + last) * g; last = c;
        const ap = C * avg + apX - C * apY; apX = avg; apY = ap;
        line[idx] = ap; if (++idx === N) idx = 0;
      }
      const fo = Math.floor(sr * .08);
      for (let n = 0; n < len; n++) out[n] = out[n] / (pk || 1) * .9 * (n > len - fo ? (len - n) / fo : 1);
      return (kotoCache[key] = buf);
    }
    // a temple bell (rin): a few inharmonic partials, each with its own decay; the fundamental beats slowly
    function bell(freq) {
      const key = Math.round(freq * 10);
      if (bellCache[key]) return bellCache[key];
      const sr = ac.sampleRate, dur = 2.4, len = Math.floor(sr * dur), buf = ac.createBuffer(1, len, sr), d = buf.getChannelData(0);
      const parts = [[1, .55, 2.3], [1.0025, .35, 2.0], [2.76, .3, 1.3], [5.40, .14, .8], [8.93, .07, .45]];
      for (const [r, a, t60] of parts) {
        if (freq * r > sr * .45) continue;
        const w = 2 * Math.PI * freq * r / sr, cw = Math.cos(w), sw = Math.sin(w), dk = Math.exp(-Math.log(1000) / (t60 * sr));
        let re = Math.cos(Math.random() * 6.28), im = Math.sqrt(1 - re * re), amp = a;
        for (let n = 0; n < len; n++) { const nr = re * cw - im * sw; im = re * sw + im * cw; re = nr; d[n] += amp * im; amp *= dk; }
      }
      const at = Math.floor(sr * .002);
      let pk = 0; for (let n = 0; n < len; n++) { if (n < at) d[n] *= n / at; pk = Math.max(pk, Math.abs(d[n])); }
      for (let n = 0; n < len; n++) d[n] = d[n] / pk * .85;
      return (bellCache[key] = buf);
    }
    const key = () => meta[cur ? cur.name : want] || meta.base || { tonic: 2, mode: "minor", bpm: 80 };
    // scale degree -> Hz: the pentatonic of the music's key (relative major / minor share its notes), from tonic 4
    function hz(deg, oct = 0, m = key()) {
      const sc = PENTA[m.mode] || PENTA.minor, o = Math.floor(deg / 5), d = ((deg % 5) + 5) % 5;
      return 440 * Math.pow(2, (60 + m.tonic + sc[d] + 12 * (o + oct) - 69) / 12);
    }
    // the next 1/div of a beat on the loop's grid (so a stinger lands in time with the music), or now
    function onGrid(div = 4) {
      const t = ac.currentTime + .015, m = key();
      if (!cur || !m.quantize || mv < .02 || state.skip) return t;
      const q = 60 / m.bpm / div;
      return cur.t0 + Math.ceil((t - cur.t0) / q) * q;
    }
    function note(buf, t, gain = .5, pan = 0, send = .3) {
      const s = ac.createBufferSource(), g = ac.createGain();
      s.buffer = buf; g.gain.value = gain;
      s.connect(g);
      if (ac.createStereoPanner) { const p = ac.createStereoPanner(); p.pan.value = pan; g.connect(p); p.connect(instIn); }
      else g.connect(instIn);
      if (send > 0) { const sg = ac.createGain(); sg.gain.value = send; g.connect(sg); sg.connect(verbIn); }
      s.start(t);
    }
    const run = (degs, t, step, gain = .42, oct = 0, panW = .35) =>
      degs.forEach((d, i) => note(koto(hz(d, oct)), t + i * step, gain * (1 - i * .04), (i / Math.max(1, degs.length - 1) - .5) * panW * 2));
    function swell(db, up = .4, hold = .6, down = 2.5) {
      const t = ac.currentTime, p = swellG.gain;
      p.cancelScheduledValues(t); p.setValueAtTime(p.value, t);
      p.linearRampToValueAtTime(Math.pow(10, db / 20), t + up); p.setValueAtTime(Math.pow(10, db / 20), t + up + hold);
      p.linearRampToValueAtTime(1, t + up + hold + down);
    }
    function padOn() {                            // a low, quiet drone on the tonic and fifth, breathing slowly
      if (pad) return;
      const t = ac.currentTime, out = ac.createGain(), f = ac.createBiquadFilter();
      f.type = "lowpass"; f.frequency.value = 900; f.Q.value = .7;
      out.gain.setValueAtTime(0, t); out.gain.linearRampToValueAtTime(.16, t + 1.2);
      f.connect(out); out.connect(bus); const sg = ac.createGain(); sg.gain.value = .5; out.connect(sg); sg.connect(verbIn);
      const oscs = [];
      for (const [deg, det] of [[0, -4], [0, 5], [3, -3], [3, 4], [0, 0]]) {
        const o = ac.createOscillator(); o.type = deg === 0 && det === 0 ? "sine" : "triangle";
        o.frequency.value = hz(deg, deg === 0 && det === 0 ? -2 : -1); o.detune.value = det;
        const g = ac.createGain(); g.gain.value = deg === 0 && det === 0 ? .5 : .22;
        o.connect(g); g.connect(f); o.start(t); oscs.push(o);
      }
      const lfo = ac.createOscillator(), lg = ac.createGain(); lfo.frequency.value = .18; lg.gain.value = 260;
      lfo.connect(lg); lg.connect(f.frequency); lfo.start(t); oscs.push(lfo);
      pad = { out, oscs };
    }
    function padOff(fade = 1.6) {
      if (!pad) return;
      const t = ac.currentTime, p = pad; pad = null;
      p.out.gain.cancelScheduledValues(t); p.out.gain.setValueAtTime(p.out.gain.value, t); p.out.gain.linearRampToValueAtTime(0, t + fade);
      p.oscs.forEach(o => o.stop(t + fade + .1));
    }
    // every koto and bell note a cue can ask for, in a track's key, synthesised ahead a few at a time while the
    // page is idle - so a cue never stalls a frame (the first test spent 210 ms making notes on the spot)
    const warmed = {};
    function prewarm(role) {
      const m = meta[role];
      if (!m || warmed[role]) return;
      warmed[role] = true;
      const jobs = [];
      for (let d = -5; d <= 16; d++) jobs.push(() => koto(hz(d, 0, m)));
      for (const d of [-5, 0, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12, 14, 16]) jobs.push(() => bell(hz(d, 0, m)));
      const idle = window.requestIdleCallback || (f => setTimeout(f, 30));
      const step = () => { for (let i = 0; i < 3 && jobs.length; i++) jobs.shift()(); if (jobs.length) idle(step); };
      idle(step);
    }
    const load = () => loading || (loading = (async () => {
      try { meta = await (await fetch("assets/music/music.json")).json(); } catch (e) { meta = {}; }
      await Promise.all(["base", "frenzy"].map(async n => {
        try { bufs[n] = await ac.decodeAudioData(await (await fetch(`assets/music/${n}.ogg`)).arrayBuffer()); } catch (e) { /* none */ }
      }));
      prewarm("base");
    })());
    async function play(name, fade = 2.2) {
      want = name;
      if (!graph()) return;
      await load();
      if (want !== name || !bufs[name] || (cur && cur.name === name)) return;
      const t = ac.currentTime + .05;
      if (cur) { const o = cur; o.g.gain.cancelScheduledValues(t); o.g.gain.setValueAtTime(o.g.gain.value, t); o.g.gain.linearRampToValueAtTime(0, t + fade); o.src.stop(t + fade + .1); }
      const src = ac.createBufferSource(), g = ac.createGain();
      src.buffer = bufs[name]; src.loop = true;
      g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(1, t + fade);
      src.connect(g); g.connect(lp); src.start(t);
      cur = { name, src, g, t0: t };
      prewarm(name);
    }
    function duck(level, ms = 600) {             // 1 = open; lower = quieter and a little darker (never muffled)
      if (!bus) return;
      const t = ac.currentTime, d = Math.max(.03, ms / 1000 / speed());
      for (const [p, v] of [[duckG.gain, Math.max(0, level)], [lp.frequency, level >= .99 ? 20000 : 2200 + 15000 * level * level]]) {
        p.cancelScheduledValues(t); p.setValueAtTime(p.value, t); p.linearRampToValueAtTime(v, t + d);
      }
    }
    // the director: what each moment does to the music
    function cue(type, a = {}) {
      if (!graph() || mv <= 0) return;
      const m = key(), beat = 60 / (m.bpm || 80);
      switch (type) {
        case "star": {                           // each bonus icon rings a bell, a step higher than the last
          const i = a.i || 0, t = onGrid(2);
          note(bell(hz([0, 2, 3, 4, 5, 7][Math.min(i, 5)], 1)), t, .5, (i % 2 ? .25 : -.25), .55);
          note(koto(hz([0, 2, 3, 4, 5, 7][Math.min(i, 5)])), t, .3, 0, .3);
          break;
        }
        case "tension": a.on ? padOn() : padOff(); break;
        case "line": {                           // a koto run as long as the line, each line starting higher
          const i = a.i || 0, n = Math.max(3, Math.min(5, a.n || 3));
          run(Array.from({ length: n }, (_, k) => i + k), onGrid(4), beat / 4, .4);
          break;
        }
        case "combo": {                          // a quick glissando up and a bell on top
          const c = a.c || 2, t = onGrid(4), degs = Array.from({ length: 5 + c * 2 }, (_, k) => 2 + k);
          run(degs, t, beat / 8, .34, 0, .5);
          note(bell(hz(degs[degs.length - 1], 0)), t + degs.length * beat / 8, .45, 0, .6);
          swell(1.5, .3, .4, 1.5);
          break;
        }
        case "win": {                            // any win settles on the tonic and fifth, an octave apart
          const t = onGrid(2), big = (a.lines || 1) >= 3;
          note(koto(hz(0, -1)), t, .38, -.2, .35); note(koto(hz(3, -1)), t + .03, .3, .2, .35);
          note(koto(hz(5, -1)), t + .06, .26, 0, .35);
          if (big) note(bell(hz(5, 0)), t + beat / 2, .35, 0, .6);
          break;
        }
        case "side": note(koto(hz(5 + Math.floor(Math.random() * 5))), onGrid(4), .2, Math.random() - .5, .4); break;
        case "mult": { const t = onGrid(4); note(bell(hz(5, 1)), t, .35, -.2, .5); note(bell(hz(7, 1)), t + beat / 4, .35, .2, .5); break; }
        case "frost": { const t = onGrid(4); [7, 9, 11].forEach((d, k) => note(bell(hz(d, 1)), t + k * beat / 6, .18, (k - 1) * .4, .7)); break; }
        case "bigwin": {                         // the loop swells, a two-octave sweep, a bell over it all
          const t = onGrid(2);
          swell(3, .5, 1.2, 3);
          run(Array.from({ length: 11 }, (_, k) => k), t, beat / 8, .36, -1, .6);
          note(bell(hz(10, 0)), t + 11 * beat / 8, .55, 0, .7);
          break;
        }
        case "bonusStart": {                     // the base fades under a slow rising arpeggio and a deep bell
          prewarm("frenzy");
          const t = ac.currentTime + .05;
          note(bell(hz(0, -1)), t, .6, 0, .8);
          run([0, 2, 3, 5, 7, 8, 10], t + .25, beat / 3, .36, 0, .6);
          padOff(.8);
          break;
        }
        case "bonusEnd": {                       // back home: a falling phrase that comes to rest
          const t = onGrid(1);
          run([10, 8, 7, 5, 3, 2, 0], t, beat / 4, .36, 0, .5);
          note(bell(hz(0, 0)), t + 7 * beat / 4, .5, 0, .8);
          break;
        }
        case "bomb": {                           // the music stumbles like a tape stopping, then comes back
          if (!cur) break;
          const t = ac.currentTime, r = cur.src.playbackRate;
          r.cancelScheduledValues(t); r.setValueAtTime(1, t); r.linearRampToValueAtTime(.5, t + .45); r.linearRampToValueAtTime(1, t + 2.2);
          cur.t0 += .45 * .25 + 1.75 * .25;      // the time it lost while slowed: keeps the beat grid true
          duck(.25, 120); setTimeout(() => duck(1, 1600), 900);
          break;
        }
      }
    }
    return { play, duck, cue, setVolume(v) { mv = v; if (bus) bus.gain.value = v; },
             debug: () => ({ mv, graph: !!bus, playing: cur && cur.name, want, ctx: ac && ac.state, kotos: Object.keys(kotoCache).length, bells: Object.keys(bellCache).length, pad: !!pad }) };
  })();
  return {
    unlock() { ensure(); if (ac && ac.state === "suspended") ac.resume(); if (!unlocked) { unlocked = true; loadBank(); } music.play(state.frenzy ? "frenzy" : "base"); },
    // the SMUKIEZ ident's sounds (from zeqpz/orleans): decoded first, and only played into audio the page was already
    // allowed to start (a launched iframe with autoplay) - never queued into a suspended context to burst out later
    warmIdent() {
      try { if (navigator.getAutoplayPolicy && navigator.getAutoplayPolicy("audiocontext") === "disallowed") return Promise.resolve(); } catch (e) { /* */ }
      if (!ensure()) return Promise.resolve();
      return loadBank(["introWhoosh", "introHit", "introShimmer", "introOut", "landBrick"]);
    },
    ident(name, rate = 1) { if (ac && ac.state === "running") sample(name, { rate, jitter: 0 }); },
    loadBank,
    music,
    loaded: () => Object.fromEntries(Object.entries(bank).map(([k, v]) => [k, v.bufs.length])),
    setVolume(s, m) { sv = s; if (out) out.gain.value = s; if (m != null) music.setVolume(m); },
    // the cinematic set (tools/sfx/gen_sfx2.py), each with a synth stand-in until it loads
    slowIn() { sample("slowmo_in", { jitter: .02 }) || tone(220, .8, .14, "sine", 0, .35); },
    slowOut() { sample("slowmo_out", { jitter: .02 }) || tone(110, .5, .1, "sine", 0, 3); },
    heartbeat(i = 0) { sample("heartbeat", { rate: 1 + i * .04, jitter: .01, gain: 1 + i * .08 }) || (tone(55, .18, .5, "sine", 0, .7), tone(50, .16, .4, "sine", .2, .7)); },
    starPing(i = 0) { music.cue("star", { i }); sample("star_ping", { gain: .35, jitter: .02 }); },   // the bell is in key; the sparkle on top
    riser() { sample("riser", { jitter: 0 }) || noise(1.8, 300, 6000, 1.2, .25); },
    impact() { sample("impact", { jitter: .02 }) || (noise(1, 700, 40, .6, .9, "lowpass"), tone(55, .9, .6, "sine", 0, .5)); },
    taiko() { sample("taiko", { jitter: .03 }) || tone(80, .6, .6, "sine", 0, .6); },
    gong() { sample("gong", { jitter: .02 }) || [196, 293, 415].forEach(f => tone(f, 2.5, .07, "triangle")); },
    camWhoosh() { sample("cam_whoosh", { jitter: .06 }); },
    swordDraw() { sample("sword_draw", { jitter: .05 }); },
    // synthesised: crisp at the device's rate (the generated takes were dull thuds)
    clack() {      // hyoshigi: two hard wooden modes and a click
      const j = 1 + (Math.random() - .5) * .06;
      tone(1180 * j, .07, .22, "sine", 0, .97); tone(2630 * j, .045, .12, "sine", 0, .97); noise(.025, 5200, 3000, 1.4, .28); },
    uiClick() {    // a small, soft wooden tick
      const j = 1 + (Math.random() - .5) * .08;
      tone(1650 * j, .028, .07, "sine", 0, .9); noise(.018, 4200, 2600, 1.8, .1); },
    swoosh() { sample("swoosh", { jitter: .08 }) || noise(.16, 3800, 900, 1.2, .35); },
    throw() { sample("drop", { gain: .8 }) || noise(.35, 300, 900, .8, .12, "lowpass"); },
    squish(id) {
      if (sample(SLICE(id), { jitter: .05 })) return; const lo = id && id.startsWith("H") ? 1 : 1.3; noise(.18, 1600 * lo, 300, 1.5, .5); tone(180 * lo, .12, .12, "sine", 0, .5); },
    coin(n) {      // the coins: a crisp tick (the line's tune is the music director's koto run)
      if (sample("coin_tick", { rate: 1 + .05 * Math.max(0, n - 3), gain: 1.1 })) return; tone(2400, .05, .06, "square"); },
    combo(c, lines = 3) { music.cue("combo", { c, lines }); },
    chime(n) { for (let i = 0; i < n; i++) setTimeout(() => music.cue("star", { i }), i * 140); },
    power() {
      music.cue("mult");
      if (sample("multiplier")) return; tone(440, .35, .16, "sawtooth", 0, 3); tone(880, .3, .08, "sine", .05, 2); },
    freeze() {
      music.cue("frost");
      if (sample("frost")) return; noise(.6, 6000, 9000, 4, .2, "highpass"); [2637, 3136, 3520].forEach((f, i) => tone(f, .5, .05, "sine", i * .07)); },
    fuse() {
      if (sample("fuse", { jitter: 0 })) return; noise(.6, 5000, 7000, 6, .12, "bandpass"); },
    boom() {
      if (sample("boom", { jitter: .02 })) return; noise(1.2, 900, 40, .6, 1.0, "lowpass"); tone(70, .8, .6, "sine", 0, .4); },
    fanfare() {
      if (sample("frenzy_start", { jitter: 0 })) return; [392, 523, 659, 784, 1047].forEach((f, i) => { tone(f, .3, .14, "square", i * .1); tone(f / 2, .3, .1, "triangle", i * .1); }); },
    coinShower() {
      if (sample("big_win", { jitter: 0 })) return; for (let i = 0; i < 14; i++) tone(1500 + Math.random() * 1500, .14, .06, "triangle", i * .06); },
    hit(i) {
      if (sample("slice_JM", { rate: 1 + Math.min(.35, i * .012), jitter: .03 })) return; noise(.12, 2400 + i * 60, 600, 2, .35); tone(300 + i * 25, .08, .08, "square"); },
    pop() { sample("bump", { rate: 1.6 + Math.random() * .4, gain: .35, jitter: .1 }); },
    tick() {
      if (sample("coin_tick")) return; tone(1200, .04, .06, "square"); },
    bump() {
      if (sample("bump", { jitter: .1, gain: .9 })) return; noise(.07, 500, 200, 1, .18, "lowpass"); },
  };
})();

/* ---------------------------------------------------------------- the Bonus button's FX */
// Sparkles twinkling about the BONUS lettering, a few at a time round its edge (the lightning it had is gone:
// owner, 2026-11-17) - drawn on a small canvas over the button, on while a spin plays too.
(function bonusFx() {
  const btn = $("bonusBtn"), cv = btn && btn.querySelector(".bfx");
  if (!cv || REDUCED) return;
  const cx = cv.getContext("2d");
  const bolts = [], stars = [];
  let next = .4, lastT = performance.now();
  const jag = (x0, y0, x1, y1, rough, depth) => {   // midpoint displacement
    if (depth === 0) return [[x0, y0], [x1, y1]];
    const mx = (x0 + x1) / 2 + (Math.random() - .5) * rough, my = (y0 + y1) / 2 + (Math.random() - .5) * rough;
    return [...jag(x0, y0, mx, my, rough / 2, depth - 1).slice(0, -1), ...jag(mx, my, x1, y1, rough / 2, depth - 1)];
  };
  const tick = now => {
    const dt = Math.min(.05, (now - lastT) / 1000); lastT = now;
    const dpr = Math.min(2, devicePixelRatio || 1), w = cv.clientWidth, h = cv.clientHeight;
    if (!w) { cx.clearRect(0, 0, cv.width, cv.height); requestAnimationFrame(tick); return; }   // (it sparkles on while a spin plays)
    if (cv.width !== Math.round(w * dpr)) { cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); }
    cx.setTransform(dpr, 0, 0, dpr, 0, 0);
    cx.clearRect(0, 0, w, h);
    next -= dt;
    if (next <= 0) {   // a little cluster of twinkles somewhere on the lettering's edge (no lightning: owner, 2026-11-17)
      next = .35 + Math.random() * 1.1;
      const a = Math.random() * Math.PI * 2, rx = w * .27, ry = h * .19;
      const x0 = w / 2 + Math.cos(a) * rx, y0 = h / 2 + Math.sin(a) * ry;
      for (let i = 0; i < 3; i++) stars.push({ x: x0 + (Math.random() - .5) * 40, y: y0 + (Math.random() - .5) * 28, age: 0, dur: .5 + Math.random() * .4, r: 5 + Math.random() * 6 });
    }
    if (Math.random() < dt * 3) stars.push({ x: w * (.2 + Math.random() * .6), y: h * (.3 + Math.random() * .4), age: 0, dur: .6 + Math.random() * .6, r: 4 + Math.random() * 6 });
    cx.lineCap = "round"; cx.lineJoin = "round";
    for (const bo of bolts) {
      bo.age += dt;
      const k = bo.age / bo.dur, on = k < .25 || (k > .45 && k < .7);   // it flickers: on, off, on, gone
      if (!on) continue;
      for (const [col, wd, blur] of [["rgba(255,200,60,.6)", 14, 26], ["rgba(255,236,150,.9)", 7, 12], ["#ffffff", 3.4, 6]]) {
        cx.strokeStyle = col; cx.lineWidth = wd; cx.shadowColor = "#ffcf3a"; cx.shadowBlur = blur;
        for (const path of [bo.pts, bo.fork]) {
          if (!path) continue;
          cx.beginPath(); cx.moveTo(...path[0]); for (const q of path) cx.lineTo(...q); cx.stroke();
        }
      }
    }
    cx.shadowBlur = 0;
    for (const st of stars) {   // four-point twinkles
      st.age += dt;
      const k = st.age / st.dur, a = Math.sin(Math.PI * Math.min(1, k)), r = st.r * (.6 + a * .8);
      cx.globalAlpha = a; cx.fillStyle = "#fff6c8";
      cx.beginPath();
      for (let i = 0; i < 8; i++) { const an = i * Math.PI / 4, rr = i % 2 ? r * .22 : r * 1.6; cx.lineTo(st.x + Math.cos(an) * rr, st.y + Math.sin(an) * rr); }
      cx.closePath(); cx.fill();
    }
    cx.globalAlpha = 1;
    for (let i = bolts.length - 1; i >= 0; i--) if (bolts[i].age > bolts[i].dur) bolts.splice(i, 1);
    for (let i = stars.length - 1; i >= 0; i--) if (stars[i].age > stars[i].dur) stars.splice(i, 1);
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
})();

/* ---------------------------------------------------------------- the opening */
// The studio ident (owner, 2026-11-18: as zeqpz/orleans): the black-and-white SMUKIEZ wordmark (see .intro). It starts
// once its letters are decoded and its sounds are ready (the sounds 400 ms at most), plays its beats with sound where
// the page may already play audio and silently where it may not, then holds while the loading bar fills. Loading
// (art + the RGS) is what ends it - never sooner than the ident has played. Returns { progress(0..1), finish() }.
const INTRO_SIZE = [2736, 1160];
const INTRO_PIECES = { S: [322, 236, 275, 372], M: [615, 246, 388, 362], U: [1021, 240, 325, 368], K: [1364, 236, 283, 372], i: [1665, 245, 119, 363],
                       E: [1802, 245, 292, 363], Z: [2112, 244, 301, 364], swash: [532, 656, 1877, 184], tm: [2417, 242, 125, 73], glow: [-110, -110, 2956, 1380] };
const INTRO_DROP = ["S", "M", "U", "K", "i", "E", "Z"];
let introDone = Promise.resolve();
function runIntro(loaded) {
  const wrap = $("intro"), fill = $("introFill"), word = $("introWord"), pieceEl = {};
  let done = false, settle;
  introDone = new Promise(r => { settle = r; });
  const timers = [], after = (ms, fn) => timers.push(setTimeout(fn, ms)), wait = ms => new Promise(r => setTimeout(r, ms));
  const IDENT = 3300;                                     // ms the ident needs before it may hand over
  const place = (el, [x, y, w, h]) => Object.assign(el.style, { left: (x / INTRO_SIZE[0] * 100) + "%", top: (y / INTRO_SIZE[1] * 100) + "%",
                                                                width: (w / INTRO_SIZE[0] * 100) + "%", height: (h / INTRO_SIZE[1] * 100) + "%" });
  place(word.querySelector(".iwglow"), INTRO_PIECES.glow);
  for (const [k, box] of Object.entries(INTRO_PIECES)) {
    if (k === "glow") continue;
    const im = new Image();
    im.className = "iwl"; im.alt = ""; im.draggable = false; im.src = `assets/intro_letters/${k}.webp`;
    place(im, box); word.appendChild(im); pieceEl[k] = im;
  }
  let beganAt = performance.now();
  const finish = () => {
    if (done) return;
    done = true;
    timers.forEach(clearTimeout);
    if (REDUCED) { wrap.classList.add("gone"); setTimeout(() => wrap.remove(), 700); settle(); return; }
    SFX.ident("introOut");
    wrap.classList.add("out");                            // the word lifts away
    setTimeout(() => { wrap.classList.add("gone"); settle(); }, 520);   // and the screen fades through black
    setTimeout(() => wrap.remove(), 1300);
  };
  if (REDUCED) {
    wrap.classList.add("static");
    loaded.then(() => after(600, finish));
  } else {
    const grain = wrap.querySelector(".intrograin");      // film grain: a tile of noise, shuffled by the stylesheet
    const c = document.createElement("canvas"); c.width = c.height = 160;
    const g2 = c.getContext("2d"), px = g2.createImageData(160, 160);
    for (let i = 0; i < px.data.length; i += 4) { const v = Math.random() * 255; px.data[i] = px.data[i + 1] = px.data[i + 2] = v; px.data[i + 3] = 255; }
    g2.putImageData(px, 0, 0);
    grain.style.backgroundImage = `url(${c.toDataURL()})`;
    const mark = Promise.all([...wrap.querySelectorAll(".introword img")].map(i => i.decode ? i.decode().catch(() => {}) : Promise.resolve()));
    const ready = Promise.all([Promise.race([mark, wait(2500)]), Promise.race([SFX.warmIdent(), wait(400)])]);
    ready.then(() => { if (done) return; beganAt = performance.now(); wrap.classList.add("go"); dropLetters(); });
    Promise.all([loaded, ready]).then(() => after(Math.max(0, IDENT - (performance.now() - beganAt)), finish));
  }
  after(20000, finish);                                   // a piece that never answers must not hold the game shut

  // each letter falls out of the dark (stretched by its speed), lands squashed, bounces and settles, one after
  // another, a tick on each landing a step higher; the last lands on the hit (a bloom, a nudge of the whole word);
  // then the swash sweeps in, the glow comes up and the trademark rolls up on the shimmer
  function dropLetters() {
    const STAGGER = 105, FALL = 980, LAND = .42;
    const drop = -(innerHeight * .75 + word.getBoundingClientRect().top);
    const keys = [
      { offset: 0, transform: `translateY(${drop.toFixed(0)}px) scale(.94, 1.12)`, opacity: 1, easing: "cubic-bezier(.5, 0, .9, .55)" },
      { offset: LAND, transform: "translateY(0) scale(1.2, .7)", easing: "cubic-bezier(.2, .7, .4, 1)" },
      { offset: .6, transform: "translateY(-11%) scale(.95, 1.07)", easing: "cubic-bezier(.5, 0, .8, .5)" },
      { offset: .74, transform: "translateY(0) scale(1.08, .9)", easing: "cubic-bezier(.2, .7, .4, 1)" },
      { offset: .85, transform: "translateY(-2.5%) scale(.99, 1.02)", easing: "cubic-bezier(.5, 0, .8, .5)" },
      { offset: .93, transform: "translateY(0) scale(1.02, .98)" },
      { offset: 1, transform: "none", opacity: 1 },
    ];
    let t = 120;
    INTRO_DROP.forEach((k, i) => {
      const el = pieceEl[k], last = i === INTRO_DROP.length - 1;
      after(t, () => el.animate(keys, { duration: FALL, fill: "both" }).finished.then(() => el.classList.add("flat"), () => {}));
      after(t + FALL * LAND, () => {
        SFX.ident("landBrick", .82 + i * .07);
        if (last) {
          SFX.ident("introHit");
          const fl = wrap.querySelector(".introflash"); fl.classList.remove("on"); void fl.offsetWidth; fl.classList.add("on");
          word.animate([{ transform: "none" }, { transform: "translateY(1.2%) scale(1.03)" }, { transform: "none" }], { duration: 420, easing: "cubic-bezier(.2, .9, .3, 1)" });
        }
      });
      t += STAGGER;
    });
    const landed = 120 + (INTRO_DROP.length - 1) * STAGGER + FALL * LAND;
    after(landed + 140, () => {
      SFX.ident("introWhoosh");
      pieceEl.swash.animate([{ clipPath: "inset(0 100% 0 0)", opacity: 1 }, { clipPath: "inset(0 0 0 0)", opacity: 1 }],
                            { duration: 420, easing: "cubic-bezier(.5, 0, .2, 1)", fill: "both" }).finished.then(() => pieceEl.swash.classList.add("flat"), () => {});
    });
    after(landed + 520, () => word.querySelector(".iwglow").classList.add("up"));
    after(landed + 760, () => {
      wrap.querySelector(".introtm span").animate([{ transform: "translateY(120%)" }, { transform: "translateY(-12%)", offset: .7 }, { transform: "none" }],
                                                   { duration: 620, easing: "cubic-bezier(.2, .8, .3, 1)", fill: "both" });
      pieceEl.tm.animate([{ opacity: 0, transform: "translateY(40%) scale(.6)" }, { opacity: 1, transform: "none" }],
                         { duration: 360, delay: 160, easing: "cubic-bezier(.2, .9, .3, 1.4)", fill: "both" }).finished.then(() => pieceEl.tm.classList.add("flat"), () => {});
      after(520, () => SFX.ident("introShimmer"));
    });
  }
  return { progress: p => { fill.style.width = (Math.max(0, Math.min(1, p)) * 100).toFixed(1) + "%"; }, finish };
}

// The plates arrive as one stack in the middle of their row - fanned a few degrees, the middle one on top - and are
// dealt out to their places, eased, a beat apart (on translate/rotate, added over their own drift).
function fanPlates(wrap) {
  if (REDUCED || !Element.prototype.animate) return;
  const row = wrap.querySelector(".fboxes"), plates = [...wrap.querySelectorAll(".fbox")];
  const rr = row.getBoundingClientRect(), cx = rr.left + rr.width / 2, cy = rr.top + rr.height / 2, mid = (plates.length - 1) / 2;
  plates.forEach((el, i) => {
    const r = el.getBoundingClientRect(), dx = cx - (r.left + r.width / 2), dy = cy - (r.top + r.height / 2);
    if (i === Math.round(mid)) el.style.zIndex = "1";
    el.animate([{ translate: `${dx.toFixed(1)}px ${dy.toFixed(1)}px`, rotate: `${((i - mid) * 7).toFixed(1)}deg` }, { translate: "0px 0px", rotate: "0deg" }],
               { duration: 950, delay: 300 + i * 110, easing: "cubic-bezier(.22, 1, .36, 1)", fill: "backwards", composite: "add" })
      .finished.then(() => { el.style.zIndex = ""; }, () => {});
  });
}
// The plates in 3D: --mx/--my (where the pointer is across and down a plate, -.5...5) and --glare (0..1), eased every
// frame while anything still moves; the CSS turns them into the tilt, the sliding shadow and sheen. Touch never tilts.
function tiltPlates(plates) {
  if (REDUCED) return { stop() {} };
  const tilts = [];
  let raf = 0, stopped = false;
  const step = () => {
    raf = 0;
    if (stopped) return;
    let moving = false;
    for (const p of tilts) {
      p.x += (p.tx - p.x) * .16; p.y += (p.ty - p.y) * .16; p.g += (p.tg - p.g) * .14;
      if (Math.abs(p.tx - p.x) + Math.abs(p.ty - p.y) + Math.abs(p.tg - p.g) > .002) moving = true;
      else { p.x = p.tx; p.y = p.ty; p.g = p.tg; }
      p.el.style.setProperty("--mx", p.x.toFixed(4)); p.el.style.setProperty("--my", p.y.toFixed(4)); p.el.style.setProperty("--glare", p.g.toFixed(3));
    }
    if (moving) raf = requestAnimationFrame(step);
  };
  const wake = () => { if (!raf && !stopped) raf = requestAnimationFrame(step); };
  const clamp = v => Math.max(-.5, Math.min(.5, v));
  plates.forEach(el => {
    const p = { el, x: 0, y: 0, g: 0, tx: 0, ty: 0, tg: 0 };
    tilts.push(p);
    el.addEventListener("pointermove", e => {
      if (e.pointerType === "touch") return;
      const r = el.getBoundingClientRect(); if (!r.width) return;
      p.tx = clamp((e.clientX - r.left) / r.width - .5); p.ty = clamp((e.clientY - r.top) / r.height - .5); p.tg = 1; wake();
    });
    el.addEventListener("pointerleave", () => { p.tx = p.ty = p.tg = 0; wake(); });
  });
  return { stop() { stopped = true; if (raf) cancelAnimationFrame(raf); } };
}
// The features screen (owner, 2026-11-18: orleans' three plates, ninja style): the title and three plates that say how
// the game plays, over the dojo wall with the game faded out beneath. A click (or Space / Enter) anywhere goes in - and
// is the press that lets the music and sound start. Resolves once the game is showing.
function runFeatures() {
  return new Promise(resolve => {
    document.body.classList.add("features-up", "features-fade");
    const wrap = document.createElement("div");
    wrap.className = "features";
    wrap.setAttribute("role", "dialog");
    wrap.setAttribute("aria-label", T("How the game works"));
    const box = (img, title, text) => `<div class="fbox"><div class="fin"><div class="ficon"><img src="assets/features/${img}.webp" alt="" draggable="false"></div>` +
                                      `<h3>${fnHTML(title, "gold")}</h3><p>${text}</p></div></div>`;
    wrap.innerHTML =
      `<img class="ftitle" src="assets/logo.webp" alt="Juice Dojo" draggable="false">` +
      `<div class="fboxes">` +
        box("lines", T("Slice the lines"),
            T("Every spin drops a <b>4 x 4</b> wave of fruit. <b>10</b> lines - rows, columns and diagonals - pay <b>both ways</b> for <b>3</b> or <b>4</b> of a kind. Slice <b>3</b> or more lines in one wave for a <b>x2</b> combo, <b>5</b> or more for <b>x3</b>.")) +
        box("frenzy", T("Fruit Frenzy"),
            T("<b>3</b> or more golden star fruit start up to <b>50</b> faster waves in a row. <b>4</b> star fruit start the multiplier at <b>x2</b>, <b>5</b> or more at <b>x3</b>. Side fruit pays on every wave, and surviving all <b>50</b> slices the <b>Gold Melon</b>.")) +
        box("bomb", T("Peaches & bombs"),
            T("Multiplier peaches - <b>x2</b> to <b>x10</b> - add up into one frenzy multiplier. Any frenzy wave may carry a bomb: it ends the frenzy, but everything won is kept. Frost grapes knock the bomb chance back to <b>5%</b>.")) +
      `</div>` +
      `<div class="fcont"><span class="fhit"><span class="ftxt">${T("Click to play")}</span></span></div>`;
    document.body.appendChild(wrap);
    // the title, the plates and CLICK TO PLAY together fit the window: shrunk as one when they are taller (--ffit)
    const fit = () => {
      if (!wrap.isConnected) return removeEventListener("resize", fit);
      // each plate's title shrinks to its panel when it is wider (PEACHES & BOMBS was clipped at the edges)
      for (const h of wrap.querySelectorAll(".fbox h3")) {
        h.style.fontSize = "";
        const word = h.firstElementChild, k = h.parentElement.clientWidth / Math.max(1, word.offsetWidth);
        if (k < 1) h.style.fontSize = `calc(8.6cqw * ${(k * .96).toFixed(3)})`;
      }
      wrap.style.setProperty("--ffit", "1");
      for (let i = 0; i < 3; i++) {
        const have = wrap.clientHeight, need = wrap.scrollHeight;
        if (need <= have + 1) break;
        const k = parseFloat(wrap.style.getPropertyValue("--ffit")) || 1;
        wrap.style.setProperty("--ffit", Math.max(.3, k * have / need * .985).toFixed(3));
      }
    };
    fit(); addEventListener("resize", fit);
    const title = wrap.querySelector(".ftitle");
    if (!title.complete) title.addEventListener("load", fit, { once: true });
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(fit);
    const tilt = tiltPlates([...wrap.querySelectorAll(".fbox"), wrap.querySelector(".fcont .fhit")]);
    requestAnimationFrame(() => { fanPlates(wrap); wrap.classList.add("up"); });
    let done = false;
    const go = () => {
      if (done || !wrap.classList.contains("up")) return;
      done = true;
      document.removeEventListener("keydown", onKey, true);
      SFX.unlock();                                       // the press that lets sound start
      SFX.swordDraw();
      wrap.classList.add("gone");                         // the plates fade out
      document.body.classList.remove("features-up");     // and the game fades in beneath them
      setTimeout(() => { tilt.stop(); wrap.remove(); document.body.classList.remove("features-fade"); resolve(); }, 800);
    };
    const onKey = e => { if (e.code !== "Space" && e.code !== "Enter") return; e.preventDefault(); e.stopPropagation(); go(); };
    document.addEventListener("keydown", onKey, true);
    wrap.addEventListener("click", go);
  });
}

/* ---------------------------------------------------------------- boot */
async function boot() {
  layout();
  addEventListener("resize", () => { buildHud(); fitHud(); layout(); });
  requestAnimationFrame(frame);
  let loadedOk;
  const loaded = new Promise(r => { loadedOk = r; });
  const intro = runIntro(loaded);
  const art = loadArt(k => intro.progress(k * .6));
  const rp = RGS.replayParams();
  state.replay = rp.replay;
  if (rp.replay) document.body.classList.add("replay");
  try {
    if (!rp.replay) await RGS.authenticate();
  } catch (err) {
    await art;
    intro.finish(); await introDone;
    return fatal("Can't connect", (err && err.message) || "The game server could not be reached.");
  }
  intro.progress(.8);
  await art;
  intro.progress(1);
  for (const m of (RGS.state.config && RGS.state.config.gameModes) || []) modeCost[m.mode] = m.costMultiplier;
  state.bets = RGS.betLevels();
  const def = (RGS.state.config && RGS.state.config.defaultBetLevel) || UNIT;
  let want = def;
  try { const s = +sessionStorage.getItem("juicedojo.bet"); if (s) want = s; } catch (e) { /* ignore */ }
  state.betIdx = Math.max(0, state.bets.findIndex(b => b >= want));
  if (state.bets[state.betIdx] !== want) state.betIdx = Math.max(0, state.bets.indexOf(def));
  showBalance(RGS.state.balance);
  paintVol(); paintAuto(); refreshBet();
  loadedOk();
  await introDone;
  if (rp.replay) return runReplay(rp);                    // (a replay link: straight to its window)
  await runFeatures();
  // a round left open by a disconnect is finished first
  const open = RGS.state.round;
  if (open && open.active) {
    notice(T("Finishing your last round…"));
    state.playing = true; setButtons(false);
    await runRound(open);
  }
}

async function runReplay(rp) {
  $("replayWrap").hidden = false;
  $("replayMeta").textContent = `${rp.mode} · ${T("bet")} ${RGS.money(rp.amount * UNIT, rp.currency)}`;
  try {
    const d = await RGS.replay(rp);
    state.bets = [Math.round(rp.amount * UNIT) || UNIT]; state.betIdx = 0;
    $("replayStatus").textContent = `${T("Payout")}: ${(d.payoutMultiplier || 0).toFixed(2)}x · ${T("cost")} ${d.costMultiplier || 1}x`;
    $("replayPlay").hidden = false;
    $("replayPlay").onclick = async () => {
      SFX.unlock();
      $("replayWrap").hidden = true;
      state.playing = true; setButtons(false);
      await playEvents(d.state);
      const pay = Math.round((d.payoutMultiplier || 0) * bet());
      if (pay > 0) await bigWin(pay);
      state.playing = false;
      $("replayResult").hidden = false;
      $("replayResult").textContent = `${T("Win")}: ${fmt(pay)} (${(d.payoutMultiplier || 0).toFixed(2)}x)`;
      $("replayPlay").textContent = T("Play again");
      $("replayWrap").hidden = false;
    };
  } catch (err) {
    $("replayStatus").textContent = T("This round could not be loaded.");
  }
}

boot();
