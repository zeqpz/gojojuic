"""Juice Dojo math: simulates rounds and writes Stake Engine publish files.

BASE GAME: one spin is one WAVE - a 4x4 board of fruit falls through the dojo, the blade slashes the
10 lines (4 rows, 4 columns, 2 diagonals) and every line with 3 or 4 of the same fruit in a row from
EITHER end pays (the higher of the two ends). There are no bombs in the base game. 3+ golden star fruit
in the wave start FRUIT FRENZY.

FRUIT FRENZY: up to 50 faster waves. Every wave may carry a BOMB: the chance starts low and rises a
little every wave; a bomb wave explodes, pays nothing and ends the frenzy (everything already won is
kept). Multiplier peaches (x2/x3/x5/x10) fall in the waves: the peaches in a wave add up and multiply
THAT wave's line wins only (no line, no effect; nothing carries over - owner, 2026-11-18); frost
grapes knock the bomb chance back to its starting value; side fruit flies in each wave for small pays.
Clear all 50 waves and the giant Gold Melon is slashed 6-30 times for the finale.

All amounts are in hundredths of the bet (100 == 1x), as the books require.

    python math/juice_math.py sim [--base 300000 --bonus 60000]   # writes math/publish_files
    python math/juice_math.py stats                                # quick RTP / hit-rate estimate
"""
import argparse
import io
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "publish_files")

ROWS = COLS = 4
FRUITS = ["H1", "H2", "H3", "H4", "L1", "L2", "L3", "L4"]
# pays in hundredths of the bet for 3 / 4 in a line
PAY = {
    "H1": (680, 3400), "H2": (455, 2060), "H3": (340, 1360), "H4": (225, 905),
    "L1": (135, 535), "L2": (115, 455), "L3": (88, 360), "L4": (67, 268),
}
# a side fruit (frenzy only) pays a little on its own
SIDE_PAY = {"H1": 20, "H2": 16, "H3": 12, "H4": 10, "L1": 6, "L2": 5, "L3": 4, "L4": 4}

W_BASE = {"H1": 5, "H2": 6, "H3": 7, "H4": 8, "L1": 12, "L2": 13, "L3": 14, "L4": 15}
# the frenzy is richer: high fruit more common, lemon and kiwi rare, so more waves carry lines for the peaches
W_FRENZY = {"H1": 10, "H2": 11, "H3": 12, "H4": 13, "L1": 14, "L2": 14, "L3": 3, "L4": 3}
P_SCATTER = 0.0225           # per cell, base game only
F_MAX_WAVES = 50              # a frenzy is at most this many waves
F_BOMB0 = 0.035               # the first frenzy wave's bomb chance ...
F_BOMB_RAMP = 0.004           # ... rising this much every wave (since the last frost grapes) ...
F_BOMB_MAX = 0.20             # ... up to this
P_MULT = 0.64                 # a multiplier peach this wave (it multiplies only that wave's lines)
P_MULT2 = 0.35                # ... and a second peach with it
MULT_VALUES = ((2, 30), (3, 30), (5, 25), (10, 15))
P_FREEZE = 0.07               # frost grapes: the bomb chance drops back to F_BOMB0
FINALE_HITS = list(range(6, 31))
FINALE_W = [max(1, 34 - h) for h in FINALE_HITS]
FINALE_PER_HIT = 25           # 0.25x per hit
MAX_WIN = 500000              # 5,000x
BUY_COST = 77.0

# XTREME FRENZY (bought only): peaches in almost every wave (often two), always x3 or more,
# and the bomb chance starts lower and climbs more slowly.
X_P_MULT = 0.95
X_P_MULT2 = 0.65
X_MULT_VALUES = ((3, 30), (5, 35), (10, 35))
X_BOMB0 = 0.018
X_BOMB_RAMP = 0.0015
X_COST = 265.0

# BONUS BOOST: every spin costs 1.25x the bet and lands Fruit Frenzy 1.6x as often (star fruit a
# little more likely per cell: P(3+ of 16) scales ~ p^3, tuned by stats below).
BOOST_COST = 1.25
P_SCATTER_BOOST = 0.0265

LINES = ([[(r, c) for c in range(COLS)] for r in range(ROWS)] +
         [[(r, c) for r in range(ROWS)] for c in range(COLS)] +
         [[(i, i) for i in range(4)], [(i, 3 - i) for i in range(4)]])


def pick(rng, table):
    syms, ws = table
    return rng.choices(syms, ws)[0]


def tbl(d):
    return list(d), list(d.values())


T_BASE, T_FRENZY = tbl(W_BASE), tbl(W_FRENZY)


def board(rng, t, scatter=0.0):
    return [["SC" if scatter and rng.random() < scatter else pick(rng, t) for _ in range(COLS)] for _ in range(ROWS)]


def run_from(b, cells):
    s = b[cells[0][0]][cells[0][1]]
    if s not in PAY:
        return None, 0
    n = 1
    while n < 4 and b[cells[n][0]][cells[n][1]] == s:
        n += 1
    return s, n


def line_wins(b):
    """Each line pays its best run of 3-4 from either end (a full line counts once)."""
    wins = []
    for k, cells in enumerate(LINES):
        best = None
        for seq in (cells, cells[::-1]):
            s, n = run_from(b, seq)
            if n >= 3:
                w = {"line": k, "sym": s, "count": n, "cells": [list(x) for x in seq[:n]], "win": PAY[s][n - 3]}
                if best is None or w["win"] > best["win"]:
                    best = w
        if best:
            wins.append(best)
    return wins


def combo_of(n):
    # Slicing many lines in one swipe is a combo: 3-4 lines double the wave, 5+ triple it.
    return 3 if n >= 5 else 2 if n >= 3 else 1


def wave_eval(b):
    wins = line_wins(b)
    combo = combo_of(len(wins))
    return wins, combo, sum(w["win"] for w in wins) * combo


class Round:
    def __init__(self):
        self.events, self.total = [], 0

    def ev(self, e):
        e["index"] = len(self.events)
        self.events.append(e)

    def add(self, amount):
        room = MAX_WIN - self.total
        amount = min(amount, room)
        self.total += amount
        return amount


NORMAL = {"p_mult": None, "p_mult2": None, "values": None, "bomb0": None, "ramp": None, "xtreme": False}
XTREME = {"p_mult": X_P_MULT, "p_mult2": X_P_MULT2, "values": X_MULT_VALUES, "bomb0": X_BOMB0, "ramp": X_BOMB_RAMP, "xtreme": True}


def frenzy(rng, R, prof=NORMAL):
    """Multipliers are per wave (owner, 2026-11-18): the peaches that fall in a wave add up into that wave's
    multiplier, which multiplies that wave's line wins only - if the wave has no line, the peaches pay
    nothing. Nothing carries over to the next wave; side fruit and the finale are not multiplied."""
    p_mult = prof["p_mult"] or P_MULT
    values = prof["values"] or MULT_VALUES
    bomb0 = prof["bomb0"] or F_BOMB0
    ramp = prof["ramp"] or F_BOMB_RAMP
    R.ev({"type": "frenzyStart", "maxWaves": F_MAX_WAVES, "mult": 1, "bombChance": bomb0,
          "xtreme": prof["xtreme"]})
    won, reason, since = 0, "clear", 0
    for i in range(F_MAX_WAVES):
        if R.total >= MAX_WIN:
            reason = "max"
            break
        pace = round(min(2.2, 1 + 0.025 * i), 3)
        p_bomb = min(F_BOMB_MAX, bomb0 + ramp * since)
        since += 1
        b = board(rng, T_FRENZY)
        free = [(r, c) for r in range(ROWS) for c in range(COLS)]
        rng.shuffle(free)
        base = {"type": "wave", "frenzy": True, "n": i, "maxWaves": F_MAX_WAVES, "pace": pace,
                "bombChance": round(p_bomb, 4)}
        if rng.random() < p_bomb:
            # the bomb falls in the formation in place of one fruit; the wave pays nothing and the frenzy ends
            r, c = free.pop()
            b[r][c] = "BOMB"
            R.ev({**base, "board": b, "bomb": [r, c], "wins": [], "combo": 1, "power": [], "side": [],
                  "mult": 1, "waveWin": 0, "total": R.total})
            reason = "bomb"
            break
        power, wmult = [], 0
        n_peach = (1 + (rng.random() < (prof["p_mult2"] or P_MULT2))) if rng.random() < p_mult else 0
        for _ in range(n_peach):
            r, c = free.pop()
            v = rng.choices([m for m, _ in values], [w for _, w in values])[0]
            b[r][c] = f"PW{v}"
            wmult += v
            power.append({"cell": [r, c], "kind": "mult", "value": v})
        wmult = max(1, wmult)
        if rng.random() < P_FREEZE:
            r, c = free.pop()
            b[r][c] = "FRZ"
            since = 0
            power.append({"cell": [r, c], "kind": "frost", "bombChance": bomb0})
        wins, combo, raw = wave_eval(b)
        if not wins:
            wmult = 1                      # peaches with no line to multiply
        side = []
        for _ in range(2 + rng.randint(0, 3) + i // 8):
            s = pick(rng, T_FRENZY)
            side.append({"sym": s, "win": SIDE_PAY[s], "from": rng.choice("LR")})
        for w in wins:
            w["win"] *= wmult
        pay = R.add(raw * wmult + sum(s["win"] for s in side))
        won += pay
        R.ev({**base, "board": b, "bomb": None, "wins": wins, "combo": combo, "power": power, "side": side,
              "mult": wmult, "waveWin": pay, "total": R.total})
    if reason == "clear" and R.total < MAX_WIN:
        hits = rng.choices(FINALE_HITS, FINALE_W)[0]
        pay = R.add(hits * FINALE_PER_HIT)
        won += pay
        R.ev({"type": "finale", "hits": hits, "perHit": FINALE_PER_HIT, "mult": 1, "win": pay,
              "total": R.total})
    R.ev({"type": "frenzyEnd", "reason": reason, "win": won, "mult": 1, "total": R.total})


def base_round(rng, boost=False):
    R = Round()
    b = board(rng, T_BASE, P_SCATTER_BOOST if boost else P_SCATTER)
    wins, combo, raw = wave_eval(b)
    pay = R.add(raw)
    sc = [[r, c] for r in range(ROWS) for c in range(COLS) if b[r][c] == "SC"]
    R.ev({"type": "wave", "frenzy": False, "n": 0, "pace": 1.0, "board": b, "bomb": None, "wins": wins,
          "combo": combo, "waveWin": pay, "total": R.total, "scatters": sc})
    if len(sc) >= 3:
        frenzy(rng, R)
    R.ev({"type": "finalWin", "amount": R.total})
    return R


def bonus_round(rng):
    R = Round()
    frenzy(rng, R)
    R.ev({"type": "finalWin", "amount": R.total})
    return R


def xtreme_round(rng):
    R = Round()
    frenzy(rng, R, XTREME)
    R.ev({"type": "finalWin", "amount": R.total})
    return R


def boost_round(rng):
    return base_round(rng, boost=True)


ROUND = {"base": base_round, "bonus": bonus_round, "extremebonus": xtreme_round, "boost": boost_round}
COST = {"base": 1.0, "bonus": BUY_COST, "extremebonus": X_COST, "boost": BOOST_COST}


def summarize(pays, cost):
    n = len(pays)
    mean = sum(pays) / n / 100
    hits = sum(1 for p in pays if p > 0) / n
    return f"RTP {mean / cost:.4f}  hit {hits:.3f}  max {max(pays) / 100:.0f}x  mean {mean:.3f}x"


def weights_for(pays, cost, target=0.967, base=1_000_000):
    """Uniform weights, then extra weight on the zero books (RTP too high) or on the mid-paying books
    (too low) so the table's RTP lands on the target to within a hair."""
    n = len(pays)
    w = [base] * n
    goal = target * cost * 100                  # mean payout in hundredths
    tot_w, tot_p = base * n, base * sum(pays)
    mean = tot_p / tot_w
    if mean > goal:
        zeros = [i for i, p in enumerate(pays) if p == 0]
        extra = (tot_p / goal - tot_w)            # weight to add at payout 0
        each, rem = divmod(int(round(extra)), len(zeros))
        for j, i in enumerate(zeros):
            w[i] += each + (1 if j < rem else 0)
    elif mean < goal:
        mid = [i for i, p in enumerate(pays) if 0 < p <= goal * 20]
        s_mid = sum(pays[i] for i in mid)
        # add k to each mid book: (tot_p + k*s_mid) / (tot_w + k*len(mid)) = goal
        k = (goal * tot_w - tot_p) / (s_mid - goal * len(mid))
        for i in mid:
            w[i] += int(round(k))
    rtp = sum(a * b for a, b in zip(w, pays)) / sum(w) / 100 / cost
    return w, rtp


def simulate(mode, n, seed):
    rng = random.Random(seed)
    fn = ROUND[mode]
    books = []
    for i in range(n):
        R = fn(rng)
        books.append({"id": i, "payoutMultiplier": R.total, "events": R.events})
    return books


def write_mode(mode, books, cost):
    import zstandard
    pays = [b["payoutMultiplier"] for b in books]
    w, rtp = weights_for(pays, cost)
    os.makedirs(OUT, exist_ok=True)
    buf = io.BytesIO()
    biggest = 0
    for b in books:
        line = json.dumps(b, separators=(",", ":")).encode() + b"\n"
        biggest = max(biggest, len(line))
        buf.write(line)
    with open(os.path.join(OUT, f"books_{mode}.jsonl.zst"), "wb") as fh:
        fh.write(zstandard.ZstdCompressor(level=19).compress(buf.getvalue()))
    with open(os.path.join(OUT, f"lookUpTable_{mode}_0.csv"), "w", encoding="utf-8", newline="\n") as fh:
        for b, wt in zip(books, w):
            fh.write(f"{b['id']},{wt},{b['payoutMultiplier']}\n")
    print(f"[{mode}] {len(books)} books  {summarize(pays, cost)}  -> weighted RTP {rtp:.5f}  "
          f"largest book {biggest / 1024:.1f} KiB", flush=True)
    return rtp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["sim", "stats"])
    ap.add_argument("--base", type=int, default=300000)
    ap.add_argument("--bonus", type=int, default=60000)
    ap.add_argument("--seed", type=int, default=20261113)
    ap.add_argument("--modes", default="base,bonus,extremebonus,boost")
    a = ap.parse_args()
    want = a.modes.split(",")
    size = {"base": a.base, "boost": a.base, "bonus": a.bonus, "extremebonus": a.bonus}
    seed_of = {"base": 0, "bonus": 7, "extremebonus": 11, "boost": 13}
    if a.cmd == "stats":
        for mode in want:
            n = min(size[mode], 100000 if mode in ("base", "boost") else 20000)
            books = simulate(mode, n, a.seed + seed_of[mode])
            pays = [b["payoutMultiplier"] for b in books]
            if mode in ("base", "boost"):
                fr = sum(1 for b in books if any(e["type"] == "frenzyStart" for e in b["events"]))
                extra = f"  frenzy 1 in {n / max(fr, 1):.0f}"
            else:
                fw = [sum(1 for e in b["events"] if e["type"] == "wave") for b in books]
                clear = sum(1 for b in books if any(e["type"] == "finale" for e in b["events"]))
                extra = (f"  frenzy mean {sum(pays) / n / 100:.1f}x (price {COST[mode]:.0f}x)  avg waves {sum(fw) / n:.1f}"
                         f"  all-50 1 in {n / max(clear, 1):.0f}  p95 {sorted(pays)[int(n * .95)] / 100:.0f}x")
            print(f"[{mode}] {summarize(pays, COST[mode])}{extra}", flush=True)
        return
    for mode in want:
        write_mode(mode, simulate(mode, size[mode], a.seed + seed_of[mode]), COST[mode])
    with open(os.path.join(OUT, "index.json"), "w", encoding="utf-8") as fh:
        order = ["base", "bonus", "extremebonus", "boost"]
        json.dump({"modes": [{"name": m, "cost": COST[m], "events": f"books_{m}.jsonl.zst",
                              "weights": f"lookUpTable_{m}_0.csv"} for m in order
                             if os.path.exists(os.path.join(OUT, f"books_{m}.jsonl.zst"))]}, fh, indent=4)

if __name__ == "__main__":
    sys.exit(main())
