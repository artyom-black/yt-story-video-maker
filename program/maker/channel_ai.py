"""Channel art drawn with the same AI and the same Kai as the videos.

    profile_N.png  800x800   Kai's face, for the round channel picture
    banner_N.png   2560x1440 Kai through history, channel name inside the 1546x423 centre area every device shows

Usage:  python -m maker.channel_ai OUT_DIR "KAI FILMS" 4
"""
from __future__ import annotations

import os
import random
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import pictures as P

FONT = os.path.join(P.ROOT, "fonts", "Anton-Regular.ttf")
TAGLINE = "REAL HISTORY. ONE STICKMAN."

PROFILE = (
    f"{P.HEAD}Close-up portrait of {P.KAI_ID}, only his head and shoulders, big in the middle of a square picture, "
    "a happy confident smile, looking straight at the viewer, wearing his brown peasant tunic. Behind him a plain bright "
    "golden-yellow circle on a plain deep blue background, nothing else. Square picture. No text, no letters.")

BANNER = (
    f"{P.HEAD}A wide colourful cartoon picture: a very wide, short picture. Five copies of {P.KAI_ID}, small enough that each one is "
    "seen whole from head to feet, standing side by side in a row on the right half of the picture, each one in a different time in history: a medieval peasant in a brown tunic holding a "
    "sickle, a knight in shining armour with a sword, an Egyptian pharaoh with a striped headdress, a Viking with a "
    "round helmet and a shield, and a Roman soldier with a red cape. Every one of them has the same white round "
    "head, the same messy brown hair, two dot eyes and a big smile. Behind them a bright drawn landscape that changes "
    "from a village with a castle to pyramids and the sea. The left half of the picture is open blue sky with a few "
    "soft clouds and nothing else. Very wide picture. No text, no letters.")


def profile(src, dst):
    im = Image.open(src).convert("RGB")
    s = min(im.size)
    im = im.crop(((im.width - s) // 2, (im.height - s) // 2, (im.width + s) // 2, (im.height + s) // 2))
    im.resize((800, 800), Image.LANCZOS).save(dst)


def banner(src, dst, name):
    """The drawn strip fills exactly the 1546x423 centre that every device shows; the rest of the 2560x1440
    (seen only on TVs) is a soft blurred stretch of the same picture."""
    strip = Image.open(src).convert("RGB")
    im = strip.resize((2560, 1440), Image.LANCZOS).filter(ImageFilter.GaussianBlur(40))
    im.paste(strip.resize((1546, 424), Image.LANCZOS), (507, 508))
    d = ImageDraw.Draw(im)
    left, size = 560, 190
    font = ImageFont.truetype(FONT, size)
    while d.textlength(name, font=font) > 680 and size > 90:
        size -= 10
        font = ImageFont.truetype(FONT, size)
    small = ImageFont.truetype(FONT, 50)
    y_name = 560
    for dx, dy in [(x, y) for x in range(-8, 9, 4) for y in range(-8, 9, 4)]:
        d.text((left + dx, y_name + dy), name, font=font, fill="black")
    d.text((left, y_name), name, font=font, fill="#ffd23f")
    y_tag = y_name + size + 30
    for dx, dy in [(x, y) for x in range(-4, 5, 4) for y in range(-4, 5, 4)]:
        d.text((left + dx, y_tag + dy), TAGLINE, font=small, fill="black")
    d.text((left, y_tag), TAGLINE, font=small, fill="white")
    im.save(dst)


def main(out, name, count):
    os.makedirs(out, exist_ok=True)
    refs = [P.small_ref(P.FACE_REF, os.path.join(out, "_kai_ref.png"))]
    for n in range(1, count + 1):
        for kind, prompt, w, h in (("profile", PROFILE, 1024, 1024), ("banner", BANNER, 1920, 528)):
            raw = os.path.join(out, f"_{kind}_{n}_raw.png")
            try:
                P.draw(prompt, w, h, seed=random.randint(1, 10 ** 6), refs=refs, out=raw)
            except Exception as ex:
                print(f"{kind} {n} failed: {str(ex)[:150]}", flush=True)
                continue
            if kind == "profile":
                profile(raw, os.path.join(out, f"profile_{n}.png"))
            else:
                banner(raw, os.path.join(out, f"banner_{n}.png"), name)
            os.remove(raw)
            print("drew", kind, n, flush=True)
    os.remove(refs[0])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "KAI FILMS", int(sys.argv[3]) if len(sys.argv) > 3 else 4)
