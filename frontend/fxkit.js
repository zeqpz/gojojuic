/* Juice Dojo FX kit - the light, sparkle and juice detail of the bonus-buy banner art, drawn on the fx canvas.
 *   sprites  soft glows, hot dots, four-point flares, turning ray fans, light streaks, snowflakes and bokeh discs,
 *            each built once on a small canvas (per colour) and stamped
 *   parts    one pool of particles: glitter, sparks, embers, frost, juice beads, fruit chunks, seeds, smoke
 *   auras    the special fruit: a pulsing halo, turning rays, twinkles orbiting on a tilted ring, a light streak and
 *            a glitter trail as they fall; crackling arcs on the multiplier peaches, a spitting fuse on the bomb
 *            (its spark tracked frame by frame from Blender: meta.json track.fuse), frost on the grapes
 *   bursts   a cut fruit throws glossy juice beads in strings, chunks of flesh and seeds and a few sparkles; a
 *            special fruit goes off in a flare and rays with a shower of glitter (lightning for the peaches)
 *   room     warm bokeh drifting over the wall and dust glinting in the light; in the frenzy, embers rising and
 *            (Xtreme) lightning crackling at the edges
 *   juice    drops in flight are glossy lit beads stretched along their flight; strings of beads hang together by
 *            thin filaments; a fine spray and a soft mist at the cut
 *   stains   the juice that hits the wall soaks into the wood: each splat and drip (OpenRouter renders, turned into
 *            density / glint / shape layers by tools/stain_layers.py) is tinted and MULTIPLIED into the wood (the
 *            #stain canvas blends with mix-blend-mode: multiply) so the grain shows through - thin film at the
 *            edges, deep where it pools, a darker drying rim - and while it is wet it is lit in screen space from
 *            the room's light (top left, like the fruit): a bright rim where it faces the light, a dark rim away
 *            from it, a sheen and its glints, all fading as it dries. Drips creep down painting as they go, led by
 *            a glossy bead; stray drops leave small elongated stains where they land
 * Loaded before game.js; reads its globals (world, W, H, S, DPR, META, SPRITE, REDUCED) only when called.
 * Additive layers are drawn with "lighter". The pool is capped so a busy frenzy stays cheap. */
"use strict";

const FX = (() => {
  const TAU = Math.PI * 2;
  const memo = new Map();
  const once = (key, make) => { let c = memo.get(key); if (!c) { c = make(); memo.set(key, c); } return c; };
  const canvas = (w, h = w) => { const c = document.createElement("canvas"); c.width = w; c.height = h; return [c, c.getContext("2d")]; };
  const rgbOf = hex => {
    const h = hex.length === 4 ? hex[1] + hex[1] + hex[2] + hex[2] + hex[3] + hex[3] : hex.slice(1, 7), n = parseInt(h, 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  };
  const rgba = (hex, a) => { const [r, gr, b] = rgbOf(hex); return `rgba(${r},${gr},${b},${a})`; };
  const rnd = (a, b) => a + Math.random() * (b - a);
  const pick = a => a[Math.floor(Math.random() * a.length)];
  const clock = () => performance.now() / 1000;

  /* ------------------------------------------------------------------ sprites */
  // a soft glow, the colour full at the heart and gone at the edge
  function glow(col) {
    return once("glow" + col, () => {
      const [c, x] = canvas(128), gr = x.createRadialGradient(64, 64, 0, 64, 64, 64);
      gr.addColorStop(0, rgba(col, 1)); gr.addColorStop(.14, rgba(col, .7)); gr.addColorStop(.32, rgba(col, .3));
      gr.addColorStop(.58, rgba(col, .09)); gr.addColorStop(1, rgba(col, 0));
      x.fillStyle = gr; x.fillRect(0, 0, 128, 128);
      return c;
    });
  }
  // a glitter dot: white-hot centre in a coloured glow
  function dot(col) {
    return once("dot" + col, () => {
      const [c, x] = canvas(64), gr = x.createRadialGradient(32, 32, 0, 32, 32, 32);
      gr.addColorStop(0, "rgba(255,255,255,1)"); gr.addColorStop(.1, rgba(col, .95)); gr.addColorStop(.28, rgba(col, .38));
      gr.addColorStop(.6, rgba(col, .08)); gr.addColorStop(1, rgba(col, 0));
      x.fillStyle = gr; x.fillRect(0, 0, 64, 64);
      return c;
    });
  }
  // a four-point star flare: two long streaks, two short diagonals, a white core in a coloured glow
  function flare(col) {
    return once("flare" + col, () => {
      const N = 256, h = N / 2, [c, x] = canvas(N);
      x.globalCompositeOperation = "lighter";
      x.globalAlpha = .55; x.drawImage(glow(col), h * .45, h * .45, h * 1.1, h * 1.1);
      x.globalAlpha = 1;
      const streak = (ang, len, thin, a) => {
        x.save(); x.translate(h, h); x.rotate(ang); x.scale(1, thin);
        const gr = x.createRadialGradient(0, 0, 0, 0, 0, h * len);
        gr.addColorStop(0, `rgba(255,255,255,${a})`); gr.addColorStop(.22, rgba(col, a * .8)); gr.addColorStop(1, rgba(col, 0));
        x.fillStyle = gr; x.beginPath(); x.arc(0, 0, h * len, 0, TAU); x.fill(); x.restore();
      };
      streak(0, 1, .05, 1); streak(Math.PI / 2, 1, .05, 1);
      streak(Math.PI / 4, .5, .045, .6); streak(-Math.PI / 4, .5, .045, .6);
      const core = x.createRadialGradient(h, h, 0, h, h, h * .17);
      core.addColorStop(0, "rgba(255,255,255,1)"); core.addColorStop(1, "rgba(255,255,255,0)");
      x.fillStyle = core; x.fillRect(0, 0, N, N);
      return c;
    });
  }
  // a fan of light rays of uneven width and length, soft-edged (seed: a different fan)
  function rays(col, seed = 1) {
    return once(`rays${col}${seed}`, () => {
      const N = 512, h = N / 2, [c, x] = canvas(N);
      let s = seed * 7919;
      const r01 = () => ((s = (s * 16807) % 2147483647) / 2147483647);
      x.globalCompositeOperation = "lighter";
      const n = 15 + seed * 2;
      for (let i = 0; i < n; i++) {
        const a = (i + r01() * .7) / n * TAU, w = .02 + r01() * .05, L = h * (.5 + r01() * .5), al = .3 + r01() * .55;
        const gr = x.createRadialGradient(h, h, 0, h, h, L);
        gr.addColorStop(0, rgba(col, al)); gr.addColorStop(.3, rgba(col, al * .6)); gr.addColorStop(1, rgba(col, 0));
        x.fillStyle = gr;
        for (const [ww, aa] of [[w * 1.8, .35], [w, .6], [w * .4, .9]]) {   // soft edges: wide and faint to narrow and bright
          x.globalAlpha = aa;
          x.beginPath(); x.moveTo(h, h);
          x.lineTo(h + Math.cos(a - ww) * L, h + Math.sin(a - ww) * L);
          x.lineTo(h + Math.cos(a + ww) * L, h + Math.sin(a + ww) * L);
          x.closePath(); x.fill();
        }
      }
      const [c2, x2] = canvas(N);                       // a touch of blur where the browser can
      x2.filter = "blur(2px)"; x2.drawImage(c, 0, 0);
      return x2.filter === "blur(2px)" ? c2 : c;
    });
  }
  // a light streak: bright at the bottom (where the fruit is), fading up, soft at the sides
  function streak(col) {
    return once("streak" + col, () => {
      const w = 64, h = 256, [c, x] = canvas(w, h);
      const v = x.createLinearGradient(0, 0, 0, h);
      v.addColorStop(0, rgba(col, 0)); v.addColorStop(.55, rgba(col, .3)); v.addColorStop(.9, rgba(col, .85)); v.addColorStop(1, "rgba(255,255,255,.95)");
      x.fillStyle = v; x.fillRect(0, 0, w, h);
      x.globalCompositeOperation = "destination-in";
      const s = x.createLinearGradient(0, 0, w, 0);
      s.addColorStop(0, "rgba(0,0,0,0)"); s.addColorStop(.5, "rgba(0,0,0,1)"); s.addColorStop(1, "rgba(0,0,0,0)");
      x.fillStyle = s; x.fillRect(0, 0, w, h);
      return c;
    });
  }
  // a snowflake glinting in an icy glow
  function snow() {
    return once("snow", () => {
      const [c, x] = canvas(48), h = 24;
      x.globalCompositeOperation = "lighter";
      x.globalAlpha = .7; x.drawImage(glow("#9fdcff"), 2, 2, 44, 44); x.globalAlpha = 1;
      x.strokeStyle = "rgba(255,255,255,.95)"; x.lineCap = "round"; x.lineWidth = 2;
      for (let i = 0; i < 6; i++) {
        const a = i * Math.PI / 3;
        x.beginPath(); x.moveTo(h, h); x.lineTo(h + Math.cos(a) * 15, h + Math.sin(a) * 15); x.stroke();
        for (const sd of [-1, 1]) {
          const bx = h + Math.cos(a) * 9, by = h + Math.sin(a) * 9, ba = a + sd * .75;
          x.beginPath(); x.moveTo(bx, by); x.lineTo(bx + Math.cos(ba) * 5, by + Math.sin(ba) * 5); x.stroke();
        }
      }
      return c;
    });
  }
  // an out-of-focus light: a soft disc with a slightly brighter rim
  function bokeh(col) {
    return once("bokeh" + col, () => {
      const [c, x] = canvas(96), gr = x.createRadialGradient(48, 48, 0, 48, 48, 48);
      gr.addColorStop(0, rgba(col, .45)); gr.addColorStop(.72, rgba(col, .4)); gr.addColorStop(.87, rgba(col, .62));
      gr.addColorStop(.95, rgba(col, .18)); gr.addColorStop(1, rgba(col, 0));
      x.fillStyle = gr; x.fillRect(0, 0, 96, 96);
      return c;
    });
  }

  // a drop of juice, translucent and lit from the top left: light inside, deeper at the rim, a caustic low right where
  // the light comes through, a sharp glint (drawn upright, so the glint stays where the light is)
  function droplet(col) {
    return once("drop" + col, () => {
      const N = 48, h = N / 2, [c, x] = canvas(N), deep = shade(col, -.45), lite = shade(col, .42);
      const body = x.createRadialGradient(h - 4, h - 5, 1, h, h, h - 1.5);
      body.addColorStop(0, rgba(lite, .88)); body.addColorStop(.5, rgba(col, .8)); body.addColorStop(.84, rgba(deep, .9)); body.addColorStop(1, rgba(deep, .95));
      x.fillStyle = body; x.beginPath(); x.arc(h, h, h - 1.5, 0, TAU); x.fill();
      const cs = x.createRadialGradient(h + 7, h + 8, 0, h + 7, h + 8, 10);      // light gathered low right, through the drop
      cs.addColorStop(0, rgba(lite, .75)); cs.addColorStop(1, rgba(lite, 0));
      x.fillStyle = cs; x.beginPath(); x.arc(h, h, h - 1.5, 0, TAU); x.fill();
      const gl = x.createRadialGradient(h - 7, h - 8, 0, h - 7, h - 8, 8);       // the glint
      gl.addColorStop(0, "rgba(255,255,255,1)"); gl.addColorStop(.3, "rgba(255,255,255,.85)"); gl.addColorStop(1, "rgba(255,255,255,0)");
      x.fillStyle = gl; x.beginPath(); x.ellipse(h - 7, h - 8, 8, 5.5, -.6, 0, TAU); x.fill();
      return c;
    });
  }
  // the tail a flying drop draws out behind it: a wedge of juice thinning to nothing, lit along its upper edge
  // (pointing +x: the drop's head is at the right end)
  function tail(col) {
    return once("tail" + col, () => {
      const w = 64, h = 16, [c, x] = canvas(w, h), gr = x.createLinearGradient(0, 0, w, 0);
      gr.addColorStop(0, rgba(col, 0)); gr.addColorStop(.65, rgba(col, .42)); gr.addColorStop(1, rgba(col, .78));
      x.fillStyle = gr; x.beginPath(); x.moveTo(0, h / 2); x.lineTo(w, 1.5); x.lineTo(w, h - 1.5); x.closePath(); x.fill();
      const hl = x.createLinearGradient(16, 0, w, 0);
      hl.addColorStop(0, "rgba(255,255,255,0)"); hl.addColorStop(1, "rgba(255,255,255,.6)");
      x.strokeStyle = hl; x.lineWidth = 1.2; x.beginPath(); x.moveTo(16, h / 2 - 1.6); x.lineTo(w - 2, 3.6); x.stroke();
      return c;
    });
  }
  // a cube of flesh, toon-lit like the fruit: light top face, mid front, dark side, the dark outline, a wet glint
  function chunkSpr(col) {
    return once("chunk" + col, () => {
      const [c, x] = canvas(32), s = 11, cx = 16, cy = 16;
      const poly = (pts, fill) => { x.beginPath(); x.moveTo(pts[0][0], pts[0][1]); for (const p of pts) x.lineTo(p[0], p[1]); x.closePath(); x.fillStyle = fill; x.fill(); };
      poly([[cx, cy - s], [cx + s, cy - s * .5], [cx, cy], [cx - s, cy - s * .5]], shade(col, .38));
      poly([[cx - s, cy - s * .5], [cx, cy], [cx, cy + s], [cx - s, cy + s * .5]], col);
      poly([[cx, cy], [cx + s, cy - s * .5], [cx + s, cy + s * .5], [cx, cy + s]], shade(col, -.3));
      x.strokeStyle = "rgba(40,16,6,.8)"; x.lineWidth = 1.7; x.lineJoin = "round";
      x.beginPath(); x.moveTo(cx, cy - s); x.lineTo(cx + s, cy - s * .5); x.lineTo(cx + s, cy + s * .5); x.lineTo(cx, cy + s);
      x.lineTo(cx - s, cy + s * .5); x.lineTo(cx - s, cy - s * .5); x.closePath(); x.stroke();
      x.fillStyle = "rgba(255,255,255,.8)"; x.beginPath(); x.ellipse(cx - 2, cy - s * .55, 3.2, 1.4, -.45, 0, TAU); x.fill();
      return c;
    });
  }
  function seedSpr(col) {
    return once("seed" + col, () => {
      const [c, x] = canvas(24);
      x.fillStyle = col; x.beginPath(); x.ellipse(12, 12, 9, 5.5, 0, 0, TAU); x.fill();
      x.fillStyle = "rgba(255,255,255,.55)"; x.beginPath(); x.ellipse(8.5, 10, 2.6, 1.3, -.3, 0, TAU); x.fill();
      return c;
    });
  }
  // the light on a small wet drop on the wall: a glint top left, a dark crescent low right
  function wetDot() {
    return once("wetdot", () => {
      const [c, x] = canvas(32);
      x.fillStyle = "rgba(28,12,4,.42)"; x.beginPath(); x.arc(17.5, 18.5, 8, 0, TAU); x.fill();
      x.globalCompositeOperation = "destination-out"; x.beginPath(); x.arc(15.2, 15.6, 8, 0, TAU); x.fill();
      x.globalCompositeOperation = "source-over";
      const gl = x.createRadialGradient(12.5, 12, 0, 12.5, 12, 5.5);
      gl.addColorStop(0, "rgba(255,255,255,.95)"); gl.addColorStop(1, "rgba(255,255,255,0)");
      x.fillStyle = gl; x.fillRect(0, 0, 32, 32);
      return c;
    });
  }

  /* ------------------------------------------------------------------ the special fruit */
  // col: the aura; hot: its bright heart; glit: the sparkle it sheds. rays/orbit/arcs scale those layers.
  const AURA = {
    SC:   { col: "#ffc21f", hot: "#fff2a8", glit: "#ffe58a", rays: 1,    orbit: 3, trail: 1 },
    JM:   { col: "#ffbf1a", hot: "#fff4c0", glit: "#ffe9a0", rays: 1.5,  orbit: 5, trail: 0 },
    PW2:  { col: "#3d9bff", hot: "#d2ecff", glit: "#a8d8ff", rays: .8,   orbit: 2, trail: 1, arcs: 1 },
    PW3:  { col: "#b04dff", hot: "#efd6ff", glit: "#dcb4ff", rays: .8,   orbit: 2, trail: 1, arcs: 1.2 },
    PW5:  { col: "#ff4d2a", hot: "#ffd6c2", glit: "#ffb08a", rays: .9,   orbit: 3, trail: 1, arcs: 1.5 },
    PW10: { col: "#ffcc00", hot: "#fff3b8", glit: "#ffe27a", rays: 1.1,  orbit: 4, trail: 1, arcs: 1.8 },
    FRZ:  { col: "#6fcfff", hot: "#f0fbff", glit: "#ffffff", rays: .55,  orbit: 0, trail: 1, frost: 1 },
    BOMB: { col: "#ff2a1a", hot: "#ffb08a", glit: "#ffcf6a", rays: 0,    orbit: 0, trail: 0, fuse: 1 },
  };
  // the flesh a cut fruit shows (chunks) and its seeds
  const FLESH = { H1: "#ff3348", H2: "#ffd84a", H3: "#f7f4ee", H4: "#f6f8ff", L1: "#ffa21a", L2: "#fff1c2", L3: "#fff38a",
                  L4: "#86dc22", SC: "#ffe45a", PW2: "#ffb55e", PW3: "#ffb55e", PW5: "#ffb55e", PW10: "#ffb55e", FRZ: "#d8f2ff", JM: "#ffd23a" };
  const SEEDS = { H1: "#1c120c", H3: "#17110c", L4: "#17110c" };
  const live = f => AURA[f.id] && !f.gone && f.mode !== "wait" && !(f.delay > 0);
  const tilt = f => f.rot + (f.wobA ? Math.sin(f.ph) * f.wobA : 0);   // the angle the fruit is drawn at
  const k1 = () => S / 120;                                            // sizes are tuned at a 120 px cell

  // where the bomb's fuse spark is right now (its tumble frame, interpolated), and whether it is in view
  function fusePos(f) {
    const m = META && META.fruit[SPRITE(f.id)], tr = m && m.track && m.track.fuse;
    if (!tr) return null;
    const n = tr.length, u = ((f.spin / TAU) % 1 + 1) % 1 * n, i0 = Math.floor(u) % n, i1 = (i0 + 1) % n, fr = u - Math.floor(u);
    const lerp = j => tr[i0][j] + (tr[i1][j] - tr[i0][j]) * fr;
    const k = f.size * 1.06, lx = (lerp(0) - .5) * k, ly = (lerp(1) - .5) * k, a = tilt(f), c = Math.cos(a), s = Math.sin(a);
    return { x: f.x + lx * c - ly * s, y: f.y + lx * s + ly * c, vis: lerp(2) };
  }

  /* ------------------------------------------------------------------ particles */
  const P = [], MAX = 560, strings = [];
  function add(p) { if (P.length >= MAX) P.splice(0, 40); p.age = 0; P.push(p); return p; }
  const glitter = (x, y, vx, vy, col, r, life, extra) => add(Object.assign({ k: "gl", x, y, vx, vy, col, r, life, drag: 1.8, grav: 120, tw: rnd(8, 20), ph: rnd(0, TAU) }, extra));

  const flashes = [], bolts = [];
  const flash = (x, y, spr, size, dur, a0 = 1, rot = 0, vr = 0, grow = .35) => flashes.push({ x, y, spr, size, dur, a0, rot, vr, grow, age: 0 });
  function jag(x0, y0, x1, y1, rough, depth, out) {       // a lightning path by midpoint displacement
    if (depth === 0) { out.push([x1, y1]); return; }
    const mx = (x0 + x1) / 2 + (Math.random() - .5) * rough, my = (y0 + y1) / 2 + (Math.random() - .5) * rough;
    jag(x0, y0, mx, my, rough / 2, depth - 1, out); jag(mx, my, x1, y1, rough / 2, depth - 1, out);
  }
  function arcAround(R) {                                   // fruit-local: a crackle round the skin, or a bolt leaping off it
    const pts = [], kind = Math.random();
    if (kind < .28) {
      const a = rnd(0, TAU), r0 = R * .42, L = R * rnd(.5, 1.1), b = a + rnd(-.5, .5), x0 = Math.cos(a) * r0, y0 = Math.sin(a) * r0;
      pts.push([x0, y0]); jag(x0, y0, x0 + Math.cos(b) * L, y0 + Math.sin(b) * L, L * .5, 4, pts);
    } else if (kind < .55) {                              // a vein of light across the skin
      const a = rnd(0, TAU), b = a + rnd(-.9, .9), x0 = Math.cos(a) * R * .44, y0 = Math.sin(a) * R * .44, r1 = R * rnd(.05, .25);
      pts.push([x0, y0]); jag(x0, y0, Math.cos(b) * r1, Math.sin(b) * r1, R * .14, 3, pts);
      return { pts, age: 0, dur: rnd(.16, .32), w: rnd(.45, .7) };
    } else {
      const a0 = rnd(0, TAU), span = rnd(.7, 1.7), n = 6;
      let px = Math.cos(a0) * R * .47, py = Math.sin(a0) * R * .47;
      pts.push([px, py]);
      for (let i = 1; i <= n; i++) {
        const a = a0 + span * i / n, r = R * rnd(.41, .53), x = Math.cos(a) * r, y = Math.sin(a) * r;
        jag(px, py, x, y, R * .12, 2, pts); px = x; py = y;
      }
    }
    return { pts, age: 0, dur: rnd(.12, .26), w: rnd(.8, 1.3) };
  }
  function strokeBolt(ctx, pts, col, hot, w, a) {
    for (const [c, lw, al] of [[col, 10, .32], [hot, 4.2, .8], ["#ffffff", 1.6, 1]]) {
      ctx.strokeStyle = c; ctx.globalAlpha = al * a; ctx.lineWidth = lw * w;
      ctx.beginPath(); ctx.moveTo(pts[0][0], pts[0][1]); for (const q of pts) ctx.lineTo(q[0], q[1]); ctx.stroke();
    }
  }
  const flick = k => k < .35 || (k > .5 && k < .8);         // on, off, on, gone
  // B (the context's transform as it was, screen shake included) x translate(x, y) x rotate(a)
  function place(ctx, B, x, y, a) {
    const c = Math.cos(a), s = Math.sin(a);
    ctx.setTransform(B.a * c + B.c * s, B.b * c + B.d * s, B.c * c - B.a * s, B.d * c - B.b * s, B.a * x + B.c * y + B.e, B.b * x + B.d * y + B.f);
  }

  /* ------------------------------------------------------------------ the room */
  const room = { bokeh: [], dust: [], w: 0, h: 0, mode: 0, nextBolt: 1 };
  function roomInit() {
    room.w = W; room.h = H; room.bokeh.length = 0; room.dust.length = 0;
    for (let i = 0; i < 11; i++) room.bokeh.push({ x: rnd(0, W), y: rnd(0, H), r: rnd(.35, 1.1) * S, vx: rnd(-7, 7), vy: rnd(-5, 3), a: rnd(.05, .1), ph: rnd(0, TAU), col: pick(["#ffd27a", "#ffb35c", "#ffe2a8"]) });
    for (let i = 0; i < 26; i++) room.dust.push({ x: rnd(0, W), y: rnd(0, H), r: rnd(.7, 1.8), vx: rnd(-4, 4), vy: rnd(3, 12), a: rnd(.25, .6), ph: rnd(0, TAU), tw: rnd(1, 3) });
  }
  const wrap = (v, lo, hi) => (v < lo ? v + (hi - lo) : v > hi ? v - (hi - lo) : v);

  /* ------------------------------------------------------------------ update (called from step) */
  function update(dt, rdt) {
    if (room.w !== W || room.h !== H) roomInit();
    let j = 0;
    for (let i = 0; i < P.length; i++) {
      const p = P[i];
      p.age += dt;
      if (p.age >= p.life) { if (p.k === "bd" && Math.random() < .4 && p.y < H) dropStain(p); continue; }
      const d = Math.max(0, 1 - p.drag * dt);
      p.vx *= d; p.vy = p.vy * d + p.grav * dt;
      if (p.sway) p.vx += Math.sin(p.age * 2.3 + p.ph) * p.sway * dt;
      p.x += p.vx * dt; p.y += p.vy * dt;
      if (p.vr) p.rot += p.vr * dt;
      P[j++] = p;
    }
    P.length = j;
    for (let i = strings.length - 1; i >= 0; i--) if (strings[i].beads.every(b => b.age >= b.life)) strings.splice(i, 1);
    // the wet stains dry; the drips creep down, painting the wall as they go
    for (const s of wet) {
      s.t += dt;
      if (s.drip && s.drip.k < 1) { const d = s.drip; d.t += dt; d.k = 1 - Math.pow(1 - Math.min(1, d.t / d.dur), 2.6); paintDrip(d); }
    }
    for (let i = wet.length - 1; i >= 0; i--) if (wet[i].t >= wet[i].dur && !(wet[i].drip && wet[i].drip.k < 1)) wet.splice(i, 1);
    for (const fl of flashes) fl.age += dt;
    for (let i = flashes.length - 1; i >= 0; i--) if (flashes[i].age >= flashes[i].dur) flashes.splice(i, 1);
    for (const b of bolts) b.age += dt;
    for (let i = bolts.length - 1; i >= 0; i--) if (bolts[i].age >= bolts[i].dur) bolts.splice(i, 1);
    if (REDUCED) return;
    const k = k1();
    // the special fruit: what they shed as they fall
    for (const f of world.fruit) {
      if (!live(f)) continue;
      const A = AURA[f.id], R = f.size, sp = Math.hypot(f.vx, f.vy);
      if (A.trail || A.orbit) {
        f.fxGl = (f.fxGl || 0) + dt * (10 + Math.min(26, sp / 35));
        while (f.fxGl >= 1) {
          f.fxGl--;
          const a = rnd(0, TAU), rr = R * rnd(.15, .5);
          glitter(f.x + Math.cos(a) * rr, f.y + Math.sin(a) * rr, f.vx * .08 + rnd(-30, 30), f.vy * .08 + rnd(-40, 10),
                  Math.random() < .7 ? A.glit : A.hot, rnd(1, 2.6) * k, rnd(.5, 1.1), { drag: 2, grav: 60 });
        }
      }
      if (A.fuse) {
        const q = fusePos(f);
        if (q && q.vis > .5) {
          f.fxSp = (f.fxSp || 0) + dt * 110;
          while (f.fxSp >= 1) {
            f.fxSp--;
            const a = -Math.PI / 2 + rnd(-1.5, 1.5), v = rnd(90, 330) * k;
            add({ k: "sp", x: q.x, y: q.y, vx: Math.cos(a) * v + f.vx * .9, vy: Math.sin(a) * v + f.vy * .9, col: pick(["#fff6c8", "#ffd27a", "#ff9a2a"]),
                  r: rnd(1, 2.2) * k, life: rnd(.16, .4), drag: 1.5, grav: 900 });
          }
          f.fxSm = (f.fxSm || 0) + dt * 7;
          while (f.fxSm >= 1) {
            f.fxSm--;
            add({ k: "sm", x: q.x, y: q.y, vx: f.vx * .85 + rnd(-15, 15), vy: f.vy * .85 - rnd(20, 50) * k, r: rnd(5, 9) * k, grow: rnd(14, 26) * k,
                  life: rnd(.5, .9), drag: 1.2, grav: -30, col: "#5d544c" });
          }
        }
      }
      if (A.frost) {
        f.fxSn = (f.fxSn || 0) + dt * 11;
        while (f.fxSn >= 1) {
          f.fxSn--;
          const a = rnd(0, TAU), rr = R * rnd(.3, .55);
          add({ k: "sn", x: f.x + Math.cos(a) * rr, y: f.y + Math.sin(a) * rr, vx: f.vx * .5 + Math.cos(a) * rnd(10, 40), vy: f.vy * .5 + Math.sin(a) * rnd(10, 40),
                r: rnd(1.6, 3) * k, life: rnd(.6, 1.2), drag: 1.4, grav: 40, rot: rnd(0, TAU), vr: rnd(-3, 3), ph: rnd(0, TAU) });
        }
      }
      if (A.arcs) {
        const arcs = f.fxArcs || (f.fxArcs = []);
        for (const a of arcs) a.age += rdt;
        for (let i = arcs.length - 1; i >= 0; i--) if (arcs[i].age >= arcs[i].dur) arcs.splice(i, 1);
        f.fxNextArc = (f.fxNextArc == null ? rnd(0, .1) : f.fxNextArc) - rdt;
        if (f.fxNextArc <= 0) { f.fxNextArc = rnd(.04, .16) / A.arcs; arcs.push(arcAround(R)); }
      }
    }
    // the room
    for (const b of room.bokeh) { b.x = wrap(b.x + b.vx * rdt, -b.r, W + b.r); b.y = wrap(b.y + b.vy * rdt, -b.r, H + b.r); }
    for (const d of room.dust) { d.x = wrap(d.x + (d.vx + Math.sin(clock() * .7 + d.ph) * 6) * rdt, 0, W); d.y = wrap(d.y + d.vy * rdt, 0, H); }
    if (room.mode) {
      // the frenzy: embers rising off the bottom of the screen
      room.emb = (room.emb || 0) + rdt * (room.mode === 2 ? 22 : 16);
      while (room.emb >= 1) {
        room.emb--;
        const x = rnd(0, W), xt = room.mode === 2;
        add({ k: "em", x, y: H + 8, vx: rnd(-20, 20), vy: -rnd(60, 170) * k, col: xt ? pick(["#ff4fa8", "#c56bff", "#ff6a3a"]) : pick(["#ffb347", "#ffd27a", "#ff7a12"]),
              r: rnd(1.2, 2.8) * k, life: rnd(2.5, 4.5), drag: .2, grav: -12, sway: 30, ph: rnd(0, TAU) });
      }
      if (room.mode === 2) {                                // Xtreme: lightning crackling down the edges
        room.nextBolt -= rdt;
        if (room.nextBolt <= 0) {
          room.nextBolt = rnd(.5, 1.5);
          const right = Math.random() < .5, x0 = right ? W - rnd(4, 34) : rnd(4, 34), y0 = rnd(-20, H * .55), y1 = y0 + rnd(.2, .45) * H;
          const pts = [[x0, y0]]; jag(x0, y0, x0 + rnd(-24, 24), y1, 70, 5, pts);
          bolts.push({ pts, col: pick(["#b04dff", "#ff2a8a"]), hot: "#ffd6f5", age: 0, dur: rnd(.22, .34), w: rnd(.9, 1.4) });
        }
      }
    }
  }

  /* ------------------------------------------------------------------ drawing */
  // behind everything on the fx canvas: the room's bokeh and dust
  function drawRoom(ctx) {
    if (REDUCED) return;
    const t = clock(), xt = room.mode === 2;
    ctx.save(); ctx.globalCompositeOperation = "lighter";
    for (const b of room.bokeh) {
      const col = room.mode ? (xt ? (b.col === "#ffb35c" ? "#ff4fa8" : "#a35cff") : "#ffae42") : b.col;
      ctx.globalAlpha = b.a * (room.mode ? 1.35 : 1) * (.7 + .3 * Math.sin(t * .5 + b.ph));
      ctx.drawImage(bokeh(col), b.x - b.r, b.y - b.r, b.r * 2, b.r * 2);
    }
    for (const d of room.dust) {
      ctx.globalAlpha = d.a * (.5 + .5 * Math.sin(t * d.tw + d.ph));
      const r = d.r * 3;
      ctx.drawImage(dot("#ffe6b8"), d.x - r, d.y - r, r * 2, r * 2);
    }
    ctx.restore();
  }
  // behind a special fruit: its halo, its turning rays, its light streak, the far side of its twinkle ring
  function auraBack(ctx, f) {
    if (!live(f)) return;
    const A = AURA[f.id], R = f.size, t = clock();
    if (f.fxPh == null) f.fxPh = rnd(0, TAU);
    ctx.save(); ctx.globalCompositeOperation = "lighter";
    const pulse = .5 + .5 * Math.sin(t * (A.fuse ? 10 : 3.1) + f.fxPh);
    let r = R * (1.32 + .12 * pulse);
    ctx.globalAlpha = A.fuse ? .22 + .3 * pulse : .6 + .2 * pulse;
    ctx.drawImage(glow(A.col), f.x - r, f.y - r, r * 2, r * 2);
    r = R * .95;                                                         // the colour hugging its edge
    ctx.globalAlpha = A.fuse ? .2 : .55;
    ctx.drawImage(glow(A.col), f.x - r, f.y - r, r * 2, r * 2);
    r = R * .8;                                                          // and a hot rim peeking round it
    ctx.globalAlpha = A.fuse ? .14 : .5;
    ctx.drawImage(glow(A.hot), f.x - r, f.y - r, r * 2, r * 2);
    if (!REDUCED) {
      const sp = Math.hypot(f.vx, f.vy);
      if (A.trail && sp > 120) {                                         // a light streak behind it, along its fall
        const L = Math.min(S * 2.4, sp * .2);
        ctx.save(); ctx.translate(f.x, f.y); ctx.rotate(Math.atan2(-f.vx, f.vy));
        ctx.globalAlpha = .7; ctx.drawImage(streak(A.col), -R * .62, -L, R * 1.24, L);
        ctx.globalAlpha = .85; ctx.drawImage(streak(A.hot), -R * .16, -L * .85, R * .32, L * .85);
        ctx.restore();
      }
      if (A.rays) {
        ctx.save(); ctx.translate(f.x, f.y);
        ctx.rotate(t * .45 + f.fxPh); ctx.globalAlpha = .62; r = R * 1.85 * A.rays;
        ctx.drawImage(rays(A.col, 1), -r, -r, r * 2, r * 2);
        ctx.rotate(-t * 1.05 - f.fxPh * 2); ctx.globalAlpha = .48; r = R * 1.4 * A.rays;
        ctx.drawImage(rays(A.hot, 2), -r, -r, r * 2, r * 2);
        ctx.restore();
      }
      orbit(ctx, f, A, false, t);
    }
    ctx.restore();
  }
  // over a special fruit: the near side of its twinkle ring, its arcs, its fuse
  function auraFront(ctx, f) {
    if (!live(f)) return;
    const A = AURA[f.id], t = clock();
    ctx.save(); ctx.globalCompositeOperation = "lighter";
    if (!REDUCED) orbit(ctx, f, A, true, t);
    if (A.arcs && f.fxArcs && f.fxArcs.length) {
      ctx.save(); ctx.translate(f.x, f.y); ctx.lineCap = ctx.lineJoin = "round";
      for (const a of f.fxArcs) { const kk = a.age / a.dur; if (flick(kk)) strokeBolt(ctx, a.pts, A.col, A.hot, a.w * k1(), 1 - kk * .5); }
      ctx.restore();
    }
    if (A.fuse) {
      const q = fusePos(f);
      if (q && q.vis > .02) {
        const fl = .82 + .22 * Math.sin(t * 37) + .14 * Math.sin(t * 61 + 1), r = f.size * .66 * fl;
        ctx.globalAlpha = q.vis;
        ctx.drawImage(flare("#ffb43a"), q.x - r, q.y - r, r * 2, r * 2);
        const c = r * .5; ctx.drawImage(dot("#fff2c0"), q.x - c, q.y - c, c * 2, c * 2);
      }
    }
    ctx.restore();
  }
  function orbit(ctx, f, A, front, t) {
    const n = A.orbit;
    if (!n) return;
    const R = f.size, ct = Math.cos(-.42), st = Math.sin(-.42);
    for (let i = 0; i < n; i++) {
      const th = t * 1.7 + f.fxPh + i * TAU / n, depth = Math.sin(th);
      if ((depth > 0) !== front) continue;
      const ex = Math.cos(th) * R * .68, ey = depth * R * .2, x = f.x + ex * ct - ey * st, y = f.y + ex * st + ey * ct;
      const tw = .65 + .35 * Math.sin(t * 9 + i * 2.1), r = R * (.27 + .14 * tw) * (front ? 1 : .7);
      ctx.globalAlpha = front ? 1 : .55;
      ctx.drawImage(flare(A.hot), x - r, y - r, r * 2, r * 2);
    }
  }
  // the particles: the solid ones (smoke, chunks, seeds, juice beads), then the lights
  function drawParts(ctx) {
    if (!P.length) return;
    ctx.save();
    const B = ctx.getTransform();
    for (const p of P) {
      const life = p.life - p.age;
      if (p.k === "sm") {
        const kk = p.age / p.life, r = p.r + p.grow * kk;
        ctx.globalAlpha = .3 * (1 - kk); ctx.drawImage(glow(p.col), p.x - r, p.y - r, r * 2, r * 2);
      } else if (p.k === "ch") {                          // a chunk of flesh: a little toon cube
        ctx.globalAlpha = Math.min(1, life * 4);
        const s = p.r * 1.45;
        place(ctx, B, p.x, p.y, p.rot);
        ctx.drawImage(chunkSpr(p.col), -s, -s, s * 2, s * 2);
        ctx.setTransform(B);
      } else if (p.k === "sd") {                          // a seed
        ctx.globalAlpha = Math.min(1, life * 4);
        const s = p.r * 1.7;
        place(ctx, B, p.x, p.y, p.rot);
        ctx.drawImage(seedSpr(p.col), -s, -s, s * 2, s * 2);
        ctx.setTransform(B);
      }
    }
    // juice strings: neighbouring beads of a string still close together hang on a thin filament of juice
    ctx.lineCap = "round";
    for (const st of strings) {
      const bs = st.beads;
      for (let i = 1; i < bs.length; i++) {
        const a = bs[i - 1], b = bs[i];
        if (a.age >= a.life || b.age >= b.life) continue;
        const dx = b.x - a.x, dy = b.y - a.y, d2 = dx * dx + dy * dy, reach = (a.r + b.r) * 3.4;
        if (d2 > reach * reach) continue;
        const thin = 1 - Math.sqrt(d2) / reach, lw = Math.min(a.r, b.r) * (.35 + .75 * thin);
        ctx.globalAlpha = Math.min(1, (b.life - b.age) * 3) * .9;
        ctx.strokeStyle = st.col; ctx.lineWidth = lw;
        ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
        ctx.globalAlpha *= .55; ctx.strokeStyle = "#ffffff"; ctx.lineWidth = Math.max(.5, lw * .28);
        ctx.beginPath(); ctx.moveTo(a.x - lw * .22, a.y - lw * .26); ctx.lineTo(b.x - lw * .22, b.y - lw * .26); ctx.stroke();
      }
    }
    for (const p of P) {                                 // the beads: glossy drops, a short tail behind each
      if (p.k !== "bd") continue;
      const sp = Math.hypot(p.vx, p.vy), st = Math.min(1.4, sp / 500), r = p.r * 1.1;
      ctx.globalAlpha = Math.min(1, (p.life - p.age) * 3);
      if (st > .25) { const L = r * (1 + st * 2); place(ctx, B, p.x, p.y, Math.atan2(p.vy, p.vx)); ctx.drawImage(tail(p.col), -L, -r * .8, L, r * 1.6); ctx.setTransform(B); }
      ctx.drawImage(droplet(p.col), p.x - r, p.y - r, r * 2, r * 2);
    }
    ctx.globalCompositeOperation = "lighter";
    for (const p of P) {
      if (p.k === "gl" || p.k === "em") {
        const kk = p.age / p.life, fade = kk < .12 ? kk / .12 : 1 - Math.pow((kk - .12) / .88, 1.6);
        const tw = p.k === "gl" ? .55 + .45 * Math.sin(p.age * p.tw + p.ph) : .7 + .3 * Math.sin(p.age * 23 + p.ph);
        const r = p.r * 3.2;
        ctx.globalAlpha = fade * tw;
        ctx.drawImage(dot(p.col), p.x - r, p.y - r, r * 2, r * 2);
        if (p.k === "gl" && p.r > 2.1 && tw > .82) { const fr = p.r * 6.5; ctx.drawImage(flare(p.col), p.x - fr, p.y - fr, fr * 2, fr * 2); }
      } else if (p.k === "sp") {
        ctx.globalAlpha = 1 - p.age / p.life; ctx.strokeStyle = p.col; ctx.lineWidth = p.r; ctx.lineCap = "round";
        ctx.beginPath(); ctx.moveTo(p.x - p.vx * .025, p.y - p.vy * .025); ctx.lineTo(p.x, p.y); ctx.stroke();
      } else if (p.k === "sn") {
        const kk = p.age / p.life, r = p.r * 4;
        ctx.globalAlpha = (1 - kk) * (.6 + .4 * Math.sin(p.age * 12 + p.ph));
        place(ctx, B, p.x, p.y, p.rot);
        ctx.drawImage(snow(), -r, -r, r * 2, r * 2);
        ctx.setTransform(B);
      } else if (p.k === "st") {                          // a star flare flying out of a burst
        const kk = p.age / p.life, r = p.r * (1 - kk * .5);
        ctx.globalAlpha = (1 - kk) * (.7 + .3 * Math.sin(p.age * 20 + p.ph));
        place(ctx, B, p.x, p.y, p.rot);
        ctx.drawImage(flare(p.col), -r, -r, r * 2, r * 2);
        ctx.setTransform(B);
      }
    }
    ctx.restore();
  }
  // over everything but the HUD: burst flashes and lightning
  function drawTop(ctx) {
    if (!flashes.length && !bolts.length) return;
    ctx.save(); ctx.globalCompositeOperation = "lighter"; ctx.lineCap = ctx.lineJoin = "round";
    const B = ctx.getTransform();
    for (const fl of flashes) {
      const kk = fl.age / fl.dur, s = fl.size * (1 - fl.grow + fl.grow * (1 - Math.pow(1 - kk, 3)));
      ctx.globalAlpha = fl.a0 * Math.pow(1 - kk, 1.4);
      place(ctx, B, fl.x, fl.y, fl.rot + fl.vr * fl.age);
      ctx.drawImage(fl.spr, -s / 2, -s / 2, s, s);
    }
    ctx.setTransform(B);
    for (const b of bolts) { const kk = b.age / b.dur; if (flick(kk)) strokeBolt(ctx, b.pts, b.col, b.hot, b.w * k1(), 1); }
    ctx.restore();
  }

  /* ------------------------------------------------------------------ stains on the wall */
  const STAIN = { splat: [], drip: [], meta: {} }, wet = [], WET_MAX = 40;
  function loadStains() {
    for (const kind of ["splat", "drip"]) for (let i = 1; i <= 4; i++) {
      const im = new Image(); im.src = `assets/fx/stain_${kind}${i}.webp`; im.dataset.name = kind + i; STAIN[kind].push(im);
    }
    return fetch("assets/fx/stains.json").then(r => r.json()).then(m => { STAIN.meta = m; }).catch(() => {});
  }
  const ready = ims => ims.filter(im => im.complete && im.naturalWidth);
  // what a stain multiplies the wood by: the juice, deepened (wet juice soaks in darker), never quite white
  const wetMul = col => { const c = rgbOf(col).map(v => Math.round(255 * Math.pow(v / 255, 1.4) * .76)); return `rgb(${c[0]},${c[1]},${c[2]})`; };
  function ink(im, col) {                                    // the density tile, tinted (per sprite and colour)
    return once(`ink:${im.dataset.name}:${col}`, () => {
      const w = im.naturalWidth / 3, h = im.naturalHeight, [c, x] = canvas(w, h);
      x.drawImage(im, 0, 0, w, h, 0, 0, w, h);
      x.globalCompositeOperation = "source-in"; x.fillStyle = wetMul(col); x.fillRect(0, 0, w, h);
      return c;
    });
  }
  // The light on one wet stain, built in screen space whichever way the stain is turned: its density drawn turned
  // and scaled; what is left of it once a copy nudged away from the light is cut out is the rim facing the light;
  // the same the other way round, darkened, is the rim in shadow. Plus a faint sheen and the render's own glints.
  // One canvas, gloss on the left half, shade on the right.
  function wetLight(im, dw, dh, rot) {
    const sc = Math.min(1.5, DPR), w = im.naturalWidth / 3, h = im.naturalHeight, cs = Math.cos(rot), sn = Math.sin(rot);
    const bw = Math.abs(dw * cs) + Math.abs(dh * sn) + 8, bh = Math.abs(dw * sn) + Math.abs(dh * cs) + 8;
    const cw = Math.ceil(bw * sc), ch = Math.ceil(bh * sc), [c, x] = canvas(cw * 2, ch);
    const d = Math.max(.9, Math.min(2.4, dw * .008)) * sc;
    const put = (src, ox, dx, dy) => {
      x.setTransform(cs, sn, -sn, cs, ox + cw / 2 + dx, ch / 2 + dy);
      x.drawImage(im, src * w, 0, w, h, -dw * sc / 2, -dh * sc / 2, dw * sc, dh * sc);
    };
    x.globalAlpha = .75; put(2, 0, 0, 0);                                         // where the juice stands thick...
    x.globalCompositeOperation = "destination-out"; x.globalAlpha = 1; put(2, 0, d, d * 1.15);   // ...less a copy nudged off the light
    x.globalCompositeOperation = "source-over"; x.globalAlpha = .05; put(2, 0, 0, 0);            // a faint sheen where it pools
    x.globalCompositeOperation = "lighter"; x.globalAlpha = .45; put(1, 0, 0, 0);                // the render's own glints
    x.globalCompositeOperation = "source-over"; x.globalAlpha = 1; put(2, cw, 0, 0);
    x.globalCompositeOperation = "destination-out"; put(2, cw, -d * 1.25, -d * 1.4);
    x.setTransform(1, 0, 0, 1, 0, 0);
    x.globalCompositeOperation = "source-atop"; x.fillStyle = "rgb(30,12,4)"; x.fillRect(cw, 0, cw, ch);
    return { c, cw, ch, sc };
  }
  function trimWet() {                                       // too many wet at once: the oldest dries off quickly
    if (wet.length < WET_MAX) return;
    const s = wet.find(o => !o.fast && !(o.drip && o.drip.k < 1));
    if (s) { s.fast = true; s.t = Math.max(s.t, s.dur - .25); }
  }
  // a splat of juice hits the wall where a fruit was cut, and a run or two creeps down from it
  function stain(x, y, col, power = 1) {
    const ims = ready(STAIN.splat);
    if (!ims.length) return;
    const im = pick(ims), w = im.naturalWidth / 3, h = im.naturalHeight;
    const R = S * (.55 + Math.random() * .35) * power, k = R * 2 / Math.max(w, h), dw = w * k, dh = h * k, rot = rnd(0, TAU);
    gs.save(); gs.translate(x, y); gs.rotate(rot); gs.globalAlpha = .95;
    gs.drawImage(ink(im, col), -dw / 2, -dh / 2, dw, dh);
    gs.restore();
    if (!REDUCED) { trimWet(); wet.push({ L: wetLight(im, dw, dh, rot), x, y, t: 0, dur: rnd(2.8, 4) }); }
    const drips = ready(STAIN.drip);
    for (let j = 0, n = 1 + Math.floor(Math.random() * 2.6); j < n && drips.length; j++) {
      const di = pick(drips), wc = R * (.2 + Math.random() * .18) * (power > 1 ? 1.25 : 1);
      startDrip(x + (Math.random() - .5) * R * .9, y + R * (.05 + Math.random() * .25), col, wc, di);
    }
  }
  function startDrip(x, y, col, wc, im) {
    const w = im.naturalWidth / 3, h = im.naturalHeight, dh = wc * h / w * rnd(.8, 1.4);
    const d = { im, x, y, w: wc, h: dh, col, k: 0, t: 0, dur: rnd(.9, 2.2), painted: Math.round(y * DPR), name: im.dataset.name };
    if (REDUCED) { d.k = 1; paintDrip(d); return; }
    trimWet();
    wet.push({ drip: d, L: wetLight(im, wc, dh, 0), x, y: y + dh / 2, t: 0, dur: d.dur + rnd(1.6, 2.6) });
  }
  // paint the rows a drip has newly run down (whole device rows, so the bands meet without a seam)
  function paintDrip(d) {
    const Y0 = d.y * DPR, Hd = d.h * DPR, r1 = Math.round(Y0 + Hd * d.k);
    if (r1 <= d.painted) return;
    const src = ink(d.im, d.col), sh = src.height;
    const s0 = Math.max(0, Math.min(sh, (d.painted - Y0) / Hd * sh)), s1 = Math.max(0, Math.min(sh, (r1 - Y0) / Hd * sh));
    if (s1 - s0 > .01) {
      gs.save(); gs.setTransform(1, 0, 0, 1, 0, 0); gs.globalAlpha = .9;
      gs.drawImage(src, 0, s0, src.width, s1 - s0, (d.x - d.w / 2) * DPR, d.painted, d.w * DPR, r1 - d.painted);
      gs.restore();
    }
    d.painted = r1;
  }
  // a stray drop lands on the wall: a small stain stretched along its flight, with a tail
  function dropStain(p) {
    const sp = Math.hypot(p.vx, p.vy), a = Math.atan2(p.vy, p.vx), el = 1 + Math.min(1.6, sp / 900), r = Math.max(.8, p.r * .9);
    gs.save(); gs.translate(p.x, p.y); gs.rotate(a); gs.globalAlpha = .85; gs.fillStyle = wetMul(p.col);
    gs.beginPath(); gs.ellipse(0, 0, r * el, r, 0, 0, TAU); gs.fill();
    if (el > 1.5) { gs.beginPath(); gs.ellipse(r * el + r * .9, 0, r * .45, r * .32, 0, 0, TAU); gs.fill(); }
    gs.restore();
    if (!REDUCED && wet.length < WET_MAX * 3) wet.push({ dot: true, x: p.x, y: p.y, r: r * (1 + (el - 1) * .4), t: 0, dur: rnd(1.2, 2.2) });
  }
  // the wet light, under the fruit: each stain's sheen and rims, fading as it dries; a bead leading each running drip
  function drawWet(ctx) {
    if (!wet.length) return;
    ctx.save();
    for (const s of wet) {
      const u = s.t < .35 ? 1 : Math.max(0, 1 - (s.t - .35) / Math.max(.1, s.dur - .35)), e = u * u * (3 - 2 * u);
      if (e <= .01 && !(s.drip && s.drip.k < 1)) continue;
      if (s.dot) { const r = s.r * 1.6; ctx.globalAlpha = e; ctx.drawImage(wetDot(), s.x - r, s.y - r, r * 2, r * 2); continue; }
      const L = s.L, cw = L.cw / L.sc, chh = L.ch / L.sc;
      if (s.drip) {
        const d = s.drip, top = d.y - 4, rows = Math.max(1, Math.min(L.ch, Math.round((4 + d.h * d.k) * L.sc))), hh = rows / L.sc;
        ctx.globalAlpha = .5 * e; ctx.drawImage(L.c, L.cw, 0, L.cw, rows, d.x - cw / 2, top, cw, hh);
        ctx.globalAlpha = .95 * e; ctx.drawImage(L.c, 0, 0, L.cw, rows, d.x - cw / 2, top, cw, hh);
        if (d.k < 1) {                                   // the bead at its head, following the strand
          const m = STAIN.meta[d.name], row = Math.min(63, Math.floor(d.k * 64)), fx = m ? m.cx[row] : .5, fw = m ? Math.max(.12, m.w[row]) : .3;
          const r = Math.max(1.4, fw * d.w * .62), bx = d.x - d.w / 2 + fx * d.w, by = d.y + d.h * d.k - r * .7;
          ctx.globalAlpha = Math.min(1, (1 - d.k) * 10) * .92;
          ctx.drawImage(droplet(shade(d.col, -.22)), bx - r, by - r, r * 2, r * 2.3);
        }
        continue;
      }
      ctx.globalAlpha = .5 * e; ctx.drawImage(L.c, L.cw, 0, L.cw, L.ch, s.x - cw / 2, s.y - chh / 2, cw, chh);
      ctx.globalAlpha = .95 * e; ctx.drawImage(L.c, 0, 0, L.cw, L.ch, s.x - cw / 2, s.y - chh / 2, cw, chh);
    }
    ctx.restore();
  }

  /* ------------------------------------------------------------------ juice in flight (game.js's world.drops, mists) */
  function drawDrops(ctx, drops) {
    if (!drops.length) return;
    ctx.save();
    const B = ctx.getTransform();
    ctx.lineCap = "round";
    for (const d of drops) {
      const a = Math.min(1, d.life * 3), sp = Math.hypot(d.vx, d.vy);
      if (!d.juice) {                                    // the bomb's embers and bits of shell: streaks
        const st = Math.min(.035, 14 / Math.max(1, sp));
        ctx.globalAlpha = a; ctx.strokeStyle = d.col; ctx.lineWidth = d.r * 2;
        ctx.beginPath(); ctx.moveTo(d.x - d.vx * st, d.y - d.vy * st); ctx.lineTo(d.x, d.y); ctx.stroke();
        continue;
      }
      const st = Math.min(2.6, sp / 380), r = d.r * (d.spray ? .9 : 1.1);
      ctx.globalAlpha = a * (d.spray ? .6 : .95);
      if (st > .25) { const L = r * (1 + st * 2.2); place(ctx, B, d.x, d.y, Math.atan2(d.vy, d.vx)); ctx.drawImage(tail(d.col), -L, -r * .8, L, r * 1.6); ctx.setTransform(B); }
      ctx.drawImage(droplet(d.col), d.x - r, d.y - r, r * 2, r * 2);
    }
    ctx.restore();
  }
  function drawMists(ctx, mists) {
    if (!mists.length) return;
    ctx.save();
    for (const m of mists) {
      const kk = m.age / m.dur, r = m.r0 + (m.r1 - m.r0) * (1 - (1 - kk) ** 2);
      ctx.globalAlpha = (1 - kk) * .42;
      ctx.drawImage(glow(m.col), m.x - r, m.y - r, r * 2, r * 2);
    }
    ctx.restore();
  }

  /* ------------------------------------------------------------------ events */
  // a fruit is cut (slice in game.js): juice in strings of beads, chunks, seeds, sparkles; a special one goes off
  function cut(f, dx, dy) {
    if (REDUCED) return;
    const id = f.id, A = AURA[id], m = (META && META.fruit[SPRITE(id)]) || {}, col = m.juice || "#ffffff", R = f.size, k = k1();
    const dark = shade(col, -.38), big = id === "JM" ? 2 : 1, n0 = id === "BOMB" ? 0 : 1;
    if (n0) for (const s of [1, -1]) {                    // a string of beads thrown out either side of the cut
      const str = { col, beads: [] };
      strings.push(str);
      const px = dy * s, py = -dx * s, along = rnd(-.35, .6);
      let ux = px + dx * along, uy = py + dy * along - .45;
      const l = Math.hypot(ux, uy) || 1; ux /= l; uy /= l;
      const v0 = rnd(420, 700) * k * big, n = 6 + Math.floor(Math.random() * 5) * big, r0 = rnd(3.2, 5.4) * k * (R / S + .3);
      for (let i = 0; i < n; i++) {
        const v = v0 * (1 - i * .075), a = rnd(-.05, .05), c = Math.cos(a), sn = Math.sin(a);
        str.beads.push(add({ k: "bd", x: f.x + rnd(-3, 3), y: f.y + rnd(-3, 3), vx: (ux * c - uy * sn) * v + f.vx * .3, vy: (ux * sn + uy * c) * v + f.vy * .3,
              col, dark, r: Math.max(1.2, r0 * (1 - i * .07)), life: rnd(.8, 1.2), drag: .45, grav: 1500 * (H / 786) }));
      }
    }
    const flesh = FLESH[id];
    if (flesh) for (let i = 0, n = (3 + Math.floor(Math.random() * 4)) * big; i < n; i++) {   // chunks of flesh
      const a = -Math.PI / 2 + rnd(-1.6, 1.6), v = rnd(180, 470) * k;
      add({ k: "ch", x: f.x + rnd(-R * .15, R * .15), y: f.y + rnd(-R * .15, R * .15), vx: Math.cos(a) * v + f.vx * .35, vy: Math.sin(a) * v + f.vy * .35,
            col: flesh, r: R * rnd(.035, .065), life: rnd(.9, 1.4), drag: .3, grav: 1700 * (H / 786), rot: rnd(0, TAU), vr: rnd(-12, 12) });
    }
    if (SEEDS[id]) for (let i = 0, n = 3 + Math.floor(Math.random() * 3); i < n; i++) {
      const a = rnd(0, TAU), v = rnd(140, 380) * k;
      add({ k: "sd", x: f.x, y: f.y, vx: Math.cos(a) * v + f.vx * .35, vy: Math.sin(a) * v + f.vy * .35 - 120 * k, col: SEEDS[id],
            r: R * rnd(.018, .026), life: rnd(.8, 1.2), drag: .3, grav: 1700 * (H / 786), rot: rnd(0, TAU), vr: rnd(-14, 14) });
    }
    for (let i = 0; i < 5; i++) {                         // a few sparkles at the cut
      const a = rnd(0, TAU), v = rnd(60, 300) * k;
      glitter(f.x, f.y, Math.cos(a) * v + f.vx * .2, Math.sin(a) * v + f.vy * .2, A ? A.glit : "#ffe7a0", rnd(1.1, 2.4) * k, rnd(.4, .85));
    }
    if (A) burst(f.x, f.y, A, id, f);
  }
  function burst(x, y, A, id, f) {
    const k = k1(), vx = f ? f.vx * .2 : 0, vy = f ? f.vy * .2 : 0;
    flash(x, y, flare(A.hot), S * 3.4, .42, 1, rnd(0, TAU), rnd(-1, 1));
    flash(x, y, rays(A.col, 1), S * 4.2, .6, .85, rnd(0, TAU), rnd(-1.2, 1.2), .6);
    flash(x, y, glow(A.hot), S * 2.2, .26, .9);
    for (let i = 0; i < 38; i++) {
      const a = rnd(0, TAU), v = rnd(120, 720) * k;
      glitter(x, y, Math.cos(a) * v + vx, Math.sin(a) * v + vy - 80 * k, Math.random() < .5 ? A.glit : A.hot, rnd(1.4, 3.4) * k, rnd(.6, 1.3), { grav: 420 });
    }
    if (A.arcs) for (let i = 0; i < 6; i++) {             // lightning out of the peach
      const a = rnd(0, TAU), L = S * rnd(.9, 1.8), pts = [[x, y]];
      jag(x, y, x + Math.cos(a) * L, y + Math.sin(a) * L, L * .45, 5, pts);
      bolts.push({ pts, col: A.col, hot: A.hot, age: 0, dur: rnd(.18, .32), w: rnd(1, 1.6) });
    }
    if (A.frost) for (let i = 0; i < 24; i++) {           // a puff of ice
      const a = rnd(0, TAU), v = rnd(80, 420) * k;
      add({ k: "sn", x, y, vx: Math.cos(a) * v, vy: Math.sin(a) * v, r: rnd(2.2, 4.2) * k, life: rnd(.7, 1.3), drag: 1.6, grav: 160, rot: rnd(0, TAU), vr: rnd(-4, 4), ph: rnd(0, TAU) });
    }
    if (id === "SC" || id === "JM") for (let i = 0, n = id === "JM" ? 18 : 9; i < n; i++) {   // stars flying out
      const a = rnd(0, TAU), v = rnd(200, 600) * k;
      add({ k: "st", x, y, vx: Math.cos(a) * v, vy: Math.sin(a) * v - 60 * k, col: A.hot, r: rnd(10, 20) * k, life: rnd(.5, .9), drag: 2.2, grav: 300, rot: rnd(0, TAU), vr: rnd(-3, 3), ph: rnd(0, TAU) });
    }
  }
  // the bomb goes off: a white-orange flare and rays over the fireball, sparks everywhere
  function boom(x, y) {
    if (REDUCED) return;
    const k = k1();
    flash(x, y, flare("#ffd27a"), S * 6.5, .55, 1, rnd(0, TAU), .4);
    flash(x, y, rays("#ff7a12", 1), S * 7.5, .8, .9, rnd(0, TAU), .8, .7);
    for (let i = 0; i < 30; i++) {
      const a = rnd(0, TAU), v = rnd(400, 1200) * k;
      add({ k: "sp", x, y, vx: Math.cos(a) * v, vy: Math.sin(a) * v - 200 * k, col: pick(["#fff6c8", "#ffd27a", "#ff7a12"]), r: rnd(1.4, 3) * k, life: rnd(.3, .7), drag: 1.2, grav: 1100 });
    }
  }
  // a special fruit is picked out (the star fruit's chime): a quick flare and a few sparkles
  function ping(f) {
    if (REDUCED || !f) return;
    const A = AURA[f.id] || AURA.SC;
    flash(f.x, f.y, flare(A.hot), f.size * 2.4, .5, .9, rnd(0, TAU), rnd(-1, 1));
    for (let i = 0; i < 10; i++) { const a = rnd(0, TAU), v = rnd(80, 260) * k1(); glitter(f.x, f.y, Math.cos(a) * v + f.vx * .5, Math.sin(a) * v + f.vy * .5, A.glit, rnd(1.2, 2.6) * k1(), rnd(.5, 1)); }
  }
  // a pop of text (a win, a multiplier) throws a little glitter
  function sparkle(x, y, col, n = 10) {
    if (REDUCED) return;
    for (let i = 0; i < n; i++) { const a = rnd(0, TAU), v = rnd(60, 280) * k1(); glitter(x, y, Math.cos(a) * v, Math.sin(a) * v - 40, col, rnd(1, 2.4) * k1(), rnd(.45, .9)); }
  }
  // the blade's head sheds glitter while it moves (real time, so a pause never piles it up)
  function bladeHead(ctx, b, hx, hy) {
    const t = clock(), dt = Math.min(.05, t - (b.fxT || t)), k = k1();
    b.fxT = t;
    if (!REDUCED) {
      b.fxAcc = (b.fxAcc || 0) + dt * 150;
      while (b.fxAcc >= 1) {
        b.fxAcc--;
        const a = rnd(0, TAU), v = rnd(20, 150) * k;
        glitter(hx + rnd(-4, 4), hy + rnd(-4, 4), Math.cos(a) * v, Math.sin(a) * v, pick(["#ffffff", b.glow, "#ffe9a8"]), rnd(.9, 2.2) * k, rnd(.25, .6), { drag: 3, grav: 80 });
      }
    }
    const r = b.w * 3.2;
    ctx.drawImage(flare(b.glow), hx - r, hy - r, r * 2, r * 2);
  }
  // the four-point glint of a cut (game.js draws the hot line; this is its star)
  function glint(ctx, x, y, r, col, ang) {
    const B = ctx.getTransform();
    place(ctx, B, x, y, ang);
    ctx.drawImage(flare(col), -r, -r, r * 2, r * 2);
    ctx.setTransform(B);
  }
  // a soft glow behind a pop of text
  function textGlow(ctx, col, w, h) { ctx.drawImage(glow(col), -w / 2, -h / 2, w, h); }
  function setFrenzy(mode) { room.mode = mode; room.nextBolt = .6; }
  // build the sprites while the game loads, so the first special fruit never hitches
  function warm() {
    for (const A of Object.values(AURA)) { glow(A.col); glow(A.hot); flare(A.hot); dot(A.glit); dot(A.hot); if (A.rays) { rays(A.col, 1); rays(A.hot, 2); } if (A.trail) { streak(A.col); streak(A.hot); } }
    for (const c of ["#ffd27a", "#ffb35c", "#ffe2a8", "#ffae42", "#ff4fa8", "#a35cff"]) bokeh(c);
    for (const c of ["#ffffff", "#7fd4ff", "#ffb347", "#ffe9a8", "#ffe7a0", "#ffe6b8", "#ffd84a"]) { dot(c); flare(c); }
    flare("#ffb43a"); flare("#ffd27a"); rays("#ff7a12", 1); glow("#5d544c"); snow(); wetDot();
    if (META) for (const [id, m] of Object.entries(META.fruit)) {     // every juice's drops, chunks, seeds
      if (m.juice) { droplet(m.juice); tail(m.juice); droplet(shade(m.juice, -.22)); glow(m.juice); }
      if (FLESH[id]) chunkSpr(FLESH[id]);
      if (SEEDS[id]) seedSpr(SEEDS[id]);
    }
  }
  return { update, drawRoom, auraBack, auraFront, drawParts, drawTop, cut, burst, boom, ping, sparkle, bladeHead, glint, textGlow,
           setFrenzy, warm, loadStains, stain, dropStain, drawWet, drawDrops, drawMists, AURA, sprite: { glow, dot, flare, rays, droplet } };
})();
