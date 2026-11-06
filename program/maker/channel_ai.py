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
    f"{P.HEAD}Clean simple icon of {P.KAI_ID}, drawn exactly like image 0 with the same face and hair: only his big "
    "round head and the top of his shoulders, filling the middle of a square picture, one eyebrow raised and a curious "
    "cheeky smile, looking straight at the viewer. No hands, no arms in the picture. Plain pure white background, "
    "nothing else. Square picture. No text, no letters.")

COSTUMES = {
    "skate": "riding a skateboard with both arms out for balance, wearing a yellow hoodie",
    "knight": "in shining grey armour, holding up a sword proudly",
    "banana": "slipping on a banana peel, falling backwards with arms flailing and a shocked face, in an orange t-shirt",
    "caveman": "a caveman in a brown fur outfit, holding a wooden club and scratching his head, confused",
    "chef": "a chef with a tall white hat, tossing a pancake from a frying pan, happy",
    "astronaut": "an astronaut in a white space suit with the helmet off under one arm, waving",
    "pharaoh": "an Egyptian pharaoh with a blue and gold striped headdress, pointing forward like a boss",
    "detective": "a detective in a brown coat and hat, looking through a big magnifying glass",
    "pirate": "a pirate with an eye patch and a black pirate hat, holding up a small sword and laughing",
}


def costume_prompt(what):
    return (f"{P.HEAD}One single full body {P.KAI_ID} {what}. A clear funny pose and a big clear "
            "face, the whole body from the top of his hair to his shoes visible. He has exactly two thin black stick arms "
            "and two thin black stick legs; each arm ends in one small round white cartoon hand with a black outline, "
            "exactly like image 0. Clean bold even black outlines, flat bright colours. Plain pure white background, nothing else, no ground, no shadow. "
            "No text, no letters.")


def profile(src, dst):
    im = Image.open(src).convert("RGB")
    s = min(im.size)
    im = im.crop(((im.width - s) // 2, (im.height - s) // 2, (im.width + s) // 2, (im.height + s) // 2))
    im.resize((800, 800), Image.LANCZOS).save(dst)


def trim(path):
    """Cut the white around a drawn character."""
    im = Image.open(path).convert("RGB")
    gray = im.convert("L").point(lambda v: 255 if v < 235 else 0)
    box = gray.getbbox()
    return im.crop(box) if box else im


def banner(paths, dst):
    """Like the big stick figure channels: a white banner with one row of characters all walking the same way,
    no text. The row sits inside the 1546x423 centre that every device shows."""
    im = Image.new("RGB", (2560, 1440), (255, 255, 255))
    figs = [trim(p) for p in paths]
    h = 380
    ratio = sum(f.width / f.height for f in figs)
    h = int(min(h, 1546 * 0.86 / ratio))                    # always some white space between them
    figs = [f.resize((max(1, int(f.width * h / f.height)), h), Image.LANCZOS) for f in figs]
    gap = (1546 - sum(f.width for f in figs)) / (len(figs) + 1)
    x = 507 + gap
    for f in figs:
        im.paste(f, (int(x), 508 + (424 - h) // 2 + (380 - h) // 3))
        x += f.width + gap
    im.save(dst)


def main(out, name, count):
    os.makedirs(out, exist_ok=True)
    refs = [P.small_ref(P.FACE_REF, os.path.join(out, "_kai_ref.png"))]
    jobs = [(f"profile_{n}", PROFILE, 1024, 1024) for n in range(1, count + 1)]
    jobs += [(f"{k}_{n}", costume_prompt(v), 768, 1024) for k, v in COSTUMES.items() for n in range(1, count + 1)]
    only = [w for w in os.environ.get("ONLY", "").replace(",", " ").split() if w]
    if only:
        jobs = [j for j in jobs if j[0].rsplit("_", 1)[0] in only]
    for lab, prompt, w, h in jobs:
        dst = os.path.join(out, f"{lab}.png")
        try:
            P.draw(prompt, w, h, seed=random.randint(1, 10 ** 6), refs=refs, out=dst)
            print("drew", lab, flush=True)
        except Exception as ex:
            print(f"{lab} failed: {str(ex)[:150]}", flush=True)
    os.remove(refs[0])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "KAI FILMS", int(sys.argv[3]) if len(sys.argv) > 3 else 3)
