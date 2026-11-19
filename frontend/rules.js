/* Juice Dojo rules screen. The numbers here mirror math/juice_math.py - change both together.
 *
 * Laid out the way orleans lays out its game information (frontend/rules.js there): a section per
 * topic, each with a small spaced-caps label; the headline figures as three tiles; the paytable as
 * one card per fruit; the specials as icon rows; the modes and the controls as tables; the legal
 * text last, outside any box. Styling: info.css (#infoWrap). Fruit icons: paint() below draws every
 * canvas[data-fruit] with the game's own sprite sheets.
 */
const RULES = (() => {
  const PAY = { H1: [6.8, 34], H2: [4.55, 20.6], H3: [3.4, 13.6], H4: [2.25, 9.05], L1: [1.35, 5.35], L2: [1.15, 4.55], L3: [0.88, 3.6], L4: [0.67, 2.68] };
  const NAME = { H1: "Watermelon", H2: "Pineapple", H3: "Dragon Fruit", H4: "Coconut", L1: "Orange", L2: "Apple", L3: "Lemon", L4: "Kiwi" };
  const LINES = [
    ...[0, 1, 2, 3].map(r => [0, 1, 2, 3].map(c => [r, c])),
    ...[0, 1, 2, 3].map(c => [0, 1, 2, 3].map(r => [r, c])),
    [0, 1, 2, 3].map(i => [i, i]), [0, 1, 2, 3].map(i => [i, 3 - i]),
  ];
  const RTP = "96.70%", MAX_WIN = 5000;
  // one line's diagram: the 4 x 4 board as dots, the line drawn over it, its first cell marked
  const lineSvg = cells => {
    const p = ([r, c]) => [c * 12 + 8, r * 12 + 8];
    let dots = "";
    for (let r = 0; r < 4; r++) for (let c = 0; c < 4; c++) dots += `<circle cx="${c * 12 + 8}" cy="${r * 12 + 8}" r="1.9"/>`;
    const [x0, y0] = p(cells[0]), [x1, y1] = p(cells[cells.length - 1]);
    return `<svg viewBox="0 0 52 52" aria-hidden="true"><g class="ld">${dots}</g><polyline points="${cells.map(q => p(q).join(",")).join(" ")}"/><circle class="le" cx="${x0}" cy="${y0}" r="3.2"/><circle class="le" cx="${x1}" cy="${y1}" r="3.2"/></svg>`;
  };
  // t: the frame of the fruit's tumble to show (the star fruit reads as a star only face-on); k: a size factor for
  // sprites drawn small in their tile (the bomb)
  const icon = (id, t, k) => `<canvas class="ricon" data-fruit="${id}"${t != null ? ` data-t="${t}"` : ""}${k ? ` data-k="${k}"` : ""} width="112" height="112" aria-hidden="true"></canvas>`;

  function html({ T, fmt, bet, cost, xcost = 265, boost = 1.25, social }) {
    const x = v => fmt(Math.round(v * bet));
    const big = n => n.toLocaleString("en-US");

    const pays = Object.keys(PAY).map(id => `<div class="prow">${icon(id)}
      <div class="pname">${NAME[id]}</div>
      <dl class="pvals"><div><dt>4</dt><dd>x${PAY[id][1]}</dd><dd><em>${x(PAY[id][1])}</em></dd></div><div><dt>3</dt><dd>x${PAY[id][0]}</dd><dd><em>${x(PAY[id][0])}</em></dd></div></dl>
    </div>`).join("");

    return `
<section>
  <h4>${T("How it plays")}</h4>
  <p>${T("Every spin drops a 4 x 4 wave of fruit through the dojo. As it falls through the board, the blade slices every line that pays and the fruit falls on through. There are no bombs in the base game.")}</p>
  <div class="kvgrid">
    <div><span>RTP</span><b>${RTP}</b><small>${T("every mode")}</small></div>
    <div><span>${T("Max win")}</span><b>x${big(MAX_WIN)}</b><small>${T("the bet")} · ${x(MAX_WIN)}</small></div>
    <div><span>${T("Lines")}</span><b>10</b><small>${T("both ways")}</small></div>
  </div>
  <p class="fine">${T("Base game RTP")}: <b>${RTP}</b>. ${T("Fruit Frenzy, Xtreme Frenzy and Bonus Boost RTP")}: <b>${RTP}</b>. ${T("Maximum win")}: <b>5,000x</b> ${T("the bet; a round stops paying once it reaches the maximum.")}</p>
</section>

<section>
  <h4>${T("Pays")}<span class="h4note">${T("at the current bet")} · ${fmt(bet)}</span></h4>
  <div class="paytable">${pays}</div>
</section>

<section>
  <h4>${T("Lines")}</h4>
  <p>${T("10 lines: 4 rows, 4 columns and 2 diagonals. Lines pay both ways: a line pays when 3 or 4 of the same fruit sit next to each other starting from either end. Only the highest win per line is paid; wins on different lines add up.")}</p>
  <div class="linesvg">${LINES.map(lineSvg).join("")}</div>
  <p><b>${T("Combo")}</b> — ${T("Slice 3 or 4 paying lines in one wave for a x2 combo on that wave's win, 5 or more for x3.")}</p>
</section>

<section>
  <h4>Fruit Frenzy</h4>
  <div class="srow">${icon("SC", 1.2, 1.1)}<p>${T("3 or more golden star fruit in one spin start Fruit Frenzy: up to 50 faster waves in a row. Frenzy waves carry more of the high fruit and only a few lemons and kiwis.")}</p></div>
  <div class="srow">${icon("BOMB", 0.4, 1.25)}<p><b>${T("Bombs")}</b>: ${T("bombs only appear in Fruit Frenzy. A bomb falls in the wave in place of one fruit: the chance starts at 3.5% and rises by 0.4% each wave, up to 20%. A bomb wave explodes and pays nothing, and the frenzy ends - everything already won is kept.")}</p></div>
  <div class="srow">${icon("PW5")}<p><b>${T("Multiplier peaches")}</b> (x2, x3, x5, x10): ${T("peaches fall in with the fruit of a wave. If that wave slices one or more lines, its peaches add together and multiply that wave's line wins (two peaches x2 and x5 make x7). A wave with no line gets nothing from its peaches, and nothing carries over to the next wave.")}</p></div>
  <div class="srow">${icon("FRZ")}<p><b>${T("Frost grapes")}</b>: ${T("knock the bomb chance back down to its starting value; it starts rising again from there.")}</p></div>
  <div class="srow">${icon("H2")}<p><b>${T("Side fruit")}</b>: ${T("every frenzy wave, fruit flies in from the sides and pays a small amount each (watermelon 0.2x, pineapple 0.16x, dragon fruit 0.12x, coconut 0.1x, orange 0.06x, apple 0.05x, lemon and kiwi 0.04x). More of it comes as the waves go on.")}</p></div>
  <div class="srow">${icon("JM")}<p><b>${T("Gold Melon finale")}</b>: ${T("survive all 50 waves and the Gold Melon is sliced 6 to 30 times, each slice paying 0.25x.")}</p></div>
</section>

<section>
  <h4>${T("Bonus Buy")}</h4>
  <table class="modes">
    <thead><tr><th>${T("Mode")}</th><th>${T("Cost")}</th><th>${T("What you get")}</th></tr></thead>
    <tbody>
      <tr><td><b>Fruit Frenzy</b></td><td>${cost}x ${T("the bet")} <em>${fmt(Math.round(cost * bet))}</em></td><td>${T("starts Fruit Frenzy straight away, at x1.")}</td></tr>
      <tr><td><b>Xtreme Frenzy</b></td><td>${xcost}x ${T("the bet")} <em>${fmt(Math.round(xcost * bet))}</em></td><td>${T("a frenzy where multiplier peaches fall in almost every wave, often two at once, and are always x3, x5 or x10; the bomb chance starts at 1.8% and rises by 0.15% a wave.")}</td></tr>
      <tr><td><b>${T("Bonus Boost")}</b></td><td>${boost}x ${T("the bet per spin while it is on")} <em>${fmt(Math.round(boost * bet))}</em></td><td>${T("every spin is 1.6x as likely to land Fruit Frenzy. Switch it on and off in the Bonus Buy menu; the bar shows the boosted cost.")}</td></tr>
    </tbody>
  </table>
</section>

<section>
  <h4>${T("Controls")}</h4>
  <table class="guide">
    <tr><td><b>${T("Spin")}</b></td><td>${T("Starts a round (also the space bar). Press it again during a round to speed it up.")}</td></tr>
    <tr><td><b>+ / −</b></td><td>${T("Change the bet.")}</td></tr>
    <tr><td><b>${T("Rapid")}</b></td><td>${T("Plays rounds faster.")}</td></tr>
    <tr><td><b>${T("Auto")}</b></td><td>${T("Plays a number of rounds in a row and stops if the balance can't cover the next.")}</td></tr>
    <tr><td><b>${T("Bonus")}</b></td><td>${T("Opens the Bonus Buy menu: Fruit Frenzy, Xtreme Frenzy and Bonus Boost.")}</td></tr>
    <tr><td><b>${T("Audio")}</b></td><td>${T("Sound and music volume.")}</td></tr>
    <tr><td><b>${T("Info")}</b></td><td>${T("Opens this page.")}</td></tr>
  </table>
</section>

<p class="legal">${T("Malfunction voids all wins and plays. A consistent internet connection is required. In the event of a disconnection, reload the game to finish any uncompleted rounds. The expected return is calculated over many plays. The game display is not representative of any physical device and is for illustrative purposes only. Winnings are settled according to the amount received from the Remote Game Server and not from events within the web browser.")}</p>`;
  }
  function paint(SHEETS, META, drawFruit) {
    for (const cv of document.querySelectorAll("#rulesBody canvas[data-fruit]")) {
      const c = cv.getContext("2d");
      c.clearRect(0, 0, cv.width, cv.height);
      drawFruit(c, cv.dataset.fruit, false, cv.dataset.t ? +cv.dataset.t : 0.4, cv.width / 2, cv.height / 2, cv.width * .9 * (+cv.dataset.k || 1), 0);
    }
  }
  return { html, paint };
})();
