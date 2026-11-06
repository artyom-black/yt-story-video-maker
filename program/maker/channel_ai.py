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

SIDE = ("side view facing the right of the picture: his face, body and feet turned to the right. He is NOT "
        "running and NOT walking: he stands in place with both feet on the ground, busy doing his action, a normal "
        "grown-up size: ")
COSTUMES = {
    "skate": SIDE + "riding a skateboard, knees bent, leaning forward, arms out for balance, wind lines behind him, "
             "an excited grin, wearing a yellow hoodie and long blue jeans",
    "knight": SIDE + "in a fighting stance, front knee bent, holding the handle of his sword firmly with both hands "
              "and swinging it forward in front of him, the sword clearly in his hands, a brave face, wearing shining "
              "grey armour from neck to feet",
    "samurai": "a full side profile view like a shadow puppet: we see him exactly from his left side, his chest, nose side of his face and toes all pointing to the right edge of the picture, never facing the viewer. " + SIDE + "with a big round head and a short small cartoon body like every Kai (the head is a quarter of his height), in a ready fighting stance, front foot forward, knees slightly bent, holding a short katana with both hands at the handle near his waist, the long blade pointing forward and up to the right, a focused serious face, wearing a dark blue kimono top, wide grey trousers and sandals",
    "caveman": SIDE + "kneeling on one knee and rubbing a stick between both hands on a small piece of wood, a little "
               "orange flame and smoke starting at the tip of the stick, an amazed excited face, wearing a "
               "sleeveless brown fur tunic and long brown fur trousers",
    "chef": "his body the same size as always: a big round head on a normal stick figure body, the head about a quarter of his whole height, " + SIDE + "standing straight with both feet flat on the ground, legs in black trousers side by side, flipping a pancake: one hand holds a black frying pan by its handle out in front of him and a round golden pancake is in the air just above the pan, his face looking at the pancake, wearing a white chef jacket and a white chef hat",
    "pharaoh": "a short cartoon stick figure: a big round head, short neck, short body and short legs, exactly the same size and shape as KAI always is, no taller. " + SIDE + "standing proud, one bare thin black stick arm stretched straight forward to the right with a small white cartoon hand pointing one finger ahead, no sleeve on that arm, his face in profile looking where he points, wearing a classic Egyptian pharaoh headdress (a blue and gold striped cloth that covers the top of his head and hangs down behind his ears to his shoulders), a gold collar and a sleeveless white robe down to his ankles with a gold belt, golden sandals",
    "detective": "his body the same size as always: a big round head on a normal stick figure body, the head about a quarter of his whole height, " + SIDE + "holding a small round magnifying glass right in front of his eye "
                 "with one hand and looking through it at something ahead of him, his eye looking big through the "
                 "glass, a curious face, wearing a long brown trench coat, a brown hat and brown trousers",
    "musician": "his body the same size as always: a big round head on a normal stick figure body, the head about a quarter of his whole height, " + SIDE + "standing with feet apart, playing an acoustic guitar: the guitar body held against his belly, one hand strumming the strings, the other hand holding the neck of the guitar out in front of him to the right, eyes closed, singing happily with his mouth open, a few music notes floating in the air, wearing a blue denim jacket, a white t-shirt and black trousers",
    "pirate": "his body the same size as always: a big round head on a normal stick figure body, the head about a quarter of his whole height, " + SIDE + "standing with both feet on the ground, feet apart, front knee a little bent, holding a small curved sword pointed forward with one hand, other hand on his hip, laughing, black trousers tucked into black boots, a red and white striped shirt, a black vest, a black pirate hat and an eye patch",
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


def head_width(path):
    """Diameter of Kai's head circle. The white face is found, and a circle is fitted to its lower half (the chin
    line), because hair, hats and headdresses cover the top of the head."""
    import cv2
    import numpy as np
    from scipy import ndimage
    g = np.array(Image.open(path).convert("L"))
    lab, n = ndimage.label(g > 225)
    best = None
    for i, sl in enumerate(ndimage.find_objects(lab), 1):
        ys, xs = sl
        h, w = ys.stop - ys.start, xs.stop - xs.start
        if ys.start == 0 or xs.start == 0 or ys.stop >= g.shape[0] or xs.stop >= g.shape[1]:
            continue
        if ys.start > g.shape[0] * 0.55 or not 0.5 < w / h < 1.8:
            continue
        area = int((lab[sl] == i).sum())
        if area > 3000 and (best is None or area > best[0]):
            best = (area, i)
    if not best:
        return None
    m = cv2.morphologyEx((lab == best[1]).astype("uint8"), cv2.MORPH_CLOSE, np.ones((15, 15), "uint8"))
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    pts = max(cs, key=cv2.contourArea)[:, 0, :].astype(float)
    low = pts[pts[:, 1] > pts[:, 1].mean()]
    x, y = low[:, 0], low[:, 1]
    cx, cy, c = np.linalg.lstsq(np.c_[2 * x, 2 * y, np.ones(len(x))], x ** 2 + y ** 2, rcond=None)[0]
    return 2 * float(np.sqrt(c + cx ** 2 + cy ** 2))


def banner(paths, dst, heads=None):
    """Like the big stick figure channels: a white banner with one row of characters, no text. Every Kai's head is
    the same size, they all stand on one ground line, and the row sits inside the 1546x423 centre every device shows."""
    im = Image.new("RGB", (2560, 1440), (255, 255, 255))
    heads = heads or [head_width(p) for p in paths]
    known = [h for h in heads if h]
    target = sorted(known)[len(known) // 2] if known else 1
    figs = []
    for p, hw in zip(paths, heads):
        f = trim(p)
        k = target / hw if hw else 1
        figs.append(f.resize((max(1, int(f.width * k)), max(1, int(f.height * k))), Image.LANCZOS))
    k = 400 / max(f.height for f in figs)
    k = min(k, 1546 * 0.88 / sum(f.width for f in figs))       # always some white space between them
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
