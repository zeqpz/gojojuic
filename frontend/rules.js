/* Juice Dojo rules screen. The numbers here mirror math/juice_math.py - change both together. */
const RULES = (() => {
  const PAY = { H1: [6.8, 34], H2: [4.55, 20.6], H3: [3.4, 13.6], H4: [2.25, 9.05], L1: [1.35, 5.35], L2: [1.15, 4.55], L3: [0.88, 3.6], L4: [0.67, 2.68] };
  const NAME = { H1: "Watermelon", H2: "Pineapple", H3: "Dragon Fruit", H4: "Coconut", L1: "Orange", L2: "Apple", L3: "Lemon", L4: "Kiwi" };
  const LINES = [
    ...[0, 1, 2, 3].map(r => [0, 1, 2, 3].map(c => [r, c])),
    ...[0, 1, 2, 3].map(c => [0, 1, 2, 3].map(r => [r, c])),
    [0, 1, 2, 3].map(i => [i, i]), [0, 1, 2, 3].map(i => [i, 3 - i]),
  ];
  const RTP = "96.70%";
  const lineSvg = cells => {
    const pts = cells.map(([r, c]) => `${c * 12 + 8},${r * 12 + 8}`).join(" ");
    let dots = "";
    for (let r = 0; r < 4; r++) for (let c = 0; c < 4; c++) dots += `<circle cx="${c * 12 + 8}" cy="${r * 12 + 8}" r="2.2" fill="rgba(255,255,255,.25)"/>`;
    return `<svg viewBox="0 0 52 52">${dots}<polyline points="${pts}" fill="none" stroke="#ffcf3a" stroke-width="3" stroke-linecap="round"/><circle cx="${cells[0][1] * 12 + 8}" cy="${cells[0][0] * 12 + 8}" r="3.4" fill="#ff7a12"/></svg>`;
  };
  function html({ T, fmt, bet, cost, xcost = 265, boost = 1.25, social }) {
    const x = v => fmt(Math.round(v * bet));
    const rows = Object.keys(PAY).map(id => `<div class="pt"><canvas data-fruit="${id}" width="112" height="112"></canvas>
      <div class="pv"><div>${NAME[id]}</div><div>4 <b>${x(PAY[id][1])}</b></div><div>3 <b>${x(PAY[id][0])}</b></div></div></div>`).join("");
    return `
<section><h4>${T("How it plays")}</h4>
<p>${T("Every spin drops a 4 x 4 wave of fruit through the dojo. As it falls through the board, the blade slices every line that pays and the fruit falls on through. There are no bombs in the base game.")}</p></section>
<section><h4>${T("Lines")}</h4>
<p>${T("10 lines: 4 rows, 4 columns and 2 diagonals. Lines pay both ways: a line pays when 3 or 4 of the same fruit sit next to each other starting from either end. Only the highest win per line is paid; wins on different lines add up.")}</p>
<div class="linesvg">${LINES.map(lineSvg).join("")}</div></section>
<section><h4>${T("Pays")} <span class="fine">(${T("at the current bet")})</span></h4><div class="paytable">${rows}</div></section>
<section><h4>${T("Combo")}</h4><p>${T("Slice 3 or 4 paying lines in one wave for a x2 combo on that wave's win, 5 or more for x3.")}</p></section>
<section><h4>Fruit Frenzy</h4>
<p>${T("3 or more golden star fruit in one spin start Fruit Frenzy: up to 50 faster waves in a row. 4 star fruit start the frenzy multiplier at x2, 5 or more at x3.")}</p>
<p><b>${T("Bombs")}</b>: ${T("bombs only appear in Fruit Frenzy. Every frenzy wave may carry one: the chance starts at 5% and rises by 0.6% each wave, up to 25%. A bomb wave explodes and pays nothing, and the frenzy ends - everything already won is kept.")}</p>
<ul>
<li><b>${T("Multiplier peaches")}</b> (x2, x3, x5, x10): ${T("sliced peaches add their value to one frenzy multiplier (the first replaces x1), which multiplies every frenzy win from that wave on.")}</li>
<li><b>${T("Frost grapes")}</b>: ${T("knock the bomb chance back down to 5%; it starts rising again from there.")}</li>
<li><b>${T("Side fruit")}</b>: ${T("every frenzy wave, fruit flies in from the sides and pays a small amount each, times the multiplier (watermelon 0.2x, pineapple 0.16x, dragon fruit 0.12x, coconut 0.1x, orange 0.06x, apple 0.05x, lemon and kiwi 0.04x). More of it comes as the waves go on.")}</li>
<li><b>${T("Gold Melon finale")}</b>: ${T("survive all 50 waves and the Gold Melon is sliced 6 to 30 times, each slice paying 0.25x times the multiplier.")}</li>
</ul></section>
<section><h4>${T("Bonus Buy")}</h4>
<p><b>Fruit Frenzy</b> - ${cost}x ${T("the bet")} (${fmt(Math.round(cost * bet))}): ${T("starts Fruit Frenzy straight away, at x1.")}</p>
<p><b>Xtreme Frenzy</b> - ${xcost}x ${T("the bet")} (${fmt(Math.round(xcost * bet))}): ${T("a frenzy that starts at x3; multiplier peaches drop more often and are always x3, x5 or x10; the bomb chance starts at 4% and rises by 0.5% a wave.")}</p>
<p><b>${T("Bonus Boost")}</b> - ${boost}x ${T("the bet per spin while it is on")}: ${T("every spin is 1.6x as likely to land Fruit Frenzy. Switch it on and off in the Bonus Buy menu; the bar shows the boosted cost.")}</p></section>
<section><h4>${T("Return to player")}</h4>
<p>${T("Base game RTP")}: <b>${RTP}</b>. ${T("Fruit Frenzy, Xtreme Frenzy and Bonus Boost RTP")}: <b>${RTP}</b>. ${T("Maximum win")}: <b>5,000x</b> ${T("the bet; a round stops paying once it reaches the maximum.")}</p></section>
<section><h4>${T("Controls")}</h4>
<p>${T("Spin starts a round (also the space bar). Press it again during a round to speed it up. Rapid plays rounds faster. Auto play plays a number of rounds in a row and stops if the balance can't cover the next. + and - change the bet.")}</p></section>
<p class="legal">${T("Malfunction voids all wins and plays. A consistent internet connection is required. In the event of a disconnection, reload the game to finish any uncompleted rounds. The expected return is calculated over many plays. The game display is not representative of any physical device and is for illustrative purposes only. Winnings are settled according to the amount received from the Remote Game Server and not from events within the web browser.")}</p>`;
  }
  function paint(SHEETS, META, drawFruit) {
    for (const cv of document.querySelectorAll("#rulesBody canvas[data-fruit]")) {
      const c = cv.getContext("2d");
      c.clearRect(0, 0, cv.width, cv.height);
      drawFruit(c, cv.dataset.fruit, false, 0.4, cv.width / 2, cv.height / 2, cv.width * .9, 0);
    }
  }
  return { html, paint };
})();
