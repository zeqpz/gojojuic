/* Juice Dojo win screen - zeqpz/orleans' totalWinScreen, ported (structure, timing and motion kept: the figure
 * counting up on its backing, the tier headline slamming in at 15x / 40x / 100x with its sheen, flash, knock and
 * sparks, the HUD bar dropping away, physics icons raining behind) and reskinned: Fruit Ninja's lettering (the
 * Gang of Three typeface, fnHTML in game.js) for the headlines and the figure, a paper backing, our 3D fruit raining.
 * Needs game.js's SHEETS / META / drawFruit, fmt, bet(), RGS, SFX, T. */
"use strict";

// figures in the lettering: gold on the win screen and the frenzy intro, white painted on the wall
function numeralRow(text) { return fnHTML(text, "gold num"); }
function numeralRowWhite(text) { return fnHTML(text, "white num"); }

const restyle = el => void el.offsetWidth;

// A burst of sparks and juice flecks flying off a point (orleans' sparkBurst)
function sparkBurst(host, { x = .5, y = .5, n = 18, colors = ["#ffffff", "#FFE39A", "#ff7a12"], reach = 1, size = 1 } = {}) {
  if (REDUCED || !host) return;
  const box = document.createElement("div");
  box.className = "sparks";
  box.setAttribute("aria-hidden", "true");
  box.style.left = (x * 100).toFixed(1) + "%";
  box.style.top = (y * 100).toFixed(1) + "%";
  for (let i = 0; i < n; i++) {
    const s = document.createElement("i");
    const a = Math.random() * Math.PI * 2, d = (70 + Math.random() * 170) * reach;
    s.className = Math.random() < .45 ? "streak" : "fleck";
    s.style.setProperty("--dx", (Math.cos(a) * d).toFixed(1) + "px");
    s.style.setProperty("--dy", (Math.sin(a) * d * .75 - 18 * reach).toFixed(1) + "px");
    s.style.setProperty("--fall", ((24 + Math.random() * 70) * reach).toFixed(1) + "px");
    s.style.setProperty("--rot", (a * 180 / Math.PI).toFixed(0) + "deg");
    s.style.setProperty("--sz", ((.65 + Math.random() * .8) * size).toFixed(2));
    s.style.setProperty("--dur", (.65 + Math.random() * .6).toFixed(2) + "s");
    s.style.color = colors[i % colors.length];
    box.append(s);
  }
  host.append(box);
  setTimeout(() => box.remove(), 1500);
}

// A headline lands: slam, neon flicker on, a band of light across the lettering, sparks, a knock - harder each tier.
// lvl: 0 BIG, 1 MEGA, 2 EPIC, 3 TOTAL WIN
const HEAD_FX = [
  { scale: 1,    sparks: 16, reach: .95, knock: .7,  flash: 0,   glow: "255, 170, 40",  colors: ["#ffffff", "#FFE39A", "#ff9a12", "#ff3b4e"] },
  { scale: 1.07, sparks: 26, reach: 1.15, knock: 1,  flash: .28, glow: "255, 70, 120",  colors: ["#ffd6ec", "#ff4f8f", "#ffffff", "#FFE39A"] },
  { scale: 1.14, sparks: 40, reach: 1.4, knock: 1.5, flash: .42, glow: "150, 110, 255", colors: ["#d8ccff", "#8a6cff", "#ffffff", "#FFE39A"] },
  { scale: 1.08, sparks: 34, reach: 1.3, knock: 1.1, flash: .3,  glow: "245, 197, 24",  colors: ["#FFE58A", "#F5C518", "#ffffff", "#ff9a12"] },
];
function headFx(wrap, head, lvl) {
  const f = HEAD_FX[lvl] || HEAD_FX[0];
  head.style.setProperty("--lvl", lvl);
  head.style.setProperty("--hs", f.scale);
  head.style.setProperty("--hglow", f.glow);
  const art = head.querySelector("img.twlogo.on"), sheen = head.querySelector(".twsheen");
  if (art && sheen) sheen.style.setProperty("--art", `url("${art.getAttribute("src")}")`);
  const word = head.querySelector(".twlogo.on.fnt");   // the lettering's own sheen sweeps again as it lands
  if (word) { word.classList.remove("shine"); restyle(word); word.classList.add("shine"); }
  if (REDUCED) return;
  sparkBurst(head, { n: f.sparks, reach: f.reach, colors: f.colors, size: 1 + lvl * .12 });
  const twin = wrap.querySelector(".twin"), flash = wrap.querySelector(".twflash");
  twin.style.setProperty("--knock", f.knock);
  twin.classList.remove("knock"); restyle(twin); twin.classList.add("knock");
  if (flash && f.flash) {
    flash.style.setProperty("--flash", f.flash);
    flash.classList.remove("go"); restyle(flash); flash.classList.add("go");
  }
}

// A wander that never repeats (orleans' hoverWin): writes --p* (the backing) and --t* (the words, a beat behind)
function hoverWin(host, reach, lag) {
  if (REDUCED || !host) return;
  const unit = reach.unit || "px", pace = reach.pace || 1;
  const chans = [["x", 1.3], ["y", 1.05], ["r", 1.6], ["s", 1.9]].map(([k, step]) => ({
    k, amp: reach[k] || 0, step: step * pace * (.85 + Math.random() * .3), stops: [0],
  }));
  const stop = (c, i) => { while (c.stops.length <= i) c.stops.push(Math.random() * 2 - 1); return c.stops[i]; };
  const at = t => {
    const o = {};
    for (const c of chans) {
      if (t <= 0 || !c.amp) { o[c.k] = 0; continue; }
      const u = t / c.step, i = Math.floor(u), f = u - i;
      const p0 = i > 0 ? stop(c, i - 1) : 0, p1 = stop(c, i), p2 = stop(c, i + 1), p3 = stop(c, i + 2);
      o[c.k] = c.amp * .5 * (2 * p1 + (p2 - p0) * f + (2 * p0 - 5 * p1 + 4 * p2 - p3) * f * f + (3 * p1 - p0 - 3 * p2 + p3) * f * f * f);
    }
    return o;
  };
  const put = (tag, v) => {
    host.style.setProperty(`--${tag}x`, v.x.toFixed(2) + unit);
    host.style.setProperty(`--${tag}y`, v.y.toFixed(2) + unit);
    host.style.setProperty(`--${tag}r`, v.r.toFixed(3) + "deg");
    host.style.setProperty(`--${tag}s`, (1 + v.s).toFixed(4));
  };
  const t0 = performance.now();
  const frame = now => {
    if (!host.isConnected) return;
    const t = (now - t0) / 1000;
    put("p", at(t)); put("t", at(t - lag));
    requestAnimationFrame(frame);
  };
  requestAnimationFrame(frame);
}

// Fruit raining behind the figure: orleans' physics toy (gravity, air, spin, round bodies bouncing off each
// other, walls at the sides, open at the bottom), drawn from our 3D fruit sheets - each body tumbles through
// its own frames.
const RAIN_KINDS = ["H1", "H2", "H3", "H4", "L1", "L2", "L3", "L4", "SC", "PW2", "PW3", "PW5", "FRZ"];
function startIconRain(host) {
  if (REDUCED) return () => {};
  const layer = document.createElement("canvas");
  layer.className = "iconrain";
  host.prepend(layer);
  const ctx = layer.getContext("2d");
  const GRAVITY = 1250, DRAG_X = 0.5, DRAG_Y = 1.1, BOUNCE = 0.62, SPIN_DRAG = 0.6, SPIN_KICK = 0.9;
  const PER_SEC = 36, CROWD = 40, MAX = 160;
  const bodies = [];
  let stopped = false, spawnTimer = null, raf = 0, last = performance.now();
  const width = () => innerWidth, height = () => innerHeight;
  const across = () => Math.max(0.6, width() / 1000);
  const grow = Math.min(1, Math.max(0.55, width() / 1000));
  const spawn = (above = 0) => {
    if (stopped || bodies.length >= MAX) return;
    const size = (48 + Math.random() * 62) * grow, r = size * 0.38;
    bodies.push({
      id: RAIN_KINDS[Math.floor(Math.random() * RAIN_KINDS.length)], size, r, m: r * r,
      k: 1.7 - 1.15 * (size / grow - 48) / 62,
      x: r + Math.random() * Math.max(1, width() - 2 * r), y: -size - Math.random() * above,
      vx: (Math.random() * 2 - 1) * 220, vy: -120 + Math.random() * 420,
      a: Math.random() * 6.28, va: (Math.random() * 2 - 1) * 4.5, spin: Math.random() * 7, vs: (Math.random() < .5 ? -1 : 1) * (2 + Math.random() * 4),
    });
  };
  const tick = now => {
    const dt = Math.min(1 / 30, (now - last) / 1000);
    last = now;
    const w = width(), h = height();
    for (const b of bodies) {
      b.vy += GRAVITY * dt;
      b.vx -= b.vx * DRAG_X * b.k * dt; b.vy -= b.vy * DRAG_Y * b.k * dt;
      b.va -= b.va * SPIN_DRAG * dt;
      b.x += b.vx * dt; b.y += b.vy * dt; b.a += b.va * dt; b.spin += b.vs * dt;
      if (b.x < b.r) { b.x = b.r; b.vx = Math.abs(b.vx) * BOUNCE; }
      else if (b.x > w - b.r) { b.x = w - b.r; b.vx = -Math.abs(b.vx) * BOUNCE; }
    }
    for (let i = 0; i < bodies.length; i++) {
      const p = bodies[i];
      for (let j = i + 1; j < bodies.length; j++) {
        const q = bodies[j];
        const dx = q.x - p.x, dy = q.y - p.y, reach = p.r + q.r, d2 = dx * dx + dy * dy;
        if (d2 >= reach * reach || d2 === 0) continue;
        const d = Math.sqrt(d2), nx = dx / d, ny = dy / d;
        const ip = 1 / p.m, iq = 1 / q.m, share = (reach - d) / (ip + iq);
        p.x -= nx * share * ip; p.y -= ny * share * ip;
        q.x += nx * share * iq; q.y += ny * share * iq;
        const rvx = q.vx - p.vx, rvy = q.vy - p.vy, vn = rvx * nx + rvy * ny;
        if (vn >= 0) continue;
        const jn = -(1 + BOUNCE) * vn / (ip + iq);
        p.vx -= jn * nx * ip; p.vy -= jn * ny * ip;
        q.vx += jn * nx * iq; q.vy += jn * ny * iq;
        const vt = -rvx * ny + rvy * nx;
        p.va -= vt * SPIN_KICK / 60; q.va += vt * SPIN_KICK / 60;
      }
    }
    for (let i = bodies.length - 1; i >= 0; i--) if (bodies[i].y - bodies[i].size > h) bodies.splice(i, 1);
    const dpr = Math.min(2, devicePixelRatio || 1);
    const cw = Math.round(w * dpr), ch = Math.round(h * dpr);
    if (layer.width !== cw || layer.height !== ch) { layer.width = cw; layer.height = ch; }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    for (const b of bodies) {   // soft shadows first, so none lies across a fruit
      ctx.globalAlpha = .28; ctx.fillStyle = "#140902";
      ctx.beginPath(); ctx.ellipse(b.x + b.size * .06, b.y + b.size * .12, b.size * .36, b.size * .32, 0, 0, Math.PI * 2); ctx.fill();
    }
    ctx.globalAlpha = 1;
    for (const b of bodies) drawFruit(ctx, b.id, false, b.spin, b.x, b.y, b.size, b.a);
    raf = requestAnimationFrame(tick);
  };
  const crowd = Math.round((0.7 + Math.random() * 0.6) * CROWD * across());
  for (let i = 0; i < crowd; i++) spawn(700);
  const stream = () => { spawn(); spawnTimer = setTimeout(stream, (0.4 + Math.random() * 1.2) * 1000 / (PER_SEC * across())); };
  spawnTimer = setTimeout(stream, 200);
  raf = requestAnimationFrame(tick);
  return () => {
    stopped = true;
    clearTimeout(spawnTimer);
    layer.classList.add("done");
    setTimeout(() => { cancelAnimationFrame(raf); layer.remove(); }, 400);
  };
}

// The HUD bar drops off the screen while a win screen is up, and springs back when it goes (orleans)
function hudAway() {
  const bar = document.querySelector(".bottom");
  if (REDUCED || !bar || bar.classList.contains("away")) return;
  bar.classList.remove("back");
  const fit = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--fit")) || 1;
  const drop = (innerHeight - bar.getBoundingClientRect().top) / fit + 40;
  bar.style.setProperty("--hud-drop", drop.toFixed(0) + "px");
  bar.classList.add("away");
}
function hudBack() {
  const bar = document.querySelector(".bottom");
  if (!bar || !bar.classList.contains("away")) return;
  bar.classList.remove("away");
  bar.classList.add("back");
  bar.addEventListener("animationend", () => bar.classList.remove("back"), { once: true });
}

// The marks the headline climbs through, in multiples of the bet
// (art is the headline's id; fn its colour in the lettering)
const WIN_TIERS = [
  { at: 15,  art: "win/big_win.webp",  label: "Big win",  fn: "gold",   rate: 1 },
  { at: 40,  art: "win/mega_win.webp", label: "Mega win", fn: "pink",   rate: 1.12 },
  { at: 100, art: "win/epic_win.webp", label: "Epic win", fn: "violet", rate: 1.25 },
];
const TW_HEADS = [...WIN_TIERS.map(t => [t.art, t.label, t.fn]), ["win/total_win.webp", "Total win", "gold"]];
const OVER_BOARD_AT = 10;   // a spin has to pay more than this many times the bet for the screen

function totalWinScreen(amount, { total = true } = {}) {
  return new Promise(resolve => {
    const wrap = document.createElement("div");
    wrap.className = "totalwin";
    wrap.setAttribute("role", "dialog");
    wrap.setAttribute("aria-label", T("Win") + " " + fmt(amount));
    wrap.innerHTML =
      `<i class="twflash" aria-hidden="true"></i>` +
      `<div class="twin">` +
        `<div class="twhead blank">` +
          TW_HEADS.map(([art, label, fn]) => fnHTML(T(label), `${fn} shine twlogo`, `data-art="${art}" aria-hidden="true"`)).join("") +
          `<i class="twsheen" aria-hidden="true"></i>` +
        `</div>` +
        `<div class="twamount"><div class="twfig">${numeralRow(fmt(0))}</div></div>` +
      `</div>` +
      `<div class="twcont">${T("Click to continue")}</div>`;
    // the figure sits in the middle of the board
    const centre = () => {
      wrap.style.setProperty("--cx", (GX + 2 * S).toFixed(0) + "px");
      wrap.style.setProperty("--cy", (GY + 2.15 * S).toFixed(0) + "px");
      fitFigure();
    };
    const fitFigure = () => {
      const el = wrap.querySelector(".twamount");
      if (!el) return;
      const room = innerWidth * .96, need = el.offsetWidth;
      el.style.scale = need > room ? (room / need).toFixed(3) : "";
    };
    const refit = window.ResizeObserver ? new ResizeObserver(fitFigure) : null;
    centre();
    addEventListener("resize", centre);
    if (refit) refit.observe(wrap.querySelector(".twfig"));
    document.body.appendChild(wrap);
    const stopRain = startIconRain(wrap);
    const step = (ms, fn) => setTimeout(fn, REDUCED ? 0 : ms / speed());
    let phase = 0, settled = REDUCED, done2 = false, holdTimer = null;
    const onKey = e => {
      if (e.code !== "Space" && e.code !== "Enter") return;
      e.preventDefault(); e.stopPropagation();
      go();
    };
    const go = () => {
      if (phase !== 1) return;
      if (!settled) { settled = true; paint(amount); return; }   // first press lands the figure
      if (total && !done2) return;
      close();
    };
    const close = () => {
      if (phase !== 1) return;
      phase = 2;
      clearTimeout(holdTimer);
      document.removeEventListener("keydown", onKey, true);
      removeEventListener("resize", centre);
      if (refit) refit.disconnect();
      stopRain();
      wrap.classList.remove("up");
      step(150, hudBack);
      step(420, () => {
        wrap.classList.remove("on");
        step(340, () => { wrap.remove(); resolve(); });
      });
    };
    wrap.addEventListener("click", go);
    document.addEventListener("keydown", onKey, true);
    const amountEl = wrap.querySelector(".twfig");
    const logos = [...wrap.querySelectorAll(".twlogo")];
    for (const l of logos) l.decode && l.decode().catch(() => {});
    const showArt = (art, label) => {
      for (const l of logos) { const on = l.dataset.art === art; l.classList.toggle("on", on); l.setAttribute("aria-hidden", on ? "false" : "true"); }
    };
    const head = wrap.querySelector(".twhead");
    const perBet = bet() > 0 ? amount / bet() : 0;
    const tiers = WIN_TIERS.filter(t => perBet >= t.at);
    const runMs = REDUCED ? 0 : (2200 + tiers.length * 700) / speed();
    let shown = -1, fitLen = -1, lastTick = 0;
    const paint = v => {
      const s = v >= amount ? fmt(amount) : RGS.money(cents(v), undefined, 0);
      amountEl.innerHTML = numeralRow(s);
      if (s.length !== fitLen) { fitLen = s.length; fitFigure(); }
      if (v < amount && performance.now() - lastTick > 70) { lastTick = performance.now(); SFX.tick(); }
      let idx = -1;
      for (let i = 0; i < tiers.length; i++) if ((bet() > 0 ? v / bet() : 0) >= tiers[i].at) idx = i;
      if (idx === shown) return;
      shown = idx;
      if (idx < 0) return;
      const t = tiers[idx];
      showArt(t.art, T(t.label));
      head.classList.remove("blank");
      head.classList.add("tier");
      wrap.setAttribute("aria-label", T(t.label) + " " + fmt(amount));
      headFx(wrap, head, WIN_TIERS.indexOf(t));
      head.classList.remove("hit"); restyle(head); head.classList.add("hit");
      SFX.combo(Math.min(3, 2 + idx), 3 + idx);   // a sting a step higher at every mark
    };
    const countUp = () => new Promise(done => {
      if (!runMs) { paint(amount); done(); return; }
      const t0 = performance.now();
      const tick = () => {
        const p = Math.min(1, (performance.now() - t0) / runMs);
        paint(amount * p * p);
        if (p < 1 && !settled) requestAnimationFrame(tick);
        else { settled = true; paint(amount); done(); }
      };
      requestAnimationFrame(tick);
    });
    restyle(wrap);
    wrap.classList.add("on");
    hudAway();
    $("autoPop").hidden = true; $("volPop").hidden = true;
    SFX.coinShower();
    step(300, () => {
      wrap.classList.add("up");
      phase = 1;
      const reach = { x: .8, y: 1.1, r: .8, s: .02, unit: "vh" };
      hoverWin(head, reach, .2);
      hoverWin(wrap.querySelector(".twamount"), reach, .2);
      countUp().then(() => {
        if (phase !== 1) return;
        if (!total) {
          holdTimer = setTimeout(close, (REDUCED ? 1200 : tiers.length ? 2400 : 1500) / speed());
          return;
        }
        step(700, () => {
          if (phase !== 1) return;
          wrap.classList.add("swap");
          step(REDUCED ? 0 : 360, () => {
            if (phase !== 1) return;
            showArt("win/total_win.webp", T("Total win"));
            head.classList.remove("blank", "tier");
            wrap.setAttribute("aria-label", T("Total win") + " " + fmt(amount));
            amountEl.innerHTML = numeralRow(fmt(amount));
            fitFigure();
            wrap.classList.remove("swap");
            headFx(wrap, head, 3);
            head.classList.remove("hit"); restyle(head); head.classList.add("hit");
            wrap.classList.add("done");
            done2 = true;
            SFX.coinShower();
            // autoplay never waits on a press
            if (state.auto > 0) holdTimer = setTimeout(close, 2600 / speed());
          });
        });
      });
    });
  });
}
