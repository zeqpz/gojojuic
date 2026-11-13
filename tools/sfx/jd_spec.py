"""Juice Dojo sound pass: what Seed Audio (OpenRouter) is asked for, and how each set is cut and levelled.

name -> (prompt, takes, kind, (min s, max s, keep, mode override), out)
  kind  the trim / clean rules of fallslotsga's tools/sfx (process2.K, clean3.HP): hit, impact, click, drop, tone,
        whoosh, foley, spray, and "sting" (a short musical flourish kept whole, activity merged over 0.6 s gaps)
  mode  "hit" (each onset an event), "gesture" (a group of activity merged over the kind's gap: a slice is a swish
        AND a squelch, so the slices use it), "sustain" (the longest steady stretch)
  out   ("set", stem, target momentary-max LUFS, manifest vol, what) -> frontend/assets/sfx/<stem>_1..keep.ogg

All sounds are original generations in a juicy, crunchy, arcade fruit-slicing spirit (no existing game's audio is
referenced or copied). jd.py runs it; see its docstring."""

PRE = "[Sound effect only. No voice, no speech, no music.] "
PRE_STING = "[Sound effect only. No voice, no speech, no singing, no lyrics.] "
CLOSE = " Single isolated sound effect, close-mic, dry, clean studio foley recording, crisp and punchy, no background " \
        "noise, no room hiss, no reverb tail."
CLOSE_MUSIC = " Single isolated short game sound effect, clean studio recording, crisp and bright, no background " \
              "noise, no hiss, no voice."

BLADE = "A razor-sharp steel katana blade whipping through the air and slicing clean through "


def slice_(fruit, what, takes=6, tgt=-14, vol=.8):
    return (PRE + BLADE + fruit + " in one lightning-fast stroke: a very short, bright, metallic blade 'shing' lasting only a tenth of a "
            "second, instantly followed by " + what + " The whole slice is over in under half a second, then "
            "silence.", takes, "hit",
            (.2, 1.1, 3, "gesture"), ("set", None, tgt, vol, fruit))


S = {
    # ---------------- the fruit slices (one set per symbol) ----------------
    "slice_H1": slice_("a whole ripe watermelon",
                       "a big, deep, heavy, wet, watery crunch as the thick rind cracks and the juicy red flesh "
                       "bursts open with a splash of juice."),
    "slice_H2": slice_("a ripe pineapple",
                       "a crunchy, fibrous, stringy crunch as the tough skin and fibrous flesh tear apart, with a "
                       "sweet wet spurt of juice."),
    "slice_H3": slice_("a soft ripe dragon fruit",
                       "a soft, creamy, smooth wet squish as the tender seedy flesh parts like custard, a gentle "
                       "juicy squelch."),
    "slice_H4": slice_("a hard coconut",
                       "a sharp hard woody CRACK of the shell splitting, then a quick splash of coconut water "
                       "spilling out."),
    "slice_L1": slice_("a juicy orange",
                       "a zesty, wet, spraying citrus burst: the peel splits and a fine fizzy spray of juice "
                       "spritzes out."),
    "slice_L2": slice_("a crisp fresh apple",
                       "one loud, clean, crisp, crunchy snap of firm apple flesh, bright and juicy."),
    "slice_L3": slice_("a lemon",
                       "a sharp, tart, quick spritz: a tight little wet squirt of lemon juice with a light peel "
                       "snap."),
    "slice_L4": slice_("a small kiwi fruit",
                       "a small, soft, quick, wet squish of tender green flesh, light and cute.", tgt=-15, vol=.75),
    "slice_SC": (PRE + BLADE + "a glowing golden star fruit in one fast stroke: a quick bright metallic 'shing' and a "
                 "crisp juicy slice, then a bright magical sparkling chime glitter ringing up and twinkling away. "
                 "One single sound, under a second.", 6, "hit", (.35, 1.4, 3, "gesture"),
                 ("set", None, -14, .85, "golden star fruit (scatter): slice + magic sparkle chime")),
    "slice_PW": (PRE + BLADE + "a juicy ripe peach in one fast stroke: a quick bright metallic 'shing' and a soft "
                 "wet juicy slice, then a quick rising electric power-up zap that sweeps up in pitch. One single "
                 "sound, under a second.", 6, "hit", (.35, 1.4, 3, "gesture"),
                 ("set", None, -14, .85, "multiplier peach: juicy slice + rising power-up zap")),
    "slice_FRZ": (PRE + BLADE + "a bunch of frozen icy grapes in one fast stroke: a quick bright metallic 'shing', a "
                  "glassy crystalline icy shatter of tinkling ice shards, and a small cold wet squish. One single "
                  "sound, under a second.", 6, "hit", (.3, 1.3, 3, "gesture"),
                  ("set", None, -14, .8, "frost grapes: icy crystalline shatter + squish")),
    "slice_JM": (PRE + BLADE + "a giant golden melon in one smooth stroke: a warm bright 'shing', a rich, full, "
                 "juicy, satisfying wet slice, and a soft shimmer of gold coins jingling. Pleasant and warm, not "
                 "harsh. One single sound, under a second.", 6, "hit", (.3, 1.3, 3, "gesture"),
                 ("set", None, -15, .7, "giant gold melon (finale, repeated many times): rich slice + coin shimmer")),

    # ---------------- blade and board ----------------
    "swoosh": (PRE + "A thin bamboo stick whipped very fast through the air right past the microphone: one short, "
               "sharp, airy whoosh.", 7, "whoosh", (.2, .9, 4, None),
               ("set", None, -17, .5, "blade swoosh through air")),
    "bump": (PRE + "Two ripe round fruits, like two oranges, knocking together once: one soft, short, rounded, "
             "slightly hollow wooden-ish thunk.", 6, "hit", (.04, .3, 3, None),
             ("set", None, -21, .45, "two fruits knocking together")),
    "drop": (PRE + "A wave of a dozen ripe fruits tossed up into the air together: a soft, airy, rising whoosh "
             "with a light rustle and a few gentle soft fruit tumbles.", 5, "whoosh", (.4, 1.0, 2, None),
             ("set", None, -20, .5, "a wave of fruit tumbling in")),

    # ---------------- frenzy ----------------
    "fuse": (PRE + "A cartoon bomb's lit fuse burning: a steady, crackling, spitting sizzle and hiss with little "
             "sparks popping, for about one second.", 5, "spray", (.6, 1.0, 2, "sustain"),
             ("set", None, -21, .55, "bomb fuse hiss / sizzle")),
    "boom": (PRE + "A big round cartoon bomb exploding: one big, deep, rounded, punchy BOOM with a soft rumbling "
             "decay and a little debris patter. Powerful but warm, not harsh or distorted.", 6, "impact",
             (.6, 1.6, 2, "gesture"), ("set", None, -12, .9, "cartoon bomb explosion (frenzy over)")),
    "frenzy_start": (PRE_STING + "A short bright exciting Japanese-style fanfare: three powerful taiko drum hits "
                     "building up, then a fast bright bamboo flute run rising to a high held note, with a cymbal "
                     "swell. About two seconds, energetic and celebratory.", 6, "sting", (1.4, 2.6, 2, None),
                     ("set", None, -14, .85, "Fruit Frenzy starts: taiko + flute flourish")),
    "multiplier": (PRE + "A magical power-up being collected: a bright, rising, shimmering sparkle sweep climbing "
                   "quickly up in pitch and ending on a clear ringing chime.", 6, "tone", (.4, 1.2, 2, "gesture"),
                   ("set", None, -16, .7, "multiplier collected: rising power-up sparkle")),
    "frost": (PRE + "A magical freeze spell: a cold airy whoosh with bright glassy ice crystals chiming and "
              "crackling as they form, sparkling and frosty.", 6, "tone", (.5, 1.3, 2, "gesture"),
              ("set", None, -17, .65, "frost grapes: ice chime / freeze whoosh")),

    # ---------------- wins ----------------
    "combo": (PRE_STING + "A short, happy, bouncy arcade reward sting: three quick bright marimba and bell notes "
              "stepping upward, the last one ringing. Cheerful and punchy, under one second.", 6, "sting",
              (.35, 1.0, 1, None), ("set", None, -15, .7, "combo: happy rising sting (files 1-3 rise in pitch)")),
    "line_win": (PRE + "A short bright reward chime: two quick sparkling bell dings with a light jingle of gold "
                 "coins.", 6, "tone", (.3, .9, 3, "gesture"),
                 ("set", None, -18, .6, "a line pays: short coin / chime reward")),
    "big_win": (PRE_STING + "A big celebratory win sting: a bright brass and taiko fanfare hit that swells up, with "
                "shimmering chimes and a cascade of gold coins, ending on a triumphant ringing chord. About two "
                "seconds.", 6, "sting", (1.5, 2.6, 2, None),
                ("set", None, -13, .9, "big win celebration sting")),
    "coin_tick": (PRE + "One single small gold coin tapped lightly on another coin: one tiny, short, bright, "
                  "metallic tick.", 6, "click", (.015, .08, 3, None),
                  ("set", None, -22, .35, "win counter tick")),
}
for _n, _v in S.items():                       # stem = the set's own name
    if _v[4][1] is None:
        S[_n] = _v[:4] + ((_v[4][0], _n) + _v[4][2:],)

# one event per take for these (no second hit inside the event)
SINGLE = {"bump", "coin_tick"}
# ringing sounds: cleaning a tone makes it purer, so the guard allows a bigger flatness change
TONAL = {"slice_SC", "slice_JM", "slice_FRZ", "slice_PW", "multiplier", "frost", "combo", "line_win", "big_win",
         "frenzy_start", "coin_tick"}
# end fades (ms) for the ringing ones
FOUT = {"slice_SC": 160, "slice_PW": 120, "slice_FRZ": 120, "slice_JM": 140, "multiplier": 200, "frost": 220,
        "combo": 160, "line_win": 160, "big_win": 400, "frenzy_start": 300, "boom": 350, "drop": 150, "fuse": 90,
        "swoosh": 40}
# the bed allowed under a sound that is itself noise (a whoosh, a sizzle); everything else clean3's -72 dBFS
BED = {"swoosh": -56, "drop": -56, "frost": -56, "slice_L1": -60, "slice_FRZ": -60, "multiplier": -58,
       # takes that are sound from end to end (a chime / zap / coin ring under the whole take): clean3 finds no quiet
       # stretch to measure a bed in and reads the sound itself as one; their raw takes sit on digital silence, the
       # gate does the work, and jd.py report checks the shipped files' floor instead
       "slice_H4": -30, "slice_SC": -20, "slice_PW": -20, "slice_JM": -20, "frenzy_start": -15, "drop": -40}
# the continuous ones whose 'bed' is the sound itself: level + fade only (fall.py texture)
TEXTURE = set()
# cut by hand from the raw takes (jd.py windows: take, from s, to s), high-passed, levelled, faded: the fuse's
# crackling, spitting takes (3, 4) swing too much in level for the sustain finder, which only found the plain hiss (1)
# frenzy_start: the takes play the three taiko hits, go quiet ~0.3-0.5 s, then the flute run and held note; the
# quiet stretch is cut out (30 ms crossfades) so it is one ~2.5 s flourish
WINDOWS = {"fuse": [(3, [(.12, .97)]), (4, [(.62, 1.47)])],
           "frenzy_start": [(2, [(.05, 1.62), (1.88, 2.95)]), (3, [(.05, 1.45), (1.98, 3.0)])]}
# hand picks (take files from cand/), filled in after review where the scoring can't tell
MANUAL = {}
ENDPEAK = {}
STRETCH = {}
# after build (jd.py shape; the pre-shape copies are kept, so it can be re-run):
#   impact (pre s, low-pass Hz, cap s): start `pre` before the onset of the main low/mid hit (the crunch), the blade
#            swish in front of it eased in, so the juice lands right on the slice; at most `cap` long
#   peakwin (pre s, post s): a window around the loudest moment (a blade whoosh: quick rise, fast fall)
#   lead: cut what is in front of the first real hit (-20 dB re the peak) to 4 ms
#   cap s: at most this long (cosine fade over the last 80 ms when it cuts)
#   accent (kind, s after the onset, dB re the slice's peak): an accents.py layer mixed on (sparkle / zap / coins), so
#            the special fruit's identity does not depend on what the generator put in the take
SHAPE = {n: {"impact": (.07, 1500, .6)} for n in S if n.startswith("slice_") and n[6:] in
         ("H1", "H2", "H3", "H4", "L1", "L2", "L3", "L4")}
SHAPE.update({"slice_SC": {"impact": (.07, 1500, .6), "accent": ("sparkle", .03, -5)},
              "slice_PW": {"impact": (.07, 1500, .55), "accent": ("zap", .04, -5)},
              "slice_FRZ": {"impact": (.07, 1500, .85)},
              "slice_JM": {"impact": (.07, 1500, .6), "accent": ("coins", .03, -9)},
              "swoosh": {"peakwin": (.1, .17)}, "drop": {"lead": 1, "cap": 1.0}, "boom": {"lead": 1},
              "multiplier": {"lead": 1}, "frost": {"lead": 1}, "combo": {"lead": 1}, "line_win": {"lead": 1},
              "big_win": {"lead": 1}, "frenzy_start": {"lead": 1}, "bump": {"lead": 1}, "coin_tick": {"lead": 1}})
# made after build: combo_2 / combo_3 are combo_1 sped up this many semitones (an escalating combo)
PITCH_STEPS = {"combo": [0, 3, 7]}


def jobs():
    for name, (prompt, takes, kind, _, _) in S.items():
        close = CLOSE_MUSIC if kind in ("sting", "tone") else CLOSE
        yield name, prompt + close, takes, kind
