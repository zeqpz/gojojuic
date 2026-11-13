"""Generate Juice Dojo's art through OpenRouter (tools/orimg.py).

    python tools/gen_art.py whole      # every whole fruit / special, in parallel
    python tools/gen_art.py halves     # the cut half of each fruit, referencing its whole sprite
    python tools/gen_art.py scene      # background + logo
    python tools/gen_art.py all
    add ids to limit:  python tools/gen_art.py whole H1 L2

Raw outputs land in art/raw/<id>.png (never overwritten unless --force)."""
import os, sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from orimg import generate  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "art", "raw")

STYLE = ("Premium mobile slot game icon, original art. Glossy, juicy, hyper-saturated semi-realistic cartoon "
         "rendering with soft studio lighting, crisp specular highlights, subtle rim light and a thin dark "
         "outline. One single object, centred, filling about 85% of the canvas, viewed straight on, no shadow "
         "on the ground, no text, no letters, no numbers, no border, fully transparent background.")

FRUIT = {
    "H1": "a whole round watermelon with deep green stripes",
    "H2": "a whole golden pineapple with a spiky green crown",
    "H3": "a whole pink dragon fruit with green-tipped scales",
    "H4": "a whole brown hairy coconut",
    "L1": "a whole bright orange (citrus) with a small green leaf",
    "L2": "a whole shiny red apple with a short stem and leaf",
    "L3": "a whole yellow lemon",
    "L4": "a whole fuzzy brown kiwi fruit",
}
SPECIAL = {
    "SC": "a magical glowing golden star fruit (carambola) radiating warm sparkles and a soft golden aura",
    "BOMB": "a classic round black cartoon bomb with a lit sparking fuse, red glowing danger accents and metal cap",
    "PW2": "a magical glowing sapphire-blue peach, crackling with electric blue energy and sparkles",
    "PW3": "a magical glowing violet-purple peach, crackling with purple energy and sparkles",
    "PW5": "a magical glowing ruby-red and gold peach, crackling with fiery energy and sparkles",
    "FRZ": "a cluster of frozen icy-blue grapes covered in frost crystals and tiny icicles, cold mist",
    "JM": "a giant shining solid-gold watermelon with jewel highlights, radiant golden glow",
}
HALF = {k: v.replace("a whole ", "") for k, v in FRUIT.items()}
HALF.update({"SC": "magical golden star fruit", "PW2": "glowing sapphire-blue peach",
             "PW3": "glowing violet peach", "PW5": "glowing ruby-red and gold peach",
             "FRZ": "frozen icy-blue grape cluster", "JM": "solid-gold watermelon with a ruby-red juicy inside"})


def job_whole(i):
    return (os.path.join(RAW, f"{i}.png"), f"{STYLE} Subject: {FRUIT.get(i) or SPECIAL[i]}.", "1:1", True, ())


def job_half(i):
    ref = os.path.join(RAW, f"{i}.png")
    p = (f"{STYLE} Subject: exactly ONE half of the {HALF[i]} from the reference image, cut cleanly straight "
         f"through the middle by a sword, seen from the cut side at a slight angle so the wet, juicy cross-section "
         f"of the flesh (with seeds or core where the real fruit has them) faces the viewer and the skin shows "
         f"around the rim. The cut face is flat and fills most of the shape. Same rendering style, colours and "
         f"outline as the reference.")
    return (os.path.join(RAW, f"{i}_half.png"), p, "1:1", True, (ref,))


def job_scene(i):
    if i == "BG":
        return (os.path.join(RAW, "BG.png"),
                "Background painting for a premium fruit-slicing slot game, original art, 16:9. The inside of a "
                "traditional wooden Japanese dojo at dusk: a big wall of dark, rich, weathered wooden planks fills "
                "the frame, warm paper lanterns glowing at the top corners, faint cherry blossom petals drifting, "
                "soft warm light pooling in the middle and a deep vignette at the edges. The middle area is calm and "
                "uncluttered so game pieces read clearly on top of it. No people, no text, no fruit, no weapons.",
                "16:9", False, ())
    if i == "LOGO":
        return (os.path.join(RAW, "LOGO.png"),
                "Game logo wordmark that reads exactly \"JUICE DOJO\" in two stacked words, original design: chunky "
                "bold brush-stroke letters, glossy juicy orange-to-red gradient with white highlights and a thick "
                "dark outline, juice splashes and droplets flying off the letters, a thin silver katana slash "
                "cutting diagonally across behind the text. Transparent background, nothing else.",
                "3:2", True, ())
    if i == "WOOD":
        return (os.path.join(RAW, "WOOD.png"),
                "Seamless-looking background for a premium slot game, 16:9: a plain wall of warm wooden planks seen straight on, "
                "planks running vertically, rich honey and walnut browns with natural grain, a few knots, soft even lighting "
                "with a gentle darker vignette at the edges. Nothing else: no objects, no lanterns, no plants, no text, no people, "
                "no fruit, no windows. Clean, calm, slightly stylised painterly look.",
                "16:9", False, ())
    if i.startswith("SPLAT"):
        k = int(i[5:])
        shapes = ["a round burst with many thin radiating streaks and droplets",
                  "an elongated directional splash flung to the right, with a tapering tail of droplets",
                  "a dense splatter with a few short drips running downward",
                  "a loose spray of small and medium droplets around a soft core"]
        return (os.path.join(RAW, f"{i}.png"),
                f"A single liquid juice splat stamp: {shapes[k - 1]}. Pure flat WHITE silhouette only, crisp organic edges, "
                "no shading, no colour, no outline, no texture, centred, fully transparent background.",
                "1:1", True, ())
    ban = {"BAN_FRENZY": "an explosive burst of fruit - watermelon, pineapple, oranges, a dragon fruit - being sliced mid-air by a "
                          "gleaming katana arc, halves spinning apart, bright juice spray, a glowing golden star fruit at the centre, "
                          "warm golden light, plain warm wooden plank wall behind",
           "BAN_XFRENZY": "an intense, fiery version: glowing ruby-red and violet power peaches crackling with energy, fruit "
                          "halves and juice flying through a crimson and purple energy blast, a lit cartoon bomb tumbling at the edge, "
                          "dramatic rim light, plain dark wooden plank wall behind",
           "BAN_BOOST": "a shower of glowing golden star fruits falling from above with sparkles and light streaks, a warm "
                        "golden glow, plain warm wooden plank wall behind, the middle left calm and uncluttered"}
    if i in ban:
        return (os.path.join(RAW, f"{i}.png"),
                f"Bonus-buy card banner art for a premium fruit-slicing slot game, original art, 16:9, glossy semi-realistic "
                f"cartoon style matching juicy 3D-looking fruit: {ban[i]}. No text, no letters, no numbers, no logos, no people.",
                "16:9", False, ())
    wm = {"WM_FRENZY": ("FRUIT FRENZY", "glossy juicy golden-orange to red gradient"),
          "WM_XFRENZY": ("XTREME FRENZY", "glossy hot crimson-to-violet gradient with electric purple highlights"),
          "WM_BONUS": ("BONUS", "glossy juicy golden-orange to red gradient")}
    if i in wm:
        word, col = wm[i]
        return (os.path.join(RAW, f"{i}.png"),
                f"Game wordmark that reads exactly \"{word}\", in the same lettering style as the reference logo: chunky bold "
                f"brush-stroke letters, {col}, white highlights, thick dark outline, juice splashes and droplets flying off the "
                f"letters. Only the word, on one line, no sword, no other text, transparent background.",
                "3:2" if word != "BONUS" else "16:9", True, (os.path.join(RAW, "LOGO.png"),))
    if i.startswith("NUM_"):
        g = {"dot": "a full stop (period) dot", "comma": "a comma", "x": "a lowercase multiplication letter x",
             "pct": "a percent sign %"}.get(i[4:], f"the digit {i[4:]}")
        return (os.path.join(RAW, f"{i}.png"),
                f"A single numeral glyph for a game font: {g}, nothing else. Same lettering style as the reference "
                "logo: chunky, bold, slightly irregular brush-stroke shape, glossy juicy golden-yellow to orange to red "
                "vertical gradient, bright white highlights, a thick dark-brown outline, two or three small juice "
                "droplets dripping off it. Centred, upright, fully transparent background, no other characters.",
                "1:1", True, (os.path.join(RAW, "LOGO.png"),))
    words = {"WM_BIGWIN": ("BIG WIN", "glossy juicy golden-orange to red gradient"),
             "WM_MEGAWIN": ("MEGA WIN", "glossy hot pink to deep red gradient with gold highlights"),
             "WM_EPICWIN": ("EPIC WIN", "glossy violet to electric blue gradient with gold highlights"),
             "WM_TOTALWIN": ("TOTAL WIN", "glossy rich gold gradient with white highlights"),
             "WM_UPTO": ("UP TO", "glossy juicy golden-orange to red gradient"),
             "WM_WAVES": ("FRENZY WAVES", "glossy juicy golden-orange to red gradient")}
    if i in words:
        word, col = words[i]
        return (os.path.join(RAW, f"{i}.png"),
                f"Game wordmark that reads exactly \"{word}\", in the same lettering style as the reference logo: chunky "
                f"bold brush-stroke letters, {col}, white highlights, thick dark outline, juice splashes and droplets "
                f"flying off the letters. Only the words, on one line, no sword, no other text, transparent background.",
                "16:9", True, (os.path.join(RAW, "LOGO.png"),))
    white = {"WW_WAVE": "WAVE", "WW_MULTI": "MULTI", "WW_BOMB": "BOMB CHANCE"}
    if i in white:
        return (os.path.join(RAW, f"{i}.png"),
                f"Game lettering that reads exactly \"{white[i]}\", in the same chunky bold brush-stroke letter shapes as "
                "the reference logo, but PURE WHITE letters with soft light-grey shading, a thin dark outline, and a few "
                "small white paint drips, like it was painted on a wall. Only the words, on one line, nothing else, "
                "transparent background.",
                "16:9", True, (os.path.join(RAW, "LOGO.png"),))
    if i.startswith("DRIP"):
        k = int(i[4:])
        shape = ["one long thin drip line with a single fat round bead at the bottom",
                 "two drip lines side by side of different lengths, each ending in a bead",
                 "a short thick drip with a heavy teardrop bead just about to fall",
                 "one long wavy drip line that thins out and ends in a small bead, a smaller droplet below it"][k - 1]
        return (os.path.join(RAW, f"{i}.png"),
                f"A realistic run of thick fruit juice dripping down a vertical wall, seen straight on: a wet rounded blob at "
                f"the top, {shape}. Glossy liquid with soft volume shading and bright white specular highlights along its "
                "edges. Rendered in GRAYSCALE only - white to light grey liquid, no colour - so it can be tinted later. "
                "Nothing else, fully transparent background, the drip centred and vertical.", "9:16", True, ())
    if i.startswith("GSPLAT"):
        k = int(i[6:])
        shape = ["a round burst with radiating streaks and flung droplets",
                 "an elongated directional splash flung to one side with a tail of droplets",
                 "a dense heavy splat with three or four short drips running downward",
                 "a loose spray of droplets of many sizes around a soft wet core"][k - 1]
        return (os.path.join(RAW, f"{i}.png"),
                f"A realistic splat of thick fruit juice on a wall, seen straight on: {shape}. Glossy wet liquid with "
                "volume, soft shading and bright white specular highlights on the blobs and droplets. Rendered in "
                "GRAYSCALE only - white to light grey liquid, no colour - so it can be tinted later. Nothing else, fully "
                "transparent background, centred.", "1:1", True, ())
    if i == "NF_BOOM":
        return (os.path.join(RAW, f"{i}.png"),
                "Game lettering that reads exactly \"BOOM!\": an angular, sharp-edged, Asian-inspired brush display face - "
                "strokes that taper to pointed blade-like tips and hooked serifs - glossy fiery gradient from bright orange "
                "at the top to deep red at the bottom, a thin dark outline and a slight 3D bevel. Only the word, one line, "
                "nothing else, transparent background.", "16:9", True, ())
    nfw = {"NF_TOTALWIN": ("TOTAL WIN", "glossy rich gold to deep orange gradient"),
           "NF_BIGWIN": ("BIG WIN", "glossy fiery gradient from bright orange at the top to deep red at the bottom"),
           "NF_MEGAWIN": ("MEGA WIN", "glossy gradient from hot pink at the top to deep crimson at the bottom"),
           "NF_EPICWIN": ("EPIC WIN", "glossy gradient from bright violet at the top to deep purple at the bottom")}
    if i in nfw:
        word, col = nfw[i]
        return (os.path.join(RAW, f"{i}.png"),
                f"Game lettering that reads exactly \"{word}\": the same angular, sharp-edged, Asian-inspired brush display "
                f"face as the reference - strokes tapering to pointed blade-like tips and hooked serifs - {col}, a thin dark "
                "outline and a slight 3D bevel. Only the words, one line, nothing else, transparent background.",
                "16:9", True, (os.path.join(RAW, "NF_BOOM.png"),))
    if i == "NF_MULTI":
        return (os.path.join(RAW, f"{i}.png"),
                "Game lettering that reads exactly \"MULTI\": an angular, sharp-edged, Asian-inspired brush display face - "
                "strokes that taper to pointed blade-like tips and hooked serifs - PURE WHITE letters with soft light-grey "
                "shading and a thin dark outline, as if painted on a wooden wall. Only the word, one line, nothing else, "
                "transparent background.", "16:9", True, ())
    if i.startswith("NF_"):
        g = {"dot": "a full stop (period) - a small square-ish dot", "comma": "a comma", "x": "a lowercase multiplication letter x",
             "pct": "a percent sign %", "dollar": "a dollar sign $", "euro": "a euro sign"}.get(i[3:], f"the digit {i[3:]}")
        ref = () if i == "NF_0" else (os.path.join(RAW, "NF_0.png"),)
        style = ("Chunky, bold, blocky arcade-game score lettering: thick strokes with slightly rounded square corners and "
                 "flat angled cuts, glossy orange-gold vertical gradient (pale yellow-orange at the top to deep orange at the "
                 "bottom), a soft inner bevel highlight along the top edges, and a thick dark reddish-brown outline. "
                 "Clean flat cartoon shading, no drips, no splashes.")
        return (os.path.join(RAW, f"{i}.png"),
                f"A single glyph for a mobile game's score font: {g}, nothing else. {style} "
                + ("Exactly the same style, colours, outline and proportions as the reference glyph. " if ref else "")
                + "Centred, upright, fully transparent background, no other characters.",
                "1:1", True, ref)
    if i == "PAPER":
        return (os.path.join(RAW, f"{i}.png"),
                "A sheet of old parchment paper for a game results panel, seen flat and straight on: warm light tan paper "
                "with subtle fibres and soft darker stains toward the edges, roughly torn and notched edges all the way "
                "round, a faint darker inset border line a little inside the edge, a soft drop shadow under it. Wider than "
                "tall. Nothing on it - no text, no pictures. Transparent background around the sheet.",
                "3:2", True, ())
    if i == "PLAQUE":
        return (os.path.join(RAW, "PLAQUE.png"),
                "A wide horizontal backing plaque for a big number in a fruit-slicing game: a thick glossy splash of "
                "bright orange-red fruit juice spread into a wide rounded blob, wet highlights, a darker juicy rim, "
                "droplets and little splatters flung off its edges, a few tiny fruit pulp flecks, the middle smooth and "
                "empty to hold text. No text, no numbers, no fruit, nothing else, transparent background.",
                "16:9", True, ())
    raise KeyError(i)


GROUPS = {
    "whole": (list(FRUIT) + list(SPECIAL), job_whole),
    "halves": ([*FRUIT, "SC", "PW2", "PW3", "PW5", "FRZ", "JM"], job_half),
    "scene": (["BG", "LOGO"], job_scene),
    "bonus": (["BAN_FRENZY", "BAN_XFRENZY", "BAN_BOOST", "WM_FRENZY", "WM_XFRENZY", "WM_BONUS"], job_scene),
    "numerals": ([f"NUM_{d}" for d in "0123456789"] + ["NUM_dot", "NUM_comma", "NUM_x", "NUM_pct",
                  "WM_BIGWIN", "WM_MEGAWIN", "WM_EPICWIN", "WM_TOTALWIN", "WM_UPTO", "WM_WAVES", "PLAQUE",
                  "WW_WAVE", "WW_MULTI", "WW_BOMB"], job_scene),
    "nf": (["NF_0", "NF_BOOM", "NF_MULTI", "PAPER"], job_scene),
    "nf2": ([f"NF_{d}" for d in "123456789"] + ["NF_dot", "NF_comma", "NF_x", "NF_pct"], job_scene),
    "drips": (["DRIP1", "DRIP2", "DRIP3", "DRIP4", "GSPLAT1", "GSPLAT2", "GSPLAT3", "GSPLAT4"], job_scene),
    "nf3": (["NF_dollar", "NF_euro", "NF_TOTALWIN", "NF_BIGWIN", "NF_MEGAWIN", "NF_EPICWIN"], job_scene),
    "wood": (["WOOD", "SPLAT1", "SPLAT2", "SPLAT3", "SPLAT4"], job_scene),
}


def run(group, ids, force):
    names, fn = GROUPS[group]
    jobs = [fn(i) for i in names if not ids or i in ids]
    jobs = [j for j in jobs if force or not os.path.exists(j[0])]

    def go(j):
        out, prompt, aspect, transparent, refs = j
        try:
            _, cost = generate(out, prompt, aspect, transparent, refs)
            return f"OK   {os.path.basename(out)} cost {cost}"
        except Exception as e:  # noqa: BLE001
            return f"FAIL {os.path.basename(out)} {e}"

    with ThreadPoolExecutor(6) as ex:
        for line in ex.map(go, jobs):
            print(line, flush=True)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    force = "--force" in sys.argv
    group, ids = (args[0] if args else "all"), set(args[1:])
    os.makedirs(RAW, exist_ok=True)
    for g in (["whole", "scene", "halves"] if group == "all" else [group]):
        run(g, ids, force)
