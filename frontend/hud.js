/* HUD shape (HUD v3) ported verbatim from zeqpz/orleans: buildHud() draws the bar, the spin hexagon and the four tabs as vectors. */
const $ = id => document.getElementById(id);
function buildHud() {
  const frame = document.querySelector(".hudframe");
  if (!frame) return;
  const upright = matchMedia("(max-width: 1100px) and (orientation: portrait)").matches;
  const T60 = Math.sqrt(3), S60 = Math.sqrt(3) / 2;
  const M = 4, H = 128, TOP = M, BOT = M + H, CY = M + H / 2;   // M: room for the outline
  const S = 74;                                    // the hexagon's half-width
  const BH = 100, BT = CY - BH / 2, BB = CY + BH / 2;   // the bar, its top and bottom
  const LEN = upright ? 520 : 720;                 // the bar's straight run (longer for the WIN readout, 2026-11-05)
  const G = 6, GX = G / S60, TW = 72, TG = 6;      // tab gap (square to the face), its run across, tab width, gap within a pair
  const run = (BH / 2) / T60;                      // the pointed end's reach
  const Y1 = CY - TG / 2, Y2 = CY + TG / 2;
  const X0 = M + TW + GX - (CY - Y1) / T60;        // the bar's point: the left tabs' outer corner lands on M
  const XI = X0 + run + LEN;                       // where the bar's edges meet the hexagon's faces
  const HX = XI - run + S;                         // the hexagon's centre
  const li = y => X0 + Math.abs(CY - y) / T60 - GX;      // the left tabs' inner edge
  const ri = y => HX + S - Math.abs(y - CY) / T60 + GX;  // the right tabs' inner edge
  const FW = ri(Y1) + TW + M, FH = BOT + M;
  const tabs = {
    menuBtn:  [[li(TOP) - TW, TOP], [li(TOP), TOP], [li(Y1), Y1], [li(Y1) - TW, Y1]],
    audioBtn: [[li(Y2) - TW, Y2], [li(Y2), Y2], [li(BOT), BOT], [li(BOT) - TW, BOT]],
    rapidBtn: [[ri(TOP), TOP], [ri(TOP) + TW, TOP], [ri(Y1) + TW, Y1], [ri(Y1), Y1]],
    autoBtn:  [[ri(Y2), Y2], [ri(Y2) + TW, Y2], [ri(BOT) + TW, BOT], [ri(BOT), BOT]],
  };
  const body = [[X0, CY], [X0 + run, BT], [XI, BT], [HX - S / 2, TOP], [HX + S / 2, TOP], [HX + S, CY],
                [HX + S / 2, BOT], [HX - S / 2, BOT], [XI, BB], [X0 + run, BB]];
  const n2 = v => +v.toFixed(2);
  // a polygon with its corners rounded (radius per corner, or one for all)
  const round = (pts, rad) => {
    let d = "";
    pts.forEach(([vx, vy], i) => {
      const [px, py] = pts[(i + pts.length - 1) % pts.length], [nx, ny] = pts[(i + 1) % pts.length];
      const ax = px - vx, ay = py - vy, bx = nx - vx, by = ny - vy;
      const la = Math.hypot(ax, ay), lb = Math.hypot(bx, by);
      const ang = Math.acos(Math.max(-1, Math.min(1, (ax * bx + ay * by) / (la * lb))));
      const r = Array.isArray(rad) ? rad[i] : rad;
      const t = Math.min(r / Math.tan(ang / 2), la / 2, lb / 2), rr = t * Math.tan(ang / 2);
      const sweep = ax * by - ay * bx < 0 ? 1 : 0;
      d += `${i ? "L" : "M"}${n2(vx + ax / la * t)} ${n2(vy + ay / la * t)}A${n2(rr)} ${n2(rr)} 0 0 ${sweep} ${n2(vx + bx / lb * t)} ${n2(vy + by / lb * t)}`;
    });
    return d + "Z";
  };
  const pct = (v, of) => (v / of * 100).toFixed(4) + "%";
  const put = (el, x, y, w, h) => {
    if (!el) return;
    el.style.left = pct(x, FW); el.style.top = pct(y, FH); el.style.width = pct(w, FW); el.style.height = pct(h, FH);
  };
  frame.style.setProperty("--hud-fw", n2(FW));
  frame.style.setProperty("--hud-fh", n2(FH));
  const shape = frame.querySelector(".hudshape");
  shape.setAttribute("viewBox", `0 0 ${n2(FW)} ${n2(FH)}`);
  shape.querySelector("path").setAttribute("d", round(body, [16, 10, 10, 12, 12, 14, 12, 12, 10, 10]));
  const NS = "http://www.w3.org/2000/svg";
  for (const [id, pts] of Object.entries(tabs)) {
    const btn = $(id);
    if (!btn) continue;
    const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]);
    const x = Math.min(...xs), y = Math.min(...ys), w = Math.max(...xs) - x, h = Math.max(...ys) - y;
    put(btn, x, y, w, h);
    let svg = btn.querySelector(":scope > svg.tabshape");
    if (!svg) {
      svg = document.createElementNS(NS, "svg");
      svg.setAttribute("class", "tabshape"); svg.setAttribute("aria-hidden", "true"); svg.setAttribute("focusable", "false");
      svg.appendChild(document.createElementNS(NS, "path"));
      btn.prepend(svg);
    }
    svg.setAttribute("viewBox", `${n2(x)} ${n2(y)} ${n2(w)} ${n2(h)}`);
    svg.firstChild.setAttribute("d", round(pts, 10));
  }
  // the readouts between the point and the hexagon (whose left corner reaches `run` into the bar)
  put(frame.querySelector(".hudbar"), X0 + run + 2, BT, LEN - run - 16, BH);
  put(frame.querySelector(".spinwrap"), HX - S, TOP, 2 * S, H);
}
// Juice Dojo: the HUD layer is scaled exactly the way orleans scales its whole page (fitApp there).
// Orleans lays its page out ~1140 wide and 1440 tall (+138 per unit the bar is raised), fits it to the
// window (--fit), and raises the bar (--hs) so it reads at ~0.72 of full-HD size, at most x1.5 and never
// wider than the screen. #app here is that page's foot: W / fit wide, scaled by fit from its corner.
const PAGE_W = 1140, PAGE_H = 1440, BAR_H = 138;
function fitHud() {
  const W = innerWidth, H = innerHeight;
  if (W < 40 || H < 40) return;
  const app = document.getElementById("app"), root = document.documentElement.style;
  const f = document.querySelector(".hudframe");
  const natW = (parseFloat(f && f.style.getPropertyValue("--hud-fw")) || 1030);
  const fitAt = hs => Math.max(.05, Math.min(1, W / PAGE_W, H / (PAGE_H + (hs - 1) * BAR_H)));
  let fit = fitAt(1);
  let hs = Math.min(1.5, Math.max(1, .72 / fit));
  hs = Math.max(1, Math.min(hs, (W / fit - 40) / natW));
  fit = fitAt(hs);
  if (natW * hs > W / fit - 40) { hs = Math.max(1, (W / fit - 40) / natW); fit = fitAt(hs); }
  root.setProperty("--hs", hs.toFixed(3));
  root.setProperty("--fit", fit.toFixed(4));
  app.style.width = (W / fit) + "px";
  app.style.transform = `scale(${fit.toFixed(4)})`;
}
buildHud();
fitHud();
addEventListener("resize", fitHud);
matchMedia("(max-width: 1100px) and (orientation: portrait)").addEventListener?.("change", buildHud);



// ---- verbatim from orleans: pop-ups placed over their tab, and the spin arrows' slow turn ----
const REDUCED_MOTION = matchMedia("(prefers-reduced-motion: reduce)").matches;
function placePop(pop, btn, dx = 0) {   // dx: a layout-px nudge sideways, for two pops over one button
  const row = document.querySelector(".bottom");
  if (!row || !pop || !btn) return;
  const rr = row.getBoundingClientRect(), br = btn.getBoundingClientRect();
  const k = rr.width / Math.max(1, row.offsetWidth);
  const pr = pop.getBoundingClientRect(), half = pr.width / 2;
  // A pop marked data-side="left" (the volume panel: the speaker tab sits under the menu tab,
  // so from above its pointer could only land on the menu) stands beside the HUD instead, level
  // with its tab, the pointer on the tab's outer side - wherever there is room for it there,
  // which also keeps it off the board. Without the room it rises over the tab as usual.
  const frame = btn.closest(".hudframe");
  if (pop.dataset.side === "left" && frame) {
    const fr = frame.getBoundingClientRect(), s0 = pr.width / Math.max(1, pop.offsetWidth);
    const gap = 16 * k * s0;
    if (fr.left - rr.left - 10 * k >= pr.width + gap) {
      pop.classList.add("side");
      const by = br.top + br.height / 2;
      const foot = Math.min(by + pr.height / 2, fr.bottom);         // level with the tab, never below the HUD
      const left = ((fr.left - gap - half - rr.left) / k) + "px";   // its centre (the pop is centred on `left`)
      const bottom = ((rr.bottom - foot) / k) + "px";
      const ay = Math.max(18, Math.min(pop.offsetHeight - 18, (by - (foot - pr.height)) / Math.max(.01, s0))).toFixed(1) + "px";
      if (pop.style.left !== left) pop.style.left = left;
      if (pop.style.bottom !== bottom) pop.style.bottom = bottom;
      if (pop.style.getPropertyValue("--ay") !== ay) pop.style.setProperty("--ay", ay);
      return;
    }
  }
  pop.classList.remove("side");
  // Centre on the button, then pull back inside the bar. The three-line button sits at the
  // very left edge and its pop-up is three buttons wide, so centred alone puts the first one
  // off the side of the screen.
  const margin = 10 * k;
  const lo = rr.left + half + margin, hi = rr.right - half - margin;
  let cx = br.left + br.width / 2 + dx * k;
  if (lo <= hi) cx = Math.max(lo, Math.min(hi, cx));
  const left = ((cx - rr.left) / k) + "px";
  // Rise clear of the button, and of anything stacked over it that the pop would land on.
  // A button inside an already-open pop-up sits above the whole bar, so this resolves to
  // "10px over the button" for it and to "10px over the tallest thing in the way" otherwise.
  //
  // Only things in the bar's own flow count. The pop-ups hang off the bar as children of it,
  // so measuring them here makes each one clear the other: open one, and the next frame
  // lifts it past the first, and the frame after that lifts it again. That is a runaway -
  // it put both of them a hundred thousand pixels off the top of the screen.
  let top = br.top;
  for (const el of row.children) {
    const r = el.getBoundingClientRect();
    if (!r.width && !r.height) continue;   // a hidden child is a 0x0 box at the page origin
    const pos = getComputedStyle(el).position;
    if (pos === "absolute" || pos === "fixed") continue;   // an overlay, not part of the bar
    if (r.right > cx - half && r.left < cx + half) top = Math.min(top, r.top);
  }
  const bottom = ((rr.bottom - top) / k + 14) + "px";   // clear of the bar by its pointer's length
  if (pop.style.left !== left) pop.style.left = left;        // only write on a real move, so
  if (pop.style.bottom !== bottom) pop.style.bottom = bottom;  // the tracker costs reads only
  // the pointer on the pop's foot sits over the button even where the pop was pulled aside
  // (--ax, in the pop's own px: its rect carries its scale)
  const s = pr.width / Math.max(1, pop.offsetWidth), w = pop.offsetWidth;
  const ax = Math.max(24, Math.min(w - 24, (br.left + br.width / 2 - (cx - half)) / Math.max(.01, s))).toFixed(1) + "px";
  if (pop.style.getPropertyValue("--ax") !== ax) pop.style.setProperty("--ax", ax);
}
const spinArrows = (() => {
  const TURN = 3000;   // ms per revolution
  let raf = 0, t0 = 0, angle = 0, winding = null;
  const put = () => { const b = $("spinBtn"); if (b) b.style.setProperty("--arrows", angle.toFixed(2) + "deg"); };
  const tick = now => {
    if (winding) {
      const p = Math.min(1, (now - winding.t0) / winding.ms);
      angle = winding.from + (winding.to - winding.from) * (1 - Math.pow(1 - p, 3));
      put();
      if (p >= 1) { winding = null; angle = 0; put(); raf = 0; return; }
    } else {
      angle = Math.max(0, now - t0) / TURN * 360;
      put();
    }
    raf = requestAnimationFrame(tick);
  };
  return {
    start() {
      if (REDUCED_MOTION || (raf && !winding)) return;   // already turning
      winding = null;
      t0 = performance.now() + 800;                       // after the press's quick turn
      if (!raf) raf = requestAnimationFrame(tick);
    },
    stop() {
      if (!raf || winding) return;
      const to = Math.ceil(angle / 360) * 360;            // on to the next upright
      winding = { from: angle, to, t0: performance.now(), ms: Math.max(250, (to - angle) / 360 * TURN * .6) };
    },
  };
})();
