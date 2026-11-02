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
         "uncluttered, nothing small and fussy. Only ONE person in the whole picture: him. The whole picture is "
         "fully drawn edge to edge (no empty white areas); the {side} side of the background is just simpler "
         "(sky, wall or shadow) so big words fit there. Bright enough to see everything clearly even at night. "
         "Real-life sizes. Clean and correct: he has exactly two arms, two hands and two legs; every animal has a normal "
         "body with the right number of legs and stands on something solid; nothing floats in the air. "
         "Absolutely no text, no letters, no watermark.")


HALF_STYLE = ("One half of a split-screen YouTube thumbnail for a hit animated history explainer channel (a tall "
              "picture). Simple stick figure character exactly like the one in image 0: the same round white head, "
              "face, hair and thin black line arms and legs, big in the frame, in the lower two thirds, acting with "
              "an extreme, clear facial expression. Detailed, colourful, painted 2D cartoon world, bright, high "
              "contrast, one clear focal point, fully drawn edge to edge; the top quarter is open sky so a big word "
              "fits there. Only ONE person in the whole picture: him. Real-life sizes. He has exactly two arms, two "
              "hands and two legs; nothing floats. Absolutely no text, no letters, no watermark.")


def split(words, idea, info, ref, out, i):
    """Before/after thumbnail: 'LEFT WORDS / RIGHT WORDS | left scene || right scene'."""
    labels = [w.strip() for w in words.split("/")]
    scenes = [x.strip() for x in idea.split("||")]
    base = int(os.environ.get("THUMB_SEED", "900"))
    halves = []
    for j, scene in enumerate(scenes[:2]):
        prompt = f"{HALF_STYLE} He wears {info.get('clothes', 'simple clothes')}. The scene: {scene}."
        data = None
        for t in range(3):
            try:
                pinned = (info.get("seeds") or [])[j:j + 1]
                seed = (int(pinned[0]) if pinned and pinned[0].isdigit() and not t
                        else base + i * 37 + j * 101 + 1000 * t)
                print(f"half {j + 1}: seed {seed}", flush=True)
                data = generate(prompt + (" Friendly, clean, family-friendly cartoon." if t else ""), 640, 720,
                                seed=seed, refs=[ref])
                break
            except Exception as ex:
                print(f"half {j + 1} try {t + 1} failed: {str(ex)[:150]}", flush=True)
        if data is None:
            return None
        hp = os.path.join(out, f"thumb_{i}_half{j + 1}.png")
        open(hp, "wb").write(data)
        halves.append(Image.open(hp).convert("RGB").resize((640, 720), Image.LANCZOS))
    im = Image.new("RGB", (1280, 720), "white")
    im.paste(halves[0], (0, 0)); im.paste(halves[1], (640, 0))
    im = ImageEnhance.Contrast(ImageEnhance.Color(im).enhance(1.2)).enhance(1.08).convert("RGBA")
    d = ImageDraw.Draw(im)
    d.rectangle([632, 0, 648, 720], fill="#111111"); d.rectangle([636, 0, 644, 720], fill="#ffffff")
    for j, lab in enumerate(labels[:2]):
        layer = text_layer(lab.upper(), 150, fill="#ffd23f" if j == 0 else "#ff4d4d")
        s_ = min(1.0, 360 / layer.width, 125 / layer.height)
        layer = layer.resize((int(layer.width * s_), int(layer.height * s_)), Image.LANCZOS)
        im.alpha_composite(layer, (j * 640 + (640 - layer.width) // 2, 8))
    final = os.path.join(out, f"thumb_{i}.png")
    im.convert("RGB").save(final, quality=95)
    return final


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
        elif k == "SEEDS":                                   # pin a picture: "SEEDS: auto, 155"
            info["seeds"] = [x.strip() for x in v.split(",")]
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
    s = min(1.0, 460 / block.width, 300 / block.height)
    block = block.resize((int(block.width * s), int(block.height * s)), Image.LANCZOS)
    block = block.rotate(-5 if side == "right" else 5, expand=True, resample=Image.BICUBIC)
    x = 1280 - block.width - 30 if side == "right" else 30
    im.alpha_composite(block, (x, 25))                    # in the sky / top area, never over the action
    im.convert("RGB").save(out, quality=95)


def make(story, out):
    info = read(story)
    ref = os.path.join(ROOT, info["character"])
    os.makedirs(out, exist_ok=True)
    done = []
    for i, (words, idea) in enumerate(info["thumbs"], 1):
        if "||" in idea:                                   # before/after split thumbnail
            final = split(words, idea, info, ref, out, i)
            if final:
                done.append((final, words))
            continue
        side = "right" if i % 2 else "left"
        prompt = (f"{STYLE.format(side=side)} He wears {info.get('clothes', 'simple clothes')}. "
                  f"The scene: {idea}. The character is on the {'left' if side == 'right' else 'right'} "
                  f"two thirds of the picture.")
        import hashlib
        h = hashlib.sha1(prompt.encode()).hexdigest()[:8]
        plain = os.path.join(out, f"thumb_{i}_plain_{h}.png")      # a changed idea gets a new picture,
        for old in os.listdir(out):                                # an unchanged one is kept
            if old.startswith(f"thumb_{i}_plain") and old != os.path.basename(plain):
                os.remove(os.path.join(out, old))
        if os.path.exists(plain) and os.path.getsize(plain) < 1000:     # a broken file from a failed run
            os.remove(plain)
        if not os.path.exists(plain):
            data = None
            for t in range(3):                       # the AI sometimes refuses a prompt: try again, gentler
                try:
                    data = generate(prompt + (" Friendly, clean, family-friendly cartoon." if t else ""), 1280, 720,
                                    seed=int(os.environ.get("THUMB_SEED", "900")) + i * 37 + 1000 * t, refs=[ref])
                    break
                except Exception as ex:
                    print(f"thumbnail {i} try {t + 1} failed: {str(ex)[:150]}", flush=True)
            if data is None:
                continue
            open(plain, "wb").write(data)
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
