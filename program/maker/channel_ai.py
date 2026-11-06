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
    "skate": "riding a skateboard with both arms out for balance, wearing a yellow hoodie and long blue jeans that "
             "cover his legs down to his shoes",
    "knight": "in shining grey armour from his neck down to his feet, his legs fully covered by grey leg armour, "
              "holding up a sword proudly",
    "banana": "wearing a plain orange t-shirt and long blue jeans, slipping on a banana peel like in an old cartoon: "
              "one foot shooting up into the air, his body falling backwards, both arms flailing, a shocked face with "
              "his mouth open, and under his other shoe one small normal-sized peeled yellow banana skin",
    "caveman": "a caveman wearing a brown fur tunic and long brown fur trousers that cover his legs down to his feet, "
               "holding a wooden club in one hand and scratching his head with the other, confused",
    "chef": "a chef wearing a white chef jacket, black trousers and a short white chef hat, holding a frying pan and "
            "flipping a pancake in the air, happy",
    "pharaoh": "an Egyptian pharaoh wearing a blue and gold striped headdress, a gold collar on his chest and a long "
               "white robe with a gold belt that reaches down to his ankles and covers his legs, golden sandals, "
               "pointing forward with one hand like a boss",
    "detective": "a detective wearing a long brown trench coat, a brown hat and brown trousers, holding a big round "
                 "magnifying glass up next to his face with one hand, squinting curiously",
    "pirate": "a pirate wearing a red and white striped shirt, a black vest, black trousers and boots, a black pirate "
              "hat and an eye patch, holding up a small curved sword and laughing",
}


def costume_prompt(what):
    return (f"{P.HEAD}One single full body {P.KAI_ID} {what}. He is fully dressed in that outfit. He is a normal grown-up size, the same height as always. A clear funny pose and a big clear "
            "face, the whole body from the top of his hair to his shoes visible. He has exactly two thin black stick arms; his legs are fully covered by the clothes of his outfit; each arm ends in one small round white cartoon hand with a black outline, "
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
    # one common scale for all, so a tall hat does not make a character smaller than the others
    k = 380 / max(f.height for f in figs)
    k = min(k, 1546 * 0.86 / sum(f.width for f in figs))       # always some white space between them
    figs = [f.resize((max(1, int(f.width * k)), max(1, int(f.height * k))), Image.LANCZOS) for f in figs]
    h = max(f.height for f in figs)
    gap = (1546 - sum(f.width for f in figs)) / (len(figs) + 1)
    x = 507 + gap
    for f in figs:
        im.paste(f, (int(x), 508 + (424 - h) // 2 + (h - f.height)))   # all standing on one line
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
