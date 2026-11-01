"""Thumbnails, MrBeast style: one huge character with an extreme face, one crazy thing next to him, a detailed
bright painted world, and 1-3 big yellow words. Drawn from the video's character reference picture, so the
thumbnail shows exactly the character of the video.

The story file says what to draw:
    TITLE: What Did Medieval Peasants Actually Do All Day?
    CHARACTER: program/characters/stick/video1_reference.png
    CLOTHES: a patched brown wool tunic with a rope belt
    THUMBNAIL: COW BEDROOM? | terrified in his straw bed in a dark hut, a huge cow head right next to his face

    python -m maker.thumbs STORY_FILE OUT_DIR
writes OUT_DIR/thumb_<n>.png (finished, with text), OUT_DIR/thumb_<n>_plain.png and OUT_DIR/thumbnails.jpg
"""
from __future__ import annotations

import os
import re
import sys

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

from .art_lab import generate
from .editor import text_layer

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

STYLE = ("YouTube thumbnail for a hit animated history explainer channel. Simple stick figure character exactly "
         "like the one in image 0: the same round white head, face, hair and thin black line arms and legs, now "
         "big in the frame and acting with an extreme, clear facial expression. The world around him is a "
         "detailed, colourful, painted 2D cartoon background, bright and high contrast, one clear focal point, "
         "uncluttered, nothing small and fussy. Leave the {side} third of the picture calm and simple for big "
         "words. Real-life sizes. Absolutely no text, no letters, no watermark.")


def read(story):
    info = {"thumbs": []}
    for line in open(story, encoding="utf-8"):
        m = re.match(r"^([A-Z_]+):\s*(.*)$", line.strip())
        if not m:
            continue
        k, v = m.groups()
        if k == "THUMBNAIL" and "|" in v:
            words, idea = (x.strip() for x in v.split("|", 1))
            info["thumbs"].append((words, idea))
        elif k in ("TITLE", "CHARACTER", "CLOTHES"):
            info[k.lower()] = v.strip()
    return info


def finish(plain, words, side, out):
    """The words: huge yellow letters with a thick black outline, slightly tilted, in the empty third."""
    im = Image.open(plain).convert("RGB").resize((1280, 720), Image.LANCZOS)
    im = ImageEnhance.Contrast(ImageEnhance.Color(im).enhance(1.2)).enhance(1.08).convert("RGBA")
    lines = words.upper().split(" ") if len(words) > 10 and " " in words else [words.upper()]
    layers = [text_layer(l, 170) for l in lines]
    w = max(l.width for l in layers)
    h = sum(l.height for l in layers) - 30 * (len(layers) - 1)
    block = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    y = 0
    for l in layers:
        block.alpha_composite(l, ((w - l.width) // 2, y))
        y += l.height - 30
    s = min(1.0, 460 / block.width, 560 / block.height)
    block = block.resize((int(block.width * s), int(block.height * s)), Image.LANCZOS)
    block = block.rotate(-5 if side == "right" else 5, expand=True, resample=Image.BICUBIC)
    x = 1280 - block.width - 30 if side == "right" else 30
    im.alpha_composite(block, (x, (720 - block.height) // 2 - 40))
    im.convert("RGB").save(out, quality=95)


def make(story, out):
    info = read(story)
    ref = os.path.join(ROOT, info["character"])
    os.makedirs(out, exist_ok=True)
    done = []
    for i, (words, idea) in enumerate(info["thumbs"], 1):
        side = "right" if i % 2 else "left"
        plain = os.path.join(out, f"thumb_{i}_plain.png")
        if not os.path.exists(plain):
            prompt = (f"{STYLE.format(side=side)} He wears {info.get('clothes', 'simple clothes')}. "
                      f"The scene: {idea}. The character stands on the {'left' if side == 'right' else 'right'} "
                      f"two thirds of the picture.")
            open(plain, "wb").write(generate(prompt, 1280, 720, seed=900 + i * 37, refs=[ref]))
            print("drew thumbnail", i, flush=True)
        final = os.path.join(out, f"thumb_{i}.png")
        finish(plain, words, side, final)
        done.append((final, words))
    sheet(done, os.path.join(out, "thumbnails.jpg"))
    return done


def sheet(done, out):
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 34)
    except Exception:
        font = ImageFont.load_default()
    cols = 2
    rows = (len(done) + 1) // 2
    full = Image.new("RGB", (cols * 650, rows * 410), (20, 20, 20))
    for i, (p, _w) in enumerate(done):
        im = Image.open(p).convert("RGB").resize((640, 360))
        x, y = (i % cols) * 650, (i // cols) * 410
        full.paste(im, (x + 5, y + 45))
        ImageDraw.Draw(full).text((x + 10, y + 4), str(i + 1), font=font, fill=(255, 215, 0))
    full.save(out, quality=90)


if __name__ == "__main__":
    make(sys.argv[1], sys.argv[2])
