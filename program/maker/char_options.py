"""Character options: 4 original simple-style designs for Kai Films' main character, each shown in a neutral
outfit, as a poor 1346 peasant, as a rich lord and inside a scene, so you can see the same character
staying recognisable in different clothes and situations.

    python -m maker.char_options OUT_DIR
writes OUT_DIR/<A-D>_<view>.png and OUT_DIR/options.jpg (one row per design)
"""
from __future__ import annotations

import os
import sys

from PIL import Image, ImageDraw, ImageFont

from .art_lab import generate

NO_TEXT = "Absolutely no text, no letters, no watermark."

DESIGNS = {
    "A": ("Clean flat",
          "Simple flat 2D cartoon style with thick clean black outlines, flat colours, no shading, very few "
          "details. The character: a young man with a round peach-coloured face, two small black oval eyes, short "
          "thick eyebrows, a simple line mouth, a big swoosh of glossy black side-swept hair with the fringe "
          "falling over one side of his forehead, a slim simple body with normal adult proportions"),
    "B": ("Bean head",
          "Simple flat 2D cartoon style with thick clean black outlines and flat colours. The character: a "
          "young man with a smooth bean-shaped head with no neck, big expressive black eyebrows that do most of "
          "the acting, two black dot eyes, a small mouth, a short spiky black fringe sweeping to one side, a "
          "small simple body with thin arms and legs"),
    "C": ("Ink + red",
          "Black ink line drawing on warm off-white paper, loose confident brush lines, the whole world drawn in "
          "black, white and soft grey ink washes, and ONLY the main character's clothes coloured in bright red. "
          "The character: a young man with a simple oval face, dot eyes, a strong black ink side-swept fringe, "
          "a slim body with normal adult proportions"),
    "D": ("Paper cut-out",
          "Paper cut-out craft animation style: flat shapes cut from coloured paper with a subtle paper texture "
          "and soft drop shadows between layers, simple and charming. The character: a young man with a round "
          "light paper face, two black dot eyes, a black paper side-swept fringe, a slim simple body"),
}

VIEWS = {
    "1_neutral": ("wearing a plain grey t-shirt and dark trousers, standing relaxed facing the viewer, friendly "
                  "smile, full body, plain light background", 768, 1024),
    "2_peasant": ("wearing a patched rough red wool tunic down to the knees with a rope belt and brown wool "
                  "trousers, a poor medieval peasant in the year 1346, tired face, full body, plain light "
                  "background", 768, 1024),
    "3_lord": ("wearing a long red velvet robe with a white fur collar and a wide gold belt, a rich medieval "
               "lord in 1346, proud happy face, full body, plain light background", 768, 1024),
    "4_scene": ("in his patched red wool peasant tunic, sitting up on straw inside a dark medieval wooden hut at "
                "night next to a big brown cow, shocked face, small fire in the middle, 16:9 picture", 1280, 720),
}


def run(out):
    os.makedirs(out, exist_ok=True)
    for d, (_name, look) in DESIGNS.items():
        base = os.path.join(out, f"{d}_1_neutral.png")
        for view, (what, w, h) in VIEWS.items():
            path = os.path.join(out, f"{d}_{view}.png")
            if os.path.exists(path):
                continue
            if view == "1_neutral":
                prompt = f"Character design. {look}, {what}. {NO_TEXT}"
                refs = []
            else:
                prompt = (f"The same young man as in image 0: exactly the same face, hair, head shape and drawing "
                          f"style. {look}, {what}. Only one person. {NO_TEXT}")
                refs = [base] if os.path.exists(base) else []
            try:
                data = generate(prompt, w, h, seed=4242 + ord(d), refs=refs)
            except Exception as ex:
                print(d, view, "failed:", str(ex)[:200], flush=True)
                continue
            open(path, "wb").write(data)
            print("drew", d, view, flush=True)
    sheet(out)


def sheet(out):
    rows = []
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 44)
    except Exception:
        font = ImageFont.load_default()
    for d, (name, _look) in DESIGNS.items():
        row = Image.new("RGB", (300 * 3 + 640 + 40, 440), (25, 25, 25))
        dr = ImageDraw.Draw(row)
        dr.text((16, 6), f"{d}  {name}", font=font, fill=(255, 215, 0))
        x = 10
        for view in VIEWS:
            p = os.path.join(out, f"{d}_{view}.png")
            box = (300, 380) if view != "4_scene" else (640, 360)
            if os.path.exists(p):
                im = Image.open(p).convert("RGB")
                im.thumbnail(box)
                row.paste(im, (x, 60))
            x += box[0] + 10
        rows.append(row)
    full = Image.new("RGB", (rows[0].width, sum(r.height for r in rows)))
    y = 0
    for r in rows:
        full.paste(r, (0, y))
        y += r.height
    full.save(os.path.join(out, "options.jpg"), quality=88)


if __name__ == "__main__":
    run(sys.argv[1])
