"""Character options: 4 original stick-figure designs for the channel's main character, each standing,
shocked, laughing, in a scene and as a thumbnail face, so one can be chosen.

    python -m maker.char_options OUT_DIR
writes OUT_DIR/<A-D>_<view>.png and OUT_DIR/options.jpg (one row per design)
"""
from __future__ import annotations

import os
import sys

from PIL import Image, ImageDraw, ImageFont

from .art_lab import generate

NO_TEXT = "Absolutely no text, no letters, no watermark."

STICK = ("Simple 2D stick figure cartoon in a clean explainer-video style: a big round white head with a bold black "
         "outline, a body, arms and legs made of thick smooth black lines, simple round hands, two black dot eyes and "
         "simple expressive eyebrows and mouth, flat bright colours, no shading, very clean and minimal")

DESIGNS = {
    "A": ("Side fringe", f"{STICK}. His signature: a glossy black side-swept fringe of hair falling over one side "
                         f"of his forehead"),
    "B": ("Quiff", f"{STICK}. His signature: one tall bouncy black curl of hair standing up on top of his head, "
                   f"like a question mark"),
    "C": ("Round glasses", f"{STICK}. His signature: big round black glasses and short messy brown hair"),
    "D": ("Red scarf", f"{STICK}. He is bald. His signature: a long bright red scarf wrapped around his neck with "
                       f"the ends flying"),
}

VIEWS = {
    "1_standing": ("standing relaxed facing the viewer, friendly smile, waving one hand, full body, plain light "
                   "background", 768, 1024),
    "2_shocked": ("extremely shocked, eyes huge, mouth wide open, both hands on his head, full body, plain light "
                  "background", 768, 1024),
    "3_laughing": ("laughing hard, eyes closed, holding his belly, full body, plain light background", 768, 1024),
    "4_scene": ("walking along a path through a bright green countryside with simple round trees and a small "
                "village in the distance, curious face, 16:9 picture", 1280, 720),
    "5_thumb": ("YouTube thumbnail: close-up of his head and shoulders, extremely shocked, eyes wide, mouth open, "
                "very bright yellow simple background", 1280, 720),
}


def run(out):
    os.makedirs(out, exist_ok=True)
    for d, (_name, look) in DESIGNS.items():
        base = os.path.join(out, f"{d}_1_standing.png")
        for view, (what, w, h) in VIEWS.items():
            path = os.path.join(out, f"{d}_{view}.png")
            if os.path.exists(path):
                continue
            if view == "1_standing":
                prompt = f"Character design. {look}, {what}. {NO_TEXT}"
                refs = []
            else:
                prompt = (f"The same stick figure character as in image 0: exactly the same head, face, hair, "
                          f"signature and drawing style. {look}, {what}. Only one person. {NO_TEXT}")
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
        row = Image.new("RGB", (300 * 3 + 640 * 2 + 50, 440), (25, 25, 25))
        dr = ImageDraw.Draw(row)
        dr.text((16, 6), f"{d}  {name}", font=font, fill=(255, 215, 0))
        x = 10
        for view in VIEWS:
            p = os.path.join(out, f"{d}_{view}.png")
            box = (300, 380) if view[0] in "123" else (640, 360)
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
