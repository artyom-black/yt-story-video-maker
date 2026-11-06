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
    f"{P.HEAD}Clean simple icon of {P.KAI_ID}: exactly the same head, face, smile and messy brown hair as image 0, "
    "seen from the chest up and centred in a square picture. He wears a plain bright red t-shirt with short sleeves "
    "and a round neck; his shoulders are drawn by the t-shirt, a thin black neck line joins the head to the collar. "
    "His arms hang down out of the picture, no hands visible. A happy friendly smile, looking straight at the viewer. "
    "Plain pure white background, nothing else. Square picture. No text, no letters.")

SIDE = ("seen from the side, moving to the right of the picture, his face, body and feet turned to the right, "
        "caught in the middle of the action: ")
COSTUMES = {
    "skate": SIDE + "riding fast on a skateboard, knees bent, leaning forward, arms out for balance, wind lines "
             "behind him, an excited grin, wearing a yellow hoodie and long blue jeans",
    "knight": SIDE + "charging forward at a run, one leg far in front of the other, holding his sword high above "
              "his head, a brave shouting face, wearing shining grey armour from neck to feet",
    "samurai": SIDE + "jumping forward through the air with both knees bent, swinging a katana sword with both "
               "hands, a fierce face, wearing a dark blue kimono top, wide grey trousers and sandals",
    "caveman": SIDE + "running fast with long strides, holding a wooden club over his shoulder, a scared face looking "
               "back over his shoulder, wearing a sleeveless brown fur tunic and long brown fur trousers",
    "chef": SIDE + "running forward wearing a white chef jacket, black trousers and a white chef hat, holding a "
            "black frying pan by its handle in one hand, stretched out in front of him; a round golden pancake is "
            "flipping in the air just above the pan; a surprised funny face looking up at the pancake",
    "pharaoh": SIDE + "marching proudly with big steps, chin up, one arm thrown forward pointing ahead and giving "
               "orders, wearing a blue and gold striped headdress, a gold collar and a long white robe to his "
               "ankles with a gold belt, golden sandals",
    "detective": SIDE + "sneaking forward on tiptoe, bent over, holding a big magnifying glass close to the ground "
                 "and following a trail of footprints, a curious squinting face, wearing a long brown trench coat, "
                 "a brown hat and brown trousers",
    "pirate": SIDE + "leaping forward with one foot in the air, holding a small curved sword up high, laughing, "
              "wearing a red and white striped shirt, a black vest, black trousers, boots, a black pirate hat and "
              "an eye patch",
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
    face = os.path.join(P.REPO, "channel", "profile-picture.png")     # the approved face
    prefs = [P.small_ref(face, os.path.join(out, "_face_ref.png"))] if os.path.exists(face) else refs
    jobs = [(f"profile_{n}", PROFILE, 1024, 1024) for n in range(1, count + 1)]
    jobs += [(f"{k}_{n}", costume_prompt(v), 768, 1024) for k, v in COSTUMES.items() for n in range(1, count + 1)]
    only = [w for w in os.environ.get("ONLY", "").replace(",", " ").split() if w]
    if only:
        jobs = [j for j in jobs if j[0].rsplit("_", 1)[0] in only]
    for lab, prompt, w, h in jobs:
        dst = os.path.join(out, f"{lab}.png")
        try:
            P.draw(prompt, w, h, seed=random.randint(1, 10 ** 6), refs=prefs if lab.startswith("profile") else refs, out=dst)
            print("drew", lab, flush=True)
        except Exception as ex:
            print(f"{lab} failed: {str(ex)[:150]}", flush=True)
    for r in set(refs + prefs):
        os.remove(r)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "KAI FILMS", int(sys.argv[3]) if len(sys.argv) > 3 else 3)
