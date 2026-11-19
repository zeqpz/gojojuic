"""Cartoon dojo scenery for Juice Dojo (owner, 2026-11-18: "more cartoon like and not static").

The back wall is one opaque painting; the things that move are separate transparent cut-outs that the page
sways in CSS (lanterns, bamboo, a blossom branch). Petals are drawn procedurally in game.js.

    python tools/gen_scene.py [name ...]      # all by default; writes art/raw/scene/<name>.png
Then tools/pack_scene.py converts them to frontend/assets/scene/*.webp.
"""
import os, sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from orimg import generate  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "art", "raw", "scene")

STYLE = ("Original cartoon mobile arcade game art: bold clean dark-brown outlines, flat cel shading with two or "
         "three tones per surface, soft painted highlights, warm saturated colours, playful and premium, "
         "like a polished animated TV show. No text, no letters, no logos, no watermark, no characters, no people.")

OUTDOOR = {
    # background: the far landscape, no ground in front (owner, 2026-11-18: outside in Japan, no floor)
    "sky": ("16:9", False,
            "A wide cartoon landscape in Japan at golden hour, seen straight on, used as the far background of a game. "
            "Snow-capped Mount Fuji in the distance a little right of centre, soft layered blue-violet hills, a red "
            "five-storey pagoda small on a hill at the left, a warm peach and gold sky with a few soft clouds, a calm "
            "lake reflecting the light in the lower third. Soft, slightly hazy so it sits far back; the centre is calm "
            "and open. No foreground objects, no ground or floor close to the viewer, no trees in front. " + STYLE),
    "sky_tall": ("9:16", False,
                 "A tall cartoon landscape in Japan at golden hour, portrait, used as the far background of a phone "
                 "game. Snow-capped Mount Fuji in the distance in the middle, soft layered blue-violet hills, a small "
                 "red pagoda on a hill at the left, a warm peach and gold sky with soft clouds filling the upper half, "
                 "a calm lake reflecting the light at the bottom. Soft, slightly hazy so it sits far back. No foreground "
                 "objects, no ground or floor close to the viewer, no trees in front. " + STYLE),
    # midground: framing cut-outs at the sides that sway
    "tree": ("2:3", True,
             "One cartoon Japanese cherry blossom tree with a dark twisting trunk and a big full canopy of pink blossom "
             "clusters leaning to the right, seen from the side, the trunk reaching the bottom edge of the image. "
             "Just the tree, no ground, no grass, no rocks. Fully transparent background. " + STYLE),
    "pine": ("2:3", True,
             "One cartoon Japanese black pine tree with a curving trunk and flat cloud-like layers of dark green "
             "needles leaning to the left, beside a tall grey stone toro lantern with a warm glowing light inside. The "
             "trunk and lantern base reach the bottom edge of the image. No ground, no grass. Fully transparent "
             "background. " + STYLE),
    "clouds": ("3:1", True,
               "Three separate soft fluffy cartoon clouds in a row with gentle peach and lavender shading from a sunset, "
               "spaced apart, nothing touching the edges. Fully transparent background, nothing else. " + STYLE),
    # foreground: the board the fruit are cut on
    "board": ("1:1", True,
              "A big square cartoon wooden board seen straight on from the front, filling the image: thick honey-brown "
              "planks running vertically held by a darker wooden frame with rounded corners and a few iron rivets at "
              "the corners, simple wood grain and knots, a soft highlight at the top and gentle wear. Flat and even "
              "in the middle so things on it read clearly. Fully transparent background around the board, nothing "
              "else. " + STYLE),
}

JOBS = {
    "wall": ("16:9", False,
             "A cartoon Japanese dojo interior seen straight on, used as the background behind a fruit-slicing game. "
             "The middle of the picture is a big calm wall of warm honey-brown wooden planks running vertically, with "
             "simple cartoon wood grain and a few knots, gently lit from the top left, darker towards the edges. It "
             "must stay uncluttered in the centre two thirds - nothing in front of it - so fruit read clearly on it. "
             "Framing the wall on the far left and far right: thick red-lacquered wooden pillars, and beyond them "
             "glowing paper shoji screens with a soft warm light behind. Along the top, a dark wooden beam with a "
             "simple carved edge. At the very bottom, the edge of a green tatami floor. Cosy, warm evening light. "
             + STYLE),
    "wall_tall": ("9:16", False,
                  "A cartoon Japanese dojo interior seen straight on, portrait, used as the background behind a "
                  "fruit-slicing game on a phone. Almost all of it is a big calm wall of warm honey-brown wooden "
                  "planks running vertically, with simple cartoon wood grain and a few knots, gently lit from the "
                  "top, darker towards the edges; the centre must stay completely uncluttered so fruit read clearly. "
                  "Thin red-lacquered pillars at the very left and right edges, a dark wooden beam across the top, "
                  "the edge of a green tatami floor at the very bottom. Cosy, warm evening light. " + STYLE),
    "lantern": ("2:3", True,
                "One red round Japanese paper lantern hanging from a short black cord at the top, with black lacquered "
                "rims at top and bottom, a short gold tassel underneath, and a warm glow from inside making the paper "
                "light up orange in the middle. Plain lantern, no writing or symbols on it. Seen straight on, centred, "
                "the cord reaching the very top edge of the image. Fully transparent background. " + STYLE),
    "bamboo": ("1:2", True,
               "A cluster of three tall green bamboo stalks with joints, growing up from the bottom edge and reaching "
               "the top edge, with a few sprays of slender bamboo leaves near the top and middle. Seen straight on, "
               "the stalks upright. Fully transparent background, nothing else. " + STYLE),
    "blossom": ("3:2", True,
                "A cherry blossom branch reaching in from the top-left corner towards the right, dark brown twisty "
                "branch with clusters of pink five-petal blossoms and a few buds. It enters from the top-left corner "
                "of the image. Fully transparent background, nothing else. " + STYLE),
}


JOBS.update(OUTDOOR)

# the features screen (owner, 2026-11-18: orleans' three plates, ninja style, explaining the gameplay)
FEATURES = {
    "plate": ("3:4", True,
              "One tall ninja-themed card plate for a game menu, seen straight on: a dark charcoal lacquered wooden "
              "panel with a slim deep-red lacquer inner border, a black braided cord with a red tassel knotted across the "
              "top edge, small steel shuriken studs at the four corners, faint brushed-ink cloud swirls in the frame. The "
              "middle is one big flat, plain, very dark area filling most of the panel, so white text reads on it. "
              "Fully transparent background around the plate, nothing else. " + STYLE),
    "icon_lines": ("1:1", True,
                   "A cartoon game icon: a gleaming katana blade mid-swing slicing a juicy watermelon cleanly in half, "
                   "a bright curved motion streak along the cut, red juice droplets flying. Centred, no background, fully "
                   "transparent background. " + STYLE),
    "icon_frenzy": ("1:1", True,
                    "A cartoon game icon: one glowing golden star fruit (carambola) wearing a red ninja headband with its "
                    "tails fluttering, golden sparkles around it. Centred, fully transparent background. " + STYLE),
    "icon_bomb": ("1:1", True,
                  "A cartoon game icon: a juicy glowing peach with a leaf beside a round black ninja bomb with a lit "
                  "sparkling fuse and a small white shuriken emblem on it. Centred, fully transparent background. " + STYLE),
}
JOBS.update(FEATURES)

# the 2000s fruit-machine look (owner, 2026-11-18: "fit the vibe with the old 2000s fruit feel", after the fruit were
# re-rendered as glossy Golden-Dragon-style CGI): pre-rendered 3D casino-arcade art instead of the flat cartoon wall
STYLE2K = ("Pre-rendered glossy 3D CGI in the style of a mid-2000s Asian arcade or casino fruit slot machine cabinet: "
           "rich saturated colours, deep red lacquer and polished gold trim, chrome and gold bevels with bright "
           "specular glints, soft bloom and glow, little lens sparkles, high contrast, slick and premium. "
           "No text, no letters, no numbers, no logos, no watermark, no characters, no people, no fruit.")
CASINO = {
    "wall2k": ("16:9", False,
               "The background of a fruit-slicing slot game: a lavish Asian dojo-style casino hall seen straight on. The "
               "centre two thirds is one big calm, dark, smooth panel of deep crimson-to-black lacquer with a faint "
               "golden sunburst of rays fanning out from behind the middle and a few tiny drifting gold sparkles - "
               "uncluttered and darker in the middle so bright glossy fruit pop on it. Framing it on the far left and "
               "right: thick glossy red lacquered pillars wrapped by coiling golden dragons, with glowing red-and-gold "
               "paper lanterns behind. Across the top, a polished dark wood and gold beam lined with a row of warm "
               "glowing marquee light bulbs like a classic fruit machine. No floor visible. " + STYLE2K),
    "wall2k_tall": ("9:16", False,
                    "The portrait background of a fruit-slicing slot game on a phone: a lavish Asian casino hall seen "
                    "straight on. Almost all of it is one big calm, dark, smooth panel of deep crimson-to-black lacquer "
                    "with a faint golden sunburst of rays fanning out from behind the middle and a few tiny drifting "
                    "gold sparkles - uncluttered and darker in the middle so bright glossy fruit pop on it. Thin glossy "
                    "red pillars with golden dragon coils at the very left and right edges; across the top, a polished "
                    "dark wood and gold beam lined with a row of warm glowing marquee light bulbs like a classic fruit "
                    "machine. No floor visible. " + STYLE2K),
    "lantern2k": ("2:3", True,
                  "One glossy round red Chinese silk lantern hanging from a short gold cord at the top, with polished "
                  "gold caps at top and bottom, a long red-and-gold tassel underneath, glowing warmly from inside. Plain, "
                  "no writing or symbols. Seen straight on, centred, the cord reaching the very top edge of the image. "
                  "Fully transparent background. " + STYLE2K),
}
JOBS.update(CASINO)


def run(name):
    aspect, transparent, prompt = JOBS[name]
    out = os.path.join(OUT, name + ".png")
    try:
        _, cost = generate(out, prompt, aspect, transparent)
        return f"OK {name} cost {cost}"
    except RuntimeError as e:
        return f"FAIL {name} {e}"


if __name__ == "__main__":
    names = sys.argv[1:] or list(JOBS)
    os.makedirs(OUT, exist_ok=True)
    with ThreadPoolExecutor(len(names)) as ex:
        for line in ex.map(run, names):
            print(line, flush=True)
